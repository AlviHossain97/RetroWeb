"""
Haunted Ruins — Stage 2 map set.
Two connected maps: ruins_approach (entry) and ruins_depths (main + boss).

ruins_approach : 50×36 tiles — crumbling battlefield leading to ancient ruins.
ruins_depths   : 60×40 tiles — interior ruins: crypts, bone halls, boss chamber.

Ground tile IDs (reuse village/dungeon vocabulary):
  0=grass  1=dirt  2=stone  3=dark_grass  4=water  5=wood  6=stone_wall
  7=roof   8=door  9=hedge  10=sand       11=bridge 12=fence_h 13=fence_v
  14=cobble 15=grass_flower 16=deep_water 17=wood_wall

Ruins-specific interpretation: stone(2) = cracked stone floor, stone_wall(6) = ruin wall,
  dark_grass(3) = dead/blackened grass, cobble(14) = ancient paving, sand(10) = ash/dust

Decor IDs (same set as village):
  0=none 1=oak_tree 2=pine_tree 3=red_flowers 4=rock 5=sign
  6=chest 7=well 8=barrel 9=crate 10=blue_flowers 11=lamp_post
  12=stall 13=bush 14=grave
"""

# ─────────────────────────────────────────────────────────────────────────────
# RUINS APPROACH (50×36) — crumbling battlefield, entry from village side
# ─────────────────────────────────────────────────────────────────────────────

W_A, H_A = 50, 36


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


def _approach_ground():
    g = _grid(W_A, H_A, 3)  # dead dark grass base

    # Variation: ash patches, cracked earth
    for r in range(H_A):
        for c in range(W_A):
            if (c * 5 + r * 7) % 17 == 0:
                g[r][c] = 10   # ash dust
            elif (c + r * 3) % 19 == 0:
                g[r][c] = 2    # cracked stone

    # Impassable border (dense dead hedges)
    _fill_rect(g, 0, 0, W_A - 1, 0, 9)
    _fill_rect(g, 0, H_A - 1, W_A - 1, H_A - 1, 9)
    _fill_rect(g, 0, 0, 0, H_A - 1, 9)
    _fill_rect(g, W_A - 1, 0, W_A - 1, H_A - 1, 9)

    # West entrance gap (from village/dungeon)
    for r in range(15, 21):
        g[r][0] = 3

    # East exit gap (to ruins_depths) — must cover path rows 21-22 too
    for r in range(15, 23):
        g[r][W_A - 1] = 2

    # Main winding path west→east
    for c in range(0, 12):
        g[17][c] = 1
        g[18][c] = 1
    for r in range(12, 18):
        g[r][11] = 1
        g[r][12] = 1
    for c in range(11, 28):
        g[12][c] = 1
        g[13][c] = 1
    for r in range(12, 22):
        g[r][27] = 1
        g[r][28] = 1
    for c in range(27, 50):
        g[21][c] = 1
        g[22][c] = 1

    # Ruined courtyard area (cracked cobble)
    _fill_rect(g, 32, 8, 46, 20, 14)
    _fill_border(g, 32, 8, 46, 20, 6)   # ruin wall border
    # South entrance from main path
    for c in range(37, 41):
        g[20][c] = 14
    # West entrance from the north path area
    for r in range(12, 15):
        g[r][32] = 14
    # East opening (ruined wall gap) → leads toward the exit
    for r in range(14, 19):
        g[r][46] = 14

    # Connecting path from courtyard east side to the map exit
    for c in range(46, W_A):
        g[17][c] = 1
        g[18][c] = 1

    # Broken walls scattered
    for r, c in [(5, 10), (5, 11), (6, 10), (8, 20), (8, 21), (9, 21),
                 (25, 15), (26, 15), (25, 16), (28, 35), (29, 35), (28, 36)]:
        if 0 <= r < H_A and 0 <= c < W_A:
            g[r][c] = 6

    # Stagnant puddles
    for r, c in [(20, 5), (20, 6), (21, 5), (30, 25), (30, 26), (31, 25)]:
        if 0 <= r < H_A and 0 <= c < W_A:
            g[r][c] = 4

    return g


