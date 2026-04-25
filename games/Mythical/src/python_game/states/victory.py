"""
Victory / stage-completion screen.

Stage 1 completion → Dark Golem defeated → transitions to Stage 2 intro
Stage 2 completion → Gravewarden defeated → transitions to Stage 3 intro
Stage 3 completion → Mythic Sovereign defeated → TRUE FINAL ENDING

The screen is only shown after the Stage 3 boss for the real finale.
Intermediate stage completions show a brief "Stage Complete" card and
route the player to the Stage 2/3 intro instead.
"""

import pygame
import math
from settings import COLOR_ACCENT, COLOR_WHITE
from states.state_machine import State
from ui.fonts import get_font
from campaign import STAGE_NAMES, STAGE_BOSS_IDS, FORM_LABELS
from bestiary import ENTRY_DEFS


class VictoryState(State):
    def __init__(self, game):
        super().__init__(game)
        self.timer = 0.0
        self._completed_stage = 3  # set by the caller before changing state

    def prepare(self, completed_stage: int) -> None:
        """Call before changing to this state to set which stage just ended."""
        self._completed_stage = completed_stage

    def _recover_from_invalid_finale(self) -> None:
        """
        If something routes into the final victory screen too early, fall back
        to playable Stage 3 content instead of trapping the user in the ending.
        """
        gameplay = self.game.states._states.get("gameplay")
        campaign = getattr(self.game, "campaign", None)
        if gameplay and campaign and getattr(campaign, "world_stage", 1) >= 3:
            gameplay.defeated_boss = False
            gameplay.boss_save_state = {}
            gameplay._boss_defeat_timer = 0.0
            if hasattr(gameplay, "_load_map"):
                gameplay._load_map(
                    campaign.get_entry_map(3),
                    capture_checkpoint=True,
                    grant_transition_heal=False,
                )
                if hasattr(gameplay, "_sync_player_weapon"):
                    gameplay._sync_player_weapon()
                if hasattr(gameplay, "_init_player_forms"):
                    gameplay._init_player_forms()
            self.game.states.change("gameplay")
            return
        if gameplay:
            self.game.states.change("gameplay")
            return
        self.game.states.change("title")

    def enter(self):
        campaign = getattr(self.game, "campaign", None)
        if (
            self._completed_stage >= 3
            and campaign
            and not campaign.is_final_stage_complete()
        ):
            self._recover_from_invalid_finale()
            return
        self.timer = 0
        if hasattr(self.game, "audio"):
            self.game.audio.stop_music()
            self.game.audio.play_sfx("victory")

    def update(self, dt):
        self.timer += dt
        if self.timer > 2.0:
            if self.game.input.is_pressed("a") or self.game.input.is_pressed("start"):
                if self._completed_stage < 3:
                    next_stage = self._completed_stage + 1
                    intro = self.game.states._states.get("stage_intro")
                    campaign = getattr(self.game, "campaign", None)
                    if intro and hasattr(intro, "prepare"):
                        stage_name = (
                            campaign.get_stage_name(next_stage)
                            if campaign
                            else f"Act {next_stage}"
                        )
                        intro.prepare(next_stage, stage_name)
                        self.game.states.change("stage_intro")
                        return
                self.game.states.change("title")

    def render(self, screen):
        stage = self._completed_stage
        if stage < 3:
            self._render_stage_complete(screen, stage)
        else:
            self._render_final_victory(screen)

    # ── Intermediate stage completion (Stage 1 or 2) ──────────────────────────

    def _render_stage_complete(self, screen: pygame.Surface, stage: int) -> None:
        t = self.timer
        vw, vh = self._viewport_size(screen)
        compact = self._is_compact_view(screen)
        bg_colors = {1: (10, 30, 10), 2: (30, 10, 40)}
        accent_colors = {1: (140, 220, 140), 2: (180, 100, 220)}
        boss_id = STAGE_BOSS_IDS.get(stage)
        boss_name = (
            ENTRY_DEFS.get(boss_id, {}).get("name", "Boss") if boss_id else "Boss"
        )
        next_stage = stage + 1
        next_name = STAGE_NAMES.get(next_stage, f"Act {next_stage}")

        screen.fill(bg_colors.get(stage, (10, 10, 30)))

        alpha = min(255, int(t * 200))
        title_font = get_font(24 if compact else 32, bold=True)
        txt_col = accent_colors.get(stage, (200, 200, 200))
        ts = title_font.render("STAGE COMPLETE", True, txt_col)
        ts.set_alpha(alpha)
        title_y = 28 if compact else 120
        screen.blit(ts, (vw // 2 - ts.get_width() // 2, title_y))

        if t > 0.7:
            sub_font = get_font(13 if compact else 16)
            lines = [
                f"{boss_name} has fallen.",
                "",
                f"Next: {next_name}",
            ]
            for i, line in enumerate(lines):
                s = sub_font.render(line, True, (200, 200, 210))
                s.set_alpha(min(255, int((t - 0.7) * 300)))
                sub_y = (70 if compact else 200) + i * (18 if compact else 28)
                screen.blit(s, (vw // 2 - s.get_width() // 2, sub_y))

        if t > 2.5:
            prompt_font = get_font(11 if compact else 13)
            blink = int(t * 2) % 2
            if blink:
                ps = prompt_font.render("Press A to continue", True, (150, 150, 160))
                screen.blit(
                    ps, (vw // 2 - ps.get_width() // 2, vh - (26 if compact else 50))
                )

    # ── True final victory (Stage 3 complete) ────────────────────────────���───

    def _render_final_victory(self, screen: pygame.Surface) -> None:
        t = self.timer
        vw, vh = self._viewport_size(screen)
        compact = self._is_compact_view(screen)
        screen.fill((8, 6, 16))

        boss_id = STAGE_BOSS_IDS.get(3)
        boss_display = (
            ENTRY_DEFS.get(boss_id, {}).get("name", "Mythic Sovereign")
            if boss_id
            else "Mythic Sovereign"
        )
        champion_label = FORM_LABELS.get("mythic", "Mythic Champion")

        # Gold particles
        particle_count = 20 if compact else 40
        radius_base = 44 if compact else 90
        for i in range(particle_count):
            x = vw // 2 + int(
                math.cos(i * 0.8 + t) * (radius_base + i * (2 if compact else 4))
            )
            y = vh - int((t * 50 + i * 12) % vh)
            pygame.draw.circle(screen, (255, 210, 80), (x, y), 2)

        # Title
        alpha = min(255, int(t * 150))
        title_font = get_font(28 if compact else 46, bold=True)
        ts = title_font.render("VICTORY", True, (255, 210, 60))
        ts.set_alpha(alpha)
        screen.blit(ts, (vw // 2 - ts.get_width() // 2, 28 if compact else 100))

        if t > 0.8:
            sub_alpha = min(255, int((t - 0.8) * 180))
            sub_font = get_font(11 if compact else 15)
            if compact:
                lines = [
                    f"{boss_display} destroyed.",
                    "The sanctum collapses into the void.",
                    "The mortal realm is free.",
                    f"You are the {champion_label}.",
                    "Thank you for playing MYTHICAL.",
                ]
                start_y = 68
                line_step = 15
            else:
                lines = [
                    f"The {boss_display} has been destroyed.",
                    "The shattered sanctum crumbles into the void.",
                    "",
                    "The mortal realm is free.",
                    "",
                    f"You are the {champion_label}.",
                    "",
                    "Thank you for playing MYTHICAL.",
                ]
                start_y = 190
                line_step = 24
            for i, line in enumerate(lines):
                col = (255, 220, 100) if champion_label in line else (200, 200, 210)
                s = sub_font.render(line, True, col)
                s.set_alpha(sub_alpha)
                screen.blit(s, (vw // 2 - s.get_width() // 2, start_y + i * line_step))

        if t > 3.0:
            prompt_font = get_font(11 if compact else 13)
            blink = int(t * 2) % 2
            if blink:
                ps = prompt_font.render(
                    "Press A to return to title", True, (150, 150, 160)
                )
                screen.blit(
                    ps, (vw // 2 - ps.get_width() // 2, vh - (18 if compact else 46))
                )
