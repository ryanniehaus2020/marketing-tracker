"""
Source of truth for team membership, RACI owner overrides, and the
multi-board dedup priority order.

This is the one file you edit by hand when the team's roster or RACI
assignments change -- everything else should be derived from source-tool
data, not hardcoded.
"""

# --- Team roster --------------------------------------------------------
# Order here also controls display order in the rendered tracker.
TEAMS = {
    "Executive": {
        "members": ["Caroline McCausland"],
        "default_open": False,
        "note": "No connected board yet.",
    },
    "Growth": {
        "members": [
            "Dafne Delgado",
            "Camila Santos",
            "Lisa Harding",
            "Luke Derderian",
            "Tilda Persson",
        ],
        "default_open": True,
    },
    "Product Marketing": {
        "members": ["Dana Pellegrini", "Laura Etchalus de Macedo"],
        "default_open": True,
    },
    "Content & Brand": {
        "members": [
            "Emily Gerson",
            "Alec Hamilton",
            "Mike Zientara",
            "Diana Corredin",
        ],
        "default_open": True,
        "note": (
            "Unassigned/contractor creative requests are folded into this "
            "team rather than shown as a standalone team."
        ),
    },
    "Events": {
        "members": ["Kristen Beinke", "Carah Etscheidt", "Vinni Chu"],
        "default_open": False,
    },
    "Operations": {
        "members": ["Ryan Niehaus", "Milla Nordwall"],
        "default_open": True,
    },
}

# Flat lookup: person -> team, derived from TEAMS above. Use this instead
# of re-deriving it ad hoc elsewhere.
PERSON_TO_TEAM = {
    person: team for team, cfg in TEAMS.items() for person in cfg["members"]
}

# --- RACI owner overrides ------------------------------------------------
# Some tools show the literal assignee/requester rather than the working
# owner per the RACI doc. Key = the literal source-tool value you see;
# value = the person the tracker should attribute the task to instead.
#
# Example from the source doc: several "Web Marketing Requests" tasks show
# Ryan Niehaus as the Asana assignee because he's the requester, not the
# worker -- the RACI owner is Dafne Delgado.
RACI_OWNER_OVERRIDES = {
    # (source, literal_assignee, project_tag_substring_or_None): real_owner
    ("asana", "Ryan Niehaus", "Web Marketing Requests"): "Dafne Delgado",
    # Add more as they're discovered, e.g.:
    # ("asana", "Camila Santos", "Localization needed for a success story"): "Camila Santos",
}


def apply_raci_override(source: str, literal_assignee: str, project_tag: str) -> str:
    """Return the RACI-corrected owner, or the literal assignee unchanged."""
    for (src, assignee, tag_substr), real_owner in RACI_OWNER_OVERRIDES.items():
        if src != source or assignee != literal_assignee:
            continue
        if tag_substr is None or (project_tag and tag_substr in project_tag):
            return real_owner
    return literal_assignee


# --- Channel -> default owner ---------------------------------------------
# When an outward-facing activity (an initiative activity, a HubSpot
# publish, etc.) only has a channel/type and no explicit owner yet, infer
# the owner from the channel rather than leaving it blank/TBD. An explicit
# owner on the item always wins -- this only fills a gap.
CHANNEL_OWNER_DEFAULTS = {
    "EMAIL": "Luke Derderian",
    "SOCIAL": "Emily Gerson",
    "WEBSITE": "Dafne Delgado",
    "NEWSLETTER": "Luke Derderian",
}


def default_owner_for_channel(channel: str | None) -> str | None:
    """Returns the inferred owner for a channel/type, or None if the
    channel isn't one we have a default for (e.g. BLOG, PR, CLIP, EVENT
    -- those still need an explicit owner)."""
    if not channel:
        return None
    return CHANNEL_OWNER_DEFAULTS.get(channel.strip().upper())


