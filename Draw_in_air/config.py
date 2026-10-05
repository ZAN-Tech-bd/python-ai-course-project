CAMERA_INDEX = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

RAINBOW = "rainbow"  # special "color" that cycles through every hue while drawing

# name, BGR color (keys 1-9 pick these in order)
# No black: the canvas treats black pixels as empty, so it would act like an eraser.
COLORS = [
    ("Red", (50, 50, 240)),
    ("Orange", (0, 150, 255)),
    ("Yellow", (0, 230, 255)),
    ("Green", (60, 200, 60)),
    ("Blue", (230, 110, 40)),
    ("Purple", (220, 80, 160)),
    ("Pink", (180, 105, 255)),
    ("White", (255, 255, 255)),
    ("Rainbow", RAINBOW),
]

BRUSH_SIZES = [6, 14, 26]
BRUSH_NAMES = ["Small", "Medium", "Big"]
DEFAULT_BRUSH_INDEX = 1
ERASER_SIZE = 50

# label shown on the button, tool id
TOOLS = [
    ("Pen", "pen"),
    ("Line", "line"),
    ("Box", "rectangle"),
    ("Circle", "circle"),
    ("Eraser", "eraser"),
]

HOVER_SELECT_TIME = 0.8  # seconds to dwell-hover a toolbar button to select it
NO_HAND_HINT_DELAY = 1.5  # seconds without a hand before showing "Show me your hand!"
SAVE_DIR = "saved_drawings"
