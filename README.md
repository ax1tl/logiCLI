# logiCLI

A terminal-based logic circuit editor built with [Rich](https://github.com/Textualize/rich). Place gates on a grid, wire them together with traces, and save/load your circuits as projects.

## Requirements

- Python 3.10+
- [`rich`](https://pypi.org/project/rich/)
- [`readchar`](https://pypi.org/project/readchar/)

```bash
pip install rich readchar
```

## Running

```bash
python logiCLI.py
```

## Controls

### Navigation
| Key | Action |
|---|---|
| `↑` `↓` `←` `→` | Move cursor |

### Editing
| Key | Action |
|---|---|
| `i` | Place a wire/ink segment |
| `a` | Place an **AND** gate |
| `o` | Place an **OR** gate |
| `n` | Place a **NOT** gate |
| `x` | Place an **XOR** gate |
| `I` | Place an **Input** node |
| `O` | Place an **Output** node |
| `Backspace` / `Delete` | Clear the current cell |
| `Enter` | Cycle the trace shape at the cursor (straight ↔ corner ↔ T-junction ↔ cross) |
| `e` `r` | Rotate the trace at the cursor clockwise |
| `q` | Rotate the trace at the cursor counter-clockwise |
| `g` | Toggle the background grid dots on/off |

### File / Project
| Key | Action |
|---|---|
| `s` | Save the current project (prompts for a filename) |
| `l` | Load a project from file (prompts for a filename) |
| `m` | Save the circuit as a named custom module |
| `p` | Place a saved custom module at the cursor |
| `N` | Start a new, blank project |
| `Space` | Enter/exit circuit test mode |

### Other
| Key | Action |
|---|---|
| `Esc` | Quit logiCLI |

## Projects

Projects are saved as plain JSON files containing the board dimensions and cell contents.
