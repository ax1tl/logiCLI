import argparse
import fnmatch
import os
import sys
import textwrap
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.status import Status
from rich import box

# KEY CODES FOR GATES:

# w - 1      - wire
# a - 2      - and
# o - 3      - or
# n - 4      - not
# x - 5      - xor
# I - 6,7    - input switch
# O - 8,9    - output led

ver = "v0.0.0"

console = Console()

gates = []

# init board
rows = 10
cols = 10
board = [[0 for _ in range(cols)] for _ in range(rows)]

def render() -> None:
    print("Hey chat, how's it going?")


