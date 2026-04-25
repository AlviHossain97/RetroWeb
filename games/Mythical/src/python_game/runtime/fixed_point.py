"""
Fixed-point arithmetic for GBA port compatibility.

This module provides integer-based math that can replace float operations
during the GBA port. Uses 24.8 fixed-point format (8 fractional bits).

On GBA: fixed-point math is faster than soft-float and saves code size.
"""

from __future__ import annotations

# Fixed-point constants (24.8 format)
FP_SHIFT = 8
FP_ONE = 1 << FP_SHIFT  # 256
FP_HALF = FP_ONE // 2  # 128
FP_MASK = FP_ONE - 1  # 255

# Lookup table sizes (must be power of 2 for fast modulo)
SIN_TABLE_SIZE = 256
ANGLE_MASK = SIN_TABLE_SIZE - 1


def to_fixed(value: float) -> int:
    """Convert float to fixed-point integer."""
    return int(value * FP_ONE)


def to_float(value: int) -> float:
    """Convert fixed-point to float (for debug/display)."""
    return value / FP_ONE


def from_int(value: int) -> int:
    """Convert integer to fixed-point."""
    return value << FP_SHIFT


def to_int(value: int) -> int:
    """Convert fixed-point to integer (truncates)."""
    return value >> FP_SHIFT


def to_int_rounded(value: int) -> int:
    """Convert fixed-point to integer with rounding."""
    return (value + FP_HALF) >> FP_SHIFT


def mul(a: int, b: int) -> int:
    """Multiply two fixed-point values."""
    return (a * b) >> FP_SHIFT


def div(numerator: int, denominator: int) -> int:
    """Divide two fixed-point values."""
    if denominator == 0:
        return 0
    return (numerator << FP_SHIFT) // denominator


def sqrt(value: int) -> int:
    """Integer square root of fixed-point value."""
    if value <= 0:
        return 0
    # Newton-Raphson iteration
    x = value << (FP_SHIFT // 2)
    for _ in range(8):  # Converges quickly
        x = (x + div(value, x)) >> 1
    return x


def clamp_fixed(value: int, min_val: int, max_val: int) -> int:
    """Clamp fixed-point value to range."""
    if value < min_val:
        return min_val
    if value > max_val:
        return max_val
    return value


def lerp_fixed(a: int, b: int, t: int) -> int:
    """Linear interpolation: a + (b - a) * t"""
    return a + mul(b - a, t)


# Trigonometry lookup tables (generated at import)
def _build_sin_table() -> tuple[list[int], list[int]]:
    """Build sine/cosine lookup tables in fixed-point."""
    import math

    sin_table = []
    cos_table = []
    for i in range(SIN_TABLE_SIZE):
        angle = (i / SIN_TABLE_SIZE) * 2 * math.pi
        sin_table.append(to_fixed(math.sin(angle)))
        cos_table.append(to_fixed(math.cos(angle)))
    return sin_table, cos_table


_SIN_TABLE, _COS_TABLE = _build_sin_table()


def sin(angle_index: int) -> int:
    """Get sine from lookup table (angle_index is 0-255 for 0-360 degrees)."""
    return _SIN_TABLE[angle_index & ANGLE_MASK]


def cos(angle_index: int) -> int:
    """Get cosine from lookup table."""
    return _COS_TABLE[angle_index & ANGLE_MASK]


def angle_from_degrees(degrees: float) -> int:
    """Convert degrees to table index (0-255)."""
    return int((degrees / 360.0) * SIN_TABLE_SIZE) & ANGLE_MASK


def polar_offset_fixed(angle_index: int, magnitude: int) -> tuple[int, int]:
    """Calculate offset from angle and magnitude (both fixed-point)."""
    dx = mul(cos(angle_index), magnitude)
    dy = mul(sin(angle_index), magnitude)
    return dx, dy


# Distance and movement helpers (for entity systems)
def distance_sq_fixed(x1: int, y1: int, x2: int, y2: int) -> int:
    """Squared distance between two fixed-point points."""
    dx = x2 - x1
    dy = y2 - y1
    return mul(dx, dx) + mul(dy, dy)


def distance_fixed(x1: int, y1: int, x2: int, y2: int) -> int:
    """Distance between two fixed-point points."""
    return sqrt(distance_sq_fixed(x1, y1, x2, y2))


def normalize_fixed(dx: int, dy: int, min_val: int = 1) -> tuple[int, int, int]:
    """Normalize a vector, returns (nx, ny, length) in fixed-point."""
    length_sq = mul(dx, dx) + mul(dy, dy)
    if length_sq < min_val * min_val:
        return dx, dy, 1 << FP_SHIFT  # Return identity if too small

    length = sqrt(length_sq)
    if length == 0:
        return 0, 0, 1 << FP_SHIFT

    nx = div(dx, length)
    ny = div(dy, length)
    return nx, ny, length


# Migration helpers for gradual porting
class FixedVec2:
    """2D vector using fixed-point math. Drop-in replacement for float tuples."""

    __slots__ = ("x", "y")

    def __init__(self, x: float | int = 0, y: float | int = 0, *, fixed: bool = False):
        if fixed:
            self.x = int(x)
            self.y = int(y)
        else:
            self.x = to_fixed(float(x))
            self.y = to_fixed(float(y))

    @property
    def xf(self) -> float:
        """X as float (for debug)."""
        return to_float(self.x)

    @property
    def yf(self) -> float:
        """Y as float (for debug)."""
        return to_float(self.y)

    @property
    def xi(self) -> int:
        """X as integer pixel position."""
        return to_int(self.x)

    @property
    def yi(self) -> int:
        """Y as integer pixel position."""
        return to_int(self.y)

    def __add__(self, other: "FixedVec2") -> "FixedVec2":
        return FixedVec2(self.x + other.x, self.y + other.y, fixed=True)

    def __sub__(self, other: "FixedVec2") -> "FixedVec2":
        return FixedVec2(self.x - other.x, self.y - other.y, fixed=True)

    def __mul__(self, scalar: int) -> "FixedVec2":
        """Scalar multiply with fixed-point scalar."""
        return FixedVec2(mul(self.x, scalar), mul(self.y, scalar), fixed=True)

    def length(self) -> int:
        return sqrt(mul(self.x, self.x) + mul(self.y, self.y))

    def normalized(self) -> "FixedVec2":
        nx, ny, _ = normalize_fixed(self.x, self.y)
        return FixedVec2(nx, ny, fixed=True)

    def distance_to(self, other: "FixedVec2") -> int:
        return distance_fixed(self.x, self.y, other.x, other.y)

    def to_tile(self, tile_size: int = 32 << FP_SHIFT) -> tuple[int, int]:
        """Convert to tile coordinates."""
        return div(self.x, tile_size), div(self.y, tile_size)

    @classmethod
    def from_tile(
        cls, tx: int, ty: int, tile_size: int = 32 << FP_SHIFT
    ) -> "FixedVec2":
        """Create from tile coordinates.

        tx, ty are tile indices (integers), tile_size is in fixed-point.
        """
        return cls(
            from_int(tx) * to_int(tile_size),
            from_int(ty) * to_int(tile_size),
            fixed=True,
        )

    def __repr__(self) -> str:
        return f"FixedVec2({self.xf:.3f}, {self.yf:.3f})"
