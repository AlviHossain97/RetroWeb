"""
Enemy system — FSM-driven enemies with layered navigation and tactical positioning.
States: idle, alerted, chase, reposition, retreat, attack, hurt, death.
"""
from __future__ import annotations

import math
import random

import pygame

from ai.config_loader import get_difficulty_config, get_enemy_config
from ai.influence import choose_tactical_tile
from ai.pathfinding import find_path, has_line_of_sight, quantize_tile
from game_math import oscillate, point_distance, polar_offset, safe_normalize
from settings import TILE_SIZE, ENEMY_KNOCKBACK


from runtime.gba_compat import GBAEntity
from runtime.fixed_point import FixedVec2

class Enemy(GBAEntity):
    def __init__(
        self,
        etype: str,
        tile_x: float,
        tile_y: float,
        spawn_id: str | None = None,
        difficulty_mode: str = "normal",
        difficulty_config: dict | None = None,
    ):
        super().__init__(tile_x, tile_y)
        base = get_enemy_config(etype, difficulty_mode)
        diff = difficulty_config or get_difficulty_config(difficulty_mode)
        enemy_mults = diff.get("enemy_stat_mults", {})
        ai_mults = diff.get("ai", {})

        self.etype = etype
        self.spawn_id = spawn_id or f"{etype}_{int(tile_x)}_{int(tile_y)}"
        self.spawn_x = self.x  # x/y are properties backed by self.pos (FixedVec2)
        self.spawn_y = self.y

        self.max_hp = max(1, int(round(base["max_hp"] * enemy_mults.get("hp", 1.0))))
        self.hp = self.max_hp
        self.damage = max(1, int(round(base["damage"] * enemy_mults.get("damage", 1.0))))
        self.speed = base["speed"] * enemy_mults.get("speed", 1.0)
        self.chase_range = base["chase_range"] * enemy_mults.get("chase_range", 1.0)
        self.attack_range = base["attack_range"]
        self.attack_cd = base["attack_cd"] * enemy_mults.get("attack_cd", 1.0)
        self.color = tuple(base["color"])
        self.size = base["size"]
        self.xp = base.get("xp", 1)
        self.drops = base.get("drops", [])

        ai_cfg = base.get("ai", {})
        self.active_radius = ai_cfg.get("active_radius", self.chase_range + 3.0)
        self.preferred_range = ai_cfg.get("preferred_range", self.attack_range)
        self.search_radius = max(2, int(round(ai_cfg.get("search_radius", 5) * ai_mults.get("search_radius_scale", 1.0))))
        self.direct_move_range = ai_cfg.get("direct_move_range", self.chase_range)
        self.path_refresh_base = ai_cfg.get("path_refresh", 0.75) * ai_mults.get("path_refresh_scale", 1.0)
        self.reposition_cooldown = ai_cfg.get("reposition_cooldown", 0.8) * ai_mults.get("reposition_cooldown_scale", 1.0)
        self.stuck_timeout = ai_cfg.get("stuck_timeout", 0.6)
        self.aggro_confidence = ai_cfg.get("aggro_confidence", 1.0) * enemy_mults.get("aggro_confidence", 1.0)
        self.tactical_enabled = bool(ai_cfg.get("tactical_enabled", False))
        self.retreat_enabled = bool(ai_cfg.get("retreat_enabled", False))
        self.retreat_hp_ratio = ai_cfg.get("retreat_hp_ratio", 0.0) * ai_mults.get("retreat_bias", 1.0)
        self.flank_bias = ai_cfg.get("flank_bias", 0.0) * ai_mults.get("flank_bias", 1.0) * ai_mults.get("tactical_quality", 1.0)
        self.pressure_bias = ai_cfg.get("pressure_bias", 1.0) * ai_mults.get("pressure_scale", 1.0)
        self.range_weight = ai_cfg.get("range_weight", 1.0)
        self.line_of_sight_bias = ai_cfg.get("line_of_sight_bias", 0.0) * ai_mults.get("tactical_quality", 1.0)

        # FSM
        self.state = "idle"
        self.state_timer = 0.0
        self.facing = "down"
        self.attack_timer = 0.0
        self.hurt_timer = 0.0
        self.death_timer = 0.0
        self.alive = True
        self.has_attacked = False

        # Motion and navigation
        self.knockback_vx = 0.0
        self.knockback_vy = 0.0
        self.anim_timer = 0.0
        self.idle_dir_timer = random.uniform(1.0, 2.5)
        self.current_path: list[tuple[int, int]] = []
        self.desired_tile: tuple[int, int] | None = None
        self.last_scores: dict[tuple[int, int], float] = {}
        self.path_recalc_timer = 0.0
        self.last_goal_tile: tuple[int, int] | None = None
        self.last_map_name = ""
        self.last_pos = (self.x, self.y)
        self.stuck_timer = 0.0
        self.reposition_lock = 0.0
        self.debug_color = tuple(max(40, min(255, c + 20)) for c in self.color)
        self.loot_spawned = False

    # ── Canonical identity contract ────────────────────────────────────
    # gameplay.py, bestiary, XP, drops, and debug all use these names.

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
    def enemy_type(self) -> str:
        """Canonical runtime identity used by gameplay, bestiary, XP, drops."""
        return self.etype

    @property
    def xp_reward(self) -> int:
        """XP granted on kill."""
        return self.xp

    def dist_to(self, tx, ty):
        return point_distance(self.x, self.y, tx, ty)

    def face_toward(self, tx, ty):
        dx, dy = tx - self.x, ty - self.y
        if abs(dx) > abs(dy):
            self.facing = "right" if dx > 0 else "left"
        else:
            self.facing = "down" if dy > 0 else "up"

    def take_damage(self, dmg, knockback_x=0, knockback_y=0):
        if self.state == "death":
            return False
        self.hp -= dmg
        self.knockback_vx = knockback_x * ENEMY_KNOCKBACK
        self.knockback_vy = knockback_y * ENEMY_KNOCKBACK
        self.current_path = []
        self.desired_tile = None
        if self.hp <= 0:
            self.state = "death"
            self.death_timer = 0.5
            self.alive = False
        else:
            self.state = "hurt"
            self.hurt_timer = 0.28
            self.state_timer = 0.0
        return True

    @property
    def is_dead(self):
        return self.state == "death"

    @property
    def should_remove(self):
        return self.state == "death" and self.death_timer <= 0

    def _apply_knockback(self, dt, tilemap, blockers):
        if abs(self.knockback_vx) <= 0.1 and abs(self.knockback_vy) <= 0.1:
            return
        nx = self.x + self.knockback_vx * dt
        ny = self.y + self.knockback_vy * dt
        if self._can_occupy(tilemap, nx, self.y, blockers):
            self.x = nx
        if self._can_occupy(tilemap, self.x, ny, blockers):
            self.y = ny
        self.knockback_vx *= 0.85
        self.knockback_vy *= 0.85

    def _can_occupy(self, tilemap, tx, ty, blockers):
        tile = quantize_tile(tx, ty)
        if tilemap.is_solid(tile[0], tile[1]):
            return False
        if blockers and tile in blockers:
            return False
        return True

    def _move_toward(self, target_x, target_y, dt, tilemap, blockers):
        dx = target_x - self.x
        dy = target_y - self.y
        nx, ny, _ = safe_normalize(dx, dy)
        self.face_toward(target_x, target_y)
        mx = nx * self.speed * dt
        my = ny * self.speed * dt
        moved = False
        if self._can_occupy(tilemap, self.x + mx, self.y, blockers):
            self.x += mx
            moved = True
        if self._can_occupy(tilemap, self.x, self.y + my, blockers):
            self.y += my
            moved = True
        return moved

    def _follow_path(self, dt, tilemap, blockers):
        if not self.current_path:
            return False
        actor_tile = quantize_tile(self.x, self.y)
        while len(self.current_path) > 1 and self.current_path[0] == actor_tile:
            self.current_path.pop(0)
        if len(self.current_path) <= 1:
            return False
        nxt = self.current_path[1]
        moved = self._move_toward(nxt[0], nxt[1], dt, tilemap, blockers)
        if quantize_tile(self.x, self.y) == nxt:
            self.current_path.pop(0)
        return moved

    def _refresh_path(self, tilemap, map_name, goal_tile, blockers):
        actor_tile = quantize_tile(self.x, self.y)
        self.current_path = find_path(tilemap, actor_tile, goal_tile, blockers=blockers, max_nodes=900)
        self.last_goal_tile = goal_tile
        self.path_recalc_timer = self.path_refresh_base
        self.last_map_name = map_name

    def _movement_blockers(self, dynamic_blockers):
        if not dynamic_blockers:
            return set()
        tile = quantize_tile(self.x, self.y)
        return {blocker for blocker in dynamic_blockers if blocker != tile}

    def _update_stuck_state(self, dt):
        moved = point_distance(self.x, self.y, self.last_pos[0], self.last_pos[1])
        if moved < 0.02:
            self.stuck_timer += dt
        else:
            self.stuck_timer = 0.0
        self.last_pos = (self.x, self.y)

    def _should_use_tactics(self, allow_expensive_ai):
        return allow_expensive_ai and self.tactical_enabled

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
        self.anim_timer += dt
        self.state_timer += dt
        self.path_recalc_timer = max(0.0, self.path_recalc_timer - dt)
        self.reposition_lock = max(0.0, self.reposition_lock - dt)

        blockers = self._movement_blockers(dynamic_blockers)
        self._apply_knockback(dt, tilemap, blockers)

        dist = self.dist_to(player_x, player_y)
        player_tile = quantize_tile(player_x, player_y)
        actor_tile = quantize_tile(self.x, self.y)
        los_to_player = has_line_of_sight(tilemap, actor_tile, player_tile)

        if self.state == "death":
            self.death_timer -= dt
            return

        if self.state == "hurt":
            self.hurt_timer -= dt
            if self.hurt_timer <= 0:
                self.state = "chase"
                self.state_timer = 0.0
            return

        if not allow_expensive_ai and dist > self.chase_range * 0.8 and self.state not in ("attack", "alerted"):
            self.state = "idle"
            self.current_path = []
            self.desired_tile = None

        if self.state == "idle":
            self.idle_dir_timer -= dt
            if self.idle_dir_timer <= 0:
                self.facing = random.choice(["up", "down", "left", "right"])
                self.idle_dir_timer = random.uniform(1.2, 2.8)
            if dist <= self.chase_range * self.aggro_confidence:
                self.state = "alerted"
                self.state_timer = 0.0
                self.current_path = []
                self.desired_tile = None

        elif self.state == "alerted":
            self.face_toward(player_x, player_y)
            if self.state_timer >= 0.18:
                self.state = "chase"
                self.state_timer = 0.0

        elif self.state == "attack":
            self.attack_timer += dt
            if self.attack_timer > 0.24 and not self.has_attacked:
                self.has_attacked = True
            if self.attack_timer > self.attack_cd:
                self.state = "chase"
                self.state_timer = 0.0
                self.has_attacked = False

        elif self.state in ("chase", "reposition", "retreat"):
            if dist > self.chase_range * 1.7 and self.state != "retreat":
                self.state = "idle"
                self.current_path = []
                self.desired_tile = None
                self.state_timer = 0.0
                return

            low_hp = (self.hp / max(1, self.max_hp)) <= self.retreat_hp_ratio
            wants_retreat = self.retreat_enabled and low_hp and dist < self.preferred_range + 1.4

            if wants_retreat and self.state != "retreat":
                self.state = "retreat"
                self.current_path = []
                self.desired_tile = None
                self.state_timer = 0.0

            in_attack_range = dist <= self.attack_range * 1.08
            if in_attack_range and (los_to_player or dist <= 1.05):
                self.state = "attack"
                self.attack_timer = 0.0
                self.state_timer = 0.0
                self.has_attacked = False
                self.current_path = []
                return

            use_tactics = self._should_use_tactics(allow_expensive_ai)
            needs_reposition = use_tactics and self.reposition_lock <= 0 and abs(dist - self.preferred_range) > 0.7

            if self.state == "chase" and needs_reposition:
                self.state = "reposition"
                self.state_timer = 0.0

            if self.state in ("reposition", "retreat"):
                desired_range = self.preferred_range + (1.1 if self.state == "retreat" else 0.0)
                desired_tile, score_map = choose_tactical_tile(
                    tilemap,
                    actor_tile=actor_tile,
                    player_tile=player_tile,
                    field=player_field,
                    desired_range=desired_range,
                    search_radius=self.search_radius,
                    retreat=self.state == "retreat",
                    pressure_bias=self.pressure_bias,
                    flank_bias=self.flank_bias,
                    line_of_sight_bias=self.line_of_sight_bias,
                    retreat_bias=max(1.0, self.retreat_hp_ratio * 3.5),
                ) if player_field else (None, {})
                self.last_scores = score_map
                self.desired_tile = desired_tile
                if desired_tile is None or desired_tile == actor_tile:
                    if self.state_timer > 0.35:
                        self.state = "chase"
                        self.state_timer = 0.0
                    return

                if actor_tile == desired_tile or self.state_timer > 1.5:
                    self.reposition_lock = self.reposition_cooldown
                    self.state = "chase"
                    self.state_timer = 0.0
                    self.current_path = []
                    return

                if has_line_of_sight(tilemap, actor_tile, desired_tile, blockers=blockers) and dist <= self.direct_move_range + 2.0:
                    self._move_toward(desired_tile[0], desired_tile[1], dt, tilemap, blockers)
                else:
                    if (
                        not self.current_path
                        or self.last_goal_tile != desired_tile
                        or self.path_recalc_timer <= 0
                        or self.last_map_name != map_name
                        or self.stuck_timer >= self.stuck_timeout
                    ):
                        self._refresh_path(tilemap, map_name, desired_tile, blockers)
                    if not self._follow_path(dt, tilemap, blockers):
                        self._move_toward(player_x, player_y, dt, tilemap, blockers)
            else:
                self.desired_tile = player_tile
                if los_to_player and dist <= self.direct_move_range:
                    self.current_path = []
                    self._move_toward(player_x, player_y, dt, tilemap, blockers)
                else:
                    if (
                        not self.current_path
                        or self.last_goal_tile != player_tile
                        or self.path_recalc_timer <= 0
                        or self.last_map_name != map_name
                        or self.stuck_timer >= self.stuck_timeout
                    ):
                        self._refresh_path(tilemap, map_name, player_tile, blockers)
                    if not self._follow_path(dt, tilemap, blockers):
                        self._move_toward(player_x, player_y, dt, tilemap, blockers)

            self.face_toward(player_x, player_y)
            self._update_stuck_state(dt)

    def render(self, screen, cam_x, cam_y):
        T = TILE_SIZE
        sx = int(self.x * T) - cam_x
        sy = int(self.y * T) - cam_y
        sz = int(T * self.size)
        offset = (T - sz) // 2

        if self.state == "death":
            alpha = max(0, int(255 * (self.death_timer / 0.5)))
            surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
            c = (*self.color, alpha)
            pygame.draw.ellipse(surf, c, (0, sz // 4, sz, sz // 2))
            screen.blit(surf, (sx + offset, sy + offset))
            return

        shadow = pygame.Surface((sz, sz // 3), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 40), (0, 0, sz, sz // 3))
        screen.blit(shadow, (sx + offset, sy + T - sz // 4))

        color = (255, 255, 255) if self.state == "hurt" and int(self.hurt_timer * 20) % 2 else self.color
        dark = tuple(max(0, c - 40) for c in self.color)
        bob = int(oscillate(self.anim_timer, 4, amplitude=2))
        bx, by = sx + offset, sy + offset + bob

        if self.etype == "slime":
            squash = int(abs(oscillate(self.anim_timer, 3, amplitude=2)))
            pygame.draw.ellipse(screen, color, (bx, by + squash, sz, sz - squash))
            ew = sz // 5
            pygame.draw.circle(screen, (255, 255, 255), (bx + sz // 3, by + sz // 3 + squash), ew)
            pygame.draw.circle(screen, (255, 255, 255), (bx + sz * 2 // 3, by + sz // 3 + squash), ew)
            pygame.draw.circle(screen, (20, 20, 20), (bx + sz // 3, by + sz // 3 + squash + 1), ew // 2)
            pygame.draw.circle(screen, (20, 20, 20), (bx + sz * 2 // 3, by + sz // 3 + squash + 1), ew // 2)

        elif self.etype == "bat":
            wing = int(oscillate(self.anim_timer, 10, amplitude=4))
            pygame.draw.ellipse(screen, color, (bx - 4, by + 4 + wing, sz // 2, sz // 2))
            pygame.draw.ellipse(screen, color, (bx + sz // 2 + 4, by + 4 - wing, sz // 2, sz // 2))
            pygame.draw.ellipse(screen, dark, (bx + 4, by, sz - 8, sz))
            pygame.draw.circle(screen, (255, 50, 50), (bx + sz // 3, by + sz // 3), 2)
            pygame.draw.circle(screen, (255, 50, 50), (bx + sz * 2 // 3, by + sz // 3), 2)

        elif self.etype == "skeleton":
            pygame.draw.rect(screen, color, (bx + sz // 4, by + sz // 4, sz // 2, sz * 3 // 4), border_radius=3)
            pygame.draw.circle(screen, color, (bx + sz // 2, by + sz // 4), sz // 4)
            pygame.draw.rect(screen, (20, 20, 20), (bx + sz // 3 - 1, by + sz // 5, 3, 4))
            pygame.draw.rect(screen, (20, 20, 20), (bx + sz * 2 // 3 - 2, by + sz // 5, 3, 4))

        elif self.etype == "golem":
            pygame.draw.rect(screen, color, (bx + 2, by + sz // 6, sz - 4, sz * 5 // 6), border_radius=4)
            pygame.draw.rect(screen, color, (bx + sz // 4, by, sz // 2, sz // 3), border_radius=3)
            pygame.draw.circle(screen, (200, 100, 50), (bx + sz // 3, by + sz // 6), 3)
            pygame.draw.circle(screen, (200, 100, 50), (bx + sz * 2 // 3, by + sz // 6), 3)

        elif self.etype == "wraith" or self.etype == "ascended_wraith":
            # Ghostly floating shape with wispy edges
            ghost_bob = int(oscillate(self.anim_timer, 5, amplitude=3))
            gs = pygame.Surface((sz + 8, sz + 8), pygame.SRCALPHA)
            alpha = 160 if self.etype == "wraith" else 180
            gc = (*color, alpha)
            # Main body (tapered bottom)
            pygame.draw.ellipse(gs, gc, (4, 2, sz, sz * 2 // 3))
            # Wispy tail
            for i in range(3):
                wx = 4 + sz // 4 + i * (sz // 3)
                wy = sz * 2 // 3 + int(oscillate(self.anim_timer, 6, amplitude=2, phase=i))
                pygame.draw.ellipse(gs, gc, (wx - 3, wy, 8, 10))
            screen.blit(gs, (bx - 4, by + ghost_bob - 4))
            # Eyes (glowing)
            eye_col = (255, 120, 255) if self.etype == "ascended_wraith" else (200, 100, 255)
            pygame.draw.circle(screen, eye_col, (bx + sz // 3, by + sz // 3 + ghost_bob), 3)
            pygame.draw.circle(screen, eye_col, (bx + sz * 2 // 3, by + sz // 3 + ghost_bob), 3)

        elif self.etype == "bone_archer":
            # Skeleton with a bow shape
            pygame.draw.rect(screen, color, (bx + sz // 4, by + sz // 4, sz // 2, sz * 3 // 4), border_radius=2)
            pygame.draw.circle(screen, color, (bx + sz // 2, by + sz // 5), sz // 4)
            # Bow on the side
            bow_x = bx + sz - 4
            pygame.draw.arc(screen, (140, 100, 50),
                            (bow_x - 6, by + sz // 6, 10, sz * 2 // 3), 1.0, 5.3, 2)
            # Eye sockets
            pygame.draw.rect(screen, (20, 20, 20), (bx + sz // 3 - 1, by + sz // 6, 3, 3))
            pygame.draw.rect(screen, (20, 20, 20), (bx + sz * 2 // 3 - 2, by + sz // 6, 3, 3))

        elif self.etype == "corrupted_knight":
            # Armored figure — bulky with helmet
            pygame.draw.rect(screen, dark, (bx + 2, by + sz // 5, sz - 4, sz * 4 // 5), border_radius=3)
            # Helmet
            pygame.draw.rect(screen, color, (bx + sz // 5, by, sz * 3 // 5, sz // 3), border_radius=4)
            # Visor slit
            pygame.draw.rect(screen, (180, 40, 40), (bx + sz // 3, by + sz // 6, sz // 3, 3))
            # Shoulder pauldrons
            pygame.draw.circle(screen, color, (bx + 3, by + sz // 4), sz // 5)
            pygame.draw.circle(screen, color, (bx + sz - 3, by + sz // 4), sz // 5)

        elif self.etype == "revenant":
            # Undead warrior — tattered cloak shape
            pygame.draw.rect(screen, color, (bx + sz // 5, by + sz // 6, sz * 3 // 5, sz * 3 // 4), border_radius=3)
            pygame.draw.circle(screen, color, (bx + sz // 2, by + sz // 5), sz // 4)
            # Tattered bottom edge
            for i in range(4):
                tx_ = bx + sz // 5 + i * (sz * 3 // 5) // 4
                pygame.draw.line(screen, dark, (tx_, by + sz * 11 // 12),
                                 (tx_ + 2, by + sz + 3), 2)
            # Glowing eyes
            pygame.draw.circle(screen, (180, 60, 200), (bx + sz // 3, by + sz // 5), 2)
            pygame.draw.circle(screen, (180, 60, 200), (bx + sz * 2 // 3, by + sz // 5), 2)

        elif self.etype == "void_shade":
            # Dark flickering shape
            flicker = int(oscillate(self.anim_timer, 12, amplitude=2))
            vs = pygame.Surface((sz + 4, sz + 4), pygame.SRCALPHA)
            vc = (*color, 140)
            pygame.draw.ellipse(vs, vc, (2 + flicker, 2, sz, sz))
            screen.blit(vs, (bx - 2, by - 2))
            # Void eyes
            pygame.draw.circle(screen, (120, 40, 255), (bx + sz // 3, by + sz // 3), 3)
            pygame.draw.circle(screen, (120, 40, 255), (bx + sz * 2 // 3, by + sz // 3), 3)
            # Dark tendrils
            for i in range(3):
                ta = self.anim_timer * 4 + i * 2.1
                ox, oy = polar_offset(ta, 1.0)
                tx_ = bx + sz // 2 + int(4 * ox)
                ty_ = by + sz * 3 // 4 + int(3 * oy)
                pygame.draw.line(screen, dark, (bx + sz // 2, by + sz * 2 // 3), (tx_, ty_), 2)

        elif self.etype == "crystal_colossus":
            # Large crystalline body
            pts = [(bx + sz // 2, by), (bx + sz - 2, by + sz // 2),
                   (bx + sz * 3 // 4, by + sz), (bx + sz // 4, by + sz),
                   (bx + 2, by + sz // 2)]
            pygame.draw.polygon(screen, color, pts)
            pygame.draw.polygon(screen, dark, pts, 2)
            # Crystal facets
            lt = tuple(min(255, c + 60) for c in self.color)
            pygame.draw.line(screen, lt, (bx + sz // 2, by + 4), (bx + sz * 3 // 4, by + sz // 2), 2)
            pygame.draw.line(screen, lt, (bx + sz // 2, by + 4), (bx + sz // 4, by + sz // 2), 2)
            # Eye
            pygame.draw.circle(screen, (200, 255, 255), (bx + sz // 2, by + sz // 3), 4)
            pygame.draw.circle(screen, (100, 200, 240), (bx + sz // 2, by + sz // 3), 2)

        elif self.etype == "mythic_sentinel":
            # Elite golden guardian
            pygame.draw.rect(screen, color, (bx + 3, by + sz // 5, sz - 6, sz * 4 // 5), border_radius=4)
            pygame.draw.rect(screen, color, (bx + sz // 4, by, sz // 2, sz // 3), border_radius=3)
            # Crown/crest
            lt = tuple(min(255, c + 40) for c in self.color)
            for i in range(3):
                tip_x = bx + sz // 3 + i * (sz // 6)
                pygame.draw.polygon(screen, lt, [
                    (tip_x - 2, by + 2), (tip_x + 2, by + 2), (tip_x, by - 4)])
            # Glowing eyes
            pygame.draw.circle(screen, (255, 220, 60), (bx + sz // 3, by + sz // 6), 3)
            pygame.draw.circle(screen, (255, 220, 60), (bx + sz * 2 // 3, by + sz // 6), 3)

        else:
            pygame.draw.rect(screen, color, (bx, by, sz, sz), border_radius=4)

        if self.hp < self.max_hp and self.state != "death":
            bar_w = sz
            bar_h = 3
            bar_x = sx + offset
            bar_y = sy + offset - 6 + bob
            ratio = max(0, self.hp / self.max_hp)
            pygame.draw.rect(screen, (40, 10, 10), (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(screen, (200, 50, 50), (bar_x, bar_y, int(bar_w * ratio), bar_h))

        if self.state == "attack" and 0.1 < self.attack_timer < 0.35:
            offsets = {"up": (0, -T // 2), "down": (0, T // 2), "left": (-T // 2, 0), "right": (T // 2, 0)}
            ox, oy = offsets.get(self.facing, (0, 0))
            cx = sx + T // 2 + ox
            cy = sy + T // 2 + oy
            pygame.draw.circle(screen, (255, 100, 80, 180), (cx, cy), 6)
