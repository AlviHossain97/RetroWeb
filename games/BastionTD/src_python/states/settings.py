"""
states/settings.py - Settings menu state for Bastion TD.
"""
import pygame
from states.state_machine import State
from settings import (
    SCREEN_W, SCREEN_H, COLOR_HUD_BG, COLOR_WHITE, COLOR_ACCENT, COLOR_GOLD,
)


class SettingsState(State):
    """Settings menu with toggleable options."""

    def __init__(self, game):
        super().__init__(game)
        self.cursor_idx = 0
        self._font_title = None
        self._font_menu = None
        self._font_hint = None
        self._fonts_ready = False

    def _ensure_fonts(self):
        if not self._fonts_ready:
            self._font_title = pygame.font.SysFont("monospace", 32, bold=True)
            self._font_menu = pygame.font.SysFont("monospace", 18)
            self._font_hint = pygame.font.SysFont("monospace", 14)
            self._fonts_ready = True

    def enter(self):
        self.cursor_idx = 0

    def _get_items(self):
        """Build menu items dynamically from current game settings."""
        g = self.game
        sprite_label = "ON" if g.use_sprites else "OFF"
        sfx_label = "ON" if g.sfx_enabled else "OFF"
        bgm_label = "ON" if g.bgm_enabled else "OFF"
        ff_label = "ON" if g.show_fps else "OFF"

        return [
            ("Graphics Mode", f"Sprites: {sprite_label}", "toggle_sprites"),
            ("Sound Effects", f"SFX: {sfx_label}", "toggle_sfx"),
            ("Background Music", f"BGM: {bgm_label}", "toggle_bgm"),
            ("Show FPS", f"FPS Counter: {ff_label}", "toggle_fps"),
            ("Back", "Return to title", "back"),
        ]

    def update(self, dt):
        inp = self.game.input
        items = self._get_items()

        if inp.pressed("up"):
            self.cursor_idx = (self.cursor_idx - 1) % len(items)
            self.game.audio.play("menu_move")
        if inp.pressed("down"):
            self.cursor_idx = (self.cursor_idx + 1) % len(items)
            self.game.audio.play("menu_move")

        if inp.pressed("a"):
            self.game.audio.play("menu_select")
            action = items[self.cursor_idx][2]

            if action == "toggle_sprites":
                self.game.use_sprites = not self.game.use_sprites
            elif action == "toggle_sfx":
                self.game.sfx_enabled = not self.game.sfx_enabled
                self.game.audio.set_sfx_enabled(self.game.sfx_enabled)
            elif action == "toggle_bgm":
                self.game.bgm_enabled = not self.game.bgm_enabled
                if self.game.bgm_enabled:
                    self.game.audio.play_bgm("bgm_title")
                else:
                    self.game.audio.stop_bgm()
            elif action == "toggle_fps":
                self.game.show_fps = not self.game.show_fps
            elif action == "back":
                self.game.state_machine.change("title")

        # B or ESC also goes back
        if inp.pressed("b") or inp.pressed("start"):
            self.game.state_machine.change("title")

    def render(self, screen):
        self._ensure_fonts()
        items = self._get_items()

        screen.fill(COLOR_HUD_BG)

        # Title
        title_surf = self._font_title.render("SETTINGS", True, COLOR_ACCENT)
        title_rect = title_surf.get_rect(center=(SCREEN_W // 2, 60))
        screen.blit(title_surf, title_rect)

        # Menu items
        start_y = 140
        for i, (label, value, _action) in enumerate(items):
            is_selected = i == self.cursor_idx
            prefix = "> " if is_selected else "  "
            color = COLOR_ACCENT if is_selected else COLOR_WHITE

            # Label on left
            label_surf = self._font_menu.render(f"{prefix}{label}", True, color)
            screen.blit(label_surf, (80, start_y + i * 40))

            # Value on right (highlighted)
            val_color = COLOR_GOLD if is_selected else (160, 160, 160)
            val_surf = self._font_menu.render(value, True, val_color)
            screen.blit(val_surf, (SCREEN_W - 80 - val_surf.get_width(), start_y + i * 40))

        # Hint
        hint_surf = self._font_hint.render(
            "Z/Enter=Toggle  X/ESC=Back", True, (120, 120, 120)
        )
        hint_rect = hint_surf.get_rect(center=(SCREEN_W // 2, SCREEN_H - 30))
        screen.blit(hint_surf, hint_rect)
