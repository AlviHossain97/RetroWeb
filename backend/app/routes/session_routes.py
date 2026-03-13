"""
Session routes — POST /session/start and POST /session/end.
"""

from fastapi import APIRouter
from app.models.api_models import StartEvent, EndEvent
from app.services import session_service

router = APIRouter(prefix="/session", tags=["sessions"])


@router.post("/start")
def session_start(ev: StartEvent):
    """Record the start of a new gaming session."""
    return session_service.start_session(ev)


@router.post("/end")
def session_end(ev: EndEvent):
    """Record the end of a gaming session."""
    return session_service.end_session(ev)
