GESTURE_DRAW = "draw"          # index finger only -> draw / move cursor
GESTURE_SELECT = "select"      # index + middle -> hover / select toolbar, pen-up
GESTURE_PALM = "palm"          # open hand -> idle
GESTURE_FIST = "fist"          # closed hand -> idle
GESTURE_UNKNOWN = "unknown"


def classify(fingers):
    thumb, index, middle, ring, pinky = fingers

    if index and not middle and not ring and not pinky:
        return GESTURE_DRAW
    if index and middle and not ring and not pinky:
        return GESTURE_SELECT
    if thumb and index and middle and ring and pinky:
        return GESTURE_PALM
    if not any(fingers):
        return GESTURE_FIST
    return GESTURE_UNKNOWN
