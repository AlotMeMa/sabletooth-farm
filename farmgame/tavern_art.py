# -*- coding: utf-8 -*-
"""Таверна: разметка зала, рисунки (люди, кружки, жетоны, ноты, облачка), фон зала и доски.
(3.17: вынесено из tavern_ui.py без изменений. Экран таверны — tavern_ui.py и его части.)
Логика заданий — в tavern.py.
Свои картинки (необязательно):
    assets/backgrounds/tavern.png       — зал целиком (1000x640), без бармена и барда;
    assets/backgrounds/quest_board.png  — доска заданий (1000x640), без записок;
    assets/characters/barman.png        — бармен по пояс, низ картинки = край стойки (150x150);
    assets/characters/bard.png          — бард в полный рост, низ = сцена (130x180);
    assets/icons/token.png              — жетон таверны (40x40);
    assets/ui/btn_tavern.png            — кнопка «Таверна» (квадрат).
Музыка — assets/music/tavern.ogg, гул голосов — assets/sfx/crowd.ogg (без файла — встроенный).
"""
import json
import math
import os
import random

import pygame

from .config import W, H, N_CROPS, CUR, fmt, PEASANT_MAX, MILL_MAX_LVL, ASSET_DIR, SONGS, DEV, CASINO_UNLOCK_TOKENS, PRIZES
from .art import (OUT, WHITE, GOLD, RAINBOW, PANEL, PILL, BTN_GREEN, BTN_BLUE, BTN_GREY, P, poly, ellipse, blob, rounded,
                  draw_text, draw_text_fit, render_text, draw_bar, draw_coin, draw_cur_icon, has_sprite, blit_sprite,
                  blit_tf, blit_light, extended_down)
from .particles import soft_dot
from .audio import has_scene_music
from . import tavern as tv
from . import hd

BROWN, SOFT = (90, 70, 60), (140, 110, 95)

# --- раскладка зала (по ней же рисуется свой фон: см. assets_templates/_layout/tavern_layout.png) ---
COUNTER_TOP = 338             # верх барной стойки: на этой линии бармен «стоит» по пояс
BAR_X0, BAR_X1 = 612, 905
BARMAN_X = 768
STAGE_C = (470, 478)          # центр сцены (эллипс 310x86)
BARD_FEET = (470, 474)
BALCONY_FLOOR = 196           # пол балкона; перила 148-196
BOARD_SIGN = pygame.Rect(14, 236, 132, 104)   # стрелка «Доска заданий»
CASINO_DOOR = pygame.Rect(916, 266, 78, 176)
CASINO_SIGN = pygame.Rect(896, 224, 100, 38)
BARMAN_ZONE = pygame.Rect(BARMAN_X - 60, 205, 120, 135)
BARD_ZONE = pygame.Rect(STAGE_C[0] - 70, 330, 140, 150)

# --- доска: всё внутри пробкового поля (x 118-885, y 135-505) ---
BOARD_CORK = pygame.Rect(118, 135, 767, 370)
NOTE_RECTS = [pygame.Rect(128 + c * 260, 145 + r * 183, 245, 167) for r in range(2) for c in range(2)]
WEEKLY_RECT = pygame.Rect(645, 145, 230, 350)

BALCONY_PEOPLE = [   # x, внешность, куда смотрит
    (330, dict(top=(90, 150, 90), dress=(90, 150, 90), hair=(150, 70, 40), style="long", girl=True), 1),
    (385, dict(top=(80, 120, 200), dress=(80, 120, 200), hair=(240, 200, 100), style="bun", girl=True), -1),
    (530, dict(top=(170, 90, 60), legs=(80, 60, 50), hair=(90, 60, 40), style="cap", mug=True), 0),
    (705, dict(top=(150, 90, 170), dress=(150, 90, 170), hair=(40, 30, 30), style="long", girl=True), 1),
    (760, dict(top=(120, 100, 70), legs=(70, 60, 50), hair=(110, 80, 50), style="short", beard=True, mug=True), -1),
]
BALCONY_LINES = ["Слыхала?..", "Хи-хи!", "Да ты что!", "За урожай!", "Ох, этот бард...", "Ещё по одной!",
                 "Ну и ну!", "А он мне...", "Тише ты!", "Ха-ха-ха!"]
PATRONS = [   # гости у левого стола
    (150, dict(top=(110, 120, 140), legs=(70, 70, 80), hair=(60, 50, 40), style="hood", mug=True), 1),
    (282, dict(top=(200, 160, 80), legs=(100, 80, 60), hair=(200, 120, 60), style="short", beard=True, mug=True), -1),
]


