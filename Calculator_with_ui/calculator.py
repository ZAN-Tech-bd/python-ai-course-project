import pygame
import sys

pygame.init()

# ---------------------------------------------------------------------------
# Window setup
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 360, 582
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Calculator")
clock = pygame.time.Clock()

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
BG = (28, 28, 30)
DISPLAY_BG = (18, 18, 20)
TEXT_COLOR = (255, 255, 255)
SUB_TEXT_COLOR = (150, 150, 150)

NUM_BTN = (58, 58, 60)
NUM_BTN_HOVER = (78, 78, 80)
NUM_BTN_PRESS = (98, 98, 100)

OP_BTN = (255, 149, 0)
OP_BTN_HOVER = (255, 176, 63)
OP_BTN_PRESS = (204, 119, 0)

FUNC_BTN = (165, 165, 170)
FUNC_BTN_HOVER = (200, 200, 205)
FUNC_BTN_PRESS = (130, 130, 135)
FUNC_TEXT = (20, 20, 20)

ERROR_COLOR = (255, 90, 90)

FONT_DISPLAY = pygame.font.SysFont("Segoe UI", 56, bold=True)
FONT_SUB = pygame.font.SysFont("Segoe UI", 22)
FONT_BTN = pygame.font.SysFont("Segoe UI", 26)

# ---------------------------------------------------------------------------
# Button definition
# ---------------------------------------------------------------------------
class Button:
    def __init__(self, label, rect, kind="num"):
        self.label = label
        self.rect = pygame.Rect(rect)
        self.kind = kind  # "num", "op", "func"
        self.pressed = False

    def colors(self):
        if self.kind == "op":
            return OP_BTN, OP_BTN_HOVER, OP_BTN_PRESS, TEXT_COLOR
        elif self.kind == "func":
            return FUNC_BTN, FUNC_BTN_HOVER, FUNC_BTN_PRESS, FUNC_TEXT
        else:
            return NUM_BTN, NUM_BTN_HOVER, NUM_BTN_PRESS, TEXT_COLOR

    def draw(self, surface, mouse_pos):
        base, hover, press, text_color = self.colors()
        if self.pressed:
            color = press
        elif self.rect.collidepoint(mouse_pos):
            color = hover
        else:
            color = base

        pygame.draw.rect(surface, color, self.rect, border_radius=16)
        text_surf = FONT_BTN.render(self.label, True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
MARGIN = 12
GAP = 10
COLS = 4
ROWS = 5
btn_w = (WIDTH - 2 * MARGIN - (COLS - 1) * GAP) / COLS
btn_h = 70
grid_top = 170

layout = [
    ["C", "( )", "%", "/"],
    ["7", "8", "9", "*"],
    ["4", "5", "6", "-"],
    ["1", "2", "3", "+"],
    ["+/-", "0", ".", "="],
]

buttons = []
for r, row in enumerate(layout):
    for c, label in enumerate(row):
        x = MARGIN + c * (btn_w + GAP)
        y = grid_top + r * (btn_h + GAP)
        if label in ("/", "*", "-", "+", "="):
            kind = "op"
        elif label in ("C", "( )", "%", "+/-"):
            kind = "func"
        else:
            kind = "num"
        buttons.append(Button(label, (x, y, btn_w, btn_h), kind))

# ---------------------------------------------------------------------------
# Calculator state
# ---------------------------------------------------------------------------
expression = ""      # what the user is typing / building
result_text = ""      # last computed result (shown small above, or big on screen)
error = False
paren_open_count = 0

ALLOWED_CHARS = set("0123456789.+-*/()% ")


def safe_eval(expr):
    if not expr:
        return None
    cleaned = expr.replace("%", "/100")
    if not set(cleaned) <= ALLOWED_CHARS.union({"/"}):
        raise ValueError("invalid characters")
    return eval(cleaned, {"__builtins__": {}}, {})


def format_number(value):
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.8f}".rstrip("0").rstrip(".")
    return str(value)


