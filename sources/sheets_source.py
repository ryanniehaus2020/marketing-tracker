"""
Google Sheets source (AI Roadmap FY27) -- later milestone.

Feeds: AI Roadmap FY27 items (Milla Nordwall) -- quarter-level only, no
real due dates yet. Per the known data-quality gap in the source doc,
these items should stay flagged "Missing" until the sheet gets a real
due-date column -- don't invent a fake date to make them look complete.

Setup:
  1. Create a Google Cloud service account, enable the Sheets API, and
     share the "AI Roadmap" sheet with the service account's email.
  2. Download the service account JSON key, set
     GOOGLE_SERVICE_ACCOUNT_JSON_PATH to its path.
  3. Set AI_ROADMAP_SHEET_ID (from the sheet's URL) and
     AI_ROADMAP_SHEET_RANGE (e.g. "Sheet1!A1:F200").

Expected sheet columns (adjust COLUMN_MAP if the real sheet differs):
  A: Item name
  B: Quarter (e.g. "Q3 FY27")
  C: Owner
  D: Status
"""

import os

from .base import NormalizedTask, require_env

COLUMN_MAP = {"name": 0, "quarter": 1, "owner": 2, "status": 3}


def fetch(mock: bool = False) -> list[dict]:
    if mock:
        return _mock_tasks()

    require_env(
        os.environ,
        "GOOGLE_SERVICE_ACCOUNT_JSON_PATH",
        "AI_ROADMAP_SHEET_ID",
        "AI_ROADMAP_SHEET_RANGE",
    )
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "Reading the AI Roadmap sheet requires google-api-python-client "
            "and google-auth. Run: pip install google-api-python-client google-auth"
        ) from exc

    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_SERVICE_ACCOUNT_JSON_PATH"],
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    service = build("sheets", "v4", credentials=creds)
    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=os.environ["AI_ROADMAP_SHEET_ID"],
            range=os.environ["AI_ROADMAP_SHEET_RANGE"],
        )
        .execute()
    )
    rows = result.get("values", [])[1:]  # skip header row

    tasks = []
    for row in rows:
        if not row or not row[0]:
            continue
        name = row[COLUMN_MAP["name"]] if len(row) > COLUMN_MAP["name"] else ""
        quarter = row[COLUMN_MAP["quarter"]] if len(row) > COLUMN_MAP["quarter"] else None
        owner = row[COLUMN_MAP["owner"]] if len(row) > COLUMN_MAP["owner"] else None
        status = row[COLUMN_MAP["status"]] if len(row) > COLUMN_MAP["status"] else "Backlog"
        tasks.append(
            NormalizedTask(
                name=f"{name} ({quarter})" if quarter else name,
                status=status,
                source="sheets",
                all_project_tags=["AI Roadmap FY27"],
                owner=owner,
                due_date=None,  # intentional -- no real due-date field exists yet
                source_url=None,
            ).to_dict()
        )
    return tasks


def _mock_tasks() -> list[dict]:
    return [
        NormalizedTask(
            name="AI coaching pilot scoping (Q4 FY27)",
            status="Backlog",
            source="sheets",
            all_project_tags=["AI Roadmap FY27"],
            owner="Milla Nordwall",
            due_date=None,
            source_url=None,
        ).to_dict(),
    ]
