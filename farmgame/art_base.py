# -*- coding: utf-8 -*-
"""Цвета, сетка поля, текст и шрифты, примитивы (многоугольники, овалы, плашки, монетки, полоски).

Часть art.py (3.17: вынесено без изменений). Снаружи всё берётся как раньше: from .art import ...
"""
import math
import os
import random

import pygame

from . import spritefit
from . import hd
from .config import *  # noqa: F401,F403
from .art_sprites import *  # noqa: F401,F403


# ======================================================================
#                              ГРАФИКА
# ======================================================================
OUT = (60, 40, 35)
WHITE = (255, 255, 255)
GOLD = (255, 205, 50)
GREEN = (80, 180, 70)
GRASS = (156, 222, 118)
SAND = (245, 230, 140)
SOIL = (226, 146, 86)
SOIL_DARK = (198, 118, 64)
SOIL_SIDE = (168, 98, 55)
BTN_BLUE = (70, 170, 230)
BTN_GREEN = (110, 200, 90)
BTN_GREY = (165, 165, 170)
PANEL = (240, 222, 212)
PILL = (160, 228, 245)

TW, TH = 180, 90            # размер изометрической клетки
OX, OY = 500, 215           # центр клетки (0,0)
# Поле — матрица 3x3, повёрнутая ромбом: 11 сверху, 13 справа, 31 слева, 33 снизу.
# Культуры открываются по порядку: 33, 32, 31, 23, 22, 21, 13, 12, 11.
UNLOCK_ORDER = ["33", "32", "31", "23", "22", "21", "13", "12", "11"]
# клетка "rc" (строка, столбец) -> координаты сетки (i, j): i = столбец-1, j = строка-1
SLOT = [(int(rc[1]) - 1, int(rc[0]) - 1) for rc in UNLOCK_ORDER]
DRAW_ORDER = sorted(range(N_CROPS), key=lambda k: (SLOT[k][0] + SLOT[k][1], SLOT[k][0]))
BAR_W = 50                  # ширина полоски прогресса под грядкой
PLANT_SPOTS = [(0, -16), (-42, 8), (42, 8)]

TRUCK_PARK_X = 830
TRUCK_GROUND = 592


def P(v):
    return int(round(v))


FIELD_DY = [0.0]           # 3.38.1: сдвиг всего поля вниз (своё у фермы: THEME["field_dy"]; ставит apply_farm)


def grid_oy():
    return OY + FIELD_DY[0]


def tile_center(i, j):
    return OX + (i - j) * TW / 2, grid_oy() + (i + j) * TH / 2


def crop_center(k):
    return tile_center(*SLOT[k])


# ---------- текст ----------
_fonts = {}
_texts = {}
SYS_FONTS = "segoeui,arial,verdana,dejavusans,liberationsans,freesans"
FONT_EXTS = (".ttf", ".otf")
FONT_SAMPLE = "Весёлая ферма: $1.23M, урожай x10!"
_font_files = {}
_font_ratio = {}


def font_files():
    """Свой шрифт из assets/fonts/: {"title": путь, "body": путь} (None — системный).
    title — для надписей с обводкой (кнопки, заголовки): файл с Black/Heavy в имени;
    body — для обычного текста: ExtraBold/Bold. Один файл — он для всего."""
    if _font_files:
        return _font_files
    found = []
    folder = os.path.join(ASSET_DIR, "fonts")
    if os.path.isdir(folder):
        found = [os.path.join(folder, fn) for fn in sorted(os.listdir(folder)) if fn.lower().endswith(FONT_EXTS)]

    def pick(*words):
        for w in words:
            for path in found:
                if w in os.path.basename(path).lower().replace("-", "").replace("_", ""):
                    return path
        return None
    body = pick("extrabold", "bold", "semibold", "black", "heavy") or (found[0] if found else None)
    title = pick("black", "heavy", "extrabold") or body
    _font_files.update(title=title, body=body)
    if found:
        print("Шрифт:", ", ".join(os.path.basename(p) for p in {title, body} if p))
    return _font_files


