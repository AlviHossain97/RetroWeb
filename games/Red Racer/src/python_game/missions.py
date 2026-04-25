"""
missions.py — In-run dynamic mission/challenge system for Red Racer Ultimate Edition.

Missions give players mid-run objectives that:
- Reward bonus score, boost, or XP
- Improve replayability by creating dynamic goals
- Create tension and decision-making during runs

Each run randomly selects 1-3 missions from the pool.
Missions track progress live and notify on completion.

GBA Portability: GOOD CANDIDATE TO PORT (simple counter-based checks, small data)
"""

import random


class Mission:
    """A single in-run mission/challenge."""

    def __init__(self, mid, name, description, target, reward_type="score",
                 reward_amount=500, category="general"):
        self.id = mid
        self.name = name
        self.description = description
        self.target = target          # Target value to reach
        self.reward_type = reward_type  # "score", "boost", "xp"
        self.reward_amount = reward_amount
        self.category = category

        # Runtime state (reset per run)
        self.progress = 0
        self.completed = False
        self.notified = False  # For UI flash

    def reset(self):
        self.progress = 0
        self.completed = False
        self.notified = False

    def update_progress(self, value):
        if self.completed:
            return False
        self.progress = value
        if self.progress >= self.target:
            self.completed = True
            return True
        return False

    def add_progress(self, delta):
        if self.completed:
            return False
        self.progress += delta
        if self.progress >= self.target:
            self.completed = True
            return True
        return False

    def progress_ratio(self):
        return min(1.0, self.progress / max(1, self.target))


# --- Mission Pool ---

MISSION_POOL = [
    # Near-miss missions
    Mission("nm_3", "Close Calls", "Perform 3 near misses", 3, "score", 300, "risk"),
    Mission("nm_5", "Risk Taker", "Perform 5 near misses", 5, "score", 600, "risk"),
    Mission("nm_10", "Adrenaline Junkie", "Perform 10 near misses", 10, "score", 1200, "risk"),
    Mission("nm_15", "Daredevil Drive", "Perform 15 near misses", 15, "boost", 40, "risk"),

    # Survival missions
    Mission("surv_30", "Steady Start", "Survive 30 seconds", 30, "score", 200, "survival"),
    Mission("surv_60", "One Minute", "Survive 60 seconds", 60, "score", 500, "survival"),
    Mission("surv_120", "Two Minutes", "Survive 120 seconds", 120, "score", 1000, "survival"),
    Mission("surv_180", "Endurance Test", "Survive 180 seconds", 180, "xp", 50, "survival"),

    # Score missions
    Mission("score_500", "Point Getter", "Reach 500 score", 500, "boost", 20, "score"),
    Mission("score_2k", "Two Grand", "Reach 2,000 score", 2000, "boost", 30, "score"),
    Mission("score_5k", "Five Thousand", "Reach 5,000 score", 5000, "score", 800, "score"),

    # Combo missions
    Mission("combo_x2", "Combo Builder", "Reach 2x multiplier", 2, "score", 250, "combo"),
    Mission("combo_x4", "Chain Master", "Reach 4x multiplier", 4, "score", 600, "combo"),
    Mission("combo_x6", "Maximum Combo", "Reach 6x multiplier", 6, "boost", 50, "combo"),

    # Collection missions
    Mission("coins_3", "Coin Collector", "Collect 3 coins", 3, "score", 200, "collection"),
    Mission("coins_5", "Treasure Hunter", "Collect 5 coins", 5, "score", 400, "collection"),
    Mission("fuel_2", "Fuel Up", "Collect 2 fuel canisters", 2, "score", 200, "collection"),

    # Pass/overtake missions
    Mission("pass_10", "Traffic Weaver", "Pass 10 cars", 10, "score", 300, "traffic"),
    Mission("pass_20", "Overtake Artist", "Pass 20 cars", 20, "score", 600, "traffic"),
    Mission("pass_30", "Road Dominator", "Pass 30 cars", 30, "boost", 35, "traffic"),

    # Speed missions
    Mission("speed_180", "Speed Runner", "Reach 180 MPH", 180, "score", 400, "speed"),
    Mission("speed_220", "Velocity", "Reach 220 MPH", 220, "score", 700, "speed"),
    Mission("speed_250", "Terminal Speed", "Reach 250 MPH", 250, "boost", 40, "speed"),

    # Boost missions
    Mission("boost_5s", "Boost Beginner", "Use boost for 5 seconds", 5, "score", 300, "boost"),
    Mission("boost_15s", "Boost Runner", "Use boost for 15 seconds", 15, "score", 600, "boost"),
]