# --- раскладка зала: где бармен, бард, вывески, кто болтает и что стоит ПЕРЕД персонажами ---
def _layout_procedural():
    return dict(
        custom=False,
        barman=dict(x=BARMAN_X, waist=COUNTER_TOP + 4, k=1.15, sprite_scale=1.0),
        bard=dict(x=BARD_FEET[0], y=BARD_FEET[1], k=1.15, sprite_scale=1.0),
        board_sign=list(BOARD_SIGN), casino_door=list(CASINO_DOOR), casino_sign=list(CASINO_SIGN),
        talkers=[[x, BALCONY_FLOOR - 72] for x, _l, _f in BALCONY_PEOPLE],
        occluders=[],
        music=dict(MUSIC_TIMING), music_girl=dict(MUSIC_GIRL_TIMING),
        music_fiddler=dict(MUSIC_FIDDLER_TIMING), music_bagpipe=dict(MUSIC_BAGPIPE_TIMING),
        trophies=[[640, 236, "hang"], [700, 338, "stand", "front"], [190, 268, "stand"], [300, 250, "shelf"]],
        fireside=[214, 378, 84, 60],
        decor=dict(kettle=[256, 412], kettle_top=384, flowers=[[342, 452]]),
        fx=dict(fire=[256, 424], candles=[[342, 460], [598, 460], [360, 250], [560, 250]],
                steam=[[778, 592], [180, 506]], motes=[400, 30, 860, 120], barman_mug=None),
    )


# 3.5: темп музыки таверны — по нему бард качается и пускает ноты в такт.
#   bpm — долей в минуту; offset — через сколько секунд от начала трека первая доля (+ задержка звука);
#   loop — длина трека в секундах (pygame не сбрасывает время музыки на повторе).
# Сменил музыку — поправь эти числа в assets/backgrounds/tavern.json: "music": {"bpm": ..., "offset": ..., "loop": ...}
MUSIC_TIMING = dict(bpm=86.68, offset=0.03, loop=56.31)    # под assets/music/tavern.ogg (джига 6/8, доля = ♩.)
# 3.15.2: песня певицы Милы — assets/music/tavern_girl.ogg (нет файла — играет обычная музыка таверны).
# Темп её трека посчитан по файлу (23.11): ровно 120 долей в минуту всю песню, первая доля через 0.08 с,
# длина 234.88 с. Поменял трек — поправь "music_girl" в tavern.json или попроси пересчитать.
MUSIC_GIRL_TIMING = dict(bpm=120.0, offset=0.08, loop=234.88)
# 3.27: песни скрипача и волынщика (посчитано по трекам пользователя; у скрипача рил 172 BPM — качается на половине)
MUSIC_FIDDLER_TIMING = dict(bpm=86.12, offset=0.19, loop=189.49)
MUSIC_BAGPIPE_TIMING = dict(bpm=99.9, offset=0.08, loop=189.05)
# 3.23: как рисовать артиста кодом, пока нет картинки characters/<id>
ARTIST_LOOKS = {
    "bard": dict(top=(60, 140, 90), legs=(150, 60, 60), hair=(170, 110, 60), style="bard"),
    "bard_girl": dict(top=(230, 225, 205), dress=(190, 90, 80), hair=(200, 140, 70), style="long", girl=True),
    "fiddler": dict(top=(200, 120, 60), legs=(80, 90, 130), hair=(240, 200, 110), style="short"),
    "bagpiper": dict(top=(90, 110, 70), legs=(120, 90, 60), hair=(210, 210, 215), style="short", beard=True),
}
NOTE_COLORS = [(255, 235, 150), (255, 200, 120), (190, 230, 255), (255, 190, 210)]


# Под фон assets/backgrounds/tavern.* (зал из Gemini: стойка по диагонали справа, сцена в центре).
# Поменял фон — поправь числа в assets/backgrounds/tavern.json (те же ключи), код трогать не нужно.
CUSTOM_LAYOUT = dict(
    custom=True,
    # 3.20: бармен на 14 px левее — его нижний срез теперь везде за стойкой (справа край стойки ниже)
    barman=dict(x=714, waist=402, k=1.2, sprite_scale=0.66),      # стоит за стойкой, ниже пояса его закрывает стойка
    bard=dict(x=480, y=428, k=1.2, sprite_scale=0.72),            # в центре сцены
    board_sign=[14, 236, 132, 104],
    casino_door=[908, 262, 92, 268],
    casino_sign=[898, 214, 100, 36],
    talkers=[[557, 56], [603, 58], [766, 46], [88, 408], [282, 440]],   # над головами нарисованных гостей
    # что стоит ПЕРЕД персонажами: эти куски фона рисуются поверх них (точки многоугольника)
    occluders=[[[604, 362], [662, 365], [796, 404], [796, 526], [698, 528], [604, 440]]],   # стойка
    # 3.5: живой зал — где на фоне огонь, свечи, что парит (хлеб, кружки), где пылинки в свете окон, кружка бармена
    music=dict(MUSIC_TIMING), music_girl=dict(MUSIC_GIRL_TIMING),
        music_fiddler=dict(MUSIC_FIDDLER_TIMING), music_bagpipe=dict(MUSIC_BAGPIPE_TIMING),
    # трофеи стоят только на том, что нарисовано на фоне (порядок: подкова, кубок, крестьянин, колос).
    # 3.20: все — над камином: подкова прибита к трубе над свечой, остальные три — на каминной полке
    # (её верх идёт наискосок: слева y≈358, справа y≈348)
    trophies=[[205, 316, "hang"], [229, 351, "stand"], [161, 356, "stand"], [258, 349, "stand"]],
    # 3.19: камин (клик — посидеть у огня) и где в зале стоят купленные украшения
    fireside=[188, 362, 82, 98],
    decor=dict(kettle=[222, 424], kettle_top=372, flowers=[[176, 512]]),
    fx=dict(fire=[219, 444], candles=[[205, 335], [359, 393], [564, 393]],
            steam=[[870, 572], [960, 561], [210, 483]], motes=[330, 36, 720, 128], barman_mug=[717, 372]),
)