def _sys_font(size):
    return pygame.font.SysFont(SYS_FONTS, size, bold=True)


def _ratio(kind, path):
    """Свой шрифт подгоняем по ширине под прежний (системный): все надписи остаются в своих кнопках."""
    r = _font_ratio.get(kind)
    if r is None:
        try:
            a = _sys_font(40).size(FONT_SAMPLE)[0]
            b = pygame.font.Font(path, 40).size(FONT_SAMPLE)[0]
            r = max(0.8, min(1.15, a / b)) if a > 0 and b > 0 else 1.0
        except Exception:
            r = 1.0
        _font_ratio[kind] = r
    return r


def font(size, kind="body"):
    key = (size, kind)
    f = _fonts.get(key)
    if f is None:
        path = font_files().get(kind)
        f = None
        if path:
            try:
                f = pygame.font.Font(path, max(1, int(round(size * _ratio(kind, path)))))
            except Exception as e:      # битый файл шрифта не должен ронять игру
                print(f"Шрифт {os.path.basename(path)} не загрузился: {e}")
                _font_files[kind] = None
        if f is None:
            f = _sys_font(size)
        _fonts[key] = f
    return f


def render_text(s, size, color, outline):
    key = (s, size, color, outline, hd.K[0])
    img = _texts.get(key)
    if img is not None:
        return img
    k = hd.K[0]
    # HD: буквы рендерятся шрифтом в k раз крупнее — текст чёткий, а снаружи он прежнего размера
    kind = "title" if outline else "body"    # с обводкой — жирнее (Black), обычный текст — ExtraBold
    f = font(size, kind) if k == 1 else font(max(1, int(round(size * k))), kind)
    base = f.render(s, True, color)
    if outline:
        o = 2 if size >= 16 else 1
        if k != 1:
            o = max(1, int(round(o * k)))
        w, h = base.get_size()
        img = pygame.Surface((w + 2 * o, h + 2 * o), pygame.SRCALPHA)
        ol = f.render(s, True, outline)
        for dx in range(-o, o + 1):
            for dy in range(-o, o + 1):
                if (dx or dy) and (k == 1 or dx * dx + dy * dy <= o * o + o):   # в HD обводка круглая
                    img.blit(ol, (dx + o, dy + o))
        img.blit(base, (o, o))
    else:
        img = base
    if k != 1:
        img = hd.HiSurf(img, k)
    if len(_texts) > 1500:
        _texts.clear()
    _texts[key] = img
    return img


def draw_text(surf, s, size, pos, color=WHITE, anchor="center", outline=OUT):
    img = render_text(s, size, color, outline)
    r = img.get_rect(**{anchor: (P(pos[0]), P(pos[1]))})
    surf.blit(img, r)
    return r


def draw_text_fit(surf, s, size, pos, maxw, color=WHITE, anchor="center", outline=OUT):
    """Как draw_text, но уменьшает шрифт, пока текст не влезет в maxw."""
    while size > 8 and render_text(s, size, color, outline).get_width() > maxw:
        size -= 1
    return draw_text(surf, s, size, pos, color, anchor, outline)


# ---------- примитивы ----------
def poly(surf, color, pts, w=2):
    pts = [(P(x), P(y)) for x, y in pts]
    pygame.draw.polygon(surf, color, pts)
    if w:
        pygame.draw.polygon(surf, OUT, pts, w)


def ellipse(surf, color, cx, cy, w, h, ow=2):
    r = pygame.Rect(P(cx - w / 2), P(cy - h / 2), max(1, P(w)), max(1, P(h)))
    pygame.draw.ellipse(surf, color, r)
    if ow and r.w >= 6 and r.h >= 6:
        pygame.draw.ellipse(surf, OUT, r, ow)


def blob(surf, color, circles, ow=2):
    """Несколько кругов с общей обводкой: (x, y, r)."""
    for x, y, r in circles:
        pygame.draw.circle(surf, OUT, (P(x), P(y)), P(r) + ow)
    for x, y, r in circles:
        pygame.draw.circle(surf, color, (P(x), P(y)), max(1, P(r)))


