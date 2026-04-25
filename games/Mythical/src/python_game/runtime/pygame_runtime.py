"""Desktop pygame runtime adapter."""
from __future__ import annotations

import pygame

from audio_manager import AudioManager
from input_handler import InputHandler
from runtime.null_audio import NullAudioManager
from runtime.pygame_input import PygameInputAdapter
from runtime.target_profiles import PYGAME_PROFILE
from save_manager import load_game, save_exists, write_save_data


class PygameRuntime:
    name = "pygame"
    profile = PYGAME_PROFILE

    def __init__(self):
        self._input_adapter = PygameInputAdapter()
        self._mixer_ready = False

    def boot(self, title: str, screen_size: tuple[int, int]):
        pygame.init()
        try:
            pygame.mixer.init(22050, -16, 1, 512)
            self._mixer_ready = True
        except pygame.error:
            self._mixer_ready = False
        screen = pygame.display.set_mode(screen_size)
        pygame.display.set_caption(title)
        clock = pygame.time.Clock()
        return screen, clock

    def shutdown(self) -> None:
        pygame.quit()

    def tick(self, clock, target_fps: int) -> float:
        return clock.tick(target_fps) / 1000.0

    def poll_events(self) -> list[pygame.event.Event]:
        return list(pygame.event.get())

    def present(self) -> None:
        pygame.display.flip()

    def create_input(self):
        return InputHandler()

    def create_audio(self):
        if not self.profile.supports_procedural_audio or not self._mixer_ready:
            return NullAudioManager()
        try:
            return AudioManager()
        except pygame.error:
            return NullAudioManager()

    def route_input_event(self, input_handler, event) -> None:
        self._input_adapter.route_event(input_handler, event)

    def load_save(self) -> dict | None:
        return load_game()

    def write_save(self, data: dict) -> bool:
        return write_save_data(data)

    def save_exists(self) -> bool:
        return save_exists()
