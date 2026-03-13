"""
Dashboard routes — serves the HTML dashboard views.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.services import dashboard_service
from app.utils.time_utils import format_seconds
from app.utils.title_utils import game_title_from_path

router = APIRouter(tags=["dashboard"])


def _render_dashboard(request: Request, template_name: str) -> HTMLResponse:
    """Fetch dashboard data and render the specified template."""
    ctx = dashboard_service.get_dashboard_context()
    env = request.app.state.templates
    template = env.get_template(template_name)
    html = template.render(
        ctx=ctx,
        format_seconds=format_seconds,
        game_title_from_path=game_title_from_path,
    )
    return HTMLResponse(content=html)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    """Main dashboard — defaults to the kiosk view."""
    return _render_dashboard(request, "kiosk/dashboard.html")


@router.get("/dashboard/kiosk", response_class=HTMLResponse)
def dashboard_kiosk(request: Request):
    """Kiosk dashboard — optimized for EmulationStation fullscreen."""
    return _render_dashboard(request, "kiosk/dashboard.html")


@router.get("/dashboard/admin", response_class=HTMLResponse)
def dashboard_admin(request: Request):
    """Admin dashboard — richer view for browser-based management."""
    return _render_dashboard(request, "admin/dashboard.html")
