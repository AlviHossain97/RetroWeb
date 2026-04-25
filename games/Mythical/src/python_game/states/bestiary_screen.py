"""Bestiary screen — viewable from pause menu. Shows discovered creatures."""
import pygame
from settings import COLOR_ACCENT
from states.state_machine import State
from bestiary import render_bestiary_panel
from ui.fonts import get_font


class BestiaryScreenState(State):
    def __init__(self, game):
        super().__init__(game)
        self._cursor = 0
        self._font = None
        self._sfont = None
        self._tfont = None

    def _ensure_fonts(self):
        if self._font is None:
            self._font = get_font(14)
            self._sfont = get_font(12)
            self._tfont = get_font(10)

    def enter(self):
        self._cursor = 0

    def update(self, dt):
        inp = self.game.input
        if inp.is_pressed("b") or inp.is_pressed("start") or inp.is_pressed("select"):
            self.game.states.change("pause")
            return
        if inp.is_pressed("up"):
            self._cursor = max(0, self._cursor - 1)
        if inp.is_pressed("down"):
            self._cursor += 1
            bestiary = getattr(self.game, "bestiary", None)
            if bestiary:
                from bestiary import ENTRY_DEFS
                self._cursor = min(self._cursor, len(ENTRY_DEFS) - 1)

    def render(self, screen):
        self._ensure_fonts()
        vw, vh = self._viewport_size(screen)
        compact = self._is_compact_view(screen)

        # Dimmer
        dim = pygame.Surface((vw, vh), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 220))
        screen.blit(dim, (0, 0))

        # Panel
        px, py = (6, 6) if compact else (20, 16)
        pw, ph = vw - px * 2, vh - py * 2
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((7, 9, 18, 245))
        screen.blit(panel, (px, py))
        pygame.draw.rect(screen, (58, 62, 82), (px, py, pw, ph), 1, border_radius=5)

        # Header
        ts = self._font.render("BESTIARY", True, COLOR_ACCENT)
        screen.blit(ts, (px + 12, py + 8))

        bestiary = getattr(self.game, "bestiary", None)
        if bestiary:
            unlocked, total = bestiary.completion_ratio()
            ps = self._tfont.render(f"{unlocked}/{total} fully unlocked", True, (120, 180, 120))
            screen.blit(ps, (px + pw - ps.get_width() - 12, py + 10))

        pygame.draw.line(screen, (40, 44, 60), (px + 8, py + 28), (px + pw - 8, py + 28))

        # Bestiary content
        if bestiary:
            render_bestiary_panel(
                screen, bestiary,
                self._font, self._sfont,
                px + 14, py + 34, pw - 28, ph - (50 if compact else 60),
                self._cursor)

        # Footer
        footer_text = "Up/Down Navigate   B Back" if compact else "Up/Down=Navigate   B/ESC=Back"
        foot = self._tfont.render(footer_text, True, (80, 84, 102))
        screen.blit(foot, (px + pw // 2 - foot.get_width() // 2, py + ph - 16))
