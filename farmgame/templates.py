# -*- coding: utf-8 -*-
"""Экспорт шаблонов спрайтов: текущая графика, нарисованная кодом, сохраняется в PNG
ровно того размера и с той точкой привязки, которые ждёт игра.

Запуск:  python farm_idle.py --export-templates
Результат: папка assets_templates/ рядом с игрой. Нарисуй поверх (или вместо) в том же
размере и положи файл с тем же именем в assets/ — игра подхватит его сама.
"""
import os

import pygame

from . import config as cfg
from .config import FARMS, ANIMALS, TRUCK_TIERS, W, H
from . import art
from . import spritefit
from . import hd
from . import tavern_ui as tu


def _surface(size):
    return pygame.Surface(size, pygame.SRCALPHA)


def _interior(kind):
    """Фон сарая или мельницы изнутри, нарисованный кодом (без загонов и кнопок)."""
    from .app import App
    return App.build_barn_background(None) if kind == "barn" else App.build_mill_background(None)


def _tavern_scene():
    """Зал таверны без людей: фон + передний слой (стойка, перила, столы)."""
    bg, fg, _custom = tu.build_tavern_scene()
    surf = _surface((W, H))
    surf.blit(bg, (0, 0))
    if fg is not None:
        surf.blit(fg, (0, 0))
    return surf


def _draw_barman(s):
    look = dict(top=(200, 210, 225), apron=True, hair=(70, 50, 40), style="bald", mustache=True)
    hands = tu.draw_person(s, 75, 150, 1.15, look, upper=True, arms=(0.9, 0.9))
    tu.draw_mug(s, hands[0][0] + 4, hands[0][1] - 6, 0.8)


def _draw_bard(s):
    look = dict(top=(60, 140, 90), legs=(150, 60, 60), hair=(170, 110, 60), style="bard")
    tu.draw_person(s, 65, 178, 1.15, look, arms=(1.35, 0.7))
    tu.draw_lute(s, 69, 132, 1.15, 0)


