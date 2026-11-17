# -*- coding: utf-8 -*-
"""Файл сохранения: запись, запасная копия, повреждённый файл."""
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

from tests import helpers  # noqa: F401
from farmgame import savefile


class SaveFile(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "farm_save.json")
        savefile._last_bak.clear()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def files(self):
        return sorted(os.listdir(self.dir))

    def test_write_then_read(self):
        self.assertTrue(savefile.write(self.path, {"money": 5}))
        self.assertEqual(savefile.read(self.path), ({"money": 5}, None, None))
        self.assertEqual(self.files(), ["farm_save.json"])        # временный файл не остаётся

    def test_no_file_means_new_game(self):
        self.assertEqual(savefile.read(self.path), (None, None, None))
        with open(savefile.bak_path(self.path), "w") as f:         # копия есть, а файла нет — всё равно новая игра
            f.write('{"money": 1}')
        self.assertEqual(savefile.read(self.path), (None, None, None))

    def test_backup_made_from_previous_good_file(self):
        savefile.write(self.path, {"n": 1}, now=1000)             # файла ещё не было — копировать нечего
        self.assertFalse(os.path.exists(savefile.bak_path(self.path)))
        savefile.write(self.path, {"n": 2}, now=1010)
        self.assertEqual(savefile.load_json(savefile.bak_path(self.path)), {"n": 1})
        savefile.write(self.path, {"n": 3}, now=1020)             # 5 минут не прошло — копия прежняя
        self.assertEqual(savefile.load_json(savefile.bak_path(self.path)), {"n": 1})
        savefile.write(self.path, {"n": 4}, now=1010 + savefile.BAK_EVERY)
        self.assertEqual(savefile.load_json(savefile.bak_path(self.path)), {"n": 3})
        self.assertEqual(savefile.load_json(self.path), {"n": 4})

    def test_broken_file_restored_from_backup(self):
        savefile.write(self.path, {"n": 1}, now=0)
        savefile.write(self.path, {"n": 2}, now=1000)
        with open(self.path, "w") as f:
            f.write('{"n": 2, "levels": [1, 2')                    # оборванный файл
        data, note, kept = savefile.read(self.path)
        self.assertEqual((data, note), ({"n": 1}, "restored"))
        self.assertIn(kept, self.files())
        with open(os.path.join(self.dir, kept)) as f:
            self.assertIn('"levels": [1, 2', f.read())             # повреждённый файл сохранён как был

    def test_broken_file_without_backup(self):
        for junk in ("", "не json", "[1, 2, 3]", "null"):
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(junk)
            data, note, kept = savefile.read(self.path)
            self.assertEqual((data, note), (None, "lost"))
            self.assertTrue(kept and kept.startswith("farm_save.broken_"))

    def test_broken_file_never_becomes_backup(self):
        savefile.write(self.path, {"n": 1}, now=0)
        savefile.write(self.path, {"n": 2}, now=1000)             # копия = {"n": 1}
        with open(self.path, "w") as f:
            f.write("мусор")
        savefile.write(self.path, {"n": 3}, now=5000)
        self.assertEqual(savefile.load_json(savefile.bak_path(self.path)), {"n": 1})

    def test_unserializable_data_keeps_old_file(self):
        savefile.write(self.path, {"n": 1})
        with contextlib.redirect_stdout(io.StringIO()):            # сообщение «Не удалось сохранить» здесь ожидаемо
            self.assertFalse(savefile.write(self.path, {"bad": {1, 2}}))
        self.assertEqual(savefile.load_json(self.path), {"n": 1})

    def test_names_match_gitignore(self):
        """Все файлы сохранения подходят под farm_save*.json (их не берёт git)."""
        import re
        save_re = re.compile(r"^farm_save.*\.json$", re.IGNORECASE)
        for path in (self.path, os.path.join(self.dir, "farm_save_dev.json")):
            savefile.write(path, {"n": 1})
            self.assertTrue(save_re.match(os.path.basename(savefile.bak_path(path))))
            self.assertTrue(save_re.match(savefile.keep_broken(path)))

    def test_old_broken_copies_are_pruned(self):
        for i in range(savefile.KEEP_BROKEN + 4):
            with open(os.path.join(self.dir, f"farm_save.broken_2020-01-{i + 1:02d}_00-00-00.json"), "w") as f:
                f.write("x")
        savefile.write(self.path, {"n": 1})
        savefile.keep_broken(self.path)
        left = [fn for fn in self.files() if ".broken_" in fn]
        self.assertEqual(len(left), savefile.KEEP_BROKEN)
        self.assertNotIn("farm_save.broken_2020-01-01_00-00-00.json", left)

    def test_json_roundtrip_of_real_state(self):
        from farmgame.logic import Farm
        f = helpers.summer_farm()
        f.offline_earn(300)
        savefile.write(self.path, f.to_dict())
        g = Farm()
        g.from_dict(savefile.read(self.path)[0])
        self.assertEqual(json.dumps(g.to_dict()), json.dumps(f.to_dict()))


if __name__ == "__main__":
    unittest.main()
