"""
Diff/scope-notes layer: compares today's normalized snapshot against
yesterday's to auto-generate the "what changed since last refresh"
prose bullets, instead of writing them by hand every day.

Snapshots are stored as plain JSON in data/snapshots/, one file per day
(YYYY-MM-DD.json), containing exactly what rules.process_all() returns.
"""

import json
import os
from datetime import date, timedelta
from pathlib import Path


def snapshot_path(snapshot_dir: str, day: date) -> Path:
    return Path(snapshot_dir) / f"{day.isoformat()}.json"


def load_snapshot(snapshot_dir: str, day: date) -> dict | None:
    path = snapshot_path(snapshot_dir, day)
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def load_previous_snapshot(snapshot_dir: str, today: date | None = None) -> dict | None:
    """Loads the most recent snapshot to diff against. Checks today's own
    file first -- if main.py already ran once today (a same-day rerun
    after fixing a source, or the manual "run it twice" check in the
    README), diff against that rather than reporting "first run" every
    time. Otherwise walks back up to 7 days to find yesterday's (or the
    most recent prior) snapshot -- better a slightly-stale diff than
    none at all."""
    today = today or date.today()
    for days_back in range(0, 8):
        snap = load_snapshot(snapshot_dir, today - timedelta(days=days_back))
        if snap is not None:
            return snap
    return None


def save_snapshot(snapshot_dir: str, day: date, processed: dict) -> None:
    Path(snapshot_dir).mkdir(parents=True, exist_ok=True)
    with open(snapshot_path(snapshot_dir, day), "w") as f:
        json.dump(processed, f, indent=2, default=str)


def _task_key(task: dict) -> str:
    return task.get("source_url") or f"{task.get('source')}::{task.get('name')}"


def generate_scope_notes(today_processed: dict, previous_processed: dict | None) -> list[str]:
    """Returns a list of prose bullet strings summarizing what changed.
    This is intentionally simple string-diffing over task keys/fields --
    it's meant to draft the scope notes, not replace human judgment. Edit
    the output before publishing if something needs more context (e.g.
    *why* a task dropped out, which a raw diff can't know)."""
    notes: list[str] = []

    if previous_processed is None:
        notes.append("First run -- no prior snapshot to diff against yet.")
        return notes

    # HubSpot tasks are excluded here -- that section already only shows
    # items new since the last refresh (rules.filter_hubspot_new_only), so
    # every HubSpot item is *expected* to disappear on the following
    # refresh. Diffing it too would relabel that by-design behavior as a
    # bogus "dropped out, check manually" note every single day.
    today_by_key = {
        _task_key(t): t
        for team in today_processed["teams"].values()
        for t in team
        if not t.get("is_empty_state") and t.get("source") != "hubspot"
    }
    prev_by_key = {
        _task_key(t): t
        for team in previous_processed["teams"].values()
        for t in team
        if not t.get("is_empty_state") and t.get("source") != "hubspot"
    }

    new_keys = set(today_by_key) - set(prev_by_key)
    dropped_keys = set(prev_by_key) - set(today_by_key)
    common_keys = set(today_by_key) & set(prev_by_key)

    for key in sorted(new_keys):
        t = today_by_key[key]
        notes.append(f"New: \"{t['name']}\" ({t.get('owner') or 'unassigned'}) now shows in the window.")

    for key in sorted(dropped_keys):
        t = prev_by_key[key]
        notes.append(
            f"Dropped out: \"{t['name']}\" ({t.get('owner') or 'unassigned'}) no longer meets the "
            f"7-day/active-work bar -- check manually if it should still be visible."
        )

    for key in sorted(common_keys):
        before, after = prev_by_key[key], today_by_key[key]
        if before.get("status") != after.get("status"):
            notes.append(
                f"Status change: \"{after['name']}\" moved from {before.get('status')} to {after.get('status')}."
            )
        if before.get("due_date") != after.get("due_date"):
            notes.append(
                f"Due date change: \"{after['name']}\" moved from {before.get('due_date') or 'no date'} "
                f"to {after.get('due_date') or 'no date'}."
            )

    if not notes:
        notes.append("No material changes since the last refresh.")

    return notes
