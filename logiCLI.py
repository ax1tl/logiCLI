import time
from pathlib import Path

import readchar
from rich import box
from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

ver = "v0.1.1"

console = Console()
layout = Layout()
clrMain = "bright_black"
clrLite = "white"

layout.split_column(
    Layout(name="top_bar", size=3),
    Layout(name="stage", ratio=1),
    Layout(name="bottom_bar", size=3),
)

gates = []

# init board
def get_board_dims() -> tuple[int, int]:
    width, height = console.size
    # stage panel has a 1-char border on each side; top/bottom bars take 3 rows each
    usable_width = width - 3
    usable_height = height - 2 - 3 - 3
    # each cell renders as 2 chars wide (char + connector/space), 1 row tall
    board_cols = max(1, usable_width // 2)
    board_rows = max(1, usable_height)
    return board_rows, board_cols

rows, cols = get_board_dims()
board = [[0 for _ in range(cols)] for _ in range(rows)]

topBarText = "File | Edit | View | Help"
bottomBarText = ("["+clrMain+"]"+"["+clrLite+"]i[/"+clrLite+"]nk")

cursor_row = 0
cursor_col = 0

# key -> gate id this key writes into the current cell
EDIT_KEY_MAP = {
    "i":  5,
    "r": 16,
    "w": 17,
    "a": 18,
    "o": 19,
    "n": 20,
    "x": 21,
    "I": 22,
    "O": 24,
}

clock = time.strftime("%H:%M:%S")
topTable = Table.grid(expand=True)
topTable.add_column(justify="left")
topTable.add_column(justify="right")
topTable.add_row(topBarText, Text(clock, style=clrLite))

def make_top_bar(file_name: str = "untitled", modified: bool = False) -> Panel:
    mod_flag = "*" if modified else ""
    return Panel(
        topTable,
        border_style=clrMain,
        box=box.ROUNDED,
        title=f"logiCLI - {file_name}{mod_flag} {ver}",
        title_align="left",
    )

def make_bottom_bar() -> Panel:
    return Panel(
        bottomBarText,
        border_style=clrMain,
        box=box.ROUNDED,
        title="Controls",
        title_align="left",
    )

grid = "·"

GATE_STYLE = {
    0:  (grid,"dim"),
    #1:  ("#",""),
   #2:  ("#",""),
    3:  ("╗","white"),
    #4:  ("#",""),
    5:  ("═","white"),
    6:  ("╔","white"),
    7:  ("╦","white"),
    #8:  ("#",""),
    9:  ("╝","white"),
    10: ("║","white"),
    11: ("╣","white"),
    12: ("╚","white"),
    13: ("╩","white"),
    14: ("╠","white"),
    15: ("╬","white"),
    16: ("r","black on bright_red"),
    17: ("w","black on blue"),
    18: ("a","black on yellow"),
    19: ("o","black on cyan"),
    20: ("n","black on magenta"),
    21: ("x","black on green"),
    22: ("I","white"),
    23: ("I","black on white"),
    24: ("O","white"),
    25: ("O","black on white")
}
ROTATE_CW_MAP = {
    5:  10,
    10:  5,
    3:   9,
    9:  12,
    12:  6,
    6:   3,
    7:  11,
    11: 13,
    13: 14,
    14:  7
}
DEFAULT_STYLE = ("#", "dark_red")

TRACE_STYLE = "white"


def invert_style(style: str) -> str:
    # appends the "reverse" attribute, which swaps fg/bg at render time
    return f"{style} reverse" if style else "reverse"


def render_board() -> Text:
    out = Text()
    for r, row in enumerate(board):
        for c, cell in enumerate(row):
            next_cell = row[c + 1] if c + 1 < len(row) else None
            is_traced = next_cell is not None and (
                (cell in (5, 6, 7, 12, 13, 14, 15))
                and ((16 <= next_cell <= 25) or (3 <= next_cell <= 15 and next_cell % 2 == 1))
            )
            char, style = GATE_STYLE.get(cell, DEFAULT_STYLE)

            if r == cursor_row and c == cursor_col:
                style = invert_style(style)

            out.append(char, style=style)
            out.append("═" if is_traced else " ", style=TRACE_STYLE if is_traced else style)
        out.append("\n")
    return out


def make_stage() -> Panel:
    rendered_board = render_board()
    return Panel(rendered_board, border_style=clrMain, box=box.ROUNDED)

def update_layout(file_name: str = "untitled", modified: bool = False) -> None:
    layout["top_bar"].update(make_top_bar(file_name, modified))
    layout["stage"].update(make_stage())
    layout["bottom_bar"].update(make_bottom_bar())


def move_cursor(d_row: int, d_col: int) -> None:
    global cursor_row, cursor_col
    cursor_row = max(0, min(rows - 1, cursor_row + d_row))
    cursor_col = max(0, min(cols - 1, cursor_col + d_col))

def toggle_grid() -> None:
    global grid
    grid = " " if grid == "·" else "·"
    update_layout(modified=True)

def edit_cell(gate_id: int) -> None:
    board[cursor_row][cursor_col] = gate_id

def switch_trace() -> None:
    board_cell = board[cursor_row][cursor_col]
    if board_cell in (22, 24):
        board_cell += 1
    elif board_cell in (23, 25):
        board_cell -= 1

    elif board_cell in (5, 10):
        board[cursor_row][cursor_col] = 3
    elif board_cell in (3, 6, 9, 12):
        board[cursor_row][cursor_col] = 7
    elif board_cell in (7, 11, 13, 14):
            board[cursor_row][cursor_col] = 15
    elif board_cell == 15:
        board[cursor_row][cursor_col] = 5



def rotate_trace_cw() -> None:
    board_cell = board[cursor_row][cursor_col]
    if board_cell in ROTATE_CW_MAP:
        board[cursor_row][cursor_col] = ROTATE_CW_MAP[board_cell]

def rotate_trace_ccw() -> None:
    board_cell = board[cursor_row][cursor_col]
    if board_cell in ROTATE_CW_MAP:
        # find the key in ROTATE_CW_MAP that has the value of board_cell
        for k, v in ROTATE_CW_MAP.items():
            if v == board_cell:
                board[cursor_row][cursor_col] = k
                break

    

update_layout()

with Live(layout, console=console, screen=True, refresh_per_second=10) as live:
    try:
        while True:
            clock = time.strftime("%H:%M:%S")
            key = readchar.readkey()
            if key == readchar.key.UP:
                move_cursor(-1, 0)
            elif key == readchar.key.DOWN:
                move_cursor(1, 0)
            elif key == readchar.key.LEFT:
                move_cursor(0, -1)
            elif key == readchar.key.RIGHT:
                move_cursor(0, 1)
            elif key in (readchar.key.BACKSPACE, readchar.key.DELETE):
                edit_cell(0)
            elif key == readchar.key.ESC:
                break
            elif key == "s":
                # save to file
                pass
            elif key == "l":
                # load from file
                pass
            elif key == "e":
                rotate_trace_cw()
            elif key == "q":
                rotate_trace_ccw()
            elif key == "g":
                toggle_grid()
            elif key == readchar.key.ENTER:
                switch_trace()
            elif key in EDIT_KEY_MAP:
                edit_cell(EDIT_KEY_MAP[key])

            update_layout(modified=True)
    except KeyboardInterrupt:
        pass