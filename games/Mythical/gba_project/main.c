#include <stddef.h>

#include "gba.h"
#include "generated/assets.h"
#include "generated/content.h"
#include "generated/maps.h"

enum GameState {
  STATE_TITLE,
  STATE_PLAY,
  STATE_HELP,
  STATE_PAUSE,
  STATE_INVENTORY,
  STATE_CRAFTING,
  STATE_SKILLS,
  STATE_BESTIARY,
  STATE_TRAVEL,
  STATE_STAGE_INTRO,
  STATE_STAGE_CLEAR,
  STATE_GAME_OVER,
  STATE_VICTORY,
};

enum Facing {
  FACE_DOWN = 0,
  FACE_UP = 1,
  FACE_LEFT = 2,
  FACE_RIGHT = 3,
};

enum BossState {
  BOSS_DORMANT = 0,
  BOSS_WAKE = 1,
  BOSS_CHASE = 2,
  BOSS_SLAM = 3,
  BOSS_CHARGE = 4,
  BOSS_SPIN = 5,
  BOSS_WAVE = 6,
  BOSS_RIFT = 7,
  BOSS_DEAD = 8,
};

typedef struct {
  u16 held;
  u16 pressed;
  u16 released;
} InputState;

typedef struct {
  u8 active;
  const char *speaker;
  const char **pages;
  u8 page_count;
  u8 page_index;
  u8 chars_visible;
  u8 char_timer;
  u8 pending_give;
  u8 pending_take;
  const char *pending_npc_trigger;
} DialogueState;

typedef struct {
  u8 active;
  const GBAEnemySpawnDef *def;
  int x_fp;
  int y_fp;
  s16 hp;
  u8 cooldown;
  u8 hurt_timer;
  u8 flash_timer;
} EnemyRuntime;

typedef struct {
  u8 active;
  const GBABossDef *def;
  int x_fp;
  int y_fp;
  s16 hp;
  u8 phase;
  u8 state;
  u8 cooldown;
  u8 state_timer;
  u8 damage_done;
  u8 flash_timer;
} BossRuntime;

typedef struct {
  u8 active;
  u8 animal_type;
  int x_fp;
  int y_fp;
  s8 hp;
  u8 state;
  u8 timer;
  u8 move_dir;
  u8 cooldown;
  u8 flash_timer;
  u8 spawn_index;
} AnimalRuntime;

#define MAX_ACTIVE_ANIMALS 12
#define ANIMAL_STATE_WANDER 0
#define ANIMAL_STATE_FLEE 1
#define ANIMAL_STATE_AGGRO 2
#define ANIMAL_STATE_DEAD 3

#define BITFIELD_SIZE(count) (((count) + 7) / 8)
#define FP_SHIFT 8
#define FP_ONE (1 << FP_SHIFT)
#define PLAYER_W GBA_PLAYER_W
#define PLAYER_H GBA_PLAYER_H
#define PLAYER_COLLIDE_LEFT 3
#define PLAYER_COLLIDE_TOP 6
#define PLAYER_COLLIDE_RIGHT 12
#define PLAYER_COLLIDE_BOTTOM 15
#define MAX_ACTIVE_ENEMIES 16
#define WORLD_HW_TILE_SIZE 8
#define WORLD_BUFFER_TILES 64
#define WORLD_VISIBLE_HW_TILES_X ((SCREEN_WIDTH / WORLD_HW_TILE_SIZE) + 1)
#define WORLD_VISIBLE_HW_TILES_Y ((SCREEN_HEIGHT / WORLD_HW_TILE_SIZE) + 1)
#define WORLD_BG0_SBB 16
#define WORLD_BG1_SBB 20
#define UI_BG_SBB 28
#define SAVE_MAGIC 0x4D595448u
#define SAVE_VERSION 4u
#define SRAM ((volatile u8 *)0x0E000000)

/* 8-slot hotbar — matches settings.HOTBAR_SIZE in the Python build so
 * handheld play mirrors the desktop quick-use strip. Each slot stores an
 * item index into gba_items[] or -1 for empty. */
#define HOTBAR_SLOTS 8

typedef struct __attribute__((packed)) {
  u32 magic;
  u16 version;
  u16 checksum;
  u8 map_id;
  u8 player_tile_x;
  u8 player_tile_y;
  u8 facing;
  u8 hp;
  u16 coins;
  u8 world_stage;
  u8 completed_stage_bits;
  u8 boss_kill_bits;
  u16 xp;
  u8 level;
  u8 player_form;
  u8 active_hotbar;
  s8 equipped_weapon;
  s8 equipped_armor;
  s8 equipped_accessory;
  u8 quest_stage[GBA_QUEST_COUNT];
  u8 quest_complete_bits;
  u8 item_counts[GBA_ITEM_COUNT];
  u8 opened_chests[BITFIELD_SIZE(GBA_CHEST_COUNT)];
  u8 collected_ground[BITFIELD_SIZE(GBA_GROUND_ITEM_COUNT)];
  u8 collected_lore[BITFIELD_SIZE(GBA_LORE_COUNT)];
  u8 defeated_enemies[BITFIELD_SIZE(GBA_ENEMY_SPAWN_COUNT)];
  u8 defeated_bosses[BITFIELD_SIZE(GBA_BOSS_COUNT)];
  u8 defeated_animals[BITFIELD_SIZE(GBA_ANIMAL_SPAWN_COUNT)];
  u8 skill_atk;
  u8 skill_def;
  u8 skill_hp;
  u8 skill_points;
  u8 waypoint_bits;
  s8 reputation[3];
  u8 consequence_bits;
  u8 weather_state;
  u16 enemy_kill_counts[GBA_ENEMY_TYPE_COUNT];
  s8 hotbar[HOTBAR_SLOTS];
} SaveData;

static ObjAttr g_oam_shadow[128] EWRAM_DATA;
static u16 g_bg0_shadow[4][1024] EWRAM_DATA;
static u16 g_bg1_shadow[4][1024] EWRAM_DATA;
static u16 g_ui_shadow[1024] EWRAM_DATA;
static InputState g_input;
static DialogueState g_dialogue;
static EnemyRuntime g_enemies[MAX_ACTIVE_ENEMIES];
static BossRuntime g_boss;

static AnimalRuntime g_animals[MAX_ACTIVE_ANIMALS];
static u8 g_defeated_animals[BITFIELD_SIZE(GBA_ANIMAL_SPAWN_COUNT)];

static enum GameState g_state = STATE_TITLE;
static u8 g_current_map = MAP_VILLAGE;
static int g_player_x_fp = 0;
static int g_player_y_fp = 0;
static int g_camera_x = 0;
static int g_camera_y = 0;
static u8 g_facing = FACE_DOWN;
static u8 g_anim_frame = 0;
static u8 g_anim_timer = 0;
static u8 g_attack_timer = 0;
static u8 g_attack_cooldown = 0;
static u8 g_player_iframes = 0;
static u8 g_player_flash = 0;
static u8 g_player_hp = 6;
static u8 g_title_cursor = 0;
static u8 g_inventory_cursor = 0;
static u8 g_stage_clear_target = 0;
static u16 g_coins = 0;
static u16 g_xp = 0;
static u8 g_level = 1;
static u8 g_player_form = 0;
static u8 g_active_hotbar = 0;
static s8 g_hotbar[HOTBAR_SLOTS] = {-1, -1, -1, -1, -1, -1, -1, -1};
/* Accumulates half-heart heals (raw/cooked meat). Every two half-hearts
 * collected combine into one full heart. Persists across eats but not across
 * saves (a half-heart in progress is forgotten on reload — matches pygame
 * behaviour since pygame's player.partial_hp isn't saved either). */
static u8 g_half_heart_pending = 0;
static u8 g_world_stage = 1;
static u8 g_completed_stage_bits = 0;
static u8 g_boss_kill_bits = 0;
static s8 g_equipped_weapon = -1;
static s8 g_equipped_armor = -1;
static s8 g_equipped_accessory = -1;
static u8 g_quest_stage[GBA_QUEST_COUNT];
static u8 g_quest_complete_bits = 0;
static u8 g_item_counts[GBA_ITEM_COUNT];
static u8 g_opened_chests[BITFIELD_SIZE(GBA_CHEST_COUNT)];
static u8 g_collected_ground[BITFIELD_SIZE(GBA_GROUND_ITEM_COUNT)];
static u8 g_collected_lore[BITFIELD_SIZE(GBA_LORE_COUNT)];
static u8 g_defeated_enemies[BITFIELD_SIZE(GBA_ENEMY_SPAWN_COUNT)];
static u8 g_defeated_bosses[BITFIELD_SIZE(GBA_BOSS_COUNT)];
static u8 g_skill_atk = 0;
static u8 g_skill_def = 0;
static u8 g_skill_hp = 0;
static u8 g_skill_points = 0;
static u8 g_waypoint_bits = 0;
static s8 g_reputation[3] = {0, 0, 0};
static u8 g_consequence_bits = 0;
static u8 g_weather_state = 0;
static u8 g_weather_timer = 0;
static u16 g_enemy_kill_counts[GBA_ENEMY_TYPE_COUNT];
static u8 g_crafting_cursor = 0;
static u8 g_skills_cursor = 0;
static u8 g_bestiary_cursor = 0;
static u8 g_travel_cursor = 0;
static u8 g_pause_cursor = 0;
static u8 g_continue_available = 0;
static u8 g_status_timer = 0;
static u8 g_objective_timer = 0;
static char g_status_text[80] = "";
static char g_dialogue_page_buffer[4][80];
static const char *g_dialogue_page_refs[4];
static u32 g_rng_state = 0x7A3B92E1u;
static u32 g_frame_counter = 0;
static int g_world_min_hw_x = 0;
static int g_world_max_hw_x = 0;
static int g_world_min_hw_y = 0;
static int g_world_max_hw_y = 0;
static u8 g_world_video_ready = 0;
static u8 g_world_bg_dirty = 1;

static int clamp_int(int value, int minimum, int maximum) {
  if (value < minimum) {
    return minimum;
  }
  if (value > maximum) {
    return maximum;
  }
  return value;
}

static int abs_int(int value) {
  return value < 0 ? -value : value;
}

static int string_length(const char *text) {
  int length = 0;
  while (text && text[length]) {
    length++;
  }
  return length;
}

static int string_equals(const char *a, const char *b) {
  int index = 0;
  if (!a || !b) {
    return 0;
  }
  while (a[index] && b[index]) {
    if (a[index] != b[index]) {
      return 0;
    }
    index++;
  }
  return a[index] == '\0' && b[index] == '\0';
}

static int quest_target_matches(const char *expected, const char *actual) {
  if (string_equals(expected, actual)) {
    return 1;
  }
  if ((string_equals(expected, "golem") && string_equals(actual, "dark_golem")) ||
      (string_equals(expected, "dark_golem") && string_equals(actual, "golem"))) {
    return 1;
  }
  return 0;
}

static void copy_text(char *dst, int dst_size, const char *src) {
  int index = 0;
  if (dst_size <= 0) {
    return;
  }
  while (index < dst_size - 1 && src && src[index]) {
    dst[index] = src[index];
    index++;
  }
  dst[index] = '\0';
}

static void int_to_text(int value, char *buffer, int buffer_size) {
  char reversed[16];
  int count = 0;
  int negative = 0;
  int index;
  unsigned int current;
  if (buffer_size <= 0) {
    return;
  }
  if (value < 0) {
    negative = 1;
    current = (unsigned int)(-value);
  } else {
    current = (unsigned int)value;
  }
  do {
    reversed[count++] = (char)('0' + (current % 10));
    current /= 10;
  } while (current && count < 15);
  index = 0;
  if (negative && index < buffer_size - 1) {
    buffer[index++] = '-';
  }
  while (count > 0 && index < buffer_size - 1) {
    buffer[index++] = reversed[--count];
  }
  buffer[index] = '\0';
}

static u32 random_u32(void) {
  g_rng_state = g_rng_state * 1664525u + 1013904223u;
  return g_rng_state;
}

static int random_percent(int percent) {
  return (int)(random_u32() % 100u) < percent;
}

static int bit_test(const u8 *bits, int index) {
  return (bits[index >> 3] >> (index & 7)) & 1;
}

static void bit_set(u8 *bits, int index) {
  bits[index >> 3] |= (u8)(1u << (index & 7));
}

static void set_status(const char *text, int timer) {
  copy_text(g_status_text, (int)sizeof(g_status_text), text);
  g_status_timer = (u8)clamp_int(timer, 0, 255);
}

static void pulse_objective(int timer) {
  g_objective_timer = (u8)clamp_int(timer, 0, 255);
}

static int string_width(const char *text) {
  return string_length(text);
}

static void ui_fill_rect(int tx, int ty, int width, int height, u16 tile_index);
static void begin_sprite_frame(void);
static int player_speed_modifier(void);

static void update_input(void) {
  u16 previous = g_input.held;
  u16 current = (u16)(~REG_KEYINPUT & 0x03FF);
  g_input.held = current;
  g_input.pressed = (u16)(current & ~previous);
  g_input.released = (u16)(previous & ~current);
}

static void clear_shadow_block(u16 block[1024], u16 value) {
  int index;
  for (index = 0; index < 1024; index++) {
    block[index] = value;
  }
}

static void clear_world_shadows(void) {
  int block;
  for (block = 0; block < 4; block++) {
    clear_shadow_block(g_bg0_shadow[block], 0);
    clear_shadow_block(g_bg1_shadow[block], 0);
  }
}

static void clear_ui_shadow(void) {
  clear_shadow_block(g_ui_shadow, 0);
}

static void begin_ui_scene(u16 fill_tile) {
  begin_sprite_frame();
  clear_world_shadows();
  g_world_bg_dirty = 1;
  g_world_video_ready = 0;
  clear_ui_shadow();
  ui_fill_rect(0, 0, 32, 32, fill_tile);
  g_camera_x = 0;
  g_camera_y = 0;
}

static u16 *shadow_entry_ptr(u16 shadow[4][1024], int hw_x, int hw_y) {
  int block = (hw_x >= 32 ? 1 : 0) + (hw_y >= 32 ? 2 : 0);
  int offset = (hw_y & 31) * 32 + (hw_x & 31);
  return &shadow[block][offset];
}

static void set_bg_shadow_entry(u16 shadow[4][1024], int hw_x, int hw_y, u16 value) {
  *shadow_entry_ptr(shadow, hw_x & 63, hw_y & 63) = value;
}

static void hide_all_sprites(void) {
  int index;
  for (index = 0; index < 128; index++) {
    g_oam_shadow[index].attr0 = ATTR0_HIDE;
    g_oam_shadow[index].attr1 = 0;
    g_oam_shadow[index].attr2 = 0;
    g_oam_shadow[index].pad = 0;
  }
}

static u16 ui_font_tile(int font_base, char c) {
  unsigned char index = (unsigned char)c;
  if (index < 32 || index >= 128) {
    index = '?';
  }
  return (u16)(font_base + (index - 32));
}

static void ui_set_tile(int tx, int ty, u16 tile_index) {
  if (tx < 0 || ty < 0 || tx >= 32 || ty >= 32) {
    return;
  }
  g_ui_shadow[ty * 32 + tx] = tile_index;
}

static void ui_fill_rect(int tx, int ty, int width, int height, u16 tile_index) {
  int row;
  int col;
  for (row = 0; row < height; row++) {
    for (col = 0; col < width; col++) {
      ui_set_tile(tx + col, ty + row, tile_index);
    }
  }
}

static void ui_draw_box(int tx, int ty, int width, int height, int accent_header) {
  int row;
  int col;
  if (width < 2 || height < 2) {
    return;
  }
  ui_fill_rect(tx, ty, width, height, GBA_UI_TILE_FILL);
  if (accent_header) {
    ui_fill_rect(tx + 1, ty + 1, width - 2, 1, GBA_UI_TILE_FILL_ALT);
  }
  ui_set_tile(tx, ty, GBA_UI_TILE_CORNER_TL);
  ui_set_tile(tx + width - 1, ty, GBA_UI_TILE_CORNER_TR);
  ui_set_tile(tx, ty + height - 1, GBA_UI_TILE_CORNER_BL);
  ui_set_tile(tx + width - 1, ty + height - 1, GBA_UI_TILE_CORNER_BR);
  for (col = 1; col < width - 1; col++) {
    ui_set_tile(tx + col, ty, GBA_UI_TILE_HLINE);
    ui_set_tile(tx + col, ty + height - 1, GBA_UI_TILE_HLINE);
  }
  for (row = 1; row < height - 1; row++) {
    ui_set_tile(tx, ty + row, GBA_UI_TILE_VLINE);
    ui_set_tile(tx + width - 1, ty + row, GBA_UI_TILE_VLINE);
  }
}

static void ui_draw_text(int tx, int ty, const char *text, int accent) {
  int index = 0;
  int start_x = tx;
  int font_base = accent ? GBA_UI_FONT_GOLD_BASE : GBA_UI_FONT_WHITE_BASE;
  while (text && text[index]) {
    if (text[index] == '\n') {
      ty++;
      tx = start_x;
      index++;
      continue;
    }
    ui_set_tile(tx, ty, ui_font_tile(font_base, text[index]));
    tx++;
    index++;
  }
}

