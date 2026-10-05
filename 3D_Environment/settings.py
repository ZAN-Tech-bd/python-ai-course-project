"""Central tuning constants for the open-world game."""

# --- City layout ---
BLOCKS_PER_SIDE = 5          # NxN grid of city blocks
BLOCK_SIZE = 18              # building footprint area per block
ROAD_WIDTH = 8                # full road width between blocks
SIDEWALK_MARGIN = 2           # pavement margin left visible beside the dark road
PITCH = BLOCK_SIZE + ROAD_WIDTH
CITY_SPAN = BLOCKS_PER_SIDE * PITCH
HALF_CITY = CITY_SPAN / 2

# --- Player ---
PLAYER_WALK_SPEED = 4.5
PLAYER_RUN_SPEED = 9.0
PLAYER_JUMP_HEIGHT = 1.6
PLAYER_RADIUS = 0.4
PLAYER_MAX_STAMINA = 100
STAMINA_DRAIN = 28          # per second while sprinting
STAMINA_REGEN = 16          # per second while not sprinting
PLAYER_MAX_HEALTH = 100

# --- Vehicle ---
CAR_MAX_SPEED = 26
CAR_REVERSE_SPEED = 8
CAR_ACCEL = 10
CAR_BRAKE = 22
CAR_DRAG = 6
CAR_TURN_SPEED = 90          # degrees/sec at full speed factor
CAR_RADIUS = 1.6
ENTER_EXIT_RANGE = 3.2

# --- Camera ---
CAM_DISTANCE_WALK = 6.0
CAM_HEIGHT_WALK = 2.4
CAM_DISTANCE_CAR = 8.5
CAM_HEIGHT_CAR = 3.2
MOUSE_SENSITIVITY = 40

# --- Day/night cycle ---
DAY_LENGTH_SECONDS = 240      # full day/night cycle length

# --- Mission ---
MISSION_RADIUS = 3.0
MISSION_REWARD = 150

# --- Colors (roughly GTA-ish palette) ---
BUILDING_PALETTE = [
    (0.55, 0.58, 0.62),
    (0.62, 0.5, 0.42),
    (0.35, 0.4, 0.48),
    (0.7, 0.65, 0.55),
    (0.45, 0.45, 0.5),
    (0.5, 0.35, 0.32),
]

KEYBINDS_HELP = [
    "WASD - Move / Drive",
    "Shift - Sprint",
    "Space - Jump",
    "Mouse - Look around",
    "E - Enter / Exit vehicle",
    "Esc - Pause menu",
    "H - Toggle this help",
    "M - Toggle minimap size",
    "F11 - Toggle fullscreen",
]