def load_layout(custom):
    lay = _layout_procedural() if not custom else json.loads(json.dumps(CUSTOM_LAYOUT))
    if custom:
        path = os.path.join(ASSET_DIR, "backgrounds", "tavern.json")
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    extra = json.load(f)
                for k, v in extra.items():
                    if isinstance(v, dict) and isinstance(lay.get(k), dict):
                        lay[k].update(v)
                    else:
                        lay[k] = v
                print("Таверна: разметка из backgrounds/tavern.json")
            except (OSError, ValueError) as e:
                print("backgrounds/tavern.json не прочитан:", e)
    for key in ("board_sign", "casino_door", "casino_sign"):
        lay[key] = pygame.Rect(lay[key])
    b, d = lay["barman"], lay["bard"]
    lay["barman_zone"] = pygame.Rect(int(b["x"] - 50 * b["k"]), int(b["waist"] - 100 * b["k"]), int(100 * b["k"]), int(110 * b["k"]))
    lay["bard_zone"] = pygame.Rect(int(d["x"] - 55 * d["k"]), int(d["y"] - 125 * d["k"]), int(110 * d["k"]), int(130 * d["k"]))
    return lay


TAVERN_TIP = "Таверна: задания на день и неделю, жетоны   (T)"


def build_occluders(bg, polygons):
    """Куски фона, которые стоят перед персонажами (стойка и т. п.): вырезаем их из самого фона
    по многоугольникам и рисуем поверх персонажей. Шва не видно — это те же пиксели.
    Возвращает [(картинка, позиция)]."""
    from .spritefit import Pix
    out = []
    for poly_pts in polygons:
        pts = [(int(x), int(y)) for x, y in poly_pts]
        if len(pts) < 3:
            continue
        x0, y0 = max(0, min(p[0] for p in pts)), max(0, min(p[1] for p in pts))
        x1, y1 = min(W, max(p[0] for p in pts) + 1), min(H, max(p[1] for p in pts) + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        # в HD — по настоящим пикселям фона (маска и кусок тоже в k раз крупнее)
        mask = hd.Surface((x1 - x0, y1 - y0), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 0))
        pygame.draw.polygon(mask, (255, 255, 255, 255), [(x - x0, y - y0) for x, y in pts])
        piece = hd.Surface((x1 - x0, y1 - y0), pygame.SRCALPHA)
        piece.blit(bg, (-x0, -y0))
        pm, pp = Pix(hd.real(mask)), Pix(hd.real(piece))
        for i in range(3, len(pp.buf), 4):
            pp.buf[i] = pm.buf[i]
        out.append((hd.wrap(pp.surface()), (x0, y0)))
    return out


def wrap(text, size, maxw, max_lines=4):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if render_text(t, size, BROWN, None).get_width() <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] += "…"
    return lines


def fmt_long(sec):
    sec = int(max(0, sec))
    d, h, m = sec // 86400, sec % 86400 // 3600, sec % 3600 // 60
    if d:
        return f"{d} д {h} ч"
    if h:
        return f"{h} ч {m} мин"
    return f"{max(1, m)} мин"


# ======================================================================
#                              РИСОВАНИЕ
# ======================================================================
def draw_star(s, x, y, r, color=GOLD):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    poly(s, color, pts, 1)