static void ui_draw_text_clipped(int tx, int ty, int max_chars, const char *text, int accent) {
  char clipped[64];
  int length = string_length(text);
  int index;
  if (max_chars <= 0) {
    return;
  }
  if (length <= max_chars) {
    ui_draw_text(tx, ty, text, accent);
    return;
  }
  if (max_chars <= 2) {
    ui_draw_text(tx, ty, "..", accent);
    return;
  }
  for (index = 0; index < max_chars - 2 && text[index]; index++) {
    clipped[index] = text[index];
  }
  clipped[index++] = '.';
  clipped[index++] = '.';
  clipped[index] = '\0';
  ui_draw_text(tx, ty, clipped, accent);
}

static void ui_draw_text_centered(int ty, const char *text, int accent) {
  ui_draw_text((30 - string_width(text)) / 2, ty, text, accent);
}

static int ui_draw_wrapped_text(int tx, int ty, int max_chars, const char *text, int accent, int max_lines) {
  int index = 0;
  int line = 0;
  int cursor_x = tx;
  char word[48];
  while (text && text[index] && line < max_lines) {
    int word_len = 0;
    if (text[index] == '\n') {
      line++;
      ty++;
      cursor_x = tx;
      index++;
      continue;
    }
    while (text[index] == ' ') {
      index++;
      if (cursor_x > tx) {
        cursor_x++;
      }
    }
    while (text[index] && text[index] != ' ' && text[index] != '\n' && word_len < (int)sizeof(word) - 1) {
      word[word_len++] = text[index++];
    }
    word[word_len] = '\0';
    if (!word_len) {
      continue;
    }
    if (cursor_x > tx && cursor_x + word_len > tx + max_chars) {
      line++;
      if (line >= max_lines) {
        break;
      }
      ty++;
      cursor_x = tx;
    }
    ui_draw_text(cursor_x, ty, word, accent);
    cursor_x += word_len;
    if (text[index] == ' ') {
      cursor_x++;
    }
  }
  return line + 1;
}

static int world_bg_tile(int layer, int world_hw_x, int world_hw_y) {
  const GBAMap *map = &gba_maps[g_current_map];
  int tile_x = world_hw_x >> 1;
  int tile_y = world_hw_y >> 1;
  int subtile = ((world_hw_y & 1) << 1) | (world_hw_x & 1);
  int map_index;
  u8 tile_id;
  if (tile_x < 0 || tile_y < 0 || tile_x >= map->width || tile_y >= map->height) {
    return 0;
  }
  map_index = tile_y * map->width + tile_x;
  tile_id = layer == 0 ? map->ground[map_index] : map->decor[map_index];
  if (layer == 0) {
    if (tile_id >= GBA_GROUND_TILE_COUNT) {
      return 0;
    }
    return gba_ground_tile_bases[tile_id] + subtile;
  }
  if (tile_id >= GBA_DECOR_TILE_COUNT || tile_id == 0) {
    return 0;
  }
  return gba_decor_tile_bases[tile_id] + subtile;
}

static void populate_world_cell(int world_hw_x, int world_hw_y) {
  int physical_x = world_hw_x & 63;
  int physical_y = world_hw_y & 63;
  set_bg_shadow_entry(g_bg0_shadow, physical_x, physical_y, (u16)world_bg_tile(0, world_hw_x, world_hw_y));
  set_bg_shadow_entry(g_bg1_shadow, physical_x, physical_y, (u16)world_bg_tile(1, world_hw_x, world_hw_y));
}

static void rebuild_world_window(void) {
  int cam_hw_x = g_camera_x / WORLD_HW_TILE_SIZE;
  int cam_hw_y = g_camera_y / WORLD_HW_TILE_SIZE;
  int world_y;
  int world_x;
  clear_world_shadows();
  g_world_min_hw_x = cam_hw_x;
  g_world_max_hw_x = cam_hw_x + WORLD_BUFFER_TILES - 1;
  g_world_min_hw_y = cam_hw_y;
  g_world_max_hw_y = cam_hw_y + WORLD_BUFFER_TILES - 1;
  for (world_y = g_world_min_hw_y; world_y <= g_world_max_hw_y; world_y++) {
    for (world_x = g_world_min_hw_x; world_x <= g_world_max_hw_x; world_x++) {
      populate_world_cell(world_x, world_y);
    }
  }
  g_world_video_ready = 1;
  g_world_bg_dirty = 1;
}

static void stream_world_column(int world_hw_x) {
  int world_y;
  for (world_y = g_world_min_hw_y; world_y <= g_world_max_hw_y; world_y++) {
    populate_world_cell(world_hw_x, world_y);
  }
  g_world_bg_dirty = 1;
}

static void stream_world_row(int world_hw_y) {
  int world_x;
  for (world_x = g_world_min_hw_x; world_x <= g_world_max_hw_x; world_x++) {
    populate_world_cell(world_x, world_hw_y);
  }
  g_world_bg_dirty = 1;
}

static void sync_world_window(void) {
  int cam_hw_x = g_camera_x / WORLD_HW_TILE_SIZE;
  int cam_hw_y = g_camera_y / WORLD_HW_TILE_SIZE;
  int visible_max_x = cam_hw_x + WORLD_VISIBLE_HW_TILES_X;
  int visible_max_y = cam_hw_y + WORLD_VISIBLE_HW_TILES_Y;
  if (!g_world_video_ready) {
    rebuild_world_window();
    return;
  }
  while (cam_hw_x < g_world_min_hw_x) {
    g_world_min_hw_x--;
    g_world_max_hw_x--;
    stream_world_column(g_world_min_hw_x);
  }
  while (visible_max_x > g_world_max_hw_x) {
    g_world_min_hw_x++;
    g_world_max_hw_x++;
    stream_world_column(g_world_max_hw_x);
  }
  while (cam_hw_y < g_world_min_hw_y) {
    g_world_min_hw_y--;
    g_world_max_hw_y--;
    stream_world_row(g_world_min_hw_y);
  }
  while (visible_max_y > g_world_max_hw_y) {
    g_world_min_hw_y++;
    g_world_max_hw_y++;
    stream_world_row(g_world_max_hw_y);
  }
}

static int g_sprite_cursor = 0;

static void begin_sprite_frame(void) {
  g_sprite_cursor = 0;
  hide_all_sprites();
}

static void emit_sprite(int x, int y, u16 tile_base, int size, int priority) {
  u16 attr1_size;
  int extent;
  ObjAttr *obj;
  if (g_sprite_cursor >= 128) {
    return;
  }
  if (size == 32) {
    attr1_size = ATTR1_SIZE_32;
    extent = 32;
  } else if (size == 16) {
    attr1_size = ATTR1_SIZE_16;
    extent = 16;
  } else {
    attr1_size = ATTR1_SIZE_8;
    extent = 8;
  }
  if (x <= -extent || y <= -extent || x >= SCREEN_WIDTH || y >= SCREEN_HEIGHT) {
    return;
  }
  obj = &g_oam_shadow[g_sprite_cursor++];
  obj->attr0 = (u16)((y & 0x00FF) | ATTR0_REGULAR | ATTR0_8BPP | ATTR0_SQUARE);
  obj->attr1 = (u16)((x & 0x01FF) | attr1_size);
  obj->attr2 = (u16)(tile_base | ATTR2_PRIORITY(priority));
  obj->pad = 0;
}

static void video_init(void) {
  int block;
  REG_DISPCNT = MODE_0 | BG0_ENABLE | BG1_ENABLE | BG2_ENABLE | OBJ_ENABLE | OBJ_MAP_1D;
  REG_BG0CNT = BG_PRIORITY(2) | BG_CHARBLOCK(0) | BG_256_COLOR | BG_SCREENBLOCK(WORLD_BG0_SBB) | BG_SIZE_64X64;
  REG_BG1CNT = BG_PRIORITY(1) | BG_CHARBLOCK(0) | BG_256_COLOR | BG_SCREENBLOCK(WORLD_BG1_SBB) | BG_SIZE_64X64;
  REG_BG2CNT = BG_PRIORITY(0) | BG_CHARBLOCK(1) | BG_256_COLOR | BG_SCREENBLOCK(UI_BG_SBB) | BG_SIZE_32X32;
  dmaCopy16(gba_palette, (void *)BG_PALETTE, 256);
  dmaCopy16(gba_palette, (void *)OBJ_PALETTE, 256);
  dmaCopy16(gba_bg_tiles, (void *)CHARBLOCK(0), (u32)(sizeof(gba_bg_tiles) / sizeof(u16)));
  dmaCopy16(gba_ui_tiles, (void *)CHARBLOCK(1), (u32)(sizeof(gba_ui_tiles) / sizeof(u16)));
  dmaCopy16(gba_obj_tiles, (void *)OBJ_TILE_MEM, (u32)(sizeof(gba_obj_tiles) / sizeof(u16)));
  clear_world_shadows();
  clear_ui_shadow();
  hide_all_sprites();
  for (block = 0; block < 4; block++) {
    dmaCopy16(g_bg0_shadow[block], (void *)SCREENBLOCK(WORLD_BG0_SBB + block), 1024);
    dmaCopy16(g_bg1_shadow[block], (void *)SCREENBLOCK(WORLD_BG1_SBB + block), 1024);
  }
  dmaCopy16(g_ui_shadow, (void *)SCREENBLOCK(UI_BG_SBB), 1024);
  dmaCopy16(g_oam_shadow, (void *)OAM, (u32)(sizeof(g_oam_shadow) >> 1));
}

static void present(void) {
  int block;
  waitForVBlank();
  if (g_world_bg_dirty) {
    for (block = 0; block < 4; block++) {
      dmaCopy16(g_bg0_shadow[block], (void *)SCREENBLOCK(WORLD_BG0_SBB + block), 1024);
      dmaCopy16(g_bg1_shadow[block], (void *)SCREENBLOCK(WORLD_BG1_SBB + block), 1024);
    }
    g_world_bg_dirty = 0;
  }
  dmaCopy16(g_ui_shadow, (void *)SCREENBLOCK(UI_BG_SBB), 1024);
  dmaCopy16(g_oam_shadow, (void *)OAM, (u32)(sizeof(g_oam_shadow) >> 1));
  REG_BG0HOFS = (u16)g_camera_x;
  REG_BG0VOFS = (u16)g_camera_y;
  REG_BG1HOFS = (u16)g_camera_x;
  REG_BG1VOFS = (u16)g_camera_y;
  REG_BG2HOFS = 0;
  REG_BG2VOFS = 0;
}

static int collision_at(const GBAMap *map, int tile_x, int tile_y) {
  int index;
  if (tile_x < 0 || tile_y < 0 || tile_x >= map->width || tile_y >= map->height) {
    return 1;
  }
  index = tile_y * map->width + tile_x;
  return (map->collision[index >> 3] >> (index & 7)) & 1;
}

static int has_weapon_equipped(void) {
  return g_equipped_weapon >= 0 && g_equipped_weapon < GBA_ITEM_COUNT;
}

static int player_attack_bonus(void) {
  int bonus = g_level / 4 + g_skill_atk;
  if (g_world_stage >= 2) {
    bonus += 1;
  }
  if (g_world_stage >= 3) {
    bonus += 1;
  }
  if (g_equipped_weapon >= 0) {
    bonus += gba_items[g_equipped_weapon].attack_bonus;
  }
  if (g_equipped_accessory >= 0) {
    bonus += gba_items[g_equipped_accessory].attack_bonus;
  }
  return bonus;
}

static int player_defense_bonus(void) {
  int bonus = g_skill_def;
  if (g_world_stage >= 2) {
    bonus += 1;
  }
  if (g_world_stage >= 3) {
    bonus += 1;
  }
  if (g_equipped_armor >= 0) {
    bonus += gba_items[g_equipped_armor].defense_bonus;
  }
  if (g_equipped_accessory >= 0) {
    bonus += gba_items[g_equipped_accessory].defense_bonus;
  }
  return bonus;
}

static int player_speed_fp(void) {
  int speed = FP_ONE;
  if (g_world_stage == 2) {
    speed += 38;
  } else if (g_world_stage >= 3) {
    speed += 90;
  }
  if (g_equipped_weapon >= 0) {
    speed += gba_items[g_equipped_weapon].speed_bonus_q8;
  }
  if (g_equipped_armor >= 0) {
    speed += gba_items[g_equipped_armor].speed_bonus_q8;
  }
  if (g_equipped_accessory >= 0) {
    speed += gba_items[g_equipped_accessory].speed_bonus_q8;
  }
  speed += player_speed_modifier();
  if (speed < FP_ONE / 2) {
    speed = FP_ONE / 2;
  }
  return speed;
}

static u8 player_max_hp(void) {
  return (u8)(6 + gba_stage_hp_bonus[g_world_stage] + g_level / 3 + g_skill_hp);
}

static u16 xp_for_level(int level) {
  return (u16)(level * level * 10);
}

static void grant_xp(int amount) {
  g_xp += (u16)amount;
  while (g_level < 20 && g_xp >= xp_for_level(g_level + 1)) {
    g_level++;
    g_skill_points++;
    set_status("Level up! Skill point earned.", 90);
  }
}

static const char *weather_name(void) {
  switch (g_weather_state) {
    case 1: return "Cloudy";
    case 2: return "Rain";
    case 3: return "Fog";
    default: return "Clear";
  }
}

static int player_speed_modifier(void) {
  if (g_weather_state == 3) { return -32; }
  return 0;
}

static const char *player_form_name(void) {
  if (g_player_form == 2) { return "Mythic"; }
  if (g_player_form == 1) { return "Hero"; }
  return "Base";
}

static int find_item_index(const char *item_id) {
  int index;
  for (index = 0; index < GBA_ITEM_COUNT; index++) {
    if (string_equals(gba_items[index].id, item_id)) {
      return index;
    }
  }
  return -1;
}

static const GBAQuestDef *current_quest(void) {
  return &gba_quests[gba_stage_quest_index[g_world_stage]];
}

static const char *current_quest_desc(void) {
  const GBAQuestDef *quest = current_quest();
  int index = gba_stage_quest_index[g_world_stage];
  if (bit_test(&g_quest_complete_bits, index)) {
    return "Complete!";
  }
  if (g_quest_stage[index] >= quest->stage_count) {
    return "Complete!";
  }
  return quest->stages[g_quest_stage[index]].desc;
}

static const char *current_quest_brief(void) {
  const GBAQuestDef *quest = current_quest();
  int index = gba_stage_quest_index[g_world_stage];
  if (bit_test(&g_quest_complete_bits, index)) {
    return "Quest clear";
  }
  if (g_quest_stage[index] >= quest->stage_count) {
    return "Quest clear";
  }
  return quest->stages[g_quest_stage[index]].brief;
}

static int inventory_has_item(int item_index, int amount) {
  if (item_index < 0 || item_index >= GBA_ITEM_COUNT) {
    return 0;
  }
  return g_item_counts[item_index] >= amount;
}

static int score_equipped_item(int item_index) {
  if (item_index < 0 || item_index >= GBA_ITEM_COUNT) {
    return -999;
  }
  return gba_items[item_index].attack_bonus * 4 +
         gba_items[item_index].defense_bonus * 3 +
         gba_items[item_index].speed_bonus_q8 / 32 +
         gba_items[item_index].heal_amount;
}

static void equip_item(int item_index) {
  if (item_index < 0 || item_index >= GBA_ITEM_COUNT) {
    return;
  }
  if (gba_items[item_index].equip_slot == GBA_SLOT_WEAPON) {
    g_equipped_weapon = (s8)item_index;
    set_status("Weapon equipped.", 90);
  } else if (gba_items[item_index].equip_slot == GBA_SLOT_ARMOR) {
    g_equipped_armor = (s8)item_index;
    set_status("Armor equipped.", 90);
  } else if (gba_items[item_index].equip_slot == GBA_SLOT_ACCESSORY) {
    g_equipped_accessory = (s8)item_index;
    set_status("Accessory equipped.", 90);
  }
}

static u16 item_icon_tile(int item_index) {
  if (item_index < 0 || item_index >= GBA_ITEM_COUNT) {
    return GBA_UI_TILE_BLANK;
  }
  switch (gba_items[item_index].category) {
    case GBA_ITEM_WEAPON:     return GBA_UI_TILE_ITEM_WEAPON;
    case GBA_ITEM_ARMOR:      return GBA_UI_TILE_ITEM_ARMOR;
    case GBA_ITEM_ACCESSORY:  return GBA_UI_TILE_ITEM_ACCESSORY;
    case GBA_ITEM_CONSUMABLE:
      if (gba_items[item_index].use_effect == GBA_USE_EAT_RAW ||
          gba_items[item_index].use_effect == GBA_USE_EAT_COOKED) {
        return GBA_UI_TILE_ITEM_FOOD;
      }
      return GBA_UI_TILE_ITEM_POTION;
    case GBA_ITEM_MATERIAL:   return GBA_UI_TILE_ITEM_MATERIAL;
    case GBA_ITEM_KEY_ITEM:   return GBA_UI_TILE_ITEM_KEY;
    default:                  return GBA_UI_TILE_BLANK;
  }
}

