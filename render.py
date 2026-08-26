"""
Render layer: feeds normalized+filtered data and the initiatives config
into the Jinja2 template to reproduce the original artifact's HTML/CSS
structure.

Team tables are fully computed server-side (rules.py already did the
filtering/sorting). The initiatives section keeps the original's
client-side JS bucketing (next week / coming weeks / completed) since
that's just as easy to do in the browser and matches the reference
artifact's structure -- we just pass the raw activities list as JSON.
"""

import json
from datetime import date, datetime

from jinja2 import Environment, FileSystemLoader

STATUS_BADGE_STYLES = {
    "queue": ("#eef0f4", "#5b6472"),
    "backlog": ("#f1f1f4", "#5b6472"),
    "in progress": ("#e8f0fd", "#1f5fbf"),
    "this week": ("#e8f0fd", "#1f5fbf"),
    "waiting on others": ("#e8f0fd", "#1f5fbf"),
    "blocked": ("#fbe7e4", "#c0392b"),
    "in review": ("#fdf3d9", "#b8860b"),
    "live": ("#e7f6ee", "#1b8a5a"),
    "done": ("#e7f6ee", "#1b8a5a"),
}

ACTIVITY_TYPE_COLORS = {
    "SOCIAL": "#7c4fd1",
    "EMAIL": "#0f8b8d",
    "BLOG": "#b8860b",
    "NEWSLETTER": "#0f8b8d",
    "WEBSITE": "#4a5568",
    "PR": "#c2477b",
    "CLIP": "#7c4fd1",
    "EVENT": "#a8791a",
}


def status_badge_colors(status: str | None) -> tuple[str, str]:
    if not status:
        return STATUS_BADGE_STYLES["queue"]
    return STATUS_BADGE_STYLES.get(status.strip().lower(), STATUS_BADGE_STYLES["queue"])


def render(
    processed: dict,
    initiatives: list[dict],
    scope_notes: list[str],
    team_order: list[str],
    team_open_by_default: dict[str, bool],
    template_dir: str = "templates",
    template_name: str = "tracker.html.jinja2",
) -> str:
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
    env.filters["status_colors"] = status_badge_colors
    template = env.get_template(template_name)

    now = datetime.now()
    return template.render(
        last_refreshed=now.strftime("%B %-d, %Y at %-I:%M %p"),
        window_label="Next 7 days",
        cadence_label="Refreshed daily",
        teams=processed["teams"],
        team_order=team_order,
        team_open_by_default=team_open_by_default,
        initiatives=initiatives,
        initiatives_json=json.dumps(initiatives),
        scope_notes=scope_notes,
        activity_type_colors=ACTIVITY_TYPE_COLORS,
        today_iso=date.today().isoformat(),
    )
