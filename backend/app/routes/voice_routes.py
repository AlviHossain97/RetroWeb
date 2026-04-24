"""Realtime voice gateway routes."""

from fastapi import APIRouter, HTTPException, WebSocket

from app.services.voice_gateway import get_voice_gateway_service

router = APIRouter(prefix="/ai/voice", tags=["voice"])


@router.get("/health")
async def voice_health():
    """Return normalized voice provider availability."""
    service = get_voice_gateway_service()
    return await service.check_health()


@router.post("/session")
async def create_voice_session():
    """Create a prepared realtime voice session."""
    service = get_voice_gateway_service()
    try:
        return await service.create_session()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.websocket("/realtime")
async def voice_realtime(websocket: WebSocket):
    """Primary browser-facing realtime voice websocket."""
    session_id = websocket.query_params.get("session_id", "").strip()
    if not session_id:
        await websocket.close(code=4400)
        return

    service = get_voice_gateway_service()
    await service.accept_websocket(websocket, session_id)
