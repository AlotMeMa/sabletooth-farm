# -*- coding: utf-8 -*-
"""Спрайты: поиск картинок в assets/, загрузка с подгонкой, рисование с масштабом/поворотом.

Часть art.py (3.17: вынесено без изменений). Снаружи всё берётся как раньше: from .art import ...
"""
import math
import os
import random

import pygame

from . import spritefit
from . import hd
from .config import *  # noqa: F401,F403


# ======================================================================
#                 СПРАЙТЫ: картинки из assets/ (если есть)
# ======================================================================
# Любой объект сначала ищет свою картинку в папке assets/ (см. docs/SPRITES.md).
# Если картинки нет — рисуется как раньше, кодом. Так графику можно менять по одному файлу.
USE_SPRITES = [True]
_sprite_cache = {}
_sprite_scaled = {}
SCALE_STEP = 0.02


IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def find_asset_file(name):
    """assets/<name>.png (или .jpg/.jpeg/.webp/.bmp, регистр букв не важен). None — если нет."""
    folder = os.path.join(ASSET_DIR, *name.split("/")[:-1])
    base = name.split("/")[-1].lower()
    if not os.path.isdir(folder):
        return None
    found = []
    for fn in sorted(os.listdir(folder)):
        stem, ext = os.path.splitext(fn)
        if stem.lower() == base and ext.lower() in IMAGE_EXTS:
            found.append(os.path.join(folder, fn))
    for path in found:          # два файла с одним именем (.png и .jpg): своя картинка важнее копии шаблона
        if not is_template_copy(name, path):
            return path
    return found[0] if found else None


def sprite(name):
    """PNG из assets/<name>.png или None. Загружается один раз."""
    if not USE_SPRITES[0]:
        return None
    if name in _sprite_cache:
        return _sprite_cache[name]
    img = None
    try:
        img = hd.wrap(_load_sprite(name))     # в HD картинка подогнана крупнее — снаружи она «логического» размера
    except Exception as e:  # битый файл не должен ронять игру
        print(f"Не удалось загрузить спрайт {name}: {e}")
        img = None
    _sprite_cache[name] = img
    return img


def is_template_copy(name, path):
    """True, если файл в assets/ — просто копия шаблона из assets_templates/ (байт в байт).
    Такие файлы игра пропускает: они ничего не меняют, но мешают полоскам и листам (их «перекрывают»)."""
    tpl = os.path.join(BASE_DIR, "assets_templates", *name.split("/")) + ".png"
    try:
        if not os.path.exists(tpl) or os.path.getsize(tpl) != os.path.getsize(path):
            return False
        with open(tpl, "rb") as a, open(path, "rb") as b:
            return a.read() == b.read()
    except OSError:
        return False


def _load_sprite(name):
    """Свой файл; иначе — стадия из полоски crops/<ферма>/<культура>.png или иконка из icons/sheet.png.
    name@2x — та же картинка вдвое крупнее (spritefit.HI): для крупных иконок."""
    if name.endswith(spritefit.HI):
        base = name[:-len(spritefit.HI)]
        path = find_asset_file(base)
        if path and not is_template_copy(base, path):
            return spritefit.load_fitted(name, path)
        for sheet_name, (prefix, order, rows, cols) in spritefit.SHEETS.items():
            if base.startswith(prefix) and base[len(prefix):] in order:
                sheet = find_asset_file(sheet_name)
                if sheet:
                    return spritefit.load_fitted(name, sheet, ("sheet", order.index(base[len(prefix):]), prefix, order, rows, cols))
        return None
    path = find_asset_file(name)
    if path and is_template_copy(name, path):
        path = None
    parts = name.split("/")
    if path:
        if parts[0] == "crops" and len(parts) == 3 and not parts[2][-2:] in ("_1", "_2", "_3"):
            if spritefit.is_strip(pygame.image.load(path), path):
                return sprite(name + "_3")      # одна картинка-полоска: показываем спелую стадию
        return spritefit.load_fitted(name, path)
    if parts[0] == "crops" and len(parts) == 3 and parts[2][-2:] in ("_1", "_2", "_3"):
        strip = find_asset_file(name[:-2])
        if strip and spritefit.is_strip(pygame.image.load(strip), strip):
            return spritefit.load_fitted(name, strip, ("strip", int(name[-1])))
        return None
    for sheet_name, (prefix, order, rows, cols) in spritefit.SHEETS.items():   # иконка/кнопка/фишка из листа
        if name.startswith(prefix) and name[len(prefix):] in order:
            sheet = find_asset_file(sheet_name)
            if sheet:
                return spritefit.load_fitted(name, sheet, ("sheet", order.index(name[len(prefix):]), prefix, order, rows, cols))
    return None


def extended_down(name, ext, from_frac=0.7):
    """Спрайт name, у которого низ продлён вниз на ext логических px: каждый столбец, дошедший ниже
    from_frac высоты, тянется своим цветом (чуть выше края) до нового низа. Так персонаж «по пояс»
    (бармен) уходит за стойку целиком — без щели под локтями. Имя результата: name + "#down".
    None — если картинки нет."""
    key = name + "#down"
    if key in _sprite_cache:
        return key if _sprite_cache[key] is not None else None
    img = sprite(name)
    if img is None:
        _sprite_cache[key] = None
        return None
    src = hd.real(img)
    k = hd.scale()
    px = spritefit.Pix(src)
    w, h, b = px.w, px.h, px.buf
    e = max(1, int(round(ext * k)))
    out = bytearray(b) + bytearray(w * e * 4)
    nh = h + e
    lift = max(1, int(round(2 * k)))
    for x in range(w):
        yb = -1
        for y in range(h - 1, -1, -1):
            if b[(y * w + x) * 4 + 3] > 128:
                yb = y
                break
        if yb < h * from_frac:
            continue
        sy = max(0, yb - lift)
        pix = bytes(b[(sy * w + x) * 4:(sy * w + x) * 4 + 3]) + b"\xff"
        for y in range(yb + 1, nh):
            i = (y * w + x) * 4
            out[i:i + 4] = pix
    surf = spritefit._frombytes(bytes(out), (w, nh))
    _sprite_cache[key] = hd.wrap(surf) if k != 1 else surf
    return key


