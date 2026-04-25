#include "assets.h"
#include "gba.h"

// ---------------------------------------------------------------------------
// Entity Struct
// ---------------------------------------------------------------------------
typedef struct {
  float x, y;
  int w, h;
  int type;    // 0=Enemy, 1=Coin, 2=Fuel, 3=Repair, 4=Nitro
  int subtype;
  int active;
  float speed_y;
  int behavior;
  float lateral_vel;
  float target_x;
  int timer;
  int weave_dir;
  u8 nm_scored; // 1 = near-miss already awarded for this entity
} Entity;

#define MAX_ENTITIES 12
// Visual rendering bounds (always the same, full road texture strip)
#define ROAD_LEFT 40
#define ROAD_RIGHT 200
#define ENABLE_DEBUG_OVERLAY 0
#define ENABLE_PARTICLES 1

// Near-miss detection thresholds
#define NEAR_MISS_DIST 22
#define NEAR_MISS_SPEED 3.0f

// Time attack duration
#define TIME_ATTACK_FRAMES (90 * 60)

// XP per level
#define XP_PER_LEVEL 200

// ---------------------------------------------------------------------------
// Car Definitions — ordered by unlock progression
// ---------------------------------------------------------------------------
const CarDef car_defs[NUM_CARS] = {
  // name       spr col unlock   spd  acc  hdl  brk  fuel  drag   grip   wgt  bst
  {"Ferrari",  0,  2, 0     , 211, 82, 78, 75,  95, 0.95f, 1.02f, 50, 100},
  {"Supra",  8,  2, 0     , 155, 55, 85, 80, 114, 1.05f, 1.10f, 55,  95},
  {"Audi",  3,  8, 1500  , 205, 70, 82, 78, 110, 0.96f, 1.06f, 58,  95},
  {"Corvette",  5,  2, 500   , 194, 72, 70, 72, 105, 0.98f, 0.98f, 60, 100},
  {"Lotus", 10,  5, 3000  , 180, 65, 95, 88, 108, 0.99f, 1.15f, 35, 105},
  {"911", 11,  8, 12000 , 205, 85, 92, 90,  92, 0.95f, 1.12f, 42, 108},
  {"Aston",  9,  3, 8000  , 211, 78, 75, 74,  98, 0.96f, 1.02f, 55, 102},
  {"Mercedes",  4,  8, 5000  , 202, 75, 68, 70,  95, 0.97f, 1.00f, 72, 100},
  {"Viper", 12,  4, 18000 , 206, 80, 58, 62,  85, 0.98f, 0.92f, 78, 110},
  {"Lambo",  1,  5, 35000 , 211, 86, 76, 72,  88, 0.94f, 1.08f, 52, 125},
  {"McLaren",  2,  6, 25000 , 208, 88, 80, 82,  90, 0.93f, 1.02f, 40, 105},
  {"Zonda", 13,  8, 50000 , 217, 84, 82, 78,  85, 0.94f, 1.04f, 32, 114},
  {"CCX",  7,  8, 70000 , 245, 90, 65, 68,  82, 0.92f, 0.95f, 30, 120},
  {"Veyron",  6,  4, 99000 , 253, 95, 60, 65,  75, 0.90f, 1.10f, 80, 110},
};

// Road definitions with per-road gameplay bounds and modifiers
// play_left/play_right: gameplay drivable area (subset of visual 40-200)
const RoadStats road_stats[] = {
  //  name              fric traf risk spawn  pL  pR  rew  drn  spd
  {"City Express", 100, 50, 10, 1.00f, 78, 162, 100, 100, 100 },
  {"Industrial", 100, 50, 11, 0.84f, 87, 153, 108, 112, 100 },
  {"Coastal Run", 100, 50, 10, 0.94f, 83, 157, 110, 102, 100 },
  {"Night Circuit", 100, 50, 12, 0.88f, 66, 174, 118, 120, 100 },
};
#define NUM_ROADS 4

// Game mode rules — const data defining per-mode gameplay behavior
const ModeRules mode_rules[NUM_MODES] = {
  // short  risk% spawn% fuel 1h time itm nit foc act pad
  {"CLASS", 100,  100,   1,  0,    0,   1,   1,   0,   1,   0},
  {"HIGH-", 135,   85,   1,  0,    0,   0,   1,   0,   1,   0},
  {"TIME ", 100,   78,   1,  0,    1,   1,   1,   0,   1,   0},
  {"HARDC", 150,   85,   0,  1,    0,   0,   0,   0,   1,   0},
  {"FUEL ", 110,  100,   1,  0,    0,   1,   1,   0,   1,   0},
  {"BOOST", 140,   90,   1,  0,    0,   1,   1,   0,   1,   0},
  {"ENDUR", 120,  100,   1,  0,    0,   1,   1,   0,   1,   0},
  {"DAILY", 100,  100,   1,  0,    0,   1,   1,   0,   1,   0},
  {"ZEN",  50,  125,   0,  0,    0,   1,   0,   1,   0,   0},
};

static const char *mode_names[] = {
  "Classic Endless", "High Risk", "Time Attack", "Hardcore", "Fuel Crisis", "Boost Rush", "Endurance", "Daily Run", "Zen"
};

// ---------------------------------------------------------------------------
// Game States & Enums
// ---------------------------------------------------------------------------
enum GameState {
  STATE_MENU,
  STATE_PLAY,
  STATE_GAMEOVER,
  STATE_INSTRUCTIONS,
  STATE_GARAGE,
  STATE_ROAD_SELECT,
  STATE_RECORDS,
  STATE_RUN_SUMMARY
};

enum Difficulty { DIFF_NORMAL, DIFF_HARD, DIFF_EASY };
enum GameMode { 
  MODE_CLASSIC, MODE_HIGH_RISK, MODE_TIME_ATTACK, MODE_HARDCORE, 
  MODE_FUEL_CRISIS, MODE_BOOST_RUSH, MODE_ENDURANCE, MODE_DAILY_RUN, MODE_ZEN 
};

// ---------------------------------------------------------------------------
// Globals
// ---------------------------------------------------------------------------
int current_car_idx = 0;
int current_road_idx = 0;
int pending_car_idx = 0;
int pending_road_idx = 0;
int difficulty = DIFF_NORMAL;
int game_mode = MODE_CLASSIC;
int records_scroll = 0;

// Road preview cache
#define PREVIEW_W 200
#define PREVIEW_H 100
#define PREVIEW_SHORTS ((PREVIEW_W * PREVIEW_H) / 2)
u16 road_preview_cache[PREVIEW_SHORTS];
int road_preview_cached_idx = -1;

// Menu held-key repeat
#define REPEAT_INITIAL_DELAY 18
#define REPEAT_INTERVAL 6
int nav_repeat_timer = 0;
int nav_repeat_active = 0;

// Health (easy mode)
#define PLAYER_MAX_HEALTH 100
#define COLLISION_DAMAGE 30
#define REPAIR_HEAL_AMOUNT 15
int player_health = PLAYER_MAX_HEALTH;

// Player physics
int player_x = 120;
int player_y = 120;
float player_x_f = 120.0f;
float vel_x = 0.0f;
float scroll_y = 0.0f;
float speed = 2.0f;
int score = 0;
int high_score = 0;
float fuel = 100.0f;

// Entities
Entity entities[MAX_ENTITIES];
int spawn_timer = 0;

// Particles
#define MAX_PARTICLES 20
typedef struct {
  float x, y, vx, vy;
  int life, color_idx, active;
} Particle;
Particle particles[MAX_PARTICLES];

// Game state
enum GameState current_state = STATE_MENU;
int selected_btn = 0;

// Run summary state
int summary_new_best = 0;
int summary_new_unlocks = 0;
u16 summary_unlock_mask = 0;
int summary_run_score = 0;
int summary_risk_score = 0;
u32 summary_run_duration = 0;

// Frame counter
u32 frame_counter = 0;

