"""
Player entity — movement, animation, combat, health, and simple gear overlays.
On GBA: struct + OAM sprite entry.
"""
import pygame
import math
from game_math import degrees_offset, polar_offset, safe_normalize
from settings import (
    TILE_SIZE, PLAYER_SPEED, PLAYER_MAX_HP, PLAYER_IFRAMES,
    PLAYER_ATTACK_WINDUP, PLAYER_ATTACK_ACTIVE, PLAYER_ATTACK_RECOVERY,
    PLAYER_KNOCKBACK,
)
from combat import get_attack_hitbox, circle_hits_entity
from runtime.asset_manager import get_frame, load_sprite_sheet


from runtime.gba_compat import GBAEntity
from runtime.fixed_point import FixedVec2

from runtime.gba_compat import GBAEntity
from runtime.fixed_point import FixedVec2

class Player(GBAEntity):
    def __init__(self, tile_x: float, tile_y: float):
        super().__init__(tile_x, tile_y)
        self.facing = "down"
        self.moving = False

        # Health
        self.hp = PLAYER_MAX_HP
        self.max_hp = PLAYER_MAX_HP
        self.partial_hp: float = 0.0   # fractional heart accumulator (0.0..1.0)

        # Weapon / attack capability
        self.has_sword = False

        # Combat state
        self.state = "idle"  # idle, attack_windup, attack_active, attack_recovery, hurt, dead
        self.state_timer = 0.0
        self.iframes = 0.0
        self.knockback_vx = 0.0
        self.knockback_vy = 0.0

        # Animation
        self.category_id = "player"
        self.anim_frame = 0
        self.anim_timer = 0.0
        self.anim_speed = 0.13

    @property
    def x(self) -> float:
        return self.pos.xf

    @x.setter
    def x(self, val: float):
        self.pos = FixedVec2(val, self.pos.yf)

    @property
    def y(self) -> float:
        return self.pos.yf

    @y.setter
    def y(self, val: float):
        self.pos = FixedVec2(self.pos.xf, val)

    @property
    def is_alive(self):
        return self.state != "dead"

    @property
    def can_act(self):
        return self.state in ("idle",)

    @property
    def can_attack(self):
        """Player can only attack if they have the sword and are in idle state."""
        return self.has_sword and self.can_act

    @property
    def is_attacking(self):
        return self.state == "attack_active"

    def start_attack(self):
        if not self.can_attack:
            return False
        self.state = "attack_windup"
        self.state_timer = 0
        self.moving = False
        return True

    def take_damage(self, dmg, source_x=None, source_y=None):
        if self.iframes > 0 or self.state == "dead": return False
        self.hp -= dmg
        self.iframes = PLAYER_IFRAMES
        if self.hp <= 0:
            self.hp = 0
            self.state = "dead"
            self.state_timer = 0
            return True
        self.state = "hurt"
        self.state_timer = 0
        # Knockback away from source
        if source_x is not None:
            dx = self.x - source_x
            dy = self.y - source_y
            nx, ny, _ = safe_normalize(dx, dy, minimum=0.1)
            self.knockback_vx = nx * PLAYER_KNOCKBACK
            self.knockback_vy = ny * PLAYER_KNOCKBACK
        return True

    def heal(self, amount):
        if isinstance(amount, float) and amount % 1.0 != 0.0:
            # Fractional heal — accumulate into partial_hp
            self.partial_hp += amount
            whole = int(self.partial_hp)
            if whole > 0:
                self.hp = min(self.max_hp, self.hp + whole)
                self.partial_hp -= whole
        else:
            self.hp = min(self.max_hp, self.hp + int(amount))
        if self.hp >= self.max_hp:
            self.partial_hp = 0.0

    def update(self, dt, input_handler, tilemap, npcs=None, boss_body=None):
        self.state_timer += dt
        if self.iframes > 0:
            self.iframes -= dt

        # Apply knockback
        if abs(self.knockback_vx) > 0.1 or abs(self.knockback_vy) > 0.1:
            nx = self.x + self.knockback_vx * dt
            ny = self.y + self.knockback_vy * dt
            if tilemap.is_passable(nx, self.y) and not self._hits_npc(nx, self.y, npcs) and not self._hits_boss(nx, self.y, boss_body):
                self.x = nx
            if tilemap.is_passable(self.x, ny) and not self._hits_npc(self.x, ny, npcs) and not self._hits_boss(self.x, ny, boss_body):
                self.y = ny
            self.knockback_vx *= 0.82
            self.knockback_vy *= 0.82

        # State machine
        if self.state == "dead":
            return
        elif self.state == "hurt":
            if self.state_timer > 0.25:
                self.state = "idle"
                self.state_timer = 0
            return
        elif self.state == "attack_windup":
            if self.state_timer > PLAYER_ATTACK_WINDUP:
                self.state = "attack_active"
                self.state_timer = 0
            return
        elif self.state == "attack_active":
            if self.state_timer > PLAYER_ATTACK_ACTIVE:
                self.state = "attack_recovery"
                self.state_timer = 0
            return
        elif self.state == "attack_recovery":
            if self.state_timer > PLAYER_ATTACK_RECOVERY:
                self.state = "idle"
                self.state_timer = 0
            return

        # Idle: process movement
        dx, dy = 0.0, 0.0
        if input_handler.is_held("up"):
            dy = -PLAYER_SPEED * dt; self.facing = "up"
        elif input_handler.is_held("down"):
            dy = PLAYER_SPEED * dt; self.facing = "down"
        if input_handler.is_held("left"):
            dx = -PLAYER_SPEED * dt; self.facing = "left"
        elif input_handler.is_held("right"):
            dx = PLAYER_SPEED * dt; self.facing = "right"
        self.moving = dx != 0 or dy != 0

        new_x = self.x + dx
        if tilemap.is_passable(new_x, self.y) and not self._hits_npc(new_x, self.y, npcs) and not self._hits_boss(new_x, self.y, boss_body):
            self.x = new_x
        new_y = self.y + dy
        if tilemap.is_passable(self.x, new_y) and not self._hits_npc(self.x, new_y, npcs) and not self._hits_boss(self.x, new_y, boss_body):
            self.y = new_y

        # Walk animation
        if self.moving:
            self.anim_timer += dt
            if self.anim_timer >= self.anim_speed:
                self.anim_timer = 0
                self.anim_frame = (self.anim_frame + 1) % 4
        else:
            self.anim_frame = 0
            self.anim_timer = 0

    def _hits_npc(self, tx, ty, npcs):
        if not npcs: return False
        cx, cy = int(tx + 0.5), int(ty + 0.5)
        return any(npc.occupies(cx, cy) for npc in npcs)

    def _hits_boss(self, tx, ty, boss_body):
        """Check if the player position overlaps the boss body collision footprint.
        boss_body is None or a dict with {x, y, radius} in tile coords."""
        if self.state == "hurt":
            # Let knockback and recovery move the player out of boss overlap
            # instead of pinning them in place.
            return False
        if not boss_body:
            return False
        bx = boss_body["x"]
        by = boss_body["y"]
        br = boss_body["radius"]
        # Player center vs boss circle collision
        pcx = tx + 0.5
        pcy = ty + 0.5
        player_half = 0.35  # player collision half-size
        # AABB vs circle: closest point on player box to boss center
        closest_x = max(pcx - player_half, min(bx, pcx + player_half))
        closest_y = max(pcy - player_half, min(by, pcy + player_half))
        dist_sq = (closest_x - bx) ** 2 + (closest_y - by) ** 2
        return dist_sq < br * br

    def get_interact_tile(self):
        offsets = {"up":(0,-1),"down":(0,1),"left":(-1,0),"right":(1,0)}
        ox, oy = offsets[self.facing]
        return int(self.x + 0.5) + ox, int(self.y + 0.5) + oy

    def get_attack_hitbox(self):
        return get_attack_hitbox(self.x, self.y, self.facing)

    def _draw_equipment_back(self, screen, sx, sy, equipment):
        if not equipment:
            return
        equipped = getattr(equipment, "equipped", {})
        armor_items = [equipped.get("armor_1"), equipped.get("armor_2")]
        if "shadow_cloak" in armor_items:
            cloak = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            if self.facing == "up":
                points = [(8, 10), (24, 10), (22, 26), (16, 30), (10, 26)]
            elif self.facing == "left":
                points = [(10, 9), (24, 11), (22, 26), (12, 30), (8, 20)]
            elif self.facing == "right":
                points = [(8, 11), (22, 9), (24, 20), (20, 30), (10, 26)]
            else:
                points = [(8, 8), (24, 8), (26, 24), (16, 31), (6, 24)]
            pygame.draw.polygon(cloak, (42, 34, 68, 220), points)
            pygame.draw.line(cloak, (90, 82, 128, 180), points[0], points[1], 2)
            screen.blit(cloak, (sx, sy))

    def _draw_equipment_front(self, screen, sx, sy, equipment):
        if not equipment:
            return
        equipped = getattr(equipment, "equipped", {})
        armor_items = [equipped.get("armor_1"), equipped.get("armor_2")]
        accessory = equipped.get("accessory")

        armor_overlay = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        if any(item in armor_items for item in ("ascended_aegis", "iron_armor", "shadow_mail", "leather_armor", "mage_robes")):
            if "ascended_aegis" in armor_items:
                chest = (232, 220, 170, 185)
                trim = (255, 244, 200, 220)
            elif "shadow_mail" in armor_items:
                chest = (76, 80, 112, 170)
                trim = (122, 126, 170, 210)
            elif "mage_robes" in armor_items:
                chest = (80, 92, 180, 165)
                trim = (140, 170, 255, 210)
            elif "iron_armor" in armor_items:
                chest = (126, 132, 150, 170)
                trim = (176, 182, 205, 210)
            else:
                chest = (126, 94, 62, 165)
                trim = (175, 136, 92, 210)

            pygame.draw.rect(armor_overlay, chest, (8, 10, 16, 12), border_radius=3)
            pygame.draw.line(armor_overlay, trim, (16, 10), (16, 22), 2)
            pygame.draw.line(armor_overlay, trim, (10, 12), (22, 12), 2)
            pygame.draw.rect(armor_overlay, trim, (7, 9, 18, 14), 1, border_radius=3)
            if "ascended_aegis" in armor_items:
                pygame.draw.circle(armor_overlay, (255, 248, 210, 190), (16, 16), 3)

        if accessory:
            if accessory == "sovereign_crown":
                pygame.draw.polygon(armor_overlay, (220, 192, 70, 220),
                                    [(10, 6), (13, 2), (16, 6), (19, 2), (22, 6), (22, 9), (10, 9)])
                pygame.draw.circle(armor_overlay, (255, 235, 120, 220), (16, 5), 2)
            else:
                chain = (190, 190, 205, 190)
                gem = (120, 220, 180, 230) if accessory == "revenant_core" else (180, 120, 220, 220)
                pygame.draw.line(armor_overlay, chain, (12, 11), (16, 15), 1)
                pygame.draw.line(armor_overlay, chain, (20, 11), (16, 15), 1)
                pygame.draw.circle(armor_overlay, gem, (16, 17), 3)
                if accessory == "revenant_core":
                    pygame.draw.circle(armor_overlay, (220, 255, 245, 120), (16, 17), 5, 1)

        screen.blit(armor_overlay, (sx, sy))

    def render(self, screen, cam_x, cam_y, equipment=None):
        T = TILE_SIZE
        sx = int(self.x * T) - cam_x
        sy = int(self.y * T) - cam_y

        # Invisible during iframes (blink)
        if self.iframes > 0 and int(self.iframes * 12) % 2:
            return

        self._draw_equipment_back(screen, sx, sy, equipment)

        # Draw sprite
        frame = get_frame(self.category_id, self.facing, self.anim_frame)
        if frame:
            screen.blit(frame, (sx, sy))
        else:
            pygame.draw.rect(screen, (70, 130, 70), (sx, sy, T, T))
            
        self._draw_equipment_front(screen, sx, sy, equipment)

        # Attack effect — different for bow vs melee
        if self.state in ("attack_active", "attack_windup"):
            offsets = {"up":(0,-T//2),"down":(0,T//2),"left":(-T//2,0),"right":(T//2,0)}
            ox, oy = offsets[self.facing]
            cx = sx + T//2 + ox
            cy = sy + T//2 + oy

            is_bow = getattr(self, '_using_bow', False)

            if self.state == "attack_active":
                if is_bow:
                    # Arrow projectile flying outward
                    angle_offsets = {"up": -90, "down": 90, "left": 180, "right": 0}
                    progress = self.state_timer / PLAYER_ATTACK_ACTIVE
                    # Arrow shaft
                    dist = T * (0.3 + 2.0 * progress)
                    ox, oy = degrees_offset(angle_offsets[self.facing], dist)
                    ax = sx + T // 2 + int(ox)
                    ay = sy + T // 2 + int(oy)
                    txo, tyo = degrees_offset(angle_offsets[self.facing], 8)
                    tail_x = ax - int(txo)
                    tail_y = ay - int(tyo)
                    pygame.draw.line(screen, (200, 180, 140), (tail_x, tail_y), (ax, ay), 2)
                    # Arrowhead
                    pygame.draw.circle(screen, (255, 240, 180), (ax, ay), 2)
                    # Trail particles
                    for i in range(3):
                        tp = max(0, progress - i * 0.08)
                        td = T * (0.3 + 2.0 * tp)
                        tox, toy = degrees_offset(angle_offsets[self.facing], td)
                        tx = sx + T // 2 + int(tox)
                        ty = sy + T // 2 + int(toy)
                        alpha = max(0, 120 - i * 40)
                        trail_s = pygame.Surface((4, 4), pygame.SRCALPHA)
                        pygame.draw.circle(trail_s, (200, 180, 140, alpha), (2, 2), 2)
                        screen.blit(trail_s, (tx - 2, ty - 2))
                else:
                    # Melee slash arc
                    angle_offsets = {"up": -90, "down": 90, "left": 180, "right": 0}
                    progress = self.state_timer / PLAYER_ATTACK_ACTIVE
                    for i in range(5):
                        a = math.radians(angle_offsets[self.facing] + (-40 + 80 * progress) + (i * 8 - 16))
                        r = T * 0.4 + i * 2
                        ox, oy = polar_offset(a, r)
                        px_ = cx + int(ox)
                        py_ = cy + int(oy)
                        pygame.draw.circle(screen, (255, 255, 200), (px_, py_), 3)
            elif self.state == "attack_windup":
                if is_bow:
                    # Bow draw — arc behind player
                    pcx, pcy = sx + T // 2, sy + T // 2
                    angle_offsets = {"up": 90, "down": -90, "left": 0, "right": 180}
                    ba = math.radians(angle_offsets[self.facing])
                    box, boy = polar_offset(ba, 6)
                    bx_ = pcx + int(box)
                    by_ = pcy + int(boy)
                    pygame.draw.arc(screen, (160, 120, 60),
                                    (bx_ - 8, by_ - 10, 16, 20),
                                    ba - 1.2, ba + 1.2, 2)
                    # String
                    s1x, s1y = polar_offset(ba - 1.0, 8)
                    s2x, s2y = polar_offset(ba + 1.0, 8)
                    pygame.draw.line(screen, (180, 170, 150),
                                     (bx_ + int(s1x), by_ + int(s1y)),
                                     (bx_ + int(s2x), by_ + int(s2y)), 1)
                else:
                    pygame.draw.circle(screen, (255, 200, 100), (cx, cy), 4)
