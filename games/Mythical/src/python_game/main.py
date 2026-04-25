"""
MYTHICAL — A Retro Fantasy Adventure
Pygame prototype designed for eventual GBA port.
"""

import pygame
import sys
from settings import *
from ai.config_loader import (
    get_default_difficulty,
    get_difficulty_config,
    normalize_difficulty,
)
from runtime.frame_clock import advance_time, reset_time
from runtime import create_runtime
from states.state_machine import StateMachine
from states.title import TitleState
from states.gameplay import GameplayState
from states.pause import PauseState
from states.game_over import GameOverState
from states.inventory_screen import InventoryScreenState
from states.victory import VictoryState
from states.instructions import InstructionsState
from states.skill_screen import SkillScreenState
from inventory import Inventory
from quest import QuestManager
from save_manager import (
    build_save_data,
    load_progression,
    load_reputation,
    load_bestiary,
    load_consequence_state,
    load_fast_travel,
    load_weather,
    load_inventory,
    load_killed_animals,
    load_campaign,
    sanitize_loaded_save,
)
from wallet import Wallet
from progression import Progression
from reputation import Reputation
from bestiary import Bestiary
from campaign import Campaign
from consequence_system import ConsequenceState
from states.stage_intro import StageIntroState
from states.bestiary_screen import BestiaryScreenState


