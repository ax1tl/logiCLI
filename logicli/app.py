"""The interactive application: app state plus the main key-handling loop."""

from __future__ import annotations

from pathlib import Path

import readchar
from rich.console import Console
from rich.layout import Layout
from rich.live import Live

from . import constants as C
from .board import Board
from .render import make_bottom_bar, make_stage, make_top_bar
from .ui import flash_message, prompt_input


def make_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="top_bar", size=3),
        Layout(name="stage", ratio=1),
        Layout(name="bottom_bar", size=3),
    )
    return layout


class App:
    def __init__(self) -> None:
        self.console = Console()
        self.layout = make_layout()
        self.board = Board.sized_for(self.console)
        self.current_file: Path | None = None
        self.is_modified = False
        self.grid_char = "\u00b7"  # ·

    # -- state changes -------------------------------------------------

    def toggle_grid(self) -> None:
        self.grid_char = " " if self.grid_char == "\u00b7" else "\u00b7"

    def new_project(self) -> None:
        self.board = Board.sized_for(self.console)
        self.current_file = None
        self.is_modified = False

    def save_as(self, live: Live) -> None:
        default_name = self.current_file.name if self.current_file else "untitled.lgc"
        result = prompt_input(live, self.layout, "Save as: ", default=default_name)
        if not result:
            return
        try:
            path = Path(result)
            self.board.save(path)
            self.current_file = path
            self.is_modified = False
        except OSError as e:
            flash_message(live, self.layout, f"Save failed: {e}")

    def load(self, live: Live) -> None:
        result = prompt_input(live, self.layout, "Load file: ")
        if not result:
            return
        path = Path(result)
        try:
            self.board = Board.load(path)
            self.current_file = path
            self.is_modified = False
        except (OSError, ValueError, KeyError) as e:
            flash_message(live, self.layout, f"Load failed: {e}")

    def confirm_new_project(self, live: Live) -> None:
        result = prompt_input(
            live,
            self.layout,
            "Create a new project? Unsaved changes will be lost. (y/n): ",
        )
        if result == "y":
            self.new_project()

    # -- rendering -------------------------------------------------------

    def refresh_layout(self) -> None:
        file_name = self.current_file.name if self.current_file else "untitled"
        self.layout["top_bar"].update(make_top_bar(file_name, self.is_modified))
        self.layout["stage"].update(make_stage(self.board, self.grid_char))
        self.layout["bottom_bar"].update(make_bottom_bar())

    # -- input -------------------------------------------------------------

    def handle_key(self, key: str, live: Live) -> bool:
        """Handle one keypress. Returns False if the app should exit."""
        if key == readchar.key.UP:
            self.board.move_cursor(-1, 0)
        elif key == readchar.key.DOWN:
            self.board.move_cursor(1, 0)
        elif key == readchar.key.LEFT:
            self.board.move_cursor(0, -1)
        elif key == readchar.key.RIGHT:
            self.board.move_cursor(0, 1)
        elif key in (readchar.key.BACKSPACE, readchar.key.DELETE):
            self.board.edit_cell(C.EMPTY)
            self.is_modified = True
        elif key == readchar.key.ESC:
            return False
        elif key == readchar.key.CTRL_S:
            self.save_as(live)
        elif key == "l":
            self.load(live)
        elif key == "N":
            self.confirm_new_project(live)
        elif key in ("e", "r"):
            self.board.rotate_cw()
        elif key == "q":
            self.board.rotate_ccw()
        elif key == "g":
            self.toggle_grid()
        elif key == readchar.key.ENTER:
            self.board.switch_trace()
        elif key in C.EDIT_KEY_MAP:
            self.board.edit_cell(C.EDIT_KEY_MAP[key])
            self.is_modified = True
        return True

    def run(self) -> None:
        self.refresh_layout()
        with Live(self.layout, console=self.console, screen=True, refresh_per_second=10) as live:
            try:
                running = True
                while running:
                    key = readchar.readkey()
                    running = self.handle_key(key, live)
                    self.refresh_layout()
            except KeyboardInterrupt:
                pass
