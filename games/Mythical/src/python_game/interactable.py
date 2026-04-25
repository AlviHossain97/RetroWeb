"""
Interactables — chests, ground pickups, and other tile-based interactions.
Each has a position, a type, and state (opened/collected or not).
On GBA: array of structs in EWRAM, state bits in SRAM.
"""

import math
import pygame
from rewards import REWARD_CURRENCY, REWARD_HEAL, REWARD_KEY_ITEM, make_key_item_reward, normalize_reward
from runtime.frame_clock import get_time
from settings import TILE_SIZE


def _canonical_reward(reward: dict) -> dict:
    normalized = normalize_reward(reward)
    canonical = {"kind": normalized["kind"]}
    if normalized["kind"] == REWARD_KEY_ITEM:
        canonical["item_id"] = normalized["item_id"]
    else:
        canonical["amount"] = normalized["amount"]
    if normalized.get("label"):
        canonical["label"] = normalized["label"]
    return canonical


class Chest:
    def __init__(
        self,
        tile_x: int,
        tile_y: int,
        item_id: str | None = None,
        label: str = "Chest",
        chest_id: str | None = None,
        reward: dict | None = None,
    ):
        self.x = tile_x
        self.y = tile_y
        self.label = label
        self.chest_id = chest_id or f"chest_{tile_x}_{tile_y}"
        self.opened = False
        if reward is None:
            reward = make_key_item_reward(item_id or "", label=label)
        self.reward = _canonical_reward(reward)

    def occupies(self, tx: int, ty: int) -> bool:
        return self.x == tx and self.y == ty and not self.opened

    def open(self) -> dict | None:
        """Open the chest. Returns reward payload if not already opened."""
        if self.opened:
            return None
        self.opened = True
        return dict(self.reward)

    def render(self, screen: pygame.Surface, cam_x: int, cam_y: int):
        """Render is handled by tilemap decor, but we draw an indicator if unopened."""
        if self.opened:
            return
        sx = self.x * TILE_SIZE - cam_x
        sy = self.y * TILE_SIZE - cam_y
        # Sparkle indicator
        t = get_time() * (1000.0 / 300.0)
        alpha = int(120 + 80 * math.sin(t))
        sparkle = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(sparkle, (255, 255, 150, alpha), (4, 4), 4)
        screen.blit(sparkle, (sx + TILE_SIZE // 2 - 4, sy - 6))


class GroundItem:
    def __init__(
        self,
        tile_x: int,
        tile_y: int,
        item_id: str | None = None,
        item_kind: str = "item",
        heal_amount: int = 0,
        drop_id: str | None = None,
        label: str = "",
        dynamic: bool = False,
        reward: dict | None = None,
    ):
        self.x = tile_x
        self.y = tile_y
        self.dynamic = dynamic
        self.collected = False
        if reward is None:
            if item_kind == REWARD_HEAL:
                reward = {"kind": REWARD_HEAL, "amount": heal_amount, "label": label}
            else:
                reward = {"kind": item_kind, "item_id": item_id, "label": label}
        self.reward = _canonical_reward(reward)
        reward_key = self.reward.get("item_id", self.reward.get("kind"))
        self.drop_id = drop_id or f"drop_{tile_x}_{tile_y}_{reward_key}"

    def occupies(self, tx: int, ty: int) -> bool:
        return self.x == tx and self.y == ty and not self.collected

    def collect(self) -> dict | None:
        if self.collected:
            return None
        self.collected = True
        return {
            "reward": dict(self.reward),
            "drop_id": self.drop_id,
            "dynamic": self.dynamic,
        }

    def to_save_data(self, map_name: str) -> dict:
        return {
            "id": self.drop_id,
            "map": map_name,
            "x": self.x,
            "y": self.y,
            "reward": dict(self.reward),
        }

    def render(self, screen: pygame.Surface, cam_x: int, cam_y: int):
        if self.collected:
            return
        sx = self.x * TILE_SIZE - cam_x
        sy = self.y * TILE_SIZE - cam_y
        bob = int(3 * math.sin(get_time() * (1000.0 / 400.0)))
        cx = sx + TILE_SIZE // 2
        cy = sy + TILE_SIZE // 2 + bob

        reward_kind = self.reward["kind"]

        if reward_kind == REWARD_KEY_ITEM:
            item_id = self.reward.get("item_id", "")
            if item_id:
                from item_system import draw_item_icon
                icon_size = 18
                # Subtle shadow/glow behind icon
                glow = pygame.Surface((icon_size + 6, icon_size + 6), pygame.SRCALPHA)
                pygame.draw.circle(glow, (0, 0, 0, 70),
                                   (icon_size // 2 + 3, icon_size // 2 + 3), icon_size // 2 + 2)
                screen.blit(glow, (cx - icon_size // 2 - 3, cy - icon_size // 2 - 3))
                draw_item_icon(screen, item_id, cx - icon_size // 2, cy - icon_size // 2, icon_size)
                return

        if reward_kind == REWARD_HEAL:
            outer = (120, 255, 140)
            inner = (220, 255, 220)
        elif reward_kind == REWARD_CURRENCY:
            outer = (255, 210, 70)
            inner = (255, 245, 170)
        else:
            outer = (255, 220, 80)
            inner = (255, 250, 180)
        pygame.draw.circle(screen, outer, (cx, cy), 5)
        pygame.draw.circle(screen, inner, (cx, cy - 1), 2)
