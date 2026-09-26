"""The interactive application: app state plus the main key-handling loop."""

from __future__ import annotations

from pathlib import Path

import readchar
from rich.console import Console
from rich.layout import Layout
from rich.live import Live

from . import constants as C
from .board import Board
from .custom_modules import (
    CircuitError,
    formulas_for_board,
    load_custom_module,
    save_custom_module,
    simulate_board,
)
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
        self.test_mode = False
        self.test_inputs: dict[tuple[int, int], bool] = {}
        self.simulation: dict | None = None

    # -- state changes -------------------------------------------------

    def toggle_grid(self) -> None:
        self.grid_char = " " if self.grid_char == "\u00b7" else "\u00b7"

    def new_project(self) -> None:
        self.board = Board.sized_for(self.console)
        self.current_file = None
        self.is_modified = False
        self.test_mode = False
        self.test_inputs = {}
        self.simulation = None

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
            self.test_mode = False
            self.test_inputs = {}
            self.simulation = None
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

    def save_as_custom_gate(self, live: Live) -> None:
        try:
            formulas, inputs = formulas_for_board(self.board)
        except CircuitError as e:
            flash_message(live, self.layout, f"Cannot save module: {e}")
            return

        name = prompt_input(live, self.layout, "Module name: ")
        if not name:
            return
        try:
            path = save_custom_module(name, formulas, inputs)
        except FileExistsError:
            overwrite = prompt_input(
                live,
                self.layout,
                "Module exists. Overwrite? (y/n): ",
                default="n",
            )
            if overwrite != "y":
                return
            try:
                path = save_custom_module(name, formulas, inputs, overwrite=True)
            except (OSError, ValueError) as e:
                flash_message(live, self.layout, f"Save failed: {e}")
                return
        except (OSError, ValueError) as e:
            flash_message(live, self.layout, f"Save failed: {e}")
            return

        flash_message(
            live,
            self.layout,
            f"Saved {path} with {len(formulas)} output(s).",
            title="Module saved",
            style="green",
        )

    def place_custom_module(self, live: Live) -> None:
        module_paths = sorted(Path("custom_modules").glob("*.json"))
        definitions = []
        for path in module_paths:
            try:
                definitions.append((path, load_custom_module(path)))
            except (OSError, ValueError, KeyError) as e:
                flash_message(live, self.layout, f"Cannot load {path.name}: {e}")
                return
        if not definitions:
            flash_message(live, self.layout, "No custom modules found in custom_modules/")
            return

        available = ", ".join(module["name"] for _, module in definitions)
        requested = prompt_input(live, self.layout, f"Place module ({available}): ")
        if not requested:
            return
        selected = next(
            (
                module
                for path, module in definitions
                if requested.strip().casefold() in (module["name"].casefold(), path.stem.casefold())
            ),
            None,
        )
        if selected is None:
            flash_message(live, self.layout, f"Unknown module: {requested}")
            return
        try:
            self.board.place_module(self.board.cursor_row, self.board.cursor_col, selected)
        except ValueError as e:
            flash_message(live, self.layout, str(e))
            return
        self.is_modified = True
        flash_message(live, self.layout, f"Placed {selected['name']}.", title="Module placed", style="green")

    def toggle_test_mode(self, live: Live) -> None:
        if self.test_mode:
            self.test_mode = False
            self.test_inputs.clear()
            self.simulation = None
            return
        self.test_inputs = {
            (row, col): cell == C.INPUT_ACTIVE
            for row, line in enumerate(self.board.cells)
            for col, cell in enumerate(line)
            if cell in (C.INPUT, C.INPUT_ACTIVE)
        }
        self.test_mode = True
        self.refresh_simulation(live)

    def refresh_simulation(self, live: Live) -> None:
        try:
            self.simulation = simulate_board(self.board, self.test_inputs)
        except CircuitError as e:
            self.simulation = None
            flash_message(live, self.layout, f"Test mode: {e}")

    def toggle_test_input(self, live: Live) -> None:
        position = (self.board.cursor_row, self.board.cursor_col)
        if self.board.cursor_cell not in (C.INPUT, C.INPUT_ACTIVE):
            return
        self.test_inputs[position] = not self.test_inputs[position]
        self.refresh_simulation(live)

    # -- rendering -------------------------------------------------------

    def refresh_layout(self) -> None:
        file_name = self.current_file.name if self.current_file else "untitled"
        self.layout["top_bar"].update(make_top_bar(file_name, self.is_modified, self.board.cursor_col, self.board.cursor_row))
        self.layout["stage"].update(make_stage(self.board, self.grid_char, self.simulation))
        self.layout["bottom_bar"].update(make_bottom_bar(self.test_mode))

    # -- input -------------------------------------------------------------

    def handle_key(self, key: str, live: Live) -> bool:
        """Handle one keypress. Returns False if the app should exit."""
        if self.test_mode:
            if key == readchar.key.UP:
                self.board.move_cursor(-1, 0)
            elif key == readchar.key.DOWN:
                self.board.move_cursor(1, 0)
            elif key == readchar.key.LEFT:
                self.board.move_cursor(0, -1)
            elif key == readchar.key.RIGHT:
                self.board.move_cursor(0, 1)
            elif key == readchar.key.ENTER:
                self.toggle_test_input(live)
            elif key == " ":
                self.toggle_test_mode(live)
            elif key == readchar.key.ESC:
                return False
            return True

        if key == " ":
            self.toggle_test_mode(live)
            return True
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
        elif key == "m":
            self.save_as_custom_gate(live)
        elif key == "p":
            self.place_custom_module(live)
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
