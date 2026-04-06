"""
Session routes — POST /session/start and POST /session/end.
"""

from fastapi import APIRouter, HTTPException
from app.models.api_models import StartEvent, EndEvent
from app.services import session_service

router = APIRouter(prefix="/session", tags=["sessions"])


@router.post("/start")
def session_start(ev: StartEvent):
    """Record the start of a new gaming session."""
    try:
        return session_service.start_session(ev)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {e}")


@router.post("/end")
def session_end(ev: EndEvent):
    """Record the end of a gaming session."""
    try:
        return session_service.end_session(ev)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end session: {e}")
