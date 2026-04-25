"""
achievements.py — Achievement/badge/medal system for Red Racer Ultimate Edition.

Achievements are checked after each run (and some during runs).
Each achievement has:
- unique ID
- display name
- description
- category
- check function (takes profile + run_record)
- optional progress tracking

GBA Portability: GOOD CANDIDATE TO PORT (simple flag-based system maps to bitfield)
"""


class Achievement:
    def __init__(self, aid, name, description, category="general", icon="★",
                 check_fn=None, progress_key=None, progress_target=None):
        self.id = aid
        self.name = name
        self.description = description
        self.category = category
        self.icon = icon
        self.check_fn = check_fn
        self.progress_key = progress_key
        self.progress_target = progress_target

    def is_earned(self, profile):
        return self.id in profile.achievements_unlocked

    def check(self, profile, run_record=None):
        if self.is_earned(profile):
            return False
        if self.check_fn and self.check_fn(profile, run_record):
            return True
        return False

    def get_progress(self, profile):
        if self.progress_key and self.progress_target:
            current = profile.achievement_progress.get(self.progress_key, 0)
            return min(1.0, current / self.progress_target)
        return 1.0 if self.is_earned(profile) else 0.0


# --- Achievement Check Functions ---

def _check_first_run(profile, run):
    return profile.total_runs >= 1

def _check_score_1k(profile, run):
    return profile.high_score >= 1000

def _check_score_5k(profile, run):
    return profile.high_score >= 5000

def _check_score_10k(profile, run):
    return profile.high_score >= 10000

def _check_score_25k(profile, run):
    return profile.high_score >= 25000

def _check_score_50k(profile, run):
    return profile.high_score >= 50000

def _check_score_100k(profile, run):
    return profile.high_score >= 100000

def _check_near_miss_first(profile, run):
    return run and run.near_misses >= 1

def _check_near_miss_10(profile, run):
    return run and run.near_misses >= 10

def _check_near_miss_20(profile, run):
    return run and run.near_misses >= 20

def _check_near_miss_50(profile, run):
    return run and run.near_misses >= 50

def _check_combo_x3(profile, run):
    return run and run.top_multiplier >= 3.0

def _check_combo_x5(profile, run):
    return run and run.top_multiplier >= 5.0

def _check_combo_x6(profile, run):
    return run and run.top_multiplier >= 6.0

def _check_survive_60s(profile, run):
    return run and run.duration_seconds >= 60

def _check_survive_180s(profile, run):
    return run and run.duration_seconds >= 180

def _check_survive_300s(profile, run):
    return run and run.duration_seconds >= 300

def _check_unlock_all_cars(profile, run):
    from save_system import CAR_UNLOCK_THRESHOLDS
    return all(k in profile.cars_unlocked for k in CAR_UNLOCK_THRESHOLDS)

def _check_no_hit_run(profile, run):
    # Needs special flag in run_record
    return run and getattr(run, "no_hit", False)

def _check_low_fuel_finish(profile, run):
    return run and getattr(run, "fuel_at_end", 100) <= 5 and run.duration_seconds >= 30

def _check_10_runs(profile, run):
    return profile.total_runs >= 10

def _check_50_runs(profile, run):
    return profile.total_runs >= 50

def _check_100_runs(profile, run):
    return profile.total_runs >= 100

def _check_mastery_5(profile, run):
    for m in profile.car_mastery.values():
        if m.mastery_level >= 5:
            return True
    return False

def _check_mastery_10(profile, run):
    for m in profile.car_mastery.values():
        if m.mastery_level >= 10:
            return True
    return False

def _check_level_5(profile, run):
    return profile.level >= 5

def _check_level_10(profile, run):
    return profile.level >= 10

def _check_level_25(profile, run):
    return profile.level >= 25

def _check_all_roads(profile, run):
    roads = {"Road.png", "Road2.png", "Road3.png", "Road4.png"}
    played = set()
    for r in profile.recent_runs:
        played.add(r.get("road_key", "Road.png"))
    return roads.issubset(played)

def _check_all_modes(profile, run):
    modes = {"CLASSIC_ENDLESS", "HIGH_RISK", "TIME_ATTACK", "ONE_LIFE_HARDCORE", "DAILY_RUN", "ZEN"}
    played = set()
    for r in profile.recent_runs:
        played.add(r.get("game_mode", "CLASSIC_ENDLESS"))
    return modes.issubset(played)

def _check_daily_run(profile, run):
    return run and run.game_mode == "DAILY_RUN"

def _check_hardcore_1k(profile, run):
    return run and run.game_mode == "ONE_LIFE_HARDCORE" and run.score >= 1000

def _check_speed_demon(profile, run):
    return run and run.max_speed >= 240

def _check_boost_master(profile, run):
    return run and run.boost_used_seconds >= 30

def _check_mission_5(profile, run):
    return profile.lifetime_stats.get("total_missions_completed", 0) >= 5

def _check_mission_25(profile, run):
    return profile.lifetime_stats.get("total_missions_completed", 0) >= 25


# --- Achievement Registry ---