static int hotbar_slot_for(int item_index) {
  int slot;
  if (item_index < 0) {
    return -1;
  }
  for (slot = 0; slot < HOTBAR_SLOTS; slot++) {
    if (g_hotbar[slot] == item_index) {
      return slot;
    }
  }
  return -1;
}

static int first_empty_hotbar_slot(void) {
  int slot;
  for (slot = 0; slot < HOTBAR_SLOTS; slot++) {
    if (g_hotbar[slot] < 0) {
      return slot;
    }
  }
  return -1;
}

static int item_is_hotbar_eligible(int item_index) {
  int slot;
  if (item_index < 0 || item_index >= GBA_ITEM_COUNT) {
    return 0;
  }
  slot = gba_items[item_index].equip_slot;
  if (slot == GBA_SLOT_WEAPON) {
    return 1;
  }
  /* Python hotbar also holds any item with a use_effect: potions, meat,
   * antidotes, and the mythic core. */
  return gba_items[item_index].use_effect != GBA_USE_NONE;
}

static void assign_active_hotbar(int item_index) {
  int existing;
  if (item_index < 0) {
    g_hotbar[g_active_hotbar] = -1;
    return;
  }
  existing = hotbar_slot_for(item_index);
  if (existing == g_active_hotbar) {
    g_hotbar[g_active_hotbar] = -1;  /* toggle off */
    return;
  }
  if (existing >= 0) {
    g_hotbar[existing] = g_hotbar[g_active_hotbar];  /* swap */
  }
  g_hotbar[g_active_hotbar] = (s8)item_index;
}

static void maybe_add_to_hotbar(int item_index) {
  int slot;
  if (!item_is_hotbar_eligible(item_index)) {
    return;
  }
  if (hotbar_slot_for(item_index) >= 0) {
    return;
  }
  slot = first_empty_hotbar_slot();
  if (slot < 0) {
    return;
  }
  g_hotbar[slot] = (s8)item_index;
}

static void sync_active_hotbar_weapon(void) {
  int item = g_hotbar[g_active_hotbar];
  if (item >= 0 && gba_items[item].equip_slot == GBA_SLOT_WEAPON && g_item_counts[item] > 0) {
    g_equipped_weapon = (s8)item;
  }
}

static void maybe_auto_equip(int item_index) {
  int current_index = -1;
  if (item_index < 0 || item_index >= GBA_ITEM_COUNT) {
    return;
  }
  if (gba_items[item_index].equip_slot == GBA_SLOT_WEAPON) {
    current_index = g_equipped_weapon;
  } else if (gba_items[item_index].equip_slot == GBA_SLOT_ARMOR) {
    current_index = g_equipped_armor;
  } else if (gba_items[item_index].equip_slot == GBA_SLOT_ACCESSORY) {
    current_index = g_equipped_accessory;
  } else {
    return;
  }
  if (current_index < 0 || score_equipped_item(item_index) > score_equipped_item(current_index)) {
    equip_item(item_index);
  }
}

static int inventory_add_item(const char *item_id, int amount) {
  int index = find_item_index(item_id);
  int stack_max;
  if (index < 0) {
    return 0;
  }
  stack_max = gba_items[index].stack_max ? gba_items[index].stack_max : 1;
  if (g_item_counts[index] >= stack_max) {
    return 0;
  }
  g_item_counts[index] = (u8)clamp_int(g_item_counts[index] + amount, 0, stack_max);
  maybe_auto_equip(index);
  maybe_add_to_hotbar(index);
  return 1;
}

static int inventory_remove_item(const char *item_id, int amount) {
  int index = find_item_index(item_id);
  if (index < 0 || g_item_counts[index] < amount) {
    return 0;
  }
  g_item_counts[index] = (u8)(g_item_counts[index] - amount);
  if (g_item_counts[index] == 0) {
    int slot;
    if (g_equipped_weapon == index) {
      g_equipped_weapon = -1;
    }
    if (g_equipped_armor == index) {
      g_equipped_armor = -1;
    }
    if (g_equipped_accessory == index) {
      g_equipped_accessory = -1;
    }
    for (slot = 0; slot < HOTBAR_SLOTS; slot++) {
      if (g_hotbar[slot] == index) {
        g_hotbar[slot] = -1;
      }
    }
  }
  return 1;
}

static void reset_runtime_flags(void) {
  int i;
  for (i = 0; i < MAX_ACTIVE_ENEMIES; i++) {
    g_enemies[i].active = 0;
  }
  g_boss.active = 0;
  g_dialogue.active = 0;
  g_dialogue.pending_give = 0;
  g_dialogue.pending_take = 0;
  g_dialogue.pending_npc_trigger = NULL;
  g_world_video_ready = 0;
  g_world_bg_dirty = 1;
}

static void reset_progress(void) {
  int i;
  g_current_map = gba_stage_entry_maps[1];
  g_world_stage = 1;
  g_completed_stage_bits = 0;
  g_boss_kill_bits = 0;
  g_xp = 0;
  g_level = 1;
  g_player_form = 0;
  g_active_hotbar = 0;
  for (i = 0; i < HOTBAR_SLOTS; i++) {
    g_hotbar[i] = -1;
  }
  g_skill_atk = 0;
  g_skill_def = 0;
  g_skill_hp = 0;
  g_skill_points = 0;
  g_waypoint_bits = 1;
  g_reputation[0] = 0;
  g_reputation[1] = 0;
  g_reputation[2] = 0;
  g_consequence_bits = 0;
  g_weather_state = 0;
  g_weather_timer = 0;
  for (i = 0; i < GBA_ENEMY_TYPE_COUNT; i++) {
    g_enemy_kill_counts[i] = 0;
  }
  g_equipped_weapon = -1;
  g_equipped_armor = -1;
  g_equipped_accessory = -1;
  g_coins = 0;
  g_player_hp = player_max_hp();
  for (i = 0; i < GBA_QUEST_COUNT; i++) {
    g_quest_stage[i] = 0;
  }
  g_quest_complete_bits = 0;
  for (i = 0; i < GBA_ITEM_COUNT; i++) {
    g_item_counts[i] = 0;
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_CHEST_COUNT); i++) {
    g_opened_chests[i] = 0;
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_GROUND_ITEM_COUNT); i++) {
    g_collected_ground[i] = 0;
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_LORE_COUNT); i++) {
    g_collected_lore[i] = 0;
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_ENEMY_SPAWN_COUNT); i++) {
    g_defeated_enemies[i] = 0;
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_BOSS_COUNT); i++) {
    g_defeated_bosses[i] = 0;
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_ANIMAL_SPAWN_COUNT); i++) {
    g_defeated_animals[i] = 0;
  }
  reset_runtime_flags();
  g_status_timer = 0;
  g_objective_timer = 0;
}

static u16 save_checksum(const SaveData *save) {
  const u8 *bytes = (const u8 *)save;
  u32 sum = 0;
  size_t i;
  for (i = offsetof(SaveData, map_id); i < sizeof(SaveData); i++) {
    sum += bytes[i];
  }
  return (u16)(sum & 0xFFFFu);
}

static void write_save(void) {
  SaveData save;
  const u8 *src;
  size_t i;
  int tile_x = (g_player_x_fp >> FP_SHIFT) / GBA_TILE_SIZE;
  int tile_y = (g_player_y_fp >> FP_SHIFT) / GBA_TILE_SIZE;
  save.magic = SAVE_MAGIC;
  save.version = SAVE_VERSION;
  save.checksum = 0;
  save.map_id = g_current_map;
  save.player_tile_x = (u8)clamp_int(tile_x, 0, 255);
  save.player_tile_y = (u8)clamp_int(tile_y, 0, 255);
  save.facing = g_facing;
  save.hp = g_player_hp;
  save.coins = g_coins;
  save.world_stage = g_world_stage;
  save.completed_stage_bits = g_completed_stage_bits;
  save.boss_kill_bits = g_boss_kill_bits;
  save.xp = g_xp;
  save.level = g_level;
  save.player_form = g_player_form;
  save.active_hotbar = g_active_hotbar;
  for (i = 0; i < HOTBAR_SLOTS; i++) {
    save.hotbar[i] = g_hotbar[i];
  }
  save.equipped_weapon = g_equipped_weapon;
  save.equipped_armor = g_equipped_armor;
  save.equipped_accessory = g_equipped_accessory;
  for (i = 0; i < GBA_QUEST_COUNT; i++) {
    save.quest_stage[i] = g_quest_stage[i];
  }
  save.quest_complete_bits = g_quest_complete_bits;
  for (i = 0; i < GBA_ITEM_COUNT; i++) {
    save.item_counts[i] = g_item_counts[i];
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_CHEST_COUNT); i++) {
    save.opened_chests[i] = g_opened_chests[i];
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_GROUND_ITEM_COUNT); i++) {
    save.collected_ground[i] = g_collected_ground[i];
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_LORE_COUNT); i++) {
    save.collected_lore[i] = g_collected_lore[i];
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_ENEMY_SPAWN_COUNT); i++) {
    save.defeated_enemies[i] = g_defeated_enemies[i];
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_BOSS_COUNT); i++) {
    save.defeated_bosses[i] = g_defeated_bosses[i];
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_ANIMAL_SPAWN_COUNT); i++) {
    save.defeated_animals[i] = g_defeated_animals[i];
  }
  save.skill_atk = g_skill_atk;
  save.skill_def = g_skill_def;
  save.skill_hp = g_skill_hp;
  save.skill_points = g_skill_points;
  save.waypoint_bits = g_waypoint_bits;
  save.reputation[0] = g_reputation[0];
  save.reputation[1] = g_reputation[1];
  save.reputation[2] = g_reputation[2];
  save.consequence_bits = g_consequence_bits;
  save.weather_state = g_weather_state;
  for (i = 0; i < GBA_ENEMY_TYPE_COUNT; i++) {
    save.enemy_kill_counts[i] = g_enemy_kill_counts[i];
  }
  save.checksum = save_checksum(&save);
  src = (const u8 *)&save;
  for (i = 0; i < sizeof(SaveData); i++) {
    SRAM[i] = src[i];
  }
  g_continue_available = 1;
}

static int load_save(void) {
  SaveData save;
  u8 *dst = (u8 *)&save;
  size_t i;
  for (i = 0; i < sizeof(SaveData); i++) {
    dst[i] = SRAM[i];
  }
  if (save.magic != SAVE_MAGIC || save.version != SAVE_VERSION) {
    return 0;
  }
  if (save.checksum != save_checksum(&save)) {
    return 0;
  }
  g_current_map = save.map_id;
  g_facing = save.facing;
  g_player_hp = save.hp;
  g_coins = save.coins;
  g_world_stage = clamp_int(save.world_stage, 1, 3);
  g_completed_stage_bits = save.completed_stage_bits;
  g_boss_kill_bits = save.boss_kill_bits;
  g_xp = save.xp;
  g_level = clamp_int(save.level, 1, 20);
  g_player_form = clamp_int(save.player_form, 0, 2);
  g_active_hotbar = clamp_int(save.active_hotbar, 0, HOTBAR_SLOTS - 1);
  for (i = 0; i < HOTBAR_SLOTS; i++) {
    s8 slot = save.hotbar[i];
    g_hotbar[i] = (slot >= 0 && slot < GBA_ITEM_COUNT && g_item_counts[slot] > 0) ? slot : -1;
  }
  g_equipped_weapon = save.equipped_weapon;
  g_equipped_armor = save.equipped_armor;
  g_equipped_accessory = save.equipped_accessory;
  for (i = 0; i < GBA_QUEST_COUNT; i++) {
    g_quest_stage[i] = save.quest_stage[i];
  }
  g_quest_complete_bits = save.quest_complete_bits;
  for (i = 0; i < GBA_ITEM_COUNT; i++) {
    g_item_counts[i] = save.item_counts[i];
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_CHEST_COUNT); i++) {
    g_opened_chests[i] = save.opened_chests[i];
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_GROUND_ITEM_COUNT); i++) {
    g_collected_ground[i] = save.collected_ground[i];
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_LORE_COUNT); i++) {
    g_collected_lore[i] = save.collected_lore[i];
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_ENEMY_SPAWN_COUNT); i++) {
    g_defeated_enemies[i] = save.defeated_enemies[i];
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_BOSS_COUNT); i++) {
    g_defeated_bosses[i] = save.defeated_bosses[i];
  }
  for (i = 0; i < BITFIELD_SIZE(GBA_ANIMAL_SPAWN_COUNT); i++) {
    g_defeated_animals[i] = save.defeated_animals[i];
  }
  g_skill_atk = save.skill_atk;
  g_skill_def = save.skill_def;
  g_skill_hp = save.skill_hp;
  g_skill_points = save.skill_points;
  g_waypoint_bits = save.waypoint_bits;
  g_reputation[0] = save.reputation[0];
  g_reputation[1] = save.reputation[1];
  g_reputation[2] = save.reputation[2];
  g_consequence_bits = save.consequence_bits;
  g_weather_state = save.weather_state;
  for (i = 0; i < GBA_ENEMY_TYPE_COUNT; i++) {
    g_enemy_kill_counts[i] = save.enemy_kill_counts[i];
  }
  g_player_hp = clamp_int(g_player_hp, 1, player_max_hp());
  g_player_x_fp = (save.player_tile_x * GBA_TILE_SIZE) << FP_SHIFT;
  g_player_y_fp = (save.player_tile_y * GBA_TILE_SIZE) << FP_SHIFT;
  reset_runtime_flags();
  g_continue_available = 1;
  return 1;
}

static void update_camera(void) {
  const GBAMap *map = &gba_maps[g_current_map];
  int map_width_px = map->width * GBA_TILE_SIZE;
  int map_height_px = map->height * GBA_TILE_SIZE;
  int player_x = (g_player_x_fp >> FP_SHIFT) + PLAYER_W / 2;
  int player_y = (g_player_y_fp >> FP_SHIFT) + PLAYER_H / 2;
  int margin_x = 72;
  int margin_y = 44;
  if (player_x < g_camera_x + margin_x) {
    g_camera_x = player_x - margin_x;
  } else if (player_x > g_camera_x + SCREEN_WIDTH - margin_x) {
    g_camera_x = player_x - (SCREEN_WIDTH - margin_x);
  }
  if (player_y < g_camera_y + margin_y) {
    g_camera_y = player_y - margin_y;
  } else if (player_y > g_camera_y + SCREEN_HEIGHT - margin_y) {
    g_camera_y = player_y - (SCREEN_HEIGHT - margin_y);
  }
  g_camera_x = clamp_int(g_camera_x, 0, map_width_px - SCREEN_WIDTH);
  g_camera_y = clamp_int(g_camera_y, 0, map_height_px - SCREEN_HEIGHT);
  if (map_width_px <= SCREEN_WIDTH) {
    g_camera_x = 0;
  }
  if (map_height_px <= SCREEN_HEIGHT) {
    g_camera_y = 0;
  }
}

static void open_dialogue(const char *speaker, const char **pages, int page_count) {
  g_dialogue.active = 1;
  g_dialogue.speaker = speaker;
  g_dialogue.pages = pages;
  g_dialogue.page_count = (u8)page_count;
  g_dialogue.page_index = 0;
  g_dialogue.chars_visible = 0;
  g_dialogue.char_timer = 0;
}

static void open_single_page_dialogue(const char *speaker, const char *text) {
  copy_text(g_dialogue_page_buffer[0], sizeof(g_dialogue_page_buffer[0]), text);
  g_dialogue_page_refs[0] = g_dialogue_page_buffer[0];
  open_dialogue(speaker, g_dialogue_page_refs, 1);
}

static void fire_trigger(int trigger, const char *target) {
  int quest_index;
  for (quest_index = 0; quest_index < GBA_QUEST_COUNT; quest_index++) {
    const GBAQuestDef *quest = &gba_quests[quest_index];
    u8 stage = g_quest_stage[quest_index];
    if (bit_test(&g_quest_complete_bits, quest_index) || stage >= quest->stage_count) {
      continue;
    }
    if (quest->stages[stage].trigger != trigger) {
      continue;
    }
    if (!quest_target_matches(quest->stages[stage].target, target)) {
      continue;
    }
    g_quest_stage[quest_index]++;
    if (g_quest_stage[quest_index] >= quest->stage_count) {
      bit_set(&g_quest_complete_bits, quest_index);
      set_status("Quest clear!", 100);
    } else {
      set_status("Goal updated.", 80);
    }
    pulse_objective(180);
    write_save();
  }
}

static int map_has_npc_at(int tile_x, int tile_y) {
  int index;
  for (index = 0; index < GBA_NPC_COUNT; index++) {
    if (gba_npcs[index].map_id == g_current_map &&
        gba_npcs[index].tile_x == tile_x &&
        gba_npcs[index].tile_y == tile_y) {
      return 1;
    }
  }
  return 0;
}

static int can_move_to(const GBAMap *map, int player_x, int player_y) {
  int left = (player_x + PLAYER_COLLIDE_LEFT) / GBA_TILE_SIZE;
  int right = (player_x + PLAYER_COLLIDE_RIGHT) / GBA_TILE_SIZE;
  int top = (player_y + PLAYER_COLLIDE_TOP) / GBA_TILE_SIZE;
  int bottom = (player_y + PLAYER_COLLIDE_BOTTOM) / GBA_TILE_SIZE;
  if (collision_at(map, left, top) ||
      collision_at(map, right, top) ||
      collision_at(map, left, bottom) ||
      collision_at(map, right, bottom)) {
    return 0;
  }
  if (map_has_npc_at(left, top) || map_has_npc_at(right, top) ||
      map_has_npc_at(left, bottom) || map_has_npc_at(right, bottom)) {
    return 0;
  }
  return 1;
}

