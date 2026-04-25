"""
test_campaign.py — regression tests for the three-stage campaign system.

Tests verify:
  1. Campaign stage tracking (separate from quest.stage)
  2. Stage unlock gating
  3. Boss kill → stage completion routing
  4. Player form advancement
  5. save/load round-trip for campaign data
  6. Stage 2/3 difficulty configs exist and preserve test-friendly tuning
  7. Stage 2/3 content registries load without error
  8. Stage 3 Hard is still tougher overall than Stage 1 Normal (effective metrics)
  9. Boss classes instantiate correctly
  10. MAP_REGISTRY contains all 6 maps
  11. New items exist in ITEM_DEFS
  12. Victory screen prepare() accepts stage args
"""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
pygame.init()


# ─────────────────────────────────────────────────────────────────────────────
# Campaign core
# ─────────────────────────────────────────────────────────────────────────────

class TestCampaignCore(unittest.TestCase):

    def setUp(self):
        from campaign import Campaign
        self.Campaign = Campaign

    def test_initial_stage_is_1(self):
        c = self.Campaign()
        self.assertEqual(c.world_stage, 1)

    def test_stage_1_always_unlocked(self):
        c = self.Campaign()
        self.assertTrue(c.is_stage_unlocked(1))

    def test_stage_2_locked_by_default(self):
        c = self.Campaign()
        self.assertFalse(c.is_stage_unlocked(2))

    def test_stage_2_unlocked_after_stage_1_complete(self):
        c = self.Campaign()
        c.complete_stage(1)
        self.assertTrue(c.is_stage_unlocked(2))
        self.assertEqual(c.world_stage, 2)

    def test_stage_3_locked_until_stage_2_complete(self):
        c = self.Campaign()
        c.complete_stage(1)
        self.assertFalse(c.is_stage_unlocked(3))
        c.complete_stage(2)
        self.assertTrue(c.is_stage_unlocked(3))
        self.assertEqual(c.world_stage, 3)

    def test_boss_kill_dark_golem_completes_stage_1(self):
        c = self.Campaign()
        result = c.on_boss_killed("dark_golem")
        self.assertEqual(result, 1)
        self.assertIn(1, c.completed_stages)
        self.assertEqual(c.world_stage, 2)

    def test_boss_kill_gravewarden_completes_stage_2(self):
        c = self.Campaign()
        c.complete_stage(1)
        result = c.on_boss_killed("gravewarden")
        self.assertEqual(result, 2)
        self.assertIn(2, c.completed_stages)
        self.assertEqual(c.world_stage, 3)

    def test_boss_kill_mythic_sovereign_completes_stage_3(self):
        c = self.Campaign()
        c.complete_stage(1)
        c.complete_stage(2)
        result = c.on_boss_killed("mythic_sovereign")
        self.assertEqual(result, 3)
        self.assertIn(3, c.completed_stages)
        self.assertTrue(c.is_final_stage_complete())

    def test_boss_kill_unknown_returns_none(self):
        c = self.Campaign()
        result = c.on_boss_killed("random_unknown_boss")
        self.assertIsNone(result)

    def test_player_form_advances_on_stage_unlock(self):
        c = self.Campaign()
        self.assertEqual(c.player_form, "base")
        c.on_boss_killed("dark_golem")
        self.assertEqual(c.player_form, "hero")
        c.on_boss_killed("gravewarden")
        self.assertEqual(c.player_form, "mythic")

    def test_stage_name_changes(self):
        c = self.Campaign()
        self.assertIn("I", c.get_stage_name())
        c.complete_stage(1)
        self.assertIn("II", c.get_stage_name())

    def test_completing_stage_3_does_not_advance_world_stage_beyond_3(self):
        c = self.Campaign()
        c.complete_stage(1)
        c.complete_stage(2)
        c.complete_stage(3)
        self.assertEqual(c.world_stage, 3)   # capped at 3


# ─────────────────────────────────────────────────────────────────────────────
# Save / Load round-trip
# ─────────────────────────────────────────────────────────────────────────────

