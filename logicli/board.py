"""Board state: the grid of gate cells, the cursor, and persistence."""

from __future__ import annotations

import json
from pathlib import Path

from . import constants as C

# switch_trace() cycles a cell through these forms, in this order:
#   (─ or │) -> ┐/┌/┘/└ -> ┬/┤/┴/├ -> ┼ -> back to ─
SWITCH_TRACE_MAP = {
    C.WIRE_H: C.WIRE_TR, C.WIRE_V: C.WIRE_TR,
    C.WIRE_TR: C.WIRE_T_DOWN, C.WIRE_TL: C.WIRE_T_DOWN,
    C.WIRE_BR: C.WIRE_T_DOWN, C.WIRE_BL: C.WIRE_T_DOWN,
    C.WIRE_T_DOWN: C.WIRE_CROSS, C.WIRE_T_LEFT: C.WIRE_CROSS,
    C.WIRE_T_UP: C.WIRE_CROSS, C.WIRE_T_RIGHT: C.WIRE_CROSS,
    C.WIRE_CROSS: C.WIRE_H,
}
# switch_trace() also toggles I/O cells between their idle and active glyphs
IO_TOGGLE = {
    C.INPUT: C.INPUT_ACTIVE, C.INPUT_ACTIVE: C.INPUT,
    C.OUTPUT: C.OUTPUT_ACTIVE, C.OUTPUT_ACTIVE: C.OUTPUT,
}


def compute_board_dims(width: int, height: int) -> tuple[int, int]:
    """How many board rows/cols fit in a terminal of the given size.

    The stage panel has a 1-char border on each side, and the top/bottom
    bars each take 3 rows. Each cell renders as 2 characters wide, 1 row tall.
    """
    usable_width = width - 3
    usable_height = height - 2 - 3 - 3
    cols = max(1, usable_width // 2)
    rows = max(1, usable_height)
    return rows, cols


class Board:
    """A grid of gate-id cells plus the cursor position within it."""

    def __init__(self, rows: int, cols: int):
        self.rows = rows
        self.cols = cols
        self.cells = [[C.EMPTY for _ in range(cols)] for _ in range(rows)]
        self.cursor_row = 0
        self.cursor_col = 0

    @classmethod
    def sized_for(cls, console) -> "Board":
        """Create a fresh, empty board sized to fit a Rich console."""
        rows, cols = compute_board_dims(*console.size)
        return cls(rows, cols)

    @property
    def cursor_cell(self) -> int:
        return self.cells[self.cursor_row][self.cursor_col]

    @cursor_cell.setter
    def cursor_cell(self, gate_id: int) -> None:
        self.cells[self.cursor_row][self.cursor_col] = gate_id

    def move_cursor(self, d_row: int, d_col: int) -> None:
        self.cursor_row = max(0, min(self.rows - 1, self.cursor_row + d_row))
        self.cursor_col = max(0, min(self.cols - 1, self.cursor_col + d_col))

    def edit_cell(self, gate_id: int) -> None:
        self.cursor_cell = gate_id

    def switch_trace(self) -> None:
        """Cycle the cell under the cursor to its next wire/I-O form."""
        cell = self.cursor_cell
        if cell in IO_TOGGLE:
            self.cursor_cell = IO_TOGGLE[cell]
        elif cell in SWITCH_TRACE_MAP:
            self.cursor_cell = SWITCH_TRACE_MAP[cell]

    def rotate_cw(self) -> None:
        cell = self.cursor_cell
        if cell in C.ROTATE_CW_MAP:
            self.cursor_cell = C.ROTATE_CW_MAP[cell]

    def rotate_ccw(self) -> None:
        cell = self.cursor_cell
        if cell in C.ROTATE_CCW_MAP:
            self.cursor_cell = C.ROTATE_CCW_MAP[cell]

    # -- persistence -------------------------------------------------

    def to_dict(self) -> dict:
        return {"rows": self.rows, "cols": self.cols, "board": self.cells}

    @classmethod
    def from_dict(cls, data: dict) -> "Board":
        board = cls(data["rows"], data["cols"])
        board.cells = data["board"]
        return board

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict()))

    @classmethod
    def load(cls, path: Path) -> "Board":
        data = json.loads(path.read_text())
        return cls.from_dict(data)
