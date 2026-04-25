"""
save_manager.py - JSON high-score persistence for Bastion TD.
"""
import json
import os


class SaveManager:
    """Handles loading and saving high-score data to a JSON file."""

    def __init__(self):
        # Place save file in the same directory as this module
        self.SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "bastion_td_save.json")

    def load(self):
        """Load save data from JSON file. Return defaults if file doesn't exist or is corrupt."""
        default = {"best_wave": 0, "best_score": 0, "games_played": 0}
        if not os.path.exists(self.SAVE_FILE):
            return default
        try:
            with open(self.SAVE_FILE, "r") as f:
                data = json.load(f)
            # Ensure all keys exist
            for key in default:
                if key not in data:
                    data[key] = default[key]
            return data
        except (json.JSONDecodeError, IOError, OSError):
            return default

    def save(self, wave, score, games_played):
        """Save high-score data. Only update best_wave/best_score if current exceeds previous."""
        data = self.load()
        if wave > data["best_wave"]:
            data["best_wave"] = wave
        if score > data["best_score"]:
            data["best_score"] = score
        data["games_played"] = games_played
        try:
            with open(self.SAVE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except (IOError, OSError):
            pass

    def increment_games(self):
        """Load data, increment games_played by 1, and save."""
        data = self.load()
        data["games_played"] = data.get("games_played", 0) + 1
        try:
            with open(self.SAVE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except (IOError, OSError):
            pass