class MissionSystem:
    """Manages active missions for a run."""

    def __init__(self, mission_count=2, difficulty="NORMAL", game_mode="CLASSIC_ENDLESS"):
        self.active_missions = []
        self.completed_this_run = []
        self._select_missions(mission_count, difficulty, game_mode)

    def _select_missions(self, count, difficulty, game_mode):
        pool = list(MISSION_POOL)

        # Filter by mode
        if game_mode == "ZEN":
            pool = [m for m in pool if m.category not in ("risk",)]
        elif game_mode == "ONE_LIFE_HARDCORE":
            pool = [m for m in pool if m.category != "collection"]

        # Harder difficulty = harder missions
        if difficulty == "EASY":
            pool = [m for m in pool if m.target <= 15 or m.category == "survival"]
        elif difficulty == "HARD":
            pool = [m for m in pool if m.target >= 3]

        random.shuffle(pool)

        # Pick diverse categories
        seen_cats = set()
        selected = []
        for m in pool:
            if len(selected) >= count:
                break
            if m.category not in seen_cats or len(selected) < count:
                m_copy = Mission(m.id, m.name, m.description, m.target,
                                 m.reward_type, m.reward_amount, m.category)
                m_copy.reset()
                selected.append(m_copy)
                seen_cats.add(m.category)

        self.active_missions = selected[:count]

    def update(self, run_state):
        """
        Update all active missions with current run state.
        run_state is a dict with keys like:
        - near_misses, duration_seconds, score, multiplier,
        - coins_collected, fuel_collected, enemies_passed,
        - max_speed, boost_seconds
        Returns list of newly completed Mission objects.
        """
        newly_completed = []

        for m in self.active_missions:
            if m.completed:
                continue

            just_done = False

            if m.id.startswith("nm_"):
                just_done = m.update_progress(run_state.get("near_misses", 0))
            elif m.id.startswith("surv_"):
                just_done = m.update_progress(run_state.get("duration_seconds", 0))
            elif m.id.startswith("score_"):
                just_done = m.update_progress(run_state.get("score", 0))
            elif m.id.startswith("combo_"):
                just_done = m.update_progress(run_state.get("multiplier", 1.0))
            elif m.id.startswith("coins_"):
                just_done = m.update_progress(run_state.get("coins_collected", 0))
            elif m.id.startswith("fuel_"):
                just_done = m.update_progress(run_state.get("fuel_collected", 0))
            elif m.id.startswith("pass_"):
                just_done = m.update_progress(run_state.get("enemies_passed", 0))
            elif m.id.startswith("speed_"):
                just_done = m.update_progress(run_state.get("max_speed", 0))
            elif m.id.startswith("boost_"):
                just_done = m.update_progress(run_state.get("boost_seconds", 0))

            if just_done:
                newly_completed.append(m)
                self.completed_this_run.append(m)

        return newly_completed

    def get_rewards(self):
        """Sum up all rewards from completed missions."""
        rewards = {"score": 0, "boost": 0, "xp": 0}
        for m in self.completed_this_run:
            rewards[m.reward_type] = rewards.get(m.reward_type, 0) + m.reward_amount
        return rewards

    def get_completed_ids(self):
        return [m.id for m in self.completed_this_run]
