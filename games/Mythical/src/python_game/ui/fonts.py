"""Cached font access for pygame-backed UI rendering.

This keeps font selection centralized so future runtime targets can replace the
implementation without every screen instantiating fonts directly.
"""
from __future__ import annotations

from functools import lru_cache

import pygame


@lru_cache(maxsize=128)
def get_font(size: int, bold: bool = False, italic: bool = False, name: str = "monospace"):
    return pygame.font.SysFont(name, int(size), bold=bold, italic=italic)


def clear_font_cache() -> None:
    get_font.cache_clear()
