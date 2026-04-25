#include "mythical/core/fixed.hpp"

namespace mythical {

namespace {

// sin table: 256 entries, one full circle.
// Entry angle_bin256 = i maps to radians i * 2*pi / 256.
// Values are Fixed (24.8) in range [-256, 256].
// Precomputed below, symmetrical; we generate by quadrant at startup via once-only init.
struct SinTable {
    Fixed values[256];
    SinTable() {
        // Use integer approximation via Taylor series for half-circle, mirror for the rest.
        // We'll use a small iterative approach using an integer CORDIC-style rotation.
        // To avoid floats entirely: use a precomputed 0..64 quadrant.
        // quarter[i] = round(sin(i/64 * pi/2) * 256), for i in 0..64.
        static const int quarter[65] = {
            0,   6,   13,  19,  25,  31,  38,  44,  50,  56,  62,  68,  74,  80,  86,  92,
            98,  103, 109, 115, 120, 126, 131, 136, 142, 147, 152, 157, 162, 167, 171, 176,
            181, 185, 189, 193, 197, 201, 205, 209, 212, 216, 219, 222, 225, 228, 231, 234,
            236, 238, 241, 243, 244, 246, 248, 249, 251, 252, 253, 254, 255, 255, 256, 256,
            256
        };
        for (int i = 0; i < 256; ++i) {
            int q = i & 63;
            int s;
            switch (i / 64) {
                case 0: s = quarter[q]; break;
                case 1: s = quarter[64 - q]; break;
                case 2: s = -quarter[q]; break;
                default: s = -quarter[64 - q]; break;
            }
            values[i] = static_cast<Fixed>(s);
        }
    }
};

const SinTable& sin_table() {
    static SinTable t;
    return t;
}

}  // namespace

Fixed fx_sqrt(Fixed value) {
    if (value <= 0) return 0;
    // Newton-Raphson in fixed-point.
    // We want sqrt(value) in fixed-point where value is 24.8.
    // So actual = sqrt(v/256) * 256 = sqrt(v * 256).
    std::int64_t v256 = static_cast<std::int64_t>(value) << FIXED_SHIFT;
    std::int64_t x = value > FIXED_ONE ? (static_cast<std::int64_t>(value)) : FIXED_ONE;
    for (int i = 0; i < 16; ++i) {
        if (x == 0) break;
        std::int64_t next = (x + v256 / x) >> 1;
        if (next == x) break;
        x = next;
    }
    return static_cast<Fixed>(x);
}

Fixed fx_sin(int angle_bin256) {
    return sin_table().values[angle_bin256 & 0xff];
}

Fixed fx_cos(int angle_bin256) {
    return sin_table().values[(angle_bin256 + 64) & 0xff];
}

Fixed fx_distance(const FixedVec2& a, const FixedVec2& b) {
    Fixed dx = a.x - b.x;
    Fixed dy = a.y - b.y;
    std::int64_t d2 = (static_cast<std::int64_t>(dx) * dx + static_cast<std::int64_t>(dy) * dy) >> FIXED_SHIFT;
    return fx_sqrt(static_cast<Fixed>(d2));
}

}  // namespace mythical
