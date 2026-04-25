"""
item_system.py — Minecraft-style inventory: grid slots, stacking, equipment, tooltips.

Architecture:
  ItemStack      — (item_id, quantity) stored in a single grid slot.
  GridInventory  — 6×4 = 24 slots + HOTBAR_SIZE hotbar alias into row-0.
  EquipmentSlots — dual armor + accessory slots with stat application.
  CraftingBag    — separate 4×3 bag for crafting materials.

Backward compat: the legacy Inventory class in inventory.py is kept unchanged;
gameplay code that needs the full system uses GridInventory instead.
"""
from __future__ import annotations
import math
from typing import Optional

import pygame

from settings import INV_COLS, INV_ROWS, HOTBAR_SIZE

# ─────────────────────────────────────────────────────────────────────────────
# ITEM DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────
# Categories: "key_item", "weapon", "armor", "accessory", "consumable", "material"
# stack_max: 1 = unstackable (equipment / key items), otherwise stack limit.
# equip_slot: None | "weapon" | "armor" | "accessory"
# stats: flat modifiers applied when equipped.
# effect: string tag resolved by gameplay layer (e.g. "enable_dash").
# use_effect: string tag for consumable on-use action.

ITEM_DEFS: dict[str, dict] = {
    # ── Quest / key items (unstackable, no equip slot) ──────────────────
    "old_sword":   {"name": "Old Sword",        "category": "weapon",    "stack_max": 1,
                    "desc": "A rusty but effective blade. Required to attack.",
                    "icon": "⚔",  "equip_slot": "weapon",
                    "stats": {"attack": 1},  "effect": "enable_attacks"},
    "forest_key":  {"name": "Forest Key",       "category": "key_item",  "stack_max": 1,
                    "desc": "Opens the gate to the eastern forest.",
                    "icon": "🗝",  "equip_slot": None},
    "herb":        {"name": "Healing Herb",     "category": "key_item",  "stack_max": 1,
                    "desc": "A fragrant herb with restorative properties.",
                    "icon": "🌿",  "equip_slot": None},
    "amulet":      {"name": "Elder Amulet",     "category": "accessory", "stack_max": 1,
                    "desc": "Proof of the village's trust. Passively regenerates HP over time.",
                    "icon": "🔮",  "equip_slot": "accessory",
                    "stats": {"hp_regen": 0.002}, "effect": "hp_regen"},
    "mushroom":    {"name": "Glowing Mushroom", "category": "key_item",  "stack_max": 1,
                    "desc": "Pulses with faint blue light. Strange energy inside.",
                    "icon": "🍄",  "equip_slot": None},
    "letter":      {"name": "Sealed Letter",    "category": "key_item",  "stack_max": 1,
                    "desc": "A message from the Elder to an old friend.",
                    "icon": "✉",   "equip_slot": None},
    "cave_map":    {"name": "Cave Map",         "category": "key_item",  "stack_max": 1,
                    "desc": "A rough sketch of the cave layout.",
                    "icon": "🗺",  "equip_slot": None},
    "boss_key":    {"name": "Boss Key",         "category": "key_item",  "stack_max": 1,
                    "desc": "An ornate key found deep in the caves.",
                    "icon": "🔑",  "equip_slot": None},
    "crystal":     {"name": "Dark Crystal",     "category": "key_item",  "stack_max": 1,
                    "desc": "Pulses with an ominous energy.",
                    "icon": "💎",  "equip_slot": None},
    # ── Craftable / obtainable weapons ───────────────────────────────────
    "iron_sword":  {"name": "Iron Sword",       "category": "weapon",    "stack_max": 1,
                    "desc": "A well-forged iron blade. Wider swing arc.",
                    "icon": "⚔",  "equip_slot": "weapon",
                    "stats": {"attack": 2, "attack_range": 0.2}, "effect": "enable_attacks"},
    "shadow_blade":{"name": "Shadow Blade",     "category": "weapon",    "stack_max": 1,
                    "desc": "Forged from dungeon obsidian. Fast and deadly. Enables the Dash-Strike.",
                    "icon": "🗡",  "equip_slot": "weapon",
                    "stats": {"attack": 4, "speed": 0.3}, "effect": "enable_attacks,enable_dash_strike"},
    "fire_staff":  {"name": "Fire Staff",       "category": "weapon",    "stack_max": 1,
                    "desc": "Ranged fire projectile. Ignites enemies on hit.",
                    "icon": "🔥",  "equip_slot": "weapon",
                    # SYNERGY: Mage Ignite + Warrior Slam → Explosion (AoE)
                    "stats": {"attack": 3, "attack_range": 2.5}, "effect": "enable_fire_attack"},
    "ice_wand":    {"name": "Ice Wand",         "category": "weapon",    "stack_max": 1,
                    "desc": "Fires ice shards. Enemies hit are slowed.",
                    "icon": "❄",  "equip_slot": "weapon",
                    # SYNERGY: Mage Ice Slow + Rogue Backstab → guaranteed crit on frozen enemy
                    "stats": {"attack": 2, "attack_range": 2.0}, "effect": "enable_ice_attack"},
    # ── Armor ─────────────────────────────────────────────────────────────
    "leather_armor":{"name": "Leather Armor",  "category": "armor",     "stack_max": 1,
                     "desc": "Light protection. No movement penalty.",
                     "icon": "🛡",  "equip_slot": "armor",
                     "stats": {"defense": 1}},
    "iron_armor":  {"name": "Iron Armor",       "category": "armor",     "stack_max": 1,
                    "desc": "Heavy plate. Reduces damage taken significantly.",
                    "icon": "🛡",  "equip_slot": "armor",
                    "stats": {"defense": 3, "speed": -0.5}},
    "shadow_cloak":{"name": "Shadow Cloak",     "category": "armor",     "stack_max": 1,
                    "desc": "Dark leather cloak. Enables the Dash mechanic (Shift).",
                    "icon": "🌑",  "equip_slot": "armor",
                    # This armor directly UNLOCKS a new movement mechanic — not just stats.
                    # SYNERGY: Shadow Cloak + Rogue Evasion skill → 0.5-sec invulnerability on dash
                    "stats": {"defense": 1, "speed": 0.5}, "effect": "enable_dash"},
    "mage_robes":  {"name": "Mage Robes",       "category": "armor",     "stack_max": 1,
                    "desc": "Flows with arcane energy. Enhances magic weapons.",
                    "icon": "🔮",  "equip_slot": "armor",
                    # SYNERGY: Mage Robes + Fire Staff → fire damage doubled
                    "stats": {"defense": 0, "magic_amp": 1.5}, "effect": "amplify_magic"},
    # ── Accessories ───────────────────────────────────────────────────────
    "speed_ring":  {"name": "Swift Ring",       "category": "accessory", "stack_max": 1,
                    "desc": "A ring that quickens your step.",
                    "icon": "💍",  "equip_slot": "accessory",
                    "stats": {"speed": 1.0}},
    "hunters_necklace":{"name": "Hunter's Necklace","category":"accessory","stack_max":1,
                    "desc": "Grants +75% damage when flanking enemies.",
                    "icon": "📿",  "equip_slot": "accessory",
                    # SYNERGY: Hunter's Necklace + Rogue Flank skill = total +150% flank dmg
                    "stats": {"flank_bonus": 0.75}, "effect": "enhanced_flank"},
    # ── Consumables (stackable) ───────────────────────────────────────────
    "health_potion":{"name": "Health Potion",  "category": "consumable", "stack_max": 64,
                     "desc": "Instantly restores 1 full heart.",
                     "icon": "🧪",  "equip_slot": None, "use_effect": "heal_2"},
    "healing_orb": {"name": "Healing Orb",     "category": "consumable", "stack_max": 64,
                    "desc": "A glowing green orb dropped by monsters. Restores 1 heart.",
                    "icon": "💚",  "equip_slot": None, "use_effect": "heal_2"},
    "raw_meat":    {"name": "Raw Meat",         "category": "consumable", "stack_max": 64,
                    "desc": "Dropped by animals. Eat 2 pieces to restore half a heart.",
                    "icon": "🥩",  "equip_slot": None, "use_effect": "heal_1"},
    "cooked_meat": {"name": "Cooked Meat",      "category": "consumable", "stack_max": 64,
                    "desc": "Cooked over a fire. Restores half a heart per piece.",
                    "icon": "🍖",  "equip_slot": None, "use_effect": "heal_3"},
    "antidote":    {"name": "Antidote",         "category": "consumable", "stack_max": 64,
                    "desc": "Cures poison status.",
                    "icon": "💊",  "equip_slot": None, "use_effect": "cure_poison"},
    # ── Crafting materials (stackable, auto-sorted to crafting bag) ───────
    "animal_hide": {"name": "Animal Hide",      "category": "material",  "stack_max": 64,
                    "desc": "Tough hide from forest animals. Used in armor crafting.",
                    "icon": "🦔",  "equip_slot": None},
    "bones":       {"name": "Bone",             "category": "material",  "stack_max": 64,
                    "desc": "Skeletal remains. Used in crafting and brewing.",
                    "icon": "🦴",  "equip_slot": None},
    "crystal_shard":{"name":"Crystal Shard",   "category": "material",  "stack_max": 64,
                    "desc": "A fragment of raw crystal. Conducts magic energy.",
                    "icon": "💠",  "equip_slot": None},
    "forest_herbs":{"name": "Forest Herbs",    "category": "material",  "stack_max": 64,
                    "desc": "Gathered from herb nodes. Used in potions.",
                    "icon": "🌿",  "equip_slot": None},
    "mushroom_spore":{"name":"Mushroom Spore", "category": "material",  "stack_max": 64,
                    "desc": "Harvested from glowing mushrooms. Alchemical reagent.",
                    "icon": "🍄",  "equip_slot": None},
    "iron_ore":    {"name": "Iron Ore",         "category": "material",  "stack_max": 64,
                    "desc": "Mined from cave walls. Smelt into iron ingots.",
                    "icon": "⛏",  "equip_slot": None},
    "iron_ingot":  {"name": "Iron Ingot",       "category": "material",  "stack_max": 64,
                    "desc": "Smelted iron. Primary metal for weapons and armor.",
                    "icon": "🔩",  "equip_slot": None},
    "shadow_dust": {"name": "Shadow Dust",      "category": "material",  "stack_max": 64,
                    "desc": "Fine dark powder from shadow bats. Used in shadow gear.",
                    "icon": "✨",  "equip_slot": None},
    "fire_essence":{"name": "Fire Essence",     "category": "material",  "stack_max": 64,
                    "desc": "Condensed flame energy. Imbues weapons with fire.",
                    "icon": "🔥",  "equip_slot": None},
    # ── Lore / hidden items ───────────────────────────────────────────────
    "ancient_tome":{"name": "Ancient Tome",    "category": "key_item",  "stack_max": 1,
                    "desc": "Pages filled with forgotten runes. Unlocks a skill point.",
                    "icon": "📖",  "equip_slot": None, "use_effect": "grant_skill_point"},
    "lore_fragment":{"name":"Lore Fragment",   "category": "key_item",  "stack_max": 64,
                    "desc": "A shard of narrative history. Collect 5 for a secret reward.",
                    "icon": "📜",  "equip_slot": None},
    # ── Bows (ranged, consume bone_arrow ammo) ──────────────────────────────
    "hunters_bow":  {"name": "Hunter's Bow",     "category": "weapon",    "stack_max": 1,
                    "desc": "A sturdy recurve bow. Consumes bone arrows as ammo.",
                    "icon": "🏹",  "equip_slot": "weapon",
                    "stats": {"attack": 3, "attack_range": 3.5}, "effect": "enable_attacks,ranged_bow"},
    "runic_bow":   {"name": "Runic Bow",         "category": "weapon",    "stack_max": 1,
                    "desc": "Imbued with ruin-energy. Devastating at range. Consumes bone arrows.",
                    "loot_tier": "rare",
                    "icon": "🏹",  "equip_slot": "weapon",
                    "stats": {"attack": 5, "attack_range": 4.5}, "effect": "enable_attacks,ranged_bow"},
    # ── Stage 2 weapons & armor ──────────────────────────────────────────────
    "runic_sword":  {"name": "Runic Sword",     "category": "weapon",    "stack_max": 1,
                    "desc": "Forged from ruins-metal. Runic energy surges on each strike.",
                    "loot_tier": "rare",
                    "icon": "⚔",  "equip_slot": "weapon",
                    "stats": {"attack": 4, "attack_range": 0.3}, "effect": "enable_attacks,runic_strike"},
    "shadow_mail":  {"name": "Shadow Mail",     "category": "armor",     "stack_max": 1,
                    "desc": "Dark chainmail from the ruins. High protection, keeps mobility.",
                    "loot_tier": "rare",
                    "icon": "🛡",  "equip_slot": "armor",
                    "stats": {"defense": 4, "speed": -0.2}},
    "speed_talisman":{"name":"Speed Talisman",  "category": "accessory", "stack_max": 1,
                    "desc": "An enchanted rune-stone. Greatly increases movement speed.",
                    "loot_tier": "rare",
                    "icon": "💍",  "equip_slot": "accessory",
                    "stats": {"speed": 1.8, "flank_bonus": 0.20}},
    # ── Stage 2 materials & key items ────────────────────────────────────────
    "runic_crystal":{"name": "Runic Crystal",   "category": "material",  "stack_max": 64,
                    "desc": "Glows with ruin-energy. Weakens undead bosses when equipped.",
                    "loot_tier": "rare",
                    "icon": "💠",  "equip_slot": None},
    "bone_arrow":   {"name": "Bone Arrow",      "category": "material",  "stack_max": 64,
                    "desc": "Sharp arrow carved from ruins bones. Crafting ingredient.",
                    "loot_tier": "rare",
                    "icon": "🦴",  "equip_slot": None},
    "revenant_core":{"name": "Revenant Core",   "category": "key_item",  "stack_max": 1,
                    "desc": "The pulsing heart of the Gravewarden. Grants undead resistance.",
                    "loot_tier": "rare",
                    "icon": "💜",  "equip_slot": "accessory",
                    "stats": {"defense": 2, "hp_regen": 0.001}, "effect": "undead_resist"},
    # ── Stage 3 weapons & armor ──────────────────────────────────────────────
    "mythblade":    {"name": "Mythblade",        "category": "weapon",    "stack_max": 1,
                    "desc": "The legendary blade of the mortal realm. Blazing gold aura on every swing.",
                    "loot_tier": "mythic",
                    "icon": "⚔",  "equip_slot": "weapon",
                    "stats": {"attack": 7, "attack_range": 0.5, "crit_chance": 0.15},
                    "effect": "enable_attacks,mythic_strike"},
    "ascended_aegis":{"name":"Ascended Aegis",  "category": "armor",     "stack_max": 1,
                    "desc": "Armor of pure condensed light. Best protection in existence.",
                    "loot_tier": "mythic",
                    "icon": "🛡",  "equip_slot": "armor",
                    "stats": {"defense": 7, "speed": 0.0}},
    "sovereign_crown":{"name":"Sovereign Crown","category": "accessory", "stack_max": 1,
                    "desc": "The Mythic Sovereign's crown, repurposed. Amplifies all combat stats.",
                    "loot_tier": "mythic",
                    "icon": "👑",  "equip_slot": "accessory",
                    "stats": {"attack": 2, "defense": 2, "speed": 0.5, "crit_chance": 0.10},
                    "effect": "mythic_presence"},
    # ── Stage 3 materials & passive items ────────────────────────────────────
    "void_shard":   {"name": "Void Shard",       "category": "material",  "stack_max": 64,
                    "desc": "A fragment of the shattered sanctum. Radiates raw mythic energy.",
                    "loot_tier": "mythic",
                    "icon": "🔮",  "equip_slot": None},
    "mythic_core":  {"name": "Mythic Core",      "category": "key_item",  "stack_max": 1,
                    "desc": "The crystallised essence of mythic power. Unlocks all skill synergies.",
                    "loot_tier": "mythic",
                    "icon": "✨",  "equip_slot": "accessory",
                    "stats": {"attack": 1, "defense": 1, "crit_chance": 0.05},
                    "effect": "all_synergies"},
}

