"""Pause menu — clean dark panel, save/load, quit."""

import math
import pygame
from settings import COLOR_ACCENT
from states.state_machine import State
from ui.fonts import get_font

_MENU_ITEMS = ["Resume", "Inventory", "Bestiary", "Save Game", "Quit to Title"]
_DIM = (70, 72, 88)
_BRT = (218, 220, 232)


class PauseState(State):
    def __init__(self, game):
        super().__init__(game)
        self.cursor = 0
        self.items = list(_MENU_ITEMS)
        self.message = ""
        self.msg_timer = 0.0
        self._font = None
        self._sfont = None
        self._tfont = None
        self._timer = 0.0

    def _ensure_fonts(self):
        if self._font is None:
            self._font = get_font(22, bold=True)
            self._sfont = get_font(18)
            self._tfont = get_font(11)

    def enter(self):
        self.cursor = 0
        self.message = ""
        self.msg_timer = 0.0
        self._timer = 0.0

    def update(self, dt):
        self._timer += dt
        if self.msg_timer > 0:
            self.msg_timer -= dt
            if self.msg_timer <= 0:
                self.message = ""

        inp = self.game.input
        if inp.is_pressed("start") or inp.is_pressed("b"):
            self.game.states.change("gameplay")
            return

        if inp.is_pressed("up"):
            self.cursor = (self.cursor - 1) % len(self.items)
            if hasattr(self.game, "audio"):
                self.game.audio.play_sfx("menu_move")
        if inp.is_pressed("down"):
            self.cursor = (self.cursor + 1) % len(self.items)
            if hasattr(self.game, "audio"):
                self.game.audio.play_sfx("menu_move")

        if inp.is_pressed("a"):
            choice = self.items[self.cursor]
            if choice == "Resume":
                self.game.states.change("gameplay")
            elif choice == "Inventory":
                self.game.states.change("inventory")
            elif choice == "Bestiary":
                self.game.states.change("bestiary")
            elif choice == "Save Game":
                success = self.game.save_current_game()
                self.message = "Game saved." if success else "Save failed!"
                self.msg_timer = 2.5
                if hasattr(self.game, "audio"):
                    self.game.audio.play_sfx("menu_select")
            elif choice == "Quit to Title":
                self.game.states.change("title")

    def render(self, screen):
        self._ensure_fonts()
        t = self._timer
        vw, vh = self._viewport_size(screen)
        compact = self._is_compact_view(screen)

        # Backdrop
        dim = pygame.Surface((vw, vh), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 178))
        screen.blit(dim, (0, 0))

        # Panel
        row_h = 36 if compact else 44
        pw = min(280, max(208, vw - 24))
        ph = (48 if compact else 60) + len(self.items) * row_h + (26 if compact else 40)
        px = vw // 2 - pw // 2
        py = vh // 2 - ph // 2 - (8 if compact else 20)

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((7, 9, 18, 248))
        screen.blit(panel, (px, py))
        pygame.draw.rect(screen, (48, 52, 68), (px, py, pw, ph), 1, border_radius=5)
        pygame.draw.rect(
            screen, (28, 32, 44), (px + 1, py + 1, pw - 2, ph - 2), 1, border_radius=4
        )

        # Title "PAUSED"
        title_s = self._font.render("PAUSED", True, (215, 218, 228))
        screen.blit(title_s, (px + pw // 2 - title_s.get_width() // 2, py + 14))
        # Thin rule under title
        pygame.draw.line(
            screen, (38, 42, 58), (px + 20, py + 42), (px + pw - 20, py + 42)
        )

        # Menu items
        for i, item in enumerate(self.items):
            iy = py + (48 if compact else 52) + i * row_h
            selected = i == self.cursor

            if selected:
                # Selection bg
                pulse = 0.55 + 0.45 * math.sin(t * 2.5)
                sbg_h = 28 if compact else 34
                sbg = pygame.Surface((pw - 24, sbg_h), pygame.SRCALPHA)
                sbg.fill((int(20 * pulse), int(28 * pulse), int(50 * pulse), 140))
                screen.blit(sbg, (px + 12, iy - 4))
                pygame.draw.rect(
                    screen,
                    (int(45 * pulse + 28), int(65 * pulse + 40), int(55 * pulse + 42)),
                    (px + 12, iy - 4, pw - 24, sbg_h),
                    1,
                    border_radius=3,
                )

                # Chevron
                chev = self._sfont.render(">", True, COLOR_ACCENT)
                screen.blit(chev, (px + 18, iy + 2))

                # Label
                ls = self._sfont.render(item, True, COLOR_ACCENT)
                screen.blit(ls, (px + 32, iy + 2))
            else:
                ls = self._sfont.render(item, True, _DIM)
                screen.blit(ls, (px + 32, iy + 2))

        # Save confirmation message
        if self.message:
            msg_a = min(1.0, self.msg_timer / 0.4) * 255
            ms = self._tfont.render(self.message, True, (180, 218, 148))
            ms.set_alpha(int(msg_a))
            screen.blit(ms, (vw // 2 - ms.get_width() // 2, py + ph - 22))

        # Footer
        footer_text = (
            "B/ESC Resume  Z Select" if compact else "ESC/B = Resume   Z = Select"
        )
        foot = self._tfont.render(footer_text, True, (42, 44, 56))
        screen.blit(foot, (vw // 2 - foot.get_width() // 2, vh - 18))
