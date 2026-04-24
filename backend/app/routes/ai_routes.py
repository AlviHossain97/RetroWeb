"""AI context endpoint — enriches AI prompts with gaming data."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.ai_context_service import fetch_context

router = APIRouter(prefix="/ai", tags=["ai"])


class ContextRequest(BaseModel):
    question: str | None = None


@router.post("/context")
def get_ai_context(req: ContextRequest | None = None):
    """Returns gaming data context for AI system prompt enrichment."""
    try:
        return {"context": fetch_context()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch AI context: {e}")


@router.get("/context")
def get_ai_context_get():
    """GET version for easy testing."""
    try:
        return {"context": fetch_context()}
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