def draw_mug(s, cx, cy, k=1.0):
    """Кружка с пеной: (cx, cy) — центр."""
    body = pygame.Rect(P(cx - 9 * k), P(cy - 9 * k), P(18 * k), P(20 * k))
    pygame.draw.circle(s, OUT, (P(cx + 10 * k), P(cy + 1 * k)), P(7 * k), max(2, P(3 * k)))
    rounded(s, (230, 170, 60), body, P(3 * k), 2)
    pygame.draw.line(s, (250, 210, 120), (body.x + P(5 * k), body.y + P(6 * k)), (body.x + P(5 * k), body.bottom - P(4 * k)), max(1, P(2 * k)))
    blob(s, (255, 250, 240), [(cx - 6 * k, cy - 10 * k, 5 * k), (cx, cy - 12 * k, 6 * k), (cx + 6 * k, cy - 10 * k, 5 * k)], 2)


def draw_token(s, x, y, k=1.0):
    """Жетон таверны: бронзовая монета с кружкой."""
    if blit_sprite(s, "icons/token", x, y, k * 0.85, "center"):
        return
    r = 16 * k
    pygame.draw.circle(s, OUT, (P(x), P(y)), P(r) + 2)
    pygame.draw.circle(s, (200, 125, 65), (P(x), P(y)), P(r))
    pygame.draw.circle(s, (225, 155, 90), (P(x), P(y)), P(r * 0.76))
    draw_mug(s, x - 1 * k, y + 2 * k, 0.55 * k)


def draw_person(s, x, y, k, look, t=0.0, talk=False, upper=False, arms=(0.25, -0.25), face=0):
    """Человечек в стиле игры. (x, y) — ступни; upper=True — только по пояс, y = пояс.
    arms — углы рук от «вниз» (радианы, + — наружу). Возвращает (левая кисть, правая кисть)."""
    skin = look.get("skin", (245, 205, 170))
    top = look.get("top", (150, 110, 80))
    leg = 0 if upper else 30 * k
    wy = y - leg
    if not upper:
        if look.get("dress"):
            poly(s, look["dress"], [(x - 13 * k, wy - 6 * k), (x + 13 * k, wy - 6 * k), (x + 21 * k, y), (x - 21 * k, y)], 2)
        else:
            for dx in (-7, 7):
                rounded(s, look.get("legs", (90, 70, 60)), (P(x + dx * k - 5 * k), P(wy - 2), P(10 * k), P(leg - 3 * k)), 3, 2)
                rounded(s, (70, 50, 40), (P(x + dx * k - 6 * k), P(y - 7 * k), P(13 * k), P(7 * k)), 3, 2)
    tw, th = 30 * k, 40 * k
    torso = pygame.Rect(P(x - tw / 2), P(wy - th), P(tw), P(th + (2 if not upper else 0)))
    # руки — сзади тела только «плечи», кисти поверх
    hands = []
    for side, ang in ((-1, arms[0]), (1, arms[1])):
        sx, sy = x + side * (tw / 2 - 4 * k), wy - th + 8 * k
        a = ang * side
        hx, hy = sx + math.sin(a) * 26 * k, sy + math.cos(a) * 26 * k
        pygame.draw.line(s, OUT, (P(sx), P(sy)), (P(hx), P(hy)), max(3, P(10 * k)))
        pygame.draw.line(s, top, (P(sx), P(sy)), (P(hx), P(hy)), max(2, P(7 * k)))
        hands.append((hx, hy))
    rounded(s, top, torso, P(9 * k), 2)
    if look.get("apron"):
        rounded(s, (242, 238, 228), (P(x - 11 * k), P(wy - th * 0.62), P(22 * k), P(th * 0.62 + 2)), 3, 2)
    if look.get("dress") and not upper:   # шнуровка корсажа
        pygame.draw.line(s, (250, 235, 200), (P(x), P(wy - th + 12 * k)), (P(x), P(wy - 4 * k)), max(1, P(2 * k)))
    for hx, hy in hands:
        pygame.draw.circle(s, OUT, (P(hx), P(hy)), P(5 * k) + 1)
        pygame.draw.circle(s, skin, (P(hx), P(hy)), P(5 * k))
    # голова
    hx, hy, hr = x + face * 1.5 * k, wy - th - 11 * k, 13 * k
    style, hair = look.get("style", "short"), look.get("hair", (90, 60, 40))
    if style == "long":
        rounded(s, hair, (P(hx - 15 * k), P(hy - 8 * k), P(30 * k), P(34 * k)), P(10 * k), 2)
    if style == "hood":
        pygame.draw.circle(s, OUT, (P(hx), P(hy - 1 * k)), P(hr + 5 * k) + 2)
        pygame.draw.circle(s, top, (P(hx), P(hy - 1 * k)), P(hr + 5 * k))
    pygame.draw.circle(s, OUT, (P(hx), P(hy)), P(hr) + 2)
    pygame.draw.circle(s, skin, (P(hx), P(hy)), P(hr))
    if style in ("short", "long", "bun", "cap"):
        pts = [(hx - hr - 1, hy + 1 * k), (hx - hr + 2 * k, hy - 8 * k), (hx - 4 * k, hy - hr - 2 * k),
               (hx + 6 * k, hy - hr - 1 * k), (hx + hr, hy - 6 * k), (hx + hr + 1, hy + 1 * k),
               (hx + 6 * k, hy - 6 * k), (hx - 6 * k, hy - 5 * k)]
        poly(s, hair, pts, 2)
    if style == "bun":
        pygame.draw.circle(s, OUT, (P(hx), P(hy - hr - 4 * k)), P(6 * k) + 2)
        pygame.draw.circle(s, hair, (P(hx), P(hy - hr - 4 * k)), P(6 * k))
    if style == "cap":
        poly(s, (170, 60, 60), [(hx - hr, hy - 6 * k), (hx - hr + 3 * k, hy - hr - 4 * k), (hx + hr - 3 * k, hy - hr - 4 * k),
                                (hx + hr + 5 * k, hy - 6 * k)], 2)
    if style == "bald":
        for side in (-1, 1):
            pygame.draw.circle(s, hair, (P(hx + side * (hr - 2 * k)), P(hy - 1 * k)), P(4 * k))
    if style == "bard":
        poly(s, (60, 120, 170), [(hx - hr - 6 * k, hy - 5 * k), (hx - hr + 2 * k, hy - hr - 6 * k), (hx + hr + 4 * k, hy - hr - 4 * k),
                                 (hx + hr + 8 * k, hy - 5 * k)], 2)
        pygame.draw.line(s, OUT, (P(hx + 6 * k), P(hy - hr - 4 * k)), (P(hx + 22 * k), P(hy - hr - 20 * k)), max(3, P(5 * k)))
        pygame.draw.line(s, (235, 80, 70), (P(hx + 6 * k), P(hy - hr - 4 * k)), (P(hx + 22 * k), P(hy - hr - 20 * k)), max(2, P(3 * k)))
    # лицо
    ex = face * 1.5 * k
    er = max(1, P(1.8 * k))
    pygame.draw.circle(s, OUT, (P(hx - 4.5 * k + ex), P(hy - 1 * k)), er)
    pygame.draw.circle(s, OUT, (P(hx + 4.5 * k + ex), P(hy - 1 * k)), er)
    if look.get("girl"):
        for side in (-1, 1):
            pygame.draw.circle(s, (255, 150, 155), (P(hx + side * 7.5 * k + ex), P(hy + 3 * k)), max(1, P(2 * k)))
    if look.get("beard"):
        poly(s, look.get("hair", (90, 60, 40)), [(hx - 9 * k, hy + 3 * k), (hx + 9 * k, hy + 3 * k), (hx + 5 * k, hy + 13 * k),
                                                 (hx, hy + 15 * k), (hx - 5 * k, hy + 13 * k)], 1)
    if look.get("mustache"):
        poly(s, look.get("hair", (90, 60, 40)), [(hx - 9 * k + ex, hy + 5 * k), (hx + ex, hy + 2.5 * k), (hx + 9 * k + ex, hy + 5 * k),
                                                 (hx + ex, hy + 6 * k)], 1)
    mouth_y = hy + 6 * k
    if talk and math.sin(t * 14) > 0:
        pygame.draw.ellipse(s, (150, 50, 50), (P(hx - 2.5 * k + ex), P(mouth_y - 1 * k), max(2, P(5 * k)), max(2, P(4 * k))))
    elif not look.get("beard") and not look.get("mustache"):
        pygame.draw.arc(s, OUT, (P(hx - 3 * k + ex), P(mouth_y - 3 * k), max(2, P(6 * k)), max(2, P(5 * k))),
                        math.pi + 0.3, 2 * math.pi - 0.3, 1)
    return hands