// Risk / Combo system
int combo_meter = 0;       // 0-100
int combo_decay_timer = 0;
int score_multiplier = 1;  // 1-6x, derived from combo_meter
int risk_score = 0;        // Risk points this run
int wrong_lane_timer = 0;

// Boost system (replaces old nitro_timer)
int boost_meter = 0;       // 0-100
int boost_drain_tick = 0;  // For half-rate drain in sustain mode
int boost_active = 0;      // 0=off, 1=sustain (L), 2=burst (R)
float boost_mult = 1.0f;   // Applied to eff_speed

// Screen shake
int shake_timer = 0;

// Time attack countdown
int time_attack_remaining = 0;

// Zen focus meter
int zen_focus = 100;

// Video page
u16 *vid_page = (u16 *)0x600A000;

// RNG
u32 rand_seed = 1234;
u32 rand() {
  rand_seed = rand_seed * 1103515245 + 12345;
  return (rand_seed / 65536) % 32768;
}

// ---------------------------------------------------------------------------
// Input, Save, Session
// ---------------------------------------------------------------------------
InputState input;
SaveData save_data;
SessionData session;

// ---------------------------------------------------------------------------
// Road Bounds Helpers — centralized per-road gameplay boundaries
// ---------------------------------------------------------------------------

static inline int getRoadLeft(void) {
  return road_stats[current_road_idx].play_left;
}

static inline int getRoadRight(void) {
  return road_stats[current_road_idx].play_right;
}

int clampToRoad(int x, int obj_w) {
  int left = getRoadLeft();
  int right = getRoadRight();
  if (x < left) return left;
  if (x > right - obj_w) return right - obj_w;
  return x;
}

int randomRoadSpawnX(int obj_w) {
  int left = getRoadLeft() + 4;
  int right = getRoadRight() - 4 - obj_w;
  int range = right - left;
  if (range < 1) range = 1;
  return left + (rand() % range);
}

void clampEntityToRoad(Entity *e) {
  int left = getRoadLeft();
  int right = getRoadRight();
  if (e->x < left) { e->x = (float)left; e->weave_dir = 1; }
  if (e->x > right - e->w) { e->x = (float)(right - e->w); e->weave_dir = -1; }
}

// ---------------------------------------------------------------------------
// SRAM Save System (v3)
// ---------------------------------------------------------------------------

u32 calculate_checksum(const SaveData *data) {
  u32 sum = 0;
  const u8 *p = (const u8 *)data;
  int len = (int)sizeof(SaveData) - (int)sizeof(u32);
  for (int i = 0; i < len; i++) sum += p[i];
  return sum;
}

void savePersistentData() {
  save_data.magic = SRAM_MAGIC;
  save_data.version = SAVE_VERSION;
  save_data.checksum = calculate_checksum(&save_data);
  u8 *src = (u8 *)&save_data;
  volatile u8 *dst = SRAM;
  for (int i = 0; i < (int)sizeof(SaveData); i++) dst[i] = src[i];
}

void resetSaveData() {
  u8 *p = (u8 *)&save_data;
  for (int i = 0; i < (int)sizeof(SaveData); i++) p[i] = 0;
  save_data.magic = SRAM_MAGIC;
  save_data.version = SAVE_VERSION;
  save_data.cars_unlocked = 0x0003; // Supra + Corvette
  save_data.selected_car = 0;
  save_data.selected_road = 0;
  save_data.difficulty = DIFF_NORMAL;
  save_data.game_mode = MODE_CLASSIC;
  save_data.level = 1;
  save_data.xp = 0;
  savePersistentData();
}

void loadSaveData() {
  volatile u8 *src = SRAM;
  u8 *dst = (u8 *)&save_data;
  for (int i = 0; i < (int)sizeof(SaveData); i++) dst[i] = src[i];
  if (save_data.magic != SRAM_MAGIC ||
      save_data.version != SAVE_VERSION ||
      save_data.checksum != calculate_checksum(&save_data)) {
    resetSaveData();
  }
  high_score = (int)save_data.high_score;
  current_car_idx = save_data.selected_car;
  current_road_idx = save_data.selected_road;
  difficulty = save_data.difficulty;
  game_mode = save_data.game_mode;
  if (current_car_idx >= NUM_CARS) current_car_idx = 0;
  if (current_road_idx >= NUM_ROADS) current_road_idx = 0;
  if (game_mode >= NUM_MODES) game_mode = MODE_CLASSIC;
  pending_car_idx = current_car_idx;
  pending_road_idx = current_road_idx;
}

// ---------------------------------------------------------------------------
// Progression Helpers
// ---------------------------------------------------------------------------

int isCarUnlocked(int car_id) {
  if (car_id < 0 || car_id >= NUM_CARS) return 0;
  return (save_data.cars_unlocked >> car_id) & 1;
}

void unlockCar(int car_id) {
  if (car_id >= 0 && car_id < NUM_CARS)
    save_data.cars_unlocked |= (u16)(1 << car_id);
}

int updateUnlocksFromScore(int best_score) {
  int count = 0;
  summary_unlock_mask = 0;
  for (int i = 0; i < NUM_CARS; i++) {
    if (!isCarUnlocked(i) && (u32)best_score >= car_defs[i].unlock_score) {
      unlockCar(i);
      summary_unlock_mask |= (u16)(1 << i);
      count++;
    }
  }
  return count;
}

void addXP(int amount) {
  save_data.xp += (u32)amount;
  int threshold = (int)save_data.level * XP_PER_LEVEL;
  while ((int)save_data.xp >= threshold && save_data.level < 255) {
    save_data.xp -= (u32)threshold;
    save_data.level++;
    threshold = (int)save_data.level * XP_PER_LEVEL;
  }
}

void addRecentRun(int run_score, int r_score, int car_id, int road_id,
                  u32 duration, int mode, int flags_val) {
  RunRecord *rec = &save_data.recent_runs[save_data.recent_run_head];
  rec->score = (u32)run_score;
  rec->risk_score = (u16)(r_score > 65535 ? 65535 : r_score);
  rec->duration_frames = (u16)(duration > 65535 ? 65535 : duration);
  rec->car_id = (u8)car_id;
  rec->road_id = (u8)road_id;
  rec->game_mode = (u8)mode;
  rec->flags = (u8)flags_val;
  save_data.recent_run_head = (save_data.recent_run_head + 1) % MAX_RECENT_RUNS;
  if (save_data.recent_run_count < MAX_RECENT_RUNS) save_data.recent_run_count++;
}

void recordRunResult(int run_score, int r_score, int car_id, int road_id,
                     u32 duration) {
  int new_best = 0;
  int flags_val = 0;
  if ((u32)run_score > save_data.high_score) {
    save_data.high_score = (u32)run_score;
    high_score = run_score;
    new_best = 1;
    flags_val |= 0x02;
  }
  if (car_id >= 0 && car_id < NUM_CARS) {
    if ((u32)run_score > save_data.per_car_best[car_id])
      save_data.per_car_best[car_id] = (u32)run_score;
  }
  if (game_mode >= 0 && game_mode < NUM_MODES) {
    if ((u32)run_score > save_data.per_mode_best[game_mode])
      save_data.per_mode_best[game_mode] = (u32)run_score;
  }
  int newly_unlocked = updateUnlocksFromScore(high_score);
  if (newly_unlocked > 0) flags_val |= 0x01;
  addRecentRun(run_score, r_score, car_id, road_id, duration, game_mode, flags_val);
  addXP(run_score / 10);
  save_data.total_runs++;
  save_data.total_playtime_frames += duration;
  savePersistentData();

  summary_new_best = new_best;
  summary_new_unlocks = newly_unlocked;
  summary_run_score = run_score;
  summary_risk_score = r_score;
  summary_run_duration = duration;
}

void initSessionData() {
  session.session_frame_count = 0;
  session.runs_this_session = 0;
  session.best_score_session = 0;
  session.total_score_session = 0;
  session.run_start_frame = 0;
}

