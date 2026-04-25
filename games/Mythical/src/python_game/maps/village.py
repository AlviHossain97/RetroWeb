"""
Village map — the starting hub area.
50x36 tiles — a proper RPG village with river, bridge, market, garden, and exits.

Ground IDs:
  0=grass 1=dirt 2=stone 3=dark_grass 4=water 5=wood 6=stone_wall
  7=roof 8=door 9=hedge 10=sand 11=bridge 12=fence_h 13=fence_v
  14=cobble 15=grass_flower 16=deep_water 17=wood_wall

Decor IDs:
  0=none 1=oak_tree 2=pine_tree 3=red_flowers 4=rock 5=sign
  6=chest 7=well 8=barrel 9=crate 10=blue_flowers 11=lamp_post
  12=stall 13=bush 14=grave
"""

W, H = 50, 36


def _grid(w, h, val=0):
    return [[val] * w for _ in range(h)]


def _fill_rect(grid, x1, y1, x2, y2, val):
    for r in range(y1, y2 + 1):
        for c in range(x1, x2 + 1):
            if 0 <= r < len(grid) and 0 <= c < len(grid[0]):
                grid[r][c] = val


def _fill_border(grid, x1, y1, x2, y2, val):
    for c in range(x1, x2 + 1):
        if 0 <= y1 < len(grid) and 0 <= c < len(grid[0]):
            grid[y1][c] = val
        if 0 <= y2 < len(grid) and 0 <= c < len(grid[0]):
            grid[y2][c] = val
    for r in range(y1, y2 + 1):
        if 0 <= r < len(grid) and 0 <= x1 < len(grid[0]):
            grid[r][x1] = val
        if 0 <= r < len(grid) and 0 <= x2 < len(grid[0]):
            grid[r][x2] = val


def _build_ground():
    g = _grid(W, H, 0)

    # ── Grass variants ──
    for r in range(H):
        for c in range(W):
            if (c + r * 3) % 11 == 0:
                g[r][c] = 3
            elif (c * 7 + r * 5) % 23 == 0:
                g[r][c] = 15

    # ── Border hedge ──
    _fill_rect(g, 0, 0, W - 1, 0, 9)
    _fill_rect(g, 0, H - 1, W - 1, H - 1, 9)
    _fill_rect(g, 0, 0, 0, H - 1, 9)
    _fill_rect(g, W - 1, 0, W - 1, H - 1, 9)

    # ── East exit gap (to dungeon) ──
    for r in range(16, 20):
        g[r][W - 1] = 1

    # ── River (north-south, east side) ──
    for r in range(H):
        meander = 0 if r < 5 else (1 if 10 <= r <= 20 else (-1 if r > 28 else 0))
        for c in range(36 + meander, 39 + meander):
            if 0 < r < H - 1 and 0 < c < W - 1:
                g[r][c] = 4
        dc = 37 + meander
        if 0 < r < H - 1 and 0 < dc < W - 1:
            g[r][dc] = 16

    # ── Bridge ──
    for c in range(35, 41):
        g[17][c] = 11
        g[18][c] = 11

    # ── Main road (east-west) ──
    for c in range(1, W - 1):
        g[17][c] = 1
        g[18][c] = 1

    # ── North-south path ──
    for r in range(6, 28):
        g[r][15] = 1
        g[r][16] = 1

    # ── Cobblestone village square ──
    _fill_rect(g, 10, 20, 22, 27, 14)

    # ── Market stall area ──
    _fill_rect(g, 24, 20, 30, 25, 14)

    # ── Sand near river ──
    for r in range(14, 22):
        for c in range(33, 36):
            if g[r][c] == 0 or g[r][c] == 3:
                g[r][c] = 10

    # ── HOUSE 1: Elder's house ──
    _fill_border(g, 5, 5, 12, 10, 6)
    _fill_rect(g, 6, 6, 11, 9, 5)
    _fill_rect(g, 5, 4, 12, 4, 7)
    g[10][8] = 8
    g[10][9] = 8

    # ── HOUSE 2: Merchant's shop ──
    _fill_border(g, 20, 6, 28, 11, 17)
    _fill_rect(g, 21, 7, 27, 10, 5)
    _fill_rect(g, 20, 5, 28, 5, 7)
    g[11][23] = 8
    g[11][24] = 8

    # ── HOUSE 3: Cottage ──
    _fill_border(g, 3, 28, 9, 33, 6)
    _fill_rect(g, 4, 29, 8, 32, 5)
    _fill_rect(g, 3, 27, 9, 27, 7)
    g[28][6] = 8

    # ── Garden ──
    for c in range(10, 23):
        g[28][c] = 12
        g[33][c] = 12
    for r in range(28, 34):
        g[r][10] = 13
        g[r][22] = 13
    _fill_rect(g, 11, 29, 21, 32, 15)
    _fill_rect(g, 15, 29, 16, 32, 1)
    g[28][15] = 1
    g[28][16] = 1

    # ── South path + exit ──
    for r in range(27, H - 1):
        g[r][15] = 1
        g[r][16] = 1
    g[H - 1][15] = 1
    g[H - 1][16] = 1

    return g


