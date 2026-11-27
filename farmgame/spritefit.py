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

try:                     # 3.40.4: если numpy есть — маски фона считаются им (в разы быстрее); нет — тем же кодом на Python
    import numpy as _np
except Exception:        # noqa: BLE001
    _np = None

from .config import BASE_DIR, W, H, PRIZE_SHEET_IDS

CACHE_VERSION = "fit11"   # 3.40.4: ключ — содержимое файла (md5); в листах убираются крохи рамок
CACHE_DIR = os.path.join(BASE_DIR, ".sprite_cache")

SHADOW_HUE, SHADOW_HUE_LOW = 0.6, 0.2   # тень на цветном фоне: насколько её оттенок может отличаться от фона
                                       # (по «слабому» каналу фона — строже)
BG_TOL = 48      # насколько пиксель может отличаться от цвета фона и всё ещё считаться фоном
EDGE_TOLS = (130, 170)   # кольца края: до этой разницы с фоном пиксель делается полупрозрачным (без ореола)
SLED_BOX = {"sled_1": (430, 124), "sled_2": (430, 142)}   # 3.26.2: остальные упряжки — как телега, 270×124
GRID_FULL, GRID_THIN = 0.85, 0.012
GRID_DARK, GRID_DARK_SHARE = 110, 0.6   # 3.45.1: и почти вся тёмная (чёрная рамка), а не цветные тела рыб   # 3.40.4: линия сетки листа — «не фон» в 85% высоты, толщиной до 1.2% картинки
SHEET_SPECK = 24  # 3.40.4: в листе крошка — кусок не больше стольких пикселей (хвост рамки между клетками)
MIN_ALPHA = 16   # что прозрачнее — считается пустотой при обрезке
SPECK_SHARE, SPECK_MIN = 0.00006, 6   # 3.26.1: крошка — отдельный кусочек меньше этой доли площади (не меньше 6 px)
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
# 3.20: лист карточек дерева 2×3 — можно копить, можно купить, всё изучено; закрыто, кружок пустой, кружок полный
TREE_SHEET_ORDER = ["tree_node_open", "tree_node_ready", "tree_node_max", "tree_node_locked", "tree_pip_off", "tree_pip_on"]
# 3.26.2: все мелкие картинки зимы одним запросом к нейросети (лист 3×3, assets/icons/winter_sheet.png)
WINTER_SHEET_ORDER = ["icons/frostleaf", "icons/down", "icons/wool",
                      "icons/cheese", "icons/jam", "icons/gnome",
                      "ui/btn_shaman", "characters/gnome_worker", "characters/gnome_shaman"]
# 3.27: Игровая одним запросом (лист 2×3, assets/icons/gameroom_sheet.png): обод колеса фортуны, стрелка, значки игр
GAMEROOM_SHEET_ORDER = ["props/fortune_wheel", "props/fortune_pointer", "icons/game_wheel",
                        "icons/game_roulette", "icons/game_blackjack", "icons/game_secret"]
# 3.27: заранее под блэкджек (лист 3×3, assets/icons/cards_sheet.png): рубашка, пустое лицо, башмак, 4 масти,
# две особые рубашки (кандидаты в джекпот колеса фортуны)
CARDS_SHEET_ORDER = ["props/card_back", "props/card_face", "props/card_shoe",
                     "icons/suit_hearts", "icons/suit_diamonds", "icons/suit_clubs",
                     "icons/suit_spades", "props/card_back_gold", "props/card_back_winter"]
# 3.27: разные гномы зимы одним запросом (лист 2×3, assets/characters/gnomes_sheet.png): 4 работника и 2 шамана
GNOMES_SHEET_ORDER = ["gnome_worker_1", "gnome_worker_2", "gnome_worker_3",
                      "gnome_worker_4", "gnome_shaman_1", "gnome_shaman_2"]
# 3.39.1: свои крестьяне у грядок средневековья (лист 2×2, assets/characters/peasants_sheet.png)
PEASANTS_SHEET_ORDER = ["peasant_worker_1", "peasant_worker_2", "peasant_worker_3", "peasant_worker_4"]
# 3.29: второй лист призов (3×3, assets/icons/prizes_2.png) — украшения 3.19–3.27, у которых не было картинок;
# девятая клетка — запас (пропуск)
PRIZE2_SHEET_ORDER = ["flowers", "rug", "kettle", "cat", "fiddler", "bagpiper", "rainbow_notes", "star_trail", "_unused"]
# 3.33: значки новых призов — два листа 3×3 (assets/icons/prizes_3.png и prizes_4.png)
PRIZE3_SHEET_ORDER = ["acorn", "seal_trophy", "crown", "snowflake", "golden_squirrel", "golden_pitchfork",
                      "wreath", "lanterns", "rocking_chair"]
PRIZE4_SHEET_ORDER = ["dog", "owl", "own_mug", "fireflies", "leaf_trail", "bubble_trail", "cards_gold", "cards_winter",
                      "_unused"]
# 3.36: Рыбацкая деревня — мелочь одним листом 3×3 (assets/icons/fishing_sheet.png) и повозка 1×3 (полные имена)
FISHING_SHEET_ORDER = ["creatures/crab", "creatures/crab_gold", "creatures/gull", "creatures/gull_fly", "icons/fisherman",
                       "icons/hook", "ui/btn_fishfest", "characters/fisher_worker", "characters/fisher_dancer"]
# 3.38.1: лодка вместо повозки. 3.40.4: на листе пользователя лодки идут наоборот — парусник, баркас, лодочка
BOAT_SHEET_ORDER = ["vehicles/boat_2", "vehicles/boat_1", "vehicles/boat_0"]
BOAT_BOX = {"boat_0": (210, 120), "boat_1": (250, 170), "boat_2": (280, 200)}   # лодочка ниже и короче парусника
PREDATOR_SHEET_ORDER = ["pike", "asp", "zander", "burbot", "catfish", "eel", "taimen", "sturgeon", "beluga", "swordfish"]
# 3.40.4: лист пользователя нарисован 5 рядов × 2 и без сома (на его месте второй осётр — «_spare», не берём).
# Сом пока рисуется кодом; своя картинка — assets/fish/catfish.png (отдельный файл важнее листа).
# 3.45: рыбки аквариума одним листом 3×3 (assets/fish/swim_sheet.png), смотрят влево, порядок — как участки пруда
SWIM_SHEET_ORDER = ["swim_roach", "swim_crucian", "swim_perch", "swim_bream", "swim_carp", "swim_trout", "swim_salmon",
                    "swim_koi", "swim_goldfish"]
