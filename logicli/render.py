"""Turning a Board (and the surrounding app chrome) into Rich renderables."""

from __future__ import annotations

import time

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import constants as C
from .board import Board, module_height

# Cells whose right edge draws a connecting "─" into the next cell, when the
# next cell continues the trace (see _is_trace_continuation below).
_TRACE_SOURCES = {
    C.WIRE_X, C.WIRE_H, C.WIRE_TL, C.WIRE_T_DOWN,
    C.WIRE_BL, C.WIRE_T_UP, C.WIRE_T_RIGHT, C.WIRE_CROSS,
}


def _is_trace_continuation(next_cell: int) -> bool:
    if 16 <= next_cell <= 25:
        return True
    if 2 <= next_cell <= 15:
        return next_cell % 2 == 1 or next_cell == C.WIRE_X
    return False


def invert_style(style: str) -> str:
    """Swap fg/bg by appending Rich's 'reverse' attribute."""
    return f"{style} reverse" if style else "reverse"


def render_board(board: Board, grid_char: str, simulation: dict | None = None) -> Text:
    out = Text()
    simulation = simulation or {}
    powered_wires = simulation.get("wires", set())
    powered_outputs = simulation.get("outputs", {})
    input_states = simulation.get("inputs", {})
    module_cells: dict[tuple[int, int], str] = {}
    for module in board.modules:
        row, col = module["row"], module["col"]
        height = module_height(module)
        for d_row in range(height):
            for d_col in range(C.CUSTOM_MODULE_WIDTH):
                module_cells[(row + d_row, col + d_col)] = "  "
        for input_index in range(len(module["inputs"])):
            module_cells[(row + input_index, col)] = "I "
        for output_index in range(len(module["outputs"])):
            module_cells[(row + output_index, col + C.CUSTOM_MODULE_WIDTH - 1)] = "O "
        module_cells[(row + height // 2, col + 1)] = f"{module['name'][:2].upper():<2}"

    for r, row in enumerate(board.cells):
        for c, cell in enumerate(row):
            next_cell = row[c + 1] if c + 1 < len(row) else None
            is_traced = (
                next_cell is not None
                and (r, c) not in module_cells
                and (r, c + 1) not in module_cells
                and cell in _TRACE_SOURCES
                and _is_trace_continuation(next_cell)
            )
            if (r, c) in module_cells:
                char, style = module_cells[(r, c)], C.CUSTOM_MODULE_STYLE
            else:
                if cell in (C.OUTPUT, C.OUTPUT_ACTIVE):
                    cell = C.OUTPUT_ACTIVE if powered_outputs.get((r, c), False) else C.OUTPUT
                elif cell in (C.INPUT, C.INPUT_ACTIVE) and (r, c) in input_states:
                    cell = C.INPUT_ACTIVE if input_states[(r, c)] else C.INPUT
                glyph, style = (
                    (grid_char, C.COLOR_MAIN) if cell == C.EMPTY
                    else C.GATE_STYLE.get(cell, C.DEFAULT_STYLE)
                )
                if (r, c) in powered_wires:
                    style = "yellow"
                char = glyph

            if r == board.cursor_row and c == board.cursor_col:
                style = invert_style(style)

            out.append(char, style=style)
            if (r, c) not in module_cells:
                trace_style = "yellow" if (r, c) in powered_wires else C.TRACE_STYLE
                out.append("─" if is_traced else " ", style=trace_style if is_traced else style)
        out.append("\n")
    return out


def make_top_bar(file_name: str = "untitled", modified: bool = False, c_x: int = 0, c_y: int = 0) -> Panel:
    mod_flag = "*" if modified else ""
    coords = f"x: {c_x}\ty: {c_y}"
    top_table = Table.grid(expand=True)
    top_table.add_column(justify="left")
    top_table.add_column(justify="right")
    top_table.add_row(C.TOP_BAR_TEXT, Text(coords, style=C.COLOR_LITE))
    return Panel(
        top_table,
        border_style=C.COLOR_MAIN,
        box=box.ROUNDED,
        title=f"logiCLI - {file_name}{mod_flag} {C.VERSION}",
        title_align="left",
    )


def make_bottom_bar(test_mode: bool = False) -> Panel:
    controls = (
        "(arrows) move | (Enter) toggle input | (Space) edit mode | (Esc) exit"
        if test_mode
        else C.BOTTOM_BAR_TEXT
    )
    return Panel(
        controls,
        border_style=C.COLOR_MAIN,
        box=box.ROUNDED,
        title="Controls",
        title_align="left",
    )


def make_stage(board: Board, grid_char: str, simulation: dict | None = None) -> Panel:
    return Panel(render_board(board, grid_char, simulation), border_style=C.COLOR_MAIN, box=box.ROUNDED)
