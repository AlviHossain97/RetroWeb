import random
import pygame
import os
from settings import *
from utils import load_image

class Entity:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def draw_rect(self, screen, color):
        pygame.draw.rect(screen, color, self.rect)

class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(2, 5) # Moving down relative to screen (since car moves up/static)
        self.radius = random.randint(3, 6)
        self.color = [100, 100, 100] # Gray
        self.alpha = 255
        self.lifetime = random.randint(20, 40)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.radius -= 0.1
        self.alpha -= 5
        self.lifetime -= 1
        return self.lifetime > 0

    def draw(self, screen):
        if self.radius > 0:
            s = pygame.Surface((self.radius*2, self.radius*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, max(0, self.alpha)), (self.radius, self.radius), self.radius)
            screen.blit(s, (self.x - self.radius, self.y - self.radius))

class Player(Entity):
    def __init__(self, x, y, image, road_limits=(ROAD_LEFT, ROAD_RIGHT)):
        super().__init__(x, y, 50, 100)
        self.original_image = image
        self.image = image
        self.speed = PLAYER_SPEED
        self.angle = 0
        self.target_angle = 0
        self.road_left = road_limits[0]
        self.road_right = road_limits[1]
        # Additive handling systems (toggleable via feature flags)
        self.use_inertia = False
        self.use_drift_assist = False
        self.lateral_velocity = 0.0
        self.max_lateral_speed = float(PLAYER_SPEED)
        self.lateral_accel = 1.2
        self.lateral_friction = 0.80
        self.boost_multiplier = 1.0
        self.last_steer_dir = 0
        self.last_steer_change_frame = 0
        self.precision_correction = False

    def configure_handling(self, use_inertia=False, use_drift_assist=False):
        self.use_inertia = bool(use_inertia)
        self.use_drift_assist = bool(use_drift_assist)

    def set_boost_multiplier(self, boost_multiplier):
        self.boost_multiplier = max(1.0, float(boost_multiplier))

    def move(self, keys, ai_action=None):
        # Determine movement and angle
        self.target_angle = 0
        self.precision_correction = False
        
        move_left = False
        move_right = False
        move_up = False
        move_down = False
        
        if ai_action:
            if ai_action == "LEFT": 
                move_left = True
                if self.rect.x <= self.road_left:
                    print(f"DEBUG: Blocked Left. X={self.rect.x} Limit={self.road_left}")
            elif ai_action == "RIGHT": 
                move_right = True
                if self.rect.x >= self.road_right - self.rect.width:
                    print(f"DEBUG: Blocked Right. X={self.rect.x} Limit={self.road_right} Width={self.rect.width}")
            elif ai_action == "BRAKE":
                move_down = True
            
            # print(f"DEBUG: AI Action {ai_action} -> L:{move_left} R:{move_right}. Speed={self.speed}")
        else:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: move_left = True
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: move_right = True
            if keys[pygame.K_UP] or keys[pygame.K_w]: move_up = True
            if keys[pygame.K_DOWN] or keys[pygame.K_s]: move_down = True

        steer_dir = 0
        if move_left and not move_right:
            steer_dir = -1
        elif move_right and not move_left:
            steer_dir = 1

        # Reward micro-corrections (quick, controlled counter-steer)
        current_ticks = pygame.time.get_ticks()
        if steer_dir != 0 and self.last_steer_dir != 0 and steer_dir != self.last_steer_dir:
            if current_ticks - self.last_steer_change_frame < 220:
                self.precision_correction = True
            self.last_steer_change_frame = current_ticks
        elif steer_dir != 0 and self.last_steer_dir == 0:
            self.last_steer_change_frame = current_ticks
        if steer_dir != 0:
            self.last_steer_dir = steer_dir

        effective_speed = self.speed * self.boost_multiplier

        if self.use_inertia:
            target_vel = steer_dir * self.max_lateral_speed * self.boost_multiplier
            self.lateral_velocity += (target_vel - self.lateral_velocity) * min(1.0, self.lateral_accel * 0.25)
            self.lateral_velocity *= self.lateral_friction
            if self.use_drift_assist and abs(self.lateral_velocity) > self.max_lateral_speed * 0.7:
                self.lateral_velocity *= 0.92
            self.rect.x += int(self.lateral_velocity)
            if self.lateral_velocity < -0.5:
                self.target_angle = 15
            elif self.lateral_velocity > 0.5:
                self.target_angle = -15
        else:
            if move_left and self.rect.x > self.road_left:
                self.rect.x -= int(effective_speed)
                self.target_angle = 15 # Tilt Left
            if move_right and self.rect.x < self.road_right - self.rect.width:
                self.rect.x += int(effective_speed)
                self.target_angle = -15 # Tilt Right

        self.rect.x = max(self.road_left, min(self.rect.x, self.road_right - self.rect.width))
        if move_up and self.rect.y > 0:
            self.rect.y -= int(self.speed)
        if move_down and self.rect.y < SCREEN_HEIGHT - self.rect.height:
            self.rect.y += int(self.speed)
        
        # Smooth Rotation
        self.angle += (self.target_angle - self.angle) * 0.2
        
        # Rotate Image
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        # Update rect to keep center
        center = self.rect.center
        self.rect = self.image.get_rect(center=center)
        # Shrink collision box slightly to be forgiving/accurate after rotation
        self.rect.inflate_ip(-10, -10)

        return self.precision_correction

    def draw(self, screen):
        screen.blit(self.image, self.rect)

