"""
HUD — health hearts, hotbar, XP bar, mini-map, quest objective strip,
boss HP bar, notifications.  All drawn in screen-space after world render.

Visual direction: premium retro-fantasy.  Clean, readable, no clutter.
"""
import math
import pygame
from runtime.frame_clock import get_time
from runtime.display_defaults import (
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_VIEWPORT_WIDTH,
)
from settings import (
    COLOR_WHITE, COLOR_ACCENT,
    COLOR_BOSS_HP,
    HOTBAR_SIZE,
    MINIMAP_W, MINIMAP_H,
)
from item_system import draw_item_icon
from ui.fonts import get_font


# Palette
_GOLD        = (248, 210, 55)
_HEART_FULL  = (210, 45,  45)
_HEART_EMPTY = (50,  18,  18)
_HEART_SH    = (140, 20,  20)
_XP_BAR      = (68, 135, 218)
_QUEST_BG    = (0,   0,   0,  130)
_NOTIF_BG    = (0,   0,   0,  155)


class HUD:
    def __init__(
        self,
        viewport_width: int = DEFAULT_VIEWPORT_WIDTH,
        viewport_height: int = DEFAULT_VIEWPORT_HEIGHT,
    ):
        self.font       = None
        self.small_font = None
        self.tiny_font  = None
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.notification  = ""
        self.notif_timer   = 0.0
        self.notif_duration = 3.0
        self.boss_ref      = None

        self.show_minimap  = True
        self.show_hotbar   = True
        self.show_xp_bar   = True
        self.hud_opacity   = 1.0

        self._notif_queue: list[tuple[str, float]] = []
        self._minimap_surf: pygame.Surface | None = None
        self._minimap_map: str = ""
        self._minimap_dims: tuple[int, int] = (MINIMAP_W, MINIMAP_H)
        self.in_combat = False

    def set_viewport_size(self, width: int, height: int):
        width = max(1, int(width))
        height = max(1, int(height))
        if (width, height) != (self.viewport_width, self.viewport_height):
            self.viewport_width = width
            self.viewport_height = height
            self._minimap_surf = None

    def _sync_viewport(self, screen):
        if screen is not None and hasattr(screen, "get_size"):
            self.set_viewport_size(*screen.get_size())

    def _hotbar_layout(self) -> tuple[int, int, int, int, int]:
        pad = 3 if self.viewport_width >= 320 else 2
        available_w = max(120, self.viewport_width - 16)
        slot_sz = min(34, max(20, (available_w - pad * (HOTBAR_SIZE - 1)) // HOTBAR_SIZE))
        total_w = HOTBAR_SIZE * (slot_sz + pad) - pad
        hx = max(8, self.viewport_width // 2 - total_w // 2)
        hy = max(8, self.viewport_height - slot_sz - 8)
        return hx, hy, slot_sz, pad, total_w

    def _xp_bar_layout(self) -> tuple[int, int, int, int]:
        _, hotbar_y, _, _, _ = self._hotbar_layout()
        bar_w = min(160, max(84, self.viewport_width - 120))
        bar_h = 5
        bx = self.viewport_width // 2 - bar_w // 2
        by = max(28, hotbar_y - 10)
        return bx, by, bar_w, bar_h

    def _minimap_layout(self) -> tuple[int, int, int, int]:
        if self.viewport_width >= 320 and self.viewport_height >= 220:
            mm_w, mm_h = MINIMAP_W, MINIMAP_H
            my = self.viewport_height - mm_h - 8
        else:
            mm_w = max(48, min(MINIMAP_W, self.viewport_width // 4))
            mm_h = max(36, min(MINIMAP_H, self.viewport_height // 4))
            _, hotbar_y, _, _, _ = self._hotbar_layout()
            my = max(8, hotbar_y - mm_h - 10)
        mx = self.viewport_width - mm_w - 8
        return mx, my, mm_w, mm_h

    def _ensure_fonts(self):
        if self.font is None:
            self.font       = get_font(14)
            self.small_font = get_font(12)
            self.tiny_font  = get_font(10)

    def show_notification(self, text: str, duration: float = 3.0):
        self.notification    = text
        self.notif_timer     = duration
        self.notif_duration  = duration
        self._notif_queue.append((text, duration))

    def update(self, dt: float):
        if self.notif_timer > 0:
            self.notif_timer -= dt
        if not self.notif_timer and self._notif_queue:
            self._notif_queue.pop(0)
            if self._notif_queue:
                self.notification, self.notif_timer = self._notif_queue[0]

    # ── Main render entry ──────────────────────────────────────────────────────

    def render(self, screen, player, inventory, quest_manager, map_name="",
               difficulty_label="", coins=0, progression=None,
               tilemap=None, camera=None, reputation=None, campaign=None):
        self._ensure_fonts()
        self._sync_viewport(screen)
        alpha = max(0, min(255, int(self.hud_opacity * 255)))

        hud = pygame.Surface((self.viewport_width, self.viewport_height), pygame.SRCALPHA)

        self._draw_health(hud, player)
        self._draw_top_right(hud, map_name, difficulty_label, coins)
        world_stage = getattr(campaign, "world_stage", 1) if campaign else 1
        self._draw_quest_strip(hud, quest_manager, world_stage)

        if self.show_hotbar:
            self._draw_hotbar(hud, inventory)

        if self.show_xp_bar and progression:
            self._draw_xp_bar(hud, progression)

        if self.show_minimap and tilemap and camera:
            self._draw_minimap(hud, tilemap, player, camera, map_name)

        self._draw_boss_bar(hud)
        self._draw_notification(hud)

        if alpha < 255:
            hud.set_alpha(alpha)
        screen.blit(hud, (0, 0))

    # ── Health hearts ──────────────────────────────────────────────────────────

    def _draw_health(self, surf, player):
        sz  = 15
        pad = 3
        hx, hy = 8, 7

        partial = getattr(player, "partial_hp", 0.0)
        for i in range(player.max_hp):
            x = hx + i * (sz + pad)
            full = i < player.hp
            half = (not full) and (i == player.hp) and partial >= 0.5
            self._draw_heart(surf, x, hy, sz, full, half)

        # Low-HP warning glow
        if player.hp <= 1:
            t = get_time() * (1000.0 / 280.0)
            p = abs(math.sin(t))
            glow = pygame.Surface((sz + 10, sz + 10), pygame.SRCALPHA)
            pygame.draw.circle(glow, (220 + int(30 * p), 28, 28, int(55 * p)),
                               (sz // 2 + 5, sz // 2 + 5), sz // 2 + 4)
            surf.blit(glow, (hx - 5, hy - 5))

    def _draw_heart(self, surf, x, y, sz, full: bool, half: bool = False):
        s   = sz
        hs  = s // 2
        sh  = _HEART_SH if (full or half) else (30, 10, 10)
        # Shadow offset (always draw with empty-ish shadow)
        pygame.draw.circle(surf, sh, (x + hs // 2 + 2, y + hs // 2 + 1), hs // 2 + 1)
        pygame.draw.circle(surf, sh, (x + s - hs // 2 - 1 + 1, y + hs // 2 + 1), hs // 2 + 1)
        sh_pts = [(x + 1, y + hs // 2 + 1), (x + s + 1, y + hs // 2 + 1), (x + hs + 1, y + s + 1)]
        pygame.draw.polygon(surf, sh, sh_pts)

        if full:
            # Full heart
            col = _HEART_FULL
            pygame.draw.circle(surf, col, (x + hs // 2 + 1, y + hs // 2), hs // 2 + 1)
            pygame.draw.circle(surf, col, (x + s - hs // 2 - 1, y + hs // 2), hs // 2 + 1)
            pts = [(x, y + hs // 2), (x + s, y + hs // 2), (x + hs, y + s)]
            pygame.draw.polygon(surf, col, pts)
            pygame.draw.circle(surf, (240, 100, 100),
                               (x + hs // 2 - 1, y + hs // 2 - 1), max(1, hs // 4))
        elif half:
            # Empty base, then fill only the left lobe
            pygame.draw.circle(surf, _HEART_EMPTY, (x + hs // 2 + 1, y + hs // 2), hs // 2 + 1)
            pygame.draw.circle(surf, _HEART_EMPTY, (x + s - hs // 2 - 1, y + hs // 2), hs // 2 + 1)
            pts = [(x, y + hs // 2), (x + s, y + hs // 2), (x + hs, y + s)]
            pygame.draw.polygon(surf, _HEART_EMPTY, pts)
            pygame.draw.circle(surf, _HEART_FULL, (x + hs // 2 + 1, y + hs // 2), hs // 2 + 1)
            pygame.draw.circle(surf, (240, 100, 100),
                               (x + hs // 2 - 1, y + hs // 2 - 1), max(1, hs // 4))
        else:
            # Empty heart
            col = _HEART_EMPTY
            pygame.draw.circle(surf, col, (x + hs // 2 + 1, y + hs // 2), hs // 2 + 1)
            pygame.draw.circle(surf, col, (x + s - hs // 2 - 1, y + hs // 2), hs // 2 + 1)
            pts = [(x, y + hs // 2), (x + s, y + hs // 2), (x + hs, y + s)]
            pygame.draw.polygon(surf, col, pts)

    # ── Top-right info ─────────────────────────────────────────────────────────

    def _draw_top_right(self, surf, map_name, difficulty_label, coins):
        right = self.viewport_width - 8

        if map_name:
            ms = self.font.render(map_name.upper(), True, (128, 130, 145))
            surf.blit(ms, (right - ms.get_width(), 6))

        if difficulty_label:
            ds = self.tiny_font.render(difficulty_label.upper(), True, (110, 118, 158))
            surf.blit(ds, (right - ds.get_width(), 22))

        # Coin display with mini icon area
        coin_str = f"{int(coins):,}"
        cs = self.small_font.render(coin_str, True, _GOLD)
        cw = cs.get_width() + 18
        cbg = pygame.Surface((cw + 4, 17), pygame.SRCALPHA)
        cbg.fill((0, 0, 0, 100))
        surf.blit(cbg, (right - cw - 4, 34))
        # Gold dot
        pygame.draw.circle(surf, _GOLD, (right - cw - 1, 42), 4)
        pygame.draw.circle(surf, (200, 160, 30), (right - cw - 1, 42), 4, 1)
        surf.blit(cs, (right - cw + 8, 35))

    # ── Quest objective strip ──────────────────────────────────────────────────

    def _draw_quest_strip(self, surf, quest_manager, world_stage: int = 1):
        quest_key = {1: "main", 2: "main_s2", 3: "main_s3"}.get(world_stage, "main")
        main = quest_manager.get_quest(quest_key)
        if not main or main.complete:
            return

        desc = main.current_desc
        if not desc:
            return

        t       = get_time() * (1000.0 / 2200.0)
        chevron = ">" if int(t * 2) % 2 == 0 else " "
        label   = f"{chevron} {desc}"

        ls  = self.small_font.render(label, True, (210, 208, 155))
        pad = 8
        bw  = ls.get_width() + pad * 2
        bh  = 18

        # Background pill
        bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 118))
        bx = 6
        by = 44
        surf.blit(bg, (bx, by))
        pygame.draw.rect(surf, (55, 55, 38), (bx, by, bw, bh), 1)
        surf.blit(ls, (bx + pad, by + 2))

    # ── Hotbar ─────────────────────────────────────────────────────────────────

    def _draw_hotbar(self, surf, inventory):
        hx, hy, slot_sz, pad, total_w = self._hotbar_layout()

        hotbar   = inventory.grid.hotbar[:HOTBAR_SIZE]
        active   = inventory.grid.active_hotbar

        # Background tray
        tray_w = total_w + 10
        tray   = pygame.Surface((tray_w, slot_sz + 8), pygame.SRCALPHA)
        tray.fill((0, 0, 0, 90))
        surf.blit(tray, (hx - 5, hy - 4))
        pygame.draw.rect(surf, (38, 40, 55),
                         (hx - 5, hy - 4, tray_w, slot_sz + 8), 1, border_radius=3)

        for i, stack in enumerate(hotbar):
            sx      = hx + i * (slot_sz + pad)
            is_act  = (i == active)

            # Slot bg
            if is_act:
                bg_c = (28, 32, 55)
            else:
                bg_c = (14, 16, 28)
            pygame.draw.rect(surf, bg_c, (sx, hy, slot_sz, slot_sz), border_radius=3)

            # Border
            if is_act:
                t  = get_time() * (1000.0 / 600.0)
                p  = 0.6 + 0.4 * math.sin(t)
                bc = (int(58 * p + 38), int(88 * p + 58), int(228 * p + 22))
                pygame.draw.rect(surf, bc, (sx, hy, slot_sz, slot_sz), 2, border_radius=3)
            else:
                pygame.draw.rect(surf, (38, 40, 55), (sx, hy, slot_sz, slot_sz), 1, border_radius=3)

            if stack:
                draw_item_icon(surf, stack.item_id, sx + 5, hy + 5, slot_sz - 10)
                if stack.qty > 1:
                    qs = self.tiny_font.render(str(stack.qty), True, (218, 218, 80))
                    surf.blit(qs, (sx + slot_sz - qs.get_width() - 2,
                                   hy + slot_sz - qs.get_height() - 1))

        # Number labels below
        for i in range(HOTBAR_SIZE):
            sx  = hx + i * (slot_sz + pad)
            ns  = self.tiny_font.render(str(i + 1), True, (55, 58, 72))
            surf.blit(ns, (sx + 2, hy + 2))

    # ── XP bar ─────────────────────────────────────────────────────────────────

    def _draw_xp_bar(self, surf, progression):
        bx, by, bar_w, bar_h = self._xp_bar_layout()

        ratio = progression.level_progress_ratio

        # Shadow
        sbg = pygame.Surface((bar_w + 4, bar_h + 4), pygame.SRCALPHA)
        sbg.fill((0, 0, 0, 90))
        surf.blit(sbg, (bx - 2, by - 2))

        # Track
        pygame.draw.rect(surf, (22, 24, 38), (bx, by, bar_w, bar_h))

        # Fill
        fill_w = int(bar_w * ratio)
        if fill_w > 0:
            pygame.draw.rect(surf, _XP_BAR, (bx, by, fill_w, bar_h))
            # Shine strip
            if fill_w > 4:
                pygame.draw.rect(surf, (108, 175, 245), (bx, by, fill_w, 2))

        # Frame
        pygame.draw.rect(surf, (48, 52, 72), (bx, by, bar_w, bar_h), 1)

        # Level label
        lv  = self.tiny_font.render(f"LV {progression.level}", True, (118, 140, 198))
        surf.blit(lv, (bx - lv.get_width() - 4, by - 1))

        if progression.skill_points > 0:
            sp  = self.tiny_font.render(f"SP:{progression.skill_points}", True, (252, 215, 72))
            surf.blit(sp, (bx + bar_w + 4, by - 1))

    # ── Mini-map ────────────────────────────────────────────────────────────────

    def _draw_minimap(self, surf, tilemap, player, camera, map_name):
        mx, my, mm_w, mm_h = self._minimap_layout()

        if (
            self._minimap_map != map_name
            or self._minimap_surf is None
            or self._minimap_dims != (mm_w, mm_h)
        ):
            self._build_minimap(tilemap, mm_w, mm_h)
            self._minimap_map = map_name
            self._minimap_dims = (mm_w, mm_h)

        # Frame + shadow
        sh = pygame.Surface((mm_w + 6, mm_h + 6), pygame.SRCALPHA)
        sh.fill((0, 0, 0, 80))
        surf.blit(sh, (mx - 3, my - 3))

        surf.blit(self._minimap_surf, (mx, my))
        pygame.draw.rect(surf, (65, 68, 85), (mx - 1, my - 1, mm_w + 2, mm_h + 2), 1)

        # Player dot
        px = mx + int((player.x / max(1, tilemap.width)) * mm_w)
        py = my + int((player.y / max(1, tilemap.height)) * mm_h)
        px = max(mx + 2, min(mx + mm_w - 3, px))
        py = max(my + 2, min(my + mm_h - 3, py))
        pygame.draw.circle(surf, (68, 220, 118), (px, py), 3)
        pygame.draw.circle(surf, (28, 160, 78),  (px, py), 3, 1)

    def _build_minimap(self, tilemap, mm_w: int, mm_h: int):
        self._minimap_surf = pygame.Surface((mm_w, mm_h))
        self._minimap_surf.fill((14, 14, 22))
        row_step = max(1, math.ceil(tilemap.height / max(1, mm_h)))
        col_step = max(1, math.ceil(tilemap.width / max(1, mm_w)))
        for row in range(mm_h):
            src_row = min(tilemap.height - 1, row * row_step)
            for col in range(mm_w):
                src_col = min(tilemap.width - 1, col * col_step)
                tid = tilemap.ground[src_row][src_col]
                from tilemap import TILE_DEFS
                tdef = TILE_DEFS.get(tid, TILE_DEFS[0])
                base = tdef["base"]
                c    = tuple(max(0, b - 35) for b in base)
                if tilemap.collision[src_row][src_col]:
                    c = (32, 32, 42)
                self._minimap_surf.set_at((col, row), c)

    # ── Boss HP bar ─────────────────────────────────────────────────────────────

    def _draw_boss_bar(self, surf):
        if not (self.boss_ref and self.boss_ref.active and self.boss_ref.alive):
            return
        boss  = self.boss_ref
        bar_w = min(280, max(140, self.viewport_width - 32))
        bar_h = 11
        bx    = self.viewport_width // 2 - bar_w // 2
        # Name label above bar, bar below it — sits at top-centre
        boss_name = getattr(boss, 'boss_id', 'boss').replace('_', ' ').upper()
        name_s = self.font.render(boss_name, True, (218, 172, 148))
        name_y = 8
        by     = name_y + name_s.get_height() + 4
        ratio  = max(0.0, boss.hp / boss.max_hp)

        # Dark panel behind the whole block
        panel_pad = 6
        panel = pygame.Surface((bar_w + panel_pad * 2, name_s.get_height() + bar_h + panel_pad * 2 + 4),
                                pygame.SRCALPHA)
        panel.fill((8, 4, 4, 210))
        surf.blit(panel, (bx - panel_pad, name_y - panel_pad))
        pygame.draw.rect(surf, (60, 22, 22),
                         (bx - panel_pad, name_y - panel_pad,
                          bar_w + panel_pad * 2, name_s.get_height() + bar_h + panel_pad * 2 + 4),
                         1, border_radius=4)

        # Name centred above bar
        surf.blit(name_s, (self.viewport_width // 2 - name_s.get_width() // 2, name_y))

        # Outer frame
        pygame.draw.rect(surf, (12, 6, 6), (bx - 3, by - 3, bar_w + 6, bar_h + 6), border_radius=4)
        pygame.draw.rect(surf, (80, 30, 30), (bx - 3, by - 3, bar_w + 6, bar_h + 6), 1, border_radius=4)

        # Track
        pygame.draw.rect(surf, (32, 10, 10), (bx, by, bar_w, bar_h))

        # Fill
        fill_w = int(bar_w * ratio)
        if fill_w > 0:
            pygame.draw.rect(surf, COLOR_BOSS_HP, (bx, by, fill_w, bar_h))
            pygame.draw.rect(surf, (240, 90, 60), (bx, by, fill_w, 4))

        # Frame
        pygame.draw.rect(surf, (95, 35, 35), (bx, by, bar_w, bar_h), 1)

        # Phase pips at 33% / 66%
        for frac in (0.33, 0.66):
            px = bx + int(bar_w * frac)
            pygame.draw.line(surf, (80, 30, 30), (px, by), (px, by + bar_h), 1)

    # ── Notification banner ─────────────────────────────────────────────────────

    def _draw_notification(self, surf):
        if self.notif_timer <= 0:
            return

        fade_in  = min(1.0, self.notif_timer / 0.3)
        fade_out = min(1.0, (self.notif_duration - self.notif_timer) / 0.3) if self.notif_duration > 0.3 else 1.0
        alpha    = int(min(fade_in, fade_out) * 240)

        ns   = self.font.render(self.notification, True, (252, 248, 195))
        padx = 14
        pady = 5
        bw   = ns.get_width() + padx * 2
        bh   = ns.get_height() + pady * 2
        nx   = self.viewport_width // 2 - bw // 2
        ny   = 56

        nbg = pygame.Surface((bw, bh), pygame.SRCALPHA)
        nbg.fill((0, 0, 0, min(148, alpha)))
        pygame.draw.rect(nbg, (*COLOR_ACCENT, min(120, alpha)), (0, 0, bw, bh), 1)

        ns_copy = ns.copy()
        ns_copy.set_alpha(alpha)
        nbg.set_alpha(alpha)

        surf.blit(nbg, (nx, ny))
        surf.blit(ns_copy, (nx + padx, ny + pady))
