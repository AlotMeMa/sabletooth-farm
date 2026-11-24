# -*- coding: utf-8 -*-
"""3.24: заготовка зимней главы — данные сходятся, лето и средневековье не задеты."""
import os
import re
import unittest

from tests import helpers
from farmgame import config as cfg


class WinterData(unittest.TestCase):
    def winter(self):
        return next(fm for fm in cfg.FARMS if fm["id"] == "winter")

    def test_names_plants_and_currency(self):
        w = self.winter()
        self.assertEqual(len(w["names"]), cfg.N_CROPS)
        self.assertEqual(len(w["plants"]), cfg.N_CROPS)
        self.assertEqual(w["cur"], "frost")
        self.assertEqual(cfg.CURRENCIES["frost"]["tree"], "ЗИМНЕЕ ДЕРЕВО")
        self.assertEqual(w["vehicle"], "sled")
        self.assertIn("winter", cfg.TREES)

    def test_every_plant_has_code_drawing(self):
        with open(os.path.join(helpers.ROOT, "farmgame", "art_world.py"), encoding="utf-8") as f:
            art = f.read()
        known = set(re.findall(r'"(\w+)": plant_\w+', art))
        for fm in cfg.FARMS:
            for key in fm["plants"]:
                self.assertIn(key, known, f"{fm['id']}: нет рисунка кодом для {key}")

    def test_winter_animals_match_summer_balance(self):
        for s, w in zip(cfg.ANIMALS_SUMMER, cfg.ANIMALS_WINTER):
            for k in ("crop", "ratio", "time", "cost", "keeper"):
                self.assertEqual(s[k], w[k])
            self.assertNotEqual(s["key"], w["key"])
        self.assertEqual([a["name"] for a in cfg.ANIMALS], [a["name"] for a in cfg.ANIMALS_SUMMER])  # сейчас лето

    def test_winter_still_closed(self):
        self.assertFalse(self.winter()["ready"])


if __name__ == "__main__":
    unittest.main()
