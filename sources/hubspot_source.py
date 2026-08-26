"""
HubSpot source -- later milestone.

Feeds: published landing pages (credited to Dafne, Growth) and published
marketing emails (credited to Luke, Growth).

Important behavior difference from the other sources: this section only
ever shows items that are NEW since the last refresh ("no news isn't
shown as news" -- see source doc section 7). This module itself just
returns everything published recently; the "is it actually new" filter
happens in rules.filter_hubspot_new_only(), which compares against
yesterday's snapshot by source_url. Keep that separation -- don't bake
the "since last refresh" logic in here, or diff.py loses visibility into
what would have shown.

Docs: https://developers.hubspot.com/docs/api/cms/pages
      https://developers.hubspot.com/docs/api/marketing/marketing-email
"""

import os
from datetime import date, timedelta

import requests

from .base import NormalizedTask, require_env

HUBSPOT_API_BASE = "https://api.hubapi.com"

# credited owner per the source doc -- HubSpot's own "published by" field
# is not reliably a real person, so these are hardcoded per the doc.
LANDING_PAGE_OWNER = "Dafne Delgado"
MARKETING_EMAIL_OWNER = "Luke Derderian"

LOOKBACK_DAYS = 3  # how far back to check for "recently published" candidates


def fetch(mock: bool = False) -> list[dict]:
    if mock:
        return _mock_tasks()

    require_env(os.environ, "HUBSPOT_PRIVATE_APP_TOKEN")
    token = os.environ["HUBSPOT_PRIVATE_APP_TOKEN"]
    headers = {"Authorization": f"Bearer {token}"}
    since = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()

    tasks = []

    pages_resp = requests.get(
        f"{HUBSPOT_API_BASE}/cms/v3/pages/site-pages",
        headers=headers,
        params={"publishDate__gte": since, "state": "PUBLISHED"},
        timeout=30,
    )
    pages_resp.raise_for_status()
    for page in pages_resp.json().get("results", []):
        tasks.append(
            NormalizedTask(
                name=f"Published: {page.get('name')}",
                status="Live",
                source="hubspot",
                all_project_tags=["Published landing pages"],
                owner=LANDING_PAGE_OWNER,
                due_date=(page.get("publishDate") or "")[:10] or None,
                source_url=page.get("url"),
            ).to_dict()
        )

    emails_resp = requests.get(
        f"{HUBSPOT_API_BASE}/marketing/v3/emails",
        headers=headers,
        params={"state": "PUBLISHED"},
        timeout=30,
    )
    emails_resp.raise_for_status()
    for email in emails_resp.json().get("results", []):
        tasks.append(
            NormalizedTask(
                name=f"Published: {email.get('name')}",
                status="Live",
                source="hubspot",
                all_project_tags=["Published marketing emails"],
                owner=MARKETING_EMAIL_OWNER,
                due_date=(email.get("updatedAt") or "")[:10] or None,
                source_url=None,
            ).to_dict()
        )

    return tasks


def _mock_tasks() -> list[dict]:
    today = date.today().isoformat()
    return [
        NormalizedTask(
            name="Published: Degreed.ai Product Launch landing page",
            status="Live",
            source="hubspot",
            all_project_tags=["Published landing pages"],
            owner=LANDING_PAGE_OWNER,
            due_date=today,
            source_url="https://degreed.com/mock-landing-page",
        ).to_dict(),
    ]