class Enemy(Entity):
    def __init__(self, x, y, image, speed, road_limits=(ROAD_LEFT, ROAD_RIGHT)):
        super().__init__(x, y, 50, 100)
        self.original_image = image
        self.image = image
        self.speed = speed
        self.angle = 0
        self.target_angle = 0
        self.lateral_speed = random.uniform(1, 3)
        self.target_x = x
        self.change_dir_timer = random.randint(0, 60)
        self.road_left = road_limits[0]
        self.road_right = road_limits[1]
        # Additive behavior layer; defaults preserve existing behavior
        self.behavior = "normal"
        self.brake_timer = 0
        self.weave_direction = random.choice([-1, 1])

    def set_behavior(self, behavior_name):
        self.behavior = behavior_name or "normal"

    def update(self):
        # Y Movement
        speed_multiplier = 1.0
        lane_change_chance = 0.8

        if self.behavior == "lane_drifter":
            lane_change_chance = 0.95
            self.lateral_speed = max(self.lateral_speed, 2.6)
        elif self.behavior == "sudden_braker":
            if self.brake_timer <= 0 and random.random() < 0.01:
                self.brake_timer = random.randint(10, 24)
            if self.brake_timer > 0:
                self.brake_timer -= 1
                speed_multiplier = 0.45
        elif self.behavior == "speeder":
            speed_multiplier = 1.35
            lane_change_chance = 0.5
        elif self.behavior == "weaver":
            lane_change_chance = 1.0
            self.lateral_speed = max(self.lateral_speed, 3.3)
            if random.random() < 0.05:
                self.weave_direction *= -1
            self.target_x = self.rect.x + (self.weave_direction * random.choice([45, 70]))
            self.target_x = max(self.road_left, min(self.target_x, self.road_right - self.rect.width))
        elif self.behavior == "chaos":
            speed_multiplier = random.uniform(0.7, 1.6)
            lane_change_chance = 1.0
            self.lateral_speed = random.uniform(2.2, 4.6)

        self.rect.y += self.speed * speed_multiplier
        
        # AI Logic: Change lanes periodically
        self.change_dir_timer += 1
        if self.change_dir_timer > 30: # Check every 0.5s
            self.change_dir_timer = 0
            if random.random() < lane_change_chance: # behavior-tunable chance to try moving
                # Pick a random lane/position relative to current
                offset = random.choice([-100, -50, 50, 100])
                candidates = self.rect.x + offset
                # Clamp to road
                self.target_x = max(self.road_left, min(candidates, self.road_right - self.rect.width))
                # Randomize speed slightly for realism
                self.lateral_speed = random.uniform(2, 4)

        # Lateral Movement toward target_x
        self.target_angle = 0
        if abs(self.rect.x - self.target_x) > 4: # Tolerance
            if self.rect.x < self.target_x:
                self.rect.x += self.lateral_speed
                self.target_angle = -15 # Tilt Right
            else:
                self.rect.x -= self.lateral_speed
                self.target_angle = 15 # Tilt Left
        
        # Smooth Rotation
        self.angle += (self.target_angle - self.angle) * 0.1
        
        # Rotate Image
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        # Update rect to keep center (prevent wobbling position)
        center = self.rect.center
        self.rect = self.image.get_rect(center=center)
        # Inflate negative to keep hitbox reasonable
        self.rect.inflate_ip(-10, -10)
        
    def draw(self, screen):
        screen.blit(self.image, self.rect)

