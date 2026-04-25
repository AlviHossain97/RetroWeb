import json
import math
import os
import time
import hashlib


DEFAULT_GAME_CONFIG = {
    "compatibility": {
        "legacy_handling_default": True,
        "legacy_scoring_default": True,
        "allow_feature_toggles": True,
    },
    "features": {
        "risk_scoring": True,
        "traffic_behaviors": True,
        "advanced_handling": False,
        "boost_system": True,
        "drift_assist": False,
        "precision_reward": True,
        "camera_zoom": True,
        "screen_shake": True,
        "motion_streaks": True,
        "crash_slowmo": True,
        "reduced_motion": False,
        "colorblind_hud": False,
        "debug_overlay": False,
        "deterministic_mode": False,
    },
    "risk": {
        "combo_grace_seconds": 1.8,
        "combo_decay_per_second": 12.0,
        "combo_max": 100.0,
        "multiplier_base": 1.0,
        "multiplier_max": 6.0,
        "near_miss_distance": 44,
        "near_miss_speed_gate": 4.5,
        "wrong_lane_tick_seconds": 0.35,
        "high_speed_gate": 8.0,
        "pressure_radius": 125,
    },
    "boost": {
        "max_meter": 100.0,
        "burst_drain_per_second": 55.0,
        "sustain_drain_per_second": 28.0,
        "burst_multiplier": 1.65,
        "sustain_multiplier": 1.25,
        "risk_to_boost_ratio": 0.07,
    },
    "nitro": {
        "spawn_chance_base": 0.08,
        "refill_amount": 45.0,
        "mode_spawn_multipliers": {
            "CLASSIC_ENDLESS": 1.00,
            "HIGH_RISK": 1.35,
            "TIME_ATTACK": 1.10,
            "ONE_LIFE_HARDCORE": 0.45,
            "DAILY_RUN": 1.00,
            "ZEN": 0.00,
        },
        "mode_refill_multipliers": {
            "CLASSIC_ENDLESS": 1.00,
            "HIGH_RISK": 1.20,
            "TIME_ATTACK": 1.10,
            "ONE_LIFE_HARDCORE": 0.85,
            "DAILY_RUN": 1.00,
            "ZEN": 0.00,
        },
    },
    "modes": {
        "default": "CLASSIC_ENDLESS",
        "daily_seed_salt": "red-racer-daily",
    },
    "performance": {
        "target_fps": 60,
        "max_particles": 240,
        "max_enemies": 14,
        "max_collectibles": 12,
    },
}


def _deep_merge(base, override):
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_game_config(path):
    if not os.path.exists(path):
        return dict(DEFAULT_GAME_CONFIG)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _deep_merge(DEFAULT_GAME_CONFIG, data)
    except Exception:
        return dict(DEFAULT_GAME_CONFIG)


class GameModes:
    ORDER = [
        "CLASSIC_ENDLESS",
        "HIGH_RISK",
        "TIME_ATTACK",
        "ONE_LIFE_HARDCORE",
        "DAILY_RUN",
        "ZEN",
    ]

    @staticmethod
    def next_mode(current):
        if current not in GameModes.ORDER:
            return GameModes.ORDER[0]
        idx = (GameModes.ORDER.index(current) + 1) % len(GameModes.ORDER)
        return GameModes.ORDER[idx]

    @staticmethod
    def short_name(mode):
        mapping = {
            "CLASSIC_ENDLESS": "CLASSIC",
            "HIGH_RISK": "HIGH-RISK",
            "TIME_ATTACK": "TIME ATTACK",
            "ONE_LIFE_HARDCORE": "HARDCORE",
            "DAILY_RUN": "DAILY RUN",
            "ZEN": "ZEN",
        }
        return mapping.get(mode, mode)


