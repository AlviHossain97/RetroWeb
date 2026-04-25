"""Convert project PNGs into Butano-ready 4bpp BMP + JSON sprite items.

Usage:
    python tools/convert_assets.py

Output layout (under gba_project/graphics/):
    characters.bmp + .json  — 5 characters in a vertical 16x16 strip
    towers.bmp     + .json  — 9 tower body frames in a vertical 16x16 strip
    terrain.bmp    + .json  — 8 terrain / base frames in a vertical 8x8 strip
    props.bmp      + .json  — 6 environmental props in a vertical 16x16 strip
    projectile.bmp + .json  — 8x8 single dot
    cursor.bmp     + .json  — 8x8 cursor frame

The mappings mirror the SDL/C++ sprite bake script so the GBA build uses the
same extracted art source set.
"""
from __future__ import annotations

import json
import os
import struct
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
EXTRACTED = ROOT / "assets" / "extracted"
OUT = ROOT / "gba_project" / "graphics"
OUT.mkdir(parents=True, exist_ok=True)


def pad_to(img: Image.Image, w: int, h: int, bg=(0, 0, 0, 0)) -> Image.Image:
    """Center-pad an RGBA image into a w x h canvas."""
    canvas = Image.new("RGBA", (w, h), bg)
    iw, ih = img.size
    scale = min(w / iw, h / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    resized = img.resize((nw, nh), Image.NEAREST)
    canvas.paste(resized, ((w - nw) // 2, (h - nh) // 2), resized)
    return canvas


def scale_to(img: Image.Image, w: int, h: int) -> Image.Image:
    """Nearest-neighbour scale to an exact tile size."""
    return img.convert("RGBA").resize((w, h), Image.NEAREST)


def terrain_tile(img: Image.Image, w: int = 8, h: int = 8, crop: float = 0.6) -> Image.Image:
    """Scale a repeating terrain source to a tile size while avoiding edge-bright
    bands that would show as horizontal seams between stacked tiles.

    Many source PNGs have lighter bezels on their outer rows/cols. Center-crop
    the inner ``crop`` fraction before downscaling with BOX averaging so each
    output row samples the same visual region of the source.
    """
    src = img.convert("RGBA")
    sw, sh = src.size
    cw = max(1, int(sw * crop))
    ch = max(1, int(sh * crop))
    ox = (sw - cw) // 2
    oy = (sh - ch) // 2
    cropped = src.crop((ox, oy, ox + cw, oy + ch))
    return cropped.resize((w, h), Image.BOX)


def tint(img: Image.Image, color: tuple[int, int, int], alpha: int = 80) -> Image.Image:
    """Apply the same simple colour overlay used by the desktop asset loader."""
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (*color, alpha))
    return Image.alpha_composite(base, overlay)


def stack_vertical(frames: list[Image.Image]) -> Image.Image:
    w = frames[0].width
    total = Image.new("RGBA", (w, frames[0].height * len(frames)), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        total.paste(f, (0, i * f.height), f)
    return total


def to_indexed(img: Image.Image, palette_size: int = 16, transparent=(255, 0, 255)) -> Image.Image:
    """Quantize to palette_size colours, ensuring index 0 is the transparent key."""
    rgba = img.convert("RGBA")
    pixels = rgba.load()
    transparent_mask: list[bool] = []
    fill_rgb: tuple[int, int, int] | None = None

    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = pixels[x, y]
            if a >= 128:
                fill_rgb = (r, g, b)
                break
        if fill_rgb is not None:
            break

    if fill_rgb is None:
        fill_rgb = (0, 0, 0)

    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = pixels[x, y]
            if a < 128:
                transparent_mask.append(True)
                pixels[x, y] = (*fill_rgb, 255)
            else:
                transparent_mask.append(False)
                pixels[x, y] = (r, g, b, 255)

    rgb = rgba.convert("RGB")
    quantized = rgb.quantize(colors=palette_size - 1, method=Image.MEDIANCUT, dither=Image.NONE)
    pal = quantized.getpalette()[: (palette_size - 1) * 3]
    new_pal = list(transparent) + pal
    new_pal += [0] * (768 - len(new_pal))
    data = list(quantized.getdata())
    shifted = bytes(0 if transparent_mask[i] else data[i] + 1 for i in range(len(data)))
    out = Image.frombytes("P", quantized.size, shifted)
    out.putpalette(new_pal)
    return out


def write_bmp(img: Image.Image, path: Path) -> None:
    img.save(path, format="BMP")


def write_json(path: Path, body: dict) -> None:
    path.write_text(json.dumps(body, indent=4))


def build_characters() -> None:
    frames = []
    for i in range(5):
        src = EXTRACTED / "characters" / f"char_{i}.png"
        frames.append(pad_to(Image.open(src), 16, 16))
    sheet = stack_vertical(frames)
    indexed = to_indexed(sheet, 16)
    write_bmp(indexed, OUT / "characters.bmp")
    write_json(OUT / "characters.json", {"type": "sprite", "height": 16})


def build_towers() -> None:
    frames = []
    # Rows 0,1,2 are tower types 0..2 (arrow, cannon, ice) with 3 levels each.
    # Lightning + Flame recolour at runtime via palette swap, so only three
    # source rows are needed for the base art.
    for row in range(3):
        for col in range(3):
            src = EXTRACTED / "towers" / f"tower_{row}_{col}.png"
            frames.append(pad_to(Image.open(src), 16, 16))
    sheet = stack_vertical(frames)
    indexed = to_indexed(sheet, 16)
    write_bmp(indexed, OUT / "towers.bmp")
    write_json(OUT / "towers.json", {"type": "sprite", "height": 16})


def solid_tile(color: tuple[int, int, int], size: int = 8) -> Image.Image:
    """Build a flat-color 8x8 tile. GBA reads these as uniform BG fills so
    stacked tiles blend seamlessly (no visible seams between cells)."""
    return Image.new("RGBA", (size, size), (*color, 255))


def build_terrain() -> None:
    """Flat-color terrain tiles.

    The shared renderer calls these as BG tiles and alternates a "grass" /
    "grass_alt" pair on a checkerboard. To match the design intent (solid
    green field with a distinct sand path through it), each pair uses the
    same colour so the checkerboard reads as a single flat zone rather than
    clashing textures.
    """
    grass_col = (58, 130, 58)       # solid mid-green
    grass_alt_col = (50, 118, 50)    # slightly darker for subtle variation
    path_col = (230, 180, 70)       # warm sandy yellow
    path_alt_col = (218, 168, 60)   # slightly darker sand
    water_col = (40, 90, 180)
    spawn_col = (190, 70, 70)
    base_col = (70, 90, 200)
    tower_base_col = (72, 148, 72)  # slightly lighter grass to hint buildable

    frames = [
        solid_tile(grass_col),
        solid_tile(grass_alt_col),
        solid_tile(path_col),
        solid_tile(path_alt_col),
        solid_tile(water_col),
        solid_tile(spawn_col),
        solid_tile(base_col),
        solid_tile(tower_base_col),
    ]
    sheet = stack_vertical(frames)
    indexed = to_indexed(sheet, 16)
    write_bmp(indexed, OUT / "terrain.bmp")
    write_json(OUT / "terrain.json", {"type": "sprite", "height": 8})


def build_props() -> None:
    sources = [
        EXTRACTED / "props" / "prop_0_0.png",
        EXTRACTED / "props" / "prop_1_0.png",
        EXTRACTED / "props" / "prop_2_0.png",
        EXTRACTED / "props" / "prop_4_0.png",
        EXTRACTED / "props" / "prop_4_1.png",
        EXTRACTED / "props" / "prop_5_1.png",
    ]
    frames = [pad_to(Image.open(path), 16, 16) for path in sources]
    sheet = stack_vertical(frames)
    indexed = to_indexed(sheet, 16)
    write_bmp(indexed, OUT / "props.bmp")
    write_json(OUT / "props.json", {"type": "sprite", "height": 16})


def build_cursor_and_dot() -> None:
    cursor = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    for i in range(8):
        cursor.putpixel((i, 0), (255, 255, 255, 255))
        cursor.putpixel((i, 7), (255, 255, 255, 255))
        cursor.putpixel((0, i), (255, 255, 255, 255))
        cursor.putpixel((7, i), (255, 255, 255, 255))
    write_bmp(to_indexed(cursor, 16), OUT / "cursor.bmp")
    write_json(OUT / "cursor.json", {"type": "sprite", "height": 8})

    dot = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    for y in range(2, 6):
        for x in range(2, 6):
            dot.putpixel((x, y), (255, 220, 80, 255))
    write_bmp(to_indexed(dot, 16), OUT / "projectile.bmp")
    write_json(OUT / "projectile.json", {"type": "sprite", "height": 8})


def build_effects() -> None:
    """Auxiliary sprites for HUD: HP bars, boss bar, level pips, slow marker, particles.

    Frames (each 8x8):
        0       HP bar bg (full 8x1 dark-red row on row 0, rest transparent)
        1..8    HP bar fg (dark-red bg + N green pixels overlay on row 0)
        9       Boss bar bg (dark-red 8x3 strip on rows 0..2)
        10      Boss bar fg (red/health 8x3 strip on rows 0..2)
        11      Level pip (1x1 white at bottom-left)
        12      Slow marker (6x6 blue centered)
        13      Particle white
        14      Particle gold
        15      Particle red
    """
    bar_bg = (90, 20, 20, 255)
    bar_fg = (80, 200, 120, 255)     # ACCENT
    boss_fg = (220, 50, 50, 255)     # HEALTH
    slow_c = (80, 140, 220, 255)
    pip_c = (240, 235, 220, 255)
    p_white = (240, 235, 220, 255)
    p_gold = (255, 210, 80, 255)
    p_red = (220, 80, 80, 255)

    frames = []

    # 0: HP bar bg
    f = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    for x in range(8):
        f.putpixel((x, 0), bar_bg)
    frames.append(f)

    # 1..8: HP bar fg (bg + N green)
    for n in range(1, 9):
        f = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        for x in range(8):
            f.putpixel((x, 0), bar_bg)
        for x in range(n):
            f.putpixel((x, 0), bar_fg)
        frames.append(f)

    # 9: Boss bar bg (3-tall dark red strip)
    f = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    for y in range(3):
        for x in range(8):
            f.putpixel((x, y), bar_bg)
    frames.append(f)

    # 10: Boss bar fg (3-tall health strip)
    f = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    for y in range(3):
        for x in range(8):
            f.putpixel((x, y), boss_fg)
    frames.append(f)

    # 11: Level pip (1x1 at bottom-left)
    f = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    f.putpixel((0, 7), pip_c)
    frames.append(f)

    # 12: Slow marker (6x6 blue centered)
    f = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    for y in range(1, 7):
        for x in range(1, 7):
            f.putpixel((x, y), slow_c)
    frames.append(f)

    # 13..15: particles (2x2 centered)
    for color in (p_white, p_gold, p_red):
        f = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        for y in range(3, 5):
            for x in range(3, 5):
                f.putpixel((x, y), color)
        frames.append(f)

    sheet = stack_vertical(frames)
    indexed = to_indexed(sheet, 16)
    write_bmp(indexed, OUT / "effects.bmp")
    write_json(OUT / "effects.json", {"type": "sprite", "height": 8})


def build_outline() -> None:
    """4-frame 8x8 sprite: top/bottom/left/right edge strokes for outline drawing."""
    c = (240, 235, 220, 255)
    frames = []

    # 0: top edge (row 0 fully drawn)
    f = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    for x in range(8):
        f.putpixel((x, 0), c)
    frames.append(f)

    # 1: bottom edge (row 7)
    f = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    for x in range(8):
        f.putpixel((x, 7), c)
    frames.append(f)

    # 2: left edge (col 0)
    f = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    for y in range(8):
        f.putpixel((0, y), c)
    frames.append(f)

    # 3: right edge (col 7)
    f = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    for y in range(8):
        f.putpixel((7, y), c)
    frames.append(f)

    sheet = stack_vertical(frames)
    indexed = to_indexed(sheet, 16)
    write_bmp(indexed, OUT / "outline.bmp")
    write_json(OUT / "outline.json", {"type": "sprite", "height": 8})


def build_range_dot() -> None:
    """8x8, 1 frame: small white dot for composing range-preview rings."""
    f = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    for y in range(3, 5):
        for x in range(3, 5):
            f.putpixel((x, y), (240, 235, 220, 255))
    write_bmp(to_indexed(f, 16), OUT / "range_dot.bmp")
    write_json(OUT / "range_dot.json", {"type": "sprite", "height": 8})


def build_hud_bg() -> None:
    """32x32 BG tileset: 2 frames (HUD_BG dark and TRAY_BG dark) + transparent frame.

    Used by the GBA renderer to paint the HUD and tower-tray backdrops.
    Exported as bg type so butano produces bg_item + tile data.
    """
    hud_col = (10, 10, 18, 255)
    tray_col = (15, 15, 25, 255)
    # 3 tile frames of 8x8, stacked into an 8x24 sheet typed as bg.
    frames = []
    # Transparent tile
    frames.append(Image.new("RGBA", (8, 8), (0, 0, 0, 0)))
    # HUD solid
    f = Image.new("RGBA", (8, 8), hud_col)
    frames.append(f)
    # TRAY solid
    f = Image.new("RGBA", (8, 8), tray_col)
    frames.append(f)
    sheet = stack_vertical(frames)
    indexed = to_indexed(sheet, 16)
    write_bmp(indexed, OUT / "hud_bg.bmp")
    write_json(OUT / "hud_bg.json", {"type": "sprite", "height": 8})


def main() -> None:
    build_characters()
    build_towers()
    build_terrain()
    build_props()
    build_cursor_and_dot()
    build_effects()
    build_outline()
    build_range_dot()
    build_hud_bg()
    print("butano assets written to", OUT)


if __name__ == "__main__":
    main()
