"""
Inventory screen — grid view with Minecraft-style equipment slots.
Features: keyboard nav, pick/place drag, dual armor slots, drawn item icons,
detail panel, crafting, sort. Weapons stay in the hotbar instead of a gear slot.
"""

import math
import pygame
from runtime.frame_clock import get_time
from settings import (
    COLOR_ACCENT,
    INV_COLS,
    INV_ROWS,
    HOTBAR_SIZE,
    INV_SLOT_SIZE,
    INV_SLOT_PAD,
)
from states.state_machine import State
from item_system import ITEM_DEFS, ItemStack, draw_item_icon
from crafting import CraftingManager
from ui.fonts import get_font

SLOT_SZ = INV_SLOT_SIZE  # 38
SLOT_PAD = INV_SLOT_PAD  # 3

RARITY_COLORS = {
    "common": (165, 165, 178),
    "uncommon": (68, 200, 78),
    "rare": (68, 138, 255),
    "epic": (178, 68, 240),
    "legendary": (255, 168, 28),
}

_BG = (7, 9, 18)
_PANEL = (11, 14, 26)
_BORDER = (40, 44, 60)
_BORDER_LT = (58, 62, 82)
_SLOT_BG = (16, 18, 30)
_SLOT_SEL = (24, 28, 50)
_TEXT_DIM = (80, 84, 102)
_TEXT_MID = (150, 154, 175)
_TEXT_BRT = (220, 222, 235)

# Visible equipment slots. Weapons stay in the hotbar.
_EQUIP_SLOTS = [
    ("armor_1", "Armor I", (80, 130, 200)),
    ("armor_2", "Armor II", (100, 150, 220)),
    ("accessory", "Accessory", (180, 160, 50)),
]

# Cursor zones: "grid" for inventory grid, "equip" for equipment slots
_ZONE_GRID = "grid"
_ZONE_EQUIP = "equip"
_EQUIP_PANEL_W = 100


