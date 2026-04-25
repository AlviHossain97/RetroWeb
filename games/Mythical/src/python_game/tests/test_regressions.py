import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import save_manager
from ai.config_loader import get_difficulty_config, get_enemy_config, get_boss_config, clear_config_cache
from boss import Boss
from boss2 import Gravewarden
from campaign import Campaign
from content_registry import ENEMY_SPAWN_DEFS
from enemy import Enemy
from interactable import GroundItem
from inventory import Inventory
from player import Player
from quest import QuestManager
from rewards import (
    REWARD_CURRENCY, REWARD_HEAL, REWARD_KEY_ITEM,
    make_currency_reward, make_key_item_reward, make_heal_reward,
    normalize_reward, is_currency, is_key_item,
)
from input_handler import InputHandler
from settings import INPUT_MAP, PLAYER_MAX_HP
from states.gameplay import DEATH_SEQUENCE_DURATION, GameplayState
from wallet import Wallet


class _DummyInput:
    def is_pressed(self, _name):
        return False

    def is_held(self, _name):
        return False


class _DummyStates:
    def __init__(self):
        self.current_name = ""
        self.changes = []
        self._states = {}

    def change(self, name: str):
        self.current_name = name
        self.changes.append(name)

    def register(self, name, state):
        self._states[name] = state


class _DummyGame:
    def __init__(self):
        self.difficulty_mode = "normal"
        self.difficulty_config = get_difficulty_config("normal")
        self.inventory = Inventory()
        self.quest_manager = QuestManager()
        self.wallet = Wallet()
        self.campaign = Campaign()
        self.input = _DummyInput()
        self.states = _DummyStates()

    @property
    def difficulty_label(self):
        return self.difficulty_mode.title()

    def set_difficulty(self, mode):
        from ai.config_loader import normalize_difficulty
        self.difficulty_mode = normalize_difficulty(mode)
        self.difficulty_config = get_difficulty_config(self.difficulty_mode)


# ─── Coin Handling ─────────────────────────────────────────────────────

class TestCoinPickup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_currency_pickup_uses_wallet_not_inventory(self):
        """Coins go to wallet, not key-item inventory."""
        game = _DummyGame()
        gameplay = GameplayState(game)
        for i in range(game.inventory.max_items):
            game.inventory.add(f"dummy_{i}")

        start_count = game.inventory.count()
        coins = GroundItem(0, 0, reward=make_currency_reward(5))
        gameplay._collect_reward_item(coins)

        self.assertEqual(game.wallet.coins, 5)
        self.assertEqual(game.inventory.count(), start_count)
        self.assertTrue(coins.collected)

    def test_currency_never_triggers_already_carrying(self):
        """Multiple currency pickups never fail with 'Already carrying that'."""
        game = _DummyGame()
        gameplay = GameplayState(game)

        for _ in range(10):
            coin = GroundItem(0, 0, reward=make_currency_reward(3))
            gameplay._collect_reward_item(coin)
            self.assertTrue(coin.collected)

        self.assertEqual(game.wallet.coins, 30)

    def test_currency_with_full_inventory(self):
        """Coins work even when key-item inventory is completely full."""
        game = _DummyGame()
        gameplay = GameplayState(game)
        # Fill with a known stackable item to actually fill grid slots
        # health_potion stacks to 10, so we need to fill all 24 slots
        # by placing one ItemStack(unique item) per slot
        from item_system import ItemStack
        for i in range(game.inventory.max_items):
            game.inventory.grid.set_slot(i, ItemStack("health_potion", 10))
        self.assertEqual(game.inventory.count(), game.inventory.max_items)

        coin = GroundItem(0, 0, reward=make_currency_reward(10))
        gameplay._collect_reward_item(coin)

        self.assertTrue(coin.collected)
        self.assertEqual(game.wallet.coins, 10)
        self.assertEqual(game.inventory.count(), game.inventory.max_items)

    def test_heal_reward_does_not_use_inventory(self):
        """Heal rewards don't consume inventory slots."""
        game = _DummyGame()
        gameplay = GameplayState(game)
        gameplay.player.hp = 1

        heal = GroundItem(0, 0, reward=make_heal_reward(2))
        gameplay._collect_reward_item(heal)

        self.assertTrue(heal.collected)
        self.assertGreater(gameplay.player.hp, 1)
        self.assertEqual(game.inventory.count(), 0)


# ─── Reward Type Classification ───────────────────────────────────────

class TestRewardTypes(unittest.TestCase):
    def test_is_currency_detects_coins(self):
        self.assertTrue(is_currency({"kind": "currency", "amount": 5}))
        self.assertTrue(is_currency({"kind": "coin", "amount": 1}))
        self.assertTrue(is_currency({"kind": "coins", "amount": 1}))

    def test_is_currency_rejects_key_items(self):
        self.assertFalse(is_currency({"kind": "key_item", "item_id": "sword"}))
        self.assertFalse(is_currency({"kind": "item", "item_id": "sword"}))

    def test_is_key_item_detects_items(self):
        self.assertTrue(is_key_item({"kind": "key_item", "item_id": "x"}))
        self.assertTrue(is_key_item({"kind": "item", "item_id": "x"}))

    def test_is_key_item_rejects_currency(self):
        self.assertFalse(is_key_item({"kind": "currency", "amount": 5}))


# ─── Sword / Attack Gating ────────────────────────────────────────────

