"""Pygame-specific keyboard translation into logical game buttons."""
from __future__ import annotations

import pygame


PYGAME_KEY_BINDINGS = {
    "up": (pygame.K_UP, pygame.K_w),
    "down": (pygame.K_DOWN, pygame.K_s),
    "left": (pygame.K_LEFT, pygame.K_a),
    "right": (pygame.K_RIGHT, pygame.K_d),
    "a": (pygame.K_z, pygame.K_RETURN),
    "b": (pygame.K_x, pygame.K_BACKSPACE),
    "start": (pygame.K_ESCAPE,),
    "select": (pygame.K_TAB,),
    "l": (pygame.K_q,),
    "r": (pygame.K_e,),
    "dash": (pygame.K_LSHIFT,),
    "sort": (pygame.K_F6,),
    "skill": (pygame.K_k,),
    "craft": (pygame.K_c,),
    "travel": (pygame.K_t,),
    "hotbar1": (pygame.K_1,),
    "hotbar2": (pygame.K_2,),
    "hotbar3": (pygame.K_3,),
    "hotbar4": (pygame.K_4,),
    "hotbar5": (pygame.K_5,),
    "hotbar6": (pygame.K_6,),
    "hotbar7": (pygame.K_7,),
    "hotbar8": (pygame.K_8,),
    "debug_paths": (pygame.K_F1,),
    "debug_heatmap": (pygame.K_F2,),
    "debug_labels": (pygame.K_F3,),
    "debug_targets": (pygame.K_F4,),
    "debug_info": (pygame.K_F5,),
}


_BUTTONS_BY_KEY: dict[int, tuple[str, ...]] = {}
for _button_name, _keys in PYGAME_KEY_BINDINGS.items():
    for _key in _keys:
        _BUTTONS_BY_KEY.setdefault(_key, []).append(_button_name)
_BUTTONS_BY_KEY = {key: tuple(buttons) for key, buttons in _BUTTONS_BY_KEY.items()}


class PygameInputAdapter:
    def route_event(self, input_handler, event) -> None:
        if event.type not in (pygame.KEYDOWN, pygame.KEYUP):
            return

        for button_name in _BUTTONS_BY_KEY.get(getattr(event, "key", None), ()):
            if event.type == pygame.KEYDOWN:
                input_handler.press(button_name)
            else:
                input_handler.release(button_name)
