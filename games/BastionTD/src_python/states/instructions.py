"""
states/instructions.py - Instructions/how-to-play screen for Bastion TD.
"""
import pygame
from states.state_machine import State
from settings import (
    SCREEN_W, SCREEN_H, COLOR_HUD_BG, COLOR_WHITE, COLOR_ACCENT,
    COLOR_GOLD, TOWER_DEFS, TOWER_ORDER,
)


class InstructionsState(State):
    """Displays controls, gameplay explanation, and tower summary."""

    def __init__(self, game):
        super().__init__(game)
        self._font_title = None
        self._font_body = None
        self._font_small = None
        self._fonts_ready = False

    def _ensure_fonts(self):
        if not self._fonts_ready:
            self._font_title = pygame.font.SysFont("monospace", 28, bold=True)
            self._font_body = pygame.font.SysFont("monospace", 15)
            self._font_small = pygame.font.SysFont("monospace", 13)
            self._fonts_ready = True

    def enter(self):
        pass

    def exit(self):
        pass

    def update(self, dt):
        inp = self.game.input
        if inp.pressed("a") or inp.pressed("b") or inp.pressed("start"):
            self.game.audio.play("menu_select")
            self.game.state_machine.change("title")

    def render(self, screen):
        self._ensure_fonts()
        screen.fill(COLOR_HUD_BG)

        y = 15

        # Title
        title_surf = self._font_title.render("HOW TO PLAY", True, COLOR_ACCENT)
        title_rect = title_surf.get_rect(center=(SCREEN_W // 2, y))
        screen.blit(title_surf, title_rect)
        y += 40

        # Controls table
        controls = [
            ("Action", "Keyboard", "GBA"),
            ("--------", "--------", "--------"),
            ("Move cursor", "WASD / Arrows", "D-pad"),
            ("Place tower / Confirm", "Z / Enter", "A"),
            ("Upgrade / Sell tower", "X / Backspace", "B"),
            ("Prev tower type", "Q", "L"),
            ("Next tower type", "E", "R"),
            ("Pause", "ESC", "Start"),
            ("Fast-forward (3x)", "TAB", "Select"),
        ]

        for row in controls:
            text = f"{row[0]:<24}{row[1]:<16}{row[2]}"
            color = COLOR_WHITE if row[0] != "Action" and row[0] != "--------" else COLOR_GOLD
            surf = self._font_small.render(text, True, color)
            screen.blit(surf, (40, y))
            y += 18

        y += 10

        # Gameplay explanation
        explanation = [
            "Build towers to defend your base from waves of enemies.",
            "Enemies follow the brown path from Spawn(S) to Base(B).",
            "Place towers on green (empty) tiles during build phase.",
            "Press A on empty ground to start the next wave.",
            "Survive all 20 waves to win! Don't let lives reach 0.",
            "Hold B on a tower for 1s to sell it (50% refund).",
        ]
        for line in explanation:
            surf = self._font_body.render(line, True, COLOR_WHITE)
            screen.blit(surf, (40, y))
            y += 20

        y += 10

        # Tower summary
        header = f"{'Tower':<12}{'Cost':>5}  {'Special':<10}{'Range':>5}"
        surf = self._font_small.render(header, True, COLOR_GOLD)
        screen.blit(surf, (40, y))
        y += 18

        for key in TOWER_ORDER:
            tdef = TOWER_DEFS[key]
            name = tdef["name"][:10]
            cost = tdef["cost"]
            special = tdef["special"]
            rng = tdef["range"]
            line = f"{name:<12}{cost:>4}g  {special:<10}{rng:>4.1f}"
            # Color swatch
            swatch_rect = pygame.Rect(24, y + 2, 10, 10)
            pygame.draw.rect(screen, tdef["color"], swatch_rect)
            surf = self._font_small.render(line, True, COLOR_WHITE)
            screen.blit(surf, (40, y))
            y += 18

        # Return hint
        hint_surf = self._font_body.render(
            "Press Z/Enter or X/Backspace to return", True, (120, 120, 120)
        )
        hint_rect = hint_surf.get_rect(center=(SCREEN_W // 2, SCREEN_H - 20))
        screen.blit(hint_surf, hint_rect)