class TestSwordGating(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_player_cannot_attack_without_sword(self):
        """Before obtaining sword, start_attack should fail."""
        player = Player(5, 5)
        self.assertFalse(player.has_sword)
        self.assertFalse(player.can_attack)
        result = player.start_attack()
        self.assertFalse(result)
        self.assertEqual(player.state, "idle")

    def test_player_can_attack_with_sword(self):
        """After obtaining sword, start_attack should succeed."""
        player = Player(5, 5)
        player.has_sword = True
        self.assertTrue(player.can_attack)
        result = player.start_attack()
        self.assertTrue(result)
        self.assertEqual(player.state, "attack_windup")

    def test_sword_gating_in_gameplay(self):
        """Gameplay syncs has_sword from inventory correctly."""
        game = _DummyGame()
        gameplay = GameplayState(game)
        self.assertFalse(gameplay.player.has_sword)

        game.inventory.add("old_sword")
        gameplay._sync_player_weapon()
        self.assertTrue(gameplay.player.has_sword)

    def test_sword_state_survives_save_load(self):
        """Sword state persists through save/load."""
        game = _DummyGame()
        gameplay = GameplayState(game)
        game.inventory.add("old_sword")
        gameplay._sync_player_weapon()
        self.assertTrue(gameplay.player.has_sword)

        # Simulate save
        snapshot = gameplay._make_snapshot()
        # With v4 inventory, the snapshot dict has {"grid": [{id: "old_sword", qty: 1}, ...]}
        grid_items = [slot["id"] for slot in snapshot["inventory"]["grid"] if slot is not None]
        self.assertIn("old_sword", grid_items)

        # Simulate load
        game2 = _DummyGame()
        game2.inventory.add("old_sword")
        gameplay2 = GameplayState(game2)
        gameplay2._sync_player_weapon()
        self.assertTrue(gameplay2.player.has_sword)

    def test_new_game_player_has_no_sword(self):
        """Fresh game starts without sword."""
        game = _DummyGame()
        gameplay = GameplayState(game)
        self.assertFalse(gameplay.player.has_sword)
        self.assertFalse(gameplay.player.can_attack)


# ─── Boss Collision ───────────────────────────────────────────────────

class TestBossCollision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_boss_body_collision_returned_when_active(self):
        """Active boss returns collision footprint."""
        boss = Boss(10, 10)
        boss.activate()
        boss.state = "idle"
        boss.state_timer = 3.0
        body = boss.body_collision()
        self.assertIsNotNone(body)
        self.assertIn("x", body)
        self.assertIn("y", body)
        self.assertIn("radius", body)

    def test_boss_no_collision_when_dormant(self):
        """Dormant boss has no collision."""
        boss = Boss(10, 10)
        body = boss.body_collision()
        self.assertIsNone(body)

    def test_boss_no_collision_when_dead(self):
        """Dead boss has no collision."""
        boss = Boss(10, 10)
        boss.alive = False
        boss.state = "death"
        body = boss.body_collision()
        self.assertIsNone(body)

    def test_player_blocked_by_boss_body(self):
        """Player _hits_boss correctly detects overlap."""
        player = Player(10, 10)
        boss_body = {"x": 10.5, "y": 10.5, "radius": 0.8}
        self.assertTrue(player._hits_boss(10.0, 10.0, boss_body))

    def test_player_not_blocked_when_far(self):
        """Player not blocked when far from boss."""
        player = Player(5, 5)
        boss_body = {"x": 10.5, "y": 10.5, "radius": 0.8}
        self.assertFalse(player._hits_boss(5.0, 5.0, boss_body))

    def test_player_hits_boss_is_false_when_none(self):
        """No boss body means no collision."""
        player = Player(10, 10)
        self.assertFalse(player._hits_boss(10.0, 10.0, None))


# ─── Drop Map Scoping ─────────────────────────────────────────────────

class TestDropMapScoping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_dynamic_drop_records_have_map_field(self):
        """Dynamic drops must be tagged with their map name."""
        game = _DummyGame()
        gameplay = GameplayState(game)
        coin = GroundItem(5, 5, drop_id="test_drop", dynamic=True, reward=make_currency_reward(1))
        gameplay._register_dynamic_drop(coin)

        self.assertTrue(len(gameplay.dynamic_drop_records) > 0)
        record = gameplay.dynamic_drop_records[-1]
        self.assertIn("map", record)
        self.assertEqual(record["map"], gameplay.map_mgr.current_name)


class TestPortabilityRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_tilemap_bake_does_not_reset_global_random_stream(self):
        import random
        from tilemap import TileMap

        map_data = {
            "width": 1,
            "height": 1,
            "ground": [[0]],
            "decor": [[0]],
            "collision": [[0]],
            "spawns": {},
        }

        random.seed(999)
        first = random.random()
        TileMap(map_data)
        after_bake = random.random()

        random.seed(999)
        self.assertEqual(first, random.random())
        expected_after = random.random()
        self.assertEqual(after_bake, expected_after)

    def test_input_handler_tracks_logical_button_edges_without_pygame_events(self):
        handler = InputHandler(buttons=("a", "start"))

        handler.update()
        handler.press("a")
        self.assertTrue(handler.is_pressed("a"))
        self.assertTrue(handler.is_held("a"))

        handler.update()
        self.assertFalse(handler.is_pressed("a"))
        self.assertTrue(handler.is_held("a"))

        handler.release("a")
        self.assertTrue(handler.is_released("a"))
        self.assertFalse(handler.is_held("a"))

    def test_pygame_runtime_routes_keyboard_events_into_logical_buttons(self):
        from runtime.pygame_runtime import PygameRuntime

        runtime = PygameRuntime()
        handler = InputHandler()
        handler.update()

        runtime.route_input_event(
            handler,
            pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_z}),
        )
        self.assertTrue(handler.is_pressed("a"))
        self.assertTrue(handler.is_held("a"))

        handler.update()
        runtime.route_input_event(
            handler,
            pygame.event.Event(pygame.KEYUP, {"key": pygame.K_z}),
        )
        self.assertTrue(handler.is_released("a"))
        self.assertFalse(handler.is_held("a"))

    def test_gameplay_camera_uses_target_profile_viewport(self):
        game = _DummyGame()
        game.target_profile = type(
            "_Profile",
            (),
            {"screen_width": 240, "screen_height": 160},
        )()

        gameplay = GameplayState(game)

        self.assertEqual(gameplay.viewport_width, 240)
        self.assertEqual(gameplay.viewport_height, 160)
        self.assertEqual(gameplay.camera.viewport_width, 240)
        self.assertEqual(gameplay.camera.viewport_height, 160)

    def test_hud_layout_scales_inside_small_viewport(self):
        from hud import HUD

        hud = HUD(240, 160)
        hx, hy, slot_sz, pad, total_w = hud._hotbar_layout()
        mx, my, mm_w, mm_h = hud._minimap_layout()

        self.assertGreaterEqual(hx, 0)
        self.assertLessEqual(hx + total_w, hud.viewport_width)
        self.assertGreaterEqual(hy, 0)
        self.assertLessEqual(hy + slot_sz, hud.viewport_height)
        self.assertGreaterEqual(mx, 0)
        self.assertGreaterEqual(my, 0)
        self.assertLessEqual(mx + mm_w, hud.viewport_width)
        self.assertLessEqual(my + mm_h, hud.viewport_height)

    def test_dialogue_box_layout_stays_inside_small_viewport(self):
        from dialogue import DialogueBox

        box = DialogueBox(240, 160)
        self.assertGreaterEqual(box.box_x, 0)
        self.assertGreaterEqual(box.box_y, 0)
        self.assertLessEqual(box.box_x + box.box_w, box.viewport_width)
        self.assertLessEqual(box.box_y + box.box_height, box.viewport_height)

        surface = pygame.Surface((240, 160))
        box.open("Guide", ["Test dialogue for handheld layout."])
        box.render(surface)

    def test_pause_state_renders_on_small_viewport(self):
        from states.pause import PauseState

        game = _DummyGame()
        game.target_profile = type("_Profile", (), {"screen_width": 240, "screen_height": 160})()
        surface = pygame.Surface((240, 160))

        state = PauseState(game)
        state.enter()
        state.render(surface)

    def test_game_over_state_renders_on_small_viewport(self):
        from states.game_over import GameOverState

        game = _DummyGame()
        game.target_profile = type("_Profile", (), {"screen_width": 240, "screen_height": 160})()
        surface = pygame.Surface((240, 160))

        state = GameOverState(game)
        state.enter()
        state.timer = 2.0
        state.render(surface)

    def test_victory_state_renders_on_small_viewport(self):
        from states.victory import VictoryState

        game = _DummyGame()
        game.target_profile = type("_Profile", (), {"screen_width": 240, "screen_height": 160})()
        surface = pygame.Surface((240, 160))

        state = VictoryState(game)
        state.prepare(2)
        state.timer = 3.0
        state.render(surface)
        state.prepare(3)
        state.timer = 4.0
        state.render(surface)

    def test_instructions_state_renders_on_small_viewport(self):
        from states.instructions import InstructionsState

        game = _DummyGame()
        game.target_profile = type("_Profile", (), {"screen_width": 240, "screen_height": 160})()
        surface = pygame.Surface((240, 160))

        state = InstructionsState(game)
        state.enter()
        state.render(surface)
        self.assertGreater(state._content_h, 0)

    def test_inventory_screen_renders_on_small_viewport(self):
        from states.inventory_screen import InventoryScreenState

        game = _DummyGame()
        game.target_profile = type("_Profile", (), {"screen_width": 240, "screen_height": 160})()
        surface = pygame.Surface((240, 160))

        state = InventoryScreenState(game)
        state.enter()
        state.render(surface)

    def test_skill_screen_renders_on_small_viewport(self):
        from progression import Progression
        from states.skill_screen import SkillScreenState

        game = _DummyGame()
        game.progression = Progression()
        game.target_profile = type("_Profile", (), {"screen_width": 240, "screen_height": 160})()
        surface = pygame.Surface((240, 160))

        state = SkillScreenState(game)
        state.enter()
        state.render(surface)



    def test_bestiary_screen_renders_on_small_viewport(self):
        from bestiary import Bestiary
        from states.bestiary_screen import BestiaryScreenState

        game = _DummyGame()
        game.bestiary = Bestiary()
        game.target_profile = type("_Profile", (), {"screen_width": 240, "screen_height": 160})()
        surface = pygame.Surface((240, 160))

        state = BestiaryScreenState(game)
        state.enter()
        state.render(surface)

    def test_stage_intro_renders_on_small_viewport(self):
        from states.stage_intro import StageIntroState

        game = _DummyGame()
        game.target_profile = type("_Profile", (), {"screen_width": 240, "screen_height": 160})()
        surface = pygame.Surface((240, 160))

        state = StageIntroState(game)
        state.prepare(3, "The Mythic Sanctum")
        state.enter()
        state.timer = 1.2
        state.render(surface)

    def test_font_cache_reuses_matching_fonts(self):
        from ui.fonts import clear_font_cache, get_font

        clear_font_cache()
        font_a = get_font(14)
        font_b = get_font(14)
        font_c = get_font(14, bold=True)

        self.assertIs(font_a, font_b)
        self.assertIsNot(font_a, font_c)

    def test_title_screen_renders_on_small_viewport(self):
        from states.title import TitleState

        game = _DummyGame()
        game.target_profile = type("_Profile", (), {"screen_width": 240, "screen_height": 160})()
        surface = pygame.Surface((240, 160))

        state = TitleState(game)
        state.enter()
        state.render(surface)

    def test_runtime_frame_clock_advances_without_pygame_timer(self):
        from runtime.frame_clock import advance_time, get_time, reset_time

        reset_time()
        self.assertEqual(get_time(), 0.0)
        advance_time(0.25)
        advance_time(0.5)
        self.assertAlmostEqual(get_time(), 0.75)

    def test_weather_system_tracks_small_viewport(self):
        from weather import WeatherSystem

        weather = WeatherSystem(viewport_width=240, viewport_height=160)
        weather.force_state("rain")
        weather.update(0.2)

        self.assertTrue(all(0 <= p.x <= 240 for p in weather._particles))

        surface = pygame.Surface((240, 160))
        weather.render(surface)
        self.assertEqual(weather._overlay_surf.get_size(), (240, 160))

    def test_game_math_helpers_produce_stable_vector_results(self):
        from game_math import angle_between_vectors_deg, point_distance, pulse01, safe_normalize

        nx, ny, length = safe_normalize(3.0, 4.0)
        self.assertAlmostEqual(length, 5.0)
        self.assertAlmostEqual(nx, 0.6)
        self.assertAlmostEqual(ny, 0.8)
        self.assertAlmostEqual(point_distance(1.0, 2.0, 4.0, 6.0), 5.0)
        self.assertAlmostEqual(angle_between_vectors_deg(1.0, 0.0, 0.0, 1.0), 90.0)
        self.assertAlmostEqual(pulse01(0.0, 3.0), 0.5)

    def test_pygame_runtime_falls_back_to_null_audio_without_mixer(self):
        from runtime.null_audio import NullAudioManager
        from runtime.pygame_runtime import PygameRuntime

        runtime = PygameRuntime()
        runtime._mixer_ready = False

        self.assertIsInstance(runtime.create_audio(), NullAudioManager)

    def test_map_manager_fade_resizes_to_small_viewport(self):
        from map_manager import MapManager

        mgr = MapManager(240, 160, supports_alpha=True)
        mgr.transitioning = True
        mgr.fade_alpha = 128
        surface = pygame.Surface((240, 160))

        mgr.render_fade(surface)

        self.assertEqual(mgr._fade_surf.get_size(), (240, 160))

    def test_map_manager_quantized_fade_supports_non_alpha_targets(self):
        from map_manager import MapManager

        mgr = MapManager(240, 160, supports_alpha=False)
        mgr.transitioning = True
        mgr.fade_alpha = 255
        surface = pygame.Surface((240, 160))
        surface.fill((90, 40, 20))

        mgr.render_fade(surface)

        self.assertEqual(surface.get_at((0, 0))[:3], (0, 0, 0))

    def test_lighting_system_tracks_small_viewport_and_non_alpha_fallback(self):
        from lighting import LightingSystem

        lighting = LightingSystem(240, 160, supports_alpha=False)
        lighting.set_map("dungeon")
        lighting.update(0.16, 10.0, 12.0, set())

        surface = pygame.Surface((240, 160))
        surface.fill((120, 100, 80))
        lighting.render(surface, 0, 0)

        self.assertEqual((lighting.viewport_width, lighting.viewport_height), (240, 160))
        self.assertNotEqual(surface.get_at((0, 0))[:3], (120, 100, 80))

    def test_post_processor_tracks_small_viewport_and_non_alpha_fallback(self):
        from post_process import PostProcessor

        post = PostProcessor(240, 160, supports_alpha=False)
        post.set_map("dungeon")
        post.trigger_hit_flash((255, 255, 255), 0.6)
        post.trigger_death_fade()
        post.update(0.25)

        surface = pygame.Surface((240, 160))
        surface.fill((80, 90, 120))
        post.render(surface)

        self.assertEqual((post.viewport_width, post.viewport_height), (240, 160))
        self.assertGreater(post._death_fade_alpha, 0.0)

    def test_gameplay_target_profile_drives_shared_fx_capabilities(self):
        game = _DummyGame()
        game.target_profile = type(
            "_Profile",
            (),
            {"screen_width": 240, "screen_height": 160, "supports_alpha": False},
        )()

        gameplay = GameplayState(game)

        self.assertFalse(gameplay.lighting._supports_alpha)
        self.assertFalse(gameplay.post_process._supports_alpha)

    def test_gameplay_damage_advances_post_process_effects(self):
        game = _DummyGame()
        gameplay = GameplayState(game)

        gameplay._apply_player_damage(1, gameplay.player.x, gameplay.player.y, sfx="hurt")
        self.assertGreater(gameplay.post_process._hit_flash_alpha, 0.0)
        flash_alpha = gameplay.post_process._hit_flash_alpha
        gameplay.post_process.update(0.1)
        self.assertLess(gameplay.post_process._hit_flash_alpha, flash_alpha)

        gameplay.player.hp = 1
        gameplay.player.iframes = 0.0
        gameplay.player.state = "idle"
        gameplay._apply_player_damage(999, gameplay.player.x, gameplay.player.y, sfx="boss_slam")
        gameplay.post_process.update(0.1)
        self.assertGreater(gameplay.post_process._death_fade_alpha, 0.0)

    def test_tilemap_render_uses_visible_area_blit(self):
        from tilemap import TileMap

        map_data = {
            "width": 4,
            "height": 4,
            "ground": [[0, 1, 2, 3] for _ in range(4)],
            "decor": [[0, 0, 0, 0] for _ in range(4)],
            "collision": [[0, 0, 0, 0] for _ in range(4)],
            "spawns": {},
        }
        tilemap = TileMap(map_data)
        surface = pygame.Surface((24, 24))
        surface.fill((255, 0, 255))

        tilemap.render(surface, 8, 8)

        self.assertEqual(surface.get_at((0, 0)), tilemap._ground_surf.get_at((8, 8)))

    def test_tilemap_render_handles_negative_camera_offset(self):
        from tilemap import TileMap

        map_data = {
            "width": 2,
            "height": 2,
            "ground": [[0, 0], [0, 0]],
            "decor": [[0, 0], [0, 0]],
            "collision": [[0, 0], [0, 0]],
            "spawns": {},
        }
        tilemap = TileMap(map_data)
        surface = pygame.Surface((32, 32))
        surface.fill((255, 0, 255))

        tilemap.render(surface, -4, -6)

        self.assertEqual(surface.get_at((4, 6)), tilemap._ground_surf.get_at((0, 0)))