def _approach_decor():
    d = _grid(W_A, H_A, 0)
    # Dead/twisted trees
    dead_trees = [
        (3, 5), (4, 8), (6, 15), (3, 22), (5, 30), (3, 38), (4, 44),
        (10, 3), (10, 20), (10, 42), (32, 3), (33, 8), (32, 40), (33, 45),
    ]
    for r, c in dead_trees:
        if 0 <= r < H_A and 0 <= c < W_A:
            d[r][c] = 2  # pine (sparse dead silhouette)

    # Graves scattered on battlefield
    graves = [
        (7, 12), (9, 14), (11, 18), (7, 25), (9, 28), (11, 32), (7, 38),
        (25, 6), (27, 9), (25, 18), (27, 22), (29, 30)
    ]
    for r, c in graves:
        if 0 <= r < H_A and 0 <= c < W_A:
            d[r][c] = 14  # grave

    # Rocks scattered
    rocks = [(15, 6), (14, 20), (16, 34), (20, 42), (25, 12), (30, 40)]
    for r, c in rocks:
        if 0 <= r < H_A and 0 <= c < W_A:
            d[r][c] = 4

    # Chest: ruins_approach north chest (early Stage 2 loot)
    d[7][38] = 6

    # Entrance sign
    d[17][2] = 5

    return d


def _approach_collision():
    g = _approach_ground()
    solid = {6, 9}  # stone_wall, hedge
    c = _grid(W_A, H_A, 0)
    for r in range(H_A):
        for col in range(W_A):
            c[r][col] = 1 if g[r][col] in solid else 0
    return c


def _approach_spawns():
    return {
        "player":      (2, 17),
        "guide_npc":   (5, 17),
        "ruins_exit":  (47, 21),
    }


