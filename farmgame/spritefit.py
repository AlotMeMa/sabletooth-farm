# -*- coding: utf-8 -*-
"""Автоподгонка картинок из assets/ под размер, который ждёт игра.

Картинку из нейросети (большую, на однотонном фоне) можно класть как есть:
  1) однотонный фон (маджента, белый — любой ровный цвет по углам) убирается заливкой от краёв,
     поэтому белая курица на маджента-фоне или белые стены на белом фоне внутри контура не пострадают;
  2) пустые поля обрезаются;
  3) рисунок вписывается в холст из шаблона с сохранением пропорций и ставится «ногами» на свою точку.

Особые случаи:
  crops/<ферма>/<культура>.png — полоска из 3 стадий роста (широкая картинка) режется на 3 спрайта;
  icons/sheet.png — лист иконок 3×3 режется на 9 иконок (порядок как в промпте).

Картинку ровно нужного размера и уже с прозрачностью игра не трогает — ручная работа важнее.
Готовый результат кладётся в .sprite_cache/ рядом с игрой, чтобы не считать его при каждом запуске.
"""
import hashlib
import os
import re

import pygame

from .config import BASE_DIR, W, H, PRIZE_SHEET_IDS

CACHE_VERSION = "fit7"   # 3.11.2: светлое (мука, дымка) у края на мадженте больше не розовеет — картинки пересчитаются
CACHE_DIR = os.path.join(BASE_DIR, ".sprite_cache")

SHADOW_HUE, SHADOW_HUE_LOW = 0.6, 0.2   # тень на цветном фоне: насколько её оттенок может отличаться от фона
                                       # (по «слабому» каналу фона — строже)
BG_TOL = 48      # насколько пиксель может отличаться от цвета фона и всё ещё считаться фоном
EDGE_TOLS = (130, 170)   # кольца края: до этой разницы с фоном пиксель делается полупрозрачным (без ореола)
MIN_ALPHA = 16   # что прозрачнее — считается пустотой при обрезке
CURSOR_SIZE = 24         # обычный курсор, px (поменьше)
CURSOR_HOVER_SIZE = 32   # курсор над кнопкой, px
HOLE_TOL = 34    # «дырка» внутри рисунка — пиксели почти точно цвета фона
SPILL_NEAR = 0.04   # 3.11.2: до такого расстояния от фона (доля стороны картинки) светлое отмывается от цвета фона
SPILL_HUE = 22      # отмывается только то, что того же оттенка, что и фон (± градусов): смесь бесцветного с фоном
SPILL_HUE_LIGHT, SPILL_LIGHT = 45, 130   # светлое (слабый канал фона ярче 130) — и в стороне до 45° (мука на мадженте)
HOLE_MAX_WHITE = 0.004   # на белом фоне убираем только просветы меньше 0.4% картинки
HOLE_SLIM = 3.0          # ...и вытянутые просветы (длина ≥ 3 ширин, например между стеблями) — до 4 таких лимитов
LINE_TOL = 100           # линии-рамки на фоне (нейросеть рисует стадии «по клеткам»): бледные, тонкие, через полкартинки
LINE_MIN = 0.4

ICON_SHEET_ORDER = ["coin", "coin_silver", "leaf", "seal", "peasant", "egg", "milk", "truffle", "honey"]
# лист кнопок 3×3 (assets/ui/buttons.png), порядок по строкам:
BUTTON_SHEET_ORDER = ["shop", "upgrade", "tree", "barn", "mill", "move", "settings", "field", "close"]
# 3.14.3: листы казино — несколько картинок одной генерацией
PRIZE_SHEET_ORDER = list(PRIZE_SHEET_IDS)       # лист призов 3×3 (assets/icons/prizes.png): порядок клеток
                                                    # (новые призы — отдельными файлами icons/prize_<id>)
