"""
Field normalization for incoming RetroPie hook data.

Extracts structured metadata (ROM path, system, emulator, core) from
the raw command-line string passed by runcommand hooks.
"""

import re
from pathlib import Path


def normalize_fields(
    rom_path: str,
    system_name: str | None,
    emulator: str | None,
    core: str | None,
) -> tuple[str, str | None, str | None, str | None]:
    """Normalize and extract metadata from raw hook inputs.

    Steps:
        1. Extract clean ROM path from the raw command string.
        2. Detect libretro core from -L argument if not provided.
        3. Infer system name from ROM path directory structure if not provided.
        4. Detect emulator (retroarch) from command string if not provided.

    Returns:
        Tuple of (rom_path, system_name, emulator, core)
    """
    cmd = (rom_path or "").strip()
    rom = cmd

    # Step 1: ROM path extraction
    m = re.search(r'(")?(/home/pi/RetroPie/roms/[^"]+)\1', cmd)
    if m:
        rom = m.group(2)

    # Step 2: Core detection from -L argument
    if not core:
        m = re.search(r'-L\s+(\S+)', cmd)
        if m:
            so = m.group(1)
            base = so.split("/")[-1]
            core = base.replace("_libretro.so", "")

    # Step 3: System name from ROM path directory
    if not system_name and rom:
        try:
            parts = Path(rom).parts
            i = parts.index("roms")
            if i + 1 < len(parts):
                system_name = parts[i + 1]
        except ValueError:
            pass

    # Step 4: Emulator detection
    if not emulator and "retroarch" in cmd:
        emulator = "retroarch"

    return rom, system_name, emulator, core
