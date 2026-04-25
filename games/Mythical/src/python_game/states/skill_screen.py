"""
Skill tree screen — opened with K.
Shows three trees (Warrior / Rogue / Mage) as a tier layout with prerequisite arrows.
Unspent SP counter top-right. Select node with A, confirm with A again.
"""

import pygame
from settings import COLOR_WHITE, COLOR_ACCENT
from states.state_machine import State
from skill_tree import SKILL_TREES, get_skill
from ui.fonts import get_font

# ── Layout constants ──────────────────────────────────────────────────────────
TREE_COLS = 3  # warrior | rogue | mage side-by-side
NODE_W = 72
NODE_H = 40
NODE_PAD_X = 20  # horizontal gap between nodes in the same tier
NODE_PAD_Y = 18  # vertical gap between tiers
TREES_ORDER = ["warrior", "rogue", "mage"]


def _tree_color(tree_id):
    """Pull color from the live SKILL_TREES data."""
    return SKILL_TREES.get(tree_id, {}).get("color", (160, 160, 160))


def _tier_x_start(tree_idx: int, panel_x: int, panel_w: int) -> int:
    col_w = panel_w // TREE_COLS
    return panel_x + tree_idx * col_w + col_w // 2 - NODE_W // 2


def _node_rect(tree_idx, tier, panel_x, panel_y, panel_w):
    x = _tier_x_start(tree_idx, panel_x, panel_w)
    y = panel_y + 50 + tier * (NODE_H + NODE_PAD_Y)
    return pygame.Rect(x, y, NODE_W, NODE_H)


