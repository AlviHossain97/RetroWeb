"""
economy.py - Gold, lives, cost validation, and wave-clear bonus for Bastion TD.
"""
from settings import START_GOLD, START_LIVES, WAVE_CLEAR_BONUS


class Economy:
    """Tracks the player's gold and lives."""

    def __init__(self):
        self.gold: int = START_GOLD
        self.lives: int = START_LIVES
        self.total_earned: int = 0

    def can_afford(self, cost: int) -> bool:
        """Return True if the player has enough gold."""
        return self.gold >= cost

    def spend(self, cost: int) -> None:
        """Subtract gold (caller must check can_afford first)."""
        self.gold -= cost

    def earn(self, amount: int) -> None:
        """Add gold and track total earned."""
        self.gold += amount
        self.total_earned += amount

    def lose_lives(self, amount: int) -> None:
        """Subtract lives."""
        self.lives -= amount

    def is_game_over(self) -> bool:
        """True if lives have reached zero or below."""
        return self.lives <= 0

    def wave_clear_bonus(self) -> None:
        """Award the wave-clear bonus gold."""
        self.earn(WAVE_CLEAR_BONUS)