class BoostSystem:
    def __init__(self, cfg):
        self.cfg = cfg
        self.max_meter = float(cfg.get("max_meter", 100.0))
        # Start full by default so every run has immediate boost play.
        self.meter = self.max_meter
        self.active_type = None
        self.last_gain = 0.0

    def reset(self):
        self.meter = self.max_meter
        self.active_type = None
        self.last_gain = 0.0

    def gain_from_risk(self, risk_points):
        gain = float(risk_points) * float(self.cfg.get("risk_to_boost_ratio", 0.07))
        self.last_gain = gain
        self.meter = min(self.max_meter, self.meter + gain)

    def activate(self, boost_type):
        if self.meter <= 1.0:
            return
        if boost_type in ("burst", "sustain"):
            self.active_type = boost_type

    def deactivate(self):
        self.active_type = None

    def update(self, dt):
        if self.active_type == "burst":
            self.meter -= float(self.cfg.get("burst_drain_per_second", 55.0)) * dt
        elif self.active_type == "sustain":
            self.meter -= float(self.cfg.get("sustain_drain_per_second", 28.0)) * dt

        if self.meter <= 0:
            self.meter = 0.0
            self.active_type = None

    def speed_multiplier(self):
        if self.active_type == "burst":
            return float(self.cfg.get("burst_multiplier", 1.65))
        if self.active_type == "sustain":
            return float(self.cfg.get("sustain_multiplier", 1.25))
        return 1.0


class RiskScoringSystem:
    def __init__(self, cfg):
        self.cfg = cfg
        self.combo = 0.0
        self.combo_max = float(cfg.get("combo_max", 100.0))
        self.multiplier_base = float(cfg.get("multiplier_base", 1.0))
        self.multiplier_max = float(cfg.get("multiplier_max", 6.0))
        self.combo_grace = float(cfg.get("combo_grace_seconds", 1.8))
        self.combo_decay = float(cfg.get("combo_decay_per_second", 12.0))
        self.last_risk_time = 0.0
        self.last_wrong_lane_tick = 0.0
        self.recent_events = []
        self.risk_score = 0
        self.max_combo = 0.0
        self.near_miss_count = 0
        self.extreme_near_miss_timer = 0.0
        self.edge_pulse = 0.0
        self.glow = 0.0
        self.active_bonuses = []

    def reset(self):
        self.combo = 0.0
        self.last_risk_time = 0.0
        self.last_wrong_lane_tick = 0.0
        self.recent_events = []
        self.risk_score = 0
        self.max_combo = 0.0
        self.near_miss_count = 0
        self.extreme_near_miss_timer = 0.0
        self.edge_pulse = 0.0
        self.glow = 0.0
        self.active_bonuses = []

    def hard_reset(self):
        self.combo = 0.0
        self.active_bonuses = []

    def multiplier(self):
        t = min(1.0, self.combo / max(1.0, self.combo_max))
        return self.multiplier_base + (self.multiplier_max - self.multiplier_base) * t

    def _register_event(self, name, combo_gain, base_points):
        now = time.time()
        self.last_risk_time = now
        self.combo = min(self.combo_max, self.combo + combo_gain)
        self.max_combo = max(self.max_combo, self.combo)
        points = int(base_points * self.multiplier())
        self.risk_score += points
        self.recent_events.append((name, now, points))
        if len(self.recent_events) > 12:
            self.recent_events.pop(0)
        self.edge_pulse = min(1.0, self.edge_pulse + 0.14)
        self.glow = min(1.0, self.glow + 0.18)
        self.active_bonuses = [n for (n, _, _) in self.recent_events[-4:]]
        return points

    def update(self, dt, player_rect, player_speed, enemies, road_center_x, boost_active=False, precision=False):
        now = time.time()
        total_points = 0

        self.edge_pulse = max(0.0, self.edge_pulse - dt * 1.8)
        self.glow = max(0.0, self.glow - dt * 1.2)
        self.extreme_near_miss_timer = max(0.0, self.extreme_near_miss_timer - dt)

        if now - self.last_risk_time > self.combo_grace and self.combo > 0:
            self.combo = max(0.0, self.combo - self.combo_decay * dt)

        near_threshold = float(self.cfg.get("near_miss_distance", 44))
        near_speed_gate = float(self.cfg.get("near_miss_speed_gate", 4.5))
        pressure_radius = float(self.cfg.get("pressure_radius", 125))

        close_enemies = 0
        left_block = False
        right_block = False

        for e in enemies:
            dx = e.rect.centerx - player_rect.centerx
            dy = e.rect.centery - player_rect.centery
            d = math.hypot(dx, dy)

            if d < pressure_radius:
                close_enemies += 1
            if abs(dy) < 60 and -120 < dx < -20:
                left_block = True
            if abs(dy) < 60 and 20 < dx < 120:
                right_block = True

            if d < near_threshold and player_speed >= near_speed_gate:
                self.near_miss_count += 1
                total_points += self._register_event("NEAR MISS", 8.0, 35)
                if d < near_threshold * 0.6:
                    self.extreme_near_miss_timer = 0.15

            if -80 < dy < 20 and abs(dx) < near_threshold * 1.4 and player_speed > near_speed_gate * 1.2:
                total_points += self._register_event("HIGH-SPEED OVERTAKE", 6.0, 22)

        if left_block and right_block:
            total_points += self._register_event("THREAD THE GAP", 10.0, 40)

        wrong_lane_interval = float(self.cfg.get("wrong_lane_tick_seconds", 0.35))
        if player_rect.centerx < road_center_x and (now - self.last_wrong_lane_tick) >= wrong_lane_interval:
            self.last_wrong_lane_tick = now
            total_points += self._register_event("WRONG LANE", 2.2, 8)

        high_speed_gate = float(self.cfg.get("high_speed_gate", 8.0))
        if player_speed >= high_speed_gate and close_enemies >= 2:
            total_points += self._register_event("UNDER PRESSURE", 1.8, 6)

        if boost_active and close_enemies > 0:
            total_points += self._register_event("BOOST IN TRAFFIC", 2.5, 10)

        if precision:
            total_points += self._register_event("PRECISION STEER", 1.0, 5)

        return total_points