// ---------------------------------------------------------------------------
// Risk / Combo Helpers
// ---------------------------------------------------------------------------

void addRiskPoints(int base_points) {
  const ModeRules *mr = &mode_rules[game_mode];
  if (!mr->risk_active) return;
  int points = base_points * (int)mr->risk_mult_pct / 100;
  risk_score += points * score_multiplier;
  // Risk→boost conversion: ~7% of points = boost meter charge
  int charge = (base_points * 7) / 100;
  if (charge < 1 && base_points > 0) charge = 1;
  boost_meter += charge;
  if (boost_meter > 100) boost_meter = 100;
}

void triggerNearMiss(void) {
  combo_meter += 12;
  if (combo_meter > 100) combo_meter = 100;
  addRiskPoints(8);
}

void triggerOvertake(void) {
  combo_meter += 6;
  if (combo_meter > 100) combo_meter = 100;
  addRiskPoints(22);
}

void triggerThreadGap(void) {
  combo_meter += 10;
  if (combo_meter > 100) combo_meter = 100;
  addRiskPoints(22);
}

void updateComboDecay(void) {
  if (combo_meter > 0) {
    combo_decay_timer++;
    if (combo_decay_timer >= 5) { // ~12/sec decay
      combo_decay_timer = 0;
      combo_meter--;
    }
  }
  score_multiplier = (combo_meter / 20) + 1; // 1x at 0, 6x at 100
}

void triggerScreenShake(void) {
  shake_timer = 12; // ~0.2 sec
}

// ---------------------------------------------------------------------------
// Drawing Functions
// ---------------------------------------------------------------------------

void drawBackground() {
  int y_shift = (int)scroll_y % 160;
  int src_y = 160 - y_shift;
  if (src_y >= 160) src_y = 0;
  const u16 *src = roads[current_road_idx];
  int hw_start = ROAD_LEFT / 2;
  int hw_count = (ROAD_RIGHT - ROAD_LEFT) / 2;
  for (int y = 0; y < 160; y++) {
    const u16 *src_line = src + src_y * 120 + hw_start;
    u16 *dst_line = vid_page + y * 120 + hw_start;
    for (int i = 0; i < hw_count; i++) dst_line[i] = src_line[i];
    src_y++;
    if (src_y >= 160) src_y = 0;
  }
}

void drawSprite(int x, int y, const u16 *sprite_data, int w, int h) {
  x &= ~1;
  int w_shorts = w / 2;
  for (int j = 0; j < h; j++) {
    int screen_y = y + j;
    if (screen_y < 0 || screen_y >= 160) continue;
    u16 *dst_line = vid_page + (screen_y * 120);
    const u16 *src_line = sprite_data + (j * w_shorts);
    for (int i = 0; i < w_shorts; i++) {
      int sx = (x / 2) + i;
      if (sx >= 0 && sx < 120) {
        u16 pp = src_line[i];
        u8 p1 = pp & 0xFF;
        u8 p2 = (pp >> 8) & 0xFF;
        u16 bg = dst_line[sx];
        u8 b1 = bg & 0xFF;
        u8 b2 = (bg >> 8) & 0xFF;
        if (p1 != 0) b1 = p1;
        if (p2 != 0) b2 = p2;
        dst_line[sx] = (b2 << 8) | b1;
      }
    }
  }
}

#define C_BLACK 0
#define C_WHITE 1
#define C_RED 2
#define C_GREEN 3
#define C_BLUE 4
#define C_YELLOW 5
#define C_CYAN 6
#define C_PURPLE 7
#define C_GRAY 8

void fillScreen(int c) {
  u16 val = (c << 8) | c;
  for (int i = 0; i < 19200; i += 8) {
    vid_page[i+0]=val; vid_page[i+1]=val;
    vid_page[i+2]=val; vid_page[i+3]=val;
    vid_page[i+4]=val; vid_page[i+5]=val;
    vid_page[i+6]=val; vid_page[i+7]=val;
  }
}

void drawRect(int x, int y, int w, int h, int c) {
  for (int j = 0; j < h; j++) {
    int py = y + j;
    if (py < 0 || py >= 160) continue;
    for (int i = 0; i < w; i++) {
      int px = x + i;
      if (px < 0 || px >= 240) continue;
      int off = (py * 240 + px) / 2;
      u16 *dst = vid_page + off;
      if (px & 1) *dst = (*dst & 0x00FF) | (c << 8);
      else *dst = (*dst & 0xFF00) | c;
    }
  }
}

void drawChar(int x, int y, char c) {
  if (c < 0 || c > 127) return;
  const u16 *glyph = font_lookup[(int)c];
  if (glyph) drawSprite(x, y, glyph, 8, 8);
}

void drawText(int x, int y, const char *str) {
  while (*str) { drawChar(x, y, *str); x += 8; str++; }
}

void drawInt(int x, int y, int val) {
  char buf[12]; char *p = buf + 11; *p = 0;
  if (val <= 0) { drawText(x, y, "0"); return; }
  while (val > 0) { *--p = '0' + (val % 10); val /= 10; }
  drawText(x, y, p);
}

void drawStatBar(int x, int y, int w, int h, int value, int max_val, int color) {
  drawRect(x, y, w, h, C_GRAY);
  int fw = (value * w) / max_val;
  if (fw > w) fw = w;
  if (fw > 0) drawRect(x, y, fw, h, color);
}

// Vertical bar: fills from bottom up
void drawVBar(int x, int y, int w, int h, int value, int max_val, int color) {
  drawRect(x, y, w, h, C_GRAY);
  int fh = (value * h) / max_val;
  if (fh > h) fh = h;
  if (fh > 0) drawRect(x, y + h - fh, w, fh, color);
}

// ---------------------------------------------------------------------------
// Road Preview Helpers
// ---------------------------------------------------------------------------

static u8 samplePixel4(const u16 *bitmap, int x, int y) {
  u16 pair = bitmap[y * 120 + x / 2];
  return (x & 1) ? ((pair >> 8) & 0xFF) : (pair & 0xFF);
}

void rebuildRoadPreviewCache(int road_idx) {
  const u16 *road = roads[road_idx];
  for (int py = 0; py < PREVIEW_H; py++) {
    int sy = (py * 160) / PREVIEW_H;
    if (sy > 159) sy = 159;
    for (int px = 0; px < PREVIEW_W; px += 2) {
      int sx0 = (px * 240) / PREVIEW_W;
      int sx1 = ((px + 1) * 240) / PREVIEW_W;
      if (sx0 > 239) sx0 = 239;
      if (sx1 > 239) sx1 = 239;
      u8 p0 = samplePixel4(road, sx0, sy);
      u8 p1 = samplePixel4(road, sx1, sy);
      road_preview_cache[py * (PREVIEW_W / 2) + px / 2] = ((u16)p1 << 8) | p0;
    }
  }
  road_preview_cached_idx = road_idx;
}

void drawCachedRoadPreview(int dx, int dy) {
  dx &= ~1;
  for (int py = 0; py < PREVIEW_H; py++) {
    int sy = dy + py;
    if (sy < 0 || sy >= 160) continue;
    u16 *dr = vid_page + sy * 120 + dx / 2;
    const u16 *sr = road_preview_cache + py * (PREVIEW_W / 2);
    for (int i = 0; i < PREVIEW_W / 2; i++) dr[i] = sr[i];
  }
}

// ---------------------------------------------------------------------------
// Game Logic
// ---------------------------------------------------------------------------

void finalizeRun(void);

