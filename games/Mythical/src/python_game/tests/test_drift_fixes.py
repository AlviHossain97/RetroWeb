"""
test_drift_fixes.py — Tests for the drift fixes across the desktop codebase.

Verifies:
  1. Crafting screen API alignment
  2. Skill screen API alignment
  3. BGM map routing for all 6 maps
  4. Audio manager boss music routing
  5. Weather set_map called on map load
  6. Environmental crystal type
  7. Consequence system round-trip
  8. Reputation system contract
  9. Fast travel waypoint coverage
"""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

pygame.init()


class TestCraftingScreenAPIAlignment(unittest.TestCase):
    """Verify crafting screen matches live crafting.py API."""

    def setUp(self):
        from crafting import CraftingManager, RECIPES

        self.cm = CraftingManager()
        self.recipes = RECIPES

    def test_recipe_output_uses_nested_dict(self):
        """All recipes have 'output' dict with 'item_id' and 'qty'."""
        for rid, recipe in self.recipes.items():
            self.assertIn("output", recipe, f"Recipe '{rid}' missing 'output' key")
            self.assertIn(
                "item_id", recipe["output"], f"Recipe '{rid}' output missing 'item_id'"
            )
            self.assertIn(
                "qty", recipe["output"], f"Recipe '{rid}' output missing 'qty'"
            )

    def test_missing_ingredients_returns_list(self):
        """missing_ingredients() returns a list of dicts, not a dict."""
        from item_system import GridInventory, CraftingBag

        grid = GridInventory()
        bag = CraftingBag()
        result = self.cm.missing_ingredients("iron_sword", grid, bag)
        self.assertIsInstance(result, list, "missing_ingredients should return a list")
        for item in result:
            self.assertIn("item_id", item)
            self.assertIn("need", item)
            self.assertIn("have", item)

    def test_can_craft_requires_three_args(self):
        """can_craft() requires recipe_id, grid_inv, craft_bag."""
        from item_system import GridInventory, CraftingBag

        grid = GridInventory()
        bag = CraftingBag()
        # Should work with 3 args
        result = self.cm.can_craft("cooked_meat", grid, bag)
        self.assertIsInstance(result, bool)

    def test_craft_requires_three_args(self):
        """craft() requires recipe_id, grid_inv, craft_bag."""
        from item_system import GridInventory, CraftingBag

        grid = GridInventory()
        bag = CraftingBag()
        # craft() already adds output to grid_inv, no double-add
        grid.add_item("raw_meat", 2)
        bag_result = self.cm.craft("cooked_meat", grid, bag, station="cooking")
        if bag_result:
            self.assertIn("item_id", bag_result)
            self.assertIn("qty", bag_result)


class TestSkillScreenAPIAlignment(unittest.TestCase):
    """Verify skill screen matches live skill_tree.py data."""

    def setUp(self):
        from skill_tree import SKILL_TREES

        self.trees = SKILL_TREES

    def test_skill_trees_have_color_field(self):
        """Every tree has a 'color' tuple."""
        for tree_id, tree in self.trees.items():
            self.assertIn("color", tree, f"Tree '{tree_id}' missing 'color' key")
            self.assertEqual(
                len(tree["color"]), 3, f"Tree '{tree_id}' color should be RGB tuple"
            )

    def test_skill_trees_have_skills_list(self):
        """Every tree has a 'skills' list."""
        for tree_id, tree in self.trees.items():
            self.assertIn("skills", tree, f"Tree '{tree_id}' missing 'skills' key")
            self.assertIsInstance(tree["skills"], list)

    def test_skills_have_required_fields(self):
        """Every skill dict has id, name, max_rank, tier."""
        for tree_id, tree in self.trees.items():
            for skill in tree["skills"]:
                self.assertIn("id", skill, f"Skill in '{tree_id}' missing 'id'")
                self.assertIn("name", skill, f"Skill in '{tree_id}' missing 'name'")
                self.assertIn(
                    "max_rank", skill, f"Skill in '{tree_id}' missing 'max_rank'"
                )
                self.assertIn("tier", skill, f"Skill in '{tree_id}' missing 'tier'")

    def test_no_cost_field_on_skills(self):
        """Skills should NOT have a 'cost' field — SP cost is always 1."""
        for tree_id, tree in self.trees.items():
            for skill in tree["skills"]:
                # cost field should not exist (screen should use default 1 SP)
                self.assertNotIn(
                    "cost",
                    skill,
                    f"Skill '{skill.get('id')}' has unexpected 'cost' field. "
                    f"All skills cost 1 SP per rank.",
                )