CHIP_SHEET_ORDER = ["ui/chip_5", "ui/chip_10", "ui/chip_25", "ui/chip_50", "props/roulette_ball"]   # ряд из 5 (ui/chips.png)
# 3.16: доска заданий и таблички (2×3), облачко и стрелка (1×3), частицы и лампочки гирлянды (3×3)
BOARD_SHEET_ORDER = ["quest_note_1", "quest_note_2", "quest_note_3", "sign", "pin", "wax_seal"]
TALK_SHEET_ORDER = ["bubble", "bubble_tail", "arrow"]
# 3.18: лист плашек. 3.19.1: Gemini нарисовал его 3 ряда × 2 столбца, по рядам: светлая плашка счёта,
# тёмная плашка сообщения; лента-баннер, вторая лента (не нужна — пропуск); рамка полоски, вывеска казино.
# Белой заливки полоски на листе нет — заливку рисует код (или свой файл ui/bar_fill.png).
PLATE_SHEET_ORDER = ["pill", "toast", "banner", "_unused", "bar_frame", "sign_casino"]
FX_SHEET_ORDER = ["feather", "star", "puff", "spark", "raindrop", "bulb_red", "bulb_yellow", "bulb_green", "bulb_blue"]
SHEETS = {   # имя листа -> (папка/префикс картинок, порядок, строк, столбцов)
    "icons/sheet": ("icons/", ICON_SHEET_ORDER, 3, 3),
    "ui/buttons": ("ui/btn_", BUTTON_SHEET_ORDER, 3, 3),
    "icons/prizes": ("icons/prize_", PRIZE_SHEET_ORDER, 3, 3),
    "ui/chips": ("", CHIP_SHEET_ORDER, 1, 5),   # полные имена: фишки 5/10/25/50 и шарик рулетки
    "ui/board_sheet": ("ui/", BOARD_SHEET_ORDER, 2, 3),
    "ui/talk_sheet": ("ui/", TALK_SHEET_ORDER, 1, 3),
    "fx/sheet": ("fx/", FX_SHEET_ORDER, 3, 3),
    "ui/plate_sheet": ("ui/", PLATE_SHEET_ORDER, 3, 2),
}
BTN_CANVAS = 128   # 3.4.2: кнопки подгоняются вдвое крупнее (было 64) и уменьшаются при выводе — края чище
MILL_PROPS = {   # props/<имя>: холст w×h и привязка (экран мельницы, 3.7)
    "millstone": (160, 160, "center"), "mill_bed": (260, 104, "bottom"), "mill_hopper": (150, 200, "bottom"),
    "grain_heap": (140, 70, "bottom"), "flour_sacks_1": (90, 90, "bottom"), "flour_sacks_2": (120, 90, "bottom"),
    "flour_sacks_3": (150, 100, "bottom"), "oven": (240, 240, "bottom"), "oven_fire": (100, 75, "bottom"),
    "bread_shelf": (200, 150, "bottom"),
    "mill_card": (360, 130, "bottom"), "bakery_card": (360, 130, "bottom"),   # 3.13: картинки карточек мельницы
}
UI_TRIM = {"panel": (520, 400), "card": (420, 140), "panel_header": (440, 110),   # наибольший размер (3.4)
           # 3.16: растягиваемые записки доски, свиток недели, табличка на поле, облачко речи
           "quest_note_1": (490, 334), "quest_note_2": (490, 334), "quest_note_3": (490, 334),
           "quest_weekly": (460, 720), "sign": (300, 170), "bubble": (360, 200),
           # 3.18: плашки, сообщение, баннер, полоска, указатели таверны
           "pill": (360, 100), "toast": (480, 90), "banner": (520, 110), "bar_frame": (400, 60),
           "bar_fill": (400, 60), "sign_board": (264, 208), "sign_casino": (300, 108)}
DECOR_SIZE = {"cat": (120, 80, "bottom"), "kettle": (110, 110, "bottom"), "flowers": (60, 110, "bottom"),
              "rug": (600, 130, "center")}          # 3.19: decor/<имя> — холст w×h и как прижат рисунок
FX_SIZE = {"feather": 40, "star": 32, "puff": 40, "spark": 24, "raindrop": 24}   # 3.16: частицы, холст s×s
STAGE_HEIGHT = {1: 0.42, 2: 0.7, 3: 1.0}   # высота стадии, если стадии лежат отдельными файлами


# ----------------------------------------------------------------------
#                    куда и как вписывать каждую картинку
# ----------------------------------------------------------------------
def _spec(canvas, box, align="bottom", hfrac=1.0):
    return {"canvas": canvas, "box": box, "align": align, "hfrac": hfrac}


def _box(w, h, l, t, r, b):
    """Холст w×h, внутри него поле для рисунка с отступами слева/сверху/справа/снизу."""
    return (w, h), (l, t, w - r, h - b)


FIT_SCALE = [1.0]   # HD-режим: всё подгоняется в столько раз крупнее (см. hd.py)


def _work(n):
    """Рабочий размер исходника для подгонки холста размером n: в 4 раза больше обычного размера
    (в HD — не меньше чем в 2 раза больше настоящего). Так в HD подгонка не становится в разы дольше."""
    return int(n * max(2.0, 4.0 / FIT_SCALE[0]))


def _upscale(img, k=None):
    """Картинку «обычного» размера — в k раз крупнее (для HD)."""
    k = FIT_SCALE[0] if k is None else k
    if k == 1:
        return img
    w, h = img.get_size()
    return pygame.transform.smoothscale(img, (max(1, int(round(w * k))), max(1, int(round(h * k)))))


def fit_spec(name):
    """Как подгонять картинку с этим именем (в HD — крупнее в FIT_SCALE раз). None — не трогать вообще."""
    spec = _fit_spec_base(name)
    k = FIT_SCALE[0]
    if spec is None or k == 1:
        return spec
    (cw, ch), (x0, y0, x1, y1) = spec["canvas"], spec["box"]
    r = lambda v: int(round(v * k))
    return dict(spec, canvas=(r(cw), r(ch)), box=(r(x0), r(y0), r(x1), r(y1)))


HI = "@2x"   # 3.13.2: «name@2x» — та же картинка, подогнанная вдвое крупнее (для крупных иконок: не мыльная)


