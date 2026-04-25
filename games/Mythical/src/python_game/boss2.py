"""
boss2.py — The Gravewarden, Stage 2 boss.

An ancient warlord corrupted by the ruins' dark energy. Armored and relentless.

Phase 1 (full HP → 50%):
  - Slower, uses shield to tank hits (blocks 1 damage when shield_up)
  - Attacks: charge, slam, shield_bash
  - Periodically raises shield (state: shield_up), becomes briefly invulnerable

Phase 2 (50% HP → 0, shield shatters):
  - Much faster, no more shield
  - Attacks: charge (faster), slam (wider), bone_spin (rapid spin sweep)
  - More aggressive — shorter decision delays
  - Visual: red aura, cracked armor tint

On defeat: drops runic_sword + shadow_mail (handled by gameplay via stage_configs).
"""
from __future__ import annotations

import math
import random

import pygame

from ai.pathfinding import find_path, has_line_of_sight, quantize_tile
from ai.influence import choose_tactical_tile
from game_math import point_distance, pulse01, safe_normalize
from settings import TILE_SIZE


# ── Base stats (scaled by stage difficulty matrix in gameplay) ─────────────

_BASE = {
    "max_hp":            30,
    "damage":            3,
    "speed":             2.8,
    "charge_speed":      8.0,
    "slam_radius":       1.8,
    "spin_radius":       1.5,
    "charge_telegraph":  0.55,
    "charge_duration":   0.35,
    "slam_duration":     0.45,
    "spin_duration":     0.60,
    "shield_bash_range": 1.2,
    "preferred_range_p1": 2.2,
    "preferred_range_p2": 1.4,
    "intro_duration":    1.8,
    "decision_delay_p1": 0.90,
    "decision_delay_p2": 0.55,
    "attack_cooldown":   1.20,
    "active_radius":     14.0,
    "body_radius":       0.9,
}


from runtime.gba_compat import GBAEntity
from runtime.fixed_point import FixedVec2
from runtime.asset_manager import get_frame, load_sprite_sheet