PREDATOR_SHEET_CELLS = ["pike", "asp", "zander", "burbot", "eel", "taimen", "sturgeon", "_spare", "beluga", "swordfish"]
# 3.33: сами украшения и персонажи в сцене (лист 2×3, assets/decor/sheet_2.png, полные имена)
DECOR2_SHEET_ORDER = ["decor/wreath", "decor/lantern", "decor/rocking_chair", "decor/own_mug", "characters/dog",
                      "characters/owl"]
# 3.34.2: свой значок-медаль у каждого достижения — 5 листов 3×3 (assets/icons/ach_sheet_1..5.png), порядок как в
# achievements.ACHIEVEMENTS; в последнем листе три клетки — запас (пропуск)
def _ach_orders():
    from .achievements import ACHIEVEMENTS
    ids = [a["id"] for a in ACHIEVEMENTS]
    ids = ids[:43] + ["_unused"] * 2 + ids[43:]      # 3.39: листы 1–5 уже нарисованы (2 запасные клетки), новые — с 6-го
    ids += ["_unused"] * (-len(ids) % 9)
    return [ids[i:i + 9] for i in range(0, len(ids), 9)]


ACH_SHEET_ORDERS = _ach_orders()
FX_SHEET_ORDER = ["feather", "star", "puff", "spark", "raindrop", "bulb_red", "bulb_yellow", "bulb_green", "bulb_blue"]
SHEETS = {   # имя листа -> (папка/префикс картинок, порядок, строк, столбцов)
    "icons/sheet": ("icons/", ICON_SHEET_ORDER, 3, 3),
    "ui/buttons": ("ui/btn_", BUTTON_SHEET_ORDER, 3, 3),
    "icons/prizes": ("icons/prize_", PRIZE_SHEET_ORDER, 3, 3),
    "icons/prizes_2": ("icons/prize_", PRIZE2_SHEET_ORDER, 3, 3),   # 3.29: украшения без картинок
    "icons/prizes_3": ("icons/prize_", PRIZE3_SHEET_ORDER, 3, 3),   # 3.33: трофеи и украшения
    "icons/prizes_4": ("icons/prize_", PRIZE4_SHEET_ORDER, 3, 3),   # 3.33: персонажи, эффекты, прочее
    "decor/sheet_2": ("", DECOR2_SHEET_ORDER, 2, 3),                # 3.33: новые украшения и звери в сцене
    # 3.48: лист главы 5 пользователя — пока берём только монету-чешую (остальное — когда решим главу)
    "icons/dragons_sheet": ("", ["_unused"] * 5 + ["icons/scale"] + ["_unused"] * 3, 3, 3),
    # 3.47: призы глав 3–5 — значки (по листу на главу) и украшения в зале (один лист на все 9)
    "icons/prizes_5": ("icons/prize_", ["ice_idols", "helga", "gnome_choir", "snow_globe", "antlers", "ice_chandelier",
                                        "snow_trail", "frost_notes", "snowfall"], 3, 3),
    "icons/prizes_6": ("icons/prize_", ["sirens", "undina", "kuzma", "ship_wheel", "goldfish_bowl", "nets",
                                        "starfish_trail", "pearl_notes", "jellyfish"], 3, 3),
    "icons/prizes_7": ("icons/prize_", ["flame_idols", "saya", "grom", "dragon_egg", "dragon_shield", "brazier",
                                        "ember_trail", "fire_notes", "fire_butterflies"], 3, 3),
    "decor/sheet_3": ("decor/", ["snow_globe", "antlers", "ice_chandelier", "ship_wheel", "goldfish_bowl", "nets",
                                 "dragon_egg", "dragon_shield", "brazier"], 3, 3),
    "icons/fishing_sheet": ("", FISHING_SHEET_ORDER, 3, 3),         # 3.36: Рыбацкая деревня
    "vehicles/boat_sheet": ("", BOAT_SHEET_ORDER, 1, 3),            # 3.38.1: лодка рыботорговца, 3 уровня
    "fish/predators_sheet": ("fish/", PREDATOR_SHEET_CELLS, 5, 2),
    "fish/swim_sheet": ("fish/", SWIM_SHEET_ORDER, 3, 3),          # 3.45: рыбки аквариума  # 3.37: хищники садка (3.40.4: 5×2, как нарисовано)
    "characters/snails_sheet": ("characters/snail_", ["1", "2", "3", "4", "5"], 1, 5),   # 3.40: улитки скачек
    "ui/chips": ("", CHIP_SHEET_ORDER, 1, 5),   # полные имена: фишки 5/10/25/50 и шарик рулетки
    "ui/board_sheet": ("ui/", BOARD_SHEET_ORDER, 2, 3),
    "ui/talk_sheet": ("ui/", TALK_SHEET_ORDER, 1, 3),
    "fx/sheet": ("fx/", FX_SHEET_ORDER, 3, 3),
    "ui/plate_sheet": ("ui/", PLATE_SHEET_ORDER, 3, 2),
    "ui/tree_sheet": ("ui/", TREE_SHEET_ORDER, 2, 3),
    "icons/winter_sheet": ("", WINTER_SHEET_ORDER, 3, 3),   # полные имена: иконки, кнопка и гномы зимы
    "icons/gameroom_sheet": ("", GAMEROOM_SHEET_ORDER, 2, 3),   # 3.27: Игровая
    "icons/cards_sheet": ("", CARDS_SHEET_ORDER, 3, 3),         # 3.27: заготовка под блэкджек
    "characters/gnomes_sheet": ("characters/", GNOMES_SHEET_ORDER, 2, 3),   # 3.27: разные гномы одним запросом
    "characters/peasants_sheet": ("characters/", PEASANTS_SHEET_ORDER, 2, 2),   # 3.39.1: крестьяне у грядок
}
SHEETS.update({f"icons/ach_sheet_{n}": ("icons/ach_", order, 3, 3)      # 3.34.2: медали достижений, 5 листов
               for n, order in enumerate(ACH_SHEET_ORDERS, 1)})
