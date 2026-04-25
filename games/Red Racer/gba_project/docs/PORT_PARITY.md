# Port Parity: Python -> GBA

This document tracks the feature parity between the original Python/Pygame version and the GBA port.

| Python Feature | GBA Equivalent | Status | Notes | Where Implemented |
| :--- | :--- | :--- | :--- | :--- |
| **Core Gameplay** | | | | |
| Left/Right Steering | D-Pad Left/Right | ✅ Done | Physics-based accell/friction | `main.c` |
| Accelerate/Brake | A/B Buttons | ✅ Done | A=Gas, B=Brake | `main.c` |
| Fuel System | Fuel Gauge & Drain | ✅ Done | `Fuel` float, drain rate | `main.c` |
| Health/Damage | Health Bar | ✅ Done | Collision damage | `main.c` |
| Infinite Scrolling | Background Scroll | ✅ Done | Mode 4 vertical scroll | `main.c` |
| **Entities** | | | | |
| Player Car | Sprite | ✅ Done | 16x32 sprite | `main.c` |
| Traffic (Enemies) | Sprites | ✅ Done | Pool of entities | `main.c` |
| Coins | Sprite | ✅ Done | Yellow orb | `main.c` |
| Fuel | Sprite | ✅ Done | Cyan orb | `main.c` |
| Repair Kit | Sprite | ✅ Done | White orb | `main.c` |
| Nitro | Sprite | ✅ Done | Blue orb | `main.c` |
| **Traffic AI** | | | | |
| "Normal" Behavior | Constant Speed | ✅ Done | | `main.c` |
| "Weaver" Behavior | Sine Wave / Lane Change | ✅ Done | `weave_dir` logic | `main.c` |
| "Speeder" Behavior | High Speed | ✅ Done | Fast relative velocity | `main.c` |
| "Braker" Behavior | Sudden Stop | ✅ Done | Timer-based slow | `main.c` |
| "Lane Drifter" | Slow Lateral Move | ✅ Done | | `main.c` |
| "Blocker" Behavior | Front drift / slow | ✅ Done | | `main.c` |
| **Game Modes** | | | | |
| Classic Endless | Standard Loop | ✅ Done | Default mode | `main.c` |
| High-Risk | High Traffic/Speed | ✅ Done | Array mapping | `main.c` |
| Time Attack | Fixed Time/Seed | ✅ Done | Array mapping | `main.c` |
| Hardcore (1 Life) | 1 HP / Permadeath | ✅ Done | Array mapping | `main.c` |
| Fuel Crisis | High Fuel Drain | ✅ Done | Array mapping | `main.c` |
| Boost Rush | High Boost Gain | ✅ Done | Array mapping | `main.c` |
| Endurance | Low Resources | ✅ Done | Array mapping | `main.c` |
| Daily Run | Deterministic Seed | ❌ Todo | Needs date hashing | |
| Zen Mode | No Traffic/Die | ✅ Done | Array mapping | `main.c` |
| **Risk Scoring** | | | | |
| Near Miss | Distance Check | ✅ Done | Fixed-point distance | `main.c` |
| Wrong Lane | Position Check | ✅ Done | `x < ROAD_CENTER` | `main.c` |
| High Speed Overtake | Speed + Pass | ✅ Done | `dy > CAR_H` check | `main.c` |
| Combo Meter | Float Timer | ✅ Done | Decay logic | `main.c` |
| Thread the Gap | Double Near Miss | ✅ Done | `nm_left && nm_right` | `main.c` |
| **Progression** | | | | |
| XP / Level Up | SRAM Data | ✅ Done | Save struct | `main.c` |
| Unlock Cars | Bitmask/Flags | ✅ Done | `unlock_score` | `main.c` |
| Upgrades (Speed/Etc) | Stat Multipliers | ❌ Todo | Apply to `CarStats` | |
| Cosmetics | Palette Swap | ❌ Todo | `start_palette_idx` | |
| **UI / HUD** | | | | |
| Speedometer | Text Draw | ✅ Done | `drawInt` used | `main.c` |
| Combo Bar | Rect Draw | ✅ Done | `drawRect` | `main.c` |
| Boost Bar | Rect Draw | ✅ Done | `drawRect` | `main.c` |
| Clean Fonts | Bitmap Font | ⚠️ Partial | Basic 8x8 font used | `gba.h` |
| Menus | State Machine | ⚠️ Partial | Basic Select/Play | `main.c` |
| **Audio** | | | | |
| Music | Tracker/PCM | ❌ Todo | Silence currently | |
| SFX | DirectSound | ❌ Todo | Silence currently | |
| **Visual Effects** | | | | |
| Screen Shake | scroll_x offset | ❌ Todo | `REG_BG2HOFS` | |
| Particles | Pixel particles | ✅ Done | `spawnParticle` | `main.c` |
| Hit Stop | Frame Sleep | ❌ Todo | Freeze loop | |
| Speed Lines | Starfield/Lines | ❌ Todo | | |
