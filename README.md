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

Custom modules are saved as JSON files in `custom_modules/`, with their name, input labels, and one formula per output (`O1`, `O2`, and so on). Inputs are labeled `A`, `B`, `C`, and so on from left to right (top to bottom for inputs in the same column). AND, OR, and XOR gates use up to three connected inputs from the top, left, and bottom, and output to the right; unconnected inputs are ignored. NOT gates use one of those input sides and the same right output. Buffers pass signals straight through horizontally or vertically.

Press `p` and enter a saved module's name to place it at the cursor. The pink block is three cells wide and at least three cells tall, growing to fit the larger of its input and output counts. Inputs face left and outputs face right; both are ordered top-to-bottom. The center shows an abbreviated name. Modules support up to eight inputs, with as many outputs as fit on the board. Set `CUSTOM_MODULE_COLOR` in `logicli/constants.py` to change the block color. Older module files with a single `formula` field are still supported as `O1`.

In test mode, use the arrow keys to select an input and `Enter` to toggle it. Powered wires turn yellow and powered outputs switch to their active appearance. Editing controls are disabled until you press `Space` to return to edit mode; test input changes do not modify the saved circuit.
