# logiCLI Wiki

Welcome to the logiCLI reference. logiCLI is a terminal-based logic circuit editor built with [Rich](https://github.com/Textualize/rich). This guide covers setup, editing circuits, saving projects, reusable modules, and test mode.

## Contents

- [Getting started](#getting-started)
- [Editor overview](#editor-overview)
- [Keyboard reference](#keyboard-reference)
- [Circuit rules](#circuit-rules)
- [Projects and files](#projects-and-files)
- [Custom modules](#custom-modules)
- [Test mode](#test-mode)
- [Troubleshooting](#troubleshooting)

## Getting started

### Requirements

- Python 3.10 or later
- [Rich](https://pypi.org/project/rich/)
- [readchar](https://pypi.org/project/readchar/)

Install the dependencies and start the editor from the repository root:

```bash
python -m pip install rich readchar
python main.py
```

## Editor overview

The editor is a grid. Move the cursor with the arrow keys, place a gate or trace using its key, and connect cells by placing adjacent trace segments. The cursor position is shown in the top bar. Press `Esc` to quit.

### Gates and nodes

| Key | Cell | Description |
|---|---|---|
| `a` | AND | Combines connected top, left, and bottom inputs. |
| `o` | OR | Combines connected top, left, and bottom inputs. |
| `x` | XOR | Outputs true when an odd number of connected inputs are true. |
| `n` | NOT | Inverts its single connected input. |
| `b` | Buffer | Passes a signal straight through horizontally or vertically. |
| `I` | Input | An externally controlled signal source. |
| `O` | Output | Displays the state of a connected signal. |
| `i` | Trace | Places a horizontal wire; use trace controls to shape it. |

AND, OR, and XOR ignore unconnected input sides. A trace network must have one signal source to be evaluated.

### Trace shapes

Place a horizontal trace with `i`. Move to it and press `Enter` to cycle through straight, corner, T-junction, and crossing forms. Use `e` or `r` to rotate clockwise and `q` to rotate counter-clockwise.

## Keyboard reference

| Key | Action |
|---|---|
| `↑` `↓` `←` `→` | Move the cursor |
| `i` | Place a trace |
| `a` `o` `x` `n` `b` | Place an AND, OR, XOR, NOT, or buffer gate |
| `I` `O` | Place an input or output node |
| `Enter` | Cycle a trace shape; in test mode, toggle the selected input |
| `e` `r` | Rotate a trace clockwise |
| `q` | Rotate a trace counter-clockwise |
| `Backspace` `Delete` | Clear the cell or remove a module under the cursor |
| `g` | Toggle grid dots |
| `Space` | Enter or leave test mode |
| `Ctrl+S` | Save the current project under a filename |
| `l` | Load a project |
| `m` | Save the circuit as a custom module |
| `p` | Place a saved custom module |
| `N` | Create a new project |
| `Esc` | Quit |

## Circuit rules

The formula generator labels input nodes `A`, `B`, `C`, and so on, ordered left to right and then top to bottom within a column. It derives each output's sum-of-products formula from the circuit's connected traces and gates.

Logic gates have their output on the right. AND, OR, and XOR accept up to three connected inputs from the top, left, and bottom; NOT accepts exactly one. Buffers carry horizontal and vertical signals independently. A circuit used to create a custom module needs at least one input and one output.

## Projects and files

### Circuit projects

Use `Ctrl+S` to save a project and `l` to load one. Projects are JSON files containing board dimensions, cell contents, and any placed custom modules. Older project files without module data continue to load.

### Custom module definitions

Custom modules are JSON files in `custom_modules/`. Each definition stores its name, input labels, and formula for each output. Older definitions with one `formula` field are read as output `O1`.

## Custom modules

### Save a module

Build and connect a circuit, then press `m` and enter a name. The editor writes a named JSON definition. Existing names prompt before overwrite.

### Place a module

Move the cursor to the module's top-left position, press `p`, and enter its name. The block is three cells wide and grows vertically to fit the larger of its input and output counts. Its input pins face left and its output pins face right; both are ordered top to bottom. The center shows an abbreviated name, and the block color is set by `CUSTOM_MODULE_COLOR` in `logicli/constants.py`.

Modules can be connected to traces, gates, and other modules. Clearing any cell inside a module removes the whole module. Placement requires the full footprint to fit on the board and not overlap other cells or modules.

## Test mode

Press `Space` to enter test mode. Editing controls are disabled while testing.

1. Use the arrow keys to select an input node.
2. Press `Enter` to toggle its temporary state.
3. Observe powered traces in yellow and powered outputs in their active style.
4. Press `Space` to return to editing.

Test input states are temporary and do not change the saved project.

## Troubleshooting

### A gate input has no signal source

Check that the gate-facing trace connects continuously to an input or another gate's right-side output. Corner and T-junction orientation matters: the visible trace openings must face the connected cells.

### A module will not place

The module's entire three-cell-wide footprint must fit on the board. Its height is at least three rows and expands to fit its pins. Move the cursor to a clear top-left position and try again.

### A custom module is not listed

Check that its JSON definition is in the repository's `custom_modules/` directory and contains a name, inputs, and at least one output formula.