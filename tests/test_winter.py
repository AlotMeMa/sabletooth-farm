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

    def test_gnomes_and_gnome_rush(self):
        w = self.winter()
        self.assertTrue(w["peasants"])
        self.assertEqual(cfg.HELPERS[w["helpers"]]["title"], "Гномы")
        self.assertEqual(w["weather"], "Гномье пришествие")
        self.assertEqual(cfg.WEATHER_BUTTON[w["weather"]], "shaman")
        self.assertTrue(w.get("rush_helpers"))
        self.assertEqual(len(cfg.SHAMAN_SPOTS), 2)

    def test_gnome_rush_works_every_bed(self):
        """3.26: пока идёт пришествие, грядки без своего гнома копят урожай сами; кончилось — снова ждут."""
        from farmgame.logic import Farm
        f = Farm()
        f.farm_index = next(n for n, fm in enumerate(cfg.FARMS) if fm["id"] == "winter")
        f.levels[0] = 1
        f.farmers[0] = False
        t = f.cycle_time(0)
        f.update(t * 1.01)                       # без пришествия: созрела и ждёт
        self.assertTrue(f.ready[0])
        one = f.stash[0]
        self.assertFalse(f.helper_rush())
        f.rain_cd = 0
        self.assertTrue(f.start_rain())
        self.assertTrue(f.helper_rush() and f.working(0))
        f.update(0.001)                          # созревшее не считается дважды
        self.assertAlmostEqual(f.stash[0], one)
        for _ in range(5):
            f.update(t / f.growth_speed() * 1.001)
        self.assertGreater(f.stash[0], one * 4)  # гном работал: урожай копится, грядка не ждёт
        self.assertFalse(f.ready[0])
        f.rain_left = 0.0
        self.assertFalse(f.helper_rush())

    def test_summer_rain_has_no_rush(self):
        from farmgame.logic import Farm
        f = Farm()
        f.rain_cd = 0
        f.start_rain()
        self.assertFalse(f.helper_rush())

    def test_quest_says_gnomes(self):
        from farmgame import tavern as tv
        tpl = next(q for q in tv.QUESTS if q["id"] == "peasant")
        t = tv.Tavern()
        self.assertIn("гном", t._quest_text(tpl, 3, self.winter()))
        self.assertIn("крестьян", t._quest_text(tpl, 3, cfg.FARMS[1]))

    def test_winter_still_closed(self):
        self.assertFalse(self.winter()["ready"])


if __name__ == "__main__":
    unittest.main()