BTN_CANVAS = 128   # 3.4.2: кнопки подгоняются вдвое крупнее (было 64) и уменьшаются при выводе — края чище
MILL_PROPS = {   # props/<имя>: холст w×h и привязка (экран мельницы, 3.7)
    "millstone": (160, 160, "center"), "mill_bed": (260, 104, "bottom"), "mill_hopper": (150, 200, "bottom"),
    "grain_heap": (140, 70, "bottom"), "flour_sacks_1": (90, 90, "bottom"), "flour_sacks_2": (120, 90, "bottom"),
    "flour_sacks_3": (150, 100, "bottom"), "oven": (240, 240, "bottom"), "oven_fire": (100, 75, "bottom"),
    "bread_shelf": (200, 150, "bottom"),
    "mill_card": (360, 130, "bottom"), "bakery_card": (360, 130, "bottom"),   # 3.13: картинки карточек мельницы
}
UI_TRIM = {"panel": (520, 400), "card": (420, 140), "panel_header": (440, 110),   # наибольший размер (3.4)
           # 3.20: карточки дерева
           "tree_node_open": (420, 140), "tree_node_ready": (420, 140), "tree_node_max": (420, 140),
           "tree_node_locked": (420, 140),
           # 3.16: растягиваемые записки доски, свиток недели, табличка на поле, облачко речи
           "quest_note_1": (490, 334), "quest_note_2": (490, 334), "quest_note_3": (490, 334),
           "quest_weekly": (460, 720), "sign": (300, 170), "bubble": (360, 200),
           # 3.18: плашки, сообщение, баннер, полоска, указатели таверны
           "pill": (360, 100), "toast": (480, 90), "banner": (520, 110), "bar_frame": (400, 60),
           "bar_fill": (400, 60), "sign_board": (264, 208), "sign_casino": (300, 108)}
