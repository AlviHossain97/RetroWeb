"""
Memory budget definitions for GBA port constraints.

GBA hardware specs:
- 384 KB total RAM (32 KB fast IWRAM + 256 KB EWRAM + 96 KB VRAM)
- Video RAM: 96 KB (64 KB VRAM + 32 KB OAM + palette)
- Save: 64-512 KB SRAM/Flash

These budgets guide the Python implementation toward GBA-compatible sizes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class MemoryBudget:
    """Defines memory constraints for a target platform."""

    name: str

    # Total RAM budgets (in bytes)
    max_ram_total: int
    max_vram_tiles: int  # Number of 8x8 tiles
    max_vram_palettes: int  # Number of 16-color palettes
    max_sprites: int  # OAM entries

    # Entity budgets
    max_entities: int
    max_particles: int
    max_map_width: int  # tiles
    max_map_height: int  # tiles

    # Save budget
    max_save_size: int  # SRAM size

    # Notes
    notes: str = ""


# GBA hardware limits
GBA_BUDGET = MemoryBudget(
    name="gba",
    max_ram_total=262144,  # 256 KB EWRAM for game state
    max_vram_tiles=1024,  # 1KB tiles (8x8@4bpp = 32 bytes each)
    max_vram_palettes=16,  # 16 palettes of 16 colors
    max_sprites=128,  # Hardware OAM limit
    max_entities=64,  # Player + enemies + animals + items
    max_particles=256,  # Visual effects
    max_map_width=64,  # Maps tile to hardware BG
    max_map_height=64,
    max_save_size=65536,  # 64 KB SRAM minimum
    notes="GBA hardware constraints: 256KB EWRAM, 96KB VRAM, 128 hardware sprites",
)

# Desktop development (unlimited for prototyping)
DESKTOP_BUDGET = MemoryBudget(
    name="desktop",
    max_ram_total=268435456,  # 256 MB (arbitrary)
    max_vram_tiles=65536,
    max_vram_palettes=256,
    max_sprites=1024,
    max_entities=512,
    max_particles=2048,
    max_map_width=256,
    max_map_height=256,
    max_save_size=1048576,  # 1 MB
    notes="Desktop development - no hard limits",
)


class MemoryTracker:
    """Track memory usage against budgets (development tool)."""

    def __init__(self, budget: MemoryBudget = GBA_BUDGET):
        self.budget = budget
        self.peak_entities = 0
        self.peak_particles = 0
        self.peak_map_tiles = 0
        self._warnings: List[str] = []

    def check_entity_count(self, count: int) -> bool:
        """Check if entity count is within budget."""
        self.peak_entities = max(self.peak_entities, count)
        if count > self.budget.max_entities:
            self._warnings.append(
                f"Entity count {count} exceeds budget {self.budget.max_entities}"
            )
            return False
        return True

    def check_particle_count(self, count: int) -> bool:
        """Check if particle count is within budget."""
        self.peak_particles = max(self.peak_particles, count)
        if count > self.budget.max_particles:
            self._warnings.append(
                f"Particle count {count} exceeds budget {self.budget.max_particles}"
            )
            return False
        return True

    def check_map_size(self, width: int, height: int) -> bool:
        """Check if map dimensions are within budget."""
        self.peak_map_tiles = max(self.peak_map_tiles, width * height)
        if width > self.budget.max_map_width or height > self.budget.max_map_height:
            self._warnings.append(
                f"Map size {width}x{height} exceeds budget "
                f"{self.budget.max_map_width}x{self.budget.max_map_height}"
            )
            return False
        return True

    def check_save_size(self, size: int) -> bool:
        """Check if save data fits in SRAM."""
        if size > self.budget.max_save_size:
            self._warnings.append(
                f"Save size {size} exceeds budget {self.budget.max_save_size}"
            )
            return False
        return True

    def get_warnings(self) -> List[str]:
        """Get and clear warning messages."""
        warnings = self._warnings.copy()
        self._warnings.clear()
        return warnings

    def report(self) -> Dict[str, any]:
        """Generate memory usage report."""
        return {
            "budget": self.budget.name,
            "peak_entities": self.peak_entities,
            "entity_budget": self.budget.max_entities,
            "entity_pct": (self.peak_entities / self.budget.max_entities) * 100,
            "peak_particles": self.peak_particles,
            "particle_budget": self.budget.max_particles,
            "particle_pct": (self.peak_particles / self.budget.max_particles) * 100,
            "peak_map_tiles": self.peak_map_tiles,
            "max_map_tiles": self.budget.max_map_width * self.budget.max_map_height,
            "warnings": len(self._warnings),
        }


# Global tracker for development
_active_tracker: MemoryTracker | None = None


def get_tracker() -> MemoryTracker:
    """Get or create the global memory tracker."""
    global _active_tracker
    if _active_tracker is None:
        _active_tracker = MemoryTracker()
    return _active_tracker


def set_budget(budget_name: str) -> None:
    """Switch active budget (gba or desktop)."""
    global _active_tracker
    budget = GBA_BUDGET if budget_name == "gba" else DESKTOP_BUDGET
    _active_tracker = MemoryTracker(budget)


# Size estimates for save data (in bytes) - for planning
SAVE_SIZE_ESTIMATES = {
    "player_state": 64,  # HP, position, facing, etc
    "inventory_slot": 8,  # Item ID + count + durability/etc
    "inventory_grid": 6 * 4 * 8,  # 24 slots
    "equipment": 6 * 8,  # 6 equipment slots
    "crafting_bag": 16 * 8,  # 16 crafting slots
    "hotbar": 8 * 8,  # 8 hotbar slots
    "quest_stage": 8,  # Quest ID + stage + complete flag
    "map_discoveries": 64 * 64 // 8,  # Bitmask for explored tiles
    "bestiary_entry": 16,  # ID + kills + discovered flags
    "reputation_faction": 4,  # Faction ID + value
    "consequence_flag": 8,  # Key + value
    "fast_travel_point": 4,  # Point ID + unlocked flag
    "weather_state": 8,
    "campaign_state": 32,
    "progression": 32,  # XP, level, skill points
    "skill_allocations": 20 * 2,  # 20 skills, 2 bytes each
}


def estimate_save_size(
    num_quests: int = 10,
    num_bestiary: int = 20,
    num_factions: int = 5,
    num_consequences: int = 20,
    num_fast_travel: int = 8,
) -> int:
    """Estimate total save size based on content counts."""
    total = SAVE_SIZE_ESTIMATES["player_state"]
    total += SAVE_SIZE_ESTIMATES["inventory_grid"]
    total += SAVE_SIZE_ESTIMATES["equipment"]
    total += SAVE_SIZE_ESTIMATES["crafting_bag"]
    total += SAVE_SIZE_ESTIMATES["hotbar"]
    total += num_quests * SAVE_SIZE_ESTIMATES["quest_stage"]
    total += SAVE_SIZE_ESTIMATES["map_discoveries"] * 6  # 6 maps
    total += num_bestiary * SAVE_SIZE_ESTIMATES["bestiary_entry"]
    total += num_factions * SAVE_SIZE_ESTIMATES["reputation_faction"]
    total += num_consequences * SAVE_SIZE_ESTIMATES["consequence_flag"]
    total += num_fast_travel * SAVE_SIZE_ESTIMATES["fast_travel_point"]
    total += SAVE_SIZE_ESTIMATES["weather_state"]
    total += SAVE_SIZE_ESTIMATES["campaign_state"]
    total += SAVE_SIZE_ESTIMATES["progression"]
    total += SAVE_SIZE_ESTIMATES["skill_allocations"]
    total += 256  # Overhead, header, checksum, padding
    return total


# Verify current save design fits in GBA SRAM
def verify_save_fit() -> tuple[bool, int]:
    """Check if current save design fits GBA SRAM budget."""
    estimated = estimate_save_size()
    fits = estimated <= GBA_BUDGET.max_save_size
    return fits, estimated
