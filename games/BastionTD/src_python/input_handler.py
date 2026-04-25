"""
input_handler.py - GBA-button abstraction for keyboard input.

Tracks previous and current frame key states to provide pressed (first frame only),
held (continuously down), and released (first frame up) queries per logical action.
"""
from settings import INPUT_MAP


class InputHandler:
    """Maps physical keyboard keys to logical GBA-style actions with edge detection."""

    def __init__(self):
        # Current frame: True if ANY mapped key for that action is down
        self._current = {action: False for action in INPUT_MAP}
        # Previous frame snapshot
        self._previous = {action: False for action in INPUT_MAP}

    def update(self, pygame_keys):
        """Call once per frame with the result of pygame.key.get_pressed().

        Snapshots the previous state, then samples every mapped key to compute
        the new current state for each logical action.
        """
        # Rotate: current becomes previous
        for action in INPUT_MAP:
            self._previous[action] = self._current[action]

        # Sample new state
        for action, key_list in INPUT_MAP.items():
            self._current[action] = any(pygame_keys[k] for k in key_list)

    def pressed(self, action: str) -> bool:
        """True only on the first frame the action's key(s) go down."""
        return self._current.get(action, False) and not self._previous.get(action, False)

    def held(self, action: str) -> bool:
        """True every frame the action's key(s) are held down."""
        return self._current.get(action, False)

    def released(self, action: str) -> bool:
        """True only on the first frame the action's key(s) come back up."""
        return not self._current.get(action, False) and self._previous.get(action, False)
