"""Shared gameplay math helpers.

These functions centralize the float/trig operations that still exist in the
prototype. The immediate benefit is consistency across systems; the longer-term
benefit is that a fixed-point or lookup-table implementation can later replace
these helpers in one place during a real GBA port.
"""
from __future__ import annotations

import math


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def vector_length(dx: float, dy: float) -> float:
    return math.hypot(dx, dy)


def point_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def safe_normalize(dx: float, dy: float, *, minimum: float = 0.001) -> tuple[float, float, float]:
    length = max(minimum, math.hypot(dx, dy))
    return dx / length, dy / length, length


def polar_offset(angle_radians: float, magnitude: float) -> tuple[float, float]:
    return math.cos(angle_radians) * magnitude, math.sin(angle_radians) * magnitude


def degrees_offset(angle_degrees: float, magnitude: float) -> tuple[float, float]:
    return polar_offset(math.radians(angle_degrees), magnitude)


def oscillate(
    timer: float,
    frequency: float,
    *,
    amplitude: float = 1.0,
    offset: float = 0.0,
    phase: float = 0.0,
) -> float:
    return offset + amplitude * math.sin(timer * frequency + phase)


def pulse01(timer: float, frequency: float, *, phase: float = 0.0) -> float:
    return 0.5 + 0.5 * math.sin(timer * frequency + phase)


def angle_to(dx: float, dy: float) -> float:
    return math.atan2(dy, dx)


def angle_between_vectors_deg(ax: float, ay: float, bx: float, by: float) -> float:
    amag = max(0.001, math.hypot(ax, ay))
    bmag = max(0.001, math.hypot(bx, by))
    dot = (ax * bx + ay * by) / (amag * bmag)
    return math.degrees(math.acos(clamp(dot, -1.0, 1.0)))
