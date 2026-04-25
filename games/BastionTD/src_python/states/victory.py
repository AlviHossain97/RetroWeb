"""
states/victory.py - Victory screen for Bastion TD.
"""
import math
import pygame
from states.state_machine import State
from settings import (
    SCREEN_W, SCREEN_H, COLOR_HUD_BG, COLOR_WHITE, COLOR_ACCENT,
    COLOR_GOLD,
)
from effects import ParticleSystem


class VictoryState(State):
    """Displays victory screen with celebration particles and stats."""

    def __init__(self, game):
        super().__init__(game)
        self.menu_items = ["Title"]
        self.cursor_idx = 0
        self.wave_reached = 0
        self.total_gold = 0
        self.towers_built = 0
        self.particles = ParticleSystem()
        self.time_elapsed = 0.0
        self._font_title = None
        self._font_body = None
        self._font_menu = None
        self._fonts_ready = False

    def _ensure_fonts(self):
        if not self._fonts_ready:
            self._font_title = pygame.font.SysFont("monospace", 40, bold=True)
            self._font_body = pygame.font.SysFont("monospace", 18)
            self._font_menu = pygame.font.SysFont("monospace", 22)
            self._fonts_ready = True

    def enter(self):
        self.cursor_idx = 0
        self.time_elapsed = 0.0
        self.particles = ParticleSystem()
        self.game.audio.stop_bgm()
        self.game.audio.play("victory")

        # Pull stats from gameplay state
        gp = self.game.state_machine.states.get("gameplay")
        if gp is not None:
            self.wave_reached = gp.wave_mgr.current_wave
            self.total_gold = gp.economy.total_earned
            self.towers_built = gp.towers_built_count
        else:
            self.wave_reached = 20
            self.total_gold = 0
            self.towers_built = 0

        # Save high score
        save_data = self.game.save.load()
        games_played = save_data.get("games_played", 0) + 1
        self.game.save.save(self.wave_reached, self.total_gold, games_played)

        # Celebration particle burst (emit at center in tile coords)
        center_x = SCREEN_W / 64.0  # approximate center in tile space
        center_y = SCREEN_H / 64.0
        celebration_colors = [
            COLOR_GOLD, COLOR_ACCENT, COLOR_WHITE,
            (255, 100, 100), (100, 100, 255), (255, 255, 100),
        ]
        for color in celebration_colors:
            self.particles.emit(center_x, center_y, color, count=15, spread=4.0)

    def exit(self):
        pass

    def update(self, dt):
        self.time_elapsed += dt
        self.particles.update(dt)

        inp = self.game.input

        if inp.pressed("up"):
            self.cursor_idx = (self.cursor_idx - 1) % len(self.menu_items)
            self.game.audio.play("menu_move")
        if inp.pressed("down"):
            self.cursor_idx = (self.cursor_idx + 1) % len(self.menu_items)
            self.game.audio.play("menu_move")

        if inp.pressed("a"):
            self.game.audio.play("menu_select")
            self.game.state_machine.change("title")

    def render(self, screen):
        self._ensure_fonts()
        screen.fill(COLOR_HUD_BG)

        # Particles (render at 0,0 since they are in abstract coords)
        self.particles.render(screen, 0, 0)

        # "VICTORY!" title with color pulse
        pulse = int(abs(math.sin(self.time_elapsed * 3.0)) * 60)
        title_color = (
            min(COLOR_GOLD[0], 255),
            min(COLOR_GOLD[1] + pulse, 255),
            min(COLOR_GOLD[2], 255),
        )
        # Shadow
        shadow_surf = self._font_title.render("VICTORY!", True, (80, 60, 20))
        shadow_rect = shadow_surf.get_rect(center=(SCREEN_W // 2 + 2, 82))
        screen.blit(shadow_surf, shadow_rect)
        # Main
        title_surf = self._font_title.render("VICTORY!", True, title_color)
        title_rect = title_surf.get_rect(center=(SCREEN_W // 2, 80))
        screen.blit(title_surf, title_rect)

        # Subtitle
        sub_surf = self._font_body.render("You survived all 20 waves!", True, COLOR_WHITE)
        sub_rect = sub_surf.get_rect(center=(SCREEN_W // 2, 130))
        screen.blit(sub_surf, sub_rect)

        # Stats
        stats = [
            f"Waves Completed: {self.wave_reached}",
            f"Total Gold Earned: {self.total_gold}g",
            f"Towers Built: {self.towers_built}",
        ]
        y = 190
        for line in stats:
            surf = self._font_body.render(line, True, COLOR_WHITE)
            rect = surf.get_rect(center=(SCREEN_W // 2, y))
            screen.blit(surf, rect)
            y += 32

        # Menu items
        menu_y = 340
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
