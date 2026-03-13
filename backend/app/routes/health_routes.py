"""
Health and version routes.
"""

from fastapi import APIRouter
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """Simple health check."""
    return {"ok": True}


@router.get("/version")
def version():
    """Return API identity and version."""
    settings = get_settings()
    return {"api": "pistation", "version": settings.app_version}