def _approach_signs():
    return {
        (2, 17): "The ruins ahead reek of death.\nProceed with caution.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# RUINS DEPTHS (60×40) — crypts, bone halls, boss arena
# ─────────────────────────────────────────────────────────────────────────────

W_D, H_D = 60, 40


def _depths_ground():
    g = _grid(W_D, H_D, 6)  # stone wall default (solid)

    # Main floor cavity
    _fill_rect(g, 1, 1, W_D - 2, H_D - 2, 2)   # cracked stone floor

    # Outer border
    _fill_rect(g, 0, 0, W_D - 1, 0, 6)
    _fill_rect(g, 0, H_D - 1, W_D - 1, H_D - 1, 6)
    _fill_rect(g, 0, 0, 0, H_D - 1, 6)
    _fill_rect(g, W_D - 1, 0, W_D - 1, H_D - 1, 6)

    # West entrance
    for r in range(17, 23):
        g[r][0] = 2
        g[r][1] = 2   # clear room 1 border so player can reach the exit

    # ── Room 1: Entry hall (west) ──
    _fill_rect(g, 1,  12, 14,  27, 2)
    _fill_border(g, 1, 12, 14, 27, 6)
    # Re-open west entrance through room 1 wall
    for r in range(17, 23):
        g[r][1] = 2
    for r in range(18, 22):
        g[r][14] = 2   # east passage

    # ── Corridor A ──
    for r in range(18, 22):
        for c in range(14, 22):
            g[r][c] = 2

    # ── Room 2: Bone chamber ──
    _fill_rect(g, 22, 10, 38, 29, 2)
    _fill_border(g, 22, 10, 38, 29, 6)
    # Open west entrance from corridor A
    for r in range(18, 22):
        g[r][22] = 2
    for r in range(18, 22):
        g[r][38] = 2   # east passage

    # ── Corridor B ──
    for r in range(18, 22):
        for c in range(38, 46):
            g[r][c] = 2

    # ── Boss chamber (east) ──
    _fill_rect(g, 46, 8, 58, 32, 2)
    _fill_border(g, 46, 8, 58, 32, 6)
    for r in range(18, 22):
        g[r][46] = 2   # boss entrance

    # Cobblestone floor in boss arena
    _fill_rect(g, 47, 9, 57, 31, 14)

    # East sanctum causeway — widen the exit lane after the boss chamber
    _fill_rect(g, 50, 15, W_D - 1, 24, 14)

    # Pillar obstacles in rooms (impassable) — keep out of passage rows 18-21
    for r, c in [(15, 5), (15, 10), (25, 5), (25, 10),  # room 1 pillars
                 (14, 28), (14, 34), (26, 28), (26, 34),  # room 2 pillars
                 (12, 50), (12, 54), (16, 50), (16, 54), (28, 50), (28, 54)]:  # boss room pillars
        if 0 <= r < H_D and 0 <= c < W_D:
            g[r][c] = 6

    # Stagnant water pools in bone chamber
    for r, c in [(12, 24), (12, 25), (13, 24), (26, 31), (26, 32), (27, 31)]:
        if 0 <= r < H_D and 0 <= c < W_D:
            g[r][c] = 4

    # East exit → Mythic Sanctum (open boss chamber right wall + border)
    for r in range(16, 25):
        g[r][W_D - 2] = 2   # boss chamber right border (col 58)
        g[r][W_D - 1] = 2   # map edge border (col 59)
    for r in range(17, 24):
        for c in range(52, W_D):
            if (r + c) % 3 == 0:
                g[r][c] = 2

    return g


def _depths_decor():
    d = _grid(W_D, H_D, 0)
    # Graves/bones in bone chamber
    grave_positions = [
        (14, 25), (16, 27), (18, 30), (20, 32), (22, 25),
        (24, 28), (26, 25), (27, 36), (13, 33)
    ]
    for r, c in grave_positions:
        if 0 <= r < H_D and 0 <= c < W_D:
            d[r][c] = 14

    # Barrels/crates near entrance
    for r, c in [(15, 3), (16, 3), (22, 3), (22, 12), (23, 12)]:
        if 0 <= r < H_D and 0 <= c < W_D:
            d[r][c] = 8

    # Boss chamber: chests + signs
    d[10][56] = 6   # ruins_depths_boss_chest (post-boss reward)
    d[30][56] = 9   # crate

    # Signs
    d[20][45] = 5   # "The Gravewarden sleeps ahead."
    d[17][57] = 5   # sign pointing east to Mythic Sanctum

    return d


def _depths_collision():
    g = _depths_ground()
    solid = {6}
    c = _grid(W_D, H_D, 0)
    for r in range(H_D):
        for col in range(W_D):
            c[r][col] = 1 if g[r][col] in solid else 0
    return c


def _depths_spawns():
    return {
        "player":          (2, 19),
        "ruins_scout_npc": (4, 19),
        "boss_gravewarden": (52, 20),
    }


def _depths_signs():
    return {
        (45, 20): "A faint inscription:\n'The Gravewarden never truly dies.'",
        (57, 17): "A shattered archway leads east.\n'The Mythic Sanctum awaits beyond.'",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Exported map data dicts
# ─────────────────────────────────────────────────────────────────────────────

RUINS_APPROACH = {
    "name":      "ruins_approach",
    "width":     W_A,
    "height":    H_A,
    "ground":    _approach_ground(),
    "decor":     _approach_decor(),
    "collision": _approach_collision(),
    "spawns":    _approach_spawns(),
    "signs":     _approach_signs(),
    "exits": {
        **{(W_A - 1, r): {"map": "ruins_depths", "spawn": (2, 19)} for r in range(15, 23)},
        **{(0, r): {"map": "dungeon", "spawn": (37, 24)} for r in range(15, 21)},
    },
    "ambient_light": 90,
}

RUINS_DEPTHS = {
    "name":      "ruins_depths",
    "width":     W_D,
    "height":    H_D,
    "ground":    _depths_ground(),
    "decor":     _depths_decor(),
    "collision": _depths_collision(),
    "spawns":    _depths_spawns(),
    "signs":     _depths_signs(),
    "exits": {
        **{(0, r): {"map": "ruins_approach", "spawn": (47, 21)} for r in range(17, 23)},
        **{(W_D - 1, r): {"map": "sanctum_halls", "spawn": (2, 19)} for r in range(16, 25)},
    },
    "ambient_light": 60,
}
