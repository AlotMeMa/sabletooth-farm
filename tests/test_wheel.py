# -*- coding: utf-8 -*-
"""3.27: колесо фортуны в Игровой — раз в день, джекпот недели, скин не продаётся."""
import datetime
import random
import unittest

from farmgame import wheel
from farmgame.tavern import Tavern
from farmgame import config as cfg


class Wheel(unittest.TestCase):
    def test_once_a_day(self):
        t = Tavern()
        d = datetime.date(2026, 11, 25)
        self.assertIsNotNone(wheel.spin(t, d, random.Random(1)))
        self.assertIsNone(wheel.spin(t, d, random.Random(1)))
        self.assertIsNotNone(wheel.spin(t, d + datetime.timedelta(days=1), random.Random(1)))

    def test_weights_and_segments(self):
        self.assertEqual(len(wheel.SEGMENTS), len(wheel.WEIGHTS))
        self.assertEqual(sum(wheel.WEIGHTS), 100)
        self.assertEqual(sum(1 for s in wheel.SEGMENTS if s[0] == "jackpot"), 1)

    def test_jackpot_changes_weekly(self):
        d = datetime.date(2026, 11, 23)            # понедельник
        same = {wheel.jackpot_for(d + datetime.timedelta(days=i))["name"] for i in range(7)}
        self.assertEqual(len(same), 1)
        self.assertNotEqual(wheel.jackpot_for(d)["name"], wheel.jackpot_for(d + datetime.timedelta(days=7))["name"])

    def test_jackpot_prize_and_fallback(self):
        class Jack:
            def choices(self, seq, weights):
                return [len(wheel.SEGMENTS) - 1]
        d = next(datetime.date(2026, 11, 23) + datetime.timedelta(weeks=i) for i in range(8)
                 if wheel.jackpot_for(datetime.date(2026, 11, 23) + datetime.timedelta(weeks=i))["kind"] == "prize")
        pid = wheel.jackpot_for(d)["prize"]
        t = Tavern()
        _i, r = wheel.spin(t, d, Jack())
        self.assertTrue(t.prizes.get(pid))
        self.assertEqual(r["kind"], "prize")
        before = t.tokens
        _i, r = wheel.spin(t, d + datetime.timedelta(days=1), Jack())     # та же неделя, скин уже есть
        self.assertEqual(t.tokens - before, wheel.JACKPOT_OWNED_TOKENS)

    def test_jackpot_skins_not_for_sale(self):
        t = Tavern()
        t.tokens = 10 ** 6
        for p in cfg.PRIZES:
            if p.get("jackpot"):
                ok, _why = t.buy_prize(None, p["id"])
                self.assertFalse(ok)
        for jp in wheel.JACKPOTS:
            if jp["kind"] == "prize":
                self.assertTrue(any(p["id"] == jp["prize"] and p.get("jackpot") for p in cfg.PRIZES))

    def test_saved(self):
        t = Tavern()
        wheel.spin(t, datetime.date(2026, 11, 25), random.Random(3))
        t2 = Tavern()
        t2.from_dict(t.to_dict())
        self.assertEqual(t2.wheel_day, "2026-11-25")
        self.assertFalse(wheel.can_spin(t2, datetime.date(2026, 11, 25)))


if __name__ == "__main__":
    unittest.main()