ALL_ACHIEVEMENTS = [
    # Score milestones
    Achievement("score_1k", "Rookie Racer", "Reach a high score of 1,000", "score", "🏁",
                _check_score_1k, "high_score", 1000),
    Achievement("score_5k", "Getting Serious", "Reach a high score of 5,000", "score", "🏁",
                _check_score_5k, "high_score", 5000),
    Achievement("score_10k", "Ten Grand", "Reach a high score of 10,000", "score", "🏆",
                _check_score_10k, "high_score", 10000),
    Achievement("score_25k", "Quarter Master", "Reach a high score of 25,000", "score", "🏆",
                _check_score_25k, "high_score", 25000),
    Achievement("score_50k", "Fifty Stack", "Reach a high score of 50,000", "score", "👑",
                _check_score_50k, "high_score", 50000),
    Achievement("score_100k", "Legend", "Reach a high score of 100,000", "score", "👑",
                _check_score_100k, "high_score", 100000),

    # Near-miss
    Achievement("nm_first", "Close Call", "Perform your first near miss", "risk", "⚡",
                _check_near_miss_first),
    Achievement("nm_10", "Thread Needle", "10 near misses in one run", "risk", "⚡",
                _check_near_miss_10),
    Achievement("nm_20", "Daredevil", "20 near misses in one run", "risk", "🔥",
                _check_near_miss_20),
    Achievement("nm_50", "Death Wish", "50 near misses in one run", "risk", "💀",
                _check_near_miss_50),

    # Combo
    Achievement("combo_x3", "Combo Starter", "Reach 3x multiplier", "risk", "✨",
                _check_combo_x3),
    Achievement("combo_x5", "Combo Chain", "Reach 5x multiplier", "risk", "✨",
                _check_combo_x5),
    Achievement("combo_x6", "Maximum Overdrive", "Reach 6x multiplier (maximum)", "risk", "💎",
                _check_combo_x6),

    # Survival
    Achievement("survive_60", "One Minute Man", "Survive for 60 seconds", "survival", "⏱",
                _check_survive_60s),
    Achievement("survive_180", "Endurance", "Survive for 3 minutes", "survival", "⏱",
                _check_survive_180s),
    Achievement("survive_300", "Iron Will", "Survive for 5 minutes", "survival", "🛡",
                _check_survive_300s),

    # Run count
    Achievement("first_run", "First Ride", "Complete your first run", "milestone", "🎮",
                _check_first_run),
    Achievement("runs_10", "Regular", "Complete 10 runs", "milestone", "🎮",
                _check_10_runs, "total_runs", 10),
    Achievement("runs_50", "Dedicated", "Complete 50 runs", "milestone", "🎮",
                _check_50_runs, "total_runs", 50),
    Achievement("runs_100", "Veteran", "Complete 100 runs", "milestone", "🎮",
                _check_100_runs, "total_runs", 100),

    # Unlocks / mastery
    Achievement("all_cars", "Collector", "Unlock all 14 cars", "collection", "🚗",
                _check_unlock_all_cars),
    Achievement("mastery_5", "Specialist", "Reach mastery level 5 with any car", "mastery", "⭐",
                _check_mastery_5),
    Achievement("mastery_10", "Grand Master", "Reach mastery level 10 with any car", "mastery", "⭐",
                _check_mastery_10),

    # Level
    Achievement("level_5", "Rising Star", "Reach player level 5", "progression", "📈",
                _check_level_5),
    Achievement("level_10", "Experienced", "Reach player level 10", "progression", "📈",
                _check_level_10),
    Achievement("level_25", "Elite", "Reach player level 25", "progression", "📈",
                _check_level_25),

    # Exploration
    Achievement("all_roads", "Road Warrior", "Race on all 4 roads", "exploration", "🗺",
                _check_all_roads),
    Achievement("all_modes", "Mode Master", "Play all 6 game modes", "exploration", "🗺",
                _check_all_modes),

    # Mode-specific
    Achievement("daily_first", "Daily Driver", "Complete a Daily Run", "modes", "📅",
                _check_daily_run),
    Achievement("hardcore_1k", "Hardcore Hero", "Score 1,000 in Hardcore mode", "modes", "💀",
                _check_hardcore_1k),

    # Feats
    Achievement("speed_demon", "Speed Demon", "Reach 240 MPH in a single run", "feats", "💨",
                _check_speed_demon),
    Achievement("boost_master", "Boost Master", "Use boost for 30+ seconds in one run", "feats", "🚀",
                _check_boost_master),
    Achievement("low_fuel", "Fumes Finish", "Finish a 30s+ run with under 5% fuel", "feats", "⛽",
                _check_low_fuel_finish),

    # Missions
    Achievement("mission_5", "Task Runner", "Complete 5 missions", "missions", "📋",
                _check_mission_5, "total_missions_completed", 5),
    Achievement("mission_25", "Mission Expert", "Complete 25 missions", "missions", "📋",
                _check_mission_25, "total_missions_completed", 25),
]

ACHIEVEMENTS_BY_ID = {a.id: a for a in ALL_ACHIEVEMENTS}


def check_achievements(profile, run_record=None):
    """
    Check all achievements against current profile state.
    Returns list of newly earned Achievement objects.
    """
    newly_earned = []
    for ach in ALL_ACHIEVEMENTS:
        if ach.is_earned(profile):
            continue
        if ach.check(profile, run_record):
            profile.achievements_unlocked.append(ach.id)
            newly_earned.append(ach)

    # Update progress tracking
    profile.achievement_progress["high_score"] = profile.high_score
    profile.achievement_progress["total_runs"] = profile.total_runs
    profile.achievement_progress["total_missions_completed"] = (
        profile.lifetime_stats.get("total_missions_completed", 0)
    )

    return newly_earned


def get_achievement_categories():
    """Returns ordered list of (category_name, [achievements])."""
    cats = {}
    for a in ALL_ACHIEVEMENTS:
        cats.setdefault(a.category, []).append(a)
    order = ["score", "risk", "survival", "milestone", "collection", "mastery",
             "progression", "exploration", "modes", "feats", "missions"]
    result = []
    for cat in order:
        if cat in cats:
            result.append((cat.upper(), cats[cat]))
    return result


def get_all_achievements():
    """Returns list of dicts with name/description for UI display."""
    return [{"name": a.id, "description": a.description, "category": a.category} for a in ALL_ACHIEVEMENTS]
