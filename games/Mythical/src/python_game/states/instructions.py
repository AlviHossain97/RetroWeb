"""Instructions / How to Play screen — premium retro-fantasy visual design."""
import math
import pygame
from settings import COLOR_ACCENT
from states.state_machine import State
from ui.fonts import get_font

# Palette
_SECTION_COLOR  = COLOR_ACCENT
_KEY_COLOR      = (230, 220, 148)
_DESC_COLOR     = (185, 185, 200)
_DIM            = (70,  72,  88)
_PANEL_BG       = (7,   9,  18, 245)
_PANEL_BORDER   = (38, 42, 58)
_DIVIDER        = (28, 32, 44)

_SECTIONS = [
    ("MOVEMENT & ACTIONS", [
        ("Arrow Keys / WASD",   "Move the character"),
        ("Z / Enter",           "Interact  ·  Talk  ·  Use consumable"),
        ("X / Backspace",       "Attack with equipped sword"),
        ("Shift",               "Dash  (requires Shadow Cloak)"),
        ("ESC",                 "Pause menu  ·  Save"),
        ("TAB",                 "Open inventory"),
        ("1 – 8",               "Select hotbar slot"),
    ]),
    ("COMBAT", [
        "Swing your sword in the direction you face.",
        "Enemies flash white when hit and get knocked back.",
        "You blink when hurt — invincible briefly.",
        "Hearts (top-left) = your current health.",
        "Flank enemies from behind for bonus damage!",
    ]),
    ("FOOD & CONSUMABLES", [
        "Select a consumable in your hotbar (1–8), then press Z.",
        "Raw Meat:      eat 2 pieces → ½ heart  (4 total = 1 heart).",
        "Cooked Meat:   eat 1 piece  → ½ heart  (2 total = 1 heart).",
        "Health Potion: drink 1      → 1 full heart.",
        "Cook raw meat at a campfire: 2 raw → 1 cooked.",
    ]),
    ("QUEST", [
        "Talk to Elder Rowan to begin your quest.",
        "Your current objective is shown below your hearts.",
        "Follow the objective strip — it updates automatically.",
        "Defeat the Dark Golem in the dungeon to win!",
    ]),
    ("TIPS", [
        "Open chests by facing them and pressing Z.",
        "Walk over glowing ground items to pick them up.",
        "Kill animals for Raw Meat to restore health.",
        "Get the Forest Key before heading east.",
        "Save anytime from the Pause menu (ESC).",
    ]),
]


