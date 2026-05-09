import logging
import os

import requests

from stages.jira_poller import _jira, _get_transition_id, _comment
from exceptions import PipelineError

log = logging.getLogger("pipeline")

_DONE_NAMES    = ["done", "closed", "complete", "resolved"]
_BUG_NAMES     = ["bug reported", "in review", "needs review", "reopened", "blocked"]


def close(issue_key: str, qa_status: str, deployment_url: str, pr_url: str, out_dir: str) -> None:
    if qa_status == "PASS":
        _close_as_done(issue_key, deployment_url, pr_url)
    else:
        _close_as_bug(issue_key, qa_status, deployment_url, pr_url, out_dir)

    _verify_not_in_progress(issue_key)


def _close_as_done(issue_key: str, deployment_url: str, pr_url: str) -> None:
    tid = _find_transition(issue_key, _DONE_NAMES)
    _jira("POST", f"/issue/{issue_key}/transitions", json={"transition": {"id": tid}})
    log.info("[%s] Transitioned to Done", issue_key)

    _comment(
        issue_key,
        f"✅ Pipeline complete — all QA tests passed.\n\n"
        f"Deployment URL: {deployment_url}\n"
        f"GitHub PR: {pr_url}\n\n"
        f"_Automated by the Zero Human Touch Pipeline_",
    )


def _close_as_bug(
    issue_key: str, qa_status: str, deployment_url: str, pr_url: str, out_dir: str
) -> None:
    tid = _find_transition(issue_key, _BUG_NAMES, fallback=_DONE_NAMES)
    _jira("POST", f"/issue/{issue_key}/transitions", json={"transition": {"id": tid}})
    log.info("[%s] Transitioned to Bug Reported/In Review", issue_key)

    report_path = os.path.join(out_dir, "bug-report.md")
    report_text = ""
    if os.path.exists(report_path):
        with open(report_path) as f:
            report_text = f.read()

    _comment(
        issue_key,
        f"❌ Pipeline complete — QA status: {qa_status}\n\n"
        f"Deployment URL: {deployment_url}\n"
        f"GitHub PR: {pr_url}\n\n"
        f"--- Bug Report ---\n\n{report_text[:3000]}\n\n"
        f"_Automated by the Zero Human Touch Pipeline_",
    )


def _find_transition(issue_key: str, preferred: list[str], fallback: list[str] | None = None) -> str:
    data = _jira("GET", f"/issue/{issue_key}/transitions").json()
    transitions = data["transitions"]

    for name in preferred:
        for t in transitions:
            if name in t["name"].lower():
                return t["id"]

    if fallback:
        for name in fallback:
            for t in transitions:
                if name in t["name"].lower():
                    return t["id"]

    available = [t["name"] for t in transitions]
    log.warning("[%s] No matching transition found. Available: %s — using first", issue_key, available)
    return transitions[0]["id"]


def _verify_not_in_progress(issue_key: str) -> None:
    data = _jira("GET", f"/issue/{issue_key}?fields=status").json()
    status_name = data["fields"]["status"]["name"]
    if "progress" in status_name.lower():
        log.error("[%s] Story still In Progress after close attempt!", issue_key)
        raise PipelineError(
            f"Story {issue_key} is still in '{status_name}' after close attempt",
            stage="jira-closer",
        )
    log.info("[%s] Final Jira status: %s", issue_key, status_name)
