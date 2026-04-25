"""
Core gameplay state — integrates maps, player, NPCs, enemies, boss,
combat, effects, items, quests, transitions, difficulty, AI, and persistence.
"""

from __future__ import annotations

import math
import random

import pygame

from ai.config_loader import (
    get_difficulty_config,
    get_stage_boss_loot,
    get_stage_boss_xp,
    get_stage_difficulty_override,
    get_stage_player_hp_bonus,
)
from ai.debug import DebugToggles, render_ai_debug
from ai.influence import InfluenceMapCache
from ai.pathfinding import quantize_tile
from boss import Boss
from boss2 import Gravewarden
from boss3 import MythicSovereign
from camera import Camera
from combat import attack_has_los, circle_hits_entity, get_attack_hitbox
from content_registry import (
    BGM_MAP as _BGM_MAP_S1,
    BOSS_DEFS as _BOSS_DEFS_S1,
    CHEST_DEFS as _CHEST_DEFS_S1,
    ENEMY_SPAWN_DEFS as _ENEMY_SPAWN_DEFS_S1,
    GROUND_ITEM_DEFS as _GROUND_ITEM_DEFS_S1,
    NPC_DEFS as _NPC_DEFS_S1,
    ENV_DEFS as _ENV_DEFS_S1,
    LORE_ITEM_DEFS as _LORE_ITEM_DEFS_S1,
    FAST_TRAVEL_HINTS as _FT_HINTS_S1,
)
from content.stage2_content import (
    BGM_MAP as _BGM_MAP_S2,
    BOSS_DEFS as _BOSS_DEFS_S2,
    CHEST_DEFS as _CHEST_DEFS_S2,
    ENEMY_SPAWN_DEFS as _ENEMY_SPAWN_DEFS_S2,
    GROUND_ITEM_DEFS as _GROUND_ITEM_DEFS_S2,
    NPC_DEFS as _NPC_DEFS_S2,
    ENV_DEFS as _ENV_DEFS_S2,
    LORE_ITEM_DEFS as _LORE_ITEM_DEFS_S2,
    FAST_TRAVEL_HINTS as _FT_HINTS_S2,
)
from content.stage3_content import (
    BGM_MAP as _BGM_MAP_S3,
    BOSS_DEFS as _BOSS_DEFS_S3,
    CHEST_DEFS as _CHEST_DEFS_S3,
    ENEMY_SPAWN_DEFS as _ENEMY_SPAWN_DEFS_S3,
    GROUND_ITEM_DEFS as _GROUND_ITEM_DEFS_S3,
    NPC_DEFS as _NPC_DEFS_S3,
    ENV_DEFS as _ENV_DEFS_S3,
    LORE_ITEM_DEFS as _LORE_ITEM_DEFS_S3,
    FAST_TRAVEL_HINTS as _FT_HINTS_S3,
)
from dialogue import DialogueBox
from effects import DamageNumberSystem, ParticleSystem, ScreenShake
from enemy import Enemy
from hud import HUD
from interactable import Chest, GroundItem
from inventory import ITEM_DEFS, Inventory
from map_manager import MapManager
from maps.dungeon import DUNGEON
from maps.village import VILLAGE
from maps.ruins import RUINS_APPROACH, RUINS_DEPTHS
from maps.sanctum import SANCTUM_HALLS, THRONE_ROOM
from npc import NPC
from player import Player
from player_forms import PlayerForms
from quest import QuestManager
from rewards import (
    REWARD_CURRENCY,
    REWARD_HEAL,
    REWARD_KEY_ITEM,
    make_key_item_reward,
    normalize_reward,
)
from settings import *
from states.state_machine import State
from tilemap import TileMap

# v4 systems
from animal_spawner import AnimalSpawner
from environmental import EnvironmentalManager
from weather import WeatherSystem
from post_process import PostProcessor
from lighting import LightingSystem, build_static_lights_for_map
from fast_travel import FastTravelManager, WAYPOINT_DEFS
from game_math import angle_between_vectors_deg, point_distance
from crafting import CraftingManager


MAP_REGISTRY = {
    "village": VILLAGE,
    "dungeon": DUNGEON,
    "ruins_approach": RUINS_APPROACH,
    "ruins_depths": RUINS_DEPTHS,
    "sanctum_halls": SANCTUM_HALLS,
    "throne_room": THRONE_ROOM,
}

# ── Stage-specific content tables merged into unified dicts ──────────────────
# Maps within a stage share the same content registry
_STAGE_MAPS = {
    "village": 1,
    "dungeon": 1,
    "ruins_approach": 2,
    "ruins_depths": 2,
    "sanctum_halls": 3,
    "throne_room": 3,
}
_NPC_DEFS_ALL = {**_NPC_DEFS_S1, **_NPC_DEFS_S2, **_NPC_DEFS_S3}
_BOSS_DEFS_ALL = {**_BOSS_DEFS_S1, **_BOSS_DEFS_S2, **_BOSS_DEFS_S3}
_CHEST_DEFS_ALL = {**_CHEST_DEFS_S1, **_CHEST_DEFS_S2, **_CHEST_DEFS_S3}
_ENEMY_DEFS_ALL = {
    **_ENEMY_SPAWN_DEFS_S1,
    **_ENEMY_SPAWN_DEFS_S2,
    **_ENEMY_SPAWN_DEFS_S3,
}
_GROUND_DEFS_ALL = {
    **_GROUND_ITEM_DEFS_S1,
    **_GROUND_ITEM_DEFS_S2,
    **_GROUND_ITEM_DEFS_S3,
}
_ENV_DEFS_ALL = {**_ENV_DEFS_S1, **_ENV_DEFS_S2, **_ENV_DEFS_S3}
_LORE_DEFS_ALL = {**_LORE_ITEM_DEFS_S1, **_LORE_ITEM_DEFS_S2, **_LORE_ITEM_DEFS_S3}
_BGM_MAP_ALL = {**_BGM_MAP_S1, **_BGM_MAP_S2, **_BGM_MAP_S3}
_FT_HINTS_ALL = {**_FT_HINTS_S1, **_FT_HINTS_S2, **_FT_HINTS_S3}
DEATH_SEQUENCE_DURATION = 1.0


def _nearest_passable(tx, ty, tilemap, max_search=5):
    if tilemap.is_passable(float(tx), float(ty)):
        return tx, ty
    for radius in range(1, max_search + 1):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if abs(dx) != radius and abs(dy) != radius:
                    continue
                nx, ny = tx + dx, ty + dy
                if tilemap.is_passable(float(nx), float(ny)):
                    return nx, ny
    return tx, ty


