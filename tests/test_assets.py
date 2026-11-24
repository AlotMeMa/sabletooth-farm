# -*- coding: utf-8 -*-
"""3.17: тяжёлые файлы в assets/ — каждый попадает в историю git навсегда (даже если потом удалить).
Тест падает, если что-то слишком большое, и подсказывает, что сделать. pygame не нужен."""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
LIMITS = {   # папка -> (максимум байт, совет)
    "music": (6 * 1024 * 1024, "пережми в OGG ~128 кбит/с (или попроси Claude — он пережмёт)"),
    "sfx": (6 * 1024 * 1024, "пережми в OGG ~128 кбит/с"),
    "fonts": (2 * 1024 * 1024, "возьми один-два начертания шрифта, а не всё семейство"),
}
IMAGE_LIMIT = (4 * 1024 * 1024, "сохрани как JPG или уменьши до ~2000 px по большей стороне")


class HeavyFiles(unittest.TestCase):
    def test_no_huge_files_in_assets(self):
        too_big = []
        for root, _dirs, files in os.walk(ASSETS):
            for fn in files:
                if fn.lower().endswith(".wav"):       # WAV в git не попадает (.gitignore) — пусть лежит
                    continue
                path = os.path.join(root, fn)
                rel = os.path.relpath(path, ASSETS).replace(os.sep, "/")
                limit, tip = LIMITS.get(rel.split("/")[0], IMAGE_LIMIT)
                size = os.path.getsize(path)
                if size > limit:
                    too_big.append(f"assets/{rel}: {size / 1048576:.1f} МБ (можно до {limit / 1048576:.0f}) — {tip}")
        self.assertEqual(too_big, [], "\n" + "\n".join(too_big))

