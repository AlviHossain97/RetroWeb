#include "core/config.h"
#include "core/wave_manager.h"

#include <cassert>
#include <cstdio>

void test_wave_generation() {
    cfg::WaveDef waves[cfg::TOTAL_WAVES];
    cfg::generate_waves(waves);

    assert(waves[0].entry_count >= 1);
    assert(waves[0].entries[0].type == EnemyType::Goblin);
    assert(waves[0].entries[0].count == 6);

    assert(waves[4].has_titan);
    assert(waves[9].has_titan);
    assert(waves[14].has_titan);
    assert(waves[19].has_titan);

    bool found_titan = false;
    for (int i = 0; i < waves[19].entry_count; ++i) {
        if (waves[19].entries[i].type == EnemyType::Titan) {
            assert(waves[19].entries[i].count == 2);
            found_titan = true;
        }
    }
    assert(found_titan);

    std::printf("PASS: test_wave_generation\n");
}

void test_all_20_waves_defined() {
    cfg::WaveDef waves[cfg::TOTAL_WAVES];
    cfg::generate_waves(waves);
    for (int w = 0; w < cfg::TOTAL_WAVES; ++w) {
        assert(waves[w].entry_count > 0);
        for (int e = 0; e < waves[w].entry_count; ++e) {
            assert(waves[w].entries[e].count > 0);
        }
    }
    std::printf("PASS: test_all_20_waves_defined\n");
}

int main() {
    test_wave_generation();
    test_all_20_waves_defined();
    std::printf("All wave tests passed.\n");
    return 0;
}
