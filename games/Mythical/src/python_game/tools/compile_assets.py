"""
Build-time Asset Compiler for Mythical.

This script bakes procedural PyGame drawing routines into static sprite sheets
and JSON metadata for both the PyGame desktop client and the GBA compiler.

Authoring layer: placeholder_sprites.py and procedural drawing functions.
"""
import os
import sys
import json
import pygame

# Make sure we can import Mythical modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from settings import TILE_SIZE
from placeholder_sprites import generate_character_sheet
from tools.author_sprites import generate_animal_sheet, generate_boss_sheet

EXPORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'compiled'))

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# Mocked ANIMAL_DEFS for compiler reference
ANIMAL_DEFS = {
    "deer": {"size": 0.85, "color": (170, 120, 60), "accent": (220, 180, 100)},
    "rabbit": {"size": 0.4, "color": (200, 190, 170), "accent": (230, 220, 200)},
    "wolf": {"size": 0.8, "color": (80, 80, 90), "accent": (120, 120, 130)},
    "boar": {"size": 0.9, "color": (110, 75, 50), "accent": (150, 110, 80)},
    "bear": {"size": 1.1, "color": (90, 60, 40), "accent": (130, 100, 70)},
    "fish": {"size": 0.35, "color": (60, 150, 200), "accent": (100, 200, 230)},
}

def compile_player_sprites():
    sprites = generate_character_sheet(
        body_color=(70, 130, 70),
        head_color=(210, 170, 130),
        hair_color=(65, 40, 20),
        eye_color=(30, 30, 50),
        jeans_color=(50, 75, 135)
    )

    out_dir = os.path.join(EXPORT_DIR, "player")
    ensure_dir(out_dir)

    metadata = {"frame_size": [TILE_SIZE, TILE_SIZE], "animations": {}}

    for anim_name, frames in sprites.items():
        anim_data = {"length": len(frames), "speed": 0.13, "frames": []}
        
        for i, frame_surf in enumerate(frames):
            filename = f"{anim_name}_{i}.png"
            filepath = os.path.join(out_dir, filename)
            pygame.image.save(frame_surf, filepath)
            anim_data["frames"].append(filename)
            
        metadata["animations"][anim_name] = anim_data

    # Save metadata
    with open(os.path.join(out_dir, "meta.json"), "w") as f:
        json.dump(metadata, f, indent=4)
        
    print(f"Compiled Player sprites to {out_dir}")

def compile_animal_sprites():
    for atype, adef in ANIMAL_DEFS.items():
        sz = int(TILE_SIZE * adef["size"])
        sprites = generate_animal_sheet(atype, sz, adef["color"], adef["accent"])
        
        out_dir = os.path.join(EXPORT_DIR, f"animal_{atype}")
        ensure_dir(out_dir)
        
        metadata = {"frame_size": [sz, sz], "animations": {}}
        for anim_name, frames in sprites.items():
            anim_data = {"length": len(frames), "speed": 0.15, "frames": []}
            for i, frame_surf in enumerate(frames):
                filename = f"{anim_name}_{i}.png"
                filepath = os.path.join(out_dir, filename)
                pygame.image.save(frame_surf, filepath)
                anim_data["frames"].append(filename)
            metadata["animations"][anim_name] = anim_data
            
        with open(os.path.join(out_dir, "meta.json"), "w") as f:
            json.dump(metadata, f, indent=4)
        print(f"Compiled Animal ({atype}) sprites to {out_dir}")

def compile_boss_sprites():
    for boss_type in [1, 2, 3]:
        sz = int(TILE_SIZE * 1.5)  # Make them a bit larger
        sprites = generate_boss_sheet(boss_type, sz)
        
        out_dir = os.path.join(EXPORT_DIR, f"boss_{boss_type}")
        ensure_dir(out_dir)
        
        metadata = {"frame_size": [sz * 2, sz * 2], "animations": {}}
        for anim_name, frames in sprites.items():
            anim_data = {"length": len(frames), "speed": 0.15, "frames": []}
            for i, frame_surf in enumerate(frames):
                filename = f"{anim_name}_{i}.png"
                filepath = os.path.join(out_dir, filename)
                pygame.image.save(frame_surf, filepath)
                anim_data["frames"].append(filename)
            metadata["animations"][anim_name] = anim_data
            
        with open(os.path.join(out_dir, "meta.json"), "w") as f:
            json.dump(metadata, f, indent=4)
        print(f"Compiled Boss ({boss_type}) sprites to {out_dir}")

def main():
    print("Starting Asset Compilation...")
    # Initialize hidden PyGame display for surface creation
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    ensure_dir(EXPORT_DIR)
    
    compile_player_sprites()
    compile_animal_sprites()
    compile_boss_sprites()
    
    print("Asset Compilation Complete!")

if __name__ == "__main__":
    main()
