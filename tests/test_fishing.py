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
        self.assertTrue(fm["ready"])                        # 3.44: открыта (все картинки есть)
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

    def test_move_from_winter_to_village(self):
        f = Farm()
        f.farm_index = 2
        f.reset_run()
        self.assertTrue(f.has_next_farm())                  # 3.44: с зимы переезжаем в деревню
        f.earn(f.move_threshold())
        self.assertTrue(f.can_move())
        f.move_farm()
        self.assertEqual(f.farm_def()["id"], "fishing")
        self.assertFalse(f.has_next_farm())                 # дальше пока ничего

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
            if fm["id"] not in ("fishing", "dragons"):     # 3.48: фон драконов нарисован под раскладку деревни
                self.assertEqual(fm["theme"].get("field_dy", 0), 0)
                self.assertTrue(fm["theme"].get("fence", True))

    def test_buyer_comes_by_boat(self):
        """3.38.1: решение пользователя 26.11 — за уловом приходит лодка, не повозка."""
        fm = next(f for f in cfg.FARMS if f["id"] == "fishing")
        self.assertEqual(fm["vehicle"], "boat")
        self.assertEqual(len(fm["tiers"]), 3)
        self.assertIn("лодка", fm["arrive"])


class Helpers345(unittest.TestCase):
    """3.45: помощников не больше, чем мест для них; убранный приз возвращает жетоны."""
    def test_peasant_max_by_farm(self):
        f = Farm()
        for idx, want in ((1, 16), (2, cfg.N_CROPS), (3, cfg.N_CROPS)):
            f.farm_index = idx
            f.reset_run()
            self.assertEqual(f.peasant_max(), want)
        f.money = 1e30
        while f.hire_peasant():
            pass
        self.assertEqual(f.peasants, cfg.N_CROPS)

    def test_extra_fishermen_from_old_save_let_go(self):
        f = Farm()
        f.farm_index = 3
        f.reset_run()
        d = f.to_dict()
        d["peasants"] = 16
        g = Farm()
        g.from_dict(d)
        self.assertEqual(g.peasants, cfg.N_CROPS)

    def test_rocking_chair_refund(self):
        from farmgame.tavern import Tavern
        t = Tavern()
        d = t.to_dict()
        d["tokens"] = 10
        d["prizes"] = {"rocking_chair": True, "cat": True}
        t2 = Tavern()
        t2.from_dict(d)
        self.assertEqual(t2.tokens, 10 + cfg.REMOVED_PRIZES["rocking_chair"])
        self.assertNotIn("rocking_chair", t2.prizes)
        self.assertTrue(t2.prizes.get("cat"))
