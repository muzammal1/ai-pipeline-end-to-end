#!/usr/bin/env python3
"""Zero Human Touch Pipeline — orchestrator.

Usage:
  uv run python orchestrator.py --once      # single poll cycle
  uv run python orchestrator.py --schedule  # run every 5 min forever
"""

import argparse
import logging
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import schedule

import config
from exceptions import PipelineError
from stages import jira_poller, build_agent, test_runner, github_pusher, vercel_deployer, qa_agent, email_reporter, jira_closer

# ── Logging ──────────────────────────────────────────────────────────────────

os.makedirs(config.LOGS_DIR, exist_ok=True)
os.makedirs(config.OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(config.LOGS_DIR, "pipeline.log")),
    ],
)
log = logging.getLogger("pipeline")


# ── Per-story pipeline ────────────────────────────────────────────────────────

def run_story(story: dict) -> None:
    issue_key   = story["issue_key"]
    summary     = story["summary"]
    requirements = story["requirements"]
    start       = time.time()

    log.info("[%s] ═══ Pipeline started ═══", issue_key)

    out_dir    = None
    pr_url     = f"https://github.com/{config.GITHUB_REPO}"
    deploy_url = ""
    qa_status  = "FAIL"

    try:
        # Stage 2 — Build
        log.info("[%s] Stage 2: Building web app…", issue_key)
        out_dir = build_agent.build(issue_key, requirements)

        # Stage 3 — Tests
        log.info("[%s] Stage 3: Running test feedback loop…", issue_key)
        test_runner.run(issue_key, out_dir)

        # Stage 4 — GitHub
        log.info("[%s] Stage 4: Pushing to GitHub…", issue_key)
        gh_result = github_pusher.push(issue_key, summary, out_dir)
        branch    = gh_result["branch"]
        pr_url    = gh_result["pr_url"]

        # Stage 5 — Vercel
        log.info("[%s] Stage 5: Deploying to Vercel…", issue_key)
        v_result   = vercel_deployer.deploy(issue_key, branch)
        deploy_url = v_result["deployment_url"]

        # Stage 6 — QA
        log.info("[%s] Stage 6: Running Playwright QA…", issue_key)
        qa_status = qa_agent.run(issue_key, deploy_url, out_dir)

        # Stage 7 — Email
        log.info("[%s] Stage 7: Sending QA email…", issue_key)
        email_reporter.send(issue_key, qa_status, out_dir)

    except PipelineError as e:
        log.error("[%s] Pipeline error: %s", issue_key, e)
        _emergency_close(issue_key, str(e), out_dir)
        return

    except Exception as e:
        tb = traceback.format_exc()
        log.error("[%s] Unexpected error: %s\n%s", issue_key, e, tb)
        _emergency_close(issue_key, f"Unexpected error: {e}\n\n{tb}", out_dir)
        return

    # Stage 8 — Close Jira
    log.info("[%s] Stage 8: Closing Jira loop…", issue_key)
    try:
        jira_closer.close(issue_key, qa_status, deploy_url, pr_url, out_dir)
    except Exception as e:
        log.error("[%s] Jira close failed: %s", issue_key, e)

    elapsed = time.time() - start
    log.info("[%s] ═══ Pipeline complete in %.0fs — %s ═══", issue_key, elapsed, qa_status)


def _emergency_close(issue_key: str, error_msg: str, out_dir: str | None) -> None:
    """Always transition the story out of In Progress, even on hard failure."""
    log.warning("[%s] Emergency close — transitioning to Bug Reported", issue_key)
    try:
        from stages.jira_poller import _jira, _comment
        data = _jira("GET", f"/issue/{issue_key}/transitions").json()
        transitions = data["transitions"]
        bug_id = next(
            (t["id"] for t in transitions if "bug" in t["name"].lower() or "review" in t["name"].lower()),
            transitions[0]["id"] if transitions else None,
        )
        if bug_id:
            _jira("POST", f"/issue/{issue_key}/transitions", json={"transition": {"id": bug_id}})
        _comment(issue_key, f"🚨 Pipeline failed at an early stage.\n\nError:\n{error_msg[:2000]}")
    except Exception as e:
        log.error("[%s] Emergency close also failed: %s", issue_key, e)


# ── Poll cycle ────────────────────────────────────────────────────────────────

def poll_and_run() -> None:
    log.info("Polling Jira for new stories…")
    try:
        stories = jira_poller.poll()
    except PipelineError as e:
        log.error("Jira poll failed: %s", e)
        return

    if not stories:
        log.info("No new stories found.")
        return

    log.info("Processing %d story(ies)…", len(stories))

    if len(stories) == 1:
        run_story(stories[0])
    else:
        # Principle 6 — run multiple stories in parallel
        with ThreadPoolExecutor(max_workers=min(len(stories), 3)) as executor:
            futures = {executor.submit(run_story, s): s["issue_key"] for s in stories}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    future.result()
                except Exception as e:
                    log.error("[%s] Unhandled future error: %s", key, e)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Zero Human Touch Pipeline")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--once",     action="store_true", help="Run a single poll cycle and exit")
    group.add_argument("--schedule", action="store_true", help="Run on a 5-minute schedule forever")
    args = parser.parse_args()

    if args.once:
        poll_and_run()
    else:
        log.info("Scheduler started — polling every 5 minutes")
        schedule.every(5).minutes.do(poll_and_run)
        poll_and_run()  # run immediately on startup
        while True:
            schedule.run_pending()
            time.sleep(30)


if __name__ == "__main__":
    main()
