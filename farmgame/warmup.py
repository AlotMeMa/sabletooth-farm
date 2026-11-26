# -*- coding: utf-8 -*-
"""3.40.4: первая подгонка картинок — в нескольких процессах сразу.

Подгонка (убрать фон, обрезать, разрезать листы) — чистый Python и упирается в одно ядро. При первом запуске
(или после новых картинок) это минуты. Здесь недостающие картинки раздаются отдельным процессам: каждый берёт
свой исходный файл целиком (лист или полоску — все его кусочки сразу) и кладёт результат в .sprite_cache/.
Окно игры в это время крутит заставку, а потом берёт всё из кэша.
"""
import os
import sys

from . import spritefit


def _init(k, cache_dir):
    """В процессе-помощнике: тот же масштаб HD и та же папка кэша, что у игры."""
    spritefit.FIT_SCALE[0] = k
    spritefit.CACHE_DIR = cache_dir


def _job(names):
    """Подогнать картинки names (обычно — все из одного файла). Возвращает, сколько сделано."""
    from .art_sprites import _load_sprite
    for name in names:
        try:
            _load_sprite(name)
        except Exception as e:      # noqa: BLE001 — одна битая картинка не должна ронять остальные
            print(f"Подгонка {name}: {e}")
    return len(names)


def source_of(name):
    """Из какого файла assets/ берётся картинка name (чтобы кусочки одного листа делал один процесс)."""
    from .art_sprites import find_asset_file
    base = name[:-len(spritefit.HI)] if name.endswith(spritefit.HI) else name
    path = find_asset_file(base)
    if path:
        return path
    parts = base.split("/")
    if parts[0] == "crops" and len(parts) == 3 and parts[2][-2:] in ("_1", "_2", "_3"):
        strip = find_asset_file(base[:-2])
        if strip:
            return strip
    for sheet_name, (prefix, order, _rows, _cols) in spritefit.SHEETS.items():
        if base.startswith(prefix) and base[len(prefix):] in order:
            sheet = find_asset_file(sheet_name)
            if sheet:
                return sheet
    return name


def groups(names):
    """Недостающие картинки, сгруппированные по исходному файлу; крупные группы — первыми."""
    by_src = {}
    for n in names:
        by_src.setdefault(source_of(n), []).append(n)
    out = list(by_src.values())
    out.sort(key=len, reverse=True)
    return out


def workers():
    """Сколько процессов: все ядра, кроме одного (оно рисует заставку), но не больше 8 (FARM_WORKERS — вручную)."""
    if os.environ.get("FARM_WORKERS", "").isdigit():
        return max(1, int(os.environ["FARM_WORKERS"]))
    return max(1, min(8, (os.cpu_count() or 2) - 1))


def start(names):
    """Запускает подгонку names в процессах. -> (executor, [(future, сколько картинок)]) или None, если не вышло."""
    import concurrent.futures as cf
    import multiprocessing as mp
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    # помощникам не нужен главный файл игры (farm_idle.py): без него они стартуют быстрее и не запускают его код
    main = sys.modules.get("__main__")
    main_file = getattr(main, "__file__", None)
    try:
        if main_file:
            main.__file__ = None
        ex = cf.ProcessPoolExecutor(max_workers=workers(), mp_context=mp.get_context("spawn"),
                                    initializer=_init, initargs=(spritefit.FIT_SCALE[0], spritefit.CACHE_DIR))
        jobs = [(ex.submit(_job, g), len(g)) for g in groups(names)]
    except Exception as e:          # noqa: BLE001 — нет процессов (запрет, странная сборка) — подгоним по-старому
        print("Подгонка в процессах не запустилась:", e)
        return None
    finally:
        if main_file:
            main.__file__ = main_file
    return ex, jobs
