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
        # Personal to-do boards are named "<first name> — <bucket>" (e.g.
        # "Lisa — This Week", "Lisa — To Do", "Lisa — Waiting On Others")
        # -- match on the person's first name rather than a fixed bucket
        # list, since the bucket names vary per person and over time.
        "personal_board_prefixes": True,
    },
]

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
