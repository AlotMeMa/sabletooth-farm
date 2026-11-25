# -*- coding: utf-8 -*-
"""3.37: рыборазводня — нерестовый садок и садок хищников."""
import json
import unittest

from tests import helpers  # noqa: F401
from farmgame import config as cfg
from farmgame.logic import Farm


def village():
    f = Farm()
    f.farm_index = 3
    f.reset_run()
    f.levels = [10] * cfg.N_CROPS
    f.money = 1e18
    return f


class Fishery(unittest.TestCase):
    def test_predators_five_ranks_two_each(self):
        ranks = [p["rank"] for p in cfg.PREDATORS]
        self.assertEqual(sorted(set(ranks)), [1, 2, 3, 4, 5])
        for r in range(1, 6):
            self.assertEqual(ranks.count(r), 2)
        self.assertEqual(len(cfg.PRED_RANK_NAMES), 6)
        for a, b in zip(cfg.PREDATORS, cfg.PREDATORS[1:]):   # чем дальше, тем дороже, выгоднее и сложнее
            self.assertLess(a["cost"], b["cost"])
            self.assertLess(a["ratio"], b["ratio"])
            self.assertLess(a["diff"], b["diff"])

    def test_only_in_fishing_village(self):
        f = Farm()
        self.assertFalse(f.has_fishery())
        self.assertFalse(f.stock_fish(0))
        self.assertTrue(village().has_fishery())

    def test_costlier_fish_earns_more(self):
        f = village()
        f.levels = [10, 10, 10, 10, 10, 10, 10, 10, 10]
        self.assertGreater(f.fish_value(8), f.fish_value(0))           # золотая дороже плотвы
        self.assertGreater(f.fish_stock_cost(8), f.fish_stock_cost(0))

    def test_stock_and_switch_species(self):
        f = village()
        self.assertTrue(f.stock_fish(2))
        self.assertEqual((f.fy_species, f.fy_pop), (3, cfg.FISH_STOCK))
        f.stock_fish(2)
        self.assertEqual(f.fy_pop, min(cfg.FISH_POND_CAP[0], 2 * cfg.FISH_STOCK))
        f.stock_fish(5)                                                # другой вид — садок заново
        self.assertEqual((f.fy_species, f.fy_pop), (6, cfg.FISH_STOCK))
        f.levels[7] = 0
        self.assertFalse(f.stock_fish(7))                              # закрытый участок не разводят

    def test_breeding_stays_within_cap(self):
        f = village()
        f.stock_fish(0)
        for _ in range(2000):
            f.update(1.0)
        self.assertLessEqual(f.fy_pop, f.fish_cap())
        self.assertGreater(f.fy_pop, f.fish_cap() * 0.95)

    def test_predator_eats_grows_and_sells(self):
        f = village()
        f.stock_fish(8)
        self.assertTrue(f.buy_predator(0, 0))
        self.assertFalse(f.buy_predator(0, 1))                         # место занято
        self.assertFalse(f.buy_predator(1, 0))                         # место не открыто
        self.assertLess(f.predator_kg(0), 1.0)
        for _ in range(3000):
            f.update(1.0)
            self.assertGreaterEqual(f.fy_pop, f.fish_floor() - 1e-9)   # маточное стадо не трогают
        self.assertTrue(f.predator_full(0))
        self.assertAlmostEqual(f.predator_kg(0), cfg.PREDATORS[0]["kg"])
        val = f.fy_value[0]
        self.assertAlmostEqual(val, cfg.PREDATORS[0]["fish"] * f.fish_value(8) * cfg.PREDATORS[0]["ratio"], delta=val * 1e-6)
        m = f.money
        amt, p = f.catch_predator(0)
        self.assertEqual(p["id"], "pike")
        self.assertGreater(f.money, m)
        self.assertEqual(f.fy_type[0], 0)
        self.assertIsNone(f.catch_predator(0))

    def test_slots_and_pond_upgrades(self):
        f = village()
        for n in range(cfg.FISH_SLOTS - 1):
            self.assertTrue(f.buy_fish_slot())
        self.assertIsNone(f.fish_slot_cost())
        self.assertFalse(f.buy_fish_slot())
        for _ in range(len(cfg.FISH_POND_CAP) - 1):
            self.assertTrue(f.upgrade_fish_pond())
        self.assertEqual(f.fish_cap(), cfg.FISH_POND_CAP[-1])
        self.assertIsNone(f.fish_pond_cost())

    def test_save_roundtrip_and_sanitize(self):
        f = village()
        f.stock_fish(4)
        f.buy_fish_slot()
        f.buy_predator(1, 3)
        for _ in range(300):
            f.update(1.0)
        g = Farm()
        g.from_dict(json.loads(json.dumps(f.to_dict())))
        for k in ("fy_species", "fy_pop", "fy_lvl", "fy_slots", "fy_type", "fy_eaten", "fy_value"):
            self.assertEqual(getattr(g, k), getattr(f, k), k)
        d = f.to_dict()
        d.update(fy_species=99, fy_lvl=99, fy_slots=99, fy_type=[77, 1], fy_eaten="x")
        g = Farm()
        g.from_dict(d)
        self.assertLessEqual(g.fy_species, cfg.N_CROPS)
        self.assertLessEqual(g.fy_lvl, len(cfg.FISH_POND_CAP))
        self.assertLessEqual(g.fy_slots, cfg.FISH_SLOTS)
        self.assertEqual(len(g.fy_type), cfg.FISH_SLOTS)
        self.assertTrue(all(0 <= t <= len(cfg.PREDATORS) for t in g.fy_type))
        self.assertEqual(len(g.fy_eaten), cfg.FISH_SLOTS)

    def test_predator_value_counts_in_run_total(self):
        f = village()
        f.stock_fish(4)
        f.buy_predator(0, 0)
        for _ in range(200):
            f.update(1.0)
        self.assertGreater(f.fy_value[0], 0)


if __name__ == "__main__":
    unittest.main()


class PredatorArt(unittest.TestCase):
    def test_sheet_order_matches_predators(self):
        import ast, os
        src = open(os.path.join(os.path.dirname(__file__), "..", "farmgame", "spritefit.py"), encoding="utf-8").read()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "PREDATOR_SHEET_ORDER":
                order = ast.literal_eval(node.value)
        self.assertEqual(order, [p["id"] for p in cfg.PREDATORS])
