"""
Mythic Sanctum — Stage 3 map set.
Two connected maps: sanctum_halls (approach) and throne_room (final boss).

Thematic identity: a shattered floating citadel above the world.
Void tiles (impassable dark crystal) replace hedges as the outer boundary.
Crystal formations, energy conduits, and fractured stone make up the terrain.

sanctum_halls : 60×40 tiles — approach halls, crystal chambers, elite enemies.
throne_room   : 50×36 tiles — the Sovereign's throne chamber, final boss arena.

Ground tile ID reuse:
  2=cracked stone floor, 6=void/crystal wall (impassable),
  14=ancient gilded cobble, 10=ash/crystal dust,
  4=shimmering abyss pool (impassable like water),
  16=deep abyss (instant kill if reached — handled by gameplay as solid)
"""

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

W_H, H_H = 60, 40
W_T, H_T = 50, 36


def _grid(w, h, val=0):
    return [[val] * w for _ in range(h)]


def _fill_rect(grid, x1, y1, x2, y2, val):
    for r in range(y1, y2 + 1):
        for c in range(x1, x2 + 1):
            if 0 <= r < len(grid) and 0 <= c < len(grid[0]):
                grid[r][c] = val


def _fill_border(grid, x1, y1, x2, y2, val):
    for c in range(x1, x2 + 1):
        if 0 <= y1 < len(grid): grid[y1][c] = val
        if 0 <= y2 < len(grid): grid[y2][c] = val
    for r in range(y1, y2 + 1):
        if 0 <= r < len(grid):
            if 0 <= x1 < len(grid[0]): grid[r][x1] = val
            if 0 <= x2 < len(grid[0]): grid[r][x2] = val


# ─────────────────────────────────────────────────────────────────────────────
# SANCTUM HALLS (60×40)
# ─────────────────────────────────────────────────────────────────────────────

def _halls_ground():
    g = _grid(W_H, H_H, 6)  # void crystal default

    # Entire interior as abyss by default, then carve walkable platforms
    _fill_rect(g, 1, 1, W_H - 2, H_H - 2, 16)   # deep abyss (solid, looks dangerous)

    # Outer walls
    _fill_rect(g, 0, 0, W_H - 1, 0, 6)
    _fill_rect(g, 0, H_H - 1, W_H - 1, H_H - 1, 6)
    _fill_rect(g, 0, 0, 0, H_H - 1, 6)
    _fill_rect(g, W_H - 1, 0, W_H - 1, H_H - 1, 6)

    # West entrance platform
    for r in range(16, 25):
        g[r][0] = 14
    _fill_rect(g, 1, 14, 10, 26, 14)    # entry platform

    # ── Floating platform chain west→east ──
    # Platform 1 (entrance hall)
    _fill_rect(g, 1,  14, 16,  26, 14)
    _fill_border(g, 1, 14, 16, 26, 6)
    # Open west entrance through platform 1 border
    for r in range(16, 25):
        g[r][1] = 14
    for r in range(18, 22): g[r][16] = 14   # bridge east

    # Narrow bridge 1
    for r in range(18, 22):
        for c in range(16, 22):
            g[r][c] = 14

    # Platform 2 (crystal chamber)
    _fill_rect(g, 22, 12, 38, 28, 14)
    _fill_border(g, 22, 12, 38, 28, 6)
    # Open west entrance from bridge 1
    for r in range(18, 22):
        g[r][22] = 14
    # Crystal shards inside (impassable crystal columns)
    for r, c in [(15, 28), (15, 32), (16, 30), (25, 24), (25, 36), (26, 24)]:
        if 0 <= r < H_H and 0 <= c < W_H:
            g[r][c] = 6
    for r in range(18, 22): g[r][38] = 14   # bridge east

    # Narrow bridge 2
    for r in range(18, 22):
        for c in range(38, 46):
            g[r][c] = 14

    # Platform 3 (throne approach)
    _fill_rect(g, 46, 10, 58, 30, 14)
    _fill_border(g, 46, 10, 58, 30, 6)
    # Open west entrance from bridge 2
    for r in range(18, 22):
        g[r][46] = 14

    # East causeway to throne_room — widen and brighten the final approach
    _fill_rect(g, 50, 15, W_H - 1, 24, 14)
    for r in range(16, 24):
        g[r][W_H - 2] = 14   # platform 3 right border (col 58)
        g[r][W_H - 1] = 14   # map edge (col 59)
    for r in range(17, 23):
        for c in range(52, W_H):
            if (r + c) % 3 == 0:
                g[r][c] = 2

    # Gilded floor variation
    for r in range(H_H):
        for c in range(W_H):
            if g[r][c] == 14 and (c * 3 + r * 5) % 11 == 0:
                g[r][c] = 2   # cracked patches

    return g


def _halls_decor():
    d = _grid(W_H, H_H, 0)

    # Crystal formations (rocks)
    crystal_spots = [
        (16, 4), (16, 13), (14, 9), (26, 14), (26, 36),
        (13, 24), (13, 34), (47, 12), (47, 28), (57, 12), (57, 28)
    ]
    for r, c in crystal_spots:
        if 0 <= r < H_H and 0 <= c < W_H:
            d[r][c] = 4   # rock / crystal

    # Graves of fallen champions (throne approach)
    for r, c in [(48, 48), (50, 50), (52, 48), (54, 50), (28, 14), (28, 36)]:
        if 0 <= r < H_H and 0 <= c < W_H:
            d[r][c] = 14

    # Chests
    d[14][14] = 6   # sanctum_halls_chest_west  (hidden near entrance)
    d[14][36] = 6   # sanctum_halls_chest_east  (near throne approach)

    # Sign
    d[19][45] = 5

    return d


