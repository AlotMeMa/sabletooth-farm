# -*- coding: utf-8 -*-
"""3.9: обучение — шаги идут по событиям, пропуск, сохранение, старые сохранения без обучения."""
import unittest

from tests import helpers  # noqa: F401  (добавляет папку игры в путь)
from farmgame import tutorial as tu


class TutorialSteps(unittest.TestCase):
    def test_full_path(self):
        t = tu.Tutorial()
        self.assertEqual(t.current["id"], "hello")
        self.assertFalse(t.on("collect"))          # приветствие ждёт кнопку, а не событие
        t.next()
        for event in ("collect", "plant", "buy_level", "shop"):
            self.assertFalse(t.on("что-то другое"))
            self.assertTrue(t.on(event), event)
        self.assertEqual(t.current["id"], "bye")
        t.next()
        self.assertTrue(t.done)
        self.assertIsNone(t.current)
        self.assertFalse(t.on("collect"))

    def test_wrong_order_does_not_advance(self):
        t = tu.Tutorial()
        t.next()
        self.assertFalse(t.on("shop"))             # магазин раньше времени — шаг «собери урожай» остаётся
        self.assertEqual(t.current["id"], "collect")

    def test_skip_button_appears_later(self):
        t = tu.Tutorial()
        self.assertTrue(t.can_skip_step())         # приветствие — кнопка сразу
        t.next()
        self.assertFalse(t.can_skip_step())
        t.tick(tu.SKIP_AFTER + 0.1)
        self.assertTrue(t.can_skip_step())
        t.on("collect")
        self.assertFalse(t.can_skip_step())        # новый шаг — таймер заново

    def test_finish_and_restart(self):
        t = tu.Tutorial()
        t.next()
        t.finish()
        self.assertTrue(t.done)
        t.restart()
        self.assertFalse(t.done)
        self.assertEqual(t.current["id"], "hello")

    def test_save_roundtrip(self):
        t = tu.Tutorial()
        t.next()
        t.on("collect")
        u = tu.Tutorial.from_save(t.to_dict())
        self.assertFalse(u.done)
        self.assertEqual(u.current["id"], "plant")

    def test_old_save_skips_tutorial(self):
        self.assertTrue(tu.Tutorial.from_save(None).done)
        self.assertTrue(tu.Tutorial.from_save({}).done)

    def test_broken_save(self):
        u = tu.Tutorial.from_save({"done": False, "step": 999})
        self.assertFalse(u.done)
        self.assertEqual(u.step, 0)
        u = tu.Tutorial.from_save({"done": False, "step": "x"})
        self.assertEqual(u.step, 0)


if __name__ == "__main__":
    unittest.main()
