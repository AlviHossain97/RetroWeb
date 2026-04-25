"""
Tilemap — loads and renders a tile-based map from a simple dict format.
Supports multiple layers (ground, decoration, collision).

Enhanced with richer tile rendering — textured colors, outlines, and details.
On GBA this maps directly to tilemap arrays in ROM + hardware BG layers.
"""

import pygame
import random
from settings import TILE_SIZE

_TILE_BAKE_SEED = 42

# ── Ground tile definitions ──────────────────────────────────────────
# ID: (base_color, detail_function_name_or_None)
TILE_DEFS = {
    0:  {"name": "grass",       "base": (52, 110, 62),  "detail": "grass"},
    1:  {"name": "dirt_path",   "base": (145, 115, 80), "detail": "dirt"},
    2:  {"name": "stone_floor", "base": (115, 115, 130),"detail": "stone"},
    3:  {"name": "grass_dark",  "base": (40, 90, 48),   "detail": "grass"},
    4:  {"name": "water",       "base": (40, 80, 170),  "detail": "water"},
    5:  {"name": "wood_floor",  "base": (130, 95, 60),  "detail": "wood"},
    6:  {"name": "wall_stone",  "base": (75, 75, 85),   "detail": "brick"},
    7:  {"name": "roof",        "base": (140, 55, 45),  "detail": "roof"},
    8:  {"name": "door",        "base": (120, 80, 40),  "detail": "door"},
    9:  {"name": "hedge",       "base": (30, 70, 35),   "detail": "hedge"},
    10: {"name": "sand",        "base": (200, 185, 140),"detail": "dirt"},
    11: {"name": "bridge",      "base": (110, 80, 45),  "detail": "bridge"},
    12: {"name": "fence_h",     "base": (140, 110, 65), "detail": "fence_h"},
    13: {"name": "fence_v",     "base": (140, 110, 65), "detail": "fence_v"},
    14: {"name": "cobble",      "base": (130, 125, 120),"detail": "cobble"},
    15: {"name": "grass_flower","base": (52, 110, 62),  "detail": "flowers"},
    16: {"name": "water_deep",  "base": (25, 55, 140),  "detail": "water"},
    17: {"name": "wall_wood",   "base": (100, 70, 40),  "detail": "brick"},
}

# ── Decoration tile definitions ──────────────────────────────────────
DECOR_DEFS = {
    0:  None,
    1:  {"name": "tree_oak",    "color": (35, 100, 40), "trunk": (90, 60, 30)},
    2:  {"name": "tree_pine",   "color": (25, 80, 35),  "trunk": (80, 50, 25)},
    3:  {"name": "flowers_red", "petals": (200, 50, 50),"stem": (40, 90, 40)},
    4:  {"name": "rock",        "color": (130, 125, 120),"shade": (100, 95, 90)},
    5:  {"name": "sign",        "color": (160, 130, 80),"text": (60, 40, 20)},
    6:  {"name": "chest",       "color": (160, 120, 50),"lock": (200, 180, 60)},
    7:  {"name": "well",        "color": (100, 100, 110),"roof": (140, 55, 45)},
    8:  {"name": "barrel",      "color": (120, 85, 45), "band": (80, 80, 90)},
    9:  {"name": "crate",       "color": (140, 110, 65),"stripe": (100, 75, 40)},
    10: {"name": "flowers_blue","petals": (70, 100, 200),"stem": (40, 90, 40)},
    11: {"name": "lamp_post",   "color": (60, 60, 70),  "light": (255, 220, 120)},
    12: {"name": "stall",       "color": (140, 100, 55),"cloth": (180, 50, 50)},
    13: {"name": "bush",        "color": (35, 85, 40),  "berry": (180, 40, 40)},
    14: {"name": "grave",       "color": (120, 120, 130),"shade": (90, 90, 100)},
}


def _vary(color, amount=8):
    """Add slight random variation to a color for texture."""
    return tuple(max(0, min(255, c + random.randint(-amount, amount))) for c in color)


def _darken(color, amt=30):
    return tuple(max(0, c - amt) for c in color)


def _lighten(color, amt=30):
    return tuple(min(255, c + amt) for c in color)


