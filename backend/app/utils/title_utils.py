"""
Game title extraction from ROM file paths.
"""

from pathlib import Path


def game_title_from_path(path: str) -> str:
    """Extract a human-readable game title from a ROM file path.

    Takes the file stem (filename without extension) as the display title.

    Examples:
        "/home/pi/RetroPie/roms/snes/Super Mario World.sfc" → "Super Mario World"
        None or "" → "Unknown Game"
    """
    if not path:
        return "Unknown Game"
    return Path(path).stem