class Gravewarden(GBAEntity):
    """
    Stage 2 boss.  API-compatible with Boss so gameplay code can treat it
    uniformly via duck-typing.
    """

    def __init__(
        self,
        tile_x: int,
        tile_y: int,
        boss_id: str = "gravewarden",
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
        self.charge_speed      = _BASE["charge_speed"]
        self.slam_radius       = _BASE["slam_radius"]
        self.spin_radius       = _BASE["spin_radius"]
        self.charge_telegraph  = _BASE["charge_telegraph"]
        self.charge_duration   = _BASE["charge_duration"]
        self.slam_duration     = _BASE["slam_duration"]
        self.spin_duration     = _BASE["spin_duration"]
        self.shield_bash_range = _BASE["shield_bash_range"]
        self.charge_radius     = 1.3
        self.body_radius       = _BASE["body_radius"]
        self.active_radius     = _BASE["active_radius"]

        # AI timing
        self.intro_duration      = _BASE["intro_duration"]
        self.decision_delay_p1   = _BASE["decision_delay_p1"] * cd_m
        self.decision_delay_p2   = _BASE["decision_delay_p2"] * cd_m
        self.attack_cooldown     = _BASE["attack_cooldown"] * cd_m
        self.preferred_range_p1  = _BASE["preferred_range_p1"]
        self.preferred_range_p2  = _BASE["preferred_range_p2"]

        # State
        self.phase       = 1
        self.state       = "dormant"
        self.state_timer = 0.0
        self.facing      = "down"

        self.alive    = True
        self.active   = False
        self.defeated = False

        self.hurt_timer    = 0.0
        self.shield_up     = False
        self.shield_timer  = 0.0
        self.shield_health = 3     # hits before shattering in phase 1
        self.attack_hit    = False

        self.knockback_vx = 0.0
        self.knockback_vy = 0.0

        self.charge_tx = self.x
        self.charge_ty = self.y

        self.current_path: list[tuple[int, int]] = []
        self.path_recalc_timer = 0.0
        self.decision_timer    = 0.0
        self.attack_timer      = 0.0
        self.reposition_lock   = 0.0
        self.last_map_name     = ""
        self.last_pos          = (self.x, self.y)
        self.stuck_timer       = 0.0
        self.debug_color       = (180, 80, 40)
        self.last_scores: dict = {}

        # Visual aura for phase transitions
        self._phase2_aura_timer = 0.0

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
        self.active   = True
        self.state    = "intro"
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
        # Phase 1 shield absorbs 1 damage
        if self.shield_up and self.phase == 1:
            self.shield_health -= 1
            amount = max(0, amount - 1)
            if self.shield_health <= 0:
                self.shield_up     = False
                self.shield_health = 0
        if amount <= 0:
            return
        self.hp -= amount
        self.hurt_timer     = 0.25
        self.knockback_vx   = kx * 1.5
        self.knockback_vy   = ky * 1.5
        if self.hp <= 0:
            self.hp       = 0
            self.alive    = False
            self.defeated = True
            self.state    = "death"
            self.state_timer = 0.0
        elif self.phase == 1 and self.hp <= self.max_hp * 0.50:
            self._enter_phase2()

    def _enter_phase2(self) -> None:
        self.phase         = 2
        self.shield_up     = False
        self.speed         *= 1.25
        self.attack_cooldown = max(0.5, self.attack_cooldown * 0.75)
        self._phase2_aura_timer = 0.0

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
        if self.phase == 2 and not self.defeated:
            self.speed *= 1.25

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

        self.state_timer += dt
        if self.hurt_timer > 0:
            self.hurt_timer = max(0.0, self.hurt_timer - dt)

        if self.phase == 2:
            self._phase2_aura_timer += dt

        # Knockback physics
        if abs(self.knockback_vx) > 0.01 or abs(self.knockback_vy) > 0.01:
            nx = self.x + self.knockback_vx * dt
            ny = self.y + self.knockback_vy * dt
            if tilemap.is_passable(nx, ny):
                self.x, self.y = nx, ny
            self.knockback_vx *= 0.80
            self.knockback_vy *= 0.80

        dist = self.dist_to(px, py)
        self._update_facing(px, py)

        if self.state == "intro":
            if self.state_timer >= self.intro_duration:
                self.state       = "idle"
                self.state_timer = 0.0
            return

        if self.state == "idle":
            delay = self.decision_delay_p1 if self.phase == 1 else self.decision_delay_p2
            self.decision_timer  = getattr(self, "decision_timer", 0.0) + dt
            self.attack_timer    = getattr(self, "attack_timer", 0.0) + dt
            if self.decision_timer >= delay:
                self.decision_timer = 0.0
                self._decide(px, py, tilemap, player_field, dynamic_blockers, allow_expensive_ai)
            return

        if self.state == "reposition":
            self._do_reposition(dt, tilemap)
            return

        if self.state == "shield_up":
            self.shield_up = True
            if self.state_timer >= 1.8:
                self.shield_up   = False
                self.state       = "idle"
                self.state_timer = 0.0
            return

        if self.state == "charge":
            self._do_charge(dt, px, py, tilemap)
            return

        if self.state == "slam":
            if self.state_timer >= self.slam_duration:
                self.state       = "idle"
                self.state_timer = 0.0
            return

        if self.state in ("spin", "bone_spin"):
            if self.state_timer >= self.spin_duration:
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
        preferred = self.preferred_range_p1 if self.phase == 1 else self.preferred_range_p2

        # Phase 1: occasionally raise shield
        if self.phase == 1 and not self.shield_up and random.random() < 0.15:
            self.state       = "shield_up"
            self.state_timer = 0.0
            return

        # Close-range attacks
        if dist < preferred * 1.2:
            roll = random.random()
            if self.phase == 1:
                if roll < 0.40:
                    self._start_charge(px, py)
                elif roll < 0.70:
                    self.state = "slam"
                    self.state_timer = 0.0
                    self.attack_hit  = False
                else:
                    self.state = "spin"
                    self.state_timer = 0.0
                    self.attack_hit  = False
            else:
                # Phase 2 is more aggressive
                if roll < 0.50:
                    self._start_charge(px, py)
                elif roll < 0.78:
                    self.state = "slam"
                    self.state_timer = 0.0
                    self.attack_hit  = False
                else:
                    self.state = "bone_spin"
                    self.state_timer = 0.0
                    self.attack_hit  = False
        else:
            # Reposition toward player
            self._navigate_toward(px, py, tilemap, dynamic_blockers, allow_expensive)

    def _start_charge(self, px: float, py: float) -> None:
        self.charge_tx   = px
        self.charge_ty   = py
        self.state       = "charge"
        self.state_timer = 0.0
        self.attack_hit  = False

    def _do_charge(self, dt: float, px: float, py: float, tilemap) -> None:
        if self.state_timer < self.charge_telegraph:
            return  # telegraph pause
        dx = self.charge_tx - self.x
        dy = self.charge_ty - self.y
        nx, ny, d = safe_normalize(dx, dy)
        if d < 0.15 or self.state_timer > self.charge_telegraph + self.charge_duration:
            self.state       = "idle"
            self.state_timer = 0.0
            return
        speed = self.charge_speed * (1.3 if self.phase == 2 else 1.0)
        next_x = self.x + nx * speed * dt
        next_y = self.y + ny * speed * dt
        if tilemap.is_passable(next_x, next_y):
            self.x, self.y = next_x, next_y
        else:
            self.state       = "idle"
            self.state_timer = 0.0

    def _do_reposition(self, dt: float, tilemap) -> None:
        if not self.current_path:
            self.state       = "idle"
            self.state_timer = 0.0
            return
        tx, ty = self.current_path[0]
        dx, dy = tx - self.x, ty - self.y
        nx, ny, d = safe_normalize(dx, dy)
        if d < 0.1:
            self.current_path.pop(0)
            return
        spd = self.speed * (1.0 if self.phase == 1 else 1.25)
        step = min(d, spd * dt)
        next_x = self.x + nx * step
        next_y = self.y + ny * step
        if tilemap.is_passable(next_x, next_y):
            self.x, self.y = next_x, next_y

    def _navigate_toward(self, px, py, tilemap, blockers, allow_expensive) -> None:
        tx, ty = int(round(px)), int(round(py))
        if allow_expensive:
            path = find_path(
                tilemap,
                quantize_tile(self.x, self.y),
                (tx, ty),
                blockers=frozenset(blockers or []),
                max_nodes=900,
            )
            if path:
                self.current_path = path
        if self.current_path:
            self.state       = "reposition"
            self.state_timer = 0.0

    # ── Render ────────────────────────────────────────────────────────────────

    def render(self, screen: pygame.Surface, cam_x: int, cam_y: int) -> None:
        if not self.alive and not self.defeated:
            return
        if self.defeated and self.state == "death" and self.state_timer > 1.0:
            return

        sx = int(self.x * TILE_SIZE) - cam_x
        sy = int(self.y * TILE_SIZE) - cam_y
        S  = TILE_SIZE

        # Shadow
        shadow_surf = pygame.Surface((S, S), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 60),
                            (sx - S // 2, sy + S // 2 - 4, S, S // 5))
        screen.blit(shadow_surf, (0, 0))

        anim_name = f"idle_{self.phase}"
        hurt = self.hurt_timer > 0
        if hurt: anim_name = "hurt"
        elif self.state == "death": anim_name = "death"
        
        frame_idx = 0 if hurt else int(self.state_timer / 0.15) % 4
        if self.state == "death":
            frame_idx = min(3, int(self.state_timer * 3))
            
        surf = get_frame("boss_2", anim_name, frame_idx)
        if surf:
            screen.blit(surf, (sx - S + S//4, sy - S + S//4))

        # Shield (phase 1 only)
        if self.phase == 1 and self.shield_up:
            shield_col = (120, 200, 255, 180)
            shield_surf = pygame.Surface((S, S), pygame.SRCALPHA)
            pygame.draw.ellipse(shield_surf, shield_col,
                                (sx - int(S * 0.6), sy - int(S * 0.6),
                                 int(S * 1.2), int(S * 1.2)), 4)
            screen.blit(shield_surf, (0, 0))

        # HP bar
        hp_ratio = max(0.0, self.hp / self.max_hp)
        bar_w = S
        pygame.draw.rect(screen, (50, 20, 20),
                         (sx - bar_w // 2, sy - int(S * 0.7), bar_w, 6))
        fill_col = (180, 60, 60) if self.phase == 2 else (220, 100, 60)
        pygame.draw.rect(screen, fill_col,
                         (sx - bar_w // 2, sy - int(S * 0.7),
                          int(bar_w * hp_ratio), 6))
