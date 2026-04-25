"""
effects.py - Particle system, screen shake, and damage number effects for Bastion TD.
"""
import random
import math
import pygame
from settings import *


class ParticleSystem:
    """Manages a pool of small particles for visual effects."""

    def __init__(self):
        self.particles = []  # [{x, y, vx, vy, color, life, max_life}]

    def emit(self, x, y, color, count=10, spread=2.0):
        """Emit particles at tile position (x, y) with random velocities."""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, spread)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.uniform(0.3, 0.8)
            self.particles.append({
                "x": x,
                "y": y,
                "vx": vx,
                "vy": vy,
                "color": color,
                "life": life,
                "max_life": life,
            })

    def update(self, dt):
        """Move particles, decrement life, remove dead ones."""
        alive = []
        for p in self.particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
            if p["life"] > 0:
                alive.append(p)
        self.particles = alive

    def render(self, screen, offset_x, offset_y):
        """Draw particles as small filled circles with alpha fade."""
        for p in self.particles:
            alpha_ratio = max(0.0, p["life"] / p["max_life"])
            px = int(p["x"] * TILE_SIZE + offset_x)
            py = int(p["y"] * TILE_SIZE + offset_y)
            radius = max(1, int(3 * alpha_ratio))
            # Fade color toward black based on remaining life
            r = int(p["color"][0] * alpha_ratio)
            g = int(p["color"][1] * alpha_ratio)
            b = int(p["color"][2] * alpha_ratio)
            faded_color = (max(0, min(255, r)),
                           max(0, min(255, g)),
                           max(0, min(255, b)))
            # Use a small surface with per-pixel alpha for smooth fade
            size = radius * 2 + 2
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            alpha_val = int(255 * alpha_ratio)
            draw_color = (faded_color[0], faded_color[1], faded_color[2], alpha_val)
            pygame.draw.circle(surf, draw_color, (size // 2, size // 2), radius)
            screen.blit(surf, (px - size // 2, py - size // 2))


class ScreenShake:
    """Simple screen shake effect with decaying intensity."""

    def __init__(self):
        self.timer = 0.0
        self.intensity = 0.0

    def trigger(self, intensity=4, duration=0.3):
        """Start a screen shake with given pixel intensity and duration."""
        self.intensity = intensity
        self.timer = duration

    def update(self, dt):
        """Decrement the shake timer."""
        if self.timer > 0:
            self.timer -= dt
            if self.timer < 0:
                self.timer = 0

    def get_offset(self):
        """Return (dx, dy) random pixel offset if shaking, else (0, 0)."""
        if self.timer > 0:
            dx = random.randint(int(-self.intensity), int(self.intensity))
            dy = random.randint(int(-self.intensity), int(self.intensity))
            return (dx, dy)
        return (0, 0)


class DamageNumberSystem:
    """Floating damage numbers that drift upward and fade out."""

    def __init__(self):
        self.numbers = []  # [{x, y, text, life, max_life, vy}]

    def add(self, x, y, amount):
        """Create a floating damage number at tile position (x, y)."""
        # Format: integer if whole number, one decimal otherwise
        if amount == int(amount):
            text = str(int(amount))
        else:
            text = f"{amount:.1f}"
        self.numbers.append({
            "x": x,
            "y": y,
            "text": text,
            "life": 0.6,
            "max_life": 0.6,
            "vy": -1.0,  # tiles per second upward
        })

    def update(self, dt):
        """Move numbers upward, decrement life, remove expired."""
        alive = []
        for n in self.numbers:
            n["y"] += n["vy"] * dt
            n["life"] -= dt
            if n["life"] > 0:
                alive.append(n)
        self.numbers = alive

    def render(self, screen, offset_x, offset_y):
        """Draw floating damage numbers with alpha fade."""
        font = pygame.font.SysFont("monospace", 14)
        for n in self.numbers:
            alpha_ratio = max(0.0, n["life"] / n["max_life"])
            px = int(n["x"] * TILE_SIZE + offset_x)
            py = int(n["y"] * TILE_SIZE + offset_y)
            # Render text with fade
            text_surf = font.render(n["text"], True, COLOR_WHITE)
            alpha_val = int(255 * alpha_ratio)
            text_surf.set_alpha(alpha_val)
            # Center the text horizontally on the position
            text_rect = text_surf.get_rect(center=(px, py))
            screen.blit(text_surf, text_rect)
