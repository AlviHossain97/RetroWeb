"""
Tests for GBA runtime modules - fixed-point, memory budgets, asset pipeline.

These tests verify the new GBA port infrastructure works correctly.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Suppress pygame display/audio for headless testing
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cpp_game_tools"))

import pygame

pygame.init()

from runtime.fixed_point import (
    FP_ONE,
    FixedVec2,
    angle_from_degrees,
    cos,
    distance_fixed,
    div,
    from_int,
    mul,
    normalize_fixed,
    polar_offset_fixed,
    sin,
    sqrt,
    to_fixed,
    to_float,
    to_int,
)
from runtime.memory_budget import (
    DESKTOP_BUDGET,
    GBA_BUDGET,
    MemoryTracker,
    estimate_save_size,
    get_tracker,
    set_budget,
    verify_save_fit,
)


class TestFixedPoint(unittest.TestCase):
    """Test fixed-point arithmetic."""

    def test_conversion_to_fixed(self):
        """Float to fixed conversion."""
        self.assertEqual(to_fixed(1.0), FP_ONE)  # 256
        self.assertEqual(to_fixed(0.5), FP_ONE // 2)  # 128
        self.assertEqual(to_fixed(2.0), FP_ONE * 2)  # 512

    def test_conversion_to_float(self):
        """Fixed to float conversion."""
        self.assertAlmostEqual(to_float(FP_ONE), 1.0, places=3)
        self.assertAlmostEqual(to_float(FP_ONE // 2), 0.5, places=3)

    def test_multiplication(self):
        """Fixed-point multiplication."""
        a = to_fixed(2.0)  # 512
        b = to_fixed(3.0)  # 768
        result = mul(a, b)  # Should be 6.0
        self.assertAlmostEqual(to_float(result), 6.0, places=3)

    def test_division(self):
        """Fixed-point division."""
        a = to_fixed(6.0)
        b = to_fixed(2.0)
        result = div(a, b)  # Should be 3.0
        self.assertAlmostEqual(to_float(result), 3.0, places=3)

    def test_sqrt(self):
        """Fixed-point square root."""
        value = to_fixed(16.0)
        result = sqrt(value)
        self.assertAlmostEqual(to_float(result), 4.0, delta=0.1)

    def test_sqrt_zero(self):
        """Square root of zero."""
        self.assertEqual(sqrt(0), 0)

    def test_distance(self):
        """Distance calculation."""
        # 3-4-5 triangle
        x1, y1 = from_int(0), from_int(0)
        x2, y2 = from_int(3), from_int(4)
        dist = distance_fixed(x1, y1, x2, y2)
        self.assertAlmostEqual(to_float(dist), 5.0, delta=0.1)

    def test_normalize(self):
        """Vector normalization."""
        dx, dy = from_int(3), from_int(4)
        nx, ny, length = normalize_fixed(dx, dy)
        self.assertAlmostEqual(to_float(length), 5.0, delta=0.1)
        # Normalized vector should have length 1.0
        len_check = sqrt(mul(nx, nx) + mul(ny, ny))
        self.assertAlmostEqual(to_float(len_check), 1.0, delta=0.05)

    def test_trig_lookup_sin(self):
        """Sine lookup table."""
        # sin(0) = 0
        self.assertAlmostEqual(to_float(sin(0)), 0.0, delta=0.01)
        # sin(90) ≈ 1 (at index 64 in 256-entry table)
        self.assertAlmostEqual(to_float(sin(64)), 1.0, delta=0.01)

    def test_trig_lookup_cos(self):
        """Cosine lookup table."""
        # cos(0) = 1
        self.assertAlmostEqual(to_float(cos(0)), 1.0, delta=0.01)
        # cos(90) ≈ 0
        self.assertAlmostEqual(to_float(cos(64)), 0.0, delta=0.01)

    def test_angle_from_degrees(self):
        """Degree to table index conversion."""
        self.assertEqual(angle_from_degrees(0), 0)
        self.assertEqual(angle_from_degrees(90), 64)  # 256 / 4
        self.assertEqual(angle_from_degrees(180), 128)
        self.assertEqual(angle_from_degrees(360), 0)  # Wraps around

    def test_polar_offset(self):
        """Polar coordinate conversion."""
        # 0 degrees, magnitude 10
        dx, dy = polar_offset_fixed(0, from_int(10))
        self.assertAlmostEqual(to_float(dx), 10.0, delta=0.1)
        self.assertAlmostEqual(to_float(dy), 0.0, delta=0.1)


class TestFixedVec2(unittest.TestCase):
    """Test FixedVec2 class."""

    def test_initialization(self):
        """Create FixedVec2 from floats."""
        v = FixedVec2(10.5, 20.25)
        self.assertAlmostEqual(v.xf, 10.5, places=3)
        self.assertAlmostEqual(v.yf, 20.25, places=3)

    def test_integer_conversion(self):
        """Get integer pixel positions."""
        v = FixedVec2(10.9, 20.1)  # Should truncate
        self.assertEqual(v.xi, 10)
        self.assertEqual(v.yi, 20)

    def test_addition(self):
        """Vector addition."""
        a = FixedVec2(10, 20)
        b = FixedVec2(5, 5)
        c = a + b
        self.assertAlmostEqual(c.xf, 15.0, places=3)
        self.assertAlmostEqual(c.yf, 25.0, places=3)

    def test_subtraction(self):
        """Vector subtraction."""
        a = FixedVec2(10, 20)
        b = FixedVec2(3, 4)
        c = a - b
        self.assertAlmostEqual(c.xf, 7.0, places=3)
        self.assertAlmostEqual(c.yf, 16.0, places=3)

    def test_scalar_multiply(self):
        """Scalar multiplication."""
        v = FixedVec2(10, 20)
        scalar = to_fixed(2.0)
        result = v * scalar
        self.assertAlmostEqual(result.xf, 20.0, places=3)
        self.assertAlmostEqual(result.yf, 40.0, places=3)

    def test_length(self):
        """Vector length."""
        # 3-4-5 triangle
        v = FixedVec2(3, 4)
        self.assertAlmostEqual(to_float(v.length()), 5.0, delta=0.1)

    def test_normalized(self):
        """Vector normalization."""
        v = FixedVec2(10, 0)
        n = v.normalized()
        # Fixed-point has precision loss, allow larger tolerance
        self.assertAlmostEqual(to_float(n.length()), 1.0, delta=0.15)

    def test_distance_to(self):
        """Distance between vectors."""
        a = FixedVec2(0, 0)
        b = FixedVec2(3, 4)
        self.assertAlmostEqual(to_float(a.distance_to(b)), 5.0, delta=0.1)

    def test_to_tile(self):
        """Convert to tile coordinates."""
        v = FixedVec2(64, 96)  # Assuming 32px tiles: tile (2, 3)
        tile_size = to_fixed(32)
        tx, ty = v.to_tile(tile_size)
        self.assertEqual(to_int(tx), 2)
        self.assertEqual(to_int(ty), 3)

    def test_from_tile(self):
        """Create from tile coordinates."""
        tile_size = to_fixed(32)
        v = FixedVec2.from_tile(2, 3, tile_size)
        self.assertAlmostEqual(v.xf, 64.0, places=2)  # 2 * 32
        self.assertAlmostEqual(v.yf, 96.0, places=2)  # 3 * 32


class TestMemoryBudget(unittest.TestCase):
    """Test memory budget tracking."""

    def test_gba_budget_limits(self):
        """GBA budget has realistic limits."""
        self.assertEqual(GBA_BUDGET.max_sprites, 128)  # Hardware OAM
        self.assertEqual(GBA_BUDGET.max_entities, 64)
        self.assertEqual(GBA_BUDGET.max_particles, 256)
        self.assertEqual(GBA_BUDGET.max_map_width, 64)
        self.assertEqual(GBA_BUDGET.max_map_height, 64)
        self.assertEqual(GBA_BUDGET.max_save_size, 65536)  # 64 KB SRAM

    def test_desktop_budget_is_larger(self):
        """Desktop budget allows more resources."""
        self.assertGreater(DESKTOP_BUDGET.max_entities, GBA_BUDGET.max_entities)
        self.assertGreater(DESKTOP_BUDGET.max_particles, GBA_BUDGET.max_particles)

    def test_memory_tracker_entity_count(self):
        """Track entity count against budget."""
        tracker = MemoryTracker(GBA_BUDGET)
        self.assertTrue(tracker.check_entity_count(32))  # Under budget
        self.assertTrue(tracker.check_entity_count(64))  # At budget
        self.assertFalse(tracker.check_entity_count(65))  # Over budget
        self.assertEqual(tracker.peak_entities, 65)  # Still tracked

    def test_memory_tracker_particle_count(self):
        """Track particle count against budget."""
        tracker = MemoryTracker(GBA_BUDGET)
        self.assertTrue(tracker.check_particle_count(128))
        self.assertFalse(tracker.check_particle_count(300))

    def test_memory_tracker_map_size(self):
        """Track map dimensions."""
        tracker = MemoryTracker(GBA_BUDGET)
        self.assertTrue(tracker.check_map_size(32, 32))
        self.assertTrue(tracker.check_map_size(64, 64))
        self.assertFalse(tracker.check_map_size(128, 64))

    def test_save_size_estimate(self):
        """Save size estimation."""
        size = estimate_save_size()
        self.assertGreater(size, 0)
        self.assertLess(size, GBA_BUDGET.max_save_size)  # Should fit

    def test_verify_save_fit(self):
        """Verify save fits GBA SRAM."""
        fits, size = verify_save_fit()
        self.assertTrue(fits)
        self.assertGreater(size, 0)
        self.assertLess(size, GBA_BUDGET.max_save_size)

    def test_tracker_warnings(self):
        """Tracker collects warnings."""
        tracker = MemoryTracker(GBA_BUDGET)
        tracker.check_entity_count(100)  # Over budget
        warnings = tracker.get_warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("exceeds budget", warnings[0])

    def test_tracker_report(self):
        """Generate usage report."""
        tracker = MemoryTracker(GBA_BUDGET)
        tracker.check_entity_count(32)
        tracker.check_particle_count(64)
        report = tracker.report()
        self.assertEqual(report["budget"], "gba")
        self.assertEqual(report["peak_entities"], 32)
        self.assertLess(report["entity_pct"], 100)


class TestBudgetSwitching(unittest.TestCase):
    """Test switching between budgets."""

    def test_set_budget_gba(self):
        """Switch to GBA budget."""
        set_budget("gba")
        tracker = get_tracker()
        self.assertEqual(tracker.budget.name, "gba")
        self.assertEqual(tracker.budget.max_entities, 64)

    def test_set_budget_desktop(self):
        """Switch to desktop budget."""
        set_budget("desktop")
        tracker = get_tracker()
        self.assertEqual(tracker.budget.name, "desktop")
        self.assertGreater(tracker.budget.max_entities, 64)


class TestSavePacking(unittest.TestCase):
    """Test binary save format."""

    def test_round_trip(self):
        """Save data survives round-trip."""
        from runtime.asset_pipeline import SavePacker

        packer = SavePacker()
        test_data = {
            "player": {"x": 10.5, "y": 20.25, "hp": 5, "max_hp": 6, "facing": "left"},
            "inventory": {"slots": [{"item_id": 1, "count": 5}]},
            "quest_stages": {"main": {"stage": 2, "complete": False}},
            "progression": {"xp": 150, "level": 3, "skill_points": 4},
            "campaign": {"world_stage": 2, "completed_stages": [1]},
        }

        packed = packer.pack_save(test_data)
        unpacked = packer.unpack_save(packed)

        self.assertIsNotNone(unpacked)
        self.assertAlmostEqual(unpacked["player"]["x"], 10.5, places=2)
        self.assertEqual(unpacked["campaign"]["world_stage"], 2)

    def test_invalid_magic_fails(self):
        """Invalid magic bytes rejected."""
        from runtime.asset_pipeline import SavePacker

        packer = SavePacker()
        invalid_data = b"XXXX" + b"\x00" * 20
        result = packer.unpack_save(invalid_data)
        self.assertIsNone(result)

    def test_short_data_fails(self):
        """Too-short data rejected."""
        from runtime.asset_pipeline import SavePacker

        packer = SavePacker()
        result = packer.unpack_save(b"MYTH")
        self.assertIsNone(result)


class TestGBAROMTableGenerator(unittest.TestCase):
    """Test generated ROM tables."""

    def test_item_table_uses_stable_ids_and_item_categories(self):
        """Item rows keep source order and preserve category/rarity metadata."""
        from generate_gba_rom_tables import CGenerator, ItemTableGenerator

        item_defs = {
            "old_sword": {
                "category": "weapon",
                "stack_max": 1,
                "stats": {"attack": 2},
            },
            "swift_charm": {
                "category": "accessory",
                "stack_max": 1,
                "loot_tier": "mythic",
                "stats": {"speed": 1.8},
            },
            "health_potion": {
                "category": "consumable",
                "stack_max": 64,
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            generator = ItemTableGenerator(CGenerator(Path(tmp)))
            c_content, h_content = generator.generate(item_defs)

        self.assertIn("ITEM_OLD_SWORD = 0", h_content)
        self.assertIn("ITEM_SWIFT_CHARM = 1", h_content)
        self.assertIn("#define ITEM_TYPE_ACCESSORY 5", h_content)
        self.assertIn("/* old_sword */ {0, 0, 0, 0, 2, 1}", c_content)
        self.assertIn("/* swift_charm */ {1, 5, 5, 0, 2, 1}", c_content)
        self.assertIn("/* health_potion */ {2, 2, 0, 0, 0, 64}", c_content)

    def test_tilemap_collision_size_rounds_up(self):
        """Bit-packed collision arrays reserve enough bytes for odd tile counts."""
        from generate_gba_rom_tables import CGenerator, TilemapGenerator

        map_data = {
            "odd_room": {
                "width": 3,
                "height": 3,
                "ground": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
                "collision": [[False, False, False], [False, True, False], [False, False, True]],
            }
        }

        with tempfile.TemporaryDirectory() as tmp:
            generator = TilemapGenerator(CGenerator(Path(tmp)))
            c_content, h_content = generator.generate(map_data)

        self.assertIn("extern const u8 odd_room_collision[2];", h_content)
        self.assertIn("const u8 odd_room_collision[2] = {", c_content)


class TestGBACompatLayer(unittest.TestCase):
    """Test GBA compatibility layer."""

    def test_gba_compat_mode_context(self):
        """GBACompatMode can be used as context manager."""
        from runtime.gba_compat import GBACompatMode

        # Should not raise
        with GBACompatMode(enable_limits=False, show_warnings=False):
            pass

    def test_gba_entity_creation(self):
        """Create GBA-compatible entity."""
        from runtime.gba_compat import GBAEntity

        ent = GBAEntity(5.0, 10.0)
        self.assertEqual(ent.tile_x, 0)  # 160 / 32 = 5, but at origin
        self.assertEqual(ent.tile_y, 0)

    def test_gba_entity_velocity(self):
        """GBA entity moves with velocity."""
        from runtime.gba_compat import GBAEntity

        ent = GBAEntity(0, 0)
        ent.set_velocity(2.0, 1.0)
        ent.update(FP_ONE)  # 1 second at 60fps
        self.assertGreater(ent.pixel_x, 0)
        self.assertGreater(ent.pixel_y, 0)

    def test_gba_oam_manager_allocation(self):
        """OAM manager allocates sprite entries."""
        from runtime.gba_compat import GBAOAMManager

        oam = GBAOAMManager()
        obj_id = oam.allocate(100, 100, 0)
        self.assertIsNotNone(obj_id)
        self.assertEqual(oam.get_used_count(), 1)

    def test_gba_oam_max_sprites(self):
        """OAM respects 128 sprite limit."""
        from runtime.gba_compat import GBAOAMManager

        oam = GBAOAMManager()
        for i in range(128):
            obj_id = oam.allocate(i, i, i)
            self.assertIsNotNone(obj_id)

        # 129th allocation should fail
        obj_id = oam.allocate(0, 0, 0)
        self.assertIsNone(obj_id)

    def test_distance_check(self):
        """Integer distance check."""
        from runtime.gba_compat import gba_distance_check

        # 3-4-5 triangle, radius 5
        self.assertTrue(gba_distance_check(0, 0, 3, 4, 5))
        # Just outside radius
        self.assertFalse(gba_distance_check(0, 0, 10, 10, 5))

    def test_circle_collision(self):
        """Integer circle collision."""
        from runtime.gba_compat import gba_circle_collision

        # Overlapping circles
        self.assertTrue(gba_circle_collision(0, 0, 5, 8, 0, 5))
        # Non-overlapping
        self.assertFalse(gba_circle_collision(0, 0, 5, 20, 0, 5))


if __name__ == "__main__":
    unittest.main()
