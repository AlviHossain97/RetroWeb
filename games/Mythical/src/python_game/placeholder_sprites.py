"""
Placeholder sprite generator — creates detailed colored character sprites at runtime.
Swap this out for real spritesheet loading when you have art assets.

Characters have: shadow, body, tunic/clothing, head, hair, eyes, arms, and feet.
4 directions × 4 frames (idle, walk1, idle-mirror, walk2).

Visual direction: clear silhouettes, distinct clothing, readable face at tile scale.
"""

import pygame
import math
from settings import TILE_SIZE

DIRECTIONS = ["down", "up", "left", "right"]
FRAMES_PER_DIR = 4


def _darken(color, amount=40):
    return tuple(max(0, c - amount) for c in color)


def _lighten(color, amount=40):
    return tuple(min(255, c + amount) for c in color)


def _mix(a, b, t=0.5):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def generate_character_sheet(
    body_color: tuple[int, int, int],
    head_color: tuple[int, int, int] | None = None,
    hair_color: tuple[int, int, int] | None = None,
    eye_color: tuple[int, int, int] = (25, 25, 50),
    size: int = TILE_SIZE,
    jeans_color: tuple[int, int, int] | None = None,
) -> dict[str, list[pygame.Surface]]:
    """
    Generate a dict of {direction: [frame_surfaces]} for a character.
    """
    if head_color is None:
        head_color = (225, 185, 145)
    if hair_color is None:
        hair_color = _darken(body_color, 30)

    S = size
    sheets: dict[str, list[pygame.Surface]] = {}

    for direction in DIRECTIONS:
        frames = []
        for f in range(FRAMES_PER_DIR):
            surf = pygame.Surface((S, S), pygame.SRCALPHA)

            # Walk cycle offsets
            is_walk = f in (1, 3)
            bob = -2 if is_walk else 0
            sway = (1 if f == 1 else -1) if is_walk else 0
            # Leg offsets for walk
            left_leg_off = 3 if f == 1 else (-3 if f == 3 else 0)
            right_leg_off = -left_leg_off
            # Arm swing
            left_arm_off = -2 if f == 1 else (2 if f == 3 else 0)
            right_arm_off = -left_arm_off

            cx = S // 2 + sway

            # === SHADOW (ellipse on ground) ===
            shadow_surf = pygame.Surface((S, S), pygame.SRCALPHA)
            shadow_w, shadow_h = S * 5 // 8, S // 7
            shadow_rect = pygame.Rect(
                cx - shadow_w // 2, S - shadow_h - 1, shadow_w, shadow_h
            )
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 58), shadow_rect)
            surf.blit(shadow_surf, (0, 0))

            # Proportions
            head_r = S * 5 // 24          # radius
            head_cy = S * 5 // 16 + bob   # center y of head
            body_top = head_cy + head_r - 1
            body_w = S * 5 // 12
            body_h = S * 5 // 16
            leg_top = body_top + body_h - 2
            leg_w = S // 6
            leg_h = S * 3 // 16
            foot_h = S // 10
            arm_w = S // 7
            arm_h = S * 5 // 16

            # === LEGS ===
            leg_color = jeans_color if jeans_color else _darken(body_color, 20)
            foot_color = _darken(jeans_color, 30) if jeans_color else _darken(body_color, 50)
            # Left leg
            ll_x = cx - body_w // 4 - leg_w // 2
            ll_y = leg_top + left_leg_off
            pygame.draw.rect(surf, leg_color,
                             (ll_x, ll_y, leg_w, leg_h), border_radius=2)
            # Left foot
            pygame.draw.rect(surf, foot_color,
                             (ll_x - 1, ll_y + leg_h - 2, leg_w + 2, foot_h),
                             border_radius=2)

            # Right leg
            rl_x = cx + body_w // 4 - leg_w // 2
            rl_y = leg_top + right_leg_off
            pygame.draw.rect(surf, leg_color,
                             (rl_x, rl_y, leg_w, leg_h), border_radius=2)
            # Right foot
            pygame.draw.rect(surf, foot_color,
                             (rl_x - 1, rl_y + leg_h - 2, leg_w + 2, foot_h),
                             border_radius=2)

            # === ARMS (behind body for down/up, beside for left/right) ===
            if direction in ("left", "right"):
                # Arms visible on sides
                # Back arm
                ba_x = cx - body_w // 2 - arm_w + 2 if direction == "right" else cx + body_w // 2 - 2
                ba_y = body_top + 4 + right_arm_off
                pygame.draw.rect(surf, head_color,
                                 (ba_x, ba_y, arm_w, arm_h), border_radius=3)

            else:
                # Left arm
                la_x = cx - body_w // 2 - arm_w + 3
                la_y = body_top + 4 + left_arm_off
                pygame.draw.rect(surf, head_color,
                                 (la_x, la_y, arm_w, arm_h - 2), border_radius=3)
                # Right arm
                ra_x = cx + body_w // 2 - 3
                ra_y = body_top + 4 + right_arm_off
                pygame.draw.rect(surf, head_color,
                                 (ra_x, ra_y, arm_w, arm_h - 2), border_radius=3)

            # === BODY / SHIRT ===
            body_rect = pygame.Rect(cx - body_w // 2, body_top, body_w, body_h)
            pygame.draw.rect(surf, body_color, body_rect, border_radius=3)
            # Side shadow to give volume
            shadow_side = pygame.Surface((body_w // 3, body_h), pygame.SRCALPHA)
            shadow_side.fill((0, 0, 0, 28))
            surf.blit(shadow_side, (cx + body_w // 2 - body_w // 3, body_top))
            if jeans_color:
                # Casual shirt: hem line + subtle collar
                hem_y = body_top + body_h - 2
                pygame.draw.line(surf, _darken(body_color, 18),
                                 (cx - body_w // 2 + 1, hem_y),
                                 (cx + body_w // 2 - 1, hem_y), 1)
                # Collar V
                pygame.draw.line(surf, _lighten(body_color, 25),
                                 (cx - 2, body_top + 2), (cx, body_top + 5), 1)
                pygame.draw.line(surf, _lighten(body_color, 25),
                                 (cx + 2, body_top + 2), (cx, body_top + 5), 1)
            else:
                # Fantasy tunic: belt line + decorative collar + shoulder line
                belt_y = body_top + body_h * 2 // 3
                # Belt
                pygame.draw.rect(surf, _darken(body_color, 35),
                                 (cx - body_w // 2 + 1, belt_y - 1, body_w - 2, 3),
                                 border_radius=1)
                # Belt buckle
                pygame.draw.rect(surf, (185, 155, 38),
                                 (cx - 2, belt_y - 1, 4, 3))
                # Collar
                collar_y = body_top + 2
                pygame.draw.line(surf, _lighten(body_color, 25),
                                 (cx - 4, collar_y), (cx + 4, collar_y), 2)
                # Shoulder seam
                pygame.draw.line(surf, _darken(body_color, 15),
                                 (cx - body_w // 2 + 2, body_top + 3),
                                 (cx - body_w // 2 + 2, body_top + 6), 1)
                pygame.draw.line(surf, _darken(body_color, 15),
                                 (cx + body_w // 2 - 3, body_top + 3),
                                 (cx + body_w // 2 - 3, body_top + 6), 1)

            # Front arm (for side views)
            if direction in ("left", "right"):
                fa_x = cx + body_w // 2 - 2 if direction == "right" else cx - body_w // 2 - arm_w + 2
                fa_y = body_top + 4 + left_arm_off
                pygame.draw.rect(surf, head_color,
                                 (fa_x, fa_y, arm_w, arm_h), border_radius=3)

            # === HEAD ===
            if jeans_color:
                # Blocky head (rounded rect, Steve-style)
                head_rect = pygame.Rect(cx - head_r, head_cy - head_r, head_r * 2, head_r * 2)
                pygame.draw.rect(surf, head_color, head_rect, border_radius=3)
            else:
                pygame.draw.circle(surf, head_color, (cx, head_cy), head_r)

            # === HAIR ===
            if jeans_color:
                # Blocky flat hair on top
                hair_h = head_r * 2 // 3
                if direction == "down":
                    pygame.draw.rect(surf, hair_color,
                                     (cx - head_r, head_cy - head_r, head_r * 2, hair_h),
                                     border_radius=2)
                    # Bangs
                    pygame.draw.rect(surf, hair_color,
                                     (cx - head_r + 1, head_cy - head_r + hair_h - 2, head_r * 2 - 2, 3))
                elif direction == "up":
                    pygame.draw.rect(surf, hair_color,
                                     (cx - head_r, head_cy - head_r, head_r * 2, head_r * 2),
                                     border_radius=3)
                elif direction == "left":
                    pygame.draw.rect(surf, hair_color,
                                     (cx - head_r, head_cy - head_r, head_r * 2, hair_h),
                                     border_radius=2)
                    pygame.draw.rect(surf, hair_color,
                                     (cx, head_cy - head_r, head_r, head_r * 2),
                                     border_radius=2)
                elif direction == "right":
                    pygame.draw.rect(surf, hair_color,
                                     (cx - head_r, head_cy - head_r, head_r * 2, hair_h),
                                     border_radius=2)
                    pygame.draw.rect(surf, hair_color,
                                     (cx - head_r, head_cy - head_r, head_r, head_r * 2),
                                     border_radius=2)
            else:
                if direction == "down":
                    hair_rect = pygame.Rect(cx - head_r, head_cy - head_r,
                                            head_r * 2, head_r)
                    pygame.draw.ellipse(surf, hair_color, hair_rect)
                elif direction == "up":
                    pygame.draw.circle(surf, hair_color, (cx, head_cy), head_r)
                    ear_r = head_r // 3
                    pygame.draw.circle(surf, head_color, (cx - head_r + 2, head_cy + 2), ear_r)
                    pygame.draw.circle(surf, head_color, (cx + head_r - 2, head_cy + 2), ear_r)
                elif direction == "left":
                    pygame.draw.circle(surf, hair_color, (cx + 1, head_cy), head_r)
                    pygame.draw.circle(surf, head_color, (cx - 2, head_cy), head_r - 2)
                    pygame.draw.ellipse(surf, hair_color,
                                        (cx - head_r, head_cy - head_r, head_r * 2, head_r))
                elif direction == "right":
                    pygame.draw.circle(surf, hair_color, (cx - 1, head_cy), head_r)
                    pygame.draw.circle(surf, head_color, (cx + 2, head_cy), head_r - 2)
                    pygame.draw.ellipse(surf, hair_color,
                                        (cx - head_r, head_cy - head_r, head_r * 2, head_r))

            # === EYES ===
            eye_size = max(2, S // 14)
            white = (248, 245, 238)
            if direction == "down":
                for ex_off in (-head_r // 3, head_r // 3):
                    # White sclerae
                    pygame.draw.circle(surf, white, (cx + ex_off, head_cy + 1), eye_size)
                    # Iris
                    pygame.draw.circle(surf, eye_color, (cx + ex_off, head_cy + 2), eye_size - 1)
                    # Tiny highlight
                    pygame.draw.circle(surf, (255, 255, 255),
                                       (cx + ex_off - 1, head_cy), max(1, eye_size // 3))
            elif direction == "up":
                pass  # back of head
            elif direction == "left":
                ex = cx - head_r // 3 - 1
                pygame.draw.circle(surf, white, (ex + 1, head_cy + 1), eye_size)
                pygame.draw.circle(surf, eye_color, (ex, head_cy + 2), eye_size - 1)
                pygame.draw.circle(surf, (255, 255, 255), (ex - 1, head_cy), max(1, eye_size // 3))
            elif direction == "right":
                ex = cx + head_r // 3 + 1
                pygame.draw.circle(surf, white, (ex - 1, head_cy + 1), eye_size)
                pygame.draw.circle(surf, eye_color, (ex, head_cy + 2), eye_size - 1)
                pygame.draw.circle(surf, (255, 255, 255), (ex + 1, head_cy), max(1, eye_size // 3))

            # === MOUTH (only facing down) ===
            if direction == "down":
                mouth_y = head_cy + head_r // 2 + 1
                pygame.draw.line(surf, _darken(head_color, 60),
                                 (cx - 2, mouth_y), (cx + 2, mouth_y), 1)

            frames.append(surf)
        sheets[direction] = frames

    return sheets
