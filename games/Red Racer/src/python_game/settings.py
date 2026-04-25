import os

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
PURPLE = (128, 0, 128)
GRAY = (100, 100, 100)

# Game Constants
FPS = 60
PLAYER_SPEED = 7
ENEMY_SPEED_INITIAL = 5
FUEL_DECREASE_RATE = 0.5
FUEL_MAX = 100

# Difficulty Settings
PLAYER_MAX_HEALTH = 100
COLLISION_DAMAGE = 30
REPAIR_HEAL_AMOUNT = 15
HEALTH_BAR_COLOR = (0, 255, 0)
DAMAGE_COLOR = (255, 0, 0)

# Road Boundaries (Defaults)
ROAD_LEFT = 130
ROAD_RIGHT = 670

# Road Configuration (Image Name -> (Left Boundary, Right Boundary))
# Calculated based on user-provided road width vs image width ratios scaled to 800px screen.
ROAD_CONFIGS = {
    "Road.png": (261, 539),       # Ratio: 355/1024 -> 277px wide
    "Road2.png": (289, 511),      # Ratio: 175/632 -> 221px wide (Result is narrow!)
    "Road3.png": (277, 523),      # Ratio: 315/1024 -> 246px wide
    "Road4.png": (220, 580),      # Ratio: 115/256 -> 359px wide
}

# Paths
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "python_game")
BACKGROUND_IMG = os.path.join(ASSETS_DIR, "Road.png")
PLAYER_IMG_DEFAULT = os.path.join(ASSETS_DIR, "Felucia.png") 

# Audio Paths — prototype reference audio removed from the repository;
# leave as None so the audio-availability check in main.py falls through.
MENU_MUSIC_PATH = None
GAME_SOUND_PATH = None

# Enemy Images List
POSSIBLE_ENEMIES = ["Aurion.png", "Vyrex.png", "Lumbra.png", "Suprex.png", "CXR.png"]

# Shield pickup
SHIELD_DURATION = 3.0  # seconds

# Score multiplier pickup
SCORE_MULT_PICKUP_DURATION = 5.0  # seconds
SCORE_MULT_PICKUP_BONUS = 1.0  # +1x added to current multiplier
