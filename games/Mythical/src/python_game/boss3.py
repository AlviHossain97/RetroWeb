"""
boss3.py — The Mythic Sovereign, Stage 3 final boss.

The corrupted god-king who shattered the world and refuses to die.
Three-phase fight — the hardest encounter in the game.

Phase 1 (full HP → ~65%):
  - Ground-level melee: sword sweeps, charge, energy pulse
  - Methodical — tests the player's dodge timing

Phase 2 (~65% → ~30%):
  - Partially levitates — moves faster, orbit pattern
  - Adds void_wave (expanding ring of damage) and crystal_barrage (AoE slam)
  - Enrages: attack cooldown shortened, more aggressive repositioning

Phase 3 (~30% → 0):
  - Full enrage: glowing gold/white aura, maximum speed
  - All Phase 1+2 attacks plus reality_rift (screen-wide damaging pulse)
  - Shortest decision delay, highest aggression

Visual identity:
  Phase 1: tall dark armored figure, crown, dark purple glow
  Phase 2: cracked armor reveals golden light, partial levitation (drawn higher)
  Phase 3: blazing gold/white aura, crown fragments, overwhelming presence
"""
from __future__ import annotations

import math
import random

import pygame

from ai.pathfinding import find_path, quantize_tile
from game_math import point_distance, pulse01, safe_normalize
from settings import TILE_SIZE


_BASE = {
    "max_hp":            50,
    "damage":            4,
    "speed":             3.2,
    "charge_speed":      9.0,
    "slam_radius":       2.2,
    "spin_radius":       1.8,
    "void_wave_radius":  3.5,
    "crystal_barrage_radius": 2.5,
    "rift_radius":       4.5,
    "charge_telegraph":  0.50,
    "charge_duration":   0.40,
    "slam_duration":     0.50,
    "spin_duration":     0.55,
    "wave_duration":     0.70,
    "rift_duration":     0.80,
    "preferred_range_p1": 2.0,
    "preferred_range_p2": 2.5,
    "preferred_range_p3": 1.8,
    "intro_duration":    2.2,
    "decision_delay_p1": 0.80,
    "decision_delay_p2": 0.55,
    "decision_delay_p3": 0.35,
    "attack_cooldown":   1.10,
    "active_radius":     16.0,
    "body_radius":       1.0,
    "phase2_threshold":  0.65,   # overridden by stage_config
    "phase3_threshold":  0.30,   # overridden by stage_config
}


from runtime.gba_compat import GBAEntity
from runtime.fixed_point import FixedVec2
from runtime.asset_manager import get_frame, load_sprite_sheet