class InventoryScreenState(State):
    def __init__(self, game):
        super().__init__(game)
        self._cx = 0
        self._cy = 0
        self._zone = _ZONE_GRID  # which zone the cursor is in
        self._equip_idx = 0  # 0=armor_1, 1=armor_2, 2=accessory
        self._held_stack = None  # ItemStack being dragged
        self._held_src = None  # ("grid", idx) or ("equip", slot_name)
        self._craft_mgr = CraftingManager()
        self._craft_cursor = 0
        self._craft_msg = ""
        self._craft_msg_timer = 0.0
        self.font = None
        self.small_font = None
        self.tiny_font = None
        self._compact = False
        self._slot_sz = SLOT_SZ
        self._slot_pad = SLOT_PAD
        self._equip_panel_w = _EQUIP_PANEL_W

    def _ensure_fonts(self):
        if self.font is None:
            self.font = get_font(14)
            self.small_font = get_font(12)
            self.tiny_font = get_font(10)

    def enter(self):
        self._cx, self._cy = 0, 0
        self._zone = _ZONE_GRID
        self._equip_idx = 0
        self._held_stack = None
        self._held_src = None

    def update(self, dt):
        if self._craft_msg_timer > 0:
            self._craft_msg_timer -= dt
            if self._craft_msg_timer <= 0:
                self._craft_msg = ""

        inp = self.game.input
        if inp.is_pressed("select") or inp.is_pressed("b") or inp.is_pressed("start"):
            self._cancel_drag()
            self.game.states.change("gameplay")
            return

        if inp.is_pressed("sort"):
            self.game.inventory.grid.auto_sort()

        # Navigation
        if self._zone == _ZONE_GRID:
            if inp.is_pressed("up"):
                self._cy = (self._cy - 1) % INV_ROWS
            elif inp.is_pressed("down"):
                self._cy = (self._cy + 1) % INV_ROWS
            if inp.is_pressed("left"):
                self._cx = (self._cx - 1) % INV_COLS
            elif inp.is_pressed("right"):
                if self._cx == INV_COLS - 1:
                    # Jump to equipment zone
                    self._zone = _ZONE_EQUIP
                    self._equip_idx = min(self._cy, len(_EQUIP_SLOTS) - 1)
                else:
                    self._cx = (self._cx + 1) % INV_COLS
        elif self._zone == _ZONE_EQUIP:
            if inp.is_pressed("up"):
                self._equip_idx = (self._equip_idx - 1) % len(_EQUIP_SLOTS)
            elif inp.is_pressed("down"):
                self._equip_idx = (self._equip_idx + 1) % len(_EQUIP_SLOTS)
            if inp.is_pressed("left"):
                # Jump back to grid
                self._zone = _ZONE_GRID
                self._cx = INV_COLS - 1
                self._cy = min(self._equip_idx, INV_ROWS - 1)
            elif inp.is_pressed("right"):
                pass  # nowhere to go

        if inp.is_pressed("a"):
            self._interact()

        if inp.is_pressed("r"):
            self._quick_equip()

        if inp.is_pressed("craft"):
            self._try_craft_in_menu()

    # ── Interaction (pick / place / equip) ────────────────────────────────────

    def _interact(self):
        if self._zone == _ZONE_GRID:
            self._interact_grid()
        elif self._zone == _ZONE_EQUIP:
            self._interact_equip()

    def _interact_grid(self):
        grid = self.game.inventory.grid
        idx = self._cy * INV_COLS + self._cx

        if self._held_stack is None:
            # Pick up from grid
            stack = grid.slots[idx] if idx < len(grid.slots) else None
            if stack:
                self._held_stack = stack
                self._held_src = (_ZONE_GRID, idx)
                grid.slots[idx] = None
        else:
            # Place into grid
            target = grid.slots[idx] if idx < len(grid.slots) else None
            if target is None:
                grid.slots[idx] = self._held_stack
                self._held_stack = None
                self._held_src = None
            elif target.item_id == self._held_stack.item_id:
                mx = ITEM_DEFS.get(target.item_id, {}).get("stack_max", 1)
                space = mx - target.qty
                move = min(space, self._held_stack.qty)
                target.qty += move
                self._held_stack.qty -= move
                if self._held_stack.qty <= 0:
                    self._held_stack = None
                    self._held_src = None
            else:
                # Swap
                grid.slots[idx] = self._held_stack
                self._held_stack = target
                self._held_src = (_ZONE_GRID, idx)

    def _interact_equip(self):
        equip = self.game.inventory.equipment
        slot_name = _EQUIP_SLOTS[self._equip_idx][0]
        current_id = equip.equipped.get(slot_name)

        if self._held_stack is None:
            # Pick up from equipment slot (unequip)
            if current_id:
                equip.equipped[slot_name] = None
                self._held_stack = ItemStack(current_id, 1)
                self._held_src = (_ZONE_EQUIP, slot_name)
        else:
            # Try to place into equipment slot
            idef = ITEM_DEFS.get(self._held_stack.item_id, {})
            equipped_name = idef.get("name", self._held_stack.item_id)
            if not equip.accepts(slot_name, self._held_stack.item_id):
                if idef.get("equip_slot") == "weapon":
                    self._craft_msg = "Weapons stay in the hotbar."
                else:
                    self._craft_msg = "That item can't go there."
                self._craft_msg_timer = 1.5
                return
            # Swap with current equipment
            prev_id = equip.equip(self._held_stack.item_id, preferred_slot=slot_name)
            if prev_id:
                self._held_stack = ItemStack(prev_id, 1)
                self._held_src = (_ZONE_EQUIP, slot_name)
            else:
                self._held_stack = None
                self._held_src = None
            self._craft_msg = f"Equipped: {equipped_name}"
            self._craft_msg_timer = 2.0

    def _quick_equip(self):
        """E key: auto-equip from grid / auto-unequip from equipment slot."""
        if self._zone == _ZONE_EQUIP:
            equip = self.game.inventory.equipment
            slot_name = _EQUIP_SLOTS[self._equip_idx][0]
            item_id = equip.equipped.get(slot_name)
            if not item_id:
                return
            grid = self.game.inventory.grid
            if grid.add_item(item_id, 1):
                equip.equipped[slot_name] = None
                iname = ITEM_DEFS.get(item_id, {}).get("name", item_id)
                self._craft_msg = f"Unequipped: {iname}"
                self._craft_msg_timer = 2.0
                if hasattr(self.game, "audio"):
                    self.game.audio.play_sfx("menu_select")
            else:
                self._craft_msg = "Inventory full!"
                self._craft_msg_timer = 1.5
            return
        if self._zone != _ZONE_GRID:
            return
        grid = self.game.inventory.grid
        equip = self.game.inventory.equipment
        idx = self._cy * INV_COLS + self._cx
        stack = grid.slots[idx] if idx < len(grid.slots) else None
        if not stack:
            return
        idef = ITEM_DEFS.get(stack.item_id, {})
        slot_type = idef.get("equip_slot")
        if slot_type == "weapon":
            self._craft_msg = "Weapons stay in the hotbar."
            self._craft_msg_timer = 1.5
            return
        if not slot_type or not equip.compatible_slots(stack.item_id):
            self._craft_msg = "Can't equip that."
            self._craft_msg_timer = 1.5
            return
        prev_id = equip.equip(stack.item_id)
        grid.slots[idx] = None
        if prev_id:
            grid.slots[idx] = ItemStack(prev_id, 1)
        self._craft_msg = f"Equipped: {idef.get('name', stack.item_id)}"
        self._craft_msg_timer = 2.0
        if hasattr(self.game, "audio"):
            self.game.audio.play_sfx("menu_select")

    def _cancel_drag(self):
        if self._held_stack is not None:
            self.game.inventory.grid.add_item(
                self._held_stack.item_id, self._held_stack.qty
            )
            self._held_stack = None
            self._held_src = None

    def _try_craft_in_menu(self):
        inv = self.game.inventory
        available = [
            rid
            for rid in self._craft_mgr.recipes
            if self._craft_mgr.can_craft(
                rid, inv.grid, inv.craft_bag, ignore_station=True
            )
        ]
        if not available:
            self._craft_msg = "No craftable recipes."
            self._craft_msg_timer = 2.0
            return
        self._craft_cursor = self._craft_cursor % len(available)
        rid = available[self._craft_cursor]
        result = self._craft_mgr.craft(
            rid, inv.grid, inv.craft_bag, ignore_station=True
        )
        if result:
            name = ITEM_DEFS.get(result["item_id"], {}).get("name", result["item_id"])
            self._craft_msg = f"Crafted: {name}!"
            self._craft_msg_timer = 3.0
            if hasattr(self.game, "audio"):
                self.game.audio.play_sfx("craft")
        self._craft_cursor += 1

    # ── Render ────────────────────────────────────────────────────────────────

    def render(self, screen):
        self._ensure_fonts()
        vw, vh = self._viewport_size(screen)
        self._compact = self._is_compact_view(screen)
        self._slot_sz = 18 if self._compact else SLOT_SZ
        self._slot_pad = 2 if self._compact else SLOT_PAD
        self._equip_panel_w = 72 if self._compact else _EQUIP_PANEL_W

        dim = pygame.Surface((vw, vh), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 210))
        screen.blit(dim, (0, 0))

        if self._compact:
            self._render_compact(screen, vw, vh)
            return

        px, py = 14, 12
        pw, ph = vw - 28, vh - 24

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((*_BG, 245))
        screen.blit(panel, (px, py))
        pygame.draw.rect(screen, _BORDER_LT, (px, py, pw, ph), 1, border_radius=5)
        pygame.draw.rect(
            screen, _BORDER, (px + 1, py + 1, pw - 2, ph - 2), 1, border_radius=4
        )

        self._draw_header(screen, px, py, pw)
        div_y = py + 30
        pygame.draw.line(screen, _BORDER, (px + 8, div_y), (px + pw - 8, div_y))
        content_y = div_y + 6

        grid_x = px + 14
        grid_cols_w = INV_COLS * (SLOT_SZ + SLOT_PAD) - SLOT_PAD

        # Equipment slots to the right of grid
        equip_x = grid_x + grid_cols_w + 10
        equip_w = _EQUIP_PANEL_W

        # Detail panel to the right of equipment
        detail_x = equip_x + equip_w + 10
        detail_w = pw - (detail_x - px) - 10

        self._draw_grid(screen, grid_x, content_y)
        self._draw_equip_slots(screen, equip_x, content_y)

        hotbar_y = content_y + INV_ROWS * (SLOT_SZ + SLOT_PAD) + 6
        self._draw_hotbar_strip(screen, grid_x, hotbar_y)

        self._draw_detail_panel(screen, detail_x, content_y, detail_w, ph - 40)

        craft_y = hotbar_y + SLOT_SZ + 10
        self._draw_craft_section(screen, grid_x, craft_y, grid_cols_w)

        if self._held_stack:
            self._draw_held_indicator(screen, px, py, pw)

        footer = (
            "TAB/B=Close  Arrows=Nav  A=Pick/Place  E=Equip/Unequip  C=Craft  F6=Sort"
        )
        fs = self.tiny_font.render(footer, True, _TEXT_DIM)
        screen.blit(fs, (px + pw // 2 - fs.get_width() // 2, py + ph - 14))

    def _render_compact(self, screen, vw, vh):
        px, py = 4, 4
        pw, ph = vw - 8, vh - 8

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((*_BG, 245))
        screen.blit(panel, (px, py))
        pygame.draw.rect(screen, _BORDER_LT, (px, py, pw, ph), 1, border_radius=5)
        pygame.draw.rect(
            screen, _BORDER, (px + 1, py + 1, pw - 2, ph - 2), 1, border_radius=4
        )

        self._draw_header(screen, px, py, pw)
        div_y = py + 24
        pygame.draw.line(screen, _BORDER, (px + 8, div_y), (px + pw - 8, div_y))
        content_y = div_y + 6

        grid_x = px + 8
        grid_cols_w = INV_COLS * (self._slot_sz + self._slot_pad) - self._slot_pad
        equip_x = px + pw - self._equip_panel_w - 8
        top_h = max(
            INV_ROWS * (self._slot_sz + self._slot_pad) - self._slot_pad,
            (len(_EQUIP_SLOTS) - 1) * (self._slot_sz + 10) + self._slot_sz + 8,
        )

        self._draw_grid(screen, grid_x, content_y)
        self._draw_equip_slots(screen, equip_x, content_y)

        detail_y = content_y + top_h + 4
        detail_h = max(24, py + ph - detail_y - 18)
        self._draw_detail_panel(screen, px + 8, detail_y, pw - 16, detail_h)

        if self._held_stack:
            self._draw_held_indicator(screen, px, py, pw)

        active = self.game.inventory.grid.active_hotbar + 1
        footer = f"B Close  A Move  E Equip  C Craft  HB:{active}"
        fs = self.tiny_font.render(footer, True, _TEXT_DIM)
        screen.blit(fs, (px + pw // 2 - fs.get_width() // 2, py + ph - 12))

    # ── Header ────────────────────────────────────────────────────────────────

    def _draw_header(self, screen, px, py, pw):
        ts = self.font.render("INVENTORY", True, COLOR_ACCENT)
        screen.blit(ts, (px + 12, py + 8))
        coins = int(self.game.wallet.coins)
        cs = self.small_font.render(f"  {coins} coins", True, (248, 210, 55))
        screen.blit(cs, (px + pw - cs.get_width() - 12, py + 8))
        prog = getattr(self.game, "progression", None)
        if prog:
            lv_s = self.tiny_font.render(f"LV {prog.level}", True, _TEXT_MID)
            screen.blit(
                lv_s, (px + pw - cs.get_width() - lv_s.get_width() - 22, py + 10)
            )

    # ── Grid ──────────────────────────────────────────────────────────────────

    def _draw_grid(self, screen, gx, gy):
        slots = self.game.inventory.grid.slots
        for row in range(INV_ROWS):
            for col in range(INV_COLS):
                idx = row * INV_COLS + col
                sx = gx + col * (self._slot_sz + self._slot_pad)
                sy = gy + row * (self._slot_sz + self._slot_pad)
                stack = slots[idx] if idx < len(slots) else None
                selected = (
                    self._zone == _ZONE_GRID and col == self._cx and row == self._cy
                )
                is_held_src = self._held_src == (_ZONE_GRID, idx)
                self._draw_slot(screen, sx, sy, stack, selected, is_held_src)

    # ── Equipment slots (Minecraft-style) ────────────────────────────────────

    def _draw_equip_slots(self, screen, ex, ey):
        equip = self.game.inventory.equipment

        # Panel background
        panel_w = self._equip_panel_w
        slot_spacing = self._slot_sz + (10 if self._compact else 17)
        panel_h = (len(_EQUIP_SLOTS) - 1) * slot_spacing + self._slot_sz + 8
        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg.fill((*_PANEL, 180))
        screen.blit(bg, (ex - 4, ey - 2))
        pygame.draw.rect(
            screen, _BORDER_LT, (ex - 4, ey - 2, panel_w, panel_h), 1, border_radius=5
        )

        # Title
        title = self.tiny_font.render(
            "EQUIP" if self._compact else "EQUIPMENT", True, _TEXT_MID
        )
        screen.blit(title, (ex, ey - 13))

        for i, (slot_name, slot_label, slot_color) in enumerate(_EQUIP_SLOTS):
            sx = ex
            sy = ey + 2 + i * slot_spacing

            selected = self._zone == _ZONE_EQUIP and self._equip_idx == i
            is_held_src = self._held_src == (_ZONE_EQUIP, slot_name)

            # Check if held item can go in this slot (valid drop target)
            is_valid_target = False
            if self._held_stack and not is_held_src:
                if equip.accepts(slot_name, self._held_stack.item_id):
                    is_valid_target = True

            # Slot type label
            compact_label = {"Armor I": "A1", "Armor II": "A2", "Accessory": "ACC"}.get(
                slot_label, slot_label
            )
            lbl = self.tiny_font.render(
                compact_label if self._compact else slot_label, True, slot_color
            )
            screen.blit(lbl, (sx + self._slot_sz + 4, sy + 2))

            # Equipped item name or "empty"
            item_id = equip.equipped.get(slot_name)
            if item_id:
                iname = ITEM_DEFS.get(item_id, {}).get("name", item_id)
                max_w = panel_w - self._slot_sz - 12
                ns = self.tiny_font.render(iname, True, _TEXT_BRT)
                if ns.get_width() > max_w:
                    while (
                        len(iname) > 3 and self.tiny_font.size(iname + "..")[0] > max_w
                    ):
                        iname = iname[:-1]
                    ns = self.tiny_font.render(iname + "..", True, _TEXT_BRT)
                screen.blit(
                    ns, (sx + self._slot_sz + 4, sy + (12 if self._compact else 14))
                )
            else:
                es = self.tiny_font.render("empty", True, (45, 48, 62))
                screen.blit(
                    es, (sx + self._slot_sz + 4, sy + (12 if self._compact else 14))
                )

            stack = ItemStack(item_id, 1) if item_id else None

            # Valid drop target glow (behind slot)
            if is_valid_target:
                t = get_time() * (1000.0 / 400.0)
                alpha = int(40 + 35 * math.sin(t))
                glow = pygame.Surface(
                    (self._slot_sz + 6, self._slot_sz + 6), pygame.SRCALPHA
                )
                glow.fill((*slot_color, alpha))
                screen.blit(glow, (sx - 3, sy - 3))

            self._draw_slot(
                screen, sx, sy, stack, selected, is_held_src, border_color=slot_color
            )

            # Placeholder icon for empty slots
            if not stack and not is_held_src:
                self._draw_placeholder_icon(screen, slot_name, sx, sy)

    def _draw_placeholder_icon(self, screen, slot_type, x, y):
        """Draw a dim silhouette icon in an empty equipment slot."""
        dim = (35, 38, 55)
        cx = x + self._slot_sz // 2
        cy = y + self._slot_sz // 2
        h = (self._slot_sz - 14) // 2

        if slot_type.startswith("armor"):
            pts = [
                (cx, cy - h),
                (cx + h, cy - h // 2),
                (cx + h - 1, cy + h // 2),
                (cx, cy + h),
                (cx - h + 1, cy + h // 2),
                (cx - h, cy - h // 2),
            ]
            pygame.draw.polygon(screen, dim, pts, 2)
        elif slot_type == "accessory":
            pygame.draw.circle(screen, dim, (cx, cy + 2), h - 2, 2)
            pygame.draw.circle(screen, dim, (cx, cy - h + 4), max(h // 3, 2), 1)

    # ── Shared slot renderer ──────────────────────────────────────────────────

    def _draw_slot(
        self,
        screen,
        sx,
        sy,
        stack,
        selected=False,
        is_held_src=False,
        border_color=None,
    ):
        if selected:
            bg = _SLOT_SEL
        elif is_held_src:
            bg = (22, 14, 8)
        else:
            bg = _SLOT_BG

        pygame.draw.rect(
            screen, bg, (sx, sy, self._slot_sz, self._slot_sz), border_radius=3
        )

        if selected:
            t = get_time() * (1000.0 / 700.0)
            p = 0.55 + 0.45 * math.sin(t)
            bc = border_color or (int(65 * p + 45), int(90 * p + 60), int(240 * p + 10))
            if border_color:
                bc = tuple(int(c * (0.6 + 0.4 * p)) for c in border_color)
            pygame.draw.rect(
                screen, bc, (sx, sy, self._slot_sz, self._slot_sz), 2, border_radius=3
            )
        elif is_held_src:
            pygame.draw.rect(
                screen,
                (130, 85, 28),
                (sx, sy, self._slot_sz, self._slot_sz),
                1,
                border_radius=3,
            )
        elif border_color:
            dim_bc = tuple(c // 3 for c in border_color)
            pygame.draw.rect(
                screen,
                dim_bc,
                (sx, sy, self._slot_sz, self._slot_sz),
                1,
                border_radius=3,
            )
        else:
            pygame.draw.rect(
                screen,
                _BORDER,
                (sx, sy, self._slot_sz, self._slot_sz),
                1,
                border_radius=3,
            )

        if not stack:
            return

        idef = ITEM_DEFS.get(stack.item_id, {})
        rarity = idef.get("loot_tier", idef.get("rarity", "common"))
        rc = RARITY_COLORS.get(rarity, (165, 165, 178))
        tint = pygame.Surface((self._slot_sz - 4, self._slot_sz - 4), pygame.SRCALPHA)
        tint.fill((rc[0] // 9, rc[1] // 9, rc[2] // 9, 55))
        screen.blit(tint, (sx + 2, sy + 2))

        draw_item_icon(
            screen, stack.item_id, sx + 5, sy + 5, max(8, self._slot_sz - 10)
        )

        if stack.qty > 1:
            qs = self.tiny_font.render(str(stack.qty), True, (218, 218, 88))
            screen.blit(
                qs,
                (
                    sx + self._slot_sz - qs.get_width() - 2,
                    sy + self._slot_sz - qs.get_height() - 1,
                ),
            )

    # ── Hotbar strip ──────────────────────────────────────────────────────────

    def _draw_hotbar_strip(self, screen, hx, hy):
        inv = self.game.inventory
        active = inv.grid.active_hotbar
        label = self.tiny_font.render("HOTBAR", True, _TEXT_DIM)
        screen.blit(label, (hx, hy - 11))

        for i in range(HOTBAR_SIZE):
            sx = hx + i * (self._slot_sz + self._slot_pad)
            stack = inv.grid.slots[i] if i < len(inv.grid.slots) else None
            is_held_src = self._held_src == (_ZONE_GRID, i)
            self._draw_slot(screen, sx, hy, stack, False, is_held_src)
            num_s = self.tiny_font.render(str(i + 1), True, _TEXT_DIM)
            screen.blit(num_s, (sx + 2, hy + 2))
            if i == active:
                pygame.draw.rect(
                    screen,
                    (78, 118, 200),
                    (sx, hy, self._slot_sz, self._slot_sz),
                    2,
                    border_radius=3,
                )

    # ── Detail panel ──────────────────────────────────────────────────────────

    def _draw_detail_panel(self, screen, dx, dy, dw, dh):
        dpanel = pygame.Surface((dw, dh), pygame.SRCALPHA)
        dpanel.fill((*_PANEL, 200))
        screen.blit(dpanel, (dx, dy))
        pygame.draw.rect(screen, _BORDER, (dx, dy, dw, dh), 1, border_radius=4)

        cy = dy + 8

        # Determine what to show detail for
        stack = None
        if self._held_stack:
            stack = self._held_stack
        elif self._zone == _ZONE_GRID:
            sel_idx = self._cy * INV_COLS + self._cx
            stack = (
                self.game.inventory.grid.slots[sel_idx]
                if sel_idx < len(self.game.inventory.grid.slots)
                else None
            )
        elif self._zone == _ZONE_EQUIP:
            slot_name = _EQUIP_SLOTS[self._equip_idx][0]
            item_id = self.game.inventory.equipment.equipped.get(slot_name)
            if item_id:
                stack = ItemStack(item_id, 1)

        if stack:
            self._draw_item_detail(
                screen, dx, cy, dw, stack, holding=self._held_stack is not None
            )
        else:
            empty_s = self.tiny_font.render("[ select an item ]", True, _TEXT_DIM)
            screen.blit(empty_s, (dx + dw // 2 - empty_s.get_width() // 2, cy + 18))

    def _draw_item_detail(self, screen, dx, dy, dw, stack, holding=False):
        idef = ITEM_DEFS.get(stack.item_id, {})
        name = idef.get("name", stack.item_id)
        desc = idef.get("desc", "")
        stats = idef.get("stats", {})
        rarity = idef.get("loot_tier", idef.get("rarity", "common"))
        rc = RARITY_COLORS.get(rarity, (165, 165, 178))
        cy = dy

        if self._compact:
            icon_sz = min(18, max(12, dw - 12))
            draw_item_icon(screen, stack.item_id, dx + 6, cy + 4, icon_sz)

            max_name_w = dw - icon_sz - 18
            title = name
            while len(title) > 3 and self.small_font.size(title)[0] > max_name_w:
                title = title[:-1]
            if title != name:
                title += ".."
            ns = self.small_font.render(title, True, rc)
            screen.blit(ns, (dx + icon_sz + 10, cy + 4))

            meta = f"{rarity}"
            if stack.qty > 1:
                meta += f" x{stack.qty}"
            ms = self.tiny_font.render(meta, True, _TEXT_MID)
            screen.blit(ms, (dx + icon_sz + 10, cy + 16))
            return

        if holding:
            hs = self.tiny_font.render("HOLDING", True, (188, 128, 45))
            screen.blit(hs, (dx + dw // 2 - hs.get_width() // 2, cy))
            cy += 13

        icon_sz = min(36, dw - 16)
        draw_item_icon(screen, stack.item_id, dx + dw // 2 - icon_sz // 2, cy, icon_sz)
        cy += icon_sz + 6

        ns = self.small_font.render(name, True, rc)
        screen.blit(ns, (dx + dw // 2 - ns.get_width() // 2, cy))
        cy += 15

        rt = self.tiny_font.render(f"[{rarity}]", True, tuple(v // 2 + 50 for v in rc))
        screen.blit(rt, (dx + dw // 2 - rt.get_width() // 2, cy))
        cy += 14

        pygame.draw.line(screen, _BORDER, (dx + 4, cy), (dx + dw - 4, cy))
        cy += 6

        if desc:
            words = desc.split()
            line = ""
            for word in words:
                test = (line + " " + word).strip()
                if self.tiny_font.size(test)[0] > dw - 12:
                    if line:
                        ds = self.tiny_font.render(line, True, _TEXT_MID)
                        screen.blit(ds, (dx + 5, cy))
                        cy += 12
                    line = word
                else:
                    line = test
            if line:
                ds = self.tiny_font.render(line, True, _TEXT_MID)
                screen.blit(ds, (dx + 5, cy))
                cy += 13

        if stats:
            cy += 2
            for k, v in stats.items():
                sv = f"+{v}" if isinstance(v, (int, float)) and v >= 0 else str(v)
                ss = self.tiny_font.render(f"  {sv} {k}", True, (88, 218, 108))
                screen.blit(ss, (dx + 4, cy))
                cy += 12

        if stack.qty > 1:
            qs = self.tiny_font.render(f"qty: {stack.qty}", True, _TEXT_DIM)
            screen.blit(qs, (dx + dw // 2 - qs.get_width() // 2, cy + 4))

    # ── Crafting section ──────────────────────────────────────────────────────

    def _draw_craft_section(self, screen, cx, cy, cw):
        label = self.tiny_font.render("CRAFTING (C to craft)", True, _TEXT_DIM)
        screen.blit(label, (cx, cy))
        cy += 13

        inv = self.game.inventory
        available = []
        for rid, recipe in self._craft_mgr.recipes.items():
            can = self._craft_mgr.can_craft(
                rid, inv.grid, inv.craft_bag, ignore_station=True
            )
            available.append((rid, recipe, can))

        if not any(c for _, _, c in available):
            ns = self.tiny_font.render("No recipes available", True, _TEXT_DIM)
            screen.blit(ns, (cx + 4, cy))
        else:
            shown = 0
            for rid, recipe, can in available:
                if not can:
                    continue
                if shown >= 3:
                    more = self.tiny_font.render("...", True, _TEXT_DIM)
                    screen.blit(more, (cx + 4, cy))
                    break
                col = (88, 218, 108) if can else _TEXT_DIM
                name = recipe.get("name", rid)
                ings = ", ".join(
                    f"{i['qty']}x {ITEM_DEFS.get(i['item_id'], {}).get('name', i['item_id'])}"
                    for i in recipe["ingredients"]
                )
                rs = self.tiny_font.render(f"{name}  ({ings})", True, col)
                screen.blit(rs, (cx + 4, cy))
                cy += 12
                shown += 1

        if self._craft_msg:
            alpha = min(1.0, self._craft_msg_timer / 0.4) * 255
            ms = self.small_font.render(self._craft_msg, True, (180, 218, 100))
            ms.set_alpha(int(alpha))
            screen.blit(ms, (cx + 4, cy + 4))

    # ── Held indicator ────────────────────────────────────────────────────────

    def _draw_held_indicator(self, screen, px, py, pw):
        sz = 26 if self._compact else 36
        hx = px + pw - sz - 12
        hy = py + (32 if self._compact else 40)

        bg = pygame.Surface((sz + 4, sz + 4), pygame.SRCALPHA)
        bg.fill((38, 22, 8, 210))
        screen.blit(bg, (hx - 2, hy - 2))
        pygame.draw.rect(
            screen, (195, 135, 38), (hx - 2, hy - 2, sz + 4, sz + 4), 1, border_radius=3
        )

        draw_item_icon(screen, self._held_stack.item_id, hx + 5, hy + 5, sz - 10)

        hs = self.tiny_font.render("HELD", True, (185, 130, 38))
        screen.blit(hs, (hx + sz // 2 - hs.get_width() // 2, hy - 11))