class SkillScreenState(State):
    def __init__(self, game):
        super().__init__(game)
        self.font = None
        self.small_font = None
        self.tiny_font = None
        # Flat list of (tree_id, skill_id) for cursor navigation
        self._nodes: list[tuple[str, str]] = []
        self._cursor = 0
        # Layout lookup: (tree_id, skill_id) → Rect
        self._rects: dict[tuple, pygame.Rect] = {}
        self._confirm = False  # press A twice to spend point

    def _iter_tree_skills(self, tree_id: str):
        tree = SKILL_TREES.get(tree_id, {})
        return list(tree.get("skills", []))

    def _ensure_fonts(self):
        if self.font is None:
            self.font = get_font(13)
            self.small_font = get_font(11)
            self.tiny_font = get_font(10)

    def _build_nodes(self):
        """Build flat nav list in stable tree/tier order."""
        self._nodes = []
        for tree_id in TREES_ORDER:
            tiers: dict[int, list[dict]] = {}
            for sdef in self._iter_tree_skills(tree_id):
                tiers.setdefault(sdef.get("tier", 0), []).append(sdef)
            for tier_num in sorted(tiers):
                tier_skills = sorted(
                    tiers[tier_num], key=lambda s: s.get("pos", (0, 0))
                )
                for sdef in tier_skills:
                    self._nodes.append((tree_id, sdef["id"]))

    def _build_layout(self, panel_x, panel_y, panel_w, compact=False):
        """Compute rects for every node for the current panel size."""
        self._rects = {}

        if not self._nodes:
            self._build_nodes()

        node_w = 48 if compact else NODE_W
        node_h = 22 if compact else NODE_H
        node_pad_y = 10 if compact else NODE_PAD_Y
        node_pad_x = 10 if compact else NODE_PAD_X

        for ti, tree_id in enumerate(TREES_ORDER):
            tree = SKILL_TREES.get(tree_id, {})
            skills = self._iter_tree_skills(tree_id)
            # Group by tier
            tiers: dict[int, list[dict]] = {}
            for sdef in skills:
                t = sdef.get("tier", 0)
                tiers.setdefault(t, []).append(sdef)

            for tier_idx, tier_num in enumerate(sorted(tiers)):
                tier_skills = sorted(
                    tiers[tier_num], key=lambda s: s.get("pos", (0, 0))
                )
                total_w = (
                    len(tier_skills) * node_w
                    + max(0, len(tier_skills) - 1) * node_pad_x
                )
                center_x = _tier_x_start(ti, panel_x, panel_w) + NODE_W // 2
                start_x = center_x - total_w // 2
                for j, sdef in enumerate(tier_skills):
                    sid = sdef["id"]
                    x = start_x + j * (node_w + node_pad_x)
                    y = (
                        panel_y
                        + (44 if compact else 52)
                        + tier_idx * (node_h + node_pad_y)
                    )
                    r = pygame.Rect(x, y, NODE_W, NODE_H)
                    key = (tree_id, sid)
                    self._rects[key] = pygame.Rect(x, y, node_w, node_h)

    # ── State interface ───────────────────────────────────────────────────────

    def enter(self):
        self._build_nodes()
        self._rects = {}
        self._cursor = 0
        self._confirm = False

    def update(self, dt):
        inp = self.game.input

        if inp.is_pressed("skill") or inp.is_pressed("b") or inp.is_pressed("start"):
            self._confirm = False
            self.game.states.change("gameplay")
            return

        n = len(self._nodes)
        if n == 0:
            return

        if inp.is_pressed("up"):
            self._cursor = (self._cursor - 1) % n
            self._confirm = False
        elif inp.is_pressed("down"):
            self._cursor = (self._cursor + 1) % n
            self._confirm = False
        elif inp.is_pressed("left"):
            self._cursor = (self._cursor - 1) % n
            self._confirm = False
        elif inp.is_pressed("right"):
            self._cursor = (self._cursor + 1) % n
            self._confirm = False

        if inp.is_pressed("a"):
            if not self._confirm:
                self._confirm = True  # first press: prime
            else:
                self._try_upgrade()
                self._confirm = False

    def _try_upgrade(self):
        if not self._nodes:
            return
        prog = getattr(self.game, "progression", None)
        if prog is None:
            return
        tree_id, skill_id = self._nodes[self._cursor]
        success = prog.spend_skill_point(tree_id, skill_id)
        if success:
            if hasattr(self.game, "audio"):
                self.game.audio.play_sfx("menu_select")
        else:
            if hasattr(self.game, "audio"):
                self.game.audio.play_sfx("menu_move")

    # ── Render ────────────────────────────────────────────────────────────────

    def render(self, screen):
        self._ensure_fonts()
        vw, vh = self._viewport_size(screen)
        compact = self._is_compact_view(screen)

        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 215))
        screen.blit(overlay, (0, 0))

        px, py = (6, 6) if compact else (10, 10)
        pw, ph = vw - px * 2, vh - py * 2

        pygame.draw.rect(screen, (10, 10, 20), (px, py, pw, ph), border_radius=6)
        pygame.draw.rect(screen, (60, 60, 80), (px, py, pw, ph), 1, border_radius=6)

        if compact:
            self._render_compact(screen, px, py, pw, ph)
            return

        self._build_layout(px, py, pw, compact=False)

        # Title + SP
        title_s = self.font.render("SKILL TREES", True, COLOR_ACCENT)
        screen.blit(title_s, (px + pw // 2 - title_s.get_width() // 2, py + 8))

        prog = getattr(self.game, "progression", None)
        sp = prog.skill_points if prog else 0
        lv = prog.level if prog else 1
        sp_s = self.small_font.render(
            f"LV {lv}  SP: {sp}", True, (255, 220, 60) if sp > 0 else (120, 120, 130)
        )
        screen.blit(sp_s, (px + pw - sp_s.get_width() - 12, py + 8))

        # Tree column headers
        for ti, tree_id in enumerate(TREES_ORDER):
            hx = _tier_x_start(ti, px, pw) + NODE_W // 2
            hy = py + 28
            tree = SKILL_TREES.get(tree_id, {})
            hs = self.small_font.render(
                tree.get("name", tree_id).upper(), True, _tree_color(tree_id)
            )
            screen.blit(hs, (hx - hs.get_width() // 2, hy))

        # Draw prerequisite arrows
        self._draw_arrows(screen, prog)

        # Draw nodes
        for i, (tree_id, skill_id) in enumerate(self._nodes):
            rect = self._rects.get((tree_id, skill_id))
            if rect is None:
                continue
            sdef = get_skill(tree_id, skill_id)
            selected = i == self._cursor
            rank = prog.get_skill_rank(tree_id, skill_id) if prog else 0
            max_r = sdef.get("max_rank", 1)
            self._draw_node(screen, rect, sdef, tree_id, rank, max_r, selected)

        # Detail panel for selected node
        if self._nodes:
            self._draw_detail(screen, px, py, pw, ph, prog)

        # Footer
        footer = "K/B=Close  ↑↓←→=Navigate  A=Select  A+A=Upgrade"
        if self._confirm:
            footer = "Press A again to confirm upgrade"
        fs = self.tiny_font.render(
            footer, True, (200, 200, 80) if self._confirm else (70, 70, 90)
        )
        screen.blit(fs, (px + pw // 2 - fs.get_width() // 2, py + ph - 16))

    def _render_compact(self, screen, px, py, pw, ph):
        if not self._nodes:
            self._build_nodes()

        prog = getattr(self.game, "progression", None)
        sp = prog.skill_points if prog else 0
        lv = prog.level if prog else 1

        title_s = self.font.render("SKILLS", True, COLOR_ACCENT)
        screen.blit(title_s, (px + 8, py + 8))

        sp_s = self.tiny_font.render(
            f"LV {lv}  SP:{sp}", True, (255, 220, 60) if sp > 0 else (120, 120, 130)
        )
        screen.blit(sp_s, (px + pw - sp_s.get_width() - 8, py + 10))

        list_x = px + 8
        list_y = py + 28
        detail_h = 34
        list_h = ph - 56 - detail_h
        row_h = 18
        visible = max(1, list_h // row_h)
        scroll = max(
            0, min(self._cursor - visible // 2, max(0, len(self._nodes) - visible))
        )

        for i, (tree_id, skill_id) in enumerate(self._nodes[scroll : scroll + visible]):
            real_i = scroll + i
            ry = list_y + i * row_h
            selected = real_i == self._cursor
            sdef = get_skill(tree_id, skill_id) or {}
            rank = prog.get_skill_rank(tree_id, skill_id) if prog else 0
            max_r = sdef.get("max_rank", 1)
            color = _tree_color(tree_id)

            if selected:
                pygame.draw.rect(
                    screen,
                    (28, 30, 48),
                    (list_x - 3, ry - 1, pw - 16, row_h - 1),
                    border_radius=3,
                )
                pygame.draw.rect(
                    screen,
                    color,
                    (list_x - 3, ry - 1, pw - 16, row_h - 1),
                    1,
                    border_radius=3,
                )

            tag = self.tiny_font.render(tree_id[:3].upper(), True, color)
            screen.blit(tag, (list_x, ry + 4))

            name = sdef.get("name", "?") or "?"
            while len(name) > 3 and self.small_font.size(name)[0] > pw - 92:
                name = name[:-1]
            if name != sdef.get("name", "?"):
                name += ".."
            ns = self.small_font.render(
                name, True, COLOR_WHITE if selected else (180, 180, 190)
            )
            screen.blit(ns, (list_x + 28, ry + 3))

            rs = self.tiny_font.render(
                f"{rank}/{max_r}", True, color if rank else (90, 90, 100)
            )
            screen.blit(rs, (px + pw - rs.get_width() - 10, ry + 4))

        # Detail strip
        dpx = px + 6
        dpy = py + ph - detail_h - 8
        dpw = pw - 12
        pygame.draw.rect(
            screen, (8, 10, 22), (dpx, dpy, dpw, detail_h), border_radius=4
        )
        pygame.draw.rect(
            screen, (60, 60, 80), (dpx, dpy, dpw, detail_h), 1, border_radius=4
        )

        if self._nodes:
            tree_id, skill_id = self._nodes[self._cursor]
            sdef = get_skill(tree_id, skill_id) or {}
            rank = prog.get_skill_rank(tree_id, skill_id) if prog else 0
            max_r = sdef.get("max_rank", 1)
            title = self.small_font.render(
                f"{sdef.get('name', '?')} [{rank}/{max_r}]",
                True,
                _tree_color(tree_id),
            )
            screen.blit(title, (dpx + 6, dpy + 4))
            desc = (sdef.get("desc", "") or "")[:34]
            ds = self.tiny_font.render(desc, True, (170, 170, 180))
            screen.blit(ds, (dpx + 6, dpy + 18))

        footer = "A Select" if not self._confirm else "A again to upgrade"
        fs = self.tiny_font.render(
            footer, True, (200, 200, 80) if self._confirm else (70, 70, 90)
        )
        screen.blit(fs, (px + pw // 2 - fs.get_width() // 2, py + ph - 12))

    def _draw_arrows(self, screen, prog):
        for ti, tree_id in enumerate(TREES_ORDER):
            skills = self._iter_tree_skills(tree_id)
            for sdef in skills:
                sid = sdef["id"]
                prereqs = sdef.get("requires") or []
                if isinstance(prereqs, str):
                    prereqs = [prereqs.split(".", 1)[-1]]
                for pre_id in prereqs:
                    src = self._rects.get((tree_id, pre_id))
                    dst = self._rects.get((tree_id, sid))
                    if src and dst:
                        rank_met = (
                            (prog.get_skill_rank(tree_id, pre_id) > 0)
                            if prog
                            else False
                        )
                        color = (80, 160, 80) if rank_met else (60, 60, 70)
                        sx = src.centerx
                        sy = src.bottom
                        ex = dst.centerx
                        ey = dst.top
                        pygame.draw.line(screen, color, (sx, sy), (ex, ey), 1)
                        # Arrow head
                        pygame.draw.polygon(
                            screen,
                            color,
                            [
                                (ex, ey),
                                (ex - 4, ey - 6),
                                (ex + 4, ey - 6),
                            ],
                        )

    def _draw_node(self, screen, rect, sdef, tree_id, rank, max_rank, selected):
        tc = _tree_color(tree_id)
        maxed = rank >= max_rank
        learned = rank > 0

        if maxed:
            bg = (int(tc[0] * 0.4), int(tc[1] * 0.4), int(tc[2] * 0.4))
            border = tc
        elif learned:
            bg = (int(tc[0] * 0.2), int(tc[1] * 0.2), int(tc[2] * 0.2))
            border = tc
        else:
            bg = (18, 18, 30)
            border = (60, 60, 78)

        if selected:
            border = (255, 255, 200)
            # Outer glow
            glow = pygame.Surface((rect.w + 6, rect.h + 6), pygame.SRCALPHA)
            pygame.draw.rect(
                glow, (*border, 60), (0, 0, rect.w + 6, rect.h + 6), border_radius=5
            )
            screen.blit(glow, (rect.x - 3, rect.y - 3))

        pygame.draw.rect(screen, bg, rect, border_radius=4)
        pygame.draw.rect(screen, border, rect, 1, border_radius=4)

        # Skill name (truncated)
        name = sdef.get("name", "?")[:9]
        ns = self.tiny_font.render(name, True, (200, 200, 210) if not maxed else tc)
        screen.blit(ns, (rect.x + rect.w // 2 - ns.get_width() // 2, rect.y + 5))

        # Rank pips
        pip_w = 8
        pip_gap = 2
        total_pip_w = max_rank * (pip_w + pip_gap) - pip_gap
        pip_x = rect.x + rect.w // 2 - total_pip_w // 2
        pip_y = rect.bottom - 10
        for r in range(max_rank):
            filled = r < rank
            c = tc if filled else (40, 40, 55)
            pygame.draw.rect(
                screen, c, (pip_x + r * (pip_w + pip_gap), pip_y, pip_w, 5)
            )

    def _draw_detail(self, screen, px, py, pw, ph, prog):
        if not self._nodes:
            return
        tree_id, skill_id = self._nodes[self._cursor]
        sdef = get_skill(tree_id, skill_id)
        rank = prog.get_skill_rank(tree_id, skill_id) if prog else 0
        max_r = sdef.get("max_rank", 1)
        tc = _tree_color(tree_id)

        dpx = px + 12
        dpy = py + ph - 82
        dpw = pw - 24

        bg = pygame.Surface((dpw, 72), pygame.SRCALPHA)
        bg.fill((6, 6, 18, 220))
        screen.blit(bg, (dpx, dpy))
        pygame.draw.rect(screen, tc, (dpx, dpy, dpw, 72), 1)

        # Name + rank
        name_s = self.font.render(
            f"{sdef.get('name', '?')}  [{rank}/{max_r}]", True, tc
        )
        screen.blit(name_s, (dpx + 8, dpy + 6))

        # Description
        desc = sdef.get("desc", "")
        ds = self.small_font.render(desc[:60], True, (180, 180, 190))
        screen.blit(ds, (dpx + 8, dpy + 24))

        # Stats per rank
        stats = sdef.get("stats_per_rank", {})
        stat_parts = [f"+{v * (rank + 1)} {k}" for k, v in stats.items()]
        if stat_parts:
            ss = self.tiny_font.render("  ".join(stat_parts), True, (140, 220, 140))
            screen.blit(ss, (dpx + 8, dpy + 42))

        # Cost / prereqs — every skill costs 1 SP
        prereqs = sdef.get("requires", [])
        if isinstance(prereqs, str):
            prereqs = [prereqs.split(".", 1)[-1]]
        cost = 1  # All skills cost 1 SP per rank
        if prereqs:
            pre_names = []
            for p in prereqs:
                pre_skill = get_skill(tree_id, p)
                pre_names.append(pre_skill.get("name", p) if pre_skill else p)
            pre_s = self.tiny_font.render(
                f"Requires: {', '.join(pre_names)}  Cost: {cost} SP",
                True,
                (160, 130, 80),
            )
        else:
            pre_s = self.tiny_font.render(f"Cost: {cost} SP", True, (160, 130, 80))
        screen.blit(pre_s, (dpx + 8, dpy + 56))