class Game:
    def __init__(self, runtime=None):
        self.runtime = runtime or create_runtime()
        self.target_profile = self.runtime.profile
        self.screen_size = (
            self.target_profile.screen_width,
            self.target_profile.screen_height,
        )
        reset_time()
        self.screen, self.clock = self.runtime.boot(GAME_TITLE, self.screen_size)
        self.running = True

        self.input = self.runtime.create_input()
        self.audio = self.runtime.create_audio()
        self.difficulty_mode = get_default_difficulty()
        self.difficulty_config = get_difficulty_config(self.difficulty_mode)

        # Shared game state
        self.inventory = Inventory()
        self.quest_manager = QuestManager()
        self.wallet = Wallet()
        # v4 systems
        self.progression = Progression()
        self.reputation = Reputation()
        self.bestiary = Bestiary()
        # v5: campaign stage
        self.campaign = Campaign()

        # State machine
        self.states = StateMachine()
        self.states.register("title", TitleState(self))
        self.states.register("gameplay", GameplayState(self))
        self.states.register("pause", PauseState(self))
        self.states.register("game_over", GameOverState(self))
        self.states.register("inventory", InventoryScreenState(self))
        self.states.register("victory", VictoryState(self))
        self.states.register("instructions", InstructionsState(self))
        self.states.register("skill_screen", SkillScreenState(self))
        self.states.register("stage_intro", StageIntroState(self))
        self.states.register("bestiary", BestiaryScreenState(self))
        self.states.change("title")

    def set_difficulty(self, mode: str | None):
        self.difficulty_mode = normalize_difficulty(mode)
        self.difficulty_config = get_difficulty_config(self.difficulty_mode)

    @property
    def difficulty_label(self) -> str:
        return self.difficulty_config.get("label", self.difficulty_mode.title())

    def cycle_difficulty(self, delta: int):
        order = ["easy", "normal", "hard"]
        current = (
            self.difficulty_mode
            if self.difficulty_mode in order
            else get_default_difficulty()
        )
        idx = order.index(current)
        self.set_difficulty(order[(idx + delta) % len(order)])

    def start_new_game(self, difficulty_mode: str | None = None):
        """Reset everything and start fresh."""
        self.set_difficulty(difficulty_mode or self.difficulty_mode)
        self.inventory = Inventory()
        self.quest_manager = QuestManager()
        self.wallet = Wallet()
        self.progression = Progression()
        self.reputation = Reputation()
        self.bestiary = Bestiary()
        self.consequence_state = ConsequenceState()
        self.campaign = Campaign()
        gameplay = GameplayState(self)
        self.states.register("gameplay", gameplay)
        self.states.register("victory", VictoryState(self))
        self.states.register("stage_intro", StageIntroState(self))
        self.states.register("skill_screen", SkillScreenState(self))
        self.states.change("gameplay")

    def load_saved_game(self):
        """Load from save file (supports v3 and v4 formats)."""
        raw_data = self.runtime.load_save()
        if not raw_data:
            self.start_new_game()
            return
        data = sanitize_loaded_save(raw_data)
        if data != raw_data:
            self.runtime.write_save(data)
        self.set_difficulty(data.get("difficulty", get_default_difficulty()))
        # Restore inventory (v4 dict or v3 flat list)
        self.inventory = load_inventory(data)
        self.wallet = Wallet(data.get("coins", 0))
        # Restore quests
        self.quest_manager = QuestManager()
        for qid, qdata in data.get("quest_stages", {}).items():
            q = self.quest_manager.get_quest(qid)
            if q:
                q.stage = qdata["stage"]
                q.complete = qdata["complete"]
        # v4 systems
        self.progression = load_progression(data)
        self.reputation = load_reputation(data)
        self.bestiary = load_bestiary(data)
        self.consequence_state = load_consequence_state(data)
        # v5: campaign
        self.campaign = load_campaign(data)
        # Create gameplay with saved state
        gameplay = GameplayState(self)
        gameplay.apply_save_data(data)
        # Restore fast-travel and weather into gameplay systems
        gameplay.fast_travel_mgr = load_fast_travel(data)
        gameplay.weather = load_weather(
            data,
            viewport_width=self.target_profile.screen_width,
            viewport_height=self.target_profile.screen_height,
        )
        # Restore killed animals into the spawner
        killed_animals = load_killed_animals(data)
        if hasattr(gameplay, "animal_spawner"):
            gameplay.animal_spawner._killed_ids = killed_animals
        self.states.register("gameplay", gameplay)
        self.states.register("victory", VictoryState(self))
        self.states.register("stage_intro", StageIntroState(self))
        self.states.register("skill_screen", SkillScreenState(self))
        self.states.change("gameplay")

    def retry_from_checkpoint(self):
        gameplay = self.states._states.get("gameplay")
        if (
            gameplay
            and hasattr(gameplay, "restore_checkpoint")
            and gameplay.restore_checkpoint()
        ):
            self.states.change("gameplay")
            return
        self.start_new_game(self.difficulty_mode)

    def has_saved_game(self) -> bool:
        return bool(self.runtime.save_exists())

    def save_current_game(self) -> bool:
        """Save current state (v4 format). Returns True on success."""
        gs = self.states._states.get("gameplay")
        if gs and hasattr(gs, "get_save_data"):
            sd = gs.get_save_data()
            data = build_save_data(
                gs.player,
                self.inventory,
                self.quest_manager,
                sd["map"],
                sd["opened_chests"],
                sd["collected_items"],
                sd["defeated_boss"],
                difficulty_mode=self.difficulty_mode,
                coins=self.wallet.coins,
                defeated_enemies=sd.get("defeated_enemies", []),
                dynamic_drops=sd.get("dynamic_drops", []),
                boss_state=sd.get("boss_state", {}),
                # v4 systems
                progression=getattr(self, "progression", None),
                reputation=getattr(self, "reputation", None),
                bestiary=getattr(self, "bestiary", None),
                consequence_state=getattr(self, "consequence_state", None),
                fast_travel=getattr(gs, "fast_travel_mgr", None),
                weather=getattr(gs, "weather", None),
                killed_animals=(
                    gs.animal_spawner.collect_killed_ids()
                    if hasattr(gs, "animal_spawner")
                    else set()
                ),
                # v5: campaign
                campaign=getattr(self, "campaign", None),
            )
            return bool(self.runtime.write_save(data))
        return False

    def run(self):
        accumulator = 0.0
        while self.running:
            dt = self.runtime.tick(self.clock, TARGET_FPS)
            if dt > MAX_DT:
                dt = MAX_DT
            advance_time(dt)
            accumulator += dt

            self.input.update()
            for event in self.runtime.poll_events():
                if getattr(event, "type", None) == pygame.QUIT:
                    self.running = False
                self.runtime.route_input_event(self.input, event)

            while accumulator >= FIXED_DT:
                self.states.update(FIXED_DT)
                accumulator -= FIXED_DT

            self.screen.fill(COLOR_BG)
            self.states.render(self.screen)
            self.runtime.present()

        self.runtime.shutdown()
        sys.exit()


if __name__ == "__main__":
    import os

    if os.environ.get("MYTHICAL_DEV_MODE") == "1":
        print("Dev mode active: Auto-compiling assets...")
        from tools.compile_assets import main as compile_main

        compile_main()
    Game().run()