DECOR_SIZE = {"cat": (120, 80, "bottom"), "kettle": (110, 110, "bottom"), "flowers": (60, 110, "bottom"),
              "rug": (600, 130, "center"),
              # 3.33: венок (на стене у камина), фонарь (под балкой зала, верх — крючок), кресло-качалка, своя кружка
              "wreath": (130, 150, "center"), "lantern": (60, 100, "top"), "rocking_chair": (190, 190, "bottom"),
              "own_mug": (60, 64, "bottom"),          # 3.19: decor/<имя> — холст w×h и как прижат рисунок
              # 3.47: украшения глав 3–5 (на стойке — низ; на стене — центр; люстра и сети висят — верх)
              "snow_globe": (60, 70, "bottom"), "goldfish_bowl": (64, 64, "bottom"), "dragon_egg": (56, 70, "bottom"),
              "brazier": (80, 80, "bottom"), "antlers": (100, 80, "bottom"), "ship_wheel": (80, 80, "center"),
              "dragon_shield": (70, 80, "center"), "ice_chandelier": (110, 90, "top"), "nets": (740, 70, "top")}
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
    if folder == "fish" and last not in ("predators_sheet", "swim_sheet"):   # 3.37: хищник садка, смотрит влево; рисуется с 0.45 * k
        return _spec(*_box(200, 100, 6, 6, 6, 6), "center")
    if folder == "tiles":     # 3.39.6: «fill» — все плитки ровно 166×94, как бы ни были нарисованы (решение 26.11)
        return _spec(*_box(184, 104, 9, 5, 9, 5), "fill")
    if folder == "props" and last == "fence_strip":
        # прямой кусок забора анфас: игра сама повторит его по длине и наклонит вдоль края поля
        return _spec((640, 128), (0, 0, 640, 128), "bottom")
    if folder == "props":
        if last == "fortune_wheel":        # 3.27: обод колеса фортуны (середина пустая — сектора кодом)
            return _spec(*_box(300, 300, 0, 0, 0, 0), "center")
        if last == "fortune_pointer":
            return _spec(*_box(60, 70, 1, 1, 1, 1), "bottom")
        if last.startswith("card_back") or last == "card_face":   # 3.27: карты блэкджека (знаки рисует игра)
            return _spec(*_box(84, 120, 1, 1, 1, 1), "center")
        if last == "card_shoe":
            return _spec(*_box(140, 100, 2, 2, 2, 0), "bottom")
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
        for key, size in (("squirrel", (90, 80)), ("crow", (90, 90)), ("bandit", (80, 90)),
                          ("crab", (90, 80)), ("gull", (90, 90))):       # 3.36: краб и чайка Рыбацкой деревни
            if last.startswith(key):
                return _spec(*_box(size[0], size[1], 2, 2, 2, 2), "bottom")
        return None
    if folder == "characters":
        # жители таверны: бармен — по пояс (низ картинки = край стойки), бард — в полный рост (низ = сцена)
        if last == "barman":
            return _spec(*_box(150, 150, 4, 4, 4, 0), "bottom")
        if last in ("bard", "bard_girl", "fiddler", "bagpiper", "helga", "undina", "kuzma", "saya", "grom"):
            return _spec(*_box(130, 180, 4, 4, 4, 0), "bottom")       # 3.15.2 / 3.23 / 3.47: артисты сцены
        if last in ("ice_idols", "gnome_choir", "sirens", "flame_idols"):  # 3.47: группа на сцене — трое в ряд
            return _spec(*_box(260, 180, 4, 4, 4, 0), "bottom")
        if last == "dragoness":            # 3.43: драконица Искра по пояс, низ = край стола
            return _spec(*_box(150, 150, 4, 4, 4, 0), "bottom")
        if last == "sailor":               # 3.40: Старый Якорь по пояс, низ = край стола (как Ворчун)
            return _spec(*_box(150, 150, 4, 4, 4, 0), "bottom")
        if last.startswith("snail_"):      # 3.40: улитки скачек, смотрят вправо
            return _spec(*_box(80, 60, 2, 2, 2, 0), "bottom")
        if last == "dealer_gnome":        # 3.28: дилер блэкджека — рыжий гном Ворчун по пояс, низ = край стола
            return _spec(*_box(150, 150, 4, 4, 4, 0), "bottom")
        if last == "croupier":            # 3.14: крупье по пояс, низ картинки = край стола
            return _spec(*_box(150, 150, 4, 4, 4, 0), "bottom")
        if last.startswith("gnome_worker"):   # 3.26: гном из «пришествия» с тяпкой (зима); 3.27: варианты _1.._4
            return _spec(*_box(56, 68, 2, 2, 2, 0), "bottom")     # 3.27: крупнее (на поле — ×1.25)
        if last.startswith("peasant_worker"):  # 3.39.1: свой крестьянин у грядки (средневековье), варианты _1.._4
            return _spec(*_box(64, 80, 2, 2, 2, 0), "bottom")
        if last.startswith("gnome_shaman"):   # 3.26: гном-шаман с бубном над головой; 3.27: варианты _1, _2
            return _spec(*_box(90, 112, 2, 2, 2, 0), "bottom")    # 3.27: крупнее (на лужайке — ×1.6)
        if last.startswith("fisher_"):     # 3.36: рыбак с удочкой (фестиваль) и рыбак-плясун с уловом
            return _spec(*_box(90, 120, 2, 2, 2, 0), "bottom")
        if last == "dog":                  # 3.33: пёс Буян спит у камина (лежит боком)
            return _spec(*_box(220, 120, 2, 2, 2, 0), "bottom")
        if last == "owl":                  # 3.33: сова Ухта (3.45: сидит на перилах балкона у левого окна)
            return _spec(*_box(100, 140, 2, 2, 2, 0), "bottom")
        if last in ("miller", "baker"):    # работники мельницы и пекарни (3.7), в полный рост
            return _spec(*_box(100, 150, 3, 3, 3, 0), "bottom")
        return None
    if folder == "vehicles":
        if last.startswith("truck"):
            return _spec(*_box(240, 124, 4, 2, 4, 0), "bottom")
        if last.startswith("sled"):        # 3.26.2: упряжки 2 и 3 уровня длиннее (4 и 8 собак) — им шире место
            w, h = SLED_BOX.get(last.replace("_cargo", ""), (270, 124))
            return _spec(*_box(w, h, 4, 2, 4, 0), "bottom")
        if last.startswith("cart") or last.startswith("fishcart"):     # 3.36: повозка рыботорговца
            return _spec(*_box(270, 124, 4, 2, 4, 0), "bottom")
        if last.startswith("boat"):        # 3.38.1: лодка рыботорговца: с мачтой выше, низ корпуса — под водой
            w, h = BOAT_BOX.get(last.replace("_cargo", ""), (280, 200))
            return _spec(*_box(w, h, 4, 2, 4, 0), "bottom")
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
    if folder == "ui" and last == "gameroom_map":      # 3.27: карта Игровой (высокая полоса)
        return _spec((540, 566), (0, 0, 540, 566), "full")      # 3.45.2: один экран, игры — на площадках картинки
    if folder == "icons" and last.startswith("suit_"):
        return _spec(*_box(48, 48, 1, 1, 1, 1), "center")
    if folder == "icons" and last.startswith("ach_") and not last.startswith("ach_sheet"):   # 3.34.2: медали
        return _spec(*_box(96, 96, 2, 2, 2, 2), "center")
    if folder == "icons" and last.startswith("game_"):  # 3.27: значки игр в кружках карты Игровой
        return _spec(*_box(100, 100, 2, 2, 2, 2), "center")
    if folder == "ui" and last.startswith("move_map_"):  # 3.46: плитка карты глав (из квадрата — полоса посередине)
        return _spec((518, 278), (0, 0, 518, 278), "full")
    if folder == "ui" and last == "move_map":          # 3.23: карта глав в окне «Переезд» (длинная полоса)
        return _spec((1240, 278), (0, 0, 1240, 278), "full")
    if folder == "ui" and last in ("tree_pip_off", "tree_pip_on"):    # 3.20: кружки уровней на карточке дерева
        return _spec(*_box(32, 32, 1, 1, 1, 1), "center")
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
        if last in ("peasant", "gnome", "fisherman"):       # 3.25: гном — значок помощника зимы
            s = 26
        elif last.startswith("prize_"):   # 3.14: призы казино
            s = 40
        elif last.startswith("note_"):    # ноты барда (3.6): icons/note_1 ... note_4
            s = 30
        elif last in ("egg", "milk", "truffle", "honey", "down", "wool", "cheese", "jam"):
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


def _nview(buf, w=None):
    """numpy-вид на bytearray без копии (запись в него меняет buf); None — numpy нет."""
    if _np is None:
        return None
    a = _np.frombuffer(buf, dtype=_np.uint8)
    return a if w is None else a.reshape(-1, w)


def _touching(ring, h, w):
    """Пиксели, у которых сосед слева/справа/сверху/снизу лежит в ring (numpy bool h×w)."""
    adj = _np.zeros((h, w), dtype=bool)
    adj[:, 1:] |= ring[:, :-1]
    adj[:, :-1] |= ring[:, 1:]
    adj[1:, :] |= ring[:-1, :]
    adj[:-1, :] |= ring[1:, :]
    return adj


