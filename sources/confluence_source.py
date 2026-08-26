"""
Confluence source (MAR space) -- later milestone.

Feeds: Marketing Operations Roadmap (Ryan Niehaus's Operations tasks).

Unlike the other sources, this isn't a task-tracker API -- it's a wiki
page. The Marketing Ops Roadmap page presumably has its tasks in a table
or a Confluence "task list" macro. Two viable approaches:

  A) If the roadmap uses Confluence's native task macro, use the
     `/wiki/rest/api/content/{id}/task` list (Confluence tasks API) --
     cleanest, but only works if tasks are literally created as
     Confluence tasks (checkboxes), not a hand-written table.
  B) If the roadmap is a plain table on the page, fetch the page body
     (storage format / HTML) and parse the table with an HTML parser
     (e.g. BeautifulSoup). More brittle -- breaks if someone reformats
     the table -- but works with what's there today.

This scaffold implements (B) since that's the more common real-world
case for a hand-maintained roadmap page. Swap in (A) if you confirm the
page actually uses task macros.

Docs: https://developer.atlassian.com/cloud/confluence/rest/v2/
"""

import os
from base64 import b64encode

import requests

from .base import NormalizedTask, require_env


def _auth_header(email: str, token: str) -> dict:
    raw = f"{email}:{token}".encode()
    return {"Authorization": f"Basic {b64encode(raw).decode()}"}


def fetch(mock: bool = False) -> list[dict]:
    if mock:
        return _mock_tasks()

    require_env(
        os.environ,
        "CONFLUENCE_BASE_URL",
        "CONFLUENCE_EMAIL",
        "CONFLUENCE_API_TOKEN",
        "CONFLUENCE_OPS_ROADMAP_PAGE_ID",
    )
    base_url = os.environ["CONFLUENCE_BASE_URL"]
    page_id = os.environ["CONFLUENCE_OPS_ROADMAP_PAGE_ID"]

    resp = requests.get(
        f"{base_url}/rest/api/content/{page_id}",
        headers=_auth_header(os.environ["CONFLUENCE_EMAIL"], os.environ["CONFLUENCE_API_TOKEN"]),
        params={"expand": "body.storage"},
        timeout=30,
    )
    resp.raise_for_status()
    html = resp.json()["body"]["storage"]["value"]

    return _parse_roadmap_table(html, page_url=f"{base_url}/pages/viewpage.action?pageId={page_id}")


def _parse_roadmap_table(html: str, page_url: str) -> list[dict]:
    """Parse a plain HTML table with columns: Task | Status | Due Date.
    Adjust column order/names once you've looked at the real page."""
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError(
            "Parsing the Confluence roadmap table requires beautifulsoup4. "
            "Run: pip install beautifulsoup4"
        ) from exc

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        return []

    tasks = []
    rows = table.find_all("tr")[1:]  # skip header row
    for row in rows:
        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        name = cells[0]
        status = cells[1] if len(cells) > 1 else "Unknown"
        due_date = cells[2] if len(cells) > 2 and cells[2] else None
        tasks.append(
            NormalizedTask(
                name=name,
                status=status,
                source="confluence",
                all_project_tags=["Marketing Operations Roadmap"],
                owner="Ryan Niehaus",
                due_date=due_date,
                source_url=page_url,
            ).to_dict()
        )
    return tasks


def _mock_tasks() -> list[dict]:
    return [
        NormalizedTask(
            name="Audit HubSpot workflow duplicates",
            status="In Progress",
            source="confluence",
            all_project_tags=["Marketing Operations Roadmap"],
            owner="Ryan Niehaus",
            due_date=None,
            source_url="https://degreed.atlassian.net/wiki/mock",
        ).to_dict(),
    ]