class GameplayState(State):
    def __init__(self, game):
        super().__init__(game)
        profile = getattr(game, "target_profile", None)
        self.viewport_width = getattr(profile, "screen_width", SCREEN_WIDTH)
        self.viewport_height = getattr(profile, "screen_height", SCREEN_HEIGHT)
        self.map_mgr = MapManager(
            self.viewport_width,
            self.viewport_height,
            supports_alpha=getattr(profile, "supports_alpha", True),
        )
        for name, data in MAP_REGISTRY.items():
            self.map_mgr.register(name, data)

        self.dialogue = DialogueBox(self.viewport_width, self.viewport_height)
        self.hud = HUD(self.viewport_width, self.viewport_height)
        self.particles = ParticleSystem()
        self.dmg_numbers = DamageNumberSystem()
        self.shake = ScreenShake()
        self.influence_cache = InfluenceMapCache()
        self.debug_toggles = DebugToggles()

        # v4 systems
        self.animal_spawner = AnimalSpawner(getattr(game, "difficulty_mode", "normal"))
        self.env_manager = EnvironmentalManager()
        self.weather = WeatherSystem(
            viewport_width=self.viewport_width,
            viewport_height=self.viewport_height,
        )
        self.post_process = PostProcessor(
            self.viewport_width,
            self.viewport_height,
            supports_alpha=getattr(profile, "supports_alpha", True),
        )
        self.lighting = LightingSystem(
            self.viewport_width,
            self.viewport_height,
            supports_alpha=getattr(profile, "supports_alpha", True),
        )
        self.fast_travel_mgr = FastTravelManager()
        self.crafting_manager = CraftingManager()
        # Dash state
        self._dash_timer = 0.0
        self._dash_active = False
        self._dash_vx = 0.0
        self._dash_vy = 0.0
        self._dash_cooldown = 0.0

        self._pending_give_item = None
        self._pending_give_extras: list[str] = []
        self._pending_take_item = None
        self._pending_npc_trigger = None

        self.opened_chests: set[str] = set()
        self.collected_items: set[str] = set()
        self.defeated_enemy_ids: set[str] = set()
        self.dynamic_drop_records: list[dict] = []
        self.defeated_boss = False
        self.boss_save_state: dict = {}
        self.checkpoint_data: dict | None = None

        self.boss = None
        self.boss_triggered = False
        self._boss_defeat_timer = 0.0
        self._current_boss_id = None
        self.enemies: list[Enemy] = []
        self.npcs: list[NPC] = []
        self.chests: list[Chest] = []
        self.ground_items: list[GroundItem] = []
        self.current_signs: dict = {}
        self.player = None
        self.flow_state = "normal"
        self.death_transition_timer = 0.0
        self._aura_timer = 0.0
        self.player_forms: PlayerForms | None = None

        self._load_map("village", capture_checkpoint=True, grant_transition_heal=False)
        self._sync_player_weapon()
        self._init_player_forms()

    def enter(self):
        if self.player_forms is None:
            self._init_player_forms()

    def _init_player_forms(self) -> None:
        """Initialize the PlayerForms helper (uses game.campaign)."""
        campaign = getattr(self.game, "campaign", None)
        if campaign is not None:
            self.player_forms = PlayerForms(campaign)

    def _get_stage_difficulty_config(self) -> dict:
        """
        Return a difficulty config extended with stage-specific scaling factors.
        Stage multipliers from data/stage_configs.json are layered on top of
        the base difficulty config.
        """
        base = dict(self._difficulty())
        campaign = getattr(self.game, "campaign", None)
        stage = getattr(campaign, "world_stage", 1)
        sm = get_stage_difficulty_override(stage, self.game.difficulty_mode)
        # Blend into boss_stat_mults
        existing_boss = dict(base.get("boss_stat_mults", {}))
        existing_boss["hp"] = existing_boss.get("hp", 1.0) * sm.get("boss_hp_mult", 1.0)
        existing_boss["damage"] = existing_boss.get("damage", 1.0) * sm.get(
            "boss_damage_mult", 1.0
        )
        existing_boss["speed"] = existing_boss.get("speed", 1.0) * sm.get(
            "boss_speed_mult", sm.get("enemy_speed_mult", 1.0)
        )
        base["boss_stat_mults"] = existing_boss
        # Store stage config fields for boss constructors / phases
        base["_stage_config"] = sm
        # Blend into enemy_stat_mults
        existing_enemy = dict(base.get("enemy_stat_mults", {}))
        existing_enemy["hp"] = existing_enemy.get("hp", 1.0) * sm.get(
            "enemy_hp_mult", 1.0
        )
        existing_enemy["damage"] = existing_enemy.get("damage", 1.0) * sm.get(
            "enemy_damage_mult", 1.0
        )
        existing_enemy["speed"] = existing_enemy.get("speed", 1.0) * sm.get(
            "enemy_speed_mult", 1.0
        )
        base["enemy_stat_mults"] = existing_enemy
        return base

    def _difficulty(self) -> dict:
        return (
            self.game.difficulty_config
            if hasattr(self.game, "difficulty_config")
            else get_difficulty_config("normal")
        )

    def _get_stage_hp_bonus(self, stage: int | None = None) -> int:
        campaign = getattr(self.game, "campaign", None)
        current_stage = (
            stage if stage is not None else getattr(campaign, "world_stage", 1)
        )
        fallback = max(0, (int(current_stage) - 1) * 2)
        return get_stage_player_hp_bonus(current_stage, fallback=fallback)

    def _sync_player_max_hp(self, *, heal_for_growth: bool = False) -> int:
        if not self.player:
            return 0
        old_max = getattr(self.player, "max_hp", PLAYER_MAX_HP)
        new_max = PLAYER_MAX_HP + self._get_stage_hp_bonus()
        self.player.max_hp = new_max
        if self.player.hp > self.player.max_hp:
            self.player.hp = self.player.max_hp
        growth = max(0, new_max - old_max)
        if heal_for_growth and growth > 0:
            self.player.hp = min(self.player.max_hp, self.player.hp + growth)
        return growth

    def _reset_flow_state(self):
        self.flow_state = "normal"
        self.death_transition_timer = 0.0
        self.post_process.reset_death_fade()

    def _clear_pending_actions(self):
        self._pending_give_item = None
        self._pending_give_extras = []
        self._pending_take_item = None
        self._pending_npc_trigger = None

    def _trigger_player_death(self):
        if self.flow_state == "player_dying":
            return
        assert self.player.hp <= 0 or not self.player.is_alive, (
            "Death flow triggered while player is still alive"
        )
        self.player.hp = 0
        self.player.state = "dead"
        self.player.state_timer = 0.0
        self.player.iframes = max(self.player.iframes, 0.2)
        self.player.knockback_vx = 0.0
        self.player.knockback_vy = 0.0
        self.post_process.trigger_death_fade()
        self.flow_state = "player_dying"
        self.death_transition_timer = DEATH_SEQUENCE_DURATION
        self.dialogue.close()
        self._clear_pending_actions()

    def _update_death_sequence(self, dt: float) -> bool:
        if self.flow_state != "player_dying":
            return False
        self.player.state_timer += dt
        self.death_transition_timer = max(0.0, self.death_transition_timer - dt)
        if self.death_transition_timer <= 0.0:
            self.flow_state = "game_over_transition"
            self.game.states.change("game_over")
        return True

    def _get_weapon_def(self) -> dict:
        """Return the ITEM_DEFS entry for the weapon in the active hotbar slot, or {}."""
        from item_system import ITEM_DEFS

        stack = self.game.inventory.grid.active_item
        if stack:
            idef = ITEM_DEFS.get(stack.item_id, {})
            if idef.get("equip_slot") == "weapon":
                return idef
        return {}

    def _player_attack_damage(self) -> int:
        mult = self._difficulty().get("player_attack_damage_mult", 1.0)
        base = max(1, int(round(PLAYER_ATTACK_DAMAGE * mult)))
        wdef = self._get_weapon_def()
        base += wdef.get("stats", {}).get("attack", 0)
        if self.player_forms:
            base += self.player_forms.get_stat_bonuses().get("attack_bonus", 0)
        prog = getattr(self.game, "progression", None)
        if prog:
            base += prog.get_combat_stats()["attack_bonus"]
        return max(1, base)

    def _incoming_damage(self, amount: int) -> int:
        mult = self._difficulty().get("player_damage_taken_mult", 1.0)
        reduction = 0
        if self.player_forms:
            reduction += self.player_forms.get_stat_bonuses().get("defense", 0)
        prog = getattr(self.game, "progression", None)
        if prog:
            reduction += prog.get_combat_stats()["defense"]
        return max(1, int(round(amount * mult)) - reduction)

    def _quest_snapshot(self) -> dict:
        data = {}
        for qid, quest in self.game.quest_manager.quests.items():
            data[qid] = {"stage": quest.stage, "complete": quest.complete}
        return data

    def _make_snapshot(self) -> dict:
        boss_state = dict(self.boss_save_state)
        if self.boss and self.map_mgr.current_name == "dungeon":
            boss_state = self.boss.snapshot_state()
        return {
            "map": self.map_mgr.current_name,
            "player_x": self.player.x,
            "player_y": self.player.y,
            "player_hp": self.player.hp,
            "player_facing": self.player.facing,
            "inventory": self.game.inventory.to_save(),
            "quest_stages": self._quest_snapshot(),
            "opened_chests": list(self.opened_chests),
            "collected_items": list(self.collected_items),
            "defeated_boss": self.defeated_boss,
            "defeated_enemies": list(self.defeated_enemy_ids),
            "dynamic_drops": [dict(record) for record in self.dynamic_drop_records],
            "boss_state": boss_state,
            "difficulty": self.game.difficulty_mode,
            "coins": self.game.wallet.coins,
            "fast_travel": self.fast_travel_mgr.to_save(),
            "progression": self.game.progression.to_save()
            if hasattr(self.game, "progression")
            else {},
            "reputation": self.game.reputation.to_save()
            if hasattr(self.game, "reputation")
            else {},
            "bestiary_info": self.game.bestiary.to_save()
            if hasattr(self.game, "bestiary")
            else {},
            "campaign": self.game.campaign.to_save()
            if hasattr(self.game, "campaign")
            else {},
            "killed_animals": list(self.animal_spawner.collect_killed_ids())
            if hasattr(self, "animal_spawner")
            else [],
        }

    def capture_checkpoint(self):
        self.checkpoint_data = self._make_snapshot()

    def restore_checkpoint(self):
        if not self.checkpoint_data:
            return False
        data = dict(self.checkpoint_data)
        self.game.set_difficulty(data.get("difficulty", self.game.difficulty_mode))
        self.game.inventory = Inventory.from_save(data.get("inventory", {}))
        self.game.wallet.set(data.get("coins", 0))
        self.game.quest_manager = QuestManager()
        for qid, qdata in data.get("quest_stages", {}).items():
            quest = self.game.quest_manager.get_quest(qid)
            if quest:
                quest.stage = qdata["stage"]
                quest.complete = qdata["complete"]
        if "progression" in data:
            from progression import Progression as _Prog

            self.game.progression = _Prog.from_save(data["progression"])
        if "reputation" in data:
            from reputation import Reputation as _Rep

            self.game.reputation = _Rep.from_save(data["reputation"])
        if "bestiary_info" in data:
            from bestiary import Bestiary as _Best

            b = _Best()
            b_data = data["bestiary_info"]
            b.encountered = set(b_data.get("encountered", []))
            b.kills = {k: int(v) for k, v in b_data.get("kills", {}).items()}
            self.game.bestiary = b
        if "campaign" in data:
            from campaign import Campaign as _Camp

            self.game.campaign = _Camp.from_save(data["campaign"])
        if "killed_animals" in data:
            self.animal_spawner._killed_ids = set(data["killed_animals"])
        self.apply_save_data(data, capture_checkpoint=False)
        if "fast_travel" in data:
            self.fast_travel_mgr = FastTravelManager.from_save(data["fast_travel"])
        self._sync_player_weapon()
        respawn_ratio = self._difficulty().get("respawn_hp_ratio", 0.85)
        bonus = self._difficulty().get("checkpoint_heal_bonus", 0)
        min_hp = int(math.ceil(self.player.max_hp * respawn_ratio)) + int(bonus)
        self.player.hp = min(self.player.max_hp, max(self.player.hp, min_hp))
        self.player.state = "idle"
        self.player.state_timer = 0.0
        self.player.iframes = 1.0
        self.player.knockback_vx = 0.0
        self.player.knockback_vy = 0.0
        self._reset_flow_state()
        self.particles.particles.clear()
        self.dmg_numbers.numbers.clear()
        self.shake.timer = 0.0
        self.shake.intensity = 0.0
        self.dialogue.close()
        self._clear_pending_actions()
        self.hud.show_notification("Checkpoint restored", 3.0)
        return True

    def get_save_data(self):
        snapshot = self._make_snapshot()
        return {
            "map": snapshot["map"],
            "opened_chests": snapshot["opened_chests"],
            "collected_items": snapshot["collected_items"],
            "defeated_boss": snapshot["defeated_boss"],
            "defeated_enemies": snapshot["defeated_enemies"],
            "dynamic_drops": snapshot["dynamic_drops"],
            "boss_state": snapshot["boss_state"],
            "coins": snapshot["coins"],
        }

    def apply_save_data(self, data, capture_checkpoint=True):
        self.opened_chests = set(data.get("opened_chests", []))
        self.collected_items = set(data.get("collected_items", []))
        self.defeated_enemy_ids = set(data.get("defeated_enemies", []))
        self.dynamic_drop_records = [
            dict(record) for record in data.get("dynamic_drops", [])
        ]
        self.defeated_boss = bool(data.get("defeated_boss", False))
        self.boss_save_state = dict(data.get("boss_state", {}))
        self._load_map(
            data.get("map", "village"),
            spawn=(data.get("player_x", 15), data.get("player_y", 19)),
            capture_checkpoint=capture_checkpoint,
            grant_transition_heal=False,
            preserve_boss_state=True,
            player_facing=data.get("player_facing", "down"),
            player_hp=data.get("player_hp", PLAYER_MAX_HP),
        )
        self._sync_player_weapon()

    def _spawn_npcs(self, map_name, data):
        self.npcs = []
        for nd in _NPC_DEFS_ALL.get(map_name, []):
            pos = data["spawns"].get(nd["spawn_key"], (0, 0))
            self.npcs.append(
                NPC(
                    name=nd["name"],
                    npc_id=nd["npc_id"],
                    tile_x=pos[0],
                    tile_y=pos[1],
                    dialogue_stages=nd["dialogue_stages"],
                    body_color=nd["body_color"],
                    hair_color=nd.get("hair_color"),
                    facing=nd.get("facing", "down"),
                    gives_item=nd.get("gives_item"),
                    takes_item=nd.get("takes_item"),
                )
            )

    def _spawn_chests(self, map_name):
        self.chests = []
        for cd in _CHEST_DEFS_ALL.get(map_name, []):
            if cd["id"] in self.opened_chests:
                continue
            reward = cd.get("reward")
            if reward is None and cd.get("item_id"):
                reward = make_key_item_reward(cd["item_id"], label=cd.get("label"))
            self.chests.append(
                Chest(
                    cd["tile_x"],
                    cd["tile_y"],
                    item_id=cd.get("item_id"),
                    label=cd.get("label", "Chest"),
                    chest_id=cd["id"],
                    reward=reward,
                )
            )

    def _spawn_ground_items(self, map_name):
        self.ground_items = []
        for gd in _GROUND_DEFS_ALL.get(map_name, []):
            if gd["id"] in self.collected_items:
                continue
            gx, gy = _nearest_passable(gd["tile_x"], gd["tile_y"], self.tilemap)
            reward = gd.get("reward")
            if reward is None and gd.get("item_id"):
                reward = make_key_item_reward(
                    gd["item_id"], label=gd.get("label", gd["item_id"])
                )
            self.ground_items.append(
                GroundItem(gx, gy, drop_id=gd["id"], reward=reward)
            )
        for record in self.dynamic_drop_records:
            if record.get("map") != map_name:
                continue
            reward = record.get("reward")
            if reward is None:
                reward = {
                    "kind": record.get("kind", "item"),
                    "item_id": record.get("item_id"),
                    "amount": record.get("amount", record.get("heal")),
                    "label": record.get("label", ""),
                }
            self.ground_items.append(
                GroundItem(
                    record["x"],
                    record["y"],
                    drop_id=record["id"],
                    dynamic=True,
                    reward=reward,
                )
            )

    def _spawn_enemies(self, map_name):
        self.enemies = []
        stage_diff = self._get_stage_difficulty_config()
        for ed in _ENEMY_DEFS_ALL.get(map_name, []):
            if ed["id"] in self.defeated_enemy_ids:
                continue
            self.enemies.append(
                Enemy(
                    ed["type"],
                    ed["x"],
                    ed["y"],
                    spawn_id=ed["id"],
                    difficulty_mode=self.game.difficulty_mode,
                    difficulty_config=stage_diff,
                )
            )

    def _spawn_boss(self, map_name):
        self.boss = None
        self.hud.boss_ref = None
        self.boss_triggered = False
        self._current_boss_id = None
        bd = _BOSS_DEFS_ALL.get(map_name)
        if not bd or self.defeated_boss:
            return
        # Don't respawn bosses from stages the player already completed
        from campaign import STAGE_BOSS_IDS

        campaign = getattr(self.game, "campaign", None)
        boss_id = bd["id"]
        if campaign:
            for stage, bid in STAGE_BOSS_IDS.items():
                if bid == boss_id and stage in campaign.completed_stages:
                    return
        stage_diff = self._get_stage_difficulty_config()
        boss_id = bd["id"]
        self._current_boss_id = boss_id
        if boss_id == "gravewarden":
            self.boss = Gravewarden(
                bd["x"],
                bd["y"],
                boss_id=boss_id,
                difficulty_mode=self.game.difficulty_mode,
                difficulty_config=stage_diff,
            )
        elif boss_id == "mythic_sovereign":
            self.boss = MythicSovereign(
                bd["x"],
                bd["y"],
                boss_id=boss_id,
                difficulty_mode=self.game.difficulty_mode,
                difficulty_config=stage_diff,
            )
        else:
            self.boss = Boss(
                bd["x"],
                bd["y"],
                boss_id=boss_id,
                difficulty_mode=self.game.difficulty_mode,
                difficulty_config=stage_diff,
            )
        if self.boss_save_state:
            self.boss.apply_saved_state(self.boss_save_state)
        self.hud.boss_ref = self.boss

    def _load_map(
        self,
        map_name,
        spawn=None,
        capture_checkpoint=True,
        grant_transition_heal=False,
        preserve_boss_state=False,
        player_facing="down",
        player_hp=PLAYER_MAX_HP,
    ):
        # Reset defeated_boss when entering a different map so future bosses can spawn
        old_map = getattr(self.map_mgr, "current_name", "")
        if old_map and old_map != map_name and not preserve_boss_state:
            self.defeated_boss = False
            self.boss_save_state = {}

        data = self.map_mgr.load(map_name)
        self.tilemap = TileMap(data)
        self.camera = Camera(
            self.tilemap.width,
            self.tilemap.height,
            viewport_width=self.viewport_width,
            viewport_height=self.viewport_height,
        )
        self.current_signs = data.get("signs", {})
        self.influence_cache.invalidate()

        if spawn:
            px, py = float(spawn[0]), float(spawn[1])
        else:
            s = data["spawns"].get("player", (1, 1))
            px, py = float(s[0]), float(s[1])

        if self.player:
            self.player.x = px
            self.player.y = py
        else:
            self.player = Player(px, py)
        self._sync_player_max_hp()
        self.player.facing = player_facing
        self.player.hp = max(1, min(self.player.max_hp, int(player_hp)))
        self.player.state = "idle"
        self.player.state_timer = 0.0
        self.player.iframes = 0.0
        self.player.knockback_vx = 0.0
        self.player.knockback_vy = 0.0
        self._reset_flow_state()
        self._clear_pending_actions()

        self._spawn_npcs(map_name, data)
        self._spawn_chests(map_name)
        self._spawn_ground_items(map_name)
        self._spawn_enemies(map_name)
        self._spawn_boss(map_name)

        bgm = _BGM_MAP_ALL.get(map_name)
        if bgm and hasattr(self.game, "audio"):
            self.game.audio.set_map_audio(bgm)

        # v4 system resets / spawns
        killed = getattr(self.animal_spawner, "_killed_ids", set())
        self.animal_spawner.spawn_for_map(map_name, killed, tilemap=self.tilemap)
        self.env_manager.load_for_map(map_name, _ENV_DEFS_ALL.get(map_name, {}))
        self.weather.set_map(map_name)
        self.post_process.set_map(map_name)
        self.lighting.set_map(map_name)
        self.lighting.set_static_lights(build_static_lights_for_map(map_name, data))

        if grant_transition_heal:
            heal_amount = int(self._difficulty().get("map_transition_heal", 0))
            if heal_amount > 0 and self.player.hp < self.player.max_hp:
                old_hp = self.player.hp
                self.player.heal(heal_amount)
                if self.player.hp > old_hp:
                    self.hud.show_notification(
                        f"Recovered {self.player.hp - old_hp} HP on arrival", 2.0
                    )

        if capture_checkpoint:
            self.capture_checkpoint()

        # Advance any quests that trigger on entering this map
        advanced = self.game.quest_manager.fire_trigger("map_entered", map_name)
        self._unlock_waypoints_for_quests(advanced)

        # Show fast travel hint for this map if there are locked waypoints
        ft_hint = _FT_HINTS_ALL.get(map_name)
        if ft_hint:
            locked_ids = [
                wpid
                for wpid, wdef in WAYPOINT_DEFS.items()
                if wdef["map"] == map_name and wpid not in self.fast_travel_mgr.unlocked
            ]
            if locked_ids:
                self.hud.show_notification(ft_hint, 4.0)

    def _sync_player_weapon(self):
        """Sync player.has_sword based on active hotbar slot having a weapon."""
        if self.player:
            from item_system import ITEM_DEFS

            stack = self.game.inventory.grid.active_item
            if stack:
                idef = ITEM_DEFS.get(stack.item_id, {})
                self.player.has_sword = idef.get("equip_slot") == "weapon"
            else:
                self.player.has_sword = False

    def _boss_body(self):
        """Return boss body collision dict for player movement blocking, or None."""
        if self.boss:
            return self.boss.body_collision()
        return None

    def _blockers_for_enemy(self, enemy):
        blockers = {(npc.x, npc.y) for npc in self.npcs}
        blockers.update((ch.x, ch.y) for ch in self.chests if not ch.opened)
        blockers.update(
            quantize_tile(other.x, other.y)
            for other in self.enemies
            if other is not enemy and not other.is_dead
        )
        if self.boss and self.boss.alive and not self.boss.defeated:
            blockers.add(quantize_tile(self.boss.x, self.boss.y))
        return blockers

    def _blockers_for_boss(self):
        blockers = {(npc.x, npc.y) for npc in self.npcs}
        blockers.update((ch.x, ch.y) for ch in self.chests if not ch.opened)
        blockers.update(
            quantize_tile(enemy.x, enemy.y)
            for enemy in self.enemies
            if not enemy.is_dead
        )
        return blockers

    def _allow_expensive_ai(self, actor) -> bool:
        cam_x, cam_y = self.camera.offset
        sx = int(actor.x * TILE_SIZE) - cam_x
        sy = int(actor.y * TILE_SIZE) - cam_y
        on_screen = (
            -64 <= sx <= self.viewport_width + 64
            and -64 <= sy <= self.viewport_height + 64
        )
        near_player = actor.dist_to(self.player.x, self.player.y) <= getattr(
            actor, "active_radius", 10.0
        )
        return on_screen or near_player

    def _register_dynamic_drop(self, item: GroundItem):
        record = item.to_save_data(self.map_mgr.current_name)
        existing = {entry["id"] for entry in self.dynamic_drop_records}
        if record["id"] not in existing:
            self.dynamic_drop_records.append(record)

    def _remove_dynamic_drop(self, drop_id: str):
        self.dynamic_drop_records = [
            record for record in self.dynamic_drop_records if record["id"] != drop_id
        ]

    def _play_sfx(self, name: str):
        if hasattr(self.game, "audio"):
            self.game.audio.play_sfx(name)

    def _is_stage_path_unlocked(self, target_map: str) -> bool:
        """Allow stage transitions even if a save's world_stage lags behind."""
        campaign = getattr(self.game, "campaign", None)
        world_stage = getattr(campaign, "world_stage", 1) if campaign else 1
        if target_map == "ruins_approach":
            if world_stage >= 2:
                return True
            if campaign and (
                campaign.is_stage_unlocked(2)
                or 1 in getattr(campaign, "completed_stages", set())
                or getattr(campaign, "boss_kills", {}).get("dark_golem")
            ):
                return True
            return False
        if target_map == "sanctum_halls":
            if world_stage >= 3:
                return True
            if campaign and (
                campaign.is_stage_unlocked(3)
                or 2 in getattr(campaign, "completed_stages", set())
                or getattr(campaign, "boss_kills", {}).get("gravewarden")
            ):
                return True
            if self.map_mgr.current_name == "ruins_depths":
                if self.defeated_boss or self.boss_save_state.get("defeated"):
                    return True
                stage2_quest = self.game.quest_manager.get_quest("main_s2")
                if stage2_quest and stage2_quest.complete:
                    return True
            return False
        return True

    def _coin_text(self, amount: int) -> str:
        return f"+{amount} coin" if amount == 1 else f"+{amount} coins"

    def _apply_reward(self, reward: dict, source: str = "pickup") -> bool:
        reward = normalize_reward(reward)
        kind = reward["kind"]

        if kind == REWARD_HEAL:
            old_hp = self.player.hp
            heal_amt = reward["amount"]
            if old_hp >= self.player.max_hp:
                # Convert unneeded heal to coins so it's always collectible
                coins = max(1, heal_amt)
                self.game.wallet.add(coins)
                self.hud.show_notification(self._coin_text(coins))
                return True
            self.player.heal(heal_amt)
            healed = self.player.hp - old_hp
            if healed <= 0:
                coins = max(1, heal_amt)
                self.game.wallet.add(coins)
                self.hud.show_notification(self._coin_text(coins))
                return True
            self.hud.show_notification(f"Recovered {healed} HP")
            return True

        if kind == REWARD_CURRENCY:
            amount = reward["amount"]
            self.game.wallet.add(amount)
            self.hud.show_notification(self._coin_text(amount), 2.0)
            return True

        item_id = reward["item_id"]
        item_name = ITEM_DEFS.get(item_id, {}).get("name", item_id)
        if self.game.inventory.add(item_id):
            if source == "chest":
                message = f"Found: {item_name}!"
            elif source == "npc":
                message = f"Got: {item_name}"
            else:
                message = f"Picked up: {item_name}"
            self.hud.show_notification(message)
            self.game.quest_manager.fire_trigger("pickup_item", item_id)
            # Sync weapon state if player just picked up the sword
            if item_id == "old_sword":
                self._sync_player_weapon()
            return True

        if self.game.inventory.has(item_id):
            self.hud.show_notification("Already carrying that.", 2.0)
        else:
            self.hud.show_notification("Inventory full!", 2.0)
        return False

    def _collect_reward_item(self, item: GroundItem) -> None:
        payload = item.collect()
        if not payload:
            return
        reward = payload["reward"]
        if not self._apply_reward(reward, source="pickup"):
            item.collected = False
            return
        if payload.get("dynamic"):
            self._remove_dynamic_drop(payload["drop_id"])
        else:
            self.collected_items.add(payload["drop_id"])
        self.particles.emit_pickup(
            int((item.x + 0.5) * TILE_SIZE), int((item.y + 0.5) * TILE_SIZE)
        )
        self._play_sfx("pickup")

    def _apply_player_damage(
        self,
        amount: int,
        source_x=None,
        source_y=None,
        *,
        shake: tuple[int, float] | None = None,
        sfx: str | None = None,
    ) -> bool:
        if self.flow_state != "normal":
            return False
        took_damage = self.player.take_damage(amount, source_x, source_y)
        if not took_damage:
            return False
        self.post_process.trigger_hit_flash(
            (255, 210, 210) if sfx == "hurt" else (255, 240, 220),
            0.42 if sfx == "boss_slam" else 0.32,
        )
        if shake:
            self.shake.trigger(shake[0], shake[1])
        if sfx:
            self._play_sfx(sfx)
        if not self.player.is_alive:
            self._trigger_player_death()
            return True
        return False

    def _spawn_enemy_drop(self, enemy, drop_def):
        reward = normalize_reward(drop_def)
        # Only skip unstackable (stack_max=1) key items the player already holds.
        # Stackable consumables/materials (raw_meat etc.) must always be allowed to drop.
        if reward["kind"] == REWARD_KEY_ITEM:
            item_id = reward.get("item_id", "")
            idef = ITEM_DEFS.get(item_id, {})
            if idef.get("stack_max", 1) == 1 and self.game.inventory.has(item_id):
                return
        chance = float(drop_def.get("chance", 0.0))
        if reward["kind"] == REWARD_HEAL:
            chance += float(self._difficulty().get("drop_heal_chance_bonus", 0.0))
        elif reward["kind"] != REWARD_CURRENCY:
            chance += float(self._difficulty().get("drop_item_chance_bonus", 0.0))
        chance = max(0.0, min(1.0, chance))
        if random.random() >= chance:
            return
        # Ensure drop is on the current map and at the enemy's position
        current_map = self.map_mgr.current_name
        if self.map_mgr.transitioning:
            return  # Do not spawn drops during map transition
        dx, dy = _nearest_passable(int(enemy.x), int(enemy.y), self.tilemap)
        reward_id = reward.get("item_id", reward.get("label", reward["kind"]))
        drop_id = f"{enemy.spawn_id}_{drop_def.get('drop_id', reward_id)}"
        item = GroundItem(dx, dy, drop_id=drop_id, dynamic=True, reward=reward)
        self.ground_items.append(item)
        self._register_dynamic_drop(item)

    def update(self, dt):
        inp = self.game.input
        self.debug_toggles.update_from_input(inp)
        self.hud.update(dt)
        self.particles.update(dt)
        self.dmg_numbers.update(dt)
        self.shake.update(dt)
        self.post_process.update(dt)

        if self.map_mgr.transitioning:
            swap = self.map_mgr.update(dt)
            if swap:
                self._load_map(
                    swap["map"],
                    swap["spawn"],
                    capture_checkpoint=True,
                    grant_transition_heal=True,
                )
            return

        if self.player and (self.player.hp <= 0 or not self.player.is_alive):
            self._trigger_player_death()
        if self._update_death_sequence(dt):
            return

        if self.dialogue.active:
            if not self.dialogue.update(dt, inp):
                self._process_pending_actions()
            return

        if inp.is_pressed("start"):
            self.game.states.change("pause")
            return
        if inp.is_pressed("select"):
            self.game.states.change("inventory")
            return
        if inp.is_pressed("skill"):
            self.game.states.change("skill_screen")
            return
        if inp.is_pressed("travel"):
            self._try_fast_travel()
            return
        if inp.is_pressed("craft"):
            self._try_craft()
            return

        # Numeric hotbar slot switching (keys 1-8)
        for slot_idx in range(8):
            key_name = f"hotbar{slot_idx + 1}"
            if inp.is_pressed(key_name):
                self.game.inventory.grid.active_hotbar = slot_idx
                self._sync_player_weapon()
                break

        # Dash (requires Shadow Cloak in equipment)
        if inp.is_pressed("dash") and self._dash_cooldown <= 0:
            effects = self.game.inventory.equipped_effects
            if "enable_dash" in effects:
                self._start_dash()

        if inp.is_pressed("b"):
            if self.player.can_attack:
                wdef = self._get_weapon_def()
                self.player._using_bow = "ranged_bow" in wdef.get("effect", "")
                self.player.start_attack()
                if hasattr(self.game, "audio"):
                    self.game.audio.play_sfx("sword")
                    self.game.audio.notify_combat_start()
            elif not self.player.has_sword:
                self.hud.show_notification("No weapon equipped.", 1.5)
        if inp.is_pressed("a"):
            ix, iy = self.player.get_interact_tile()
            if not self._handle_interaction(ix, iy):
                self._try_use_active_consumable()

        self._aura_timer += dt
        self.player.update(
            dt, inp, self.tilemap, self.npcs, boss_body=self._boss_body()
        )
        player_tile = quantize_tile(self.player.x, self.player.y)
        field_radius = max(self.tilemap.width, self.tilemap.height)
        player_field = self.influence_cache.get_player_field(
            self.map_mgr.current_name, self.tilemap, player_tile, field_radius
        )

        if self.player.is_attacking and self.player.state_timer < 0.02:
            knock_x = {"left": -1, "right": 1, "up": 0, "down": 0}[self.player.facing]
            knock_y = {"left": 0, "right": 0, "up": -1, "down": 1}[self.player.facing]
            attack_damage = self._player_attack_damage()

            # Determine reach — ranged weapons use weapon range if ammo available
            wdef = self._get_weapon_def()
            weapon_range = wdef.get("stats", {}).get("attack_range", 0)
            is_bow = "ranged_bow" in wdef.get("effect", "")
            reach = PLAYER_ATTACK_RANGE
            if is_bow and weapon_range > 0:
                if self.game.inventory.craft_bag.has("bone_arrow"):
                    self.game.inventory.craft_bag.remove_item("bone_arrow", 1)
                    reach = weapon_range
                    self._play_sfx("sword")  # arrow release sound
                else:
                    self.hud.show_notification("No bone arrows!", 1.5)
                    reach = 0.8
                    attack_damage = 1
            elif weapon_range > 0:
                reach = max(reach, weapon_range)

            cx, cy, radius = get_attack_hitbox(
                self.player.x, self.player.y, self.player.facing, reach
            )
            for enemy in self.enemies:
                if enemy.is_dead:
                    continue
                if circle_hits_entity(
                    cx, cy, radius, enemy.x, enemy.y, enemy.size
                ) and attack_has_los(
                    self.player.x, self.player.y, enemy.x, enemy.y, self.tilemap
                ):
                    # Flanking bonus
                    dmg = attack_damage
                    flank = self._is_flanking(enemy)
                    if flank:
                        flank_bonus = FLANK_DAMAGE_BONUS
                        prog = getattr(self.game, "progression", None)
                        if prog:
                            flank_bonus += prog.get_combat_stats().get(
                                "flank_bonus", 0.0
                            )
                        dmg = int(dmg * (1 + flank_bonus))
                    # Bestiary knowledge bonus (+20% damage if fully researched)
                    if (
                        hasattr(self.game, "bestiary")
                        and getattr(enemy, "enemy_type", None)
                        and self.game.bestiary.is_fully_unlocked(enemy.enemy_type)
                    ):
                        dmg = int(dmg * 1.2)
                    # Crit from skill tree
                    prog_stats = getattr(self.game, "progression", None)
                    if prog_stats:
                        import random as _rng

                        crit_chance = prog_stats.get_combat_stats().get(
                            "crit_chance", 0.0
                        )
                        if crit_chance > 0 and _rng.random() < crit_chance:
                            crit_mult = prog_stats.get_combat_stats().get(
                                "crit_mult", 1.5
                            )
                            dmg = int(dmg * crit_mult)
                    enemy.take_damage(dmg, knock_x, knock_y)
                    wx = int((enemy.x + 0.5) * TILE_SIZE)
                    wy = int((enemy.y + 0.3) * TILE_SIZE)
                    self.particles.emit_blood(wx, wy, self.player.facing)
                    self.dmg_numbers.spawn(
                        wx, wy - 8, dmg, (255, 220, 60) if flank else (255, 100, 100)
                    )
                    self.shake.trigger(3, 0.1)
                    if hasattr(self.game, "audio"):
                        self.game.audio.play_sfx("hit")
                        self.game.audio.notify_combat_hit()
            if self.boss and self.boss.active and self.boss.alive:
                if circle_hits_entity(
                    cx, cy, radius, self.boss.x, self.boss.y, 1.2
                ) and attack_has_los(
                    self.player.x, self.player.y, self.boss.x, self.boss.y, self.tilemap
                ):
                    boss_dmg = attack_damage
                    if hasattr(
                        self.game, "bestiary"
                    ) and self.game.bestiary.is_fully_unlocked(
                        self._current_boss_id or "dark_golem"
                    ):
                        boss_dmg = int(boss_dmg * 1.2)
                    self.boss.take_damage(boss_dmg, knock_x, knock_y)
                    wx = int((self.boss.x + 0.5) * TILE_SIZE)
                    wy = int((self.boss.y + 0.3) * TILE_SIZE)
                    self.particles.emit_hit(wx, wy, 8)
                    self.dmg_numbers.spawn(wx, wy - 10, boss_dmg, (255, 220, 80))
                    self.shake.trigger(5, 0.15)
                    if hasattr(self.game, "audio"):
                        self.game.audio.play_sfx("boss_hit")
                    self.boss_save_state = self.boss.snapshot_state()
                    if self.boss.defeated:
                        self.particles.emit_death(wx, wy, (200, 100, 50), 20)
                        self.defeated_boss = True
                        boss_defeat_msgs = {
                            "dark_golem": "The Dark Golem is defeated!",
                            "gravewarden": "The Gravewarden is finally slain!",
                            "mythic_sovereign": "The Mythic Sovereign falls!",
                        }
                        from bestiary import ENTRY_DEFS as _BOSS_BESTIARY2

                        _bname = _BOSS_BESTIARY2.get(
                            self._current_boss_id or "dark_golem", {}
                        ).get("name")
                        if _bname:
                            boss_defeat_msgs = {
                                self._current_boss_id
                                or "dark_golem": f"{_bname} is defeated!"
                            }
                        self.hud.show_notification(
                            boss_defeat_msgs.get(
                                self._current_boss_id, "Boss defeated!"
                            ),
                            5.0,
                        )
                        advanced_quests = self.game.quest_manager.fire_trigger(
                            "boss_defeated", self._current_boss_id or "golem"
                        )
                        self._unlock_waypoints_for_quests(advanced_quests)
                        if hasattr(self.game, "audio"):
                            self.game.audio.notify_boss_defeated()
                            self.game.audio.play_sfx("victory")
                        if hasattr(self.game, "bestiary"):
                            self.game.bestiary.on_kill(
                                self._current_boss_id or "dark_golem"
                            )
                        _stage = getattr(
                            getattr(self.game, "campaign", None), "world_stage", 1
                        )
                        _xp = get_stage_boss_xp(
                            _stage, self._current_boss_id or "dark_golem", default=100
                        )
                        self._grant_xp(
                            _xp, wx, wy, self._current_boss_id or "dark_golem"
                        )
                        # Grant boss loot drops
                        self._grant_boss_loot(self.boss)

            # ── Player attacks animals ────────────────────────────────
            for animal in self.animal_spawner.animals:
                if animal.is_dead:
                    continue
                if circle_hits_entity(
                    cx, cy, radius, animal.x, animal.y, animal.size
                ) and attack_has_los(
                    self.player.x, self.player.y, animal.x, animal.y, self.tilemap
                ):
                    anim_dmg = attack_damage
                    if (
                        hasattr(self.game, "bestiary")
                        and getattr(animal, "enemy_type", None)
                        and self.game.bestiary.is_fully_unlocked(animal.enemy_type)
                    ):
                        anim_dmg = int(anim_dmg * 1.2)
                    animal.take_damage(anim_dmg, knock_x, knock_y)
                    wx = int((animal.x + 0.5) * TILE_SIZE)
                    wy = int((animal.y + 0.3) * TILE_SIZE)
                    self.particles.emit_blood(wx, wy, self.player.facing)
                    self.dmg_numbers.spawn(wx, wy - 8, anim_dmg, (255, 100, 100))
                    self.shake.trigger(2, 0.08)
                    if hasattr(self.game, "audio"):
                        self.game.audio.play_sfx("hit")
                    if hasattr(self.game, "bestiary"):
                        self.game.bestiary.on_encounter(animal.enemy_type)

        for enemy in self.enemies:
            if enemy.should_remove:
                continue
            enemy.update(
                dt,
                self.player.x,
                self.player.y,
                self.tilemap,
                map_name=self.map_mgr.current_name,
                dynamic_blockers=self._blockers_for_enemy(enemy),
                player_field=player_field,
                allow_expensive_ai=self._allow_expensive_ai(enemy),
            )
            if not enemy.is_dead and enemy.state == "attack" and enemy.has_attacked:
                if (
                    enemy.dist_to(self.player.x, self.player.y)
                    < enemy.attack_range * 1.2
                ):
                    if self._apply_player_damage(
                        self._incoming_damage(enemy.damage),
                        enemy.x,
                        enemy.y,
                        shake=(4, 0.12),
                        sfx="hurt",
                    ):
                        enemy.has_attacked = False
                        return
                enemy.has_attacked = False
            if enemy.is_dead and not enemy.loot_spawned and enemy.death_timer <= 0.45:
                wx = int((enemy.x + 0.5) * TILE_SIZE)
                wy = int((enemy.y + 0.5) * TILE_SIZE)
                self.particles.emit_death(wx, wy, enemy.color)
                if hasattr(self.game, "audio"):
                    self.game.audio.play_sfx("enemy_death")
                self.defeated_enemy_ids.add(enemy.spawn_id)
                for drop_def in enemy.drops:
                    self._spawn_enemy_drop(enemy, drop_def)
                enemy.loot_spawned = True
                # XP + bestiary
                xp = getattr(enemy, "xp_reward", 10)
                self._grant_xp(xp, wx, wy, enemy.enemy_type)
                if hasattr(self.game, "bestiary"):
                    self.game.bestiary.on_kill(enemy.enemy_type)
        self.enemies = [enemy for enemy in self.enemies if not enemy.should_remove]

        if self.boss:
            if not self.boss_triggered and not self.boss.defeated:
                if self.boss.dist_to(self.player.x, self.player.y) < 5.0:
                    self.boss.activate()
                    self.boss_triggered = True
                    boss_wake_msgs = {
                        "dark_golem": "The Dark Golem awakens!",
                        "gravewarden": "The Gravewarden rises from the dead!",
                        "mythic_sovereign": "The Mythic Sovereign descends!",
                    }
                    from bestiary import ENTRY_DEFS as _BOSS_BESTIARY

                    boss_name = _BOSS_BESTIARY.get(self._current_boss_id, {}).get(
                        "name"
                    )
                    if boss_name:
                        boss_wake_msgs = {
                            self._current_boss_id: f"{boss_name} approaches!"
                        }
                    self.hud.show_notification(
                        boss_wake_msgs.get(self._current_boss_id, "A boss appears!"),
                        3.0,
                    )
                    if hasattr(self.game, "audio"):
                        self.game.audio.notify_boss_active()
                    if hasattr(self.game, "bestiary"):
                        self.game.bestiary.on_encounter(
                            self._current_boss_id or "dark_golem"
                        )
            if self.boss.active and not self.boss.defeated:
                self.boss.update(
                    dt,
                    self.player.x,
                    self.player.y,
                    self.tilemap,
                    map_name=self.map_mgr.current_name,
                    dynamic_blockers=self._blockers_for_boss(),
                    player_field=player_field,
                    allow_expensive_ai=True,
                )
                self.boss_save_state = self.boss.snapshot_state()
                dist = self.boss.dist_to(self.player.x, self.player.y)
                if (
                    self.boss.state == "slam"
                    and self.boss.state_timer < 0.3
                    and dist < self.boss.slam_radius
                ):
                    if self._apply_player_damage(
                        self._incoming_damage(self.boss.damage),
                        self.boss.x,
                        self.boss.y,
                        shake=(6, 0.2),
                        sfx="boss_slam",
                    ):
                        return
                elif (
                    self.boss.state in ("spin", "bone_spin")
                    and dist < self.boss.spin_radius
                ):
                    if self._apply_player_damage(
                        self._incoming_damage(self.boss.damage),
                        self.boss.x,
                        self.boss.y,
                        shake=(4, 0.12),
                        sfx="hurt",
                    ):
                        return
                elif (
                    self.boss.state == "charge"
                    and self.boss.state_timer > self.boss.charge_telegraph
                    and dist < self.boss.charge_radius
                ):
                    if self._apply_player_damage(
                        self._incoming_damage(self.boss.damage),
                        self.boss.x,
                        self.boss.y,
                        shake=(5, 0.15),
                        sfx="hurt",
                    ):
                        return
                elif self.boss.state == "void_wave" and dist < getattr(
                    self.boss, "void_wave_radius", 99
                ):
                    if self._apply_player_damage(
                        self._incoming_damage(self.boss.damage),
                        self.boss.x,
                        self.boss.y,
                        shake=(5, 0.18),
                        sfx="boss_slam",
                    ):
                        return
                elif (
                    self.boss.state == "crystal_barrage"
                    and self.boss.state_timer < 0.3
                    and dist < getattr(self.boss, "crystal_barrage_radius", 99)
                ):
                    if self._apply_player_damage(
                        self._incoming_damage(self.boss.damage),
                        self.boss.x,
                        self.boss.y,
                        shake=(6, 0.2),
                        sfx="boss_slam",
                    ):
                        return
                elif (
                    self.boss.state == "rift"
                    and self.boss.state_timer < 0.4
                    and dist < getattr(self.boss, "rift_radius", 99)
                ):
                    if self._apply_player_damage(
                        self._incoming_damage(self.boss.damage + 1),
                        self.boss.x,
                        self.boss.y,
                        shake=(8, 0.25),
                        sfx="boss_slam",
                    ):
                        return
            if self.boss and self.boss.defeated:
                self._boss_defeat_timer += dt
                if self._boss_defeat_timer > 2.0:
                    self._handle_boss_defeat_routing()
                    return

        ptx, pty = quantize_tile(self.player.x, self.player.y)
        for ground_item in self.ground_items:
            if ground_item.occupies(ptx, pty):
                self._collect_reward_item(ground_item)

        exit_info = self.map_mgr.check_exit(self.player.x, self.player.y)
        if exit_info:
            target_map = exit_info["map"]
            campaign = getattr(self.game, "campaign", None)

            def _push_back():
                self.player.x -= {"left": -0.2, "right": 0.2, "up": 0, "down": 0}.get(
                    self.player.facing, 0
                )
                self.player.y -= {"left": 0, "right": 0, "up": -0.2, "down": 0.2}.get(
                    self.player.facing, 0
                )

            if target_map == "dungeon" and not self.game.inventory.has("forest_key"):
                self.hud.show_notification(
                    "The gate is locked. You need the Forest Key.", 2.0
                )
                _push_back()
                return

            # Inter-stage fallback paths are gated behind stage completion
            if target_map == "ruins_approach" and not self._is_stage_path_unlocked(
                target_map
            ):
                self.hud.show_notification(
                    "Defeat the Dark Golem to open this path.", 2.5
                )
                _push_back()
                return
            if target_map == "sanctum_halls" and not self._is_stage_path_unlocked(
                target_map
            ):
                self.hud.show_notification(
                    "Defeat the Gravewarden to open this path.", 2.5
                )
                _push_back()
                return

            self.map_mgr.start_transition(exit_info["map"], exit_info["spawn"])
            return

        self.camera.follow(self.player.x, self.player.y)

        # ── v4 system updates ──────────────────────────────────────────
        self.weather.update(dt)
        animal_attackers = self.animal_spawner.update(
            dt, self.player.x, self.player.y, self.tilemap
        )
        for attacker in animal_attackers:
            dmg = getattr(attacker, "damage", 1)
            self._apply_player_damage(
                self._incoming_damage(dmg),
                attacker.x,
                attacker.y,
                shake=(3, 0.1),
                sfx="animal_hurt",
            )

        # ── Animal death processing (XP, drops, bestiary) ─────────
        for animal in self.animal_spawner.animals:
            if (
                animal.is_dead
                and not animal.loot_spawned
                and animal.death_timer <= 0.45
            ):
                wx = int((animal.x + 0.5) * TILE_SIZE)
                wy = int((animal.y + 0.5) * TILE_SIZE)
                self.particles.emit_death(wx, wy, animal.color)
                if hasattr(self.game, "audio"):
                    self.game.audio.play_sfx("enemy_death")
                # Track kill for persistence
                self.animal_spawner.on_animal_killed(animal.spawn_id)
                # Drops: convert animal drop format (item_id/qty/chance)
                # to reward format (kind/item_id/amount/chance) for _spawn_enemy_drop
                for drop_idx, raw_drop in enumerate(animal.drops):
                    drop_def = {
                        "kind": "key_item",
                        "item_id": raw_drop["item_id"],
                        "chance": raw_drop.get("chance", 1.0),
                        # Unique drop_id per entry so same-item drops don't collide
                        "drop_id": f"d{drop_idx}_{raw_drop['item_id']}",
                    }
                    for _q in range(raw_drop.get("qty", 1)):
                        self._spawn_enemy_drop(animal, drop_def)
                animal.loot_spawned = True
                # XP + bestiary
                xp = animal.xp_reward
                self._grant_xp(xp, wx, wy, animal.enemy_type)
                if hasattr(self.game, "bestiary"):
                    self.game.bestiary.on_kill(animal.enemy_type)
                # Reputation penalty for killing passive animals
                if animal.behavior in ("flee", "passive") and hasattr(
                    self.game, "reputation"
                ):
                    self.game.reputation.modify("forest_spirits", -2)
        # Environmental objects: pass entity positions
        env_entities = [(self.player.x, self.player.y, False)]
        env_dmg_events = self.env_manager.update(dt, env_entities)
        for evt in env_dmg_events:
            if evt.get("entity_idx", -1) == 0:
                self._apply_player_damage(
                    self._incoming_damage(evt["damage"]), sfx="ice_hit"
                )
        # Spawn env drops into world
        for drop in self.env_manager.collect_pending_drops():
            from interactable import GroundItem as GI
            from rewards import make_key_item_reward as mkr

            gi = GI(
                drop["tile_x"],
                drop["tile_y"],
                drop_id=f"env_{drop['tile_x']}_{drop['tile_y']}",
                dynamic=True,
                reward=mkr(drop["item_id"]),
            )
            self.ground_items.append(gi)
        self.fast_travel_mgr.update(dt)
        newly_unlocked = self.fast_travel_mgr.check_proximity(
            self.player.x, self.player.y, self.map_mgr.current_name
        )
        for wp_name in newly_unlocked:
            self.hud.show_notification(f"Waypoint unlocked: {wp_name}", 3.0)
        if hasattr(self.game, "audio"):
            self.game.audio.update(dt)

        # Dash timer
        self._dash_cooldown = max(0.0, self._dash_cooldown - dt)
        if self._dash_active:
            self._dash_timer -= dt
            speed = getattr(self.player, "dash_speed", DASH_SPEED)
            nx = self.player.x + self._dash_vx * speed * dt
            ny = self.player.y + self._dash_vy * speed * dt
            if self.tilemap.is_passable(nx, ny):
                self.player.x = nx
                self.player.y = ny
            if self._dash_timer <= 0:
                self._dash_active = False

        combat_active = (
            self.boss is not None and self.boss.active and not self.boss.defeated
        ) or any(
            not enemy.is_dead and enemy.dist_to(self.player.x, self.player.y) <= 6.0
            for enemy in self.enemies
        )
        self.post_process.add_combat_vignette(combat_active)

    def _handle_boss_defeat_routing(self) -> None:
        """
        After a boss is defeated, decide what happens next:
          - Stage 1 boss (dark_golem)       → unlock Stage 2 → stage_intro (Act II)
          - Stage 2 boss (gravewarden)       → unlock Stage 3 → stage_intro (Act III)
          - Stage 3 boss (mythic_sovereign)  → true final victory screen
        """
        campaign = getattr(self.game, "campaign", None)
        boss_id = self._current_boss_id or "dark_golem"

        completed_stage = None
        if campaign is not None:
            completed_stage = campaign.on_boss_killed(boss_id)

        rep = getattr(self.game, "reputation", None)
        if rep:
            deltas = rep.apply_event("boss_killed")
            for faction, delta in deltas.items():
                label = "+" if delta >= 0 else ""
                self.hud.show_notification(
                    f"{faction.title()}: {label}{delta} rep", 3.0
                )

        # Force-complete the quest for the stage that just ended (handles stuck quests)
        quest_keys = {1: "main", 2: "main_s2", 3: "main_s3"}
        if completed_stage is not None:
            qkey = quest_keys.get(completed_stage)
            if qkey:
                q = self.game.quest_manager.get_quest(qkey)
                if q and not q.complete:
                    while not q.complete:
                        q.advance()
            rep = getattr(self.game, "reputation", None)
            if rep:
                rep.apply_event("quest_main_complete")

        if completed_stage is None:
            # Boss was already defeated or not a stage boss — ignore
            self.hud.show_notification("You have already conquered this foe.", 3.0)
            return

        if completed_stage < 3:
            next_stage = completed_stage + 1
            hp_gain = self._sync_player_max_hp(heal_for_growth=True)
            if hp_gain > 0:
                self.hud.show_notification(
                    f"Max HP increased by {hp_gain} for {campaign.get_stage_name(next_stage) if campaign else f'Act {next_stage}'}!",
                    3.0,
                )

        # Save progress after all stage rewards and campaign changes are applied.
        self.game.save_current_game()

        if completed_stage >= 3:
            # Final stage — true victory
            victory = self.game.states._states.get("victory")
            if victory and hasattr(victory, "prepare"):
                victory.prepare(3)
            self.game.states.change("victory")
        else:
            self._transition_to_next_stage(next_stage)

    def _transition_to_next_stage(self, next_stage: int) -> None:
        """Move into the next act without ever falling through to final victory."""
        campaign = getattr(self.game, "campaign", None)
        intro = self.game.states._states.get("stage_intro")
        if intro and hasattr(intro, "prepare"):
            stage_name = (
                campaign.get_stage_name(next_stage) if campaign else f"Act {next_stage}"
            )
            intro.prepare(next_stage, stage_name)
            self.game.states.change("stage_intro")
            return

        # Safety fallback: if stage_intro is unavailable, jump straight into the
        # next act's entry map rather than showing the final victory state.
        entry_map = campaign.get_entry_map(next_stage) if campaign else "village"
        self.defeated_boss = False
        self.boss_save_state = {}
        self._boss_defeat_timer = 0.0
        self._load_map(entry_map, capture_checkpoint=True, grant_transition_heal=True)
        self._sync_player_weapon()
        self._init_player_forms()
        self.game.states.change("gameplay")

    def _grant_boss_loot(self, boss) -> None:
        """
        Drop guaranteed boss loot items into the world near the boss position.
        Uses the boss_loot table from stage_configs.json.
        """
        import random

        loot_table = get_stage_boss_loot(self._current_boss_id)

        for drop in loot_table:
            if random.random() > drop.get("chance", 1.0):
                continue
            item_id = drop.get("item_id")
            if not item_id:
                continue
            idef = ITEM_DEFS.get(item_id, {})
            if idef.get("stack_max", 1) == 1 and self.game.inventory.has(item_id):
                continue  # already have unique item
            from rewards import make_key_item_reward

            reward = make_key_item_reward(item_id, label=idef.get("name", item_id))
            dx, dy = _nearest_passable(int(boss.x), int(boss.y), self.tilemap)
            drop_item = GroundItem(
                dx + len(loot_table) % 2,
                dy,
                drop_id=f"boss_drop_{self._current_boss_id}_{item_id}",
                dynamic=True,
                reward=reward,
            )
            self.ground_items.append(drop_item)
            self._register_dynamic_drop(drop_item)

    def _start_dash(self):
        dx = {"left": -1, "right": 1, "up": 0, "down": 0}.get(self.player.facing, 0)
        dy = {"left": 0, "right": 0, "up": -1, "down": 1}.get(self.player.facing, 0)
        self._dash_vx = float(dx)
        self._dash_vy = float(dy)
        self._dash_active = True
        self._dash_timer = DASH_DURATION
        self._dash_cooldown = DASH_COOLDOWN
        self.particles.emit_dust(
            int(self.player.x * TILE_SIZE), int(self.player.y * TILE_SIZE)
        )
        self._play_sfx("fast_travel")

    def _try_craft(self):
        """Press C to cycle through and auto-craft available recipes."""
        cm = self.crafting_manager
        inv = self.game.inventory
        # Gather all recipes player has ingredients for (ignore station requirement)
        available = [
            rid
            for rid in cm.recipes
            if cm.can_craft(rid, inv.grid, inv.craft_bag, ignore_station=True)
        ]
        if not available:
            self.hud.show_notification("No craftable recipes (missing materials).", 2.0)
            return
        idx = getattr(self, "_craft_cycle", 0) % len(available)
        rid = available[idx]
        result = cm.craft(rid, inv.grid, inv.craft_bag, ignore_station=True)
        if result:
            from item_system import ITEM_DEFS

            name = ITEM_DEFS.get(result["item_id"], {}).get("name", result["item_id"])
            self.hud.show_notification(f"Crafted: {name}!", 3.0)
            self._play_sfx("craft")
        self._craft_cycle = idx + 1

    def _unlock_waypoints_for_quests(self, advanced_quest_ids: list):
        """After quests advance, unlock any qualifying waypoints."""
        ftm = getattr(self, "fast_travel_mgr", None) or getattr(
            self.game, "fast_travel_mgr", None
        )
        if not ftm:
            return
        for qid in advanced_quest_ids:
            quest = self.game.quest_manager.get_quest(qid)
            if quest:
                ftm.unlock_by_quest_stage(qid, quest.stage)

    def _try_fast_travel(self):
        """Travel to the nearest unlocked waypoint on the current map, or show list."""
        current_map = self.map_mgr.current_name
        waypoints = self.fast_travel_mgr.get_unlocked_for_map(current_map)
        if not waypoints:
            # Try other maps — pick first globally unlocked waypoint
            waypoints = self.fast_travel_mgr.get_unlocked_all()
        if not waypoints:
            self.hud.show_notification("No waypoints unlocked yet.", 2.0)
            return
        # Find nearest to player
        best = min(
            waypoints,
            key=lambda w: point_distance(
                self.player.x, self.player.y, w["tile_x"], w["tile_y"]
            ),
        )
        dest = self.fast_travel_mgr.travel_to(best["id"])
        if dest:
            self.hud.show_notification(f"Travelling to {dest['name']}...", 2.0)
            self._play_sfx("fast_travel")
            self.map_mgr.start_transition(dest["map"], dest["spawn"])

    def _is_flanking(self, enemy) -> bool:
        """Return True if player is attacking from behind (> FLANK_ANGLE_THRESHOLD degrees)."""
        ex = enemy.x - self.player.x
        ey = enemy.y - self.player.y
        attack_dir = {
            "right": (1, 0),
            "left": (-1, 0),
            "down": (0, 1),
            "up": (0, -1),
        }.get(self.player.facing, (0, 1))
        angle_deg = angle_between_vectors_deg(ex, ey, attack_dir[0], attack_dir[1])
        return angle_deg > FLANK_ANGLE_THRESHOLD

    def _grant_xp(
        self,
        amount: int,
        wx: int,
        wy: int,
        enemy_type: str = "",
        is_env_kill: bool = False,
    ):
        """Award XP to progression, show level-up if threshold crossed."""
        prog = getattr(self.game, "progression", None)
        if prog is None:
            return
        combat_stats = prog.get_combat_stats()
        mult = combat_stats.get("xp_bonus_mult", 1.0)
        if is_env_kill:
            amount += combat_stats.get("env_kill_bonus", 0)
        amount = max(1, int(round(amount * mult)))
        leveled = prog.add_xp(amount)
        if leveled:
            self.hud.show_notification(f"Level Up! LV {prog.level}", 3.0)
            self.particles.emit_levelup(wx, wy)
            self._play_sfx("levelup")

    def _try_use_active_consumable(self):
        """Use the consumable in the active hotbar slot. raw_meat requires 4 per HP."""
        stack = self.game.inventory.grid.active_item
        if not stack:
            return
        idef = ITEM_DEFS.get(stack.item_id, {})
        if idef.get("category") != "consumable":
            return
        use_effect = idef.get("use_effect", "")
        if not use_effect:
            return

        # Determine cost and heal amount per press of Z
        # raw_meat:       2 pieces → ½ heart    (need 4 for 1 full heart)
        # cooked_meat:    1 piece  → ½ heart    (need 2 for 1 full heart)
        # health_potion:  1 bottle → 1 heart
        if stack.item_id == "raw_meat":
            cost, heal_amount = 2, 0.5
            min_needed = cost
        elif stack.item_id == "cooked_meat":
            cost, heal_amount = 1, 0.5
            min_needed = cost
        elif use_effect == "heal_2" or use_effect == "heal_1":
            # health_potion and any other heal → 1 full heart per use
            cost, heal_amount = 1, 1
            min_needed = cost
        elif use_effect == "heal_3":
            cost, heal_amount = 1, 1
            min_needed = cost
        elif use_effect == "grant_skill_point":
            prog = getattr(self.game, "progression", None)
            if prog:
                prog.grant_skill_point()
                self.hud.show_notification("Gained a Skill Point!", 3.0)
                self.game.inventory.grid.remove_item(stack.item_id, 1)
                self._play_sfx("levelup")
            return
        else:
            return

        at_full = self.player.hp >= self.player.max_hp
        if at_full:
            self.hud.show_notification("Already at full health.", 1.5)
            return

        total = self.game.inventory.grid.count(stack.item_id)
        if total < min_needed:
            if stack.item_id == "raw_meat":
                self.hud.show_notification(
                    f"Need {min_needed} raw meat to eat ({total} in bag).", 2.0
                )
            else:
                self.hud.show_notification(
                    f"Not enough {idef.get('name', stack.item_id)}.", 1.5
                )
            return

        self.game.inventory.grid.remove_item(stack.item_id, cost)
        old_hp = self.player.hp
        old_partial = getattr(self.player, "partial_hp", 0.0)
        self.player.heal(heal_amount)
        item_name = idef.get("name", stack.item_id)
        if heal_amount < 1.0:
            self.hud.show_notification(f"Ate {item_name}! +½ heart", 2.0)
        else:
            gained = self.player.hp - old_hp
            self.hud.show_notification(f"Used {item_name}! +{gained} HP", 2.0)
        self._play_sfx("pickup")

    def _current_quest(self):
        """Return the quest appropriate for the current campaign stage."""
        campaign = getattr(self.game, "campaign", None)
        stage = getattr(campaign, "world_stage", 1)
        quest_map = {1: "main", 2: "main_s2", 3: "main_s3"}
        quest_id = quest_map.get(stage, "main")
        quest = self.game.quest_manager.get_quest(quest_id)
        if quest:
            return quest
        return self.game.quest_manager.get_quest("main")

    def _handle_interaction(self, ix, iy) -> bool:
        quest = self._current_quest()
        quest_stage = quest.stage if quest else 0
        quest_complete = quest.complete if quest else False

        for npc in self.npcs:
            if not npc.occupies(ix, iy):
                continue
            self.dialogue.open(npc.name, npc.get_dialogue(quest_stage, quest_complete))
            for give_item in npc.gives_items:
                if give_item["quest_stage"] == quest_stage:
                    if self._pending_give_item is None:
                        self._pending_give_item = give_item["item_id"]
                    else:
                        self._pending_give_extras.append(give_item["item_id"])
            if (
                npc.takes_item
                and npc.takes_item["quest_stage"] == quest_stage
                and self.game.inventory.has(npc.takes_item["item_id"])
            ):
                self._pending_take_item = npc.takes_item["item_id"]
            self._pending_npc_trigger = npc.npc_id
            return True

        for chest in self.chests:
            if not chest.occupies(ix, iy):
                continue
            reward = chest.open()
            if reward:
                if self._apply_reward(reward, source="chest"):
                    normalized = normalize_reward(reward)
                    if normalized["kind"] == REWARD_KEY_ITEM:
                        name = ITEM_DEFS.get(normalized["item_id"], {}).get(
                            "name", normalized["item_id"]
                        )
                        self.dialogue.open(chest.label, [f"Found: {name}!"])
                    elif normalized["kind"] == REWARD_CURRENCY:
                        self.dialogue.open(
                            chest.label, [self._coin_text(normalized["amount"])]
                        )
                    else:
                        self.dialogue.open(
                            chest.label, [f"Recovered {normalized['amount']} HP"]
                        )
                    self.opened_chests.add(chest.chest_id)
                    self._play_sfx("chest")
                else:
                    normalized = normalize_reward(reward)
                    if normalized[
                        "kind"
                    ] == REWARD_KEY_ITEM and self.game.inventory.has(
                        normalized["item_id"]
                    ):
                        self.dialogue.open(chest.label, ["You already have that item."])
                    elif normalized["kind"] == REWARD_KEY_ITEM:
                        self.dialogue.open(chest.label, ["Inventory full!"])
                    else:
                        self.dialogue.open(chest.label, ["Nothing happens."])
                    chest.opened = False
            return True

        sign_text = self.current_signs.get((ix, iy))
        if sign_text:
            pages = [line for line in str(sign_text).split("\n") if line.strip()]
            self.dialogue.open("Sign", pages or ["..."])
            return True

        return False

    def _process_pending_actions(self):
        if self._pending_take_item:
            item_id = self._pending_take_item
            if self.game.inventory.has(item_id):
                self.game.inventory.remove(item_id)
                self.hud.show_notification(
                    f"Gave: {ITEM_DEFS.get(item_id, {}).get('name', item_id)}"
                )
            self._pending_take_item = None

        if self._pending_give_item:
            item_id = self._pending_give_item
            if self._apply_reward(make_key_item_reward(item_id), source="npc"):
                self._play_sfx("pickup")
            self._pending_give_item = None

        for extra_id in self._pending_give_extras:
            if self._apply_reward(make_key_item_reward(extra_id), source="npc"):
                self._play_sfx("pickup")
        self._pending_give_extras = []

        if self._pending_npc_trigger:
            advanced = self.game.quest_manager.fire_trigger(
                "talk_npc", self._pending_npc_trigger
            )
            if advanced:
                quest = self.game.quest_manager.get_quest("main")
                if quest and quest.complete:
                    self.hud.show_notification("Quest Complete!", 5.0)
                else:
                    self.hud.show_notification("New Objective!", 3.0)
                self._play_sfx("quest")
            self._pending_npc_trigger = None

    def render(self, screen):
        shake_x, shake_y = self.shake.get_offset()
        cam_x, cam_y = self.camera.offset
        cam_x -= shake_x
        cam_y -= shake_y

        self.tilemap.render(screen, cam_x, cam_y)
        # Environmental objects
        self.env_manager.render(screen, cam_x, cam_y)
        for ground_item in self.ground_items:
            ground_item.render(screen, cam_x, cam_y)
        for chest in self.chests:
            chest.render(screen, cam_x, cam_y)
        for enemy in self.enemies:
            enemy.render(screen, cam_x, cam_y)
        if self.boss:
            self.boss.render(screen, cam_x, cam_y)
        for npc in self.npcs:
            npc.render(screen, cam_x, cam_y)
        # Animals
        self.animal_spawner.render(screen, cam_x, cam_y)
        # Fast travel markers
        self.fast_travel_mgr.render(screen, self.map_mgr.current_name, cam_x, cam_y)
        # Player form aura (drawn before player so player sprite is on top)
        if self.player_forms and self.player_forms.is_upgraded():
            sx = int(self.player.x * TILE_SIZE) - cam_x
            sy = int(self.player.y * TILE_SIZE) - cam_y
            self.player_forms.render_aura(screen, sx, sy, TILE_SIZE, self._aura_timer)
        self.player.render(
            screen, cam_x, cam_y, equipment=self.game.inventory.equipment
        )
        # Attack trail for upgraded forms
        if (
            self.player_forms
            and self.player.is_attacking
            and self.player_forms.is_upgraded()
        ):
            sx = int(self.player.x * TILE_SIZE) - cam_x
            sy = int(self.player.y * TILE_SIZE) - cam_y
            self.player_forms.render_attack_trail(
                screen, sx, sy, TILE_SIZE, self.player.facing
            )
        self.particles.render(screen, cam_x, cam_y)
        self.dmg_numbers.render(screen, cam_x, cam_y)
        # Dynamic lighting overlay
        equip_effects = self.game.inventory.equipped_effects
        self.lighting.update(0, self.player.x, self.player.y, equip_effects)
        self.lighting.render(screen, cam_x, cam_y)
        # Weather overlay
        self.weather.render(screen)
        # Post-processing (vignette, color grade, hit flash, death fade)
        self.post_process.render(screen)

        render_ai_debug(
            screen,
            cam_x,
            cam_y,
            self.debug_toggles,
            self.enemies,
            self.boss,
            self.influence_cache.last_field,
            self.game.difficulty_mode,
        )

        self.dialogue.render(screen)
        self.map_mgr.render_fade(screen)
        self.hud.render(
            screen,
            self.player,
            self.game.inventory,
            self.game.quest_manager,
            self.map_mgr.current_name,
            difficulty_label=self.game.difficulty_label,
            coins=self.game.wallet.coins,
            progression=getattr(self.game, "progression", None),
            tilemap=self.tilemap,
            camera=self.camera,
            reputation=getattr(self.game, "reputation", None),
            campaign=getattr(self.game, "campaign", None),
        )
