"""
Asana source -- Milestone 1 target.

Feeds: Growth team tasks (Web Marketing Requests, Lisa Harding's
personal to-do board, Email & Automation Management), plus Content &
Brand and Events boards once you extend PROJECT_GIDS below. "Website
Roadmap" is NOT here -- see the note below.

Real API docs: https://developers.asana.com/reference/rest-api-reference

Setup:
  1. Create a Personal Access Token in Asana (My Profile Settings > Apps
     > Manage Developer Apps) and put it in ASANA_ACCESS_TOKEN.
  2. Find your workspace gid: GET /workspaces, put it in ASANA_WORKSPACE_GID.
  3. Fill in PROJECT_GIDS below with the real gids for each board (find
     them in the Asana URL when viewing a project, or via GET /projects).
"""

import os
from datetime import date

import requests

from .base import NormalizedTask, require_env

ASANA_API_BASE = "https://app.asana.com/api/1.0"

# Map a human-readable board name -> its Asana project gid.
# Resolved 2026-08-27 against the real Degreed Asana workspace (gid
# 1199943304774115) by name search, confirmed against the team 2026-08-27.
#
# NOTE: "Website Roadmap" was never an Asana board -- it's a Google Doc
# ("Website Fixes & Improvements - Roadmap", id
# 16MTqGAve79Ij4CIBuEHjKZVu2kuHUfk1rfT-YMPvlCU, Summary tab), an
# unstructured bulleted list grouped by month with no owner/status/
# due-date fields. It's intentionally NOT in this dict -- see
# sources/website_roadmap_source.py, which derives those three fields
# instead of reading them.
PROJECT_GIDS = {
    "Web Marketing Requests": "1202966122105252",
    "Lisa To Do's": "1217792928253659",  # Lisa Harding's personal to-do board (was guessed as "Lisa — This Week")
    "Email & Automation Management": "1200025860801880",
    "Content Calendar": "1203158713461129",  # Content & Brand
    "All Creative Projects": "1200519962061957",  # Content & Brand
    "Event Projects": "1201483003070040",  # Events -- other similarly-named boards exist: "Events & Communications Projects" (1200160052714843), "Event Projects (2020 + 2021)" (1200155527155377), "Event Projects (2019 + 2018)" (1200161586211355)
}

TASK_FIELDS = "name,completed,due_on,assignee.name,memberships.project.name,permalink_url"


def _fetch_project_tasks(project_gid: str, project_name: str, token: str) -> list[dict]:
    resp = requests.get(
        f"{ASANA_API_BASE}/projects/{project_gid}/tasks",
        headers={"Authorization": f"Bearer {token}"},
        params={"opt_fields": TASK_FIELDS, "completed_since": "now"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def _status_from_task(raw_task: dict) -> str:
    """Asana has no built-in 'status' field the way Jira does -- teams
    usually track it via a custom field or a section name. Adjust this to
    read whatever your team actually uses (a custom field gid, or the
    section the task sits in) once you have real data to look at."""
    if raw_task.get("completed"):
        return "Done"
    # Placeholder default -- replace with a real custom-field / section lookup.
    return "Queue"


def fetch(mock: bool = False) -> list[dict]:
    if mock:
        return _mock_tasks()

    require_env(os.environ, "ASANA_ACCESS_TOKEN", "ASANA_WORKSPACE_GID")
    token = os.environ["ASANA_ACCESS_TOKEN"]

    tasks: list[NormalizedTask] = []
    for project_name, project_gid in PROJECT_GIDS.items():
        if not project_gid:
            continue  # not wired up yet -- skip rather than error
        for raw in _fetch_project_tasks(project_gid, project_name, token):
            memberships = raw.get("memberships") or []
            all_tags = [m["project"]["name"] for m in memberships if m.get("project")]
            tasks.append(
                NormalizedTask(
                    name=raw["name"],
                    status=_status_from_task(raw),
                    source="asana",
                    project_tag=None,  # resolved by rules.py's dedup step
                    all_project_tags=all_tags or [project_name],
                    owner=(raw.get("assignee") or {}).get("name"),
                    due_date=raw.get("due_on"),
                    source_url=raw.get("permalink_url"),
                )
            )
    return [t.to_dict() for t in tasks]


def _mock_tasks() -> list[dict]:
    """Fixture data for `--mock` runs, shaped to match the reference
    tracker's Growth team table so you can sanity-check rules.py/render.py
    before touching real credentials."""
    today = date.today()
    return [
        NormalizedTask(
            name="Finalize Q4 paid social calendar",
            status="In Progress",
            source="asana",
            all_project_tags=["Web Marketing Requests"],
            owner="Ryan Niehaus",  # literal Asana assignee -- RACI override applies
            due_date=str(today.replace(day=min(today.day + 3, 28))),
            source_url="https://app.asana.com/0/mock/1",
        ).to_dict(),
        NormalizedTask(
            name="Localization needed for a success story",
            status="Blocked",
            source="asana",
            all_project_tags=["Content Calendar"],
            owner="Camila Santos",
            due_date=None,  # missing-data case
            source_url="https://app.asana.com/0/mock/2",
        ).to_dict(),
        NormalizedTask(
            name="Refresh homepage hero for Degreed.ai launch",
            status="This Week",
            source="asana",
            all_project_tags=["Website Roadmap", "Web Marketing Requests"],
            owner="Dafne Delgado",
            due_date=str(today.replace(day=min(today.day + 20, 28))),  # far out but active
            source_url="https://app.asana.com/0/mock/3",
        ).to_dict(),
        NormalizedTask(
            name="Draft nurture email #3",
            status="Queue",
            source="asana",
            all_project_tags=["Email & Automation Management"],
            owner="Luke Derderian",
            due_date=str(today.replace(day=min(today.day + 40, 28))),  # out of window, not active
            source_url="https://app.asana.com/0/mock/4",
        ).to_dict(),
        # Tilda Persson intentionally has zero mock tasks to exercise the
        # empty-state row logic.
    ]