def has_sprite(name):
    return sprite(name) is not None


def blit_sprite(surf, name, x, y, scale=1.0, anchor="midbottom", flip=False, angle=0.0, sway=0.0):
    """Рисует спрайт с привязкой anchor в точке (x, y). Возвращает False, если картинки нет.
    angle — повернуть вокруг центра; sway — наклонить (в градусах) вокруг низа картинки, как растение на ветру."""
    img = sprite(name)
    if img is None:
        return False
    # масштаб округляем до шага 2%: растущие растения меняют размер каждый кадр, а так
    # уменьшенная копия картинки берётся из кэша, а не пересчитывается заново
    scale = round(scale / SCALE_STEP) * SCALE_STEP or SCALE_STEP
    key = (name, round(scale, 3), flip)
    out = _sprite_scaled.get(key)
    if out is None:
        out = img
        if flip:
            out = pygame.transform.flip(out, True, False)
        if abs(scale - 1.0) > 1e-3:
            out = pygame.transform.smoothscale(out, (max(1, int(out.get_width() * scale + 0.5)),
                                                     max(1, int(out.get_height() * scale + 0.5))))
        if len(_sprite_scaled) > 3000:
            _sprite_scaled.clear()
        _sprite_scaled[key] = out
    if sway and anchor == "midbottom":
        # поворот вокруг середины низа: центр повёрнутой картинки сдвигается так, чтобы низ остался на месте
        h2 = out.get_height() / 2
        a = math.radians(sway)
        out = pygame.transform.rotate(out, sway)
        cx, cy = x - h2 * math.sin(a), y - h2 * math.cos(a)
        surf.blit(out, out.get_rect(center=(int(round(cx)), int(round(cy)))))
        return True
    if angle:
        out = pygame.transform.rotate(out, angle)
        anchor = "center"
    r = out.get_rect(**{anchor: (int(round(x)), int(round(y)))})
    surf.blit(out, r)
    return True


def blit_tf(surf, names, x, y, scale=1.0, flip=False, sx=1.0, sy=1.0, angle=0.0, pivot="midbottom", alpha=None):
    """Спрайт «как живой» (3.3): сплющить/вытянуть (sx, sy), наклонить на angle градусов (+ — против часовой)
    вокруг середины низа (pivot="midbottom": лапы стоят на месте) или центра (pivot="center"), сделать
    полупрозрачным (alpha 0..255). (x, y) — точка pivot. names — имя или список (берётся первый, что есть).
    Возвращает False, если ни одной картинки нет (тогда рисуем кодом)."""
    for name in ([names] if isinstance(names, str) else names):
        img = sprite(name)
        if img is None:
            continue
        kx = round(scale * sx / SCALE_STEP) * SCALE_STEP or SCALE_STEP
        ky = round(scale * sy / SCALE_STEP) * SCALE_STEP or SCALE_STEP
        key = ("tf", name, round(kx, 3), round(ky, 3), flip)
        out = _sprite_scaled.get(key)
        if out is None:
            out = img
            if flip:
                out = pygame.transform.flip(out, True, False)
            if abs(kx - 1.0) > 1e-3 or abs(ky - 1.0) > 1e-3:
                out = pygame.transform.smoothscale(out, (max(1, int(out.get_width() * kx + 0.5)),
                                                         max(1, int(out.get_height() * ky + 0.5))))
            if len(_sprite_scaled) > 3000:
                _sprite_scaled.clear()
            _sprite_scaled[key] = out
        h2 = out.get_height() / 2
        rot = out
        if abs(angle) > 0.05:
            rot = pygame.transform.rotate(out, angle)
        if alpha is not None and alpha < 255:
            if rot is out:
                rot = out.copy()          # картинка из кэша — её прозрачность не трогаем
            hd.real(rot).set_alpha(max(0, int(alpha)))     # только число: set_alpha(None) делает картинку сплошной
        if pivot == "midbottom":
            a = math.radians(angle)
            cx, cy = x - h2 * math.sin(a), y - h2 * math.cos(a)
        else:
            cx, cy = x, y
        surf.blit(rot, rot.get_rect(center=(int(round(cx)), int(round(cy)))))
        return True
    return False


def blit_any(surf, names, *args, **kwargs):
    """Пробует несколько имён по очереди (например, сначала зимний вариант, потом обычный)."""
    for name in names:
        if blit_sprite(surf, name, *args, **kwargs):
            return True
    return False


def farm_names(folder, file):
    """Сначала картинка для текущей фермы, потом общая: tiles/summer/soil -> tiles/soil."""
    return [f"{folder}/{FARM_ID[0]}/{file}", f"{folder}/{file}"]


# текущая ферма (папка спрайтов растений и фонов) — меняет art_world.apply_farm

CROP_KEYS = list(FARMS[0]["plants"])   # ключи культур текущей фермы (для спрайтов)
FARM_ID = [FARMS[0]["id"]]             # id текущей фермы (папка спрайтов)