void initGame() {
  int rl = getRoadLeft();
  int rr = getRoadRight();
  player_x = (rl + rr) / 2 - CAR_W / 2;
  player_y = 120;
  player_x_f = (float)player_x;
  vel_x = 0.0f;
  score = 0;
  fuel = 100.0f;
  speed = 2.0f;
  if (difficulty == DIFF_HARD) speed *= 1.2f;
  player_health = PLAYER_MAX_HEALTH;
  spawn_timer = 0;
  scroll_y = 0.0f;
  for (int i = 0; i < MAX_ENTITIES; i++) entities[i].active = 0;
  for (int i = 0; i < MAX_PARTICLES; i++) particles[i].active = 0;
  session.run_start_frame = session.session_frame_count;

  // Reset per-run systems
  combo_meter = 0; combo_decay_timer = 0;
  score_multiplier = 1; risk_score = 0; wrong_lane_timer = 0;
  boost_meter = 50; boost_drain_tick = 0; boost_active = 0; boost_mult = 1.0f;
  shake_timer = 0;
  zen_focus = 100;
  time_attack_remaining = TIME_ATTACK_FRAMES;

  rand_seed = (u32)REG_VCOUNT;
  if (game_mode == MODE_TIME_ATTACK) rand_seed = 42; // Deterministic
}

void finalizeRun(void) {
  // Compute final score based on mode
  int final_score = score;
  if (game_mode == MODE_HIGH_RISK) final_score = risk_score;
  else final_score = score + risk_score;

  u32 duration = session.session_frame_count - session.run_start_frame;
  recordRunResult(final_score, risk_score, current_car_idx, current_road_idx, duration);
  session.runs_this_session++;
  session.total_score_session += (u32)final_score;
  if ((u32)final_score > session.best_score_session)
    session.best_score_session = (u32)final_score;
  summary_run_score = final_score;
  current_state = STATE_RUN_SUMMARY;
}

void spawnEntityType(int forced_type) {
  const ModeRules *mr = &mode_rules[game_mode];

  // Mode restrictions
  if (forced_type >= 1 && forced_type <= 3 && !mr->spawn_items) return;
  if (forced_type == 4 && !mr->spawn_nitro) return;

  int slot = -1;
  for (int i = 0; i < MAX_ENTITIES; i++) {
    if (!entities[i].active) { slot = i; break; }
  }
  if (slot == -1) return;

  Entity *e = &entities[slot];
  e->active = 1;
  e->timer = 0;
  e->behavior = BEHAVIOR_NORMAL;
  e->lateral_vel = 0;
  e->target_x = 0;
  e->weave_dir = (rand() % 2) ? 1 : -1;
  e->nm_scored = 0;

  if (forced_type == 0) {
    e->type = 0;
    e->subtype = rand() % 5;
    e->w = CAR_W; e->h = CAR_H;
    e->speed_y = speed * 0.5f;
    int roll = rand() % 100;
    if (difficulty == DIFF_HARD) {
      if (roll < 20) e->behavior = BEHAVIOR_SPEEDER;
      else if (roll < 35) e->behavior = BEHAVIOR_WEAVER;
      else if (roll < 50) e->behavior = BEHAVIOR_SUDDEN_BRAKER;
      else if (roll < 60) e->behavior = BEHAVIOR_LANE_DRIFTER;
      else if (roll < 68) e->behavior = BEHAVIOR_CHAOS;
      else if (roll < 76) e->behavior = BEHAVIOR_BLOCKER;
      else e->behavior = BEHAVIOR_NORMAL;
    } else {
      if (roll < 8) e->behavior = BEHAVIOR_LANE_DRIFTER;
      else if (roll < 16) e->behavior = BEHAVIOR_SUDDEN_BRAKER;
      else if (roll < 22) e->behavior = BEHAVIOR_SPEEDER;
      else if (roll < 26) e->behavior = BEHAVIOR_CHAOS;
      else if (roll < 32) e->behavior = BEHAVIOR_BLOCKER;
      else e->behavior = BEHAVIOR_NORMAL;
    }
  } else {
    e->type = forced_type;
    e->w = ITEM_W; e->h = ITEM_H; e->speed_y = speed;
  }

  e->y = -(float)e->h;
  e->x = (float)randomRoadSpawnX(e->w);
  e->target_x = e->x;
}

// ---------------------------------------------------------------------------
// Particles
// ---------------------------------------------------------------------------
void spawnParticle(float x, float y) {
#if ENABLE_PARTICLES
  for (int i = 0; i < MAX_PARTICLES; i++) {
    if (!particles[i].active) {
      particles[i].active = 1;
      particles[i].x = x; particles[i].y = y;
      particles[i].vx = (float)((rand() % 10) - 5) / 10.0f;
      particles[i].vy = (float)((rand() % 20) + 10) / 10.0f;
      particles[i].life = 10 + (rand() % 15);
      particles[i].color_idx = 1;
      break;
    }
  }
#else
  (void)x; (void)y;
#endif
}

void updateParticles() {
#if ENABLE_PARTICLES
  for (int i = 0; i < MAX_PARTICLES; i++) {
    if (particles[i].active) {
      particles[i].x += particles[i].vx;
      particles[i].y += particles[i].vy;
      if (--particles[i].life <= 0) particles[i].active = 0;
    }
  }
#endif
}

void drawParticles() {
#if ENABLE_PARTICLES
  for (int i = 0; i < MAX_PARTICLES; i++) {
    if (particles[i].active) {
      int px = (int)particles[i].x;
      int py = (int)particles[i].y;
      if (px >= 0 && px < 240 && py >= 0 && py < 160) {
        int off = (py * 240 + px) / 2;
        u16 *dst = vid_page + off;
        if (px & 1) *dst = (*dst & 0x00FF) | 0x0100;
        else *dst = (*dst & 0xFF00) | 0x01;
      }
    }
  }
#endif
}

int checkRect(int x1, int y1, int w1, int h1, int x2, int y2, int w2, int h2) {
  return x1 < x2 + w2 && x1 + w1 > x2 && y1 < y2 + h2 && y1 + h1 > y2;
}

