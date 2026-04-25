"""
Visual effects — particles, screen shake, hit flash.
Lightweight and GBA-portable (no shaders, just sprite tricks).

Extended effects:
  emit_blood       — melee hit with direction-based blood arc
  emit_magic_sparks— magic weapon hit: blue/purple sparks
  emit_levelup     — starburst for level-up event
  emit_env_kill    — gold burst for environmental kills
  emit_fire        — fire embers rising upward
  emit_frost       — frost crystals (ice attacks)
  emit_leaves      — wind / weather leaves drifting
"""
import pygame
import math
import random
from game_math import angle_to, polar_offset
from settings import TILE_SIZE
from ui.fonts import get_font


class ScreenShake:
    def __init__(self):
        self.intensity = 0.0
        self.timer = 0.0
    def trigger(self, intensity=4.0, duration=0.15):
        self.intensity = intensity
        self.timer = duration
    def update(self, dt):
        if self.timer > 0:
            self.timer -= dt
            if self.timer <= 0:
                self.intensity = 0
    def get_offset(self):
        if self.timer <= 0: return 0, 0
        ox = random.randint(int(-self.intensity), int(self.intensity))
        oy = random.randint(int(-self.intensity), int(self.intensity))
        return ox, oy


class Particle:
    def __init__(self, x, y, vx, vy, color, life=0.4, size=3):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size
        self.alive = True
    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 60 * dt  # gravity
        self.life -= dt
        if self.life <= 0: self.alive = False
    def render(self, screen, cam_x, cam_y):
        if not self.alive: return
        alpha = max(0, self.life / self.max_life)
        sz = max(1, int(self.size * alpha))
        sx = int(self.x) - cam_x
        sy = int(self.y) - cam_y
        pygame.draw.circle(screen, self.color, (sx, sy), sz)