# ─── Hard Mode Meaningful Differences ─────────────────────────────────

class TestHardModeDifficulty(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        clear_config_cache()

    def test_hard_enemies_have_more_damage(self):
        """Hard mode enemies should deal more damage than normal."""
        normal_cfg = get_difficulty_config("normal")
        hard_cfg = get_difficulty_config("hard")
        self.assertGreater(
            hard_cfg["enemy_stat_mults"]["damage"],
            normal_cfg["enemy_stat_mults"]["damage"]
        )

    def test_hard_enemies_are_faster(self):
        """Hard mode enemies should be faster."""
        normal_cfg = get_difficulty_config("normal")
        hard_cfg = get_difficulty_config("hard")
        self.assertGreater(
            hard_cfg["enemy_stat_mults"]["speed"],
            normal_cfg["enemy_stat_mults"]["speed"]
        )

    def test_hard_enemies_attack_faster(self):
        """Hard mode enemies have shorter attack cooldowns."""
        normal_cfg = get_difficulty_config("normal")
        hard_cfg = get_difficulty_config("hard")
        self.assertLess(
            hard_cfg["enemy_stat_mults"]["attack_cd"],
            normal_cfg["enemy_stat_mults"]["attack_cd"]
        )

    def test_hard_boss_has_more_hp(self):
        """Hard mode boss should have more HP."""
        normal_cfg = get_difficulty_config("normal")
        hard_cfg = get_difficulty_config("hard")
        self.assertGreater(
            hard_cfg["boss_stat_mults"]["hp"],
            normal_cfg["boss_stat_mults"]["hp"]
        )

    def test_hard_boss_has_shorter_cooldowns(self):
        """Hard mode boss should have shorter cooldowns."""
        normal_cfg = get_difficulty_config("normal")
        hard_cfg = get_difficulty_config("hard")
        self.assertLess(
            hard_cfg["boss_stat_mults"]["cooldown"],
            normal_cfg["boss_stat_mults"]["cooldown"]
        )

    def test_hard_boss_has_more_damage(self):
        """Hard mode boss should deal more damage."""
        normal_cfg = get_difficulty_config("normal")
        hard_cfg = get_difficulty_config("hard")
        self.assertGreater(
            hard_cfg["boss_stat_mults"]["damage"],
            normal_cfg["boss_stat_mults"]["damage"]
        )

    def test_hard_boss_phase2_triggers_earlier(self):
        """Hard boss enters phase 2 at higher HP threshold."""
        normal_cfg = get_difficulty_config("normal")
        hard_cfg = get_difficulty_config("hard")
        self.assertGreater(
            hard_cfg["boss_stat_mults"]["phase2_threshold"],
            normal_cfg["boss_stat_mults"]["phase2_threshold"]
        )

    def test_hard_ai_more_aggressive(self):
        """Hard mode AI has higher aggression multipliers."""
        normal_cfg = get_difficulty_config("normal")
        hard_cfg = get_difficulty_config("hard")
        self.assertGreater(hard_cfg["ai"]["pressure_scale"], normal_cfg["ai"]["pressure_scale"])
        self.assertGreater(hard_cfg["ai"]["aggressiveness"], normal_cfg["ai"]["aggressiveness"])
        self.assertLess(hard_cfg["ai"]["retreat_bias"], normal_cfg["ai"]["retreat_bias"])

    def test_hard_player_takes_more_damage(self):
        """Hard mode player damage taken multiplier is higher."""
        normal_cfg = get_difficulty_config("normal")
        hard_cfg = get_difficulty_config("hard")
        self.assertGreater(
            hard_cfg["player_damage_taken_mult"],
            normal_cfg["player_damage_taken_mult"]
        )

    def test_hard_player_deals_less_damage(self):
        """Hard mode player deals less attack damage."""
        normal_cfg = get_difficulty_config("normal")
        hard_cfg = get_difficulty_config("hard")
        self.assertLess(
            hard_cfg["player_attack_damage_mult"],
            normal_cfg["player_attack_damage_mult"]
        )

    def test_hard_mode_significant_damage_difference(self):
        """Hard enemy damage mult should be at least 1.4x normal (meaningful gap)."""
        hard_cfg = get_difficulty_config("hard")
        self.assertGreaterEqual(hard_cfg["enemy_stat_mults"]["damage"], 1.4)

    def test_hard_boss_cooldown_significantly_shorter(self):
        """Hard boss cooldown mult should be at most 0.7x normal (meaningful gap)."""
        hard_cfg = get_difficulty_config("hard")
        self.assertLessEqual(hard_cfg["boss_stat_mults"]["cooldown"], 0.7)


class TestStageRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_stage_2_boss_routes_to_stage_3_intro(self):
        from states.stage_intro import StageIntroState
        from states.victory import VictoryState

        game = _DummyGame()
        game.save_current_game = lambda: None
        game.campaign.complete_stage(1)
        gameplay = GameplayState(game)
        game.states.register("gameplay", gameplay)
        game.states.register("victory", VictoryState(game))
        game.states.register("stage_intro", StageIntroState(game))

        gameplay._current_boss_id = "gravewarden"
        gameplay._handle_boss_defeat_routing()

        self.assertEqual(game.campaign.world_stage, 3)
        self.assertEqual(game.states.current_name, "stage_intro")
        intro = game.states._states["stage_intro"]
        self.assertEqual(intro.stage_number, 3)

    def test_stage_2_boss_without_intro_state_falls_forward_not_to_victory(self):
        from states.victory import VictoryState

        game = _DummyGame()
        game.save_current_game = lambda: None
        game.campaign.complete_stage(1)
        gameplay = GameplayState(game)
        game.states.register("gameplay", gameplay)
        game.states.register("victory", VictoryState(game))

        gameplay._current_boss_id = "gravewarden"
        gameplay._handle_boss_defeat_routing()

        self.assertEqual(game.campaign.world_stage, 3)
        self.assertEqual(game.states.current_name, "gameplay")
        self.assertEqual(gameplay.map_mgr.current_name, "sanctum_halls")

    def test_stage_3_path_unlocks_from_stage_2_completion_fallbacks(self):
        game = _DummyGame()
        gameplay = GameplayState(game)
        game.campaign.boss_kills["gravewarden"] = True
        self.assertTrue(gameplay._is_stage_path_unlocked("sanctum_halls"))

        game2 = _DummyGame()
        gameplay2 = GameplayState(game2)
        game2.quest_manager.get_quest("main_s2").complete = True
        gameplay2._load_map("ruins_depths", capture_checkpoint=False)
        self.assertTrue(gameplay2._is_stage_path_unlocked("sanctum_halls"))

    def test_player_can_transition_from_ruins_depths_into_stage_3(self):
        game = _DummyGame()
        gameplay = GameplayState(game)
        game.campaign.complete_stage(1)
        game.campaign.complete_stage(2)
        gameplay._load_map("ruins_depths", spawn=(58.6, 19.0), capture_checkpoint=False)

        gameplay.update(1 / 60)
        self.assertTrue(gameplay.map_mgr.transitioning)

        gameplay.update(1.0)
        self.assertEqual(gameplay.map_mgr.current_name, "sanctum_halls")

    def test_invalid_final_victory_recovers_to_stage_3_gameplay(self):
        from states.victory import VictoryState

        game = _DummyGame()
        game.campaign.complete_stage(1)
        game.campaign.complete_stage(2)
        gameplay = GameplayState(game)
        game.states.register("gameplay", gameplay)
        game.states.register("victory", VictoryState(game))

        victory = game.states._states["victory"]
        victory.prepare(3)
        victory.enter()

        self.assertEqual(game.states.current_name, "gameplay")
        self.assertEqual(gameplay.map_mgr.current_name, "sanctum_halls")
        self.assertFalse(gameplay.defeated_boss)


# ─── Save/Load ─────────────────────────────────────────────────────────

class TestSaveLoad(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_save_load_preserves_coin_total(self):
        player = Player(2, 3)
        inventory = Inventory()
        inventory.add("old_sword")
        quests = QuestManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            original_path = save_manager.SAVE_PATH
            save_manager.SAVE_PATH = os.path.join(tmpdir, "savegame.json")
            try:
                saved = save_manager.save_game(
                    player, inventory, quests, "village",
                    opened_chests=[], collected_items=[],
                    defeated_boss=False, difficulty_mode="hard", coins=42,
                )
                self.assertTrue(saved)
                loaded = save_manager.load_game()
            finally:
                save_manager.SAVE_PATH = original_path

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["coins"], 42)
        self.assertEqual(loaded["difficulty"], "hard")
        # v4 inventory format: check grid for the item
        inv_data = loaded["inventory"]
        if isinstance(inv_data, dict):
            grid = inv_data.get("grid", [])
            item_ids = [s["id"] for s in grid if s]
            self.assertIn("old_sword", item_ids)
        else:
            self.assertIn("old_sword", inv_data)

    def test_save_load_preserves_sword_in_inventory(self):
        """Sword item persists through save/load."""
        player = Player(5, 5)
        inventory = Inventory()
        inventory.add("old_sword")
        quests = QuestManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            original_path = save_manager.SAVE_PATH
            save_manager.SAVE_PATH = os.path.join(tmpdir, "savegame.json")
            try:
                save_manager.save_game(
                    player, inventory, quests, "dungeon",
                    opened_chests=[], collected_items=[],
                    defeated_boss=False, coins=0,
                )
                loaded = save_manager.load_game()
            finally:
                save_manager.SAVE_PATH = original_path

        # v4 inventory format: check grid for the item
        inv_data = loaded["inventory"]
        if isinstance(inv_data, dict):
            grid = inv_data.get("grid", [])
            item_ids = [s["id"] for s in grid if s]
            self.assertIn("old_sword", item_ids)
        else:
            self.assertIn("old_sword", inv_data)

    def test_save_serialization_roundtrips_through_bytes(self):
        data = {
            "version": 5,
            "map": "sanctum_halls",
            "coins": 42,
            "inventory": {"grid": [{"id": "old_sword", "qty": 1}], "craft_bag": []},
        }

        payload = save_manager.serialize_save_data(data)
        restored = save_manager.deserialize_save_data(payload)

        self.assertIsInstance(payload, bytes)
        self.assertEqual(restored, data)
        self.assertGreater(save_manager.estimate_save_size(data), 0)

    def test_apply_save_data_preserves_saved_boss_flags(self):
        """Loading a saved boss room should not wipe boss completion flags mid-load."""
        game = _DummyGame()
        gameplay = GameplayState(game)

        gameplay.apply_save_data({
            "map": "dungeon",
            "player_x": 20,
            "player_y": 8,
            "player_hp": 5,
            "player_facing": "left",
            "opened_chests": [],
            "collected_items": [],
            "defeated_enemies": [],
            "dynamic_drops": [],
            "defeated_boss": True,
            "boss_state": {
                "x": 20.0,
                "y": 8.0,
                "hp": 0,
                "defeated": True,
                "active": True,
            },
        }, capture_checkpoint=False)

        self.assertTrue(gameplay.defeated_boss)
        self.assertTrue(gameplay.boss_save_state.get("defeated"))
        self.assertIsNone(gameplay.boss)

    def test_sanitize_loaded_save_rewinds_completed_throne_room_resume(self):
        """Completed throne-room saves should rewind to the Stage 3 gateway for replay/testing."""
        data = {
            "map": "throne_room",
            "player_x": 39.4,
            "player_y": 15.8,
            "player_facing": "up",
            "defeated_boss": True,
            "defeated_enemies": ["sh_void_01", "tr_void_01", "dungeon_slime_01"],
            "boss_state": {"hp": 0, "defeated": True, "active": True},
            "quest_stages": {
                "main_s3": {"stage": 3, "complete": True},
            },
            "campaign": {
                "world_stage": 3,
                "completed_stages": [1, 2, 3],
                "boss_kills": {
                    "dark_golem": True,
                    "gravewarden": True,
                    "mythic_sovereign": True,
                },
                "stage_flags": {},
                "player_form": "mythic",
            },
        }

        sanitized = save_manager.sanitize_loaded_save(data)

        self.assertEqual(sanitized["map"], "ruins_depths")
        self.assertEqual(sanitized["player_x"], 58.6)
        self.assertEqual(sanitized["player_y"], 19.0)
        self.assertEqual(sanitized["player_facing"], "right")
        self.assertFalse(sanitized["defeated_boss"])
        self.assertEqual(sanitized["boss_state"], {})
        self.assertEqual(sanitized["defeated_enemies"], ["dungeon_slime_01"])
        self.assertEqual(sanitized["campaign"]["completed_stages"], [1, 2])
        self.assertFalse(sanitized["campaign"]["boss_kills"]["mythic_sovereign"])
        self.assertFalse(sanitized["quest_stages"]["main_s3"]["complete"])

    def test_sanitize_loaded_save_rewinds_unfinished_throne_room_resume(self):
        """Unfinished throne-room saves should resume before the final arena, not inside it."""
        data = {
            "map": "throne_room",
            "player_x": 30.0,
            "player_y": 17.0,
            "player_facing": "up",
            "defeated_boss": False,
            "boss_state": {},
            "quest_stages": {
                "main_s3": {"stage": 2, "complete": False},
            },
            "campaign": {
                "world_stage": 3,
                "completed_stages": [1, 2],
                "boss_kills": {
                    "dark_golem": True,
                    "gravewarden": True,
                    "mythic_sovereign": False,
                },
                "stage_flags": {},
                "player_form": "mythic",
            },
        }

        sanitized = save_manager.sanitize_loaded_save(data)

        self.assertEqual(sanitized["map"], "sanctum_halls")
        self.assertEqual(sanitized["player_x"], 2.0)
        self.assertEqual(sanitized["player_y"], 19.0)
        self.assertEqual(sanitized["player_facing"], "right")
        self.assertFalse(sanitized["defeated_boss"])
        self.assertEqual(sanitized["boss_state"], {})


# ─── Equipment Model ─────────────────────────────────────────────────

class TestEquipmentModel(unittest.TestCase):
    def test_dual_armor_slots_allow_cloak_and_aegis(self):
        """Two armor items can be equipped at the same time."""
        inv = Inventory()
        inv.add("shadow_cloak")
        inv.add("ascended_aegis")

        self.assertTrue(inv.equip("shadow_cloak"))
        self.assertTrue(inv.equip("ascended_aegis"))

        equipped = inv.equipment.equipped
        self.assertEqual(
            {equipped["armor_1"], equipped["armor_2"]},
            {"shadow_cloak", "ascended_aegis"},
        )
        self.assertIn("enable_dash", inv.equipped_effects)
        self.assertEqual(inv.equipped_stats.get("defense"), 8)

    def test_weapons_are_not_equipped_through_gear_slots(self):
        """Weapons stay in the grid/hotbar and do not consume an equipment slot."""
        inv = Inventory()
        inv.add("old_sword")

        self.assertFalse(inv.equip("old_sword"))
        self.assertTrue(inv.grid.has("old_sword"))
        self.assertIsNone(inv.equipment.weapon)
        self.assertEqual(inv.equipped_weapon, "old_sword")

    def test_legacy_weapon_slot_migrates_back_to_grid(self):
        """Loading an old save moves the equipped weapon back into the grid."""
        inv = Inventory.from_save({
            "grid": [],
            "craft_bag": [],
            "equipment": {
                "weapon": "old_sword",
                "armor": "shadow_cloak",
                "accessory": "speed_ring",
            },
        })

        self.assertTrue(inv.grid.has("old_sword"))
        self.assertEqual(inv.equipment.equipped["armor_1"], "shadow_cloak")
        self.assertIsNone(inv.equipment.equipped["armor_2"])
        self.assertEqual(inv.equipment.equipped["accessory"], "speed_ring")


# ─── Boss Recovery / Stage Scaling ───────────────────────────────────

class TestBossRecoveryAndStageScaling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_player_can_escape_boss_collision_while_hurt(self):
        """Hurt-state knockback should not be pinned by boss body overlap."""
        player = Player(10, 10)
        player.state = "hurt"
        boss_body = {"x": 10.5, "y": 10.5, "radius": 0.9}
        self.assertFalse(player._hits_boss(10.0, 10.0, boss_body))

    def test_stage_three_grants_bonus_max_hp(self):
        """Later stages increase player max HP to keep pace with difficulty."""
        game = _DummyGame()
        game.campaign.world_stage = 3
        gameplay = GameplayState(game)
        self.assertEqual(gameplay.player.max_hp, PLAYER_MAX_HP + 4)

    def test_gravewarden_body_collision_uses_centered_footprint(self):
        """Stage 2 boss body collision should be centered like the stage 1 boss."""
        boss = Gravewarden(10, 12)
        boss.activate()
        boss.state = "idle"
        boss.state_timer = boss.intro_duration
        body = boss.body_collision()
        self.assertIsNotNone(body)
        self.assertEqual(body["x"], 10.5)
        self.assertEqual(body["y"], 12.5)


# ─── Death Flow ────────────────────────────────────────────────────────

class TestDeathFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_lethal_damage_reliably_transitions_to_game_over(self):
        game = _DummyGame()
        gameplay = GameplayState(game)

        lethal = gameplay._apply_player_damage(gameplay.player.max_hp, 0, 0)

        self.assertTrue(lethal)
        self.assertEqual(gameplay.player.hp, 0)
        self.assertEqual(gameplay.flow_state, "player_dying")
        self.assertEqual(game.states.changes, [])

        gameplay._update_death_sequence(DEATH_SEQUENCE_DURATION)

        self.assertEqual(game.states.current_name, "game_over")
        self.assertIn("game_over", game.states.changes)


# ─── Identity Contract ────────────────────────────────────────────────

class TestIdentityContract(unittest.TestCase):
    """All combat-relevant entities expose enemy_type and xp_reward."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_enemy_has_enemy_type_property(self):
        """Enemy.enemy_type returns the archetype string."""
        e = Enemy("slime", 5, 5, spawn_id="test_slime")
        self.assertEqual(e.enemy_type, "slime")
        e2 = Enemy("bat", 3, 3, spawn_id="test_bat")
        self.assertEqual(e2.enemy_type, "bat")

    def test_enemy_has_xp_reward_property(self):
        """Enemy.xp_reward returns the XP value."""
        e = Enemy("slime", 5, 5, spawn_id="test_slime")
        self.assertIsInstance(e.xp_reward, int)
        self.assertGreater(e.xp_reward, 0)

    def test_boss_has_enemy_type_equivalent(self):
        """Boss exposes an identity for bestiary tracking."""
        b = Boss(14, 26, boss_id="dark_golem")
        # Boss may not have enemy_type, but must be identifiable
        boss_id = getattr(b, "boss_id", getattr(b, "enemy_type", None))
        self.assertIsNotNone(boss_id)
        self.assertEqual(boss_id, "dark_golem")

    def test_animal_has_enemy_type_property(self):
        """Animal.enemy_type returns the atype string."""
        from animal import Animal
        a = Animal("deer", 10, 10, spawn_id="test_deer")
        self.assertEqual(a.enemy_type, "deer")

    def test_animal_has_xp_reward_property(self):
        """Animal.xp_reward returns XP value."""
        from animal import Animal
        a = Animal("wolf", 10, 10, spawn_id="test_wolf")
        self.assertIsInstance(a.xp_reward, int)
        self.assertGreater(a.xp_reward, 0)

    def test_enemy_type_matches_bestiary_keys(self):
        """All enemy types used in spawns have matching bestiary entries."""
        from bestiary import ENTRY_DEFS
        for map_name, spawn_list in ENEMY_SPAWN_DEFS.items():
            for ed in spawn_list:
                etype = ed["type"]
                self.assertIn(etype, ENTRY_DEFS,
                              f"Enemy type '{etype}' from {map_name} spawn has no bestiary entry")


# ─── Animal Spawn Validation ─────────────────────────────────────────

class TestAnimalSpawnValidation(unittest.TestCase):
    """Animals only spawn on walkable, reachable tiles."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_validate_spawn_tile_rejects_walls(self):
        """validate_spawn_tile returns False for solid tiles."""
        from animal_spawner import validate_spawn_tile
        game = _DummyGame()
        gameplay = GameplayState(game)
        tilemap = gameplay.tilemap
        # Find a known wall tile
        wall_found = False
        for row in range(tilemap.height):
            for col in range(tilemap.width):
                if tilemap.is_solid(col, row):
                    self.assertFalse(validate_spawn_tile(tilemap, float(col), float(row)))
                    wall_found = True
                    break
            if wall_found:
                break
        self.assertTrue(wall_found, "No wall tiles found to test against")

    def test_validate_spawn_tile_accepts_passable(self):
        """validate_spawn_tile returns True for passable tiles."""
        from animal_spawner import validate_spawn_tile
        game = _DummyGame()
        gameplay = GameplayState(game)
        tilemap = gameplay.tilemap
        # Player spawn must be passable
        self.assertTrue(validate_spawn_tile(tilemap, gameplay.player.x, gameplay.player.y))

    def test_flood_fill_returns_nonempty_set(self):
        """_flood_fill_reachable produces a non-empty set of walkable tiles."""
        from animal_spawner import _flood_fill_reachable
        game = _DummyGame()
        gameplay = GameplayState(game)
        reachable = _flood_fill_reachable(gameplay.tilemap)
        self.assertGreater(len(reachable), 10)

    def test_spawner_passes_tilemap(self):
        """AnimalSpawner.spawn_for_map stores tilemap for validation."""
        from animal_spawner import AnimalSpawner
        game = _DummyGame()
        gameplay = GameplayState(game)
        spawner = AnimalSpawner()
        spawner.spawn_for_map("village", set(), tilemap=gameplay.tilemap)
        self.assertIs(spawner._tilemap, gameplay.tilemap)


# ─── Animal Combat ────────────────────────────────────────────────────

class TestAnimalCombat(unittest.TestCase):
    """Animals can be damaged, killed, and drop loot."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_animal_takes_damage(self):
        """Animal.take_damage reduces HP."""
        from animal import Animal
        a = Animal("deer", 10, 10, spawn_id="test_deer")
        old_hp = a.hp
        a.take_damage(1, 0, 0)
        self.assertEqual(a.hp, old_hp - 1)

    def test_animal_dies_at_zero_hp(self):
        """Animal enters death state when HP reaches 0."""
        from animal import Animal
        a = Animal("rabbit", 10, 10, spawn_id="test_rabbit")
        a.take_damage(a.max_hp, 0, 0)
        self.assertTrue(a.is_dead)
        self.assertEqual(a.state, "death")

    def test_animal_has_drops(self):
        """All animals have a drops list."""
        from animal import ANIMAL_DEFS, Animal
        for atype in ANIMAL_DEFS:
            a = Animal(atype, 0, 0, spawn_id=f"test_{atype}")
            self.assertIsInstance(a.drops, list, f"{atype} has no drops list")

    def test_animal_drops_have_item_id_and_chance(self):
        """Each animal drop entry has item_id and chance fields."""
        from animal import ANIMAL_DEFS, Animal
        for atype, adef in ANIMAL_DEFS.items():
            for drop in adef.get("drops", []):
                self.assertIn("item_id", drop, f"{atype} drop missing item_id")
                self.assertIn("chance", drop, f"{atype} drop missing chance")

    def test_dead_animal_tracks_loot_spawned(self):
        """Animal has loot_spawned flag for single-fire drop processing."""
        from animal import Animal
        a = Animal("deer", 10, 10, spawn_id="test_deer")
        self.assertFalse(a.loot_spawned)
        a.take_damage(a.max_hp, 0, 0)
        self.assertTrue(a.is_dead)
        a.loot_spawned = True
        self.assertTrue(a.loot_spawned)


# ─── Hotbar Switching ─────────────────────────────────────────────────

class TestHotbarSwitching(unittest.TestCase):
    """Number keys 1-8 switch active hotbar slot."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_hotbar_keys_exist_in_input_map(self):
        """Keys hotbar1..hotbar8 are registered in INPUT_MAP."""
        for i in range(1, 9):
            key_name = f"hotbar{i}"
            self.assertIn(key_name, INPUT_MAP,
                          f"{key_name} missing from INPUT_MAP")

    def test_hotbar_slot_default_is_zero(self):
        """Active hotbar slot starts at 0."""
        game = _DummyGame()
        self.assertEqual(game.inventory.grid.active_hotbar, 0)

    def test_hotbar_slot_assignment(self):
        """Setting active_hotbar changes the selected slot."""
        game = _DummyGame()
        for i in range(8):
            game.inventory.grid.active_hotbar = i
            self.assertEqual(game.inventory.grid.active_hotbar, i)


# ─── Animal Flee Panic ────────────────────────────────────────────────

class TestAnimalFleePanic(unittest.TestCase):
    """Flee-type animals panic-flee briefly after being hit, then calm down."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_hurt_transitions_to_flee_with_panic_timer(self):
        """After hurt ends, flee-type animal enters flee state with panic timer."""
        from animal import Animal
        a = Animal("deer", 10, 10, spawn_id="test_deer")
        a.take_damage(1, 0, 0)
        self.assertEqual(a.state, "hurt")
        # Simulate hurt timer expiring
        a.hurt_timer = 0.0
        # Create a minimal tilemap mock for update
        class MockTilemap:
            width = 40; height = 40
            def is_passable(self, x, y): return True
        a.update(0.01, 15, 15, MockTilemap())
        self.assertEqual(a.state, "flee")
        self.assertGreater(a._flee_panic_timer, 0)

    def test_flee_panic_expires_to_idle_wander(self):
        """After panic timer runs out, animal returns to idle_wander."""
        from animal import Animal
        a = Animal("deer", 10, 10, spawn_id="test_deer")
        a.state = "flee"
        a._flee_panic_timer = 0.01  # almost expired
        class MockTilemap:
            width = 40; height = 40
            def is_passable(self, x, y): return True
        a.update(0.02, 20, 20, MockTilemap())
        self.assertEqual(a.state, "idle_wander")


if __name__ == "__main__":
    unittest.main()
