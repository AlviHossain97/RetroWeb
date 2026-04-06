"""
Dashboard routes — serves the HTML dashboard views.
"""

import os
import subprocess
import threading
import time

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
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
    try:
        return _render_dashboard(request, "kiosk/dashboard.html")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard render error: {e}")


@router.get("/dashboard/kiosk", response_class=HTMLResponse)
def dashboard_kiosk(request: Request):
    """Kiosk dashboard — optimized for EmulationStation fullscreen."""
    try:
        return _render_dashboard(request, "kiosk/dashboard.html")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard render error: {e}")


@router.get("/dashboard/admin", response_class=HTMLResponse)
def dashboard_admin(request: Request):
    """Admin dashboard — richer view for browser-based management."""
    try:
        return _render_dashboard(request, "admin/dashboard.html")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard render error: {e}")


# ── Screenshot fallback for ultra-lightweight Pi display ──

_SCREENSHOT_PATH = "/tmp/pistation-dashboard.jpg"
_SCREENSHOT_TMP = "/tmp/pistation-dashboard-new.jpg"


def _screenshot_worker():
    """Background thread: headless Brave screenshots the kiosk page every 10s."""
    while True:
        try:
            subprocess.run(
                [
                    "brave-browser-stable", "--headless", "--disable-gpu",
                    f"--screenshot={_SCREENSHOT_TMP}",
                    "--window-size=1280,720",
                    "http://localhost:8000/dashboard/kiosk",
                ],
                timeout=15,
                capture_output=True,
            )
            if os.path.exists(_SCREENSHOT_TMP):
                os.replace(_SCREENSHOT_TMP, _SCREENSHOT_PATH)
        except Exception:
            pass
        time.sleep(10)


# Start worker on import
threading.Thread(target=_screenshot_worker, daemon=True).start()


@router.get("/dashboard/live", response_class=HTMLResponse)
def dashboard_live():
    """Tiny HTML page that auto-refreshes a screenshot of the kiosk dashboard.

    Pi loads this page — near-zero rendering effort (just an image).
    """
    return HTMLResponse(content=(
        '<!DOCTYPE html><html><head>'
        '<meta http-equiv="refresh" content="10">'
        '<style>*{margin:0;padding:0}img{width:100vw;height:100vh;object-fit:cover}</style>'
        '</head><body><img src="/dashboard/screenshot" alt="PiStation Dashboard"></body></html>'
    ))


@router.get("/dashboard/screenshot")
def dashboard_screenshot():
    """Returns the latest headless-rendered screenshot of the kiosk dashboard."""
    if os.path.exists(_SCREENSHOT_PATH):
        return FileResponse(_SCREENSHOT_PATH, media_type="image/jpeg")
    return HTMLResponse("Screenshot not ready yet — check back in 10 seconds.", status_code=503)