def leaf(surf, x, y, ang_deg, length, width, color, vein=None):
    a = math.radians(ang_deg)
    dx, dy = math.cos(a), -math.sin(a)
    nx, ny = -dy, dx
    pts = [(x, y),
           (x + dx * length * 0.5 + nx * width / 2, y + dy * length * 0.5 + ny * width / 2),
           (x + dx * length, y + dy * length),
           (x + dx * length * 0.5 - nx * width / 2, y + dy * length * 0.5 - ny * width / 2)]
    poly(surf, color, pts, 2 if length > 8 else 1)
    if vein and length > 8:
        pygame.draw.line(surf, vein, (P(x), P(y)), (P(x + dx * length * 0.8), P(y + dy * length * 0.8)), 1)


def face(surf, x, y, s):
    if s < 0.45:
        return
    er = max(1, P(1.7 * s))
    pygame.draw.circle(surf, OUT, (P(x - 4 * s), P(y - 1 * s)), er)
    pygame.draw.circle(surf, OUT, (P(x + 4 * s), P(y - 1 * s)), er)
    r = pygame.Rect(P(x - 3 * s), P(y - 1 * s), max(2, P(6 * s)), max(2, P(5 * s)))
    pygame.draw.arc(surf, OUT, r, math.pi + 0.3, 2 * math.pi - 0.3, 1)
    if s >= 0.9:  # румянец
        pygame.draw.circle(surf, (255, 140, 150), (P(x - 7 * s), P(y + 2 * s)), max(1, P(1.6 * s)))
        pygame.draw.circle(surf, (255, 140, 150), (P(x + 7 * s), P(y + 2 * s)), max(1, P(1.6 * s)))


def rounded(surf, color, rect, radius=10, border=3, border_color=OUT, skin="auto"):
    """Скруглённый прямоугольник. Цвет старой кнопки/карточки (см. skin.AUTO) — рисуется оформлением
    «дерево + пергамент» (картинка из assets/ui/ или то же кодом); skin=None — всегда просто цветом."""
    rect = pygame.Rect(rect)
    if skin:
        from . import skin as _skin
        name = _skin.AUTO.get(tuple(color[:3])) if skin == "auto" else skin
        if name and border:
            _skin.draw(surf, name, rect)
            return
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)


def draw_coin(surf, x, y, r, color=GOLD):
    if blit_sprite(surf, "icons/coin" if color == GOLD else "icons/coin_silver", x, y, r / 17, "center"):
        return
    pygame.draw.circle(surf, OUT, (P(x), P(y)), P(r) + 2)
    pygame.draw.circle(surf, color, (P(x), P(y)), P(r))
    lighter = tuple(min(255, c + 35) for c in color)
    pygame.draw.circle(surf, lighter, (P(x), P(y)), max(1, P(r * 0.72)))
    draw_text(surf, "$", max(10, P(r * 1.25)), (x, y), (190, 120, 10) if color == GOLD else (90, 110, 150), outline=None)


def draw_leaf_icon(surf, x, y, s=1.0):
    if blit_sprite(surf, "icons/leaf", x, y, s, "center"):
        return
    pygame.draw.circle(surf, OUT, (P(x), P(y)), P(16 * s) + 2)
    pygame.draw.circle(surf, (120, 210, 110), (P(x), P(y)), P(16 * s))
    leaf(surf, x - 7 * s, y + 7 * s, 45, 19 * s, 11 * s, (60, 160, 60), vein=(30, 100, 30))


