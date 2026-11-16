# -*- coding: utf-8 -*-
"""Обновление «Весёлой фермы» без потери твоих файлов.

Как пользоваться:
    1) положи архив с новой версией (.zip) в папку с игрой;
    2) дважды щёлкни update.bat (или перетащи архив прямо на update.bat).

Что делает:
    - сохраняет текущий код и сохранения в _backup/<дата>_v<версия>/ — из него можно откатиться;
    - заменяет только код игры (farmgame/, farm_idle.py, шаблоны, инструкции);
    - НИКОГДА не трогает: assets/ (твои картинки), farm_save*.json (прогресс и его запасные копии),
      .sprite_cache/, _backup/ и сам update.bat;
    - архив с путями «..» (мимо папки игры) не ставит вообще; откат на более старую версию — только по слову «да».

Откат: скопируй содержимое нужной папки из _backup/ обратно в папку игры.
Запуск без вопроса «Обновить?»:  python update.py --yes [архив.zip]
"""
import datetime
import os
import re
import shutil
import sys
import zipfile

GAME_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(GAME_DIR, "_backup")
MAX_BACKUPS = 10

# верхний уровень папки игры, который обновление не трогает никогда
PROTECTED_DIRS = {"assets", "_backup", ".sprite_cache", "__pycache__"}
PROTECTED_FILES = {"update.bat"}
SAVE_RE = re.compile(r"^farm_save.*\.json$", re.IGNORECASE)
# что из старой версии кладём в бэкап (шаблоны не нужны — их можно выгрузить заново)
NO_BACKUP_DIRS = {"assets_templates"}

BAT = ("@echo off\r\nchcp 65001 >nul\r\ncd /d \"%~dp0\"\r\n"
       "where py >nul 2>nul\r\n"
       "if %errorlevel%==0 (py update.py %*) else (python update.py %*)\r\n"
       "echo.\r\npause\r\n")


def say(text=""):
    print(text, flush=True)


def is_protected(rel):
    """rel — путь внутри папки игры через '/'. True — этот файл обновление не трогает."""
    top = rel.split("/", 1)[0]
    if top in PROTECTED_DIRS or "__pycache__" in rel.split("/"):
        return True
    if "/" not in rel and (rel in PROTECTED_FILES or SAVE_RE.match(rel)):
        return True
    return False


def is_safe(rel):
    """Путь из архива ведёт строго внутрь папки игры: без «..», без диска и без корня."""
    parts = rel.split("/")
    return bool(rel) and not rel.startswith("/") and all(p not in ("", ".", "..") and ":" not in p for p in parts)


def read_version(text):
    m = re.search(r'GAME_VERSION\s*=\s*"([^"]+)"', text or "")
    return m.group(1) if m else "?"


def version_key(ver):
    """'2.10' -> (2, 10): чтобы сравнивать версии как числа, а не как строки."""
    return tuple(int(x) for x in re.findall(r"\d+", ver or ""))


def local_version():
    path = os.path.join(GAME_DIR, "farmgame", "config.py")
    if not os.path.exists(path):
        return "?"
    with open(path, encoding="utf-8") as fh:
        return read_version(fh.read())


def find_zip(args):
    for a in args:
        if a.lower().endswith(".zip"):
            return os.path.abspath(a)
    zips = [os.path.join(GAME_DIR, fn) for fn in os.listdir(GAME_DIR) if fn.lower().endswith(".zip")]
    if not zips:
        return None
    return max(zips, key=os.path.getmtime)


def game_root_in_zip(z):
    """Префикс папки игры внутри архива ('' или 'Vesyolaya_ferma/'). None — это не архив игры."""
    best = None
    for name in z.namelist():
        n = name.replace("\\", "/")
        if n.endswith("farm_idle.py") and (n == "farm_idle.py" or n.endswith("/farm_idle.py")):
            prefix = n[:-len("farm_idle.py")]
            if prefix + "farmgame/config.py" in z.namelist() and (best is None or len(prefix) < len(best)):
                best = prefix
    return best


def plan(z, prefix):
    """-> (файлы для записи [(имя в архиве, путь в игре)], папки верхнего уровня под замену, файлы-пропуски)."""
    files, dirs, skipped = [], set(), []
    for name in z.namelist():
        n = name.replace("\\", "/")
        if not n.startswith(prefix) or n.endswith("/"):
            continue
        rel = n[len(prefix):]
        if not rel:
            continue
        if is_protected(rel):
            skipped.append(rel)
            continue
        if not is_safe(rel):        # «..» или чужой диск в пути: такой файл лёг бы мимо папки игры
            raise ValueError(f"подозрительный путь в архиве: {rel}")
        files.append((name, rel))
        if "/" in rel:
            dirs.add(rel.split("/", 1)[0])
    return files, sorted(dirs), skipped


def make_backup(stamp, old_ver, files, dirs):
    dest = os.path.join(BACKUP_DIR, f"{stamp}_v{old_ver}")
    os.makedirs(dest, exist_ok=True)
    count = 0
    # папки кода целиком (кроме шаблонов и кэша)
    for d in dirs:
        src = os.path.join(GAME_DIR, d)
        if d in NO_BACKUP_DIRS or not os.path.isdir(src):
            continue
        shutil.copytree(src, os.path.join(dest, d), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        count += sum(len(fs) for _r, _d, fs in os.walk(os.path.join(dest, d)))
    # файлы в корне, которые будут заменены
    for _name, rel in files:
        if "/" in rel:
            continue
        src = os.path.join(GAME_DIR, rel)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(dest, rel))
            count += 1
    # сохранения — на всякий случай
    for fn in os.listdir(GAME_DIR):
        if SAVE_RE.match(fn):
            shutil.copy2(os.path.join(GAME_DIR, fn), os.path.join(dest, fn))
            count += 1
    return dest, count