# Short lookup set for legacy key-item IDs used by existing quest system
LEGACY_KEY_ITEMS = {
    "old_sword", "forest_key", "herb", "amulet", "mushroom",
    "letter", "cave_map", "boss_key", "crystal",
}

# Which categories auto-route to the crafting bag when picked up
MATERIAL_CATEGORIES = {"material"}


# ─────────────────────────────────────────────────────────────────────────────
# ITEM STACK
# ─────────────────────────────────────────────────────────────────────────────

class ItemStack:
    """One slot's contents: an item ID and a quantity."""
    __slots__ = ("item_id", "qty")

    def __init__(self, item_id: str, qty: int = 1):
        self.item_id = item_id
        self.qty = max(1, int(qty))

    @property
    def definition(self) -> dict:
        return ITEM_DEFS.get(self.item_id, {"name": self.item_id, "category": "key_item",
                                             "stack_max": 1, "desc": "???", "icon": "?"})

    @property
    def max_stack(self) -> int:
        return self.definition.get("stack_max", 1)

    @property
    def is_full(self) -> bool:
        return self.qty >= self.max_stack

    def can_merge(self, other: "ItemStack") -> bool:
        return other.item_id == self.item_id and not self.is_full

    def add(self, amount: int) -> int:
        """Add amount, return overflow that didn't fit."""
        space = self.max_stack - self.qty
        added = min(space, amount)
        self.qty += added
        return amount - added

    def split(self) -> "ItemStack":
        """Split stack in half; returns the taken half."""
        taken = max(1, self.qty // 2)
        self.qty -= taken
        return ItemStack(self.item_id, taken)

    def __repr__(self):
        return f"ItemStack({self.item_id!r}, {self.qty})"


# ─────────────────────────────────────────────────────────────────────────────
# GRID INVENTORY
# ─────────────────────────────────────────────────────────────────────────────

class GridInventory:
    """
    Full grid-based inventory: INV_COLS × INV_ROWS slots.
    Row 0 is the hotbar (HOTBAR_SIZE visible slots).
    Slots are indexed left-to-right, top-to-bottom.
    """

    def __init__(self):
        self._slots: list[Optional[ItemStack]] = [None] * (INV_COLS * INV_ROWS)
        self.active_hotbar: int = 0  # which hotbar slot is selected (0..HOTBAR_SIZE-1)

    # ── Slot addressing ───────────────────────────────────────────────

    @property
    def slots(self) -> list[Optional[ItemStack]]:
        return self._slots

    def _idx(self, col: int, row: int) -> int:
        return row * INV_COLS + col

    def slot(self, idx: int) -> Optional[ItemStack]:
        if 0 <= idx < len(self._slots):
            return self._slots[idx]
        return None

    def set_slot(self, idx: int, stack: Optional[ItemStack]):
        if 0 <= idx < len(self._slots):
            self._slots[idx] = stack

    @property
    def hotbar(self) -> list[Optional[ItemStack]]:
        """First HOTBAR_SIZE slots."""
        return self._slots[:HOTBAR_SIZE]

    @property
    def active_item(self) -> Optional[ItemStack]:
        return self._slots[self.active_hotbar]

    # ── Adding items ──────────────────────────────────────────────────

    def add_item(self, item_id: str, qty: int = 1) -> bool:
        """
        Add qty of item_id. Tries to stack into existing stacks first,
        then finds an empty slot. Returns True if fully added.
        """
        remaining = qty
        idef = ITEM_DEFS.get(item_id)
        if not idef:
            return False

        # Try merging into existing partial stacks
        for i, s in enumerate(self._slots):
            if s and s.item_id == item_id and not s.is_full:
                remaining = s.add(remaining)
                if remaining == 0:
                    return True

        # Find empty slot(s)
        while remaining > 0:
            empty = self._first_empty()
            if empty is None:
                return False  # inventory full
            new_stack = ItemStack(item_id, min(remaining, idef.get("stack_max", 1)))
            self._slots[empty] = new_stack
            remaining -= new_stack.qty

        return True

    def _first_empty(self) -> Optional[int]:
        for i, s in enumerate(self._slots):
            if s is None:
                return i
        return None

    # ── Removing items ────────────────────────────────────────────────

    def remove_item(self, item_id: str, qty: int = 1) -> bool:
        """Remove qty of item_id. Returns True on success."""
        available = self.count(item_id)
        if available < qty:
            return False
        remaining = qty
        for i, s in enumerate(self._slots):
            if s and s.item_id == item_id:
                take = min(s.qty, remaining)
                s.qty -= take
                remaining -= take
                if s.qty <= 0:
                    self._slots[i] = None
                if remaining == 0:
                    return True
        return True

    def count(self, item_id: str) -> int:
        return sum(s.qty for s in self._slots if s and s.item_id == item_id)

    def has(self, item_id: str, qty: int = 1) -> bool:
        return self.count(item_id) >= qty

    # ── Drag / drop ───────────────────────────────────────────────────

    def swap_slots(self, idx_a: int, idx_b: int):
        """Swap two slots. If same item, merge instead."""
        a, b = self._slots[idx_a], self._slots[idx_b]
        if a and b and a.item_id == b.item_id:
            overflow = b.add(a.qty)
            if overflow == 0:
                self._slots[idx_a] = None
            else:
                a.qty = overflow
        else:
            self._slots[idx_a], self._slots[idx_b] = b, a

    def split_slot(self, src_idx: int, dst_idx: int) -> bool:
        """Move half of src into dst (must be empty or same item)."""
        src = self._slots[src_idx]
        if not src or src.qty < 2:
            return False
        dst = self._slots[dst_idx]
        half = src.split()
        if dst is None:
            self._slots[dst_idx] = half
        elif dst.item_id == src.item_id and not dst.is_full:
            dst.add(half.qty)
        else:
            return False
        return True

    # ── Auto-sort ─────────────────────────────────────────────────────

    def auto_sort(self):
        """
        Sort by category priority then name.
        Category order: weapon > armor > accessory > key_item > consumable > material
        """
        cat_order = {"weapon": 0, "armor": 1, "accessory": 2,
                     "key_item": 3, "consumable": 4, "material": 5}
        non_null = [s for s in self._slots if s]
        non_null.sort(key=lambda s: (
            cat_order.get(s.definition.get("category", "material"), 9),
            s.definition.get("name", s.item_id),
        ))
        # Re-fill slots from the start of the inventory/hotbar area
        for i in range(len(self._slots)):
            self._slots[i] = non_null[i] if i < len(non_null) else None

    # ── Serialise / deserialise ───────────────────────────────────────

    def to_save(self) -> list[dict | None]:
        out = []
        for s in self._slots:
            out.append({"id": s.item_id, "qty": s.qty} if s else None)
        return out

    @classmethod
    def from_save(cls, data: list) -> "GridInventory":
        inv = cls()
        for i, entry in enumerate(data[:INV_COLS * INV_ROWS]):
            if entry:
                inv._slots[i] = ItemStack(entry["id"], entry.get("qty", 1))
        return inv

    # ── Legacy bridge: mirror to old Inventory-style list ────────────

    def legacy_items(self) -> list[str]:
        """Return a flat list of item IDs (one per stack) for legacy systems."""
        seen = set()
        result = []
        for s in self._slots:
            if s and s.item_id not in seen:
                seen.add(s.item_id)
                result.append(s.item_id)
        return result

    def get_display_list(self) -> list[dict]:
        """For backward-compat with HUD/old inventory screen."""
        result = []
        for s in self._slots:
            if s:
                d = dict(s.definition)
                d["id"] = s.item_id
                d["qty"] = s.qty
                result.append(d)
        return result

    def count_items(self) -> int:
        return sum(1 for s in self._slots if s)


# ─────────────────────────────────────────────────────────────────────────────
# CRAFTING BAG
# ─────────────────────────────────────────────────────────────────────────────

CRAFT_BAG_COLS = 6
CRAFT_BAG_ROWS = 3

class CraftingBag(GridInventory):
    """Dedicated 6×3 bag for crafting materials only."""

    def __init__(self):
        self._slots: list[Optional[ItemStack]] = [None] * (CRAFT_BAG_COLS * CRAFT_BAG_ROWS)
        self.active_hotbar = 0

    def accepts(self, item_id: str) -> bool:
        cat = ITEM_DEFS.get(item_id, {}).get("category", "")
        return cat in MATERIAL_CATEGORIES

    def to_save(self) -> list[dict | None]:
        return super().to_save()

    @classmethod
    def from_save(cls, data: list) -> "CraftingBag":
        bag = cls()
        for i, entry in enumerate(data[:CRAFT_BAG_COLS * CRAFT_BAG_ROWS]):
            if entry:
                bag._slots[i] = ItemStack(entry["id"], entry.get("qty", 1))
        return bag


# ─────────────────────────────────────────────────────────────────────────────
# EQUIPMENT SLOTS
# ─────────────────────────────────────────────────────────────────────────────

class EquipmentSlots:
    """
    Three visible equipment slots: two armor slots and one accessory slot.
    Weapons live directly in the hotbar / grid inventory instead of here.
    Applying equipment stats modifies a player-stat dict.
    Gear can unlock mechanic flags via the 'effect' field.
    """

    SLOTS = ("armor_1", "armor_2", "accessory")
    CATEGORY_TO_SLOTS = {
        "armor": ("armor_1", "armor_2"),
        "accessory": ("accessory",),
    }
    SLOT_TO_CATEGORY = {
        "armor_1": "armor",
        "armor_2": "armor",
        "accessory": "accessory",
    }

    def __init__(self):
        self.equipped: dict[str, Optional[str]] = {s: None for s in self.SLOTS}

    def compatible_slots(self, item_id: str) -> tuple[str, ...]:
        idef = ITEM_DEFS.get(item_id, {})
        return self.CATEGORY_TO_SLOTS.get(idef.get("equip_slot"), ())

    def accepts(self, slot: str, item_id: str) -> bool:
        return slot in self.compatible_slots(item_id)

    def equip(self, item_id: str, preferred_slot: str | None = None) -> Optional[str]:
        """
        Equip item_id into the appropriate slot.
        Returns the previously equipped item_id (for swapping back into inventory),
        or None if the slot was empty.
        """
        compatible = self.compatible_slots(item_id)
        if not compatible:
            return None

        if preferred_slot is not None:
            if preferred_slot not in compatible:
                return None
            slot = preferred_slot
        else:
            slot = next((name for name in compatible if self.equipped[name] is None), compatible[0])

        prev = self.equipped[slot]
        self.equipped[slot] = item_id
        return prev  # may be None

    def unequip(self, slot: str) -> Optional[str]:
        """Unequip and return item_id, or None if empty."""
        if slot not in self.SLOTS:
            return None
        item = self.equipped[slot]
        self.equipped[slot] = None
        return item

    def get_all_stats(self) -> dict:
        """Aggregate stats from all equipped items."""
        stats: dict = {}
        for item_id in self.equipped.values():
            if item_id:
                idef = ITEM_DEFS.get(item_id, {})
                for k, v in idef.get("stats", {}).items():
                    stats[k] = stats.get(k, 0) + v
        return stats

    def get_all_effects(self) -> set[str]:
        """Aggregate mechanic effects from all equipped items."""
        effects: set[str] = set()
        for item_id in self.equipped.values():
            if item_id:
                idef = ITEM_DEFS.get(item_id, {})
                for tag in idef.get("effect", "").split(","):
                    tag = tag.strip()
                    if tag:
                        effects.add(tag)
        return effects

    @property
    def weapon(self) -> Optional[str]:
        return None

    @property
    def armor(self) -> Optional[str]:
        return self.equipped["armor_1"] or self.equipped["armor_2"]

    @property
    def armor_1(self) -> Optional[str]:
        return self.equipped["armor_1"]

    @property
    def armor_2(self) -> Optional[str]:
        return self.equipped["armor_2"]

    @property
    def accessory(self) -> Optional[str]:
        return self.equipped["accessory"]

    def to_save(self) -> dict:
        return dict(self.equipped)

    @classmethod
    def from_save(cls, data: dict) -> "EquipmentSlots":
        eq = cls()
        if not isinstance(data, dict):
            return eq
        for slot in cls.SLOTS:
            if slot in data:
                eq.equipped[slot] = data[slot]
        # v4 compatibility: the single old armor slot becomes armor_1
        if eq.equipped["armor_1"] is None and "armor" in data:
            eq.equipped["armor_1"] = data["armor"]
        return eq


# ─────────────────────────────────────────────────────────────────────────────
# ICON RENDERING  — drawn icons for inventory / hotbar (replaces emoji glyphs)
# ─────────────────────────────────────────────────────────────────────────────

# (icon_type, primary_color)
ICON_MAP: dict[str, tuple[str, tuple]] = {
    "old_sword":         ("sword",     (155, 158, 172)),
    "forest_key":        ("key",       (200, 170,  55)),
    "herb":              ("herb",      ( 60, 185,  80)),
    "amulet":            ("orb",       (140,  80, 220)),
    "mushroom":          ("mushroom",  ( 90, 155, 215)),
    "letter":            ("envelope",  (220, 205, 158)),
    "cave_map":          ("scroll",    (165, 130,  82)),
    "boss_key":          ("boss_key",  (220, 160,  35)),
    "crystal":           ("diamond",   ( 60,  40, 180)),
    "iron_sword":        ("sword",     (125, 140, 160)),
    "shadow_blade":      ("dagger",    ( 55,  50,  85)),
    "fire_staff":        ("staff",     (225,  88,  38)),
    "ice_wand":          ("wand",      ( 75, 178, 238)),
    "leather_armor":     ("shield",    (128,  92,  52)),
    "iron_armor":        ("shield",    (118, 122, 138)),
    "shadow_cloak":      ("cloak",     ( 58,  48,  80)),
    "mage_robes":        ("robe",      ( 58,  78, 185)),
    "speed_ring":        ("ring",      (198, 172,  48)),
    "hunters_necklace":  ("necklace",  (198, 138,  48)),
    "health_potion":     ("flask",     (200,  55,  75)),
    "healing_orb":       ("flask",     ( 68, 220,  98)),
    "raw_meat":          ("bone",      (178,  78,  78)),
    "cooked_meat":       ("bone",      (158,  98,  58)),
    "antidote":          ("flask",     ( 58, 185,  80)),
    "animal_hide":       ("hide",      (138, 108,  72)),
    "bones":             ("bone",      (208, 198, 172)),
    "crystal_shard":     ("diamond",   ( 78, 118, 200)),
    "forest_herbs":      ("herb",      ( 58, 175,  78)),
    "mushroom_spore":    ("mushroom",  (168, 128, 210)),
    "iron_ore":          ("ore",       (128,  98,  78)),
    "iron_ingot":        ("ingot",     (118, 118, 135)),
    "shadow_dust":       ("sparkle",   ( 98,  78, 150)),
    "fire_essence":      ("flame",     (225,  88,  38)),
    "ancient_tome":      ("book",      (138, 108,  72)),
    "lore_fragment":     ("scroll",    (188, 168, 118)),
    "runic_crystal":     ("diamond",   (120,  80, 200)),
    "bone_arrow":        ("arrow",     (198, 178, 148)),
    "void_shard":        ("diamond",   ( 80,  40, 160)),
    "hunters_bow":       ("bow",       (148, 118,  72)),
    "runic_bow":         ("bow",       (140,  90, 210)),
}


def _dk(c: tuple, a: int = 55) -> tuple:
    return tuple(max(0, v - a) for v in c)


def _lt(c: tuple, a: int = 55) -> tuple:
    return tuple(min(255, v + a) for v in c)


def draw_item_icon(surf: pygame.Surface, item_id: str,
                   x: int, y: int, size: int = 24) -> None:
    """Render a distinct drawn icon for item_id into surf at (x, y)."""
    icon_type, col = ICON_MAP.get(item_id, ("box", (120, 120, 135)))
    _draw_icon_shape(surf, icon_type, x, y, size, col)


def _draw_icon_shape(surf, icon_type, x, y, s, col):
    cx = x + s // 2
    cy = y + s // 2
    dk = _dk(col)
    lt = _lt(col)

    if icon_type == "sword":
        # Diagonal blade + crossguard + pommel
        p1 = (x + s - 5, y + 4)
        p2 = (x + 4, y + s - 4)
        pygame.draw.line(surf, lt, p1, (p1[0]-1, p1[1]-1), 2)   # tip glint
        pygame.draw.line(surf, col, p1, p2, 3)
        pygame.draw.line(surf, dk, p2, (p2[0]+1, p2[1]+1), 2)  # shadow
        gx, gy = cx - 1, cy - 1
        pygame.draw.line(surf, dk, (gx - 4, gy + 4), (gx + 4, gy - 4), 2)
        pygame.draw.circle(surf, dk, p2, 2)

    elif icon_type == "dagger":
        pygame.draw.line(surf, col, (cx, cy + 7), (cx, cy - 7), 2)
        pygame.draw.line(surf, dk, (cx - 4, cy + 3), (cx + 4, cy + 3), 2)
        pygame.draw.circle(surf, lt, (cx, cy - 7), 2)
        pygame.draw.circle(surf, dk, (cx, cy + 9), 2)

    elif icon_type == "key":
        pygame.draw.circle(surf, col, (cx - 2, cy - 3), 5, 2)
        pygame.draw.line(surf, col, (cx + 3, cy - 3), (cx + 3, cy + 6), 2)
        pygame.draw.line(surf, col, (cx + 3, cy + 2), (cx + 6, cy + 2), 2)
        pygame.draw.line(surf, col, (cx + 3, cy + 5), (cx + 5, cy + 5), 2)

    elif icon_type == "boss_key":
        # Ornate key with gems
        pygame.draw.circle(surf, col, (cx - 2, cy - 3), 6, 2)
        pygame.draw.circle(surf, lt, (cx - 2, cy - 3), 2)
        pygame.draw.line(surf, col, (cx + 4, cy - 3), (cx + 4, cy + 7), 2)
        pygame.draw.line(surf, col, (cx + 4, cy + 1), (cx + 7, cy + 1), 2)
        pygame.draw.line(surf, col, (cx + 4, cy + 4), (cx + 6, cy + 4), 2)

    elif icon_type == "herb":
        pts = [(cx, cy - 7), (cx + 5, cy - 1), (cx + 3, cy + 5),
               (cx, cy + 4), (cx - 3, cy + 5), (cx - 5, cy - 1)]
        pygame.draw.polygon(surf, col, pts)
        pygame.draw.line(surf, dk, (cx, cy - 5), (cx, cy + 4), 1)

    elif icon_type == "orb":
        r = s // 3 + 1
        pygame.draw.circle(surf, col, (cx, cy), r)
        pygame.draw.circle(surf, dk, (cx, cy), r, 1)
        pygame.draw.circle(surf, lt, (cx - 2, cy - 2), max(1, r // 3))

    elif icon_type == "mushroom":
        pygame.draw.ellipse(surf, col, (cx - 7, cy - 5, 14, 8))
        pygame.draw.ellipse(surf, dk, (cx - 7, cy - 5, 14, 8), 1)
        pygame.draw.rect(surf, lt, (cx - 3, cy + 2, 6, 6), border_radius=1)
        pygame.draw.rect(surf, dk, (cx - 3, cy + 2, 6, 6), 1, border_radius=1)
        pygame.draw.circle(surf, lt, (cx - 2, cy - 2), 2)

    elif icon_type == "envelope":
        pygame.draw.rect(surf, col, (cx - 7, cy - 4, 14, 10))
        pygame.draw.rect(surf, dk, (cx - 7, cy - 4, 14, 10), 1)
        pygame.draw.line(surf, dk, (cx - 7, cy - 4), (cx, cy + 1), 1)
        pygame.draw.line(surf, dk, (cx + 7, cy - 4), (cx, cy + 1), 1)

    elif icon_type == "scroll":
        pygame.draw.rect(surf, col, (cx - 6, cy - 6, 12, 12), border_radius=3)
        pygame.draw.rect(surf, dk, (cx - 6, cy - 6, 12, 12), 1, border_radius=3)
        for iy in range(cy - 3, cy + 5, 3):
            pygame.draw.line(surf, dk, (cx - 4, iy), (cx + 4, iy), 1)

    elif icon_type == "diamond":
        pts = [(cx, cy - 8), (cx + 6, cy), (cx, cy + 8), (cx - 6, cy)]
        pygame.draw.polygon(surf, col, pts)
        pygame.draw.polygon(surf, dk, pts, 1)
        pygame.draw.polygon(surf, lt, [(cx, cy - 8), (cx + 6, cy), (cx, cy - 1)], 0)

    elif icon_type == "shield":
        pts = [(cx - 7, cy - 6), (cx + 7, cy - 6), (cx + 7, cy + 1),
               (cx, cy + 7), (cx - 7, cy + 1)]
        pygame.draw.polygon(surf, col, pts)
        pygame.draw.polygon(surf, dk, pts, 1)
        pygame.draw.line(surf, lt, (cx, cy - 5), (cx, cy + 4), 1)

    elif icon_type == "cloak":
        pts = [(cx - 6, cy - 5), (cx + 6, cy - 5), (cx + 8, cy + 6),
               (cx, cy + 4), (cx - 8, cy + 6)]
        pygame.draw.polygon(surf, col, pts)
        pygame.draw.polygon(surf, dk, pts, 1)
        pygame.draw.line(surf, lt, (cx, cy - 4), (cx, cy + 2), 1)

    elif icon_type == "robe":
        pts = [(cx - 5, cy - 7), (cx + 5, cy - 7), (cx + 7, cy + 7),
               (cx, cy + 5), (cx - 7, cy + 7)]
        pygame.draw.polygon(surf, col, pts)
        pygame.draw.polygon(surf, dk, pts, 1)
        # Collar
        pygame.draw.arc(surf, lt,
                        pygame.Rect(cx - 3, cy - 8, 6, 5), 0, math.pi, 2)

    elif icon_type == "staff":
        pygame.draw.line(surf, dk, (cx - 1, cy - 7), (cx - 1, cy + 8), 2)
        pygame.draw.circle(surf, col, (cx - 1, cy - 6), 4)
        pygame.draw.circle(surf, lt, (cx - 2, cy - 7), 2)

    elif icon_type == "wand":
        pygame.draw.line(surf, dk, (cx + 4, cy + 6), (cx - 4, cy - 6), 2)
        pygame.draw.circle(surf, col, (cx - 4, cy - 6), 3)
        pygame.draw.circle(surf, lt, (cx - 5, cy - 7), 1)

    elif icon_type == "flask":
        pygame.draw.circle(surf, col, (cx, cy + 3), 5)
        pygame.draw.rect(surf, col, (cx - 2, cy - 5, 4, 6))
        pygame.draw.rect(surf, dk, (cx - 3, cy - 6, 6, 2))
        pygame.draw.circle(surf, lt, (cx + 2, cy + 2), 2)

    elif icon_type == "bone":
        pygame.draw.line(surf, col, (cx - 4, cy - 4), (cx + 4, cy + 4), 2)
        pygame.draw.circle(surf, col, (cx - 4, cy - 4), 3)
        pygame.draw.circle(surf, col, (cx + 4, cy + 4), 3)

    elif icon_type == "ring":
        pygame.draw.circle(surf, col, (cx, cy + 2), 5, 2)
        pygame.draw.circle(surf, lt, (cx, cy - 3), 2)
        pygame.draw.circle(surf, dk, (cx, cy - 3), 2, 1)

    elif icon_type == "necklace":
        pygame.draw.arc(surf, col,
                        pygame.Rect(cx - 6, cy - 2, 12, 10), 0, math.pi, 2)
        pygame.draw.circle(surf, lt, (cx, cy + 6), 3)
        pygame.draw.circle(surf, dk, (cx, cy + 6), 3, 1)

    elif icon_type == "hide":
        pts = [(cx - 6, cy - 4), (cx, cy - 7), (cx + 6, cy - 4),
               (cx + 5, cy + 4), (cx, cy + 7), (cx - 5, cy + 4)]
        pygame.draw.polygon(surf, col, pts)
        pygame.draw.polygon(surf, dk, pts, 1)

    elif icon_type == "ore":
        pygame.draw.polygon(surf, col, [
            (cx - 4, cy + 5), (cx - 6, cy), (cx - 2, cy - 5),
            (cx + 3, cy - 6), (cx + 6, cy - 1), (cx + 4, cy + 5)])
        pygame.draw.polygon(surf, dk, [
            (cx - 4, cy + 5), (cx - 6, cy), (cx - 2, cy - 5),
            (cx + 3, cy - 6), (cx + 6, cy - 1), (cx + 4, cy + 5)], 1)
        pygame.draw.circle(surf, lt, (cx, cy - 2), 2)

    elif icon_type == "ingot":
        pygame.draw.rect(surf, col, (cx - 7, cy - 3, 14, 7), border_radius=2)
        pygame.draw.rect(surf, dk, (cx - 7, cy - 3, 14, 7), 1, border_radius=2)
        pygame.draw.line(surf, lt, (cx - 5, cy - 1), (cx + 5, cy - 1), 1)

    elif icon_type == "sparkle":
        for ang in range(0, 360, 45):
            r = math.radians(ang)
            r2 = 5 if ang % 90 == 0 else 3
            ex = int(cx + r2 * math.cos(r))
            ey = int(cy + r2 * math.sin(r))
            pygame.draw.line(surf, col, (cx, cy), (ex, ey), 1)
        pygame.draw.circle(surf, lt, (cx, cy), 2)

    elif icon_type == "flame":
        pts = [(cx, cy - 7), (cx + 4, cy - 1), (cx + 2, cy + 5),
               (cx - 2, cy + 5), (cx - 4, cy - 1)]
        pygame.draw.polygon(surf, col, pts)
        inner = [(cx, cy - 3), (cx + 2, cy + 1), (cx - 2, cy + 1)]
        pygame.draw.polygon(surf, lt, inner)

    elif icon_type == "book":
        pygame.draw.rect(surf, col, (cx - 7, cy - 6, 14, 12), border_radius=1)
        pygame.draw.rect(surf, dk, (cx - 7, cy - 6, 14, 12), 1, border_radius=1)
        pygame.draw.line(surf, dk, (cx - 1, cy - 6), (cx - 1, cy + 6), 1)
        for iy in range(cy - 3, cy + 5, 3):
            pygame.draw.line(surf, lt, (cx, iy), (cx + 5, iy), 1)

    elif icon_type == "bow":
        # Curved bow body + string
        pygame.draw.arc(surf, col,
                        pygame.Rect(cx - 2, cy - 8, 10, 16), 1.2, 5.1, 3)
        pygame.draw.line(surf, dk, (cx + 1, cy - 7), (cx + 1, cy + 7), 1)
        pygame.draw.circle(surf, lt, (cx + 7, cy), 2)

    elif icon_type == "arrow":
        # Diagonal arrow shaft + tip
        pygame.draw.line(surf, col, (cx - 5, cy + 5), (cx + 5, cy - 5), 2)
        pygame.draw.polygon(surf, lt, [
            (cx + 5, cy - 5), (cx + 2, cy - 3), (cx + 3, cy - 6)])
        pygame.draw.line(surf, dk, (cx - 5, cy + 5), (cx - 4, cy + 3), 2)
        pygame.draw.line(surf, dk, (cx - 5, cy + 5), (cx - 3, cy + 4), 2)

    else:
        # Fallback colored box
        pygame.draw.rect(surf, col, (cx - 5, cy - 5, 10, 10), border_radius=2)
        pygame.draw.rect(surf, dk, (cx - 5, cy - 5, 10, 10), 1, border_radius=2)
