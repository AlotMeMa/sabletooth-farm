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
        with open(os.path.join(helpers.ROOT, "farmgame", "art_fishing.py"), encoding="utf-8") as f:
            known |= set(re.findall(r'^    "(\w+)": \(\(', f.read(), re.M))      # 3.36: рыбы Рыбацкой деревни
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

    def test_winter_is_open(self):
        """3.35: зима открыта для игроков — со средневековья можно переехать."""
        from farmgame.logic import Farm
        self.assertTrue(self.winter()["ready"])
        f = Farm()
        f.farm_index = 1
        f.reset_run()
        self.assertTrue(f.has_next_farm())
        f.run_earned = f.move_threshold()
        self.assertTrue(f.move_farm())
        self.assertEqual(f.farm_def()["id"], "winter")

    def test_medieval_trophy_gives_helpers(self):
        from farmgame.logic import Farm
        f = Farm()
        f.farm_index = 1
        f.reset_run()
        before = f.peasants
        f.farm_index = 2
        f.reset_run()
        self.assertEqual(f.peasants, before + cfg.TROPHY_HELPERS)
        self.assertEqual(f.levels[0], cfg.TROPHY_START_LEVEL)       # и летний трофей по-прежнему работает

    def test_finale_achievement(self):
        from farmgame.logic import Farm
        from farmgame import achievements as ach
        f, t = Farm(), __import__("farmgame.tavern", fromlist=["x"]).Tavern()
        f.farm_index = 2
        f.reset_run()
        self.assertNotIn("final_1", [a["id"] for a in ach.check(f, t)])
        f.run_earned = f.move_threshold()
        self.assertIn("final_1", [a["id"] for a in ach.check(f, t)])
        f.reset_run()                      # после продажи упряжке достижение не пропадает
        self.assertIn("final_1", t.ach_done)


if __name__ == "__main__":
    unittest.main()


class WinterTree(unittest.TestCase):
    """3.29: своё Зимнее дерево — названия под зиму, без летних узлов, которые зимой не работают."""

    def test_names_and_nodes(self):
        tree = cfg.TREES["winter"]
        branches = [b for b, _ in tree]
        self.assertIn(cfg.GNOME_RUSH, branches)
        ids = [n["id"] for _, nodes in tree for n in nodes]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn("farmers", ids)        # зимой гномы — артель (serfs), как крестьяне
        self.assertNotIn("scarecrow", ids)      # ворон зимой нет
        self.assertIn("warmbeds", ids)
        self.assertIn("icepick", ids)
        for _, nodes in tree:
            for n in nodes:
                for lvl in range(len(n["costs"]) + 1):
                    text = n["eff"](lvl)
                    self.assertIsInstance(text, str)
                    self.assertNotIn("грузовик", text)
                    self.assertNotIn("дожд", text)
                    self.assertNotIn("листьев", text)
        summer = {n["name"] for _, nodes in cfg.TREES["summer"] for n in nodes}
        winter = {n["name"] for _, nodes in tree for n in nodes}
        self.assertFalse(summer & winter, summer & winter)   # все названия свои
