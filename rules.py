"""
Business-rules layer: applies the 7-day/active-work visibility filter,
multi-board dedup, RACI owner overrides, sort order, and empty-state rows.

This is the layer most likely to need tweaking as you validate output
against the reference tracker -- keep it isolated from the source
modules (which should only ever normalize, never filter or judge).
"""

import os
from datetime import date, datetime, timedelta

from config.roster import (
    ACTIVE_WORK_STATUSES,
    DEDUP_PRIORITY,
    PERSON_TO_TEAM,
    TEAMS,
    VISIBILITY_WINDOW_DAYS,
    apply_raci_override,
)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def resolve_project_tag(all_project_tags: list[str]) -> str | None:
    """Pick ONE project tag per the fixed priority order in
    config.roster.DEDUP_PRIORITY. Falls back to the first tag if nothing
    in the priority list matches (better to show something than nothing)."""
    if not all_project_tags:
        return None

    for tier in DEDUP_PRIORITY:
        if "portfolio_env" in tier:
            portfolio_gid = os.environ.get(tier["portfolio_env"])
            # Portfolio membership isn't knowable from project *names* alone --
            # source modules should attach the portfolio's project name to
            # all_project_tags if a task is in that portfolio. This checks by
            # name for now; swap for a real gid-membership check once wired up.
            continue
        if "project_names" in tier:
            for tag in all_project_tags:
                if tag in tier["project_names"]:
                    return tag
        if "project_name_suffixes" in tier:
            for tag in all_project_tags:
                if any(tag.endswith(suffix) for suffix in tier["project_name_suffixes"]):
                    return tag
        if tier.get("personal_board_prefixes"):
            first_names = {person.split()[0] for person in PERSON_TO_TEAM}
            for tag in all_project_tags:
                if any(tag.startswith(f"{name} — ") or tag.startswith(f"{name} - ") for name in first_names):
                    return tag

    return all_project_tags[0]


def apply_owner_override(task: dict) -> dict:
    """Apply RACI owner correction in place (returns a new dict)."""
    corrected = dict(task)
    corrected["owner"] = apply_raci_override(
        source=task["source"],
        literal_assignee=task.get("owner") or "",
        project_tag=task.get("project_tag") or "",
    )
    return corrected


def is_missing_data(task: dict) -> tuple[bool, str | None]:
    """Returns (is_missing, context_note). A task is 'missing' if it has
    no owner or no due date -- separate from the 7-day distance filter."""
    reasons = []
    if not task.get("owner"):
        reasons.append("no owner")
    if not task.get("due_date"):
        reasons.append("no due date")
    if reasons:
        return True, " / ".join(reasons)
    return False, None


def in_visibility_window(task: dict, today: date | None = None) -> bool:
    """A task is shown if:
      - due date falls within today -> today+7, OR
      - status indicates active work (regardless of date distance), OR
      - it has no due date at all (missing-data flag, not a distance filter)
    Tasks that are far out AND not actively worked are omitted."""
    today = today or date.today()
    status = (task.get("status") or "").strip().lower()
    due = _parse_date(task.get("due_date"))

    if due is None:
        return True  # missing-data case -- shown, flagged separately
    if status in ACTIVE_WORK_STATUSES:
        return True
    return today <= due <= today + timedelta(days=VISIBILITY_WINDOW_DAYS)


def is_overdue(task: dict, today: date | None = None) -> bool:
    today = today or date.today()
    due = _parse_date(task.get("due_date"))
    return due is not None and due < today


def sort_key(task: dict):
    """Sort by due date ascending; no-due-date items grouped at the end."""
    due = _parse_date(task.get("due_date"))
    return (due is None, due or date.max)


def filter_hubspot_new_only(hubspot_tasks: list[dict], previous_snapshot: dict | None) -> list[dict]:
    """HubSpot section only shows items NEW since the last refresh --
    'no news isn't shown as news'. Compares by source_url (falls back to
    name if source_url is missing) against yesterday's snapshot."""
    if not previous_snapshot:
        return hubspot_tasks  # first run ever -- nothing to diff against

    previously_seen = {
        (t.get("source_url") or t.get("name"))
        for t in previous_snapshot.get("raw_tasks", [])
        if t.get("source") == "hubspot"
    }
    return [
        t for t in hubspot_tasks
        if (t.get("source_url") or t.get("name")) not in previously_seen
    ]


