"""AI context endpoint — enriches AI prompts with gaming data."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import get_conn
from app.services import ai_tools_service
from app.utils.title_utils import game_title_from_path

router = APIRouter(prefix="/ai", tags=["ai"])


def _format_time(seconds: int) -> str:
    if not seconds or seconds <= 0:
        return "0 minutes"
    if seconds < 60:
        return f"{seconds} seconds"
    if seconds < 3600:
        return f"{seconds // 60} minutes"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h} hours {m} minutes"


def _build_context(
    summary: dict,
    top_games: list,
    systems: list,
    recent: list,
    active: list,
    longest: dict | None,
) -> str:
    """Build a natural language context string from gaming data."""
    lines = []

    # Overall stats
    if summary:
        lines.append("GAMING STATS OVERVIEW:")
        lines.append(f"- Total sessions: {summary.get('total_sessions', 0)}")
        lines.append(f"- Total playtime: {_format_time(summary.get('total_seconds', 0))}")
        lines.append(f"- Unique systems: {summary.get('unique_systems', 0)}")
        if summary.get('first_session'):
            lines.append(f"- First session: {summary['first_session']}")
        if summary.get('last_session'):
            lines.append(f"- Last session: {summary['last_session']}")

    # Active sessions
    if active:
        lines.append("\nCURRENTLY PLAYING:")
        for s in active:
            title = game_title_from_path(s.get('rom_path', ''))
            lines.append(
                f"- {title} ({s.get('system_name', 'unknown')}) "
                f"on {s.get('pi_hostname', 'unknown')} since {s.get('started_at', '?')}"
            )

    # Top games
    if top_games:
        lines.append("\nTOP GAMES BY PLAYTIME:")
        for i, g in enumerate(top_games, 1):
            title = game_title_from_path(g.get('rom_path', ''))
            lines.append(
                f"  {i}. {title} ({g.get('system_name', 'unknown')}) "
                f"- {_format_time(g.get('total_seconds', 0))}, "
                f"{g.get('session_count', 0)} sessions"
            )

    # System breakdown
    if systems:
        lines.append("\nPLAYTIME BY SYSTEM:")
        for s in systems:
            lines.append(
                f"  - {s.get('system_name', 'unknown').upper()}: "
                f"{_format_time(s.get('total_seconds', 0))}, "
                f"{s.get('session_count', 0)} sessions"
            )

    # Recent sessions
    if recent:
        lines.append("\nRECENT SESSIONS:")
        for s in recent:
            title = game_title_from_path(s.get('rom_path', ''))
            duration = (
                _format_time(s.get('duration_seconds', 0))
                if s.get('duration_seconds')
                else 'in progress'
            )
            lines.append(
                f"  - {title} ({s.get('system_name', 'unknown')}) "
                f"on {s.get('pi_hostname', 'unknown')}, "
                f"{s.get('started_at', '?')}, duration: {duration}"
            )

    # Longest session
    if longest:
        title = game_title_from_path(longest.get('rom_path', ''))
        lines.append(
            f"\nLONGEST SESSION EVER: {title} "
            f"({longest.get('system_name', 'unknown')}) "
            f"- {_format_time(longest.get('duration_seconds', 0))}"
        )

    return "\n".join(lines)


class ContextRequest(BaseModel):
    question: str | None = None


def _fetch_context() -> str:
    """Shared helper to query DB and build context string."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            summary = ai_tools_service.get_gaming_summary(cur)
            top_games = ai_tools_service.get_top_games(cur, 5)
            systems = ai_tools_service.get_system_breakdown(cur)
            recent = ai_tools_service.get_recent_sessions(cur, 5)
            active = ai_tools_service.get_active_sessions(cur)
            longest = ai_tools_service.get_longest_session(cur)
    finally:
        conn.close()

    return _build_context(summary, top_games, systems, recent, active, longest)


@router.post("/context")
def get_ai_context(req: ContextRequest | None = None):
    """Returns gaming data context for AI system prompt enrichment."""
    try:
        return {"context": _fetch_context()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch AI context: {e}")


@router.get("/context")
def get_ai_context_get():
    """GET version for easy testing."""
    try:
        return {"context": _fetch_context()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch AI context: {e}")


class VoiceStageRequest(BaseModel):
    stage: str
    detail: str | None = None


@router.post("/voice-stage")
def log_voice_stage(req: VoiceStageRequest):
    """Prints a voice pipeline stage marker to the server terminal."""
    if req.detail:
        print(f"[VOICE] {req.stage} — {req.detail}", flush=True)
    else:
        print(f"[VOICE] {req.stage}", flush=True)
    return {"ok": True}


class GroundingRequest(BaseModel):
    question: str
    history: list = []
    mode: str = "auto"  # "auto" | "always" | "never"

@router.post("/ground")
async def get_grounding_context(req: GroundingRequest):
    """Executes the web-search grounding pipeline.

    Accepts mode from the frontend UI toggle to override the server-side default.
    Returns structured grounding context with sources for the frontend to display.
    """
    try:
        from app.services.grounding_service import prepare_grounded_context
        print(f"[GROUND] /ai/ground hit — question={req.question!r}, mode={req.mode}")
        result = await prepare_grounded_context(
            req.question, req.history, mode_override=req.mode
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Grounding pipeline error: {e}")
