"""Convert circuit boards to named, reusable Boolean formula files."""

from __future__ import annotations

import itertools
import json
import re
from pathlib import Path

from . import constants as C
from .board import Board
from .streamliner import expr_to_string, load_rules, parse, simplify

UP, RIGHT, DOWN, LEFT = range(4)
OPPOSITE = {UP: DOWN, RIGHT: LEFT, DOWN: UP, LEFT: RIGHT}
DELTA = {UP: (-1, 0), RIGHT: (0, 1), DOWN: (1, 0), LEFT: (0, -1)}
SIDE_NAMES = {UP: "top", RIGHT: "right", DOWN: "bottom", LEFT: "left"}
WIRE_PORTS = {
    C.BUFFER: {UP, RIGHT, DOWN, LEFT},
    C.WIRE_H: {RIGHT, LEFT},
    C.WIRE_V: {UP, DOWN},
    C.WIRE_TR: {LEFT, DOWN},
    C.WIRE_TL: {RIGHT, DOWN},
    C.WIRE_T_DOWN: {RIGHT, DOWN, LEFT},
    C.WIRE_T_LEFT: {UP, DOWN, LEFT},
    C.WIRE_BR: {UP, LEFT},
    C.WIRE_BL: {UP, RIGHT},
    C.WIRE_T_UP: {UP, RIGHT, LEFT},
    C.WIRE_T_RIGHT: {UP, RIGHT, DOWN},
    C.WIRE_CROSS: {UP, RIGHT, DOWN, LEFT},
    C.WIRE_X: {UP, RIGHT, DOWN, LEFT},
}
GATE_INPUT_SIDES = (UP, LEFT, DOWN)
LOGIC_GATES = {C.AND, C.OR, C.NOT, C.XOR}


class CircuitError(ValueError):
    """The board cannot be represented as a Boolean formula."""


def streamline_formula(formula: str) -> str:
    """Apply the project’s Boolean simplifier to a saved custom-module formula."""
    formula = formula.strip()
    if not formula or formula in {"state", "not_state"}:
        return formula

    rule_path = Path(__file__).resolve().parent.parent / "logiConf" / "ruleCFG.json"
    if not rule_path.exists():
        return formula

    try:
        simplified = simplify(parse(formula), load_rules(str(rule_path)))
        return expr_to_string(simplified)
    except (TypeError, ValueError):
        return formula


def normalize_module_definition(data: dict) -> dict:
    """Read both legacy single-output files and the named-output format."""
    inputs = list(data["inputs"])
    outputs = data.get("outputs")
    if data.get("kind") == "dff":
        outputs = outputs or {"Q": "state", "Qbar": "not_state"}
        if (
            inputs != ["D", "CLK"]
            or not isinstance(outputs, dict)
            or list(outputs.values()) != ["state", "not_state"]
        ):
            raise CircuitError("A DFF module must map D, CLK to Q, Qbar.")
        return {
            "name": str(data["name"]),
            "inputs": inputs,
            "outputs": dict(outputs),
            "kind": "dff",
        }
    if outputs is None:
        formula = data.get("formula")
        if formula is None:
            raise CircuitError("The custom module has no output formulas.")
        outputs = {"O1": formula}
    if not isinstance(outputs, dict) or not outputs:
        raise CircuitError("The custom module must define at least one named output.")
    return {
        "name": str(data["name"]),
        "inputs": inputs,
        "outputs": {str(name): streamline_formula(str(formula)) for name, formula in outputs.items()},
    }


def load_custom_module(path: Path) -> dict:
    return normalize_module_definition(json.loads(path.read_text()))


def _evaluate_formula(formula: str, values: dict[str, bool]) -> bool:
    if formula == "0":
        return False
    for term in formula.split(" | "):
        literals = term[1:-1].split(" & ")
        term_value = True
        for literal in literals:
            negated = literal.startswith("~")
            name = literal[1:] if negated else literal
            if name not in values:
                raise CircuitError(f"Output formula references unknown input '{name}'.")
            term_value = term_value and (not values[name] if negated else values[name])
        if term_value:
            return True
    return False