class Coin(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 40, 40)
        from main import ASSETS_DIR # Local import if needed or use global
        self.image = load_image(os.path.join(ASSETS_DIR, "Coin.png"), 40, 40)
        if self.image is None:
             self.image = pygame.Surface((40, 40))
             self.image.fill(YELLOW)

    def update(self, speed):
        self.rect.y += speed

    def draw(self, screen):
        screen.blit(self.image, self.rect)

class FuelCan(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 40, 40)
        from main import ASSETS_DIR
        self.image = load_image(os.path.join(ASSETS_DIR, "Fuel.png"), 40, 40)
        if self.image is None:
             self.image = pygame.Surface((40, 40))
             self.image.fill(CYAN)

    def update(self, speed):
        self.rect.y += speed

    def draw(self, screen):
        screen.blit(self.image, self.rect)

class NitroBottle(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 40, 40)
        from main import ASSETS_DIR
        self.image = load_image(os.path.join(ASSETS_DIR, "Nitro.png"), 40, 40)
        if self.image is None:
             self.image = pygame.Surface((40, 40))
             self.image.fill((120, 180, 255))

    def update(self, speed):
        self.rect.y += speed

    def draw(self, screen):
        screen.blit(self.image, self.rect)

class RepairKit(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 40, 40)
        from main import ASSETS_DIR
        self.image = load_image(os.path.join(ASSETS_DIR, "Repair.png"), 40, 40)
        if self.image is None:
             self.image = pygame.Surface((40, 40))
             self.image.fill(WHITE)

    def update(self, speed):
        self.rect.y += speed

    def draw(self, screen):
        screen.blit(self.image, self.rect)


class ShieldPickup(Entity):
    """Temporary invulnerability shield. Lasts a few seconds."""
    def __init__(self, x, y):
        super().__init__(x, y, 36, 36)
        self.image = pygame.Surface((36, 36), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (80, 200, 255, 200), (18, 18), 18)
        pygame.draw.circle(self.image, (255, 255, 255, 180), (18, 18), 12, 2)

    def update(self, speed):
        self.rect.y += speed

    def draw(self, screen):
        screen.blit(self.image, self.rect)


class ScoreMultPickup(Entity):
    """Temporary score multiplier boost. Adds +1x for a few seconds."""
    def __init__(self, x, y):
        super().__init__(x, y, 36, 36)
        self.image = pygame.Surface((36, 36), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (255, 215, 0, 200), (2, 2, 32, 32), border_radius=6)
        font = pygame.font.Font(None, 28)
        txt = font.render("x2", True, (60, 20, 0))
        self.image.blit(txt, (6, 8))

    def update(self, speed):
        self.rect.y += speed

    def draw(self, screen):
        screen.blit(self.image, self.rect)