def draw_seal_icon(surf, x, y, s=1.0):
    """Королевская печать: красный сургуч с короной."""
    if blit_sprite(surf, "icons/seal", x, y, s, "center"):
        return
    blob(surf, (200, 45, 50), [(x + math.cos(a) * 11 * s, y + math.sin(a) * 11 * s, 7 * s) for a in
                               [i * math.pi / 4 for i in range(8)]] + [(x, y, 13 * s)], 2)
    pygame.draw.circle(surf, (165, 30, 40), (P(x), P(y)), P(10 * s))
    poly(surf, (250, 205, 70), [(x - 7 * s, y + 4 * s), (x - 7 * s, y - 5 * s), (x - 3.5 * s, y - 1 * s), (x, y - 7 * s),
                                (x + 3.5 * s, y - 1 * s), (x + 7 * s, y - 5 * s), (x + 7 * s, y + 4 * s)], 1)


def draw_frostleaf_icon(surf, x, y, s=1.0):
    """3.24: голубой листочек — валюта зимы."""
    if blit_sprite(surf, "icons/frostleaf", x, y, s, "center"):
        return
    pygame.draw.circle(surf, OUT, (P(x), P(y)), P(16 * s) + 2)
    pygame.draw.circle(surf, (170, 215, 245), (P(x), P(y)), P(16 * s))
    leaf(surf, x - 7 * s, y + 7 * s, 45, 19 * s, 11 * s, (70, 150, 220), vein=(40, 95, 160))


def draw_hook_icon(surf, x, y, s=1.0):
    """3.36: крючок — валюта Рыбацкой деревни."""
    if blit_sprite(surf, "icons/hook", x, y, s, "center"):
        return
    pygame.draw.circle(surf, OUT, (P(x), P(y)), P(16 * s) + 2)
    pygame.draw.circle(surf, (150, 190, 215), (P(x), P(y)), P(16 * s))
    r = pygame.Rect(P(x - 8 * s), P(y - 2 * s), max(4, P(14 * s)), max(4, P(14 * s)))
    pygame.draw.arc(surf, OUT, r, math.pi, 2 * math.pi + 0.2, max(3, P(4 * s)))
    pygame.draw.arc(surf, (230, 232, 238), r, math.pi, 2 * math.pi + 0.2, max(1, P(2 * s)))
    pygame.draw.line(surf, OUT, (P(x + 6 * s), P(y + 5 * s)), (P(x + 6 * s), P(y - 11 * s)), max(3, P(4 * s)))
    pygame.draw.line(surf, (230, 232, 238), (P(x + 6 * s), P(y + 5 * s)), (P(x + 6 * s), P(y - 11 * s)), max(1, P(2 * s)))
    pygame.draw.circle(surf, OUT, (P(x + 6 * s), P(y - 12 * s)), max(2, P(3 * s)), max(1, P(1.5 * s)))
    poly(surf, (230, 232, 238), [(x - 8 * s, y + 5 * s), (x - 11 * s, y), (x - 5 * s, y + 2 * s)], 1)


def draw_cur_icon(surf, x, y, s=1.0):
    """Иконка валюты престижа текущей фермы (лист, печать, голубой листочек или крючок)."""
    icon = CUR.get("icon")
    if icon == "scale" and blit_sprite(surf, "icons/scale", x, y, s, "center"):    # 3.48: своя картинка главы 5
        return
    {"seal": draw_seal_icon, "frostleaf": draw_frostleaf_icon, "hook": draw_hook_icon}.get(icon, draw_leaf_icon)(surf, x, y, s)


def draw_bar(surf, rect, frac, color=(255, 200, 40)):
    rect = pygame.Rect(rect)
    from . import skin                       # 3.18: своя полоска ui/bar_frame + ui/bar_fill
    if skin.bar(surf, rect, frac, color):
        return
    pygame.draw.rect(surf, OUT, rect, border_radius=rect.h // 2)
    inner = rect.inflate(-4, -4)
    pygame.draw.rect(surf, (90, 70, 60), inner, border_radius=inner.h // 2)
    frac = max(0.0, min(1.0, frac))
    if frac > 0:
        fill = pygame.Rect(inner.x, inner.y, max(inner.h, P(inner.w * frac)), inner.h)
        pygame.draw.rect(surf, color, fill, border_radius=inner.h // 2)
