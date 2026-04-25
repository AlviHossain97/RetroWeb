# Full C++ And GBA Port Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the first buildable shared C++ core, desktop executable shell, and standalone GBA project shell for the full-parity Mythical port.

**Architecture:** Start with deterministic gameplay contracts in `cpp_core`, then connect a desktop console executable in `cpp_port`, and a GBA project skeleton in `gba_project` that compiles the same shared-core sources. The first phase implements campaign, inventory, save, map gating, and combat contracts with tests before adding broader gameplay systems.

**Tech Stack:** C++17, CMake for desktop/core builds, a small no-dependency C++ test runner, and a devkitARM/libtonc-compatible GBA Makefile.

---

## File Structure

- Create `cpp_core/include/mythical/core/*.hpp` for portable public APIs.
- Create `cpp_core/src/*.cpp` for portable implementations.
- Create `cpp_core/tests/*.cpp` for no-dependency test executables.
- Create `cpp_port/CMakeLists.txt` and `cpp_port/src/main.cpp` for the desktop executable.
- Create `gba_project/Makefile`, `gba_project/source/main.cpp`, and `gba_project/include/gba_platform.hpp` for the handheld project shell.
- Create top-level `CMakeLists.txt` to build the core tests and desktop executable.
- Create `docs/CPP_GBA_PORT.md` with build and target notes.

## Task 1: Portable Core Scaffold And Campaign Tests

**Files:**
- Create: `CMakeLists.txt`
- Create: `cpp_core/CMakeLists.txt`
- Create: `cpp_core/include/mythical/core/campaign.hpp`
- Create: `cpp_core/src/campaign.cpp`
- Create: `cpp_core/tests/test_campaign.cpp`

- [ ] **Step 1: Write the failing test**

```cpp
#include "mythical/core/campaign.hpp"

#include <cstdlib>
#include <iostream>

static void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << "\n";
        std::exit(1);
    }
}

int main() {
    mythical::Campaign campaign;
    require(campaign.world_stage() == 1, "new campaign starts at stage 1");
    require(campaign.entry_map() == "village", "stage 1 entry map is village");
    require(!campaign.is_stage_unlocked(2), "stage 2 starts locked");

    const auto next = campaign.on_boss_defeated("dark_golem");
    require(next.has_value(), "dark golem defeat unlocks next stage");
    require(*next == 2, "dark golem unlocks stage 2");
    require(campaign.world_stage() == 2, "world stage updates to 2");
    require(campaign.current_form() == "hero", "stage 2 unlocks hero form");
    require(campaign.entry_map() == "ruins_approach", "stage 2 entry map is ruins approach");

    const auto final_next = campaign.on_boss_defeated("mythic_sovereign");
    require(!final_next.has_value(), "final boss has no next stage");
    require(campaign.is_final_stage_complete(), "final boss completes campaign");

    return 0;
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cmake -S . -B build/cpp && cmake --build build/cpp --target mythical_core_tests`

Expected: configuration or compile fails because `Campaign` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implement `Campaign` with stage metadata for the three shipped campaign stages and boss routing for `dark_golem`, `gravewarden`, and `mythic_sovereign`.

- [ ] **Step 4: Run test to verify it passes**

Run: `ctest --test-dir build/cpp --output-on-failure`

Expected: `test_campaign` passes.

## Task 2: Inventory, Equipment, Hotbar, And Wallet Contracts

**Files:**
- Create: `cpp_core/include/mythical/core/items.hpp`
- Create: `cpp_core/include/mythical/core/inventory.hpp`
- Create: `cpp_core/src/items.cpp`
- Create: `cpp_core/src/inventory.cpp`
- Create: `cpp_core/tests/test_inventory.cpp`

- [ ] **Step 1: Write the failing test**

```cpp
#include "mythical/core/inventory.hpp"

#include <cstdlib>
#include <iostream>

static void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << "\n";
        std::exit(1);
    }
}

int main() {
    mythical::Inventory inventory;
    require(inventory.add("old_sword", 1), "can add old sword");
    require(inventory.add("health_potion", 3), "can add stacked potions");
    require(inventory.count("health_potion") == 3, "potion count is tracked");
    require(inventory.equip("old_sword"), "weapon can be equipped");
    require(inventory.equipped_weapon().has_value(), "equipped weapon exists");
    require(inventory.equipped_weapon()->id == "old_sword", "old sword is equipped");
    require(inventory.set_hotbar(0, "health_potion"), "can assign potion to hotbar");
    require(inventory.hotbar_item(0).has_value(), "hotbar item exists");
    require(inventory.remove("health_potion", 1), "can consume one potion");
    require(inventory.count("health_potion") == 2, "potion count decrements");
    inventory.wallet().add(25);
    require(inventory.wallet().coins() == 25, "wallet stores coins");
    return 0;
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cmake --build build/cpp --target test_inventory`

Expected: compile fails because inventory APIs do not exist.

- [ ] **Step 3: Write minimal implementation**

Implement a fixed-size inventory model with item definitions for the 48 generated item IDs, equipment slots, nine hotbar slots, and a coin wallet.

- [ ] **Step 4: Run test to verify it passes**

Run: `ctest --test-dir build/cpp --output-on-failure`

Expected: campaign and inventory tests pass.

