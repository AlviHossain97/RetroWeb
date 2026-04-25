"""
Minimal state machine. Register named states, switch between them.
On GBA this becomes a function pointer table.
"""

from runtime.display_defaults import (
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_VIEWPORT_WIDTH,
)


class State:
    """Base class for all game states."""

    def __init__(self, game):
        self.game = game

    def _viewport_size(self, screen=None) -> tuple[int, int]:
        if screen is not None and hasattr(screen, "get_size"):
            return tuple(int(v) for v in screen.get_size())
        profile = getattr(self.game, "target_profile", None)
        width = getattr(profile, "screen_width", DEFAULT_VIEWPORT_WIDTH)
        height = getattr(profile, "screen_height", DEFAULT_VIEWPORT_HEIGHT)
        return int(width), int(height)

    def _is_compact_view(self, screen=None) -> bool:
        width, height = self._viewport_size(screen)
        return width < 320 or height < 220

    def enter(self):
        """Called when this state becomes active."""
        pass

    def exit(self):
        """Called when leaving this state."""
        pass

    def update(self, dt: float):
        raise NotImplementedError

    def render(self, screen):
        raise NotImplementedError


class StateMachine:
    def __init__(self):
        self._states: dict[str, State] = {}
        self.current: State | None = None
        self.current_name: str = ""

    def register(self, name: str, state: State):
        self._states[name] = state

    def change(self, name: str):
        if self.current:
            self.current.exit()
        self.current = self._states[name]
        self.current_name = name
        self.current.enter()

    def update(self, dt: float):
        if self.current:
            self.current.update(dt)

    def render(self, screen):
        if self.current:
            self.current.render(screen)
