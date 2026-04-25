"""
Dialogue box — RPG-style text box with typewriter effect.
Supports multiple pages, advances with A button, closes with B or after last page.
On GBA: text rendered to a BG layer or OBJ tiles, with a VBlank-driven char timer.
"""

import pygame
from runtime.display_defaults import (
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_VIEWPORT_WIDTH,
)
from settings import COLOR_UI_BG, COLOR_UI_BORDER, COLOR_WHITE
from ui.fonts import get_font


class DialogueBox:
    def __init__(
        self,
        viewport_width: int = DEFAULT_VIEWPORT_WIDTH,
        viewport_height: int = DEFAULT_VIEWPORT_HEIGHT,
    ):
        self.active = False
        self.pages: list[str] = []
        self.page_index = 0
        self.speaker = ""
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height

        # Typewriter state
        self.chars_shown = 0
        self.char_timer = 0.0
        self.char_speed = 0.03  # seconds per character
        self.finished_page = False

        # Layout — sits above the hotbar/XP bar/minimap strip at the bottom
        self.box_height = 90
        self.box_x = 8
        self.box_w = viewport_width - 16
        self.box_y = viewport_height - self.box_height - 76
        self.padding = 10
        self.font = None
        self.name_font = None
        self._apply_layout()

    def set_viewport_size(self, width: int, height: int):
        self.viewport_width = max(1, int(width))
        self.viewport_height = max(1, int(height))
        self._apply_layout()

    def _sync_viewport(self, screen):
        if screen is not None and hasattr(screen, "get_size"):
            self.set_viewport_size(*screen.get_size())

    def _apply_layout(self):
        self.box_x = 8
        self.box_w = max(120, self.viewport_width - 16)
        if self.viewport_height >= 220:
            reserved_bottom = 76
            self.box_height = 90
        else:
            reserved_bottom = 44
            self.box_height = max(56, min(78, self.viewport_height // 3))
        self.box_y = max(8, self.viewport_height - self.box_height - reserved_bottom)

    def _ensure_fonts(self):
        if self.font is None:
            self.font = get_font(14)
            self.name_font = get_font(13, bold=True)

    def open(self, speaker: str, pages: list[str]):
        """Start a dialogue sequence."""
        self.active = True
        self.speaker = speaker
        self.pages = pages
        self.page_index = 0
        self.chars_shown = 0
        self.char_timer = 0.0
        self.finished_page = False

    def close(self):
        self.active = False
        self.pages = []
        self.page_index = 0

    def update(self, dt: float, input_handler) -> bool:
        """Update typewriter. Returns True while dialogue is active."""
        if not self.active:
            return False

        current_text = self.pages[self.page_index]

        if not self.finished_page:
            self.char_timer += dt
            while self.char_timer >= self.char_speed and self.chars_shown < len(current_text):
                self.chars_shown += 1
                self.char_timer -= self.char_speed
            if self.chars_shown >= len(current_text):
                self.finished_page = True

        # A button: advance or show all text
        if input_handler.is_pressed("a"):
            if not self.finished_page:
                # Show full page instantly
                self.chars_shown = len(current_text)
                self.finished_page = True
            else:
                # Next page
                self.page_index += 1
                if self.page_index >= len(self.pages):
                    self.close()
                    return False
                self.chars_shown = 0
                self.char_timer = 0.0
                self.finished_page = False

        # B button: close immediately
        if input_handler.is_pressed("b"):
            self.close()
            return False

        return True

    def render(self, screen: pygame.Surface):
        if not self.active:
            return

        self._sync_viewport(screen)
        self._ensure_fonts()

        # Box background
        box_rect = pygame.Rect(self.box_x, self.box_y, self.box_w, self.box_height)
        pygame.draw.rect(screen, COLOR_UI_BG, box_rect, border_radius=6)
        pygame.draw.rect(screen, COLOR_UI_BORDER, box_rect, 2, border_radius=6)

        # Speaker name tag
        if self.speaker:
            name_surf = self.name_font.render(self.speaker, True, (120, 200, 255))
            screen.blit(name_surf, (self.box_x + self.padding, self.box_y + 6))

        # Text with word wrap and typewriter
        current_text = self.pages[self.page_index]
        visible_text = current_text[: self.chars_shown]

        text_x = self.box_x + self.padding
        text_y = self.box_y + 24
        max_width = self.box_w - self.padding * 2
        line_height = self.font.get_linesize()

        # Simple word-wrap
        words = visible_text.split(" ")
        line = ""
        for word in words:
            test = line + (" " if line else "") + word
            if self.font.size(test)[0] > max_width:
                surf = self.font.render(line, True, COLOR_WHITE)
                screen.blit(surf, (text_x, text_y))
                text_y += line_height
                line = word
            else:
                line = test
        if line:
            surf = self.font.render(line, True, COLOR_WHITE)
            screen.blit(surf, (text_x, text_y))

        # Advance prompt
        if self.finished_page:
            prompt = "Z: Next" if self.page_index < len(self.pages) - 1 else "Z: Close"
            prompt_surf = self.name_font.render(prompt, True, (130, 130, 145))
            px = self.box_x + self.box_w - self.padding - prompt_surf.get_width()
            py = self.box_y + self.box_height - 16
            screen.blit(prompt_surf, (px, py))
