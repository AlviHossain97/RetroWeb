"""
asset_manager.py - Loads and serves all sprite assets for Bastion TD.

All sprites are loaded once at init from assets/extracted/ metadata.json files.
Scaling uses pygame.transform.scale (nearest-neighbour) to keep pixel art crisp.
If any sprite fails to load, a warning is logged and primitive fallback is used.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import pygame

from settings import (
    TILE_SIZE,
    TOWER_ORDER,
    TERRAIN_EMPTY, TERRAIN_PATH, TERRAIN_ROCK, TERRAIN_WATER,
    TERRAIN_TREE, TERRAIN_SPAWN, TERRAIN_BASE, TERRAIN_TOWER,
)

log = logging.getLogger("asset_manager")

# Base directory for extracted sprites (relative to project root)
_ASSET_ROOT = Path(__file__).parent / "assets" / "extracted"


def _load_metadata(folder: str) -> list[dict]:
    """Load sprites list from a metadata.json inside _ASSET_ROOT/folder."""
    meta_path = _ASSET_ROOT / folder / "metadata.json"
    if not meta_path.exists():
        log.warning("Missing metadata: %s", meta_path)
        return []
    with open(meta_path) as f:
        data = json.load(f)
    return data.get("sprites", [])


def _load_image(folder: str, filename: str) -> pygame.Surface | None:
    """Load a single PNG with convert_alpha(). Returns None on failure."""
    path = _ASSET_ROOT / folder / filename
    if not path.exists():
        log.warning("Missing sprite: %s", path)
        return None
    try:
        return pygame.image.load(str(path)).convert_alpha()
    except pygame.error as e:
        log.warning("Failed to load %s: %s", path, e)
        return None


def _scale(surface: pygame.Surface, w: int, h: int) -> pygame.Surface:
    """Nearest-neighbour scale (never smoothscale)."""
    return pygame.transform.scale(surface, (w, h))


def _tint(surface: pygame.Surface, color: tuple[int, int, int], alpha: int = 80) -> pygame.Surface:
    """Return a copy of surface with a semi-transparent colour overlay."""
    tinted = surface.copy()
    overlay = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
    overlay.fill((*color, alpha))
    tinted.blit(overlay, (0, 0))
    return tinted


class AssetManager:
    """Central sprite registry. Instantiate once after pygame.init()."""

    def __init__(self) -> None:
        self._towers: dict[str, pygame.Surface] = {}     # "type_level" -> Surface
        self._enemies: dict[str, pygame.Surface] = {}     # enemy_type -> Surface
        self._tileset_cache: dict[str, pygame.Surface] = {}       # "theme_row_col" -> Surface
        self._props: dict[str, pygame.Surface] = {}       # "group_variant" -> Surface
        self._ui: dict[str, pygame.Surface] = {}           # "row_col" -> Surface
        self._prop_list: list[dict] = []                   # raw prop metadata for reference

        self._load_towers()
        self._load_enemies()
        self._load_tiles()
        self._load_props()
        self._load_ui()
        log.info(
            "AssetManager loaded: %d towers, %d enemies, %d tiles, %d props, %d ui",
            len(self._towers), len(self._enemies), len(self._tileset_cache),
            len(self._props), len(self._ui),
        )

    # ------------------------------------------------------------------
    # Tower sprites
    # ------------------------------------------------------------------
    # Spritesheet layout: row=sprite_type (0-2), col=upgrade_level (0-2)
    # Game tower -> sprite type mapping:
    #   arrow->0, cannon->1, ice->2, lightning->1(tint yellow), flame->2(tint orange)

    _TOWER_TYPE_MAP = {
        "arrow": (0, None),
        "cannon": (1, None),
        "ice": (2, None),
        "lightning": (1, (200, 200, 60)),   # yellow tint
        "flame": (2, (220, 100, 40)),       # orange tint
    }

    def _load_towers(self) -> None:
        sprites = _load_metadata("towers")
        raw: dict[str, pygame.Surface] = {}
        for s in sprites:
            img = _load_image("towers", s["file"])
            if img:
                key = f"{s['row']}_{s['col']}"
                raw[key] = img

        # Build per-tower-type, per-level sprites scaled to TILE_SIZE
        for tower_type, (sprite_row, tint_color) in self._TOWER_TYPE_MAP.items():
            for game_level in range(1, 4):  # 1, 2, 3
                sprite_col = game_level - 1  # 0, 1, 2
                raw_key = f"{sprite_row}_{sprite_col}"
                base = raw.get(raw_key)
                if base is None:
                    continue
                scaled = _scale(base, TILE_SIZE, TILE_SIZE)
                if tint_color:
                    scaled = _tint(scaled, tint_color, 60)
                self._towers[f"{tower_type}_{game_level}"] = scaled

    def get_tower_sprite(self, tower_type: str, level: int) -> pygame.Surface | None:
        """Get tower sprite scaled to TILE_SIZE. Returns None if unavailable."""
        return self._towers.get(f"{tower_type}_{level}")

    # ------------------------------------------------------------------
    # Enemy sprites
    # ------------------------------------------------------------------
    _ENEMY_CHAR_MAP = {
        "goblin": ("char_0.png", 1.0),
        "wolf": ("char_1.png", 1.0),
        "swarm": ("char_1.png", 0.7),
        "knight": ("char_2.png", 1.0),
        "healer": ("char_3.png", 1.0),
        "titan": ("char_4.png", 2.0),
    }

    def _load_enemies(self) -> None:
        sprites = _load_metadata("characters")
        raw: dict[str, pygame.Surface] = {}
        for s in sprites:
            img = _load_image("characters", s["file"])
            if img:
                raw[s["file"]] = img

        for enemy_type, (filename, scale_mult) in self._ENEMY_CHAR_MAP.items():
            base = raw.get(filename)
            if base is None:
                continue
            # Scale to a reasonable pixel size based on the enemy's visual size
            # from ENEMY_DEFS. We pre-scale at a base of TILE_SIZE * 0.8 * scale_mult
            target = max(8, int(TILE_SIZE * 0.6 * scale_mult))
            # Maintain aspect ratio, fit within target x target
            ow, oh = base.get_size()
            aspect = ow / oh if oh else 1
            if aspect >= 1:
                sw = target
                sh = max(1, int(target / aspect))
            else:
                sh = target
                sw = max(1, int(target * aspect))
            self._enemies[enemy_type] = _scale(base, sw, sh)

    def get_enemy_sprite(self, enemy_type: str) -> pygame.Surface | None:
        """Get enemy sprite pre-scaled to fit its rendered radius."""
        return self._enemies.get(enemy_type)

    # ------------------------------------------------------------------
    # Tile sprites
    # ------------------------------------------------------------------
    # Tile sprites
    # ------------------------------------------------------------------
    # Grass: green_edge_1 (flat green, 32x16 → scale to 32x32)
    # Path:  sand_0_0 / sand_0_1 (cobblestone circles, 48x48 → scale to 32x32)
    # Water: cyan_0_0 (cyan circular, 48x48 → scale to 32x32)
    # Rock/Tree/Spawn/Base/Tower: grass base (primitives draw detail on top)

    def _load_tiles(self) -> None:
        # Load ALL tileset images by filename
        sprites = _load_metadata("tileset1")
        raw: dict[str, pygame.Surface] = {}
        for s in sprites:
            img = _load_image("tileset1", s["file"])
            if img:
                key = s["file"].replace(".png", "")
                raw[key] = img

        ts = TILE_SIZE

        # Grass: green_edge_1 (32x16) → scale to 32x32
        grass = raw.get("green_edge_1")
        if grass:
            self._tileset_cache["grass"] = _scale(grass, ts, ts)

        # Path: sand_0_0 and sand_0_1 (48x48 cobblestone) → scale to 32x32
        for key in ("sand_0_0", "sand_0_1"):
            base = raw.get(key)
            if base:
                self._tileset_cache[key] = _scale(base, ts, ts)

        # Water: cyan_0_0 (48x48) → scale to 32x32
        water = raw.get("cyan_0_0")
        if water:
            self._tileset_cache["water"] = _scale(water, ts, ts)

        # Spawn: sand_0_0 with red tint
        spawn_base = raw.get("sand_0_0")
        if spawn_base:
            self._tileset_cache["spawn"] = _tint(_scale(spawn_base, ts, ts), (200, 50, 50), 100)

        # Base: cyan_0_0 with blue tint
        base_tile = raw.get("cyan_0_0")
        if base_tile:
            self._tileset_cache["base"] = _tint(_scale(base_tile, ts, ts), (50, 80, 220), 100)

    def get_tile_sprite(self, terrain_type: int, tx: int, ty: int) -> pygame.Surface | None:
        if terrain_type == TERRAIN_EMPTY or terrain_type == TERRAIN_TOWER:
            return self._tileset_cache.get("grass")
        if terrain_type == TERRAIN_PATH:
            return self._tileset_cache.get("sand_0_0")
        if terrain_type == TERRAIN_WATER:
            return self._tileset_cache.get("water")
        if terrain_type == TERRAIN_SPAWN:
            return self._tileset_cache.get("spawn")
        if terrain_type == TERRAIN_BASE:
            return self._tileset_cache.get("base")
        # Rock, Tree: return grass — primitive renderer draws detail on top
        if terrain_type in (TERRAIN_ROCK, TERRAIN_TREE):
            return self._tileset_cache.get("grass")
        return None

    # ------------------------------------------------------------------
    # Prop sprites
    # ------------------------------------------------------------------
    def _load_props(self) -> None:
        sprites = _load_metadata("props")
        self._prop_list = sprites
        for s in sprites:
            img = _load_image("props", s["file"])
            if img:
                key = f"{s['row']}_{s['col']}"
                self._props[key] = img

    def get_prop_sprite(self, group: int, variant: int) -> pygame.Surface | None:
        """Get a prop sprite by group (row) and variant (col) at native scale."""
        return self._props.get(f"{group}_{variant}")

    def get_prop_count(self) -> dict[int, int]:
        """Return {group: max_variant_count} for prop scattering."""
        counts: dict[int, int] = {}
        for s in self._prop_list:
            g = s["row"]
            counts[g] = counts.get(g, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # UI sprites
    # ------------------------------------------------------------------
    def _load_ui(self) -> None:
        sprites = _load_metadata("ui")
        for s in sprites:
            img = _load_image("ui", s["file"])
            if img:
                key = f"{s['row']}_{s['col']}"
                self._ui[key] = img

    def get_ui_sprite(self, row: int, col: int) -> pygame.Surface | None:
        """Get a UI sprite by row and col from the UI sheet."""
        return self._ui.get(f"{row}_{col}")
