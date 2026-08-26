# Marketing Team Tracker

A daily-refreshing dashboard of what's happening across the Degreed
marketing team in the next 7 days: outward-facing activity for the
team's 3 biggest initiatives, plus a team-by-team task table pulled from
Asana, Jira, Confluence, HubSpot, and a Google Sheet. Read-only -- it
reflects those tools, never edits them.

This repo is a working scaffold, not yet wired to real data. Verified
end-to-end in `--mock` mode; each real API integration is written but
untested against live credentials.

## Quick start (mock mode -- no credentials needed)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install beautifulsoup4   # only needed for the real Confluence source
python3 main.py --mock
open output/tracker.html     # or just open it in a browser
```

Run it twice in a row and check the "Scope notes" section at the bottom
-- the second run should say "No material changes," since mock data
doesn't change between runs. Edit a value in `sources/asana_source.py`'s
`_mock_tasks()` and re-run to see the diff layer pick it up.

## Wiring up real data

Copy `.env.example` to `.env` and fill in credentials one source at a
time, per the milestone plan below. Each `sources/*.py` module has setup
notes in its docstring. Run with `--sources asana` (etc.) to test one
source in isolation before enabling the rest.

```bash
cp .env.example .env
# fill in ASANA_ACCESS_TOKEN, ASANA_WORKSPACE_GID, and the project gids
# in sources/asana_source.py's PROJECT_GIDS dict
python3 main.py --sources asana
```

## Milestone plan

1. **Asana + Growth team.** Fill in `PROJECT_GIDS` in
   `sources/asana_source.py` with real board gids. Confirm the
   `_status_from_task()` placeholder logic matches how your team
   actually tracks status in Asana (custom field vs. section) --
   this needs a look at real data before it's right.
2. **Jira (PMM board).** Add Jira credentials, confirm the JQL in
   `jira_source.fetch()` matches the real PMM project key and that
   `statusCategory != Done` is the right "not finished" filter.
3. **Confluence (Ops roadmap).** Look at the actual Marketing
   Operations Roadmap page's HTML structure -- `confluence_source.py`
   assumes a plain table; if it uses Confluence's native task-list
   macro instead, swap to the Confluence tasks API (see the module's
   docstring for both options).
4. **HubSpot.** Confirm the CMS pages + marketing emails API scopes on
   your private app token, and sanity check the "new since last
   refresh" filter (`rules.filter_hubspot_new_only`) against a real
   two-day run.
5. **AI Roadmap Google Sheet.** Set up the service account, share the
   sheet with it, and confirm `COLUMN_MAP` in `sources/sheets_source.py`
   matches the real column order.
6. **Scheduling.** Once all 5 sources are live, put `python3 main.py`
   on a daily cron (or your CI scheduler of choice) and decide where
   the rendered `output/tracker.html` gets published -- committed to a
   repo + served via GitHub Pages, uploaded somewhere the team can
   reach, etc. (This scaffold writes a local file; publishing is a
   separate step you'll want to add once the data side is solid.)

## How the pieces fit together

- **`sources/*.py`** -- one module per external tool. Each exposes
  `fetch(mock=False) -> list[dict]` and returns tasks in the common
  normalized shape documented in `sources/base.py`. Source modules
  should only normalize, never filter or judge -- that's `rules.py`'s
  job.
- **`config/roster.py`** -- the file you'll edit most often by hand:
  team membership, RACI owner-override mapping, and the multi-board
  dedup priority order.
- **`config/initiatives.yaml`** -- hand-maintained initiative data
  (rarely changes). The three current initiatives (AI-Powered
  Revolution, Degreed.ai Product Launch, Vision 2026) are stubbed with
  a few sample activities each -- pull the full activity lists
  (Vision 2026 has ~35) from the original artifact's HTML when you
  migrate it over.
- **`rules.py`** -- the 7-day/active-work visibility filter, dedup
  resolution, RACI overrides, sort order, and per-person empty-state
  rows.
- **`diff.py`** -- stores one JSON snapshot per day in
  `data/snapshots/`, and diffs today's against the most recent prior
  one to auto-draft the "what changed" scope notes. Treat the
  generated notes as a draft, not a final -- a raw diff can't know
  *why* something changed, only *that* it did.
- **`render.py` + `templates/tracker.html.jinja2`** -- rebuilds the
  original's visual design (navy header, status pill colors, activity
  type tags, collapsible team sections) from the filtered data. The
  initiatives section keeps client-side JS to bucket activities into
  "this week / coming weeks / completed," same as the original
  artifact.
- **`main.py`** -- orchestrates pull -> filter -> diff -> render ->
  write, one source at a time so a source without credentials yet
  doesn't crash the whole run.

## Known data-quality gaps (carried forward from the original tracker)

These aren't bugs -- they're flagged intentionally so nothing silently
vanishes. Don't "fix" them without checking with the team first:

- The AI Roadmap sheet has no real due-date field yet, only
  quarter-level targets -- those items stay flagged "Missing" by
  design.
- Jira PMM issues without near-term due dates should eventually be
  summarized as a count rather than listed individually once volume
  gets high (not yet implemented -- currently listed individually).
- Lisa Harding's personal Asana list, Tilda Persson, and Diana Corredin
  are worth periodically checking to confirm they're not missing a
  connected board entirely, rather than genuinely having no work.