void updateGame() {
  const CarDef *cdef = &car_defs[current_car_idx];
  const RoadStats *rstats = &road_stats[current_road_idx];
  const ModeRules *mr = &mode_rules[game_mode];

  // Combo decay
  updateComboDecay();

  // Boost logic — L=sustain, R=burst
  boost_active = 0; boost_mult = 1.0f;
  if ((input.held & KEY_R) && boost_meter > 0) {
    boost_active = 2; boost_mult = 1.65f;
    boost_meter--; // ~1/frame = ~1.7 sec full burst
    spawnParticle((float)(player_x + CAR_W / 2.0f), (float)(player_y + CAR_H));
  } else if ((input.held & KEY_L) && boost_meter > 0) {
    boost_active = 1; boost_mult = 1.25f;
    boost_drain_tick++;
    if (boost_drain_tick >= 2) { boost_drain_tick = 0; boost_meter--; }
  }
  if (boost_meter < 0) boost_meter = 0;

  // Scroll
  float eff_speed = speed * boost_mult;
  scroll_y += eff_speed;

  // Distance-based scoring
  score++;

  // Wrong-lane scoring: player on left side of road
  if (mr->risk_active) {
    int road_center = (getRoadLeft() + getRoadRight()) / 2;
    wrong_lane_timer++;
    if (wrong_lane_timer >= 21 && player_x < road_center - 10) {
      wrong_lane_timer = 0;
      combo_meter += 3;
      if (combo_meter > 100) combo_meter = 100;
      addRiskPoints(8);
    }
  }

  // Fuel drain (mode-dependent)
  if (mr->fuel_drain) {
    float fuel_mult = 100.0f / (float)(cdef->fuel_eff > 0 ? cdef->fuel_eff : 50);
    float drain = 0.05f * fuel_mult * (1.0f / (cdef->drag * 1.05f));
    drain *= (float)rstats->drain_pct / 100.0f;
    fuel -= drain;
    if (fuel <= 0) { finalizeRun(); return; }
  }

  // Time attack countdown
  if (mr->use_timer) {
    time_attack_remaining--;
    if (time_attack_remaining <= 0) { finalizeRun(); return; }
  }

  // Zen focus regen
  if (mr->use_focus && zen_focus < 100) {
    // +3.2/sec ≈ +1 every 19 frames
    if ((frame_counter % 19) == 0) zen_focus++;
  }
  if (mr->use_focus && zen_focus <= 0) { finalizeRun(); return; }

  // Spawn
  spawn_timer++;
  int spawn_threshold = (difficulty == DIFF_HARD) ? 22 : 30;
  if (difficulty == DIFF_EASY) spawn_threshold = 40;

  // Python-style speed scaling: faster speed = faster spawn
  float speed_ratio = speed / 3.0f;
  if (speed_ratio < 0.5f) speed_ratio = 0.5f;
  
  spawn_threshold = (int)((float)spawn_threshold / speed_ratio);
  spawn_threshold = (int)((float)spawn_threshold / rstats->spawn_rate_mult);
  spawn_threshold = spawn_threshold * (int)mr->spawn_rate_pct / 100;
  if (spawn_threshold < 10) spawn_threshold = 10;

  if (spawn_timer > spawn_threshold) {
    spawn_timer = 0;
    if ((rand() % 100) < 80) spawnEntityType(0); // 80% Enemy spawn chance
    
    // Decoupled item spawns (matching Python `ai_driver`)
    if ((rand() % 100) < 30) spawnEntityType(1);
    if ((rand() % 100) < 15) spawnEntityType(2);
    if ((rand() % 100) < 8) spawnEntityType(4);
    
    if (difficulty == DIFF_EASY && (rand() % 100) < 10) spawnEntityType(3);
    else if (difficulty == DIFF_NORMAL && (rand() % 100) < 3) spawnEntityType(3);
  }

  // Screen shake decay
  if (shake_timer > 0) shake_timer--;

  // Track near-miss: left_block / right_block for thread-the-gap
  int nm_left = 0, nm_right = 0;

  // Entities
  for (int i = 0; i < MAX_ENTITIES; i++) {
    if (!entities[i].active) continue;
    Entity *e = &entities[i];
    float move_speed = eff_speed;

    if (e->type == 0) { // Enemy
      float enemy_abs = 1.5f;
      int lane_chance = 80;

      if (e->behavior == BEHAVIOR_SPEEDER) {
        enemy_abs = 3.5f;
        lane_chance = 50;
      } else if (e->behavior == BEHAVIOR_SUDDEN_BRAKER) {
        e->timer++;
        if (e->timer > 100) e->timer = 0;
        enemy_abs = (e->timer > 70) ? 0.5f : 1.5f;
        lane_chance = 30;
      } else if (e->behavior == BEHAVIOR_WEAVER) {
        enemy_abs = 1.8f;
        lane_chance = 90;
      } else if (e->behavior == BEHAVIOR_LANE_DRIFTER) {
        enemy_abs = 1.0f;
        lane_chance = 95;
      } else if (e->behavior == BEHAVIOR_CHAOS) {
        enemy_abs = 0.7f + (float)(rand() % 10) / 10.0f;
        lane_chance = 80;
      } else if (e->behavior == BEHAVIOR_BLOCKER) {
        enemy_abs = 0.6f;
        lane_chance = 40;
      }

      // 1. AI Logic: Periodic Lane Picking (every ~0.5s)
      if (((frame_counter + i * 7) % 30) == 0) {
        if ((rand() % 100) < lane_chance) {
          if (e->behavior == BEHAVIOR_BLOCKER) {
            e->target_x = player_x_f;
          } else if (e->behavior == BEHAVIOR_WEAVER) {
            e->target_x = e->x + (float)(e->weave_dir * 45);
            e->weave_dir = -e->weave_dir; // Ping-pong
          } else if (e->behavior == BEHAVIOR_CHAOS) {
            e->target_x = e->x + (float)((rand() % 80) - 40);
          } else {
            // Normal, Drifter, Speeder, Braker
            int offsets[4] = {-40, -20, 20, 40};
            e->target_x = e->x + (float)offsets[rand() % 4];
          }
          // Clamp target inside road bounds
          e->target_x = (float)clampToRoad((int)e->target_x, e->w);
        }
      }

      // 2. Lateral Movement Physics (accelerate toward target)
      float drift_accel = 0.22f; // Base acceleration (matches user lat_accel ~0.35)
      if (e->behavior == BEHAVIOR_LANE_DRIFTER) drift_accel = 0.35f;
      if (e->behavior == BEHAVIOR_WEAVER) drift_accel = 0.40f;
      if (e->behavior == BEHAVIOR_CHAOS) drift_accel = 0.45f;
      if (e->behavior == BEHAVIOR_BLOCKER) drift_accel = 0.20f;

      float diff = e->target_x - e->x;
      if (diff > 1.5f) e->lateral_vel += drift_accel;
      else if (diff < -1.5f) e->lateral_vel -= drift_accel;

      // 3. Apply standard "user-like" friction and position integration
      e->lateral_vel *= 0.88f; 
      e->x += e->lateral_vel;
      clampEntityToRoad(e);

      float rel = eff_speed - enemy_abs;
      if (rel < 0.5f) rel = 0.5f;
      move_speed = rel;
    }

    e->y += move_speed;

    int ex = (int)e->x, ey = (int)e->y;

    // Collision check
    if (checkRect(player_x, player_y, CAR_W, CAR_H, ex, ey, e->w, e->h)) {
      if (e->type == 0) { // Enemy collision
        if (mr->use_focus) {
          // Zen mode: no death, lose focus
          zen_focus -= 25;
          if (zen_focus < 0) zen_focus = 0;
          triggerScreenShake();
          e->active = 0;
        } else if (mr->one_hit_death) {
          triggerScreenShake();
          finalizeRun(); return;
        } else if (difficulty == DIFF_EASY || boost_active == 2) {
          if (boost_active == 2) {
            score += 100; spawnParticle(e->x, e->y);
          } else {
            player_health -= COLLISION_DAMAGE;
            triggerScreenShake();
          }
          e->active = 0;
          if (player_health <= 0 && boost_active != 2) {
            finalizeRun(); return;
          }
        } else {
          triggerScreenShake();
          finalizeRun(); return;
        }
      } else if (e->type == 1) { // Coin
        int reward = 50 * rstats->risk_factor / 10;
        reward = reward * rstats->reward_pct / 100;
        score += reward * score_multiplier;
        e->active = 0;
      } else if (e->type == 2) { // Fuel
        fuel += 20; if (fuel > 100) fuel = 100;
        e->active = 0;
      } else if (e->type == 3) { // Repair
        player_health += REPAIR_HEAL_AMOUNT;
        if (player_health > PLAYER_MAX_HEALTH) player_health = PLAYER_MAX_HEALTH;
        e->active = 0;
      } else if (e->type == 4) { // Boost/Nitro pickup
        boost_meter += 45;
        if (boost_meter > 100) boost_meter = 100;
        e->active = 0;
      }
    } else if (e->type == 0 && !e->nm_scored && mr->risk_active) {
      // Near-miss detection (no collision but close proximity)
      int dy = ey - player_y;
      if (dy > -CAR_H && dy < CAR_H) { // Vertically overlapping
        int dx = ex - player_x;
        int abs_dx = dx < 0 ? -dx : dx;
        if (abs_dx < NEAR_MISS_DIST && speed > NEAR_MISS_SPEED) {
          e->nm_scored = 1;
          triggerNearMiss();
          if (dx < 0) nm_left = 1; else nm_right = 1;
        }
      }
      // High-speed overtake: enemy below player, close, fast
      if (dy > CAR_H && dy < CAR_H + 30) {
        int dx = ex - player_x;
        int abs_dx = dx < 0 ? -dx : dx;
        if (abs_dx < 30 && speed > 4.0f && !e->nm_scored) {
          e->nm_scored = 1;
          triggerOvertake();
        }
      }
    }

    if (e->y > 160) e->active = 0;
    if (e->y < -200) e->active = 0;
  }

  // Thread the gap: enemies on both sides simultaneously
  if (nm_left && nm_right) triggerThreadGap();
}

