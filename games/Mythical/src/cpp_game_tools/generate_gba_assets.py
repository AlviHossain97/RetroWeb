#!/usr/bin/env python3
"""
generate_gba_assets.py — Convert Mythical Python graphics to GBA C arrays.

Generates:
  gba_src/generated/gba_assets.h  — extern declarations + constants
  gba_src/generated/gba_assets.c  — actual data arrays

BG tile output:
  gba_tile_pal[256]    : 16 palette banks × 16 colors (one bank per tile type)
  gba_tile_gfx[8192]   : 16 tile types × 16 HW tiles × 32 bytes (4bpp)

Player sprite output:
  gba_player_pal[16]   : OBJ palette bank 0 (shared across all 16 player frames)
  gba_player_gfx[2048] : 16 frames (4 dirs × 4 frames) × 4 HW tiles × 32 bytes

Run from Mythical project root:
    python tools/generate_gba_assets.py

Requires: pygame  (pip install pygame)
"""

import math
import os
import random
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, ROOT_DIR)

import pygame
pygame.init()
# Headless display — we only need the drawing APIs, not a window
_dummy = pygame.display.set_mode((1, 1), pygame.NOFRAME)

from tilemap import TILE_DEFS, _darken, _lighten, _vary

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
GEN_DIR    = os.path.join(ROOT_DIR, "gba_src", "generated")
OUT_H      = os.path.join(GEN_DIR, "gba_assets.h")
OUT_C      = os.path.join(GEN_DIR, "gba_assets.c")
PLAYER_DIR = os.path.join(ROOT_DIR, "assets", "compiled", "player")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TILE_SIZE        = 32          # 32×32 pixels per game tile
T                = TILE_SIZE
NUM_TILE_TYPES   = 16          # matches tilemap.h NUM_TILE_TYPES
TILE_BAKE_SEED   = 42          # deterministic per-tile noise seed

# Player sprites: FACE_DOWN=0, FACE_UP=1, FACE_LEFT=2, FACE_RIGHT=3
PLAYER_DIRS      = ["down", "up", "left", "right"]
PLAYER_FPDIR     = 4           # frames per direction
NUM_PLAYER_FRAME = 16          # 4 dirs × 4 frames
PLAYER_SPR_SIZE  = 16          # 16×16 OAM sprite (scaled from 32×32 PNG)
PLAYER_HW_TILES  = 4           # 2×2 GBA tiles per 16×16 frame

# OBJ VRAM tile layout
OAM_PLAYER_BASE  = 0           # tiles 0..63: player frames
OAM_ENEMY_BASE   = 64          # tiles 64..67: enemy 16×16 solid fill
OAM_BOSS_BASE    = 68          # tiles 68..83: boss 32×32 solid fill


# ===========================================================================
# Colour utilities
# ===========================================================================

def rgb_to_bgr15(r: int, g: int, b: int) -> int:
    """RGB888 → GBA BGR555 (u16)."""
    return ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)


# ===========================================================================
# Quantisation
# ===========================================================================

def quantize_surface(surf: pygame.Surface, max_colors: int = 15,
                     has_alpha: bool = True):
    """
    Reduce a pygame Surface to at most *max_colors* palette entries.
    Palette index 0 is reserved for transparency.

    Returns
    -------
    palette_rgb : list[(r,g,b)]   up to max_colors entries
    pixel_idx   : list[int]       flat row-major palette indices (0=transparent)
    """
    w, h = surf.get_size()
    freq: dict[tuple, int] = {}
    for py in range(h):
        for px in range(w):
            c = surf.get_at((px, py))
            if has_alpha and c[3] < 128:
                continue
            key = (c[0], c[1], c[2])
            freq[key] = freq.get(key, 0) + 1

    palette = sorted(freq, key=lambda k: -freq[k])[:max_colors]

    def nearest(r: int, g: int, b: int) -> int:
        bi, bd = 0, float("inf")
        for i, (pr, pg, pb) in enumerate(palette):
            d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
            if d < bd:
                bd, bi = d, i
        return bi + 1  # 1-based; index 0 = transparent

    indices: list[int] = []
    for py in range(h):
        for px in range(w):
            c = surf.get_at((px, py))
            if has_alpha and c[3] < 128:
                indices.append(0)
            else:
                indices.append(nearest(c[0], c[1], c[2]))

    return palette, indices