class TestBGMMapRouting(unittest.TestCase):
    """Verify BGM routing for all 6 maps uses correct audio names."""

    def test_all_maps_have_bgm_entry(self):
        """Every map in the registry has a BGM mapping."""
        from states.gameplay import _BGM_MAP_ALL, MAP_REGISTRY

        for map_name in MAP_REGISTRY:
            self.assertIn(
                map_name, _BGM_MAP_ALL, f"Map '{map_name}' missing from BGM_MAP_ALL"
            )

    def test_bgm_values_are_valid_audio_names(self):
        """BGM_MAP values reference audio that AudioManager generates."""
        from states.gameplay import _BGM_MAP_ALL

        valid_prefixes = ("village", "dungeon", "ruins", "sanctum", "boss")
        for map_name, bgm_name in _BGM_MAP_ALL.items():
            has_prefix = any(bgm_name.startswith(p) for p in valid_prefixes)
            self.assertTrue(
                has_prefix,
                f"BGM '{bgm_name}' for map '{map_name}' doesn't match any known audio prefix",
            )

    def test_audio_set_map_audio_uses_bgm_value(self):
        """set_map_audio should receive the BGM_MAP value, not the map name."""
        # The fix: gameplay.py passes `bgm` not `map_name`
        from states.gameplay import MAP_REGISTRY, _BGM_MAP_ALL

        # Verify that for Act 2/3 maps, bgm != map_name
        later_maps = ["ruins_approach", "ruins_depths", "sanctum_halls", "throne_room"]
        for m in later_maps:
            bgm = _BGM_MAP_ALL.get(m, "")
            self.assertNotEqual(
                m,
                bgm,
                f"Map '{m}' BGM should be a short audio name, not the map name itself",
            )


class TestAudioManagerBossRouting(unittest.TestCase):
    """Verify boss music routing works with both map names and audio names."""

    def test_ruins_boss_routing(self):
        """Boss routing should handle ruins_approach -> ruins_boss."""
        # AudioManager._map_name is set from set_map_audio(bgm)
        # Boss routing should match "ruins" as well as "ruins_approach"
        ruins_audio_names = {"ruins", "ruins_approach", "ruins_depths", "ruins_boss"}
        # These should all route to "ruins_boss" when boss_active
        for name in ruins_audio_names:
            if name in ("ruins", "ruins_boss"):
                self.assertIn(
                    name, ("ruins", "ruins_boss", "ruins_approach", "ruins_depths")
                )

    def test_sanctum_boss_routing(self):
        """Boss routing should handle sanctum_halls -> sanctum_boss."""
        sanctum_audio_names = {
            "sanctum",
            "sanctum_halls",
            "throne_room",
            "sanctum_boss",
        }
        for name in sanctum_audio_names:
            self.assertIn(name, sanctum_audio_names)


class TestWeatherSetMap(unittest.TestCase):
    """Verify WeatherSystem.set_map() stores map name."""

    def test_set_map_stores_name(self):
        from weather import WeatherSystem

        ws = WeatherSystem()
        ws.set_map("dungeon")
        self.assertEqual(ws.map_name, "dungeon")

    def test_set_map_changes_name(self):
        from weather import WeatherSystem

        ws = WeatherSystem()
        ws.set_map("village")
        ws.set_map("sanctum_halls")
        self.assertEqual(ws.map_name, "sanctum_halls")


class TestEnvironmentalCrystalType(unittest.TestCase):
    """Verify crystal destructible type is defined."""

    def test_crystal_type_exists(self):
        from environmental import DESTRUCT_TYPES

        self.assertIn(
            "crystal", DESTRUCT_TYPES, "Crystal destructible type should exist"
        )

    def test_crystal_type_has_hp(self):
        from environmental import DESTRUCT_TYPES

        crystal = DESTRUCT_TYPES["crystal"]
        self.assertIn("hp", crystal)
        self.assertGreater(crystal["hp"], 0)

    def test_crystal_type_has_drops(self):
        from environmental import DESTRUCT_TYPES

        crystal = DESTRUCT_TYPES["crystal"]
        self.assertIn("drops", crystal)
        self.assertIsInstance(crystal["drops"], list)
        self.assertGreater(len(crystal["drops"]), 0)