def bg_masks(b, bg, chroma):
    """3.40.4: для каждого пикселя RGBA-буфера b: D — насколько он отличается от цвета фона (0..255),
    L — 1, если пиксель «как фон»: близко к цвету фона или (на цветном фоне) его тень — тот же оттенок, темнее.
    Тот же расчёт, что был в remove_background по пикселю (с numpy — массивами, результат совпадает)."""
    br, bgc, bb = bg
    cr, cg, cb = br / 255.0, bgc / 255.0, bb / 255.0
    top = max(cr, cg, cb)
    lims = [SHADOW_HUE_LOW if c / top < 0.3 else SHADOW_HUE for c in (cr, cg, cb)] if top > 0 else None
    if _np is not None:
        a = _np.frombuffer(bytes(b), dtype=_np.uint8).reshape(-1, 4)
        r, g, bl = (a[:, k].astype(_np.int16) for k in range(3))
        d = _np.maximum(_np.maximum(_np.abs(r - br), _np.abs(g - bgc)), _np.abs(bl - bb))
        like = d < BG_TOL
        if chroma and lims:
            rf, gf, bf = r.astype(_np.float64), g.astype(_np.float64), bl.astype(_np.float64)
            lum = _np.maximum(_np.maximum(rf, gf), bf)
            k = lum / 255.0
            near = _np.maximum(_np.maximum(_np.abs(rf - cr * 255 * k), _np.abs(gf - cg * 255 * k)),
                               _np.abs(bf - cb * 255 * k)) < 40
            safe = _np.where(lum > 0, lum, 1.0)
            hue = ((_np.abs(rf / safe - cr / top) < lims[0]) & (_np.abs(gf / safe - cg / top) < lims[1])
                   & (_np.abs(bf / safe - cb / top) < lims[2]))
            like |= (lum >= 50) & near & hue
        return bytearray(d.astype(_np.uint8).tobytes()), bytearray(like.astype(_np.uint8).tobytes())
    n = len(b) // 4
    D, L = bytearray(n), bytearray(n)
    R, G, B = b[0::4], b[1::4], b[2::4]
    for p in range(n):
        r, g, bl = R[p], G[p], B[p]
        d = r - br if r > br else br - r
        e = g - bgc if g > bgc else bgc - g
        if e > d:
            d = e
        e = bl - bb if bl > bb else bb - bl
        if e > d:
            d = e
        D[p] = d
        if d < BG_TOL:
            L[p] = 1
        elif chroma and lims:
            lum = r if r > g else g
            if bl > lum:
                lum = bl
            if lum < 50:
                continue
            k = lum / 255.0
            if max(abs(r - cr * 255 * k), abs(g - cg * 255 * k), abs(bl - cb * 255 * k)) >= 40:
                continue
            if (abs(r / lum - cr / top) < lims[0] and abs(g / lum - cg / top) < lims[1]
                    and abs(bl / lum - cb / top) < lims[2]):
                L[p] = 1
    return D, L


DEHALO_PREFIXES = ("crops/dragons/",)   # 3.48: у огненных растений нейросеть рисует свечение по мадженте — розовый ореол


