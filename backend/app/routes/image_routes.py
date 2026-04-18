"""
Image generation routes — POST /ai/generate-image
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.image_generation_service import generate_game_art

router = APIRouter(prefix="/ai", tags=["ai"])


class ImageGenRequest(BaseModel):
    prompt: str
    gameContext: str | None = None
    stylePreset: str | None = None


@router.post("/generate-image")
async def generate_image_endpoint(req: ImageGenRequest):
    """Generate game-inspired artwork via Mistral refinement + ImageRouter."""
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")

    if len(req.prompt) > 2000:
        raise HTTPException(status_code=400, detail="Prompt too long (max 2000 chars)")

    try:
        result = await generate_game_art(
            user_prompt=req.prompt.strip(),
            game_context=req.gameContext,
            style_preset=req.stylePreset,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        print(f"[IMAGE] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Image generation failed unexpectedly")
