"""Static configuration: version string, gate glyphs/colors, and key bindings.

Nothing in this file has behavior of its own — it's all lookup tables that
board.py and render.py consult.
"""

VERSION = "v1.1.2"

# Chrome colors --------------------------------------------------------
COLOR_MAIN = "white"
COLOR_LITE = "bright_white"
TRACE_STYLE = "white"
DEFAULT_STYLE = ("#", "dark_red")

TOP_BAR_TEXT = "File | Edit | View | Help"
BOTTOM_BAR_TEXT = (
    "(i)nk | (a)nd | (o)r | (x)or | (n)ot | (b)uffer | (I)nput | (O)utput | "
    "(g)rid | (q) rotate (e) | (Enter) cycle cell | "
    "(Space) test mode | (s)ave | (l)oad | (m)odule | (p)lace | (N)ew | (Esc) exit"
)

# Gate ids ---------------------------------------------------------------
# Named instead of magic numbers so board.py and render.py read like English.
EMPTY = 0

BUFFER = 1
WIRE_X = 2          # ╳  crossing wire
WIRE_TR = 3         # ┐
WIRE_H = 5          # ─
WIRE_TL = 6         # ┌
WIRE_T_DOWN = 7     # ┬
WIRE_BR = 9         # ┘
WIRE_V = 10         # │
WIRE_T_LEFT = 11    # ┤
WIRE_BL = 12        # └
WIRE_T_UP = 13      # ┴
WIRE_T_RIGHT = 14   # ├
WIRE_CROSS = 15     # ┼
RESISTOR = 16
SWITCH = 17
AND = 18
OR = 19
NOT = 20
XOR = 21
INPUT = 22
INPUT_ACTIVE = 23
OUTPUT = 24
OUTPUT_ACTIVE = 25

CUSTOM_MODULE_WIDTH = 3
CUSTOM_MODULE_MIN_HEIGHT = 3
MAX_CUSTOM_MODULE_INPUTS = 8
CUSTOM_MODULE_COLOR = "color(213)"
CUSTOM_MODULE_STYLE = f"black on {CUSTOM_MODULE_COLOR}"

GATE_STYLE = {
    BUFFER: ("b", "black on red"),
    WIRE_X: ("╳", "white"),
    WIRE_TR: ("┐", "white"),
    WIRE_H: ("─", "white"),
    WIRE_TL: ("┌", "white"),
    WIRE_T_DOWN: ("┬", "white"),
    WIRE_BR: ("┘", "white"),
    WIRE_V: ("│", "white"),
    WIRE_T_LEFT: ("┤", "white"),
    WIRE_BL: ("└", "white"),
    WIRE_T_UP: ("┴", "white"),
    WIRE_T_RIGHT: ("├", "white"),
    WIRE_CROSS: ("┼", "white"),
    RESISTOR: ("r", "black on bright_red"),
    SWITCH: ("w", "black on blue"),
    AND: ("a", "black on yellow"),
    OR: ("o", "black on cyan"),
    NOT: ("n", "black on magenta"),
    XOR: ("x", "black on green"),
    INPUT: ("I", "white"),
    INPUT_ACTIVE: ("I", "black on white"),
    OUTPUT: ("O", "white"),
    OUTPUT_ACTIVE: ("O", "black on white"),
}

# Clockwise rotation of directional wire pieces (and its inverse)
ROTATE_CW_MAP = {
    WIRE_H: WIRE_V,
    WIRE_V: WIRE_H,
    WIRE_TR: WIRE_BR,
    WIRE_BR: WIRE_BL,
    WIRE_BL: WIRE_TL,
    WIRE_TL: WIRE_TR,
    WIRE_T_DOWN: WIRE_T_LEFT,
    WIRE_T_LEFT: WIRE_T_UP,
    WIRE_T_UP: WIRE_T_RIGHT,
    WIRE_T_RIGHT: WIRE_T_DOWN,
    WIRE_CROSS: WIRE_X,
    WIRE_X: WIRE_CROSS,
}
ROTATE_CCW_MAP = {v: k for k, v in ROTATE_CW_MAP.items()}

# Keyboard -> gate id placed in the current cell on an edit keypress
EDIT_KEY_MAP = {
    "b": BUFFER,
    "i": WIRE_H,
    "a": AND,
    "o": OR,
    "n": NOT,
    "x": XOR,
    "I": INPUT,
    "O": OUTPUT,
}
