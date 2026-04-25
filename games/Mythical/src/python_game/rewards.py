"""Typed reward helpers so gameplay routes rewards explicitly and safely."""
from __future__ import annotations


REWARD_KEY_ITEM = "key_item"
REWARD_CURRENCY = "currency"
REWARD_HEAL = "heal"

VALID_REWARD_KINDS = {REWARD_KEY_ITEM, REWARD_CURRENCY, REWARD_HEAL}
_ALIASES = {"item": REWARD_KEY_ITEM, "coin": REWARD_CURRENCY, "coins": REWARD_CURRENCY}


def make_key_item_reward(item_id: str, label: str | None = None) -> dict:
    reward = {"kind": REWARD_KEY_ITEM, "item_id": item_id}
    if label:
        reward["label"] = label
    return reward


def make_currency_reward(amount: int, label: str | None = None) -> dict:
    reward = {"kind": REWARD_CURRENCY, "amount": int(amount)}
    if label:
        reward["label"] = label
    return reward


def make_heal_reward(amount: int, label: str | None = None) -> dict:
    reward = {"kind": REWARD_HEAL, "amount": int(amount)}
    if label:
        reward["label"] = label
    return reward


def normalize_reward(reward: dict) -> dict:
    if reward is None:
        raise ValueError("Reward cannot be None")
    normalized = dict(reward)
    kind = _ALIASES.get(normalized.get("kind"), normalized.get("kind"))
    normalized["kind"] = kind
    assert kind in VALID_REWARD_KINDS, f"Unsupported reward kind: {kind!r}"

    if kind == REWARD_KEY_ITEM:
        item_id = normalized.get("item_id")
        assert isinstance(item_id, str) and item_id, "Key-item reward requires a non-empty item_id"
    elif kind in (REWARD_CURRENCY, REWARD_HEAL):
        raw_amount = normalized.get("amount")
        if raw_amount is None and kind == REWARD_HEAL:
            raw_amount = normalized.get("heal")
        amount = int(raw_amount or 0)
        assert amount > 0, f"{kind} reward requires amount > 0"
        normalized["amount"] = amount
        normalized.pop("heal", None)

    return normalized


def reward_label(reward: dict) -> str:
    reward = normalize_reward(reward)
    if reward["kind"] == REWARD_KEY_ITEM:
        return reward.get("label", reward["item_id"])
    if reward["kind"] == REWARD_CURRENCY:
        return reward.get("label", "coins")
    return reward.get("label", "healing")


def is_currency(reward: dict) -> bool:
    """Check if a reward dict is currency without full normalization."""
    kind = _ALIASES.get(reward.get("kind"), reward.get("kind"))
    return kind == REWARD_CURRENCY


def is_key_item(reward: dict) -> bool:
    """Check if a reward dict is a key item without full normalization."""
    kind = _ALIASES.get(reward.get("kind"), reward.get("kind"))
    return kind == REWARD_KEY_ITEM
