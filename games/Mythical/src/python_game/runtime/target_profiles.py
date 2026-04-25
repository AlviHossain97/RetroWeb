"""Target capability profiles for current and future runtimes."""
from __future__ import annotations

from dataclasses import dataclass

from settings import SCREEN_HEIGHT, SCREEN_WIDTH, TARGET_FPS


@dataclass(frozen=True)
class TargetProfile:
    name: str
    screen_width: int
    screen_height: int
    fixed_fps: int
    supports_alpha: bool
    supports_procedural_audio: bool
    supports_filesystem_saves: bool
    notes: str = ""


PYGAME_PROFILE = TargetProfile(
    name="pygame",
    screen_width=SCREEN_WIDTH,
    screen_height=SCREEN_HEIGHT,
    fixed_fps=TARGET_FPS,
    supports_alpha=True,
    supports_procedural_audio=True,
    supports_filesystem_saves=True,
    notes="Desktop prototype runtime using pygame display, mixer, and JSON saves.",
)


GBA_PROFILE = TargetProfile(
    name="gba",
    screen_width=240,
    screen_height=160,
    fixed_fps=60,
    supports_alpha=False,
    supports_procedural_audio=False,
    supports_filesystem_saves=False,
    notes="Handheld target profile for later port work; assumes tile/sprite rendering and SRAM saves.",
)
