# -*- coding: utf-8 -*-
"""3.38: аквариум Рыбацкой деревни — рыбки по одной, рост, икра, хищник по таймеру, тлеющий отсчёт."""
import ast
import json
import os
import random
import unittest

from tests import helpers  # noqa: F401
from farmgame import config as cfg
from farmgame.logic import Farm


def village(levels=10):
    f = Farm()
    f.farm_index = 3
    f.reset_run()
    f.levels = [levels] * cfg.N_CROPS
    f.money = 1e18
    return f


class Aquarium(unittest.TestCase):
    def setUp(self):
        random.seed(3)

    def test_predators_five_ranks_two_each(self):
        ranks = [p["rank"] for p in cfg.PREDATORS]
        for r in range(1, 6):
            self.assertEqual(ranks.count(r), 2)
        for a, b in zip(cfg.PREDATORS, cfg.PREDATORS[1:]):
            self.assertLessEqual(a["rank"], b["rank"])
            self.assertLess(a["ratio"], b["ratio"])
            self.assertLess(a["diff"], b["diff"])

    def test_only_in_fishing_village(self):
        f = Farm()
        f.money = 1e18
        self.assertFalse(f.buy_fish(0))
        f.update(1000)
        self.assertFalse(f.fy_pred)

    def test_buy_one_fish_and_dearer_species(self):
        f = village()
        self.assertGreater(f.fish_price(8), f.fish_price(0))      # золотая дороже плотвы
        m = f.money
        self.assertTrue(f.buy_fish(8))
        self.assertEqual(len(f.fy_fish), 1)
        self.assertAlmostEqual(m - f.money, f.fish_price(8))
        f.levels[3] = 0
        self.assertFalse(f.buy_fish(3))                           # закрытого участка нет в лавке

    def test_grows_to_five_times(self):
        f = village()
        f.buy_fish(0)
        price = f.fy_fish[0][1]
        f.update(cfg.FISH_GROW[0] / 2)
        self.assertAlmostEqual(f.fish_worth(f.fy_fish[0]), price * 3, delta=price * 1e-6)
        f.update(cfg.FISH_GROW[0])
        self.assertEqual(f.fy_fish[0][2], 1.0)
        m = f.money
        amt, n = f.sell_adults()
        self.assertEqual(n, 1)
        self.assertAlmostEqual(amt, price * cfg.FISH_ADULT_MULT)
        self.assertAlmostEqual(f.money - m, amt, delta=1e3)

    def test_festival_speeds_growth(self):
        a, b = village(), village()
        a.buy_fish(2), b.buy_fish(2)
        b.rain_left = 1000
        a.update(30), b.update(30)
        self.assertGreater(b.fy_fish[0][2], a.fy_fish[0][2])

    def test_capacity_and_upgrades(self):
        f = village()
        self.assertEqual(f.fy_cap, cfg.FISH_TANK_START)
        for _ in range(cfg.FISH_TANK_START):
            self.assertTrue(f.buy_fish(0))
        self.assertFalse(f.buy_fish(0))
        while f.tank_cost() is not None:
            self.assertTrue(f.upgrade_tank())
        self.assertEqual(f.fy_cap, cfg.FISH_TANK_MAX)
        self.assertFalse(f.upgrade_tank())

    def test_pair_lays_roe_that_hatches(self):
        f = village()
        f.fy_cap = 25
        f.buy_fish(1), f.buy_fish(1), f.buy_fish(5)
        for fish in f.fy_fish:
            fish[2] = 1.0
        f.fy_timer = 1e9                                          # без хищника
        for _ in range(600):
            f.update(1.0)
            if f.fy_eggs:
                break
        self.assertTrue(f.fy_eggs)
        self.assertEqual(f.fy_eggs[0][0], 2)                      # икра от пары карасей, не от одиночки
        egg = list(f.fy_eggs[0])
        n = len(f.fy_fish)
        f.update(cfg.FISH_HATCH / 2)
        self.assertEqual(f.fy_eggs[0][1:3], egg[1:3])             # висит на месте
        f.update(cfg.FISH_HATCH)
        self.assertGreater(len(f.fy_fish), n)
        self.assertIn([2], [[x[0]] for x in f.fy_fish if x[2] < 1.0])

    def test_predator_timer_eats_and_catch(self):
        f = village()
        for _ in range(5):
            f.buy_fish(4)
        f.update(cfg.FISH_PRED_EVERY - 1)
        self.assertFalse(f.fy_pred)
        f.update(2)
        self.assertEqual(f.predator()["rank"], 1)                 # первый в забеге — 1 ранга
        base = f.fy_pred_val
        f.update(cfg.FISH_BITE + 0.1)
        self.assertEqual(len(f.fy_fish), 4)
        self.assertGreater(f.fy_pred_val, base)
        m = f.money
        amt, p = f.catch_predator()
        self.assertAlmostEqual(f.money - m, amt, delta=1e3)
        self.assertFalse(f.fy_pred)
        self.assertEqual(f.fy_timer, cfg.FISH_PRED_EVERY)

    def test_predator_spares_roe_and_leaves_after_grace(self):
        f = village()
        f.buy_fish(0)
        f.fy_eggs.append([1, 0.5, 0.5, 1e9])
        f.spawn_predator()
        f.update(cfg.FISH_BITE + 0.1)
        self.assertFalse(f.fy_fish)
        self.assertEqual(len(f.fy_eggs), 1)                       # икру не трогает
        f.update(0.5)
        self.assertIsNotNone(f.grace_left())
        self.assertLess(f.grace_left(), 1.0)
        f.update(cfg.FISH_GRACE)
        self.assertFalse(f.fy_pred)                               # не успел — уплыл
        self.assertIn("left", [e[0] for e in f.fy_events])

    def test_new_fish_stops_grace(self):
        f = village()
        f.spawn_predator()
        f.update(1.0)
        self.assertIsNotNone(f.grace_left())
        f.buy_fish(0)
        self.assertIsNone(f.grace_left())

    def test_rank_climbs_but_not_always(self):
        ups = 0
        for seed in range(200):
            random.seed(seed)
            f = village()
            f.fy_rank = 2
            f.next_rank()
            r = f.next_rank()
            ups += r > 2
        self.assertLess(ups / 200, 0.9)
        self.assertGreater(ups / 200, 0.2)
        f = village()
        f.fy_rank = 3
        for _ in range(30):
            f.fy_rank = 3
            if f.next_rank() == 3:
                self.assertLessEqual(f.fy_up, cfg.FISH_UP_MAX)

    def test_first_predator_stronger_after_runs(self):
        def first_ranks(runs):
            out = []
            for seed in range(300):
                random.seed(seed)
                f = village()
                f.fy_runs = runs
                out.append(f.next_rank())
            return out
        self.assertEqual(set(first_ranks(0)), {1})
        later = first_ranks(3)
        self.assertGreater(sum(later) / len(later), 1.2)
        f = village()
        f.money = 1e300
        f.run_earned = 1e300
        if f.potential_leaves() > 0:
            f.sell_to_truck()
            self.assertEqual(f.fy_runs, 1)

    def test_no_predators_offline(self):
        f = village()
        for _ in range(5):
            f.buy_fish(0)
        f.offline_earn(3600)
        self.assertFalse(f.fy_pred)
        self.assertTrue(all(x[2] >= 1 for x in f.fy_fish))      # а рыба выросла
        self.assertFalse(f.fy_events)

    def test_value_counts_in_run_total(self):
        f = village()
        before = f.run_total()
        f.buy_fish(6)
        self.assertGreater(f.run_total(), before - f.fish_price(6) - 1)
        self.assertAlmostEqual(f.aquarium_value(), f.fish_price(6))

    def test_save_roundtrip_and_sanitize(self):
        f = village()
        f.fy_cap = 13
        for i in (0, 3, 3, 8):
            f.buy_fish(i)
        f.fy_eggs.append([4, 0.3, 0.7, 12.0])
        f.spawn_predator()
        f.update(20)
        g = Farm()
        g.from_dict(json.loads(json.dumps(f.to_dict())))
        for k in ("fy_fish", "fy_eggs", "fy_cap", "fy_pred", "fy_pred_val", "fy_pred_eaten", "fy_timer", "fy_rank",
                  "fy_up", "fy_runs"):
            self.assertEqual(getattr(g, k), getattr(f, k), k)
        d = f.to_dict()
        d.update(fy_fish=[[99, 1, 0.5, 3], "рыба", [2, -5, 7, 1], [3, 1, 0.2]], fy_eggs=[[0, 0.5, 0.5, 1]],
                 fy_cap=999, fy_pred=77, fy_rank=9)
        g = Farm()
        g.from_dict(d)
        self.assertEqual(g.fy_fish, [[2, 0.0, 1.0, 1]])
        self.assertEqual(g.fy_eggs, [])
        self.assertEqual(g.fy_cap, cfg.FISH_TANK_MAX)
        self.assertEqual(g.fy_pred, 0)
        self.assertLessEqual(g.fy_rank, 5)


class PredatorArt(unittest.TestCase):
    def test_sheet_order_matches_predators(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "farmgame", "spritefit.py"), encoding="utf-8") as fh:
            src = fh.read()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "PREDATOR_SHEET_ORDER":
                order = ast.literal_eval(node.value)
        self.assertEqual(order, [p["id"] for p in cfg.PREDATORS])


if __name__ == "__main__":
    unittest.main()
