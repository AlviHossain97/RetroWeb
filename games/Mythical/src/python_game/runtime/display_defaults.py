"""Shared logical viewport defaults for backend-neutral layout code."""
from __future__ import annotations


DEFAULT_VIEWPORT_WIDTH = 320
DEFAULT_VIEWPORT_HEIGHT = 240


def default_viewport_size() -> tuple[int, int]:
    return DEFAULT_VIEWPORT_WIDTH, DEFAULT_VIEWPORT_HEIGHT