// ---------------------------------------------------------------------------
// Main Loop
// ---------------------------------------------------------------------------
int main() {
  REG_DISPCNT = MODE_4 | BG2_ENABLE;
  for (int i = 0; i < 256; i++) PALETTE[i] = game_palette[i];
  loadSaveData();
  initSessionData();

  while (1) {
    waitForVBlank();
    frame_counter++;
    session.session_frame_count++;

    u16 keys_curr = ~REG_KEYINPUT & 0x03FF;
    input.pressed = keys_curr & ~input.held;
    input.released = input.held & ~keys_curr;
    input.held = keys_curr;

    // =================================================================
    // STATE UPDATE
    // =================================================================

    if (current_state == STATE_MENU) {
      int num_btns = 6;
      if (input.pressed & KEY_DOWN) {
        selected_btn++;
        if (selected_btn >= num_btns) selected_btn = 0;
      }
      if (input.pressed & KEY_UP) {
        selected_btn--;
        if (selected_btn < 0) selected_btn = num_btns - 1;
      }
      if (input.pressed & (KEY_A | KEY_START)) {
        if (selected_btn == 0) { // START → road select
          pending_road_idx = current_road_idx;
          current_state = STATE_ROAD_SELECT;
        } else if (selected_btn == 1) { // GARAGE
          pending_car_idx = current_car_idx;
          current_state = STATE_GARAGE;
        } else if (selected_btn == 2) { // RECORDS
          records_scroll = 0;
          current_state = STATE_RECORDS;
        } else if (selected_btn == 3) { // MODE cycle
          game_mode = (game_mode + 1) % NUM_MODES;
          save_data.game_mode = (u8)game_mode;
          savePersistentData();
        } else if (selected_btn == 4) { // DIFFICULTY cycle
          if (difficulty == DIFF_NORMAL) difficulty = DIFF_HARD;
          else if (difficulty == DIFF_HARD) difficulty = DIFF_EASY;
          else difficulty = DIFF_NORMAL;
          save_data.difficulty = (u8)difficulty;
          savePersistentData();
        } else if (selected_btn == 5) { // INSTRUCTIONS
          current_state = STATE_INSTRUCTIONS;
        }
      }

    } else if (current_state == STATE_INSTRUCTIONS) {
      if (input.pressed & (KEY_B | KEY_START)) current_state = STATE_MENU;

    } else if (current_state == STATE_PLAY) {
      const CarDef *cdef = &car_defs[current_car_idx];
      const RoadStats *rstats = &road_stats[current_road_idx];

      // Lateral movement
      float h_mult = (float)cdef->handling / 100.0f;
      float g_mult = ((float)rstats->friction / 100.0f) * cdef->grip;
      float lat_accel = 0.35f * h_mult * g_mult;
      if (input.held & KEY_LEFT) vel_x -= lat_accel;
      if (input.held & KEY_RIGHT) vel_x += lat_accel;
      vel_x *= 0.88f;
      player_x_f += vel_x;
      player_x = (int)player_x_f;

      if (input.held & KEY_UP) player_y -= 2;
      if (input.held & KEY_DOWN) player_y += 2;

      // Forward speed with road speed bonus
      float max_speed = ((float)cdef->top_speed / 35.0f);
      max_speed *= (float)rstats->speed_pct / 100.0f;
      float fwd_accel = ((float)cdef->accel / 100.0f) * 0.08f;
      if (input.held & KEY_A) {
        speed += fwd_accel;
        if (speed > max_speed) speed = max_speed;
      } else {
        if (speed > 2.0f) speed -= 0.02f * cdef->drag;
      }
      if (input.held & KEY_B) {
        float bp = 0.15f * ((float)cdef->braking / 100.0f);
        speed -= bp;
        if (speed < 0) speed = 0;
      }

      // Clamp player to road bounds (using per-road gameplay area)
      int rl = getRoadLeft(), rr = getRoadRight();
      if (player_x < rl) { player_x = rl; player_x_f = (float)rl; }
      if (player_x > rr - CAR_W) {
        player_x = rr - CAR_W; player_x_f = (float)(rr - CAR_W);
      }
      if (player_y < 0) player_y = 0;
      if (player_y > 160 - CAR_H) player_y = 160 - CAR_H;

      updateGame();

    } else if (current_state == STATE_RUN_SUMMARY) {
      if (input.pressed & (KEY_A | KEY_START)) current_state = STATE_MENU;

    } else if (current_state == STATE_GAMEOVER) {
      if (input.pressed & KEY_START) current_state = STATE_MENU;

    } else if (current_state == STATE_GARAGE) {
      u16 nk = (KEY_RIGHT | KEY_R | KEY_LEFT | KEY_L);
      if (input.pressed & (KEY_RIGHT | KEY_R)) {
        pending_car_idx = (pending_car_idx + 1) % NUM_CARS;
        nav_repeat_timer = 0; nav_repeat_active = 0;
      } else if (input.pressed & (KEY_LEFT | KEY_L)) {
        pending_car_idx = (pending_car_idx - 1 + NUM_CARS) % NUM_CARS;
        nav_repeat_timer = 0; nav_repeat_active = 0;
      } else if (input.held & nk) {
        nav_repeat_timer++;
        if (nav_repeat_timer >= (nav_repeat_active ? REPEAT_INTERVAL : REPEAT_INITIAL_DELAY)) {
          nav_repeat_timer = 0; nav_repeat_active = 1;
          if (input.held & (KEY_RIGHT | KEY_R))
            pending_car_idx = (pending_car_idx + 1) % NUM_CARS;
          else
            pending_car_idx = (pending_car_idx - 1 + NUM_CARS) % NUM_CARS;
        }
      } else { nav_repeat_timer = 0; nav_repeat_active = 0; }

      if (input.pressed & (KEY_A | KEY_START)) {
        if (isCarUnlocked(pending_car_idx)) {
          current_car_idx = pending_car_idx;
          save_data.selected_car = (u8)current_car_idx;
          savePersistentData();
          current_state = STATE_MENU;
        }
      }
      if (input.pressed & KEY_B) {
        nav_repeat_timer = 0; nav_repeat_active = 0;
        current_state = STATE_MENU;
      }

    } else if (current_state == STATE_ROAD_SELECT) {
      u16 nk = (KEY_RIGHT | KEY_R | KEY_LEFT | KEY_L);
      if (input.pressed & (KEY_RIGHT | KEY_R)) {
        pending_road_idx = (pending_road_idx + 1) % NUM_ROADS;
        nav_repeat_timer = 0; nav_repeat_active = 0;
      } else if (input.pressed & (KEY_LEFT | KEY_L)) {
        pending_road_idx = (pending_road_idx - 1 + NUM_ROADS) % NUM_ROADS;
        nav_repeat_timer = 0; nav_repeat_active = 0;
      } else if (input.held & nk) {
        nav_repeat_timer++;
        if (nav_repeat_timer >= (nav_repeat_active ? REPEAT_INTERVAL : REPEAT_INITIAL_DELAY)) {
          nav_repeat_timer = 0; nav_repeat_active = 1;
          if (input.held & (KEY_RIGHT | KEY_R))
            pending_road_idx = (pending_road_idx + 1) % NUM_ROADS;
          else
            pending_road_idx = (pending_road_idx - 1 + NUM_ROADS) % NUM_ROADS;
        }
      } else { nav_repeat_timer = 0; nav_repeat_active = 0; }

      if (input.pressed & (KEY_A | KEY_START)) {
        current_road_idx = pending_road_idx;
        save_data.selected_road = (u8)current_road_idx;
        road_preview_cached_idx = -1;
        initGame();
        current_state = STATE_PLAY;
      }
      if (input.pressed & KEY_B) {
        road_preview_cached_idx = -1;
        current_state = STATE_MENU;
      }

    } else if (current_state == STATE_RECORDS) {
      if (input.pressed & KEY_DOWN) {
        int ms = (int)save_data.recent_run_count - 5;
        if (ms < 0) ms = 0;
        if (records_scroll < ms) records_scroll++;
      }
      if (input.pressed & KEY_UP) {
        if (records_scroll > 0) records_scroll--;
      }
      if (input.pressed & (KEY_B | KEY_START)) current_state = STATE_MENU;
    }

    // =================================================================
    // DRAW BACKGROUND (gameplay only)
    // =================================================================
    if (current_state == STATE_PLAY) {
      for (int y = 0; y < 160; y++) {
        u16 *row = vid_page + y * 120;
        for (int i = 0; i < 20; i++) row[i] = 0;
        for (int i = 100; i < 120; i++) row[i] = 0;
      }
      drawBackground();
    }

    // =================================================================
    // RENDER
    // =================================================================

    if (current_state == STATE_MENU) {
      fillScreen(C_BLACK);
      drawText(80, 4, "RED RACER");
      drawText(70, 14, "ULTIMATE EDITION");

      int spr = car_defs[current_car_idx].sprite_idx;
      drawSprite(30, 32, cars_left[spr], CAR_W, CAR_H);
      drawSprite(194, 32, cars_right[spr], CAR_W, CAR_H);

      // 6 buttons: START, GARAGE, RECORDS, MODE, DIFF, INSTRUCTIONS
      const char *labels[] = {"START","GARAGE","RECORDS","MODE","DIFF","HOW TO PLAY"};
      int colors[] = {C_RED, C_YELLOW, C_CYAN, C_BLUE, C_PURPLE, C_GRAY};

      const char *diff_lbl = "NRM";
      if (difficulty == DIFF_HARD) { diff_lbl = "HRD"; colors[4] = C_RED; }
      else if (difficulty == DIFF_EASY) { diff_lbl = "EZ"; colors[4] = C_GREEN; }

      int sy = 42;
      for (int i = 0; i < 6; i++) {
        int bx = 60, by = sy + i * 16, bw = 120, bh = 12;
        if (i == selected_btn) drawRect(bx - 2, by - 2, bw + 4, bh + 4, C_WHITE);
        drawRect(bx, by, bw, bh, colors[i]);
        if (i == 3) {
          drawText(bx + 4, by + 2, "MODE:");
          drawText(bx + 48, by + 2, mode_rules[game_mode].short_name);
        } else if (i == 4) {
          drawText(bx + 4, by + 2, "DIFF:");
          drawText(bx + 48, by + 2, diff_lbl);
        } else {
          drawText(bx + 4, by + 2, labels[i]);
        }
      }

      drawText(5, 148, "CAR:");
      drawText(37, 148, car_defs[current_car_idx].name);
      drawText(120, 148, "BEST:");
      drawInt(160, 148, high_score);
      drawText(5, 138, "LV:");
      drawInt(29, 138, (int)save_data.level);

    } else if (current_state == STATE_INSTRUCTIONS) {
      fillScreen(C_BLACK);
      drawText(72, 4, "HOW TO PLAY");
      int x = 4, y = 16, dy = 9;
      drawText(x, y, "DPAD : STEER / MOVE"); y += dy;
      drawText(x, y, "A : ACCELERATE"); y += dy;
      drawText(x, y, "B : BRAKE"); y += dy;
      drawText(x, y, "L : SUSTAIN BOOST (1.25X)"); y += dy;
      drawText(x, y, "R : BURST BOOST (1.65X)"); y += dy;
      drawText(x, y, "START : CONFIRM / BACK"); y += dy + 2;
      drawText(x, y, "RISK SCORING"); y += dy;
      drawText(x, y, "NEAR-MISS ENEMIES = COMBO"); y += dy;
      drawText(x, y, "COMBO BUILDS MULTIPLIER"); y += dy;
      drawText(x, y, "RISKY PLAY CHARGES BOOST"); y += dy + 2;
      drawText(x, y, "MODES"); y += dy;
      drawText(x, y, "CLS:NORMAL RISK:RISKONLY"); y += dy;
      drawText(x, y, "TIME:90S CORE:1HIT ZEN");
      drawText(20, 152, "PRESS B OR START TO RETURN");

    } else if (current_state == STATE_GARAGE) {
      fillScreen(C_BLACK);
      const CarDef *cdef = &car_defs[pending_car_idx];
      int locked = !isCarUnlocked(pending_car_idx);

      drawText(88, 2, "GARAGE");
      drawText(8, 2, "<");
      drawInt(16, 2, pending_car_idx + 1);
      drawText(40, 2, "/");
      drawInt(48, 2, NUM_CARS);
      drawText(72, 2, ">");

      int px = 112, py = 16;
      drawRect(px - 3, py - 3, CAR_W + 6, CAR_H + 6, locked ? C_RED : C_GREEN);
      drawSprite(px, py, cars_normal[cdef->sprite_idx], CAR_W, CAR_H);
      drawText(px - 20, py + CAR_H + 6, cdef->name);

      if (locked) {
        drawText(8, 50, "LOCKED");
        drawText(8, 60, "NEED:");
        drawInt(48, 60, (int)cdef->unlock_score);
      } else {
        drawText(8, 50, "UNLOCKED");
        if (pending_car_idx == current_car_idx) drawText(8, 60, "[SELECTED]");
        drawText(8, 70, "BEST:");
        drawInt(48, 70, (int)save_data.per_car_best[pending_car_idx]);
      }

      int bx = 72, by = 86, bw = 80, bh = 5, bdy = 12, lx = 8;
      int spd_pct = ((cdef->top_speed - 150) * 100) / 110;
      if (spd_pct < 0) spd_pct = 0;
      if (spd_pct > 100) spd_pct = 100;
      drawText(lx, by, "SPD");
      drawStatBar(bx, by+1, bw, bh, spd_pct, 100, C_RED);
      drawInt(bx+bw+4, by, cdef->top_speed);
      by += bdy;
      drawText(lx, by, "ACC");
      drawStatBar(bx, by+1, bw, bh, cdef->accel, 100, C_YELLOW);
      drawInt(bx+bw+4, by, cdef->accel);
      by += bdy;
      drawText(lx, by, "HDL");
      drawStatBar(bx, by+1, bw, bh, cdef->handling, 100, C_GREEN);
      drawInt(bx+bw+4, by, cdef->handling);
      by += bdy;
      drawText(lx, by, "BRK");
      drawStatBar(bx, by+1, bw, bh, cdef->braking, 100, C_CYAN);
      drawInt(bx+bw+4, by, cdef->braking);
      by += bdy;
      drawText(lx, by, "FUL");
      drawStatBar(bx, by+1, bw, bh, cdef->fuel_eff, 100, C_BLUE);
      drawInt(bx+bw+4, by, cdef->fuel_eff);

      if (locked) drawText(20, 150, "L/R:BROWSE  B:BACK");
      else drawText(8, 150, "A:SELECT  B:BACK  L/R:BROWSE");

    } else if (current_state == STATE_ROAD_SELECT) {
      fillScreen(C_BLACK);
      drawText(5, 5, "SELECT ROAD (L/R)");
      drawText(20, 142, "A/START: GO!  B: CANCEL");

      if (road_preview_cached_idx != pending_road_idx)
        rebuildRoadPreviewCache(pending_road_idx);
      drawCachedRoadPreview((240 - PREVIEW_W) / 2, 20);

      drawText(80, 125, road_stats[pending_road_idx].name);
      drawText(80, 135, "< ROAD >");
      drawInt(140, 135, pending_road_idx + 1);
      drawText(5, 152, "CAR:");
      drawText(37, 152, car_defs[current_car_idx].name);
      drawText(130, 152, "MODE:");
      drawText(170, 152, mode_rules[game_mode].short_name);

    } else if (current_state == STATE_PLAY) {
      // Draw entities
      for (int i = 0; i < MAX_ENTITIES; i++) {
        if (!entities[i].active) continue;
        const u16 *spr = 0;
        if (entities[i].type == 0) {
          int subtype = entities[i].subtype;
          spr = cars_normal[subtype];
          if (entities[i].lateral_vel < -0.1f) spr = cars_left[subtype];
          if (entities[i].lateral_vel > 0.1f) spr = cars_right[subtype];
#if ENABLE_PARTICLES
          if ((rand() % 100) < 5)
            spawnParticle(entities[i].x + entities[i].w / 2.0f,
                          entities[i].y + entities[i].h);
#endif
        } else {
          spr = item_sprites[entities[i].type - 1];
        }
        if (spr) drawSprite((int)entities[i].x, (int)entities[i].y,
                            spr, entities[i].w, entities[i].h);
      }

      // Draw player with tilt + screen shake offset
      int spr_idx = car_defs[current_car_idx].sprite_idx;
      const u16 *pspr = cars_normal[spr_idx];
      if (vel_x < -0.5f) pspr = cars_left[spr_idx];
      if (vel_x > 0.5f) pspr = cars_right[spr_idx];
      int draw_py = player_y;
      if (shake_timer > 0) draw_py += (shake_timer & 1) ? 2 : -2;
      drawSprite(player_x, draw_py, pspr, CAR_W, CAR_H);

#if ENABLE_PARTICLES
      if ((rand() % 100) < 20)
        spawnParticle((float)(player_x + CAR_W / 2.0f), (float)(player_y + CAR_H));
#endif
      updateParticles();
      drawParticles();

      // === HUD ===
      // Top row: score + fuel
      drawText(5, 2, "SCR:");
      int display_score = score;
      if (game_mode == MODE_HIGH_RISK) display_score = risk_score;
      else display_score = score + risk_score;
      drawInt(37, 2, display_score);

      drawText(168, 2, "FUL:");
      drawInt(200, 2, (int)fuel);

      // Second row: speed + multiplier
      int display_mph = (int)(speed * 35.0f);
      drawText(5, 12, "SPD:");
      drawInt(37, 12, display_mph);

      if (mode_rules[game_mode].risk_active && score_multiplier > 1) {
        drawText(168, 12, "x");
        drawInt(176, 12, score_multiplier);
      }

      // Left margin: boost bar (vertical, x=4..8, y=24..130)
      drawVBar(4, 24, 4, 106, boost_meter, 100,
               boost_active == 2 ? C_RED : (boost_active == 1 ? C_YELLOW : C_GREEN));
      drawText(0, 132, "BST");

      // Right margin: combo bar (vertical, x=232..236, y=24..130)
      if (mode_rules[game_mode].risk_active) {
        int cmb_color = C_GRAY;
        if (combo_meter > 80) cmb_color = C_RED;
        else if (combo_meter > 40) cmb_color = C_YELLOW;
        else if (combo_meter > 0) cmb_color = C_GREEN;
        drawVBar(232, 24, 4, 106, combo_meter, 100, cmb_color);
        drawText(224, 132, "CMB");
      }

      // Mode-specific HUD
      if (mode_rules[game_mode].use_timer) {
        int secs_left = time_attack_remaining / 60;
        drawText(100, 2, "T:");
        drawInt(116, 2, secs_left);
      }

      if (mode_rules[game_mode].use_focus) {
        drawText(80, 12, "FOC:");
        drawStatBar(112, 13, 50, 5, zen_focus, 100, C_PURPLE);
      }

      if (difficulty == DIFF_EASY) {
        drawText(80, 12, "HP:");
        drawRect(104, 13, 50, 5, C_RED);
        int hpw = (player_health * 50) / PLAYER_MAX_HEALTH;
        if (hpw < 0) hpw = 0;
        if (hpw > 50) hpw = 50;
        drawRect(104, 13, hpw, 5, C_GREEN);
      }

    } else if (current_state == STATE_RUN_SUMMARY) {
      fillScreen(C_BLACK);
      drawText(72, 4, "RUN COMPLETE");
      drawText(72, 16, mode_names[game_mode]);

      drawText(60, 30, "SCORE:");
      drawInt(108, 30, summary_run_score);

      if (mode_rules[game_mode].risk_active) {
        drawText(60, 42, "RISK:");
        drawInt(108, 42, summary_risk_score);
      }

      drawText(60, 54, "CAR:");
      drawText(92, 54, car_defs[current_car_idx].name);

      int secs = (int)(summary_run_duration / 60);
      drawText(60, 66, "TIME:");
      drawInt(100, 66, secs);
      drawText(132, 66, "S");

      if (summary_new_best) drawText(68, 80, "** NEW BEST! **");

      drawText(60, 92, "HIGH:");
      drawInt(100, 92, high_score);

      if (summary_new_unlocks > 0) {
        drawRect(20, 104, 200, 20, C_YELLOW);
        drawText(28, 106, "CAR UNLOCKED!");
        for (int i = NUM_CARS - 1; i >= 0; i--) {
          if (summary_unlock_mask & (1 << i)) {
            drawText(28, 114, car_defs[i].name);
            break;
          }
        }
      }

      drawText(30, 130, "RUNS:");
      drawInt(70, 130, (int)session.runs_this_session);
      drawText(100, 130, "LV:");
      drawInt(124, 130, (int)save_data.level);

      drawText(52, 150, "PRESS A OR START");

    } else if (current_state == STATE_RECORDS) {
      fillScreen(C_BLACK);
      drawText(80, 2, "RECORDS");

      drawText(8, 14, "BEST:");
      drawInt(48, 14, high_score);
      drawText(120, 14, "RUNS:");
      drawInt(160, 14, (int)save_data.total_runs);

      int ts = (int)(save_data.total_playtime_frames / 60);
      drawText(8, 24, "PLAY:");
      drawInt(48, 24, ts / 60);
      drawText(72, 24, "M");
      drawInt(84, 24, ts % 60);
      drawText(108, 24, "S");
      drawText(120, 24, "LV:");
      drawInt(144, 24, (int)save_data.level);

      // Per-mode bests
      drawText(8, 36, "MODE BESTS:");
      for (int m = 0; m < NUM_MODES; m++) {
        int mx = 8 + m * 48;
        drawText(mx, 46, mode_rules[m].short_name);
        drawInt(mx, 54, (int)save_data.per_mode_best[m]);
      }

      drawText(8, 66, "RECENT:");
      if (save_data.recent_run_count == 0) {
        drawText(20, 78, "NO RUNS YET");
      } else {
        int max_vis = 5;
        for (int vi = 0; vi < max_vis; vi++) {
          int idx = vi + records_scroll;
          if (idx >= (int)save_data.recent_run_count) break;
          int ri = (int)save_data.recent_run_head - 1 - idx;
          while (ri < 0) ri += MAX_RECENT_RUNS;
          ri = ri % MAX_RECENT_RUNS;
          RunRecord *rec = &save_data.recent_runs[ri];
          int ry = 78 + vi * 14;
          drawInt(8, ry, idx + 1);
          drawText(24, ry, ".");
          drawInt(32, ry, (int)rec->score);
          if (rec->car_id < NUM_CARS)
            drawText(88, ry, car_defs[rec->car_id].name);
          drawText(160, ry, mode_rules[rec->game_mode < NUM_MODES ? rec->game_mode : 0].short_name);
          int ds = (int)(rec->duration_frames / 60);
          drawInt(200, ry, ds);
          drawText(224, ry, "S");
        }
      }
      drawText(36, 152, "B:BACK  UP/DN:SCROLL");

    } else if (current_state == STATE_GAMEOVER) {
      drawText(85, 60, "GAME OVER");
      drawText(80, 80, "FINAL SCORE");
      drawInt(110, 95, score);
      drawText(60, 135, "PRESS START TO RESET");
    }

#if ENABLE_DEBUG_OVERLAY
    drawText(5, 155, "ST:");
    drawInt(25, 155, current_state);
    drawText(55, 155, "FR:");
    drawInt(75, 155, (int)frame_counter);
#endif

    flipPage();
  }
  return 0;
}
