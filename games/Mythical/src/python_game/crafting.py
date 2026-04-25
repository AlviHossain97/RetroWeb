"""
crafting.py — Recipe-based crafting system.

Recipes are keyed by their output item_id.
Each recipe requires:
  • A list of {item_id, qty} ingredient stacks
  • The output item_id and qty
  • An optional station tag ("forge", "alchemy", "cooking", "none")

Players can craft anywhere for "none" recipes;
forge/alchemy/cooking require proximity to a crafting station
(interactable tile or NPC — checked by gameplay).
"""
from __future__ import annotations
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# RECIPE DATABASE
# ─────────────────────────────────────────────────────────────────────────────

RECIPES: dict[str, dict] = {
    # ── Cooking ─────────────────────────────────────────────────────────────
    "cooked_meat": {
        "name":        "Cooked Meat",
        "station":     "cooking",       # requires campfire interactable
        "ingredients": [
            {"item_id": "raw_meat", "qty": 2},
        ],
        "output":      {"item_id": "cooked_meat", "qty": 1},
        "desc":        "Cook 2 raw meats over a fire for a restorative meal.",
    },
    "health_potion": {
        "name":        "Health Potion",
        "station":     "alchemy",
        "ingredients": [
            {"item_id": "forest_herbs",  "qty": 2},
            {"item_id": "mushroom_spore","qty": 1},
        ],
        "output":      {"item_id": "health_potion", "qty": 2},
        "desc":        "Combine herbs and spores into a restorative brew.",
    },
    "antidote": {
        "name":        "Antidote",
        "station":     "alchemy",
        "ingredients": [
            {"item_id": "forest_herbs", "qty": 3},
            {"item_id": "bones",        "qty": 1},
        ],
        "output":      {"item_id": "antidote", "qty": 1},
        "desc":        "Ground bone mixed with purifying herbs.",
    },
    # ── Forging ──────────────────────────────────────────────────────────────
    "iron_ingot": {
        "name":        "Iron Ingot",
        "station":     "forge",
        "ingredients": [
            {"item_id": "iron_ore", "qty": 2},
        ],
        "output":      {"item_id": "iron_ingot", "qty": 1},
        "desc":        "Smelt raw iron ore into a usable ingot.",
    },
    "iron_sword": {
        "name":        "Iron Sword",
        "station":     "forge",
        "ingredients": [
            {"item_id": "iron_ingot",  "qty": 3},
            {"item_id": "animal_hide", "qty": 1},
        ],
        "output":      {"item_id": "iron_sword", "qty": 1},
        "desc":        "A solid iron blade. Improves on the old sword.",
    },
    "leather_armor": {
        "name":        "Leather Armor",
        "station":     "forge",
        "ingredients": [
            {"item_id": "animal_hide", "qty": 5},
        ],
        "output":      {"item_id": "leather_armor", "qty": 1},
        "desc":        "Cured hide stitched into protective armor.",
    },
    "iron_armor": {
        "name":        "Iron Armor",
        "station":     "forge",
        "ingredients": [
            {"item_id": "iron_ingot",  "qty": 6},
            {"item_id": "animal_hide", "qty": 2},
        ],
        "output":      {"item_id": "iron_armor", "qty": 1},
        "desc":        "Heavy iron plate. Solid defense, slight speed penalty.",
    },
    # ── Shadow / special ─────────────────────────────────────────────────────
    "shadow_blade": {
        "name":        "Shadow Blade",
        "station":     "forge",
        "ingredients": [
            {"item_id": "iron_ingot",  "qty": 4},
            {"item_id": "shadow_dust", "qty": 3},
            {"item_id": "crystal_shard","qty": 2},
        ],
        "output":      {"item_id": "shadow_blade", "qty": 1},
        "desc":        "An obsidian-infused blade that enables the Dash-Strike.",
    },
    "shadow_cloak": {
        "name":        "Shadow Cloak",
        "station":     "forge",
        "ingredients": [
            {"item_id": "animal_hide", "qty": 4},
            {"item_id": "shadow_dust", "qty": 4},
        ],
        "output":      {"item_id": "shadow_cloak", "qty": 1},
        "desc":        "Dark leather that unlocks the Dash mechanic.",
    },
    "fire_staff": {
        "name":        "Fire Staff",
        "station":     "forge",
        "ingredients": [
            {"item_id": "iron_ingot",   "qty": 2},
            {"item_id": "fire_essence", "qty": 4},
            {"item_id": "crystal_shard","qty": 2},
        ],
        "output":      {"item_id": "fire_staff", "qty": 1},
        "desc":        "Channels condensed flame energy into a ranged attack.",
    },
    "hunters_necklace": {
        "name":        "Hunter's Necklace",
        "station":     "forge",
        "ingredients": [
            {"item_id": "animal_hide",  "qty": 2},
            {"item_id": "bones",        "qty": 3},
            {"item_id": "crystal_shard","qty": 1},
        ],
        "output":      {"item_id": "hunters_necklace", "qty": 1},
        "desc":        "Bone and crystal talisman that amplifies flanking damage.",
    },
    "speed_ring": {
        "name":        "Swift Ring",
        "station":     "forge",
        "ingredients": [
            {"item_id": "iron_ingot",   "qty": 1},
            {"item_id": "mushroom_spore","qty": 2},
        ],
        "output":      {"item_id": "speed_ring", "qty": 1},
        "desc":        "A ring infused with speed-enhancing spores.",
    },
    # ── Bows ───────────────────────────────────────────────────────────
    "hunters_bow": {
        "name":        "Hunter's Bow",
        "station":     "forge",
        "ingredients": [
            {"item_id": "bone_arrow",   "qty": 3},
            {"item_id": "animal_hide",  "qty": 2},
        ],
        "output":      {"item_id": "hunters_bow", "qty": 1},
        "desc":        "A recurve bow for ranged combat. Uses bone arrows as ammo.",
    },
    "runic_bow": {
        "name":        "Runic Bow",
        "station":     "forge",
        "ingredients": [
            {"item_id": "bone_arrow",    "qty": 5},
            {"item_id": "runic_crystal", "qty": 2},
            {"item_id": "void_shard",    "qty": 1},
        ],
        "output":      {"item_id": "runic_bow", "qty": 1},
        "desc":        "Ruin-enhanced bow. Extreme range and devastating power.",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# CRAFTING MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class CraftingManager:
    """
    Validates and executes crafting operations.

    Usage:
      cm = CraftingManager()
      if cm.can_craft("iron_sword", grid_inv, craft_bag, station="forge"):
          result = cm.craft("iron_sword", grid_inv, craft_bag)
          # result: {"item_id": "iron_sword", "qty": 1} or None on failure
    """

    def __init__(self):
        self.recipes = RECIPES

    def get_recipe(self, recipe_id: str) -> Optional[dict]:
        return self.recipes.get(recipe_id)

    def get_craftable_list(
        self,
        grid_inv,       # GridInventory
        craft_bag,      # CraftingBag
        station: str = "none",
    ) -> list[dict]:
        """
        Return all recipes the player can currently craft,
        optionally filtered by available station.
        """
        available = []
        for rid, recipe in self.recipes.items():
            req_station = recipe.get("station", "none")
            if req_station != "none" and req_station != station:
                continue
            if self._has_ingredients(recipe, grid_inv, craft_bag):
                available.append({"id": rid, **recipe})
        return available

    def can_craft(
        self,
        recipe_id: str,
        grid_inv,
        craft_bag,
        station: str = "none",
        ignore_station: bool = False,
    ) -> bool:
        recipe = self.get_recipe(recipe_id)
        if not recipe:
            return False
        if not ignore_station:
            req_station = recipe.get("station", "none")
            if req_station != "none" and req_station != station:
                return False
        return self._has_ingredients(recipe, grid_inv, craft_bag)

    def craft(
        self,
        recipe_id: str,
        grid_inv,
        craft_bag,
        station: str = "none",
        ignore_station: bool = False,
    ) -> Optional[dict]:
        """
        Execute a crafting operation. Removes ingredients, adds output.
        Returns the output dict on success, None on failure.
        """
        if not self.can_craft(recipe_id, grid_inv, craft_bag, station, ignore_station):
            return None

        recipe = self.get_recipe(recipe_id)
        # Consume ingredients from craft_bag first, then grid_inv
        for ing in recipe["ingredients"]:
            iid, qty = ing["item_id"], ing["qty"]
            remaining = qty
            # Try craft bag first
            if craft_bag.has(iid):
                to_take = min(remaining, craft_bag.count(iid))
                craft_bag.remove_item(iid, to_take)
                remaining -= to_take
            if remaining > 0:
                grid_inv.remove_item(iid, remaining)

        # Add output to grid_inv
        output = recipe["output"]
        grid_inv.add_item(output["item_id"], output["qty"])
        return dict(output)

    # ── Helpers ───────────────────────────────────────────────────────

    def _has_ingredients(self, recipe: dict, grid_inv, craft_bag) -> bool:
        for ing in recipe["ingredients"]:
            iid, qty = ing["item_id"], ing["qty"]
            total = grid_inv.count(iid) + craft_bag.count(iid)
            if total < qty:
                return False
        return True

    def missing_ingredients(self, recipe_id: str, grid_inv, craft_bag) -> list[dict]:
        """Return list of {item_id, need, have} for a UI 'what you're missing' display."""
        recipe = self.get_recipe(recipe_id)
        if not recipe:
            return []
        result = []
        for ing in recipe["ingredients"]:
            iid, need = ing["item_id"], ing["qty"]
            have = grid_inv.count(iid) + craft_bag.count(iid)
            if have < need:
                result.append({"item_id": iid, "need": need, "have": have})
        return result