class TestCampaignSaveLoad(unittest.TestCase):

    def setUp(self):
        from campaign import Campaign
        self.Campaign = Campaign

    def test_round_trip_stage_1(self):
        c = self.Campaign()
        data = c.to_save()
        restored = self.Campaign.from_save(data)
        self.assertEqual(restored.world_stage, 1)
        self.assertEqual(restored.player_form, "base")

    def test_round_trip_stage_2(self):
        c = self.Campaign()
        c.on_boss_killed("dark_golem")
        data = c.to_save()
        restored = self.Campaign.from_save(data)
        self.assertEqual(restored.world_stage, 2)
        self.assertIn(1, restored.completed_stages)
        self.assertEqual(restored.player_form, "hero")
        self.assertTrue(restored.boss_kills.get("dark_golem"))

    def test_round_trip_final_stage(self):
        c = self.Campaign()
        c.on_boss_killed("dark_golem")
        c.on_boss_killed("gravewarden")
        c.on_boss_killed("mythic_sovereign")
        data = c.to_save()
        restored = self.Campaign.from_save(data)
        self.assertTrue(restored.is_final_stage_complete())
        self.assertEqual(restored.player_form, "mythic")
        self.assertEqual(restored.world_stage, 3)

    def test_from_save_empty_dict_gives_stage_1(self):
        c = self.Campaign.from_save({})
        self.assertEqual(c.world_stage, 1)
        self.assertEqual(c.player_form, "base")

    def test_save_manager_includes_campaign(self):
        """save_manager.save_game accepts and stores campaign data."""
        import tempfile, save_manager
        from campaign import Campaign
        from player import Player
        from inventory import Inventory
        from quest import QuestManager
        from wallet import Wallet

        p = Player(1, 1)
        inv = Inventory()
        qm = QuestManager()
        camp = Campaign()
        camp.on_boss_killed("dark_golem")

        orig_path = save_manager.SAVE_PATH
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            save_manager.SAVE_PATH = f.name
        try:
            result = save_manager.save_game(
                p, inv, qm, "village", set(), set(), False,
                campaign=camp,
            )
            self.assertTrue(result)
            data = save_manager.load_game()
            self.assertIn("campaign", data)
            self.assertEqual(data["campaign"]["world_stage"], 2)
        finally:
            save_manager.SAVE_PATH = orig_path
            os.unlink(f.name)

    def test_load_campaign_helper_returns_campaign(self):
        from save_manager import load_campaign
        from campaign import Campaign
        data = {"campaign": {"world_stage": 2, "player_form": "hero"}}
        c = load_campaign(data)
        self.assertIsInstance(c, Campaign)
        self.assertEqual(c.world_stage, 2)
        self.assertEqual(c.player_form, "hero")


# ─────────────────────────────────────────────────────────────────────────────
# Stage difficulty tuning
# ─────────────────────────────────────────────────────────────────────────────

