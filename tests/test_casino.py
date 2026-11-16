# -*- coding: utf-8 -*-
"""Казино (заготовка): выплаты рулетки, ставки и жетоны."""
import random
import unittest

from tests import helpers  # noqa: F401
from farmgame import casino as cs
from farmgame import tavern as tv


class Payouts(unittest.TestCase):
    def test_wheel_has_all_numbers_once(self):
        self.assertEqual(sorted(cs.WHEEL), list(range(37)))
        self.assertEqual(len(cs.RED), 18)

    def test_straight(self):
        self.assertEqual(cs.payout(("num", 17), 17), 36)
        self.assertEqual(cs.payout(("num", 17), 18), 0)
        self.assertEqual(cs.payout(("num", 0), 0), 36)

    def test_even_money(self):
        self.assertEqual(cs.payout(("red",), 1), 2)
        self.assertEqual(cs.payout(("black",), 2), 2)
        self.assertEqual(cs.payout(("even",), 2), 2)
        self.assertEqual(cs.payout(("odd",), 2), 0)
        self.assertEqual(cs.payout(("low",), 18), 2)
        self.assertEqual(cs.payout(("high",), 19), 2)

    def test_zero_loses_outside(self):
        for key in (("red",), ("black",), ("even",), ("odd",), ("low",), ("high",), ("dozen", 1)):
            self.assertEqual(cs.payout(key, 0), 0, key)

    def test_dozens(self):
        self.assertEqual(cs.payout(("dozen", 1), 12), 3)
        self.assertEqual(cs.payout(("dozen", 2), 13), 3)
        self.assertEqual(cs.payout(("dozen", 3), 36), 3)
        self.assertEqual(cs.payout(("dozen", 3), 24), 0)

    def test_house_edge_is_european(self):
        """Средний возврат любой ставки — 36/37 (преимущество заведения 2.7%)."""
        for key in (("num", 5), ("red",), ("odd",), ("dozen", 2), ("high",)):
            ret = sum(cs.payout(key, n) for n in range(37)) / 37
            self.assertAlmostEqual(ret, 36 / 37, places=9)


class Bets(unittest.TestCase):
    def setUp(self):
        self.t = tv.Tavern()
        self.t.tokens = 50
        self.r = cs.Roulette(random.Random(1))

    def test_place_and_clear(self):
        self.assertTrue(self.r.place(self.t, ("red",), 10)[0])
        self.assertTrue(self.r.place(self.t, ("num", 7), 5)[0])
        self.assertEqual(self.t.tokens, 35)
        self.r.clear(self.t)
        self.assertEqual(self.t.tokens, 50)
        self.assertEqual(self.r.bets, {})

    def test_not_enough_and_limits(self):
        self.assertFalse(self.r.place(self.t, ("red",), 51)[0])
        self.assertFalse(self.r.place(self.t, ("num", 37), 1)[0])
        self.assertFalse(self.r.place(self.t, ("blue",), 1)[0])
        self.t.tokens = 1000
        self.assertFalse(self.r.place(self.t, ("red",), cs.MAX_BET_TOTAL + 1)[0])

    def test_settle_win_and_loss(self):
        self.r.place(self.t, ("num", 7), 5)       # 7 — красное, нечёт
        self.r.place(self.t, ("black",), 10)
        won, staked = self.r.settle(self.t, 7)
        self.assertEqual((won, staked), (5 * 36, 15))
        self.assertEqual(self.t.tokens, 50 - 15 + 180)
        self.assertEqual(self.r.history, [7])
        self.assertEqual(self.r.bets, {})

    def test_spin_range(self):
        self.assertTrue(all(0 <= self.r.spin() <= 36 for _ in range(500)))


if __name__ == "__main__":
    unittest.main()
