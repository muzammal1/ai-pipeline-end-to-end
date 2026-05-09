import json
import logging
import os
import re
import subprocess

import config
from exceptions import PipelineError

log = logging.getLogger("pipeline")

MAX_ITERATIONS = 5

PACKAGE_JSON = {
    "name": "pipeline-tests",
    "version": "1.0.0",
    "scripts": {"test": "jest --testEnvironment jsdom --json --outputFile=test-run-raw.json"},
    "jest": {
        "testEnvironment": "jsdom",
        "testMatch": ["**/tests/**/*.test.js"],
    },
    "devDependencies": {
        "jest": "^29.0.0",
        "jest-environment-jsdom": "^29.0.0",
        "@testing-library/dom": "^9.0.0",
        "@testing-library/jest-dom": "^6.0.0",
        "@testing-library/user-event": "^14.0.0",
    },
}


_SHARED_NM = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".npm-cache", "node_modules")


def _install_deps(out_dir: str) -> None:
    """Install test deps once into a shared cache, then symlink into out_dir."""
    nm_target = os.path.join(out_dir, "node_modules")

    # If a real node_modules already exists here, skip
    if os.path.isdir(nm_target) and not os.path.islink(nm_target):
        return

    # Bootstrap shared cache on first ever install
    cache_dir = os.path.dirname(_SHARED_NM)
    os.makedirs(cache_dir, exist_ok=True)

    if not os.path.isdir(_SHARED_NM):
        log.info("Building shared npm cache (one-time, ~2 min)…")
        pkg_path = os.path.join(cache_dir, "package.json")
        with open(pkg_path, "w") as f:
            json.dump(PACKAGE_JSON, f, indent=2)
        result = _npm(["install"], cwd=cache_dir, timeout=240)
        if result.returncode != 0:
            raise PipelineError(f"npm install failed: {result.stderr[:400]}", stage="test-runner")

    # Symlink shared node_modules into the story output dir
    if os.path.islink(nm_target):
        os.unlink(nm_target)
    os.symlink(_SHARED_NM, nm_target)


