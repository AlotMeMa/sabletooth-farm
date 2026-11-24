# -*- coding: utf-8 -*-
"""3.20: вышел из таверны и вернулся за 5 секунд — песня играет дальше с того же места, позже — сначала."""
import ast
import os
import types
import unittest

from tests import helpers

AUDIO = os.path.join(helpers.ROOT, "farmgame", "audio.py")


def load_music():
    """Класс Music и длина трека без pygame: заглушка проигрывателя запоминает, с какой секунды включили."""
    with open(AUDIO, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    keep = [n for n in tree.body if (isinstance(n, ast.ClassDef) and n.name == "Music")
            or (isinstance(n, ast.FunctionDef) and n.name in ("track_length", "_ogg_length", "_wav_length"))
            or (isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id in ("RESUME_SECONDS", "FADE_MS", "_lengths"))]
    clock = {"now": 1000.0}
    player = {"pos_ms": -1, "start": None}

    def play(loops=0, start=0.0, fade_ms=0):
        player["start"], player["pos_ms"] = start, 0

    music = types.SimpleNamespace(stop=lambda: None, load=lambda p: None, set_volume=lambda v: None, play=play,
                                  get_pos=lambda: player["pos_ms"])
    pg = types.SimpleNamespace(mixer=types.SimpleNamespace(get_init=lambda: True, init=lambda: None, music=music))
    ns = {"pygame": pg, "os": os, "ASSET_DIR": os.path.join(helpers.ROOT, "assets"), "print": lambda *a, **k: None, "time": types.SimpleNamespace(time=lambda: clock["now"]),
          "find_music": lambda farm_id, scene=None: os.path.join(helpers.ROOT, "assets", "music",
                                                                 (scene or farm_id) + ".ogg"),
          }
    exec(compile(ast.Module(body=keep, type_ignores=[]), AUDIO, "exec"), ns)
    return ns["Music"](), clock, player


class MusicResume(unittest.TestCase):
    def setUp(self):
        self.m, self.clock, self.player = load_music()
        if not os.path.exists(os.path.join(helpers.ROOT, "assets", "music", "tavern_girl.ogg")):
            self.skipTest("нет assets/music/tavern_girl.ogg")

    def visit(self, seconds_in_tavern, seconds_away):
        m, p = self.m, self.player
        m.play_for("summer", "tavern_girl")
        p["pos_ms"] = int(seconds_in_tavern * 1000)
        m.play_for("summer")                      # вышел на поле
        self.clock["now"] += seconds_away
        m.play_for("summer", "tavern_girl")       # вернулся
        return p["start"]

    def test_quick_return_continues(self):
        self.assertAlmostEqual(self.visit(42.0, 3.0), 42.0, places=2)
        self.player["pos_ms"] = 500
        self.assertAlmostEqual(self.m.position(), 42.5, places=2)    # такт барда считается от места в песне

    def test_late_return_starts_over(self):
        self.assertIn(self.visit(42.0, 6.0), (0, 0.0, None))

    def test_wraps_after_loop(self):
        start = self.visit(234.88 + 10.0, 1.0)     # песня уже пошла по второму кругу
        self.assertAlmostEqual(start, 10.0, delta=0.05)


if __name__ == "__main__":
    unittest.main()
