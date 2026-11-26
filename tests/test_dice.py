# -*- coding: utf-8 -*-
"""3.43: кости «Больше / меньше / 7»."""
import random
import unittest

from tests import helpers  # noqa: F401
from farmgame import dice as dc
from farmgame.tavern import Tavern


class Rules(unittest.TestCase):
    def test_chances_and_return(self):
        self.assertAlmostEqual(dc.chance("under"), 15 / 36)
        self.assertAlmostEqual(dc.chance("seven"), 6 / 36)
        self.assertAlmostEqual(dc.chance("over"), 15 / 36)
        for a in dc.AREAS:
            rtp = dc.chance(a["id"]) * a["k"]
            self.assertTrue(0.93 <= rtp <= 0.97, (a["id"], rtp))   # около 95%, как у рулетки и улиток

    def test_locked_until_dragons(self):
        for i in range(4):
            self.assertFalse(dc.unlocked(i))


class Game(unittest.TestCase):
    def setUp(self):
        self.t = Tavern()
        self.t.tokens = 100
        self.g = dc.DiceGame()

    def test_min_bet(self):
        self.assertFalse(self.g.roll(self.t))
        self.g.add_bet(self.t, "under", dc.MIN_BET - 1)
        self.assertFalse(self.g.roll(self.t))

    def test_payout_on_several_areas(self):
        self.g.add_bet(self.t, "under", 10)
        self.g.add_bet(self.t, "seven", 10)
        dc.FORCE_NEXT = (3, 4)
        self.assertTrue(self.g.roll(self.t))
        self.assertIsNone(dc.FORCE_NEXT)
        self.assertEqual(self.g.total(), 7)
        self.assertEqual(self.g.paid, 57)
        self.assertEqual(self.g.net(), 37)
        self.assertEqual(self.t.tokens, 80 + 57)
        self.assertEqual(self.g.winning_area(), "seven")

    def test_lose_and_again(self):
        self.g.add_bet(self.t, "over", 25)
        dc.FORCE_NEXT = (1, 2)
        self.g.roll(self.t)
        self.assertFalse(self.g.won())
        self.assertEqual(self.g.net(), -25)
        self.g.finish()
        self.assertTrue(self.g.next_round(self.t))
        self.assertEqual((self.g.state, self.g.bets["over"], self.t.tokens), ("bet", 25, 50))

    def test_refund(self):
        self.g.add_bet(self.t, "seven", 30)
        self.g.refund(self.t)
        self.assertEqual((self.t.tokens, self.g.bet), (100, 0))

    def test_average_return(self):
        rnd = random.Random(4)
        bet = back = 0
        for _ in range(20000):
            t = Tavern()
            t.tokens = 10
            g = dc.DiceGame()
            g.add_bet(t, rnd.choice(["under", "seven", "over"]), 10)
            g.roll(t, rnd)
            bet += 10
            back += g.paid
        self.assertTrue(0.90 < back / bet < 1.0, back / bet)

    def test_intro_saved(self):
        t = Tavern()
        t.dc_intro = True
        t2 = Tavern()
        t2.from_dict(t.to_dict())
        self.assertTrue(t2.dc_intro)


if __name__ == "__main__":
    unittest.main()
