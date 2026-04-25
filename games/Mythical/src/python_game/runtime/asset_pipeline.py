"""
Asset pipeline for converting procedural/desktop assets to GBA-compatible formats.

Converts:
- Procedural pygame.Surfaces → Tile/sprite sheets (indexed color)
- Runtime-generated audio → Tracker module files (.mod/.s3m/.it)
- JSON map data → Binary tilemap arrays
- JSON saves → Packed binary SRAM format
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Dict, List, Tuple

import pygame

from runtime.memory_budget import GBA_BUDGET, MemoryBudget
from settings import TILE_SIZE


@dataclass
class TileSet:
    """A set of tiles ready for GBA VRAM."""

    name: str
    tiles: List[bytes]  # Each tile is 8x8@4bpp = 32 bytes
    palettes: List[List[Tuple[int, int, int]]]  # 16-color palettes

    def to_c_array(self, var_name: str) -> str:
        """Generate C array for GBA toolchain."""
        lines = [
            f"// Tileset: {self.name}",
            f"const u8 {var_name}_tiles[{len(self.tiles) * 32}] = {{",
        ]

        for i, tile in enumerate(self.tiles):
            hex_bytes = ", ".join(f"0x{b:02x}" for b in tile)
            lines.append(f"    // Tile {i}")
            lines.append(f"    {hex_bytes},")

        lines.append("};")
        lines.append("")
        lines.append(f"const u16 {var_name}_palettes[{len(self.palettes) * 16}] = {{")

        for pal_idx, palette in enumerate(self.palettes):
            lines.append(f"    // Palette {pal_idx}")
            for r, g, b in palette:
                # Convert 24-bit RGB to GBA 15-bit (xBBBBBGGGGRRRRR)
                gba_color = ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)
                lines.append(f"    0x{gba_color:04x},")

        lines.append("};")
        return "\n".join(lines)


@dataclass
class SpriteSheet:
    """A sheet of sprites for GBA OAM."""

    name: str
    frames: List[bytes]  # Each frame is 32x32@4bpp = 512 bytes
    width: int  # Sprite width in pixels
    height: int  # Sprite height in pixels
    palette: List[Tuple[int, int, int]]
    animation_fps: int = 8

    def to_c_array(self, var_name: str) -> str:
        """Generate C array for sprite data."""
        lines = [
            f"// Sprite sheet: {self.name}",
            f"const u8 {var_name}_tiles[{len(self.frames) * len(self.frames[0])}] = {{",
        ]

        for i, frame in enumerate(self.frames):
            lines.append(f"    // Frame {i}")
            for j in range(0, len(frame), 16):
                chunk = frame[j : j + 16]
                hex_bytes = ", ".join(f"0x{b:02x}" for b in chunk)
                lines.append(f"    {hex_bytes},")

        lines.append("};")
        lines.append("")

        # Palette
        lines.append(f"const u16 {var_name}_palette[16] = {{")
        for r, g, b in self.palette[:16]:
            gba_color = ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)
            lines.append(f"    0x{gba_color:04x},")
        lines.append("};")

        # Animation metadata
        lines.append(f"const u8 {var_name}_anim_fps = {self.animation_fps};")
        lines.append(f"const u8 {var_name}_frame_count = {len(self.frames)};")

        return "\n".join(lines)


class SurfaceConverter:
    """Convert pygame surfaces to GBA-compatible formats."""

    def __init__(self, budget: MemoryBudget = GBA_BUDGET):
        self.budget = budget
        self._next_palette_id = 0
        self._palettes: Dict[int, List[Tuple[int, int, int]]] = {}

    def _reduce_colors(
        self, surface: pygame.Surface, max_colors: int = 16
    ) -> pygame.Surface:
        """Reduce surface to max_colors using simple quantization."""
        # Convert to palette mode with color key for transparency
        if surface.get_alpha():
            # Has per-pixel alpha - create color key
            temp = surface.convert_alpha()
            return temp
        else:
            return surface.convert(8)

    def _extract_palette(self, surface: pygame.Surface) -> List[Tuple[int, int, int]]:
        """Extract 16-color palette from surface."""
        # Simple approach: quantize to 15 colors + 1 transparent
        palette = [(0, 0, 0)]  # Color 0 = transparent

        # Get unique colors
        width, height = surface.get_size()
        pixels = []
        for y in range(height):
            for x in range(width):
                color = surface.get_at((x, y))
                if color.a > 128:  # Not transparent
                    rgb = (color.r, color.g, color.b)
                    if rgb not in pixels:
                        pixels.append(rgb)

        # Sort by luminance and take top 15
        pixels.sort(
            key=lambda c: 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2], reverse=True
        )
        palette.extend(pixels[:15])

        # Pad to 16 colors
        while len(palette) < 16:
            palette.append((0, 0, 0))

        return palette[:16]

    def surface_to_8x8_tiles(
        self, surface: pygame.Surface, tile_ids: List[int] | None = None
    ) -> Tuple[List[bytes], List[Tuple[int, int, int]]]:
        """Convert a surface to 8x8 4bpp tiles."""
        width, height = surface.get_size()
        palette = self._extract_palette(surface)

        # Create color lookup
        color_to_index = {rgb: i for i, rgb in enumerate(palette)}
        color_to_index[(0, 0, 0)] = 0  # Default to transparent

        tiles = []

        # Process in 8x8 chunks
        for ty in range(0, height, 8):
            for tx in range(0, width, 8):
                tile_data = bytearray(32)  # 8x8@4bpp = 32 bytes

                for y in range(8):
                    for x in range(8):
                        sx = tx + x
                        sy = ty + y

                        if sx < width and sy < height:
                            color = surface.get_at((sx, sy))
                            if color.a < 128:
                                idx = 0  # Transparent
                            else:
                                rgb = (color.r, color.g, color.b)
                                idx = color_to_index.get(rgb, 1)
                        else:
                            idx = 0

                        # Pack two 4-bit pixels per byte
                        byte_pos = y * 4 + (x // 2)
                        if x % 2 == 0:
                            tile_data[byte_pos] = idx  # Low nibble first
                        else:
                            tile_data[byte_pos] |= idx << 4

                tiles.append(bytes(tile_data))

        return tiles, palette

    def convert_tilemap_to_binary(self, tilemap_data: Dict, output_path: Path) -> None:
        """Convert Python tilemap dict to binary format for GBA."""
        width = tilemap_data["width"]
        height = tilemap_data["height"]

        with open(output_path, "wb") as f:
            # Header: width, height (2 bytes each, little-endian)
            f.write(struct.pack("<HH", width, height))

            # Ground layer (1 byte per tile)
            for row in tilemap_data["ground"]:
                for tile in row:
                    f.write(struct.pack("B", tile))

            # Decor layer (1 byte per tile, 0 = empty)
            if "decor" in tilemap_data and tilemap_data["decor"]:
                for row in tilemap_data["decor"]:
                    for tile in row:
                        f.write(struct.pack("B", tile))
            else:
                # Write empty layer
                f.write(bytes(width * height))

            # Collision layer (bit-packed, 1 bit per tile)
            collision_bytes = bytearray((width * height + 7) // 8)
            if "collision" in tilemap_data:
                for y, row in enumerate(tilemap_data["collision"]):
                    for x, collidable in enumerate(row):
                        if collidable:
                            bit = y * width + x
                            collision_bytes[bit // 8] |= 1 << (bit % 8)
            f.write(collision_bytes)


class SavePacker:
    """Pack/unpack save data to binary SRAM format for GBA."""

    # Save format version for compatibility
    SAVE_VERSION = 6  # GBA-optimized binary format

    # Struct format for header
    HEADER_FORMAT = "<4s H H"  # Magic (4 bytes), version (2 bytes), checksum (2 bytes)
    HEADER_SIZE = 8

    def __init__(self):
        self.magic = b"MYTH"

    def pack_save(self, save_data: Dict) -> bytes:
        """Pack save dict to binary format."""
        buffer = bytearray()

        # Reserve header (will fill in later)
        buffer.extend(bytes(self.HEADER_SIZE))

        # Pack player state
        self._pack_player(buffer, save_data.get("player", {}))

        # Pack inventory
        self._pack_inventory(buffer, save_data.get("inventory", {}))

        # Pack quests
        self._pack_quests(buffer, save_data.get("quest_stages", {}))

        # Pack progression
        self._pack_progression(buffer, save_data.get("progression", {}))

        # Pack bestiary
        self._pack_bestiary(buffer, save_data.get("bestiary", {}))

        # Pack reputation
        self._pack_reputation(buffer, save_data.get("reputation", {}))

        # Pack campaign
        self._pack_campaign(buffer, save_data.get("campaign", {}))

        # Pack consequence state
        self._pack_consequences(buffer, save_data.get("consequences", {}))

        # Calculate checksum and write header
        checksum = self._calculate_checksum(buffer[self.HEADER_SIZE :])
        struct.pack_into("<4s H H", buffer, 0, self.magic, self.SAVE_VERSION, checksum)

        return bytes(buffer)

    def unpack_save(self, data: bytes) -> Dict | None:
        """Unpack binary save to dict. Returns None if invalid."""
        if len(data) < self.HEADER_SIZE:
            return None

        magic, version, checksum = struct.unpack_from(self.HEADER_FORMAT, data, 0)

        if magic != self.magic:
            return None

        if version != self.SAVE_VERSION:
            # Could add migration logic here
            return None

        # Verify checksum
        calc_checksum = self._calculate_checksum(data[self.HEADER_SIZE :])
        if calc_checksum != checksum:
            return None

        # Unpack sections
        offset = self.HEADER_SIZE
        result = {}

        # Unpack each section (simplified - real impl would track offsets)
        result["player"], offset = self._unpack_player(data, offset)
        result["inventory"], offset = self._unpack_inventory(data, offset)
        result["quest_stages"], offset = self._unpack_quests(data, offset)
        result["progression"], offset = self._unpack_progression(data, offset)
        result["bestiary"], offset = self._unpack_bestiary(data, offset)
        result["reputation"], offset = self._unpack_reputation(data, offset)
        result["campaign"], offset = self._unpack_campaign(data, offset)
        result["consequences"], offset = self._unpack_consequences(data, offset)

        return result

    def _calculate_checksum(self, data: bytes) -> int:
        """Simple checksum for corruption detection."""
        return sum(data) & 0xFFFF

    # Packing methods (simplified - full impl would be more detailed)
    def _pack_player(self, buffer: bytearray, player: Dict) -> None:
        # x, y (2 bytes each, fixed-point 8.8), hp, max_hp, facing (1 byte)
        x = int(player.get("x", 0) * 256)
        y = int(player.get("y", 0) * 256)
        hp = player.get("hp", 6)
        max_hp = player.get("max_hp", 6)
        facing = player.get("facing", "down")
        facing_id = {"down": 0, "up": 1, "left": 2, "right": 3}.get(facing, 0)

        buffer.extend(struct.pack("<hhBB", x, y, hp, max_hp))
        buffer.append(facing_id)

    def _pack_inventory(self, buffer: bytearray, inv: Dict) -> None:
        # Simplified - pack slot count then slots
        slots = inv.get("slots", [])
        buffer.append(len(slots))
        for slot in slots[:48]:  # Max 48 slots
            item_id = slot.get("item_id", 0)
            count = slot.get("count", 0)
            buffer.extend(struct.pack("<HB", item_id, count))

    def _pack_quests(self, buffer: bytearray, quests: Dict) -> None:
        buffer.append(len(quests))
        for qid, qdata in quests.items():
            buffer.append(len(qid))
            buffer.extend(qid.encode())
            buffer.append(qdata.get("stage", 0))
            buffer.append(1 if qdata.get("complete") else 0)

    def _pack_progression(self, buffer: bytearray, prog: Dict) -> None:
        buffer.extend(
            struct.pack(
                "<HHH",
                prog.get("xp", 0),
                prog.get("level", 1),
                prog.get("skill_points", 0),
            )
        )

    def _pack_bestiary(self, buffer: bytearray, bestiary: Dict) -> None:
        buffer.append(len(bestiary))
        for entry_id, entry in bestiary.items():
            buffer.append(len(entry_id))
            buffer.extend(entry_id.encode())
            buffer.append(entry.get("kills", 0))
            buffer.append(1 if entry.get("discovered") else 0)

    def _pack_reputation(self, buffer: bytearray, rep: Dict) -> None:
        buffer.append(len(rep))
        for faction, value in rep.items():
            buffer.append(len(faction))
            buffer.extend(faction.encode())
            buffer.extend(struct.pack("<h", value))

    def _pack_campaign(self, buffer: bytearray, campaign: Dict) -> None:
        buffer.append(campaign.get("world_stage", 1))
        completed = campaign.get("completed_stages", [])
        buffer.append(len(completed))
        for stage in completed:
            buffer.append(stage)

    def _pack_consequences(self, buffer: bytearray, consequences: Dict) -> None:
        buffer.append(len(consequences))
        for key, value in consequences.items():
            buffer.append(len(key))
            buffer.extend(key.encode())
            buffer.append(1 if value else 0)

    # Unpack methods return (value, new_offset)
    def _unpack_player(self, data: bytes, offset: int) -> Tuple[Dict, int]:
        x, y, hp, max_hp = struct.unpack_from("<hhBB", data, offset)
        facing_id = data[offset + 6]
        facings = ["down", "up", "left", "right"]
        return {
            "x": x / 256.0,
            "y": y / 256.0,
            "hp": hp,
            "max_hp": max_hp,
            "facing": facings[facing_id] if facing_id < 4 else "down",
        }, offset + 7

    def _unpack_inventory(self, data: bytes, offset: int) -> Tuple[Dict, int]:
        count = data[offset]
        offset += 1
        slots = []
        for _ in range(count):
            item_id, slot_count = struct.unpack_from("<HB", data, offset)
            slots.append({"item_id": item_id, "count": slot_count})
            offset += 3
        return {"slots": slots}, offset

    def _unpack_quests(self, data: bytes, offset: int) -> Tuple[Dict, int]:
        count = data[offset]
        offset += 1
        quests = {}
        for _ in range(count):
            id_len = data[offset]
            offset += 1
            qid = data[offset : offset + id_len].decode()
            offset += id_len
            stage = data[offset]
            complete = data[offset + 1] == 1
            offset += 2
            quests[qid] = {"stage": stage, "complete": complete}
        return quests, offset

    def _unpack_progression(self, data: bytes, offset: int) -> Tuple[Dict, int]:
        xp, level, sp = struct.unpack_from("<HHH", data, offset)
        return {"xp": xp, "level": level, "skill_points": sp}, offset + 6

    def _unpack_bestiary(self, data: bytes, offset: int) -> Tuple[Dict, int]:
        count = data[offset]
        offset += 1
        entries = {}
        for _ in range(count):
            id_len = data[offset]
            offset += 1
            entry_id = data[offset : offset + id_len].decode()
            offset += id_len
            kills = data[offset]
            discovered = data[offset + 1] == 1
            offset += 2
            entries[entry_id] = {"kills": kills, "discovered": discovered}
        return entries, offset

    def _unpack_reputation(self, data: bytes, offset: int) -> Tuple[Dict, int]:
        count = data[offset]
        offset += 1
        rep = {}
        for _ in range(count):
            id_len = data[offset]
            offset += 1
            faction = data[offset : offset + id_len].decode()
            offset += id_len
            value = struct.unpack_from("<h", data, offset)[0]
            offset += 2
            rep[faction] = value
        return rep, offset

    def _unpack_campaign(self, data: bytes, offset: int) -> Tuple[Dict, int]:
        world_stage = data[offset]
        completed_count = data[offset + 1]
        offset += 2
        completed = []
        for _ in range(completed_count):
            completed.append(data[offset])
            offset += 1
        return {"world_stage": world_stage, "completed_stages": completed}, offset

    def _unpack_consequences(self, data: bytes, offset: int) -> Tuple[Dict, int]:
        count = data[offset]
        offset += 1
        consequences = {}
        for _ in range(count):
            id_len = data[offset]
            offset += 1
            key = data[offset : offset + id_len].decode()
            offset += id_len
            value = data[offset] == 1
            offset += 1
            consequences[key] = value
        return consequences, offset


# Convenience function for testing conversion
def test_save_packing() -> bool:
    """Test that save packing round-trips correctly."""
    packer = SavePacker()

    test_data = {
        "player": {"x": 10.5, "y": 20.25, "hp": 5, "max_hp": 6, "facing": "left"},
        "inventory": {
            "slots": [{"item_id": 1, "count": 5}, {"item_id": 3, "count": 1}]
        },
        "quest_stages": {"main": {"stage": 2, "complete": False}},
        "progression": {"xp": 150, "level": 3, "skill_points": 4},
        "bestiary": {"wolf": {"kills": 5, "discovered": True}},
        "reputation": {"village": 10, "forest": -5},
        "campaign": {"world_stage": 2, "completed_stages": [1]},
        "consequences": {"spared_wolf": True},
    }

    packed = packer.pack_save(test_data)
    unpacked = packer.unpack_save(packed)

    # Check critical fields
    assert unpacked is not None, "Unpack failed"
    assert unpacked["player"]["x"] == test_data["player"]["x"], "X mismatch"
    assert unpacked["campaign"]["world_stage"] == 2, "Campaign stage mismatch"

    print(f"Save packing test passed! Packed size: {len(packed)} bytes")
    return True


if __name__ == "__main__":
    test_save_packing()
