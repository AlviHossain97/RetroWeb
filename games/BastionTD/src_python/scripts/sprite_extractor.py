#!/usr/bin/env python3
"""
sprite_extractor.py — Production-grade spritesheet slicer for BastionTD.

Extracts individual sprites from spritesheets using either manual grid
dimensions or automatic boundary detection via alpha-channel analysis.

Usage:
    # Grid mode — you know the layout
    python sprite_extractor.py assets/towers.png --rows 3 --cols 3

    # Auto-detect mode — let the tool find sprites
    python sprite_extractor.py assets/props.png --auto

    # Custom output directory and naming
    python sprite_extractor.py assets/tileset1.png --rows 14 --cols 27 \\
        --output extracted/tiles --name "tile_{row}_{col}"

    # As a library
    from sprite_extractor import SpriteExtractor, ExtractionConfig
    ext = SpriteExtractor()
    result = ext.extract("sheet.png", ExtractionConfig(mode="auto"))

Requires: Pillow (pip install Pillow)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from PIL import Image
except ImportError:
    sys.exit(
        "Pillow is required.  Install with:  pip install Pillow\n"
        "  (pygame.image cannot write individual PNGs with alpha easily)"
    )

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FMT = "[%(levelname)s] %(message)s"
logging.basicConfig(format=LOG_FMT, level=logging.INFO)
log = logging.getLogger("sprite_extractor")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class ExtractionConfig:
    """Controls how sprites are extracted from a sheet.

    Attributes:
        mode:               "grid" for manual rows/cols, "auto" for boundary
                            detection, "smart_grid" to auto-detect grid size.
        rows:               Number of rows (grid mode only).
        cols:               Number of columns (grid mode only).
        output_dir:         Where extracted PNGs are saved.
        name_pattern:       Naming template. Supported tokens:
                            {row}, {col}, {index}, {sheet}.
        alpha_threshold:    Minimum alpha value (0-255) to consider a pixel
                            non-transparent during auto-detection.
        gap_merge:          In auto mode, merge bounding boxes that are
                            within this many pixels of each other.
        trim:               Trim transparent edges from each extracted sprite.
        min_sprite_area:    Ignore detected regions smaller than this
                            (area in pixels). Filters noise.
        preserve_padding:   Keep 1px transparent border around each sprite.
        skip_empty:         Skip grid cells that contain no opaque pixels.
    """

    mode: str = "grid"
    rows: int = 1
    cols: int = 1
    output_dir: str = "extracted"
    name_pattern: str = "sprite_{row}_{col}"
    alpha_threshold: int = 10
    gap_merge: int = 1
    trim: bool = False
    min_sprite_area: int = 4
    preserve_padding: bool = False
    skip_empty: bool = True


@dataclass
class SpriteInfo:
    """Metadata for a single extracted sprite."""

    filename: str
    x: int
    y: int
    width: int
    height: int
    row: int = 0
    col: int = 0
    index: int = 0
    is_empty: bool = False
    file_size_bytes: int = 0


@dataclass
class ExtractionResult:
    """Summary returned after extraction completes."""

    source: str
    total_extracted: int
    skipped_empty: int
    warnings: list[str] = field(default_factory=list)
    sprites: list[SpriteInfo] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    metadata_path: str = ""


# ---------------------------------------------------------------------------
# Core extractor
# ---------------------------------------------------------------------------
class SpriteExtractor:
    """Extracts individual sprites from a spritesheet image."""

    def extract(
        self,
        image_path: str | Path,
        config: ExtractionConfig | None = None,
    ) -> ExtractionResult:
        """Main entry point. Load sheet, extract sprites, save, return report.

        Args:
            image_path: Path to the spritesheet PNG/JPEG/WebP.
            config:     Extraction configuration (uses defaults if None).

        Returns:
            ExtractionResult with per-sprite metadata and summary stats.

        Raises:
            FileNotFoundError: If image_path does not exist.
            ValueError:        If the image cannot be opened or config is invalid.
        """
        config = config or ExtractionConfig()
        image_path = Path(image_path)
        t0 = time.perf_counter()

        # -- Validate input ------------------------------------------------
        if not image_path.exists():
            raise FileNotFoundError(f"Spritesheet not found: {image_path}")

        try:
            sheet = Image.open(image_path).convert("RGBA")
        except Exception as exc:
            raise ValueError(f"Cannot open image {image_path}: {exc}") from exc

        log.info(
            "Loaded %s  (%dx%d, %s)",
            image_path.name,
            sheet.width,
            sheet.height,
            sheet.mode,
        )

        # -- Prepare output dir --------------------------------------------
        out_dir = Path(config.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # -- Dispatch to extraction strategy --------------------------------
        if config.mode == "auto":
            regions = self._detect_auto(sheet, config)
        elif config.mode == "smart_grid":
            rows, cols, cell_w, cell_h = self._detect_grid_size(sheet, config)
            log.info(
                "Smart grid detected: %d rows x %d cols  (cell %dx%d)",
                rows, cols, cell_w, cell_h,
            )
            config.rows, config.cols = rows, cols
            regions = self._grid_regions(sheet, config)
        else:
            regions = self._grid_regions(sheet, config)

        # -- Extract and save each region ----------------------------------
        sheet_stem = image_path.stem
        sprites: list[SpriteInfo] = []
        skipped = 0
        warnings: list[str] = []

        for idx, (x, y, w, h, row, col) in enumerate(regions):
            # Crop the region
            crop = sheet.crop((x, y, x + w, y + h))

            # Empty check
            if config.skip_empty and self._is_empty(crop, config.alpha_threshold):
                skipped += 1
                log.debug("Skipped empty cell row=%d col=%d", row, col)
                continue

            # Trim transparent edges
            if config.trim:
                crop = self._trim_transparent(crop, config.alpha_threshold)
                if crop is None:
                    skipped += 1
                    continue
                w, h = crop.size

            # Padding
            if config.preserve_padding:
                padded = Image.new("RGBA", (w + 2, h + 2), (0, 0, 0, 0))
                padded.paste(crop, (1, 1))
                crop = padded
                w, h = crop.size

            # Build filename
            name = config.name_pattern.format(
                row=row, col=col, index=idx, sheet=sheet_stem,
            )
            if not name.endswith(".png"):
                name += ".png"
            out_path = out_dir / name

            crop.save(out_path, "PNG")
            fsize = out_path.stat().st_size

            sprites.append(
                SpriteInfo(
                    filename=name,
                    x=x, y=y, width=w, height=h,
                    row=row, col=col, index=idx,
                    file_size_bytes=fsize,
                )
            )

        # -- Metadata JSON -------------------------------------------------
        meta_path = out_dir / "metadata.json"
        meta = {
            "source": str(image_path),
            "source_size": [sheet.width, sheet.height],
            "extraction_mode": config.mode,
            "total_sprites": len(sprites),
            "skipped_empty": skipped,
            "sprites": [
                {
                    "file": s.filename,
                    "x": s.x, "y": s.y,
                    "w": s.width, "h": s.height,
                    "row": s.row, "col": s.col,
                }
                for s in sprites
            ],
        }
        meta_path.write_text(json.dumps(meta, indent=2))

        elapsed = time.perf_counter() - t0
        log.info(
            "Done: %d sprites extracted, %d empty skipped  (%.2fs)",
            len(sprites), skipped, elapsed,
        )

        return ExtractionResult(
            source=str(image_path),
            total_extracted=len(sprites),
            skipped_empty=skipped,
            warnings=warnings,
            sprites=sprites,
            elapsed_seconds=elapsed,
            metadata_path=str(meta_path),
        )

    # ------------------------------------------------------------------
    # Grid-based extraction
    # ------------------------------------------------------------------
    def _grid_regions(
        self, sheet: Image.Image, config: ExtractionConfig,
    ) -> list[tuple[int, int, int, int, int, int]]:
        """Divide the sheet into a uniform grid of (rows x cols) cells.

        Returns list of (x, y, w, h, row, col) tuples.
        """
        cell_w = sheet.width // config.cols
        cell_h = sheet.height // config.rows

        if cell_w == 0 or cell_h == 0:
            raise ValueError(
                f"Grid {config.rows}x{config.cols} produces zero-size cells "
                f"for image {sheet.width}x{sheet.height}"
            )

        # Warn if there is a remainder (sheet doesn't divide evenly)
        rem_x = sheet.width % config.cols
        rem_y = sheet.height % config.rows
        if rem_x or rem_y:
            log.warning(
                "Sheet %dx%d does not divide evenly into %dx%d grid "
                "(remainder %dx%d px — rightmost/bottom cells may be partial)",
                sheet.width, sheet.height,
                config.cols, config.rows,
                rem_x, rem_y,
            )

        regions = []
        for r in range(config.rows):
            for c in range(config.cols):
                x = c * cell_w
                y = r * cell_h
                regions.append((x, y, cell_w, cell_h, r, c))
        return regions

    # ------------------------------------------------------------------
    # Automatic boundary detection
    # ------------------------------------------------------------------
    def _detect_auto(
        self, sheet: Image.Image, config: ExtractionConfig,
    ) -> list[tuple[int, int, int, int, int, int]]:
        """Find sprite regions by detecting connected non-transparent areas.

        Algorithm:
        1. Build binary mask from alpha channel (alpha > threshold = True).
        2. Flood-fill to label connected components (4-connectivity).
        3. Compute bounding box per component.
        4. Merge boxes that overlap or are within gap_merge pixels.
        5. Filter by min_sprite_area.
        6. Sort top-to-bottom, left-to-right.

        Returns list of (x, y, w, h, row_approx, col_approx).
        """
        w, h = sheet.size
        alpha = sheet.split()[3]  # A channel
        pixels = alpha.load()
        thresh = config.alpha_threshold

        # Step 1: binary mask (True = opaque)
        mask = [[pixels[x, y] > thresh for x in range(w)] for y in range(h)]

        # Step 2: connected-component labeling via BFS
        visited = [[False] * w for _ in range(h)]
        boxes: list[list[int]] = []  # [min_x, min_y, max_x, max_y]

        for sy in range(h):
            for sx in range(w):
                if mask[sy][sx] and not visited[sy][sx]:
                    # BFS flood-fill
                    queue = deque([(sx, sy)])
                    visited[sy][sx] = True
                    bx0, by0, bx1, by1 = sx, sy, sx, sy

                    while queue:
                        cx, cy = queue.popleft()
                        bx0 = min(bx0, cx)
                        by0 = min(by0, cy)
                        bx1 = max(bx1, cx)
                        by1 = max(by1, cy)

                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < w and 0 <= ny < h:
                                if mask[ny][nx] and not visited[ny][nx]:
                                    visited[ny][nx] = True
                                    queue.append((nx, ny))

                    boxes.append([bx0, by0, bx1, by1])

        log.info("Auto-detect: %d raw connected components found", len(boxes))

        # Step 3: merge nearby boxes
        boxes = self._merge_boxes(boxes, config.gap_merge)
        log.info("After merge (gap=%dpx): %d regions", config.gap_merge, len(boxes))

        # Step 4: filter tiny regions
        min_area = config.min_sprite_area
        filtered = []
        for bx0, by0, bx1, by1 in boxes:
            area = (bx1 - bx0 + 1) * (by1 - by0 + 1)
            if area >= min_area:
                filtered.append((bx0, by0, bx1, by1))
            else:
                log.debug(
                    "Filtered tiny region (%d,%d)-(%d,%d), area=%d",
                    bx0, by0, bx1, by1, area,
                )
        boxes_final = filtered

        # Step 5: sort top-to-bottom, left-to-right and assign row/col indices
        boxes_final.sort(key=lambda b: (b[1], b[0]))

        regions = []
        for idx, (bx0, by0, bx1, by1) in enumerate(boxes_final):
            rw = bx1 - bx0 + 1
            rh = by1 - by0 + 1
            regions.append((bx0, by0, rw, rh, idx // max(1, len(boxes_final)), idx))

        # Assign approximate grid row/col by clustering Y then X
        if regions:
            regions = self._assign_grid_positions(regions)

        return regions

    # ------------------------------------------------------------------
    # Smart grid detection
    # ------------------------------------------------------------------
    def _detect_grid_size(
        self, sheet: Image.Image, config: ExtractionConfig,
    ) -> tuple[int, int, int, int]:
        """Detect grid layout by finding fully-transparent row/col gutters.

        Scans every row and column of the alpha channel. A row (or column)
        that is entirely below alpha_threshold is a "gutter". Consecutive
        non-gutter rows form a cell band.

        Returns (rows, cols, cell_width, cell_height).
        """
        w, h = sheet.size
        alpha = sheet.split()[3]
        pixels = alpha.load()
        thresh = config.alpha_threshold

        def band_sizes(is_gutter: list[bool]) -> list[int]:
            """Count widths of consecutive False (non-gutter) runs."""
            sizes = []
            run = 0
            for g in is_gutter:
                if not g:
                    run += 1
                elif run > 0:
                    sizes.append(run)
                    run = 0
            if run > 0:
                sizes.append(run)
            return sizes

        # Row gutters
        row_gutter = []
        for y in range(h):
            all_clear = all(pixels[x, y] <= thresh for x in range(w))
            row_gutter.append(all_clear)

        # Col gutters
        col_gutter = []
        for x in range(w):
            all_clear = all(pixels[x, y] <= thresh for y in range(h))
            col_gutter.append(all_clear)

        row_bands = band_sizes(row_gutter)
        col_bands = band_sizes(col_gutter)

        if not row_bands or not col_bands:
            log.warning("Smart grid: no clear gutters found, falling back to 1x1")
            return 1, 1, w, h

        # Use most common band size as the cell size
        cell_h = max(set(row_bands), key=row_bands.count)
        cell_w = max(set(col_bands), key=col_bands.count)

        rows = len(row_bands)
        cols = len(col_bands)

        return rows, cols, cell_w, cell_h

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _is_empty(img: Image.Image, threshold: int) -> bool:
        """True if every pixel in img has alpha <= threshold."""
        alpha = img.split()[3]
        return alpha.getextrema()[1] <= threshold

    @staticmethod
    def _trim_transparent(
        img: Image.Image, threshold: int,
    ) -> Optional[Image.Image]:
        """Crop to tight bounding box of opaque pixels. Returns None if empty."""
        alpha = img.split()[3]
        bbox = alpha.point(lambda p: 255 if p > threshold else 0).getbbox()
        if bbox is None:
            return None
        return img.crop(bbox)

    @staticmethod
    def _merge_boxes(
        boxes: list[list[int]], gap: int,
    ) -> list[list[int]]:
        """Merge bounding boxes that overlap or are within `gap` pixels.

        Uses iterative union-find-style merging until stable.
        """
        if not boxes:
            return boxes

        def overlaps(a: list[int], b: list[int]) -> bool:
            return not (
                a[2] + gap < b[0]
                or b[2] + gap < a[0]
                or a[3] + gap < b[1]
                or b[3] + gap < a[1]
            )

        changed = True
        while changed:
            changed = False
            merged: list[list[int]] = []
            used = [False] * len(boxes)

            for i in range(len(boxes)):
                if used[i]:
                    continue
                current = list(boxes[i])
                for j in range(i + 1, len(boxes)):
                    if used[j]:
                        continue
                    if overlaps(current, boxes[j]):
                        current[0] = min(current[0], boxes[j][0])
                        current[1] = min(current[1], boxes[j][1])
                        current[2] = max(current[2], boxes[j][2])
                        current[3] = max(current[3], boxes[j][3])
                        used[j] = True
                        changed = True
                merged.append(current)

            boxes = merged

        return boxes

    @staticmethod
    def _assign_grid_positions(
        regions: list[tuple[int, int, int, int, int, int]],
    ) -> list[tuple[int, int, int, int, int, int]]:
        """Assign (row, col) by clustering Y coordinates, then X within row.

        Groups sprites into rows if their Y-centers are within half the
        median height of each other.
        """
        if not regions:
            return regions

        # Sort by Y center
        def y_center(r: tuple) -> float:
            return r[1] + r[3] / 2

        sorted_r = sorted(regions, key=y_center)
        median_h = sorted(r[3] for r in regions)[len(regions) // 2]
        cluster_gap = max(median_h * 0.5, 4)

        # Cluster into rows
        rows_list: list[list[tuple]] = [[sorted_r[0]]]
        for r in sorted_r[1:]:
            if y_center(r) - y_center(rows_list[-1][-1]) > cluster_gap:
                rows_list.append([])
            rows_list[-1].append(r)

        # Sort each row by X, assign row/col
        result = []
        for row_idx, row_sprites in enumerate(rows_list):
            row_sprites.sort(key=lambda r: r[0])
            for col_idx, (x, y, w, h, _, _) in enumerate(row_sprites):
                result.append((x, y, w, h, row_idx, col_idx))

        return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Extract individual sprites from a spritesheet.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 3x3 grid extraction
  python sprite_extractor.py towers.png --rows 3 --cols 3

  # Auto-detect sprites by transparency
  python sprite_extractor.py props.png --auto

  # Smart grid detection (finds gutters automatically)
  python sprite_extractor.py tileset1.png --smart-grid

  # Trim + custom naming
  python sprite_extractor.py chars.png --auto --trim --name "enemy_{index}"
        """,
    )
    p.add_argument("image", help="Path to the spritesheet image")
    p.add_argument("-o", "--output", default=None, help="Output directory")
    p.add_argument("--rows", type=int, default=0, help="Grid rows (grid mode)")
    p.add_argument("--cols", type=int, default=0, help="Grid columns (grid mode)")
    p.add_argument("--auto", action="store_true", help="Auto-detect sprite boundaries")
    p.add_argument("--smart-grid", action="store_true", help="Auto-detect grid layout")
    p.add_argument("--trim", action="store_true", help="Trim transparent edges")
    p.add_argument("--padding", action="store_true", help="Add 1px transparent border")
    p.add_argument("--name", default="sprite_{row}_{col}", help="Naming pattern")
    p.add_argument("--threshold", type=int, default=10, help="Alpha threshold (0-255)")
    p.add_argument("--gap", type=int, default=1, help="Merge gap for auto mode (px)")
    p.add_argument("--min-area", type=int, default=4, help="Min sprite area (px)")
    p.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)

    # Determine mode
    if args.auto:
        mode = "auto"
    elif args.smart_grid:
        mode = "smart_grid"
    elif args.rows > 0 and args.cols > 0:
        mode = "grid"
    else:
        parser.error(
            "Specify extraction mode: --rows R --cols C, --auto, or --smart-grid"
        )
        return  # unreachable, but satisfies type checker

    # Default output dir: extracted/<sheet_stem>/
    image_path = Path(args.image)
    output = args.output or str(Path("extracted") / image_path.stem)

    config = ExtractionConfig(
        mode=mode,
        rows=args.rows if args.rows > 0 else 1,
        cols=args.cols if args.cols > 0 else 1,
        output_dir=output,
        name_pattern=args.name,
        alpha_threshold=args.threshold,
        gap_merge=args.gap,
        trim=args.trim,
        preserve_padding=args.padding,
        min_sprite_area=args.min_area,
    )

    ext = SpriteExtractor()
    result = ext.extract(args.image, config)

    # Summary
    print(f"\n{'='*50}")
    print(f"  Source:     {result.source}")
    print(f"  Extracted:  {result.total_extracted} sprites")
    print(f"  Skipped:    {result.skipped_empty} empty cells")
    print(f"  Time:       {result.elapsed_seconds:.3f}s")
    print(f"  Metadata:   {result.metadata_path}")
    if result.warnings:
        print(f"  Warnings:   {len(result.warnings)}")
        for w in result.warnings:
            print(f"    - {w}")
    print(f"{'='*50}")


