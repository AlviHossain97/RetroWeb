"""
save_system.py — Unified save/profile/records system for Red Racer Ultimate Edition.

Provides structured, export-friendly data persistence:
- ProfileData: player identity, lifetime stats, unlocks, mastery
- RunRecord: per-run telemetry snapshot
- Per-car / per-road / per-mode bests
- Recent run history ring buffer
- Settings persistence
- Achievement state storage
- Clean JSON serialization with version migration

GBA Portability: MUST PORT LATER (core save architecture maps directly to SRAM structs)
"""

import json
import os
import time

SAVE_VERSION = 3
SAVE_FILE = "profile.json"

# Import centralized car unlock thresholds
from cars import CAR_UNLOCK_THRESHOLDS

MAX_RECENT_RUNS = 50
MAX_CAR_MASTERY_LEVEL = 10
MASTERY_XP_PER_LEVEL = 500


class RunRecord:
    """Snapshot of a single completed run. Export-friendly."""

    def __init__(self, **kwargs):
        self.score = kwargs.get("score", 0)
        self.risk_score = kwargs.get("risk_score", 0)
        self.base_score = kwargs.get("base_score", 0)
        self.car_key = kwargs.get("car_key", "Felucia")
        self.road_key = kwargs.get("road_key", "Road.png")
        self.game_mode = kwargs.get("game_mode", "CLASSIC_ENDLESS")
        self.difficulty = kwargs.get("difficulty", "NORMAL")
        self.duration_seconds = kwargs.get("duration_seconds", 0.0)
        self.near_misses = kwargs.get("near_misses", 0)
        self.max_combo = kwargs.get("max_combo", 0)
        self.max_speed = kwargs.get("max_speed", 0)
        self.coins_collected = kwargs.get("coins_collected", 0)
        self.fuel_collected = kwargs.get("fuel_collected", 0)
        self.boost_used_seconds = kwargs.get("boost_used_seconds", 0.0)
        self.enemies_passed = kwargs.get("enemies_passed", 0)
        self.top_multiplier = kwargs.get("top_multiplier", 1.0)
        self.timestamp = kwargs.get("timestamp", 0)
        self.new_best = kwargs.get("new_best", False)
        self.new_unlocks = kwargs.get("new_unlocks", [])
        self.achievements_earned = kwargs.get("achievements_earned", [])
        self.missions_completed = kwargs.get("missions_completed", [])
        self.no_hit = kwargs.get("no_hit", False)
        self.fuel_at_end = kwargs.get("fuel_at_end", 100.0)
        self.damage_taken = kwargs.get("damage_taken", 0)
        self.distance_meters = kwargs.get("distance_meters", 0.0)

    def to_dict(self):
        return self.__dict__.copy()

    @staticmethod
    def from_dict(d):
        return RunRecord(**d)


class CarMastery:
    """Per-car mastery tracking."""

    def __init__(self):
        self.runs = 0
        self.total_score = 0
        self.best_score = 0
        self.total_distance = 0.0
        self.total_near_misses = 0
        self.mastery_xp = 0
        self.mastery_level = 0
        self.badges = []  # e.g. "first_run", "score_10k", "mastery_5"

    def add_run(self, run_record):
        self.runs += 1
        self.total_score += run_record.score
        if run_record.score > self.best_score:
            self.best_score = run_record.score
        self.total_distance += run_record.duration_seconds * 60  # approx meters
        self.total_near_misses += run_record.near_misses
        # Mastery XP: score/10 + near_misses*5
        xp_gain = run_record.score // 10 + run_record.near_misses * 5
        self.mastery_xp += xp_gain
        while (self.mastery_xp >= MASTERY_XP_PER_LEVEL and
               self.mastery_level < MAX_CAR_MASTERY_LEVEL):
            self.mastery_xp -= MASTERY_XP_PER_LEVEL
            self.mastery_level += 1

    def to_dict(self):
        return {
            "runs": self.runs,
            "total_score": self.total_score,
            "best_score": self.best_score,
            "total_distance": self.total_distance,
            "total_near_misses": self.total_near_misses,
            "mastery_xp": self.mastery_xp,
            "mastery_level": self.mastery_level,
            "badges": self.badges,
        }

    @staticmethod
    def from_dict(d):
        m = CarMastery()
        m.runs = d.get("runs", 0)
        m.total_score = d.get("total_score", 0)
        m.best_score = d.get("best_score", 0)
        m.total_distance = d.get("total_distance", 0.0)
        m.total_near_misses = d.get("total_near_misses", 0)
        m.mastery_xp = d.get("mastery_xp", 0)
        m.mastery_level = d.get("mastery_level", 0)
        m.badges = d.get("badges", [])
        return m