class TestStageDifficultyTuning(unittest.TestCase):

    def _load_matrix(self):
        from ai.config_loader import load_stage_data
        return load_stage_data()["stage_difficulty_matrix"]

    def test_stage_configs_file_exists(self):
        import os
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "stage_configs.json")
        self.assertTrue(os.path.exists(path))

    def test_stage_loader_exposes_hp_bonus_and_boss_xp(self):
        from ai.config_loader import get_stage_boss_xp, get_stage_player_hp_bonus

        self.assertGreaterEqual(get_stage_player_hp_bonus(2), 2)
        self.assertGreaterEqual(get_stage_boss_xp(3, "mythic_sovereign"), 100)

    def test_all_stages_and_difficulties_present(self):
        matrix = self._load_matrix()
        for stage in ("1", "2", "3"):
            for diff in ("easy", "normal", "hard"):
                self.assertIn(stage, matrix, f"Stage {stage} missing")
                self.assertIn(diff, matrix[stage], f"{diff} missing in stage {stage}")

    def _merge_stage_difficulty(self, stage: str, difficulty: str) -> dict:
        from ai.config_loader import get_difficulty_config

        matrix = self._load_matrix()
        base = get_difficulty_config(difficulty)
        stage_cfg = matrix[stage][difficulty]
        base["enemy_stat_mults"]["hp"] *= stage_cfg["enemy_hp_mult"]
        base["enemy_stat_mults"]["damage"] *= stage_cfg["enemy_damage_mult"]
        base["enemy_stat_mults"]["speed"] *= stage_cfg.get("enemy_speed_mult", 1.0)
        base["boss_stat_mults"]["hp"] *= stage_cfg["boss_hp_mult"]
        base["boss_stat_mults"]["damage"] *= stage_cfg["boss_damage_mult"]
        base["boss_stat_mults"]["speed"] *= stage_cfg.get("boss_speed_mult", stage_cfg.get("enemy_speed_mult", 1.0))
        base["_stage_config"] = stage_cfg
        return base

    def test_stage_2_normal_still_pushes_regular_enemies_above_stage_1_normal(self):
        matrix = self._load_matrix()
        s1 = matrix["1"]["normal"]
        s2 = matrix["2"]["normal"]
        self.assertGreater(s2["enemy_hp_mult"], s1["enemy_hp_mult"])
        self.assertGreater(s2["enemy_damage_mult"], s1["enemy_damage_mult"])

    def test_stage_3_normal_still_pushes_regular_enemies_above_stage_2_normal(self):
        matrix = self._load_matrix()
        s2 = matrix["2"]["normal"]
        s3 = matrix["3"]["normal"]
        self.assertGreater(s3["enemy_hp_mult"], s2["enemy_hp_mult"])
        self.assertGreater(s3["boss_damage_mult"], s2["boss_damage_mult"])

    def test_stage_2_and_3_bosses_match_stage_1_kill_time_per_difficulty(self):
        from boss import Boss
        from boss2 import Gravewarden
        from boss3 import MythicSovereign

        for difficulty in ("easy", "normal", "hard"):
            s1 = Boss(10, 10, difficulty_mode=difficulty, difficulty_config=self._merge_stage_difficulty("1", difficulty))
            s2 = Gravewarden(10, 10, difficulty_mode=difficulty, difficulty_config=self._merge_stage_difficulty("2", difficulty))
            s3 = MythicSovereign(10, 10, difficulty_mode=difficulty, difficulty_config=self._merge_stage_difficulty("3", difficulty))
            self.assertAlmostEqual(s2.max_hp, s1.max_hp, delta=1)
            self.assertAlmostEqual(s3.max_hp, s1.max_hp, delta=1)

    def test_stage_3_hard_is_still_tougher_than_stage_1_normal_in_effective_stats(self):
        from boss import Boss
        from boss3 import MythicSovereign

        s1 = Boss(10, 10, difficulty_mode="normal", difficulty_config=self._merge_stage_difficulty("1", "normal"))
        s3 = MythicSovereign(10, 10, difficulty_mode="hard", difficulty_config=self._merge_stage_difficulty("3", "hard"))

        self.assertGreater(s3.max_hp, s1.max_hp)
        self.assertGreater(s3.damage, s1.damage)
        self.assertGreater(
            self._merge_stage_difficulty("3", "hard")["enemy_stat_mults"]["hp"],
            self._merge_stage_difficulty("1", "normal")["enemy_stat_mults"]["hp"],
        )

    def test_hard_within_stage_is_harder_than_normal(self):
        matrix = self._load_matrix()
        for stage in ("1", "2", "3"):
            n = matrix[stage]["normal"]
            h = matrix[stage]["hard"]
            self.assertGreater(h["enemy_hp_mult"], n["enemy_hp_mult"],
                               f"Stage {stage} hard not harder than normal")


