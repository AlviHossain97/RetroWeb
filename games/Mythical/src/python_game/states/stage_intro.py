"""
Stage intro card — displayed when the player enters a new campaign stage.

Shown as a full-screen fade-in/hold/fade-out card.
After the animation completes the state transitions to "gameplay".

Usage (from gameplay.py):
    self.game.states.get("stage_intro").prepare(stage_number, stage_name)
    self.game.states.change("stage_intro")
"""

from __future__ import annotations

import math
import pygame

from states.state_machine import State
from ui.fonts import get_font
from campaign import STAGE_NAMES


_STAGE_SUBTITLES: dict[int, str] = {
    1: STAGE_NAMES.get(1, "Act I"),
    2: STAGE_NAMES.get(2, "Act II"),
    3: STAGE_NAMES.get(3, "Act III"),
}

_STAGE_COLORS: dict[int, tuple] = {
    1: (40, 80, 40),  # forest green tinge
    2: (50, 20, 60),  # deep purple/ruin dark
    3: (20, 10, 40),  # void black with gold
}

_STAGE_TEXT_COLORS: dict[int, tuple] = {
    1: (160, 220, 160),
    2: (180, 120, 220),
    3: (255, 220, 80),
}

_TOTAL_DURATION = 3.6  # seconds: fade-in 0.8 + hold 2.0 + fade-out 0.8


class StageIntroState(State):
    def __init__(self, game):
        super().__init__(game)
        self.stage_number = 1
        self.stage_name = "Act I"
        self.timer = 0.0

    def prepare(self, stage_number: int, stage_name: str | None = None) -> None:
        self.stage_number = stage_number
        if stage_name:
            self.stage_name = stage_name
        else:
            subtitle = _STAGE_SUBTITLES.get(stage_number, f"Act {stage_number}")
            self.stage_name = subtitle

    def enter(self) -> None:
        self.timer = 0.0
        if hasattr(self.game, "audio"):
            self.game.audio.stop_music()

    def update(self, dt: float) -> None:
        self.timer += dt
        if self.timer >= _TOTAL_DURATION:
            # Load the entry map for the new stage before changing state
            campaign = getattr(self.game, "campaign", None)
            gs = self.game.states._states.get("gameplay")
            if gs and campaign:
                entry_map = campaign.get_entry_map(self.stage_number)
                if hasattr(gs, "_load_map"):
                    gs.defeated_boss = False
                    gs.boss_save_state = {}
                    gs._boss_defeat_timer = 0.0
                    gs._load_map(
                        entry_map, capture_checkpoint=True, grant_transition_heal=True
                    )
                    gs._sync_player_weapon()
                    if hasattr(gs, "_init_player_forms"):
                        gs._init_player_forms()
            self.game.states.change("gameplay")

    def render(self, screen: pygame.Surface) -> None:
        t = self.timer
        vw, vh = self._viewport_size(screen)
        compact = self._is_compact_view(screen)
        bg_col = _STAGE_COLORS.get(self.stage_number, (10, 5, 20))
        txt_col = _STAGE_TEXT_COLORS.get(self.stage_number, (200, 200, 200))

        # Background
        screen.fill(bg_col)

        # Compute alpha for fade-in / hold / fade-out
        fade_in_end = 0.8
        hold_end = fade_in_end + 2.0
        fade_out_end = hold_end + 0.8
        if t < fade_in_end:
            alpha = int(255 * (t / fade_in_end))
        elif t < hold_end:
            alpha = 255
        else:
            alpha = int(255 * max(0.0, 1.0 - (t - hold_end) / 0.8))

        # Act number label (small, dimmer)
        act_font = get_font(12 if compact else 14)
        act_str = f"ACT {self.stage_number}"
        act_surf = act_font.render(act_str, True, txt_col)
        act_surf.set_alpha(alpha)
        screen.blit(
            act_surf,
            (vw // 2 - act_surf.get_width() // 2, vh // 2 - (40 if compact else 60)),
        )

        # Stage name (large)
        title_font = get_font(22 if compact else 34, bold=True)
        title_surf = title_font.render(self.stage_name, True, txt_col)
        title_surf.set_alpha(alpha)
        screen.blit(
            title_surf,
            (vw // 2 - title_surf.get_width() // 2, vh // 2 - (12 if compact else 20)),
        )

        # Decorative divider line (fades with text)
        line_w = min(280, max(120, vw - 40))
        line_surf = pygame.Surface((line_w, 2), pygame.SRCALPHA)
        line_surf.fill(txt_col + (alpha,))
        screen.blit(
            line_surf, (vw // 2 - line_w // 2, vh // 2 + (14 if compact else 26))
        )

        # Flavour line (stage-specific)
        flavour = {
            1: "Your journey begins.",
            2: "The dead do not rest easily.",
            3: "The fate of the world rests with you.",
        }.get(self.stage_number, "")
        if flavour and t > 0.6:
            sub_font = get_font(11 if compact else 13)
            sub_alpha = int(alpha * min(1.0, (t - 0.6) / 0.6))
            sub_surf = sub_font.render(flavour, True, (200, 200, 210))
            sub_surf.set_alpha(sub_alpha)
            screen.blit(
                sub_surf,
                (
                    vw // 2 - sub_surf.get_width() // 2,
                    vh // 2 + (24 if compact else 40),
                ),
            )

        # Star/particle flourish for Stage 3
        if self.stage_number == 3:
            particle_count = 12 if compact else 20
            base_x = 44 if compact else 80
            base_y = 26 if compact else 50
            for i in range(particle_count):
                x = vw // 2 + int(
                    math.cos(i * 1.1 + t) * (base_x + i * (4 if compact else 8))
                )
                y = vh // 2 + int(
                    math.sin(i * 0.9 + t * 0.7) * (base_y + i * (2 if compact else 4))
                )
                a = int(60 + 40 * math.sin(t * 2 + i))
                star_surf = pygame.Surface((4, 4), pygame.SRCALPHA)
                pygame.draw.circle(star_surf, (255, 220, 100, a), (2, 2), 2)
                screen.blit(star_surf, (x, y))
