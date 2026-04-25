"""
Crafting screen — shows available recipes and lets the player craft items.

Correctly interfaces with the live CraftingManager API:
  cm.can_craft(rid, grid_inv, craft_bag, station, ignore_station)
  cm.craft(rid, grid_inv, craft_bag, station, ignore_station) → {"item_id", "qty"} | None
  cm.missing_ingredients(rid, grid_inv, craft_bag) → [{"item_id", "need", "have"}]
  cm.get_craftable_list(grid_inv, craft_bag, station) → [{"id", ...}]
"""

import pygame
from crafting import RECIPES, CraftingManager
from ui.fonts import get_font
from states.state_machine import State
from settings import COLOR_WHITE, COLOR_ACCENT

STATION_LABELS = {
    "none": "Hand",
    "cooking": "Campfire",
    "alchemy": "Alchemy",
    "forge": "Forge",
}
STATION_COLORS = {
    "none": (180, 180, 180),
    "cooking": (255, 160, 60),
    "alchemy": (140, 220, 180),
    "forge": (220, 140, 60),
}


class CraftingScreenState(State):
    def __init__(self, game):
        super().__init__(game)
        self.font = None
        self.small_font = None
        self.tiny_font = None
        self._cursor = 0
        self._station = "none"
        self._message = ""
        self._msg_timer = 0.0

    def _ensure_fonts(self):
        if self.font is None:
            self.font = get_font(14)
            self.small_font = get_font(12)
            self.tiny_font = get_font(10)

    def _get_crafting_mgr(self):
        return getattr(self.game, "crafting_manager", None) or CraftingManager()

    def _get_inventories(self):
        inv = self.game.inventory
        grid_inv = getattr(inv, "grid", None) or inv
        craft_bag = getattr(inv, "craft_bag", None)
        if craft_bag is None:
            from item_system import CraftingBag

            craft_bag = CraftingBag()
        return grid_inv, craft_bag

    def _build_recipe_ids(self):
        mgr = self._get_crafting_mgr()
        grid_inv, craft_bag = self._get_inventories()
        self._recipe_ids = []
        for rid, recipe in RECIPES.items():
            recipe_station = recipe.get("station", "none")
            if self._station != "none" and recipe_station != self._station:
                continue
            if mgr.can_craft(rid, grid_inv, craft_bag, self._station):
                self._recipe_ids.append(rid)
        if not self._recipe_ids:
            for rid in RECIPES:
                self._recipe_ids.append(rid)
        self._cursor = max(0, min(self._cursor, len(self._recipe_ids) - 1))

    def _do_craft(self):
        if not self._recipe_ids:
            return
        rid = self._recipe_ids[self._cursor]
        mgr = self._get_crafting_mgr()
        grid_inv, craft_bag = self._get_inventories()
        result = mgr.craft(rid, grid_inv, craft_bag, self._station)
        if result:
            recipe = RECIPES[rid]
            self._message = f"Crafted: {recipe['name']}!"
            self._msg_timer = 2.5
            if hasattr(self.game, "audio") and self.game.audio:
                self.game.audio.play_sfx("craft")
        else:
            self._message = "Missing ingredients."
            self._msg_timer = 1.5
            if hasattr(self.game, "audio") and self.game.audio:
                self.game.audio.play_sfx("menu_move")

    def enter(self):
        self._cursor = 0
        self._message = ""
        self._msg_timer = 0.0
        self._station = "none"
        self._ensure_fonts()
        self._build_recipe_ids()

    def exit(self):
        pass

    def update(self, dt):
        if self._msg_timer > 0:
            self._msg_timer -= dt

        inp = self.game.input

        if inp.is_pressed("craft") or inp.is_pressed("b") or inp.is_pressed("start"):
            self.game.states.change("gameplay")
            return

        n = len(self._recipe_ids)
        if n == 0:
            if inp.is_pressed("left") or inp.is_pressed("right"):
                self._station = "none"
                self._build_recipe_ids()
            return

        if inp.is_pressed("up"):
            self._cursor = (self._cursor - 1) % n
        elif inp.is_pressed("down"):
            self._cursor = (self._cursor + 1) % n
        elif inp.is_pressed("left") or inp.is_pressed("right"):
            stations = ["none", "cooking", "alchemy", "forge"]
            idx = stations.index(self._station) if self._station in stations else 0
            if inp.is_pressed("right"):
                idx = (idx + 1) % len(stations)
            else:
                idx = (idx - 1) % len(stations)
            self._station = stations[idx]
            self._build_recipe_ids()

        if inp.is_pressed("a"):
            self._do_craft()

    def render(self, screen):
        self._ensure_fonts()
        vw, vh = self._viewport_size(screen)
        compact = self._is_compact_view(screen)

        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 215))
        screen.blit(overlay, (0, 0))

        px = 8 if compact else 12
        py = 8 if compact else 12
        pw = vw - px * 2
        ph = vh - py * 2

        pygame.draw.rect(screen, (10, 10, 20), (px, py, pw, ph), border_radius=6)
        pygame.draw.rect(screen, (60, 60, 80), (px, py, pw, ph), 1, border_radius=6)

        title_s = self.font.render("CRAFTING", True, COLOR_ACCENT)
        screen.blit(title_s, (px + pw // 2 - title_s.get_width() // 2, py + 6))

        station_label = STATION_LABELS.get(self._station, "Hand")
        station_color = STATION_COLORS.get(self._station, (180, 180, 180))
        st_s = self.small_font.render(
            f"[L/R] Station: {station_label}", True, station_color
        )
        screen.blit(st_s, (px + pw // 2 - st_s.get_width() // 2, py + 24))

        if not self._recipe_ids:
            no_s = self.small_font.render(
                "No recipes available.", True, (120, 120, 130)
            )
            screen.blit(no_s, (px + pw // 2 - no_s.get_width() // 2, py + ph // 2))
            self._render_footer(screen, px, py, pw, ph, compact)
            return

        recipe = RECIPES[self._recipe_ids[self._cursor]]
        self._render_recipe_list(screen, px, py, pw, ph, compact)
        self._render_detail(screen, px, py, pw, ph, recipe, compact)
        self._render_footer(screen, px, py, pw, ph, compact)

    def _render_recipe_list(self, screen, px, py, pw, ph, compact):
        mgr = self._get_crafting_mgr()
        grid_inv, craft_bag = self._get_inventories()
        list_x = px + 8
        list_y = py + (40 if compact else 44)
        list_h = ph - (80 if compact else 100)
        row_h = 16 if compact else 22

        visible = max(1, list_h // row_h)
        scroll = max(
            0, min(self._cursor - visible // 2, max(0, len(self._recipe_ids) - visible))
        )

        for i in range(scroll, min(scroll + visible, len(self._recipe_ids))):
            rid = self._recipe_ids[i]
            recipe = RECIPES[rid]
            ry = list_y + (i - scroll) * row_h
            selected = i == self._cursor
            can = mgr.can_craft(rid, grid_inv, craft_bag, self._station)

            f = self.tiny_font if compact else self.small_font
            color = (
                COLOR_WHITE
                if selected
                else ((180, 220, 180) if can else (120, 120, 130))
            )

            name = recipe["name"]
            if not compact:
                station_tag = recipe.get("station", "none")
                if station_tag != "none":
                    name = f"[{station_tag[:4].upper()}] {name}"

            ns = f.render(name, True, color)
            screen.blit(
                ns, (list_x + (14 if compact else 18), ry + (2 if compact else 4))
            )

            if selected:
                cursor_s = self.tiny_font.render(">", True, COLOR_ACCENT)
                screen.blit(cursor_s, (list_x, ry + (2 if compact else 4)))

    def _render_detail(self, screen, px, py, pw, ph, recipe, compact):
        mgr = self._get_crafting_mgr()
        grid_inv, craft_bag = self._get_inventories()
        rid = self._recipe_ids[self._cursor]

        detail_y = py + ph - (50 if compact else 64)
        detail_h = 44 if compact else 56

        pygame.draw.rect(
            screen, (14, 16, 30), (px + 6, detail_y, pw - 12, detail_h), border_radius=4
        )
        pygame.draw.rect(
            screen,
            (60, 60, 80),
            (px + 6, detail_y, pw - 12, detail_h),
            1,
            border_radius=4,
        )

        name_s = self.small_font.render(recipe["name"], True, COLOR_ACCENT)
        screen.blit(name_s, (px + 12, detail_y + 4))

        output = recipe["output"]
        output_s = self.tiny_font.render(
            f"→ {output['item_id']} x{output['qty']}", True, (180, 220, 180)
        )
        screen.blit(output_s, (px + 12, detail_y + (18 if compact else 20)))

        ingredients = recipe.get("ingredients", [])
        missing = mgr.missing_ingredients(rid, grid_inv, craft_bag)
        missing_ids = {m["item_id"] for m in missing}

        from item_system import ITEM_DEFS

        parts = []
        for ing in ingredients:
            iid = ing["item_id"]
            need = ing["qty"]
            have = grid_inv.count(iid) + craft_bag.count(iid)
            iname = ITEM_DEFS.get(iid, {}).get("name", iid)
            is_missing = iid in missing_ids
            color = (255, 100, 100) if is_missing else (140, 200, 140)
            parts.append(f"{iname} {have}/{need}")

        ing_s = self.tiny_font.render("  ".join(parts), True, (160, 160, 170))
        screen.blit(ing_s, (px + 12, detail_y + (28 if compact else 34)))

        can = mgr.can_craft(rid, grid_inv, craft_bag, self._station)
        action = "A = Craft" if can else "Missing ingredients"
        action_s = self.tiny_font.render(
            action, True, COLOR_ACCENT if can else (140, 100, 100)
        )
        screen.blit(action_s, (px + pw - action_s.get_width() - 14, detail_y + 6))

        desc = recipe.get("desc", "")
        if desc and not compact:
            desc_s = self.tiny_font.render(desc[:50], True, (140, 140, 160))
            screen.blit(desc_s, (px + 12, detail_y + 42))

    def _render_footer(self, screen, px, py, pw, ph, compact):
        footer = "CRAFT/B=Close  L/R=Station  Up/Down=Select  A=Craft"
        if self._msg_timer > 0 and self._message:
            footer = self._message
        f = self.tiny_font if compact else self.small_font
        color = (
            (200, 200, 80) if (self._msg_timer > 0 and self._message) else (70, 70, 90)
        )
        fs = f.render(footer, True, color)
        screen.blit(
            fs, (px + pw // 2 - fs.get_width() // 2, py + ph - (14 if compact else 18))
        )