# ---------------------------------------------------------------------------
# BastionTD preset configs — run these to extract all game assets
# ---------------------------------------------------------------------------
BASTION_PRESETS: dict[str, ExtractionConfig] = {
    "tileset1": ExtractionConfig(
        mode="smart_grid",
        output_dir="assets/extracted/tileset1",
        name_pattern="tile_{row}_{col}",
    ),
    "towers": ExtractionConfig(
        mode="auto",
        output_dir="assets/extracted/towers",
        name_pattern="tower_{row}_{col}",
        gap_merge=2,
        trim=True,
    ),
    "characters": ExtractionConfig(
        mode="auto",
        output_dir="assets/extracted/characters",
        name_pattern="char_{index}",
        trim=True,
    ),
    "props": ExtractionConfig(
        mode="auto",
        output_dir="assets/extracted/props",
        name_pattern="prop_{row}_{col}",
        gap_merge=2,
        trim=True,
    ),
    "ui": ExtractionConfig(
        mode="auto",
        output_dir="assets/extracted/ui",
        name_pattern="ui_{row}_{col}",
        gap_merge=1,
        trim=True,
    ),
}


def extract_all_bastion(asset_dir: str = "assets/assets") -> None:
    """Extract all BastionTD spritesheets using preset configurations.

    Call from project root:
        python -c "from scripts.sprite_extractor import extract_all_bastion; extract_all_bastion()"
    """
    ext = SpriteExtractor()
    asset_path = Path(asset_dir)

    for name, config in BASTION_PRESETS.items():
        sheet_path = asset_path / f"{name}.png"
        if not sheet_path.exists():
            log.warning("Preset '%s': file not found at %s — skipping", name, sheet_path)
            continue

        log.info("--- Extracting %s ---", name)
        result = ext.extract(str(sheet_path), config)
        print(
            f"  {name}: {result.total_extracted} sprites, "
            f"{result.skipped_empty} empty, {result.elapsed_seconds:.2f}s"
        )


if __name__ == "__main__":
    main()
