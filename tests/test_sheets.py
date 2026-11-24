# -*- coding: utf-8 -*-
"""3.19.1: листы картинок — сетка листа совпадает с числом клеток в порядке (без pygame: читаем исходник)."""
import ast
import os
import unittest

from tests import helpers


class SheetGrids(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(helpers.ROOT, "farmgame", "spritefit.py"), encoding="utf-8") as f:
            tree = ast.parse(f.read())
        self.lists = {}
        self.sheets = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                if name.endswith("_ORDER") and isinstance(node.value, ast.List):
                    self.lists[name] = [e.value for e in node.value.elts]
                if name == "SHEETS":
                    self.sheets = node.value

    def test_rows_times_cols_equals_order(self):
        for key, val in zip(self.sheets.keys, self.sheets.values):
            order_node, rows, cols = val.elts[1], val.elts[2].value, val.elts[3].value
            name = order_node.id if isinstance(order_node, ast.Name) else None
            if name in self.lists:
                self.assertEqual(rows * cols, len(self.lists[name]), key.value)

    def test_plate_sheet_matches_user_picture(self):
        # картинка пользователя (24.11): 3 ряда × 2 столбца, вторая лента не нужна, белой заливки нет
        self.assertEqual(self.lists["PLATE_SHEET_ORDER"], ["pill", "toast", "banner", "_unused", "bar_frame", "sign_casino"])


if __name__ == "__main__":
    unittest.main()
