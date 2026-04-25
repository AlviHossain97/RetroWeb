"""Runtime-owned animation clock shared by rendering systems."""
from __future__ import annotations

_elapsed_seconds = 0.0


def reset_time() -> None:
    global _elapsed_seconds
    _elapsed_seconds = 0.0


def advance_time(dt: float) -> float:
    global _elapsed_seconds
    _elapsed_seconds += max(0.0, float(dt))
    return _elapsed_seconds


def get_time() -> float:
    return _elapsed_seconds
