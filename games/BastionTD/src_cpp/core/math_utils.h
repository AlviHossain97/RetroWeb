#pragma once

#include "core/types.h"

#include <algorithm>
#include <cmath>

inline float sim_mul(float a, float b) { return a * b; }
inline float sim_div(float a, float b) { return a / b; }
inline int sim_to_int(float a) { return static_cast<int>(a); }
inline float sim_abs(float a) { return std::fabs(a); }
inline float sim_min(float a, float b) { return std::min(a, b); }
inline float sim_max(float a, float b) { return std::max(a, b); }
inline float sim_clamp(float v, float lo, float hi) { return std::clamp(v, lo, hi); }

constexpr float EPSILON = 0.001f;

inline bool sim_approx_eq(float a, float b, float eps = EPSILON) {
    return sim_abs(a - b) < eps;
}

inline float distance_sq(Vec2 a, Vec2 b) {
    const float dx = a.x - b.x;
    const float dy = a.y - b.y;
    return sim_mul(dx, dx) + sim_mul(dy, dy);
}

inline float distance(Vec2 a, Vec2 b) {
    return std::sqrt(distance_sq(a, b));
}

inline Vec2 lerp(Vec2 prev, Vec2 curr, float alpha) {
    return {
        prev.x + (curr.x - prev.x) * alpha,
        prev.y + (curr.y - prev.y) * alpha,
    };
}
