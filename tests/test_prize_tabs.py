# -*- coding: utf-8 -*-
"""3.33: призовая стойка по вкладкам, группы «одно из», новые призы."""
import unittest

from tests.helpers import summer_farm
from farmgame.config import PRIZES, PRIZE_TABS
from farmgame.tavern import Tavern, prize_group


class PrizeTabs(unittest.TestCase):
    def test_trophies_are_last_tab(self):
        self.assertEqual([k for k, _ in PRIZE_TABS], ["decor", "chars", "fx", "misc", "trophy"])

    def test_every_cosmetic_has_a_tab(self):
        tabs = {k for k, _ in PRIZE_TABS}
        for p in PRIZES:
            if p["kind"] == "cosmetic":
                self.assertIn(p.get("cat"), tabs, p["id"])
        for key in tabs - {"trophy"}:
            self.assertGreaterEqual(sum(1 for p in PRIZES if p.get("cat") == key), 3, key)

    def test_groups_are_one_of(self):
        t, f = Tavern(), summer_farm()
        t.tokens = 10 ** 6
        for pid in ("gold_trail", "leaf_trail", "bubble_trail"):
            self.assertTrue(t.buy_prize(f, pid)[0])
            self.assertEqual(t.group_on("trail"), pid)
        t.toggle_prize("gold_trail")            # включить старый — новый выключится
        self.assertEqual(t.group_on("trail"), "gold_trail")
        self.assertFalse(t.prize_on("bubble_trail"))
        t.buy_prize(f, "cards_gold")
        t.buy_prize(f, "cards_winter")
        self.assertEqual(t.group_on("cards"), "cards_winter")

    def test_stage_group_still_works(self):
        self.assertEqual(prize_group(next(p for p in PRIZES if p["id"] == "fiddler")), "stage")

    def test_trophy_spots_cover_all_trophies(self):
        import ast
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "farmgame", "fireside_art.py")
        tree = ast.parse(open(path, encoding="utf-8").read())
        n = sum(1 for p in PRIZES if p["kind"] == "trophy")
        found = 0
        for node in ast.walk(tree):          # FIRESIDE_LAYOUT и FIRESIDE_CUSTOM — dict(..., trophies=[...])
            if isinstance(node, ast.keyword) and node.arg == "trophies":
                self.assertGreaterEqual(len(ast.literal_eval(node.value)), n)
                found += 1
        self.assertEqual(found, 2)


if __name__ == "__main__":
    unittest.main()