# --- Multi-board dedup priority order -------------------------------------
# When a task lives on more than one Asana board, pick ONE project tag to
# display using this fixed priority order (highest priority first).
# Each entry is a matcher against the task's list of project memberships.
DEDUP_PRIORITY = [
    {
        "label": "FY27 Marketing Initiatives portfolio",
        "portfolio_env": "ASANA_PORTFOLIO_FY27_CAMPAIGNS_GID",
        # e.g. Brand Awareness_Campaign_0826, Degreed Agents_Product Launch_0926
    },
    {
        "label": "Content Marketing portfolio",
        "portfolio_env": "ASANA_PORTFOLIO_CONTENT_MARKETING_GID",
        # e.g. Volume to Value eBook
    },
    {
        "label": "Individual team boards",
        # Not exhaustive -- add a board here as soon as it's confirmed to
        # be a standalone team board rather than a personal or campaign one.
        "project_names": [
            "Content Calendar",
            "All Creative Projects",
            "Marketing Operations",
            "Web Marketing Requests",
            "Paid Advertising + Media",
            "Email & Automation Management",
            "Event Projects",
        ],
    },
    {
        "label": "Individual contributor boards",
        # Verified against live Asana (2026-08-26): Lisa's personal board
        # is ONE project -- "Lisa To Do's" (gid 1217792928253659) -- with
        # "This Week" / "To Do" / "Waiting On Others" as *sections* inside
        # it, not separate projects named "Lisa — This Week" etc. (that
        # em-dash form was only ever this tracker's own display text).
        # Add other ICs' personal boards here once confirmed the same way
        # -- don't guess a naming convention from one example.
        "project_names": [
            "Lisa To Do's",
        ],
    },
]

# --- Known real Asana/Atlassian/Drive IDs (verified 2026-08-26) -----------
# Looked up live via the Asana/Atlassian/Google Drive connectors so the
# daily refresh doesn't have to re-search by name every run (and risk
# matching the wrong same-named object, e.g. "Marketing Operations" vs.
# "Marketing Operations Master Dashboard", or "Event Projects" vs. its
# 2019/2020/2021 archived namesakes). Re-verify and update if a board gets
# renamed, archived, or replaced.
ASANA_WORKSPACE_GID = "1199943304774115"

ASANA_PROJECT_GIDS = {
    "Web Marketing Requests": "1202966122105252",
    "Content Calendar": "1203158713461129",
    "All Creative Projects": "1200519962061957",
    "Marketing Operations": "1217800138766272",
    "Paid Advertising + Media": "1203665373615112",
    "Event Projects": "1201483003070040",
    "Email & Automation Management": "1200025860801880",
    "Lisa To Do's": "1217792928253659",
}

ASANA_PORTFOLIO_GIDS = {
    "FY27 Marketing Initiatives": "1213726795315426",
    "Content Marketing": "1212892150691924",
}

# Campaign projects living inside a portfolio above. The portfolio-membership
# fetch (get_items_for_portfolio) surfaces these for dedup priority, but their
# own tasks still have to be pulled directly -- they don't otherwise appear
# under any of the team boards in ASANA_PROJECT_GIDS.
ASANA_CAMPAIGN_PROJECT_GIDS = {
    "Degreed.ai_Product Launch_0926": "1217876918438817",  # renamed in Asana 2026-09-01 (was "Degreed Agents_Product Launch_0926"); same gid, now has real dated tasks
    "Workday_ABM Campaign_0826": "1217291381876379",
}

JIRA_PMM_PROJECT_KEY = "PMM"
ATLASSIAN_CLOUD_ID = "151636d7-9099-4803-a108-4f053f36c9fe"
CONFLUENCE_MARKETING_OPS_ROADMAP_PAGE_ID = "8566735021"  # MAR space

# Google Drive file IDs for documents this tracker's initiatives reference.
REFERENCED_DOCUMENT_IDS = {
    "AI-Powered Revolution messaging doc": "1dISbXEU8-_v7tFgLXor5cCUjugrhW7v6a716_rPi6VU",
    "Degreed.ai launch tracker (sheet)": "1rBGOEOAMml6ut6sUEsh7h4FUnqcaZgXSmOT9uzBiFc8",
    "Vision 2026 comms plan": "1ZlpbCrv7BOPtQNVrX8rQ6NtCrRZuHKzuv_5d6zi1k4I",
    "AI Roadmap FY27 (sheet)": "1d2iH1D2jXcW-jfkhLLBAJHoKeNvHceOZie3cLKhmF0E",
    "Website Roadmap working doc": "16MTqGAve79Ij4CIBuEHjKZVu2kuHUfk1rfT-YMPvlCU",
}

# --- Active-work statuses --------------------------------------------------
# Statuses that force a task into the visibility window regardless of due
# date distance.
ACTIVE_WORK_STATUSES = {
    "in progress",
    "in review",
    "blocked",
    "live",
    "this week",
    "waiting on others",
}

VISIBILITY_WINDOW_DAYS = 7