def _fit_spec_base(name):
    """Как подгонять картинку с этим именем в обычном размере (координаты 1000x640)."""
    if name.endswith(HI):
        spec = _fit_spec_base(name[:-len(HI)])
        if spec is None:
            return None
        (cw, ch), (x0, y0, x1, y1) = spec["canvas"], spec["box"]
        return dict(spec, canvas=(cw * 2, ch * 2), box=(x0 * 2, y0 * 2, x1 * 2, y1 * 2))
    n = name.lower()
    parts = n.split("/")
    folder, last = parts[0], parts[-1]
    if folder == "backgrounds" or last == "fence_front":
        return _spec((W, H), (0, 0, W, H), "full")
    if folder == "crops":
        m = re.match(r"^(.*)_([123])$", last)
        c, b = _box(110, 120, 3, 2, 3, 4)
        return _spec(c, b, "bottom", STAGE_HEIGHT[int(m.group(2))] if m else 1.0)
    if folder == "tiles":
        return _spec(*_box(184, 104, 9, 5, 9, 5), "center")
    if folder == "props" and last == "fence_strip":
        # прямой кусок забора анфас: игра сама повторит его по длине и наклонит вдоль края поля
        return _spec((640, 128), (0, 0, 640, 128), "bottom")
    if folder == "props":
        table = {"tree": _box(130, 150, 2, 2, 2, 2), "bush": _box(80, 64, 1, 2, 1, 0),
                 "castle": _box(220, 200, 2, 2, 2, 2), "chapel": _box(100, 140, 2, 2, 2, 2),
                 "chapel_ringing": _box(100, 140, 2, 2, 2, 2)}
        if last in table:
            return _spec(*table[last], "bottom")
        if last == "roulette_wheel":       # 3.14: колесо рулетки (игра вращает; центр = ось)
            return _spec(*_box(338, 338, 1, 1, 1, 1), "center")
        if last == "roulette_ball":
            return _spec(*_box(40, 40, 1, 1, 1, 1), "center")
        if last in MILL_PROPS:            # 3.6: детали живой мельницы (экран мельницы — в 3.7)
            w, h, anchor = MILL_PROPS[last]
            return _spec(*_box(w, h, 2, 2, 2, 0 if anchor == "bottom" else 2), anchor)
        if last == "sun":
            return _spec(*_box(130, 130, 3, 3, 3, 3), "center")
        if last.startswith("cloud"):
            return _spec(*_box(150, 100, 3, 3, 3, 3), "center")
        return None
    if folder == "buildings":
        if last == "windmill_blades":
            return _spec(*_box(180, 180, 2, 2, 2, 2), "center")
        if last == "windmill":
            return _spec((340, 230), (110, 8, 270, 205), "bottom")
        if last == "barn":
            return _spec(*_box(340, 230, 15, 5, 15, 15), "bottom")
        return None
    if folder == "animals":
        return _spec(*_box(160, 130, 8, 4, 8, 4), "bottom")
    if folder == "creatures":
        for key, size in (("squirrel", (90, 80)), ("crow", (90, 90)), ("bandit", (80, 90))):
            if last.startswith(key):
                return _spec(*_box(size[0], size[1], 2, 2, 2, 2), "bottom")
        return None
    if folder == "characters":
        # жители таверны: бармен — по пояс (низ картинки = край стойки), бард — в полный рост (низ = сцена)
        if last == "barman":
            return _spec(*_box(150, 150, 4, 4, 4, 0), "bottom")
        if last in ("bard", "bard_girl"):    # 3.15.2: певица — скин барда из призов казино
            return _spec(*_box(130, 180, 4, 4, 4, 0), "bottom")
        if last == "croupier":            # 3.14: крупье по пояс, низ картинки = край стола
            return _spec(*_box(150, 150, 4, 4, 4, 0), "bottom")
        if last in ("miller", "baker"):    # работники мельницы и пекарни (3.7), в полный рост
            return _spec(*_box(100, 150, 3, 3, 3, 0), "bottom")
        return None
    if folder == "vehicles":
        if last.startswith("truck"):
            return _spec(*_box(240, 124, 4, 2, 4, 0), "bottom")
        if last.startswith("cart"):
            return _spec(*_box(270, 124, 4, 2, 4, 0), "bottom")
        return None
    if folder == "ui" and (last in UI_TRIM or last.startswith("button_")):
        # 3.4: окна и кнопки — фон убрать, поля обрезать, пропорции картинки сохранить (игра режет её на 9/3 части)
        size = UI_TRIM.get(last, (300, 100))
        return _spec(size, (0, 0) + size, "trim")
    if folder == "ui" and last == "pin":               # 3.16: булавка записки на доске
        return _spec(*_box(28, 28, 1, 1, 1, 1), "center")
    if folder == "ui" and last == "wax_seal":          # 3.16: сургучная печать свитка недели
        return _spec(*_box(44, 44, 1, 1, 1, 1), "center")
    if folder == "ui" and last == "bubble_tail":       # 3.16: хвостик облачка, кончик внизу по центру
        return _spec(*_box(32, 24, 0, 0, 0, 0), "bottom")
    if folder == "ui" and last == "arrow":             # 3.16: стрелка обучения, остриё внизу по центру
        return _spec(*_box(44, 60, 1, 1, 1, 0), "bottom")
    if folder == "fx":                                 # 3.16: частицы и лампочки гирлянды
        if last.startswith("bulb_"):
            return _spec(*_box(28, 28, 1, 1, 1, 1), "center")
        if last in FX_SIZE:
            sz = FX_SIZE[last]
            return _spec(*_box(sz, sz, 1, 1, 1, 1), "center")
        return None
    if folder == "decor" and last in DECOR_SIZE:      # 3.19: украшения у камина
        w, h, align = DECOR_SIZE[last]
        return _spec(*_box(w, h, 1, 1, 1, 1), align)
    if folder == "ui" and last == "slider_knob":
        return _spec(*_box(48, 48, 1, 1, 1, 1), "center")
    if folder == "ui" and last.startswith("chip_"):   # 3.14: фишки казино (рисуются в 0.5 — вдвое крупнее для чёткости)
        return _spec(*_box(72, 72, 1, 1, 1, 1), "center")
    if folder == "ui" and last.startswith("btn_"):
        return _spec(*_box(BTN_CANVAS, BTN_CANVAS, 4, 4, 4, 4), "center")
    if folder == "ui" and last == "logo":              # экран загрузки: название игры
        return _spec(*_box(600, 200, 4, 4, 4, 4), "center")
    if folder == "ui" and last == "loading_ring":      # колесо, игра его вращает (центр картинки = ось)
        return _spec(*_box(200, 200, 2, 2, 2, 2), "center")
    if folder == "ui" and last == "loading_center":    # талисман в центре колеса, не вращается
        return _spec(*_box(120, 120, 2, 2, 2, 2), "center")
    if folder == "ui" and last == "cursor":
        # курсор: рисунок прижимается к левому верхнему углу — там кончик стрелки (точка клика)
        return _spec((32, 32), (0, 0, CURSOR_SIZE, CURSOR_SIZE), "topleft")
    if folder == "ui" and last == "cursor_hover":
        return _spec((40, 40), (0, 0, CURSOR_HOVER_SIZE, CURSOR_HOVER_SIZE), "topleft")
    if folder == "icons":
        if last == "peasant":
            s = 26
        elif last.startswith("prize_"):   # 3.14: призы казино
            s = 40
        elif last.startswith("note_"):    # ноты барда (3.6): icons/note_1 ... note_4
            s = 30
        elif last in ("egg", "milk", "truffle", "honey"):
            s = 30
        elif last == "sheet":
            return None
        else:
            s = 40
        return _spec(*_box(s, s, 1, 1, 1, 1), "center")
    return None


