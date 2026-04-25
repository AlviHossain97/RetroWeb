#include "mythical/core/fixed.hpp"

#include <cstdlib>
#include <iostream>

static void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << "\n";
        std::exit(1);
    }
}

int main() {
    using namespace mythical;

    require(fx_from_int(3) == 3 * FIXED_ONE, "from_int");
    require(fx_to_int(fx_from_int(7)) == 7, "round trip int");
    require(fx_mul(fx_from_int(4), fx_from_int(5)) == fx_from_int(20), "mul");
    require(fx_div(fx_from_int(20), fx_from_int(4)) == fx_from_int(5), "div");
    require(fx_to_int(fx_sqrt(fx_from_int(16))) == 4, "sqrt(16)=4");
    require(fx_to_int(fx_sqrt(fx_from_int(81))) == 9, "sqrt(81)=9");

    // sin(0)=0, sin(64)=1, cos(0)=1
    require(fx_sin(0) == 0, "sin 0");
    require(fx_sin(64) == FIXED_ONE, "sin 90deg = 1");
    require(fx_cos(0) == FIXED_ONE, "cos 0 = 1");

    const FixedVec2 a = FixedVec2::from_ints(0, 0);
    const FixedVec2 b = FixedVec2::from_ints(3, 4);
    require(fx_to_int(fx_distance(a, b)) == 5, "3-4-5 triangle distance");

    return 0;
}