def draw_lute(s, x, y, k, strum):
    """Лютня: корпус у пояса, гриф вверх-влево."""
    nx, ny = x - 30 * k, y - 26 * k
    pygame.draw.line(s, OUT, (P(x), P(y)), (P(nx), P(ny)), max(4, P(7 * k)))
    pygame.draw.line(s, (120, 75, 40), (P(x), P(y)), (P(nx), P(ny)), max(2, P(4 * k)))
    poly(s, (110, 70, 40), [(nx - 3 * k, ny - 5 * k), (nx + 5 * k, ny - 2 * k), (nx + 2 * k, ny + 4 * k), (nx - 6 * k, ny + 1 * k)], 2)
    ellipse(s, (215, 140, 70), x + 4 * k, y + 2 * k, 30 * k, 24 * k, 2)
    pygame.draw.circle(s, (70, 40, 25), (P(x + 3 * k), P(y + 1 * k)), P(4 * k))
    if strum > 0.6:   # дрожат струны
        pygame.draw.line(s, (255, 240, 200), (P(x - 4 * k), P(y - 6 * k)), (P(x + 10 * k), P(y + 8 * k)), 1)


def draw_note(s, x, y, alpha_k=1.0, color=(255, 235, 150)):
    pygame.draw.line(s, OUT, (P(x + 5), P(y)), (P(x + 5), P(y - 16)), 4)
    pygame.draw.line(s, color, (P(x + 5), P(y)), (P(x + 5), P(y - 16)), 2)
    poly(s, color, [(x + 5, y - 16), (x + 13, y - 11), (x + 5, y - 9)], 1)
    ellipse(s, color, x, y + 1, 12, 9, 2)