class _DisjointSet:
    def __init__(self) -> None:
        self.parent: dict[tuple, tuple] = {}

    def add(self, item: tuple) -> None:
        self.parent[item] = item

    def find(self, item: tuple) -> tuple:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, left: tuple, right: tuple) -> None:
        self.parent[self.find(left)] = self.find(right)


def _channel(row: int, col: int, cell: int, side: int) -> tuple:
    if cell in (C.WIRE_X, C.BUFFER):
        axis = "vertical" if side in (UP, DOWN) else "horizontal"
        return row, col, axis
    return row, col, "all"


def formulas_for_board(
    board: Board,
    *,
    _input_values: dict[tuple[int, int], bool] | None = None,
    _simulation: dict | None = None,
    _module_states: dict[int, dict] | None = None,
) -> tuple[dict[str, str], list[str]]:
    """Evaluate a circuit and return a sum-of-products formula for each output."""
    inputs = sorted(
        ((row, col) for row, line in enumerate(board.cells)
         for col, cell in enumerate(line) if cell in (C.INPUT, C.INPUT_ACTIVE)),
        key=lambda position: (position[1], position[0]),
    )
    outputs = [
        (row, col)
        for row, line in enumerate(board.cells)
        for col, cell in enumerate(line)
        if cell in (C.OUTPUT, C.OUTPUT_ACTIVE)
    ]
    gates = {
        (row, col): cell
        for row, line in enumerate(board.cells)
        for col, cell in enumerate(line)
        if cell in LOGIC_GATES
    }
    modules = [normalize_module_definition(module) for module in board.modules]
    if _input_values is None and any(module.get("kind") == "dff" for module in modules):
        raise CircuitError("A stateful DFF cannot be flattened into a combinational module.")
    if not inputs:
        raise CircuitError("Add at least one input node before saving a module.")
    if len(inputs) > C.MAX_CUSTOM_MODULE_INPUTS:
        raise CircuitError("Custom modules support up to 8 input pins.")
    if not outputs:
        raise CircuitError("A custom module must have at least one output node.")
    input_names = [chr(ord("A") + index) for index in range(len(inputs))]
    input_indices = {position: index for index, position in enumerate(inputs)}
    module_outputs_at: dict[tuple[int, int], tuple] = {}
    for module_index, module in enumerate(modules):
        row, col = board.modules[module_index]["row"], board.modules[module_index]["col"]
        for output_index, output_name in enumerate(module["outputs"]):
            output_name = list(module["outputs"])[output_index]
            module_outputs_at[(row + output_index, col + C.CUSTOM_MODULE_WIDTH - 1)] = (
                "module", module_index, output_name
            )

    sets = _DisjointSet()
    for row, line in enumerate(board.cells):
        for col, cell in enumerate(line):
            if cell not in WIRE_PORTS:
                continue
            for side in WIRE_PORTS[cell]:
                sets.add(_channel(row, col, cell, side))

    def in_bounds(row: int, col: int) -> bool:
        return 0 <= row < board.rows and 0 <= col < board.cols

    for row, line in enumerate(board.cells):
        for col, cell in enumerate(line):
            if cell not in WIRE_PORTS:
                continue
            for side in WIRE_PORTS[cell]:
                d_row, d_col = DELTA[side]
                next_row, next_col = row + d_row, col + d_col
                if not in_bounds(next_row, next_col):
                    continue
                next_cell = board.cells[next_row][next_col]
                if next_cell in WIRE_PORTS and OPPOSITE[side] in WIRE_PORTS[next_cell]:
                    sets.union(
                        _channel(row, col, cell, side),
                        _channel(next_row, next_col, next_cell, OPPOSITE[side]),
                    )

    component_drivers: dict[tuple, set[tuple]] = {}

    def add_component_driver(row: int, col: int, side: int, driver: tuple) -> None:
        cell = board.cells[row][col]
        root = sets.find(_channel(row, col, cell, side))
        component_drivers.setdefault(root, set()).add(driver)

    for index, (row, col) in enumerate(inputs):
        for side, (d_row, d_col) in DELTA.items():
            next_row, next_col = row + d_row, col + d_col
            if not in_bounds(next_row, next_col):
                continue
            neighbor = board.cells[next_row][next_col]
            if neighbor in WIRE_PORTS and OPPOSITE[side] in WIRE_PORTS[neighbor]:
                add_component_driver(next_row, next_col, OPPOSITE[side], ("input", index))

    for (row, col) in gates:
        next_row, next_col = row, col + 1
        if in_bounds(next_row, next_col):
            neighbor = board.cells[next_row][next_col]
            if neighbor in WIRE_PORTS and LEFT in WIRE_PORTS[neighbor]:
                add_component_driver(next_row, next_col, LEFT, ("gate", (row, col)))

    for module_index, module in enumerate(modules):
        row, col = board.modules[module_index]["row"], board.modules[module_index]["col"]
        for output_index, output_name in enumerate(module["outputs"]):
            wire_row = row + output_index
            wire_col = col + C.CUSTOM_MODULE_WIDTH
            if in_bounds(wire_row, wire_col):
                wire = board.cells[wire_row][wire_col]
                if wire in WIRE_PORTS and LEFT in WIRE_PORTS[wire]:
                    add_component_driver(
                        wire_row,
                        wire_col,
                        LEFT,
                        ("module", module_index, output_name),
                    )

    def source_for_module_input(module_index: int, input_index: int) -> tuple:
        module = modules[module_index]
        row, col = board.modules[module_index]["row"], board.modules[module_index]["col"]
        source_row, source_col = row + input_index, col - 1
        if not in_bounds(source_row, source_col):
            raise CircuitError(f"Input {module['inputs'][input_index]} of module '{module['name']}' is outside the board.")
        source_cell = board.cells[source_row][source_col]
        if source_cell in WIRE_PORTS and RIGHT in WIRE_PORTS[source_cell]:
            root = sets.find(_channel(source_row, source_col, source_cell, RIGHT))
            drivers = component_drivers.get(root, set())
            if len(drivers) == 1:
                return next(iter(drivers))
            raise CircuitError(f"Input {module['inputs'][input_index]} of module '{module['name']}' is not connected to one signal source.")
        if source_cell in (C.INPUT, C.INPUT_ACTIVE):
            return "input", input_indices[(source_row, source_col)]
        if source_cell in LOGIC_GATES:
            return "gate", (source_row, source_col)
        if (source_row, source_col) in module_outputs_at:
            return module_outputs_at[(source_row, source_col)]
        raise CircuitError(f"Input {module['inputs'][input_index]} of module '{module['name']}' is not connected to a signal source.")

    def source_for_gate_input(position: tuple[int, int], side: int) -> tuple | None:
        row, col = position
        d_row, d_col = DELTA[side]
        source_row, source_col = row + d_row, col + d_col
        if not in_bounds(source_row, source_col):
            return None
        source_cell = board.cells[source_row][source_col]
        if (source_row, source_col) in module_outputs_at:
            return module_outputs_at[(source_row, source_col)]
        if source_cell in WIRE_PORTS:
            if OPPOSITE[side] not in WIRE_PORTS[source_cell]:
                return None
            root = sets.find(_channel(source_row, source_col, source_cell, OPPOSITE[side]))
            drivers = component_drivers.get(root, set())
            if len(drivers) != 1:
                if not drivers:
                    gate_row, gate_col = position
                    raise CircuitError(
                        f"Gate at row {gate_row}, column {gate_col} has an "
                        f"undriven wire on its {SIDE_NAMES[side]} input. Connect "
                        "that trace to an input or a gate output."
                    )
                raise CircuitError("A wire network has multiple signal sources.")
            return next(iter(drivers))
        if source_cell in (C.INPUT, C.INPUT_ACTIVE):
            return "input", input_indices[(source_row, source_col)]
        if source_cell in LOGIC_GATES and side == LEFT:
            return "gate", (source_row, source_col)
        return None

    def output_source(position: tuple[int, int]) -> tuple:
        row, col = position
        candidates: set[tuple] = set()
        for side, (d_row, d_col) in DELTA.items():
            source_row, source_col = row + d_row, col + d_col
            if not in_bounds(source_row, source_col):
                continue
            source_cell = board.cells[source_row][source_col]
            if (source_row, source_col) in module_outputs_at:
                candidates.add(module_outputs_at[(source_row, source_col)])
                continue
            if source_cell in WIRE_PORTS and OPPOSITE[side] in WIRE_PORTS[source_cell]:
                root = sets.find(_channel(source_row, source_col, source_cell, OPPOSITE[side]))
                candidates.update(component_drivers.get(root, set()))
            elif source_cell in (C.INPUT, C.INPUT_ACTIVE):
                candidates.add(("input", input_indices[(source_row, source_col)]))
            elif source_cell in LOGIC_GATES and side == LEFT:
                candidates.add(("gate", (source_row, source_col)))
        if len(candidates) != 1:
            if not candidates:
                raise CircuitError("The output node is not connected to a signal source.")
            raise CircuitError("The output node has multiple signal sources.")
        return next(iter(candidates))

    resolved_outputs = {
        f"O{index + 1}": output_source(position)
        for index, position in enumerate(outputs)
    }

    def evaluate(
        assignment: tuple[bool, ...],
        resolved_output: tuple,
        output_position: tuple[int, int],
    ) -> bool:
        cache: dict[tuple, bool] = {}
        module_input_cache: dict[int, dict[str, bool]] = {}
        module_state_cache: dict[int, dict[str, bool]] = {}

        def evaluate_source(source: tuple, active: set[tuple]) -> bool:
            kind = source[0]
            if kind == "input":
                return assignment[source[1]]
            if kind == "gate":
                return evaluate_gate(source[1], active)
            return evaluate_module_output(source[1], source[2], active)

        def evaluate_gate(position: tuple[int, int], active: set[tuple]) -> bool:
            driver = ("gate", position)
            if driver in cache:
                return cache[driver]
            if driver in active:
                raise CircuitError("The circuit contains a feedback loop.")
            gate = gates[position]
            gate_active = active | {driver}
            sources = [source_for_gate_input(position, side) for side in GATE_INPUT_SIDES]
            connected = [source for source in sources if source is not None]
            if gate == C.NOT:
                if len(connected) != 1:
                    raise CircuitError("A NOT gate must have exactly one connected input.")
                result = not evaluate_source(connected[0], gate_active)
            else:
                if not connected:
                    raise CircuitError("AND, OR, and XOR gates need at least one connected input.")
                values = [evaluate_source(source, gate_active) for source in connected]
                if gate == C.AND:
                    result = all(values)
                elif gate == C.OR:
                    result = any(values)
                else:
                    result = sum(values) % 2 == 1
            cache[driver] = result
            return result

        def evaluate_module_output(module_index: int, output_name: str, active: set[tuple]) -> bool:
            driver = ("module", module_index, output_name)
            if driver in cache:
                return cache[driver]
            if driver in active:
                raise CircuitError("The circuit contains a feedback loop.")
            if module_index not in module_input_cache:
                module = modules[module_index]
                module_active = active | {driver}
                module_input_cache[module_index] = {
                    name: evaluate_source(source_for_module_input(module_index, input_index), module_active)
                    for input_index, name in enumerate(module["inputs"])
                }
            module = modules[module_index]
            if module.get("kind") == "dff":
                if _module_states is None:
                    raise CircuitError("DFF simulation requires persistent module state.")
                if module_index not in module_state_cache:
                    state = _module_states.setdefault(
                        module_index, {"q": False, "clock": None}
                    )
                    values = module_input_cache[module_index]
                    clock = values["CLK"]
                    if state["clock"] is False and clock:
                        state["q"] = values["D"]
                    state["clock"] = clock
                    module_state_cache[module_index] = {
                        name: state["q"] if meaning == "state" else not state["q"]
                        for name, meaning in module["outputs"].items()
                    }
                result = module_state_cache[module_index][output_name]
                cache[driver] = result
                return result
            result = _evaluate_formula(
                module["outputs"][output_name],
                module_input_cache[module_index],
            )
            cache[driver] = result
            return result

        result = evaluate_source(resolved_output, set())
        if _simulation is not None:
            for driver, value in cache.items():
                if driver[0] == "gate":
                    _simulation["gates"][driver[1]] = value
                elif driver[0] == "module":
                    _simulation["modules"].setdefault(driver[1], {})[driver[2]] = value
            _simulation["outputs"][output_position] = result
            for root, drivers in component_drivers.items():
                try:
                    powered = any(evaluate_source(driver, set()) for driver in drivers)
                except CircuitError:
                    powered = False
                if powered:
                    _simulation["wires"].update(
                        (channel[0], channel[1])
                        for channel in sets.parent
                        if sets.find(channel) == root
                    )
        return result

    formulas: dict[str, str] = {}
    assignments = (
        [tuple(_input_values.get(position, board.cells[position[0]][position[1]] == C.INPUT_ACTIVE)
               for position in inputs)]
        if _input_values is not None
        else tuple(itertools.product((False, True), repeat=len(inputs)))
    )
    for output_index, (output_name, resolved_output) in enumerate(resolved_outputs.items()):
        output_position = outputs[output_index]
        true_terms: list[str] = []
        for assignment in assignments:
            if evaluate(assignment, resolved_output, output_position):
                literals = [
                    name if value else f"~{name}"
                    for name, value in zip(input_names, assignment)
                ]
                true_terms.append(f"({' & '.join(literals)})")
        formulas[output_name] = " | ".join(true_terms) if true_terms else "0"
    return formulas, input_names


