"""
main.py - Entry point for Bastion TD.

Creates the Game instance, registers all states, and runs the main loop.
"""
import pygame
from settings import SCREEN_W, SCREEN_H, GAME_TITLE, TARGET_FPS, MAX_DT
from states.state_machine import StateMachine
from states.title import TitleState
from states.gameplay import GameplayState
from states.instructions import InstructionsState
from states.pause import PauseState
from states.game_over import GameOverState
from states.victory import VictoryState
from states.settings import SettingsState
from input_handler import InputHandler
from audio_manager import AudioManager
from save_manager import SaveManager
from asset_manager import AssetManager


class Game:
    """Top-level game object: owns the display, clock, input, audio, save, and state machine."""

    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True

        self.input = InputHandler()
        self.audio = AudioManager()
        self.save = SaveManager()
        self.assets = AssetManager()
        self.state_machine = StateMachine()

        # Settings flags (toggled via Settings menu)
        self.use_sprites = True      # False = primitive rendering only
        self.sfx_enabled = True
        self.bgm_enabled = True
        self.show_fps = False

        # Register all states
        self.state_machine.register("title", TitleState(self))
        self.state_machine.register("gameplay", GameplayState(self))
        self.state_machine.register("instructions", InstructionsState(self))
        self.state_machine.register("pause", PauseState(self))
        self.state_machine.register("game_over", GameOverState(self))
        self.state_machine.register("victory", VictoryState(self))
        self.state_machine.register("settings", SettingsState(self))

        self.state_machine.change("title")

    def run(self):
        """Main game loop: process events, update, render at TARGET_FPS."""
        while self.running:
            dt = self.clock.tick(TARGET_FPS) / 1000.0
            dt = min(dt, MAX_DT)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            self.input.update(pygame.key.get_pressed())
            self.state_machine.update(dt)
            self.state_machine.render(self.screen)
            if self.show_fps:
                fps_font = pygame.font.Font(None, 20)
                fps_surf = fps_font.render(f"FPS: {int(self.clock.get_fps())}", True, (200, 200, 200))
                self.screen.blit(fps_surf, (SCREEN_W - fps_surf.get_width() - 5, 2))
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    Game().run()