## Task 3: Map Registry, Stage Gates, And Save Contract

**Files:**
- Create: `cpp_core/include/mythical/core/maps.hpp`
- Create: `cpp_core/include/mythical/core/save.hpp`
- Create: `cpp_core/src/maps.cpp`
- Create: `cpp_core/src/save.cpp`
- Create: `cpp_core/tests/test_world_save.cpp`

- [ ] **Step 1: Write the failing test**

```cpp
#include "mythical/core/campaign.hpp"
#include "mythical/core/maps.hpp"
#include "mythical/core/save.hpp"

#include <cstdlib>
#include <iostream>

static void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << "\n";
        std::exit(1);
    }
}

int main() {
    mythical::Campaign campaign;
    const auto maps = mythical::MapRegistry::shipped();
    require(maps.size() == 6, "six shipped maps are registered");
    require(maps.can_enter("village", campaign), "village is open at start");
    require(!maps.can_enter("ruins_approach", campaign), "ruins are gated before stage 2");
    campaign.on_boss_defeated("dark_golem");
    require(maps.can_enter("ruins_approach", campaign), "ruins unlock after boss 1");

    mythical::SaveState state;
    state.campaign = campaign;
    state.current_map = "ruins_approach";
    state.player_x = 12;
    state.player_y = 18;
    const auto bytes = mythical::pack_save(state);
    const auto restored = mythical::unpack_save(bytes);
    require(restored.has_value(), "save round trip succeeds");
    require(restored->campaign.world_stage() == 2, "campaign stage survives save");
    require(restored->current_map == "ruins_approach", "map survives save");
    return 0;
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cmake --build build/cpp --target test_world_save`

Expected: compile fails because map and save APIs do not exist.

- [ ] **Step 3: Write minimal implementation**

Implement the six shipped maps, stage gate checks, binary save magic/version, packed campaign fields, map ID, and player tile position.

- [ ] **Step 4: Run test to verify it passes**

Run: `ctest --test-dir build/cpp --output-on-failure`

Expected: campaign, inventory, and world/save tests pass.

## Task 4: Combat And Boss Routing Slice

**Files:**
- Create: `cpp_core/include/mythical/core/combat.hpp`
- Create: `cpp_core/src/combat.cpp`
- Create: `cpp_core/tests/test_combat.cpp`

- [ ] **Step 1: Write the failing test**

```cpp
#include "mythical/core/combat.hpp"

#include <cstdlib>
#include <iostream>

static void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << "\n";
        std::exit(1);
    }
}

int main() {
    mythical::Actor player{"player", 30, 30, 6, 2};
    mythical::Actor slime{"slime", 8, 8, 2, 0};
    const auto result = mythical::attack(player, slime);
    require(result.damage == 8, "attack combines base attack and weapon power");
    require(slime.hp == 0, "target hp reaches zero");
    require(slime.is_defeated(), "target is defeated");
    return 0;
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cmake --build build/cpp --target test_combat`

Expected: compile fails because combat APIs do not exist.

- [ ] **Step 3: Write minimal implementation**

Implement `Actor`, defense-clamped damage, defeat checks, and attack results.

- [ ] **Step 4: Run test to verify it passes**

Run: `ctest --test-dir build/cpp --output-on-failure`

Expected: all core tests pass.

## Task 5: Desktop Executable Shell

**Files:**
- Create: `cpp_port/CMakeLists.txt`
- Create: `cpp_port/src/main.cpp`
- Modify: `CMakeLists.txt`

- [ ] **Step 1: Write the failing smoke test**

Add a CTest entry that runs `mythical_cpp --smoke` and expects exit code 0.

- [ ] **Step 2: Run smoke test to verify it fails**

Run: `ctest --test-dir build/cpp --output-on-failure -R mythical_cpp_smoke`

Expected: executable target does not exist.

- [ ] **Step 3: Write minimal implementation**

Implement a console desktop executable that starts the shared core, prints current campaign/map/inventory status, supports `--smoke`, and exits successfully.

- [ ] **Step 4: Run smoke test to verify it passes**

Run: `ctest --test-dir build/cpp --output-on-failure -R mythical_cpp_smoke`

Expected: smoke test passes.

## Task 6: GBA Project Shell Using Shared Core

**Files:**
- Create: `gba_project/Makefile`
- Create: `gba_project/include/gba_platform.hpp`
- Create: `gba_project/source/main.cpp`
- Create: `gba_project/README.md`

- [ ] **Step 1: Write project files**

Add a Makefile that uses `$(DEVKITARM)/bin/arm-none-eabi-g++` when available, includes `../cpp_core/include`, compiles selected shared-core sources, and fails clearly when `DEVKITARM` is not set.

- [ ] **Step 2: Run GBA build smoke**

Run: `make -C gba_project`

Expected on machines without devkitARM: fails with `DEVKITARM is not set`. Expected on configured machines: produces `build/mythical_gba.elf`.

## Task 7: Port Documentation

**Files:**
- Create: `docs/CPP_GBA_PORT.md`

- [ ] **Step 1: Write build docs**

Document CMake configuration, test commands, desktop smoke execution, GBA toolchain requirement, and the phase-1 parity scope.

- [ ] **Step 2: Verify commands**

Run all locally available commands and record any missing toolchains.