class InstructionsState(State):
    def __init__(self, game):
        super().__init__(game)
        self.scroll     = 0
        self._timer     = 0.0
        self._content_h = 0
        self._fonts_ok  = False
        self._head_font = None
        self._body_font = None
        self._key_font  = None
        self._tiny_font = None
        self._title_font = None

    def _ensure_fonts(self):
        if not self._fonts_ok:
            self._title_font = get_font(28, bold=True)
            self._head_font  = get_font(16, bold=True)
            self._body_font  = get_font(14)
            self._key_font   = get_font(13, bold=True)
            self._tiny_font  = get_font(11)
            self._fonts_ok   = True

    def enter(self):
        self.scroll  = 0
        self._timer  = 0.0

    def update(self, dt):
        self._timer += dt
        inp = self.game.input
        if inp.is_pressed("b") or inp.is_pressed("start") or inp.is_pressed("a"):
            self.game.states.change("title")
            return
        _, vh = self._viewport_size()
        if inp.is_held("down"):
            self.scroll += int(200 * dt)
        if inp.is_held("up"):
            self.scroll = max(0, self.scroll - int(200 * dt))
        max_scroll = max(0, self._content_h - vh + 60)
        self.scroll = max(0, min(self.scroll, max_scroll))

    def render(self, screen):
        self._ensure_fonts()
        t = self._timer
        vw, vh = self._viewport_size(screen)
        compact = self._is_compact_view(screen)

        # ── Dark background ────────────────────────────────────────────
        screen.fill((5, 4, 12))

        # Subtle star field
        import random, math as _math
        rng = random.Random(42)
        for _ in range(60):
            sx = rng.randint(0, vw)
            sy = rng.randint(0, vh)
            br = rng.uniform(0.3, 0.8)
            flicker = 0.7 + 0.3 * _math.sin(t * rng.uniform(0.5, 2.0) + sx * 0.1)
            c = int(br * flicker * 160)
            pygame.draw.circle(screen, (c, c, c + 15), (sx, sy), 0)

        # ── Panel ──────────────────────────────────────────────────────
        pw = min(680, vw - (24 if compact else 40))
        px = vw // 2 - pw // 2

        # Title bar (fixed, not scrolled)
        title_h = 44 if compact else 52
        title_surf = pygame.Surface((pw, title_h), pygame.SRCALPHA)
        title_surf.fill((7, 9, 18, 252))
        screen.blit(title_surf, (px, 8))
        pygame.draw.rect(screen, _PANEL_BORDER, (px, 8, pw, title_h), 1, border_radius=4)

        # Title text
        pulse = 0.85 + 0.15 * math.sin(t * 1.4)
        title_col = (
            int(COLOR_ACCENT[0] * pulse),
            int(COLOR_ACCENT[1] * pulse),
            int(COLOR_ACCENT[2] * pulse),
        )
        ts = self._title_font.render("HOW  TO  PLAY", True, title_col)
        screen.blit(ts, (vw // 2 - ts.get_width() // 2, 18 if compact else 18))

        # Rule under title
        pygame.draw.line(screen, _DIVIDER,
                         (px + 16, 8 + title_h - 1), (px + pw - 16, 8 + title_h - 1))

        # ── Scrollable content area ────────────────────────────────────
        content_top = 8 + title_h + 6
        clip_h      = vh - content_top - 32
        clip_rect   = pygame.Rect(px, content_top, pw, clip_h)

        # Draw content onto an offscreen surface, then blit clipped
        # Estimate total height first pass
        y        = 0
        line_gap = 22
        sec_gap  = 14

        rows = []   # (y, type, data)
        for sec_name, entries in _SECTIONS:
            rows.append((y, "section", sec_name))
            y += 28
            if entries and isinstance(entries[0], tuple):
                for key, action in entries:
                    rows.append((y, "kv", (key, action)))
                    y += 36 if compact else line_gap
            else:
                for line in entries:
                    rows.append((y, "line", line))
                    y += line_gap
            y += sec_gap

        self._content_h = y

        # Build a surface tall enough
        content_surf = pygame.Surface((pw, max(y + 20, 10)), pygame.SRCALPHA)
        content_surf.fill((0, 0, 0, 0))

        for row_y, kind, data in rows:
            if kind == "section":
                # Section header with rule
                hs = self._head_font.render(data, True, _SECTION_COLOR)
                content_surf.blit(hs, (16, row_y + 2))
                rule_y = row_y + 22
                pygame.draw.line(content_surf, _DIVIDER,
                                 (16, rule_y), (pw - 16, rule_y))
                # Accent dot at start
                pygame.draw.circle(content_surf, COLOR_ACCENT, (16, rule_y), 2)

            elif kind == "kv":
                key, action = data
                # Key badge
                ks = self._key_font.render(key, True, _KEY_COLOR)
                kbg = pygame.Surface((ks.get_width() + 8, ks.get_height() + 2), pygame.SRCALPHA)
                kbg.fill((22, 24, 40, 180))
                content_surf.blit(kbg, (28, row_y - 1))
                pygame.draw.rect(content_surf, (48, 52, 72),
                                 (28, row_y - 1, ks.get_width() + 8, ks.get_height() + 2), 1)
                content_surf.blit(ks, (32, row_y + 1))
                ds = self._body_font.render(action, True, _DESC_COLOR)
                if compact:
                    content_surf.blit(ds, (36, row_y + 16))
                else:
                    # Separator
                    sep_x = min(220, pw // 2)
                    pygame.draw.line(content_surf, (35, 38, 52), (sep_x, row_y + 8), (sep_x, row_y + 16))
                    # Action
                    content_surf.blit(ds, (sep_x + 12, row_y + 2))

            elif kind == "line":
                # Bullet line
                pygame.draw.circle(content_surf, _DIM, (34, row_y + 8), 2)
                ls = self._body_font.render(data, True, _DESC_COLOR)
                content_surf.blit(ls, (42, row_y + 1))

        # Blit scrolled content
        src_rect = pygame.Rect(0, self.scroll, pw, clip_h)
        screen.blit(content_surf, (px, content_top), src_rect)

        # Clip mask — fade edges to black at top/bottom of clip area
        fade_h = 18
        for i in range(fade_h):
            a = int(255 * (1 - i / fade_h))
            pygame.draw.rect(screen, (5, 4, 12),
                             (px, content_top + i, pw, 1))
        fade_surf = pygame.Surface((pw, fade_h), pygame.SRCALPHA)
        for i in range(fade_h):
            a = int(200 * (i / fade_h))
            pygame.draw.rect(fade_surf, (5, 4, 12, a), (0, i, pw, 1))
        screen.blit(fade_surf, (px, content_top + clip_h - fade_h))

        # Panel border
        pygame.draw.rect(screen, _PANEL_BORDER, (px, content_top, pw, clip_h), 1)

        # ── Scroll indicator ───────────────────────────────────────────
        max_scroll = max(1, self._content_h - clip_h)
        if max_scroll > 0:
            track_h = clip_h - 8
            track_x = px + pw - 5 if compact else px + pw + 4
            track_y = content_top + 4
            pygame.draw.rect(screen, (22, 24, 38), (track_x, track_y, 3, track_h))
            thumb_h = max(18, int(track_h * clip_h / (self._content_h + 1)))
            thumb_y = track_y + int((track_h - thumb_h) * self.scroll / max_scroll)
            pygame.draw.rect(screen, _SECTION_COLOR, (track_x, thumb_y, 3, thumb_h), border_radius=1)

        # ── Footer ─────────────────────────────────────────────────────
        foot_bg = pygame.Surface((vw, 24), pygame.SRCALPHA)
        foot_bg.fill((0, 0, 0, 180))
        screen.blit(foot_bg, (0, vh - 24))
        footer_text = (
            "Up/Down Scroll   Z/B Return"
            if compact else
            "Up/Down = Scroll     Z / ESC / B = Return to Title"
        )
        foot = self._tiny_font.render(footer_text, True, (52, 55, 68))
        screen.blit(foot, (vw // 2 - foot.get_width() // 2, vh - 17))
