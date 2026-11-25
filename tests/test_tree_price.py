# -*- coding: utf-8 -*-
"""3.31: дерево дорожает — каждый купленный уровень поднимает цену ДРУГИХ улучшений на TREE_INFLATION."""
import unittest

from farmgame import config as C
from farmgame.logic import Farm


class TreeInflation(unittest.TestCase):
    def setUp(self):
        self.f = Farm()
        self.f.leaves = self.f.home_leaves = 100_000

    def test_fresh_tree_has_base_prices(self):
        for nid, node in self.f.nodes().items():
            self.assertEqual(self.f.tree_cost(nid), node["costs"][0])

    def test_purchase_raises_other_prices(self):
        base = self.f.tree_cost("rain_len")
        self.assertTrue(self.f.buy_tree("capital"))
        self.assertEqual(self.f.tree_cost("rain_len"), round(base * (1 + C.TREE_INFLATION)))

    def test_own_levels_do_not_inflate_itself(self):
        self.f.buy_tree("capital")
        self.f.buy_tree("capital")
        self.assertEqual(self.f.tree_cost("capital"), C.TREE_SUMMER[0][1][0]["costs"][2])

    def test_paid_price_is_shown_price(self):
        self.f.buy_tree("capital")
        self.f.buy_tree("rain_len")
        cost = self.f.tree_cost("farmers")
        before = self.f.leaves
        self.assertTrue(self.f.buy_tree("farmers"))
        self.assertEqual(before - self.f.leaves, cost)

    def test_move_resets_inflation(self):
        self.f.tree = {"capital": 5, "farmers": 9}
        self.f.run_earned = self.f.move_threshold()
        self.assertTrue(self.f.move_farm())
        self.assertEqual(self.f.tree_inflation("capital"), 1.0)
        self.assertEqual(self.f.tree_cost("capital"), self.f.nodes()["capital"]["costs"][0])

    def test_cannot_buy_when_inflated_price_too_high(self):
        self.f.tree = {"capital": 5, "rain_len": 3, "offline": 5}
        self.f.leaves = self.f.home_leaves = C.TREE_SUMMER[0][1][1]["costs"][0]   # базовая цена фермеров
        self.assertFalse(self.f.can_buy_tree("farmers"))


if __name__ == "__main__":
    unittest.main()
