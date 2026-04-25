#!/usr/bin/env python3
"""
Generate paletted GBA video assets for Mythical.

This stage performs the architectural jump from a raw framebuffer asset pack to
proper GBA-native graphics:
- 8bpp streamed background tiles for the world
- 8bpp UI/font tiles for the fixed HUD layer
- 8bpp OBJ tiles for actors, pickups, and effects

The desktop Python game remains the visual source of truth; we reuse its tile
renderer and compiled player frames, then repack everything into formats the
handheld runtime can stream directly into VRAM.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pygame
from PIL import Image, ImageDraw, ImageFont


ROOT_DIR = Path(__file__).resolve().parents[1]
GEN_DIR = Path(__file__).resolve().parent / "generated"
PLAYER_DIR = ROOT_DIR / "assets" / "compiled" / "player"

sys.path.insert(0, str(ROOT_DIR))

from ai.config_loader import get_enemy_config  # noqa: E402
from animal import ANIMAL_DEFS  # noqa: E402
from convert_content import ANIMAL_TYPE_ORDER, BOSS_DEFS_ALL, ENEMY_DEFS_ALL, MAP_ORDER, NPC_DEFS_ALL  # noqa: E402
from tilemap import DECOR_DEFS, TILE_DEFS, TileMap  # noqa: E402


GBA_TILE_SIZE = 16
PLAYER_SIZE = 16
FONT_CELL = 8
TRANSPARENT_WORD = 0x0000
PLAYER_ORDER = ("down", "up", "left", "right")
FONT_CANDIDATES = (
    "lucon.ttf",
    "consola.ttf",
    "cour.ttf",
)


def rgb_to_gba(r: int, g: int, b: int) -> int:
    return ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)


def _boot_pygame() -> None:
    pygame.init()
    try:
        pygame.display.set_mode((1, 1), pygame.HIDDEN)
    except Exception:
        pygame.display.set_mode((1, 1))


def _single_tilemap(ground_id: int, decor_id: int) -> dict:
    return {
        "width": 1,
        "height": 1,
        "ground": [[ground_id]],
        "decor": [[decor_id]],
        "collision": [[0]],
        "spawns": {},
    }


def make_surface(width: int, height: int) -> pygame.Surface:
    return pygame.Surface((width, height), pygame.SRCALPHA)


def render_ground_tile(tile_id: int) -> pygame.Surface:
    tilemap = TileMap(_single_tilemap(tile_id, 0))
    return pygame.transform.scale(tilemap._ground_surf, (GBA_TILE_SIZE, GBA_TILE_SIZE))


def render_decor_tile(decor_id: int) -> pygame.Surface:
    if decor_id == 0:
        return make_surface(GBA_TILE_SIZE, GBA_TILE_SIZE)
    tilemap = TileMap(_single_tilemap(0, decor_id))
    return pygame.transform.scale(tilemap._decor_surf, (GBA_TILE_SIZE, GBA_TILE_SIZE))


def load_player_frames() -> list[pygame.Surface]:
    frames: list[pygame.Surface] = []
    for direction in PLAYER_ORDER:
        for frame_index in range(4):
            frame_path = PLAYER_DIR / f"{direction}_{frame_index}.png"
            if not frame_path.exists():
                raise FileNotFoundError(f"Missing player frame: {frame_path}")
            image = pygame.image.load(frame_path).convert_alpha()
            frames.append(pygame.transform.scale(image, (PLAYER_SIZE, PLAYER_SIZE)))
    return frames


def pil_to_surface(image: Image.Image) -> pygame.Surface:
    rgba = image.convert("RGBA")
    return pygame.image.fromstring(rgba.tobytes(), rgba.size, "RGBA").convert_alpha()


def load_font() -> ImageFont.FreeTypeFont:
    last_error: Exception | None = None
    for candidate in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, 8)
        except OSError as exc:
            last_error = exc
    raise RuntimeError(f"Unable to load UI bitmap font. Tried: {', '.join(FONT_CANDIDATES)}") from last_error


def build_font_glyph_surfaces(color: tuple[int, int, int]) -> list[pygame.Surface]:
    font = load_font()
    min_left = 0
    min_top = 0
    max_right = 0
    max_bottom = 0
    surfaces: list[pygame.Surface] = []

    for codepoint in range(32, 128):
        bbox = font.getbbox(chr(codepoint))
        if bbox is None:
            continue
        min_left = min(min_left, bbox[0])
        min_top = min(min_top, bbox[1])
        max_right = max(max_right, bbox[2])
        max_bottom = max(max_bottom, bbox[3])

    glyph_w = max_right - min_left
    glyph_h = max_bottom - min_top
    x_offset = (FONT_CELL - glyph_w) // 2 - min_left
    y_offset = (FONT_CELL - glyph_h) // 2 - min_top

    for codepoint in range(32, 128):
        image = Image.new("RGBA", (FONT_CELL, FONT_CELL), (20, 24, 28, 255))
        draw = ImageDraw.Draw(image)
        draw.text((x_offset, y_offset), chr(codepoint), fill=(*color, 255), font=font)
        surfaces.append(pil_to_surface(image))
    return surfaces


class PaletteBuilder:
    def __init__(self) -> None:
        self.colors: list[tuple[int, int, int]] = [
            (0, 0, 0),        # Transparent / backdrop
            (8, 8, 10),       # True opaque outline black
            (244, 240, 228),  # White font
            (228, 196, 88),   # Gold font/accent
            (20, 24, 28),     # Dark panel fill
            (40, 48, 60),     # Mid panel fill
            (92, 102, 116),   # Trim
            (168, 56, 64),    # Red
            (64, 144, 92),    # Green
            (88, 132, 188),   # Blue
            (208, 164, 60),   # Gold icon
        ]
        self.lookup = {color: index for index, color in enumerate(self.colors)}

    def add_color(self, color: tuple[int, int, int]) -> int:
        if color in self.lookup:
            return self.lookup[color]
        if len(self.colors) < 256:
            self.lookup[color] = len(self.colors)
            self.colors.append(color)
            return len(self.colors) - 1
        best_index = 1
        best_distance = 1 << 30
        for index, existing in enumerate(self.colors):
            if index == 0:
                continue
            distance = (
                (color[0] - existing[0]) * (color[0] - existing[0])
                + (color[1] - existing[1]) * (color[1] - existing[1])
                + (color[2] - existing[2]) * (color[2] - existing[2])
            )
            if distance < best_distance:
                best_distance = distance
                best_index = index
        return best_index

    def add_surface(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        for y in range(height):
            for x in range(width):
                color = surface.get_at((x, y))
                alpha = color.a if hasattr(color, "a") else color[3]
                if alpha < 128:
                    continue
                self.add_color((color.r, color.g, color.b))

    def index_for(self, r: int, g: int, b: int) -> int:
        return self.add_color((r, g, b))

    def words(self) -> list[int]:
        padded = self.colors + [(0, 0, 0)] * (256 - len(self.colors))
        return [rgb_to_gba(r, g, b) for r, g, b in padded]


def surface_to_8bpp_tile_bytes(surface: pygame.Surface, palette: PaletteBuilder) -> list[int]:
    width, height = surface.get_size()
    if width % 8 or height % 8:
        raise ValueError(f"Surface must be tile-aligned, got {width}x{height}")
    tile_bytes: list[int] = []
    for tile_y in range(0, height, 8):
        for tile_x in range(0, width, 8):
            for py in range(8):
                for px in range(8):
                    color = surface.get_at((tile_x + px, tile_y + py))
                    alpha = color.a if hasattr(color, "a") else color[3]
                    if alpha < 128:
                        tile_bytes.append(0)
                    else:
                        tile_bytes.append(palette.index_for(color.r, color.g, color.b))
    return tile_bytes


def bytes_to_halfwords(values: list[int]) -> list[int]:
    packed: list[int] = []
    for offset in range(0, len(values), 2):
        low = values[offset]
        high = values[offset + 1] if offset + 1 < len(values) else 0
        packed.append(low | (high << 8))
    return packed


def build_ui_tiles() -> dict[str, pygame.Surface]:
    tiles: dict[str, pygame.Surface] = {}

    blank = make_surface(8, 8)
    tiles["blank"] = blank

    fill = make_surface(8, 8)
    fill.fill((20, 24, 28, 255))
    tiles["fill"] = fill

    fill_alt = make_surface(8, 8)
    fill_alt.fill((40, 48, 60, 255))
    tiles["fill_alt"] = fill_alt

    hline = fill.copy()
    pygame.draw.line(hline, (92, 102, 116, 255), (0, 0), (7, 0))
    pygame.draw.line(hline, (228, 196, 88, 255), (0, 1), (7, 1))
    tiles["hline"] = hline

    vline = fill.copy()
    pygame.draw.line(vline, (92, 102, 116, 255), (0, 0), (0, 7))
    pygame.draw.line(vline, (228, 196, 88, 255), (1, 0), (1, 7))
    tiles["vline"] = vline

    for name in ("corner_tl", "corner_tr", "corner_bl", "corner_br"):
        tile = fill.copy()
        tiles[name] = tile

    pygame.draw.line(tiles["corner_tl"], (92, 102, 116, 255), (0, 7), (0, 0))
    pygame.draw.line(tiles["corner_tl"], (92, 102, 116, 255), (0, 0), (7, 0))
    pygame.draw.line(tiles["corner_tl"], (228, 196, 88, 255), (1, 7), (1, 1))
    pygame.draw.line(tiles["corner_tl"], (228, 196, 88, 255), (1, 1), (7, 1))

    pygame.draw.line(tiles["corner_tr"], (92, 102, 116, 255), (0, 0), (7, 0))
    pygame.draw.line(tiles["corner_tr"], (92, 102, 116, 255), (7, 0), (7, 7))
    pygame.draw.line(tiles["corner_tr"], (228, 196, 88, 255), (0, 1), (6, 1))
    pygame.draw.line(tiles["corner_tr"], (228, 196, 88, 255), (6, 1), (6, 7))

    pygame.draw.line(tiles["corner_bl"], (92, 102, 116, 255), (0, 0), (0, 7))
    pygame.draw.line(tiles["corner_bl"], (92, 102, 116, 255), (0, 7), (7, 7))
    pygame.draw.line(tiles["corner_bl"], (228, 196, 88, 255), (1, 0), (1, 6))
    pygame.draw.line(tiles["corner_bl"], (228, 196, 88, 255), (1, 6), (7, 6))

    pygame.draw.line(tiles["corner_br"], (92, 102, 116, 255), (7, 0), (7, 7))
    pygame.draw.line(tiles["corner_br"], (92, 102, 116, 255), (0, 7), (7, 7))
    pygame.draw.line(tiles["corner_br"], (228, 196, 88, 255), (6, 0), (6, 6))
    pygame.draw.line(tiles["corner_br"], (228, 196, 88, 255), (0, 6), (6, 6))

    heart_full = make_surface(8, 8)
    pygame.draw.rect(heart_full, (168, 56, 64, 255), (1, 0, 2, 2))
    pygame.draw.rect(heart_full, (168, 56, 64, 255), (4, 0, 2, 2))
    pygame.draw.rect(heart_full, (168, 56, 64, 255), (0, 1, 7, 2))
    pygame.draw.rect(heart_full, (168, 56, 64, 255), (1, 3, 5, 2))
    pygame.draw.rect(heart_full, (168, 56, 64, 255), (2, 5, 3, 2))
    pygame.draw.rect(heart_full, (240, 210, 214, 255), (1, 1, 1, 1))
    pygame.draw.rect(heart_full, (240, 210, 214, 255), (4, 1, 1, 1))
    tiles["heart_full"] = heart_full

    heart_empty = heart_full.copy()
    heart_empty.fill((0, 0, 0, 0))
    pygame.draw.rect(heart_empty, (72, 28, 34, 255), (1, 0, 2, 2))
    pygame.draw.rect(heart_empty, (72, 28, 34, 255), (4, 0, 2, 2))
    pygame.draw.rect(heart_empty, (72, 28, 34, 255), (0, 1, 7, 2))
    pygame.draw.rect(heart_empty, (72, 28, 34, 255), (1, 3, 5, 2))
    pygame.draw.rect(heart_empty, (72, 28, 34, 255), (2, 5, 3, 2))
    tiles["heart_empty"] = heart_empty

    coin = make_surface(8, 8)
    pygame.draw.rect(coin, (208, 164, 60, 255), (1, 1, 6, 5))
    pygame.draw.rect(coin, (248, 228, 124, 255), (2, 2, 3, 2))
    tiles["coin"] = coin

    bar_bg = make_surface(8, 8)
    bar_bg.fill((44, 18, 24, 255))
    pygame.draw.rect(bar_bg, (92, 102, 116, 255), (0, 0, 8, 1))
    pygame.draw.rect(bar_bg, (92, 102, 116, 255), (0, 7, 8, 1))
    tiles["bar_bg"] = bar_bg

    bar_fill = make_surface(8, 8)
    bar_fill.fill((168, 56, 64, 255))
    pygame.draw.rect(bar_fill, (224, 152, 128, 255), (0, 0, 8, 2))
    tiles["bar_fill"] = bar_fill

    # Item-category icons for the hotbar / inventory — one 8x8 glyph per
    # inventory category, so the handheld hotbar can show per-item art like the
    # pygame HUD instead of just a first-letter label.
    def _category_base():
        base = make_surface(8, 8)
        return base

    item_weapon = _category_base()
    pygame.draw.rect(item_weapon, (210, 214, 230, 255), (3, 0, 2, 6))
    pygame.draw.rect(item_weapon, (255, 255, 255, 255), (3, 0, 1, 6))
    pygame.draw.rect(item_weapon, (120, 80, 40, 255), (2, 6, 4, 1))
    pygame.draw.rect(item_weapon, (80, 50, 30, 255), (3, 7, 2, 1))
    tiles["item_weapon"] = item_weapon

    item_armor = _category_base()
    pygame.draw.rect(item_armor, (90, 128, 196, 255), (1, 1, 6, 4))
    pygame.draw.rect(item_armor, (140, 176, 232, 255), (2, 0, 4, 2))
    pygame.draw.rect(item_armor, (60, 88, 132, 255), (2, 5, 4, 1))
    pygame.draw.rect(item_armor, (60, 88, 132, 255), (3, 6, 2, 1))
    tiles["item_armor"] = item_armor

    item_accessory = _category_base()
    pygame.draw.rect(item_accessory, (238, 204, 92, 255), (1, 2, 6, 4))
    pygame.draw.rect(item_accessory, (20, 24, 28, 255), (2, 3, 4, 2))
    pygame.draw.rect(item_accessory, (255, 240, 160, 255), (1, 2, 6, 1))
    tiles["item_accessory"] = item_accessory

    item_potion = _category_base()
    pygame.draw.rect(item_potion, (200, 200, 220, 255), (3, 0, 2, 2))
    pygame.draw.rect(item_potion, (80, 92, 120, 255), (2, 2, 4, 1))
    pygame.draw.rect(item_potion, (180, 60, 84, 255), (2, 3, 4, 4))
    pygame.draw.rect(item_potion, (244, 116, 140, 255), (3, 3, 2, 1))
    pygame.draw.rect(item_potion, (80, 92, 120, 255), (2, 7, 4, 1))
    tiles["item_potion"] = item_potion

    item_food = _category_base()
    pygame.draw.rect(item_food, (172, 80, 64, 255), (1, 2, 6, 4))
    pygame.draw.rect(item_food, (232, 156, 128, 255), (2, 3, 4, 2))
    pygame.draw.rect(item_food, (240, 232, 200, 255), (0, 1, 2, 2))
    pygame.draw.rect(item_food, (240, 232, 200, 255), (6, 5, 2, 2))
    tiles["item_food"] = item_food

    item_key = _category_base()
    pygame.draw.rect(item_key, (228, 196, 88, 255), (1, 1, 3, 3))
    pygame.draw.rect(item_key, (20, 24, 28, 255), (2, 2, 1, 1))
    pygame.draw.rect(item_key, (228, 196, 88, 255), (4, 2, 3, 1))
    pygame.draw.rect(item_key, (228, 196, 88, 255), (5, 3, 1, 1))
    pygame.draw.rect(item_key, (228, 196, 88, 255), (6, 4, 1, 1))
    tiles["item_key"] = item_key

    item_material = _category_base()
    pygame.draw.rect(item_material, (148, 108, 196, 255), (2, 1, 4, 2))
    pygame.draw.rect(item_material, (200, 164, 232, 255), (3, 0, 2, 2))
    pygame.draw.rect(item_material, (108, 76, 160, 255), (1, 3, 6, 3))
    pygame.draw.rect(item_material, (200, 164, 232, 255), (2, 3, 1, 1))
    pygame.draw.rect(item_material, (200, 164, 232, 255), (5, 4, 1, 1))
    pygame.draw.rect(item_material, (108, 76, 160, 255), (2, 6, 4, 1))
    tiles["item_material"] = item_material

    # Minecraft-style hotbar slot frames — one dedicated tile per corner/edge
    # position so each slot renders as a proper 3x3 boxed cell. "_a_" variants
    # use a warm accent so the currently selected slot reads at a glance.
    def _make_slot_frame(accent: bool) -> dict[str, pygame.Surface]:
        frame_dark = (12, 14, 20, 255)
        frame_light = (248, 224, 120, 255) if accent else (174, 188, 208, 255)
        panel = (68, 58, 34, 255) if accent else (32, 36, 48, 255)
        out: dict[str, pygame.Surface] = {}
        # Each tile fills with the slot panel colour, then adds edge decor so
        # the 3x3 composition looks like a recessed square slot.
        for pos in ("tl", "t", "tr", "l", "c", "r", "bl", "b", "br"):
            surf = make_surface(8, 8)
            surf.fill(panel)
            out[pos] = surf
        # Top-row (rows 0-1) of each upper tile: dark bevel over light highlight.
        for key in ("tl", "t", "tr"):
            pygame.draw.rect(out[key], frame_light, (0, 0, 8, 1))
            pygame.draw.rect(out[key], frame_dark, (0, 1, 8, 1))
        # Bottom-row of each lower tile.
        for key in ("bl", "b", "br"):
            pygame.draw.rect(out[key], frame_light, (0, 7, 8, 1))
            pygame.draw.rect(out[key], frame_dark, (0, 6, 8, 1))
        # Left edge on left-column tiles.
        for key in ("tl", "l", "bl"):
            pygame.draw.rect(out[key], frame_light, (0, 0, 1, 8))
            pygame.draw.rect(out[key], frame_dark, (1, 0, 1, 8))
        # Right edge on right-column tiles.
        for key in ("tr", "r", "br"):
            pygame.draw.rect(out[key], frame_light, (7, 0, 1, 8))
            pygame.draw.rect(out[key], frame_dark, (6, 0, 1, 8))
        return out

    for accent, prefix in ((False, "slot_n"), (True, "slot_a")):
        parts = _make_slot_frame(accent)
        for pos, surf in parts.items():
            tiles[f"{prefix}_{pos}"] = surf

    return tiles


def _darken(color, amount=40):
    return tuple(max(0, c - amount) for c in color)

def _lighten(color, amount=40):
    return tuple(min(255, c + amount) for c in color)

def build_npc_surfaces() -> list[pygame.Surface]:
    skin = (225, 185, 145)
    surfaces: list[pygame.Surface] = []
    for map_name, _, _, _ in MAP_ORDER:
        for npc in NPC_DEFS_ALL.get(map_name, []):
            body = npc.get("body_color") or (110, 140, 110)
            hair = npc.get("hair_color") or _darken(body, 30)
            surface = make_surface(16, 16)
            # Shadow
            pygame.draw.ellipse(surface, (0, 0, 0, 60), (3, 13, 10, 3))
            # Legs
            leg_color = _darken(body, 20)
            foot_color = _darken(body, 50)
            pygame.draw.rect(surface, leg_color, (5, 11, 2, 3), border_radius=1)
            pygame.draw.rect(surface, leg_color, (9, 11, 2, 3), border_radius=1)
            pygame.draw.rect(surface, foot_color, (4, 13, 3, 2), border_radius=1)
            pygame.draw.rect(surface, foot_color, (9, 13, 3, 2), border_radius=1)
            # Arms
            pygame.draw.rect(surface, skin, (3, 7, 2, 4), border_radius=1)
            pygame.draw.rect(surface, skin, (11, 7, 2, 4), border_radius=1)
            # Tunic body
            pygame.draw.rect(surface, body, (4, 6, 8, 6), border_radius=2)
            # Belt
            belt_color = _darken(body, 35)
            pygame.draw.rect(surface, belt_color, (4, 9, 8, 2), border_radius=1)
            pygame.draw.rect(surface, (185, 155, 38, 255), (7, 9, 2, 2))
            # Collar
            pygame.draw.line(surface, _lighten(body, 25), (6, 6), (10, 6))
            # Head (round)
            pygame.draw.circle(surface, skin, (8, 4), 3)
            # Hair
            pygame.draw.ellipse(surface, hair, (5, 1, 6, 4))
            # Eyes
            pygame.draw.rect(surface, (248, 245, 238, 255), (6, 4, 2, 1))
            pygame.draw.rect(surface, (248, 245, 238, 255), (9, 4, 2, 1))
            pygame.draw.rect(surface, (25, 25, 50, 255), (7, 4, 1, 1))
            pygame.draw.rect(surface, (25, 25, 50, 255), (10, 4, 1, 1))
            surfaces.append(surface)
    return surfaces


def enemy_type_order() -> list[str]:
    ordered: list[str] = []
    for map_name, _, _, _ in MAP_ORDER:
        for spawn in ENEMY_DEFS_ALL.get(map_name, []):
            enemy_type = spawn["type"]
            if enemy_type not in ordered:
                ordered.append(enemy_type)
    return ordered


def build_enemy_surfaces() -> list[pygame.Surface]:
    surfaces: list[pygame.Surface] = []
    for enemy_id in enemy_type_order():
        config = get_enemy_config(enemy_id, "normal")
        color = tuple(config.get("color", (180, 180, 180)))
        surface = make_surface(16, 16)
        pygame.draw.rect(surface, (8, 8, 10, 255), (1, 2, 14, 12), border_radius=4)
        pygame.draw.rect(surface, color, (2, 3, 12, 10), border_radius=4)
        pygame.draw.rect(surface, (8, 8, 10, 255), (4, 6, 2, 2))
        pygame.draw.rect(surface, (8, 8, 10, 255), (10, 6, 2, 2))
        pygame.draw.rect(surface, (244, 240, 228, 255), (5, 6, 1, 1))
        pygame.draw.rect(surface, (244, 240, 228, 255), (11, 6, 1, 1))
        surfaces.append(surface)
    return surfaces


def build_boss_surfaces() -> list[pygame.Surface]:
    surfaces: list[pygame.Surface] = []
    for map_name, _, _, _ in MAP_ORDER:
        boss = BOSS_DEFS_ALL.get(map_name)
        if not boss:
            continue
        if map_name == "dungeon":
            fill = (132, 116, 92)
            trim = (212, 180, 120)
        elif map_name.startswith("ruins"):
            fill = (144, 78, 132)
            trim = (212, 150, 220)
        else:
            fill = (208, 162, 72)
            trim = (248, 228, 132)
        surface = make_surface(32, 32)
        pygame.draw.rect(surface, (8, 8, 10, 255), (2, 2, 28, 28), border_radius=6)
        pygame.draw.rect(surface, fill, (4, 4, 24, 24), border_radius=6)
        pygame.draw.rect(surface, trim, (10, 4, 4, 4))
        pygame.draw.rect(surface, trim, (18, 4, 4, 4))
        pygame.draw.rect(surface, (8, 8, 10, 255), (11, 12, 3, 3))
        pygame.draw.rect(surface, (8, 8, 10, 255), (18, 12, 3, 3))
        pygame.draw.rect(surface, trim, (8, 24, 16, 2))
        surfaces.append(surface)
    return surfaces


def build_animal_surfaces() -> list[pygame.Surface]:
    surfaces: list[pygame.Surface] = []
    for atype in ANIMAL_TYPE_ORDER:
        adef = ANIMAL_DEFS[atype]
        color = tuple(adef.get("color", (180, 180, 180)))
        accent = tuple(adef.get("accent", color))
        surface = make_surface(16, 16)
        if atype == "fish":
            pygame.draw.ellipse(surface, (8, 8, 10, 255), (2, 5, 12, 6))
            pygame.draw.ellipse(surface, color, (3, 6, 10, 4))
            pygame.draw.polygon(surface, color, [(12, 7), (15, 4), (15, 10)])
            pygame.draw.rect(surface, (244, 240, 228, 255), (5, 7, 1, 1))
        elif atype == "rabbit":
            pygame.draw.rect(surface, (8, 8, 10, 255), (4, 6, 8, 8))
            pygame.draw.rect(surface, color, (5, 7, 6, 6))
            pygame.draw.rect(surface, accent, (6, 2, 2, 5))
            pygame.draw.rect(surface, accent, (9, 2, 2, 5))
            pygame.draw.rect(surface, (244, 240, 228, 255), (6, 8, 1, 1))
            pygame.draw.rect(surface, (244, 240, 228, 255), (9, 8, 1, 1))
        else:
            pygame.draw.rect(surface, (8, 8, 10, 255), (2, 3, 12, 11), border_radius=3)
            pygame.draw.rect(surface, color, (3, 4, 10, 9), border_radius=3)
            pygame.draw.rect(surface, accent, (3, 4, 10, 3))
            pygame.draw.rect(surface, (8, 8, 10, 255), (5, 7, 2, 2))
            pygame.draw.rect(surface, (8, 8, 10, 255), (9, 7, 2, 2))
            pygame.draw.rect(surface, (244, 240, 228, 255), (6, 7, 1, 1))
            pygame.draw.rect(surface, (244, 240, 228, 255), (10, 7, 1, 1))
            if atype in ("wolf", "bear", "boar"):
                pygame.draw.rect(surface, (168, 56, 64, 255), (6, 10, 4, 1))
        surfaces.append(surface)
    return surfaces


def build_obj_icons() -> dict[str, pygame.Surface]:
    icons: dict[str, pygame.Surface] = {}

    coin = make_surface(8, 8)
    pygame.draw.rect(coin, (208, 164, 60, 255), (1, 1, 6, 5))
    pygame.draw.rect(coin, (248, 228, 124, 255), (2, 2, 3, 2))
    icons["coin"] = coin

    item = make_surface(8, 8)
    pygame.draw.polygon(item, (96, 188, 112, 255), [(4, 0), (7, 4), (4, 7), (1, 4)])
    pygame.draw.line(item, (228, 244, 228, 255), (4, 1), (4, 6))
    icons["item"] = item

    lore = make_surface(8, 8)
    pygame.draw.rect(lore, (88, 132, 188, 255), (1, 1, 6, 6))
    pygame.draw.rect(lore, (244, 240, 228, 255), (3, 2, 1, 4))
    pygame.draw.rect(lore, (244, 240, 228, 255), (2, 4, 3, 1))
    icons["lore"] = lore

    slash = make_surface(16, 16)
    pygame.draw.line(slash, (248, 228, 124, 255), (4, 13), (12, 3), 2)
    pygame.draw.line(slash, (228, 196, 88, 255), (3, 13), (11, 3), 2)
    icons["slash"] = slash

    # Directional sword sprites — one 16x16 surface per facing, showing the
    # blade pointing in that direction with a wooden hilt. Drawn overlayed on
    # the player sprite so the hero visually "holds" a sword instead of just
    # flashing a generic slash.
    blade_light = (238, 240, 244, 255)
    blade_mid   = (184, 192, 204, 255)
    blade_dark  = (104, 112, 128, 255)
    hilt_wood   = (132,  82,  44, 255)
    hilt_gold   = (228, 196,  88, 255)
    hilt_dark   = ( 66,  44,  26, 255)

    def _sword_down() -> pygame.Surface:
        s = make_surface(16, 16)
        # Hilt / pommel at top, blade hanging downward.
        pygame.draw.rect(s, hilt_wood, (7, 0, 2, 3))
        pygame.draw.rect(s, hilt_gold, (5, 3, 6, 1))
        pygame.draw.rect(s, hilt_dark, (5, 4, 6, 1))
        pygame.draw.rect(s, blade_dark,  (7, 5, 2, 9))
        pygame.draw.rect(s, blade_light, (7, 5, 1, 8))
        pygame.draw.rect(s, blade_mid,   (8, 5, 1, 8))
        pygame.draw.polygon(s, blade_light, [(7, 14), (9, 14), (8, 15)])
        return s

    def _sword_up() -> pygame.Surface:
        s = make_surface(16, 16)
        # Blade at top, hilt at bottom.
        pygame.draw.polygon(s, blade_light, [(7, 0), (9, 0), (8, -1)])
        pygame.draw.rect(s, blade_light, (7, 1, 1, 8))
        pygame.draw.rect(s, blade_mid,   (8, 1, 1, 8))
        pygame.draw.rect(s, blade_dark,  (7, 0, 2, 9))
        pygame.draw.rect(s, hilt_gold, (5, 9, 6, 1))
        pygame.draw.rect(s, hilt_dark, (5, 10, 6, 1))
        pygame.draw.rect(s, hilt_wood, (7, 11, 2, 4))
        return s

    def _sword_right() -> pygame.Surface:
        s = make_surface(16, 16)
        # Hilt on the left, blade pointing right.
        pygame.draw.rect(s, hilt_wood, (0, 7, 3, 2))
        pygame.draw.rect(s, hilt_gold, (3, 5, 1, 6))
        pygame.draw.rect(s, hilt_dark, (4, 5, 1, 6))
        pygame.draw.rect(s, blade_dark,  (5, 7, 9, 2))
        pygame.draw.rect(s, blade_light, (5, 7, 8, 1))
        pygame.draw.rect(s, blade_mid,   (5, 8, 8, 1))
        pygame.draw.polygon(s, blade_light, [(14, 7), (14, 9), (15, 8)])
        return s

    def _sword_left() -> pygame.Surface:
        s = make_surface(16, 16)
        # Mirror of right — blade on the left.
        pygame.draw.rect(s, hilt_wood, (13, 7, 3, 2))
        pygame.draw.rect(s, hilt_gold, (12, 5, 1, 6))
        pygame.draw.rect(s, hilt_dark, (11, 5, 1, 6))
        pygame.draw.rect(s, blade_dark,  (2, 7, 9, 2))
        pygame.draw.rect(s, blade_light, (3, 7, 8, 1))
        pygame.draw.rect(s, blade_mid,   (3, 8, 8, 1))
        pygame.draw.polygon(s, blade_light, [(2, 7), (2, 9), (1, 8)])
        return s

    icons["sword_down"]  = _sword_down()
    icons["sword_up"]    = _sword_up()
    icons["sword_left"]  = _sword_left()
    icons["sword_right"] = _sword_right()

    return icons


def write_words_1d(handle, ctype: str, name: str, values: list[int]) -> None:
    handle.write(f"const {ctype} {name}[{len(values)}] = {{\n")
    for offset in range(0, len(values), 16):
        chunk = values[offset : offset + 16]
        if ctype == "u16":
            handle.write("    " + ", ".join(f"0x{value:04X}" for value in chunk) + ",\n")
        else:
            handle.write("    " + ", ".join(str(value) for value in chunk) + ",\n")
    handle.write("};\n\n")


def main() -> None:
    _boot_pygame()
    GEN_DIR.mkdir(parents=True, exist_ok=True)

    ground_tile_ids = sorted(TILE_DEFS)
    decor_tile_ids = sorted(DECOR_DEFS)
    ground_surfaces = [render_ground_tile(tile_id) for tile_id in ground_tile_ids]
    decor_surfaces = [render_decor_tile(decor_id) for decor_id in decor_tile_ids]
    player_frames = load_player_frames()
    ui_tiles = build_ui_tiles()
    font_white = build_font_glyph_surfaces((244, 240, 228))
    font_gold = build_font_glyph_surfaces((228, 196, 88))
    npc_surfaces = build_npc_surfaces()
    enemy_surfaces = build_enemy_surfaces()
    boss_surfaces = build_boss_surfaces()
    animal_surfaces = build_animal_surfaces()
    obj_icons = build_obj_icons()

    palette = PaletteBuilder()
    for surface in ground_surfaces + decor_surfaces + player_frames + list(ui_tiles.values()) + font_white + font_gold + npc_surfaces + enemy_surfaces + boss_surfaces + animal_surfaces + list(obj_icons.values()):
        palette.add_surface(surface)

    bg_tile_bytes = [0] * 64
    max_ground_id = max(ground_tile_ids)
    max_decor_id = max(decor_tile_ids)
    ground_bases = [0] * (max_ground_id + 1)
    decor_bases = [0] * (max_decor_id + 1)

    for tile_id, surface in zip(ground_tile_ids, ground_surfaces):
        ground_bases[tile_id] = len(bg_tile_bytes) // 64
        bg_tile_bytes.extend(surface_to_8bpp_tile_bytes(surface, palette))
    for decor_id, surface in zip(decor_tile_ids, decor_surfaces):
        if decor_id == 0:
            decor_bases[decor_id] = 0
        else:
            decor_bases[decor_id] = len(bg_tile_bytes) // 64
            bg_tile_bytes.extend(surface_to_8bpp_tile_bytes(surface, palette))

    ui_tile_names = [
        "blank",
        "fill",
        "fill_alt",
        "hline",
        "vline",
        "corner_tl",
        "corner_tr",
        "corner_bl",
        "corner_br",
        "heart_full",
        "heart_empty",
        "coin",
        "bar_bg",
        "bar_fill",
        "item_weapon",
        "item_armor",
        "item_accessory",
        "item_potion",
        "item_food",
        "item_key",
        "item_material",
        "slot_n_tl", "slot_n_t", "slot_n_tr",
        "slot_n_l",  "slot_n_c", "slot_n_r",
        "slot_n_bl", "slot_n_b", "slot_n_br",
        "slot_a_tl", "slot_a_t", "slot_a_tr",
        "slot_a_l",  "slot_a_c", "slot_a_r",
        "slot_a_bl", "slot_a_b", "slot_a_br",
    ]
    ui_tile_indices: dict[str, int] = {}
    ui_tile_bytes: list[int] = []
    for name in ui_tile_names:
        ui_tile_indices[name] = len(ui_tile_bytes) // 64
        ui_tile_bytes.extend(surface_to_8bpp_tile_bytes(ui_tiles[name], palette))
    font_white_base = len(ui_tile_bytes) // 64
    for surface in font_white:
        ui_tile_bytes.extend(surface_to_8bpp_tile_bytes(surface, palette))
    font_gold_base = len(ui_tile_bytes) // 64
    for surface in font_gold:
        ui_tile_bytes.extend(surface_to_8bpp_tile_bytes(surface, palette))

    obj_tile_bytes: list[int] = []
    # OBJ attr2 tile index always addresses 32-byte slots on GBA hardware,
    # even in 8bpp mode where each 8x8 tile is 64 bytes.  Divide by 32.
    player_frame_bases: list[int] = []
    for surface in player_frames:
        player_frame_bases.append(len(obj_tile_bytes) // 32)
        obj_tile_bytes.extend(surface_to_8bpp_tile_bytes(surface, palette))

    npc_bases: list[int] = []
    for surface in npc_surfaces:
        npc_bases.append(len(obj_tile_bytes) // 32)
        obj_tile_bytes.extend(surface_to_8bpp_tile_bytes(surface, palette))

    enemy_bases: list[int] = []
    for surface in enemy_surfaces:
        enemy_bases.append(len(obj_tile_bytes) // 32)
        obj_tile_bytes.extend(surface_to_8bpp_tile_bytes(surface, palette))

    boss_bases: list[int] = []
    for surface in boss_surfaces:
        boss_bases.append(len(obj_tile_bytes) // 32)
        obj_tile_bytes.extend(surface_to_8bpp_tile_bytes(surface, palette))

    animal_bases: list[int] = []
    for surface in animal_surfaces:
        animal_bases.append(len(obj_tile_bytes) // 32)
        obj_tile_bytes.extend(surface_to_8bpp_tile_bytes(surface, palette))

    icon_bases: dict[str, int] = {}
    for name in ("coin", "item", "lore", "slash",
                 "sword_down", "sword_up", "sword_left", "sword_right"):
        icon_bases[name] = len(obj_tile_bytes) // 32
        obj_tile_bytes.extend(surface_to_8bpp_tile_bytes(obj_icons[name], palette))

    bg_halfwords = bytes_to_halfwords(bg_tile_bytes)
    ui_halfwords = bytes_to_halfwords(ui_tile_bytes)
    obj_halfwords = bytes_to_halfwords(obj_tile_bytes)

    if len(bg_tile_bytes) // 64 > 256:
        raise RuntimeError(f"BG tile pack exceeds charblock budget: {len(bg_tile_bytes) // 64} tiles")
    if len(ui_tile_bytes) // 64 > 256:
        raise RuntimeError(f"UI tile pack exceeds charblock budget: {len(ui_tile_bytes) // 64} tiles")
    if len(obj_tile_bytes) // 64 > 256:
        raise RuntimeError(f"OBJ tile pack exceeds hardware sprite budget: {len(obj_tile_bytes) // 64} tiles")

    header_path = GEN_DIR / "assets.h"
    source_path = GEN_DIR / "assets.c"

    with open(header_path, "w", encoding="utf-8", newline="\n") as header:
        header.write("/* Auto-generated by gba_project/convert_assets.py */\n")
        header.write("#ifndef MYTHICAL_GBA_ASSETS_H\n#define MYTHICAL_GBA_ASSETS_H\n\n")
        header.write('#include "../gba.h"\n\n')
        header.write(f"#define GBA_TILE_SIZE {GBA_TILE_SIZE}\n")
        header.write(f"#define GBA_PLAYER_W {PLAYER_SIZE}\n")
        header.write(f"#define GBA_PLAYER_H {PLAYER_SIZE}\n")
        header.write(f"#define GBA_GROUND_TILE_COUNT {len(ground_bases)}\n")
        header.write(f"#define GBA_DECOR_TILE_COUNT {len(decor_bases)}\n")
        header.write(f"#define GBA_PLAYER_FRAME_COUNT {len(player_frame_bases)}\n")
        header.write(f"#define GBA_BG_TILE_COUNT {len(bg_tile_bytes) // 64}\n")
        header.write(f"#define GBA_UI_TILE_COUNT {len(ui_tile_bytes) // 64}\n")
        header.write(f"#define GBA_OBJ_TILE_COUNT {len(obj_tile_bytes) // 64}\n")
        header.write(f"#define GBA_FONT_TILE_COUNT {len(font_white)}\n")
        header.write(f"#define GBA_UI_TILE_BLANK {ui_tile_indices['blank']}\n")
        header.write(f"#define GBA_UI_TILE_FILL {ui_tile_indices['fill']}\n")
        header.write(f"#define GBA_UI_TILE_FILL_ALT {ui_tile_indices['fill_alt']}\n")
        header.write(f"#define GBA_UI_TILE_HLINE {ui_tile_indices['hline']}\n")
        header.write(f"#define GBA_UI_TILE_VLINE {ui_tile_indices['vline']}\n")
        header.write(f"#define GBA_UI_TILE_CORNER_TL {ui_tile_indices['corner_tl']}\n")
        header.write(f"#define GBA_UI_TILE_CORNER_TR {ui_tile_indices['corner_tr']}\n")
        header.write(f"#define GBA_UI_TILE_CORNER_BL {ui_tile_indices['corner_bl']}\n")
        header.write(f"#define GBA_UI_TILE_CORNER_BR {ui_tile_indices['corner_br']}\n")
        header.write(f"#define GBA_UI_TILE_HEART_FULL {ui_tile_indices['heart_full']}\n")
        header.write(f"#define GBA_UI_TILE_HEART_EMPTY {ui_tile_indices['heart_empty']}\n")
        header.write(f"#define GBA_UI_TILE_COIN {ui_tile_indices['coin']}\n")
        header.write(f"#define GBA_UI_TILE_BAR_BG {ui_tile_indices['bar_bg']}\n")
        header.write(f"#define GBA_UI_TILE_BAR_FILL {ui_tile_indices['bar_fill']}\n")
        header.write(f"#define GBA_UI_TILE_ITEM_WEAPON {ui_tile_indices['item_weapon']}\n")
        header.write(f"#define GBA_UI_TILE_ITEM_ARMOR {ui_tile_indices['item_armor']}\n")
        header.write(f"#define GBA_UI_TILE_ITEM_ACCESSORY {ui_tile_indices['item_accessory']}\n")
        header.write(f"#define GBA_UI_TILE_ITEM_POTION {ui_tile_indices['item_potion']}\n")
        header.write(f"#define GBA_UI_TILE_ITEM_FOOD {ui_tile_indices['item_food']}\n")
        header.write(f"#define GBA_UI_TILE_ITEM_KEY {ui_tile_indices['item_key']}\n")
        header.write(f"#define GBA_UI_TILE_ITEM_MATERIAL {ui_tile_indices['item_material']}\n")
        for prefix in ("slot_n", "slot_a"):
            for pos in ("tl", "t", "tr", "l", "c", "r", "bl", "b", "br"):
                macro = f"GBA_UI_TILE_{prefix.upper()}_{pos.upper()}"
                header.write(f"#define {macro} {ui_tile_indices[f'{prefix}_{pos}']}\n")
        header.write(f"#define GBA_UI_FONT_WHITE_BASE {font_white_base}\n")
        header.write(f"#define GBA_UI_FONT_GOLD_BASE {font_gold_base}\n")
        header.write(f"#define GBA_OBJ_ICON_COIN_BASE {icon_bases['coin']}\n")
        header.write(f"#define GBA_OBJ_ICON_ITEM_BASE {icon_bases['item']}\n")
        header.write(f"#define GBA_OBJ_ICON_LORE_BASE {icon_bases['lore']}\n")
        header.write(f"#define GBA_OBJ_ICON_SLASH_BASE {icon_bases['slash']}\n")
        header.write(f"#define GBA_OBJ_ICON_SWORD_DOWN_BASE {icon_bases['sword_down']}\n")
        header.write(f"#define GBA_OBJ_ICON_SWORD_UP_BASE {icon_bases['sword_up']}\n")
        header.write(f"#define GBA_OBJ_ICON_SWORD_LEFT_BASE {icon_bases['sword_left']}\n")
        header.write(f"#define GBA_OBJ_ICON_SWORD_RIGHT_BASE {icon_bases['sword_right']}\n")
        header.write("\n")
        header.write("extern const u16 gba_palette[256];\n")
        header.write(f"extern const u16 gba_bg_tiles[{len(bg_halfwords)}];\n")
        header.write(f"extern const u16 gba_ui_tiles[{len(ui_halfwords)}];\n")
        header.write(f"extern const u16 gba_obj_tiles[{len(obj_halfwords)}];\n")
        header.write(f"extern const u16 gba_ground_tile_bases[{len(ground_bases)}];\n")
        header.write(f"extern const u16 gba_decor_tile_bases[{len(decor_bases)}];\n")
        header.write(f"extern const u16 gba_player_frame_bases[{len(player_frame_bases)}];\n")
        header.write(f"extern const u16 gba_npc_sprite_bases[{len(npc_bases)}];\n")
        header.write(f"extern const u16 gba_enemy_sprite_bases[{len(enemy_bases)}];\n")
        header.write(f"extern const u16 gba_boss_sprite_bases[{len(boss_bases)}];\n")
        header.write(f"extern const u16 gba_animal_sprite_bases[{len(animal_bases)}];\n")
        header.write("#endif\n")

    with open(source_path, "w", encoding="utf-8", newline="\n") as source:
        source.write("/* Auto-generated by gba_project/convert_assets.py */\n")
        source.write('#include "assets.h"\n\n')
        write_words_1d(source, "u16", "gba_palette", palette.words())
        write_words_1d(source, "u16", "gba_bg_tiles", bg_halfwords)
        write_words_1d(source, "u16", "gba_ui_tiles", ui_halfwords)
        write_words_1d(source, "u16", "gba_obj_tiles", obj_halfwords)
        write_words_1d(source, "u16", "gba_ground_tile_bases", ground_bases)
        write_words_1d(source, "u16", "gba_decor_tile_bases", decor_bases)
        write_words_1d(source, "u16", "gba_player_frame_bases", player_frame_bases)
        write_words_1d(source, "u16", "gba_npc_sprite_bases", npc_bases)
        write_words_1d(source, "u16", "gba_enemy_sprite_bases", enemy_bases)
        write_words_1d(source, "u16", "gba_boss_sprite_bases", boss_bases)
        write_words_1d(source, "u16", "gba_animal_sprite_bases", animal_bases)

    manifest = {
        "palette_size": len(palette.colors),
        "bg_tile_count": len(bg_tile_bytes) // 64,
        "ui_tile_count": len(ui_tile_bytes) // 64,
        "obj_tile_count": len(obj_tile_bytes) // 64,
        "font_face": "lucon.ttf/consola fallback",
        "font_cell": FONT_CELL,
        "player_frames": len(player_frame_bases),
        "npc_sprites": len(npc_bases),
        "enemy_sprites": len(enemy_bases),
        "boss_sprites": len(boss_bases),
        "animal_sprites": len(animal_bases),
    }
    with open(GEN_DIR / "assets_manifest.json", "w", encoding="utf-8", newline="\n") as manifest_file:
        json.dump(manifest, manifest_file, indent=2)

    print(f"Wrote {header_path}")
    print(f"Wrote {source_path}")


if __name__ == "__main__":
    main()
