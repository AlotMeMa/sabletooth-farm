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
        self.assertTrue(self.r.place(self.t, ("red",), 600)[0])          # 3.14: лимита за спин нет

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


class PlayerCasino(unittest.TestCase):
    """3.14: казино для игроков — открытие по жетонам, призовая стойка, сохранение."""

    def setUp(self):
        from farmgame.logic import Farm
        self.t = tv.Tavern()
        self.f = Farm()

    def test_opens_once_at_100_tokens_and_stays_open(self):
        from farmgame.config import CASINO_UNLOCK_TOKENS
        self.t.tokens = CASINO_UNLOCK_TOKENS - 1
        self.assertFalse(self.t.check_casino())
        self.t.tokens = CASINO_UNLOCK_TOKENS
        self.assertTrue(self.t.check_casino())
        self.assertFalse(self.t.check_casino())          # второй раз «только что открылось» не говорит
        self.t.tokens = 0
        self.assertTrue(self.t.casino_open)

    def test_min_chip_is_5(self):
        self.assertEqual(min(cs.CHIPS), 5)

    def test_trophy_once(self):
        self.t.tokens = 1000
        self.assertTrue(self.t.buy_prize(self.f, "cup")[0])
        self.assertFalse(self.t.buy_prize(self.f, "cup")[0])
        self.assertEqual(self.t.tokens, 850)

    def test_shop_is_cosmetic_only(self):
        # 3.19: магазин таверны — только косметика: покупки не меняют доход и шанс урожая
        from farmgame.config import PRIZES
        self.assertTrue(all(p["kind"] in ("trophy", "cosmetic") for p in PRIZES))
        self.f.levels[0] = 10
        base = self.f.cycle_income(0)
        self.t.tokens = 10 ** 6
        for p in PRIZES:
            if p.get("jackpot") or p.get("achievement"):   # 3.27/3.34: джекпот колеса и трофеи за достижения не продаются
                self.assertFalse(self.t.buy_prize(self.f, p["id"])[0], p["id"])
                continue
            self.assertTrue(self.t.buy_prize(self.f, p["id"])[0], p["id"])
        self.assertAlmostEqual(self.f.cycle_income(0), base)

    def test_cosmetic_toggle_and_save(self):
        self.t.tokens = 1000
        self.t.buy_prize(self.f, "garland")
        self.assertTrue(self.t.prize_on("garland"))
        self.t.toggle_prize("garland")
        self.assertFalse(self.t.prize_on("garland"))
        t2 = tv.Tavern()
        t2.from_dict(self.t.to_dict())
        self.assertTrue(t2.prizes.get("garland"))
        self.assertFalse(t2.prize_on("garland"))

    def test_not_enough_tokens(self):
        self.t.tokens = 10
        ok, why = self.t.buy_prize(self.f, "statue")
        self.assertFalse(ok)
        self.assertEqual(self.t.tokens, 10)


class BardGirl(unittest.TestCase):
    """3.15.2: певица Мила — украшение из призов, вкл/выкл; лист призов 3×3 — только первые 9."""

    def test_buy_and_toggle(self):
        from farmgame.logic import Farm
        t = tv.Tavern()
        t.tokens = 1000
        self.assertTrue(t.buy_prize(Farm(), "bard_girl")[0])
        self.assertTrue(t.prize_on("bard_girl"))
        t.toggle_prize("bard_girl")
        self.assertFalse(t.prize_on("bard_girl"))

    def test_prize_sheet_keeps_old_order(self):
        # лист призов 3×3 пользователя — порядок клеток фиксирован, не зависит от списка призов
        from farmgame.config import PRIZE_SHEET_IDS
        self.assertEqual(PRIZE_SHEET_IDS, ["horseshoe", "cup", "statue", "crystal", "lucky_coin", "clover",
                                           "gold_notes", "gold_trail", "garland"])


class KnownMusic(unittest.TestCase):
    def test_every_scene_track_is_known(self):
        # проверка картинок не должна называть «неузнанной» музыку, которую игра сама играет
        import re, os, glob
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        audio = open(os.path.join(root, "farmgame", "audio.py"), encoding="utf-8").read()   # без pygame
        known = re.search(r"^MUSIC_NAMES = (\([^)]*\))", audio, re.M).group(1)
        scenes = {"tavern"}
        for path in glob.glob(os.path.join(root, "farmgame", "*.py")):
            scenes |= set(re.findall(r'has_scene_music\("(\w+)"\)', open(path, encoding="utf-8").read()))
        from farmgame.config import PRIZES                   # 3.23: песни артистов сцены — в призах (stage=...)
        scenes |= {p["stage"] for p in PRIZES if p.get("stage")}
        self.assertIn("tavern_girl", scenes)                 # шаблон поиска правда что-то находит
        for name in scenes:
            self.assertIn(f'"{name}"', known)
