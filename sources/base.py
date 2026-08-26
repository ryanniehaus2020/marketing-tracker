"""
Common normalized task shape that every source module must return, plus
small shared helpers.

Every source_*.py module exposes one function:

    fetch(mock: bool = False) -> list[dict]

and each dict must have exactly this shape:

    {
        "name": str,
        "project_tag": str | None,   # display label after dedup applied
        "all_project_tags": list[str],  # every board/project this task lives on, pre-dedup
        "status": str,               # raw status string, e.g. "In Progress"
        "owner": str | None,         # literal source-tool assignee, pre-RACI-override
        "due_date": str | None,      # ISO "YYYY-MM-DD" or None
        "source": str,               # "asana" | "jira" | "confluence" | "hubspot" | "sheets"
        "source_url": str | None,
    }

Keeping this contract narrow is what lets rules.py / diff.py / render.py
stay source-agnostic.
"""

from dataclasses import dataclass, asdict


@dataclass
class NormalizedTask:
    name: str
    status: str
    source: str
    project_tag: str | None = None
    all_project_tags: list | None = None
    owner: str | None = None
    due_date: str | None = None
    source_url: str | None = None

    def __post_init__(self):
        if self.all_project_tags is None:
            self.all_project_tags = [self.project_tag] if self.project_tag else []

    def to_dict(self) -> dict:
        return asdict(self)


def require_env(env: dict, *keys: str) -> None:
    """Raise a clear error if required env vars are missing, rather than
    failing deep inside an HTTP client with a confusing message."""
    missing = [k for k in keys if not env.get(k)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            f"Check your .env against .env.example."
        )