def _halls_collision():
    g = _halls_ground()
    solid = {6, 16}
    c = _grid(W_H, H_H, 0)
    for r in range(H_H):
        for col in range(W_H):
            c[r][col] = 1 if g[r][col] in solid else 0
    return c


def _halls_spawns():
    return {
        "player":          (2, 19),
        "ascended_guide":  (4, 19),
    }


def _halls_signs():
    return {
        (45, 19): "The Sovereign's throne lies ahead.\nFace your fate."
    }


# ─────────────────────────────────────────────────────────────────────────────
# THRONE ROOM (50×36)
# ─────────────────────────────────────────────────────────────────────────────

def _throne_ground():
    g = _grid(W_T, H_T, 6)  # void walls

    # Deep abyss ring
    _fill_rect(g, 1, 1, W_T - 2, H_T - 2, 16)

    # Outer void border
    _fill_rect(g, 0, 0, W_T - 1, 0, 6)
    _fill_rect(g, 0, H_T - 1, W_T - 1, H_T - 1, 6)
    _fill_rect(g, 0, 0, 0, H_T - 1, 6)
    _fill_rect(g, W_T - 1, 0, W_T - 1, H_T - 1, 6)

    # West entrance / return bridge
    for r in range(14, 22):
        g[r][0] = 14
        g[r][1] = 14   # bridge over abyss gap

    # Main throne platform (large central arena)
    _fill_rect(g, 2, 4, W_T - 3, H_T - 5, 14)
    _fill_border(g, 2, 4, W_T - 3, H_T - 5, 6)

    # Gilded centre
    _fill_rect(g, 8, 8, W_T - 9, H_T - 9, 2)

    # Re-open entrance gap in west wall of arena and add a visible causeway
    _fill_rect(g, 2, 14, 12, 22, 14)
    for r in range(14, 22):
        g[r][2] = 14
        g[r][3] = 14
    for r in range(15, 21):
        for c in range(4, 14):
            if (r + c) % 2 == 0:
                g[r][c] = 2

    # Crystal pillars in throne room
    for r, c in [
        (7, 10), (7, 18), (7, 30), (7, 38),
        (28, 10), (28, 18), (28, 30), (28, 38),
    ]:
        if 0 <= r < H_T and 0 <= c < W_T:
            g[r][c] = 6

    # Abyss pools (dramatic effect, impassable)
    for r, c in [(18, 45), (19, 45), (18, 46), (17, 44),
                 (18, 4), (19, 4), (17, 5)]:
        if 0 <= r < H_T and 0 <= c < W_T:
            g[r][c] = 4

    return g


def _throne_decor():
    d = _grid(W_T, H_T, 0)

    # Mythic chests (reward after final boss)
    d[6][44]  = 6   # throne_room_mythic_chest_1
    d[29][44] = 6   # throne_room_mythic_chest_2

    # Crystal formations
    for r, c in [(5, 5), (5, 43), (30, 5), (30, 43), (17, 24)]:
        if 0 <= r < H_T and 0 <= c < W_T:
            d[r][c] = 4

    # Graves of previous champions
    for r, c in [(10, 6), (12, 6), (10, 42), (12, 42), (25, 6), (25, 42)]:
        if 0 <= r < H_T and 0 <= c < W_T:
            d[r][c] = 14

    return d


def _throne_collision():
    g = _throne_ground()
    solid = {6, 16}
    c = _grid(W_T, H_T, 0)
    for r in range(H_T):
        for col in range(W_T):
            c[r][col] = 1 if g[r][col] in solid else 0
    return c


def _throne_spawns():
    return {
        "player":           (4, 17),
        "boss_mythic_sovereign": (42, 17),
    }


def _throne_signs():
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Exported map data dicts
# ─────────────────────────────────────────────────────────────────────────────

SANCTUM_HALLS = {
    "name":      "sanctum_halls",
    "width":     W_H,
    "height":    H_H,
    "ground":    _halls_ground(),
    "decor":     _halls_decor(),
    "collision": _halls_collision(),
    "spawns":    _halls_spawns(),
    "signs":     _halls_signs(),
    "exits": {
        **{(W_H - 1, r): {"map": "throne_room", "spawn": (5, 18)} for r in range(16, 24)},
        **{(0, r): {"map": "ruins_depths", "spawn": (57, 19)} for r in range(16, 25)},
    },
    "ambient_light": 50,
}

THRONE_ROOM = {
    "name":      "throne_room",
    "width":     W_T,
    "height":    H_T,
    "ground":    _throne_ground(),
    "decor":     _throne_decor(),
    "collision": _throne_collision(),
    "spawns":    _throne_spawns(),
    "signs":     _throne_signs(),
    "exits": {(0, r): {"map": "sanctum_halls", "spawn": (57, 19)}
              for r in range(14, 22)},
    "ambient_light": 35,
}