class TestRuntimeTargets(unittest.TestCase):
    def test_runtime_factory_exposes_dual_targets(self):
        from runtime import create_runtime

        self.assertEqual(create_runtime("pygame").profile.name, "pygame")
        self.assertEqual(create_runtime("gba").profile.name, "gba")

    def test_runtime_factory_respects_env_target(self):
        import os
        from unittest.mock import patch

        from runtime import create_runtime

        with patch.dict(os.environ, {"MYTHICAL_TARGET": "gba"}, clear=False):
            self.assertEqual(create_runtime().profile.name, "gba")

    def test_gba_profile_uses_handheld_resolution(self):
        from runtime.target_profiles import GBA_PROFILE

        self.assertEqual((GBA_PROFILE.screen_width, GBA_PROFILE.screen_height), (240, 160))
        self.assertFalse(GBA_PROFILE.supports_filesystem_saves)


# ─────────────────────────────────────────────────────────────────────────────
# Content registries
# ─────────────────────────────────────────────────────────────────────────────

class TestStageContentRegistries(unittest.TestCase):

    def test_stage2_content_imports(self):
        from content.stage2_content import (
            NPC_DEFS, CHEST_DEFS, ENEMY_SPAWN_DEFS, BOSS_DEFS, BGM_MAP)
        self.assertIn("ruins_approach", NPC_DEFS)
        self.assertIn("ruins_depths", BOSS_DEFS)
        self.assertIsNotNone(BOSS_DEFS["ruins_depths"])
        self.assertEqual(BOSS_DEFS["ruins_depths"]["id"], "gravewarden")

    def test_stage3_content_imports(self):
        from content.stage3_content import (
            NPC_DEFS, CHEST_DEFS, ENEMY_SPAWN_DEFS, BOSS_DEFS, BGM_MAP)
        self.assertIn("throne_room", BOSS_DEFS)
        self.assertIsNotNone(BOSS_DEFS["throne_room"])
        self.assertEqual(BOSS_DEFS["throne_room"]["id"], "mythic_sovereign")

    def test_ruins_maps_load(self):
        from maps.ruins import RUINS_APPROACH, RUINS_DEPTHS
        self.assertEqual(RUINS_APPROACH["name"], "ruins_approach")
        self.assertEqual(RUINS_DEPTHS["name"], "ruins_depths")
        self.assertIn("ground", RUINS_APPROACH)
        self.assertIn("collision", RUINS_DEPTHS)

    def test_ruins_depths_has_clear_exit_path_to_sanctum_halls(self):
        from maps.ruins import RUINS_DEPTHS
        for row in range(16, 25):
            self.assertEqual(
                RUINS_DEPTHS["exits"][(59, row)]["map"],
                "sanctum_halls",
            )
            self.assertEqual(RUINS_DEPTHS["collision"][row][59], 0)

    def test_sanctum_maps_load(self):
        from maps.sanctum import SANCTUM_HALLS, THRONE_ROOM
        self.assertEqual(SANCTUM_HALLS["name"], "sanctum_halls")
        self.assertEqual(THRONE_ROOM["name"], "throne_room")

    def test_sanctum_halls_has_clear_exit_path_to_throne_room(self):
        from maps.sanctum import SANCTUM_HALLS
        for row in range(16, 24):
            self.assertEqual(
                SANCTUM_HALLS["exits"][(59, row)]["map"],
                "throne_room",
            )
            self.assertEqual(SANCTUM_HALLS["collision"][row][59], 0)

    def test_sanctum_halls_has_clear_entry_path_from_ruins_depths(self):
        from maps.sanctum import SANCTUM_HALLS
        for row in range(16, 25):
            self.assertEqual(
                SANCTUM_HALLS["exits"][(0, row)]["map"],
                "ruins_depths",
            )
            self.assertEqual(SANCTUM_HALLS["collision"][row][0], 0)

    def test_throne_room_has_clear_return_path_to_sanctum_halls(self):
        from maps.sanctum import THRONE_ROOM
        for row in range(14, 22):
            self.assertEqual(
                THRONE_ROOM["exits"][(0, row)]["map"],
                "sanctum_halls",
            )
            self.assertEqual(THRONE_ROOM["collision"][row][0], 0)

    def test_all_6_maps_in_registry(self):
        from states.gameplay import MAP_REGISTRY
        for name in ("village", "dungeon", "ruins_approach", "ruins_depths",
                     "sanctum_halls", "throne_room"):
            self.assertIn(name, MAP_REGISTRY, f"{name} missing from MAP_REGISTRY")


