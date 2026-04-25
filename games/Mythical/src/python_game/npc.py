"""
NPC entity — a static character with quest-conditional dialogue.
On GBA: struct in EWRAM, sprite in OAM.
"""

import pygame
import math
from ui.fonts import get_font
from runtime.frame_clock import get_time
from settings import TILE_SIZE
from placeholder_sprites import generate_character_sheet


class NPC:
    def __init__(
        self,
        name: str,
        npc_id: str,
        tile_x: int,
        tile_y: int,
        dialogue_stages: dict[int | str, list[str]],
        body_color: tuple[int, int, int] = (180, 80, 60),
        hair_color: tuple[int, int, int] | None = None,
        facing: str = "down",
        gives_item: dict | list | None = None,
        takes_item: dict | None = None,
    ):
        """
        dialogue_stages: maps quest stage (int) or "default"/"complete" to dialogue pages.
            Example: {0: ["Talk to me first..."], 1: ["Great, you have the sword!"], "default": ["Hello."]}
        gives_item: {"quest_stage": int, "item_id": str} — NPC gives item at this stage
        takes_item: {"quest_stage": int, "item_id": str} — NPC takes item at this stage
        """
        self.name = name
        self.npc_id = npc_id
        self.x = tile_x
        self.y = tile_y
        self.dialogue_stages = dialogue_stages
        # Normalize gives_item to a list
        if gives_item is None:
            self.gives_items = []
        elif isinstance(gives_item, dict):
            self.gives_items = [gives_item]
        else:
            self.gives_items = list(gives_item)
        self.takes_item = takes_item
        self.facing = facing

        self.sprites = generate_character_sheet(
            body_color=body_color,
            hair_color=hair_color,
        )
        self.anim_frame = 0

    def get_dialogue(self, quest_stage: int, quest_complete: bool) -> list[str]:
        """Get the right dialogue for the current quest state."""
        if quest_complete and "complete" in self.dialogue_stages:
            return self.dialogue_stages["complete"]
        if quest_stage in self.dialogue_stages:
            return self.dialogue_stages[quest_stage]
        return self.dialogue_stages.get("default", ["..."])

    def occupies(self, tile_x: int, tile_y: int) -> bool:
        return self.x == tile_x and self.y == tile_y

    def render(self, screen: pygame.Surface, cam_x: int, cam_y: int):
        sx = int(self.x * TILE_SIZE) - cam_x
        sy = int(self.y * TILE_SIZE) - cam_y
        frame_surf = self.sprites[self.facing][self.anim_frame]
        screen.blit(frame_surf, (sx, sy))

        # Name label with shadow
        font = get_font(10)
        label = font.render(self.name, True, (255, 255, 255))
        shadow = font.render(self.name, True, (0, 0, 0))
        lx = sx + TILE_SIZE // 2 - label.get_width() // 2
        ly = sy - 14
        screen.blit(shadow, (lx + 1, ly + 1))
        screen.blit(label, (lx, ly))

        # Interaction indicator (! above head when interactable)
        bang_font = get_font(14, bold=True)
        bang = bang_font.render("!", True, (255, 220, 60))
        bob = int(2 * math.sin(get_time() * (1000.0 / 300.0)))
        screen.blit(bang, (sx + TILE_SIZE // 2 - 3, sy - 22 + bob))
