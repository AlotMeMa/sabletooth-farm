# -*- coding: utf-8 -*-
"""Файл сохранения: надёжная запись, запасная копия и спасение повреждённого файла. Без графики.

Рядом с farm_save.json игра держит:
    farm_save.bak.json                — запасная копия (заведомо читаемая, не старше нескольких минут игры);
    farm_save.broken_<дата>.json      — повреждённый файл, если он не прочитался (его не затирают — можно спасти руками).
Имена farm_save*.json в .gitignore — сохранения не попадают в git.

3.17, веб-версия: файлы в браузере живут только в памяти страницы, поэтому каждая удачная запись копируется
ещё и в хранилище браузера (STORE = device.web_store()), а при запуске restore() возвращает файлы оттуда.
"""
import json
import os
import shutil
import time

BAK_EVERY = 300.0      # запасную копию обновляем не чаще раза в 5 минут
KEEP_BROKEN = 5        # сколько отложенных повреждённых файлов хранить
_last_bak = {}         # путь -> когда последний раз делали запасную копию
STORE = None           # 3.17: хранилище браузера (get(ключ) / set(ключ, текст)) — только в веб-версии


def _mirror(path, text=None):
    """Веб-версия: копия файла в хранилище браузера (ключ — имя файла)."""
    if STORE is None:
        return
    try:
        if text is None:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        STORE.set(os.path.basename(path), text)
    except OSError as e:
        print("Не удалось скопировать сохранение в браузер:", e)


def restore(path):
    """Веб-версия, при запуске: вернуть сохранение и запасную копию из хранилища браузера в файлы."""
    if STORE is None:
        return
    for p in (path, bak_path(path)):
        if os.path.exists(p):
            continue
        text = STORE.get(os.path.basename(p))
        if not text:
            continue
        try:
            folder = os.path.dirname(p)
            if folder:
                os.makedirs(folder, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError as e:
            print("Не удалось восстановить сохранение из браузера:", e)


def bak_path(path):
    root, ext = os.path.splitext(path)
    return root + ".bak" + ext


def load_json(path):
    """Словарь из файла или None (файла нет, не читается, не JSON, не словарь)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def keep_broken(path, tag="broken"):
    """Откладывает копию файла рядом: farm_save.<tag>_<дата>.json. Возвращает имя копии или None."""
    if not os.path.isfile(path):
        return None
    root, ext = os.path.splitext(path)
    dest = f"{root}.{tag}_{time.strftime('%Y-%m-%d_%H-%M-%S')}{ext}"
    try:
        shutil.copy2(path, dest)
    except OSError as e:
        print("Не удалось отложить копию сохранения:", e)
        return None
    folder, prefix = os.path.dirname(dest), os.path.basename(root) + f".{tag}_"
    try:    # старые копии не копим бесконечно
        olds = sorted(fn for fn in os.listdir(folder) if fn.startswith(prefix) and fn.endswith(ext))
        for fn in olds[:-KEEP_BROKEN]:
            os.remove(os.path.join(folder, fn))
    except OSError:
        pass
    return os.path.basename(dest)


def write(path, data, now=None):
    """Записывает сохранение так, чтобы его нельзя было испортить на полпути: сначала во временный файл,
    потом одним действием подменяет им настоящий. Раз в BAK_EVERY секунд прежний (читаемый) файл
    уходит в запасную копию. Возвращает True, если записано."""
    now = time.time() if now is None else now
    tmp = path + ".tmp"
    try:
        text = json.dumps(data)                 # если данные не превращаются в JSON — файл не трогаем
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            try:
                os.fsync(f.fileno())            # чтобы после выключения света не остался пустой файл
            except OSError:
                pass
        if now - _last_bak.get(path, 0.0) >= BAK_EVERY and load_json(path) is not None:
            shutil.copy2(path, bak_path(path))
            _last_bak[path] = now
            _mirror(bak_path(path))
        os.replace(tmp, path)
        _mirror(path, text)
        return True
    except (OSError, TypeError, ValueError) as e:
        print("Не удалось сохранить:", e)
        return False


def read(path):
    """-> (data, note, kept).
    data — словарь сохранения или None (файла нет или спасти нечего);
    note — None: всё в порядке; "restored": основной файл повреждён, взята запасная копия; "lost": повреждён, копии нет;
    kept — имя, под которым отложен повреждённый файл (или None)."""
    data = load_json(path)
    if data is not None:
        return data, None, None
    if not os.path.exists(path):                # файла нет — это новая игра (запасную копию не подсовываем)
        return None, None, None
    kept = keep_broken(path)
    bak = load_json(bak_path(path))
    if bak is not None:
        return bak, "restored", kept
    return None, "lost", kept