class MythicSovereign(GBAEntity):
    """
    Stage 3 final boss.  Duck-typed as Boss for gameplay compatibility.
    """

    def __init__(
        self,
        tile_x: int,
        tile_y: int,
        boss_id: str = "mythic_sovereign",
        difficulty_mode: str = "normal",
        difficulty_config: dict | None = None,
    ):
        super().__init__(float(tile_x), float(tile_y))
        diff  = difficulty_config or {}
        bmult = diff.get("boss_stat_mults", {})
        self.boss_id = boss_id
        self.spawn_x = self.x
        self.spawn_y = self.y

        hp_m  = bmult.get("hp",     1.0)
        dmg_m = bmult.get("damage", 1.0)
        spd_m = bmult.get("speed",  1.0)
        cd_m  = bmult.get("cooldown", 1.0)

        self.max_hp = max(1, int(round(_BASE["max_hp"] * hp_m)))
        self.hp     = self.max_hp
        self.damage = max(1, int(round(_BASE["damage"] * dmg_m)))
        self.speed  = _BASE["speed"] * spd_m

        # Attack geometry
        self.charge_speed            = _BASE["charge_speed"]
        self.slam_radius             = _BASE["slam_radius"]
        self.spin_radius             = _BASE["spin_radius"]
        self.void_wave_radius        = _BASE["void_wave_radius"]
        self.crystal_barrage_radius  = _BASE["crystal_barrage_radius"]
        self.rift_radius             = _BASE["rift_radius"]
        self.charge_telegraph        = _BASE["charge_telegraph"]
        self.charge_duration         = _BASE["charge_duration"]
        self.slam_duration           = _BASE["slam_duration"]
        self.spin_duration           = _BASE["spin_duration"]
        self.wave_duration           = _BASE["wave_duration"]
        self.rift_duration           = _BASE["rift_duration"]
        self.charge_radius           = 1.3
        self.body_radius             = _BASE["body_radius"]
        self.active_radius           = _BASE["active_radius"]

        # Phase thresholds (overridden by stage_config)
        stage_data = diff.get("_stage_config", {})
        self.phase2_threshold = stage_data.get("phase2_threshold", _BASE["phase2_threshold"])
        self.phase3_threshold = stage_data.get("phase3_threshold", _BASE["phase3_threshold"])

        # AI timing
        self.decision_delay_p1 = _BASE["decision_delay_p1"] * cd_m
        self.decision_delay_p2 = _BASE["decision_delay_p2"] * cd_m
        self.decision_delay_p3 = _BASE["decision_delay_p3"] * cd_m
        self.attack_cooldown   = _BASE["attack_cooldown"]   * cd_m
        self.intro_duration    = _BASE["intro_duration"]

        # State
        self.phase       = 1
        self.state       = "dormant"
        self.state_timer = 0.0
        self.facing      = "down"

        self.alive    = True
        self.active   = False
        self.defeated = False

        self.hurt_timer  = 0.0
        self.attack_hit  = False

        self.knockback_vx = 0.0
        self.knockback_vy = 0.0

        self.charge_tx = self.x
        self.charge_ty = self.y

        self.current_path:  list[tuple[int, int]] = []
        self.decision_timer = 0.0
        self.last_map_name  = ""
        self.last_pos       = (self.x, self.y)
        self.stuck_timer    = 0.0
        self.debug_color    = (200, 160, 40)
        self.last_scores: dict = {}

        # Visual
        self._aura_timer    = 0.0
        self._levitate_off  = 0.0   # vertical offset for phase 2/3 levitation

    # ── Public API ────────────────────────────────────────────────────────────

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

    def activate(self) -> None:
        self.active      = True
        self.state       = "intro"
        self.state_timer = 0.0

    def dist_to(self, px: float, py: float) -> float:
        return point_distance(self.x, self.y, px, py)

    def body_collision(self) -> dict:
        if not self.alive or self.defeated or self.state == "dormant":
            return None
        if self.state == "intro" and self.state_timer < self.intro_duration * 0.7:
            return None
        return {"x": self.x + 0.5, "y": self.y + 0.5, "radius": self.body_radius}

    def take_damage(self, amount: int, kx: float = 0, ky: float = 0) -> None:
        if not self.alive or self.defeated or self.state == "intro":
            return
        self.hp -= amount
        self.hurt_timer   = 0.22
        self.knockback_vx = kx * 1.2
        self.knockback_vy = ky * 1.2
        if self.hp <= 0:
            self.hp       = 0
            self.alive    = False
            self.defeated = True
            self.state    = "death"
            self.state_timer = 0.0
            return
        # Phase transitions
        hp_ratio = self.hp / self.max_hp
        if self.phase == 1 and hp_ratio <= self.phase2_threshold:
            self._enter_phase(2)
        elif self.phase == 2 and hp_ratio <= self.phase3_threshold:
            self._enter_phase(3)

    def _enter_phase(self, new_phase: int) -> None:
        self.phase = new_phase
        if new_phase == 2:
            self.speed *= 1.20
            self.attack_cooldown = max(0.5, self.attack_cooldown * 0.80)
        elif new_phase == 3:
            self.speed *= 1.25
            self.attack_cooldown = max(0.3, self.attack_cooldown * 0.70)

    def snapshot_state(self) -> dict:
        return {
            "x": self.x, "y": self.y,
            "hp": self.hp, "phase": self.phase,
            "defeated": self.defeated, "active": self.active,
        }

    def apply_saved_state(self, data: dict) -> None:
        self.x        = float(data.get("x", self.x))
        self.y        = float(data.get("y", self.y))
        self.hp       = int(data.get("hp", self.max_hp))
        self.phase    = int(data.get("phase", 1))
        self.defeated = bool(data.get("defeated", False))
        self.active   = bool(data.get("active", False))
        if self.defeated:
            self.alive = False
        # Re-apply phase multipliers
        if self.phase >= 2:
            self.speed *= 1.20
            self.attack_cooldown = max(0.5, self.attack_cooldown * 0.80)
        if self.phase == 3:
            self.speed *= 1.25
            self.attack_cooldown = max(0.3, self.attack_cooldown * 0.70)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(
        self,
        dt: float,
        px: float,
        py: float,
        tilemap,
        map_name: str = "",
        dynamic_blockers=None,
        player_field=None,
        allow_expensive_ai: bool = True,
    ) -> None:
        if not self.alive or self.defeated:
            return

        self.state_timer  += dt
        self._aura_timer  += dt
        if self.hurt_timer > 0:
            self.hurt_timer = max(0.0, self.hurt_timer - dt)

        # Levitation effect grows with phase
        target_lev = {1: 0.0, 2: 0.12, 3: 0.22}.get(self.phase, 0.0)
        self._levitate_off += (target_lev - self._levitate_off) * min(1.0, dt * 3.0)

        # Knockback
        if abs(self.knockback_vx) > 0.01 or abs(self.knockback_vy) > 0.01:
            nx = self.x + self.knockback_vx * dt
            ny = self.y + self.knockback_vy * dt
            if tilemap.is_passable(nx, ny):
                self.x, self.y = nx, ny
            self.knockback_vx *= 0.82
            self.knockback_vy *= 0.82

        self._update_facing(px, py)

        if self.state == "intro":
            if self.state_timer >= self.intro_duration:
                self.state       = "idle"
                self.state_timer = 0.0
            return

        if self.state == "idle":
            delay = [self.decision_delay_p1,
                     self.decision_delay_p2,
                     self.decision_delay_p3][min(self.phase - 1, 2)]
            self.decision_timer += dt
            if self.decision_timer >= delay:
                self.decision_timer = 0.0
                self._decide(px, py, tilemap, player_field, dynamic_blockers, allow_expensive_ai)
            return

        if self.state == "reposition":
            self._do_reposition(dt, tilemap)
            return

        if self.state == "charge":
            self._do_charge(dt, tilemap)
            return

        if self.state in ("slam", "void_wave", "crystal_barrage", "rift", "spin"):
            dur = {
                "slam":             self.slam_duration,
                "void_wave":        self.wave_duration,
                "crystal_barrage":  self.slam_duration,
                "rift":             self.rift_duration,
                "spin":             self.spin_duration,
            }.get(self.state, 0.5)
            if self.state_timer >= dur:
                self.state       = "idle"
                self.state_timer = 0.0
            return

    def _update_facing(self, px: float, py: float) -> None:
        dx, dy = px - self.x, py - self.y
        if abs(dx) >= abs(dy):
            self.facing = "right" if dx > 0 else "left"
        else:
            self.facing = "down" if dy > 0 else "up"

    def _decide(self, px, py, tilemap, player_field, dynamic_blockers, allow_expensive) -> None:
        dist = self.dist_to(px, py)
        pref = [_BASE["preferred_range_p1"],
                _BASE["preferred_range_p2"],
                _BASE["preferred_range_p3"]][min(self.phase - 1, 2)]

        if dist < pref * 1.3:
            self._pick_attack(dist, px, py)
        else:
            self._navigate_toward(px, py, tilemap, dynamic_blockers, allow_expensive)

    def _pick_attack(self, dist: float, px: float = 0, py: float = 0) -> None:
        roll = random.random()
        if self.phase == 1:
            if roll < 0.45:
                self.charge_tx = px; self.charge_ty = py
                self.state = "charge"; self.attack_hit = False
                self.state_timer = 0.0
                return
            elif roll < 0.75:
                self.state = "slam";      self.attack_hit = False
            else:
                self.state = "spin";      self.attack_hit = False
        elif self.phase == 2:
            if roll < 0.35:
                self.charge_tx = px; self.charge_ty = py
                self.state = "charge"; self.attack_hit = False
                self.state_timer = 0.0; return
            elif roll < 0.60:
                self.state = "void_wave"; self.attack_hit = False
            elif roll < 0.82:
                self.state = "slam";      self.attack_hit = False
            else:
                self.state = "crystal_barrage"; self.attack_hit = False
        else:  # phase 3
            if roll < 0.30:
                self.charge_tx = px; self.charge_ty = py
                self.state = "charge"; self.attack_hit = False
                self.state_timer = 0.0; return
            elif roll < 0.52:
                self.state = "void_wave"; self.attack_hit = False
            elif roll < 0.70:
                self.state = "rift";      self.attack_hit = False
            elif roll < 0.85:
                self.state = "slam";      self.attack_hit = False
            else:
                self.state = "crystal_barrage"; self.attack_hit = False
        self.state_timer = 0.0

    def _do_charge(self, dt: float, tilemap) -> None:
        if self.state_timer < self.charge_telegraph:
            return
        dx = self.charge_tx - self.x
        dy = self.charge_ty - self.y
        nx, ny, d = safe_normalize(dx, dy)
        if d < 0.12 or self.state_timer > self.charge_telegraph + self.charge_duration:
            self.state = "idle"; self.state_timer = 0.0; return
        spd = self.charge_speed * (1.0 + 0.1 * (self.phase - 1))
        next_x = self.x + nx * spd * dt
        next_y = self.y + ny * spd * dt
        if tilemap.is_passable(next_x, next_y):
            self.x, self.y = next_x, next_y
        else:
            self.state = "idle"; self.state_timer = 0.0

    def _do_reposition(self, dt: float, tilemap) -> None:
        if not self.current_path:
            self.state = "idle"; self.state_timer = 0.0; return
        tx, ty = self.current_path[0]
        dx, dy = tx - self.x, ty - self.y
        nx, ny, d = safe_normalize(dx, dy)
        if d < 0.1:
            self.current_path.pop(0); return
        spd  = self.speed * (1.0 + 0.15 * (self.phase - 1))
        step = min(d, spd * dt)
        next_x = self.x + nx * step
        next_y = self.y + ny * step
        if tilemap.is_passable(next_x, next_y):
            self.x, self.y = next_x, next_y

    def _navigate_toward(self, px, py, tilemap, blockers, allow_expensive) -> None:
        tx, ty = int(round(px)), int(round(py))
        if allow_expensive:
            path = find_path(
                tilemap, quantize_tile(self.x, self.y), (tx, ty),
                blockers=frozenset(blockers or []), max_nodes=1200)
            if path:
                self.current_path = path
        if self.current_path:
            self.state = "reposition"; self.state_timer = 0.0

    # ── Render ────────────────────────────────────────────────────────────────

    def render(self, screen: pygame.Surface, cam_x: int, cam_y: int) -> None:
        if not self.alive and not self.defeated:
            return
        if self.defeated and self.state == "death" and self.state_timer > 1.5:
            return

        sx = int(self.x * TILE_SIZE) - cam_x
        sy = int(self.y * TILE_SIZE) - cam_y - int(self._levitate_off * TILE_SIZE)
        S  = TILE_SIZE

        # Aura pulse
        pulse = pulse01(self._aura_timer, 3.5)
        hurt  = self.hurt_timer > 0

        # Phase-based colour palette
        if hurt:
            aura_col  = (255, 80, 80, 0)
        elif self.phase == 3:
            aura_col  = (255, 220, 50, int(80 * pulse))
        elif self.phase == 2:
            aura_col  = (180, 50, 220, int(60 * pulse))
        else:
            aura_col  = (80, 40, 140, int(40 * pulse))

        # Aura glow ring
        if self.phase >= 2:
            aura_surf = pygame.Surface((S * 3, S * 3), pygame.SRCALPHA)
            aura_r = int(S * (1.0 + 0.3 * pulse))
            a_col  = aura_col if len(aura_col) == 4 else aura_col + (80,)
            pygame.draw.circle(aura_surf, a_col,
                               (S * 3 // 2, S * 3 // 2), aura_r)
            screen.blit(aura_surf, (sx - S * 3 // 2, sy - S * 3 // 2))

        anim_name = f"idle_{self.phase}"
        if hurt: anim_name = "hurt"
        elif self.state == "death": anim_name = "death"
        
        frame_idx = 0 if hurt else int(self.state_timer / 0.15) % 4
        if self.state == "death":
            frame_idx = min(3, int(self.state_timer * 3))
            
        surf = get_frame("boss_3", anim_name, frame_idx)
        if surf:
            # We compiled S=1.5*TILE_SIZE, output is 2S x 2S (3 tiles wide).
            screen.blit(surf, (sx - int(S*1.5), sy - int(S*1.5)))

        # Phase 3: rift wave indicator ring
        if self.state == "rift" and self.state_timer < 0.5:
            frac = self.state_timer / self.rift_duration
            rift_r = int(self.rift_radius * TILE_SIZE * frac)
            if rift_r > 0:
                rift_surf = pygame.Surface((rift_r * 2 + 4, rift_r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(rift_surf, (255, 200, 50, max(0, 180 - int(200 * frac))),
                                   (rift_r + 2, rift_r + 2), rift_r, 3)
                screen.blit(rift_surf, (sx - rift_r - 2, sy - rift_r - 2))

        # HP bar
        hp_ratio = max(0.0, self.hp / self.max_hp)
        bar_w = S + 8
        pygame.draw.rect(screen, (30, 10, 30),
                         (sx - bar_w // 2, sy - int(S * 0.85), bar_w, 7))
        bar_col = {1: (120, 60, 180), 2: (160, 60, 220), 3: (220, 180, 40)}.get(self.phase, (120, 60, 180))
        pygame.draw.rect(screen, bar_col,
                         (sx - bar_w // 2, sy - int(S * 0.85),
                          int(bar_w * hp_ratio), 7))
        # Phase markers
        for thresh in (self.phase2_threshold, self.phase3_threshold):
            marker_x = sx - bar_w // 2 + int(bar_w * thresh)
            pygame.draw.line(screen, (255, 255, 100),
                             (marker_x, sy - int(S * 0.85)),
                             (marker_x, sy - int(S * 0.85) + 7), 1)
