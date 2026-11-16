# -*- coding: utf-8 -*-
"""3.10: геометрия полного экрана без чёрных полос."""
import unittest

from tests import helpers  # noqa: F401
from farmgame import screenfit as sf


class WideGeometry(unittest.TestCase):
    def test_16_9_adds_side_margins(self):
        (ww, wh), (ox, oy) = sf.wide_geometry((1500, 960), (1920, 1080))
        self.assertEqual(wh, 960)
        self.assertAlmostEqual(ww / wh, 1920 / 1080, places=2)
        self.assertEqual(oy, 0)
        self.assertEqual(ox, (ww - 1500) // 2)
        self.assertGreater(ox, 50)

    def test_4_3_adds_top_bottom(self):
        (ww, wh), (ox, oy) = sf.wide_geometry((1000, 640), (1024, 768))
        self.assertEqual(ww, 1000)
        self.assertEqual(ox, 0)
        self.assertEqual(oy, (wh - 640) // 2)
        self.assertAlmostEqual(ww / wh, 4 / 3, places=2)

    def test_same_aspect_needs_nothing(self):
        self.assertIsNone(sf.wide_geometry((1000, 640), (2000, 1280)))
        self.assertIsNone(sf.wide_geometry((1000, 640), (1002, 640)))    # разница в пару пикселей — не стоит
        self.assertEqual(sf.wide_geometry((1000, 640), (1440, 900)), ((1024, 640), (12, 0)))   # 16:10 — узкие поля
        self.assertIsNone(sf.wide_geometry((1000, 640), (0, 0)))

    def test_mouse_mapping(self):
        geo = sf.wide_geometry((1500, 960), (1920, 1080))
        ox = geo[1][0]
        self.assertEqual(sf.to_game((ox, 0), geo[1], 1.5), (0, 0))
        self.assertEqual(sf.to_game((ox + 1500 - 1, 959), geo[1], 1.5), (999, 639))
        self.assertLess(sf.to_game((ox - 30, 10), geo[1], 1.5)[0], 0)   # мышь на поле сбоку — вне игры


if __name__ == "__main__":
    unittest.main()
