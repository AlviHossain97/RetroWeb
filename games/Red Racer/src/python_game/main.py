import pygame
import sys
import random
import os
import time
import math

from settings import *
from utils import load_image
from sprites import Player, Enemy, Coin, FuelCan, NitroBottle, Particle, RepairKit, ShieldPickup, ScoreMultPickup
from ui import Button
from systems import (
    load_game_config,
    RiskScoringSystem,
    BoostSystem,
)
from cars import CAR_ROSTER, CAR_ORDER, CAR_UNLOCK_THRESHOLDS, ARCHETYPES, build_car_effects, get_car_display_stats
from roads import ROAD_ROSTER, ROAD_ORDER, get_road_effects, get_road_traffic_weights, get_road_display
from modes import MODE_ROSTER, MODE_ORDER, next_mode as modes_next_mode, short_name as modes_short_name, get_mode_rules, deterministic_seed_for_mode
from traffic import select_behavior, select_traffic_type, TRAFFIC_TYPES, BEHAVIORS
from save_system import ProfileData, RunRecord, CAR_UNLOCK_THRESHOLDS
from achievements import check_achievements, ALL_ACHIEVEMENTS, get_achievement_categories, get_all_achievements
from missions import MissionSystem

# Initialize pygame
pygame.init()
pygame.font.init()
try:
    pygame.mixer.init()
    AUDIO_AVAILABLE = True
