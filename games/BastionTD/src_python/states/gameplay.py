"""
states/gameplay.py - Core gameplay state for Bastion TD.

Integrates grid, economy, wave manager, towers, projectiles, particles,
damage numbers, screen shake, HUD, and audio into the build/wave phase loop.
"""
import pygame
from states.state_machine import State
from settings import (
    SCREEN_W, SCREEN_H, TILE_SIZE, GRID_W, GRID_H, GRID_OFFSET_Y,
    TOTAL_WAVES, BOSS_WAVES, TOWER_ORDER, TOWER_DEFS, ENEMY_DEFS,
    TERRAIN_EMPTY, TERRAIN_TOWER,
    COLOR_HUD_BG, COLOR_TRAY_BG, COLOR_CURSOR_OK, COLOR_CURSOR_BAD,
    COLOR_ACCENT, COLOR_WHITE, COLOR_GOLD, WAVE_CLEAR_BONUS,
    HUD_H, TRAY_H,
)
from grid import Grid
from economy import Economy
from wave_manager import WaveManager
from tower import Tower
from effects import ParticleSystem, DamageNumberSystem, ScreenShake
from hud import HUD
from map_generator import generate_map


class GameplayState(State):
    """The core game state: build phase <-> wave phase loop."""

    def __init__(self, game):
        super().__init__(game)
        # Core systems
        self.grid = None
        self.economy = None
        self.wave_mgr = None
        self.towers: list[Tower] = []
        self.projectiles = []
        self.particles = ParticleSystem()
        self.dmg_numbers = DamageNumberSystem()
        self.shake = ScreenShake()
        self.hud = HUD()

        # Cursor
        self.cursor_x: int = GRID_W // 2
        self.cursor_y: int = GRID_H // 2
        self.selected_tower_idx: int = 0

        # Controls
        self.fast_forward: bool = False

        # Sell/upgrade interaction
        self.sell_hold_timer: float = 0.0
        self.show_upgrade: bool = False

        # Notifications
        self.notification_text: str = ""
        self.notification_timer: float = 0.0

        # Pause overlay (handled internally)
        self.is_paused: bool = False
        self.pause_cursor_idx: int = 0

        # Stats tracking
        self.towers_built_count: int = 0
        self.game_time: float = 0.0

        # Fonts
        self._font_pause_title = None
        self._font_pause_menu = None
        self._font_info = None
        self._fonts_ready = False

    def _ensure_fonts(self):
        if not self._fonts_ready:
            self._font_pause_title = pygame.font.SysFont("monospace", 36, bold=True)
            self._font_pause_menu = pygame.font.SysFont("monospace", 22)
            self._font_info = pygame.font.SysFont("monospace", 14)
            self._fonts_ready = True

    def _init_game(self):
        """Initialize or reset all game state for a new game."""
        self.economy = Economy()
        self.wave_mgr = WaveManager()
        self.towers = []
        self.projectiles = []
        self.particles = ParticleSystem()
        self.dmg_numbers = DamageNumberSystem()
        self.shake = ScreenShake()
        self.cursor_x = GRID_W // 2
        self.cursor_y = GRID_H // 2
        self.selected_tower_idx = 0
        self.fast_forward = False
        self.sell_hold_timer = 0.0
        self.show_upgrade = False
        self.notification_text = ""
        self.notification_timer = 0.0
        self.is_paused = False
        self.pause_cursor_idx = 0
        self.towers_built_count = 0
        self.game_time = 0.0
        self._generate_map()

    def _generate_map(self):
        """Generate a new random map."""
        result = generate_map(GRID_W, GRID_H)
        self.grid = result[0]

    def enter(self):
        """Called when transitioning to gameplay state."""
        # If coming from pause (resume), don't reset
        prev = self.game.state_machine.previous_name
        if prev == "pause":
            self.is_paused = False
            return

        # Fresh game
        self._init_game()
        self.game.audio.play_bgm("bgm_build")

    def exit(self):
        pass

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt):
        inp = self.game.input

        # --- Pause toggle ---
        if inp.pressed("start"):
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.pause_cursor_idx = 0
            return

        if self.is_paused:
            self._update_pause(dt)
            return

        # --- Fast forward toggle ---
        if inp.pressed("select"):
            self.fast_forward = not self.fast_forward

        if self.fast_forward:
            dt *= 3

        # --- Update effects ---
        self.game_time += dt
        self.particles.update(dt)
        self.dmg_numbers.update(dt)
        self.shake.update(dt)

        # --- Notification timer ---
        if self.notification_timer > 0:
            self.notification_timer -= dt

        # --- Phase-specific logic ---
        if self.wave_mgr.phase == "build":
            self._update_build(dt)
        else:
            self._update_wave(dt)

    def _update_pause(self, dt):
        """Handle pause menu input."""
        inp = self.game.input
        pause_items = ["Resume", "Quit to Title"]

        if inp.pressed("up"):
            self.pause_cursor_idx = (self.pause_cursor_idx - 1) % len(pause_items)
            self.game.audio.play("menu_move")
        if inp.pressed("down"):
            self.pause_cursor_idx = (self.pause_cursor_idx + 1) % len(pause_items)
            self.game.audio.play("menu_move")

        if inp.pressed("a"):
            self.game.audio.play("menu_select")
            if pause_items[self.pause_cursor_idx] == "Resume":
                self.is_paused = False
            elif pause_items[self.pause_cursor_idx] == "Quit to Title":
                self.is_paused = False
                self.game.state_machine.change("title")

        if inp.pressed("b"):
            self.is_paused = False

    def _update_build(self, dt):
        """Handle build phase input: cursor movement, tower placement, wave start."""
        inp = self.game.input

        # --- Cursor movement ---
        if inp.pressed("up"):
            self.cursor_y = max(0, self.cursor_y - 1)
        if inp.pressed("down"):
            self.cursor_y = min(GRID_H - 1, self.cursor_y + 1)
        if inp.pressed("left"):
            self.cursor_x = max(0, self.cursor_x - 1)
        if inp.pressed("right"):
            self.cursor_x = min(GRID_W - 1, self.cursor_x + 1)

        # --- Cycle tower selection (L/R) or direct pick (1-5 / numpad) ---
        if inp.pressed("l"):
            self.selected_tower_idx = (self.selected_tower_idx - 1) % len(TOWER_ORDER)
            self.game.audio.play("menu_move")
        if inp.pressed("r"):
            self.selected_tower_idx = (self.selected_tower_idx + 1) % len(TOWER_ORDER)
            self.game.audio.play("menu_move")
        for i in range(len(TOWER_ORDER)):
            if inp.pressed(f"tower_{i + 1}"):
                self.selected_tower_idx = i
                self.game.audio.play("menu_move")
                break

        # --- Check what is under cursor ---
        tower_under = self._get_tower_at(self.cursor_x, self.cursor_y)
        is_buildable = self.grid.is_buildable(self.cursor_x, self.cursor_y)

        # --- B button: sell/upgrade on existing tower ---
        if tower_under is not None:
            if inp.held("b"):
                self.sell_hold_timer += dt
                if self.sell_hold_timer >= 1.0:
                    self._sell_tower(tower_under)
                    self.sell_hold_timer = 0.0
                    self.show_upgrade = False
            else:
                if inp.released("b"):
                    if self.sell_hold_timer < 1.0:
                        self.show_upgrade = not self.show_upgrade
                    self.sell_hold_timer = 0.0
                else:
                    self.sell_hold_timer = 0.0

            # Upgrade with A if upgrade menu is shown
            if self.show_upgrade and inp.pressed("a"):
                self._upgrade_tower(tower_under)
        else:
            self.sell_hold_timer = 0.0
            self.show_upgrade = False

            # --- A button: place tower or start wave ---
            if inp.pressed("a"):
                if is_buildable:
                    self._place_tower()
                else:
                    # Start wave
                    if self.wave_mgr.current_wave < TOTAL_WAVES:
                        self.wave_mgr.start_wave()
                        wave_num = self.wave_mgr.current_wave + 1
                        self.game.audio.play("wave_start")
                        self._set_notification(f"Wave {wave_num} incoming!")
                        # Switch BGM
                        if wave_num in BOSS_WAVES:
                            self.game.audio.play_bgm("bgm_boss")
                        else:
                            self.game.audio.play_bgm("bgm_wave")

    def _update_wave(self, dt):
        """Handle wave phase: enemy spawning, tower firing, projectile updates."""
        # --- Wave manager update ---
        events = self.wave_mgr.update(dt, self.grid)

        # --- Process wave events ---
        for event in events:
            etype = event["type"]

            if etype == "gold_earned":
                self.economy.earn(event["amount"])
                self.game.audio.play("enemy_death")
                # Particles at enemy death position
                ex = event.get("x", 0)
                ey = event.get("y", 0)
                etype_name = event.get("enemy_type", "goblin")
                ecolor = ENEMY_DEFS.get(etype_name, {}).get("color", (200, 200, 200))
                self.particles.emit(ex, ey + (GRID_OFFSET_Y / TILE_SIZE), ecolor, count=8)

            elif etype == "lives_lost":
                self.economy.lose_lives(event["amount"])
                self.game.audio.play("base_hit")
                self.shake.trigger(intensity=6, duration=0.3)

            elif etype == "boss_spawn":
                self.game.audio.play("boss_spawn")
                self.shake.trigger(intensity=8, duration=0.5)
                self._set_notification("TITAN INCOMING!")
                self.game.audio.play_bgm("bgm_boss")

            elif etype == "wave_complete":
                wave_num = event.get("wave", 0)
                # Check for no-leak bonus
                # The wave manager tracks leaks internally - if lives didn't change
                # we give bonus. Simplified: check by seeing if leaks == 0
                self.economy.wave_clear_bonus()
                self.game.audio.play("wave_clear")
                self._set_notification(f"Wave complete! +{WAVE_CLEAR_BONUS}g bonus!")
                self.game.audio.play_bgm("bgm_build")

                # Check victory
                if self.wave_mgr.current_wave >= TOTAL_WAVES:
                    self.game.state_machine.change("victory")
                    return

        # --- Tower updates: fire at enemies ---
        for tower in self.towers:
            proj = tower.update(dt, self.wave_mgr.active_enemies)
            if proj is not None:
                self.projectiles.append(proj)
                self.game.audio.play("shoot")

        # --- Projectile updates ---
        live_projectiles = []
        for proj in self.projectiles:
            was_alive = proj.alive
            proj.update(dt, self.wave_mgr.active_enemies)
            if not proj.alive and was_alive:
                # Projectile just hit
                self.game.audio.play("hit")
                # Emit particles at impact
                self.particles.emit(
                    proj.x, proj.y + (GRID_OFFSET_Y / TILE_SIZE),
                    proj.color, count=5, spread=1.5
                )
                # Damage number
                self.dmg_numbers.add(proj.x, proj.y + (GRID_OFFSET_Y / TILE_SIZE), proj.damage)
            if proj.alive:
                live_projectiles.append(proj)
        self.projectiles = live_projectiles

        # --- Check game over ---
        if self.economy.is_game_over():
            self.game.state_machine.change("game_over")
            return

    def _place_tower(self):
        """Place the currently selected tower at the cursor position."""
        tower_key = TOWER_ORDER[self.selected_tower_idx]
        tdef = TOWER_DEFS[tower_key]
        cost = tdef["cost"]

        if not self.economy.can_afford(cost):
            return

        self.economy.spend(cost)
        tower = Tower(tower_key, self.cursor_x, self.cursor_y)
        self.towers.append(tower)
        self.grid.set(self.cursor_x, self.cursor_y, TERRAIN_TOWER)
        self.towers_built_count += 1
        self.game.audio.play("place")

    def _sell_tower(self, tower: Tower):
        """Sell a tower and refund gold."""
        refund = tower.sell_value()
        self.economy.earn(refund)
        self.grid.set(tower.x, tower.y, TERRAIN_EMPTY)
        self.towers.remove(tower)
        self.game.audio.play("sell")
        self.show_upgrade = False

    def _upgrade_tower(self, tower: Tower):
        """Attempt to upgrade a tower."""
        defn = TOWER_DEFS[tower.type]
        upgrades = defn["upgrades"]
        upgrade_idx = tower.level - 1
        if upgrade_idx >= len(upgrades):
            return  # Max level

        cost = upgrades[upgrade_idx]["cost"]
        if not self.economy.can_afford(cost):
            return

        self.economy.spend(cost)
        tower.upgrade()
        self.game.audio.play("upgrade")
        self.show_upgrade = False

    def _get_tower_at(self, tx: int, ty: int) -> Tower | None:
        """Return the tower at tile position, or None."""
        for t in self.towers:
            if t.x == tx and t.y == ty:
                return t
        return None

    def _set_notification(self, text: str, duration: float = 2.0):
        """Set a center-screen notification."""
        self.notification_text = text
        self.notification_timer = duration

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
    def render(self, screen):
        self._ensure_fonts()

        shake_x, shake_y = self.shake.get_offset()

        # --- HUD background (top 64px, no shake) ---
        hud_rect = pygame.Rect(0, 0, SCREEN_W, HUD_H * TILE_SIZE)
        screen.fill(COLOR_HUD_BG, hud_rect)

        # --- Assets reference (None if sprites disabled in settings) ---
        assets = self.game.assets if self.game.use_sprites else None

        # --- Grid (with shake offset) ---
        self.grid.render(screen, cam_x=shake_x, cam_y=shake_y,
                         game_time=self.game_time, assets=assets)

        # Grid offset for all game entities
        off_x = shake_x
        off_y = GRID_OFFSET_Y + shake_y

        # --- Towers ---
        tower_under = self._get_tower_at(self.cursor_x, self.cursor_y)
        for tower in self.towers:
            tower.render(screen, off_x, off_y, assets=assets)
            # Show range circle if cursor is on this tower
            if tower is tower_under:
                tower.render_range(screen, off_x, off_y)

        # --- Enemies ---
        for enemy in self.wave_mgr.active_enemies:
            enemy.render(screen, off_x, off_y, assets=assets)

        # --- Projectiles ---
        for proj in self.projectiles:
            proj.render(screen, off_x, off_y)

        # --- Cursor overlay ---
        self._render_cursor(screen, off_x, off_y)

        # --- Particles and damage numbers ---
        self.particles.render(screen, shake_x, shake_y)
        self.dmg_numbers.render(screen, shake_x, shake_y)

        # --- HUD (no shake) ---
        # Find boss enemy for HP bar
        boss_enemy = None
        for e in self.wave_mgr.active_enemies:
            if e.type == "titan" and e.alive:
                boss_enemy = e
                break

        # Wave display: during wave phase, show current_wave+1 (1-indexed).
        # During build phase, current_wave has already been incremented after
        # the last wave completed, so it represents "next wave to play".
        # Show it as-is (which equals the last completed wave + 1, i.e. 1-indexed next).
        # Before any wave starts, current_wave is 0, so we show max(1, ...).
        if self.wave_mgr.phase == "wave":
            display_wave = self.wave_mgr.current_wave + 1
        else:
            display_wave = max(1, self.wave_mgr.current_wave)

        self.hud.render_hud(
            screen,
            wave=display_wave,
            total_waves=TOTAL_WAVES,
            gold=self.economy.gold,
            lives=self.economy.lives,
            phase=self.wave_mgr.phase,
            enemies_remaining=self.wave_mgr.enemies_remaining(),
            boss_enemy=boss_enemy,
            assets=assets,
        )

        # --- Tower tray (bottom bar, no shake) ---
        self.hud.render_tray(screen, self.selected_tower_idx, self.economy.gold,
                             assets=assets)

        # --- Upgrade/sell info on cursor ---
        if tower_under is not None and self.show_upgrade and self.wave_mgr.phase == "build":
            self._render_upgrade_info(screen, tower_under, off_x, off_y)

        # --- Notification ---
        if self.notification_timer > 0:
            self.hud.render_notification(screen, self.notification_text,
                                         self.notification_timer)

        # --- Fast forward indicator ---
        if self.fast_forward:
            ff_surf = self._font_info.render(">>> 3x SPEED >>>", True, COLOR_GOLD)
            screen.blit(ff_surf, (SCREEN_W - ff_surf.get_width() - 10, 44))

        # --- Pause overlay ---
        if self.is_paused:
            self._render_pause(screen)

    def _render_cursor(self, screen, off_x, off_y):
        """Draw the grid cursor with green/red indicator."""
        px = self.cursor_x * TILE_SIZE + off_x
        py = self.cursor_y * TILE_SIZE + off_y

        is_buildable = self.grid.is_buildable(self.cursor_x, self.cursor_y)

        # Semi-transparent cursor
        cursor_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        if is_buildable:
            cursor_surf.fill(COLOR_CURSOR_OK)
        else:
            cursor_surf.fill(COLOR_CURSOR_BAD)
        screen.blit(cursor_surf, (px, py))

        # Cursor border
        border_color = (80, 255, 80) if is_buildable else (255, 80, 80)
        pygame.draw.rect(screen, border_color, (px, py, TILE_SIZE, TILE_SIZE), 2)

    def _render_upgrade_info(self, screen, tower: Tower, off_x, off_y):
        """Render upgrade/sell info box near the tower."""
        px = tower.x * TILE_SIZE + off_x
        py = tower.y * TILE_SIZE + off_y

        # Info box position (to the right if possible)
        box_x = px + TILE_SIZE + 4
        box_y = py - 10
        if box_x + 160 > SCREEN_W:
            box_x = px - 164

        # Background
        box_rect = pygame.Rect(box_x, box_y, 160, 60)
        box_surf = pygame.Surface((160, 60), pygame.SRCALPHA)
        box_surf.fill((0, 0, 0, 180))
        screen.blit(box_surf, (box_x, box_y))

        # Tower info
        level_text = f"Lv.{tower.level} {tower.name[:10]}"
        surf = self._font_info.render(level_text, True, COLOR_WHITE)
        screen.blit(surf, (box_x + 4, box_y + 4))

        # Upgrade cost or max level
        defn = TOWER_DEFS[tower.type]
        if tower.level < 3:
            upgrade_cost = defn["upgrades"][tower.level - 1]["cost"]
            can_afford = self.economy.can_afford(upgrade_cost)
            color = COLOR_GOLD if can_afford else (150, 80, 80)
            upg_text = f"A: Upgrade {upgrade_cost}g"
            surf = self._font_info.render(upg_text, True, color)
        else:
            surf = self._font_info.render("MAX LEVEL", True, COLOR_ACCENT)
        screen.blit(surf, (box_x + 4, box_y + 22))

        # Sell value
        sell_text = f"Hold B: Sell {tower.sell_value()}g"
        surf = self._font_info.render(sell_text, True, (180, 140, 80))
        screen.blit(surf, (box_x + 4, box_y + 40))

    def _render_pause(self, screen):
        """Render the pause overlay on top of the game."""
        pause_items = ["Resume", "Quit to Title"]

        # Dark overlay
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # "PAUSED" title
        title_surf = self._font_pause_title.render("PAUSED", True, COLOR_WHITE)
        title_rect = title_surf.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 60))
        screen.blit(title_surf, title_rect)

        # Menu items
        for i, item in enumerate(pause_items):
            if i == self.pause_cursor_idx:
                prefix = "> "
                color = COLOR_ACCENT
            else:
                prefix = "  "
                color = COLOR_WHITE
            text_surf = self._font_pause_menu.render(prefix + item, True, color)
            text_rect = text_surf.get_rect(
                center=(SCREEN_W // 2, SCREEN_H // 2 + i * 40)
            )
            screen.blit(text_surf, text_rect)
