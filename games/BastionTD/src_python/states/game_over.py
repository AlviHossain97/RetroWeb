"""
states/game_over.py - Game over screen for Bastion TD.
"""
import pygame
from states.state_machine import State
from settings import (
    SCREEN_W, SCREEN_H, COLOR_HUD_BG, COLOR_WHITE, COLOR_ACCENT,
    COLOR_HEALTH, COLOR_GOLD,
)


class GameOverState(State):
    """Displays game over screen with stats and retry/title options."""

    def __init__(self, game):
        super().__init__(game)
        self.menu_items = ["Retry", "Title"]
        self.cursor_idx = 0
        self.wave_reached = 0
        self.total_gold = 0
        self.towers_built = 0
        self._font_title = None
        self._font_body = None
        self._font_menu = None
        self._fonts_ready = False

    def _ensure_fonts(self):
        if not self._fonts_ready:
            self._font_title = pygame.font.SysFont("monospace", 36, bold=True)
            self._font_body = pygame.font.SysFont("monospace", 18)
            self._font_menu = pygame.font.SysFont("monospace", 22)
            self._fonts_ready = True

    def enter(self):
        self.cursor_idx = 0
        self.game.audio.stop_bgm()
        self.game.audio.play("game_over")

        # Pull stats from gameplay state
        gp = self.game.state_machine.states.get("gameplay")
        if gp is not None:
            self.wave_reached = gp.wave_mgr.current_wave
            self.total_gold = gp.economy.total_earned
            self.towers_built = gp.towers_built_count
        else:
            self.wave_reached = 0
            self.total_gold = 0
            self.towers_built = 0

        # Save high score
        save_data = self.game.save.load()
        games_played = save_data.get("games_played", 0) + 1
        self.game.save.save(self.wave_reached, self.total_gold, games_played)

    def exit(self):
        pass

    def update(self, dt):
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
            if choice == "Retry":
                self.game.state_machine.change("gameplay")
            elif choice == "Title":
                self.game.state_machine.change("title")

    def render(self, screen):
        self._ensure_fonts()
        screen.fill(COLOR_HUD_BG)

        # "GAME OVER" title
        title_surf = self._font_title.render("GAME OVER", True, COLOR_HEALTH)
        title_rect = title_surf.get_rect(center=(SCREEN_W // 2, 80))
        screen.blit(title_surf, title_rect)

        # Stats
        stats = [
            f"Wave Reached: {self.wave_reached}",
            f"Total Gold Earned: {self.total_gold}g",
            f"Towers Built: {self.towers_built}",
        ]
        y = 160
        for line in stats:
            surf = self._font_body.render(line, True, COLOR_WHITE)
            rect = surf.get_rect(center=(SCREEN_W // 2, y))
            screen.blit(surf, rect)
            y += 32

        # Menu items
        menu_y = 310
        for i, item in enumerate(self.menu_items):
            if i == self.cursor_idx:
                prefix = "> "
                color = COLOR_ACCENT
            else:
                prefix = "  "
                color = COLOR_WHITE
            text_surf = self._font_menu.render(prefix + item, True, color)
            text_rect = text_surf.get_rect(center=(SCREEN_W // 2, menu_y + i * 40))
            screen.blit(text_surf, text_rect)
