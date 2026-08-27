#!/usr/bin/env python3
"""
Orchestrates the full daily pipeline: pull -> filter -> diff -> render -> write.

Usage:
    python main.py                 # real API calls, uses .env
    python main.py --mock          # fixture data, no credentials needed
    python main.py --sources asana # limit to specific source(s), e.g. during Milestone 1
"""

import argparse
import os
from datetime import date

import yaml
from dotenv import load_dotenv

import diff
import rules
from render import render
from config.roster import TEAMS
from sources import (
    asana_source,
    jira_source,
    confluence_source,
    hubspot_source,
    sheets_source,
    website_roadmap_source,
)

SOURCE_MODULES = {
    "asana": asana_source,
    "jira": jira_source,
    "confluence": confluence_source,
    "hubspot": hubspot_source,
    "sheets": sheets_source,
    "website_roadmap": website_roadmap_source,
}


def load_initiatives(path: str = "config/initiatives.yaml") -> list[dict]:
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("initiatives", [])


def pull_all(mock: bool, only_sources: list[str] | None) -> list[dict]:
    tasks = []
    for name, module in SOURCE_MODULES.items():
        if only_sources and name not in only_sources:
            continue
        try:
            fetched = module.fetch(mock=mock)
            tasks.extend(fetched)
            print(f"[{name}] fetched {len(fetched)} task(s)")
        except RuntimeError as exc:
            # Missing credentials for a source not yet wired up -- skip it
            # rather than crashing the whole run. Milestone 1 only needs
            # Asana working; the rest will raise this until configured.
            print(f"[{name}] skipped: {exc}")
    return tasks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="Use fixture data instead of real API calls")
    parser.add_argument("--sources", nargs="*", help="Limit to specific sources, e.g. --sources asana")
    args = parser.parse_args()

    load_dotenv()

    snapshot_dir = os.environ.get("SNAPSHOT_DIR", "./data/snapshots")
    output_path = os.environ.get("OUTPUT_HTML_PATH", "./output/tracker.html")
    today = date.today()

    previous_snapshot = diff.load_previous_snapshot(snapshot_dir, today)

    raw_tasks = pull_all(mock=args.mock, only_sources=args.sources)
    processed = rules.process_all(raw_tasks, previous_snapshot=previous_snapshot)

    scope_notes = diff.generate_scope_notes(processed, previous_snapshot)
    diff.save_snapshot(snapshot_dir, today, processed)

    initiatives = load_initiatives()
    team_order = list(TEAMS.keys())
    team_open_by_default = {name: cfg.get("default_open", False) for name, cfg in TEAMS.items()}
    # rules.process_all() may add an "Unassigned / needs review" bucket for
    # tasks whose owner isn't on the roster -- append it if present so it
    # still renders, rather than silently dropping those tasks from view.
    for extra_team in processed["teams"]:
        if extra_team not in team_order:
            team_order.append(extra_team)
            team_open_by_default[extra_team] = True

    html = render(
        processed=processed,
        initiatives=initiatives,
        scope_notes=scope_notes,
        team_order=team_order,
        team_open_by_default=team_open_by_default,
    )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    print(f"\nWrote {output_path}")
    print(f"Snapshot saved to {snapshot_dir}/{today.isoformat()}.json")


if __name__ == "__main__":
    main()
