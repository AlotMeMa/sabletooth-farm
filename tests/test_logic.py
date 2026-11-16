# -*- coding: utf-8 -*-
"""Логика фермы: офлайн, продажа, большие числа, чтение сохранений."""
import copy
import json
import random
import unittest
from unittest import mock

from tests.helpers import summer_farm, medieval_farm
from farmgame import config as cfg
from farmgame import logic
from farmgame.logic import Farm

HOUR = 3600.0


def clone(f):
    g = Farm()
    g.from_dict(json.loads(json.dumps(f.to_dict())))
    return g


class Offline(unittest.TestCase):
    def test_boost_x2_ends_on_time(self):
        """Минута буста x2 даёт минуту удвоенного дохода, а не весь офлайн (ошибка до 2.8)."""
        plain, boosted = summer_farm(), summer_farm()
        boosted.boost_left = 60.0
        a = plain.offline_earn(3 * HOUR)
        b = boosted.offline_earn(3 * HOUR)
        self.assertEqual(boosted.boost_left, 0.0)
        self.assertGreater(b, a)
        self.assertLess(b / a, 1.02)

    def test_timers_run_offline(self):
        f = summer_farm()
        f.rain_cd, f.sun_cd, f.boost_left = 200.0, 150.0, 30.0
        f.offline_earn(HOUR)
        self.assertEqual((f.rain_cd, f.sun_cd, f.boost_left), (0.0, 0.0, 0.0))

    def test_rain_finishes_then_cooldown(self):
        f = summer_farm()
        f.rain_left, f.rain_cd = 30.0, 240.0
        f.offline_earn(100.0)
        self.assertEqual(f.rain_left, 0.0)
        self.assertAlmostEqual(f.rain_cd, 240.0 - 70.0, delta=cfg.OFFLINE_STEP)

    def test_keepers_work_offline(self):
        f = summer_farm()
        per_sec = sum(f.animal_income(a) for a in range(cfg.N_ANIMALS))
        f.offline_earn(3 * HOUR)
        self.assertAlmostEqual(sum(f.a_store), per_sec * 3 * HOUR, delta=per_sec * 3 * HOUR * 0.02)

    def test_old_mode_without_automation(self):
        """OFFLINE_AUTOMATION = False возвращает прежнее поведение: звери только доедают кормушку."""
        f = summer_farm()
        per_sec = sum(f.animal_income(a) for a in range(cfg.N_ANIMALS))
        with mock.patch.object(logic, "OFFLINE_AUTOMATION", False):
            f.offline_earn(3 * HOUR)
        self.assertLess(sum(f.a_store), per_sec * cfg.FEEDER_SECONDS * 1.01 + 1)

    def test_mill_and_bakery_work_offline(self):
        f = medieval_farm()
        f.offline_earn(HOUR)
        self.assertGreater(f.bread, 0)
        expect = f.bake_rate() * HOUR * cfg.BREAD_RATIO
        self.assertAlmostEqual(f.bread, expect, delta=expect * 0.06)

    def test_offline_equals_online(self):
        """Офлайн считается тем же кодом, что и открытая игра: 10 минут дают тот же результат."""
        for make in (summer_farm, medieval_farm):
            a, b = make(), make()
            got = a.offline_earn(600.0)
            before = b.farm_value()
            for _ in range(6000):
                b.update(0.1)
            want = b.farm_value() - before
            self.assertAlmostEqual(got, want, delta=want * 0.02)

    def test_cap_and_bad_time(self):
        f, g = summer_farm(), summer_farm()
        self.assertAlmostEqual(f.offline_earn(1e9), g.offline_earn(g.offline_cap()), delta=1)
        self.assertEqual(summer_farm().offline_earn(float("nan")), 0.0)
        self.assertEqual(summer_farm().offline_earn(-50), 0.0)

    def test_no_farmer_plot_gives_one_harvest(self):
        f = Farm()
        self.assertEqual(f.offline_earn(HOUR), f.cycle_income(0))
        self.assertTrue(f.ready[0])

    def test_long_offline_is_fast(self):
        import time
        f = summer_farm()
        f.tree["offline"] = 5                  # 13 часов
        t0 = time.time()
        f.offline_earn(13 * HOUR)
        self.assertLess(time.time() - t0, 5.0)


class Selling(unittest.TestCase):
    def loaded(self, make=summer_farm):
        f = make()
        f.run_earned = f.money = 2e12
        f.offline_earn(HOUR)                   # на грядках, в сарае и на мельнице что-то лежит
        return f

    def test_gives_exactly_what_was_promised(self):
        """Ни двойного счёта сарая/мельницы, ни x10 «гигантского урожая» при продаже."""
        for make in (summer_farm, medieval_farm):
            base = self.loaded(make)
            base.tree["lucky"] = 5
            promised = base.potential_leaves()
            self.assertGreaterEqual(promised, cfg.TRUCK_MIN_LEAVES)
            for seed in range(40):
                random.seed(seed)
                f = clone(base)
                self.assertEqual(f.sell_to_truck(), promised)

    def test_sale_resets_run_and_counts_stats(self):
        f = self.loaded()
        total, value, leaves = f.total_earned, f.farm_value(), f.potential_leaves()
        f.sell_to_truck()
        self.assertEqual((f.leaves, f.home_leaves, f.prestiges), (leaves, leaves, 1))
        self.assertAlmostEqual(f.total_earned, total + value, delta=1)
        self.assertEqual((f.run_earned, sum(f.stash), sum(f.a_store), f.levels[1]), (0.0, 0.0, 0.0, 0))

    def test_nothing_happens_without_leaves(self):
        f = Farm()
        f.stash[0] = 50.0
        self.assertEqual(f.sell_to_truck(), 0)
        self.assertEqual((f.stash[0], f.prestiges, f.money), (50.0, 0, 0.0))