def process_all(raw_tasks: list[dict], previous_snapshot: dict | None = None) -> dict:
    """Full pipeline: resolve project tags -> apply RACI overrides ->
    filter to visibility window -> annotate overdue/missing -> group by
    team -> sort -> generate empty-state rows.

    Returns {"teams": {team_name: [task, ...]}, "raw_tasks": raw_tasks}
    -- raw_tasks is kept alongside so diff.py / next run's HubSpot filter
    have the full unfiltered set to compare against.
    """
    today = date.today()

    # Split HubSpot tasks out for the new-only filter before the rest of
    # the pipeline runs on them.
    hubspot_tasks = [t for t in raw_tasks if t["source"] == "hubspot"]
    other_tasks = [t for t in raw_tasks if t["source"] != "hubspot"]
    hubspot_tasks = filter_hubspot_new_only(hubspot_tasks, previous_snapshot)

    processed = []
    for task in other_tasks + hubspot_tasks:
        t = dict(task)
        t["project_tag"] = resolve_project_tag(t.get("all_project_tags") or [])
        t = apply_owner_override(t)

        if not in_visibility_window(t, today):
            continue

        missing, missing_note = is_missing_data(t)
        t["is_missing"] = missing
        t["missing_note"] = missing_note
        t["is_overdue"] = is_overdue(t, today)
        processed.append(t)

    processed.sort(key=sort_key)

    # Group by person first (empty-state rows are per-person per the source
    # doc -- "when a person has zero qualifying tasks, show one italic gray
    # row" -- not per-team), then flatten into per-team lists in roster order.
    tasks_by_person: dict[str, list[dict]] = {}
    unassigned_or_unrostered: list[dict] = []
    for task in processed:
        owner = task.get("owner")
        if owner and owner in PERSON_TO_TEAM:
            tasks_by_person.setdefault(owner, []).append(task)
        else:
            # No owner, or an owner not in the roster -- keep visible rather
            # than silently dropping; surfaced in scope notes / volume checks.
            unassigned_or_unrostered.append(task)

    teams: dict[str, list[dict]] = {name: [] for name in TEAMS}
    for team_name, cfg in TEAMS.items():
        if not cfg["members"]:
            teams[team_name] = [_empty_state_row(cfg.get("note") or "No tasks -- no team members on file.")]
            continue
        for person in cfg["members"]:
            person_tasks = tasks_by_person.get(person)
            if person_tasks:
                teams[team_name].extend(person_tasks)
            else:
                teams[team_name].append(
                    _empty_state_row(
                        cfg.get("note")
                        or f"{person}: no tasks due in this window and nothing currently active."
                    )
                )

    if unassigned_or_unrostered:
        teams.setdefault("Unassigned / needs review", [])
        teams["Unassigned / needs review"].extend(unassigned_or_unrostered)

    # Flat, single-table view across all teams (task view) -- same tasks as
    # `teams` above, minus the per-person empty-state filler rows (they
    # don't carry due dates/owners, so they don't belong in a sortable/
    # filterable table). Tagged with which team each task landed in so
    # "Team" can be a column/filter instead of a section header. Re-sort
    # after flattening since dict insertion order (team-by-team) would
    # otherwise clobber the due-date order within each team.
    task_table = [
        dict(task, team=team_name)
        for team_name, rows in teams.items()
        for task in rows
        if not task.get("is_empty_state")
    ]
    task_table.sort(key=sort_key)

    return {"teams": teams, "raw_tasks": raw_tasks, "task_table": task_table}


def _empty_state_row(text: str) -> dict:
    return {
        "name": text,
        "is_empty_state": True,
        "owner": None,
        "due_date": None,
        "status": None,
        "project_tag": None,
        "source": None,
        "source_url": None,
        "is_missing": False,
        "is_overdue": False,
    }