def indices_to_4bpp(indices: list[int], surf_w: int, surf_h: int) -> bytes:
    """
    Convert flat row-major palette-index list to GBA 4bpp tile data.

    Tiles are enumerated left→right, top→bottom.
    Each 8×8 tile = 32 bytes; byte at row py, col pair px//2:
        bits 3:0 = index of pixel at (px even, py)
        bits 7:4 = index of pixel at (px odd,  py)
    """
    tiles_x = surf_w // 8
    tiles_y = surf_h // 8
    buf = bytearray()
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            for py in range(8):
                for px in range(0, 8, 2):
                    x0 = tx * 8 + px
                    x1 = tx * 8 + px + 1
                    y  = ty * 8 + py
                    i0 = indices[y * surf_w + x0]
                    i1 = indices[y * surf_w + x1]
                    buf.append((i1 << 4) | i0)
    return bytes(buf)


# ===========================================================================
# Tile rendering  (faithfully replicates tilemap.py _bake inner loop)
# ===========================================================================

def _render_tile(tile_id: int) -> pygame.Surface:
    """
    Render one 32×32 game tile using the same procedural drawing code
    as the Python tilemap's _bake() method.

    tile_id : Python TILE_DEFS key (0-17).
    Returns : opaque 32×32 pygame.Surface.
    """
    random.seed(TILE_BAKE_SEED + tile_id * 31337)

    surf = pygame.Surface((T, T))
    tdef = TILE_DEFS.get(tile_id, TILE_DEFS[2])   # fallback: stone_floor
    base   = tdef["base"]
    detail = tdef.get("detail")

    x = y = 0
    col = row = 0   # map position used by water ripple; fixed at (0,0) for single tile
    rect = pygame.Rect(0, 0, T, T)

    # Base fill with slight variation
    pygame.draw.rect(surf, _vary(base, 10), rect)

    # ------------------------------------------------------------------
    # Detail rendering — exact copy of tilemap.py _bake() inner blocks
    # ------------------------------------------------------------------
    if detail == "grass":
        shade1 = _vary(_darken(base, 8),  8)
        shade2 = _vary(_lighten(base, 18), 10)
        shade3 = _vary(_lighten(base, 10), 6)
        for _ in range(5):
            pygame.draw.circle(surf, _vary(shade1, 5),
                               (x + random.randint(0, T-1), y + random.randint(0, T-1)), 2)
        for _ in range(6):
            gx = x + random.randint(3, T-3)
            gy = y + random.randint(4, T-2)
            gc = shade2 if random.random() > 0.4 else shade3
            h  = random.randint(3, 6)
            lean = random.randint(-1, 1)
            pygame.draw.line(surf, gc, (gx, gy), (gx+lean, gy-h), 1)
        if random.random() < 0.18:
            pygame.draw.circle(surf, _darken(base, 30),
                               (x + random.randint(5, T-5), y + random.randint(5, T-5)), 1)

    elif detail == "dirt":
        for _ in range(4):
            dx2 = x + random.randint(3, T-3)
            dy2 = y + random.randint(3, T-3)
            pygame.draw.circle(surf, _vary(_darken(base, 15), 8),
                               (dx2, dy2), random.randint(1, 2))
        if random.random() < 0.25:
            cx2 = x + random.randint(4, T-8)
            cy2 = y + random.randint(4, T-8)
            pygame.draw.line(surf, _darken(base, 25), (cx2, cy2),
                             (cx2+random.randint(3, 6), cy2+random.randint(1, 4)), 1)

    elif detail == "stone":
        lc  = _darken(base, 20)
        ltc = _lighten(base, 12)
        mx2 = x + T // 2
        my2 = y + T // 2
        pygame.draw.line(surf, lc, (x, my2), (x+T, my2), 1)
        pygame.draw.line(surf, lc, (mx2, y), (mx2, y+T), 1)
        pygame.draw.line(surf, ltc, (x+2, my2-1), (mx2-2, my2-1), 1)
        pygame.draw.line(surf, ltc, (mx2+2, my2-1), (x+T-2, my2-1), 1)
        for cx2, cy2 in ((x+3, y+3), (x+T-4, y+3), (x+3, y+T-4), (x+T-4, y+T-4)):
            pygame.draw.circle(surf, _lighten(base, 8), (cx2, cy2), 1)

    elif detail == "water":
        deep = _darken(base, 18)
        for wy in range(y+2, y+T, 6):
            pygame.draw.line(surf, _vary(deep, 5), (x, wy), (x+T, wy), 1)
        wc = _lighten(base, 30)
        w1 = y + (col * 4 + row * 9) % T
        pygame.draw.line(surf, wc, (x+5, w1%T+y), (x+T-5, (w1+3)%T+y), 1)
        w2 = y + (col * 7 + row * 5 + T//3) % T
        pygame.draw.line(surf, _vary(wc, 12), (x+3, w2%T+y), (x+T//2-2, (w2+2)%T+y), 1)
        if random.random() < 0.3:
            pygame.draw.circle(surf, (180, 210, 255),
                               (x+random.randint(4, T-4), y+random.randint(4, T-4)), 1)

    elif detail == "wood":
        lc  = _darken(base, 18)
        ltc = _lighten(base, 8)
        for wy in range(y+5, y+T, 7):
            pygame.draw.line(surf, lc,  (x+1, wy),   (x+T-1, wy),   1)
            pygame.draw.line(surf, ltc, (x+1, wy-1),  (x+T-1, wy-1), 1)
        for _ in range(2):
            gx2 = x + random.randint(3, T-3)
            gy2 = y + random.randint(3, T-8)
            pygame.draw.line(surf, _darken(base, 10), (gx2, gy2),
                             (gx2+random.randint(-1, 1), gy2+4), 1)

    elif detail == "brick":
        lc    = _darken(base, 25)
        ltc   = _lighten(base, 10)
        row_h = T // 3
        for by2 in range(y+row_h, y+T, row_h):
            pygame.draw.line(surf, lc, (x, by2), (x+T, by2), 1)
        bx2 = x + (T // 2) % T
        pygame.draw.line(surf, lc, (bx2, y), (bx2, y+T), 1)
        for br in range(3):
            ry = y + br * row_h + 2
            pygame.draw.line(surf, ltc, (x+2, ry), (x+T-2, ry), 1)

    elif detail == "roof":
        lc  = _darken(base, 22)
        ltc = _lighten(base, 8)
        for i in range(0, T*2, 7):
            pygame.draw.line(surf, lc,  (x+i, y), (x+i-T, y+T), 1)
            pygame.draw.line(surf, ltc, (x+i+1, y), (x+i-T+1, y+T), 1)
        for ry in range(y+T//4, y+T, T//4):
            pygame.draw.line(surf, lc, (x, ry), (x+T, ry), 1)

    elif detail == "door":
        dc  = _darken(base, 35)
        ltc = _lighten(base, 15)
        pygame.draw.rect(surf, dc, (x+2, y+1, T-4, T-1), 2)
        pygame.draw.rect(surf, _darken(base, 18), (x+5, y+4, T-10, T//2-2))
        pygame.draw.rect(surf, _darken(base, 18), (x+5, y+T//2+2, T-10, T//2-6))
        pygame.draw.line(surf, ltc, (x+5, y+4), (x+T-6, y+4), 1)
        pygame.draw.line(surf, ltc, (x+5, y+T//2+2), (x+T-6, y+T//2+2), 1)
        pygame.draw.circle(surf, (205, 182, 55), (x+T-7, y+T//2), 3)
        pygame.draw.circle(surf, (160, 138, 30), (x+T-7, y+T//2), 3, 1)

    elif detail == "hedge":
        for _ in range(8):
            hx2 = x + random.randint(2, T-2)
            hy2 = y + random.randint(2, T-2)
            pygame.draw.circle(surf, _vary(_lighten(base, random.randint(5, 20)), 8),
                               (hx2, hy2), random.randint(3, 6))
        for _ in range(3):
            pygame.draw.circle(surf, _darken(base, 20),
                               (x+random.randint(3, T-3), y+random.randint(3, T-3)), 2)

    elif detail == "bridge":
        lc  = _darken(base, 22)
        ltc = _lighten(base, 10)
        for bx_off in range(3, T, 8):
            pygame.draw.line(surf, lc,  (x+bx_off,   y+2), (x+bx_off,   y+T-2), 1)
            pygame.draw.line(surf, ltc, (x+bx_off+1, y+2), (x+bx_off+1, y+T-2), 1)
        for bx_off in range(5, T-3, 8):
            pygame.draw.circle(surf, _darken(base, 40), (x+bx_off, y+5),   1)
            pygame.draw.circle(surf, _darken(base, 40), (x+bx_off, y+T-5), 1)
        pygame.draw.line(surf, _darken(base, 45), (x, y+2),   (x+T, y+2),   2)
        pygame.draw.line(surf, _darken(base, 45), (x, y+T-3), (x+T, y+T-3), 2)
        pygame.draw.line(surf, ltc,               (x, y+1),   (x+T, y+1),   1)

    elif detail == "fence_h":
        bg2 = TILE_DEFS[0]["base"]
        pygame.draw.rect(surf, _vary(bg2, 6), rect)
        ltc = _lighten(base, 15)
        pygame.draw.rect(surf, base, (x, y+T//2-2, T, 4))
        pygame.draw.line(surf, ltc, (x, y+T//2-2), (x+T, y+T//2-2), 1)
        for fx in range(x+4, x+T, T//3):
            pygame.draw.rect(surf, _darken(base, 15), (fx, y+T//4, 4, T//2))
            pygame.draw.line(surf, ltc, (fx, y+T//4), (fx, y+T*3//4), 1)

    elif detail == "fence_v":
        bg2 = TILE_DEFS[0]["base"]
        pygame.draw.rect(surf, _vary(bg2, 6), rect)
        ltc = _lighten(base, 15)
        pygame.draw.rect(surf, base, (x+T//2-2, y, 4, T))
        pygame.draw.line(surf, ltc, (x+T//2-2, y), (x+T//2-2, y+T), 1)
        for fy in range(y+4, y+T, T//3):
            pygame.draw.rect(surf, _darken(base, 15), (x+T//4, fy, T//2, 4))
            pygame.draw.line(surf, ltc, (x+T//4, fy), (x+T*3//4, fy), 1)

    elif detail == "cobble":
        lc = _darken(base, 18)
        for _ in range(5):
            cx2 = x + random.randint(4, T-4)
            cy2 = y + random.randint(4, T-4)
            cr2 = random.randint(3, 6)
            sc  = _vary(_lighten(base, 12), 8)
            pygame.draw.circle(surf, sc,                    (cx2, cy2),   cr2)
            pygame.draw.circle(surf, lc,                    (cx2, cy2),   cr2, 1)
            pygame.draw.circle(surf, _lighten(base, 25),    (cx2-1, cy2-1), max(1, cr2//3))

    elif detail == "flowers":
        shade2 = _vary(_lighten(base, 18), 10)
        for _ in range(6):
            gx2  = x + random.randint(3, T-3)
            gy2  = y + random.randint(4, T-2)
            fh   = random.randint(3, 6)
            lean = random.randint(-1, 1)
            pygame.draw.line(surf, shade2, (gx2, gy2), (gx2+lean, gy2-fh), 1)
        for _ in range(3):
            fx2 = x + random.randint(5, T-5)
            fy2 = y + random.randint(5, T-5)
            fc2 = random.choice([
                (215, 55, 55), (55, 55, 210),
                (225, 205, 45), (205, 95, 185), (255, 155, 55)])
            pygame.draw.circle(surf, fc2, (fx2, fy2), 2)
            for ang in range(0, 360, 90):
                ppx = fx2 + int(2 * math.cos(math.radians(ang)))
                ppy = fy2 + int(2 * math.sin(math.radians(ang)))
                pygame.draw.circle(surf, fc2, (ppx, ppy), 1)

    # Subtle vignette: darken the 2-pixel border to match Python version
    for bx in range(T):
        for by in range(T):
            if bx < 2 or bx >= T-2 or by < 2 or by >= T-2:
                c = surf.get_at((bx, by))
                surf.set_at((bx, by),
                            (max(0, c[0]-18), max(0, c[1]-18), max(0, c[2]-18)))

    return surf


# ===========================================================================
# Player sprite loading
# ===========================================================================

def _load_player_frame(direction: str, frame: int) -> pygame.Surface:
    """Load a player PNG and scale to PLAYER_SPR_SIZE × PLAYER_SPR_SIZE."""
    path = os.path.join(PLAYER_DIR, f"{direction}_{frame}.png")
    if not os.path.exists(path):
        # Magenta fallback so missing assets are obvious
        surf = pygame.Surface((PLAYER_SPR_SIZE, PLAYER_SPR_SIZE), pygame.SRCALPHA)
        surf.fill((255, 0, 255, 255))
        return surf
    img = pygame.image.load(path).convert_alpha()
    return pygame.transform.scale(img, (PLAYER_SPR_SIZE, PLAYER_SPR_SIZE))


# ===========================================================================
# C file generation
# ===========================================================================

def _fmt_u8_array(name: str, data: bytes, comment: str = "") -> str:
    lines = []
    if comment:
        lines.append(f"/* {comment} */\n")
    lines.append(f"const u8 {name}[{len(data)}] = {{\n")
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        lines.append("    " + ", ".join(f"0x{b:02X}" for b in chunk) + ",\n")
    lines.append("};\n")
    return "".join(lines)


def _fmt_u16_array(name: str, data: list, comment: str = "") -> str:
    lines = []
    if comment:
        lines.append(f"/* {comment} */\n")
    lines.append(f"const u16 {name}[{len(data)}] = {{\n")
    for i in range(0, len(data), 8):
        chunk = data[i:i+8]
        lines.append("    " + ", ".join(f"0x{v:04X}" for v in chunk) + ",\n")
    lines.append("};\n")
    return "".join(lines)


def write_header(out_h: str) -> None:
    with open(out_h, "w") as f:
        f.write("/* gba_assets.h - auto-generated by tools/generate_gba_assets.py */\n")
        f.write("/* DO NOT EDIT MANUALLY - regenerate with: python tools/generate_gba_assets.py */\n\n")
        f.write("#ifndef GBA_ASSETS_H\n#define GBA_ASSETS_H\n\n")
        f.write('#include "gba.h"\n\n')
        f.write("/* ---------------------------------------------------------------\n")
        f.write(" * BG tile constants\n")
        f.write(" * ------------------------------------------------------------- */\n")
        f.write(f"#define GBA_NUM_TILE_TYPES       {NUM_TILE_TYPES}\n")
        f.write(f"#define GBA_HW_TILES_PER_GTILE   16   /* 4x4 GBA tiles per 32x32 game tile */\n")
        f.write(f"#define GBA_TILE_GFX_BYTES        8192 /* {NUM_TILE_TYPES} types x 16 tiles x 32 bytes */\n\n")
        f.write("/* BG palette: 16 banks x 16 colors; bank N = tile type N */\n")
        f.write("extern const u16 gba_tile_pal[256];\n\n")
        f.write("/* BG tile graphics (4bpp): tile type N starts at byte N*512 */\n")
        f.write("extern const u8  gba_tile_gfx[8192];\n\n")
        f.write("/* ---------------------------------------------------------------\n")
        f.write(" * Player sprite constants\n")
        f.write(" * ------------------------------------------------------------- */\n")
        f.write(f"#define GBA_PLAYER_FRAMES          {NUM_PLAYER_FRAME}\n")
        f.write(f"#define GBA_PLAYER_TILES_PER_FRAME {PLAYER_HW_TILES}\n")
        f.write(f"#define GBA_PLAYER_GFX_BYTES       2048 /* 16 frames x 4 tiles x 32 bytes */\n\n")
        f.write("/* OBJ VRAM tile layout:\n")
        f.write(" *   Tiles   0-63 : player (16 frames x 4 tiles; tile = (dir*4+frame)*4)\n")
        f.write(" *   Tiles  64-67 : enemy 16x16 solid fill\n")
        f.write(" *   Tiles  68-83 : boss  32x32 solid fill\n")
        f.write(" */\n")
        f.write(f"#define OAM_TILE_PLAYER_BASE  0\n")
        f.write(f"#define OAM_TILE_ENEMY        64\n")
        f.write(f"#define OAM_TILE_BOSS         68\n\n")
        f.write("/* Inline helper: tile index for player facing+frame */\n")
        f.write("static inline u8 oam_player_tile(u8 facing, u8 anim_frame) {\n")
        f.write("    return (u8)((facing * 4u + anim_frame) * 4u);\n")
        f.write("}\n\n")
        f.write("/* Player OBJ palette bank 0 (16 colors; index 0 = transparent) */\n")
        f.write("extern const u16 gba_player_pal[16];\n\n")
        f.write("/* Player sprites (4bpp): frame F starts at byte F*128 */\n")
        f.write("extern const u8  gba_player_gfx[2048];\n\n")
        f.write("#endif /* GBA_ASSETS_H */\n")


def write_source(out_c: str,
                 tile_pal: list, tile_gfx: bytes,
                 player_pal: list, player_gfx: bytes) -> None:
    with open(out_c, "w") as f:
        f.write("/* gba_assets.c - auto-generated by tools/generate_gba_assets.py */\n")
        f.write("/* DO NOT EDIT MANUALLY - regenerate with: python tools/generate_gba_assets.py */\n\n")
        f.write('#include "gba_assets.h"\n\n')
        f.write(_fmt_u16_array("gba_tile_pal", tile_pal,
                               "BG palette: 16 banks x 16 colors. Bank N = tile type N."))
        f.write("\n")
        f.write(_fmt_u8_array("gba_tile_gfx", tile_gfx,
                              "BG tile graphics (4bpp). Tile type N: bytes [N*512, N*512+511]."))
        f.write("\n")
        f.write(_fmt_u16_array("gba_player_pal", player_pal,
                               "Player OBJ palette bank 0. Index 0 = transparent."))
        f.write("\n")
        f.write(_fmt_u8_array("gba_player_gfx", player_gfx,
                              "Player sprites (4bpp). Frame F: bytes [F*128, F*128+127]."))


# ===========================================================================
# Main
# ===========================================================================

def main() -> None:
    print("=== Mythical GBA Asset Generator ===")
    os.makedirs(GEN_DIR, exist_ok=True)

    # ── BG tiles ────────────────────────────────────────────────────────────
    print("\n[1/2] Rendering BG tile textures…")
    tile_pal: list[int] = []
    tile_gfx = bytearray()

    for tid in range(NUM_TILE_TYPES):
        name = TILE_DEFS.get(tid, {}).get("name", "unknown")
        print(f"      tile {tid:2d}: {name}")

        surf = _render_tile(tid)

        # Quantise — no alpha for solid ground tiles
        pal_rgb, pix = quantize_surface(surf, max_colors=15, has_alpha=False)

        # Build palette bank: entry 0 = black (backdrop/transparent), 1-15 = tile colors
        bank = [0x0000]
        for r, g, b in pal_rgb:
            bank.append(rgb_to_bgr15(r, g, b))
        while len(bank) < 16:
            bank.append(0x0000)
        tile_pal.extend(bank)

        # Convert to 4bpp tile data: 32x32 → 16 HW tiles × 32 bytes = 512 bytes
        gfx = indices_to_4bpp(pix, T, T)
        assert len(gfx) == 512, f"tile {tid}: expected 512 bytes, got {len(gfx)}"
        tile_gfx.extend(gfx)

    assert len(tile_pal) == 256
    assert len(tile_gfx) == 8192
    print(f"      -> {NUM_TILE_TYPES} tiles, {len(tile_gfx)} bytes gfx, 256 palette entries")

    # ── Player sprites ───────────────────────────────────────────────────────
    print("\n[2/2] Loading player sprites…")
    frames: list[pygame.Surface] = []
    for direction in PLAYER_DIRS:
        for fi in range(PLAYER_FPDIR):
            surf = _load_player_frame(direction, fi)
            frames.append(surf)
            print(f"      {direction}_{fi}.png  ({surf.get_width()}×{surf.get_height()})")

    # Build a shared palette from all frames combined
    all_colors: dict[tuple, int] = {}
    for surf in frames:
        for py in range(surf.get_height()):
            for px in range(surf.get_width()):
                c = surf.get_at((px, py))
                if c[3] >= 128:
                    key = (c[0], c[1], c[2])
                    all_colors[key] = all_colors.get(key, 0) + 1

    shared_pal = sorted(all_colors, key=lambda k: -all_colors[k])[:15]

    def player_nearest(r: int, g: int, b: int) -> int:
        bi, bd = 0, float("inf")
        for i, (pr, pg, pb) in enumerate(shared_pal):
            d = (r-pr)**2 + (g-pg)**2 + (b-pb)**2
            if d < bd:
                bd, bi = d, i
        return bi + 1

    player_pal = [0x0000]   # index 0 = transparent
    for r, g, b in shared_pal:
        player_pal.append(rgb_to_bgr15(r, g, b))
    while len(player_pal) < 16:
        player_pal.append(0x0000)

    player_gfx = bytearray()
    for surf in frames:
        w, h = surf.get_size()
        pix: list[int] = []
        for py in range(h):
            for px in range(w):
                c = surf.get_at((px, py))
                if c[3] < 128:
                    pix.append(0)
                else:
                    pix.append(player_nearest(c[0], c[1], c[2]))
        gfx = indices_to_4bpp(pix, w, h)
        # Each 16x16 frame = 4 tiles × 32 bytes = 128 bytes
        assert len(gfx) == 128, f"player frame: expected 128 bytes, got {len(gfx)}"
        player_gfx.extend(gfx)

    assert len(player_gfx) == 2048
    print(f"      -> {len(frames)} frames, {len(player_gfx)} bytes gfx")

    # ── Write output ─────────────────────────────────────────────────────────
    print(f"\nWriting {OUT_H} …")
    write_header(OUT_H)
    print(f"Writing {OUT_C} …")
    write_source(OUT_C, tile_pal, bytes(tile_gfx), player_pal, bytes(player_gfx))
    print("\nDone! Rebuild with: cd gba_src && make")


if __name__ == "__main__":
    main()
