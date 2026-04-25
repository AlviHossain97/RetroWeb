"""
Inventory — key-item bag for quest progression (legacy / save-compatible layer).
The full grid inventory lives in item_system.py (GridInventory + EquipmentSlots).

This module is kept for backward compatibility with existing save files and
quest/NPC systems that reference inventory.has() / inventory.add() etc.
New code should use item_system.GridInventory directly.
"""
# Re-export the extended ITEM_DEFS from item_system so all imports resolve
from item_system import ITEM_DEFS  # noqa: F401 — legacy callers use inventory.ITEM_DEFS


class Inventory:
    """
    Legacy key-item bag — backed by a GridInventory internally.
    Maintains the original API (has/add/remove/count/get_display_list)
    so all existing quest/NPC/save code keeps working unchanged.

    The underlying GridInventory is the authoritative store; callers that
    need the full grid features should access self.grid directly.
    """
    def __init__(self):
        from item_system import GridInventory, EquipmentSlots, CraftingBag
        self.grid = GridInventory()
        self.equipment = EquipmentSlots()
        self.craft_bag = CraftingBag()
        # Legacy flat list view — kept in sync via property
        self.max_items = 24   # grid capacity

    # ── Legacy API ────────────────────────────────────────────────────

    @property
    def items(self) -> list[str]:
        """Flat list of item IDs for legacy save serialization."""
        return self.grid.legacy_items()

    def has(self, item_id: str, qty: int = 1) -> bool:
        return self.grid.has(item_id, qty)

    def add(self, item_id: str) -> bool:
        """
        Add a single unit of item_id.
        Returns True on success, False if full or (for key items) already held.
        """
        from item_system import ITEM_DEFS as _DEFS, MATERIAL_CATEGORIES
        idef = _DEFS.get(item_id, {})
        cat = idef.get("category", "key_item")

        # Key items: strict uniqueness (legacy behaviour preserved)
        if idef.get("stack_max", 1) == 1 and self.grid.has(item_id):
            return False

        # Materials auto-route to crafting bag
        if cat in MATERIAL_CATEGORIES and self.craft_bag.accepts(item_id):
            return self.craft_bag.add_item(item_id, 1)

        return self.grid.add_item(item_id, 1)

    def add_qty(self, item_id: str, qty: int = 1) -> bool:
        """Add arbitrary quantity (new systems use this for stackable items)."""
        from item_system import ITEM_DEFS as _DEFS, MATERIAL_CATEGORIES
        cat = _DEFS.get(item_id, {}).get("category", "key_item")
        if cat in MATERIAL_CATEGORIES:
            return self.craft_bag.add_item(item_id, qty)
        return self.grid.add_item(item_id, qty)

    def remove(self, item_id: str) -> bool:
        if self.grid.has(item_id):
            return self.grid.remove_item(item_id, 1)
        if self.craft_bag.has(item_id):
            return self.craft_bag.remove_item(item_id, 1)
        return False

    def count_item(self, item_id: str) -> int:
        return self.grid.count(item_id) + self.craft_bag.count(item_id)

    def get_display_list(self) -> list[dict]:
        return self.grid.get_display_list()

    def count(self) -> int:
        return self.grid.count_items()

    # ── Equipment helpers ─────────────────────────────────────────────

    def equip(self, item_id: str) -> bool:
        """
        Move item_id from grid into the appropriate equipment slot.
        If a different item was in that slot, returns it to the grid.
        Returns True on success.
        """
        if not self.grid.has(item_id):
            return False
        if not self.equipment.compatible_slots(item_id):
            return False
        prev = self.equipment.equip(item_id)
        self.grid.remove_item(item_id, 1)
        if prev:
            self.grid.add_item(prev, 1)
        return True

    def unequip(self, slot: str) -> bool:
        item = self.equipment.unequip(slot)
        if item:
            self.grid.add_item(item, 1)
            return True
        return False

    @property
    def equipped_weapon(self):
        stack = self.grid.active_item
        if not stack:
            return None
        idef = ITEM_DEFS.get(stack.item_id, {})
        if idef.get("equip_slot") == "weapon":
            return stack.item_id
        return None

    @property
    def equipped_effects(self) -> set:
        return self.equipment.get_all_effects()

    @property
    def equipped_stats(self) -> dict:
        return self.equipment.get_all_stats()

    # ── Save / load ───────────────────────────────────────────────────

    def to_save(self) -> dict:
        return {
            "grid":      self.grid.to_save(),
            "craft_bag": self.craft_bag.to_save(),
            "equipment": self.equipment.to_save(),
        }

    @classmethod
    def from_save(cls, data: dict) -> "Inventory":
        from item_system import GridInventory, EquipmentSlots, CraftingBag
        inv = cls()
        if "grid" in data:
            inv.grid = GridInventory.from_save(data["grid"])
            equipment_data = data.get("equipment", {})
            inv.equipment = EquipmentSlots.from_save(equipment_data)
            inv.craft_bag = CraftingBag.from_save(data.get("craft_bag", []))
            # v4 compatibility: weapons used to live in a dedicated equipment slot.
            # Move any legacy equipped weapon back into the grid/hotbar.
            if isinstance(equipment_data, dict):
                legacy_weapon = equipment_data.get("weapon")
                if legacy_weapon and not inv.grid.has(legacy_weapon):
                    inv.grid.add_item(legacy_weapon, 1)
        else:
            # Legacy flat list (v3 saves) — import into grid
            for iid in data if isinstance(data, list) else data.get("items", []):
                inv.grid.add_item(iid, 1)
        return inv
