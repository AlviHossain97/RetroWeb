"""
states/pause.py - Pause overlay state for Bastion TD.

Implemented as an internal flag on the gameplay state so that gameplay is not
re-entered (which would reset it). The PauseState is registered for completeness
but the actual pause is handled inside GameplayState.
"""
import pygame
from states.state_machine import State
from settings import SCREEN_W, SCREEN_H, COLOR_WHITE, COLOR_ACCENT


class PauseState(State):
    """Standalone pause state (used if state machine transitions to 'pause').

    In practice, gameplay handles pausing internally via an is_paused flag.
    This exists as a fallback and renders a simple overlay.
    """

    def __init__(self, game):
        super().__init__(game)
        self.menu_items = ["Resume", "Quit to Title"]
        self.cursor_idx = 0
        self._font_title = None
        self._font_menu = None
        self._fonts_ready = False

    def _ensure_fonts(self):
        if not self._fonts_ready:
            self._font_title = pygame.font.SysFont("monospace", 36, bold=True)
            self._font_menu = pygame.font.SysFont("monospace", 22)
            self._fonts_ready = True

    def enter(self):
        self.cursor_idx = 0

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
            if choice == "Resume":
                # Return to gameplay without re-entering
                self.game.state_machine.change("gameplay")
            elif choice == "Quit to Title":
                self.game.state_machine.change("title")

        if inp.pressed("start") or inp.pressed("b"):
            self.game.audio.play("menu_select")
            self.game.state_machine.change("gameplay")

    def render(self, screen):
        self._ensure_fonts()

        # Semi-transparent dark overlay
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # "PAUSED" text
        title_surf = self._font_title.render("PAUSED", True, COLOR_WHITE)
        title_rect = title_surf.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 60))
        screen.blit(title_surf, title_rect)

        # Menu items
        for i, item in enumerate(self.menu_items):
            if i == self.cursor_idx:
                prefix = "> "
                color = COLOR_ACCENT
            else:
                prefix = "  "
                color = COLOR_WHITE
            text_surf = self._font_menu.render(prefix + item, True, color)
            text_rect = text_surf.get_rect(
                center=(SCREEN_W // 2, SCREEN_H // 2 + i * 40)
            )
            screen.blit(text_surf, text_rect)
