import pygame
import os

# Settings
SCREEN_W = 240
SCREEN_H = 160

# Sprite Sizes (GBA)
CAR_W = 16
CAR_H = 24
ITEM_W = 12
ITEM_H = 12
FONT_W = 8
FONT_H = 8

# Paths
BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "python_game")
OUT_FILE = "assets.h"

# Asset Lists
ENEMIES = ["Audi.png", "Viper.png", "Lambo.png", "Supra.png", "CCX.png"]
ITEMS = ["Coin.png", "Fuel.png", "Repair.png"]

def main():
    pygame.init()
    
    # Palette Collection
    master_palette = [] 
    # Index 0: Transparent (Black)
    master_palette.append((0,0,0)) 
    
    # UI Colors (Indices 1-10)
    # WHITE, RED, GREEN, BLUE, YELLOW, CYAN, PURPLE, GRAY, DARK_GRAY, BLACK_OPAQUE
    ui_colors = [
        (255, 255, 255), # 1: White
        (255, 0, 0),     # 2: Red
        (0, 255, 0),     # 3: Green
        (0, 0, 255),     # 4: Blue
        (255, 255, 0),   # 5: Yellow
        (0, 255, 255),   # 6: Cyan
        (128, 0, 128),   # 7: Purple
        (100, 100, 100), # 8: Gray
        (50, 50, 50),    # 9: Dark Gray
        (10, 10, 10)     # 10: Near Black
    ]
    master_palette.extend(ui_colors)
    
    def get_color_index(r, g, b):
        # Exact match
        for i, c in enumerate(master_palette):
            if c == (r,g,b):
                return i
        # Add neew
        if len(master_palette) < 256:
            master_palette.append((r,g,b))
            return len(master_palette) - 1
        # Find nearest
        best_i = 0
        min_dist = 999999
        for i, c in enumerate(master_palette):
            dist = (r-c[0])**2 + (g-c[1])**2 + (b-c[2])**2
            if dist < min_dist:
                min_dist = dist
                best_i = i
        return best_i

    def process_surface(img, w, h, is_sprite=False):
        data = []
        for y in range(h):
            for x in range(w):
                if x < img.get_width() and y < img.get_height():
                    c = img.get_at((x, y))
                    r, g, b = c[0], c[1], c[2]
                    alpha = c[3] if len(c) > 3 else 255
                else:
                    c = (0,0,0,0) # Out of bounds
                    alpha = 0

                if is_sprite and alpha < 128:
                    data.append(0) # Transparent
                else:
                    idx = get_color_index(r, g, b)
                    # GBA Index 0 is transparent.
                    data.append(idx)
        return img, data

    def process_image(path, w, h, is_sprite=False):
        if not os.path.exists(path):
            print(f"Missing: {path}")
            surf = pygame.Surface((w, h))
            surf.fill((255, 0, 255)) # Magenta placeholder
            return surf, [1]* (w*h) # Dummy data
            
        img = pygame.image.load(path)
        img = pygame.transform.scale(img, (w, h))
        return process_surface(img, w, h, is_sprite)

    # Asset discovery
    # Find all PNGs that look like cars
    all_files = os.listdir(BASE_DIR)
    
    # Exclude items, roads, UI elements
    excludes = ["Coin.png", "Fuel.png", "Repair.png", "Road.png", "Road2.png", "Road3.png", "Road4.png", "Background.png"]
    # Also exclude generated or other non-car pngs
    cars = [f for f in all_files if f.endswith(".png") and f not in excludes and "Road" not in f]
    
    roads = ["Road.png", "Road2.png", "Road3.png", "Road4.png"]
    # Check if they exist
    roads = [r for r in roads if r in all_files]

    # Storage for C arrays
    car_definitions = [] # (name, normal_data, left_data, right_data)
    road_definitions = [] # (name, data)

    # 1. Process Cars
    print(f"Found {len(cars)} cars.")
    for car_file in cars:
        name = car_file.split('.')[0]
        print(f"Processing Car: {name}")
        
        path = os.path.join(BASE_DIR, car_file)
        img, normal_data = process_image(path, CAR_W, CAR_H, True)
        
        # Rotations
        # Left
        img_left = pygame.transform.rotate(img, 15)
        img_left = pygame.transform.scale(img_left, (CAR_W, CAR_H))
        _, left_data = process_surface(img_left, CAR_W, CAR_H, True)
        
        # Right
        img_right = pygame.transform.rotate(img, -15)
        img_right = pygame.transform.scale(img_right, (CAR_W, CAR_H))
        _, right_data = process_surface(img_right, CAR_W, CAR_H, True)

        car_definitions.append({
            "name": name,
            "normal": normal_data,
            "left": left_data,
            "right": right_data
        })

    # 2. Process Roads
    print(f"Found {len(roads)} roads.")
    for road_file in roads:
        name = road_file.split('.')[0]
        print(f"Processing Road: {name}")
        path = os.path.join(BASE_DIR, road_file)
        _, data = process_image(path, SCREEN_W, SCREEN_H)
        road_definitions.append({
            "name": name,
            "data": data
        })

    # 3. Process Items
    print("Processing Items...")
    item_maps = {}
    for name in ITEMS:
        _, data = process_image(os.path.join(BASE_DIR, name), ITEM_W, ITEM_H, True)
        item_maps[name] = data
    
    # Font
    print("Generating Font...")
    sys_font = pygame.font.Font(None, 20) # Default size
    font_maps = {}
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789: "
    for char in chars:
        # Render white text on black
        surf = sys_font.render(char, False, (255, 255, 255), (0,0,0))
        surf = pygame.transform.scale(surf, (FONT_W, FONT_H)) # Force size
        data = []
        for y in range(FONT_H):
            for x in range(FONT_W):
                c = surf.get_at((x, y))
                if c[0] > 128: # White-ish
                     data.append(get_color_index(255, 255, 255))
                else:
                     data.append(0) # Transp
        font_maps[char] = data


    # 2. Output
    print(f"Total Palette Helpers: {len(master_palette)}")
    
    with open(OUT_FILE, "w") as f:
        f.write("#ifndef ASSETS_H\n#define ASSETS_H\n\n")
        f.write("#include \"gba.h\"\n\n")
        
        # MACROS for Sizes
        f.write(f"#define CAR_W {CAR_W}\n")
        f.write(f"#define CAR_H {CAR_H}\n")
        f.write(f"#define ITEM_W {ITEM_W}\n")
        f.write(f"#define ITEM_H {ITEM_H}\n\n")
        
        # Palette
        f.write(f"const u16 game_palette[{256}] = {{\n")
        for r,g,b in master_palette:
            r5, g5, b5 = (r>>3)&0x1F, (g>>3)&0x1F, (b>>3)&0x1F
            c = (b5<<10)|(g5<<5)|r5
            f.write(f"0x{c:04X}, ")
        for _ in range(256 - len(master_palette)): f.write("0x0000, ")
        f.write("\n};\n\n")
        
        # Helper to write array
        def write_arr(name, data):
            # Mode 4 Packed
            f.write(f"const u16 {name}[{len(data)//2}] = {{\n")
            for i in range(0, len(data), 2):
                p1 = data[i]
                p2 = data[i+1] if i+1 < len(data) else 0
                val = (p2 << 8) | p1
                f.write(f"0x{val:04X}, ")
            f.write("};\n\n")

        # Write Cars
        # We need a predictable order: Alphabetical for index consistency
        car_definitions.sort(key=lambda x: x["name"])
        
        car_names = []
        for car in car_definitions:
            clean_name = car["name"].lower()
            # Normal
            n_name = f"car_{clean_name}_normal"
            write_arr(n_name, car["normal"])
            # Left
            l_name = f"car_{clean_name}_left"
            write_arr(l_name, car["left"])
            # Right
            r_name = f"car_{clean_name}_right"
            write_arr(r_name, car["right"])
            
            car_names.append(clean_name)

        # Car Collections
        f.write(f"#define NUM_CARS {len(car_names)}\n\n")
        
        f.write("const u16* cars_normal[NUM_CARS] = {\n")
        for c in car_names: f.write(f"    car_{c}_normal,\n")
        f.write("};\n\n")

        f.write("const u16* cars_left[NUM_CARS] = {\n")
        for c in car_names: f.write(f"    car_{c}_left,\n")
        f.write("};\n\n")

        f.write("const u16* cars_right[NUM_CARS] = {\n")
        for c in car_names: f.write(f"    car_{c}_right,\n")
        f.write("};\n\n")


        # Write Roads
        road_definitions.sort(key=lambda x: x["name"])
        road_names = []
        for r in road_definitions:
            clean_name = r["name"].lower()
            name = f"bg_{clean_name}"
            write_arr(name, r["data"])
            road_names.append(name)

        f.write(f"#define NUM_ROADS {len(road_names)}\n\n")
        f.write("const u16* roads[NUM_ROADS] = {\n")
        for r in road_names: f.write(f"    {r},\n")
        f.write("};\n\n")

        # Items
        item_names = []
        # sort Items?
        for name, data in item_maps.items():
             safe_name = "spr_" + name.split('.')[0].lower()
             write_arr(safe_name, data)
             item_names.append(safe_name)
             
        f.write("const u16* item_sprites[] = {\n")
        for n in item_names: f.write(f"    {n},\n")
        f.write("};\n\n")

        # Enemy Sprites (Legacy pointer? Or used in Game?)
        # Game uses `enemy_sprites`.
        # We should map `enemy_sprites` to the `cars_normal` array, but `enemy_sprites` probably used a subset (enemies only).
        # But now ANY car can be an enemy.
        # Let's redefine `enemy_sprites` to point to `cars_normal` or just use `cars_normal` in main.c?
        # To minimize main.c changes, let's just make `enemy_sprites` identical to `cars_normal`
        f.write("#define enemy_sprites cars_normal\n\n")

        # Font
        # We'll just write a giant lookup or switch? 
        # A pointer array mapped to ASCII?
        # Let's write all chars then a lookup.
        f.write("// Font Glyphs (Packed)\n")
        font_ptr_list = []
        for char, data in font_maps.items():
            # Name by hex code to be safe
            safe_name = f"font_{ord(char):02X}"
            write_arr(safe_name, data)
            font_ptr_list.append(safe_name)
            
        # Lookup table 0-127
        f.write("const u16* font_lookup[128] = {\n")
        # Fill with null/space first
        # We only have a subset.
        for i in range(128):
            char = chr(i)
            if char in font_maps:
                f.write(f"    font_{i:02X}, ")
            else:
                f.write("    0, ")
            if i % 8 == 7: f.write("\n")
        f.write("};\n\n")

        f.write("#endif\n")
        
    print(f"Generated {OUT_FILE}")

if __name__ == "__main__":
    main()