def dehalo(img):
    """3.48: розоватый ореол (свечение, смешанное с маджентой), связанный с краем картинки, — в чистую мадженту,
    чтобы он ушёл вместе с фоном. Внутри контура (розовые щёчки, фиолетовые ягоды) не трогает: заливка идёт от краёв."""
    px = Pix(img)
    b, w, h = px.buf, px.w, px.h

    def pink(p):
        i = p * 4
        r, g, bl = b[i], b[i + 1], b[i + 2]
        return r > 140 and bl > 80 and g < bl - 8 and g < r - 25

    seen = bytearray(w * h)
    stack = [p for p in list(range(w)) + list(range((h - 1) * w, h * w)) + [y * w for y in range(h)]
             + [y * w + w - 1 for y in range(h)] if pink(p)]
    for p in stack:
        seen[p] = 1
    while stack:
        p = stack.pop()
        x = p % w
        for q in ((p - 1) if x > 0 else -1, (p + 1) if x < w - 1 else -1, p - w, p + w):
            if 0 <= q < w * h and not seen[q] and pink(q):
                seen[q] = 1
                stack.append(q)
    for p in range(w * h):
        if seen[p]:
            b[p * 4:p * 4 + 4] = b"\xff\x00\xff\xff"
    return px.surface()


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

    def _remove_grid_lines(self, is_bg):
        """3.40.4: тёмные линии сетки между клетками листа (нейросеть рисует клетки чёрной рамкой). Линия — тонкая
        полоса столбцов (строк), где «не фон» почти во всю высоту (ширину). Только для листов и полосок:
        в одиночной картинке так выглядит, например, мачта."""
        w, h, b = self.w, self.h, self.buf
        # 3.45.1: линия сетки — почти во всю длину И тёмная. Раньше брали «не фон в 85%», и ряд через тела двух
        # рыб (щука и жерех лежат во всю клетку) принимался за линию: рыбы выходили разрезанными пополам.
        if _np is None:
            nb = [[not is_bg[y * w + x] for x in range(w)] for y in range(h)]
            dk = [[max(b[(y * w + x) * 4], b[(y * w + x) * 4 + 1], b[(y * w + x) * 4 + 2]) < GRID_DARK and nb[y][x]
                   for x in range(w)] for y in range(h)]
            col = [sum(nb[y][x] for y in range(h)) for x in range(w)]
            row = [sum(nb[y]) for y in range(h)]
            dcol = [sum(dk[y][x] for y in range(h)) for x in range(w)]
            drow = [sum(dk[y]) for y in range(h)]
        else:
            m = _nview(is_bg, w) == 0
            px = _nview(b).reshape(h, w, 4)
            dk = m & (px[:, :, :3].max(axis=2) < GRID_DARK)
            col, row = m.sum(axis=0).tolist(), m.sum(axis=1).tolist()
            dcol, drow = dk.sum(axis=0).tolist(), dk.sum(axis=1).tolist()
        n = 0
        for counts, darks, size, other, vertical in ((col, dcol, w, h, True), (row, drow, h, w, False)):
            full = [c >= other * GRID_FULL and d >= c * GRID_DARK_SHARE for c, d in zip(counts, darks)]
            i = 0
            while i < size:
                if not full[i]:
                    i += 1
                    continue
                j = i
                while j < size and full[j]:
                    j += 1
                if j - i <= max(4, int(size * GRID_THIN)):            # тонкая — это рамка, а не рисунок
                    a, b = max(0, i - 2), min(size, j + 2)               # с ореолом по краям линии
                    for k in range(a, b):
                        if vertical:
                            for y in range(h):
                                is_bg[y * w + k] = 1
                        else:
                            is_bg[k * w:(k + 1) * w] = b"\x01" * w
                    n += b - a
                i = j
        return n

    def remove_background(self, bg, grid=False):
        """Убирает фон:
        1) заливка от краёв картинки — по цвету фона, а на цветном фоне (маджента) ещё и по его теням;
        2) «дырки» цвета фона внутри рисунка (просветы между листьями, между досками кузова):
           на цветном фоне убираются все, на белом — только мелкие (крупное белое внутри контура —
           это часть рисунка: курица, дверь амбара);
        3) мягкий полупрозрачный край без цветного ореола."""
        b, w, h = self.buf, self.w, self.h
        br, bgc, bb = bg
        chroma = max(bg) - min(bg) > 120          # цветной фон (маджента, зелёный), а не белый/серый
        D, L = bg_masks(b, bg, chroma)            # 3.40.4: расстояние до фона и «похож на фон» — один проход

        def dist(i):
            return D[i >> 2]

        is_bg = bytearray(w * h)
        stack = []
        for p in list(range(w)) + list(range((h - 1) * w, h * w)) + [y * w for y in range(h)] + [y * w + w - 1 for y in range(h)]:
            if L[p] and not is_bg[p]:
                is_bg[p] = 1
                stack.append(p)
        last = (h - 1) * w
        while stack:                              # заливка от краёв: помечаем при постановке в очередь
            p = stack.pop()
            x = p % w
            if x > 0 and L[p - 1] and not is_bg[p - 1]:
                is_bg[p - 1] = 1
                stack.append(p - 1)
            if x < w - 1 and L[p + 1] and not is_bg[p + 1]:
                is_bg[p + 1] = 1
                stack.append(p + 1)
            if p >= w and L[p - w] and not is_bg[p - w]:
                is_bg[p - w] = 1
                stack.append(p - w)
            if p < last and L[p + w] and not is_bg[p + w]:
                is_bg[p + w] = 1
                stack.append(p + w)
        self._remove_rule_lines(is_bg, dist)
        if grid:
            self._remove_grid_lines(is_bg)
        # просветы цвета фона внутри рисунка
        hole_limit = w * h if chroma else int(w * h * HOLE_MAX_WHITE)
        seen = bytearray(w * h)
        if _np is not None:
            starts = _np.flatnonzero((_nview(is_bg) == 0) & (_nview(D) < HOLE_TOL)).tolist()
        else:
            starts = range(w * h)
        for start in starts:
            if is_bg[start] or seen[start] or D[start] >= HOLE_TOL:
                continue
            comp, stack = [], [start]
            seen[start] = 1
            while stack:
                p = stack.pop()
                comp.append(p)
                x = p % w
                for q in ((p - 1) if x > 0 else -1, (p + 1) if x < w - 1 else -1,
                          p - w if p >= w else -1, p + w if p < (h - 1) * w else -1):
                    if q >= 0 and not seen[q] and not is_bg[q] and D[q] < HOLE_TOL:
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
        if _np is not None:
            _nview(b)[3::4][_nview(is_bg) == 1] = 0
        else:
            for p in range(w * h):
                if is_bg[p]:
                    b[p * 4 + 3] = 0
        if chroma and self._despill(is_bg, bg):
            D = bg_masks(b, bg, False)[0]          # «отмытые» пиксели у края — расстояние до фона заново
        # край: 2 кольца пикселей вокруг фона. Похожие на фон делаем полупрозрачными
        # и «отмываем» их цвет от фона — так не остаётся розового/белого ореола вокруг контура.
        ring = is_bg
        for tol in EDGE_TOLS:
            span = tol - BG_TOL
            nxt = bytearray(w * h)
            if _np is not None:
                rv = _nview(ring, w) == 1
                cand = _touching(rv, h, w) & (_nview(is_bg, w) == 0)
                if ring is not is_bg:
                    cand &= ~rv
                cands = _np.flatnonzero(cand).tolist()
            else:
                cands = range(w * h)
            for p in cands:
                if is_bg[p] or (ring is not is_bg and ring[p]):
                    continue
                x = p % w
                if not ((x > 0 and ring[p - 1]) or (x < w - 1 and ring[p + 1])
                        or (p >= w and ring[p - w]) or (p < (h - 1) * w and ring[p + w])):
                    continue
                nxt[p] = 1
                i = p * 4
                d = D[p]
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
        front = [] if _np is not None else [p for p in range(w * h) if is_bg[p]]
        if _np is not None:                    # то же «не дальше reach шагов от фона», но слоями целиком
            bgm = _nview(is_bg, w) == 1
            cur = bgm.copy()
            for _ in range(reach):
                grown = cur | _touching(cur, h, w)
                if (grown == cur).all():
                    break
                cur = grown
            px4 = _nview(b).reshape(-1, 4).astype(_np.int16)
            spill_np = px4[:, strong].min(axis=1) - px4[:, weak].max(axis=1)
            cand = (cur & ~bgm).reshape(-1) & (spill_np > 8)
            for p in _np.flatnonzero(cand).tolist():
                near[p] = 2
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
        for p in (_np.flatnonzero(_nview(near) == 2).tolist() if _np is not None else range(w * h)):
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
        if _np is not None:                         # сколько «не фона» в каждом столбце и строке — сразу
            nb = _nview(is_bg, w) == 0
            cols_ok = set(_np.flatnonzero(nb.sum(axis=0) >= h * LINE_MIN).tolist())
            rows_ok = set(_np.flatnonzero(nb.sum(axis=1) >= w * LINE_MIN).tolist())
        else:
            cols_ok, rows_ok = range(w), range(h)
        for x in range(w):
            if x not in cols_ok:
                continue
            pts = [y * w + x for y in range(h) if not is_bg[y * w + x]]
            if len(pts) < h * LINE_MIN:
                continue
            line = [p for p in pts if dist(p * 4) < LINE_TOL and thin_x(p)]
            if len(line) >= h * LINE_MIN:
                found += line
        for y in range(h):
            if y not in rows_ok:
                continue
            pts = [y * w + x for x in range(w) if not is_bg[y * w + x]]
            if len(pts) < w * LINE_MIN:
                continue
            line = [p for p in pts if dist(p * 4) < LINE_TOL and thin_y(p)]
            if len(line) >= w * LINE_MIN:
                found += line
        for p in found:
            is_bg[p] = 1
        return len(found)

    def drop_specks(self, limit=None):
        """3.26.1: убрать крошки — крохотные отдельные кусочки (обычно след значка нейросети в углу картинки
        или точка шума). Один такой пиксель в углу полоски делил её как «четвёртый рисунок»: стадии 2 и 3
        склеивались, а первая уменьшалась. Крошка — кусок меньше SPECK_SHARE площади картинки."""
        b, w, h = self.buf, self.w, self.h
        limit = max(SPECK_MIN, int(w * h * SPECK_SHARE)) if limit is None else limit
        seen = bytearray(w * h)
        starts = _np.flatnonzero(_nview(b)[3::4] > MIN_ALPHA).tolist() if _np is not None else range(w * h)
        for start in starts:
            if seen[start] or b[start * 4 + 3] <= MIN_ALPHA:
                continue
            comp, stack = [start], [start]
            seen[start] = 1
            big = False
            while stack:
                p = stack.pop()
                x = p % w
                for q in ((p - 1) if x > 0 else -1, (p + 1) if x < w - 1 else -1,
                          p - w if p >= w else -1, p + w if p < (h - 1) * w else -1):
                    if q >= 0 and not seen[q] and b[q * 4 + 3] > MIN_ALPHA:
                        seen[q] = 1
                        stack.append(q)
                        if not big:
                            comp.append(q)
                            big = len(comp) > limit
            if not big:
                for p in comp:
                    b[p * 4 + 3] = 0

    def bbox(self, rect=None):
        """Границы непрозрачного рисунка внутри rect (x0, y0, x1, y1) или None."""
        x0, y0, x1, y1 = rect or (0, 0, self.w, self.h)
        b, w = self.buf, self.w
        if _np is not None:
            a = _nview(b)[3::4].reshape(-1, w)[y0:y1, x0:x1] > MIN_ALPHA
            ys, xs = _np.flatnonzero(a.any(axis=1)), _np.flatnonzero(a.any(axis=0))
            if not len(ys):
                return None
            return x0 + int(xs[0]), y0 + int(ys[0]), x0 + int(xs[-1]) + 1, y0 + int(ys[-1]) + 1
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
        if _np is not None:
            a = _nview(b)[3::4].reshape(-1, w)[y0:y1, x0:x1] > MIN_ALPHA
            return [bool(v) for v in a.any(axis=0 if axis == "x" else 1)]
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
def _prepare(img, work_max, specks=True, grid=False):
    """Уменьшает огромную картинку до рабочего размера, убирает фон (и крошки). -> Pix."""
    w, h = img.get_size()
    k = min(1.0, work_max / max(w, h))
    if k < 1.0:
        img = pygame.transform.smoothscale(img, (max(1, int(w * k)), max(1, int(h * k))))
    px = Pix(img)
    if not px.has_transparency():
        bg = px.background_color()
        if bg is not None:
            px.remove_background(bg, grid)
            if specks:
                px.drop_specks()
            else:          # 3.40.4: в листах — только совсем крохи (хвостики рамок у края), искорки остаются
                px.drop_specks(SHEET_SPECK)
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
    if spec["align"] == "fill":       # 3.39.6: растянуть ровно на поле (плитки поля — одной ширины на всех фермах)
        nw, nh = max(1, int(round(bw))), max(1, int(round(bh)))
    piece = pygame.transform.smoothscale(piece, (nw, nh))
    out = pygame.Surface((cw, ch), pygame.SRCALPHA)
    cx = (x0 + x1) / 2
    if spec["align"] == "topleft":
        r = piece.get_rect(topleft=(x0, y0))
    elif spec["align"] in ("center", "fill"):
        r = piece.get_rect(center=(int(round(cx)), int(round((y0 + y1) / 2))))
    else:
        r = piece.get_rect(midbottom=(int(round(cx)), y1))
    out.blit(piece, r)
    return out


