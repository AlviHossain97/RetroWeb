"""
Dungeon — dark forest leading into a cave system.
40x40 tiles. Entry from west (village), boss room in the east.

Layout:
  - Forest entrance (west) with winding path
  - Cave mouth midway
  - 3 cave rooms connected by corridors
  - Boss chamber (east)
  - Exit back to village (west edge)
"""

W, H = 40, 40


def _grid(w, h, val=0):
    return [[val] * w for _ in range(h)]


def _fill_rect(grid, x1, y1, x2, y2, val):
    for r in range(y1, y2 + 1):
        for c in range(x1, x2 + 1):
            if 0 <= r < len(grid) and 0 <= c < len(grid[0]):
                grid[r][c] = val


def _fill_border(grid, x1, y1, x2, y2, val):
    for c in range(x1, x2 + 1):
        if 0 <= y1 < len(grid):
            grid[y1][c] = val
        if 0 <= y2 < len(grid):
            grid[y2][c] = val
    for r in range(y1, y2 + 1):
        if 0 <= r < len(grid):
            grid[r][x1] = val
            grid[r][x2] = val


def _build_ground():
    g = _grid(W, H, 3)  # dark grass everywhere

    # ── Dense forest border ──
    _fill_rect(g, 0, 0, W - 1, 0, 9)
    _fill_rect(g, 0, H - 1, W - 1, H - 1, 9)
    _fill_rect(g, 0, 0, 0, H - 1, 9)
    _fill_rect(g, W - 1, 0, W - 1, H - 1, 9)

    # ── West entrance (from village) ──
    for r in range(4, 9):
        g[r][0] = 1  # opening

    # ── Forest floor variation ──
    for r in range(H):
        for c in range(W):
            if g[r][c] == 3 and (c * 3 + r * 7) % 13 == 0:
                g[r][c] = 0  # lighter grass patches

    # ── Winding dirt path from entrance to cave ──
    # Horizontal from entrance
    for c in range(0, 8):
        g[5][c] = 1
        g[6][c] = 1
    # Turn south
    for r in range(5, 12):
        g[r][7] = 1
        g[r][8] = 1
    # East toward cave
    for c in range(7, 16):
        g[11][c] = 1
        g[12][c] = 1
    # Turn north
    for r in range(7, 13):
        g[r][15] = 1
        g[r][16] = 1
    # East to cave mouth
    for c in range(15, 21):
        g[7][c] = 1
        g[8][c] = 1

    # ── Cave walls (stone wall border around cave system) ──
    # Cave entrance hall
    _fill_rect(g, 19, 3, 28, 12, 6)   # solid stone
    _fill_rect(g, 20, 4, 27, 11, 2)   # stone floor interior
    # Entrance opening
    g[7][19] = 2
    g[8][19] = 2

    # ── Corridor east from entrance hall ──
    for c in range(27, 32):
        g[7][c] = 6  # top wall
        g[8][c] = 2  # floor
        g[9][c] = 2  # floor
        g[10][c] = 6 # bottom wall

    # ── Room 2: Trap room (center-east) ──
    _fill_rect(g, 30, 3, 38, 14, 6)
    _fill_rect(g, 31, 4, 37, 13, 2)
    # Opening from corridor
    g[8][30] = 2
    g[9][30] = 2

    # ── Corridor south from room 2 ──
    for r in range(13, 20):
        g[r][33] = 6
        g[r][34] = 2
        g[r][35] = 2
        g[r][36] = 6

    # ── Room 3: Puzzle room (south) ──
    _fill_rect(g, 25, 19, 38, 29, 6)
    _fill_rect(g, 26, 20, 37, 28, 2)
    # Opening from corridor
    g[19][34] = 2
    g[19][35] = 2

    # ── Corridor west from puzzle room ──
    for c in range(18, 27):
        g[23][c] = 6
        g[24][c] = 2
        g[25][c] = 2
        g[26][c] = 6

    # ── Room 4: Boss chamber (south-west) ──
    _fill_rect(g, 8, 20, 19, 32, 6)
    _fill_rect(g, 9, 21, 18, 31, 2)
    # Opening from corridor
    g[24][19] = 2
    g[25][19] = 2

    # ── Water puddles in cave rooms ──
    g[6][23] = 4
    g[6][24] = 4
    g[9][24] = 4

    # Stone floor variation in caves
    for r in range(H):
        for c in range(W):
            if g[r][c] == 2 and (c * 5 + r * 11) % 17 == 0:
                g[r][c] = 14  # cobble patches

    # ── East exit corridor toward the Haunted Ruins ──
    # Extends the existing corridor (rows 24-25) all the way to the east edge
    for c_idx in range(26, W):
        g[24][c_idx] = 1
        g[25][c_idx] = 1
    # Open east border hedge for the exit rows
    for r in range(22, 28):
        g[r][W - 1] = 1

    return g