class TileMap:
    def __init__(self, map_data: dict):
        self.width = map_data["width"]
        self.height = map_data["height"]
        self.ground = map_data["ground"]
        self.decor = map_data.get("decor")
        self.collision = map_data["collision"]
        self.spawns = map_data.get("spawns", {})

        self._ground_surf = pygame.Surface(
            (self.width * TILE_SIZE, self.height * TILE_SIZE)
        )
        self._decor_surf = pygame.Surface(
            (self.width * TILE_SIZE, self.height * TILE_SIZE), pygame.SRCALPHA
        )
        # Preserve gameplay RNG. Tile baking needs deterministic texture noise,
        # but it should not reset the global random stream used by combat/drops.
        rng_state = random.getstate()
        try:
            random.seed(_TILE_BAKE_SEED)
            self._bake()
        finally:
            random.setstate(rng_state)

    def _bake(self):
        T = TILE_SIZE
        for row in range(self.height):
            for col in range(self.width):
                x, y = col * T, row * T
                rect = pygame.Rect(x, y, T, T)
                tid = self.ground[row][col]
                tdef = TILE_DEFS.get(tid, TILE_DEFS[0])
                base = tdef["base"]
                detail = tdef.get("detail")

                # Fill base with richer variation
                var_amt = 10
                pygame.draw.rect(self._ground_surf, _vary(base, var_amt), rect)

                # ── Detail rendering ─────────────────────────────────────
                if detail == "grass":
                    # Multi-shade grass coverage with longer blades
                    shade1 = _vary(_darken(base, 8),  8)
                    shade2 = _vary(_lighten(base, 18), 10)
                    shade3 = _vary(_lighten(base, 10), 6)
                    # Background variation patches
                    for _ in range(5):
                        px2 = x + random.randint(0, T - 1)
                        py2 = y + random.randint(0, T - 1)
                        pygame.draw.circle(self._ground_surf, _vary(shade1, 5), (px2, py2), 2)
                    # Grass blades — varied angles
                    for _ in range(6):
                        gx = x + random.randint(3, T - 3)
                        gy = y + random.randint(4, T - 2)
                        gc = shade2 if random.random() > 0.4 else shade3
                        h  = random.randint(3, 6)
                        lean = random.randint(-1, 1)
                        pygame.draw.line(self._ground_surf, gc,
                                         (gx, gy), (gx + lean, gy - h), 1)
                    # Occasional small pebble or dark spot
                    if random.random() < 0.18:
                        px2 = x + random.randint(5, T - 5)
                        py2 = y + random.randint(5, T - 5)
                        pygame.draw.circle(self._ground_surf, _darken(base, 30), (px2, py2), 1)

                elif detail == "dirt":
                    # Richer dirt with pebbles and variation
                    for _ in range(4):
                        dx2 = x + random.randint(3, T - 3)
                        dy2 = y + random.randint(3, T - 3)
                        pygame.draw.circle(self._ground_surf,
                                           _vary(_darken(base, 15), 8),
                                           (dx2, dy2), random.randint(1, 2))
                    # Subtle crack marks
                    if random.random() < 0.25:
                        cx2 = x + random.randint(4, T - 8)
                        cy2 = y + random.randint(4, T - 8)
                        pygame.draw.line(self._ground_surf, _darken(base, 25),
                                         (cx2, cy2), (cx2 + random.randint(3, 6),
                                                       cy2 + random.randint(1, 4)), 1)

                elif detail == "stone":
                    # Beveled stone slab look
                    lc  = _darken(base, 20)
                    ltc = _lighten(base, 12)
                    # Cross seam
                    mx2 = x + T // 2
                    my2 = y + T // 2
                    pygame.draw.line(self._ground_surf, lc, (x, my2), (x + T, my2), 1)
                    pygame.draw.line(self._ground_surf, lc, (mx2, y), (mx2, y + T), 1)
                    # Bevel highlight on inner edges
                    pygame.draw.line(self._ground_surf, ltc, (x + 2, my2 - 1), (mx2 - 2, my2 - 1), 1)
                    pygame.draw.line(self._ground_surf, ltc, (mx2 + 2, my2 - 1), (x + T - 2, my2 - 1), 1)
                    # Corner polish
                    for cx2, cy2 in ((x + 3, y + 3), (x + T - 4, y + 3),
                                     (x + 3, y + T - 4), (x + T - 4, y + T - 4)):
                        pygame.draw.circle(self._ground_surf, _lighten(base, 8), (cx2, cy2), 1)

                elif detail == "water":
                    # Deep water with ripple bands and sparkle
                    # Layer 1 — dark deep band
                    deep = _darken(base, 18)
                    for wy in range(y + 2, y + T, 6):
                        pygame.draw.line(self._ground_surf, _vary(deep, 5),
                                         (x, wy), (x + T, wy), 1)
                    # Layer 2 — highlight ripple lines
                    wc = _lighten(base, 30)
                    w1 = y + (col * 4 + row * 9) % T
                    pygame.draw.line(self._ground_surf, wc,
                                     (x + 5, w1 % T + y),
                                     (x + T - 5, (w1 + 3) % T + y), 1)
                    w2 = y + (col * 7 + row * 5 + T // 3) % T
                    pygame.draw.line(self._ground_surf, _vary(wc, 12),
                                     (x + 3, w2 % T + y),
                                     (x + T // 2 - 2, (w2 + 2) % T + y), 1)
                    # Sparkle dots
                    if random.random() < 0.3:
                        sx2 = x + random.randint(4, T - 4)
                        sy2 = y + random.randint(4, T - 4)
                        pygame.draw.circle(self._ground_surf, (180, 210, 255), (sx2, sy2), 1)

                elif detail == "wood":
                    lc  = _darken(base, 18)
                    ltc = _lighten(base, 8)
                    # Planks
                    for wy in range(y + 5, y + T, 7):
                        pygame.draw.line(self._ground_surf, lc, (x + 1, wy), (x + T - 1, wy), 1)
                        pygame.draw.line(self._ground_surf, ltc, (x + 1, wy - 1), (x + T - 1, wy - 1), 1)
                    # Grain
                    for _ in range(2):
                        gx2 = x + random.randint(3, T - 3)
                        gy2 = y + random.randint(3, T - 8)
                        pygame.draw.line(self._ground_surf, _darken(base, 10),
                                         (gx2, gy2), (gx2 + random.randint(-1, 1), gy2 + 4), 1)

                elif detail == "brick":
                    lc  = _darken(base, 25)
                    ltc = _lighten(base, 10)
                    row_h = T // 3
                    # Mortar horizontal lines
                    for by2 in range(y + row_h, y + T, row_h):
                        pygame.draw.line(self._ground_surf, lc, (x, by2), (x + T, by2), 1)
                    # Staggered vertical mortar
                    off = T // 2 if (row % 2 == 0) else 0
                    bx2 = x + (T // 2 + off) % T
                    pygame.draw.line(self._ground_surf, lc, (bx2, y), (bx2, y + T), 1)
                    # Brick face bevel highlight
                    for br in range(3):
                        ry = y + br * row_h + 2
                        pygame.draw.line(self._ground_surf, ltc, (x + 2, ry), (x + T - 2, ry), 1)

                elif detail == "roof":
                    # Layered shingles with depth
                    lc  = _darken(base, 22)
                    ltc = _lighten(base, 8)
                    for i in range(0, T * 2, 7):
                        pygame.draw.line(self._ground_surf, lc,
                                         (x + i, y), (x + i - T, y + T), 1)
                        pygame.draw.line(self._ground_surf, ltc,
                                         (x + i + 1, y), (x + i - T + 1, y + T), 1)
                    # Row breaks
                    for ry in range(y + T // 4, y + T, T // 4):
                        pygame.draw.line(self._ground_surf, lc, (x, ry), (x + T, ry), 1)

                elif detail == "door":
                    # Paneled door with arch top and handle
                    dc  = _darken(base, 35)
                    ltc = _lighten(base, 15)
                    # Frame
                    pygame.draw.rect(self._ground_surf, dc, (x + 2, y + 1, T - 4, T - 1), 2)
                    # Door panels
                    pygame.draw.rect(self._ground_surf, _darken(base, 18),
                                     (x + 5, y + 4, T - 10, T // 2 - 2))
                    pygame.draw.rect(self._ground_surf, _darken(base, 18),
                                     (x + 5, y + T // 2 + 2, T - 10, T // 2 - 6))
                    # Bevel highlight on panels
                    pygame.draw.line(self._ground_surf, ltc, (x + 5, y + 4), (x + T - 6, y + 4), 1)
                    pygame.draw.line(self._ground_surf, ltc, (x + 5, y + T // 2 + 2),
                                     (x + T - 6, y + T // 2 + 2), 1)
                    # Handle
                    pygame.draw.circle(self._ground_surf, (205, 182, 55), (x + T - 7, y + T // 2), 3)
                    pygame.draw.circle(self._ground_surf, (160, 138, 30), (x + T - 7, y + T // 2), 3, 1)

                elif detail == "hedge":
                    # Dense layered leafy clusters
                    for _ in range(8):
                        hx2 = x + random.randint(2, T - 2)
                        hy2 = y + random.randint(2, T - 2)
                        hr  = random.randint(3, 6)
                        c   = _vary(_lighten(base, random.randint(5, 20)), 8)
                        pygame.draw.circle(self._ground_surf, c, (hx2, hy2), hr)
                    # Darker leaf shadow spots
                    for _ in range(3):
                        hx2 = x + random.randint(3, T - 3)
                        hy2 = y + random.randint(3, T - 3)
                        pygame.draw.circle(self._ground_surf, _darken(base, 20), (hx2, hy2), 2)

                elif detail == "bridge":
                    # Detailed wooden bridge planks with nails and rails
                    lc  = _darken(base, 22)
                    ltc = _lighten(base, 10)
                    # Planks (horizontal boards)
                    for bx_off in range(3, T, 8):
                        pygame.draw.line(self._ground_surf, lc,
                                         (x + bx_off, y + 2), (x + bx_off, y + T - 2), 1)
                        pygame.draw.line(self._ground_surf, ltc,
                                         (x + bx_off + 1, y + 2), (x + bx_off + 1, y + T - 2), 1)
                    # Nail dots
                    for bx_off in range(5, T - 3, 8):
                        pygame.draw.circle(self._ground_surf, _darken(base, 40),
                                           (x + bx_off, y + 5), 1)
                        pygame.draw.circle(self._ground_surf, _darken(base, 40),
                                           (x + bx_off, y + T - 5), 1)
                    # Side rails
                    pygame.draw.line(self._ground_surf, _darken(base, 45),
                                     (x, y + 2), (x + T, y + 2), 2)
                    pygame.draw.line(self._ground_surf, _darken(base, 45),
                                     (x, y + T - 3), (x + T, y + T - 3), 2)
                    pygame.draw.line(self._ground_surf, ltc,
                                     (x, y + 1), (x + T, y + 1), 1)

                elif detail == "fence_h":
                    bg2 = TILE_DEFS[0]["base"]
                    pygame.draw.rect(self._ground_surf, _vary(bg2, 6), rect)
                    fc  = base
                    ltc = _lighten(fc, 15)
                    # Rails
                    pygame.draw.rect(self._ground_surf, fc, (x, y + T // 2 - 2, T, 4))
                    pygame.draw.line(self._ground_surf, ltc, (x, y + T // 2 - 2), (x + T, y + T // 2 - 2), 1)
                    # Pickets
                    for fx in range(x + 4, x + T, T // 3):
                        pygame.draw.rect(self._ground_surf, _darken(fc, 15),
                                         (fx, y + T // 4, 4, T // 2))
                        pygame.draw.line(self._ground_surf, ltc, (fx, y + T // 4), (fx, y + T * 3 // 4), 1)

                elif detail == "fence_v":
                    bg2 = TILE_DEFS[0]["base"]
                    pygame.draw.rect(self._ground_surf, _vary(bg2, 6), rect)
                    fc  = base
                    ltc = _lighten(fc, 15)
                    pygame.draw.rect(self._ground_surf, fc, (x + T // 2 - 2, y, 4, T))
                    pygame.draw.line(self._ground_surf, ltc, (x + T // 2 - 2, y), (x + T // 2 - 2, y + T), 1)
                    for fy in range(y + 4, y + T, T // 3):
                        pygame.draw.rect(self._ground_surf, _darken(fc, 15),
                                         (x + T // 4, fy, T // 2, 4))
                        pygame.draw.line(self._ground_surf, ltc, (x + T // 4, fy), (x + T * 3 // 4, fy), 1)

                elif detail == "cobble":
                    # Fully-drawn irregular cobblestones with depth shading
                    lc = _darken(base, 18)
                    for _ in range(5):
                        cx2 = x + random.randint(4, T - 4)
                        cy2 = y + random.randint(4, T - 4)
                        cr2 = random.randint(3, 6)
                        sc  = _vary(_lighten(base, 12), 8)
                        pygame.draw.circle(self._ground_surf, sc, (cx2, cy2), cr2)
                        pygame.draw.circle(self._ground_surf, lc, (cx2, cy2), cr2, 1)
                        # Highlight
                        pygame.draw.circle(self._ground_surf, _lighten(base, 25),
                                           (cx2 - 1, cy2 - 1), max(1, cr2 // 3))

                elif detail == "flowers":
                    # Lush grass with flowers
                    shade2 = _vary(_lighten(base, 18), 10)
                    for _ in range(6):
                        gx2 = x + random.randint(3, T - 3)
                        gy2 = y + random.randint(4, T - 2)
                        h   = random.randint(3, 6)
                        pygame.draw.line(self._ground_surf, shade2,
                                         (gx2, gy2), (gx2 + random.randint(-1, 1), gy2 - h), 1)
                    for _ in range(3):
                        fx2 = x + random.randint(5, T - 5)
                        fy2 = y + random.randint(5, T - 5)
                        fc2 = random.choice([
                            (215, 55, 55), (55, 55, 210),
                            (225, 205, 45), (205, 95, 185), (255, 155, 55)])
                        pygame.draw.circle(self._ground_surf, fc2, (fx2, fy2), 2)
                        # Petal dots around center
                        for ang in range(0, 360, 90):
                            import math as _m
                            px2 = fx2 + int(2 * _m.cos(_m.radians(ang)))
                            py2 = fy2 + int(2 * _m.sin(_m.radians(ang)))
                            pygame.draw.circle(self._ground_surf, fc2, (px2, py2), 1)

                # Vignette edge (subtle inner shadow on all tiles)
                edge = pygame.Surface((T, T), pygame.SRCALPHA)
                pygame.draw.rect(edge, (0, 0, 0, 18), (0, 0, T, T), 2)
                self._ground_surf.blit(edge, (x, y))

        # ── Decoration layer ──
        if self.decor:
            for row in range(self.height):
                for col in range(self.width):
                    did = self.decor[row][col]
                    ddef = DECOR_DEFS.get(did)
                    if not ddef:
                        continue

                    x, y = col * T, row * T
                    name = ddef["name"]

                    if name == "tree_oak":
                        tc = ddef["trunk"]
                        lc = ddef["color"]
                        # Trunk
                        tw = T // 4
                        pygame.draw.rect(self._decor_surf, tc,
                                         (x + T // 2 - tw // 2, y + T // 3,
                                          tw, T * 2 // 3))
                        # Canopy (overlapping circles)
                        cr = T // 3
                        for ox, oy in [(-3, 0), (3, 0), (0, -3), (-2, -5), (2, -5)]:
                            pygame.draw.circle(self._decor_surf, _vary(lc, 10),
                                               (x + T // 2 + ox, y + T // 4 + oy), cr)
                        # Highlight
                        pygame.draw.circle(self._decor_surf, _lighten(lc, 20),
                                           (x + T // 2 - 2, y + T // 5), cr // 2)

                    elif name == "tree_pine":
                        tc = ddef["trunk"]
                        lc = ddef["color"]
                        tw = T // 5
                        pygame.draw.rect(self._decor_surf, tc,
                                         (x + T // 2 - tw // 2, y + T // 2,
                                          tw, T // 2))
                        # Triangle layers
                        for i, oy in enumerate(range(T // 6, T // 2 + 4, T // 6)):
                            w = T // 3 + i * 3
                            pts = [
                                (x + T // 2, y + oy - T // 5),
                                (x + T // 2 - w // 2, y + oy + 4),
                                (x + T // 2 + w // 2, y + oy + 4),
                            ]
                            pygame.draw.polygon(self._decor_surf, _vary(lc, 8), pts)

                    elif name in ("flowers_red", "flowers_blue"):
                        pc = ddef["petals"]
                        sc = ddef["stem"]
                        for i in range(3):
                            fx = x + 8 + i * (T // 4)
                            fy = y + T // 2 + random.randint(-4, 4)
                            pygame.draw.line(self._decor_surf, sc,
                                             (fx, fy + 6), (fx, fy - 2), 1)
                            pygame.draw.circle(self._decor_surf, pc,
                                               (fx, fy - 2), 3)
                            pygame.draw.circle(self._decor_surf,
                                               _lighten(pc, 40), (fx, fy - 3), 1)

                    elif name == "rock":
                        rc = ddef["color"]
                        sc = ddef["shade"]
                        pts = [
                            (x + T // 4, y + T * 3 // 4),
                            (x + T // 6, y + T // 3),
                            (x + T // 2, y + T // 5),
                            (x + T * 5 // 6, y + T // 3),
                            (x + T * 3 // 4, y + T * 3 // 4),
                        ]
                        pygame.draw.polygon(self._decor_surf, rc, pts)
                        pygame.draw.polygon(self._decor_surf, sc, pts, 2)

                    elif name == "sign":
                        sc = ddef["color"]
                        # Post
                        pygame.draw.rect(self._decor_surf, _darken(sc, 20),
                                         (x + T // 2 - 2, y + T // 3, 4, T * 2 // 3))
                        # Board
                        pygame.draw.rect(self._decor_surf, sc,
                                         (x + T // 5, y + T // 6,
                                          T * 3 // 5, T // 3), border_radius=2)
                        pygame.draw.rect(self._decor_surf, _darken(sc, 30),
                                         (x + T // 5, y + T // 6,
                                          T * 3 // 5, T // 3), 1, border_radius=2)

                    elif name == "chest":
                        cc = ddef["color"]
                        lk = ddef["lock"]
                        cw, ch = T * 3 // 5, T // 3
                        cx_ = x + T // 2 - cw // 2
                        cy_ = y + T // 2 - ch // 2 + 2
                        pygame.draw.rect(self._decor_surf, cc,
                                         (cx_, cy_, cw, ch), border_radius=3)
                        pygame.draw.rect(self._decor_surf, _darken(cc, 30),
                                         (cx_, cy_, cw, ch), 2, border_radius=3)
                        # Lid
                        pygame.draw.rect(self._decor_surf, _lighten(cc, 15),
                                         (cx_, cy_, cw, ch // 2), border_radius=2)
                        # Lock
                        pygame.draw.circle(self._decor_surf, lk,
                                           (x + T // 2, cy_ + ch // 2), 3)

                    elif name == "well":
                        wc = ddef["color"]
                        rc = ddef["roof"]
                        # Base circle
                        pygame.draw.circle(self._decor_surf, wc,
                                           (x + T // 2, y + T // 2 + 3), T // 3, 3)
                        # Water inside
                        pygame.draw.circle(self._decor_surf, (40, 70, 150),
                                           (x + T // 2, y + T // 2 + 3), T // 3 - 3)
                        # Posts
                        pygame.draw.rect(self._decor_surf, _darken(wc, 20),
                                         (x + T // 4, y + T // 6, 3, T // 2))
                        pygame.draw.rect(self._decor_surf, _darken(wc, 20),
                                         (x + T * 3 // 4 - 3, y + T // 6, 3, T // 2))
                        # Roof
                        pts = [(x + T // 6, y + T // 5),
                               (x + T // 2, y - 2),
                               (x + T * 5 // 6, y + T // 5)]
                        pygame.draw.polygon(self._decor_surf, rc, pts)

                    elif name == "barrel":
                        bc = ddef["color"]
                        bd = ddef["band"]
                        bw, bh = T // 2, T * 2 // 3
                        bx = x + T // 2 - bw // 2
                        by = y + T - bh - 2
                        pygame.draw.ellipse(self._decor_surf, bc,
                                            (bx, by, bw, bh))
                        pygame.draw.ellipse(self._decor_surf, _darken(bc, 20),
                                            (bx, by, bw, bh), 2)
                        # Bands
                        for band_y in (by + bh // 4, by + bh * 3 // 4):
                            pygame.draw.line(self._decor_surf, bd,
                                             (bx + 2, band_y), (bx + bw - 2, band_y), 2)

                    elif name == "crate":
                        cc = ddef["color"]
                        sc = ddef["stripe"]
                        cw = T * 3 // 5
                        cx_ = x + T // 2 - cw // 2
                        cy_ = y + T - cw - 2
                        pygame.draw.rect(self._decor_surf, cc,
                                         (cx_, cy_, cw, cw))
                        pygame.draw.rect(self._decor_surf, sc,
                                         (cx_, cy_, cw, cw), 2)
                        # X pattern
                        pygame.draw.line(self._decor_surf, sc,
                                         (cx_, cy_), (cx_ + cw, cy_ + cw), 1)
                        pygame.draw.line(self._decor_surf, sc,
                                         (cx_ + cw, cy_), (cx_, cy_ + cw), 1)

                    elif name == "lamp_post":
                        pc = ddef["color"]
                        lc_ = ddef["light"]
                        # Pole
                        pygame.draw.rect(self._decor_surf, pc,
                                         (x + T // 2 - 1, y + T // 4, 3, T * 3 // 4))
                        # Lamp
                        pygame.draw.circle(self._decor_surf, lc_,
                                           (x + T // 2, y + T // 5), 4)
                        # Glow
                        glow = pygame.Surface((T, T), pygame.SRCALPHA)
                        pygame.draw.circle(glow, (*lc_, 30),
                                           (T // 2, T // 5), T // 3)
                        self._decor_surf.blit(glow, (x, y))

                    elif name == "stall":
                        sc = ddef["color"]
                        cl = ddef["cloth"]
                        # Counter
                        sw, sh = T * 4 // 5, T // 3
                        sx_ = x + T // 2 - sw // 2
                        sy_ = y + T // 2
                        pygame.draw.rect(self._decor_surf, sc,
                                         (sx_, sy_, sw, sh), border_radius=2)
                        pygame.draw.rect(self._decor_surf, _darken(sc, 20),
                                         (sx_, sy_, sw, sh), 2, border_radius=2)
                        # Awning
                        pygame.draw.rect(self._decor_surf, cl,
                                         (sx_ - 2, sy_ - 6, sw + 4, 8), border_radius=2)
                        # Stripe on awning
                        pygame.draw.line(self._decor_surf, _lighten(cl, 40),
                                         (sx_, sy_ - 4), (sx_ + sw, sy_ - 4), 1)

                    elif name == "bush":
                        bc = ddef["color"]
                        br = ddef.get("berry", (180, 40, 40))
                        for i in range(4):
                            bx_ = x + T // 4 + i * (T // 6)
                            by_ = y + T // 2 + random.randint(-2, 2)
                            pygame.draw.circle(self._decor_surf,
                                               _vary(bc, 10), (bx_, by_), T // 5)
                        # Berries
                        for _ in range(2):
                            bx_ = x + random.randint(T // 3, T * 2 // 3)
                            by_ = y + T // 2 + random.randint(-3, 3)
                            pygame.draw.circle(self._decor_surf, br, (bx_, by_), 2)

                    elif name == "grave":
                        gc = ddef["color"]
                        sc = ddef["shade"]
                        # Headstone
                        gw, gh = T // 3, T // 2
                        gx_ = x + T // 2 - gw // 2
                        gy_ = y + T // 3
                        pygame.draw.rect(self._decor_surf, gc,
                                         (gx_, gy_, gw, gh), border_radius=3)
                        pygame.draw.rect(self._decor_surf, sc,
                                         (gx_, gy_, gw, gh), 1, border_radius=3)
                        # Cross
                        pygame.draw.line(self._decor_surf, sc,
                                         (x + T // 2, gy_ + 4),
                                         (x + T // 2, gy_ + gh - 4), 1)
                        pygame.draw.line(self._decor_surf, sc,
                                         (gx_ + 3, gy_ + gh // 3),
                                         (gx_ + gw - 3, gy_ + gh // 3), 1)

    def _visible_blit(self, cam_x: int, cam_y: int, viewport_size: tuple[int, int]):
        viewport_w = max(1, int(viewport_size[0]))
        viewport_h = max(1, int(viewport_size[1]))
        map_w, map_h = self._ground_surf.get_size()

        src_x = max(0, int(cam_x))
        src_y = max(0, int(cam_y))
        dst_x = max(0, -int(cam_x))
        dst_y = max(0, -int(cam_y))

        width = min(viewport_w - dst_x, map_w - src_x)
        height = min(viewport_h - dst_y, map_h - src_y)
        if width <= 0 or height <= 0:
            return None

        return (dst_x, dst_y), pygame.Rect(src_x, src_y, width, height)

    def render(self, screen: pygame.Surface, cam_x: int, cam_y: int):
        visible = self._visible_blit(cam_x, cam_y, screen.get_size())
        if visible is None:
            return
        dest, area = visible
        screen.blit(self._ground_surf, dest, area=area)
        if self.decor:
            screen.blit(self._decor_surf, dest, area=area)

    def is_solid(self, tile_x: int, tile_y: int) -> bool:
        if tile_x < 0 or tile_y < 0 or tile_x >= self.width or tile_y >= self.height:
            return True
        return self.collision[tile_y][tile_x] == 1

    def is_passable(self, tile_x: float, tile_y: float) -> bool:
        tx = int(tile_x + 0.5)
        ty = int(tile_y + 0.5)
        return not self.is_solid(tx, ty)
