"""Global configuration and data tables for Plants vs Zombies."""

import os

# ── Display ───────────────────────────────────────────────────────────
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
TITLE = "Plants vs Zombies"

# ── Paths ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_DIR = os.path.join(BASE_DIR, "resources")

# ── Grid (5 rows × 9 columns) ────────────────────────────────────────
GRID_ROWS = 5
GRID_COLS = 9
GRID_X_START = 35       # left edge of column 0
GRID_Y_START = 90       # top edge of row 0
CELL_WIDTH = 80
CELL_HEIGHT = 100

# ── Card Bar ──────────────────────────────────────────────────────────
CARD_BAR_X = 13
CARD_BAR_Y = 6
CARD_WIDTH = 53
CARD_HEIGHT = 71
CARD_GAP = 1            # horizontal gap between cards
SUN_COUNTER_X = 13
SUN_COUNTER_Y = 57

# ── Economy ───────────────────────────────────────────────────────────
INITIAL_SUN = 50
SKY_SUN_MIN_INTERVAL = 10.0   # seconds
SKY_SUN_MAX_INTERVAL = 25.0
SUN_VALUE = 25
SUN_FALL_SPEED = 60           # pixels per second
SUN_COLLECT_SPEED = 400       # pixels per second when flying to counter
SUN_LIFETIME = 8.0            # seconds before disappearing if not collected

# ── Plant Definitions ─────────────────────────────────────────────────
PLANT_DEFS = {
    "Peashooter": {
        "cost": 100,
        "cooldown": 7.5,       # seconds
        "hp": 300,
        "anim_folder": "Plants/Peashooter",
        "anim_fps": 12,
        "card_image": "Cards/card_peashooter.png",
    },
    "SunFlower": {
        "cost": 50,
        "cooldown": 7.5,
        "hp": 300,
        "anim_folder": "Plants/SunFlower",
        "anim_fps": 12,
        "card_image": "Cards/card_sunflower.png",
    },
    "WallNut": {
        "cost": 50,
        "cooldown": 30.0,
        "hp": 4000,
        "anim_folder": "Plants/WallNut/WallNut",
        "anim_fps": 12,
        "card_image": "Cards/card_wallnut.png",
    },
}

# Card order in the bar
CARD_ORDER = ["Peashooter", "SunFlower", "WallNut"]

# ── Colors ────────────────────────────────────────────────────────────
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)
DARK_OVERLAY = (0, 0, 0, 150)
CD_OVERLAY_COLOR = (0, 0, 0, 140)