def _layout_tavern(kind):
    if kind == "tavern":
        surf = _tavern_scene()
        boxes = [((14, 10, 230, 200), "плашки денег"), ((W - 200, 10, 190, 56), "жетоны, настройки"),
                 ((16, 558, 136, 60), "«На поле»"), (tu.BOARD_SIGN, "стрелка к доске"),
                 (tu.CASINO_DOOR.union(tu.CASINO_SIGN), "дверь казино"),
                 (tu.BARMAN_ZONE, "БАРМЕН (игра)"), (tu.BARD_ZONE, "БАРД (игра)"),
                 ((W // 2 - 260, 548, 520, 76), "сообщения")]
        note = f"Стойка: верх на y={tu.COUNTER_TOP}. Сцена: центр {tu.STAGE_C}. Барда и бармена НЕ рисовать — их ставит игра"
    else:
        surf = _surface((W, H))
        surf.blit(tu.build_board_background(), (0, 0))
        boxes = [((14, 10, 160, 44), "жетоны"), ((W // 2 - 190, 6, 380, 58), "табличка"), ((W - 64, 10, 54, 54), ""),
                 ((16, 558, 172, 60), "«В таверну»")]
        boxes += [(r, f"записка {n + 1}") for n, r in enumerate(tu.NOTE_RECTS)]
        boxes.append((tu.WEEKLY_RECT, "задание недели"))
        note = "Записки и свиток рисует игра. Нужна пустая пробковая доска во весь экран"
    return _shade_boxes(surf, boxes, note, 230 if kind == "tavern" else 600)


def _shade_boxes(surf, boxes, note, note_y):
    shade = pygame.Surface((W, H), pygame.SRCALPHA)
    for rect, label in boxes:
        pygame.draw.rect(shade, (255, 255, 255, 110), rect, border_radius=10)
        pygame.draw.rect(shade, (200, 40, 40, 255), rect, 3, border_radius=10)
    surf.blit(shade, (0, 0))
    for rect, label in boxes:
        if label:
            r = pygame.Rect(rect)
            art.draw_text(surf, label, 15, r.center, (200, 40, 40), outline=(255, 255, 255))
    art.draw_text(surf, note, 14, (W // 2, note_y), (200, 40, 40), outline=(255, 255, 255))
    return surf


def _layout_guide(kind):
    """Карта раскладки: фон + полупрозрачные прямоугольники там, где поверх будет интерфейс.
    Нужна, чтобы при рисовании своего фона знать, какие места закроются карточками."""
    if kind in ("tavern", "quest_board"):
        return _layout_tavern(kind)
    surf = _interior(kind)
    boxes = [((14, 10, 190, 170), "плашки денег"), ((W - 64, 10, 54, 54), ""), ((16, 558, 136, 60), "кнопка «На поле»")]
    if kind == "barn":
        w, gap = 228, 12
        x0 = (W - (4 * w + 3 * gap)) // 2
        boxes += [((x0 + a * (w + gap), 160, w, 386), "загон") for a in range(4)]
        boxes.append(((W // 2 + 70, 26, 200, 44), "табличка"))
    else:
        boxes += [((40 + b * 480, 160, 440, 386), ("мельница", "пекарня")[b]) for b in range(2)]
        boxes.append(((W // 2 + 70, 26, 220, 44), "табличка"))
    shade = pygame.Surface((W, H), pygame.SRCALPHA)
    for rect, label in boxes:
        pygame.draw.rect(shade, (255, 255, 255, 120), rect, border_radius=10)
        pygame.draw.rect(shade, (200, 40, 40, 255), rect, 3, border_radius=10)
    surf.blit(shade, (0, 0))
    for rect, label in boxes:
        if label:
            r = pygame.Rect(rect)
            art.draw_text(surf, label, 16, r.center, (200, 40, 40), outline=(255, 255, 255))
    art.draw_text(surf, "Красное закроет интерфейс. Видно будет полосы сверху (y 0-160) и снизу (y 546-640)", 14,
                  (W // 2, 150), (200, 40, 40), outline=(255, 255, 255))
    return surf


def spec_list():
    """Список (имя, размер, где точка привязки, описание, функция рисования)."""
    specs = []
    add = lambda *a: specs.append(a)

    for idx, fm in enumerate(FARMS):
        fid = fm["id"]
        for k, key in enumerate(fm["plants"]):
            for stage, kk in art.CROP_STAGE_K.items():
                add(f"crops/{fid}/{key}_{stage}", (110, 120), "низ по центру (55, 116) = основание стебля",
                    f"{fm['names'][k]}, стадия {stage}/3", idx,
                    lambda s, f=art.PLANT_FUNCS[key], kk=kk: f(s, 55, 116, kk))
        add(f"tiles/{fid}/soil", (184, 104), "центр (92, 52) = центр клетки +5 px вниз", "грядка", idx,
            lambda s: art.draw_soil_tile(s, 92, 47, False))
        add(f"tiles/{fid}/soil_locked", (184, 104), "центр (92, 52)", "закрытая грядка", idx,
            lambda s: art.draw_soil_tile(s, 92, 47, True))
        add(f"backgrounds/{fid}", (W, H), "весь экран", "фон поля целиком (с амбаром/мельницей и задним забором)", idx,
            lambda s: s.blit(art.build_field_background(), (0, 0)))
        add(f"props/{fid}/fence_strip", (640, 128), "низ = земля; кусок анфас — игра повторит и наклонит",
            "кусок переднего забора (проще, чем fence_front)", idx,
            lambda s: art.draw_fence(s, (8, 124), (632, 124), (0, 0)))
        add(f"props/{fid}/fence_front", (W, H), "весь экран, прозрачный", "передний забор (рисуется поверх грядок)", idx,
            lambda s: art.draw_front_fence_layer(s))
        add(f"props/{fid}/tree", (130, 150), "низ по центру (65, 148)", "дерево (большое — x52, малое — x40)", idx,
            lambda s: art.draw_tree(s, 65, 127, 52))
        add(f"props/{fid}/bush", (80, 64), "низ по центру (40, 64)", "куст", idx,
            lambda s: art.draw_bush(s, 40, 43, 30))
    add("buildings/barn", (340, 230), "левый верх, ставится в (60, 18)", "амбар (лето)", 0, lambda s: art.draw_barn(s))
    add("buildings/winter/barn", (340, 230), "левый верх", "амбар в снегу (зима)", 2, lambda s: art.draw_barn(s))
    add("buildings/windmill", (340, 230), "левый верх, ставится в (60, 18)", "мельница без лопастей", 1,
        lambda s: art.draw_windmill(s))
    add("buildings/windmill_blades", (180, 180), "центр = ось (250, 73 на экране)", "лопасти, игра их вращает", 1,
        lambda s: art.draw_mill_blades(s, 90, 90, 0.3))
    add("props/castle", (220, 200), "низ по центру (110, 198)", "замок на холме", 1, lambda s: art.draw_castle(s, 110, 168))
    add("props/sun", (130, 130), "центр", "солнце", 0, lambda s: art.draw_sun_body(s, 65, 65, 0))
    add("props/cloud", (150, 100), "центр", "тучка", 0, lambda s: art.draw_cloud_body(s, 75, 45, False))
    add("props/cloud_rain", (150, 100), "центр", "тучка во время дождя", 0, lambda s: art.draw_cloud_body(s, 75, 45, True))
    keys = ["chicken", "cow", "pig", "bees"]
    from .config import ANIMALS_WINTER
    for a, an in enumerate(ANIMALS_WINTER):              # 3.24: зимние звери (глава 3)
        add(f"animals/{an['key']}", (160, 130), "низ по центру (80, 126)", an["name"] + " (зимний сарай)", 1,
            lambda s: None)
        add(f"icons/{an['icon']}", (30, 30), "центр", an["product"] + " (зима)", 1, lambda s: None)
    add("icons/frostleaf", (40, 40), "центр", "голубой листочек (валюта зимы)", 1, lambda s: None)
    add("icons/gnome", (26, 26), "центр", "гном-помощник (зима)", 1, lambda s: None)
    add("characters/gnome_worker", (44, 54), "низ по центру (22, 54) = снег у грядки",
        "гном из «Гномьего пришествия» с тяпкой (зима)", 1, lambda s: art.draw_gnome_worker(s, 22, 54, 1.0))
    for v in range(1, 5):   # 3.27: разные гномы-работники (каждой грядке свой)
        add(f"characters/gnome_worker_{v}", (44, 54), "низ по центру (22, 54) = снег у грядки",
            f"гном-работник, вариант {v} (зима)", 1, lambda s: None)
    for v in (1, 2):        # 3.27: два разных шамана
        add(f"characters/gnome_shaman_{v}", (56, 70), "низ по центру (28, 70) = снег на лужайке",
            f"гном-шаман, вариант {v} (зима)", 1, lambda s: None)
    add("characters/gnome_shaman", (56, 70), "низ по центру (28, 70) = снег на лужайке",
        "гном-шаман с бубном (зима)", 1, lambda s: art.draw_gnome_shaman(s, 28, 70, 1.0, 0.0))
    for v in ("sled", "sled_0", "sled_1", "sled_2"):
        add(f"vehicles/{v}", (270, 124), "низ по центру = снег", "собачья упряжка (зима)", 1, lambda s: None)
    for a, key in enumerate(keys):
        for winter in (False, True):
            add(f"animals/{key}" + ("_winter" if winter else ""), (160, 130), "низ по центру (80, 126)",
                ANIMALS[a]["name"] + (" (зимний наряд)" if winter else ""), 0,
                lambda s, a=a, w=winter: art.ANIMAL_DRAW[a](s, 80, 126, 1.15, 0, False, w))
    add("creatures/squirrel", (90, 80), "низ по центру (45, 78), смотрит вправо", "белка", 0,
        lambda s: art.draw_squirrel(s, 45, 78, 1))
    add("creatures/squirrel_golden", (90, 80), "низ по центру (45, 78), смотрит вправо", "золотая белка", 0,
        lambda s: art.draw_squirrel(s, 45, 78, 1, golden=True))
    add("creatures/crow", (90, 90), "низ по центру (45, 88), смотрит вправо", "ворона сидит", 0,
        lambda s: art.draw_crow(s, 45, 88, 1))
    add("creatures/crow_fly", (90, 90), "низ по центру (45, 88), смотрит вправо", "ворона летит", 0,
        lambda s: art.draw_crow(s, 45, 88, 1, 0.05, True))
    add("creatures/bandit", (80, 90), "низ по центру (40, 88), смотрит вправо", "разбойник", 1,
        lambda s: art.draw_bandit(s, 40, 88, 1))
    add("creatures/bandit_sack", (80, 90), "низ по центру (40, 88), смотрит вправо", "разбойник с мешком", 1,
        lambda s: art.draw_bandit(s, 40, 88, 1, 0, 5000))
    for tier in range(3):
        color = TRUCK_TIERS[tier][1]
        add(f"vehicles/truck_{tier}", (240, 124), "низ по центру (120, 124), едет влево", f"грузовик скупщика, уровень {tier + 1}", 0,
            lambda s, c=color: art.draw_truck(s, 125, 120, c))
        add(f"vehicles/cart_{tier}", (270, 124), "низ по центру (135, 124), едет влево", f"телега сборщика, уровень {tier + 1}", 1,
            lambda s, c=color: art.draw_cart(s, 165, 120, c))
    add("backgrounds/barn_inside", (W, H), "весь экран", "сарай изнутри (фон под загонами)", 0,
        lambda s: s.blit(_interior("barn"), (0, 0)))
    add("backgrounds/mill_inside", (W, H), "весь экран", "мельница изнутри (фон под карточками)", 1,
        lambda s: s.blit(_interior("mill"), (0, 0)))
    add("backgrounds/tavern", (W, H), "весь экран", "зал таверны: стойка справа, сцена в центре, балкон с гостями сверху "
        "(без барда и бармена)", 1, lambda s: s.blit(_tavern_scene(), (0, 0)))
    add("backgrounds/quest_board", (W, H), "весь экран", "доска заданий: пустая пробковая доска", 1,
        lambda s: s.blit(tu.build_board_background(), (0, 0)))
    add("characters/barman", (150, 150), "низ по центру (75, 150) = край стойки", "бармен по пояс", 1, _draw_barman)
    add("characters/bard", (130, 180), "низ по центру (65, 178) = пол сцены", "бард с лютней", 1, _draw_bard)
    add("characters/bard_girl", (130, 180), "низ по центру (65, 178) = пол сцены",
        "певица Мила — приз казино, поёт вместо барда", 1, lambda s: None)
    for key, desc in (("fiddler", "скрипач Тимоха — приз таверны, играет вместо барда"),
                      ("bagpiper", "волынщик Ерёма — приз таверны, играет вместо барда")):
        add(f"characters/{key}", (130, 180), "низ по центру (65, 178) = пол сцены", desc, 1, lambda s: None)
    add("icons/token", (40, 40), "центр", "жетон таверны", 1,
        lambda s: tu.draw_token(s, 20, 20, 1.0))
    add("backgrounds/loading", (W, H), "весь экран", "фон экрана загрузки (необязательно)", 0,
        lambda s: s.fill((120, 160, 90)))
    add("ui/logo", (600, 200), "центр, стоит в (500, 150)", "логотип: название игры", 0,
        lambda s: art.draw_text(s, "Весёлая ферма", 46, (300, 100)))
    add("ui/loading_ring", (200, 200), "центр = ось вращения", "колесо экрана загрузки (игра его крутит)", 0,
        lambda s: art.draw_loading_wheel(s, 100, 100, 96, 0.0))
    add("ui/loading_center", (120, 120), "центр = центр колеса", "талисман в центре колеса (не крутится)", 0,
        lambda s: art.draw_peasant_head(s, 60, 60, 4.0))
    add("ui/cursor", (32, 32), "кончик стрелки = левый верхний угол (0, 0)", "курсор мыши", 0,
        lambda s: art.draw_cursor_template(s))
    add("ui/cursor_hover", (40, 40), "кончик стрелки = левый верхний угол (0, 0)", "курсор над кнопкой (необязательно)", 0,
        lambda s: art.draw_cursor_template(s, True))
    # 3.4: окна и кнопки «дерево + пергамент» — игра растягивает их, углы остаются как нарисованы
    add("ui/panel", (520, 400), "растягивается (9 частей), углы не тянутся", "окно: деревянная рамка, внутри пергамент", 0,
        lambda s: _skin().draw_panel_fallback(s, pygame.Rect(4, 4, 510, 390)))
    add("ui/panel_header", (440, 110), "растягивается по ширине (края не тянутся)", "табличка заголовка окна", 0,
        lambda s: _skin().draw_header_fallback(s, pygame.Rect(10, 25, 420, 60)))
    add("ui/card", (420, 140), "растягивается (9 частей)", "карточка-строка в окне (товар, улучшение)", 0,
        lambda s: _skin().draw_card_fallback(s, pygame.Rect(6, 6, 408, 128)))
    for col in ("green", "blue", "orange", "red", "grey"):
        add(f"ui/button_{col}", (300, 100), "растягивается по ширине (края не тянутся)", f"кнопка ({col})", 0,
            lambda s, c=col: _skin().draw_button_fallback(s, pygame.Rect(6, 10, 288, 80), _skin().BUTTON_COLORS[c]))
    add("ui/slider_knob", (48, 48), "центр", "ручка ползунка громкости", 0,
        lambda s: _skin().draw_knob(s, 24, 24))
    from .spritefit import MILL_PROPS
    mill_desc = {"millstone": "каменное колесо-жернов (игра вращает; центр = ось)", "mill_bed": "каменная чаша под колесом",
                 "mill_hopper": "бункер для зерна", "grain_heap": "горка зерна в бункере",
                 "flour_sacks_1": "мешок муки", "flour_sacks_2": "три мешка муки", "flour_sacks_3": "гора мешков муки",
                 "oven": "хлебная печь (проём пустой и тёмный)", "oven_fire": "огонь на поленьях (без печи)",
                 "bread_shelf": "пустой стеллаж для хлеба",
                 "mill_card": "сценка для карточки «Мельница» (жернов, бункер, мешок)",
                 "bakery_card": "сценка для карточки «Пекарня» (печь с огнём, хлеб)"}
    for key, (w, h, anchor) in MILL_PROPS.items():
        add(f"props/{key}", (w, h), "центр" if anchor == "center" else "низ по центру", mill_desc.get(key, key) + " — экран мельницы",
            1, lambda s: None)
    for key, desc in (("miller", "мельник с мешком, идёт вправо"), ("baker", "пекарь с лопатой, смотрит влево")):
        add(f"characters/{key}", (100, 150), "низ по центру = пол", desc + " — экран мельницы", 1, lambda s: None)
    for key, desc in (("grain", "мешочек зерна"), ("flour", "мешок муки"), ("bread", "буханка хлеба")):
        add(f"icons/{key}", (40, 40), "центр", desc + " (мельница)", 1, lambda s: None)
    # 3.14: казино
    add("backgrounds/casino", (W, H), "весь экран", "игорный зал (без колеса и разметки стола)", 1, lambda s: None)
    add("props/roulette_wheel", (338, 338), "центр = ось", "колесо рулетки сверху, без цифр", 1, lambda s: None)
    add("props/roulette_ball", (40, 40), "центр", "шарик рулетки", 1, lambda s: None)
    for v in (5, 10, 25, 50):
        add(f"ui/chip_{v}", (72, 72), "центр", f"фишка {v} (без числа)", 1, lambda s: None)
    add("characters/croupier", (150, 150), "низ по центру = край стола", "крупье по пояс", 1, lambda s: None)
    # 3.19: посиделки у камина
    add("backgrounds/fireside", (W, H), "весь экран", "камин крупным планом: пустой очаг с углями и поленьями, без огня "
        "(огонь рисует игра; разметка — backgrounds/fireside.json)", 1, lambda s: None)
    from .spritefit import DECOR_SIZE
    decor_desc = {"cat": "рыжий кот спит клубком (вид сбоку)", "kettle": "чугунный котелок с крышкой, без цепи",
                  "flowers": "глиняный кувшин с полевыми цветами", "rug": "круглый тканый коврик на полу (вид сбоку, сплющен)"}
    for key, (w, h, align) in DECOR_SIZE.items():
        add(f"decor/{key}", (w, h), "низ по центру" if align == "bottom" else "центр", decor_desc[key] + " — приз таверны",
            1, lambda s: None)
    from .config import PRIZES
    for p in PRIZES:
        add(f"icons/prize_{p['id']}", (40, 40), "центр", f"приз таверны: {p['name']}", 1, lambda s: None)
    # 3.16: доска заданий, табличка на поле, облачко, стрелка обучения, частицы и лампочки гирлянды
    for d in (1, 2, 3):
        add(f"ui/quest_note_{d}", (245, 167), "растягивается", f"записка дня на доске, сложность {d}", 1, lambda s: None)
    add("ui/quest_weekly", (244, 366), "растягивается", "свиток задания недели с валиками сверху и снизу", 1, lambda s: None)
    add("ui/pin", (28, 28), "центр", "булавка записки", 1, lambda s: None)
    add("ui/wax_seal", (44, 44), "центр", "сургучная печать свитка недели", 1, lambda s: None)
    add("ui/sign", (112, 56), "растягивается", "деревянная табличка над грядкой (цена, прокачка)", 0, lambda s: None)
    add("ui/bubble", (250, 80), "растягивается", "облачко речи без хвостика", 1, lambda s: None)
    add("ui/bubble_tail", (32, 24), "кончик внизу по центру", "хвостик облачка, смотрит вниз", 1, lambda s: None)
    add("ui/arrow", (44, 60), "остриё внизу по центру", "стрелка обучения, смотрит вниз", 0, lambda s: None)
    # 3.18: плашки счёта, сообщения, баннер, полоски, указатели таверны
    for key, size, desc in (("pill", (180, 40), "плашка счёта (деньги, доход, жетоны, бафы), растягивается в ширину"),
                            ("toast", (300, 40), "плашка сообщения внизу экрана, растягивается в ширину"),
                            ("banner", (360, 52), "баннер-заголовок («РЕЖИМ ПРОКАЧКИ», «САРАЙ»)"),
                            ("bar_frame", (120, 16), "пустая рамка полоски прогресса"),
                            ("bar_fill", (120, 12), "белая заливка полоски (игра красит её)"),
                            ("sign_board", (132, 104), "указатель «Доска заданий» в таверне, стрелка влево"),
                            ("sign_casino", (110, 44), "вывеска «Казино» в таверне, стрелка вправо")):
        add(f"ui/{key}", size, "растягивается", desc, 1, lambda s: None)
    add("ui/move_map", (1240, 278), "вся полоса", "карта глав для окна «Переезд»: лето, средневековье, зима, туман "
        "(места глав — farmgame/move_ui.py, MAP_FIRST/MAP_GAP/MAP_Y)", 1, lambda s: None)
    # 3.20: карточки дерева листьев / печатей (лучше одним листом ui/tree_sheet)
    for key, desc in (("tree_node_open", "карточка улучшения: открыта, копишь на неё"),
                      ("tree_node_ready", "карточка улучшения: можно купить"),
                      ("tree_node_max", "карточка улучшения: изучено до конца"),
                      ("tree_node_locked", "карточка улучшения: закрыта")):
        add(f"ui/{key}", (220, 58), "растягивается (9 частей)", desc, 1, lambda s: None)
    for key, desc in (("tree_pip_off", "кружок уровня: пустой"), ("tree_pip_on", "кружок уровня: взят")):
        add(f"ui/{key}", (32, 32), "центр", desc, 1, lambda s: None)
    fx_desc = {"feather": "чёрное перо вороны (по диагонали)", "star": "звёздочка-блик", "puff": "облачко пыли (белое)",
               "spark": "искорка (белая)", "raindrop": "капля дождя", "bulb_red": "красная лампочка гирлянды",
               "bulb_yellow": "жёлтая лампочка гирлянды", "bulb_green": "зелёная лампочка гирлянды",
               "bulb_blue": "синяя лампочка гирлянды"}
    for key, desc in fx_desc.items():
        sz = spritefit.FX_SIZE.get(key, 28)
        add(f"fx/{key}", (sz, sz), "центр", desc, 0, lambda s: None)
    for n in range(1, 5):
        add(f"icons/note_{n}", (30, 30), "центр", f"нота барда, вариант {n} (в таверне; необязательно)", 1,
            lambda s, n=n: tu.draw_note(s, 9, 22, color=tu.NOTE_COLORS[n - 1]))
    add("icons/coin", (40, 40), "центр", "монета", 0, lambda s: art.draw_coin(s, 20, 20, 17))
    add("icons/coin_silver", (40, 40), "центр", "серебряная монета (доход/с)", 0,
        lambda s: art.draw_coin(s, 20, 20, 17, (200, 215, 240)))
    add("icons/leaf", (40, 40), "центр", "лист (валюта лета)", 0, lambda s: art.draw_leaf_icon(s, 20, 20))
    add("icons/seal", (40, 40), "центр", "печать (валюта средневековья)", 1, lambda s: art.draw_seal_icon(s, 20, 20))
    add("icons/peasant", (26, 26), "центр", "крестьянин", 1, lambda s: art.draw_peasant_head(s, 13, 13))
    for a, key in enumerate(("egg", "milk", "truffle", "honey")):
        add(f"icons/{key}", (30, 30), "центр", ANIMALS[a]["product"], 0, lambda s, a=a: art.draw_product(s, a, 15, 15))
    return specs


def export_templates(out_dir=None):
    out_dir = out_dir or os.path.join(cfg.BASE_DIR, "assets_templates")
    art.USE_SPRITES[0] = False          # рисуем только кодом
    count = 0
    plain = hd.plain_scale()            # шаблоны — всегда в обычном размере, даже из игры в HD
    plain.__enter__()
    try:
        for name, size, anchor, desc, farm_idx, draw in spec_list():
            art.apply_farm(farm_idx)
            surf = _surface(size)
            draw(surf)
            path = os.path.join(out_dir, *name.split("/")) + ".png"
            os.makedirs(os.path.dirname(path), exist_ok=True)
            pygame.image.save(surf, path)
            count += 1
        # карты раскладки для фонов сарая и мельницы (что закроет интерфейс)
        guide_dir = os.path.join(out_dir, "_layout")
        os.makedirs(guide_dir, exist_ok=True)
        for kind in ("barn", "mill"):
            pygame.image.save(_layout_guide(kind), os.path.join(guide_dir, f"{kind}_inside_layout.png"))
            count += 1
        for kind in ("tavern", "quest_board"):
            pygame.image.save(_layout_guide(kind), os.path.join(guide_dir, f"{kind}_layout.png"))
            count += 1
    finally:
        plain.__exit__(None, None, None)
        art.USE_SPRITES[0] = True
        art.apply_farm(0)
    return out_dir, count


def spec_table_markdown():
    rows = ["| Файл (assets/…png) | Размер | Точка привязки | Что это |", "|---|---|---|---|"]
    for name, size, anchor, desc, _f, _d in spec_list():
        rows.append(f"| `{name}.png` | {size[0]}×{size[1]} | {anchor} | {desc} |")
    return "\n".join(rows)


def _skin():
    from . import skin
    return skin


def known_names():
    names = {spec[0] for spec in spec_list()}
    from .spritefit import SHEETS
    names |= set(SHEETS)   # листы: icons/sheet, ui/buttons, icons/prizes, ui/chips
    from .spritefit import BUTTON_SHEET_ORDER
    names |= {"ui/btn_" + n for n in BUTTON_SHEET_ORDER} | {"ui/btn_festival", "ui/btn_shaman", "ui/btn_tavern", "ui/btn_prizes"}   # кнопки: отдельными файлами или листом ui/buttons
    # общие версии без папки фермы: tiles/soil, props/tree, buildings/barn ...
    for n in list(names):
        parts = n.split("/")
        if len(parts) == 3 and parts[1] in {fm["id"] for fm in FARMS}:
            names.add(parts[0] + "/" + parts[2])
    # растение одной картинкой без стадии: crops/summer/potato
    for fm in FARMS:
        for key in fm["plants"]:
            names.add(f"crops/{fm['id']}/{key}")
    return names


# картинки, которые раньше были в игре, а теперь не нужны
LEGACY = {
    "props/chapel": "часовни больше нет (теперь кнопка «Праздник урожая») — файл можно удалить",
    "props/chapel_ringing": "часовни больше нет (теперь кнопка «Праздник урожая») — файл можно удалить",
}


def check_assets():
    """Проверяет папку assets/: какие картинки игра узнала, какие нет (и что, похоже, имелось в виду).
    Возвращает (узнанные, [(файл, подсказка или None)])."""
    import difflib
    from .art import IMAGE_EXTS
    from .audio import AUDIO_EXTS, MUSIC_NAMES, SFX_NAMES
    known = known_names()
    found, unknown = [], []
    if not os.path.isdir(cfg.ASSET_DIR):
        return found, unknown
    for root, _dirs, files in os.walk(cfg.ASSET_DIR):
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), cfg.ASSET_DIR).replace(os.sep, "/")
            stem, ext = os.path.splitext(rel)
            if ext.lower() in (".md", ".txt") or fn.startswith("."):
                continue
            if ext.lower() in (".ttf", ".otf"):
                if stem.lower().startswith("fonts/"):
                    found.append(stem.lower())
                else:
                    unknown.append((rel, "шрифты клади в assets/fonts/"))
                continue
            if ext.lower() in AUDIO_EXTS:
                if stem.lower() in {"music/" + n for n in MUSIC_NAMES} | {"sfx/" + n for n in SFX_NAMES}:
                    found.append(stem.lower())
                elif stem.lower().startswith("sfx/"):
                    unknown.append((rel, "такого звука нет; имена: " + ", ".join(SFX_NAMES)))
                elif os.path.basename(stem).lower() in SFX_NAMES:
                    unknown.append((rel, f"это звук, а не музыка — перенеси в assets/sfx/{fn}"))
                else:
                    unknown.append((rel, "музыку клади в assets/music/ с именем " + ", ".join(MUSIC_NAMES)))
                continue
            if ext.lower() not in IMAGE_EXTS:
                unknown.append((rel, "нужен формат PNG (можно JPG)"))
                continue
            # частая ошибка Windows: medieval.png.png
            inner_stem, inner_ext = os.path.splitext(stem)
            if inner_ext.lower() in IMAGE_EXTS:
                unknown.append((rel, f"двойное расширение — переименуй в {inner_stem}{ext}"))
                continue
            if stem.lower() in LEGACY:
                unknown.append((rel, LEGACY[stem.lower()]))
            elif stem.lower() in known:
                found.append(stem.lower())
            else:
                close = difflib.get_close_matches(stem.lower(), sorted(known), n=1, cutoff=0.6)
                unknown.append((rel, f"может, имелось в виду assets/{close[0]}.png" if close else None))
    return found, unknown