static int enemy_contact_damage(int enemy_type_index) {
  return gba_enemy_types[enemy_type_index].damage;
}

static int apply_reward(const GBAReward *reward, const char *source_name) {
  char buffer[80];
  int item_index;
  if (reward->kind == GBA_REWARD_CURRENCY) {
    g_coins = (u16)(g_coins + reward->amount);
    copy_text(buffer, sizeof(buffer), "Coins collected.");
    set_status(buffer, 90);
    return 1;
  }
  if (reward->kind == GBA_REWARD_HEAL) {
    u8 max_hp = player_max_hp();
    if (g_player_hp < max_hp) {
      g_player_hp = (u8)clamp_int(g_player_hp + reward->amount, 0, max_hp);
      set_status("Recovered health.", 90);
    } else {
      g_coins = (u16)(g_coins + reward->amount);
      set_status("Health converted to coins.", 90);
    }
    return 1;
  }
  item_index = find_item_index(reward->item_id);
  if (item_index < 0 || !inventory_add_item(reward->item_id, 1)) {
    set_status("Inventory full.", 90);
    return 0;
  }
  copy_text(buffer, sizeof(buffer), source_name);
  if (string_length(buffer) < 2) {
    copy_text(buffer, sizeof(buffer), "Item acquired.");
  } else {
    set_status(buffer, 90);
  }
  fire_trigger(GBA_TRIGGER_PICKUP_ITEM, reward->item_id);
  return 1;
}

static int npc_dialogue_variant_index(const GBANpcDef *npc) {
  int variant_index;
  int quest_index = gba_stage_quest_index[gba_map_stage[g_current_map]];
  int quest_stage = g_quest_stage[quest_index];
  int quest_complete = bit_test(&g_quest_complete_bits, quest_index);
  for (variant_index = 0; variant_index < npc->variant_count; variant_index++) {
    if (quest_complete && npc->variants[variant_index].stage_key == GBA_DIALOG_STAGE_COMPLETE) {
      return variant_index;
    }
  }
  for (variant_index = 0; variant_index < npc->variant_count; variant_index++) {
    if (npc->variants[variant_index].stage_key == quest_stage) {
      return variant_index;
    }
  }
  for (variant_index = 0; variant_index < npc->variant_count; variant_index++) {
    if (npc->variants[variant_index].stage_key == GBA_DIALOG_STAGE_DEFAULT) {
      return variant_index;
    }
  }
  return 0;
}

static void process_dialogue_actions(void) {
  if (!g_dialogue.pending_give && !g_dialogue.pending_take && !g_dialogue.pending_npc_trigger) {
    return;
  }
  if (g_dialogue.pending_take) {
    inventory_remove_item(gba_items[g_dialogue.pending_take - 1].id, 1);
  }
  if (g_dialogue.pending_give) {
    apply_reward(&(GBAReward){GBA_REWARD_ITEM, gba_items[g_dialogue.pending_give - 1].id, 0, NULL}, "Gift received.");
  }
  if (g_dialogue.pending_npc_trigger) {
    fire_trigger(GBA_TRIGGER_TALK_NPC, g_dialogue.pending_npc_trigger);
  }
  g_dialogue.pending_give = 0;
  g_dialogue.pending_take = 0;
  g_dialogue.pending_npc_trigger = NULL;
}

static void spawn_enemies_for_map(void) {
  int runtime_index = 0;
  int index;
  for (index = 0; index < MAX_ACTIVE_ENEMIES; index++) {
    g_enemies[index].active = 0;
  }
  for (index = 0; index < GBA_ENEMY_SPAWN_COUNT && runtime_index < MAX_ACTIVE_ENEMIES; index++) {
    if (gba_enemy_spawns[index].map_id != g_current_map || bit_test(g_defeated_enemies, index)) {
      continue;
    }
    g_enemies[runtime_index].active = 1;
    g_enemies[runtime_index].def = &gba_enemy_spawns[index];
    g_enemies[runtime_index].x_fp = (gba_enemy_spawns[index].tile_x * GBA_TILE_SIZE) << FP_SHIFT;
    g_enemies[runtime_index].y_fp = (gba_enemy_spawns[index].tile_y * GBA_TILE_SIZE) << FP_SHIFT;
    g_enemies[runtime_index].hp = gba_enemy_types[gba_enemy_spawns[index].enemy_type_index].max_hp;
    g_enemies[runtime_index].cooldown = 30;
    g_enemies[runtime_index].hurt_timer = 0;
    g_enemies[runtime_index].flash_timer = 0;
    runtime_index++;
  }
}

static void spawn_boss_for_map(void) {
  int index;
  g_boss.active = 0;
  for (index = 0; index < GBA_BOSS_COUNT; index++) {
    if (gba_bosses[index].map_id != g_current_map || bit_test(g_defeated_bosses, index)) {
      continue;
    }
    g_boss.active = 1;
    g_boss.def = &gba_bosses[index];
    g_boss.x_fp = (gba_bosses[index].tile_x * GBA_TILE_SIZE) << FP_SHIFT;
    g_boss.y_fp = (gba_bosses[index].tile_y * GBA_TILE_SIZE) << FP_SHIFT;
    if (g_boss.def->stage == 1) {
      g_boss.hp = 20;
    } else if (g_boss.def->stage == 2) {
      g_boss.hp = 30;
    } else {
      g_boss.hp = 50;
    }
    g_boss.phase = 1;
    g_boss.state = BOSS_DORMANT;
    g_boss.cooldown = 60;
    g_boss.state_timer = 0;
    g_boss.damage_done = 0;
    g_boss.flash_timer = 0;
    return;
  }
}

static void spawn_animals_for_map(void) {
  int runtime_index = 0;
  int index;
  for (index = 0; index < MAX_ACTIVE_ANIMALS; index++) {
    g_animals[index].active = 0;
  }
  for (index = 0; index < GBA_ANIMAL_SPAWN_COUNT && runtime_index < MAX_ACTIVE_ANIMALS; index++) {
    if (gba_animal_spawns[index].map_id != g_current_map || bit_test(g_defeated_animals, index)) {
      continue;
    }
    g_animals[runtime_index].active = 1;
    g_animals[runtime_index].animal_type = gba_animal_spawns[index].animal_type_index;
    g_animals[runtime_index].x_fp = (gba_animal_spawns[index].tile_x * GBA_TILE_SIZE) << FP_SHIFT;
    g_animals[runtime_index].y_fp = (gba_animal_spawns[index].tile_y * GBA_TILE_SIZE) << FP_SHIFT;
    g_animals[runtime_index].hp = (s8)gba_animal_types[gba_animal_spawns[index].animal_type_index].max_hp;
    g_animals[runtime_index].state = ANIMAL_STATE_WANDER;
    g_animals[runtime_index].timer = (u8)(30 + (random_u32() & 63));
    g_animals[runtime_index].move_dir = (u8)(random_u32() & 3);
    g_animals[runtime_index].cooldown = 0;
    g_animals[runtime_index].flash_timer = 0;
    g_animals[runtime_index].spawn_index = (u8)index;
    runtime_index++;
  }
}

static int animal_can_move(int px, int py) {
  const GBAMap *map = &gba_maps[g_current_map];
  int left = (px + 3) / GBA_TILE_SIZE;
  int right = (px + 12) / GBA_TILE_SIZE;
  int top = (py + 3) / GBA_TILE_SIZE;
  int bottom = (py + 12) / GBA_TILE_SIZE;
  if (px < 0 || py < 0 || right >= map->width || bottom >= map->height) {
    return 0;
  }
  if (collision_at(map, left, top) || collision_at(map, right, top) ||
      collision_at(map, left, bottom) || collision_at(map, right, bottom)) {
    return 0;
  }
  return 1;
}

static void try_animal_move(AnimalRuntime *animal, int move_x, int move_y) {
  int nx, ny;
  if (move_x) {
    nx = (animal->x_fp + move_x) >> FP_SHIFT;
    ny = animal->y_fp >> FP_SHIFT;
    if (animal_can_move(nx, ny)) {
      animal->x_fp += move_x;
    }
  }
  if (move_y) {
    nx = animal->x_fp >> FP_SHIFT;
    ny = (animal->y_fp + move_y) >> FP_SHIFT;
    if (animal_can_move(nx, ny)) {
      animal->y_fp += move_y;
    }
  }
}

static void try_respawn_animal(void) {
  int slot = -1;
  int spawn_index;
  int index;
  for (index = 0; index < MAX_ACTIVE_ANIMALS; index++) {
    if (!g_animals[index].active) { slot = index; break; }
  }
  if (slot < 0) { return; }
  spawn_index = (int)(random_u32() % (u32)GBA_ANIMAL_SPAWN_COUNT);
  if (gba_animal_spawns[spawn_index].map_id != g_current_map) { return; }
  if (bit_test(g_defeated_animals, spawn_index)) { return; }
  for (index = 0; index < MAX_ACTIVE_ANIMALS; index++) {
    if (g_animals[index].active && g_animals[index].spawn_index == (u8)spawn_index) { return; }
  }
  {
    int sx = gba_animal_spawns[spawn_index].tile_x * GBA_TILE_SIZE;
    int sy = gba_animal_spawns[spawn_index].tile_y * GBA_TILE_SIZE;
    int px = g_player_x_fp >> FP_SHIFT;
    int py = g_player_y_fp >> FP_SHIFT;
    if (abs_int(sx - px) < SCREEN_WIDTH && abs_int(sy - py) < SCREEN_HEIGHT) { return; }
  }
  g_animals[slot].active = 1;
  g_animals[slot].animal_type = gba_animal_spawns[spawn_index].animal_type_index;
  g_animals[slot].x_fp = (gba_animal_spawns[spawn_index].tile_x * GBA_TILE_SIZE) << FP_SHIFT;
  g_animals[slot].y_fp = (gba_animal_spawns[spawn_index].tile_y * GBA_TILE_SIZE) << FP_SHIFT;
  g_animals[slot].hp = (s8)gba_animal_types[gba_animal_spawns[spawn_index].animal_type_index].max_hp;
  g_animals[slot].state = ANIMAL_STATE_WANDER;
  g_animals[slot].timer = (u8)(40 + (random_u32() & 63));
  g_animals[slot].move_dir = (u8)(random_u32() & 3);
  g_animals[slot].cooldown = 0;
  g_animals[slot].flash_timer = 0;
  g_animals[slot].spawn_index = (u8)spawn_index;
}

static void update_animal_runtime(void) {
  int index;
  int px = g_player_x_fp >> FP_SHIFT;
  int py = g_player_y_fp >> FP_SHIFT;
  if ((g_frame_counter & 127) == 0) {
    try_respawn_animal();
  }
  for (index = 0; index < MAX_ACTIVE_ANIMALS; index++) {
    AnimalRuntime *animal = &g_animals[index];
    const GBAAnimalTypeDef *atype;
    int ax, ay, dx, dy, dist_q4;
    int step;
    if (!animal->active || animal->state == ANIMAL_STATE_DEAD) {
      continue;
    }
    atype = &gba_animal_types[animal->animal_type];
    ax = animal->x_fp >> FP_SHIFT;
    ay = animal->y_fp >> FP_SHIFT;
    dx = px - ax;
    dy = py - ay;
    dist_q4 = (abs_int(dx) + abs_int(dy)) / 4;
    if (animal->flash_timer) {
      animal->flash_timer--;
    }
    if (animal->cooldown) {
      animal->cooldown--;
    }
    step = atype->speed_fp / 8;
    if (step < 32) { step = 32; }
    if (animal->state == ANIMAL_STATE_WANDER) {
      if (atype->behavior >= GBA_ANIMAL_BEHAVE_TERRITORIAL && atype->aggro_range_q4 && dist_q4 < atype->aggro_range_q4) {
        animal->state = ANIMAL_STATE_AGGRO;
      }
      if (animal->timer) {
        animal->timer--;
        if ((animal->timer & 3) == 0) {
          int mx = 0, my = 0;
          if (animal->move_dir == 0) { my = step; }
          else if (animal->move_dir == 1) { my = -step; }
          else if (animal->move_dir == 2) { mx = -step; }
          else { mx = step; }
          try_animal_move(animal, mx, my);
        }
      } else {
        animal->move_dir = (u8)(random_u32() & 3);
        animal->timer = (u8)(40 + (random_u32() & 63));
      }
    } else if (animal->state == ANIMAL_STATE_FLEE) {
      if ((g_frame_counter & 1) == 0) {
        int mx = 0, my = 0;
        int flee_step = step + step / 2;
        if (dx > 0) { mx = -flee_step; }
        else if (dx < 0) { mx = flee_step; }
        if (dy > 0) { my = -flee_step; }
        else if (dy < 0) { my = flee_step; }
        try_animal_move(animal, mx, my);
      }
      if (animal->timer) {
        animal->timer--;
      } else if (dist_q4 > atype->flee_range_q4) {
        animal->state = ANIMAL_STATE_WANDER;
        animal->timer = (u8)(60 + (random_u32() & 63));
      } else {
        animal->timer = 30;
      }
    } else if (animal->state == ANIMAL_STATE_AGGRO) {
      if (dist_q4 > atype->aggro_range_q4 * 3) {
        animal->state = ANIMAL_STATE_WANDER;
        animal->timer = 30;
      } else {
        if ((g_frame_counter & 1) == 0) {
          int mx = 0, my = 0;
          if (dx > 4) { mx = step; }
          else if (dx < -4) { mx = -step; }
          if (dy > 4) { my = step; }
          else if (dy < -4) { my = -step; }
          try_animal_move(animal, mx, my);
        }
        if (dist_q4 < 4 && !animal->cooldown && atype->damage > 0 && !g_player_iframes) {
          g_player_hp = (u8)clamp_int(g_player_hp - atype->damage, 0, 255);
          g_player_iframes = 40;
          g_player_flash = 40;
          animal->cooldown = 90;
          set_status("Wild creature attacks!", 60);
        }
      }
    }
  }
}

static void load_map(u8 map_id, int spawn_x, int spawn_y) {
  g_current_map = map_id;
  g_player_x_fp = (spawn_x * GBA_TILE_SIZE) << FP_SHIFT;
  g_player_y_fp = (spawn_y * GBA_TILE_SIZE) << FP_SHIFT;
  g_camera_x = spawn_x * GBA_TILE_SIZE + PLAYER_W / 2 - SCREEN_WIDTH / 2;
  g_camera_y = spawn_y * GBA_TILE_SIZE + PLAYER_H / 2 - SCREEN_HEIGHT / 2;
  g_attack_timer = 0;
  g_attack_cooldown = 0;
  g_player_iframes = 0;
  g_player_flash = 0;
  g_anim_frame = 0;
  g_anim_timer = 0;
  reset_runtime_flags();
  spawn_enemies_for_map();
  spawn_boss_for_map();
  spawn_animals_for_map();
  update_camera();
  fire_trigger(GBA_TRIGGER_MAP_ENTERED, gba_maps[map_id].name);
  {
    int wp;
    for (wp = 0; wp < GBA_WAYPOINT_COUNT; wp++) {
      if (gba_waypoints[wp].map_id == map_id) {
        g_waypoint_bits |= (u8)(1u << wp);
      }
    }
  }
  set_status(gba_maps[map_id].label, 60);
  pulse_objective(180);
  write_save();
}

static void start_new_game(void) {
  reset_progress();
  g_facing = FACE_DOWN;
  load_map(gba_stage_entry_maps[1], gba_maps[gba_stage_entry_maps[1]].spawn_x, gba_maps[gba_stage_entry_maps[1]].spawn_y);
  g_state = STATE_PLAY;
}

static int apply_half_heart_heal(const char *item_name) {
  /* Two half-hearts = one full heart. pygame's raw/cooked meat heals half a
   * heart per "use" so we accumulate to match. */
  if (g_player_hp >= player_max_hp()) {
    set_status("Already at full health.", 90);
    return 0;
  }
  if (g_half_heart_pending) {
    g_half_heart_pending = 0;
    g_player_hp = (u8)clamp_int(g_player_hp + 1, 0, player_max_hp());
    {
      char msg[48];
      copy_text(msg, sizeof(msg), "Ate ");
      {
        int len = string_length(msg);
        int name_len = string_length(item_name);
        int room = (int)sizeof(msg) - len - 1 - 8;
        if (name_len > room) name_len = room;
        if (name_len > 0) {
          int i;
          for (i = 0; i < name_len; i++) msg[len + i] = item_name[i];
          msg[len + name_len] = '\0';
        }
        copy_text(msg + string_length(msg), (int)sizeof(msg) - string_length(msg), "! +1 HP");
      }
      set_status(msg, 90);
    }
  } else {
    g_half_heart_pending = 1;
    char msg[48];
    copy_text(msg, sizeof(msg), "Ate ");
    {
      int len = string_length(msg);
      int name_len = string_length(item_name);
      int room = (int)sizeof(msg) - len - 1 - 10;
      if (name_len > room) name_len = room;
      if (name_len > 0) {
        int i;
        for (i = 0; i < name_len; i++) msg[len + i] = item_name[i];
        msg[len + name_len] = '\0';
      }
      copy_text(msg + string_length(msg), (int)sizeof(msg) - string_length(msg), "! +half HP");
    }
    set_status(msg, 90);
  }
  return 1;
}

