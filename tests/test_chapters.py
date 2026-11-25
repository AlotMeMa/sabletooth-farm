# -*- coding: utf-8 -*-
"""3.23: карта глав в окне «Переезд»: где игрок, что пройдено, что дальше."""
import unittest

from tests import helpers  # noqa: F401
from farmgame.chapters import chapters
from farmgame.config import FARMS


class Chapters(unittest.TestCase):
    def test_summer(self):
        st = [c["state"] for c in chapters(0)]
        self.assertEqual(st[0], "here")
        self.assertEqual(st[1], "next")                     # средневековье готово — туда можно ехать
        for c in chapters(0)[2:]:      # дальше: в работе — «скоро», готовые и тайна — «закрыто»
            self.assertEqual(c["state"], "soon" if not c["ready"] and c["id"] != "secret" else "locked")

    def test_medieval(self):
        chs = chapters(1)
        self.assertEqual([c["state"] for c in chs[:2]], ["done", "here"])
        self.assertEqual(chs[2]["id"], "winter")
        self.assertEqual(chs[2]["state"], "next" if FARMS[2]["ready"] else "soon")
        self.assertEqual(chs[-1]["id"], "secret")           # в конце карты — «тайна»

    def test_every_farm_has_text(self):
        for c in chapters(0):
            self.assertTrue(c["text"], c["id"])


if __name__ == "__main__":
    unittest.main()
