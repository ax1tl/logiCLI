import json
import tempfile
import unittest
from pathlib import Path

import readchar

from logicli import constants as C
from logicli.app import App
from logicli.board import Board
from logicli.custom_modules import (
    CircuitError,
    formula_for_board,
    formulas_for_board,
    normalize_module_definition,
    save_custom_module,
    simulate_board,
)
from logicli.render import render_board


class FormulaForBoardTests(unittest.TestCase):
    def test_three_input_and_exports_sum_of_products(self):
        board = Board(5, 5)
        board.cells[2][0] = C.INPUT
        board.cells[0][2] = C.INPUT
        board.cells[4][2] = C.INPUT
        board.cells[2][1] = C.WIRE_H
        board.cells[1][2] = C.WIRE_V
        board.cells[3][2] = C.WIRE_V
        board.cells[2][2] = C.AND
        board.cells[2][3] = C.OUTPUT

        formula, inputs = formula_for_board(board)

        self.assertEqual(inputs, ["A", "B", "C"])
        self.assertEqual(formula, "(A & B & C)")

    def test_four_input_and_can_be_composed_from_two_gates(self):
        board = Board(5, 5)
        board.cells[2][0] = C.INPUT
        board.cells[0][2] = C.INPUT
        board.cells[0][3] = C.INPUT
        board.cells[4][3] = C.INPUT
        board.cells[2][1] = C.WIRE_H
        board.cells[1][2] = C.WIRE_V
        board.cells[1][3] = C.WIRE_V
        board.cells[3][3] = C.WIRE_V
        board.cells[2][2] = C.AND
        board.cells[2][3] = C.AND
        board.cells[2][4] = C.OUTPUT

        formula, inputs = formula_for_board(board)

        self.assertEqual(inputs, ["A", "B", "C", "D"])
        self.assertEqual(formula, "(A & B & C & D)")

    def test_rejects_missing_output(self):
        board = Board(1, 2)
        board.cells[0][0] = C.INPUT

        with self.assertRaisesRegex(CircuitError, "at least one output"):
            formula_for_board(board)

    def test_generates_a_formula_for_each_output(self):
        board = Board(2, 2)
        board.cells[0][0] = C.INPUT
        board.cells[0][1] = C.OUTPUT
        board.cells[1][0] = C.OUTPUT

        formulas, inputs = formulas_for_board(board)

        self.assertEqual(inputs, ["A"])
        self.assertEqual(formulas, {"O1": "(A)", "O2": "(A)"})

    def test_placed_module_routes_multiple_outputs(self):
        board = Board(6, 8)
        board.cells[2][1] = C.INPUT
        board.place_module(
            2,
            2,
            {
                "name": "Dual",
                "inputs": ["A"],
                "outputs": {"O1": "(A)", "O2": "(~A)"},
            },
        )
        board.cells[2][5] = C.OUTPUT
        board.cells[3][5] = C.WIRE_H
        board.cells[3][6] = C.AND
        board.cells[3][7] = C.OUTPUT

        formulas, inputs = formulas_for_board(board)

        self.assertEqual(inputs, ["A"])
        self.assertEqual(formulas, {"O1": "(A)", "O2": "(~A)"})

    def test_five_input_module_scales_and_routes_all_inputs_from_left(self):
        board = Board(8, 7)
        for row in range(1, 6):
            board.cells[row][1] = C.INPUT
        board.place_module(
            1,
            2,
            {
                "name": "Five",
                "inputs": ["A", "B", "C", "D", "E"],
                "outputs": {"O1": "(A & B & C & D & E)"},
            },
        )
        board.cells[1][5] = C.OUTPUT

        formulas, inputs = formulas_for_board(board)

        self.assertEqual(inputs, ["A", "B", "C", "D", "E"])
        self.assertEqual(formulas, {"O1": "(A & B & C & D & E)"})
        self.assertIsNotNone(board.module_at(5, 2))
        self.assertIsNone(board.module_at(6, 2))
        rendered = render_board(board, ".").plain.splitlines()
        self.assertTrue(all(rendered[row][4] == "I" for row in range(1, 6)))
        self.assertEqual(rendered[1][8], "O")

    def test_module_block_renders_pins_and_roundtrips_with_board(self):
        board = Board(5, 5)
        board.place_module(
            1,
            1,
            {"name": "Dual", "inputs": ["A"], "outputs": {"O1": "(A)"}},
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "project.lgc"
            board.save(path)
            restored = Board.load(path)

        self.assertEqual(restored.modules, board.modules)
        rendered = render_board(restored, ".").plain.splitlines()
        self.assertIn("I ", rendered[1])
        self.assertIn("O ", rendered[1])
        self.assertIn("DU", rendered[2])

        restored.cursor_row = 1
        restored.cursor_col = 1
        restored.edit_cell(C.EMPTY)
        self.assertEqual(restored.modules, [])

    def test_regular_grid_cells_remain_two_columns_wide(self):
        board = Board(1, 3)

        rendered = render_board(board, ".").plain.splitlines()[0]

        self.assertEqual(len(rendered), 2 * board.cols)

    def test_simulation_updates_input_wire_and_output_states_without_mutating_board(self):
        board = Board(3, 4)
        board.cells[1][0] = C.INPUT
        board.cells[1][1] = C.WIRE_H
        board.cells[1][2] = C.WIRE_H
        board.cells[1][3] = C.OUTPUT

        simulation = simulate_board(board, {(1, 0): True})

        self.assertTrue(simulation["inputs"][(1, 0)])
        self.assertTrue(simulation["outputs"][(1, 3)])
        self.assertIn((1, 1), simulation["wires"])
        self.assertIn((1, 2), simulation["wires"])
        self.assertEqual(board.cells[1][0], C.INPUT)
        self.assertEqual(board.cells[1][3], C.OUTPUT)

        rendered = render_board(board, ".", simulation)
        self.assertTrue(rendered.plain.splitlines()[1].startswith("I "))
        self.assertTrue(rendered.plain.splitlines()[1].endswith("O "))
        self.assertTrue(any(span.style == "yellow" for span in rendered.spans))
        self.assertGreaterEqual(
            sum(span.style == "black on white" for span in rendered.spans), 4
        )

    def test_test_mode_blocks_gate_edits_and_enter_toggles_selected_input(self):
        app = App()
        app.board = Board(3, 4)
        app.board.cells[1][0] = C.INPUT
        app.board.cells[1][1] = C.WIRE_H
        app.board.cells[1][2] = C.WIRE_H
        app.board.cells[1][3] = C.OUTPUT
        app.board.cursor_row = 1
        app.board.cursor_col = 0
        app.test_mode = True
        app.test_inputs = {(1, 0): False}

        self.assertTrue(app.handle_key("a", None))
        self.assertEqual(app.board.cells[1][0], C.INPUT)
        self.assertFalse(app.is_modified)

        self.assertTrue(app.handle_key(readchar.key.ENTER, None))
        self.assertTrue(app.test_inputs[(1, 0)])
        self.assertTrue(app.simulation["outputs"][(1, 3)])
        self.assertEqual(app.board.cells[1][0], C.INPUT)

    def test_module_placement_rejects_occupied_footprint(self):
        board = Board(5, 5)
        board.cells[2][2] = C.AND

        with self.assertRaisesRegex(ValueError, "overlaps an occupied cell"):
            board.place_module(
                1,
                1,
                {"name": "Pass", "inputs": ["A"], "outputs": {"O1": "(A)"}},
            )

    def test_reports_location_of_gate_input_wire_without_source(self):
        board = Board(4, 4)
        board.cells[0][0] = C.INPUT
        board.cells[1][1] = C.AND
        board.cells[2][1] = C.WIRE_V
        board.cells[1][2] = C.OUTPUT

        with self.assertRaisesRegex(CircuitError, "row 1, column 1.*bottom input"):
            formula_for_board(board)

    def test_buffer_passes_signal_straight_through(self):
        board = Board(3, 5)
        board.cells[1][0] = C.INPUT
        board.cells[1][1] = C.WIRE_H
        board.cells[1][2] = C.BUFFER
        board.cells[1][3] = C.WIRE_H
        board.cells[1][4] = C.OUTPUT

        formula, inputs = formula_for_board(board)

        self.assertEqual(inputs, ["A"])
        self.assertEqual(formula, "(A)")

    def test_gate_output_flows_through_top_right_corner_and_down(self):
        board = Board(4, 4)
        board.cells[0][1] = C.INPUT
        board.cells[1][1] = C.AND
        board.cells[1][2] = C.WIRE_TR
        board.cells[2][2] = C.WIRE_V
        board.cells[3][2] = C.AND
        board.cells[3][3] = C.OUTPUT

        formula, inputs = formula_for_board(board)

        self.assertEqual(inputs, ["A"])
        self.assertEqual(formula, "(A)")

    def test_three_input_xor_exports_each_true_minterm(self):
        board = Board(5, 5)
        board.cells[2][0] = C.INPUT
        board.cells[0][2] = C.INPUT
        board.cells[4][2] = C.INPUT
        board.cells[2][1] = C.WIRE_H
        board.cells[1][2] = C.WIRE_V
        board.cells[3][2] = C.WIRE_V
        board.cells[2][2] = C.XOR
        board.cells[2][3] = C.OUTPUT

        formula, _ = formula_for_board(board)

        self.assertEqual(
            formula,
            "(~A & ~B & C) | (~A & B & ~C) | (A & ~B & ~C) | (A & B & C)",
        )

    def test_saves_name_inputs_and_formula(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = save_custom_module(
                "Full adder", "(A & B)", ["A", "B"], Path(temporary_directory)
            )

            self.assertEqual(path.name, "Full_adder.json")
            self.assertEqual(
                json.loads(path.read_text()),
                {"name": "Full adder", "inputs": ["A", "B"], "formula": "(A & B)"},
            )

    def test_saves_multiple_named_output_formulas(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = save_custom_module(
                "Dual output",
                {"O1": "(A)", "O2": "(~A)"},
                ["A"],
                Path(temporary_directory),
            )

            self.assertEqual(
                json.loads(path.read_text()),
                {
                    "name": "Dual output",
                    "inputs": ["A"],
                    "outputs": {"O1": "(A)", "O2": "(~A)"},
                },
            )

    def test_reads_legacy_single_formula_module_definition(self):
        module = normalize_module_definition(
            {"name": "4way", "inputs": ["A", "B"], "formula": "(A & B)"}
        )

        self.assertEqual(
            module,
            {"name": "4way", "inputs": ["A", "B"], "outputs": {"O1": "(A & B)"}},
        )


if __name__ == "__main__":
    unittest.main()