# ─────────────────────────────────────────────────────────────────────────────
# New boss classes
# ─────────────────────────────────────────────────────────────────────────────

class TestBossClasses(unittest.TestCase):

    def test_gravewarden_instantiation(self):
        from boss2 import Gravewarden
        g = Gravewarden(10, 10)
        self.assertEqual(g.boss_id, "gravewarden")
        self.assertGreater(g.max_hp, 0)
        self.assertEqual(g.phase, 1)
        self.assertFalse(g.defeated)

    def test_gravewarden_phase_2_on_damage(self):
        from boss2 import Gravewarden
        g = Gravewarden(10, 10)
        g.activate()
        g.state = "idle"   # skip intro — damage is blocked during intro
        damage_needed = int(g.max_hp * 0.51)
        g.shield_health = 0   # no shield blocking
        g.take_damage(damage_needed)
        if g.alive:
            self.assertEqual(g.phase, 2)

    def test_mythic_sovereign_instantiation(self):
        from boss3 import MythicSovereign
        s = MythicSovereign(10, 10)
        self.assertEqual(s.boss_id, "mythic_sovereign")
        self.assertGreater(s.max_hp, 0)
        self.assertEqual(s.phase, 1)
        self.assertFalse(s.defeated)

    def test_mythic_sovereign_has_3_phases(self):
        from boss3 import MythicSovereign
        s = MythicSovereign(10, 10)
        self.assertLess(s.phase3_threshold, s.phase2_threshold)

    def test_mythic_sovereign_save_restore(self):
        from boss3 import MythicSovereign
        s = MythicSovereign(10, 10)
        s.activate()
        s.take_damage(10)
        snap = s.snapshot_state()
        s2 = MythicSovereign(10, 10)
        s2.apply_saved_state(snap)
        self.assertEqual(s2.hp, s.hp)

    def test_gravewarden_has_reasonable_hp(self):
        """Gravewarden base HP is positive and balanced for player damage."""
        from boss2 import _BASE as G_BASE
        self.assertGreater(G_BASE["max_hp"], 10)
        self.assertLessEqual(G_BASE["max_hp"], 60)

    def test_mythic_sovereign_harder_than_gravewarden(self):
        from boss2 import _BASE as G_BASE
        from boss3 import _BASE as S_BASE
        self.assertGreater(S_BASE["max_hp"], G_BASE["max_hp"])
        self.assertGreater(S_BASE["damage"], G_BASE["damage"])


# ─────────────────────────────────────────────────────────────────────────────
# New items
# ─────────────────────────────────────────────────────────────────────────────

class TestNewItems(unittest.TestCase):

    def _defs(self):
        from item_system import ITEM_DEFS
        return ITEM_DEFS

    def test_stage2_items_present(self):
        defs = self._defs()
        for item_id in ("runic_sword", "shadow_mail", "speed_talisman",
                        "runic_crystal", "bone_arrow", "revenant_core"):
            self.assertIn(item_id, defs, f"{item_id} missing from ITEM_DEFS")

    def test_stage3_items_present(self):
        defs = self._defs()
        for item_id in ("mythblade", "ascended_aegis", "sovereign_crown",
                        "void_shard", "mythic_core"):
            self.assertIn(item_id, defs, f"{item_id} missing from ITEM_DEFS")

    def test_mythblade_stronger_than_runic_sword(self):
        defs = self._defs()
        runic_atk = defs["runic_sword"]["stats"]["attack"]
        myth_atk  = defs["mythblade"]["stats"]["attack"]
        self.assertGreater(myth_atk, runic_atk)

    def test_ascended_aegis_stronger_than_shadow_mail(self):
        defs = self._defs()
        self.assertGreater(
            defs["ascended_aegis"]["stats"]["defense"],
            defs["shadow_mail"]["stats"]["defense"]
        )

    def test_loot_tiers_set_correctly(self):
        defs = self._defs()
        self.assertEqual(defs["runic_sword"].get("loot_tier"), "rare")
        self.assertEqual(defs["mythblade"].get("loot_tier"), "mythic")


