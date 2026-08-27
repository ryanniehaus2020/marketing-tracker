"""
Website Roadmap source (Google Doc, not a task tracker) -- later milestone.

Feeds: the Growth team's website work-in-progress list, credited to
Dafne Delgado per the source doc.

Unlike every other source, this isn't a table or a ticket system -- it's
a hand-written Google Doc ("Website Fixes & Improvements - Roadmap",
Summary tab) with items grouped under headings like "July list:",
"August list:", etc., plus a catch-all "Parking Lot" section with no
target month. There's no owner/status/due-date column to read, so those
three fields are derived rather than read directly, per the source doc:

  - due_date: the last day of the item's month heading (e.g. everything
    under "August list:" gets due_date = Aug 31 of that doc's year).
    Parking Lot items have no month, so they get due_date = None
    (consistent with how other sources leave a field unset rather than
    inventing a value -- see the AI Roadmap sheet's due-date gap).
  - owner: always "Dafne Delgado" -- the doc has no per-item owner field.
  - status: "In Progress" if the item's month is the current month,
    "Planned" if it's a future month, "Backlog" for Parking Lot items.
    Past months are marked "Done" -- an assumption, since the doc doesn't
    actually track completion; flag it if that turns out to be wrong.

Parsing works against the doc's markdown export (Drive's
`files.export` with mimeType `text/markdown`), which is what turns
Google Docs' bullet/heading formatting into predictable `#`/`-` markup.
This is brittle in the same way confluence_source.py's table parser is
-- it breaks if someone reformats the doc's headings -- but it's what
matches the doc's actual structure today.

Docs: https://developers.google.com/drive/api/guides/manage-downloads#export_a_google_workspace_document
"""

import calendar
import os
import re
from datetime import date

from .base import NormalizedTask, require_env

# The doc has no per-item owner field -- every item is credited to Dafne
# Delgado per the source doc, same hardcoded-owner pattern hubspot_source.py
# uses for its published-pages/emails credit.
OWNER = "Dafne Delgado"

MONTH_HEADER_RE = re.compile(r"^#+\s*(?:→\s*)?([A-Za-z]+)\s+list:?\s*$", re.IGNORECASE)
YEAR_RE = re.compile(r"(\d{4})")
SUB_HEADING_RE = re.compile(r"^[—-]{1,3}\s.*\s[—-]{1,3}$")  # e.g. "— Google Ads —"
SKIP_LINES = {"<!-- end list -->", "summary"}
PARKING_LOT_HEADING = "parking lot"

MONTH_NUMBERS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}


def _status_for_month(month_num: int, year: int, today: date) -> str:
    this = (today.year, today.month)
    target = (year, month_num)
    if target == this:
        return "In Progress"
    if target > this:
        return "Planned"
    return "Done"  # assumption -- the doc doesn't mark completion explicitly


def _parse_roadmap_doc(text: str, doc_url: str, today: date | None = None) -> list[dict]:
    today = today or date.today()
    lines = [ln.strip() for ln in text.splitlines()]

    year = today.year
    for ln in lines[:5]:
        match = YEAR_RE.search(ln)
        if match:
            year = int(match.group(1))
            break

    tasks: list[dict] = []
    current_month: int | None = None
    in_parking_lot = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.lower() in SKIP_LINES:
            continue
        if line.lower() == PARKING_LOT_HEADING:
            current_month = None
            in_parking_lot = True
            continue

        month_match = MONTH_HEADER_RE.match(line)
        if month_match:
            month_name = month_match.group(1).lower()
            if month_name in MONTH_NUMBERS:
                current_month = MONTH_NUMBERS[month_name]
                in_parking_lot = False
            continue

        if line.startswith("#"):
            continue  # doc title or other heading -- not a task
        if SUB_HEADING_RE.match(line):
            continue  # sub-category label like "— Google Ads —", not a task

        name = line[2:].strip() if line.startswith("- ") else line
        if not name:
            continue

        if in_parking_lot:
            tasks.append(
                NormalizedTask(
                    name=name,
                    status="Backlog",
                    source="website_roadmap",
                    all_project_tags=["Website Roadmap"],
                    owner=OWNER,
                    due_date=None,
                    source_url=doc_url,
                ).to_dict()
            )
            continue

        if current_month is None:
            continue  # text before the first month heading (doc title/summary line)

        last_day = calendar.monthrange(year, current_month)[1]
        tasks.append(
            NormalizedTask(
                name=name,
                status=_status_for_month(current_month, year, today),
                source="website_roadmap",
                all_project_tags=["Website Roadmap"],
                owner=OWNER,
                due_date=date(year, current_month, last_day).isoformat(),
                source_url=doc_url,
            ).to_dict()
        )

    return tasks


def fetch(mock: bool = False) -> list[dict]:
    if mock:
        return _mock_tasks()

    require_env(os.environ, "GOOGLE_SERVICE_ACCOUNT_JSON_PATH", "WEBSITE_ROADMAP_DOC_ID")
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "Reading the Website Roadmap doc requires google-api-python-client "
            "and google-auth. Run: pip install google-api-python-client google-auth"
        ) from exc

    doc_id = os.environ["WEBSITE_ROADMAP_DOC_ID"]
    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_SERVICE_ACCOUNT_JSON_PATH"],
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    drive = build("drive", "v3", credentials=creds)
    raw = drive.files().export(fileId=doc_id, mimeType="text/markdown").execute()
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    return _parse_roadmap_doc(text, doc_url=doc_url)


def _mock_tasks() -> list[dict]:
    """Fixture shaped like the real doc's structure: one item in the
    current month (In Progress), one in a future month (Planned), one in
    a past month (Done), and one Parking Lot item (Backlog, no due date)."""
    today = date.today()
    this_month_last_day = calendar.monthrange(today.year, today.month)[1]
    next_month = today.month % 12 + 1
    next_month_year = today.year + (1 if next_month == 1 else 0)
    next_month_last_day = calendar.monthrange(next_month_year, next_month)[1]
    prev_month = today.month - 1 or 12
    prev_month_year = today.year - (1 if prev_month == 12 else 0)
    prev_month_last_day = calendar.monthrange(prev_month_year, prev_month)[1]

    return [
        NormalizedTask(
            name="Strengthen internal linking",
            status="In Progress",
            source="website_roadmap",
            all_project_tags=["Website Roadmap"],
            owner=OWNER,
            due_date=date(today.year, today.month, this_month_last_day).isoformat(),
            source_url="https://docs.google.com/document/d/mock/edit",
        ).to_dict(),
        NormalizedTask(
            name="Create new upskilling & reskilling page",
            status="Planned",
            source="website_roadmap",
            all_project_tags=["Website Roadmap"],
            owner=OWNER,
            due_date=date(next_month_year, next_month, next_month_last_day).isoformat(),
            source_url="https://docs.google.com/document/d/mock/edit",
        ).to_dict(),
        NormalizedTask(
            name="Update all 7 WPML plugins",
            status="Done",
            source="website_roadmap",
            all_project_tags=["Website Roadmap"],
            owner=OWNER,
            due_date=date(prev_month_year, prev_month, prev_month_last_day).isoformat(),
            source_url="https://docs.google.com/document/d/mock/edit",
        ).to_dict(),
        NormalizedTask(
            name="Think about how to improve the CTA banners on the articles",
            status="Backlog",
            source="website_roadmap",
            all_project_tags=["Website Roadmap"],
            owner=OWNER,
            due_date=None,
            source_url="https://docs.google.com/document/d/mock/edit",
        ).to_dict(),
    ]