def draw_bubble_skin(s, rect, tip, side="down"):
    """3.16: облачко-картинка ui/bubble (растягивается) + хвостик ui/bubble_tail (остриё — в tip).
    side: "down" — хвостик под облачком, "left" — слева. False — картинки облачка нет (рисуем кодом)."""
    from . import skin
    bx, by, w, h = rect
    img = skin.stretched("bubble", w, h)
    if img is None:
        return False
    tx, ty = tip
    if side == "down":
        gap = max(6, ty - (by + h) + 6)                      # хвостик от края облачка до кончика
        k = gap / 24
        if not blit_tf(s, "ui/bubble_tail", tx, ty, k):
            poly(s, WHITE, [(tx - 8, by + h - 4), (tx + 8, by + h - 4), (tx, ty)], 2)
    else:
        gap = max(6, bx - tx + 6)
        k = gap / 24
        # хвостик вниз, повёрнутый на 90° по часовой: остриё смотрит влево, на говорящего
        if not blit_tf(s, "ui/bubble_tail", tx, ty, k, angle=-90):
            poly(s, WHITE, [(bx + 4, ty - 8), (bx + 4, ty + 8), (tx, ty)], 2)
    s.blit(img, (bx, by))
    return True


def draw_note_icon(s, x, y, n=0, k=0.85):
    """Нота как в зале: своя картинка icons/note_<n+1> (если есть), иначе нарисованная кодом.
    (x, y) — как у draw_note: низ головки ноты."""
    if blit_sprite(s, f"icons/note_{n % 4 + 1}", x + 6, y - 7, k, "center"):
        return
    draw_note(s, x, y, color=NOTE_COLORS[n % len(NOTE_COLORS)])


