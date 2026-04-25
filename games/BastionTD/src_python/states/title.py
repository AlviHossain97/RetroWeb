"""
states/title.py - Title screen state for Bastion TD.
"""
import math
import pygame
from states.state_machine import State
from settings import (
    SCREEN_W, SCREEN_H, TILE_SIZE, COLOR_GRASS, COLOR_HUD_BG,
    COLOR_WHITE, COLOR_ACCENT, COLOR_GOLD, GAME_TITLE,
)


class TitleState(State):
    """Title screen with animated background, menu, and high score display."""

    def __init__(self, game):
        super().__init__(game)
        self.menu_items = ["New Game", "Instructions", "Settings", "Quit"]
        self.cursor_idx = 0
        self.scroll_offset = 0.0
        self.time_elapsed = 0.0

        # Fonts (lazily created)
        self._font_title = None
        self._font_menu = None
        self._font_small = None
        self._fonts_ready = False

    def _ensure_fonts(self):
        if not self._fonts_ready:
            self._font_title = pygame.font.SysFont("monospace", 40, bold=True)
            self._font_menu = pygame.font.SysFont("monospace", 22)
            self._font_small = pygame.font.SysFont("monospace", 16)
            self._fonts_ready = True

    def enter(self):
        self.cursor_idx = 0
        self.time_elapsed = 0.0
        self.scroll_offset = 0.0
        self.game.audio.play_bgm("bgm_title")

    def exit(self):
        pass

    def update(self, dt):
        self.time_elapsed += dt
        self.scroll_offset += dt * 15.0  # slow pixel scroll

        inp = self.game.input

        if inp.pressed("up"):
            self.cursor_idx = (self.cursor_idx - 1) % len(self.menu_items)
            self.game.audio.play("menu_move")
        if inp.pressed("down"):
            self.cursor_idx = (self.cursor_idx + 1) % len(self.menu_items)
            self.game.audio.play("menu_move")

        if inp.pressed("a"):
            self.game.audio.play("menu_select")
            choice = self.menu_items[self.cursor_idx]
            if choice == "New Game":
                self.game.state_machine.change("gameplay")
            elif choice == "Instructions":
                self.game.state_machine.change("instructions")
            elif choice == "Settings":
                self.game.state_machine.change("settings")
            elif choice == "Quit":
                self.game.running = False

    def render(self, screen):
        self._ensure_fonts()

        # --- Animated background: scrolling grid of grass tiles ---
        screen.fill(COLOR_HUD_BG)
        scroll_y = int(self.scroll_offset) % TILE_SIZE
        grass_dark = (
            max(COLOR_GRASS[0] - 15, 0),
            max(COLOR_GRASS[1] - 15, 0),
            max(COLOR_GRASS[2] - 15, 0),
        )
        for ty in range(-1, SCREEN_H // TILE_SIZE + 2):
            for tx in range(SCREEN_W // TILE_SIZE):
                px = tx * TILE_SIZE
                py = ty * TILE_SIZE - scroll_y
                # Checkerboard subtle pattern
                if (tx + ty) % 2 == 0:
                    color = (25, 40, 25)
                else:
                    color = (20, 35, 20)
                pygame.draw.rect(screen, color, (px, py, TILE_SIZE, TILE_SIZE))

        # --- Dark overlay for readability ---
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        screen.blit(overlay, (0, 0))

        # --- Title text with glow ---
        title_y = 80
        # Shadow/glow
        shadow_surf = self._font_title.render(GAME_TITLE, True, (40, 80, 40))
        shadow_rect = shadow_surf.get_rect(center=(SCREEN_W // 2 + 2, title_y + 2))
        screen.blit(shadow_surf, shadow_rect)
        # Main text
        title_surf = self._font_title.render(GAME_TITLE, True, COLOR_ACCENT)
        title_rect = title_surf.get_rect(center=(SCREEN_W // 2, title_y))
        screen.blit(title_surf, title_rect)

        # --- Subtitle ---
        sub_text = "A GBA-Style Tower Defense"
        sub_surf = self._font_small.render(sub_text, True, COLOR_WHITE)
        sub_rect = sub_surf.get_rect(center=(SCREEN_W // 2, title_y + 40))
        screen.blit(sub_surf, sub_rect)

        # --- Menu items ---
        menu_start_y = 200
        for i, item in enumerate(self.menu_items):
            if i == self.cursor_idx:
                # Cursor indicator
                prefix = "> "
                color = COLOR_ACCENT
            else:
                prefix = "  "
                color = COLOR_WHITE
            text_surf = self._font_menu.render(prefix + item, True, color)
            text_rect = text_surf.get_rect(center=(SCREEN_W // 2, menu_start_y + i * 40))
            screen.blit(text_surf, text_rect)

        # --- Best score display ---
        save_data = self.game.save.load()
        best_wave = save_data.get("best_wave", 0)
        if best_wave > 0:
            best_text = f"Best: Wave {best_wave}"
            best_surf = self._font_small.render(best_text, True, COLOR_GOLD)
            best_rect = best_surf.get_rect(center=(SCREEN_W // 2, 380))
            screen.blit(best_surf, best_rect)

        # --- Controls hint ---
        hint_surf = self._font_small.render(
            "Z/Enter=Select  Arrows/WASD=Move", True, (120, 120, 120)
        )
        hint_rect = hint_surf.get_rect(center=(SCREEN_W // 2, SCREEN_H - 30))
        screen.blit(hint_surf, hint_rect)