static int try_use_inventory_item(int item_index) {
  if (item_index < 0 || item_index >= GBA_ITEM_COUNT || !inventory_has_item(item_index, 1)) {
    return 0;
  }

  switch (gba_items[item_index].use_effect) {
    case GBA_USE_EAT_RAW: {
      /* pygame: 2 raw meat per half-heart, 4 per full heart. */
      if (g_player_hp >= player_max_hp()) {
        set_status("Already at full health.", 90);
        return 0;
      }
      if (!inventory_has_item(item_index, 2)) {
        set_status("Need 2 raw meat to eat.", 90);
        return 0;
      }
      inventory_remove_item(gba_items[item_index].id, 2);
      apply_half_heart_heal(gba_items[item_index].name);
      write_save();
      return 1;
    }
    case GBA_USE_EAT_COOKED: {
      /* pygame: 1 cooked meat per half-heart, 2 per full heart. */
      if (g_player_hp >= player_max_hp()) {
        set_status("Already at full health.", 90);
        return 0;
      }
      inventory_remove_item(gba_items[item_index].id, 1);
      apply_half_heart_heal(gba_items[item_index].name);
      write_save();
      return 1;
    }
    case GBA_USE_HEAL: {
      if (g_player_hp >= player_max_hp()) {
        set_status("Already at full health.", 90);
        return 0;
      }
      {
        int heal = gba_items[item_index].heal_amount;
        if (heal < 1) heal = 1;
        g_player_hp = (u8)clamp_int(g_player_hp + heal, 0, player_max_hp());
      }
      inventory_remove_item(gba_items[item_index].id, 1);
      set_status("Item used.", 90);
      write_save();
      return 1;
    }
    case GBA_USE_CURE: {
      /* No poison system on GBA yet, but consume it so the action reads as
       * intentional and matches pygame behaviour of spending an antidote. */
      inventory_remove_item(gba_items[item_index].id, 1);
      set_status("Antidote used.", 90);
      write_save();
      return 1;
    }
    case GBA_USE_SKILL_POINT: {
      if (g_skill_points >= 255) {
        set_status("Max skill points.", 90);
        return 0;
      }
      g_skill_points = (u8)(g_skill_points + 1);
      inventory_remove_item(gba_items[item_index].id, 1);
      set_status("Gained a Skill Point!", 120);
      write_save();
      return 1;
    }
    default:
      break;
  }

  /* Fallback: equip gear directly from the list so the existing flow keeps
   * working even though weapons/armor normally flow through the hotbar. */
  if (gba_items[item_index].equip_slot != GBA_SLOT_NONE) {
    equip_item(item_index);
    write_save();
    return 1;
  }
  return 0;
}

static int max_int(int a, int b) {
  return a > b ? a : b;
}

static int tile_distance_q4(int ax_fp, int ay_fp, int bx_fp, int by_fp) {
  int dx = (abs_int(ax_fp - bx_fp) * 4) / (GBA_TILE_SIZE * FP_ONE);
  int dy = (abs_int(ay_fp - by_fp) * 4) / (GBA_TILE_SIZE * FP_ONE);
  return max_int(dx, dy);
}

static int front_tile_x(void) {
  int px = ((g_player_x_fp >> FP_SHIFT) + PLAYER_W / 2) / GBA_TILE_SIZE;
  if (g_facing == FACE_LEFT) {
    px--;
  } else if (g_facing == FACE_RIGHT) {
    px++;
  }
  return px;
}

static int front_tile_y(void) {
  int py = ((g_player_y_fp >> FP_SHIFT) + PLAYER_H / 2) / GBA_TILE_SIZE;
  if (g_facing == FACE_UP) {
    py--;
  } else if (g_facing == FACE_DOWN) {
    py++;
  }
  return py;
}

static void player_take_damage(int amount) {
  int reduced = amount - player_defense_bonus();
  if (g_player_iframes) {
    return;
  }
  if (reduced < 1) {
    reduced = 1;
  }
  if (g_player_hp > reduced) {
    g_player_hp = (u8)(g_player_hp - reduced);
  } else {
    g_player_hp = 0;
  }
  g_player_iframes = 45;
  g_player_flash = 10;
  set_status("You were hit!", 50);
}

static void grant_enemy_rewards(const GBAEnemyTypeDef *type) {
  int drop_index;
  for (drop_index = 0; drop_index < type->drop_count; drop_index++) {
    if (!random_percent(type->drops[drop_index].chance_pct)) {
      continue;
    }
    apply_reward(&type->drops[drop_index].reward, "Enemy drop.");
  }
}

static void on_boss_defeated(void) {
  int boss_index;
  int loot_index;
  if (!g_boss.active || !g_boss.def) {
    return;
  }
  for (boss_index = 0; boss_index < GBA_BOSS_COUNT; boss_index++) {
    if (&gba_bosses[boss_index] == g_boss.def) {
      bit_set(g_defeated_bosses, boss_index);
      bit_set(&g_boss_kill_bits, g_boss.def->stage - 1);
      break;
    }
  }
  fire_trigger(GBA_TRIGGER_BOSS_DEFEATED, g_boss.def->id);
  grant_xp(50 * g_boss.def->stage);
  for (loot_index = 0; loot_index < g_boss.def->loot_count; loot_index++) {
    if (!random_percent(g_boss.def->loot[loot_index].chance_pct)) {
      continue;
    }
    inventory_add_item(g_boss.def->loot[loot_index].item_id, 1);
  }
  bit_set(&g_completed_stage_bits, g_boss.def->stage - 1);
  if (g_boss.def->stage < 3) {
    g_world_stage = (u8)(g_boss.def->stage + 1);
    g_player_form = (u8)(g_boss.def->stage);
    g_player_hp = player_max_hp();
    g_stage_clear_target = g_world_stage;
    g_state = STATE_STAGE_INTRO;
  } else {
    g_state = STATE_VICTORY;
  }
  write_save();
}

static void perform_player_attack(void) {
  int index;
  int hit_count = 0;
  if (!has_weapon_equipped() || g_attack_cooldown) {
    if (!has_weapon_equipped()) {
      set_status("You need a weapon.", 60);
    }
    return;
  }
  g_attack_timer = 10;
  g_attack_cooldown = 18;
  for (index = 0; index < MAX_ACTIVE_ENEMIES; index++) {
    int dx;
    int dy;
    int hit = 0;
    const GBAEnemyTypeDef *type;
    if (!g_enemies[index].active) {
      continue;
    }
    dx = (g_enemies[index].x_fp - g_player_x_fp) >> FP_SHIFT;
    dy = (g_enemies[index].y_fp - g_player_y_fp) >> FP_SHIFT;
    if (abs_int(dx) > 22 || abs_int(dy) > 22) {
      continue;
    }
    if (g_facing == FACE_LEFT && dx < 0 && abs_int(dy) < 16) {
      hit = 1;
    } else if (g_facing == FACE_RIGHT && dx > 0 && abs_int(dy) < 16) {
      hit = 1;
    } else if (g_facing == FACE_UP && dy < 0 && abs_int(dx) < 16) {
      hit = 1;
    } else if (g_facing == FACE_DOWN && dy > 0 && abs_int(dx) < 16) {
      hit = 1;
    }
    if (!hit) {
      continue;
    }
    type = &gba_enemy_types[g_enemies[index].def->enemy_type_index];
    g_enemies[index].hp -= (s16)(1 + player_attack_bonus());
    g_enemies[index].flash_timer = 8;
    hit_count++;
    if (g_enemies[index].hp <= 0) {
      int spawn_index = (int)(g_enemies[index].def - gba_enemy_spawns);
      bit_set(g_defeated_enemies, spawn_index);
      g_enemies[index].active = 0;
      grant_enemy_rewards(type);
      grant_xp(5 + type->max_hp / 2);
      if (g_enemies[index].def->enemy_type_index < GBA_ENEMY_TYPE_COUNT) {
        g_enemy_kill_counts[g_enemies[index].def->enemy_type_index]++;
      }
      set_status("Enemy defeated.", 70);
      write_save();
    }
  }
  for (index = 0; index < MAX_ACTIVE_ANIMALS; index++) {
    int dx, dy, hit = 0;
    if (!g_animals[index].active || g_animals[index].state == ANIMAL_STATE_DEAD) {
      continue;
    }
    dx = (g_animals[index].x_fp - g_player_x_fp) >> FP_SHIFT;
    dy = (g_animals[index].y_fp - g_player_y_fp) >> FP_SHIFT;
    if (abs_int(dx) > 22 || abs_int(dy) > 22) {
      continue;
    }
    if (g_facing == FACE_LEFT && dx < 0 && abs_int(dy) < 16) { hit = 1; }
    else if (g_facing == FACE_RIGHT && dx > 0 && abs_int(dy) < 16) { hit = 1; }
    else if (g_facing == FACE_UP && dy < 0 && abs_int(dx) < 16) { hit = 1; }
    else if (g_facing == FACE_DOWN && dy > 0 && abs_int(dx) < 16) { hit = 1; }
    if (!hit) { continue; }
    g_animals[index].hp -= (s8)(1 + player_attack_bonus());
    g_animals[index].flash_timer = 8;
    if (g_animals[index].state != ANIMAL_STATE_AGGRO) {
      g_animals[index].state = ANIMAL_STATE_FLEE;
      g_animals[index].timer = 90;
    }
    hit_count++;
    if (g_animals[index].hp <= 0) {
      g_animals[index].state = ANIMAL_STATE_DEAD;
      g_animals[index].active = 0;
      bit_set(g_defeated_animals, g_animals[index].spawn_index);
      if (random_percent(80)) { inventory_add_item("raw_meat", 1); }
      if (random_percent(50)) { inventory_add_item("animal_hide", 1); }
      grant_xp(2 + gba_animal_types[g_animals[index].animal_type].max_hp);
      set_status("Animal slain.", 60);
      write_save();
    }
  }
  if (g_boss.active && g_boss.state != BOSS_DEAD) {
    int dx = (g_boss.x_fp - g_player_x_fp) >> FP_SHIFT;
    int dy = (g_boss.y_fp - g_player_y_fp) >> FP_SHIFT;
    int hit = 0;
    if (g_facing == FACE_LEFT && dx < 0 && abs_int(dy) < 24) {
      hit = 1;
    } else if (g_facing == FACE_RIGHT && dx > 0 && abs_int(dy) < 24) {
      hit = 1;
    } else if (g_facing == FACE_UP && dy < 0 && abs_int(dx) < 24) {
      hit = 1;
    } else if (g_facing == FACE_DOWN && dy > 0 && abs_int(dx) < 24) {
      hit = 1;
    }
    if (hit) {
      g_boss.hp -= (s16)(1 + player_attack_bonus());
      g_boss.flash_timer = 10;
      hit_count++;
      if (g_boss.def->stage == 2 && g_boss.hp * 2 <= 30) {
        g_boss.phase = 2;
      }
      if (g_boss.def->stage == 3) {
        if (g_boss.hp * 100 <= 30 * 50) {
          g_boss.phase = 3;
        } else if (g_boss.hp * 100 <= 65 * 50) {
          g_boss.phase = 2;
        }
      }
      if (g_boss.hp <= 0) {
        g_boss.hp = 0;
        g_boss.state = BOSS_DEAD;
        on_boss_defeated();
      }
    }
  }
  if (!hit_count) {
    set_status("Attack missed.", 40);
  }
}

static void update_enemy_runtime(void) {
  int index;
  const GBAMap *map = &gba_maps[g_current_map];
  for (index = 0; index < MAX_ACTIVE_ENEMIES; index++) {
    EnemyRuntime *enemy = &g_enemies[index];
    const GBAEnemyTypeDef *type;
    int dx_fp;
    int dy_fp;
    int step_fp;
    if (!enemy->active) {
      continue;
    }
    type = &gba_enemy_types[enemy->def->enemy_type_index];
    if (enemy->cooldown) {
      enemy->cooldown--;
    }
    if (enemy->flash_timer) {
      enemy->flash_timer--;
    }
    dx_fp = g_player_x_fp - enemy->x_fp;
    dy_fp = g_player_y_fp - enemy->y_fp;
    if (tile_distance_q4(enemy->x_fp, enemy->y_fp, g_player_x_fp, g_player_y_fp) <= type->attack_range_q4) {
      if (!enemy->cooldown) {
        player_take_damage(enemy_contact_damage(enemy->def->enemy_type_index));
        enemy->cooldown = type->attack_cooldown_frames;
      }
      continue;
    }
    if (tile_distance_q4(enemy->x_fp, enemy->y_fp, g_player_x_fp, g_player_y_fp) > type->chase_range_q4) {
      continue;
    }
    step_fp = type->speed_fp / 4;
    if (abs_int(dx_fp) > abs_int(dy_fp)) {
      int next_x = (enemy->x_fp + (dx_fp > 0 ? step_fp : -step_fp)) >> FP_SHIFT;
      int current_y = enemy->y_fp >> FP_SHIFT;
      if (can_move_to(map, next_x, current_y)) {
        enemy->x_fp += (dx_fp > 0 ? step_fp : -step_fp);
      }
    } else {
      int current_x = enemy->x_fp >> FP_SHIFT;
      int next_y = (enemy->y_fp + (dy_fp > 0 ? step_fp : -step_fp)) >> FP_SHIFT;
      if (can_move_to(map, current_x, next_y)) {
        enemy->y_fp += (dy_fp > 0 ? step_fp : -step_fp);
      }
    }
  }
}

static void update_boss_runtime(void) {
  int dx_fp;
  int dy_fp;
  const GBAMap *map = &gba_maps[g_current_map];
  if (!g_boss.active || !g_boss.def || g_boss.state == BOSS_DEAD) {
    return;
  }
  if (g_boss.flash_timer) {
    g_boss.flash_timer--;
  }
  dx_fp = g_player_x_fp - g_boss.x_fp;
  dy_fp = g_player_y_fp - g_boss.y_fp;
  if (g_boss.state == BOSS_DORMANT && tile_distance_q4(g_boss.x_fp, g_boss.y_fp, g_player_x_fp, g_player_y_fp) < 24) {
    g_boss.state = BOSS_WAKE;
    g_boss.state_timer = 30;
    set_status("A boss approaches!", 90);
  }
  if (g_boss.cooldown) {
    g_boss.cooldown--;
  }
  if (g_boss.state_timer) {
    g_boss.state_timer--;
  }
  if (g_boss.state == BOSS_WAKE) {
    if (!g_boss.state_timer) {
      g_boss.state = BOSS_CHASE;
    }
    return;
  }
  if (g_boss.state == BOSS_SLAM || g_boss.state == BOSS_SPIN || g_boss.state == BOSS_WAVE || g_boss.state == BOSS_RIFT) {
    if (!g_boss.damage_done && g_boss.state_timer < 12 &&
        tile_distance_q4(g_boss.x_fp, g_boss.y_fp, g_player_x_fp, g_player_y_fp) <
            (g_boss.state == BOSS_RIFT ? 24 : (g_boss.state == BOSS_WAVE ? 18 : 12))) {
      player_take_damage(g_boss.def->stage + 1);
      g_boss.damage_done = 1;
    }
    if (!g_boss.state_timer) {
      g_boss.state = BOSS_CHASE;
      g_boss.cooldown = (u8)(30 - g_boss.phase * 4);
      g_boss.damage_done = 0;
    }
    return;
  }
  if (g_boss.state == BOSS_CHARGE) {
    int move_fp = (4 + g_boss.phase) * 32;
    if (abs_int(dx_fp) > abs_int(dy_fp)) {
      int next_x = (g_boss.x_fp + (dx_fp > 0 ? move_fp : -move_fp)) >> FP_SHIFT;
      int current_y = g_boss.y_fp >> FP_SHIFT;
      if (can_move_to(map, next_x, current_y)) {
        g_boss.x_fp += (dx_fp > 0 ? move_fp : -move_fp);
      }
    } else {
      int current_x = g_boss.x_fp >> FP_SHIFT;
      int next_y = (g_boss.y_fp + (dy_fp > 0 ? move_fp : -move_fp)) >> FP_SHIFT;
      if (can_move_to(map, current_x, next_y)) {
        g_boss.y_fp += (dy_fp > 0 ? move_fp : -move_fp);
      }
    }
    if (!g_boss.damage_done && tile_distance_q4(g_boss.x_fp, g_boss.y_fp, g_player_x_fp, g_player_y_fp) < 8) {
      player_take_damage(g_boss.def->stage + 1);
      g_boss.damage_done = 1;
    }
    if (!g_boss.state_timer) {
      g_boss.state = BOSS_CHASE;
      g_boss.cooldown = 24;
      g_boss.damage_done = 0;
    }
    return;
  }
  if (!g_boss.cooldown) {
    u32 roll = random_u32() % 100u;
    g_boss.damage_done = 0;
    if (g_boss.def->stage == 3 && g_boss.phase == 3 && roll > 75u) {
      g_boss.state = BOSS_RIFT;
      g_boss.state_timer = 28;
    } else if (g_boss.def->stage == 3 && g_boss.phase >= 2 && roll > 60u) {
      g_boss.state = BOSS_WAVE;
      g_boss.state_timer = 24;
    } else if (roll > 65u) {
      g_boss.state = BOSS_CHARGE;
      g_boss.state_timer = 18;
    } else if (roll > 35u) {
      g_boss.state = BOSS_SPIN;
      g_boss.state_timer = 20;
    } else {
      g_boss.state = BOSS_SLAM;
      g_boss.state_timer = 18;
    }
    return;
  }
  if (tile_distance_q4(g_boss.x_fp, g_boss.y_fp, g_player_x_fp, g_player_y_fp) < 8) {
    int move_fp = (2 + g_boss.phase) * 20;
    if (abs_int(dx_fp) > abs_int(dy_fp)) {
      int next_x = (g_boss.x_fp + (dx_fp > 0 ? move_fp : -move_fp)) >> FP_SHIFT;
      int current_y = g_boss.y_fp >> FP_SHIFT;
      if (can_move_to(map, next_x, current_y)) {
        g_boss.x_fp += (dx_fp > 0 ? move_fp : -move_fp);
      }
    } else {
      int current_x = g_boss.x_fp >> FP_SHIFT;
      int next_y = (g_boss.y_fp + (dy_fp > 0 ? move_fp : -move_fp)) >> FP_SHIFT;
      if (can_move_to(map, current_x, next_y)) {
        g_boss.y_fp += (dy_fp > 0 ? move_fp : -move_fp);
      }
    }
  }
}

