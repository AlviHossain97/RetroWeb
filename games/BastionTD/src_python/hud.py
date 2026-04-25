"""
hud.py - HUD rendering: top bar, tower tray, notifications for Bastion TD.
"""
import pygame
from settings import *


class HUD:
    """Renders the top information bar, bottom tower tray, and notifications."""

    def __init__(self):
        self._font_hud = None
        self._font_tray = None
        self._font_notify = None
        self._font_boss = None
        self._initialized = False

    def _ensure_fonts(self):
        """Lazily initialize fonts (pygame.font must be initialized first)."""
        if not self._initialized:
            self._font_hud = pygame.font.SysFont("monospace", 18)
            self._font_tray = pygame.font.SysFont("monospace", 14)
            self._font_notify = pygame.font.SysFont("monospace", 24)
            self._font_boss = pygame.font.SysFont("monospace", 12)
            self._initialized = True

    def render_hud(self, screen, wave, total_waves, gold, lives, phase,
                   enemies_remaining, boss_enemy=None, assets=None):
        """Draw the top HUD bar (top 2 tile rows, pixel Y 0-63)."""
        self._ensure_fonts()

        # Background
        hud_rect = pygame.Rect(0, 0, SCREEN_W, HUD_H * TILE_SIZE)
        pygame.draw.rect(screen, COLOR_HUD_BG, hud_rect)

        # Wave counter
        wave_text = self._font_hud.render(f"Wave: {wave}/{total_waves}", True, COLOR_WHITE)
        screen.blit(wave_text, (10, 8))

        # Gold (with icon if available)
        gold_x = 200
        if assets:
            icon = assets.get_ui_sprite(6, 0)
            if icon:
                scaled = pygame.transform.scale(icon, (icon.get_width() * 2, icon.get_height() * 2))
                screen.blit(scaled, (gold_x, 4))
                gold_x += scaled.get_width() + 4
        gold_text = self._font_hud.render(f"{gold}g", True, COLOR_GOLD)
        screen.blit(gold_text, (gold_x, 8))

        # Lives (with icon if available)
        lives_x = 380
        if assets:
            icon = assets.get_ui_sprite(6, 1)
            if icon:
                scaled = pygame.transform.scale(icon, (icon.get_width() * 2, icon.get_height() * 2))
                screen.blit(scaled, (lives_x, 4))
                lives_x += scaled.get_width() + 4
        lives_text = self._font_hud.render(f"{lives}", True, COLOR_HEALTH)
        screen.blit(lives_text, (lives_x, 8))

        # Phase label or enemy count
        if phase == "build":
            phase_text = self._font_hud.render("[BUILD PHASE]", True, COLOR_ACCENT)
        else:
            phase_text = self._font_hud.render(f"Enemies: {enemies_remaining}", True, COLOR_ACCENT)
        screen.blit(phase_text, (540, 8))

        # Boss HP bar (second row of HUD, centered) when Titan is alive
        if boss_enemy is not None and boss_enemy.alive and not boss_enemy.reached_base:
            bar_w = 300
            bar_h = 16
            bar_x = (SCREEN_W - bar_w) // 2
            bar_y = 36

            # Background (red)
            pygame.draw.rect(screen, (80, 20, 20), (bar_x, bar_y, bar_w, bar_h))

            # Health fill (green)
            hp_ratio = max(0, boss_enemy.hp / boss_enemy.max_hp)
            fill_w = int(bar_w * hp_ratio)
            if fill_w > 0:
                pygame.draw.rect(screen, (40, 180, 40), (bar_x, bar_y, fill_w, bar_h))

            # Border
            pygame.draw.rect(screen, COLOR_WHITE, (bar_x, bar_y, bar_w, bar_h), 1)

            # Label
            boss_label = self._font_boss.render(
                f"TITAN  {int(boss_enemy.hp)}/{int(boss_enemy.max_hp)}", True, COLOR_WHITE
            )
            label_rect = boss_label.get_rect(center=(SCREEN_W // 2, bar_y + bar_h // 2))
            screen.blit(boss_label, label_rect)

    def render_tray(self, screen, selected_idx, gold, assets=None):
        """Draw the bottom tower tray (pixel Y 448-479, 1 tile row)."""
        self._ensure_fonts()

        tray_y = SCREEN_H - TRAY_H * TILE_SIZE
        tray_rect = pygame.Rect(0, tray_y, SCREEN_W, TRAY_H * TILE_SIZE)
        pygame.draw.rect(screen, COLOR_TRAY_BG, tray_rect)

        slot_count = len(TOWER_ORDER)
        slot_w = SCREEN_W // slot_count  # evenly spaced

        for i, tower_key in enumerate(TOWER_ORDER):
            tdef = TOWER_DEFS[tower_key]
            slot_x = i * slot_w
            cost = tdef["cost"]
            affordable = gold >= cost

            # Selection highlight border
            if i == selected_idx:
                border_rect = pygame.Rect(slot_x + 2, tray_y + 2, slot_w - 4, TRAY_H * TILE_SIZE - 4)
                pygame.draw.rect(screen, COLOR_ACCENT, border_rect, 2)

            # Tower icon sprite or color swatch fallback
            icon_size = 20
            icon_x = slot_x + 6
            icon_y = tray_y + (TRAY_H * TILE_SIZE - icon_size) // 2
            tower_sprite = assets.get_tower_sprite(tower_key, 1) if assets else None

            if tower_sprite:
                icon = pygame.transform.scale(tower_sprite, (icon_size, icon_size))
                if not affordable:
                    # Darken by blitting a dark overlay
                    dark = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
                    dark.fill((0, 0, 0, 150))
                    icon.blit(dark, (0, 0))
                screen.blit(icon, (icon_x, icon_y))
            else:
                swatch_size = 12
                swatch_x = slot_x + 8
                swatch_y = tray_y + (TRAY_H * TILE_SIZE - swatch_size) // 2
                if affordable:
                    swatch_color = tdef["color"]
                else:
                    r, g, b = tdef["color"]
                    swatch_color = (r // 3, g // 3, b // 3)
                pygame.draw.rect(screen, swatch_color,
                                 (swatch_x, swatch_y, swatch_size, swatch_size))

            # Tower name + cost text
            text_x = icon_x + icon_size + 4
            if affordable:
                text_color = COLOR_WHITE
            else:
                text_color = (100, 100, 100)
            label = self._font_tray.render(f"{tdef['name'][:6]} {cost}g", True, text_color)
            screen.blit(label, (text_x, tray_y + 8))

    def render_notification(self, screen, text, timer):
        """Draw a center-screen notification that fades based on remaining timer."""
        self._ensure_fonts()

        if timer <= 0 or not text:
            return

        # Alpha fade: full at 2s, fade out over last 0.5s
        alpha = min(1.0, timer / 0.5)
        alpha_val = int(255 * alpha)

        text_surf = self._font_notify.render(text, True, COLOR_ACCENT)
        text_surf.set_alpha(alpha_val)
        text_rect = text_surf.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 40))
        screen.blit(text_surf, text_rect)
