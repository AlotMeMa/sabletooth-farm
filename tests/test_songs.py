# -*- coding: utf-8 -*-
"""3.8: заказ песни барду за жетоны — цена, одна песня за раз, эффект и окончание, сохранение."""
import unittest

from tests import helpers  # noqa: F401  (добавляет папку игры в путь)
from farmgame import config as cfg
from farmgame import tavern as tv
from farmgame.logic import Farm


def song(sid):
    return next(sg for sg in cfg.SONGS if sg["id"] == sid)


class OrderSong(unittest.TestCase):
    def setUp(self):
        self.t = tv.Tavern()
        self.t.unlocked = True
        self.f = Farm()
        self.f.levels[0] = 10

    def test_costs_tokens_and_starts(self):
        self.t.tokens = 12
        ok, why = tv.order_song(self.t, self.f, 2)
        self.assertTrue(ok, why)
        self.assertEqual(self.t.tokens, 12 - song(2)["cost"])
        self.assertEqual(self.f.song, 2)
        self.assertAlmostEqual(self.f.song_left, song(2)["minutes"] * 60)

    def test_not_enough_tokens(self):
        self.t.tokens = song(3)["cost"] - 1
        ok, why = tv.order_song(self.t, self.f, 3)
        self.assertFalse(ok)
        self.assertIn("жетон", why)
        self.assertEqual(self.t.tokens, song(3)["cost"] - 1)
        self.assertEqual(self.f.song, 0)

    def test_one_song_at_a_time(self):
        self.t.tokens = 100
        self.assertTrue(tv.order_song(self.t, self.f, 1)[0])
        ok, _ = tv.order_song(self.t, self.f, 3)
        self.assertFalse(ok)
        self.assertEqual(self.t.tokens, 100 - song(1)["cost"])

    def test_unknown_song(self):
        self.t.tokens = 100
        self.assertFalse(tv.order_song(self.t, self.f, 99)[0])
        self.assertEqual(self.t.tokens, 100)

    def test_income_bonus_and_end(self):
        base = self.f.cycle_income(0)
        self.t.tokens = 100
        tv.order_song(self.t, self.f, 3)
        self.assertAlmostEqual(self.f.cycle_income(0), base * song(3)["income"])
        self.f.update(song(3)["minutes"] * 60 + 1)
        self.assertEqual(self.f.song, 0)
        self.assertEqual(self.f.song_left, 0)
        self.assertAlmostEqual(self.f.cycle_income(0), base)
        self.assertTrue(tv.order_song(self.t, self.f, 1)[0])       # после конца можно заказать новую

    def test_squirrel_song_effects(self):
        self.t.tokens = 100
        self.assertEqual(self.f.song_effect("squirrel"), 1.0)
        tv.order_song(self.t, self.f, 2)
        self.assertEqual(self.f.song_effect("squirrel"), song(2)["squirrel"])
        self.assertEqual(self.f.song_effect("golden"), song(2)["golden"])
        self.assertEqual(self.f.song_effect("income"), 1.0)

    def test_saved_and_loaded(self):
        self.t.tokens = 100
        tv.order_song(self.t, self.f, 1)
        self.f.song_left = 123.0
        g = Farm()
        g.from_dict(self.f.to_dict())
        self.assertEqual((g.song, g.song_left), (1, 123.0))

    def test_old_save_without_song(self):
        d = self.f.to_dict()
        del d["song"], d["song_left"]
        g = Farm()
        g.from_dict(d)
        self.assertEqual((g.song, g.song_left), (0, 0.0))


if __name__ == "__main__":
    unittest.main()
