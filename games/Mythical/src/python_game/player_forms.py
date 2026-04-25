"""
player_forms.py — Player visual and stat progression across campaign stages.

Three forms track the player's journey:
  base    (Stage 1) — Adventurer.   Standard blue-grey tunic.
  hero    (Stage 2) — Hero.         Dark armored look, weapon trail, slight glow.
  mythic  (Stage 3) — Mythic Champ. Gold/white aura, transformed weapon, blazing eyes.

Forms are purely visual and cosmetic stat-feel; the real stat gains come
from equipment and progression.  BUT forms do grant a small flat bonus so
the player feels the transformation mechanically too.

Usage:
  forms = PlayerForms(campaign)
  visual = forms.get_visual_config()  # pass to placeholder_sprites / HUD
  bonuses = forms.get_stat_bonuses()  # add to get_combat_stats() result
"""
from __future__ import annotations
from game_math import pulse01

# ── Form definitions ─────────────────────────────────────────────────────────
#
# visual: dict fed to the HUD / sprite generator for tint/overlay hints.
# bonuses: flat stat modifiers stacked on top of skill/equipment bonuses.
# label: display name shown in the HUD form indicator.

FORM_DEFS: dict[str, dict] = {
    "base": {
        "label":        "Adventurer",
        "description":  "A capable traveller, beginning their journey.",
        "body_tint":    (200, 190, 220),     # slight blue-grey
        "weapon_tint":  (180, 170, 160),
        "aura_color":   None,                # no aura
        "eye_color":    (40, 40, 80),
        "aura_alpha":   0,
        "trail_color":  None,
        "bonuses": {
            "attack_bonus": 0,
            "speed_bonus":  0.0,
            "defense":      0,
            "crit_chance":  0.0,
        },
    },
    "hero": {
        "label":        "Hero",
        "description":  "A hardened warrior who has walked through death.",
        "body_tint":    (140, 100, 180),     # dark purple-steel
        "weapon_tint":  (160, 130, 220),     # runic purple glow on weapon
        "aura_color":   (120, 80, 200),
        "eye_color":    (180, 100, 255),     # glowing purple eyes
        "aura_alpha":   45,
        "trail_color":  (140, 80, 220),      # faint runic trail on attack
        "bonuses": {
            "attack_bonus": 1,               # +1 flat attack
            "speed_bonus":  0.15,            # +0.15 tile/s
            "defense":      1,               # +1 flat defense
            "crit_chance":  0.05,            # +5% crit
        },
    },
    "mythic": {
        "label":        "Mythic Champion",
        "description":  "A transcended warrior — the hope of the mortal realm.",
        "body_tint":    (220, 200, 80),      # gold/white
        "weapon_tint":  (255, 240, 120),     # blazing gold weapon
        "aura_color":   (255, 230, 80),
        "eye_color":    (255, 220, 40),      # blazing gold eyes
        "aura_alpha":   75,
        "trail_color":  (255, 200, 50),      # gold blazing attack trail
        "bonuses": {
            "attack_bonus": 2,               # +2 flat attack
            "speed_bonus":  0.35,            # +0.35 tile/s
            "defense":      2,               # +2 flat defense
            "crit_chance":  0.12,            # +12% crit
        },
    },
}


class PlayerForms:
    """Manages the player's current form state."""

    def __init__(self, campaign) -> None:
        self._campaign = campaign

    @property
    def current_form(self) -> str:
        return getattr(self._campaign, "player_form", "base")

    def get_form_def(self) -> dict:
        return FORM_DEFS.get(self.current_form, FORM_DEFS["base"])

    def get_visual_config(self) -> dict:
        """
        Returns the visual config for this form.  Used by HUD and
        render layer to apply tints/aura/trail.
        """
        fd = self.get_form_def()
        return {
            "form":         self.current_form,
            "label":        fd["label"],
            "body_tint":    fd["body_tint"],
            "weapon_tint":  fd["weapon_tint"],
            "aura_color":   fd["aura_color"],
            "aura_alpha":   fd["aura_alpha"],
            "eye_color":    fd["eye_color"],
            "trail_color":  fd["trail_color"],
        }

    def get_stat_bonuses(self) -> dict:
        """
        Flat stat bonuses granted by the current form.  Gameplay layer
        should add these to the progression.get_combat_stats() result.
        """
        return dict(FORM_DEFS.get(self.current_form, FORM_DEFS["base"])["bonuses"])

    def is_upgraded(self) -> bool:
        """True if the player has progressed beyond the base form."""
        return self.current_form != "base"

    def render_aura(self, screen, sx: int, sy: int, tile_size: int, timer: float) -> None:
        """
        Draw the form aura around the player sprite.
        Called from gameplay render after the player sprite is drawn.
        """
        import pygame
        fd = self.get_form_def()
        aura_color = fd["aura_color"]
        aura_alpha = fd["aura_alpha"]
        if not aura_color or aura_alpha <= 0:
            return
        pulse = pulse01(timer, 3.5)
        alpha = int(aura_alpha * pulse)
        r = int(tile_size * (0.70 + 0.15 * pulse))
        aura_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(aura_surf, aura_color + (alpha,), (r, r), r)
        screen.blit(aura_surf, (sx - r + tile_size // 2, sy - r + tile_size // 2))

    def render_attack_trail(
        self, screen, sx: int, sy: int, tile_size: int, facing: str
    ) -> None:
        """Draw a brief colour trail behind a player attack swing."""
        import pygame
        fd = self.get_form_def()
        trail_color = fd["trail_color"]
        if not trail_color:
            return
        offsets = {
            "right": [(10, 0), (16, -4), (16, 4)],
            "left":  [(-10, 0), (-16, -4), (-16, 4)],
            "up":    [(0, -10), (-4, -16), (4, -16)],
            "down":  [(0, 10),  (-4, 16),  (4, 16)],
        }.get(facing, [(0, 0)])
        cx = sx + tile_size // 2
        cy = sy + tile_size // 2
        for ox, oy in offsets:
            pygame.draw.circle(screen, trail_color, (cx + ox, cy + oy), 3)