static void update_dialogue(void) {
  const char *page;
  if (!g_dialogue.active) {
    return;
  }
  page = g_dialogue.pages[g_dialogue.page_index];
  if (g_dialogue.chars_visible < string_length(page)) {
    g_dialogue.char_timer++;
    if (g_dialogue.char_timer >= 1) {
      g_dialogue.char_timer = 0;
      g_dialogue.chars_visible++;
    }
  }
  if (g_input.pressed & KEY_A) {
    if (g_dialogue.chars_visible < string_length(page)) {
      g_dialogue.chars_visible = (u8)string_length(page);
    } else if (g_dialogue.page_index + 1 < g_dialogue.page_count) {
      g_dialogue.page_index++;
      g_dialogue.chars_visible = 0;
      g_dialogue.char_timer = 0;
    } else {
      g_dialogue.active = 0;
      process_dialogue_actions();
      write_save();
    }
  }
  if (g_input.pressed & KEY_B) {
    g_dialogue.active = 0;
    process_dialogue_actions();
    write_save();
  }
}

static void update_player_animation(int moving) {
  if (!moving) {
    g_anim_frame = 0;
    g_anim_timer = 0;
    return;
  }
  g_anim_timer++;
  if (g_anim_timer >= 8) {
    g_anim_timer = 0;
    g_anim_frame = (u8)((g_anim_frame + 1) & 3);
  }
}

static void try_collect_tile_items(void) {
  int tile_x = (g_player_x_fp >> FP_SHIFT) / GBA_TILE_SIZE;
  int tile_y = (g_player_y_fp >> FP_SHIFT) / GBA_TILE_SIZE;
  int index;
  for (index = 0; index < GBA_GROUND_ITEM_COUNT; index++) {
    if (bit_test(g_collected_ground, index) || gba_ground_items[index].map_id != g_current_map) {
      continue;
    }
    if (gba_ground_items[index].tile_x == tile_x && gba_ground_items[index].tile_y == tile_y) {
      if (apply_reward(&gba_ground_items[index].reward, "Picked up item.")) {
        bit_set(g_collected_ground, index);
        write_save();
      }
    }
  }
  for (index = 0; index < GBA_LORE_COUNT; index++) {
    if (bit_test(g_collected_lore, index) || gba_lore_items[index].map_id != g_current_map) {
      continue;
    }
    if (gba_lore_items[index].tile_x == tile_x && gba_lore_items[index].tile_y == tile_y) {
      bit_set(g_collected_lore, index);
      inventory_add_item("lore_fragment", 1);
      open_dialogue("Lore", gba_lore_items[index].pages, gba_lore_items[index].page_count);
      write_save();
      return;
    }
  }
}

static int npc_in_range(const GBANpcDef *npc) {
  int fx = front_tile_x();
  int fy = front_tile_y();
  int cx = ((g_player_x_fp >> FP_SHIFT) + PLAYER_W / 2) / GBA_TILE_SIZE;
  int cy = ((g_player_y_fp >> FP_SHIFT) + PLAYER_H / 2) / GBA_TILE_SIZE;
  if (npc->map_id != g_current_map) { return 0; }
  if (npc->tile_x == fx && npc->tile_y == fy) { return 1; }
  if (abs_int(npc->tile_x - cx) <= 1 && abs_int(npc->tile_y - cy) <= 1) { return 1; }
  return 0;
}

static void handle_interaction(void) {
  int tile_x = front_tile_x();
  int tile_y = front_tile_y();
  int index;
  for (index = 0; index < GBA_NPC_COUNT; index++) {
    int variant_index;
    const GBANpcDef *npc = &gba_npcs[index];
    if (!npc_in_range(npc)) {
      continue;
    }
    variant_index = npc_dialogue_variant_index(npc);
    g_dialogue.pending_npc_trigger = npc->npc_id;
    g_dialogue.pending_give = 0;
    g_dialogue.pending_take = 0;
    if (npc->give_stage >= 0) {
      int quest_index = gba_stage_quest_index[gba_map_stage[g_current_map]];
      if (g_quest_stage[quest_index] == npc->give_stage) {
        int item_index = find_item_index(npc->give_item_id);
        if (item_index >= 0 && !inventory_has_item(item_index, 1)) {
          g_dialogue.pending_give = (u8)(item_index + 1);
        }
      }
    }
    if (npc->take_stage >= 0) {
      int quest_index = gba_stage_quest_index[gba_map_stage[g_current_map]];
      if (g_quest_stage[quest_index] == npc->take_stage) {
        int item_index = find_item_index(npc->take_item_id);
        if (item_index >= 0 && inventory_has_item(item_index, 1)) {
          g_dialogue.pending_take = (u8)(item_index + 1);
        }
      }
    }
    open_dialogue(npc->name, npc->variants[variant_index].pages, npc->variants[variant_index].page_count);
    return;
  }
  for (index = 0; index < GBA_CHEST_COUNT; index++) {
    if (bit_test(g_opened_chests, index) || gba_chests[index].map_id != g_current_map ||
        gba_chests[index].tile_x != tile_x || gba_chests[index].tile_y != tile_y) {
      continue;
    }
    if (apply_reward(&gba_chests[index].reward, gba_chests[index].label)) {
      bit_set(g_opened_chests, index);
      open_single_page_dialogue(gba_chests[index].label, "Treasure claimed.");
      write_save();
    }
    return;
  }
  for (index = 0; index < GBA_SIGN_COUNT; index++) {
    if (gba_signs[index].map_id == g_current_map &&
        gba_signs[index].tile_x == tile_x &&
        gba_signs[index].tile_y == tile_y) {
      open_dialogue("Sign", gba_signs[index].pages, gba_signs[index].page_count);
      return;
    }
  }
}

static void check_map_exit(void) {
  const GBAMap *map = &gba_maps[g_current_map];
  int center_x = ((g_player_x_fp >> FP_SHIFT) + PLAYER_W / 2) / GBA_TILE_SIZE;
  int center_y = ((g_player_y_fp >> FP_SHIFT) + PLAYER_H / 2) / GBA_TILE_SIZE;
  int index;
  for (index = 0; index < map->exit_count; index++) {
    const GBAExit *exit = &map->exits[index];
    if (exit->x != center_x || exit->y != center_y) {
      continue;
    }
    if (exit->target_map == MAP_RUINS_APPROACH && g_world_stage < 2) {
      set_status("The eastern ruins remain sealed.", 90);
      return;
    }
    if (exit->target_map == MAP_SANCTUM_HALLS && g_world_stage < 3) {
      set_status("A greater evil still bars the sanctum.", 90);
      return;
    }
    load_map(exit->target_map, exit->target_x, exit->target_y);
    return;
  }
}

static void update_title(void) {
  if (g_input.pressed & KEY_UP) {
    if (g_title_cursor > 0) {
      g_title_cursor--;
    }
  }
  if (g_input.pressed & KEY_DOWN) {
    if (g_title_cursor < 2) {
      g_title_cursor++;
    }
  }
  if (g_input.pressed & (KEY_A | KEY_START)) {
    if (g_title_cursor == 0) {
      if (g_continue_available && load_save()) {
        load_map(g_current_map, (g_player_x_fp >> FP_SHIFT) / GBA_TILE_SIZE, (g_player_y_fp >> FP_SHIFT) / GBA_TILE_SIZE);
        g_state = STATE_PLAY;
      } else {
        start_new_game();
      }
    } else if (g_title_cursor == 1) {
      start_new_game();
    } else {
      g_state = STATE_HELP;
    }
  }
}

static void update_inventory(void) {
  int visible_indices[GBA_ITEM_COUNT];
  int visible_count = 0;
  int index;
  for (index = 0; index < GBA_ITEM_COUNT; index++) {
    if (g_item_counts[index]) {
      visible_indices[visible_count++] = index;
    }
  }
  if (g_input.pressed & KEY_UP && g_inventory_cursor > 0) {
    g_inventory_cursor--;
  }
  if (g_input.pressed & KEY_DOWN && g_inventory_cursor + 1 < visible_count) {
    g_inventory_cursor++;
  }
  if (visible_count == 0) {
    g_inventory_cursor = 0;
  } else if (g_inventory_cursor >= visible_count) {
    g_inventory_cursor = (u8)(visible_count - 1);
  }
  if (g_input.pressed & KEY_A && visible_count > 0) {
    try_use_inventory_item(visible_indices[g_inventory_cursor]);
  }
  if (g_input.pressed & KEY_L) {
    g_active_hotbar = (u8)((g_active_hotbar + HOTBAR_SLOTS - 1) & (HOTBAR_SLOTS - 1));
  }
  if (g_input.pressed & KEY_R) {
    g_active_hotbar = (u8)((g_active_hotbar + 1) & (HOTBAR_SLOTS - 1));
  }
  if (g_input.pressed & KEY_SELECT && visible_count > 0) {
    int item_index = visible_indices[g_inventory_cursor];
    if (item_is_hotbar_eligible(item_index)) {
      assign_active_hotbar(item_index);
      sync_active_hotbar_weapon();
      set_status("Assigned to hotbar.", 60);
    } else {
      set_status("Not hotbar-eligible.", 60);
    }
  }
  if (g_input.pressed & (KEY_B | KEY_START)) {
    g_state = STATE_PLAY;
  }
}

static void update_help(void) {
  if (g_input.pressed & (KEY_B | KEY_START | KEY_SELECT)) {
    g_state = STATE_TITLE;
  }
}

static void update_game_over(void) {
  if (g_input.pressed & (KEY_A | KEY_START)) {
    g_player_hp = player_max_hp();
    load_map(g_current_map, gba_maps[g_current_map].spawn_x, gba_maps[g_current_map].spawn_y);
    g_state = STATE_PLAY;
  }
}

static void update_stage_intro(void) {
  if (g_input.pressed & (KEY_A | KEY_START)) {
    g_state = STATE_STAGE_CLEAR;
  }
}

static void render_stage_intro(void) {
  begin_ui_scene(GBA_UI_TILE_FILL_ALT);
  ui_draw_box(3, 3, 24, 14, 1);
  ui_draw_text_centered(5, gba_stage_names[g_stage_clear_target], 1);
  ui_draw_text_centered(8, "A NEW CHAPTER BEGINS", 0);
  ui_draw_text(6, 10, "FORM", 1);
  ui_draw_text(11, 10, player_form_name(), 0);
  {
    char lvl[16];
    int_to_text(g_level, lvl, sizeof(lvl));
    ui_draw_text(6, 12, "LEVEL", 1);
    ui_draw_text(12, 12, lvl, 0);
  }
  ui_draw_text_centered(15, "A CONTINUE", 0);
}

static void update_stage_clear(void) {
  if (g_input.pressed & (KEY_A | KEY_START)) {
    load_map(gba_stage_entry_maps[g_stage_clear_target], gba_maps[gba_stage_entry_maps[g_stage_clear_target]].spawn_x, gba_maps[gba_stage_entry_maps[g_stage_clear_target]].spawn_y);
    g_state = STATE_PLAY;
  }
}

static void update_victory(void) {
  if (g_input.pressed & (KEY_A | KEY_START)) {
    g_state = STATE_TITLE;
  }
}

static void update_pause(void) {
  if (g_input.pressed & KEY_UP) { if (g_pause_cursor > 0) { g_pause_cursor--; } }
  if (g_input.pressed & KEY_DOWN) { if (g_pause_cursor < 7) { g_pause_cursor++; } }
  if (g_input.pressed & (KEY_B | KEY_START)) { g_state = STATE_PLAY; return; }
  if (g_input.pressed & KEY_A) {
    switch (g_pause_cursor) {
      case 0: g_state = STATE_PLAY; break;
      case 1: g_state = STATE_INVENTORY; break;
      case 2: g_crafting_cursor = 0; g_state = STATE_CRAFTING; break;
      case 3: g_skills_cursor = 0; g_state = STATE_SKILLS; break;
      case 4: g_bestiary_cursor = 0; g_state = STATE_BESTIARY; break;
      case 5: g_travel_cursor = 0; g_state = STATE_TRAVEL; break;
      case 6: write_save(); set_status("Game saved.", 90); g_state = STATE_PLAY; break;
      case 7: g_state = STATE_TITLE; break;
    }
  }
}

static void render_pause(void) {
  int row;
  static const char *labels[8] = {"RESUME", "INVENTORY", "CRAFTING", "SKILLS", "BESTIARY", "TRAVEL", "SAVE", "QUIT"};
  begin_ui_scene(GBA_UI_TILE_FILL_ALT);
  ui_draw_box(4, 0, 22, 20, 1);
  ui_draw_text_centered(1, "PAUSED", 1);
  for (row = 0; row < 8; row++) {
    ui_draw_text(7, 3 + row * 2, g_pause_cursor == row ? ">" : " ", g_pause_cursor == row);
    ui_draw_text(9, 3 + row * 2, labels[row], g_pause_cursor == row);
  }
  ui_draw_text(7, 19, "GOAL", 1);
  ui_draw_text_clipped(12, 19, 14, current_quest_brief(), 0);
  ui_draw_text(22, 1, weather_name(), 0);
}

static int can_craft(int recipe_index) {
  int i;
  const GBARecipeDef *r = &gba_recipes[recipe_index];
  for (i = 0; i < r->ingredient_count; i++) {
    int idx = find_item_index(r->ingredients[i].item_id);
    if (idx < 0 || !inventory_has_item(idx, r->ingredients[i].qty)) { return 0; }
  }
  return 1;
}

static void do_craft(int recipe_index) {
  int i;
  const GBARecipeDef *r = &gba_recipes[recipe_index];
  for (i = 0; i < r->ingredient_count; i++) {
    int idx = find_item_index(r->ingredients[i].item_id);
    int q;
    for (q = 0; q < r->ingredients[i].qty; q++) {
      inventory_remove_item(gba_items[idx].id, 1);
    }
  }
  inventory_add_item(r->output_id, r->output_qty);
  set_status("Crafted!", 60);
  write_save();
}

static void update_crafting(void) {
  if (g_input.pressed & KEY_UP) { if (g_crafting_cursor > 0) { g_crafting_cursor--; } }
  if (g_input.pressed & KEY_DOWN) { if (g_crafting_cursor < GBA_RECIPE_COUNT - 1) { g_crafting_cursor++; } }
  if (g_input.pressed & KEY_A) {
    if (can_craft(g_crafting_cursor)) { do_craft(g_crafting_cursor); }
    else { set_status("Missing ingredients.", 60); }
  }
  if (g_input.pressed & (KEY_B | KEY_START)) { g_pause_cursor = 2; g_state = STATE_PAUSE; }
}