def draw_bubble(s, x, y, text, size=15, maxw=250, tail_down=True):
    """Облачко с речью: (x, y) — кончик хвостика."""
    lines = wrap(text, size, maxw, 4)
    imgs = [render_text(line, size, BROWN, None) for line in lines]
    w = max(i.get_width() for i in imgs) + 24
    h = len(imgs) * (size + 4) + 16
    bx = max(8, min(W - w - 8, x - w // 2))
    by = max(4, y - 12 - h)
    y = max(y, by + h + 8)
    if not draw_bubble_skin(s, (bx, by, w, h), (x, y), "down"):
        poly(s, WHITE, [(x - 9, by + h - 3), (x + 9, by + h - 3), (x, y)], 2)
        rounded(s, WHITE, (bx, by, w, h), 12, 2)
        pygame.draw.polygon(s, WHITE, [(x - 7, by + h - 4), (x + 7, by + h - 4), (x, y - 3)])
    for n, img in enumerate(imgs):
        s.blit(img, img.get_rect(center=(bx + w // 2, by + 8 + (size + 4) * n + (size + 4) // 2)))


def build_tavern_scene():
    """Фон зала и передний слой (перила балкона, стойка, столы, табуреты). Свой фон — передний слой не нужен."""
    bg = hd.Surface((W, H))
    if blit_sprite(bg, "backgrounds/tavern", 0, 0, 1, "topleft"):
        return bg, None, True
    rnd = random.Random(5)
    # второй этаж: тёмные доски, окна
    bg.fill((96, 62, 40))
    for x in range(0, W, 38):
        pygame.draw.line(bg, (78, 50, 32), (x, 0), (x, BALCONY_FLOOR), 2)
    for wx in (440, 820):
        rounded(bg, (255, 215, 130), (wx - 34, 34, 68, 84), 30, 4)
        pygame.draw.line(bg, OUT, (wx, 36), (wx, 116), 3)
        pygame.draw.line(bg, OUT, (wx - 32, 76), (wx + 32, 76), 3)
    # балка балкона
    pygame.draw.rect(bg, (70, 44, 28), (0, BALCONY_FLOOR, W, 26))
    pygame.draw.rect(bg, OUT, (0, BALCONY_FLOOR, W, 26), 3)
    # первый этаж: штукатурка с балками (фахверк)
    pygame.draw.rect(bg, (214, 186, 146), (0, 222, W, 224))
    for x0, x1 in ((0, 150), (166, 600), (616, 900)):
        for yy in (300, 372):
            pass
    pygame.draw.line(bg, (112, 72, 44), (166, 300), (240, 222), 10)
    pygame.draw.line(bg, (112, 72, 44), (526, 222), (600, 300), 10)
    for px in (150, 600, 900):
        pygame.draw.rect(bg, (112, 72, 44), (px, 222, 16, 224))
        pygame.draw.rect(bg, OUT, (px, 222, 16, 224), 2)
    # фонари под балконом
    for lx in (360, 560):
        pygame.draw.line(bg, OUT, (lx, 222), (lx, 240), 2)
        glow = hd.Surface((90, 90), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 210, 120, 70), (45, 45), 44)
        bg.blit(glow, (lx - 45, 210))
        rounded(bg, (255, 220, 140), (lx - 9, 240, 18, 24), 4, 2)
        poly(bg, (70, 50, 40), [(lx - 12, 240), (lx + 12, 240), (lx, 232)], 2)
    # камин слева
    for row, y in enumerate(range(276, 446, 20)):
        for x in range(176 - (10 if row % 2 else 0), 336, 22):
            g = 140 + rnd.randint(-15, 15)
            rounded(bg, (g, g - 6, g - 12), (max(176, x), y, min(22, 336 - max(176, x)) - 1, 19), 3, 1, (95, 85, 80))
    pygame.draw.ellipse(bg, (40, 25, 20), (206, 336, 100, 90))
    pygame.draw.rect(bg, (40, 25, 20), (206, 381, 100, 65))
    pygame.draw.rect(bg, (70, 44, 28), (166, 262, 180, 16))
    pygame.draw.rect(bg, OUT, (166, 262, 180, 16), 2)
    for lx in (226, 252, 278):   # дрова
        rounded(bg, (120, 80, 50), (lx - 14, 428, 34, 12), 5, 2)
    # полки с бутылками за стойкой
    for sy in (252, 298):
        pygame.draw.rect(bg, (100, 64, 40), (BAR_X0 + 18, sy, BAR_X1 - BAR_X0 - 36, 8))
        pygame.draw.rect(bg, OUT, (BAR_X0 + 18, sy, BAR_X1 - BAR_X0 - 36, 8), 2)
        x = BAR_X0 + 30
        while x < BAR_X1 - 40:
            col = rnd.choice([(80, 150, 90), (150, 80, 60), (90, 120, 170), (190, 150, 70), (120, 70, 120)])
            hgt = rnd.randint(22, 34)
            rounded(bg, col, (x, sy - hgt, 14, hgt), 4, 2)
            rounded(bg, col, (x + 4, sy - hgt - 9, 6, 11), 2, 2)
            x += rnd.randint(19, 26)
            if abs(x - BARMAN_X) < 50:          # за барменом пусто — его так лучше видно
                x = BARMAN_X + 50
    # бочка с краном
    rounded(bg, (150, 95, 55), (BAR_X1 - 66, 312, 52, 26), 8, 2)
    # дверь в игорный зал
    d = CASINO_DOOR
    rounded(bg, (60, 30, 30), d, 36, 3)
    curt = d.inflate(-10, -10)
    for i, x in enumerate(range(curt.x, curt.right, 12)):
        pygame.draw.rect(bg, (170, 40, 50) if i % 2 == 0 else (140, 30, 40), (x, curt.y + 20, 12, curt.h - 20))
    pygame.draw.rect(bg, (220, 180, 70), (curt.x, curt.y + 16, curt.w, 6))
    # пол с перспективой
    pygame.draw.rect(bg, (150, 100, 62), (0, 446, W, H - 446))
    vx, vy = 500, 120
    for xb in range(-1300, 2400, 95):
        xt = vx + (xb - vx) * (446 - vy) / (H - vy)
        pygame.draw.line(bg, (122, 80, 48), (P(xt), 446), (xb, H), 2)
    for yy in (460, 478, 500, 528, 562, 604):
        pygame.draw.line(bg, (132, 88, 54), (0, yy), (W, yy), 2)
    pygame.draw.rect(bg, (70, 44, 28), (0, 438, W, 10))
    pygame.draw.line(bg, OUT, (0, 446), (W, 446), 2)
    # сцена
    cx, cy = STAGE_C
    pygame.draw.ellipse(bg, OUT, (cx - 157, cy - 43 + 16, 314, 88))
    pygame.draw.rect(bg, (110, 70, 40), (cx - 155, cy, 310, 18))
    pygame.draw.ellipse(bg, (110, 70, 40), (cx - 155, cy - 43 + 16, 310, 86))
    pygame.draw.line(bg, OUT, (cx - 156, cy), (cx - 156, cy + 18), 2)
    pygame.draw.line(bg, OUT, (cx + 155, cy), (cx + 155, cy + 18), 2)
    pygame.draw.arc(bg, (190, 50, 55), (cx - 155, cy - 43 + 14, 310, 86), math.pi + 0.15, 2 * math.pi - 0.15, 7)
    pygame.draw.ellipse(bg, (176, 122, 72), (cx - 155, cy - 43, 310, 86))
    pygame.draw.ellipse(bg, OUT, (cx - 155, cy - 43, 310, 86), 3)
    pygame.draw.ellipse(bg, (160, 108, 62), (cx - 115, cy - 30, 230, 60), 2)
    for sx in (cx - 128, cx + 128):          # свечи на краю сцены
        rounded(bg, (245, 240, 220), (sx - 4, cy - 14, 8, 16), 2, 2)
        pygame.draw.circle(bg, (255, 200, 80), (sx, cy - 19), 4)

    fg = hd.Surface((W, H), pygame.SRCALPHA)
    # перила балкона
    for x in range(10, W, 26):
        rounded(fg, (120, 78, 46), (x, 156, 10, 38), 3, 2)
    rounded(fg, (110, 70, 42), (0, 146, W, 12), 4, 2)
    rounded(fg, (110, 70, 42), (0, 186, W, 10), 3, 2)
    # стойка
    rounded(fg, (140, 90, 52), (BAR_X0 + 8, COUNTER_TOP + 12, BAR_X1 - BAR_X0 - 16, 446 - COUNTER_TOP - 12), 4, 3)
    for i in range(3):
        pw = (BAR_X1 - BAR_X0 - 56) // 3
        rounded(fg, (122, 78, 44), (BAR_X0 + 22 + i * (pw + 6), COUNTER_TOP + 26, pw, 64), 4, 2)
    rounded(fg, (110, 66, 36), (BAR_X0, COUNTER_TOP - 2, BAR_X1 - BAR_X0, 16), 5, 3)
    pygame.draw.line(fg, (160, 105, 65), (BAR_X0 + 10, COUNTER_TOP + 2), (BAR_X1 - 10, COUNTER_TOP + 2), 2)
    draw_mug(fg, BAR_X0 + 40, COUNTER_TOP - 10, 0.9)
    draw_mug(fg, BAR_X1 - 40, COUNTER_TOP - 10, 0.9)
    for sx in (BAR_X0 + 50, BAR_X0 + 140, BAR_X0 + 230):     # табуреты
        for lx in (-16, 16):
            pygame.draw.line(fg, OUT, (sx + lx, 460), (sx + lx * 1.3, 512), 6)
            pygame.draw.line(fg, (120, 78, 46), (sx + lx, 460), (sx + lx * 1.3, 512), 3)
        ellipse(fg, (150, 98, 58), sx, 458, 56, 18, 2)
    # стол слева
    for tx, ty, tw in ((215, 528, 190), (790, 618, 230)):
        rounded(fg, (110, 70, 42), (tx - 11, ty, 22, 60), 4, 2)
        ellipse(fg, (110, 70, 42), tx, ty + 8, tw, 46, 2)
        ellipse(fg, (160, 105, 62), tx, ty, tw, 46, 3)
    draw_mug(fg, 180, 518, 0.9)
    draw_mug(fg, 252, 520, 0.9)
    blob(fg, (230, 180, 100), [(770, 603, 16), (790, 600, 14)], 2)     # хлеб
    draw_mug(fg, 835, 604, 0.9)
    return bg, fg, False


def build_board_background():
    bg = hd.Surface((W, H))
    if blit_sprite(bg, "backgrounds/quest_board", 0, 0, 1, "topleft"):
        return bg
    rnd = random.Random(9)
    bg.fill((96, 62, 40))
    for x in range(0, W, 38):
        pygame.draw.line(bg, (78, 50, 32), (x, 0), (x, H), 2)
    cork = BOARD_CORK
    frame = cork.inflate(110, 112)
    rounded(bg, (120, 78, 46), frame, 10, 3)
    pygame.draw.rect(bg, (196, 150, 100), cork)
    for _ in range(1400):
        x, y = rnd.randrange(cork.x, cork.right), rnd.randrange(cork.y, cork.bottom)
        c = rnd.choice([(176, 130, 84), (214, 170, 118), (160, 115, 72)])
        pygame.draw.circle(bg, c, (x, y), rnd.choice((1, 1, 2)))
    pygame.draw.rect(bg, OUT, cork, 2)
    for nx, ny in ((frame.x + 6, frame.y + 6), (frame.right - 14, frame.y + 6), (frame.x + 6, frame.bottom - 14),
                   (frame.right - 14, frame.bottom - 14)):
        pygame.draw.circle(bg, (200, 190, 170), (nx + 4, ny + 4), 4)
    # пол
    pygame.draw.rect(bg, (150, 100, 62), (0, 585, W, H - 585))
    pygame.draw.line(bg, OUT, (0, 585), (W, 585), 2)
    return bg


# ======================================================================
#                              ПОВЕДЕНИЕ
# ======================================================================