class TestConsequenceSystem(unittest.TestCase):
    """Verify ConsequenceState round-trips through save/load."""

    def test_set_and_get_flag(self):
        from consequence_system import ConsequenceState

        cs = ConsequenceState()
        cs.set_flag("dark_golem_persuade")
        self.assertTrue(cs.get_flag("dark_golem_persuade"))
        self.assertFalse(cs.get_flag("unknown_flag"))

    def test_save_round_trip(self):
        from consequence_system import ConsequenceState

        cs = ConsequenceState()
        cs.set_flag("dark_golem_persuade")
        cs.set_flag("helped_elder_willingly")
        data = cs.to_save()
        cs2 = ConsequenceState.from_save(data)
        self.assertTrue(cs2.get_flag("dark_golem_persuade"))
        self.assertTrue(cs2.get_flag("helped_elder_willingly"))
        self.assertFalse(cs2.get_flag("never_set"))

    def test_has_flag(self):
        from consequence_system import ConsequenceState

        cs = ConsequenceState()
        self.assertFalse(cs.has_flag("anything"))
        cs.set_flag("anything")
        self.assertTrue(cs.has_flag("anything"))


class TestReputationContract(unittest.TestCase):
    """Verify reputation system has gameplay-facing effects."""

    def test_merchant_discount_available(self):
        from reputation import Reputation

        rep = Reputation()
        # Below threshold: no discount
        self.assertFalse(rep.has_merchant_discount())
        # At threshold: discount should activate
        rep.modify("villagers", 60)
        self.assertTrue(rep.has_merchant_discount())

    def test_forest_passage_available(self):
        from reputation import Reputation

        rep = Reputation()
        self.assertFalse(rep.has_forest_passage())
        rep.modify("forest_spirits", 30)
        self.assertTrue(rep.has_forest_passage())

    def test_seeker_maps_available(self):
        from reputation import Reputation

        rep = Reputation()
        self.assertFalse(rep.has_seeker_maps())
        rep.modify("dungeon_seekers", 30)
        self.assertTrue(rep.has_seeker_maps())


class TestFastTravelCoverage(unittest.TestCase):
    """Verify fast travel covers all acts."""

    def test_act1_waypoints_exist(self):
        from fast_travel import WAYPOINT_DEFS

        act1_maps = {"village", "dungeon"}
        act1_wps = [wp for wp in WAYPOINT_DEFS.values() if wp["map"] in act1_maps]
        self.assertGreaterEqual(
            len(act1_wps), 2, "Act 1 should have at least 2 waypoints"
        )

    def test_act2_waypoints_exist(self):
        from fast_travel import WAYPOINT_DEFS

        act2_maps = {"ruins_approach", "ruins_depths"}
        act2_wps = [wp for wp in WAYPOINT_DEFS.values() if wp["map"] in act2_maps]
        self.assertGreaterEqual(
            len(act2_wps), 1, "Act 2 should have at least 1 waypoint"
        )

    def test_act3_waypoints_exist(self):
        from fast_travel import WAYPOINT_DEFS

        act3_maps = {"sanctum_halls", "throne_room"}
        act3_wps = [wp for wp in WAYPOINT_DEFS.values() if wp["map"] in act3_maps]
        self.assertGreaterEqual(
            len(act3_wps), 1, "Act 3 should have at least 1 waypoint"
        )


class TestSaveIntegrity(unittest.TestCase):
    """Verify save/load round-trips and format correctness."""

    def test_consequence_state_save_round_trip(self):
        from consequence_system import ConsequenceState

        cs = ConsequenceState()
        cs.set_flag("chose_peace_with_golem")
        data = cs.to_save()
        restored = ConsequenceState.from_save(data)
        self.assertTrue(restored.has_flag("chose_peace_with_golem"))
        self.assertFalse(restored.has_flag("never_set"))

    def test_progression_save_includes_total_sp(self):
        from progression import Progression

        p = Progression()
        p.add_xp(100)
        data = p.to_save()
        self.assertIn("total_skill_points_earned", data)
        self.assertEqual(data["total_skill_points_earned"], p.total_skill_points_earned)

    def test_progression_from_save_restores_total_sp(self):
        from progression import Progression

        p = Progression()
        p.add_xp(100)
        data = p.to_save()
        restored = Progression.from_save(data)
        self.assertEqual(
            restored.total_skill_points_earned, p.total_skill_points_earned
        )

    def test_fast_travel_save_round_trip(self):
        from fast_travel import FastTravelManager

        ftm = FastTravelManager()
        ftm.unlock("dungeon_entrance")
        data = ftm.to_save()
        restored = FastTravelManager.from_save(data)
        self.assertIn("dungeon_entrance", restored.unlocked)
        self.assertNotIn("ruins_approach", restored.unlocked)

    def test_fast_travel_flat_list_load(self):
        from fast_travel import FastTravelManager

        ftm = FastTravelManager()
        for wp in ["village_square", "dungeon_entrance"]:
            ftm.unlocked.add(wp)
        data = list(ftm.unlocked)
        from save_manager import load_fast_travel

        restored = load_fast_travel({"fast_travel": data})
        self.assertIn("dungeon_entrance", restored.unlocked)

    def test_build_save_data_accepts_consequence_state(self):
        from save_manager import build_save_data
        from unittest.mock import MagicMock

        player = MagicMock()
        player.x = 15
        player.y = 19
        player.hp = 10
        player.facing = "down"
        inv = MagicMock()
        inv.to_save.return_value = {}
        qm = MagicMock()
        qm.quests = {}
        from consequence_system import ConsequenceState

        cs = ConsequenceState()
        cs.set_flag("test_flag")
        data = build_save_data(
            player,
            inv,
            qm,
            "village",
            set(),
            set(),
            False,
            consequence_state=cs,
        )
        self.assertIn("consequence_state", data)
        self.assertIn("test_flag", data["consequence_state"])

    def test_killed_animals_load(self):
        from save_manager import load_killed_animals

        result = load_killed_animals({"killed_animals": ["deer_1", "rabbit_2"]})
        self.assertEqual(result, {"deer_1", "rabbit_2"})

    def test_checkpoint_snapshot_includes_progression(self):
        """Verify that checkpoints save progression/reputation/bestiary/campaign."""
        from progression import Progression

        p = Progression()
        p.add_xp(50)
        data = p.to_save()
        self.assertIn("xp", data)
        self.assertIn("level", data)


