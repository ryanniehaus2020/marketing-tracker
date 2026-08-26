"""
Jira source (PMM board) -- later milestone.

Feeds: Product Marketing team tasks (Dana Pellegrini, Laura Etchalus de
Macedo). Uses Jira Cloud REST API v3 with a JQL query scoped to the PMM
project.

Docs: https://developer.atlassian.com/cloud/jira/platform/rest/v3/

Setup:
  1. Create an API token at https://id.atlassian.com/manage-profile/security/api-tokens
  2. JIRA_EMAIL + JIRA_API_TOKEN go in .env (basic auth pair)
  3. JIRA_PMM_BOARD_PROJECT_KEY should already be correct (PMM) unless the
     project key changes.

Known data-quality gap to carry forward (do not silently fix): several
Jira PMM issues for Dana/Laura lack near-term due dates (30+ each) -- the
source doc says these should be summarized as a count rather than listed
individually. rules.py handles that bucketing; this module just needs to
return everything normalized.
"""

import os
from base64 import b64encode

import requests

from .base import NormalizedTask, require_env

FIELDS = "summary,status,assignee,duedate"


def _auth_header(email: str, token: str) -> dict:
    raw = f"{email}:{token}".encode()
    return {"Authorization": f"Basic {b64encode(raw).decode()}"}


def fetch(mock: bool = False) -> list[dict]:
    if mock:
        return _mock_tasks()

    require_env(os.environ, "JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PMM_BOARD_PROJECT_KEY")
    base_url = os.environ["JIRA_BASE_URL"]
    project_key = os.environ["JIRA_PMM_BOARD_PROJECT_KEY"]

    jql = f'project = "{project_key}" AND statusCategory != Done ORDER BY duedate ASC'
    resp = requests.get(
        f"{base_url}/rest/api/3/search",
        headers=_auth_header(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"]),
        params={"jql": jql, "fields": FIELDS, "maxResults": 100},
        timeout=30,
    )
    resp.raise_for_status()
    issues = resp.json().get("issues", [])

    tasks = []
    for issue in issues:
        f = issue["fields"]
        tasks.append(
            NormalizedTask(
                name=f["summary"],
                status=(f.get("status") or {}).get("name", "Unknown"),
                source="jira",
                all_project_tags=[project_key],
                owner=(f.get("assignee") or {}).get("displayName"),
                due_date=f.get("duedate"),
                source_url=f"{base_url}/browse/{issue['key']}",
            ).to_dict()
        )
    return tasks


def _mock_tasks() -> list[dict]:
    return [
        NormalizedTask(
            name="Competitive positioning doc for AI SKU",
            status="In Review",
            source="jira",
            all_project_tags=["PMM"],
            owner="Dana Pellegrini",
            due_date=None,
            source_url="https://degreed.atlassian.net/browse/PMM-101",
        ).to_dict(),
        NormalizedTask(
            name="Sales enablement deck refresh",
            status="Backlog",
            source="jira",
            all_project_tags=["PMM"],
            owner="Laura Etchalus de Macedo",
            due_date=None,
            source_url="https://degreed.atlassian.net/browse/PMM-102",
        ).to_dict(),
    ]