def _npm(cmd: list[str], cwd: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["npm"] + cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _read_ac(out_dir: str) -> str:
    ac_path = os.path.join(out_dir, "acceptance-criteria.txt")
    if not os.path.exists(ac_path):
        return ""
    with open(ac_path) as f:
        return f.read().strip()


def run(issue_key: str, out_dir: str) -> str:
    """Write tests, run them, iterate until passing. Returns 'PASS' or 'FAIL'."""
    tests_dir = os.path.join(out_dir, "tests")
    os.makedirs(tests_dir, exist_ok=True)

    pkg_path = os.path.join(out_dir, "package.json")
    if not os.path.exists(pkg_path):
        with open(pkg_path, "w") as f:
            json.dump(PACKAGE_JSON, f, indent=2)

    log.info("[%s] Installing test dependencies…", issue_key)
    _install_deps(out_dir)
    log.info("[%s] Dependencies ready", issue_key)

    acceptance_criteria = _read_ac(out_dir)

    # Generate initial test file via claude
    _write_tests_with_claude(issue_key, out_dir, acceptance_criteria)

    status = "FAIL"
    last_output = ""
    for attempt in range(1, MAX_ITERATIONS + 1):
        log.info("[%s] Test run attempt %d/%d", issue_key, attempt, MAX_ITERATIONS)
        run_result = _npm(["test", "--", "--forceExit"], cwd=out_dir, timeout=120)
        last_output = run_result.stdout + run_result.stderr

        if run_result.returncode == 0:
            log.info("[%s] All tests passing on attempt %d", issue_key, attempt)
            status = "PASS"
            break

        log.warning("[%s] Tests failed on attempt %d", issue_key, attempt)
        if attempt < MAX_ITERATIONS:
            fixed = _apply_programmatic_fixes(out_dir, last_output)
            if not fixed:
                log.info("[%s] No programmatic fix matched — asking Claude to fix…", issue_key)
                _fix_with_claude(issue_key, out_dir, last_output)

    # Save final results
    results_path = os.path.join(out_dir, "test-results.txt")
    final_run = _npm(["test", "--", "--forceExit", "--verbose"], cwd=out_dir, timeout=120)
    with open(results_path, "w") as f:
        f.write(f"Status: {status}\n")
        f.write(f"Attempts: {attempt}\n\n")
        f.write(final_run.stdout)
        f.write(final_run.stderr)

    log.info("[%s] Test stage complete: %s", issue_key, status)
    return status


def _write_tests_with_claude(issue_key: str, out_dir: str, ac: str) -> None:
    index_path = os.path.join(out_dir, "index.html")
    index_html = open(index_path).read() if os.path.exists(index_path) else ""

    prompt = f"""Write Jest unit tests for this web application. The tests go in tests/app.test.js.

ACCEPTANCE CRITERIA (write exactly one test per criterion — use the criterion as the test name):
{ac if ac else "(read acceptance-criteria.txt)"}

CRITICAL RULES — follow these exactly or the tests will fail in jsdom:
1. Load the HTML with ONLY this pattern (never use document.write or document.open):
   const fs = require('fs');
   const path = require('path');
   beforeEach(() => {{
     document.body.innerHTML = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
   }});

2. For inline <script> tags to execute, extract and eval them after setting innerHTML:
   document.querySelectorAll('script').forEach(s => {{ if (s.textContent) eval(s.textContent); }});

3. Import @testing-library/jest-dom at the top:
   require('@testing-library/jest-dom');

4. Use querySelector/getElementById directly — do NOT import from @testing-library/dom (it may not resolve).

5. Each test must be fully independent — beforeEach must reset document.body.innerHTML.

6. For click interactions: element.click() is fine. For input: element.value = 'x'; element.dispatchEvent(new Event('input'));

7. Never use async/await — keep tests synchronous.

Write the complete tests/app.test.js file now."""

    subprocess.run(
        [config.CLAUDE_BIN, "-p", prompt, "--allowedTools", "Write,Edit"],
        cwd=out_dir,
        timeout=300,
        text=True,
    )


def _apply_programmatic_fixes(out_dir: str, failure_output: str) -> bool:
    """Apply known jsdom fixes directly without calling claude. Returns True if a fix was applied."""
    test_path = os.path.join(out_dir, "tests", "app.test.js")
    if not os.path.exists(test_path):
        return False

    with open(test_path) as f:
        content = f.read()

    original = content

    # Fix 1: document.write() → document.body.innerHTML
    if "document.write(" in content and "document.write(" in failure_output:
        log.info("Applying fix: replace document.write() with innerHTML pattern")
        # Replace the entire loadApp pattern
        content = re.sub(
            r"(function\s+\w+\(\)[^}]*)?document\.open\(\);?\s*\n?\s*document\.write\([^)]+\);?\s*\n?\s*document\.close\(\);?",
            "document.body.innerHTML = require('fs').readFileSync(require('path').join(__dirname, '..', 'index.html'), 'utf8');\n  document.querySelectorAll('script').forEach(s => { if (s.textContent) eval(s.textContent); });",
            content,
        )
        if "document.write(" in content:
            content = content.replace(
                "document.write(html);",
                "document.body.innerHTML = html;\n  document.querySelectorAll('script').forEach(s => { if (s.textContent) eval(s.textContent); });"
            )
            content = content.replace("document.open();\n", "").replace("document.close();\n", "")

    # Fix 2: Missing require for fs/path
    if "fs.readFileSync" in content and "require('fs')" not in content and 'require("fs")' not in content:
        log.info("Applying fix: add fs/path requires")
        content = "const fs = require('fs');\nconst path = require('path');\n" + content

    # Fix 3: Cannot find module '@testing-library/dom'
    if "@testing-library/dom" in failure_output and "getByRole" in content:
        log.info("Applying fix: replace @testing-library/dom with querySelector")
        content = re.sub(r"const\s*\{[^}]+\}\s*=\s*require\(['\"]@testing-library/dom['\"]\);?\n?", "", content)
        content = re.sub(r"import\s*\{[^}]+\}\s*from\s*['\"]@testing-library/dom['\"];?\n?", "", content)

    if content != original:
        with open(test_path, "w") as f:
            f.write(content)
        return True

    return False


def _fix_with_claude(issue_key: str, out_dir: str, failure_output: str) -> None:
    prompt = f"""The Jest tests are failing. Fix the test file tests/app.test.js.

FAILURE OUTPUT (last 2000 chars):
{failure_output[-2000:]}

RULES:
- NEVER use document.write(), document.open(), or document.close() — jsdom does not support them
- Load HTML with: document.body.innerHTML = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
- Then run scripts with: document.querySelectorAll('script').forEach(s => {{ if (s.textContent) eval(s.textContent); }});
- Do not use async/await
- Only fix what is broken — do not rewrite passing tests

Fix tests/app.test.js now."""

    subprocess.run(
        [config.CLAUDE_BIN, "-p", prompt, "--allowedTools", "Read,Write,Edit"],
        cwd=out_dir,
        timeout=300,
        text=True,
    )
