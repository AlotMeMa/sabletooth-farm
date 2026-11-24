# -*- coding: utf-8 -*-
"""3.19: магазин таверны — только косметика; посиделки у камина (украшения видны, звук камина по кругу)."""
import ast
import math
import os
import random
import re
import unittest

from tests import helpers
from farmgame.config import PRIZES

GAME = os.path.join(helpers.ROOT, "farmgame")


def source(name):
    with open(os.path.join(GAME, name), encoding="utf-8") as f:
        return f.read()


def functions(name, wanted):
    """Достаёт функции из файла игры без импорта (модулю нужен pygame) и возвращает их."""
    tree = ast.parse(source(name))
    mod = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted],
                     type_ignores=[])
    ns = {"math": math, "random": random}
    exec(compile(mod, name, "exec"), ns)
    return ns


class CosmeticShop(unittest.TestCase):
    def test_every_prize_has_code_icon(self):
        body = source("casino_ui.py")
        body = body[body.index("def draw_prize_icon"):]
        for p in PRIZES:
            self.assertIn(f'"{p["id"]}"', body, f"нет значка кодом для приза {p['id']}")

    def test_every_cosmetic_is_visible_somewhere(self):
        code = "".join(source(n) for n in os.listdir(GAME) if n.endswith(".py"))
        for p in PRIZES:
            if p["kind"] == "cosmetic" and not p.get("stage"):     # артисты сцены рисуются через stage_artist()
                self.assertTrue(f'prize_on("{p["id"]}")' in code, f"украшение {p['id']} нигде не рисуется")

    def test_ids_unique(self):
        ids = [p["id"] for p in PRIZES]
        self.assertEqual(len(ids), len(set(ids)))


class StageArtists(unittest.TestCase):
    def test_one_artist_on_stage(self):
        from farmgame.tavern import Tavern
        from farmgame.logic import Farm
        t, f = Tavern(), Farm()
        t.tokens = 10 ** 5
        self.assertIsNone(t.stage_artist())
        t.buy_prize(f, "bard_girl")
        self.assertEqual(t.stage_artist()["id"], "bard_girl")
        t.buy_prize(f, "fiddler")                         # купил нового — он сразу на сцене, Мила ушла
        self.assertEqual(t.stage_artist()["id"], "fiddler")
        self.assertFalse(t.prize_on("bard_girl"))
        t.toggle_prize("bard_girl")                       # вернул Милу — скрипач ушёл
        self.assertEqual(t.stage_artist()["id"], "bard_girl")
        self.assertFalse(t.prize_on("fiddler"))
        t.toggle_prize("bard_girl")                       # выключил — снова бард
        self.assertIsNone(t.stage_artist())

    def test_artists_have_code_look_and_lines(self):
        from farmgame import tavern as tv
        art = source("tavern_art.py")
        for p in PRIZES:
            if p.get("stage"):
                self.assertIn(f'"{p["id"]}": dict(', art)
                self.assertTrue(getattr(tv, tv.ARTIST_LINES[p["id"]]))


class FiresideSound(unittest.TestCase):
    def test_sounds_are_known(self):
        info = source("audio.py")
        for name in ("fire", "spark"):
            self.assertRegex(info, rf'"{name}":\s*"', f"звука {name} нет в SFX_INFO")
        self.assertIn('"fire": 1.7', source("tavern_ui.py"))

    def test_fire_loop_has_no_click_at_seam(self):
        ns = functions("audio.py", {"_crackles", "_fire"})
        rate = 8000
        loop = ns["_fire"](rate, dur=2.0)
        self.assertEqual(len(loop), 2 * int(rate // 2 * 2.0))
        self.assertLessEqual(max(abs(v) for v in loop), 0.51)
        steps = [abs(b - a) for a, b in zip(loop, loop[1:])]
        self.assertLess(abs(loop[0] - loop[-1]), max(steps) + 1e-9)    # стык не резче обычного щелчка

    def test_spark_is_short(self):
        ns = functions("audio.py", {"_crackles"})
        out = ns["_crackles"](8000, 0.9, 26, 0.7, seed=5)
        self.assertEqual(len(out), int(8000 * 0.9))
        self.assertTrue(any(abs(v) > 0.05 for v in out))


class FiresideView(unittest.TestCase):
    def test_view_is_wired(self):
        app = source("app.py")
        self.assertIn('"fireside": self.draw_fireside_view', app)
        self.assertIn("FiresideUI", app)
        self.assertRegex(app, r'view in \("board", "casino", "fireside"\):\s*\n\s*self.view = "tavern"')   # Esc — встать

    def test_layout_has_fireplace_zone(self):
        art = source("tavern_art.py")
        self.assertEqual(len(re.findall(r"fireside=\[", art)), 2)        # свой фон и нарисованный кодом
        self.assertEqual(len(re.findall(r"decor=dict\(", art)), 2)


if __name__ == "__main__":
    unittest.main()