static void render_crafting(void) {
  int index, first = 0, rows = 8;
  char qty_buf[8];
  begin_ui_scene(GBA_UI_TILE_FILL_ALT);
  ui_draw_box(0, 0, 30, 20, 1);
  ui_draw_text(2, 1, "CRAFTING", 1);
  if (g_crafting_cursor >= rows) { first = g_crafting_cursor - rows + 1; }
  for (index = first; index < GBA_RECIPE_COUNT && index < first + rows; index++) {
    int row_y = 3 + (index - first);
    const GBARecipeDef *r = &gba_recipes[index];
    int ok = can_craft(index);
    ui_draw_text(2, row_y, index == g_crafting_cursor ? ">" : " ", index == g_crafting_cursor);
    ui_draw_text_clipped(3, row_y, 10, gba_items[find_item_index(r->output_id)].name, ok);
    int_to_text(r->output_qty, qty_buf, sizeof(qty_buf));
    ui_draw_text(14, row_y, "x", 0);
    ui_draw_text(15, row_y, qty_buf, 0);
  }
  if (g_crafting_cursor < GBA_RECIPE_COUNT) {
    const GBARecipeDef *r = &gba_recipes[g_crafting_cursor];
    int i;
    ui_draw_text(2, 12, "NEEDS", 1);
    for (i = 0; i < r->ingredient_count; i++) {
      int idx = find_item_index(r->ingredients[i].item_id);
      int have = idx >= 0 ? g_item_counts[idx] : 0;
      char need[8], hav[8];
      int_to_text(r->ingredients[i].qty, need, sizeof(need));
      int_to_text(have, hav, sizeof(hav));
      ui_draw_text_clipped(3, 13 + i, 9, idx >= 0 ? gba_items[idx].name : "???", have >= r->ingredients[i].qty);
      ui_draw_text(13, 13 + i, hav, 0);
      ui_draw_text(15, 13 + i, "/", 0);
      ui_draw_text(16, 13 + i, need, 0);
    }
  }
  if (g_status_timer && g_status_text[0]) {
    ui_draw_text_clipped(2, 17, 26, g_status_text, 1);
  }
  ui_draw_text_centered(18, "A CRAFT  B BACK", 0);
}

static void update_skills(void) {
  if (g_input.pressed & KEY_UP) { if (g_skills_cursor > 0) { g_skills_cursor--; } }
  if (g_input.pressed & KEY_DOWN) { if (g_skills_cursor < 2) { g_skills_cursor++; } }
  if (g_input.pressed & KEY_A && g_skill_points > 0) {
    if (g_skills_cursor == 0 && g_skill_atk < 10) { g_skill_atk++; g_skill_points--; set_status("+1 ATK", 60); }
    else if (g_skills_cursor == 1 && g_skill_def < 10) { g_skill_def++; g_skill_points--; set_status("+1 DEF", 60); }
    else if (g_skills_cursor == 2 && g_skill_hp < 10) { g_skill_hp++; g_skill_points--; set_status("+1 HP", 60); }
    write_save();
  }
  if (g_input.pressed & (KEY_B | KEY_START)) { g_pause_cursor = 3; g_state = STATE_PAUSE; }
}

static void render_skills(void) {
  char buf[8];
  begin_ui_scene(GBA_UI_TILE_FILL_ALT);
  ui_draw_box(3, 1, 24, 18, 1);
  ui_draw_text_centered(2, "SKILLS", 1);
  ui_draw_text(6, 4, "POINTS", 1);
  int_to_text(g_skill_points, buf, sizeof(buf));
  ui_draw_text(13, 4, buf, 1);
  ui_draw_text(6, 7, g_skills_cursor == 0 ? "> ATTACK" : "  ATTACK", g_skills_cursor == 0);
  int_to_text(g_skill_atk, buf, sizeof(buf));
  ui_draw_text(18, 7, buf, 0);
  ui_draw_text(20, 7, "/10", 0);
  ui_draw_text(6, 9, g_skills_cursor == 1 ? "> DEFENSE" : "  DEFENSE", g_skills_cursor == 1);
  int_to_text(g_skill_def, buf, sizeof(buf));
  ui_draw_text(18, 9, buf, 0);
  ui_draw_text(20, 9, "/10", 0);
  ui_draw_text(6, 11, g_skills_cursor == 2 ? "> MAX HP" : "  MAX HP", g_skills_cursor == 2);
  int_to_text(g_skill_hp, buf, sizeof(buf));
  ui_draw_text(18, 11, buf, 0);
  ui_draw_text(20, 11, "/10", 0);
  ui_draw_text(6, 14, "LEVEL", 1);
  int_to_text(g_level, buf, sizeof(buf));
  ui_draw_text(12, 14, buf, 0);
  ui_draw_text(6, 15, "FORM", 1);
  ui_draw_text(12, 15, player_form_name(), 0);
  if (g_status_timer && g_status_text[0]) {
    ui_draw_text_clipped(5, 16, 20, g_status_text, 1);
  }
  ui_draw_text_centered(18, "A SPEND  B BACK", 0);
}

static void update_bestiary(void) {
  if (g_input.pressed & KEY_UP) { if (g_bestiary_cursor > 0) { g_bestiary_cursor--; } }
  if (g_input.pressed & KEY_DOWN) { if (g_bestiary_cursor < GBA_ENEMY_TYPE_COUNT - 1) { g_bestiary_cursor++; } }
  if (g_input.pressed & (KEY_B | KEY_START)) { g_pause_cursor = 4; g_state = STATE_PAUSE; }
}

static void render_bestiary(void) {
  int index, first = 0, rows = 10;
  char buf[8];
  begin_ui_scene(GBA_UI_TILE_FILL_ALT);
  ui_draw_box(0, 0, 30, 20, 1);
  ui_draw_text(2, 1, "BESTIARY", 1);
  if (g_bestiary_cursor >= rows) { first = g_bestiary_cursor - rows + 1; }
  for (index = first; index < GBA_ENEMY_TYPE_COUNT && index < first + rows; index++) {
    int row_y = 3 + (index - first);
    int discovered = g_enemy_kill_counts[index] > 0;
    ui_draw_text(2, row_y, index == g_bestiary_cursor ? ">" : " ", index == g_bestiary_cursor);
    if (discovered) {
      ui_draw_text_clipped(3, row_y, 12, gba_enemy_types[index].id, index == g_bestiary_cursor);
    } else {
      ui_draw_text(3, row_y, "???", 0);
    }
    int_to_text(g_enemy_kill_counts[index], buf, sizeof(buf));
    ui_draw_text(18, row_y, buf, 0);
    ui_draw_text(21, row_y, "KILLS", 0);
  }
  if (g_bestiary_cursor < GBA_ENEMY_TYPE_COUNT && g_enemy_kill_counts[g_bestiary_cursor] >= 3) {
    char hp[8], dmg[8];
    int_to_text(gba_enemy_types[g_bestiary_cursor].max_hp, hp, sizeof(hp));
    int_to_text(gba_enemy_types[g_bestiary_cursor].damage, dmg, sizeof(dmg));
    ui_draw_text(2, 15, "HP", 1);
    ui_draw_text(5, 15, hp, 0);
    ui_draw_text(10, 15, "DMG", 1);
    ui_draw_text(14, 15, dmg, 0);
  }
  ui_draw_text_centered(18, "B BACK", 0);
}

static void update_travel(void) {
  int max_idx = -1;
  int i;
  for (i = GBA_WAYPOINT_COUNT - 1; i >= 0; i--) {
    if (g_waypoint_bits & (1u << i)) { max_idx = i; break; }
  }
  if (max_idx < 0) { g_state = STATE_PAUSE; return; }
  if (g_input.pressed & KEY_UP) { if (g_travel_cursor > 0) { g_travel_cursor--; } }
  if (g_input.pressed & KEY_DOWN) { if (g_travel_cursor < max_idx) { g_travel_cursor++; } }
  if (g_input.pressed & KEY_A) {
    if (g_waypoint_bits & (1u << g_travel_cursor)) {
      load_map(gba_waypoints[g_travel_cursor].map_id, gba_waypoints[g_travel_cursor].tile_x, gba_waypoints[g_travel_cursor].tile_y);
      set_status("Traveled!", 60);
      g_state = STATE_PLAY;
    }
  }
  if (g_input.pressed & (KEY_B | KEY_START)) { g_pause_cursor = 5; g_state = STATE_PAUSE; }
}

static void render_travel(void) {
  int index;
  begin_ui_scene(GBA_UI_TILE_FILL_ALT);
  ui_draw_box(2, 1, 26, 18, 1);
  ui_draw_text_centered(2, "FAST TRAVEL", 1);
  for (index = 0; index < GBA_WAYPOINT_COUNT; index++) {
    int unlocked = (g_waypoint_bits >> index) & 1;
    ui_draw_text(4, 4 + index * 2, index == g_travel_cursor ? ">" : " ", index == g_travel_cursor);
    if (unlocked) {
      ui_draw_text_clipped(6, 4 + index * 2, 18, gba_waypoints[index].id, index == g_travel_cursor);
    } else {
      ui_draw_text(6, 4 + index * 2, "???", 0);
    }
  }
  ui_draw_text_centered(18, "A TRAVEL  B BACK", 0);
}

static void update_weather(void) {
  if (g_weather_timer) {
    g_weather_timer--;
    return;
  }
  g_weather_timer = (u8)(180 + (random_u32() & 127));
  g_weather_state = (u8)(random_u32() % 4u);
}

static void update_play(void) {
  const GBAMap *map = &gba_maps[g_current_map];
  int move_x = 0;
  int move_y = 0;
  int moving = 0;
  int step = player_speed_fp();
  if (g_status_timer) {
    g_status_timer--;
  }
  if (g_objective_timer) {
    g_objective_timer--;
  }
  if (g_dialogue.active) {
    update_dialogue();
    return;
  }
  if (g_player_iframes) {
    g_player_iframes--;
  }
  if (g_player_flash) {
    g_player_flash--;
  }
  if (g_attack_cooldown) {
    g_attack_cooldown--;
  }
  if (g_attack_timer) {
    g_attack_timer--;
  }
  if (g_input.pressed & KEY_START) {
    g_pause_cursor = 0;
    g_state = STATE_PAUSE;
    return;
  }
  if (g_input.pressed & KEY_L) {
    g_active_hotbar = (u8)((g_active_hotbar + HOTBAR_SLOTS - 1) & (HOTBAR_SLOTS - 1));
    sync_active_hotbar_weapon();
    {
      int item = g_hotbar[g_active_hotbar];
      set_status(item >= 0 ? gba_items[item].name : "Empty slot", 40);
    }
  }
  if (g_input.pressed & KEY_R) {
    g_active_hotbar = (u8)((g_active_hotbar + 1) & (HOTBAR_SLOTS - 1));
    sync_active_hotbar_weapon();
    {
      int item = g_hotbar[g_active_hotbar];
      set_status(item >= 0 ? gba_items[item].name : "Empty slot", 40);
    }
  }
  if (g_input.pressed & KEY_SELECT) {
    int item = g_hotbar[g_active_hotbar];
    if (item >= 0 && gba_items[item].heal_amount > 0 && g_item_counts[item] > 0) {
      try_use_inventory_item(item);
    } else {
      write_save();
      set_status("Game saved.", 90);
    }
  }
  if (g_input.pressed & KEY_A) {
    perform_player_attack();
  }
  if (g_input.pressed & KEY_B) {
    handle_interaction();
    if (g_dialogue.active) {
      return;
    }
  }
  if (g_input.held & KEY_LEFT) {
    move_x -= step;
    g_facing = FACE_LEFT;
  }
  if (g_input.held & KEY_RIGHT) {
    move_x += step;
    g_facing = FACE_RIGHT;
  }
  if (g_input.held & KEY_UP) {
    move_y -= step;
    g_facing = FACE_UP;
  }
  if (g_input.held & KEY_DOWN) {
    move_y += step;
    g_facing = FACE_DOWN;
  }
  if (move_x != 0 && move_y != 0) {
    move_x = (move_x * 3) / 4;
    move_y = (move_y * 3) / 4;
  }
  if (move_x != 0) {
    int next_x = (g_player_x_fp + move_x) >> FP_SHIFT;
    int current_y = g_player_y_fp >> FP_SHIFT;
    if (can_move_to(map, next_x, current_y)) {
      g_player_x_fp += move_x;
      moving = 1;
    }
  }
  if (move_y != 0) {
    int current_x = g_player_x_fp >> FP_SHIFT;
    int next_y = (g_player_y_fp + move_y) >> FP_SHIFT;
    if (can_move_to(map, current_x, next_y)) {
      g_player_y_fp += move_y;
      moving = 1;
    }
  }
  update_player_animation(moving);
  update_enemy_runtime();
  update_boss_runtime();
  update_animal_runtime();
  update_weather();
  try_collect_tile_items();
  update_camera();
  check_map_exit();
  if (g_player_hp == 0) {
    g_state = STATE_GAME_OVER;
  }
}

static void draw_world(const GBAMap *map) {
  (void)map;
  sync_world_window();
}

static void render_world_entities(void) {
  int index;
  int pulse = (int)((g_frame_counter >> 3) & 1u);
  for (index = 0; index < GBA_GROUND_ITEM_COUNT; index++) {
    if (bit_test(g_collected_ground, index) || gba_ground_items[index].map_id != g_current_map) {
      continue;
    }
    emit_sprite(
        gba_ground_items[index].tile_x * GBA_TILE_SIZE - g_camera_x + 4,
        gba_ground_items[index].tile_y * GBA_TILE_SIZE - g_camera_y + 4 - pulse,
        (u16)(gba_ground_items[index].reward.kind == GBA_REWARD_CURRENCY ? GBA_OBJ_ICON_COIN_BASE : GBA_OBJ_ICON_ITEM_BASE),
        8,
        1);
  }
  for (index = 0; index < GBA_LORE_COUNT; index++) {
    if (bit_test(g_collected_lore, index) || gba_lore_items[index].map_id != g_current_map) {
      continue;
    }
    emit_sprite(
        gba_lore_items[index].tile_x * GBA_TILE_SIZE - g_camera_x + 4,
        gba_lore_items[index].tile_y * GBA_TILE_SIZE - g_camera_y + 4 - pulse,
        GBA_OBJ_ICON_LORE_BASE,
        8,
        1);
  }
  for (index = 0; index < GBA_NPC_COUNT; index++) {
    if (gba_npcs[index].map_id != g_current_map) {
      continue;
    }
    emit_sprite(
        gba_npcs[index].tile_x * GBA_TILE_SIZE - g_camera_x,
        gba_npcs[index].tile_y * GBA_TILE_SIZE - g_camera_y,
        gba_npc_sprite_bases[index],
        16,
        1);
  }
  for (index = 0; index < MAX_ACTIVE_ENEMIES; index++) {
    if (!g_enemies[index].active) {
      continue;
    }
    if (g_enemies[index].flash_timer && pulse) {
      continue;
    }
    emit_sprite(
        (g_enemies[index].x_fp >> FP_SHIFT) - g_camera_x,
        (g_enemies[index].y_fp >> FP_SHIFT) - g_camera_y,
        gba_enemy_sprite_bases[g_enemies[index].def->enemy_type_index],
        16,
        1);
  }
  if (g_boss.active && g_boss.def && g_boss.state != BOSS_DEAD) {
    if (!(g_boss.flash_timer && pulse)) {
      emit_sprite(
          (g_boss.x_fp >> FP_SHIFT) - g_camera_x - 8,
          (g_boss.y_fp >> FP_SHIFT) - g_camera_y - 8,
          gba_boss_sprite_bases[g_boss.def->stage - 1],
          32,
          1);
    }
  }
  for (index = 0; index < MAX_ACTIVE_ANIMALS; index++) {
    if (!g_animals[index].active || g_animals[index].state == ANIMAL_STATE_DEAD) {
      continue;
    }
    if (g_animals[index].flash_timer && pulse) {
      continue;
    }
    emit_sprite(
        (g_animals[index].x_fp >> FP_SHIFT) - g_camera_x,
        (g_animals[index].y_fp >> FP_SHIFT) - g_camera_y,
        gba_animal_sprite_bases[g_animals[index].animal_type],
        16,
        1);
  }
}

static void render_attack_effect(int player_x, int player_y) {
  /* Draw the equipped sword next to the player whenever a weapon is held,
   * and extend it outward during the attack window so the swing reads as an
   * actual blade motion rather than a yellow flash.
   *
   * The player sprite is 16x16 and anchored at (player_x, player_y). The
   * sword sprite is also 16x16 and drawn so that its hilt sits over the
   * player's hand; the offsets below pick which side the sword hangs from
   * depending on facing.
   *
   * During the attack window we lerp between an idle offset and a fully
   * extended offset to simulate the thrust / swing animation. */
  int swing_frames;
  int swing_range;
  int swing_offset;
  int ox = 0;
  int oy = 0;
  u16 base = 0;
  if (g_equipped_weapon < 0) {
    return;
  }
  swing_frames = g_attack_timer;       /* counts 10 -> 0 during attack */
  swing_range = 8;                     /* max extra pixels of extension */
  if (swing_frames > 0) {
    /* Smooth thrust curve: peaks midway through the attack window. */
    int mid = 5;
    int dist = mid - (swing_frames > mid ? (swing_frames - mid) : (mid - swing_frames));
    swing_offset = (swing_range * dist) / mid;
    if (swing_offset < 0) swing_offset = 0;
  } else {
    swing_offset = 0;
  }

  switch (g_facing) {
    case FACE_DOWN:
      base = GBA_OBJ_ICON_SWORD_DOWN_BASE;
      ox = 4;                     /* right-hand side of body */
      oy = 4 + swing_offset;      /* hilt at shoulder, tip below feet */
      break;
    case FACE_UP:
      base = GBA_OBJ_ICON_SWORD_UP_BASE;
      ox = -4;                    /* left-hand side when facing away */
      oy = -10 - swing_offset;    /* blade reaches above head */
      break;
    case FACE_LEFT:
      base = GBA_OBJ_ICON_SWORD_LEFT_BASE;
      ox = -12 - swing_offset;
      oy = 2;
      break;
    case FACE_RIGHT:
    default:
      base = GBA_OBJ_ICON_SWORD_RIGHT_BASE;
      ox = 12 + swing_offset;
      oy = 2;
      break;
  }

  emit_sprite(player_x + ox, player_y + oy, base, 16, 0);
}