def simulate_board(
    board: Board,
    input_values: dict[tuple[int, int], bool],
    module_states: dict[int, dict] | None = None,
) -> dict:
    """Evaluate one input assignment and return powered board coordinates."""
    simulation = {
        "gates": {},
        "modules": {},
        "outputs": {},
        "inputs": {
            (row, col): input_values.get((row, col), cell == C.INPUT_ACTIVE)
            for row, line in enumerate(board.cells)
            for col, cell in enumerate(line)
            if cell in (C.INPUT, C.INPUT_ACTIVE)
        },
        "wires": set(),
    }
    formulas_for_board(
        board,
        _input_values=input_values,
        _simulation=simulation,
        _module_states=module_states if module_states is not None else {},
    )
    return simulation


def formula_for_board(board: Board) -> tuple[str, list[str]]:
    """Compatibility helper for circuits with exactly one output."""
    formulas, inputs = formulas_for_board(board)
    if len(formulas) != 1:
        raise CircuitError("This circuit has multiple outputs; use formulas_for_board().")
    return next(iter(formulas.values())), inputs


def save_custom_module(
    name: str,
    formula: str | dict[str, str],
    inputs: list[str],
    directory: Path = Path("custom_modules"),
    overwrite: bool = False,
    kind: str | None = None,
) -> Path:
    """Save a named module in a JSON file and return its path."""
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()).strip("_")
    if not safe_name:
        raise ValueError("Enter a name containing at least one letter or number.")
    path = directory / f"{safe_name}.json"
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    module = {"name": name.strip(), "inputs": inputs}
    if kind == "dff":
        module.update({"kind": "dff", "outputs": formula})
    elif isinstance(formula, str):
        module["formula"] = streamline_formula(formula)
    else:
        module["outputs"] = {key: streamline_formula(value) for key, value in formula.items()}
        if len(module["outputs"]) == 1:
            module["formula"] = next(iter(module["outputs"].values()))
    path.write_text(json.dumps(module, indent=2))
    return path
