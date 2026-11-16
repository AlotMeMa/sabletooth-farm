# -*- coding: utf-8 -*-
"""Обновлялка: настоящий запуск update.py в копии папки игры."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

from tests.helpers import ROOT

CONFIG = 'GAME_VERSION = "{}"\n'


class Updater(unittest.TestCase):
    def setUp(self):
        self.game = tempfile.mkdtemp()
        shutil.copy2(os.path.join(ROOT, "update.py"), self.game)
        self.put("farmgame/config.py", CONFIG.format("2.7"))
        self.put("farmgame/old_module.py", "OLD = 1\n")
        self.put("farm_idle.py", "print('old')\n")
        self.put("assets/crops/my_carrot.png", "МОЯ КАРТИНКА")
        self.put("farm_save.json", '{"money": 123}')
        self.put("farm_save.bak.json", '{"money": 100}')
        self.put(".sprite_cache/a.png", "cache")

    def tearDown(self):
        shutil.rmtree(self.game, ignore_errors=True)

    def put(self, rel, text):
        path = os.path.join(self.game, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def get(self, rel):
        with open(os.path.join(self.game, *rel.split("/")), encoding="utf-8") as f:
            return f.read()

    def make_zip(self, version, extra=(), name="new.zip", prefix="Vesyolaya_ferma/"):
        path = os.path.join(self.game, name)
        with zipfile.ZipFile(path, "w") as z:
            z.writestr(prefix + "farm_idle.py", "print('new')\n")
            z.writestr(prefix + "farmgame/config.py", CONFIG.format(version))
            z.writestr(prefix + "farmgame/new_module.py", "NEW = 1\n")
            z.writestr(prefix + "assets/crops/my_carrot.png", "ЧУЖАЯ КАРТИНКА")
            z.writestr(prefix + "farm_save.json", '{"money": 0}')
            for rel, text in extra:
                z.writestr(prefix + rel, text)
        return path

    def run_update(self, *args, answer=""):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        p = subprocess.run([sys.executable, os.path.join(self.game, "update.py"), *args], input=answer, text=True,
                           capture_output=True, encoding="utf-8", env=env, cwd=self.game)
        return p.returncode, p.stdout + p.stderr

    def test_update_replaces_code_and_keeps_yours(self):
        self.make_zip("2.8")
        code, out = self.run_update("--yes")
        self.assertEqual(code, 0, out)
        self.assertIn("2.8", self.get("farmgame/config.py"))
        self.assertEqual(self.get("farm_idle.py"), "print('new')\n")
        self.assertTrue(os.path.exists(os.path.join(self.game, "farmgame", "new_module.py")))
        self.assertFalse(os.path.exists(os.path.join(self.game, "farmgame", "old_module.py")))   # старые файлы кода убраны
        self.assertEqual(self.get("assets/crops/my_carrot.png"), "МОЯ КАРТИНКА")
        self.assertEqual(self.get("farm_save.json"), '{"money": 123}')
        self.assertEqual(self.get("farm_save.bak.json"), '{"money": 100}')
        self.assertEqual(self.get(".sprite_cache/a.png"), "cache")
        backups = os.listdir(os.path.join(self.game, "_backup"))
        folder = [b for b in backups if b.endswith("_v2.7")]
        self.assertEqual(len(folder), 1, backups)
        saved = os.listdir(os.path.join(self.game, "_backup", folder[0]))
        self.assertIn("farm_save.json", saved)
        self.assertIn("farm_save.bak.json", saved)
        self.assertIn("farmgame", saved)
        self.assertTrue(any(b.endswith("_installed_v2.8.zip") for b in backups))
        self.assertFalse(os.path.exists(os.path.join(self.game, "new.zip")))                   # архив убран к бэкапам

    def test_archive_with_dotdot_is_refused(self):
        """Архив с «..» в пути не должен ни писать, ни удалять что-либо за пределами папки игры."""
        outside = os.path.join(os.path.dirname(self.game), "outside_" + os.path.basename(self.game))
        self.addCleanup(lambda: os.path.exists(outside) and os.remove(outside))
        self.make_zip("2.8", extra=[("../" + os.path.basename(outside), "взлом"), ("farmgame/../../x.py", "взлом")])
        code, out = self.run_update("--yes")
        self.assertEqual(code, 1, out)
        self.assertFalse(os.path.exists(outside))
        self.assertIn("2.7", self.get("farmgame/config.py"))                                   # ничего не поменялось
        self.assertTrue(os.path.exists(os.path.join(self.game, "farmgame", "old_module.py")))

    def test_not_a_game_archive(self):
        with zipfile.ZipFile(os.path.join(self.game, "other.zip"), "w") as z:
            z.writestr("readme.txt", "hello")
        code, out = self.run_update("--yes")
        self.assertEqual(code, 1, out)
        self.assertIn("2.7", self.get("farmgame/config.py"))

    def test_downgrade_needs_explicit_yes(self):
        self.put("farmgame/config.py", CONFIG.format("2.10"))
        self.make_zip("2.9")
        code, out = self.run_update(answer="\n")                                               # просто Enter — отмена
        self.assertEqual(code, 0, out)
        self.assertIn("2.10", self.get("farmgame/config.py"))
        code, out = self.run_update(answer="да\n")
        self.assertEqual(code, 0, out)
        self.assertIn("2.9", self.get("farmgame/config.py"))

    def test_plain_enter_updates(self):
        self.make_zip("2.8", prefix="")                                                        # архив без общей папки
        code, out = self.run_update(answer="\n")
        self.assertEqual(code, 0, out)
        self.assertIn("2.8", self.get("farmgame/config.py"))

    def test_old_archives_are_pruned(self):
        os.makedirs(os.path.join(self.game, "_backup"))
        for i in range(15):
            self.put(f"_backup/2020-01-{i + 1:02d}_00-00-00_installed_v0.{i}.zip", "zip")
        self.make_zip("2.8")
        code, out = self.run_update("--yes")
        self.assertEqual(code, 0, out)
        zips = sorted(b for b in os.listdir(os.path.join(self.game, "_backup")) if b.endswith(".zip"))
        self.assertEqual(len(zips), 10)
        self.assertTrue(zips[-1].endswith("_installed_v2.8.zip"))

    def test_version_compare(self):
        sys.path.insert(0, ROOT)
        import update
        self.assertLess(update.version_key("2.9"), update.version_key("2.10"))
        self.assertTrue(update.is_safe("farmgame/app.py"))
        for bad in ("../x", "a/../b", "/abs", "C:/x", "a//b", ""):
            self.assertFalse(update.is_safe(bad), bad)


if __name__ == "__main__":
    unittest.main()
