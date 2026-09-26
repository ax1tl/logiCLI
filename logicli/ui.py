"""Small interactive helpers that borrow the Live display's bottom bar."""

from __future__ import annotations

import time

import readchar
from rich import box
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel

from . import constants as C


def prompt_input(live: Live, layout: Layout, prompt: str, default: str = "") -> str | None:
    """Read a line of text in the bottom bar. Enter confirms, Esc cancels."""
    buffer = list(default)
    while True:
        layout["bottom_bar"].update(
            Panel(
                f"{prompt}{''.join(buffer)}\u2588",
                border_style=C.COLOR_MAIN,
                box=box.ROUNDED,
                title="Input",
                title_align="left",
            )
        )
        live.refresh()
        key = readchar.readkey()
        if key == readchar.key.ENTER:
            return "".join(buffer)
        if key == readchar.key.ESC:
            return None
        if key in (readchar.key.BACKSPACE, readchar.key.DELETE):
            if buffer:
                buffer.pop()
        elif len(key) == 1 and key.isprintable():
            buffer.append(key)


def flash_message(live: Live, layout: Layout, message: str) -> None:
    """Briefly show an error message in the bottom bar."""
    layout["bottom_bar"].update(
        Panel(message, border_style="red", box=box.ROUNDED, title="Error", title_align="left")
    )
    live.refresh()
    time.sleep(1.0)