class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []

    def emit_hit(self, world_x, world_y, count=6):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(40, 120)
            vx, vy = polar_offset(angle, speed)
            vy -= 30
            color = random.choice([(255,255,200),(255,220,100),(255,180,80)])
            self.particles.append(Particle(world_x, world_y, vx, vy, color, 0.3, 3))

    def emit_death(self, world_x, world_y, color=(200,60,60), count=10):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(30, 100)
            vx, vy = polar_offset(angle, speed)
            vy -= 40
            self.particles.append(Particle(world_x, world_y, vx, vy, color, 0.5, 4))

    def emit_pickup(self, world_x, world_y):
        for _ in range(5):
            vx = random.uniform(-20, 20)
            vy = random.uniform(-80, -30)
            self.particles.append(Particle(world_x, world_y, vx, vy, (255,255,150), 0.4, 2))

    def emit_dust(self, world_x, world_y):
        for _ in range(3):
            vx = random.uniform(-15, 15)
            vy = random.uniform(-10, -30)
            self.particles.append(Particle(world_x, world_y, vx, vy, (160,150,130), 0.3, 2))

    def emit_blood(self, world_x, world_y, facing="down", count=8):
        """Directional blood spatter — arcs away from attack direction."""
        dir_map = {"up":(0,-1),"down":(0,1),"left":(-1,0),"right":(1,0)}
        dx, dy = dir_map.get(facing, (0, 1))
        base_angle = angle_to(dx, dy)
        for _ in range(count):
            spread = random.uniform(-0.9, 0.9)
            a = base_angle + spread
            speed = random.uniform(50, 130)
            vx, vy = polar_offset(a, speed)
            vy -= 20
            size = random.randint(2, 4)
            life = random.uniform(0.3, 0.5)
            color = random.choice([(180, 20, 20), (220, 40, 40), (160, 10, 10)])
            self.particles.append(Particle(world_x, world_y, vx, vy, color, life, size))

    def emit_magic_sparks(self, world_x, world_y, color=(100, 140, 255), count=10):
        """Magic weapon hit — electric sparks in arc."""
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(60, 160)
            vx, vy = polar_offset(angle, speed)
            vy -= 40
            c = random.choice([color, (200, 220, 255), (160, 80, 255)])
            size = random.randint(2, 3)
            self.particles.append(Particle(world_x, world_y, vx, vy, c, 0.4, size))

    def emit_levelup(self, world_x, world_y):
        """Starburst for level-up event — golden and white rays outward."""
        for i in range(20):
            angle = (i / 20) * math.pi * 2 + random.uniform(-0.1, 0.1)
            speed = random.uniform(80, 200)
            vx, vy = polar_offset(angle, speed)
            color = random.choice([(255, 220, 60), (255, 255, 180), (220, 200, 80)])
            self.particles.append(Particle(world_x, world_y, vx, vy, color, 0.8, 4))
        # Central flash ring — inner burst
        for _ in range(8):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(20, 60)
            vx, vy = polar_offset(angle, speed)
            self.particles.append(Particle(
                world_x, world_y,
                vx, vy - 10,
                (255, 255, 255), 0.3, 3,
            ))

    def emit_env_kill(self, world_x, world_y):
        """Gold + impact burst for environmental kills (bonus XP)."""
        for _ in range(15):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(40, 120)
            vx, vy = polar_offset(angle, speed)
            vy -= 60
            color = random.choice([(255, 200, 40), (255, 240, 100), (200, 160, 20)])
            self.particles.append(Particle(world_x, world_y, vx, vy, color, 0.6, 3))

    def emit_fire(self, world_x, world_y, count=6):
        """Rising fire embers — moves upward with random drift."""
        for _ in range(count):
            vx = random.uniform(-15, 15)
            vy = random.uniform(-80, -30)
            color = random.choice([(255,120,20),(255,80,10),(220,160,30)])
            self.particles.append(Particle(world_x, world_y, vx, vy, color, 0.5, 3))

    def emit_frost(self, world_x, world_y, count=8):
        """Ice crystal shards — slow, sparkle blue/white."""
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(20, 70)
            vx, vy = polar_offset(angle, speed)
            vy -= 10
            color = random.choice([(160, 220, 255), (200, 240, 255), (80, 160, 220)])
            p = Particle(world_x, world_y, vx, vy, color, 0.6, 2)
            p.vy = vy * 0.3   # frost falls slowly
            self.particles.append(p)

    def emit_leaves(self, world_x, world_y, count=4):
        """Falling leaves for wind/weather ambiance."""
        for _ in range(count):
            vx = random.uniform(-20, 20)
            vy = random.uniform(-5, 30)
            color = random.choice([(80,140,40),(60,120,30),(100,160,50),(120,100,30)])
            self.particles.append(Particle(world_x, world_y, vx, vy, color, 1.2, 2))

    def emit_item_glow(self, world_x, world_y, color=(255, 200, 80)):
        """Hovering glow dots over an item on the ground."""
        for _ in range(3):
            vx = random.uniform(-8, 8)
            vy = random.uniform(-20, -10)
            self.particles.append(Particle(world_x, world_y, vx, vy, color, 0.6, 2))

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]

    def render(self, screen, cam_x, cam_y):
        for p in self.particles:
            p.render(screen, cam_x, cam_y)


class DamageNumber:
    _font = None

    @classmethod
    def _get_font(cls):
        if cls._font is None:
            cls._font = get_font(16, bold=True)
        return cls._font

    def __init__(self, x, y, text, color=(255,255,255)):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.timer = 0.8
        self.alive = True
        self.vy = -40
    def update(self, dt):
        self.y += self.vy * dt
        self.timer -= dt
        if self.timer <= 0: self.alive = False
    def render(self, screen, cam_x, cam_y):
        if not self.alive: return
        alpha = min(1.0, self.timer / 0.3)
        sx, sy = int(self.x) - cam_x, int(self.y) - cam_y
        font = self._get_font()
        surf = font.render(self.text, True, self.color)
        screen.blit(surf, (sx - surf.get_width()//2, sy))


class DamageNumberSystem:
    def __init__(self):
        self.numbers: list[DamageNumber] = []
    def spawn(self, world_x, world_y, amount, color=(255,100,100)):
        self.numbers.append(DamageNumber(world_x, world_y, str(amount), color))
    def update(self, dt):
        for n in self.numbers: n.update(dt)
        self.numbers = [n for n in self.numbers if n.alive]
    def render(self, screen, cam_x, cam_y):
        for n in self.numbers: n.render(screen, cam_x, cam_y)
