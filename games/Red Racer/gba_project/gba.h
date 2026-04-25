#ifndef GBA_H
#define GBA_H

// Type Definitions
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef volatile u8 vu8;
typedef volatile u16 vu16;
typedef volatile u32 vu32;
typedef signed char s8;
typedef signed short s16;
typedef signed int s32;
typedef volatile s8 vs8;
typedef volatile s16 vs16;
typedef volatile s32 vs32;

// Memory Map
#define MEM_IO 0x04000000
#define MEM_PALETTE 0x05000000
#define MEM_VRAM 0x06000000
#define MEM_SRAM 0x0E000000

// Video Registers
#define REG_DISPCNT (*(vu16 *)(MEM_IO + 0x0000))
#define REG_VCOUNT (*(vu16 *)(MEM_IO + 0x0006))

// Display Control Flags
#define MODE_3 0x0003
#define MODE_4 0x0004
#define BG2_ENABLE 0x0400
#define SHOW_FRAME1 0x0010

// Video Memory
#define VRAM ((vu16 *)MEM_VRAM)
#define PALETTE ((vu16 *)MEM_PALETTE)

// SRAM Memory (Save RAM - 64KB)
#define SRAM ((vu8 *)MEM_SRAM)
#define SRAM_MAGIC 0x52524752 // "RRGR"
#define SAVE_VERSION 4

// Screen Dimensions
#define SCREEN_WIDTH 240
#define SCREEN_HEIGHT 160

// Colors (15-bit BGR)
#define RGB15(r, g, b) ((r) | ((g) << 5) | ((b) << 10))

// Mode 4 Double Buffering
extern u16 *vid_page;

// Input Registers
#define REG_KEYINPUT (*(vu16 *)(MEM_IO + 0x0130))

// Keys
#define KEY_A 0x0001
#define KEY_B 0x0002
#define KEY_SELECT 0x0004
#define KEY_START 0x0008
#define KEY_RIGHT 0x0010
#define KEY_LEFT 0x0020
#define KEY_UP 0x0040
#define KEY_DOWN 0x0080
#define KEY_R 0x0100
#define KEY_L 0x0200

#define KEY_DOWN_NOW(key) (~(REG_KEYINPUT) & key)

// ---------------------------------------------------------------------------
// Game Constants & Structs
// ---------------------------------------------------------------------------

#define NUM_CARS 14
#define NUM_MODES 9

// Enemy Behaviors
#define BEHAVIOR_NORMAL 0
#define BEHAVIOR_LANE_DRIFTER 1
#define BEHAVIOR_SUDDEN_BRAKER 2
#define BEHAVIOR_SPEEDER 3
#define BEHAVIOR_WEAVER 4
#define BEHAVIOR_CHAOS 5
#define BEHAVIOR_BLOCKER 6

// Car definition — central data model for all selectable cars.
// Ordered by unlock_score for progression (starters first, endgame last).
typedef struct {
  char name[12];
  u8 sprite_idx;    // Index into cars_normal/left/right sprite arrays
  u8 color_idx;     // UI accent palette index
  u32 unlock_score; // 0 = starter car, >0 = score threshold to unlock
  int top_speed;    // MPH — affects scroll speed cap
  int accel;        // 0-100 — forward acceleration rating
  int handling;     // 0-100 — lateral steering response
  int braking;      // 0-100 — brake effectiveness
  int fuel_eff;     // 0-100 — fuel efficiency (100=best, low=drains fast)
  float drag;       // Air resistance factor
  float grip;       // Lateral grip factor
  int weight;       // 0-100 — collision resilience
  int boost_pct;    // Boost gain multiplier percent (100=1.0x)
} CarDef;

// Road definition — includes per-road playable bounds and gameplay modifiers.
// play_left/play_right define the GAMEPLAY drivable area (may be narrower
// than the VISUAL rendering area of ROAD_LEFT..ROAD_RIGHT).
typedef struct {
  char name[16];
  int friction;        // Surface grip (0-100)
  int traffic_density; // 0-100
  int risk_factor;     // Base score multiplier
  float spawn_rate_mult;
  int play_left;       // Gameplay left boundary (x pixel)
  int play_right;      // Gameplay right boundary (x pixel)
  int reward_pct;      // Score reward multiplier percent (100=1.0x)
  int drain_pct;       // Fuel drain multiplier percent (100=1.0x)
  int speed_pct;       // Speed cap multiplier percent (100=1.0x)
} RoadStats;