static void render_dialogue_box(void) {
  char visible[80];
  char page_indicator[12];
  char page_current[6];
  char page_total[6];
  int indicator_len;
  const char *page;
  int visible_len;
  if (!g_dialogue.active) {
    return;
  }
  page = g_dialogue.pages[g_dialogue.page_index];
  visible_len = clamp_int(g_dialogue.chars_visible, 0, string_length(page));
  copy_text(visible, sizeof(visible), page);
  visible[visible_len] = '\0';
  ui_draw_box(1, 13, 28, 7, 1);
  int_to_text(g_dialogue.page_index + 1, page_current, sizeof(page_current));
  int_to_text(g_dialogue.page_count, page_total, sizeof(page_total));
  copy_text(page_indicator, sizeof(page_indicator), page_current);
  indicator_len = string_length(page_indicator);
  if (indicator_len < (int)sizeof(page_indicator) - 1) {
    page_indicator[indicator_len++] = '/';
    page_indicator[indicator_len] = '\0';
  }
  copy_text(page_indicator + indicator_len, (int)sizeof(page_indicator) - indicator_len, page_total);
  ui_draw_text_clipped(2, 14, 16, g_dialogue.speaker ? g_dialogue.speaker : "", 1);
  ui_draw_text(24 - string_width(page_indicator), 14, page_indicator, 1);
  ui_draw_wrapped_text(2, 15, 25, visible, 0, 3);
  ui_draw_text(19, 18, g_dialogue.page_index + 1 < g_dialogue.page_count ? "A NEXT" : "A DONE", 1);
  ui_draw_text(25, 18, "B EXIT", 0);
}

static void render_hud(void) {
  char buffer[24];
  int hp_index;
  for (hp_index = 0; hp_index < player_max_hp(); hp_index++) {
    ui_set_tile(hp_index, 0, hp_index < g_player_hp ? GBA_UI_TILE_HEART_FULL : GBA_UI_TILE_HEART_EMPTY);
  }
  ui_set_tile(22, 0, GBA_UI_TILE_COIN);
  int_to_text(g_coins, buffer, sizeof(buffer));
  ui_draw_text_clipped(23, 0, 5, buffer, 0);
  {
    char lvl[8];
    int_to_text(g_level, lvl, sizeof(lvl));
    ui_draw_text(28, 0, "L", 1);
    ui_draw_text(29, 0, lvl, 0);
  }
  if (g_boss.active && g_boss.def && g_boss.state != BOSS_DEAD) {
    int max_hp = g_boss.def->stage == 1 ? 20 : (g_boss.def->stage == 2 ? 30 : 50);
    int fill_tiles = (g_boss.hp * 8 + max_hp - 1) / max_hp;
    int bar_index;
    ui_draw_text(10, 0, "BOSS", 1);
    for (bar_index = 0; bar_index < 8; bar_index++) {
      ui_set_tile(15 + bar_index, 0, bar_index < fill_tiles ? GBA_UI_TILE_BAR_FILL : GBA_UI_TILE_BAR_BG);
    }
  }
  if (!g_dialogue.active && g_status_timer && g_status_text[0]) {
    ui_fill_rect(1, 1, 28, 1, GBA_UI_TILE_FILL);
    ui_draw_text_clipped(2, 1, 26, g_status_text, 0);
  }
  if (!g_dialogue.active) {
    /* Minecraft-style 8-slot hotbar: each slot is a 3x3 tile cell (24x24 px)
     * with a framed border. Active slot swaps to the accent frame, item
     * category icon sits in the centre, and the bottom-right tile shows the
     * slot number (1-8) — overwritten by the stack count when > 1. */
    int hotbar_top = 17;
    int slot;
    for (slot = 0; slot < HOTBAR_SLOTS; slot++) {
      int sx = slot * 3;
      int item = g_hotbar[slot];
      int accent = (slot == g_active_hotbar);
      u16 tl = accent ? GBA_UI_TILE_SLOT_A_TL : GBA_UI_TILE_SLOT_N_TL;
      u16 t  = accent ? GBA_UI_TILE_SLOT_A_T  : GBA_UI_TILE_SLOT_N_T;
      u16 tr = accent ? GBA_UI_TILE_SLOT_A_TR : GBA_UI_TILE_SLOT_N_TR;
      u16 l  = accent ? GBA_UI_TILE_SLOT_A_L  : GBA_UI_TILE_SLOT_N_L;
      u16 c  = accent ? GBA_UI_TILE_SLOT_A_C  : GBA_UI_TILE_SLOT_N_C;
      u16 r  = accent ? GBA_UI_TILE_SLOT_A_R  : GBA_UI_TILE_SLOT_N_R;
      u16 bl = accent ? GBA_UI_TILE_SLOT_A_BL : GBA_UI_TILE_SLOT_N_BL;
      u16 b  = accent ? GBA_UI_TILE_SLOT_A_B  : GBA_UI_TILE_SLOT_N_B;
      u16 br = accent ? GBA_UI_TILE_SLOT_A_BR : GBA_UI_TILE_SLOT_N_BR;

      ui_set_tile(sx,     hotbar_top,     tl);
      ui_set_tile(sx + 1, hotbar_top,     t);
      ui_set_tile(sx + 2, hotbar_top,     tr);
      ui_set_tile(sx,     hotbar_top + 1, l);
      ui_set_tile(sx + 1, hotbar_top + 1, item >= 0 ? item_icon_tile(item) : c);
      ui_set_tile(sx + 2, hotbar_top + 1, r);
      ui_set_tile(sx,     hotbar_top + 2, bl);
      ui_set_tile(sx + 1, hotbar_top + 2, b);
      ui_set_tile(sx + 2, hotbar_top + 2, br);

      /* Bottom-right shows either the stack count (if > 1) or the slot
       * number so the player always knows which L/R press lands where. */
      {
        char label[4];
        if (item >= 0 && g_item_counts[item] > 1) {
          int_to_text(g_item_counts[item], label, sizeof(label));
        } else {
          label[0] = (char)('1' + slot);
          label[1] = '\0';
        }
        ui_draw_text_clipped(sx + 2, hotbar_top + 2, 1, label, accent);
      }
    }

    /* Right of the slot strip: player form label (4 chars fits in the 6 tiles
     * left over after 8 * 3 = 24 slot tiles). */
    ui_draw_text(25, hotbar_top + 1, player_form_name(), 1);
  }
}

static void render_title(void) {
  begin_ui_scene(GBA_UI_TILE_FILL_ALT);
  ui_draw_box(3, 1, 24, 5, 1);
  ui_draw_text_centered(2, "MYTHICAL", 1);
  ui_draw_text_centered(4, "HANDHELD CAMPAIGN", 0);
  emit_sprite((SCREEN_WIDTH - PLAYER_W) / 2, 48, gba_player_frame_bases[g_anim_frame], 16, 0);
  ui_draw_box(6, 9, 18, 7, 0);
  ui_draw_text(8, 10, g_title_cursor == 0 ? "> CONTINUE" : "  CONTINUE", g_title_cursor == 0);
  ui_draw_text(8, 12, g_title_cursor == 1 ? "> NEW GAME" : "  NEW GAME", g_title_cursor == 1);
  ui_draw_text(8, 14, g_title_cursor == 2 ? "> CONTROLS" : "  CONTROLS", g_title_cursor == 2);
  ui_draw_text_centered(17, g_continue_available ? "A START SELECT" : "START A NEW QUEST", 0);
  if (!g_continue_available) {
    ui_draw_text_centered(18, "NO SRAM SAVE YET", 0);
  }
}

static void render_help(void) {
  begin_ui_scene(GBA_UI_TILE_FILL_ALT);
  ui_draw_box(1, 0, 28, 20, 1);
  ui_draw_text_centered(1, "CONTROLS", 1);
  ui_draw_text(3, 3, "DPAD", 1);
  ui_draw_text(10, 3, "MOVE", 0);
  ui_draw_text(3, 5, "A", 1);
  ui_draw_text(10, 5, "ATTACK/SELECT", 0);
  ui_draw_text(3, 7, "B", 1);
  ui_draw_text(10, 7, "TALK/BACK", 0);
  ui_draw_text(3, 9, "START", 1);
  ui_draw_text(10, 9, "PAUSE MENU", 0);
  ui_draw_text(3, 11, "SELECT", 1);
  ui_draw_text(10, 11, "EAT/DRINK/SAVE", 0);
  ui_draw_text(3, 13, "L/R", 1);
  ui_draw_text(10, 13, "SCROLL HOTBAR", 0);
  ui_draw_text(3, 15, "PACK", 1);
  ui_draw_text(10, 15, "SEL ASSIGNS SLOT", 0);
  ui_draw_text_centered(18, "B BACK", 0);
}

static void render_inventory(void) {
  int visible_indices[GBA_ITEM_COUNT];
  int visible_count = 0;
  int first_visible = 0;
  int rows_visible = 10;
  int index;
  char count_text[12];
  begin_ui_scene(GBA_UI_TILE_FILL_ALT);
  for (index = 0; index < GBA_ITEM_COUNT; index++) {
    if (g_item_counts[index]) {
      visible_indices[visible_count++] = index;
    }
  }
  if (g_inventory_cursor >= rows_visible) {
    first_visible = g_inventory_cursor - (rows_visible - 1);
  }
  if (visible_count - first_visible < rows_visible && visible_count > rows_visible) {
    first_visible = visible_count - rows_visible;
  }
  if (first_visible < 0) {
    first_visible = 0;
  }
  ui_draw_box(0, 0, 30, 20, 1);
  ui_draw_text(2, 1, "PACK", 1);
  {
    char lvl[8];
    ui_draw_text(8, 1, "LV", 1);
    int_to_text(g_level, lvl, sizeof(lvl));
    ui_draw_text(11, 1, lvl, 0);
  }
  ui_set_tile(22, 1, GBA_UI_TILE_COIN);
  int_to_text(g_coins, count_text, sizeof(count_text));
  ui_draw_text_clipped(24, 1, 4, count_text, 0);
  ui_draw_box(1, 3, 13, 15, 0);
  ui_draw_box(15, 3, 14, 8, 0);
  ui_draw_box(15, 12, 14, 6, 0);
  ui_draw_text(3, 4, "ITEMS", 1);
  ui_draw_text(17, 4, "GOAL", 1);
  ui_draw_wrapped_text(17, 6, 10, current_quest_desc(), 0, 4);
  if (!visible_count) {
    ui_draw_text(3, 7, "NOTHING YET", 0);
  }
  for (index = first_visible; index < visible_count && index < first_visible + rows_visible; index++) {
    int item_index = visible_indices[index];
    int row_y = 6 + (index - first_visible);
    int is_cursor = (index == g_inventory_cursor);
    ui_draw_text(2, row_y, is_cursor ? ">" : " ", is_cursor);
    ui_set_tile(3, row_y, item_icon_tile(item_index));
    ui_draw_text_clipped(4, row_y, 6, gba_items[item_index].name, is_cursor);
    int_to_text(g_item_counts[item_index], count_text, sizeof(count_text));
    ui_draw_text_clipped(10, row_y, 2, count_text, 0);
    if (hotbar_slot_for(item_index) >= 0) {
      ui_draw_text(12, row_y, "H", 1);
    }
  }
  if (first_visible > 0) {
    ui_draw_text(11, 5, "^", 1);
  }
  if (first_visible + rows_visible < visible_count) {
    ui_draw_text(11, 16, "V", 1);
  }
  ui_draw_text(17, 13, "GEAR", 1);
  ui_draw_text(17, 14, "W", 0);
  ui_draw_text_clipped(19, 14, 8, g_equipped_weapon >= 0 ? gba_items[g_equipped_weapon].name : "NONE", 0);
  ui_draw_text(17, 15, "A", 0);
  ui_draw_text_clipped(19, 15, 8, g_equipped_armor >= 0 ? gba_items[g_equipped_armor].name : "NONE", 0);
  ui_draw_text(17, 16, "X", 0);
  ui_draw_text_clipped(19, 16, 8, g_equipped_accessory >= 0 ? gba_items[g_equipped_accessory].name : "NONE", 0);

  /* Hotbar strip at the bottom of the inventory screen mirrors the in-play
   * HUD: one cell per slot, active slot highlighted. L / R pick the slot,
   * SELECT assigns the cursor item to it. */
  {
    int hotbar_label_y = 17;
    int hotbar_y = 18;
    int slot;
    ui_draw_text(1, hotbar_label_y, "HOTBAR", 1);
    {
      char slot_label[4];
      slot_label[0] = (char)('1' + g_active_hotbar);
      slot_label[1] = '\0';
      ui_draw_text(8, hotbar_label_y, "SLOT", 0);
      ui_draw_text(13, hotbar_label_y, slot_label, 1);
    }
    for (slot = 0; slot < HOTBAR_SLOTS; slot++) {
      int sx = 1 + slot * 3;
      int item = g_hotbar[slot];
      int accent = (slot == g_active_hotbar);
      ui_draw_text(sx, hotbar_y, accent ? ">" : " ", accent);
      if (item >= 0) {
        ui_set_tile(sx + 1, hotbar_y, item_icon_tile(item));
      } else {
        char placeholder[2];
        placeholder[0] = (char)('1' + slot);
        placeholder[1] = '\0';
        ui_draw_text(sx + 1, hotbar_y, placeholder, 0);
      }
    }
  }
  ui_draw_text_centered(19, "A:USE SEL:SET LR:SLOT B:BACK", 0);
}

static void render_stage_clear(void) {
  begin_ui_scene(GBA_UI_TILE_FILL_ALT);
  ui_draw_box(4, 4, 22, 11, 1);
  ui_draw_text_centered(6, "ACT CLEAR", 1);
  ui_draw_text_centered(8, gba_stage_names[g_stage_clear_target], 0);
  ui_draw_text_centered(11, "FORM EVOLVED", 0);
  ui_draw_text_centered(13, "HP RESTORED", 0);
  ui_draw_text_centered(16, "A START CONTINUE", 0);
}

static void render_game_over(void) {
  begin_ui_scene(GBA_UI_TILE_FILL_ALT);
  ui_draw_box(4, 5, 22, 10, 1);
  ui_draw_text_centered(7, "YOU FELL", 1);
  ui_draw_text_centered(10, "THE QUEST REMAINS", 0);
  ui_draw_text_centered(13, "A START RETRY", 0);
}

static void render_victory(void) {
  begin_ui_scene(GBA_UI_TILE_FILL_ALT);
  ui_draw_box(3, 3, 24, 13, 1);
  ui_draw_text_centered(5, "VICTORY", 1);
  ui_draw_text_centered(8, "THE SOVEREIGN FELL", 0);
  ui_draw_text_centered(10, "THE REALM ENDURES", 0);
  ui_draw_text_centered(13, "A START TITLE", 0);
}

static void render_play(void) {
  int player_x = (g_player_x_fp >> FP_SHIFT) - g_camera_x;
  int player_y = (g_player_y_fp >> FP_SHIFT) - g_camera_y;
  int player_frame = g_facing * 4 + g_anim_frame;
  begin_sprite_frame();
  clear_ui_shadow();
  draw_world(&gba_maps[g_current_map]);
  render_world_entities();
  if (!(g_player_flash && ((g_frame_counter >> 1) & 1u))) {
    emit_sprite(player_x, player_y, gba_player_frame_bases[player_frame], 16, 0);
  }
  render_attack_effect(player_x, player_y);
  render_hud();
  render_dialogue_box();
}

int main(void) {
  video_init();
  g_continue_available = load_save();
  if (!g_continue_available) {
    reset_progress();
  }
  while (1) {
    g_frame_counter++;
    update_input();
    if (g_state == STATE_TITLE) {
      update_title();
      update_player_animation(1);
      render_title();
    } else if (g_state == STATE_HELP) {
      update_help();
      render_help();
    } else if (g_state == STATE_PAUSE) {
      update_pause();
      render_pause();
    } else if (g_state == STATE_INVENTORY) {
      update_inventory();
      render_inventory();
    } else if (g_state == STATE_CRAFTING) {
      update_crafting();
      render_crafting();
    } else if (g_state == STATE_SKILLS) {
      update_skills();
      render_skills();
    } else if (g_state == STATE_BESTIARY) {
      update_bestiary();
      render_bestiary();
    } else if (g_state == STATE_TRAVEL) {
      update_travel();
      render_travel();
    } else if (g_state == STATE_STAGE_CLEAR) {
      update_stage_clear();
      render_stage_clear();
    } else if (g_state == STATE_STAGE_INTRO) {
      update_stage_intro();
      render_stage_intro();
    } else if (g_state == STATE_GAME_OVER) {
      update_game_over();
      render_game_over();
    } else if (g_state == STATE_VICTORY) {
      update_victory();
      render_victory();
    } else {
      update_play();
      render_play();
    }
    present();
  }
}
