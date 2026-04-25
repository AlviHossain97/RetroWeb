#pragma once

#include <cstdint>

namespace mythical {

// 24.8 fixed-point signed: top 24 bits integer, bottom 8 bits fraction.
using Fixed = std::int32_t;

constexpr int FIXED_SHIFT = 8;
constexpr Fixed FIXED_ONE = 1 << FIXED_SHIFT;

constexpr Fixed fx_from_int(int v) { return static_cast<Fixed>(v) << FIXED_SHIFT; }
constexpr int   fx_to_int(Fixed f)  { return static_cast<int>(f >> FIXED_SHIFT); }
constexpr Fixed fx_from_frac(int num, int den) {
    return static_cast<Fixed>((static_cast<std::int64_t>(num) << FIXED_SHIFT) / den);
}

inline Fixed fx_mul(Fixed a, Fixed b) {
    return static_cast<Fixed>((static_cast<std::int64_t>(a) * b) >> FIXED_SHIFT);
}

inline Fixed fx_div(Fixed a, Fixed b) {
    if (b == 0) return 0;
    return static_cast<Fixed>((static_cast<std::int64_t>(a) << FIXED_SHIFT) / b);
}

inline Fixed fx_abs(Fixed a) { return a < 0 ? -a : a; }

// Integer square root using Newton-Raphson; input/output in fixed-point.
Fixed fx_sqrt(Fixed value);

// 256-entry sin/cos LUT. angle is in "binary degrees" 0..255 (a full circle).
Fixed fx_sin(int angle_bin256);
Fixed fx_cos(int angle_bin256);

struct FixedVec2 {
    Fixed x = 0;
    Fixed y = 0;

    FixedVec2() = default;
    FixedVec2(Fixed x_, Fixed y_) : x(x_), y(y_) {}

    static FixedVec2 from_ints(int xi, int yi) {
        return FixedVec2(fx_from_int(xi), fx_from_int(yi));
    }

    FixedVec2 operator+(const FixedVec2& o) const { return {x + o.x, y + o.y}; }
    FixedVec2 operator-(const FixedVec2& o) const { return {x - o.x, y - o.y}; }
};

Fixed fx_distance(const FixedVec2& a, const FixedVec2& b);

}  // namespace mythical