def restore_backup(dest, dirs):
    for d in dirs:
        src = os.path.join(dest, d)
        if os.path.isdir(src):
            shutil.rmtree(os.path.join(GAME_DIR, d), ignore_errors=True)
            shutil.copytree(src, os.path.join(GAME_DIR, d))
    for fn in os.listdir(dest):
        p = os.path.join(dest, fn)
        if os.path.isfile(p) and not SAVE_RE.match(fn):
            shutil.copy2(p, os.path.join(GAME_DIR, fn))


def prune_backups():
    if not os.path.isdir(BACKUP_DIR):
        return
    olds = sorted(d for d in os.listdir(BACKUP_DIR) if os.path.isdir(os.path.join(BACKUP_DIR, d)))
    for d in olds[:-MAX_BACKUPS]:
        shutil.rmtree(os.path.join(BACKUP_DIR, d), ignore_errors=True)
    # архивы установленных версий тоже не копим бесконечно
    zips = sorted(fn for fn in os.listdir(BACKUP_DIR)
                  if fn.lower().endswith(".zip") and os.path.isfile(os.path.join(BACKUP_DIR, fn)))
    for fn in zips[:-MAX_BACKUPS]:
        try:
            os.remove(os.path.join(BACKUP_DIR, fn))
        except OSError:
            pass


def main(argv):
    yes = "--yes" in argv
    say("=== Обновление «Весёлой фермы» ===")
    zpath = find_zip([a for a in argv if not a.startswith("--")])
    if not zpath:
        say("Не нашла архив .zip в папке игры. Положи архив с новой версией рядом с update.bat")
        say("(или перетащи архив прямо на update.bat) и запусти ещё раз.")
        return 1
    say(f"Архив: {os.path.basename(zpath)}")
    try:
        z = zipfile.ZipFile(zpath)
    except zipfile.BadZipFile:
        say("Этот файл не открывается как zip-архив. Скачай его заново.")
        return 1
    with z:
        prefix = game_root_in_zip(z)
        if prefix is None:
            say("В архиве нет игры (не нашла farm_idle.py и farmgame/config.py). Ничего не меняю.")
            return 1
        new_ver = read_version(z.read(prefix + "farmgame/config.py").decode("utf-8", "replace"))
        old_ver = local_version()
        try:
            files, dirs, skipped = plan(z, prefix)
        except ValueError as e:
            say(f"Архив выглядит неправильно ({e}). Ничего не меняю.")
            return 1
        say(f"Версия: {old_ver}  ->  {new_ver}")
        older = version_key(new_ver) and version_key(old_ver) and version_key(new_ver) < version_key(old_ver)
        if older:
            say("ВНИМАНИЕ: в архиве более старая версия, чем установлена (это откат назад).")
        say(f"Будет заменено файлов: {len(files)} (папки: {', '.join(dirs) or '—'})")
        if skipped:
            say(f"Пропущу из архива (твоё, не трогаю): {len(skipped)}")
        say("Не трогаю: assets/, сохранения, .sprite_cache/, _backup/.")
        if not yes:
            try:
                ans = input("Откатить? да — откатить, Enter — отмена: " if older
                            else "Обновить? Enter — да, n — нет: ").strip().lower()
            except EOFError:
                ans = ""
            if ans in ("n", "н", "no", "нет"):
                say("Отменено, ничего не менялось.")
                return 0
            if older and ans not in ("y", "д", "yes", "да"):
                say("Откат на старую версию — только если ответить «да». Отменено, ничего не менялось.")
                return 0

        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        dest, n_backup = make_backup(stamp, old_ver, files, dirs)
        say(f"Бэкап: _backup/{os.path.basename(dest)} ({n_backup} файлов)")
        try:
            for d in dirs:   # папки кода заменяем целиком, чтобы не осталось старых файлов
                shutil.rmtree(os.path.join(GAME_DIR, d), ignore_errors=True)
            for name, rel in files:
                target = os.path.join(GAME_DIR, *rel.split("/"))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with z.open(name) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
        except Exception as e:
            say(f"Ошибка при обновлении: {e}")
            say("Возвращаю старую версию из бэкапа...")
            restore_backup(dest, dirs)
            say("Готово: всё как было. Пришли этот текст Сакуре.")
            return 1

    # bat-файл не перезаписываем (он сейчас выполняется), только создаём, если его нет
    bat = os.path.join(GAME_DIR, "update.bat")
    if not os.path.exists(bat):
        with open(bat, "w", newline="") as fh:
            fh.write(BAT)
    # архив убираем к бэкапам, чтобы он не поставился второй раз
    os.makedirs(BACKUP_DIR, exist_ok=True)
    try:
        shutil.move(zpath, os.path.join(BACKUP_DIR, f"{stamp}_installed_v{new_ver}.zip"))
    except Exception:
        pass
    prune_backups()
    say(f"Готово! Установлена версия {new_ver}. Запускай игру как обычно.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