class ProgressionSystem:
    def __init__(self, save_path):
        self.save_path = save_path
        self.level = 1
        self.xp = 0
        self.cars_unlocked = ["Felucia"]
        self.upgrades = {"speed": 0, "handling": 0, "boost_efficiency": 0}
        self.cosmetics = []
        self._load()

    def _load(self):
        if not os.path.exists(self.save_path):
            return
        try:
            with open(self.save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.level = int(data.get("level", 1))
            self.xp = int(data.get("xp", 0))
            self.cars_unlocked = list(data.get("cars_unlocked", ["Felucia"]))
            self.upgrades = dict(data.get("upgrades", self.upgrades))
            self.cosmetics = list(data.get("cosmetics", []))
        except Exception:
            return

    def save(self):
        payload = {
            "level": self.level,
            "xp": self.xp,
            "cars_unlocked": self.cars_unlocked,
            "upgrades": self.upgrades,
            "cosmetics": self.cosmetics,
        }
        try:
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            return

    def award_xp(self, amount):
        self.xp += int(max(0, amount))
        while self.xp >= self.level * 200:
            self.xp -= self.level * 200
            self.level += 1
            if self.level == 2 and "Aurion" not in self.cars_unlocked:
                self.cars_unlocked.append("Aurion")
            elif self.level == 4 and "Lumbra" not in self.cars_unlocked:
                self.cars_unlocked.append("Lumbra")


def deterministic_seed_for_mode(mode_name, cfg):
    if mode_name == "TIME_ATTACK":
        return 13371337
    if mode_name == "DAILY_RUN":
        day_key = time.strftime("%Y-%m-%d")
        salt = cfg.get("modes", {}).get("daily_seed_salt", "red-racer-daily")
        raw = f"{salt}-{day_key}".encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()[:8]
        return int(digest, 16)
    if cfg.get("features", {}).get("deterministic_mode", False):
        return 20260209
    return None