// Mode rules — const data defining per-mode gameplay behavior.
typedef struct {
  char short_name[6];
  u8 risk_mult_pct;    // Risk point multiplier (100=1x, 135=1.35x)
  u8 spawn_rate_pct;   // Spawn rate modifier (100=1x, lower=faster)
  u8 fuel_drain;       // 1=fuel drains, 0=no fuel drain
  u8 one_hit_death;    // 1=any collision kills
  u8 use_timer;        // 1=countdown mode
  u8 spawn_items;      // 1=spawn coins/fuel/repair
  u8 spawn_nitro;      // 1=spawn nitro/boost pickups
  u8 use_focus;        // 1=zen focus meter
  u8 risk_active;      // 1=risk/combo system active
  u8 padding;
} ModeRules;

// Input State
typedef struct {
  u16 held;
  u16 pressed;
  u16 released;
} InputState;

// ---------------------------------------------------------------------------
// Save / Progression Data Structures
// ---------------------------------------------------------------------------
// Designed for future external DB sync:
// - All fields are fixed-size, deterministic layout
// - IDs are stable indices into car_defs[]/road_stats[]
// - RunRecord captures per-run telemetry for history export
// - SaveData is self-describing (magic + version) for safe migration

#define MAX_RECENT_RUNS 8

// Per-run record stored in the recent-runs ring buffer.
// [persistent] — written to SRAM as part of SaveData.
typedef struct {
  u32 score;            // Final score for this run
  u16 risk_score;       // Risk points scored this run
  u16 duration_frames;  // Run length in frames (~60fps)
  u8 car_id;            // Index into car_defs[]
  u8 road_id;           // Index into road_stats[]
  u8 game_mode;         // Game mode index
  u8 flags;             // bit 0: new_unlock, bit 1: new_best
} RunRecord;

// Persistent save data — stored in SRAM. ~240 bytes, well within 64KB.
typedef struct {
  u32 magic;                          // SRAM_MAGIC
  u32 version;                        // SAVE_VERSION
  u32 high_score;                     // Global best score
  u16 cars_unlocked;                  // Bitmask: bit N = car_defs[N] unlocked
  u8 selected_car;                    // Last selected car index
  u8 selected_road;                   // Last selected road index
  u8 difficulty;                      // DIFF_NORMAL/HARD/EASY
  u8 game_mode;                       // Selected game mode
  u8 level;                           // Player level (1-255)
  u8 padding1;
  u32 xp;                             // Lifetime XP
  u32 total_runs;                     // Lifetime run counter
  u32 total_playtime_frames;          // Lifetime playtime (frames)
  u32 per_car_best[NUM_CARS];         // Best score per car
  u32 per_mode_best[NUM_MODES];       // Best score per mode
  RunRecord recent_runs[MAX_RECENT_RUNS]; // Ring buffer
  u8 recent_run_head;                 // Next write index in ring buffer
  u8 recent_run_count;                // Valid entries (0..MAX_RECENT_RUNS)
  u8 reserved[6];                     // Future use
  u32 checksum;                       // Simple byte-sum
} SaveData;

// Runtime-only session stats — resets each boot. Not saved to SRAM.
// [runtime] — useful for later DB sync as a "session summary" export.
typedef struct {
  u32 session_frame_count;
  u32 runs_this_session;
  u32 best_score_session;
  u32 total_score_session;
  u32 run_start_frame;
} SessionData;

// ---------------------------------------------------------------------------
// Hardware Helpers
// ---------------------------------------------------------------------------

static inline void waitForVBlank() {
  while (REG_VCOUNT >= 160)
    ;
  while (REG_VCOUNT < 160)
    ;
}

static inline void flipPage() {
  if (REG_DISPCNT & SHOW_FRAME1) {
    REG_DISPCNT &= ~SHOW_FRAME1;
    vid_page = (u16 *)0x600A000;
  } else {
    REG_DISPCNT |= SHOW_FRAME1;
    vid_page = (u16 *)0x6000000;
  }
}

#endif
