"""
Title screen — MYTHICAL logo, atmospheric animated background, premium menu.
"""
import pygame
import math
import random
from settings import COLOR_ACCENT
from states.state_machine import State
from ui.fonts import get_font

# Palette
_ACCENT2 = (55, 175, 105)   # darker accent
_DIM     = (75,  78,  92)


class _Orb:
    """A slow-drifting atmospheric light orb."""
    __slots__ = ("x", "y", "r", "speed", "phase", "col", "width", "height")

    def __init__(self, width: int, height: int, compact: bool = False):
        self.width = width
        self.height = height
        self.x     = random.uniform(0, width)
        self.y     = random.uniform(0, height)
        self.r     = random.uniform(10, 28) if compact else random.uniform(18, 55)
        self.speed = random.uniform(3, 10)
        self.phase = random.uniform(0, math.pi * 2)
        self.col   = random.choice([
            (30, 100, 60),
            (20,  70, 90),
            (55,  40, 80),
            (15,  85, 55),
        ])

    def update(self, dt):
        self.y -= self.speed * dt
        self.x += math.sin(self.phase + self.y * 0.01) * 0.4
        if self.y < -self.r * 2:
            self.y = self.height + self.r
            self.x = random.uniform(0, self.width)

    def render(self, surf, t):
        alpha = int(18 + 10 * math.sin(self.phase + t))
        glow  = pygame.Surface((int(self.r * 2), int(self.r * 2)), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.col, alpha),
                           (int(self.r), int(self.r)), int(self.r))
        surf.blit(glow, (int(self.x - self.r), int(self.y - self.r)),
                  special_flags=pygame.BLEND_RGBA_ADD)


