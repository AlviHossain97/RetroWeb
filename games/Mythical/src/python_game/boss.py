"""
Boss — the Dark Golem with tactical repositioning and navigation-aware movement.
"""
from __future__ import annotations

import math
import random

import pygame

from ai.config_loader import get_boss_config, get_difficulty_config
from ai.influence import choose_tactical_tile
from ai.pathfinding import find_path, has_line_of_sight, quantize_tile
from game_math import oscillate, point_distance, polar_offset, safe_normalize
from settings import TILE_SIZE


from runtime.gba_compat import GBAEntity
from runtime.fixed_point import FixedVec2
from runtime.asset_manager import get_frame, load_sprite_sheet

class Boss(GBAEntity):
    def __init__(self, tile_x, tile_y, boss_id="dark_golem", difficulty_mode="normal", difficulty_config=None):
        super().__init__(float(tile_x), float(tile_y))
        config = get_boss_config(boss_id, difficulty_mode)
        diff = difficulty_config or get_difficulty_config(difficulty_mode)
        boss_mults = diff.get("boss_stat_mults", {})
        ai_mults = diff.get("ai", {})

        self.boss_id = boss_id
        self.spawn_x = self.x
        self.spawn_y = self.y
        self.max_hp = max(1, int(round(config["max_hp"] * boss_mults.get("hp", 1.0))))
        self.hp = self.max_hp
        self.damage = max(1, int(round(config["damage"] * boss_mults.get("damage", 1.0))))
        self.speed = config["speed"] * boss_mults.get("speed", 1.0)
        self.phase = 1
        self.state = "dormant"
        self.state_timer = 0.0
        self.facing = "down"
        self.alive = True
        self.active = False
        self.defeated = False
        self.hurt_timer = 0.0
        self.attack_hit = False
        self.knockback_vx = 0.0
        self.knockback_vy = 0.0
        self.charge_tx = self.x
        self.charge_ty = self.y
        self.current_path: list[tuple[int, int]] = []
        self.desired_tile: tuple[int, int] | None = None
        self.path_recalc_timer = 0.0
        self.last_goal_tile: tuple[int, int] | None = None
        self.reposition_lock = 0.0
        self.debug_color = (255, 120, 80)
        self.last_scores: dict[tuple[int, int], float] = {}
        self.last_map_name = ""
        self.stuck_timer = 0.0
        self.last_pos = (self.x, self.y)

        self.intro_duration = config["intro_duration"]
        self.decision_delay_phase1 = config["decision_delay_phase1"] * boss_mults.get("cooldown", 1.0)
        self.decision_delay_phase2 = config["decision_delay_phase2"] * boss_mults.get("cooldown", 1.0)
        self.attack_cooldown = config["attack_cooldown"] * boss_mults.get("cooldown", 1.0)
        self.charge_telegraph = config["charge_telegraph"]
        self.charge_duration = config["charge_duration"]
        self.slam_duration = config["slam_duration"]
        self.spin_duration = config["spin_duration"]
        self.slam_radius = config["slam_radius"]
        self.spin_radius = config["spin_radius"]
        self.charge_radius = config["charge_radius"]
        self.phase2_threshold = config["phase2_threshold"] * boss_mults.get("phase2_threshold", 1.0)
        self.preferred_range_phase1 = config["preferred_range_phase1"]
        self.preferred_range_phase2 = config["preferred_range_phase2"]
        self.search_radius = max(4, int(round(config["search_radius"] * ai_mults.get("search_radius_scale", 1.0))))
        self.path_refresh_base = config["path_refresh"] * ai_mults.get("path_refresh_scale", 1.0)
        self.reposition_cooldown = config["reposition_cooldown"] * ai_mults.get("reposition_cooldown_scale", 1.0)
        self.pressure_bias = config["pressure_bias"] * boss_mults.get("pressure", 1.0) * ai_mults.get("pressure_scale", 1.0)
        self.flank_bias = config["flank_bias"] * ai_mults.get("flank_bias", 1.0)

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

    def activate(self):
        if self.state == "dormant":
            self.state = "intro"
            self.state_timer = 0.0
            self.active = True

    def snapshot_state(self) -> dict:
        return {
            "hp": self.hp,
            "phase": self.phase,
            "x": self.x,
            "y": self.y,
            "active": self.active,
            "defeated": self.defeated,
        }

    def apply_saved_state(self, data: dict):
        if not data:
            return
        self.hp = max(1, min(self.max_hp, int(data.get("hp", self.hp))))
        self.phase = int(data.get("phase", self.phase))
        self.x = float(data.get("x", self.x))
        self.y = float(data.get("y", self.y))
        self.active = bool(data.get("active", self.active))
        self.defeated = bool(data.get("defeated", self.defeated))
        if self.defeated:
            self.alive = False
            self.state = "death"
        elif self.active:
            self.state = "idle"
        else:
            self.state = "dormant"

    def take_damage(self, dmg, kx=0, ky=0):
        if self.state in ("death", "dormant", "intro"):
            return False
        self.hp -= dmg
        self.knockback_vx = kx * 3
        self.knockback_vy = ky * 3
        self.current_path = []
        self.desired_tile = None
        if self.hp <= 0:
            self.state = "death"
            self.state_timer = 0.0
            self.alive = False
            self.defeated = True
            return True
        if self.hp <= self.max_hp * self.phase2_threshold and self.phase == 1:
            self.phase = 2
            self.speed *= 1.15
        self.state = "hurt"
        self.hurt_timer = 0.3
        self.state_timer = 0.0
        return True

    def dist_to(self, tx, ty):
        return point_distance(self.x, self.y, tx, ty)

    def body_collision(self) -> dict | None:
        """Return collision footprint for player movement blocking.
        Returns None when boss should not block (dormant, dead, intro rising)."""
        if not self.alive or self.state in ("dormant", "death"):
            return None
        if self.state == "intro" and self.state_timer < self.intro_duration * 0.7:
            return None
        return {
            "x": self.x + 0.5,
            "y": self.y + 0.5,
            "radius": 0.8,
        }

    def face_toward(self, tx, ty):
        dx, dy = tx - self.x, ty - self.y
        if abs(dx) > abs(dy):
            self.facing = "right" if dx > 0 else "left"
        else:
            self.facing = "down" if dy > 0 else "up"

    def _can_occupy(self, tilemap, tx, ty, blockers):
        tile = quantize_tile(tx, ty)
        if tilemap.is_solid(tile[0], tile[1]):
            return False
        if blockers and tile in blockers:
            return False
        return True

    def _apply_knockback(self, dt, tilemap, blockers):
        if abs(self.knockback_vx) <= 0.1 and abs(self.knockback_vy) <= 0.1:
            return
        nx = self.x + self.knockback_vx * dt
        ny = self.y + self.knockback_vy * dt
        if self._can_occupy(tilemap, nx, self.y, blockers):
            self.x = nx
        if self._can_occupy(tilemap, self.x, ny, blockers):
            self.y = ny
        self.knockback_vx *= 0.8
        self.knockback_vy *= 0.8

    def _move_toward(self, tx, ty, dt, tilemap, blockers, speed_mult=1.0):
        dx = tx - self.x
        dy = ty - self.y
        nx, ny, _ = safe_normalize(dx, dy)
        self.face_toward(tx, ty)
        mx = nx * self.speed * speed_mult * dt
        my = ny * self.speed * speed_mult * dt
        moved = False
        if self._can_occupy(tilemap, self.x + mx, self.y, blockers):
            self.x += mx
            moved = True
        if self._can_occupy(tilemap, self.x, self.y + my, blockers):
            self.y += my
            moved = True
        return moved

    def _refresh_path(self, tilemap, map_name, goal_tile, blockers):
        actor_tile = quantize_tile(self.x, self.y)
        self.current_path = find_path(tilemap, actor_tile, goal_tile, blockers=blockers, max_nodes=1200)
        self.last_goal_tile = goal_tile
        self.path_recalc_timer = self.path_refresh_base
        self.last_map_name = map_name

    def _follow_path(self, dt, tilemap, blockers):
        if not self.current_path or len(self.current_path) <= 1:
            return False
        actor_tile = quantize_tile(self.x, self.y)
        while len(self.current_path) > 1 and self.current_path[0] == actor_tile:
            self.current_path.pop(0)
        if len(self.current_path) <= 1:
            return False
        nxt = self.current_path[1]
        moved = self._move_toward(nxt[0], nxt[1], dt, tilemap, blockers, speed_mult=1.1)
        if quantize_tile(self.x, self.y) == nxt:
            self.current_path.pop(0)
        return moved

    def _update_stuck_state(self, dt):
        moved = point_distance(self.x, self.y, self.last_pos[0], self.last_pos[1])
        if moved < 0.02:
            self.stuck_timer += dt
        else:
            self.stuck_timer = 0.0
        self.last_pos = (self.x, self.y)

    def _select_desired_tile(self, tilemap, player_tile, player_field):
        desired_range = self.preferred_range_phase1 if self.phase == 1 else self.preferred_range_phase2
        desired_tile, scores = choose_tactical_tile(
            tilemap,
            actor_tile=quantize_tile(self.x, self.y),
            player_tile=player_tile,
            field=player_field,
            desired_range=desired_range,
            search_radius=self.search_radius,
            retreat=False,
            pressure_bias=self.pressure_bias,
            flank_bias=self.flank_bias,
            line_of_sight_bias=0.4,
        )
        self.last_scores = scores
        self.desired_tile = desired_tile
        return desired_tile

    def update(
        self,
        dt,
        player_x,
        player_y,
        tilemap,
        map_name="",
        dynamic_blockers=None,
        player_field=None,
        allow_expensive_ai=True,
    ):
        self.state_timer += dt
        self.path_recalc_timer = max(0.0, self.path_recalc_timer - dt)
        self.reposition_lock = max(0.0, self.reposition_lock - dt)
        blockers = set(dynamic_blockers or set())
        blockers.discard(quantize_tile(self.x, self.y))
        self._apply_knockback(dt, tilemap, blockers)

        if self.state == "dormant":
            return
        if self.state == "intro":
            if self.state_timer > self.intro_duration:
                self.state = "idle"
                self.state_timer = 0.0
            return
        if self.state == "death":
            return
        if self.state == "hurt":
            self.hurt_timer -= dt
            if self.hurt_timer <= 0:
                self.state = "idle"
                self.state_timer = 0.0
            return

        player_tile = quantize_tile(player_x, player_y)
        actor_tile = quantize_tile(self.x, self.y)
        dist = self.dist_to(player_x, player_y)
        preferred_range = self.preferred_range_phase1 if self.phase == 1 else self.preferred_range_phase2
        decision_delay = self.decision_delay_phase1 if self.phase == 1 else self.decision_delay_phase2

        if self.state == "idle":
            self.face_toward(player_x, player_y)
            if self.state_timer >= decision_delay:
                needs_reposition = abs(dist - preferred_range) > 0.8
                if player_field and (needs_reposition or not has_line_of_sight(tilemap, actor_tile, player_tile)):
                    desired_tile = self._select_desired_tile(tilemap, player_tile, player_field)
                    if desired_tile and desired_tile != actor_tile:
                        self.state = "reposition"
                        self.state_timer = 0.0
                        return
                if dist <= self.slam_radius and (self.phase == 1 or random.random() < 0.55):
                    self.state = "slam"
                    self.state_timer = 0.0
                    self.attack_hit = False
                elif self.phase == 2 and dist <= self.spin_radius + 1.1 and random.random() < 0.55:
                    self.state = "spin"
                    self.state_timer = 0.0
                    self.attack_hit = False
                else:
                    self.state = "charge"
                    self.state_timer = 0.0
                    self.attack_hit = False
                    self.charge_tx = player_x
                    self.charge_ty = player_y

        elif self.state == "reposition":
            if self.desired_tile is None:
                self.state = "idle"
                self.state_timer = 0.0
                return
            if actor_tile == self.desired_tile or self.state_timer > 1.4:
                self.state = "idle"
                self.state_timer = 0.0
                self.reposition_lock = self.reposition_cooldown
                self.current_path = []
                return
            if has_line_of_sight(tilemap, actor_tile, self.desired_tile, blockers=blockers):
                self._move_toward(self.desired_tile[0], self.desired_tile[1], dt, tilemap, blockers, speed_mult=1.05)
            else:
                if (
                    not self.current_path
                    or self.last_goal_tile != self.desired_tile
                    or self.path_recalc_timer <= 0
                    or self.last_map_name != map_name
                    or self.stuck_timer > 0.6
                ):
                    self._refresh_path(tilemap, map_name, self.desired_tile, blockers)
                if not self._follow_path(dt, tilemap, blockers):
                    self._move_toward(player_x, player_y, dt, tilemap, blockers)
            self._update_stuck_state(dt)

        elif self.state == "charge":
            if self.state_timer < self.charge_telegraph:
                self.face_toward(self.charge_tx, self.charge_ty)
            elif self.state_timer < self.charge_telegraph + self.charge_duration:
                if not self._move_toward(self.charge_tx, self.charge_ty, dt, tilemap, blockers, speed_mult=3.8):
                    self.state = "slam"
                    self.state_timer = 0.0
                    self.attack_hit = False
            else:
                self.state = "slam"
                self.state_timer = 0.0
                self.attack_hit = False

        elif self.state == "slam":
            if self.state_timer > self.slam_duration:
                self.state = "idle"
                self.state_timer = 0.0

        elif self.state == "spin":
            if self.state_timer < self.spin_duration:
                self._move_toward(player_x, player_y, dt, tilemap, blockers, speed_mult=2.3)
            else:
                self.state = "idle"
                self.state_timer = 0.0

    def render(self, screen, cam_x, cam_y):
        if self.state == "dormant" and not self.active:
            return
        T = TILE_SIZE
        sz = int(T * 1.5)
        sx = int(self.x * T) - cam_x + T // 2 - sz // 2
        sy = int(self.y * T) - cam_y + T // 2 - sz // 2

        if self.state == "death":
            frame_idx = min(3, int(self.state_timer * 3))
            surf = get_frame("boss_1", "death", frame_idx)
            if surf: screen.blit(surf, (sx - sz//2, sy - sz//2))
            return

        shadow = pygame.Surface((sz, sz // 3), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 50), (0, 0, sz, sz // 3))
        screen.blit(shadow, (sx, sy + sz - 4))

        is_hurt = self.state == "hurt" and (self.hurt_timer > 0)
        
        anim_name = f"idle_{self.phase}"
        if is_hurt: anim_name = "hurt"
        
        frame_idx = 0 if is_hurt else int(self.state_timer / 0.15) % 4
        
        if self.state == "intro":
            rise = min(1.0, self.state_timer / 1.5)
            sy += int((1 - rise) * sz)
            
        surf = get_frame("boss_1", anim_name, frame_idx)
        if surf:
            # Special indicator for charge telegraph
            if self.state == "charge" and self.state_timer < self.charge_telegraph:
                if int(self.state_timer * 10) % 2:
                    surf = surf.copy()
                    surf.fill((255, 50, 50, 60), special_flags=pygame.BLEND_RGBA_ADD)
            screen.blit(surf, (sx - sz//2, sy - sz//2))

        if self.state == "slam" and self.state_timer < 0.4:
            r = int(self.state_timer * 120)
            wave = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            alpha = max(0, 200 - int(self.state_timer * 500))
            pygame.draw.circle(wave, (255, 150, 50, alpha), (r, r), r, 3)
            screen.blit(wave, (sx + sz // 2 - r, sy + sz // 2 - r))

        if self.state == "spin":
            for i in range(4):
                angle = self.state_timer * 12 + i * math.pi / 2
                ox, oy = polar_offset(angle, sz * 0.6)
                pygame.draw.circle(screen, (200, 100, 60), (sx + sz // 2 + int(ox), sy + sz // 2 + int(oy)), 5)