class ProfileData:
    """
    Complete player profile. Single source of truth for all persistent data.
    Designed for later export to external DB.
    """

    def __init__(self, save_dir="."):
        self.save_path = os.path.join(save_dir, SAVE_FILE)
        self.version = SAVE_VERSION

        # Identity
        self.level = 1
        self.xp = 0
        self.total_runs = 0
        self.total_playtime_seconds = 0.0

        # Scores
        self.high_score = 0
        self.per_mode_best = {}   # mode_name -> best score
        self.per_road_best = {}   # road_key -> best score

        # Unlocks
        self.cars_unlocked = ["Felucia", "Suprex"]  # Starters

        # Car mastery
        self.car_mastery = {}  # car_key -> CarMastery

        # Achievements
        self.achievements_unlocked = []  # list of achievement IDs
        self.achievement_progress = {}   # achievement_id -> progress value

        # Settings
        self.settings = {
            "difficulty": "NORMAL",
            "game_mode": "CLASSIC_ENDLESS",
            "selected_car": "Felucia",
            "selected_road": "Road.png",
            "boost_system": True,
            "debug_overlay": False,
            "near_miss_hitboxes": False,
            "reduced_motion": False,
            "colorblind_hud": False,
        }

        # Run history
        self.recent_runs = []  # list of RunRecord dicts

        # Lifetime stats
        self.lifetime_stats = {
            "total_score": 0,
            "total_risk_score": 0,
            "total_near_misses": 0,
            "total_coins": 0,
            "total_fuel_collected": 0,
            "total_enemies_passed": 0,
            "total_boost_seconds": 0.0,
            "best_combo": 0,
            "best_multiplier": 1.0,
            "best_near_miss_chain": 0,
            "longest_run_seconds": 0.0,
            "total_missions_completed": 0,
        }

        # Daily challenge tracking
        self.daily_runs = {}  # date_str -> RunRecord dict (best for that day)

        self._load()

    def _load(self):
        if not os.path.exists(self.save_path):
            self._save()
            return
        try:
            with open(self.save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("version", 1) < SAVE_VERSION:
                data = self._migrate(data)
            self._apply(data)
        except Exception:
            pass

    def _migrate(self, data):
        """Migrate old save formats forward."""
        v = data.get("version", 1)
        if v < 2:
            # v1 had flat structure
            data.setdefault("car_mastery", {})
            data.setdefault("achievements_unlocked", [])
            data.setdefault("achievement_progress", {})
            data.setdefault("daily_runs", {})
            data.setdefault("lifetime_stats", {})
        if v < 3:
            data.setdefault("per_mode_best", {})
            data.setdefault("per_road_best", {})
            data.setdefault("settings", {})
        data["version"] = SAVE_VERSION
        return data

    def _apply(self, data):
        self.version = data.get("version", SAVE_VERSION)
        self.level = data.get("level", 1)
        self.xp = data.get("xp", 0)
        self.total_runs = data.get("total_runs", 0)
        self.total_playtime_seconds = data.get("total_playtime_seconds", 0.0)
        self.high_score = data.get("high_score", 0)
        self.per_mode_best = data.get("per_mode_best", {})
        self.per_road_best = data.get("per_road_best", {})
        self.cars_unlocked = data.get("cars_unlocked", ["Felucia", "Suprex"])
        self.achievements_unlocked = data.get("achievements_unlocked", [])
        self.achievement_progress = data.get("achievement_progress", {})

        self.car_mastery = {}
        for k, v in data.get("car_mastery", {}).items():
            self.car_mastery[k] = CarMastery.from_dict(v)

        self.settings.update(data.get("settings", {}))

        self.recent_runs = data.get("recent_runs", [])
        if len(self.recent_runs) > MAX_RECENT_RUNS:
            self.recent_runs = self.recent_runs[-MAX_RECENT_RUNS:]

        for k, v in data.get("lifetime_stats", {}).items():
            if k in self.lifetime_stats:
                self.lifetime_stats[k] = v

        self.daily_runs = data.get("daily_runs", {})

    def _save(self):
        data = {
            "version": SAVE_VERSION,
            "level": self.level,
            "xp": self.xp,
            "total_runs": self.total_runs,
            "total_playtime_seconds": self.total_playtime_seconds,
            "high_score": self.high_score,
            "per_mode_best": self.per_mode_best,
            "per_road_best": self.per_road_best,
            "cars_unlocked": self.cars_unlocked,
            "achievements_unlocked": self.achievements_unlocked,
            "achievement_progress": self.achievement_progress,
            "car_mastery": {k: v.to_dict() for k, v in self.car_mastery.items()},
            "settings": self.settings,
            "recent_runs": self.recent_runs[-MAX_RECENT_RUNS:],
            "lifetime_stats": self.lifetime_stats,
            "daily_runs": self.daily_runs,
        }
        try:
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def save(self):
        self._save()

    # -------------------------------------------------------------------
    # Progression
    # -------------------------------------------------------------------

    def award_xp(self, amount):
        self.xp += max(0, int(amount))
        while self.xp >= self.level * 200:
            self.xp -= self.level * 200
            self.level += 1

    def xp_to_next_level(self):
        return self.level * 200

    def xp_progress_ratio(self):
        return self.xp / max(1, self.xp_to_next_level())

    # -------------------------------------------------------------------
    # Car Unlocks
    # -------------------------------------------------------------------

    def is_car_unlocked(self, car_key):
        return car_key in self.cars_unlocked

    def check_car_unlocks(self, current_high_score):
        """Check if any new cars should be unlocked. Returns list of newly unlocked car keys."""
        newly = []
        for car_key, threshold in CAR_UNLOCK_THRESHOLDS.items():
            if car_key not in self.cars_unlocked and current_high_score >= threshold:
                self.cars_unlocked.append(car_key)
                newly.append(car_key)
        return newly

    def get_car_mastery(self, car_key):
        if car_key not in self.car_mastery:
            self.car_mastery[car_key] = CarMastery()
        return self.car_mastery[car_key]

    # -------------------------------------------------------------------
    # Run Recording
    # -------------------------------------------------------------------

    def record_run(self, run_record):
        """Record a completed run. Updates all stats and returns the enriched RunRecord."""
        self.total_runs += 1
        self.total_playtime_seconds += run_record.duration_seconds

        # High score
        new_best = False
        if run_record.score > self.high_score:
            self.high_score = run_record.score
            new_best = True
        run_record.new_best = new_best

        # Per-mode best
        mode = run_record.game_mode
        if run_record.score > self.per_mode_best.get(mode, 0):
            self.per_mode_best[mode] = run_record.score

        # Per-road best
        road = run_record.road_key
        if run_record.score > self.per_road_best.get(road, 0):
            self.per_road_best[road] = run_record.score

        # Car mastery
        mastery = self.get_car_mastery(run_record.car_key)
        mastery.add_run(run_record)

        # Car unlocks
        new_unlocks = self.check_car_unlocks(self.high_score)
        run_record.new_unlocks = new_unlocks

        # Lifetime stats
        ls = self.lifetime_stats
        ls["total_score"] += run_record.score
        ls["total_risk_score"] += run_record.risk_score
        ls["total_near_misses"] += run_record.near_misses
        ls["total_coins"] += run_record.coins_collected
        ls["total_fuel_collected"] += run_record.fuel_collected
        ls["total_enemies_passed"] += run_record.enemies_passed
        ls["total_boost_seconds"] += run_record.boost_used_seconds
        ls["best_combo"] = max(ls["best_combo"], run_record.max_combo)
        ls["best_multiplier"] = max(ls["best_multiplier"], run_record.top_multiplier)
        ls["longest_run_seconds"] = max(ls["longest_run_seconds"], run_record.duration_seconds)

        # XP award: score/10 + risk_score/8 + near_misses*3
        xp = run_record.score // 10 + run_record.risk_score // 8 + run_record.near_misses * 3
        self.award_xp(xp)

        # Timestamp
        run_record.timestamp = int(time.time())

        # Add to history
        self.recent_runs.append(run_record.to_dict())
        if len(self.recent_runs) > MAX_RECENT_RUNS:
            self.recent_runs = self.recent_runs[-MAX_RECENT_RUNS:]

        # Daily tracking
        today = time.strftime("%Y-%m-%d")
        if run_record.game_mode == "DAILY_RUN":
            existing = self.daily_runs.get(today)
            if existing is None or run_record.score > existing.get("score", 0):
                self.daily_runs[today] = run_record.to_dict()

        self._save()
        return run_record

    # -------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------

    def get_recent_runs(self, count=10):
        runs = self.recent_runs[-count:]
        runs.reverse()
        return [RunRecord.from_dict(r) for r in runs]

    def get_car_best(self, car_key):
        m = self.car_mastery.get(car_key)
        return m.best_score if m else 0

    def get_mode_best(self, mode):
        return self.per_mode_best.get(mode, 0)

    def get_road_best(self, road_key):
        return self.per_road_best.get(road_key, 0)

    def get_favorite_car(self):
        """Most-played car by run count."""
        best_key, best_runs = None, 0
        for k, m in self.car_mastery.items():
            if m.runs > best_runs:
                best_key, best_runs = k, m.runs
        return best_key or "Felucia"

    def get_favorite_road(self):
        """Road with most recorded runs."""
        road_counts = {}
        for r in self.recent_runs:
            rk = r.get("road_key", "Road.png")
            road_counts[rk] = road_counts.get(rk, 0) + 1
        if not road_counts:
            return "Road.png"
        return max(road_counts, key=road_counts.get)