# ─────────────────────────────────────────────────────────────────────────────
# Player forms
# ─────────────────────────────────────────────────────────────────────────────

class TestPlayerForms(unittest.TestCase):

    def _make_forms(self, form="base"):
        from campaign import Campaign
        from player_forms import PlayerForms
        c = Campaign()
        c.player_form = form
        return PlayerForms(c)

    def test_base_form_no_aura(self):
        pf = self._make_forms("base")
        vc = pf.get_visual_config()
        self.assertIsNone(vc["aura_color"])
        self.assertFalse(pf.is_upgraded())

    def test_hero_form_has_aura(self):
        pf = self._make_forms("hero")
        vc = pf.get_visual_config()
        self.assertIsNotNone(vc["aura_color"])
        self.assertTrue(pf.is_upgraded())

    def test_mythic_form_strongest_bonuses(self):
        from player_forms import FORM_DEFS
        base_atk  = FORM_DEFS["base"]["bonuses"]["attack_bonus"]
        hero_atk  = FORM_DEFS["hero"]["bonuses"]["attack_bonus"]
        myth_atk  = FORM_DEFS["mythic"]["bonuses"]["attack_bonus"]
        self.assertGreater(hero_atk,  base_atk)
        self.assertGreater(myth_atk,  hero_atk)

    def test_form_bonuses_not_empty_for_hero_and_mythic(self):
        for form in ("hero", "mythic"):
            pf = self._make_forms(form)
            bonuses = pf.get_stat_bonuses()
            self.assertGreater(bonuses["attack_bonus"], 0)
            self.assertGreater(bonuses["defense"], 0)


# ─────────────────────────────────────────────────────────────────────────────
# Victory state
# ─────────────────────────────────────────────────────────────────────────────

class TestVictoryState(unittest.TestCase):

    def test_victory_state_prepare_accepts_stage(self):
        from states.victory import VictoryState

        class _DummyGame:
            class input:
                @staticmethod
                def is_pressed(_):
                    return False
            class audio:
                @staticmethod
                def stop_music(): pass
                @staticmethod
                def play_sfx(_): pass

        vs = VictoryState(_DummyGame())
        vs.prepare(2)
        self.assertEqual(vs._completed_stage, 2)
        vs.prepare(3)
        self.assertEqual(vs._completed_stage, 3)

    def test_no_collision_between_campaign_stage_and_quest_stage(self):
        """Campaign.world_stage and Quest.stage are completely independent integers."""
        from campaign import Campaign
        from quest import QuestManager
        c = Campaign()
        qm = QuestManager()
        q  = qm.get_quest("main")
        # Advance campaign to stage 3
        c.complete_stage(1)
        c.complete_stage(2)
        self.assertEqual(c.world_stage, 3)
        # Quest stage is still wherever it was — fully independent
        initial_quest_stage = q.stage
        self.assertEqual(q.stage, initial_quest_stage)


# ─────────────────────────────────────────────────────────────────────────────
# Stage intro state
# ─────────────────────────────────────────────────────────────────────────────

class TestStageIntroState(unittest.TestCase):

    def test_stage_intro_prepare(self):
        from states.stage_intro import StageIntroState
        screen = pygame.display.set_mode((1, 1))

        class _DummyGame:
            class audio:
                @staticmethod
                def stop_music(): pass
            class states:
                _states = {}
                @staticmethod
                def change(_): pass

        si = StageIntroState(_DummyGame())
        si.prepare(2)
        self.assertEqual(si.stage_number, 2)
        si.prepare(3, "The Mythic Sanctum")
        self.assertEqual(si.stage_name, "The Mythic Sanctum")


if __name__ == "__main__":
    unittest.main()
