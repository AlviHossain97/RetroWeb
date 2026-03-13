"""
View models for passing structured data to Jinja2 templates.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DashboardContext:
    """All data needed to render the dashboard template."""
    active_session: dict | None = None
    recent_sessions: list[dict] = field(default_factory=list)
    top_games: list[dict] = field(default_factory=list)
    total_sessions: int = 0
    total_seconds: int = 0
    fav_system_name: str = "N/A"