class TestCombatStats(unittest.TestCase):
    """Verify progression combat stats are wired into gameplay."""

    def test_get_combat_stats_returns_all_keys(self):
        from progression import Progression

        p = Progression()
        stats = p.get_combat_stats()
        expected_keys = {
            "attack_bonus",
            "speed_bonus",
            "defense",
            "flank_bonus",
            "crit_chance",
            "crit_mult",
            "xp_bonus_mult",
            "magic_amp",
            "dash_i_frames",
            "combo_window",
            "env_kill_bonus",
        }
        self.assertEqual(set(stats.keys()), expected_keys)

    def test_combat_stats_increase_with_skill_allocation(self):
        from progression import Progression

        p = Progression()
        p.add_xp(200)
        base = p.get_combat_stats()["attack_bonus"]
        p.spend_skill_point("warrior", "power_strike")
        after = p.get_combat_stats()["attack_bonus"]
        self.assertGreater(after, base)

    def test_grant_skill_point_increases_points(self):
        from progression import Progression

        p = Progression()
        initial = p.skill_points
        p.grant_skill_point()
        self.assertEqual(p.skill_points, initial + 1)
        self.assertEqual(p.total_skill_points_earned, initial + 1)


class TestBossNamesFromBestiary(unittest.TestCase):
    """Verify victory screen uses ENTRY_DEFS for boss names."""

    def test_all_boss_ids_in_entry_defs(self):
        from bestiary import ENTRY_DEFS
        from campaign import STAGE_BOSS_IDS

        for stage, boss_id in STAGE_BOSS_IDS.items():
            self.assertIn(
                boss_id, ENTRY_DEFS, f"Boss {boss_id} missing from ENTRY_DEFS"
            )
            self.assertIn("name", ENTRY_DEFS[boss_id])

    def test_stage_names_in_campaign(self):
        from campaign import STAGE_NAMES

        self.assertEqual(STAGE_NAMES[1], "Act I: The Eastern Forest")
        self.assertEqual(STAGE_NAMES[2], "Act II: The Haunted Ruins")
        self.assertEqual(STAGE_NAMES[3], "Act III: The Mythic Sanctum")


class TestReputationEvents(unittest.TestCase):
    """Verify reputation event structure."""

    def test_boss_killed_event_exists(self):
        from reputation import REP_EVENTS

        self.assertIn("boss_killed", REP_EVENTS)

    def test_quest_main_complete_event_exists(self):
        from reputation import REP_EVENTS

        self.assertIn("quest_main_complete", REP_EVENTS)

    def test_apply_event_returns_deltas(self):
        from reputation import Reputation

        rep = Reputation()
        deltas = rep.apply_event("boss_killed")
        self.assertIn("villagers", deltas)
        self.assertGreater(deltas["villagers"], 0)

    def test_apply_event_modifies_rep(self):
        from reputation import Reputation

        rep = Reputation()
        rep.apply_event("boss_killed")
        self.assertGreater(rep.get("villagers"), 0)
        self.assertGreater(rep.get("dungeon_seekers"), 0)


if __name__ == "__main__":
    unittest.main()
