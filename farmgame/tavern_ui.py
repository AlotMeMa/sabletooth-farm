# -*- coding: utf-8 -*-
"""Таверна на экране: зал (бармен, бард, балкон с гостями), доска заданий, кнопки и звук.

Подмешивается в App (class App(TavernUI)). Логика заданий — в tavern.py.
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

from .config import W, H, N_CROPS, CUR, fmt, PEASANT_MAX, MILL_MAX_LVL, ASSET_DIR
from .art import (OUT, WHITE, GOLD, PANEL, PILL, BTN_GREEN, BTN_BLUE, BTN_GREY, P, poly, ellipse, blob, rounded,
                  draw_text, draw_text_fit, render_text, draw_bar, draw_coin, draw_cur_icon, has_sprite, blit_sprite)
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
    )


# Под фон assets/backgrounds/tavern.* (зал из Gemini: стойка по диагонали справа, сцена в центре).
# Поменял фон — поправь числа в assets/backgrounds/tavern.json (те же ключи), код трогать не нужно.
CUSTOM_LAYOUT = dict(
    custom=True,
    barman=dict(x=728, waist=402, k=1.2, sprite_scale=0.66),      # стоит за стойкой, ниже пояса его закрывает стойка
    bard=dict(x=480, y=428, k=1.2, sprite_scale=0.72),            # в центре сцены
    board_sign=[14, 236, 132, 104],
    casino_door=[908, 262, 92, 268],
    casino_sign=[898, 214, 100, 36],
    talkers=[[557, 56], [603, 58], [766, 46], [88, 408], [282, 440]],   # над головами нарисованных гостей
    # что стоит ПЕРЕД персонажами: эти куски фона рисуются поверх них (точки многоугольника)
    occluders=[[[604, 362], [662, 365], [796, 404], [796, 526], [698, 528], [604, 440]]],   # стойка
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


def draw_bubble(s, x, y, text, size=15, maxw=250, tail_down=True):
    """Облачко с речью: (x, y) — кончик хвостика."""
    lines = wrap(text, size, maxw, 4)
    imgs = [render_text(line, size, BROWN, None) for line in lines]
    w = max(i.get_width() for i in imgs) + 24
    h = len(imgs) * (size + 4) + 16
    bx = max(8, min(W - w - 8, x - w // 2))
    by = max(4, y - 12 - h)
    y = max(y, by + h + 8)
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
class TavernUI:
    def init_tavern(self):
        self.tavern = tv.Tavern()
        self.tavern_check = 0.0
        self.audio_scene = None
        self.tv_bubble = None          # [x, y, text, life]
        self.tv_talk = None            # [индекс гостя на балконе, текст, life]
        self.tv_talk_timer = 2.0
        self.tv_notes = []             # ноты от барда: [x, y, life, vx]
        self.tv_note_timer = 0.0
        self.barman_line = 0
        self.tavern_greeted = False
        self.tavern_bg = self.tavern_fg = None
        self.tavern_custom = False
        self.tl = load_layout(False)
        self.tavern_occ = []
        self.tavern_debug = False      # режим разработчика: показать разметку зала
        self.tavern_check_seen = False
        self.board_bg = None

    def quest_blocked(self):
        """Задания, которые сейчас не выполнить: их не выдаём."""
        f, out = self.farm, set()
        if PEASANT_MAX - f.peasants < 2:
            out.add("peasant")
        if sum(MILL_MAX_LVL - lvl for lvl in f.m_levels) < 3:
            out.add("build")
        left = sum(len(node["costs"]) - f.up(nid) for nid, node in f.nodes().items())
        if left < 4:
            out.add("tree")
        return out

    def tavern_refresh(self):
        changed = self.tavern.refresh(self.farm_info(), blocked=self.quest_blocked())
        self.pay_owed()
        return changed

    # ---------- переходы ----------
    def open_tavern(self):
        if not self.tavern.unlocked:
            return
        self.tavern_refresh()
        self.view, self.mode = "tavern", "normal"
        self.modal = None
        if self.tavern_bg is None:
            self.tavern_bg, self.tavern_fg, self.tavern_custom = build_tavern_scene()
            self.tl = load_layout(self.tavern_custom)
            self.tavern_occ = build_occluders(self.tavern_bg, self.tl["occluders"])
        if not self.tavern_greeted:
            self.tavern_greeted = True
            hint = (" Тебя уже ждёт награда!" if self.tavern.claimable() else "")
            self.say_barman("Заходи, путник! Задания — на доске, слева." + hint)

    def open_board(self):
        if self.board_bg is None:
            self.board_bg = build_board_background()
        self.view = "board"

    def leave_tavern(self):
        self.view = "field"

    def sync_scene_audio(self):
        """Музыка и гул таверны включаются/выключаются сами по тому, где мы сейчас."""
        want = "tavern" if self.view in ("tavern", "board") else None
        if want != self.audio_scene:
            self.audio_scene = want
            self.music.play_for(self.farm_info()["id"], want)
            self.sfx.ambient("crowd" if want else None)
        self.sfx.update_ambient()

    # ---------- задания ----------
    def quest(self, event, n=1):
        for q in self.tavern.on(event, n):
            self.sfx.play("quest")
            big = q is self.tavern.weekly
            self.toast(("Задание НЕДЕЛИ выполнено" if big else "Задание выполнено") + f": «{q['title']}»! Награда — в таверне", 4)

    def quest_money(self, minutes):
        """Деньги за задание = столько минут дохода грядок (без дождя и буста), но не меньше небольшой суммы."""
        f = self.farm
        inc = sum(f.income_per_sec(i, False) for i in range(N_CROPS))
        if f.boost_left > 0:
            inc /= 2
        return max(inc * 60 * minutes, 20 * f.price_mult * minutes)

    def grant_reward(self, minutes, prestige, boost):
        """Выдаёт ферме награду задания (жетоны начисляет сама таверна). Возвращает, сколько денег дали."""
        f = self.farm
        money = self.quest_money(minutes)
        f.earn(money)
        if prestige:
            f.leaves += prestige
            f.home_leaves += prestige
            f.leaves_earned += prestige
        if boost:
            f.boost_left += boost * 60
        return money

    def pay_owed(self):
        """Награды за задания, которые сменились незабранными (полночь, понедельник), выдаём автоматически."""
        owed = self.tavern.take_owed()
        if not owed:
            return
        money = sum(self.grant_reward(o["minutes"], o["prestige"], o["boost"]) for o in owed)
        tokens, prestige, boost = (sum(o[k] for o in owed) for k in ("tokens", "prestige", "boost"))
        parts = ["+$" + fmt(money), f"+{tokens} жетонов"]
        if prestige:
            parts.append(f"+{prestige} {CUR['gen']}")
        if boost:
            parts.append(f"доход x2 на {boost} мин")
        self.sfx.play("claim")
        self.toast("Незабранные награды таверны выданы сами: " + ", ".join(parts), 7)
        self.save()

    def claim_quest(self, q, pos):
        reward = self.tavern.claim(q)
        if not reward:
            return
        minutes, tokens, prestige, boost = reward
        money = self.grant_reward(minutes, prestige, boost)
        parts = ["+$" + fmt(money), f"+{tokens} жетонов"]
        if prestige:
            parts.append(f"+{prestige} {CUR['gen']}")
        if boost:
            parts.append(f"доход x2 на {boost} мин")
        self.sfx.play("claim")
        self.floater(pos[0], pos[1] - 20, "+$" + fmt(money))
        self.toast("Награда: " + ", ".join(parts), 4)
        for d in self.tavern.just_done:
            self.sfx.play("quest")
            self.toast(f"Задание НЕДЕЛИ выполнено: «{d['title']}»!", 4)
        self.save()

    # ---------- жители ----------
    def say_barman(self, text=None):
        if text is None:
            text = tv.BARMAN_LINES[self.barman_line % len(tv.BARMAN_LINES)]
            self.barman_line += 1
        b = self.tl["barman"]
        self.tv_bubble = [b["x"], b["waist"] - 112 * b["k"], text, 4.5]

    def poke_bard(self):
        d = self.tl["bard"]
        self.tv_bubble = [d["x"], d["y"] - 135 * d["k"], random.choice(tv.BARD_LINES), 3.5]
        for _ in range(6):
            self.tv_notes.append([d["x"] + random.uniform(-30, 30), d["y"] - 70 * d["k"] + random.uniform(-10, 10), 2.0,
                                  random.uniform(-40, 40)])

    def poke_casino(self):
        self.toast("Игорный зал пока закрыт — скоро откроется!", 2.5)
        self.say_barman("Туда пока нельзя: там ещё расставляют столы для костей.")

    def tavern_tick(self, dt):
        t = self.tavern
        if not t.unlocked and self.farm.farm_index >= tv.TAVERN_FROM_FARM:
            t.unlocked = True
            self.tavern_refresh()
            self.toast("Открылась таверна «Хмельной колос»! Кнопка — над «Магазином»", 5)
            self.sfx.play("fanfare")
        self.tavern_check -= dt
        if t.unlocked and self.tavern_check <= 0:
            self.tavern_check = 5.0
            if self.tavern_refresh() and self.tavern_check_seen:
                self.toast("На доске в таверне — новые задания!", 4)
            self.tavern_check_seen = True
        self.sync_scene_audio()
        if self.view != "tavern":
            return
        rdt = min(dt, 0.25)
        if self.tv_bubble:
            self.tv_bubble[3] -= rdt
            if self.tv_bubble[3] <= 0:
                self.tv_bubble = None
        if self.tv_talk:
            self.tv_talk[2] -= rdt
            if self.tv_talk[2] <= 0:
                self.tv_talk = None
        self.tv_talk_timer -= rdt
        if self.tv_talk_timer <= 0 and self.tl["talkers"]:
            self.tv_talk_timer = random.uniform(2.5, 5.0)
            self.tv_talk = [random.randrange(len(self.tl["talkers"])), random.choice(BALCONY_LINES), 2.2]
        self.tv_note_timer -= rdt
        if self.tv_note_timer <= 0:
            self.tv_note_timer = random.uniform(0.5, 0.9)
            d = self.tl["bard"]
            self.tv_notes.append([d["x"] + random.uniform(-25, 25), d["y"] - 70 * d["k"], 2.2, random.uniform(-25, 25)])
        for n in self.tv_notes:
            n[0] += n[3] * rdt + math.sin(self.t_real * 3 + n[2]) * 0.4
            n[1] -= 40 * rdt
            n[2] -= rdt
        self.tv_notes = [n for n in self.tv_notes if n[2] > 0][-30:]

    # ---------- экран: зал ----------
    def draw_tavern_view(self):
        s, tt = self.screen, self.t_real
        s.blit(self.tavern_bg, (0, 0))
        if not self.tavern_custom:
            # огонь в камине
            for i in range(5):
                fx = 228 + i * 14
                h = 26 + 12 * math.sin(tt * 7 + i * 1.7) + 6 * math.sin(tt * 13 + i)
                poly(s, (250, 150, 50), [(fx - 9, 430), (fx + 9, 430), (fx + 2, 430 - h), (fx - 1, 430 - h * 1.1)], 0)
                poly(s, (255, 225, 110), [(fx - 4, 430), (fx + 4, 430), (fx + 1, 430 - h * 0.6)], 0)
            # гости на балконе (за перилами)
            for n, (x, look, face) in enumerate(BALCONY_PEOPLE):
                talking = self.tv_talk is not None and self.tv_talk[0] == n
                bob = math.sin(tt * 2 + n * 1.3) * 1.5
                lift = -0.9 if look.get("mug") and math.sin(tt * 0.8 + n) > 0.85 else 0.35
                hands = draw_person(s, x, BALCONY_FLOOR + bob, 0.85, look, tt, talking, arms=(0.3, lift), face=face)
                if look.get("mug"):
                    draw_mug(s, hands[1][0] + 4, hands[1][1] - 4, 0.6)
        # бармен по пояс (протирает кружку); за стойкой — стойка рисуется поверх него
        L = self.tl
        b = L["barman"]
        wipe = math.sin(tt * 3)
        if not blit_sprite(s, "characters/barman", b["x"], b["waist"] + 2 + math.sin(tt * 1.5) * 1, b["sprite_scale"], "midbottom"):
            look = dict(top=(200, 210, 225), apron=True, hair=(70, 50, 40), style="bald", mustache=True)
            talking = self.tv_bubble is not None and self.tv_bubble[0] == b["x"]
            hands = draw_person(s, b["x"], b["waist"], b["k"], look, tt, talking, upper=True,
                                arms=(0.9 + 0.25 * wipe, 0.9 - 0.25 * wipe))
            draw_mug(s, hands[0][0] + 4, hands[0][1] - 6, 0.7 * b["k"])
            rounded(s, (245, 245, 240), (P(hands[1][0] - 7 * b["k"]), P(hands[1][1] - 5 * b["k"]), P(14 * b["k"]), P(10 * b["k"])), 3, 2)
        if not self.tavern_custom:
            for n, (x, look, face) in enumerate(PATRONS):
                cheers = math.sin(tt * 0.9 + n * 2) > 0.8
                hands = draw_person(s, x, 520, 1.05, look, tt, cheers, arms=(0.3, -1.0 if cheers else 0.5), face=face)
                draw_mug(s, hands[1][0] + 2, hands[1][1] - 5, 0.75)
            s.blit(self.tavern_fg, (0, 0))
        for img, pos in self.tavern_occ:          # стойка и всё, что стоит перед персонажами
            s.blit(img, pos)
        # бард на сцене
        d = L["bard"]
        strum = (math.sin(tt * 9) + 1) / 2
        bob = abs(math.sin(tt * 4.5)) * 2
        bx, by, k = d["x"], d["y"], d["k"]
        if not blit_sprite(s, "characters/bard", bx, by - bob, d["sprite_scale"], "midbottom"):
            look = dict(top=(60, 140, 90), legs=(150, 60, 60), hair=(170, 110, 60), style="bard")
            talking = self.tv_bubble is not None and self.tv_bubble[0] == bx
            draw_person(s, bx, by - bob, k, look, tt, talking, arms=(1.35, 0.55 + 0.35 * strum))
            draw_lute(s, bx + 3.5 * k, by - bob - 40 * k, k, strum)
        for x, y, life, _vx in self.tv_notes:
            draw_note(s, x, y)
        self.zone(L["barman_zone"], self.say_barman)
        self.zone(L["bard_zone"], self.poke_bard)
        # стрелка к доске заданий
        r = L["board_sign"]
        poly(s, (176, 120, 70), [(r.x, r.centery), (r.x + 34, r.y + 10), (r.x + 34, r.y + 26), (r.right, r.y + 26),
                                 (r.right, r.bottom - 26), (r.x + 34, r.bottom - 26), (r.x + 34, r.bottom - 10)], 3)
        draw_text(s, "Доска", 18, (r.x + 82, r.centery - 11))
        draw_text(s, "заданий", 16, (r.x + 82, r.centery + 10))
        self.zone_btn(r, self.open_board, 12)
        if self.tavern.claimable():
            pygame.draw.circle(s, OUT, (r.right - 4, r.y + 24), 12)
            pygame.draw.circle(s, (240, 70, 70), (r.right - 4, r.y + 24), 10)
            draw_text(s, "!", 15, (r.right - 4, r.y + 24))
        # вывеска казино
        c, door = L["casino_sign"], L["casino_door"]
        rounded(s, (176, 120, 70), c, 6, 3)
        draw_text(s, "Казино  >", 17, c.center)
        draw_text(s, "скоро", 13, (door.centerx, door.y + 70), (255, 230, 160))
        self.zone_btn(door.union(c), self.poke_casino, 10)
        # разговоры
        if self.tv_talk and self.tv_talk[0] < len(L["talkers"]):
            n, text, _ = self.tv_talk
            tx, ty = L["talkers"][n]
            draw_bubble(s, tx, ty, text, 13, 140)
        if self.tv_bubble:
            x, y, text, _ = self.tv_bubble
            draw_bubble(s, x, y, text)
        for x, y, text, life, color in self.floaters:
            draw_text(s, text, 18, (x, y), color)
        if self.tavern_debug:
            self.draw_tavern_debug()

    def draw_tavern_debug(self):
        """Разметка зала поверх картинки (режим разработчика): что закрывает персонажей, где они стоят."""
        s, L = self.screen, self.tl
        for pts in L["occluders"]:
            pygame.draw.polygon(s, (255, 40, 40), [(int(x), int(y)) for x, y in pts], 2)
        for key, col in (("barman_zone", (60, 160, 255)), ("bard_zone", (60, 160, 255)), ("board_sign", (60, 220, 90)),
                         ("casino_door", (60, 220, 90)), ("casino_sign", (60, 220, 90))):
            pygame.draw.rect(s, col, L[key], 2)
        for tx, ty in L["talkers"]:
            pygame.draw.circle(s, (255, 230, 0), (int(tx), int(ty)), 5)
        for key in ("barman", "bard"):
            p = L[key]
            y = p["waist"] if key == "barman" else p["y"]
            pygame.draw.line(s, (255, 0, 255), (p["x"] - 12, int(y)), (p["x"] + 12, int(y)), 2)
        draw_text(s, "красное — перед персонажами, жёлтое — облачка, малиновое — пояс бармена / ноги барда", 13,
                  (W // 2, 628), (255, 230, 120))

    # ---------- экран: доска ----------
    def draw_board_view(self):
        s = self.screen
        s.blit(self.board_bg, (0, 0))
        plate = pygame.Rect(W // 2 - 190, 6, 380, 58)
        for x in (plate.x + 30, plate.right - 30):
            pygame.draw.line(s, OUT, (x, 0), (x, plate.y + 4), 3)
        rounded(s, (176, 120, 70), plate, 8, 3)
        draw_text(s, "ДОСКА ЗАДАНИЙ", 24, (plate.centerx, plate.y + 21))
        draw_text(s, "новые задания через " + fmt_long(tv.seconds_to_midnight()), 13, (plate.centerx, plate.y + 45),
                  (255, 235, 200))
        for q, r in zip(self.tavern.daily, NOTE_RECTS):
            self.draw_note_card(q, r)
        if self.tavern.weekly:
            self.draw_weekly_card(self.tavern.weekly, WEEKLY_RECT)
        for x, y, text, life, color in self.floaters:
            draw_text(s, text, 18, (x, y), color)

    def draw_reward_line(self, q, cx, y, size=15):
        """$ и жетоны в одну строку по центру."""
        s = self.screen
        minutes, tokens, _p, _b = self.tavern.reward_of(q)
        money = render_text("$" + fmt(self.quest_money(minutes)), size, BROWN, None)
        tok = render_text(str(tokens), size, BROWN, None)
        w = 22 + money.get_width() + 18 + 22 + tok.get_width()
        x = cx - w // 2
        draw_coin(s, x + 9, y, 9)
        s.blit(money, money.get_rect(midleft=(x + 22, y)))
        x += 22 + money.get_width() + 18
        draw_token(s, x + 9, y, 0.6)
        s.blit(tok, tok.get_rect(midleft=(x + 22, y)))

    def draw_claim_area(self, q, rect, size=16):
        s = self.screen
        if q["claimed"]:
            box = rect.inflate(-16, -4)
            pygame.draw.rect(s, (60, 150, 70), box, 3, border_radius=8)
            draw_text(s, "ВЫПОЛНЕНО", size, box.center, (60, 150, 70), outline=None)
        elif q["progress"] >= q["target"]:
            b = rect                      # размер не меняем: иначе «звук наведения» щёлкал бы каждый кадр
            glow = 0.5 + 0.5 * math.sin(self.t_real * 5)
            rounded(s, (255, 230, 120), b.inflate(8, 8), 13, 0)
            rounded(s, tuple(int(c + (255 - c) * 0.25 * glow) for c in BTN_GREEN), b, 10, 3)
            draw_text(s, "Забрать награду!", size, b.center)
            self.zone_btn(b, lambda: self.claim_quest(q, b.center))
        else:
            draw_text(s, "выполняется…", size - 2, rect.center, SOFT, outline=None)

    def draw_note_card(self, q, r):
        """Записка дня 245x167: звёзды сложности, название, задание, прогресс, награда, кнопка."""
        s = self.screen
        paper = {1: (250, 242, 210), 2: (246, 232, 192), 3: (242, 222, 178)}[q["diff"]]
        pygame.draw.rect(s, (60, 40, 30), r.move(3, 4), border_radius=6)
        rounded(s, paper, r, 6, 2)
        pygame.draw.circle(s, OUT, (r.centerx, r.y + 8), 7)
        pygame.draw.circle(s, (210, 60, 60), (r.centerx, r.y + 8), 5)
        for i in range(q["diff"]):
            draw_star(s, r.x + 14 + i * 16, r.y + 13, 7)
        draw_text_fit(s, q["title"], 17, (r.centerx, r.y + 31), r.w - 24, BROWN, outline=None)
        for n, line in enumerate(wrap(q["text"], 14, r.w - 22, 2)):
            draw_text(s, line, 14, (r.centerx, r.y + 52 + n * 17), SOFT, outline=None)
        bar = pygame.Rect(r.x + 14, r.y + 84, r.w - 28, 16)
        draw_bar(s, bar, q["progress"] / max(1, q["target"]), (120, 200, 90))
        draw_text(s, f"{fmt(q['progress'])} / {fmt(q['target'])}", 12, bar.center)
        self.draw_reward_line(q, r.centerx, r.y + 115, 14)
        self.draw_claim_area(q, pygame.Rect(r.x + 14, r.y + 131, r.w - 28, 28), 15)

    def draw_weekly_card(self, q, r):
        """Свиток недели 230x350."""
        s = self.screen
        pygame.draw.rect(s, (60, 40, 30), r.move(4, 5), border_radius=8)
        rounded(s, (248, 236, 200), r, 8, 3)
        for y in (r.y, r.bottom):                         # деревянные валики свитка
            rounded(s, (130, 85, 50), (r.x - 7, y - 8, r.w + 14, 16), 8, 3)
        sx, sy = r.right - 28, r.y + 34
        blob(s, (200, 45, 50), [(sx + math.cos(a) * 8, sy + math.sin(a) * 8, 6)
                                for a in [i * math.pi / 4 for i in range(8)]] + [(sx, sy, 10)], 2)
        draw_star(s, sx, sy, 7, (250, 205, 70))
        draw_text(s, "ЗАДАНИЕ", 18, (r.centerx - 14, r.y + 26), (190, 60, 50), outline=None)
        draw_text(s, "НЕДЕЛИ", 18, (r.centerx - 14, r.y + 46), (190, 60, 50), outline=None)
        draw_text_fit(s, q["title"], 19, (r.centerx, r.y + 76), r.w - 24, BROWN, outline=None)
        for n, line in enumerate(wrap(q["text"], 14, r.w - 24, 3)):
            draw_text(s, line, 14, (r.centerx, r.y + 100 + n * 18), SOFT, outline=None)
        bar = pygame.Rect(r.x + 14, r.y + 152, r.w - 28, 18)
        draw_bar(s, bar, q["progress"] / max(1, q["target"]), (230, 170, 60))
        draw_text(s, f"{fmt(q['progress'])} / {fmt(q['target'])}", 13, bar.center)
        minutes, tokens, prestige, boost = self.tavern.reward_of(q)
        draw_text(s, "Награда:", 15, (r.centerx, r.y + 188), BROWN, outline=None)
        rows = [(lambda x, y: draw_coin(s, x, y, 9), "$" + fmt(self.quest_money(minutes)) + f" ({minutes // 60} ч дохода)"),
                (lambda x, y: draw_token(s, x, y, 0.6), f"{tokens} жетонов"),
                (lambda x, y: draw_cur_icon(s, x, y, 0.55), f"{prestige} {CUR['gen']}"),
                (lambda x, y: draw_text(s, "x2", 13, (x, y), GOLD), f"доход x2 на {boost} мин")]
        for n, (icon, text) in enumerate(rows):
            y = r.y + 212 + n * 24
            icon(r.x + 24, y)
            draw_text_fit(s, text, 14, (r.x + 42, y), r.w - 52, BROWN, anchor="midleft", outline=None)
        self.draw_claim_area(q, pygame.Rect(r.x + 14, r.y + 300, r.w - 28, 30), 15)
        draw_text(s, "новое через " + fmt_long(tv.seconds_to_monday()), 12, (r.centerx, r.bottom - 14), SOFT, outline=None)

    # ---------- HUD ----------
    def draw_tokens_pill(self, x, y, right=False):
        s = self.screen
        img = render_text(str(self.tavern.tokens), 18, WHITE, OUT)
        w = 58 + img.get_width() + 14
        r = pygame.Rect(x - w if right else x, y, w, 40)
        rounded(s, (235, 190, 130), r, 20, 3)
        draw_token(s, r.x + 22, r.centery, 0.95)
        s.blit(img, img.get_rect(midleft=(r.x + 44, r.centery)))
        return r

    def draw_tavern_back(self, label, cb, width=134):
        if label == "На поле" and has_sprite("ui/btn_field"):
            self.icon_button(pygame.Rect(16, 560, 62, 56), "field", None, cb, label)
            return
        back = pygame.Rect(16, 560, width, 56)
        rounded(self.screen, BTN_GREEN, back, 10, 3)
        draw_text(self.screen, "<  " + label, 18, back.center)
        self.zone_btn(back, cb)

    def draw_tavern_button(self):
        """Кнопка «Таверна» на поле: слева, над «Магазином»."""
        if not self.tavern.unlocked:
            return
        r = pygame.Rect(16, 478, 62, 56)
        if not has_sprite("ui/btn_tavern") and has_sprite("ui/btn_shop"):
            # своих кнопок-картинок уже много, а этой нет — рисуем деревянную плашку в тон им, а не синюю
            s = self.screen
            hov = self.modal is None and r.collidepoint(self.mouse)
            rounded(s, (255, 240, 190) if hov else (120, 72, 40), r.inflate(6, 6), 12, 0)
            rounded(s, (176, 112, 62), r, 10, 3)
            rounded(s, (214, 160, 100), r.inflate(-10, -10), 7, 2, (150, 95, 55))
            draw_mug(s, r.centerx - 3, r.centery + 4, 1.2)
            draw_text(s, "Таверна", 12, (r.centerx, r.bottom + 12))
            if self.tavern.claimable():
                pygame.draw.circle(s, OUT, (r.right - 2, r.y + 2), 11)
                pygame.draw.circle(s, (240, 70, 70), (r.right - 2, r.y + 2), 9)
                draw_text(s, "!", 14, (r.right - 2, r.y + 2))
            self.zone_btn(r, self.open_tavern, glow="sprite")
            self.tip(r, TAVERN_TIP)
            return
        self.icon_button(pygame.Rect(16, 478, 62, 56), "tavern", lambda r: draw_mug(self.screen, r.centerx - 3, r.centery + 4, 1.2),
                         self.open_tavern, "Таверна", badge=bool(self.tavern.claimable()), tip=TAVERN_TIP)

    def draw_boost_pill(self, y):
        f, s = self.farm, self.screen
        if f.boost_left <= 0:
            return
        m, sec = int(f.boost_left // 60), int(f.boost_left % 60)
        img = render_text(f"доход x2   {m}:{sec:02d}", 15, WHITE, OUT)
        r = pygame.Rect(14, y, 58 + img.get_width() + 14, 32)
        rounded(s, (250, 200, 90), r, 16, 3)
        draw_text(s, "x2", 15, (r.x + 30, r.centery), WHITE)
        s.blit(img, img.get_rect(midleft=(r.x + 54, r.centery)))
