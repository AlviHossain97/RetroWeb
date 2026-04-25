"""Wallet / currency storage for coins and other future soft currencies."""


class Wallet:
    def __init__(self, coins: int = 0):
        self.coins = max(0, int(coins))

    def reset(self):
        self.coins = 0

    def set(self, amount: int):
        self.coins = max(0, int(amount))

    def add(self, amount: int) -> int:
        value = int(amount)
        if value < 0:
            raise ValueError("Wallet.add expects a non-negative amount")
        self.coins += value
        return self.coins

    def snapshot(self) -> dict:
        return {"coins": self.coins}
