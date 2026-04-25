"""Future-facing GBA runtime adapter stub.

This does not execute the game on GBA from CPython. It exists to give the
codebase a real second target surface while the port is being carved out.
"""
from __future__ import annotations

from runtime.null_audio import NullAudioManager
from runtime.target_profiles import GBA_PROFILE


class GBARuntime:
    name = "gba"
    profile = GBA_PROFILE

    def boot(self, title: str, screen_size: tuple[int, int]):
        raise RuntimeError(
            "The Python runtime target is still a desktop-only stub. "
            "Use the standalone gba_project/ build for the real handheld port, "
            "and keep using the default pygame runtime for the desktop game."
        )

    def shutdown(self) -> None:
        return None

    def tick(self, clock, target_fps: int) -> float:
        return 1.0 / float(target_fps)

    def poll_events(self) -> list[object]:
        return []

    def present(self) -> None:
        return None

    def create_input(self):
        return None

    def create_audio(self):
        return NullAudioManager()

    def route_input_event(self, input_handler, event) -> None:
        return None

    def load_save(self) -> dict | None:
        return None

    def write_save(self, data: dict) -> bool:
        return False

    def save_exists(self) -> bool:
        return False
