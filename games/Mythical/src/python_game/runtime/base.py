"""Runtime protocol used to keep platform bootstrapping separate from game logic."""
from __future__ import annotations

from typing import Any, Protocol

from runtime.target_profiles import TargetProfile


class RuntimeAdapter(Protocol):
    name: str
    profile: TargetProfile

    def boot(self, title: str, screen_size: tuple[int, int]) -> tuple[Any, Any]:
        ...

    def shutdown(self) -> None:
        ...

    def tick(self, clock: Any, target_fps: int) -> float:
        ...

    def poll_events(self) -> list[Any]:
        ...

    def present(self) -> None:
        ...

    def create_input(self) -> Any:
        ...

    def create_audio(self) -> Any:
        ...

    def route_input_event(self, input_handler: Any, event: Any) -> None:
        ...

    def load_save(self) -> dict | None:
        ...

    def write_save(self, data: dict) -> bool:
        ...

    def save_exists(self) -> bool:
        ...
