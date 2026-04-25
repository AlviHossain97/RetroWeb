"""
Authoring Layer: Recipes for generating procedural sprite sheets.
"""
import pygame
import math

DIRECTIONS = ["down", "up", "left", "right"]

def oscillate(t, freq, amplitude=1):
    return math.sin(t * freq) * amplitude

def generate_animal_sheet(atype: str, size: int, color: tuple, accent: tuple) -> dict:
    """Generate basic animations for an animal."""
    sheets = {}
    S = size
    
    # 4 frames of walk/idle for each direction, plus hurt and death
    for direction in DIRECTIONS:
        frames = []
        for f in range(4):
            surf = pygame.Surface((S, S), pygame.SRCALPHA)
            
            # Simulated time for procedural parameters
            anim_timer = f * (math.pi / 2.5) # creates a walk cycle over 4 frames
            
            bob = int(oscillate(anim_timer, 5, amplitude=2))
            
            sx = 0
            sy = 0
            off = (S - S) // 2 # usually 0 since size == S
            
            # Shadow
            sh = pygame.Surface((S, S // 3), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 35), (0, 0, S, S // 3))
            surf.blit(sh, (off, S - (S // 5)))
            
            bx, by_ = off, off + bob
            
            if atype == "deer":
                _draw_deer(surf, bx, by_, S, color, accent)
            elif atype == "rabbit":
                _draw_rabbit(surf, bx, by_, S, color, accent)
            elif atype == "wolf":
                _draw_wolf(surf, bx, by_, S, color, accent)
            elif atype == "boar":
                _draw_boar(surf, bx, by_, S, color, accent)
            elif atype == "bear":
                _draw_bear(surf, bx, by_, S, color, accent)
            elif atype == "fish":
                _draw_fish(surf, bx, by_, S, color, accent, anim_timer)
            else:
                pygame.draw.ellipse(surf, color, (bx, by_, S, S))
                
            # If direction isn't naturally supported by simple shapes, flip it
            if direction == "left":
                surf = pygame.transform.flip(surf, True, False)
                
            frames.append(surf)
        sheets[f"{direction}_walk"] = frames
        sheets[f"{direction}_idle"] = [frames[0]] # Idle is just frame 0
        
    # Hurt frame
    hurt_surf = pygame.Surface((S, S), pygame.SRCALPHA)
    hurt_col = (240, 240, 240)
    if atype == "deer": _draw_deer(hurt_surf, 0, 0, S, hurt_col, hurt_col)
    elif atype == "rabbit": _draw_rabbit(hurt_surf, 0, 0, S, hurt_col, hurt_col)
    elif atype == "wolf": _draw_wolf(hurt_surf, 0, 0, S, hurt_col, hurt_col)
    elif atype == "boar": _draw_boar(hurt_surf, 0, 0, S, hurt_col, hurt_col)
    elif atype == "bear": _draw_bear(hurt_surf, 0, 0, S, hurt_col, hurt_col)
    elif atype == "fish": _draw_fish(hurt_surf, 0, 0, S, hurt_col, hurt_col, 0)
    sheets["hurt"] = [hurt_surf]
    
    # Death frames (fade out)
    death_frames = []
    for f in range(4):
        alpha = max(0, int(255 * (1.0 - (f / 3.0))))
        dsurf = pygame.Surface((S, S // 2), pygame.SRCALPHA)
        c = (*color, alpha)
        pygame.draw.ellipse(dsurf, c, (0, 0, S, S // 2))
        
        fsurf = pygame.Surface((S, S), pygame.SRCALPHA)
        fsurf.blit(dsurf, (0, S // 4))
        death_frames.append(fsurf)
    sheets["death"] = death_frames

    return sheets

def _draw_deer(s, bx, by_, sz, c, ac):
    pygame.draw.ellipse(s, c, (bx + sz // 6, by_ + sz // 4, sz * 2 // 3, sz // 2))
    pygame.draw.circle(s, c, (bx + sz // 6, by_ + sz // 4), sz // 5)
    lc = tuple(max(0, x - 30) for x in c[:3])
    for lx in (bx + sz // 4, bx + sz * 3 // 4 - 4):
        pygame.draw.line(s, lc, (lx, by_ + sz * 3 // 4), (lx, by_ + sz), 2)
    ax = bx + sz // 6
    ay = by_ + sz // 6
    pygame.draw.line(s, ac, (ax, ay), (ax - 4, ay - 7), 2)
    pygame.draw.line(s, ac, (ax, ay), (ax + 2, ay - 6), 2)

def _draw_rabbit(s, bx, by_, sz, c, ac):
    pygame.draw.ellipse(s, c, (bx + sz // 4, by_ + sz // 3, sz // 2, sz * 2 // 3))
    pygame.draw.circle(s, c, (bx + sz // 2, by_ + sz // 3), sz // 4)
    pygame.draw.ellipse(s, c, (bx + sz // 3, by_, 5, sz // 3))
    pygame.draw.ellipse(s, c, (bx + sz * 2 // 3 - 5, by_, 5, sz // 3))
    pygame.draw.ellipse(s, ac, (bx + sz // 3 + 1, by_ + 2, 3, sz // 3 - 4))
    pygame.draw.circle(s, (220, 60, 60), (bx + sz * 2 // 5, by_ + sz // 3 - 2), 2)

def _draw_wolf(s, bx, by_, sz, c, ac):
    pygame.draw.ellipse(s, c, (bx + sz // 8, by_ + sz // 4, sz * 3 // 4, sz // 2))
    pygame.draw.ellipse(s, c, (bx, by_ + sz // 6, sz // 2, sz // 3))
    pygame.draw.ellipse(s, ac, (bx, by_ + sz // 4, sz // 3, sz // 5))
    pts1 = [(bx + sz // 4, by_ + sz // 6), (bx + sz // 3, by_), (bx + sz * 5 // 12, by_ + sz // 6)]
    pygame.draw.polygon(s, c, pts1)
    pygame.draw.arc(s, c, (bx + sz * 5 // 8, by_ + sz // 6, sz // 3, sz // 3), math.pi * 0.2, math.pi * 1.0, 3)
    pygame.draw.circle(s, (230, 200, 50), (bx + sz // 4, by_ + sz // 4 - 1), 2)

def _draw_boar(s, bx, by_, sz, c, ac):
    pygame.draw.ellipse(s, c, (bx + sz // 8, by_ + sz // 5, sz * 3 // 4, sz * 3 // 5))
    pygame.draw.ellipse(s, c, (bx, by_ + sz // 4, sz * 2 // 5, sz // 3))
    pygame.draw.line(s, (230, 220, 180), (bx + sz // 8, by_ + sz // 3 + 4), (bx - 4, by_ + sz // 3 + 8), 2)
    pygame.draw.ellipse(s, ac, (bx, by_ + sz // 3, sz // 4, sz // 6))
    pygame.draw.circle(s, (220, 100, 30), (bx + sz // 4, by_ + sz // 4), 3)

def _draw_bear(s, bx, by_, sz, c, ac):
    pygame.draw.ellipse(s, c, (bx + sz // 8, by_ + sz // 5, sz * 3 // 4, sz * 3 // 4))
    pygame.draw.circle(s, c, (bx + sz // 4, by_ + sz // 4), sz // 3)
    pygame.draw.circle(s, c, (bx + sz // 8, by_ + sz // 8), sz // 7)
    pygame.draw.circle(s, c, (bx + sz * 3 // 8, by_ + sz // 8), sz // 7)
    pygame.draw.ellipse(s, ac, (bx + sz // 8, by_ + sz // 3, sz // 3, sz // 5))
    pygame.draw.circle(s, (20, 10, 5), (bx + sz // 5, by_ + sz // 4), 3)
    lc = tuple(max(0, x - 40) for x in c[:3])
    for cx_ in (bx + sz // 3, bx + sz * 2 // 3):
        pygame.draw.line(s, lc, (cx_, by_ + sz * 5 // 6), (cx_ - 3, by_ + sz + sz + 2), 2)
        pygame.draw.line(s, lc, (cx_, by_ + sz * 5 // 6), (cx_ + 3, by_ + sz + sz + 2), 2)

def _draw_fish(s, bx, by_, sz, c, ac, anim_timer):
    wave = int(oscillate(anim_timer, 6, amplitude=3))
    pygame.draw.ellipse(s, c, (bx + sz // 6, by_ + sz // 3 + wave, sz * 2 // 3, sz // 3))
    pts = [(bx + sz // 6, by_ + sz // 2 + wave), (bx, by_ + sz // 3 + wave), (bx, by_ + sz * 2 // 3 + wave)]
    pygame.draw.polygon(s, ac, pts)
    pygame.draw.circle(s, (240, 240, 240), (bx + sz * 2 // 3, by_ + sz * 5 // 12 + wave), 3)
    pygame.draw.circle(s, (20, 20, 20), (bx + sz * 2 // 3, by_ + sz * 5 // 12 + wave), 1)

def generate_boss_sheet(boss_type: int, size: int) -> dict:
    sheets = {}
    S = size
    
    # Bosses don't have strictly directional sprites in their simple PyGame impl,
    # they just faced forward and bobbed. We'll generate "down_idle" etc for compatibility.
    
    for anim_name, phase in [("idle_1", 1), ("idle_2", 2), ("idle_3", 3), ("hurt", 1), ("death", 1)]:
        frames = []
        for f in range(4):
            surf = pygame.Surface((S * 2, S * 2), pygame.SRCALPHA)
            cx, cy = S, S
            
            bob = 0 if anim_name in ("hurt", "death") else int(oscillate(f * (math.pi / 2), 3, amplitude=2))
            
            if anim_name == "death":
                alpha = max(0, 255 - int((f/3) * 200))
                pygame.draw.rect(surf, (140, 50, 50, alpha), (cx - S//2, cy - S//2, S, S), border_radius=6)
                frames.append(surf)
                continue
                
            is_hurt = anim_name == "hurt"

            if boss_type == 1:
                body_c = (255, 255, 255) if is_hurt else ((220, 60, 40) if phase == 2 else (140, 80, 60))
                eye_c = (255, 80, 40) if phase == 2 else (200, 160, 50)
                
                pygame.draw.rect(surf, body_c, (cx - S//2 + 4, cy - S//2 + S//5 + bob, S - 8, S * 4 // 5), border_radius=6)
                pygame.draw.rect(surf, body_c, (cx - S//4, cy - S//2 + bob, S // 2, S // 3), border_radius=4)
                pygame.draw.circle(surf, eye_c, (cx - S//6, cy - S//3 + S//6 + bob), 4)
                pygame.draw.circle(surf, eye_c, (cx + S//6, cy - S//3 + S//6 + bob), 4)
                pygame.draw.circle(surf, (20, 10, 10), (cx - S//6, cy - S//3 + S//6 + bob + 1), 2)
                pygame.draw.circle(surf, (20, 10, 10), (cx + S//6, cy - S//3 + S//6 + bob + 1), 2)
                
            elif boss_type == 2:
                body_col = (255, 80, 80) if is_hurt else ((220, 50, 50) if phase == 2 else (90, 90, 110))
                hw = int(S * 0.55)
                pygame.draw.rect(surf, body_col, (cx - hw // 2, cy - hw // 2 + bob, hw, hw), border_radius=4)
                head_col = (70, 70, 90) if phase == 1 else (90, 40, 40)
                hx, hy = cx, cy - int(S * 0.35) + bob
                pygame.draw.circle(surf, head_col, (hx, hy), int(S * 0.22))
                eye_col = (200, 60, 60) if phase == 2 else (150, 150, 200)
                pygame.draw.circle(surf, eye_col, (hx - 5, hy - 2), 3)
                pygame.draw.circle(surf, eye_col, (hx + 5, hy - 2), 3)
                
            elif boss_type == 3:
                body_col = (255, 100, 100) if is_hurt else ((255, 220, 50) if phase == 3 else ((180, 60, 200) if phase == 2 else (50, 30, 80)))
                hw = int(S * 0.60)
                by = cy - hw//2 + bob
                pygame.draw.rect(surf, body_col, (cx - hw // 2, by, hw, int(hw * 1.3)), border_radius=5)
                cloak_col = tuple(max(0, c - 30) for c in body_col[:3])
                pygame.draw.rect(surf, cloak_col, (cx - hw // 2 - 3, by + hw, hw + 6, int(hw * 0.5)), border_radius=4)
                crown_col = (220, 180, 40) if phase < 3 else (255, 230, 100)
                pygame.draw.rect(surf, crown_col, (cx - hw // 2 + 2, by - 10, hw - 4, 6), border_radius=2)
                for offset in (-hw // 4, 0, hw // 4):
                    tip_y = by - 10 - (8 if offset == 0 else 5)
                    pygame.draw.polygon(surf, crown_col, [(cx + offset - 3, by - 10), (cx + offset + 3, by - 10), (cx + offset, tip_y)])
                eye_col = {1: (160, 80, 220), 2: (200, 80, 255), 3: (255, 220, 60)}.get(phase, (160, 80, 220))
                pygame.draw.circle(surf, eye_col, (cx - 6, cy - hw // 6 + bob), 3)
                pygame.draw.circle(surf, eye_col, (cx + 6, cy - hw // 6 + bob), 3)
                pygame.draw.circle(surf, (255, 255, 255), (cx - 6, cy - hw // 6 + bob), 1)
                pygame.draw.circle(surf, (255, 255, 255), (cx + 6, cy - hw // 6 + bob), 1)

            frames.append(surf)
        sheets[anim_name] = frames
        
    return sheets