except pygame.error:
    AUDIO_AVAILABLE = False


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Ultimate Red Racer")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.big_font = pygame.font.Font(None, 60)
        self.dt = 1.0 / FPS

        self.config = load_game_config(os.path.join(ASSETS_DIR, "game_config.json"))
        self.features = self.config.get("features", {})
        self.compatibility = self.config.get("compatibility", {})
        self.performance_cfg = self.config.get("performance", {})
        self.nitro_cfg = self.config.get("nitro", {})

        self.available_roads = list(ROAD_CONFIGS.keys())
        self.current_road_name = "Road.png" if "Road.png" in self.available_roads else "Road.png"
        self.road_select_index = 0
        self.road_limits = ROAD_CONFIGS.get(self.current_road_name, (ROAD_LEFT, ROAD_RIGHT))
        self.load_background()

        self.road_thumbnails = []
        for road_name in self.available_roads:
            path = os.path.join(ASSETS_DIR, road_name)
            img = load_image(path, 300, 150)
            if img:
                self.road_thumbnails.append((road_name, img))
            else:
                placeholder = pygame.Surface((300, 150))
                placeholder.fill(GRAY)
                self.road_thumbnails.append((road_name, placeholder))

        self.available_cars = []
        self.scan_for_cars()
        # Car specs now come from cars.py CAR_ROSTER
        self.car_specs = {k: v.get("specs", {}) for k, v in CAR_ROSTER.items()}
        self.car_select_index = 0
        self.active_car_key = "Felucia"
        self.player_img = None
        for name, img, _ in self.available_cars:
            if "Felucia" in name:
                self.player_img = img
                break
        if self.player_img is None and self.available_cars:
            self.player_img = self.available_cars[0][1]
        if self.player_img is None:
            fallback_car = pygame.Surface((50, 100))
            fallback_car.fill(RED)
            self.player_img = fallback_car

        self.enemy_images = []
        for name in POSSIBLE_ENEMIES:
            path = os.path.join(ASSETS_DIR, name)
            img = load_image(path, 50, 100)
            if img:
                self.enemy_images.append(img)
        if not self.enemy_images:
            fallback_enemy = pygame.Surface((50, 100))
            fallback_enemy.fill(BLUE)
            self.enemy_images.append(fallback_enemy)

        self.highscore_file = os.path.join(ASSETS_DIR, "highscore.txt")
        self.profile = ProfileData(ASSETS_DIR)
        self.high_score = self.profile.high_score
        # Legacy compat: keep self.progression for systems.py ProgressionSystem if needed
        self.progression = self.profile

        self.current_mode = self.config.get("modes", {}).get("default", "CLASSIC_ENDLESS")
        self.mode_seed = None
        self.damage_taken_total = 0
        self.distance_meters = 0.0

        self.btn_start = Button(300, 170, 200, 50, "START", RED, WHITE)
        self.btn_editor = Button(300, 230, 200, 50, "GARAGE", (220, 180, 40), WHITE)
        self.btn_difficulty = Button(300, 290, 200, 50, "DIFFICULTY: NORMAL", GREEN, BLACK, 28)
        self.btn_settings = Button(300, 350, 200, 50, "SETTINGS", (90, 90, 170), WHITE, 28)
        self.btn_instr = Button(300, 410, 200, 50, "INSTRUCTIONS", BLUE, WHITE, 28)
        self.btn_mode = Button(300, 470, 200, 50, f"MODE: {modes_short_name(self.current_mode)}", CYAN, BLACK, 24)
        self.btn_quit = Button(300, 530, 200, 50, "QUIT", GRAY, WHITE)

        self.btn_select_car = Button(300, 200, 200, 50, "SELECT CAR", YELLOW, BLACK, 30)
        self.btn_select_road = Button(300, 270, 200, 50, "SELECT ROAD", CYAN, BLACK, 30)
        self.btn_records = Button(300, 340, 200, 50, "RECORDS", (80, 180, 120), WHITE, 30)
        self.btn_achievements = Button(300, 410, 200, 50, "ACHIEVEMENTS", (200, 140, 60), WHITE, 28)
        self.btn_back = Button(300, 550, 200, 50, "BACK", RED, WHITE)

        # Road effects now come from roads.py — no more inline dicts

        self.fuel_decrease_rate = 0.1
        self.spawn_threshold_mult = 1.0
        self.risk_point_mult = 1.0
        self.reward_mult = 1.0
        self.boost_gain_mult = 1.0
        self.enemy_speed_cap = 15.0
        self.car_top_speed_mph = 210
        self.display_speed_mph = 0.0

        self.difficulty = self.profile.settings.get("difficulty", "NORMAL")
        # AI driver fully removed from production flow

        self.risk_system = RiskScoringSystem(self.config.get("risk", {}))
        self.boost_system = BoostSystem(self.config.get("boost", {}))
        self.show_debug_overlay = bool(self.features.get("debug_overlay", False))
        self.show_near_miss_hitboxes = False
        self.combo_flash = 0.0
        self.screen_shake_timer = 0.0
        self.screen_shake_offset_x = 0
        self.screen_shake_offset_y = 0
        self.slowmo_timer = 0.0
        self.precision_flag = False

        # New systems
        self.mission_system = None
        self.shield_timer = 0.0
        self.score_mult_timer = 0.0
        self.shields = []
        self.score_mults = []
        self.coins_collected = 0
        self.fuel_collected = 0
        self.enemies_passed = 0
        self.boost_active_seconds = 0.0
        self.no_hit_flag = True
        self.mission_flash_timer = 0.0
        self.mission_flash_text = ""
        self.achievement_flash_timer = 0.0
        self.achievement_flash_text = ""
        self.speed_lines = []  # Speed line visual effect
        self.records_scroll = 0
        self.achievements_scroll = 0

        self.run_stats = {
            "near_misses": 0,
            "max_combo": 0,
            "max_speed": 0,
            "risk_score": 0,
            "base_score": 0,
        }
        self.mode_time_limit = 90.0
        self.settings_toggle_rects = []
        self.mode_elapsed = 0.0
        self.daily_profile = "normal"
        self.zen_focus = 100.0
        self.rev_level = 0.0
        self.throttle_axis = 0.0
        self.display_speed_mph = 0.0

        # Restore settings from profile
        saved_diff = self.profile.settings.get("difficulty", "NORMAL")
        if saved_diff in ("NORMAL", "HARD", "EASY"):
            self.difficulty = saved_diff
        saved_mode = self.profile.settings.get("game_mode", "CLASSIC_ENDLESS")
        if saved_mode in MODE_ORDER:
            self.current_mode = saved_mode
        self.btn_mode.text = f"MODE: {modes_short_name(self.current_mode)}"
        self._sync_difficulty_button()

        self.reset_game()
        self.state = "MENU"
        self.current_music = None
        self.play_music("MENU")

    def load_background(self):
        path = os.path.join(ASSETS_DIR, self.current_road_name)
        self.background = load_image(path, SCREEN_WIDTH, SCREEN_HEIGHT)
        if self.background is None:
             self.background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
             self.background.fill(GRAY)

    def play_music(self, bg_type):
        if not AUDIO_AVAILABLE:
            return

        if self.current_music == bg_type:
            return
        
        self.current_music = bg_type
        pygame.mixer.music.stop()
        
        try:
            if bg_type == "MENU":
                if os.path.exists(MENU_MUSIC_PATH):
                    pygame.mixer.music.load(MENU_MUSIC_PATH)
                    pygame.mixer.music.play(-1) # Loop
            elif bg_type == "GAME":
                if os.path.exists(GAME_SOUND_PATH):
                    pygame.mixer.music.load(GAME_SOUND_PATH)
                    pygame.mixer.music.play(-1) # Loop
        except pygame.error as e:
            print(f"Error loading music: {e}")

    def scan_for_cars(self):
        # Scan current dir for pngs, excluding background/roads
        if not os.path.exists(ASSETS_DIR):
            return

        files = [f for f in os.listdir(ASSETS_DIR) if f.endswith('.png')]
        for f in files:
            base = f.split('.')[0]
            if base not in CAR_ROSTER:
                continue
            path = os.path.join(ASSETS_DIR, f)
            img = load_image(path, 50, 100)
            if img:
                self.available_cars.append((f, img, path))

    def load_highscore(self):
        try:
            if os.path.exists(self.highscore_file):
                with open(self.highscore_file, "r") as f:
                    return int(f.read())
            return 0
        except:
            return 0

    def save_highscore(self):
        with open(self.highscore_file, "w") as f:
            f.write(str(self.high_score))

    def reset_game(self):
        self.player = Player(SCREEN_WIDTH // 2 - 25, SCREEN_HEIGHT - 120, self.player_img, self.road_limits)
        self.player.configure_handling(
            use_inertia=bool(self.features.get("advanced_handling", False)) and not bool(self.compatibility.get("legacy_handling_default", True)),
            use_drift_assist=bool(self.features.get("drift_assist", False)),
        )
        self.enemies = []
        self.coins = []
        self.fuels = []
        self.nitros = []
        self.repair_kits = []
        self.shields = []
        self.score_mults = []
        # Keep legacy/base score as a separate layer for full compatibility.
        self.base_score = 0
        self.score = 0
        self.fuel = FUEL_MAX
        self.health = PLAYER_MAX_HEALTH
        self.enemy_speed = ENEMY_SPEED_INITIAL
        if self.difficulty == "HARD":
            self.enemy_speed *= 1.2

        self.apply_car_and_road_effects()

        self.mode_seed = deterministic_seed_for_mode(self.current_mode, self.config)
        if self.mode_seed is not None:
            random.seed(self.mode_seed)

        self.spawn_timer = 0
        self.bg_y = 0
        self.particles = []
        self.risk_system.reset()
        self.boost_system.reset()
        self.combo_flash = 0.0
        self.screen_shake_timer = 0.0
        self.screen_shake_offset_x = 0
        self.screen_shake_offset_y = 0
        self.slowmo_timer = 0.0
        self.precision_flag = False
        self.run_stats = {
            "near_misses": 0,
            "max_combo": 0,
            "max_speed": 0,
            "risk_score": 0,
            "base_score": 0,
        }
        self.mode_elapsed = 0.0
        self.zen_focus = 100.0
        self.rev_level = 0.0
        self.throttle_axis = 0.0

        # New system resets
        self.shield_timer = 0.0
        self.score_mult_timer = 0.0
        self.coins_collected = 0
        self.fuel_collected = 0
        self.enemies_passed = 0
        self.boost_active_seconds = 0.0
        self.no_hit_flag = True
        self.mission_flash_timer = 0.0
        self.mission_flash_text = ""
        self.achievement_flash_timer = 0.0
        self.achievement_flash_text = ""
        self.speed_lines = []
        self.damage_taken_total = 0
        self.distance_meters = 0.0

        # Initialize mission system using mode rules
        mode_rules = get_mode_rules(self.current_mode)
        mission_count = mode_rules.get("mission_count", 2)
        self.mission_system = MissionSystem(mission_count, self.difficulty, self.current_mode)

        if self.current_mode == "DAILY_RUN" and self.mode_seed is not None:
            profiles = ["normal", "lane_drifter", "sudden_braker", "speeder", "weaver"]
            self.daily_profile = profiles[self.mode_seed % len(profiles)]
        else:
            self.daily_profile = "normal"

    def _clamp(self, value, lo, hi):
        return max(lo, min(hi, value))

    def draw_wrapped_text(self, surface, text, font, color, x, y, max_width, line_gap=2, max_lines=None):
        words = text.split()
        if not words:
            return y

        lines = []
        current = words[0]
        for w in words[1:]:
            test = current + " " + w
            if font.size(test)[0] <= max_width:
                current = test
            else:
                lines.append(current)
                current = w
        lines.append(current)

        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
            # soft ellipsis on final line if truncated
            if not lines[-1].endswith("..."):
                while lines[-1] and font.size(lines[-1] + "...")[0] > max_width:
                    lines[-1] = lines[-1][:-1]
                lines[-1] = lines[-1].rstrip() + "..."

        for line in lines:
            surface.blit(font.render(line, True, color), (x, y))
            y += font.get_height() + line_gap
        return y

    def draw_fit_text(self, surface, text, color, x, y, max_width, start_size=24, min_size=14):
        size = start_size
        font = pygame.font.Font(None, size)
        while size > min_size and font.size(text)[0] > max_width:
            size -= 1
            font = pygame.font.Font(None, size)
        surface.blit(font.render(text, True, color), (x, y))
        return font.get_height()

    def _sync_difficulty_button(self):
        if self.difficulty == "HARD":
            self.btn_difficulty.color = RED
        elif self.difficulty == "EASY":
            self.btn_difficulty.color = GREEN
        else:
            self.btn_difficulty.color = YELLOW
        self.btn_difficulty.text = f"DIFFICULTY: {self.difficulty}"

    def _persist_settings(self):
        """Save current settings to profile."""
        self.profile.settings["difficulty"] = self.difficulty
        self.profile.settings["game_mode"] = self.current_mode
        car_key = self.get_selected_car_key()
        self.profile.settings["selected_car"] = car_key
        self.profile.settings["selected_road"] = self.current_road_name
        self.profile.save()

    def _update_speed_lines(self):
        """Generate and update speed line visual effects."""
        speed_ratio = self.display_speed_mph / max(1, self.car_top_speed_mph)
        if speed_ratio > 0.6 and not self.features.get("reduced_motion", False):
            if random.random() < (speed_ratio - 0.5) * 2.0:
                side = random.choice(["left", "right"])
                if side == "left":
                    x = random.randint(self.road_limits[0] - 30, self.road_limits[0] + 20)
                else:
                    x = random.randint(self.road_limits[1] - 20, self.road_limits[1] + 30)
                y = random.randint(-20, 0)
                length = random.randint(20, 60)
                speed = 8 + speed_ratio * 12
                self.speed_lines.append({"x": x, "y": y, "length": length,
                                         "speed": speed, "alpha": 180})

        for sl in self.speed_lines[:]:
            sl["y"] += sl["speed"]
            sl["alpha"] -= 6
            if sl["y"] > SCREEN_HEIGHT or sl["alpha"] <= 0:
                self.speed_lines.remove(sl)

    def _draw_speed_lines(self):
        for sl in self.speed_lines:
            if sl["alpha"] > 0:
                surf = pygame.Surface((2, sl["length"]), pygame.SRCALPHA)
                surf.fill((255, 255, 255, max(0, int(sl["alpha"]))))
                self.screen.blit(surf, (sl["x"], sl["y"]))

    def _update_screen_shake(self):
        """Compute actual screen shake offset."""
        if self.screen_shake_timer > 0 and not self.features.get("reduced_motion", False):
            intensity = min(1.0, self.screen_shake_timer / 0.1)
            self.screen_shake_offset_x = int(random.uniform(-3, 3) * intensity)
            self.screen_shake_offset_y = int(random.uniform(-3, 3) * intensity)
        else:
            self.screen_shake_offset_x = 0
            self.screen_shake_offset_y = 0

    def _build_run_state(self):
        """Build run state dict for mission system."""
        return {
            "near_misses": self.risk_system.near_miss_count,
            "duration_seconds": self.mode_elapsed,
            "score": self.score,
            "multiplier": self.risk_system.multiplier(),
            "coins_collected": self.coins_collected,
            "fuel_collected": self.fuel_collected,
            "enemies_passed": self.enemies_passed,
            "max_speed": int(self.display_speed_mph),
            "boost_seconds": self.boost_active_seconds,
        }

    def _build_run_record(self):
        """Build a RunRecord from current run state."""
        return RunRecord(
            score=self.score,
            risk_score=self.risk_system.risk_score,
            base_score=self.base_score,
            car_key=self.active_car_key,
            road_key=self.current_road_name,
            game_mode=self.current_mode,
            difficulty=self.difficulty,
            duration_seconds=self.mode_elapsed,
            near_misses=self.risk_system.near_miss_count,
            max_combo=int(self.risk_system.max_combo),
            max_speed=int(self.display_speed_mph),
            coins_collected=self.coins_collected,
            fuel_collected=self.fuel_collected,
            boost_used_seconds=self.boost_active_seconds,
            enemies_passed=self.enemies_passed,
            top_multiplier=self.risk_system.multiplier(),
            no_hit=self.no_hit_flag,
            fuel_at_end=self.fuel,
            damage_taken=self.damage_taken_total,
            distance_meters=self.distance_meters,
        )

    def toggle_runtime_setting(self, key):
        """Toggle a runtime feature setting."""
        if key == "debug_overlay":
            self.show_debug_overlay = not self.show_debug_overlay
            self.features["debug_overlay"] = self.show_debug_overlay
        elif key == "boost_system":
            self.features["boost_system"] = not self.features.get("boost_system", True)
            if not self.features.get("boost_system", True):
                self.boost_system.deactivate()
        elif key == "near_miss_hitboxes":
            self.show_near_miss_hitboxes = not self.show_near_miss_hitboxes
        elif key == "reduced_motion":
            self.features["reduced_motion"] = not self.features.get("reduced_motion", False)
        elif key == "colorblind_hud":
            self.features["colorblind_hud"] = not self.features.get("colorblind_hud", False)

    def setting_enabled(self, key):
        if key == "debug_overlay":
            return self.show_debug_overlay
        if key == "near_miss_hitboxes":
            return self.show_near_miss_hitboxes
        if key == "boost_system":
            return bool(self.features.get("boost_system", True))
        return bool(self.features.get(key, False))

    def get_selected_car_key(self):
        for name, img, _ in self.available_cars:
            if img == self.player_img:
                return name.split('.')[0]
        return self.available_cars[0][0].split('.')[0] if self.available_cars else "Felucia"

    def apply_car_and_road_effects(self):
        car_key = self.get_selected_car_key()
        self.active_car_key = car_key
        car_fx = build_car_effects(car_key)
        road_fx = get_road_effects(self.current_road_name)

        combined_grip = car_fx["handling_mult"] * road_fx["grip_mult"]
        self.player.speed = max(4.5, PLAYER_SPEED * car_fx["speed_mult"] * road_fx["grip_mult"])
        self.player.max_lateral_speed = max(3.8, PLAYER_SPEED * combined_grip)
        self.player.lateral_accel = self._clamp(1.0 * combined_grip, 0.85, 1.28)
        self.player.lateral_friction = self._clamp(0.78 * road_fx["grip_mult"], 0.70, 0.90)

        self.enemy_speed *= road_fx["enemy_speed_mult"]
        self.enemy_speed_cap = min(20.0, 12.5 + ((car_fx["top_speed"] - 170.0) / 18.0) + road_fx.get("cap_bonus", 0.0))
        self.car_top_speed_mph = int(car_fx["top_speed"])

        self.fuel_decrease_rate = 0.1 * road_fx["fuel_drain_mult"] / max(0.75, car_fx["fuel_eff"])
        self.spawn_threshold_mult = road_fx["spawn_threshold_mult"]
        self.risk_point_mult = road_fx["risk_mult"]
        self.reward_mult = road_fx["reward_mult"]
        self.boost_gain_mult = car_fx["boost_gain_mult"]

        # Apply mode-specific overrides
        mode_rules = get_mode_rules(self.current_mode)
        self.fuel_decrease_rate *= mode_rules.get("fuel_drain_mult", 1.0)
        self.spawn_threshold_mult *= mode_rules.get("spawn_rate_mult", 1.0)
        self.boost_gain_mult *= mode_rules.get("boost_gain_global", 1.0)

    def _spawn_enemy_with_behavior(self):
        if len(self.enemies) >= int(self.performance_cfg.get("max_enemies", 14)):
            return

        x = random.randint(self.road_limits[0], self.road_limits[1] - 50)
        for e in self.enemies:
            if abs(e.rect.x - x) < 48 and e.rect.y < 120:
                return

        img = random.choice(self.enemy_images)
        enemy_real_speed = random.uniform(self.enemy_speed * 0.3, self.enemy_speed * 0.8)
        screen_speed = max(2, self.enemy_speed - enemy_real_speed)
        enemy = Enemy(x, -100, img, screen_speed, self.road_limits)

        if self.features.get("traffic_behaviors", True):
            performance = (self.score + self.risk_system.risk_score) / 2000.0
            road_weights = get_road_traffic_weights(self.current_road_name)
            behavior = select_behavior(
                road_weights, performance, self.current_mode,
                daily_profile=self.daily_profile if self.current_mode == "DAILY_RUN" else None
            )
            enemy.set_behavior(behavior)

        self.enemies.append(enemy)

    def handle_input(self):
        pos = pygame.mouse.get_pos()
        
        if self.state == "MENU":
            self.btn_start.check_hover(pos)
            self.btn_editor.check_hover(pos)
            self.btn_difficulty.check_hover(pos)
            self.btn_settings.check_hover(pos)
            self.btn_instr.check_hover(pos)
            self.btn_mode.check_hover(pos)
            self.btn_quit.check_hover(pos)
        elif self.state == "EDITOR":
             self.btn_select_car.check_hover(pos)
             self.btn_select_road.check_hover(pos)
             self.btn_records.check_hover(pos)
             self.btn_achievements.check_hover(pos)
             self.btn_back.check_hover(pos)
        elif self.state in ("INSTRUCTIONS", "SETTINGS", "CAR_SELECT", "ROAD_SELECT",
                            "RECORDS", "ACHIEVEMENTS", "RUN_SUMMARY"):
            self.btn_back.check_hover(pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if self.state == "MENU":
                if self.btn_start.is_clicked(event):
                    self.state = "PLAYING"
                    self.play_music("GAME")
                    self.reset_game()
                elif self.btn_editor.is_clicked(event):
                    self.state = "EDITOR"
                elif self.btn_difficulty.is_clicked(event):
                    # Toggle difficulty
                    if self.difficulty == "NORMAL":
                         self.difficulty = "HARD"
                         self.btn_difficulty.color = RED
                    elif self.difficulty == "HARD":
                         self.difficulty = "EASY"
                         self.btn_difficulty.color = GREEN
                    else:
                         self.difficulty = "NORMAL"
                         self.btn_difficulty.color = YELLOW
                    self.btn_difficulty.text = f"DIFFICULTY: {self.difficulty}"
                    self._persist_settings()
                elif self.btn_settings.is_clicked(event):
                    self.state = "SETTINGS"
                elif self.btn_instr.is_clicked(event):
                    self.state = "INSTRUCTIONS"
                elif self.btn_mode.is_clicked(event):
                    self.current_mode = modes_next_mode(self.current_mode)
                    self.btn_mode.text = f"MODE: {modes_short_name(self.current_mode)}"
                    self._persist_settings()
                elif self.btn_quit.is_clicked(event):
                    pygame.quit()
                    sys.exit()
            
            elif self.state == "EDITOR":
                if self.btn_select_car.is_clicked(event):
                    # Open carousel on currently selected car
                    if self.available_cars:
                        for idx, (_, img, _) in enumerate(self.available_cars):
                            if img == self.player_img:
                                self.car_select_index = idx
                                break
                    self.state = "CAR_SELECT"
                elif self.btn_select_road.is_clicked(event):
                    if self.available_roads:
                        self.road_select_index = self.available_roads.index(self.current_road_name) if self.current_road_name in self.available_roads else 0
                    self.state = "ROAD_SELECT"
                elif self.btn_records.is_clicked(event):
                    self.records_scroll = 0
                    self.state = "RECORDS"
                elif self.btn_achievements.is_clicked(event):
                    self.achievements_scroll = 0
                    self.state = "ACHIEVEMENTS"
                elif self.btn_back.is_clicked(event):
                     self.state = "MENU"

            elif self.state == "INSTRUCTIONS":
                if self.btn_back.is_clicked(event):
                    self.state = "MENU"

            elif self.state == "SETTINGS":
                if self.btn_back.is_clicked(event):
                    self.state = "MENU"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, setting_key in self.settings_toggle_rects:
                        if rect.collidepoint(pos):
                            self.toggle_runtime_setting(setting_key)
                            break
            
            elif self.state == "CAR_SELECT":
                if self.btn_back.is_clicked(event):
                    self.state = "EDITOR"

                if self.available_cars and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    left_btn = pygame.Rect(140, 430, 70, 50)
                    right_btn = pygame.Rect(280, 430, 70, 50)
                    pick_btn = pygame.Rect(305, 500, 190, 42)

                    if left_btn.collidepoint(pos):
                        self.car_select_index = (self.car_select_index - 1) % len(self.available_cars)
                    elif right_btn.collidepoint(pos):
                        self.car_select_index = (self.car_select_index + 1) % len(self.available_cars)
                    elif pick_btn.collidepoint(pos):
                        self.player_img = self.available_cars[self.car_select_index][1]
                        self.state = "EDITOR"
            
            elif self.state == "ROAD_SELECT":
                if self.btn_back.is_clicked(event):
                    self.state = "EDITOR"

                if self.available_roads and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    left_btn = pygame.Rect(140, 430, 70, 50)
                    right_btn = pygame.Rect(280, 430, 70, 50)
                    pick_btn = pygame.Rect(305, 500, 190, 42)

                    if left_btn.collidepoint(pos):
                        self.road_select_index = (self.road_select_index - 1) % len(self.available_roads)
                    elif right_btn.collidepoint(pos):
                        self.road_select_index = (self.road_select_index + 1) % len(self.available_roads)
                    elif pick_btn.collidepoint(pos):
                        road_name = self.available_roads[self.road_select_index]
                        self.current_road_name = road_name
                        self.road_limits = ROAD_CONFIGS.get(road_name, (ROAD_LEFT, ROAD_RIGHT))
                        self.load_background()
                        self.state = "EDITOR"

            elif self.state == "RECORDS":
                if self.btn_back.is_clicked(event):
                    self.state = "EDITOR"
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 4:
                        self.records_scroll = max(0, self.records_scroll - 30)
                    elif event.button == 5:
                        self.records_scroll += 30

            elif self.state == "ACHIEVEMENTS":
                if self.btn_back.is_clicked(event):
                    self.state = "EDITOR"
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 4:
                        self.achievements_scroll = max(0, self.achievements_scroll - 30)
                    elif event.button == 5:
                        self.achievements_scroll += 30

            elif self.state == "RUN_SUMMARY":
                if self.btn_back.is_clicked(event):
                    self.state = "MENU"
                    self.play_music("MENU")
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 4:
                        self.summary_scroll = max(0, self.summary_scroll - 30)
                    elif event.button == 5:
                        self.summary_scroll += 30

            if event.type == pygame.KEYDOWN:
                if self.state in ("GAME_OVER", "RUN_SUMMARY"):
                    if event.key == pygame.K_r and self.current_mode != "ONE_LIFE_HARDCORE":
                        self.state = "PLAYING"
                        self.play_music("GAME")
                        self.reset_game()
                    elif event.key == pygame.K_q:
                        self.state = "MENU"
                        self.play_music("MENU")
                elif self.state == "RECORDS":
                    if event.key == pygame.K_ESCAPE:
                        self.state = "EDITOR"
                    elif event.key == pygame.K_UP:
                        self.records_scroll = max(0, self.records_scroll - 30)
                    elif event.key == pygame.K_DOWN:
                        self.records_scroll += 30
                elif self.state == "ACHIEVEMENTS":
                    if event.key == pygame.K_ESCAPE:
                        self.state = "EDITOR"
                    elif event.key == pygame.K_UP:
                        self.achievements_scroll = max(0, self.achievements_scroll - 30)
                    elif event.key == pygame.K_DOWN:
                        self.achievements_scroll += 30
                elif self.state == "PLAYING":
                    if event.key == pygame.K_p:
                        self.state = "PAUSED"
                    elif event.key == pygame.K_LSHIFT:
                        if self.features.get("boost_system", True):
                            self.boost_system.activate("burst")
                    elif event.key == pygame.K_LCTRL:
                        if self.features.get("boost_system", True):
                            self.boost_system.activate("sustain")
                    elif event.key == pygame.K_F3:
                        self.toggle_runtime_setting("debug_overlay")
                    elif event.key == pygame.K_F4:
                        self.toggle_runtime_setting("near_miss_hitboxes")
                    elif event.key == pygame.K_F6:
                        self.toggle_runtime_setting("reduced_motion")
                    elif event.key == pygame.K_F7:
                        self.toggle_runtime_setting("colorblind_hud")
                elif self.state == "PAUSED":
                    if event.key == pygame.K_p:
                        self.state = "PLAYING"
                elif self.state == "MENU":
                    if event.key == pygame.K_SPACE:
                        self.state = "PLAYING"
                        self.play_music("GAME")
                        self.reset_game()
                elif self.state == "CAR_SELECT" and self.available_cars:
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        self.car_select_index = (self.car_select_index - 1) % len(self.available_cars)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.car_select_index = (self.car_select_index + 1) % len(self.available_cars)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.player_img = self.available_cars[self.car_select_index][1]
                        self.state = "EDITOR"
                elif self.state == "ROAD_SELECT" and self.available_roads:
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        self.road_select_index = (self.road_select_index - 1) % len(self.available_roads)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.road_select_index = (self.road_select_index + 1) % len(self.available_roads)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        road_name = self.available_roads[self.road_select_index]
                        self.current_road_name = road_name
                        self.road_limits = ROAD_CONFIGS.get(road_name, (ROAD_LEFT, ROAD_RIGHT))
                        self.load_background()
                        self.state = "EDITOR"
                if event.key in (pygame.K_LSHIFT, pygame.K_LCTRL) and self.state != "PLAYING":
                    self.boost_system.deactivate()

            if event.type == pygame.KEYUP and self.state == "PLAYING":
                if event.key in (pygame.K_LSHIFT, pygame.K_LCTRL):
                    self.boost_system.deactivate()

        if self.state == "PLAYING":
            keys = pygame.key.get_pressed()
            self.throttle_axis = 0.0
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.throttle_axis += 1.0
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.throttle_axis -= 1.0
            self.precision_flag = bool(self.player.move(keys))
        else:
            self.throttle_axis = 0.0

    def update(self):
        if self.state == "PLAYING":
            self.mode_elapsed += self.dt
            if self.features.get("boost_system", True):
                self.boost_system.update(self.dt)
                self.player.set_boost_multiplier(self.boost_system.speed_multiplier())
            else:
                self.boost_system.deactivate()
                self.player.set_boost_multiplier(1.0)

            # Rev level responds to throttle up/down input and can reach redline.
            speed_component = min(1.0, self.enemy_speed / 15.0)
            if self.throttle_axis > 0:
                # Stronger rise under throttle so full bar is attainable.
                self.rev_level += self.dt * (0.95 + 0.75 * speed_component)
            elif self.throttle_axis < 0:
                # Braking/down input drops rev faster.
                self.rev_level -= self.dt * 1.35
            else:
                # Idle/cruise settles to a moderate band.
                cruise_target = 0.30 + 0.45 * speed_component
                self.rev_level += (cruise_target - self.rev_level) * min(1.0, self.dt * 4.0)

            self.rev_level = max(0.0, min(1.0, self.rev_level))

            self.bg_y += self.enemy_speed
            if self.bg_y >= SCREEN_HEIGHT:
                self.bg_y = 0
            
            # Track distance traveled (approximation from scroll speed)
            self.distance_meters += self.enemy_speed * self.dt * 10.0

            # Mode-specific resource pressure
            if self.current_mode != "ZEN":
                self.fuel -= self.fuel_decrease_rate
                if self.fuel <= 0:
                    self.game_over()
            else:
                self.fuel = max(30, self.fuel)

            self.spawn_timer += 1
            threshold = 60
            if self.difficulty == "HARD":
                threshold = 48
            if self.current_mode in ("HIGH_RISK", "ONE_LIFE_HARDCORE"):
                threshold = int(threshold * 0.85)
            elif self.current_mode == "TIME_ATTACK":
                threshold = int(threshold * 0.78)
            elif self.current_mode == "ZEN":
                threshold = int(threshold * 1.25)
            threshold = int(threshold * self.spawn_threshold_mult)
            
            if self.spawn_timer > threshold:
                self.spawn_timer = 0
                if random.random() < 0.7:
                    self._spawn_enemy_with_behavior()
                
                if random.random() < 0.3 and self.current_mode not in ("ZEN", "ONE_LIFE_HARDCORE"):
                    x = random.randint(self.road_limits[0], self.road_limits[1] - 30)
                    self.coins.append(Coin(x, -50))
                
                if random.random() < 0.1 and self.current_mode != "ONE_LIFE_HARDCORE":
                    x = random.randint(self.road_limits[0], self.road_limits[1] - 30)
                    self.fuels.append(FuelCan(x, -50))

                base_nitro_spawn = float(self.nitro_cfg.get("spawn_chance_base", 0.08))
                spawn_mode_mults = self.nitro_cfg.get("mode_spawn_multipliers", {})
                nitro_spawn_chance = base_nitro_spawn * float(spawn_mode_mults.get(self.current_mode, 1.0))
                if random.random() < nitro_spawn_chance and self.current_mode not in ("ZEN", "ONE_LIFE_HARDCORE"):
                    x = random.randint(self.road_limits[0], self.road_limits[1] - 30)
                    self.nitros.append(NitroBottle(x, -50))
                
                if self.difficulty == "EASY" and random.random() < 0.1 and self.current_mode not in ("ONE_LIFE_HARDCORE", "TIME_ATTACK"):
                     x = random.randint(self.road_limits[0], self.road_limits[1] - 40)
                     self.repair_kits.append(RepairKit(x, -50))

                # Shield pickup — rare
                if random.random() < 0.04 and self.current_mode not in ("ONE_LIFE_HARDCORE",):
                    x = random.randint(self.road_limits[0], self.road_limits[1] - 30)
                    self.shields.append(ShieldPickup(x, -50))

                # Score multiplier pickup — rare
                if random.random() < 0.05 and self.current_mode not in ("ZEN",):
                    x = random.randint(self.road_limits[0], self.road_limits[1] - 30)
                    self.score_mults.append(ScoreMultPickup(x, -50))

            for e in self.enemies[:]:
                e.update()
                if e.rect.colliderect(self.player.rect):
                    # Shield absorbs one hit
                    if self.shield_timer > 0:
                        self.shield_timer = 0
                        self.enemies.remove(e)
                        self.screen_shake_timer = 0.1
                        continue

                    self.no_hit_flag = False
                    self.risk_system.hard_reset()
                    self.screen_shake_timer = 0.2
                    self.damage_taken_total += 1

                    # Mode-specific collision handling for true uniqueness.
                    if self.current_mode == "ZEN":
                        self.enemies.remove(e)
                        self.base_score = max(0, self.base_score - 5)
                        self.zen_focus = max(0.0, self.zen_focus - 25.0)
                        continue

                    if self.current_mode == "ONE_LIFE_HARDCORE":
                        self.game_over()
                        break

                    if self.difficulty == "EASY":
                        self.health -= COLLISION_DAMAGE
                        self.enemies.remove(e)
                        if self.health <= 0:
                            self.game_over()
                    else:
                        self.game_over()

                if e.rect.y > SCREEN_HEIGHT:
                    self.enemies.remove(e)
                    self.enemies_passed += 1
                    self.base_score += int(10 * self.reward_mult)
            
            for c in self.coins[:]:
                c.update(self.enemy_speed)
                if c.rect.colliderect(self.player.rect):
                    self.base_score += int(50 * self.reward_mult)
                    self.coins_collected += 1
                    self.coins.remove(c)
                elif c.rect.y > SCREEN_HEIGHT:
                    self.coins.remove(c)

            for f in self.fuels[:]:
                f.update(self.enemy_speed)
                if f.rect.colliderect(self.player.rect):
                    self.fuel = min(FUEL_MAX, self.fuel + 20)
                    self.fuel_collected += 1
                    self.fuels.remove(f)
                elif f.rect.y > SCREEN_HEIGHT:
                    self.fuels.remove(f)

            for n in self.nitros[:]:
                n.update(self.enemy_speed)
                if n.rect.colliderect(self.player.rect):
                    # Nitro bottle gives a configurable, mode-tuned boost refill chunk.
                    base_refill = float(self.nitro_cfg.get("refill_amount", 45.0))
                    refill_mode_mults = self.nitro_cfg.get("mode_refill_multipliers", {})
                    refill = base_refill * float(refill_mode_mults.get(self.current_mode, 1.0))
                    self.boost_system.meter = min(self.boost_system.max_meter, self.boost_system.meter + refill)
                    self.nitros.remove(n)
                elif n.rect.y > SCREEN_HEIGHT:
                    self.nitros.remove(n)
            
            for r in self.repair_kits[:]:
                r.update(self.enemy_speed)
                if r.rect.colliderect(self.player.rect):
                    self.health = min(PLAYER_MAX_HEALTH, self.health + REPAIR_HEAL_AMOUNT)
                    self.repair_kits.remove(r)
                elif r.rect.y > SCREEN_HEIGHT:
                    self.repair_kits.remove(r)

            for s in self.shields[:]:
                s.update(self.enemy_speed)
                if s.rect.colliderect(self.player.rect):
                    self.shield_timer = SHIELD_DURATION
                    self.shields.remove(s)
                elif s.rect.y > SCREEN_HEIGHT:
                    self.shields.remove(s)

            for sm in self.score_mults[:]:
                sm.update(self.enemy_speed)
                if sm.rect.colliderect(self.player.rect):
                    self.score_mult_timer = SCORE_MULT_PICKUP_DURATION
                    self.score_mults.remove(sm)
                elif sm.rect.y > SCREEN_HEIGHT:
                    self.score_mults.remove(sm)

            # Timer countdowns
            if self.shield_timer > 0:
                self.shield_timer -= self.dt
            if self.score_mult_timer > 0:
                self.score_mult_timer -= self.dt

            # Track boost active time
            if self.boost_system.active_type is not None:
                self.boost_active_seconds += self.dt

            # Track enemies passed
            for e in self.enemies[:]:
                if e.rect.y > SCREEN_HEIGHT:
                    pass  # already counted above

            # Update missions
            run_state = self._build_run_state()
            completed_missions = self.mission_system.update(run_state)
            for m in completed_missions:
                reward = getattr(m, 'reward_amount', 0)
                self.score += reward
                self.mission_flash_text = f"MISSION COMPLETE: {m.name}! +{reward}"
                self.mission_flash_timer = 2.5

            # Speed lines
            self._update_speed_lines()

            # Screen shake offset
            self._update_screen_shake()

            if self.base_score > 0 and self.base_score % 500 == 0:
                 self.enemy_speed = min(self.enemy_speed_cap, self.enemy_speed + 0.1)

            # HUD speed model: true per-car top speed behavior.
            # Holding throttle can reach the selected car's top-speed stat.
            axis = max(-1.0, min(1.0, self.throttle_axis))
            top_speed = max(1.0, float(self.car_top_speed_mph))
            boost_active = self.features.get("boost_system", True) and self.boost_system.active_type is not None
            effective_top = top_speed + (10.0 if boost_active else 0.0)
            speed_ratio = self.display_speed_mph / max(1.0, effective_top)

            if axis > 0:
                # Taper acceleration near top speed so it approaches naturally.
                accel = (58.0 + 36.0 * axis) * max(0.10, 1.0 - (speed_ratio * 0.92))
                self.display_speed_mph += accel * self.dt
            elif axis < 0:
                brake = 95.0 * abs(axis) + 30.0
                self.display_speed_mph -= brake * self.dt
            else:
                coast_drag = 13.0 + (self.display_speed_mph * 0.020)
                self.display_speed_mph -= coast_drag * self.dt

            if boost_active:
                self.display_speed_mph += 22.0 * (1.0 - min(1.0, speed_ratio)) * self.dt

            self.display_speed_mph = max(0.0, min(effective_top, self.display_speed_mph))

            risk_points = 0
            if self.features.get("risk_scoring", True):
                risk_points = self.risk_system.update(
                    self.dt,
                    self.player.rect,
                    self.enemy_speed,
                    self.enemies,
                    (self.road_limits[0] + self.road_limits[1]) / 2,
                    boost_active=self.boost_system.active_type is not None,
                    precision=self.precision_flag and self.features.get("precision_reward", True),
                )
                if risk_points > 0:
                    risk_points = int(risk_points * self.risk_point_mult)
                    # High-Risk mode heavily amplifies risk-to-boost loop.
                    if self.current_mode == "HIGH_RISK":
                        risk_points = int(risk_points * 1.35)
                    if self.features.get("boost_system", True):
                        self.boost_system.gain_from_risk(int(risk_points * self.boost_gain_mult))
                    self.combo_flash = 1.0

            # Score multiplier pickup bonus
            score_mult_bonus = SCORE_MULT_PICKUP_BONUS if self.score_mult_timer > 0 else 1.0

            # Final displayed score is mode-based, but legacy/base scoring always runs.
            if self.current_mode == "HIGH_RISK":
                self.score = int(self.risk_system.risk_score * score_mult_bonus)
            elif self.current_mode == "ZEN":
                self.score = int(self.base_score * score_mult_bonus)
            else:
                self.score = int((self.base_score + self.risk_system.risk_score) * score_mult_bonus)

            if self.current_mode == "TIME_ATTACK" and self.mode_elapsed >= self.mode_time_limit:
                self.game_over()

            # Zen still needs a fail state: repeated poor control drains focus.
            if self.current_mode == "ZEN":
                self.zen_focus = min(100.0, self.zen_focus + (self.dt * 3.2))
                if self.zen_focus <= 0.0:
                    self.game_over()

            self.run_stats["near_misses"] = self.risk_system.near_miss_count
            self.run_stats["max_combo"] = int(max(self.run_stats["max_combo"], self.risk_system.max_combo))
            self.run_stats["max_speed"] = max(self.run_stats["max_speed"], int(self.enemy_speed * 20))
            self.run_stats["risk_score"] = self.risk_system.risk_score
            self.run_stats["base_score"] = self.base_score

            if self.risk_system.extreme_near_miss_timer > 0 and self.features.get("crash_slowmo", True):
                self.slowmo_timer = max(self.slowmo_timer, 0.12)
            self.slowmo_timer = max(0.0, self.slowmo_timer - self.dt)
            self.combo_flash = max(0.0, self.combo_flash - self.dt * 2.5)
            self.screen_shake_timer = max(0.0, self.screen_shake_timer - self.dt)

            if random.random() < 0.3 and len(self.particles) < int(self.performance_cfg.get("max_particles", 240)):
                 p1 = Particle(self.player.rect.left + 10, self.player.rect.bottom)
                 p2 = Particle(self.player.rect.right - 10, self.player.rect.bottom)
                 self.particles.extend([p1, p2])

            # Enemy Particles
            for e in self.enemies:
                if random.random() < 0.3:
                    p1 = Particle(e.rect.left + 10, e.rect.bottom)
                    p2 = Particle(e.rect.right - 10, e.rect.bottom)
                    self.particles.extend([p1, p2])

            for p in self.particles[:]:
                if not p.update():
                    self.particles.remove(p)

    def game_over(self):
        self.state = "RUN_SUMMARY"
        self.play_music("MENU")

        # Build and record run
        self.active_car_key = self.get_selected_car_key()
        run_record = self._build_run_record()
        self.profile.record_run(run_record)
        new_unlocks = getattr(run_record, 'new_unlocks', [])

        # Check achievements
        new_achievements = check_achievements(self.profile, run_record)

        # Store summary data for the RUN_SUMMARY screen
        self.last_run_record = run_record
        self.last_run_new_unlocks = new_unlocks
        self.last_run_new_achievements = new_achievements
        self.last_run_is_new_best = (run_record.score >= self.profile.high_score)

        # Also keep legacy high_score synced
        self.high_score = self.profile.high_score

        # Save profile
        self.profile.save()

        # Legacy progression compat
        self.progression.award_xp(self.risk_system.risk_score // 8 + max(0, self.score // 20))
        self.progression.save()
        self.summary_scroll = 0

    def draw(self):
        # Draw Background (Scrolling)
        non_scroll_states = ("MENU", "INSTRUCTIONS", "SETTINGS", "CAR_SELECT",
                             "ROAD_SELECT", "RECORDS", "ACHIEVEMENTS")
        if self.state not in non_scroll_states:
            sx = getattr(self, 'screen_shake_offset_x', 0) if self.state == "PLAYING" else 0
            sy = getattr(self, 'screen_shake_offset_y', 0) if self.state == "PLAYING" else 0
            self.screen.blit(self.background, (sx, self.bg_y + sy))
            self.screen.blit(self.background, (sx, self.bg_y - SCREEN_HEIGHT + sy))

        if self.state == "MENU":
            self.screen.fill(BLACK)
            
            # Title
            title = self.big_font.render("RED RACER", True, RED)
            subtitle = self.font.render("ULTIMATE EDITION", True, WHITE)
            mode_text = self.small_font.render(f"Mode: {modes_short_name(self.current_mode)}", True, CYAN)
            level_text = self.small_font.render(
                f"Level {self.progression.level}  XP {self.progression.xp}  |  Best: {self.profile.high_score}", True, WHITE)
            
            # Current Car Preview (Left and Right)
            # Scale up for better visibility (e.g. 2x size: 100x200)
            preview_img = pygame.transform.scale(self.player_img, (100, 200))
            
            # Left Side
            self.screen.blit(preview_img, (100, 300))
            
            # Right Side
            self.screen.blit(preview_img, (600, 300))
            
            self.screen.blit(title, (SCREEN_WIDTH//2 - 120, 80))
            self.screen.blit(subtitle, (SCREEN_WIDTH//2 - 110, 130))
            self.screen.blit(mode_text, (SCREEN_WIDTH//2 - 90, 550))
            self.screen.blit(level_text, (20, 20))
            
            # Buttons
            self.btn_start.draw(self.screen)
            self.btn_editor.draw(self.screen)
            self.btn_difficulty.draw(self.screen)
            self.btn_settings.draw(self.screen)
            self.btn_instr.draw(self.screen)
            self.btn_mode.draw(self.screen)
            self.btn_quit.draw(self.screen)
        
        elif self.state == "EDITOR":
             self.screen.fill(BLACK)
             title = self.font.render("GARAGE", True, PURPLE)
             self.screen.blit(title, (SCREEN_WIDTH//2 - 50, 50))
             
             # Show car mastery info
             car_key = self.get_selected_car_key()
             mastery = self.profile.get_car_mastery(car_key)
             mastery_text = self.small_font.render(
                 f"Car: {car_key}  |  Best: {mastery.best_score}  |  Runs: {mastery.runs}", True, CYAN)
             self.screen.blit(mastery_text, (SCREEN_WIDTH//2 - mastery_text.get_width()//2, 90))

             self.btn_select_car.draw(self.screen)
             self.btn_select_road.draw(self.screen)
             self.btn_records.draw(self.screen)
             self.btn_achievements.draw(self.screen)
             self.btn_back.draw(self.screen)

        elif self.state == "SETTINGS":
            self.screen.fill((10, 10, 16))
            title = self.big_font.render("SETTINGS", True, (150, 180, 255))
            subtitle = self.small_font.render("Toggle additive features (base gameplay remains intact)", True, CYAN)
            self.screen.blit(title, (SCREEN_WIDTH//2 - 130, 30))
            self.screen.blit(subtitle, (SCREEN_WIDTH//2 - subtitle.get_width()//2, 88))

            panel = pygame.Rect(70, 120, 660, 430)
            pygame.draw.rect(self.screen, (20, 20, 28), panel, border_radius=14)
            pygame.draw.rect(self.screen, (100, 125, 170), panel, 2, border_radius=14)

            self.settings_toggle_rects = []
            settings_rows = [
                ("boost_system", "Boost System", "Enable burst/sustain nitro controls and boost gain from risk.", "LSHIFT/LCTRL"),
                ("debug_overlay", "Debug Overlay", "Show FPS, speed, active bonuses, and traffic density.", "F3"),
                ("near_miss_hitboxes", "Near-Miss Hitboxes", "Visualize near-miss debug circles around traffic cars.", "F4"),
                ("reduced_motion", "Reduced Motion", "Reduce heavy screen effects for comfort/accessibility.", "F6"),
                ("colorblind_hud", "Colorblind HUD", "Switch HUD palette for clearer color distinction.", "F7"),
            ]

            y = 140
            for key, name, desc, hotkey in settings_rows:
                row = pygame.Rect(88, y, 624, 72)
                pygame.draw.rect(self.screen, (34, 34, 46), row, border_radius=10)
                pygame.draw.rect(self.screen, (95, 110, 138), row, 1, border_radius=10)

                enabled = self.setting_enabled(key)
                toggle_rect = pygame.Rect(row.right - 108, row.y + 18, 84, 36)
                toggle_color = (40, 180, 90) if enabled else (140, 60, 60)
                pygame.draw.rect(self.screen, toggle_color, toggle_rect, border_radius=8)
                pygame.draw.rect(self.screen, WHITE, toggle_rect, 2, border_radius=8)
                toggle_text = "ON" if enabled else "OFF"
                self.screen.blit(self.small_font.render(toggle_text, True, WHITE), (toggle_rect.x + 24, toggle_rect.y + 9))

                self.screen.blit(self.small_font.render(name, True, (245, 245, 255)), (104, y + 8))
                self.draw_wrapped_text(
                    self.screen,
                    desc,
                    self.small_font,
                    (210, 220, 245),
                    104,
                    y + 34,
                    row.width - 250,
                    line_gap=0,
                    max_lines=2,
                )

                hotkey_badge = pygame.Rect(row.right - 228, row.y + 6, 106, 24)
                pygame.draw.rect(self.screen, (40, 45, 70), hotkey_badge, border_radius=6)
                pygame.draw.rect(self.screen, (110, 130, 190), hotkey_badge, 1, border_radius=6)
                self.screen.blit(self.small_font.render(hotkey, True, (255, 235, 130)), (hotkey_badge.x + 12, hotkey_badge.y + 3))

                self.settings_toggle_rects.append((toggle_rect, key))
                y += 80

            self.btn_back.draw(self.screen)

        elif self.state == "INSTRUCTIONS":
            self.screen.fill((8, 8, 12))
            title = self.big_font.render("HOW TO PLAY", True, YELLOW)
            subtitle = self.small_font.render("Ultimate Edition Guide", True, CYAN)
            self.screen.blit(title, (SCREEN_WIDTH//2 - 145, 20))
            self.screen.blit(subtitle, (SCREEN_WIDTH//2 - 88, 72))

            # Left panel: controls + driving systems
            left_panel = pygame.Rect(40, 110, 350, 420)
            pygame.draw.rect(self.screen, (20, 20, 26), left_panel, border_radius=12)
            pygame.draw.rect(self.screen, (90, 120, 150), left_panel, 2, border_radius=12)

            self.screen.blit(self.small_font.render("CONTROLS", True, CYAN), (58, 126))
            controls_lines = [
                "Steer:  A/D  or  LEFT/RIGHT",
                "Throttle/Brake:  W/S  or  UP/DOWN",
                "Pause:  P",
                "Boost Burst:  LEFT SHIFT",
                "Boost Sustain:  LEFT CTRL",
                "",
                "F3  Toggle Debug Overlay",
                "F4  Near-Miss Hitboxes",
                "F6  Reduced Motion",
                "F7  Colorblind HUD",
                "",
                "Editor > DRIVER toggles HUMAN/AI",
            ]
            y = 154
            for line in controls_lines:
                color = WHITE if line else (160, 160, 170)
                if line:
                    y = self.draw_wrapped_text(self.screen, line, self.small_font, color, 58, y, left_panel.width - 28, line_gap=1, max_lines=2)
                else:
                    y += 14

            # Right panel: objective + systems + modes
            right_panel = pygame.Rect(410, 110, 350, 420)
            pygame.draw.rect(self.screen, (20, 20, 26), right_panel, border_radius=12)
            pygame.draw.rect(self.screen, (180, 120, 80), right_panel, 2, border_radius=12)

            self.screen.blit(self.small_font.render("OBJECTIVE & SYSTEMS", True, YELLOW), (428, 126))
            info_lines = [
                "Survive traffic and maximize score.",
                "Base score + Risk score stack together.",
                "Near misses and overtakes build combo.",
                "Boost is earned from risky driving.",
                "Fuel and health management matter.",
                "",
                "Pick car/road in EDITOR before racing.",
                f"Current Mode: {modes_short_name(self.current_mode)}",
                "Classic: full scoring | High-Risk: risk only",
                "Time Attack: beat timer | Hardcore: one life",
                "Daily Run: seeded traffic",
                "Zen: low pressure free driving",
            ]
            y = 154
            for line in info_lines:
                color = WHITE if line else (160, 160, 170)
                if line:
                    y = self.draw_wrapped_text(self.screen, line, self.small_font, color, 428, y, right_panel.width - 24, line_gap=1, max_lines=2)
                else:
                    y += 14

            tip_bar = pygame.Rect(46, 502, 708, 36)
            pygame.draw.rect(self.screen, (30, 24, 14), tip_bar, border_radius=8)
            pygame.draw.rect(self.screen, (170, 120, 70), tip_bar, 1, border_radius=8)
            self.draw_fit_text(
                self.screen,
                "Tip: safest scoring is slow — highest scoring is controlled risk.",
                (255, 210, 130),
                56,
                511,
                tip_bar.width - 20,
                start_size=34,
                min_size=20,
            )

            self.btn_back.draw(self.screen)
        
        elif self.state == "CAR_SELECT":
            self.screen.fill(BLACK)
            title = self.font.render("SELECT YOUR CAR", True, GREEN)
            self.screen.blit(title, (SCREEN_WIDTH//2 - 120, 24))

            if self.available_cars:
                name, img, _ = self.available_cars[self.car_select_index]
                car_key = name.split('.')[0]
                car_info = get_car_display_stats(car_key)
                spec = car_info["specs"]

                # Card panel
                panel = pygame.Rect(90, 80, 620, 430)
                pygame.draw.rect(self.screen, (20, 20, 20), panel, border_radius=12)
                pygame.draw.rect(self.screen, WHITE, panel, 2, border_radius=12)

                preview_box = pygame.Rect(120, 118, 250, 300)
                specs_box = pygame.Rect(390, 118, 290, 300)
                pygame.draw.rect(self.screen, (28, 28, 28), preview_box, border_radius=10)
                pygame.draw.rect(self.screen, (28, 28, 28), specs_box, border_radius=10)
                pygame.draw.rect(self.screen, GRAY, preview_box, 1, border_radius=10)
                pygame.draw.rect(self.screen, GRAY, specs_box, 1, border_radius=10)

                # Car display (single car only)
                car_img = pygame.transform.scale(img, (120, 240))
                car_rect = car_img.get_rect(center=(245, 270))
                self.screen.blit(car_img, car_rect)

                # Left / right carousel controls
                left_btn = pygame.Rect(140, 430, 70, 50)
                right_btn = pygame.Rect(280, 430, 70, 50)
                pygame.draw.rect(self.screen, CYAN, left_btn, border_radius=10)
                pygame.draw.rect(self.screen, CYAN, right_btn, border_radius=10)
                self.screen.blit(self.big_font.render("<", True, BLACK), (163, 422))
                self.screen.blit(self.big_font.render(">", True, BLACK), (303, 422))

                # Name and index
                name_text = self.font.render(car_info["display_name"].upper(), True, YELLOW)
                self.screen.blit(name_text, (SCREEN_WIDTH//2 - name_text.get_width()//2, 92))
                idx_text = self.small_font.render(f"{self.car_select_index + 1}/{len(self.available_cars)}", True, WHITE)
                self.screen.blit(idx_text, (SCREEN_WIDTH//2 - idx_text.get_width()//2, 122))

                # Archetype badge
                arch_color = car_info["archetype_color"]
                arch_badge = pygame.Rect(132, 320, 226, 42)
                pygame.draw.rect(self.screen, (20, 20, 20), arch_badge, border_radius=8)
                pygame.draw.rect(self.screen, arch_color, arch_badge, 2, border_radius=8)
                self.screen.blit(self.small_font.render(f"TYPE: {car_info['archetype']}", True, arch_color), (142, 326))
                self.screen.blit(self.small_font.render(f"TIER {car_info['tier']}", True, GRAY), (300, 326))

                # Archetype description
                self.draw_wrapped_text(self.screen, car_info["archetype_desc"], self.small_font,
                    (180, 180, 180), 142, 348, 206, line_gap=0, max_lines=2)

                # Specs block - gameplay stats
                self.screen.blit(self.small_font.render("PERFORMANCE", True, CYAN), (470, 132))
                y = 155
                for label, val in car_info["stats"]:
                    self.screen.blit(self.small_font.render(f"{label}: {val}", True, WHITE), (415, y))
                    y += 22

                # Real-world specs section
                y += 10
                self.screen.blit(self.small_font.render("ENGINE", True, CYAN), (470, y))
                y += 20
                spec_lines = [
                    f"BHP: {spec.get('bhp', '?')}",
                    f"0-60: {spec.get('zero_sixty', '?')}s",
                    f"Engine: {spec.get('engine', '?')}",
                    f"Drive: {spec.get('drive', '?')}",
                ]
                for line in spec_lines:
                    self.screen.blit(self.small_font.render(line, True, GRAY), (415, y))
                    y += 18

                controls = self.small_font.render("LEFT/RIGHT (or A/D) to browse", True, CYAN)
                self.screen.blit(controls, (120, 486))

                pick_btn = pygame.Rect(305, 500, 190, 42)
                pygame.draw.rect(self.screen, GREEN, pick_btn, border_radius=8)
                pygame.draw.rect(self.screen, WHITE, pick_btn, 2, border_radius=8)
                self.screen.blit(self.small_font.render("SELECT CAR", True, BLACK), (356, 511))
                self.screen.blit(self.small_font.render("ENTER/SPACE to pick", True, CYAN), (520, 510))

            self.btn_back.draw(self.screen)
        
        elif self.state == "ROAD_SELECT":
            self.screen.fill(BLACK)
            title = self.font.render("SELECT ROAD", True, CYAN)
            self.screen.blit(title, (SCREEN_WIDTH//2 - 100, 24))

            if self.available_roads:
                road_name = self.available_roads[self.road_select_index]
                thumb = next((img for rn, img in self.road_thumbnails if rn == road_name), None)
                if thumb is None:
                    thumb = pygame.Surface((300, 150))
                    thumb.fill(GRAY)

                spec = get_road_display(road_name)

                panel = pygame.Rect(90, 80, 620, 430)
                pygame.draw.rect(self.screen, (20, 20, 20), panel, border_radius=12)
                pygame.draw.rect(self.screen, WHITE, panel, 2, border_radius=12)

                preview_box = pygame.Rect(120, 118, 250, 300)
                info_box = pygame.Rect(390, 118, 290, 300)
                pygame.draw.rect(self.screen, (28, 28, 28), preview_box, border_radius=10)
                pygame.draw.rect(self.screen, (28, 28, 28), info_box, border_radius=10)
                pygame.draw.rect(self.screen, GRAY, preview_box, 1, border_radius=10)
                pygame.draw.rect(self.screen, GRAY, info_box, 1, border_radius=10)

                preview_w, preview_h = 220, 130
                scaled_w = max(1, int(thumb.get_width() * (preview_h / max(1, thumb.get_height()))))
                scaled_thumb = pygame.transform.smoothscale(thumb, (scaled_w, preview_h))
                preview_x = preview_box.x + (preview_box.width - preview_w) // 2
                preview_y = 170
                if scaled_w <= preview_w:
                    self.screen.blit(scaled_thumb, (preview_x + (preview_w - scaled_w) // 2, preview_y))
                else:
                    left_lane, right_lane = ROAD_CONFIGS.get(road_name, (ROAD_LEFT, ROAD_RIGHT))
                    lane_center_ratio = ((left_lane + right_lane) / 2) / SCREEN_WIDTH
                    center_px = int(lane_center_ratio * scaled_w)
                    src_x = max(0, min(scaled_w - preview_w, center_px - (preview_w // 2)))
                    road_preview = scaled_thumb.subsurface((src_x, 0, preview_w, preview_h))
                    self.screen.blit(road_preview, (preview_x, preview_y))

                left_btn = pygame.Rect(140, 430, 70, 50)
                right_btn = pygame.Rect(280, 430, 70, 50)
                pygame.draw.rect(self.screen, CYAN, left_btn, border_radius=10)
                pygame.draw.rect(self.screen, CYAN, right_btn, border_radius=10)
                self.screen.blit(self.big_font.render("<", True, BLACK), (163, 422))
                self.screen.blit(self.big_font.render(">", True, BLACK), (303, 422))

                name_text = self.font.render(spec["name"].upper(), True, YELLOW)
                self.screen.blit(name_text, (SCREEN_WIDTH//2 - name_text.get_width()//2, 92))
                idx_text = self.small_font.render(f"{self.road_select_index + 1}/{len(self.available_roads)}", True, WHITE)
                self.screen.blit(idx_text, (SCREEN_WIDTH//2 - idx_text.get_width()//2, 122))

                left_lane, right_lane = ROAD_CONFIGS.get(road_name, (ROAD_LEFT, ROAD_RIGHT))
                lane_width = right_lane - left_lane
                info_lines = [
                    f"Traffic Flow: {spec['traffic']}",
                    f"Risk Level: {spec['risk']}",
                    f"Surface: {spec['surface']}",
                    f"Visibility: {spec['visibility']}",
                    f"Lane Width: {lane_width}px",
                    f"Notes: {spec['note']}",
                ]

                self.screen.blit(self.small_font.render("ROAD INFO", True, CYAN), (475, 132))
                y = 170
                for line in info_lines:
                    text = self.small_font.render(line, True, WHITE)
                    self.screen.blit(text, (405, y))
                    y += 34

                controls = self.small_font.render("LEFT/RIGHT (or A/D) to browse", True, CYAN)
                self.screen.blit(controls, (120, 486))

                pick_btn = pygame.Rect(305, 500, 190, 42)
                pygame.draw.rect(self.screen, GREEN, pick_btn, border_radius=8)
                pygame.draw.rect(self.screen, WHITE, pick_btn, 2, border_radius=8)
                self.screen.blit(self.small_font.render("SELECT ROAD", True, BLACK), (350, 511))
                self.screen.blit(self.small_font.render("ENTER/SPACE to pick", True, CYAN), (520, 510))
                
            self.btn_back.draw(self.screen)


        elif self.state == "PLAYING" or self.state == "PAUSED":
            for p in self.particles:
                p.draw(self.screen)
            self.player.draw(self.screen)
            for e in self.enemies:
                e.draw(self.screen)
            for c in self.coins:
                c.draw(self.screen)
            for f in self.fuels:
                f.draw(self.screen)
            for n in self.nitros:
                n.draw(self.screen)
            for r in self.repair_kits:
                r.draw(self.screen)
            for s in self.shields:
                s.draw(self.screen)
            for sm in self.score_mults:
                sm.draw(self.screen)

            # Speed lines
            self._draw_speed_lines()

            # Shield overlay
            if self.shield_timer > 0:
                shield_surf = pygame.Surface((60, 110), pygame.SRCALPHA)
                alpha = int(80 + 40 * abs(math.sin(time.time() * 4)))
                pygame.draw.ellipse(shield_surf, (0, 200, 255, alpha), shield_surf.get_rect(), 3)
                self.screen.blit(shield_surf,
                    (self.player.rect.x - 5, self.player.rect.y - 5))

            # Score multiplier indicator
            if self.score_mult_timer > 0:
                mult_text = self.small_font.render(f"x{SCORE_MULT_PICKUP_BONUS:.1f} SCORE!", True, YELLOW)
                self.screen.blit(mult_text, (SCREEN_WIDTH // 2 - mult_text.get_width() // 2, 4))
            
            # UI
            hud_white = WHITE if not self.features.get("colorblind_hud", False) else (240, 240, 30)
            score_text = self.font.render(f"Score: {self.score}", True, hud_white)
            fuel_text = self.font.render(f"Fuel: {int(self.fuel)}%", True, CYAN)
            self.screen.blit(score_text, (10, 10))
            self.screen.blit(fuel_text, (10, 50))
            breakdown_text = self.small_font.render(
                f"Base: {self.base_score}  Risk: {self.risk_system.risk_score}",
                True,
                WHITE,
            )
            self.screen.blit(breakdown_text, (10, 146))
            mode_text = self.small_font.render(f"MODE: {modes_short_name(self.current_mode)}", True, CYAN)
            self.screen.blit(mode_text, (10, 78))

            if self.current_mode == "TIME_ATTACK":
                remaining = max(0.0, self.mode_time_limit - self.mode_elapsed)
                timer_text = self.small_font.render(f"TIME: {remaining:05.1f}s", True, YELLOW)
                self.screen.blit(timer_text, (SCREEN_WIDTH - 150, 80))
            elif self.current_mode == "DAILY_RUN":
                daily_text = self.small_font.render(f"DAILY PROFILE: {self.daily_profile.upper()}", True, YELLOW)
                self.screen.blit(daily_text, (SCREEN_WIDTH - 260, 80))
            elif self.current_mode == "ZEN":
                zen_text = self.small_font.render(f"ZEN FOCUS: {int(self.zen_focus)}", True, YELLOW)
                self.screen.blit(zen_text, (SCREEN_WIDTH - 200, 80))

            combo_w = 220
            combo_ratio = min(1.0, self.risk_system.combo / max(1.0, self.risk_system.combo_max))
            combo_fill = int(combo_w * combo_ratio)
            glow = int(100 + 155 * self.risk_system.glow)
            combo_color = (min(255, glow), 80, 40)
            pygame.draw.rect(self.screen, (30, 30, 30), (10, 108, combo_w, 16), border_radius=6)
            pygame.draw.rect(self.screen, combo_color, (10, 108, combo_fill, 16), border_radius=6)
            combo_text = self.small_font.render(f"Combo x{self.risk_system.multiplier():.2f}", True, WHITE)
            self.screen.blit(combo_text, (240, 104))

            boost_enabled = self.features.get("boost_system", True)
            boost_ratio = (self.boost_system.meter / max(1.0, self.boost_system.max_meter)) if boost_enabled else 0.0
            pygame.draw.rect(self.screen, (25, 25, 25), (10, 130, combo_w, 12), border_radius=5)
            pygame.draw.rect(self.screen, (50, 180, 255), (10, 130, int(combo_w * boost_ratio), 12), border_radius=5)
            if not boost_enabled:
                boost_state = "OFF"
            else:
                boost_state = self.boost_system.active_type.upper() if self.boost_system.active_type else "READY"
            boost_label_bg = pygame.Rect(236, 124, 132, 22)
            pygame.draw.rect(self.screen, (18, 18, 18), boost_label_bg, border_radius=6)
            self.screen.blit(self.small_font.render(f"BOOST {boost_state}", True, WHITE), (242, 127))

            # Mission HUD (right side)
            if hasattr(self, 'mission_system') and self.mission_system.active_missions:
                my = SCREEN_HEIGHT - 120
                for m in self.mission_system.active_missions:
                    if m.completed:
                        color = GREEN
                        status = "DONE"
                    else:
                        progress = getattr(m, 'progress', 0)
                        target = getattr(m, 'target', 1)
                        # Mini progress bar
                        bar_w = 80
                        bar_x = SCREEN_WIDTH - bar_w - 10
                        if target > 0:
                            ratio = min(1.0, progress / float(target))
                        else:
                            ratio = 0.0
                        color = WHITE
                        status = f"{progress}/{target}"
                        pygame.draw.rect(self.screen, (40, 40, 40), (bar_x, my + 14, bar_w, 6), border_radius=3)
                        pygame.draw.rect(self.screen, CYAN, (bar_x, my + 14, int(bar_w * ratio), 6), border_radius=3)
                    name_text = self.small_font.render(f"{m.name} {status}", True, color)
                    self.screen.blit(name_text, (SCREEN_WIDTH - name_text.get_width() - 10, my))
                    my += 26

            # Mission/achievement flash notifications
            if self.mission_flash_timer > 0:
                self.mission_flash_timer -= self.dt
                alpha = min(255, int(255 * min(1.0, self.mission_flash_timer / 0.5)))
                flash_surf = self.font.render(self.mission_flash_text, True, YELLOW)
                flash_surf.set_alpha(alpha)
                self.screen.blit(flash_surf, (SCREEN_WIDTH // 2 - flash_surf.get_width() // 2, SCREEN_HEIGHT // 3))

            if self.achievement_flash_timer > 0:
                self.achievement_flash_timer -= self.dt
                alpha = min(255, int(255 * min(1.0, self.achievement_flash_timer / 0.5)))
                flash_surf = self.font.render(self.achievement_flash_text, True, (255, 215, 0))
                flash_surf.set_alpha(alpha)
                self.screen.blit(flash_surf, (SCREEN_WIDTH // 2 - flash_surf.get_width() // 2, SCREEN_HEIGHT // 3 + 40))

            if self.risk_system.edge_pulse > 0 and not self.features.get("reduced_motion", False):
                edge = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                alpha = int(90 * self.risk_system.edge_pulse)
                edge_color = (255, 80, 30, alpha)
                pygame.draw.rect(edge, edge_color, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 8)
                self.screen.blit(edge, (0, 0))

            if self.show_near_miss_hitboxes:
                for e in self.enemies:
                    pygame.draw.circle(self.screen, YELLOW, e.rect.center, int(self.config.get("risk", {}).get("near_miss_distance", 44)), 1)

            left_stack_bottom = 165
            if self.difficulty == "EASY" and self.current_mode != "ONE_LIFE_HARDCORE":
                left_stack_bottom = 188

            if self.show_debug_overlay:
                fps = int(self.clock.get_fps())
                bonus_labels = []
                for b in self.risk_system.active_bonuses:
                    if b not in bonus_labels:
                        bonus_labels.append(b)
                bonus_text = ", ".join(bonus_labels[:3]) if bonus_labels else "None"
                if len(bonus_text) > 44:
                    bonus_text = bonus_text[:41] + "..."
                lines = [
                    f"FPS: {fps}",
                    f"SPD: {self.enemy_speed:.2f}",
                    f"Base score: {self.base_score}",
                    f"Risk bonuses: {bonus_text}",
                    f"Traffic: {len(self.enemies)}",
                ]
                y = left_stack_bottom
                for line in lines:
                    self.screen.blit(self.small_font.render(line, True, WHITE), (10, y))
                    y += 18
                left_stack_bottom = y
            
            if self.difficulty == "EASY" and self.current_mode != "ONE_LIFE_HARDCORE":
                 # Themed HP bar aligned with combo/boost visual language
                 hp_x, hp_y, hp_w, hp_h = 10, 165, 220, 14
                 hp_ratio = max(0.0, min(1.0, self.health / PLAYER_MAX_HEALTH))
                 hp_fill = int(hp_w * hp_ratio)
                 hp_color = (40, 210, 120) if hp_ratio > 0.5 else (220, 170, 40) if hp_ratio > 0.25 else (220, 70, 70)
                 pygame.draw.rect(self.screen, (25, 25, 25), (hp_x, hp_y, hp_w, hp_h), border_radius=5)
                 pygame.draw.rect(self.screen, hp_color, (hp_x, hp_y, hp_fill, hp_h), border_radius=5)
                 pygame.draw.rect(self.screen, WHITE, (hp_x, hp_y, hp_w, hp_h), 1, border_radius=5)
                 hp_text = self.small_font.render(f"HP {int(self.health)}", True, WHITE)
                 self.screen.blit(hp_text, (240, 161))
                 left_stack_bottom = max(left_stack_bottom, hp_y + hp_h + 4)

            # Compact car cluster packed inside right off-road boundary.
            boost_influence = 0.12 if self.boost_system.active_type is not None else 0.0
            rpm_ratio = max(0.0, min(1.0, self.rev_level + boost_influence))
            shoulder_w = SCREEN_WIDTH - self.road_limits[1]
            cluster_w = int(max(96, min(122, shoulder_w - 8)))
            cluster_h = 140
            cluster_x = SCREEN_WIDTH - cluster_w - 6
            cluster_y = SCREEN_HEIGHT - cluster_h - 8

            cluster_panel = pygame.Surface((cluster_w, cluster_h), pygame.SRCALPHA)
            pygame.draw.rect(cluster_panel, (10, 10, 10, 165), cluster_panel.get_rect(), border_radius=10)
            self.screen.blit(cluster_panel, (cluster_x, cluster_y))

            speed_mph = int(self.display_speed_mph)
            speed_ratio = speed_mph / max(1, self.car_top_speed_mph)
            gear_table = ["1", "2", "3", "4", "5", "6", "7"]
            gear_idx = min(len(gear_table) - 1, int(speed_ratio * len(gear_table)))
            gear = gear_table[gear_idx] if speed_mph > 5 else "N"

            self.screen.blit(self.small_font.render("MPH", True, CYAN), (cluster_x + 8, cluster_y + 7))
            self.screen.blit(self.font.render(f"{speed_mph:03d}", True, WHITE), (cluster_x + 8, cluster_y + 24))
            self.screen.blit(self.small_font.render(f"TOP {self.car_top_speed_mph}", True, GRAY), (cluster_x + 8, cluster_y + 55))
            self.screen.blit(self.small_font.render(f"G {gear}", True, CYAN if gear != "N" else GRAY), (cluster_x + cluster_w - 38, cluster_y + 8))

            boost_bar_x = cluster_x + 8
            boost_bar_y = cluster_y + 86
            boost_bar_w = cluster_w - 16
            boost_bar_h = 8
            pygame.draw.rect(self.screen, (35, 35, 35), (boost_bar_x, boost_bar_y, boost_bar_w, boost_bar_h), border_radius=4)
            fill_color = (70, 200, 255) if boost_enabled else (80, 80, 80)
            pygame.draw.rect(self.screen, fill_color, (boost_bar_x, boost_bar_y, int(boost_bar_w * boost_ratio), boost_bar_h), border_radius=4)
            label_bg = pygame.Rect(boost_bar_x - 1, boost_bar_y + 10, boost_bar_w + 2, 18)
            pygame.draw.rect(self.screen, (14, 14, 14), label_bg, border_radius=5)
            self.screen.blit(self.small_font.render(f"BOOST {boost_state}", True, WHITE if boost_enabled else (170, 170, 170)), (boost_bar_x + 2, boost_bar_y + 12))

            seg_count = 8
            seg_gap = 2
            seg_w = max(6, int((cluster_w - 14 - (seg_count - 1) * seg_gap) / seg_count))
            seg_y = cluster_y + cluster_h - 12
            active_segments = int(rpm_ratio * seg_count + 0.001)
            for i in range(seg_count):
                x = cluster_x + 7 + i * (seg_w + seg_gap)
                if i < 4:
                    on_color = (40, 220, 120)
                elif i < 6:
                    on_color = (235, 190, 40)
                else:
                    on_color = (240, 70, 70)
                color = on_color if i < active_segments else (45, 45, 45)
                if rpm_ratio > 0.98 and i >= seg_count - 2 and (pygame.time.get_ticks() // 70) % 2 == 0:
                    color = WHITE
                pygame.draw.rect(self.screen, color, (x, seg_y, seg_w, 10), border_radius=3)

            if self.state == "PAUSED":
                 pause_text = self.font.render("PAUSED", True, YELLOW)
                 self.screen.blit(pause_text, (SCREEN_WIDTH//2 - 50, SCREEN_HEIGHT//2))

        elif self.state == "GAME_OVER":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(128)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0,0))
            
            go_text = self.font.render("GAME OVER", True, RED)
            score_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
            hi_text = self.font.render(f"High Score: {self.high_score}", True, YELLOW)
            restart_text = self.font.render("Press R to Restart or Q for Menu", True, WHITE)
            if self.current_mode == "ONE_LIFE_HARDCORE":
                restart_text = self.font.render("Hardcore: Press Q for Menu", True, WHITE)

            stats = [
                f"Near Misses: {self.run_stats['near_misses']}",
                f"Max Combo: {self.run_stats['max_combo']}",
                f"Max Speed: {self.run_stats['max_speed']}",
                f"Risk Score %: {int((self.risk_system.risk_score / max(1, self.score)) * 100)}%",
            ]
            
            self.screen.blit(go_text, (SCREEN_WIDTH//2 - 80, SCREEN_HEIGHT//2 - 80))
            self.screen.blit(score_text, (SCREEN_WIDTH//2 - 90, SCREEN_HEIGHT//2 - 30))
            self.screen.blit(hi_text, (SCREEN_WIDTH//2 - 90, SCREEN_HEIGHT//2 + 10))
            self.screen.blit(restart_text, (SCREEN_WIDTH//2 - 180, SCREEN_HEIGHT//2 + 60))
            sy = SCREEN_HEIGHT//2 + 100
            for s in stats:
                self.screen.blit(self.small_font.render(s, True, WHITE), (SCREEN_WIDTH//2 - 90, sy))
                sy += 20

        elif self.state == "RUN_SUMMARY":
            self.screen.fill((5, 5, 15))
            rr = getattr(self, 'last_run_record', None)
            is_best = getattr(self, 'last_run_is_new_best', False)
            new_unlocks = getattr(self, 'last_run_new_unlocks', [])
            new_achievements = getattr(self, 'last_run_new_achievements', [])
            scroll = getattr(self, 'summary_scroll', 0)

            title_color = (255, 215, 0) if is_best else RED
            title = self.big_font.render("NEW RECORD!" if is_best else "RUN SUMMARY", True, title_color)
            self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 20))

            if rr:
                y = 80 - scroll
                lines = [
                    (f"Score: {rr.score}", WHITE),
                    (f"Risk Score: {rr.risk_score}", CYAN),
                    (f"Base Score: {rr.base_score}", WHITE),
                    (f"Car: {rr.car_key}  |  Road: {rr.road_key}", WHITE),
                    (f"Mode: {rr.game_mode}  |  Difficulty: {rr.difficulty}", WHITE),
                    (f"Duration: {rr.duration_seconds:.1f}s", WHITE),
                    (f"Near Misses: {rr.near_misses}  |  Max Combo: {rr.max_combo}", CYAN),
                    (f"Top Speed: {rr.max_speed} mph  |  Multiplier: x{rr.top_multiplier:.2f}", CYAN),
                    (f"Coins: {rr.coins_collected}  |  Fuel: {rr.fuel_collected}", WHITE),
                    (f"Enemies Passed: {rr.enemies_passed}  |  Boost: {rr.boost_used_seconds:.1f}s", WHITE),
                ]
                for text, color in lines:
                    if 60 < y < SCREEN_HEIGHT - 60:
                        self.screen.blit(self.small_font.render(text, True, color), (60, y))
                    y += 24

                if new_unlocks:
                    y += 10
                    if 60 < y < SCREEN_HEIGHT - 60:
                        self.screen.blit(self.font.render("NEW UNLOCKS!", True, (255, 215, 0)), (60, y))
                    y += 30
                    for car in new_unlocks:
                        if 60 < y < SCREEN_HEIGHT - 60:
                            self.screen.blit(self.small_font.render(f"  Unlocked: {car}", True, GREEN), (60, y))
                        y += 22

                if new_achievements:
                    y += 10
                    if 60 < y < SCREEN_HEIGHT - 60:
                        self.screen.blit(self.font.render("ACHIEVEMENTS!", True, (255, 215, 0)), (60, y))
                    y += 30
                    for ach in new_achievements:
                        if 60 < y < SCREEN_HEIGHT - 60:
                            self.screen.blit(self.small_font.render(f"  {ach.icon} {ach.name}", True, GREEN), (60, y))
                        y += 22

                y += 20
                if 60 < y < SCREEN_HEIGHT - 60:
                    # Mastery progress
                    mastery = self.profile.get_car_mastery(rr.car_key)
                    self.screen.blit(self.small_font.render(
                        f"Car Mastery: {rr.car_key} — {mastery.runs} runs, best: {mastery.best_score}",
                        True, CYAN), (60, y))

            # Navigation
            restart_text = "Press R to Retry  |  Q for Menu"
            if self.current_mode == "ONE_LIFE_HARDCORE":
                restart_text = "Press Q for Menu"
            self.screen.blit(self.small_font.render(restart_text, True, WHITE),
                (SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT - 30))
            self.btn_back.draw(self.screen)

        elif self.state == "RECORDS":
            self.screen.fill((5, 5, 15))
            title = self.big_font.render("RECORDS", True, (150, 180, 255))
            self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 15))
            scroll = getattr(self, 'records_scroll', 0)

            y = 70 - scroll
            # Lifetime stats
            stats = self.profile.lifetime_stats
            section_lines = [
                ("LIFETIME STATS", CYAN),
                (f"Total Runs: {stats.get('total_runs', 0)}  |  Total Score: {stats.get('total_score', 0)}", WHITE),
                (f"Best Score: {self.profile.high_score}  |  Total Distance: {stats.get('total_distance_seconds', 0):.0f}s", WHITE),
                (f"Near Misses: {stats.get('total_near_misses', 0)}  |  Coins: {stats.get('total_coins', 0)}", WHITE),
                (f"Fuel: {stats.get('total_fuel', 0)}  |  Boost: {stats.get('total_boost_seconds', 0):.1f}s", WHITE),
                ("", WHITE),
                ("RECENT RUNS", CYAN),
            ]
            for text, color in section_lines:
                if 50 < y < SCREEN_HEIGHT - 50:
                    self.screen.blit(self.small_font.render(text, True, color), (40, y))
                y += 22

            for i, run in enumerate(reversed(self.profile.recent_runs[-10:])):
                text = f"#{i+1}: {run.get('score', 0)} pts | {run.get('car_key', '?')} | {run.get('road_key', '?')} | {run.get('game_mode', '?')} | {run.get('duration_seconds', 0):.1f}s"
                if 50 < y < SCREEN_HEIGHT - 50:
                    self.screen.blit(self.small_font.render(text, True, WHITE), (40, y))
                y += 20

            y += 10
            if 50 < y < SCREEN_HEIGHT - 50:
                self.screen.blit(self.small_font.render("PER-CAR BESTS", True, CYAN), (40, y))
            y += 24
            for car_key, mastery_data in self.profile.car_mastery.items():
                best = mastery_data.best_score
                runs = mastery_data.runs
                if best > 0:
                    text = f"  {car_key}: Best {best} | {runs} runs"
                    if 50 < y < SCREEN_HEIGHT - 50:
                        self.screen.blit(self.small_font.render(text, True, WHITE), (40, y))
                    y += 20

            self.screen.blit(self.small_font.render("Scroll: Mouse wheel or Arrow keys", True, (100, 100, 100)),
                (SCREEN_WIDTH // 2 - 130, SCREEN_HEIGHT - 22))
            self.btn_back.draw(self.screen)

        elif self.state == "ACHIEVEMENTS":
            self.screen.fill((5, 5, 15))
            title = self.big_font.render("ACHIEVEMENTS", True, (255, 215, 0))
            self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 15))
            scroll = getattr(self, 'achievements_scroll', 0)

            earned = self.profile.achievements_unlocked
            all_achievements = get_all_achievements()
            y = 65 - scroll
            for ach in all_achievements:
                name = ach["name"]
                desc = ach.get("description", "")
                is_earned = name in earned
                color = GREEN if is_earned else (100, 100, 100)
                icon = "★" if is_earned else "○"
                text = f"{icon} {name}"
                if 50 < y < SCREEN_HEIGHT - 50:
                    self.screen.blit(self.small_font.render(text, True, color), (40, y))
                    self.screen.blit(self.small_font.render(desc, True, (140, 140, 140) if not is_earned else WHITE), (40, y + 16))
                y += 38

            self.screen.blit(self.small_font.render(
                f"Earned: {len(earned)} / {len(all_achievements)}", True, CYAN),
                (SCREEN_WIDTH // 2 - 60, SCREEN_HEIGHT - 22))
            self.btn_back.draw(self.screen)

        if self.state == "PLAYING" and pygame.key.get_pressed()[pygame.K_b]:
             pygame.draw.line(self.screen, RED, (self.road_limits[0], 0), (self.road_limits[0], SCREEN_HEIGHT), 2)
             pygame.draw.line(self.screen, RED, (self.road_limits[1], 0), (self.road_limits[1], SCREEN_HEIGHT), 2)

        pygame.display.flip()

    def run(self):
        while True:
            tick_fps = FPS
            if self.slowmo_timer > 0 and not self.features.get("reduced_motion", False):
                tick_fps = 42
            self.dt = max(0.001, self.clock.tick(tick_fps) / 1000.0)
            self.handle_input()
            self.update()
            self.draw()

if __name__ == "__main__":
    game = Game()
    game.run()