def press_button(label):
    global expression, result_text, error, paren_open_count

    if error and label not in ("C",):
        expression = ""
        error = False

    if label == "C":
        expression = ""
        result_text = ""
        error = False
        paren_open_count = 0

    elif label == "( )":
        if paren_open_count == 0 or (expression and expression[-1] in "+-*/("):
            expression += "("
            paren_open_count += 1
        elif paren_open_count > 0:
            expression += ")"
            paren_open_count -= 1

    elif label == "+/-":
        # toggle sign of the current trailing number
        i = len(expression)
        while i > 0 and (expression[i - 1].isdigit() or expression[i - 1] == "."):
            i -= 1
        if i > 0 and expression[i - 1] == "-" and (i == 1 or expression[i - 2] in "+-*/("):
            expression = expression[: i - 1] + expression[i:]
        else:
            expression = expression[:i] + "-" + expression[i:]

    elif label == "=":
        try:
            value = safe_eval(expression)
            if value is None:
                return
            result_text = format_number(value)
            expression = result_text
            error = False
        except (ZeroDivisionError,):
            result_text = "Cannot divide by 0"
            expression = ""
            error = True
        except Exception:
            result_text = "Error"
            expression = ""
            error = True

    elif label in ("+", "-", "*", "/"):
        if expression and expression[-1] in "+-*/":
            expression = expression[:-1] + label
        elif expression or label == "-":
            expression += label

    elif label == ".":
        i = len(expression)
        while i > 0 and (expression[i - 1].isdigit() or expression[i - 1] == "."):
            i -= 1
        current_number = expression[i:]
        if "." not in current_number:
            expression += "."

    elif label == "%":
        if expression and (expression[-1].isdigit() or expression[-1] == ")"):
            expression += "%"

    else:  # digits
        if expression == "0":
            expression = label
        else:
            expression += label


def handle_key(event):
    key = event.key
    unicode_char = event.unicode

    if key == pygame.K_RETURN or key == pygame.K_EQUALS or key == pygame.K_KP_EQUALS:
        press_button("=")
    elif key == pygame.K_BACKSPACE:
        global expression, error
        if error:
            expression = ""
            error = False
        else:
            expression = expression[:-1]
    elif key == pygame.K_ESCAPE:
        press_button("C")
    elif unicode_char in "0123456789":
        press_button(unicode_char)
    elif unicode_char == ".":
        press_button(".")
    elif unicode_char in "+-*/":
        press_button(unicode_char)
    elif unicode_char == "%":
        press_button("%")
    elif unicode_char in "()":
        press_button("( )")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def draw_display():
    display_rect = pygame.Rect(MARGIN, 30, WIDTH - 2 * MARGIN, 120)
    pygame.draw.rect(screen, DISPLAY_BG, display_rect, border_radius=18)

    color = ERROR_COLOR if error else TEXT_COLOR
    shown = result_text if error else (expression if expression else "0")

    # shrink font if text too long
    font = FONT_DISPLAY
    max_width = display_rect.width - 30
    text_surf = font.render(shown, True, color)
    if text_surf.get_width() > max_width:
        font = pygame.font.SysFont("Segoe UI", 38, bold=True)
        text_surf = font.render(shown, True, color)
        if text_surf.get_width() > max_width:
            font = pygame.font.SysFont("Segoe UI", 26, bold=True)
            text_surf = font.render(shown, True, color)

    text_rect = text_surf.get_rect(bottomright=(display_rect.right - 20, display_rect.bottom - 15))
    screen.blit(text_surf, text_rect)

    if not error and result_text and expression != result_text:
        sub_surf = FONT_SUB.render(result_text, True, SUB_TEXT_COLOR)
        sub_rect = sub_surf.get_rect(topright=(display_rect.right - 20, display_rect.top + 12))
        screen.blit(sub_surf, sub_rect)


def main():
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for btn in buttons:
                    if btn.is_clicked(event.pos):
                        btn.pressed = True

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                for btn in buttons:
                    if btn.pressed and btn.is_clicked(event.pos):
                        press_button(btn.label)
                    btn.pressed = False

            elif event.type == pygame.KEYDOWN:
                handle_key(event)

        screen.fill(BG)
        draw_display()
        for btn in buttons:
            btn.draw(screen, mouse_pos)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