def _build_decor():
    d = _grid(W, H, 0)

    oak_spots = [
        (3, 2), (3, 18), (3, 25), (3, 32), (3, 42), (3, 45),
        (7, 30), (7, 33), (12, 2), (12, 4), (12, 30), (12, 42),
        (14, 44), (14, 46), (20, 2), (20, 4),
        (25, 32), (25, 42), (25, 45),
        (30, 25), (30, 32), (30, 42),
        (33, 2), (33, 4), (33, 18), (33, 42), (33, 45),
    ]
    for r, c in oak_spots:
        if 0 < r < H - 1 and 0 < c < W - 1:
            d[r][c] = 1

    pine_spots = [
        (2, 43), (5, 44), (8, 43), (10, 45),
        (26, 44), (28, 43), (31, 45), (34, 44),
    ]
    for r, c in pine_spots:
        if 0 < r < H - 1 and 0 < c < W - 1:
            d[r][c] = 2

    d[23][16] = 7   # well
    d[21][25] = 12  # stalls
    d[21][28] = 12
    d[24][25] = 12
    d[12][20] = 8   # barrels/crates
    d[12][28] = 8
    d[11][20] = 9
    d[7][13] = 9
    d[7][14] = 8
    d[16][14] = 5   # sign
    d[16][10] = 11  # lamp posts
    d[16][20] = 11
    d[16][25] = 11
    d[16][30] = 11
    d[19][10] = 11
    d[19][20] = 11
    d[31][20] = 6   # chest
    d[29][12] = 3   # flowers
    d[29][14] = 10
    d[29][18] = 3
    d[29][20] = 10
    d[31][12] = 10
    d[31][14] = 3
    d[31][18] = 10
    d[11][5] = 13   # bushes
    d[11][12] = 13
    d[12][23] = 13
    d[34][3] = 13
    d[34][9] = 13
    d[15][34] = 4   # rocks
    d[20][34] = 4
    d[22][35] = 4
    d[8][41] = 14   # graves
    d[8][43] = 14
    d[10][41] = 14
    d[10][43] = 14

    return d


def _build_collision():
    c = _grid(W, H, 0)

    for col in range(W):
        c[0][col] = 1
        c[H - 1][col] = 1
    for row in range(H):
        c[row][0] = 1
        c[row][W - 1] = 1

    # Exit gaps
    for r in range(16, 20):
        c[r][W - 1] = 0
    c[H - 1][15] = 0
    c[H - 1][16] = 0

    # River
    for r in range(H):
        meander = 0 if r < 5 else (1 if 10 <= r <= 20 else (-1 if r > 28 else 0))
        for col in range(36 + meander, 39 + meander):
            if 0 < r < H - 1 and 0 < col < W - 1:
                c[r][col] = 1
    for col in range(35, 41):
        c[17][col] = 0
        c[18][col] = 0

    # House 1
    _fill_border(c, 5, 5, 12, 10, 1)
    _fill_rect(c, 6, 6, 11, 9, 0)
    c[10][8] = 0
    c[10][9] = 0
    for col in range(5, 13):
        c[4][col] = 1

    # House 2
    _fill_border(c, 20, 6, 28, 11, 1)
    _fill_rect(c, 21, 7, 27, 10, 0)
    c[11][23] = 0
    c[11][24] = 0
    for col in range(20, 29):
        c[5][col] = 1

    # House 3
    _fill_border(c, 3, 28, 9, 33, 1)
    _fill_rect(c, 4, 29, 8, 32, 0)
    c[28][6] = 0
    for col in range(3, 10):
        c[27][col] = 1

    # Garden fences
    for col in range(10, 23):
        c[28][col] = 1
        c[33][col] = 1
    for row in range(28, 34):
        c[row][10] = 1
        c[row][22] = 1
    c[28][15] = 0
    c[28][16] = 0

    # Trees
    all_trees = [
        (3, 2), (3, 18), (3, 25), (3, 32), (3, 42), (3, 45),
        (7, 30), (7, 33), (12, 2), (12, 4), (12, 30), (12, 42),
        (14, 44), (14, 46), (20, 2), (20, 4),
        (25, 32), (25, 42), (25, 45),
        (30, 25), (30, 32), (30, 42),
        (33, 2), (33, 4), (33, 18), (33, 42), (33, 45),
        (2, 43), (5, 44), (8, 43), (10, 45),
        (26, 44), (28, 43), (31, 45), (34, 44),
    ]
    for r, col in all_trees:
        if 0 < r < H - 1 and 0 < col < W - 1:
            c[r][col] = 1

    # Decoration solids
    solid_decor = [
        (23, 16), (16, 14), (15, 34), (20, 34), (22, 35),
        (12, 20), (12, 28), (11, 20), (7, 13), (7, 14), (31, 20),
        (21, 25), (21, 28), (24, 25),
        (11, 5), (11, 12), (12, 23), (34, 3), (34, 9),
        (8, 41), (8, 43), (10, 41), (10, 43),
    ]
    for r, col in solid_decor:
        if 0 < r < H - 1 and 0 < col < W - 1:
            c[r][col] = 1

    return c


# ── Build exits ──
def _build_exits():
    exits = {}
    # East edge → dungeon entrance
    for r in range(16, 20):
        exits[(W - 1, r)] = {"map": "dungeon", "spawn": (1, 5 + (r - 16))}
    return exits


VILLAGE = {
    "width": W,
    "height": H,
    "ground": _build_ground(),
    "decor": _build_decor(),
    "collision": _build_collision(),
    "spawns": {
        "player": (15, 19),
        "elder_npc": (8, 12),
        "shop_npc": (24, 12),
        "garden_npc": (16, 30),
        "healer_npc": (32, 14),
    },
    "exits": _build_exits(),
    "chests": {
        (20, 31): {"item": "supply_pack", "text": "Found a Supply Pack! Should be useful on the road."},
    },
    "signs": {
        (14, 16): "Village of Thornhollow\nEast road leads to the Dark Forest.\nTravel with caution.",
    },
}