# ----------------------------------------------------------------------
#                       пиксели (без numpy)
# ----------------------------------------------------------------------
def _tobytes(surf):
    f = getattr(pygame.image, "tobytes", None) or pygame.image.tostring
    return bytearray(f(surf, "RGBA"))


def _frombytes(buf, size):
    f = getattr(pygame.image, "frombytes", None) or pygame.image.fromstring
    surf = f(bytes(buf), size, "RGBA")
    try:
        surf = surf.convert_alpha()
    except pygame.error:
        pass
    return surf


class Pix:
    """RGBA-картинка как bytearray: быстро читать и писать без get_at/set_at."""

    def __init__(self, surf):
        self.w, self.h = surf.get_size()
        self.buf = _tobytes(surf)

    def surface(self, rect=None):
        if rect is None:
            return _frombytes(self.buf, (self.w, self.h))
        x0, y0, x1, y1 = rect
        out = bytearray()
        for y in range(y0, y1):
            i = (y * self.w + x0) * 4
            out += self.buf[i:i + (x1 - x0) * 4]
        return _frombytes(out, (x1 - x0, y1 - y0))

    def alpha(self, x, y):
        return self.buf[(y * self.w + x) * 4 + 3]

    def has_transparency(self):
        b, w, h = self.buf, self.w, self.h
        for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
            if b[(y * w + x) * 4 + 3] < 250:
                return True
        return False

    def background_color(self):
        """Цвет ровного фона по краям или None, если края пёстрые."""
        b, w, h = self.buf, self.w, self.h
        pts = []
        for t in range(9):
            fx = t / 8
            for x, y in ((int(fx * (w - 1)), 0), (int(fx * (w - 1)), h - 1),
                         (0, int(fx * (h - 1))), (w - 1, int(fx * (h - 1)))):
                i = (y * w + x) * 4
                pts.append((b[i], b[i + 1], b[i + 2]))
        pts.sort(key=sum)
        mid = pts[len(pts) // 2]
        close = [p for p in pts if max(abs(p[0] - mid[0]), abs(p[1] - mid[1]), abs(p[2] - mid[2])) < BG_TOL]
        if len(close) < len(pts) * 0.7:
            return None
        return tuple(sum(p[k] for p in close) // len(close) for k in range(3))

    def remove_background(self, bg):
        """Убирает фон:
        1) заливка от краёв картинки — по цвету фона, а на цветном фоне (маджента) ещё и по его теням;
        2) «дырки» цвета фона внутри рисунка (просветы между листьями, между досками кузова):
           на цветном фоне убираются все, на белом — только мелкие (крупное белое внутри контура —
           это часть рисунка: курица, дверь амбара);
        3) мягкий полупрозрачный край без цветного ореола."""
        b, w, h = self.buf, self.w, self.h
        br, bgc, bb = bg
        chroma = max(bg) - min(bg) > 120          # цветной фон (маджента, зелёный), а не белый/серый

        def dist(i):
            return max(abs(b[i] - br), abs(b[i + 1] - bgc), abs(b[i + 2] - bb))

        def bg_like(i):
            if dist(i) < BG_TOL:
                return True
            if chroma:   # тень на цветном фоне: тот же оттенок, только темнее
                r, g, bl = b[i], b[i + 1], b[i + 2]
                cr, cg, cb = br / 255.0, bgc / 255.0, bb / 255.0
                lum = max(r, g, bl)
                if lum < 50:
                    return False
                # насколько пиксель похож на «фон, умноженный на яркость»
                k = lum / 255.0
                if max(abs(r - cr * 255 * k), abs(g - cg * 255 * k), abs(bl - cb * 255 * k)) >= 40:
                    return False
                # 3.4.2: и оттенок тот же. Иначе тёмно-коричневый контур рисунка, который касается фона,
                # принимался за тень (тёмные цвета все «близко» к тёмной мадженте) и съедался.
                # Главное — канал, которого в фоне почти нет (у мадженты — зелёный): в тени он тоже около нуля,
                # а в коричневом контуре заметен.
                top = max(cr, cg, cb)
                for v, c in ((r, cr), (g, cg), (bl, cb)):
                    lim = SHADOW_HUE_LOW if c / top < 0.3 else SHADOW_HUE
                    if abs(v / lum - c / top) >= lim:
                        return False
                return True
            return False

        is_bg = bytearray(w * h)
        stack = []
        for x in range(w):
            stack.append(x)
            stack.append((h - 1) * w + x)
        for y in range(h):
            stack.append(y * w)
            stack.append(y * w + w - 1)
        while stack:
            p = stack.pop()
            if is_bg[p] or not bg_like(p * 4):
                continue
            is_bg[p] = 1
            x = p % w
            if x > 0:
                stack.append(p - 1)
            if x < w - 1:
                stack.append(p + 1)
            if p >= w:
                stack.append(p - w)
            if p < (h - 1) * w:
                stack.append(p + w)
        self._remove_rule_lines(is_bg, dist)
        # просветы цвета фона внутри рисунка
        hole_limit = w * h if chroma else int(w * h * HOLE_MAX_WHITE)
        seen = bytearray(w * h)
        for start in range(w * h):
            if is_bg[start] or seen[start] or dist(start * 4) >= HOLE_TOL:
                continue
            comp, stack = [], [start]
            seen[start] = 1
            while stack:
                p = stack.pop()
                comp.append(p)
                x = p % w
                for q in ((p - 1) if x > 0 else -1, (p + 1) if x < w - 1 else -1,
                          p - w if p >= w else -1, p + w if p < (h - 1) * w else -1):
                    if q >= 0 and not seen[q] and not is_bg[q] and dist(q * 4) < HOLE_TOL:
                        seen[q] = 1
                        stack.append(q)
            if len(comp) > hole_limit and not chroma and len(comp) <= hole_limit * 4:
                # большой белый просвет оставляем (это часть рисунка: дверь, бок курицы),
                # но вытянутый — это щель между стеблями или досками (лён: белая полоса между стеблями)
                xs = [p % w for p in comp]
                ys = [p // w for p in comp]
                bw, bh = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
                if max(bw, bh) >= HOLE_SLIM * min(bw, bh):
                    for p in comp:
                        is_bg[p] = 1
                    continue
            if len(comp) <= hole_limit:
                for p in comp:
                    is_bg[p] = 1
        for p in range(w * h):
            if is_bg[p]:
                b[p * 4 + 3] = 0
        if chroma:
            self._despill(is_bg, bg)
        # край: 2 кольца пикселей вокруг фона. Похожие на фон делаем полупрозрачными
        # и «отмываем» их цвет от фона — так не остаётся розового/белого ореола вокруг контура.
        ring = is_bg
        for tol in EDGE_TOLS:
            span = tol - BG_TOL
            nxt = bytearray(w * h)
            for p in range(w * h):
                if is_bg[p] or (ring is not is_bg and ring[p]):
                    continue
                x = p % w
                if not ((x > 0 and ring[p - 1]) or (x < w - 1 and ring[p + 1])
                        or (p >= w and ring[p - w]) or (p < (h - 1) * w and ring[p + w])):
                    continue
                nxt[p] = 1
                i = p * 4
                d = dist(i)
                if d >= tol:
                    continue
                a = max(0.08, (d - BG_TOL) / span)
                for k, c in ((0, br), (1, bgc), (2, bb)):
                    b[i + k] = max(0, min(255, int(c + (b[i + k] - c) / a)))
                b[i + 3] = int(b[i + 3] * a)
            ring = nxt

    def _despill(self, is_bg, bg):
        """3.11.2: светлое полупрозрачное у края (мука, пыль, дымка), нарисованное нейросетью прямо на
        мадженте, выходит розовым: в нём «просвечивает» фон. Такой пиксель — смесь бесцветного рисунка
        (белое, серое, кремовое) с фоном: по тому, насколько сильные каналы фона (у мадженты — красный
        и синий) выше слабого (зелёного), считаем долю фона, убираем её и делаем пиксель настолько же
        прозрачнее. Только пиксели рядом с фоном и только оттенка самого фона (SPILL_HUE градусов):
        поросёнок, румянец, редис, виноград и фиолетовые платья не трогаются."""
        import colorsys
        b, w, h = self.buf, self.w, self.h
        top = max(bg)
        strong = [k for k in range(3) if bg[k] > top * 0.6]
        weak = [k for k in range(3) if k not in strong]
        if not weak or not strong:
            return 0
        span = min(bg[k] for k in strong) - max(bg[k] for k in weak)
        if span < 120:
            return 0
        bg_hue = colorsys.rgb_to_hsv(*(c / 255 for c in bg))[0] * 360
        reach = max(3, int(max(w, h) * SPILL_NEAR))
        near = bytearray(is_bg)
        front = [p for p in range(w * h) if is_bg[p]]
        for _ in range(reach):                 # расстояние до фона: слоями (не дальше reach)
            nxt = []
            for p in front:
                x = p % w
                for q in ((p - 1) if x > 0 else -1, (p + 1) if x < w - 1 else -1,
                          p - w if p >= w else -1, p + w if p < (h - 1) * w else -1):
                    if q >= 0 and not near[q]:
                        near[q] = 2
                        nxt.append(q)
            front = nxt
            if not front:
                break
        n = 0
        for p in range(w * h):
            if near[p] != 2:
                continue
            i = p * 4
            px = (b[i], b[i + 1], b[i + 2])
            spill = min(px[k] for k in strong) - max(px[k] for k in weak)
            if spill <= 8:
                continue
            hue = colorsys.rgb_to_hsv(px[0] / 255, px[1] / 255, px[2] / 255)[0] * 360
            off = abs((hue - bg_hue + 180) % 360 - 180)
            # оттенок фона — всегда; чуть в сторону (кремовое/тёплое с мадженты) — только светлое
            if off > SPILL_HUE and not (off <= SPILL_HUE_LIGHT and min(px[k] for k in weak) >= SPILL_LIGHT):
                continue
            a = max(0.0, 1.0 - spill / span)
            if a < 0.04:
                b[i + 3] = 0
            else:
                for k in range(3):
                    b[i + k] = max(0, min(255, int(round((px[k] - (1 - a) * bg[k]) / a))))
                b[i + 3] = int(b[i + 3] * a)
            n += 1
        return n

    def _remove_rule_lines(self, is_bg, dist):
        """Бледные прямые линии через всю картинку (рамки между стадиями, которые рисует нейросеть).
        Пиксель линии: не фон, но бледный (ближе LINE_TOL к фону), а в 3 пикселях слева и справа
        (для строк — сверху и снизу) уже фон. Если таких в столбце (строке) больше LINE_MIN высоты —
        это линия, её пиксели становятся фоном. Стебли не трогаются: у них тёмный контур."""
        w, h = self.w, self.h

        def thin_x(p):
            x = p % w
            return x >= 3 and x < w - 3 and is_bg[p - 3] and is_bg[p + 3]

        def thin_y(p):
            return p >= 3 * w and p < (h - 3) * w and is_bg[p - 3 * w] and is_bg[p + 3 * w]

        found = []
        for x in range(w):
            pts = [y * w + x for y in range(h) if not is_bg[y * w + x]]
            if len(pts) < h * LINE_MIN:
                continue
            line = [p for p in pts if dist(p * 4) < LINE_TOL and thin_x(p)]
            if len(line) >= h * LINE_MIN:
                found += line
        for y in range(h):
            pts = [y * w + x for x in range(w) if not is_bg[y * w + x]]
            if len(pts) < w * LINE_MIN:
                continue
            line = [p for p in pts if dist(p * 4) < LINE_TOL and thin_y(p)]
            if len(line) >= w * LINE_MIN:
                found += line
        for p in found:
            is_bg[p] = 1
        return len(found)

    def bbox(self, rect=None):
        """Границы непрозрачного рисунка внутри rect (x0, y0, x1, y1) или None."""
        x0, y0, x1, y1 = rect or (0, 0, self.w, self.h)
        b, w = self.buf, self.w
        rows = [y for y in range(y0, y1) if any(b[(y * w + x) * 4 + 3] > MIN_ALPHA for x in range(x0, x1))]
        if not rows:
            return None
        cols = [x for x in range(x0, x1)
                if any(b[(y * w + x) * 4 + 3] > MIN_ALPHA for y in range(rows[0], rows[-1] + 1))]
        return cols[0], rows[0], cols[-1] + 1, rows[-1] + 1

    def occupancy(self, axis, rect):
        """Для каждого столбца (axis='x') или строки ('y') внутри rect: есть ли там рисунок."""
        x0, y0, x1, y1 = rect
        b, w = self.buf, self.w
        if axis == "x":
            return [any(b[(y * w + x) * 4 + 3] > MIN_ALPHA for y in range(y0, y1)) for x in range(x0, x1)]
        return [any(b[(y * w + x) * 4 + 3] > MIN_ALPHA for x in range(x0, x1)) for y in range(y0, y1)]


def split_by_gaps(occ, n):
    """Делит линию на n кусков по самым широким пустым промежуткам (иначе — поровну)."""
    filled = [i for i, v in enumerate(occ) if v]
    if not filled:
        return [(i * len(occ) // n, (i + 1) * len(occ) // n) for i in range(n)]
    start, end = filled[0], filled[-1] + 1
    gaps, i = [], start
    while i < end:
        if not occ[i]:
            j = i
            while j < end and not occ[j]:
                j += 1
            gaps.append((j - i, i, j))
            i = j
        else:
            i += 1
    if len(gaps) >= n - 1:
        cuts = sorted(gaps, reverse=True)[:n - 1]
        cuts.sort(key=lambda g: g[1])
        bounds, prev = [], start
        for _size, a, bnd in cuts:
            bounds.append((prev, a))
            prev = bnd
        bounds.append((prev, end))
        return bounds
    step = (end - start) / n
    return [(int(start + k * step), int(start + (k + 1) * step)) for k in range(n)]


# ----------------------------------------------------------------------
#                              подгонка
# ----------------------------------------------------------------------
def _prepare(img, work_max):
    """Уменьшает огромную картинку до рабочего размера, убирает фон. -> Pix."""
    w, h = img.get_size()
    k = min(1.0, work_max / max(w, h))
    if k < 1.0:
        img = pygame.transform.smoothscale(img, (max(1, int(w * k)), max(1, int(h * k))))
    px = Pix(img)
    if not px.has_transparency():
        bg = px.background_color()
        if bg is not None:
            px.remove_background(bg)
    return px


def _place(piece, spec, scale=None):
    """Кладёт вырезанный кусок на холст из spec. scale=None — вписать в поле целиком."""
    cw, ch = spec["canvas"]
    x0, y0, x1, y1 = spec["box"]
    bw, bh = x1 - x0, (y1 - y0) * spec["hfrac"]
    pw, ph = piece.get_size()
    if scale is None:
        scale = min(bw / pw, bh / ph)
    nw, nh = max(1, int(round(pw * scale))), max(1, int(round(ph * scale)))
    piece = pygame.transform.smoothscale(piece, (nw, nh))
    out = pygame.Surface((cw, ch), pygame.SRCALPHA)
    cx = (x0 + x1) / 2
    if spec["align"] == "topleft":
        r = piece.get_rect(topleft=(x0, y0))
    elif spec["align"] == "center":
        r = piece.get_rect(center=(int(round(cx)), int(round((y0 + y1) / 2))))
    else:
        r = piece.get_rect(midbottom=(int(round(cx)), y1))
    out.blit(piece, r)
    return out


def fit_single(img, spec):
    cw, ch = spec["canvas"]
    if spec["align"] == "full":
        return pygame.transform.smoothscale(img, (cw, ch))
    if spec["align"] == "trim":       # без холста: обрезанный рисунок, вписанный в cw×ch с его пропорциями
        px = _prepare(img, _work(max(cw, ch)))
        bb = px.bbox()
        if bb is None:
            return None
        piece = px.surface(bb)
        w, h = piece.get_size()
        k = min(cw / w, ch / h)
        return pygame.transform.smoothscale(piece, (max(1, int(round(w * k))), max(1, int(round(h * k)))))
    px = _prepare(img, _work(max(cw, ch)))
    bb = px.bbox()
    if bb is None:
        return None
    return _place(px.surface(bb), spec)


def fit_strip(img, specs):
    """Полоска из нескольких стадий одного растения: режем по промежуткам, масштаб общий."""
    cw, ch = specs[0]["canvas"]
    px = _prepare(img, _work(max(cw, ch) * len(specs)))
    whole = px.bbox()
    if whole is None:
        return [None] * len(specs)
    cols = split_by_gaps(px.occupancy("x", whole), len(specs))
    pieces = []
    for a, b in cols:
        bb = px.bbox((whole[0] + a, whole[1], whole[0] + b, whole[3]))
        pieces.append(bb)
    real = [bb for bb in pieces if bb]
    if not real:
        return [None] * len(specs)
    x0, y0, x1, y1 = specs[0]["box"]
    scale = min(min((x1 - x0) / (bb[2] - bb[0]) for bb in real), min((y1 - y0) / (bb[3] - bb[1]) for bb in real))
    full = dict(specs[0], hfrac=1.0)
    return [(_place(px.surface(bb), full, scale) if bb else None) for bb in pieces]


def fit_sheet(img, rows, cols, spec_for):
    """Лист иконок rows×cols. spec_for(i) — spec для i-й иконки. -> список поверхностей."""
    specs = [spec_for(i) for i in range(rows * cols)]      # None — клетка не нужна (пропуск в порядке листа)
    biggest = max(max(sp["canvas"]) for sp in specs if sp)
    px = _prepare(img, _work(biggest * max(rows, cols)))
    whole = px.bbox()
    if whole is None:
        return [None] * (rows * cols)
    out = []
    for ra, rb in split_by_gaps(px.occupancy("y", whole), rows):
        band = (whole[0], whole[1] + ra, whole[2], whole[1] + rb)
        for ca, cb in split_by_gaps(px.occupancy("x", band), cols):
            bb = px.bbox((band[0] + ca, band[1], band[0] + cb, band[3]))
            i = len(out)
            out.append(_fit_piece(px.surface(bb), specs[i]) if bb and specs[i] else None)
    return out


def _fit_piece(piece, spec):
    """Кусок листа -> картинка по spec. «trim» (окна, записки, облачко) — без холста, со своими пропорциями."""
    if spec is None:
        return piece
    if spec["align"] == "trim":
        cw, ch = spec["canvas"]
        w, h = piece.get_size()
        k = min(cw / w, ch / h)
        return pygame.transform.smoothscale(piece, (max(1, int(round(w * k))), max(1, int(round(h * k)))))
    return _place(piece, spec)


# ----------------------------------------------------------------------
#                 загрузка с подгонкой и кэшем на диске
# ----------------------------------------------------------------------
def _cache_path(name, src, part=None):
    st = os.stat(src)
    # в ключе и правила подгонки: поменялся размер в игре — картинка пересчитается сама
    key = f"{CACHE_VERSION}|{name}|{fit_spec(name)}|{os.path.abspath(src)}|{st.st_mtime_ns}|{st.st_size}"
    if part and part[0] == "sheet":     # 3.19.1: и клетка листа (поменялась сетка листа — вырежется заново)
        key += f"|sheet{part[1]}:{part[4]}x{part[5]}"
    return os.path.join(CACHE_DIR, hashlib.md5(key.encode("utf-8")).hexdigest() + ".png")


def _load(path):
    img = pygame.image.load(path)
    try:
        img = img.convert_alpha()
    except pygame.error:
        pass
    return img


def _save_cache(path, surf):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        pygame.image.save(surf, path)
    except Exception as e:  # кэш — не обязательная вещь
        print(f"Не удалось сохранить кэш спрайта: {e}")


_strip_cache = {}


def is_strip(img, path=None):
    """Полоска из нескольких стадий растения? Смотрим не на пропорции (нейросеть может выдать
    и 16:9, и 3:1), а на содержимое: после удаления фона в картинке 3 отдельных рисунка
    с пустыми промежутками между ними."""
    key = None
    if path:
        try:
            st = os.stat(path)
            key = (os.path.abspath(path), st.st_mtime_ns, st.st_size)
        except OSError:
            key = None
        if key in _strip_cache:
            return _strip_cache[key]
    w, h = img.get_size()
    result = False
    if w >= 1.3 * h:                       # высокая/квадратная картинка — точно одно растение
        px = _prepare(img, 360)            # грубо, но быстро: нужен только силуэт
        bb = px.bbox()
        if bb:
            occ = px.occupancy("x", bb)
            min_gap = max(2, int(len(occ) * 0.015))
            gaps, run = 0, 0
            for v in occ:
                if not v:
                    run += 1
                else:
                    if run >= min_gap:
                        gaps += 1
                    run = 0
            result = gaps >= 2
    if key:
        _strip_cache[key] = result
    return result


def load_fitted(name, path, part=None):
    """Загружает картинку path для спрайта name, подгоняя её под нужный размер.
    part: None — обычный файл; ("strip", stage) — стадия из полоски;
    ("sheet", i, префикс, порядок, строк, столбцов) — из листа."""
    spec = fit_spec(name)
    if spec is None and part is None:
        return _upscale(_load(path))     # правила нет — картинка как есть (в HD — крупнее)
    cache = _cache_path(name, path, part)
    if os.path.exists(cache):
        try:
            return _load(cache)
        except Exception:
            pass
    img = _load(path)
    cw, ch = spec["canvas"] if spec else (0, 0)
    if part is None:
        base = _fit_spec_base(name)["canvas"]
        if img.get_size() in ((cw, ch), base):
            if spec["align"] == "full" or Pix(img).has_transparency():
                # ровно нужный размер и уже вырезано — не трогаем (в HD только увеличиваем целиком)
                return img if img.get_size() == (cw, ch) else pygame.transform.smoothscale(img, (cw, ch))
        if spec["align"] == "full" and name.endswith("fence_front"):
            # передний забор во весь экран: нейросеть не даёт прозрачность — вырезаем однотонный фон
            out = pygame.transform.smoothscale(img, (cw, ch))
            px = Pix(out)
            if not px.has_transparency():
                bg = px.background_color()
                if bg is not None:
                    px.remove_background(bg)
                    out = px.surface()
        elif spec["align"] == "full":
            return fit_single(img, spec)   # простое растяжение, кэш не нужен
        else:
            out = fit_single(img, spec)
    elif part[0] == "strip":
        base = name.rsplit("_", 1)[0]
        specs = [fit_spec(f"{base}_3")] * 3
        outs = fit_strip(img, specs)
        for st, surf in enumerate(outs, 1):
            if surf is not None and st != part[1]:
                _save_cache(_cache_path(f"{base}_{st}", path), surf)
        out = outs[part[1] - 1]
    else:  # sheet: ("sheet", номер, префикс, порядок, строк, столбцов)
        _kind, idx, prefix, order, rows, cols = part
        sfx = HI if name.endswith(HI) else ""
        outs = fit_sheet(img, rows, cols, lambda i: fit_spec(prefix + order[i] + sfx))
        for i, surf in enumerate(outs):
            if surf is not None and i != idx:
                _save_cache(_cache_path(prefix + order[i] + sfx, path, (_kind, i, prefix, order, rows, cols)), surf)
        out = outs[idx]
    if out is None:
        return None
    w0, h0 = img.get_size()
    print(f"Подогнала картинку {name}: {w0}×{h0} → {out.get_width()}×{out.get_height()}")
    _save_cache(cache, out)
    return out


def make_glow(img, color, radius=4):
    """Светлый ореол по силуэту картинки (для подсветки кнопки под курсором).
    Возвращает поверхность больше исходной на radius с каждой стороны."""
    from . import hd
    if isinstance(img, hd.HiSurf):      # HD: ореол считаем по настоящим пикселям, толщину — тоже в k раз больше
        return hd.HiSurf(_make_glow(img.surf, color, max(1, int(round(radius * img.k)))), img.k)
    return _make_glow(img, color, radius)


GLOW_SOFT = 3      # 3.3.1: ореол считается в 3 раза крупнее и сглаживается — без «лесенки» по краю


def _make_glow(img, color, radius):
    """Силуэт с мягкой прозрачностью края (а не «есть пиксель / нет»), раздутый на radius
    в увеличенном в GLOW_SOFT раз виде, уменьшается обратно со сглаживанием, и край ещё раз смягчается."""
    px = Pix(img)
    w, h = px.w, px.h
    b = px.buf
    sil = bytearray(w * h * 4)
    r, g, bl = color
    for p in range(w * h):
        a = b[p * 4 + 3]
        if a:
            i = p * 4
            sil[i], sil[i + 1], sil[i + 2], sil[i + 3] = r, g, bl, min(255, a * 2)
    sil_s = _frombytes(sil, (w, h))
    pad = radius + 2                               # +2: место под мягкий край
    s = GLOW_SOFT
    big = pygame.transform.smoothscale(sil_s, (w * s, h * s))
    rr = radius * s
    out = pygame.Surface(((w + 2 * pad) * s, (h + 2 * pad) * s), pygame.SRCALPHA)
    out.fill((r, g, bl, 0))
    step = max(1, s // 2)                          # раздуваем по кругу: шаг в полпикселя исходной картинки
    for dx in range(-rr, rr + 1, step):
        for dy in range(-rr, rr + 1, step):
            if dx * dx + dy * dy <= rr * rr:
                out.blit(big, (pad * s + dx, pad * s + dy))
    ow, oh = w + 2 * pad, h + 2 * pad
    out = pygame.transform.smoothscale(out, (ow, oh))
    soft = pygame.transform.smoothscale(out, (max(1, ow // 2), max(1, oh // 2)))   # лёгкое размытие края
    return pygame.transform.smoothscale(soft, (ow, oh))
