# -*- coding: utf-8 -*-
"""3.36: Рыбацкая деревня (4-я глава, пока закрыта) — данные главы."""
import unittest

from tests import helpers  # noqa: F401
from farmgame import config as cfg
from farmgame.logic import Farm


class FishingVillage(unittest.TestCase):
    def fm(self):
        return next(f for f in cfg.FARMS if f["id"] == "fishing")

    def test_chapter_data(self):
        fm = self.fm()
        self.assertEqual(cfg.FARMS.index(fm), 3)
        self.assertFalse(fm["ready"])                       # пока собираем — закрыта
        self.assertEqual(len(fm["names"]), cfg.N_CROPS)
        self.assertEqual(len(fm["plants"]), cfg.N_CROPS)
        self.assertEqual(fm["helpers"], "fishermen")
        self.assertIn(fm["weather"], cfg.WEATHER_BUTTON)
        self.assertTrue(fm["rush_helpers"] and fm["peasants"] and fm["crow"])
        self.assertEqual(fm["cur"], "hook")
        self.assertEqual(fm["barn"], "fishery")
        self.assertTrue(fm["theme"]["pond"])

    def test_tree_uses_known_upgrades(self):
        summer_ids = {n["id"] for _b, nodes in cfg.TREE_SUMMER for n in nodes}
        fishing_ids = {n["id"] for _b, nodes in cfg.TREE_FISHING for n in nodes}
        self.assertTrue(fishing_ids <= summer_ids | {"serfs"})
        self.assertNotIn("farmers", fishing_ids)           # рыбаки — артель, наёмных фермеров нет

    def test_winter_is_not_last_but_move_closed(self):
        f = Farm()
        f.farm_index = 2
        f.reset_run()
        self.assertFalse(f.has_next_farm())                 # глава закрыта — с зимы не переехать

    def test_quest_words(self):
        from farmgame import tavern as tv
        t, fm = tv.Tavern(), self.fm()
        q = {x["id"]: x for x in tv.QUESTS}
        self.assertIn("чаек", t._quest_text(q["crow"], 5, fm))
        self.assertIn("краба", t._quest_text(q["squirrel"], 3, fm))
        self.assertIn("рыбаков", t._quest_text(q["peasant"], 5, fm))
        self.assertIn("рыботорговцу", t._quest_text(q["truck"], 1, fm))
        self.assertIn("фестиваль", t._quest_text(q["weather"], 2, fm))

    def test_fishing_farm_starts(self):
        f = Farm()
        f.farm_index = 3
        f.reset_run()
        self.assertEqual(f.farm_def()["id"], "fishing")
        self.assertEqual(f.peasants, cfg.PEASANT_START + cfg.TROPHY_HELPERS)
        self.assertEqual(f.levels[0], cfg.TROPHY_START_LEVEL)
        f.update(5.0)


if __name__ == "__main__":
    unittest.main()


class FishingScene(unittest.TestCase):
    """3.38.1: живой фон деревни — поле ниже, без забора, точки окон/дыма/дверей в пределах экрана."""

    def test_scene_points_on_screen(self):
        th = cfg.THEME_FISHING
        self.assertFalse(th["fence"])
        self.assertGreater(th["field_dy"], 0)
        sc = th["scene"]
        for key in ("windows", "smoke", "doors", "dance"):
            for pt in sc[key]:
                self.assertTrue(0 <= pt[0] <= cfg.W and 0 <= pt[1] <= cfg.H, (key, pt))
        self.assertEqual(len(sc["doors"]), 3)               # рыбаки выходят из трёх домов

    def test_other_farms_keep_field_and_fence(self):
        for fm in cfg.FARMS:
            if fm["id"] != "fishing":
                self.assertEqual(fm["theme"].get("field_dy", 0), 0)
                self.assertTrue(fm["theme"].get("fence", True))
