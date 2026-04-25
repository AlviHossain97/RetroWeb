"""Game Over screen with retry option."""
import pygame
from states.state_machine import State
from ui.fonts import get_font


class GameOverState(State):
    def __init__(self, game):
        super().__init__(game)
        self.timer = 0.0
        self.cursor = 0

    def enter(self):
        self.timer = 0
        self.cursor = 0
        if hasattr(self.game, 'audio'):
            self.game.audio.stop_music()
            self.game.audio.play_sfx("death")

    def update(self, dt):
        self.timer += dt
        if self.timer < 1.0: return
        inp = self.game.input
        if inp.is_pressed("up") or inp.is_pressed("down"):
            self.cursor = 1 - self.cursor
        if inp.is_pressed("a") or inp.is_pressed("start"):
            if self.cursor == 0:
                self.game.retry_from_checkpoint()
            else:
                self.game.states.change("title")

    def render(self, screen):
        vw, vh = self._viewport_size(screen)
        compact = self._is_compact_view(screen)

        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        font = get_font(28 if compact else 40, bold=True)
        text = font.render("GAME OVER", True, (200, 50, 50))
        screen.blit(text, (vw // 2 - text.get_width() // 2, vh // 2 - (48 if compact else 60)))

        if self.timer > 1.0:
            menu_font = get_font(16 if compact else 20)
            items = ["Retry from Checkpoint", "Title Screen"]
            for i, item in enumerate(items):
                color = (255,255,255) if i == self.cursor else (120,120,130)
                prefix = "> " if i == self.cursor else "  "
                s = menu_font.render(prefix + item, True, color)
                screen.blit(s, (vw // 2 - s.get_width() // 2, vh // 2 + 16 + i * (24 if compact else 32)))