def fit_single(img, spec):
    cw, ch = spec["canvas"]
    if spec["align"] == "full":
        w, h = img.get_size()
        ratio = (w / h) / (cw / ch)
        if ratio > 1.1 or ratio < 1 / 1.1:
            # 3.20: пропорции сильно другие (фон камина 16:9 при экране 25:16) — обрезаем края, а не сплющиваем
            if ratio > 1:
                nw = int(round(h * cw / ch))
                img = img.subsurface(((w - nw) // 2, 0, nw, h))
            else:
                nh = int(round(w * ch / cw))
                img = img.subsurface((0, (h - nh) // 2, w, nh))
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
    px = _prepare(img, _work(biggest * max(rows, cols)), specks=False, grid=True)   # в листах мелочь бывает нужной (искорки)
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
class NeedFit(Exception):
    """3.40.4: картинку надо подгонять (в кэше её нет), а сейчас только проверяем кэш (PROBE)."""


PROBE = [False]          # True — load_fitted/is_strip не считают, а бросают NeedFit (загрузка раздаёт работу процессам)
_digests = {}            # (путь, mtime, размер) -> md5 содержимого
_INDEX = "index.txt"


def _load_index():
    if _digests.get("_loaded"):
        return
    _digests["_loaded"] = True
    try:
        with open(os.path.join(CACHE_DIR, _INDEX), encoding="utf-8") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) == 4:
                    _digests[(parts[0], int(parts[1]), int(parts[2]))] = parts[3]
    except (OSError, ValueError):
        pass


def save_index():
    """Запомнить на диск, у какого файла какое содержимое (чтобы не считать md5 при каждом запуске)."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        tmp = os.path.join(CACHE_DIR, _INDEX + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            for k, v in _digests.items():
                if isinstance(k, tuple):
                    fh.write(f"{k[0]}\t{k[1]}\t{k[2]}\t{v}\n")
        os.replace(tmp, os.path.join(CACHE_DIR, _INDEX))
    except OSError:
        pass


def digest(src):
    """3.40.4: md5 содержимого картинки. Кэш привязан к содержимому, а не к пути и дате файла: после git clone,
    переноса папки или pull без изменений картинки заново не подгоняются."""
    _load_index()
    st = os.stat(src)
    key = (os.path.abspath(src), st.st_mtime_ns, st.st_size)
    d = _digests.get(key)
    if d is None:
        h = hashlib.md5()
        with open(src, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        d = _digests[key] = h.hexdigest()
    return d


def _cache_path(name, src, part=None):
    # в ключе и правила подгонки: поменялся размер в игре — картинка пересчитается сама
    key = f"{CACHE_VERSION}|{name}|{fit_spec(name)}|{digest(src)}"
    if name.startswith(DEHALO_PREFIXES):   # 3.48: с чисткой ореола — свой ключ
        key += "|dehalo"
    if part and part[0] == "sheet":     # 3.19.1: и клетка листа (поменялась сетка листа — вырежется заново)
        key += f"|sheet{part[1]}:{part[4]}x{part[5]}"
    return os.path.join(CACHE_DIR, hashlib.md5(key.encode("utf-8")).hexdigest() + ".png")


def _load(path):
    img = pygame.image.load(path)
    try:
        img = img.convert_alpha()
    except pygame.error:          # нет окна (подгонка в отдельном процессе): 32 бита с прозрачностью — вручную
        if img.get_bitsize() != 32 or not img.get_flags() & pygame.SRCALPHA:
            out = pygame.Surface(img.get_size(), pygame.SRCALPHA, 32)
            out.blit(img, (0, 0))
            img = out
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
    key = disk = None
    if path:
        try:
            key = digest(path)
        except OSError:
            key = None
        if key in _strip_cache:
            return _strip_cache[key]
        if key:                                # 3.40.4: ответ хранится и на диске — не считаем при каждом запуске
            disk = os.path.join(CACHE_DIR, f"strip2_{CACHE_VERSION}_{key}.txt")
            try:
                with open(disk, encoding="utf-8") as fh:
                    _strip_cache[key] = fh.read().strip() == "1"
                    return _strip_cache[key]
            except OSError:
                pass
            if PROBE[0]:
                raise NeedFit(path)
    if img is None:                            # картинку читаем, только если ответа ещё нет
        img = pygame.image.load(path)
    w, h = img.get_size()
    result = False
    if w >= 0.9 * h:                       # высокая картинка — точно одно растение
        px = _prepare(img, 360)            # грубо, но быстро: нужен только силуэт
        bb = px.bbox()
        # 3.45: квадратная картинка тоже бывает полоской (Gemini рисует 3 стадии в ряд посреди квадрата — кои,
        # золотая рыбка): смотрим на сам рисунок — он заметно шире, чем выше
        if bb and w < 1.3 * h and (bb[2] - bb[0]) < 1.6 * (bb[3] - bb[1]):
            bb = None
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
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(disk, "w", encoding="utf-8") as fh:
                fh.write("1" if result else "0")
        except OSError:
            pass
    return result


# 3.34.1: у этих картинок нейросеть нарисовала свечение прямо поверх маджента-фона — после вырезания фона
# по краям оставался розовый ореол (фонарь в зале). Розоватые полупрозрачные следы убираем.
DESPILL = ("decor/lantern", "icons/prize_lanterns", "icons/prize_fireflies")


def despill(name, surf):
    """Убирает розовый ореол (смесь маджента-фона со свечением) у картинок из DESPILL."""
    base = name[:-len(HI)] if HI and name.endswith(HI) else name
    if surf is None or base not in DESPILL:
        return surf
    surf = surf.copy()
    w, h = surf.get_size()
    for y in range(h):
        for x in range(w):
            r, g, b, a = surf.get_at((x, y))
            if a == 0:
                continue
            m = min(r, b) - g                  # насколько пиксель «маджентовый»
            if m > 6:                          # и светлые, и тёмные (по краю) розовые пиксели
                surf.set_at((x, y), (r, g, g, int(a * max(0.0, 1 - (m - 6) / 14))))
            elif a < 240 and r - g > 20 and abs(g - b) < 35:    # бледно-розовая дымка свечения
                surf.set_at((x, y), (r, g, b, 0))
    return surf


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
    if PROBE[0] and not (part is None and spec["align"] == "full" and not name.endswith("fence_front")):
        raise NeedFit(name)
    img = _load(path)
    if name.startswith(DEHALO_PREFIXES):
        img = dehalo(img)
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
            out = despill(name, fit_single(img, spec))
    elif part[0] == "strip":
        base = name.rsplit("_", 1)[0]
        specs = [fit_spec(f"{base}_3")] * 3
        outs = [despill(f"{base}_{st}", o) for st, o in enumerate(fit_strip(img, specs), 1)]
        for st, surf in enumerate(outs, 1):
            if surf is not None and st != part[1]:
                _save_cache(_cache_path(f"{base}_{st}", path), surf)
        out = outs[part[1] - 1]
    else:  # sheet: ("sheet", номер, префикс, порядок, строк, столбцов)
        _kind, idx, prefix, order, rows, cols = part
        sfx = HI if name.endswith(HI) else ""
        outs = [despill(prefix + order[i] + sfx, o)
                for i, o in enumerate(fit_sheet(img, rows, cols, lambda i: fit_spec(prefix + order[i] + sfx)))]
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