def _build_decor():
    d = _grid(W, H, 0)

    # ── Forest trees (dense, surrounding path) ──
    forest_trees = [
        # Around entrance path
        (2, 2), (2, 5), (2, 9), (3, 3), (3, 7), (3, 11),
        (4, 10), (4, 13),
        (8, 2), (8, 5), (9, 3), (9, 10), (9, 13),
        (10, 2), (10, 5),
        (13, 2), (13, 5), (13, 10), (13, 13),
        # Dense forest filling
        (2, 14), (2, 17), (3, 16),
        (14, 2), (14, 5), (14, 8), (14, 11),
        (16, 3), (16, 7), (16, 10), (16, 14),
        (18, 2), (18, 5), (18, 8), (18, 12),
        (20, 6), (22, 3), (22, 7),
        (24, 3), (24, 7), (26, 2), (26, 5),
        (28, 3), (28, 8), (30, 2), (30, 5),
        (32, 3), (32, 7), (34, 2), (34, 5), (34, 10),
        (36, 3), (36, 7), (36, 11), (38, 2), (38, 5),
        # East side forest
        (15, 17), (17, 16), (19, 15),
        (30, 10), (32, 14), (34, 16), (36, 15),
        (30, 15), (32, 10), (34, 13),
    ]
    for r, c in forest_trees:
        if 0 < r < H - 1 and 0 < c < W - 1:
            d[r][c] = 2  # pine trees for dark forest

    # ── Rocks along paths ──
    d[4][4] = 4
    d[10][9] = 4
    d[13][14] = 4

    # ── Mushroom-like flowers in forest ──
    d[6][3] = 3
    d[9][6] = 10
    d[12][4] = 3

    # ── Cave decorations ──
    # Entrance hall: barrels and crates (old supplies)
    d[5][21] = 8
    d[5][22] = 9
    d[10][26] = 8
    d[10][27] = 9

    # Trap room: rocks scattered
    d[5][32] = 4
    d[5][36] = 4
    d[12][32] = 4
    d[12][36] = 4
    d[8][34] = 4  # center obstacle

    # Puzzle room: crates to push (visual only for now)
    d[22][28] = 9
    d[22][32] = 9
    d[26][28] = 9
    d[26][35] = 9
    d[24][30] = 11  # lamp

    # Boss chamber: dramatic setup
    d[22][13] = 11   # lamp posts
    d[22][15] = 11
    d[28][13] = 11
    d[28][15] = 11
    d[23][10] = 4    # rocks
    d[23][17] = 4
    d[29][10] = 4
    d[29][17] = 4
    # Chest (boss reward)
    d[22][14] = 6

    # Sign at cave entrance
    d[7][18] = 5

    # Sign near east exit toward Haunted Ruins
    d[22][36] = 5

    return d


def _build_collision():
    c = _grid(W, H, 0)

    # ── All stone walls are solid ──
    g = _build_ground()
    for r in range(H):
        for cr in range(W):
            if g[r][cr] == 6:   # stone wall
                c[r][cr] = 1
            elif g[r][cr] == 9: # hedge
                c[r][cr] = 1
            elif g[r][cr] == 4: # water
                c[r][cr] = 1

    # Border
    for col in range(W):
        c[0][col] = 1
        c[H - 1][col] = 1
    for row in range(H):
        c[row][0] = 1
        c[row][W - 1] = 1

    # West entrance opening
    for r in range(4, 9):
        c[r][0] = 0

    # East exit opening
    for r in range(22, 28):
        c[r][W - 1] = 0

    # ── Trees are solid ──
    d = _build_decor()
    for r in range(H):
        for cr in range(W):
            if d[r][cr] in (1, 2):  # trees
                c[r][cr] = 1
            elif d[r][cr] == 4:     # rocks
                c[r][cr] = 1
            elif d[r][cr] == 8:     # barrels
                c[r][cr] = 1
            elif d[r][cr] == 9:     # crates
                c[r][cr] = 1
            elif d[r][cr] == 6:     # chest
                c[r][cr] = 1
            elif d[r][cr] == 5:     # sign
                c[r][cr] = 1

    return c


def _build_exits():
    exits = {}
    # West edge → back to village (east side of village, near the road)
    for r in range(4, 9):
        exits[(0, r)] = {"map": "village", "spawn": (48, 16 + (r - 4))}
    # East edge → ruins_approach (fallback path to Stage 2)
    for r in range(22, 28):
        exits[(W - 1, r)] = {"map": "ruins_approach", "spawn": (2, 17)}
    return exits


DUNGEON = {
    "width": W,
    "height": H,
    "ground": _build_ground(),
    "decor": _build_decor(),
    "collision": _build_collision(),
    "spawns": {
        "player": (1, 6),
        "guard_npc": (17, 7),
    },
    "exits": _build_exits(),
    "chests": {
        (14, 22): {"item": "ancient_relic", "text": "Found the Ancient Relic! The Elder will want to see this."},
        (30, 24): {"item": "cave_key", "text": "Found a rusty Cave Key!"},
    },
    "signs": {
        (18, 7): "DANGER: Cave system ahead.\nOnly the brave should proceed.",
        (36, 22): "A weathered signpost:\n'The Haunted Ruins lie east.\nOnly those who have faced the Golem may pass.'",
    },
}
