"""
Combat — attack resolution, hitbox checking, damage application.
On GBA: simple AABB checks per frame, no physics engine.
"""
import math
from settings import TILE_SIZE


def get_attack_hitbox(attacker_x, attacker_y, facing, reach=1.2):
    """Return (cx, cy, radius) for an attack hitbox in tile coords."""
    offsets = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
    ox, oy = offsets.get(facing, (0, 1))
    cx = attacker_x + 0.5 + ox * reach * 0.5
    cy = attacker_y + 0.5 + oy * reach * 0.5
    return cx, cy, reach * 0.6


def circle_hits_entity(cx, cy, radius, entity_x, entity_y, entity_size=0.8):
    """Check if a circle overlaps an entity's bounding box (tile coords)."""
    ex = entity_x + 0.5
    ey = entity_y + 0.5
    dx = abs(cx - ex)
    dy = abs(cy - ey)
    half = entity_size / 2
    if dx > half + radius or dy > half + radius:
        return False
    if dx <= half or dy <= half:
        return True
    corner_dist = (dx - half) ** 2 + (dy - half) ** 2
    return corner_dist <= radius ** 2


def attack_has_los(attacker_x, attacker_y, target_x, target_y, tilemap):
    """Check line-of-sight between attacker and target by stepping through tiles.
    Returns False if any solid tile lies on the path between them."""
    ax = int(attacker_x + 0.5)
    ay = int(attacker_y + 0.5)
    tx = int(target_x + 0.5)
    ty = int(target_y + 0.5)
    dx = abs(tx - ax)
    dy = abs(ty - ay)
    sx = 1 if tx > ax else -1
    sy = 1 if ty > ay else -1
    err = dx - dy
    cx, cy = ax, ay
    while True:
        if (cx, cy) != (ax, ay) and tilemap.is_solid(cx, cy):
            return False
        if cx == tx and cy == ty:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            cx += sx
        if e2 < dx:
            err += dx
            cy += sy
    return True