class TitleState(State):
    def __init__(self, game):
        super().__init__(game)
        self.cursor      = 0
        self.timer       = 0.0
        self.menu_items  = []
        self._font       = None
        self._small_font = None
        self._tiny_font  = None
        self._title_font = None
        self._font_profile = None

        # Background layer data
        self._stars = []
        self._orbs = []
        self._viewport_bounds = (0, 0)
        self._bg_surf: pygame.Surface | None = None

    def _ensure_fonts(self, compact: bool = False):
        profile = "compact" if compact else "full"
        if self._font_profile != profile:
            if compact:
                self._font       = get_font(16)
                self._small_font = get_font(11)
                self._tiny_font  = get_font(9)
                self._title_font = get_font(36, bold=True)
            else:
                self._font       = get_font(22)
                self._small_font = get_font(14)
                self._tiny_font  = get_font(11)
                self._title_font = get_font(62, bold=True)
            self._font_profile = profile

    def _set_viewport(self, width: int, height: int):
        width = max(1, int(width))
        height = max(1, int(height))
        if (width, height) == self._viewport_bounds:
            return

        compact = width < 320 or height < 220
        star_count = 50 if compact else 90
        orb_count = 8 if compact else 12
        self._stars = [
            (
                random.randint(0, width),
                random.randint(0, height),
                random.uniform(0.2, 1.0),
                random.uniform(0.5, 3.0),
            )
            for _ in range(star_count)
        ]
        self._orbs = [_Orb(width, height, compact=compact) for _ in range(orb_count)]
        self._viewport_bounds = (width, height)

    def enter(self):
        self.timer  = 0.0
        self.cursor = 0
        self.menu_items = ["New Game"]
        if hasattr(self.game, "has_saved_game") and self.game.has_saved_game():
            self.menu_items.insert(0, "Continue")
        self.menu_items += ["Difficulty", "Instructions", "Quit"]
        if hasattr(self.game, "audio"):
            self.game.audio.play_music("title")

    def _current_item(self) -> str:
        return self.menu_items[self.cursor]

    def _cycle_difficulty(self, delta: int):
        self.game.cycle_difficulty(delta)
        if hasattr(self.game, "audio"):
            self.game.audio.play_sfx("menu_move")

    def update(self, dt):
        self.timer += dt
        for orb in self._orbs:
            orb.update(dt)

        inp = self.game.input
        if inp.is_pressed("up"):
            self.cursor = (self.cursor - 1) % len(self.menu_items)
            if hasattr(self.game, "audio"):
                self.game.audio.play_sfx("menu_move")
        elif inp.is_pressed("down"):
            self.cursor = (self.cursor + 1) % len(self.menu_items)
            if hasattr(self.game, "audio"):
                self.game.audio.play_sfx("menu_move")

        if self._current_item() == "Difficulty":
            if inp.is_pressed("left") or inp.is_pressed("l"):
                self._cycle_difficulty(-1)
            elif inp.is_pressed("right") or inp.is_pressed("r"):
                self._cycle_difficulty(1)

        if inp.is_pressed("a") or inp.is_pressed("start"):
            choice = self._current_item()
            if choice == "Difficulty":
                self._cycle_difficulty(1)
                return
            if hasattr(self.game, "audio"):
                self.game.audio.play_sfx("menu_select")
            if choice == "New Game":
                self.game.start_new_game(self.game.difficulty_mode)
            elif choice == "Continue":
                self.game.load_saved_game()
            elif choice == "Instructions":
                self.game.states.change("instructions")
            elif choice == "Quit":
                self.game.running = False

    def render(self, screen):
        vw, vh = self._viewport_size(screen)
        compact = self._is_compact_view(screen)
        self._set_viewport(vw, vh)
        self._ensure_fonts(compact)
        t = self.timer

        # ── Deep background ─────────────────────────────────────────────────
        screen.fill((5, 4, 12))

        # Stars (varying flicker speed)
        for sx, sy, brightness, flicker_speed in self._stars:
            flicker = 0.65 + 0.35 * math.sin(t * flicker_speed + sx * 0.07)
            c       = int(brightness * flicker * 190)
            r       = 1 if brightness > 0.6 else 0
            pygame.draw.circle(screen, (c, c, c + 18), (sx, sy), r)

        # Atmospheric orbs (additive blend)
        for orb in self._orbs:
            orb.render(screen, t)

        # Horizon mist
        mist_h = vh // 3
        mist   = pygame.Surface((vw, mist_h), pygame.SRCALPHA)
        for i in range(mist_h):
            alpha = int(28 * (1 - i / mist_h) * (0.7 + 0.3 * math.sin(t * 0.5)))
            pygame.draw.line(mist, (20, 45, 30, alpha),
                             (0, mist_h - 1 - i), (vw, mist_h - 1 - i))
        screen.blit(mist, (0, vh - mist_h))

        # ── Logo ────────────────────────────────────────────────────────────
        logo_y  = 24 if compact else 95
        pulse   = 0.82 + 0.18 * math.sin(t * 1.2)
        glow_a  = int(22 + 14 * math.sin(t * 1.8))
        center_x = vw // 2

        # Background glow
        glow_w = min(440, max(180, vw - 20))
        glow_h = 54 if compact else 90
        glow = pygame.Surface((glow_w, glow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (55, 155, 98, glow_a), (0, 0, glow_w, glow_h))
        screen.blit(glow, (center_x - glow_w // 2, logo_y - (4 if compact else 10)),
                    special_flags=pygame.BLEND_RGBA_ADD)

        # Multi-layer title text
        # 1. Deep shadow
        sh1 = self._title_font.render("MYTHICAL", True, (8, 22, 14))
        screen.blit(sh1, (center_x - sh1.get_width() // 2 + 4, logo_y + 4))
        # 2. Soft shadow
        sh2 = self._title_font.render("MYTHICAL", True, (15, 55, 35))
        screen.blit(sh2, (center_x - sh2.get_width() // 2 + 2, logo_y + 2))
        # 3. Main text
        accent_pulse = (
            int(COLOR_ACCENT[0] * pulse),
            int(COLOR_ACCENT[1] * pulse),
            int(COLOR_ACCENT[2] * pulse),
        )
        main_s = self._title_font.render("MYTHICAL", True, accent_pulse)
        screen.blit(main_s, (center_x - main_s.get_width() // 2, logo_y))
        # 4. Thin highlight
        hl_alpha = int(55 + 35 * math.sin(t * 1.4))
        hl_col   = (min(255, COLOR_ACCENT[0] + 80), min(255, COLOR_ACCENT[1] + 80),
                    min(255, COLOR_ACCENT[2] + 40))
        hl = self._title_font.render("MYTHICAL", True, hl_col)
        hl.set_alpha(hl_alpha)
        screen.blit(hl, (center_x - hl.get_width() // 2, logo_y))

        # Subtitle
        sub = self._small_font.render("A Retro Fantasy Adventure", True, (88, 112, 98))
        sub_y = logo_y + (42 if compact else 70)
        screen.blit(sub, (center_x - sub.get_width() // 2, sub_y))

        # Decorative rule under subtitle
        rule_y  = sub_y + (12 if compact else 18)
        rule_cx = center_x
        rule_w  = 120 if compact else 180
        pygame.draw.line(screen, (35, 55, 42), (rule_cx - rule_w // 2, rule_y),
                         (rule_cx + rule_w // 2, rule_y))
        pygame.draw.circle(screen, (55, 88, 65), (rule_cx, rule_y), 3)

        # ── Menu ─────────────────────────────────────────────────────────────
        menu_y = rule_y + (12 if compact else 34)
        row_gap = 24 if compact else 38
        for i, item in enumerate(self.menu_items):
            selected = (i == self.cursor)
            label    = item
            if item == "Difficulty":
                label = f"Difficulty: {self.game.difficulty_label}"

            if selected:
                # Selection glow
                sp   = 0.6 + 0.4 * math.sin(t * 2.8)
                sc   = (int(55 * sp + 38), int(78 * sp + 55), int(62 * sp + 44))
                sel_s = self._font.render(label, True, COLOR_ACCENT)
                # Marker
                marker = self._font.render("> ", True,
                                           (int(COLOR_ACCENT[0] * sp),
                                            int(COLOR_ACCENT[1] * sp),
                                            int(COLOR_ACCENT[2] * sp)))
                mx_offset = center_x - sel_s.get_width() // 2 - marker.get_width()
                screen.blit(marker, (mx_offset, menu_y + i * row_gap))
                screen.blit(sel_s,  (center_x - sel_s.get_width() // 2, menu_y + i * row_gap))
            else:
                ns = self._font.render(label, True, _DIM)
                screen.blit(ns, (center_x - ns.get_width() // 2, menu_y + i * row_gap))

        # ── Footer ────────────────────────────────────────────────────────────
        footer_text = (
            "Arrows/Z Select  Q/E Difficulty"
            if compact else
            "Arrow keys / Z=Select   Q/E=Change Difficulty"
        )
        foot = self._tiny_font.render(footer_text, True, (48, 50, 60))
        screen.blit(foot, (center_x - foot.get_width() // 2, vh - (14 if compact else 22)))
