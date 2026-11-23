"""3.17: «запечь» картинки для телефонной сборки (APK и веб-версия).

    python devtools/bake_sprites.py <папка> [чёткость]      (чёткость по умолчанию — device.HANDHELD_K)

Подгоняет все картинки игры из assets/ под чёткость телефона — так же, как игра делает это при первом запуске, —
и кладёт результат в <папка>/ с manifest.json. В телефонную сборку идёт эта папка (как baked/), а исходники
картинок — нет: они большие, а подгонка на телефоне шла бы минутами. Нужен настоящий pygame (pygame-ce),
окно не открывается (SDL_VIDEODRIVER=dummy). Запускается в GitHub Actions (mobile/build.py).
"""
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
sys.path.insert(0, GAME)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from farmgame import art, device, hd, spritefit, templates  # noqa: E402


def names_to_bake():
    names = set(templates.known_names()) - set(spritefit.SHEETS)    # сами листы не рисуются — только их кусочки
    names |= {n + spritefit.HI for n in names if n.startswith("icons/")}     # крупные иконки (art.blit_icon)
    return sorted(names)


def opaque(img):
    """Без прозрачности (фоны) — такие сохраняем в JPEG: в разы меньше, разницы не видно."""
    if not img.get_flags() & pygame.SRCALPHA:
        return True
    return min(pygame.image.tobytes(img, "RGBA")[3::4]) == 255


def bake(out, k):
    pygame.init()
    pygame.display.set_mode((64, 64))
    hd.install(k)
    spritefit.FIT_SCALE[0] = k
    spritefit.BAKED["sprites"] = {}                      # на всякий случай: печём из исходников, а не из прошлой выпечки
    os.makedirs(out, exist_ok=True)
    table, t0, size = {}, time.time(), 0
    for name in names_to_bake() + sorted(spritefit.SHEETS):
        if name in spritefit.SHEETS:
            table[name] = None
            continue
        try:
            img = art._load_sprite(name)
        except Exception as e:
            print("Не подогналась", name, e)
            img = None
        if img is None:
            table[name] = None
            continue
        img = hd.real(img)
        fn = hashlib.md5(name.encode("utf-8")).hexdigest()[:16] + (".jpg" if opaque(img) else ".png")
        pygame.image.save(img, os.path.join(out, fn))
        size += os.path.getsize(os.path.join(out, fn))
        table[name] = fn
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"k": k, "cache": spritefit.CACHE_VERSION, "sprites": table}, f, ensure_ascii=False, indent=0)
    n = sum(1 for v in table.values() if v)
    print(f"Запечено картинок: {n} из {len(table)}, {size / 1e6:.1f} МБ, чёткость x{k:g}, {time.time() - t0:.0f} с")


if __name__ == "__main__":
    bake(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else device.HANDHELD_K)
