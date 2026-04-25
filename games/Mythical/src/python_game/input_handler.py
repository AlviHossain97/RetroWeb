"""
Input handler — abstracts keyboard into GBA-style button states.
Tracks pressed (held), just_pressed (this frame), and just_released.
On GBA this maps directly to REG_KEYINPUT reads.
"""

from settings import INPUT_MAP


class InputHandler:
    def __init__(self, buttons=None):
        self.buttons = tuple(buttons or INPUT_MAP)
        self.held = {btn: False for btn in self.buttons}
        self.just_pressed = {btn: False for btn in self.buttons}
        self.just_released = {btn: False for btn in self.buttons}

    def update(self):
        """Call once per frame BEFORE processing events — clears edge triggers."""
        for btn in self.buttons:
            self.just_pressed[btn] = False
            self.just_released[btn] = False

    def press(self, btn: str):
        """Mark a logical button as pressed for this frame."""
        if btn not in self.held:
            return
        if not self.held[btn]:
            self.held[btn] = True
            self.just_pressed[btn] = True

    def release(self, btn: str):
        """Mark a logical button as released for this frame."""
        if btn not in self.held:
            return
        if self.held[btn]:
            self.held[btn] = False
            self.just_released[btn] = True

    def is_held(self, btn: str) -> bool:
        return self.held.get(btn, False)

    def is_pressed(self, btn: str) -> bool:
        return self.just_pressed.get(btn, False)

    def is_released(self, btn: str) -> bool:
        return self.just_released.get(btn, False)
