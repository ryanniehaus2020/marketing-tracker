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


# --- Multi-board dedup priority order -------------------------------------
# When a task lives on more than one Asana board, pick ONE project tag to
# display using this fixed priority order (highest priority first).
# Each entry is a matcher against the task's list of project memberships.
DEDUP_PRIORITY = [
    {"label": "FY27 Marketing Campaigns portfolio", "portfolio_env": "ASANA_PORTFOLIO_FY27_CAMPAIGNS_GID"},
    {"label": "Content Marketing portfolio", "portfolio_env": "ASANA_PORTFOLIO_CONTENT_MARKETING_GID"},
    {
        "label": "Team boards",
        "project_names": [
            "Content Calendar",
            "All Creative Projects",
            "Email & Automation Management",
            "Paid Advertising + Media",
            "Web Marketing Requests",
            "Event Projects",
        ],
    },
    {
        "label": "Personal to-do boards",
        "project_name_suffixes": [" — This Week", " - This Week"],
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

# --- Asana campaign projects ----------------------------------------------
# Campaign projects (FY27 Marketing Initiatives portfolio) tracked as
# campaigns. Display name -> Asana project gid. Add a project here only
# after it has been approved in the daily QA review.
ASANA_CAMPAIGN_PROJECT_GIDS = {
    "Degreed.ai_Product Launch_0926": "1217876918438817",  # renamed 2026-09-01 (was "Degreed Agents_Product Launch_0926")
    "Workday_ABM Campaign_0826": "1217291381876379",
    "Marketing Website_Relaunch_0926": "1218474792086131",  # approved 2026-10-01
    "Winback/Closed Lost Opps_Campaign_0926": "1218504958548272",  # approved 2026-10-01; Asana name is " Winback/Closed Lost Opps_Campaign_0926 [In Progress]"
    "AI-Powered Revolution S3_Webinar_0926": "1218981087988039",  # approved 2026-10-01
}

# --- Asana "Progress" custom field -> tracker status -------------------------
# Used for the Degreed.ai_Product Launch_0926 project's Status column.
ASANA_PROGRESS_STATUS_MAP = {
    "Not Started": "Queue",
    "In Progress": "In Progress",
    "Completed": "Complete",
    "Running": "Live",  # approved 2026-10-01; "Live" is an active-work status
}