class BigNumbers(unittest.TestCase):
    def test_milestones_fast_lookup(self):
        f = Farm()
        for lvl in list(range(0, 1300)) + [2499, 2500, 9999, 10000, 20000]:
            f.levels[0] = lvl
            self.assertEqual(f.speed_steps(0), sum(1 for m in cfg.MILESTONES if lvl >= m))

    def test_infinite_money_does_not_crash(self):
        f = summer_farm()
        for money in (1e300, float("inf")):
            f.money = money
            n = f.max_affordable(0)
            self.assertTrue(0 <= n <= 100_000)
            self.assertIn(f.buy(0, max(1, n)), (True, False))
            self.assertFalse(f.money != f.money)          # не NaN

    def test_money_is_capped(self):
        f = Farm()
        f.earn(1e308)
        f.earn(1e308)
        f.earn(float("nan"))
        self.assertEqual(f.money, cfg.MONEY_CAP)
        self.assertEqual(f.total_earned, cfg.MONEY_CAP)

    def test_max_affordable_is_exact(self):
        f = summer_farm()
        f.money = 1e9
        n = f.max_affordable(3)
        self.assertLessEqual(f.cost(3, n), f.money)
        self.assertGreater(f.cost(3, n + 1), f.money)


class Saves(unittest.TestCase):
    def test_roundtrip(self):
        for make in (summer_farm, medieval_farm):
            f = make()
            f.tree = {"capital": 2, "fertile": 1}
            f.leaves = f.home_leaves = 40
            f.offline_earn(500)
            self.assertEqual(clone(f).to_dict(), f.to_dict())

    def test_garbage_fields_are_skipped(self):
        """Испорченное поле не роняет игру и не стирает остальной прогресс."""
        good = summer_farm()
        good.money, good.leaves, good.home_leaves = 5e9, 162, 162
        base = good.to_dict()
        bad_values = [None, "abc", [], {}, [None] * 9, float("nan"), -5, True, [1, "x", None], {"a": "b"}]
        for key in Farm.FIELDS:
            for bad in bad_values:
                d = copy.deepcopy(base)
                d[key] = bad
                f = Farm()
                f.from_dict(d)                              # не должно бросать
                f.update(0.1)
                f.offline_earn(60)
                f.total_income(), f.potential_leaves(), f.free_peasants(), f.any_tree_affordable()
                json.dumps(f.to_dict())
                if key != "levels":
                    self.assertEqual(f.levels, good.levels, key)
                if key not in ("money", "run_earned", "total_earned"):
                    self.assertGreaterEqual(f.money, 5e9, key)

    def test_not_a_dict(self):
        for bad in (None, [], "x", 5):
            with self.assertRaises(ValueError):
                Farm().from_dict(bad)

    def test_limits(self):
        d = medieval_farm().to_dict()
        d.update(a_levels=[99, 1, 1, 1], m_levels=[99, 99], m_workers=[50, 50], peasants=3,
                 farmers=[True] * 9, farm_index=77, leaves=5, home_leaves=500)
        f = Farm()
        f.from_dict(d)
        self.assertEqual(f.farm_index, len(cfg.FARMS) - 1)
        self.assertEqual(f.a_levels[0], cfg.ANIMAL_MAX_LVL)
        self.assertEqual(f.m_levels, [cfg.MILL_MAX_LVL] * 2)
        self.assertLessEqual(f.home_leaves, f.leaves)

    def test_peasants_never_overbooked(self):
        d = medieval_farm().to_dict()
        d.update(peasants=3, farmers=[True] * 9, m_workers=[2, 1])
        f = Farm()
        f.from_dict(d)
        self.assertEqual(f.free_peasants(), 0)
        self.assertEqual(f.busy_peasants(), 3)

    def test_longer_lists_from_future_version(self):
        d = summer_farm().to_dict()
        d["a_levels"] = [1, 2, 3, 4, 5, 6]
        d["levels"] = [5] * 12
        f = Farm()
        f.from_dict(d)
        self.assertEqual(len(f.a_levels), cfg.N_ANIMALS)
        self.assertEqual(len(f.levels), cfg.N_CROPS)

    def test_old_save_without_new_fields(self):
        f = Farm()
        f.from_dict({"leaves": 7, "levels": [3, 1], "money": 10})
        self.assertEqual((f.leaves, f.home_leaves, f.levels[:3], f.money), (7, 7, [3, 1, 0], 10.0))


if __name__ == "__main__":
    unittest.main()
