# -*- coding: utf-8 -*-
"""3.36: Рыбацкая деревня — рисунки кодом (пока нет картинок пользователя):
рыбы вместо овощей, пруд-участок за сеткой (закрытый — болото), краб вместо белки, чайка вместо вороны,
рыбак (значок артели, работник на фестивале, плясуны), груз повозки рыботорговца.
Свои картинки подставляются по тем же именам, что у других глав: crops/fishing/<рыба>[_1.._3],
tiles/fishing/soil(_locked), creatures/crab, creatures/gull, icons/fisherman, characters/fisher_worker ...
"""
import math

import pygame

from .config import *  # noqa: F401,F403
from .art_base import *  # noqa: F401,F403

# рыбы: (спина, брюхо, плавники, полоски/пятна)
FISH_LOOKS = {
    "roach": ((150, 165, 175), (230, 232, 236), (225, 85, 70), None),
    "crucian": ((205, 165, 70), (245, 220, 150), (190, 120, 60), None),
    "perch": ((120, 160, 80), (230, 225, 170), (235, 110, 60), "stripes"),
    "bream": ((175, 165, 140), (235, 228, 205), (120, 110, 95), None),
    "carp": ((170, 130, 70), (240, 210, 140), (150, 100, 55), "scales"),
    "trout": ((120, 150, 130), (240, 225, 225), (200, 130, 140), "spots"),
    "salmon": ((140, 160, 185), (250, 190, 170), (120, 135, 160), None),
    "koi": ((250, 250, 245), (255, 255, 250), (240, 110, 60), "koi"),
    "goldfish": ((250, 175, 40), (255, 220, 110), (255, 150, 30), "crown"),
}


def draw_fish(s, x, y, k, key, leap=0.0):
    """Рыбка с мордашкой выпрыгивает из воды: (x, y) — где круги на воде. leap 0..1 — насколько высоко."""
    back, belly, fin, mark = FISH_LOOKS.get(key, FISH_LOOKS["roach"])
    ellipse(s, (180, 215, 235), x, y, 26 * k, 7 * k, 1)                         # круги на воде
    ellipse(s, (205, 230, 245), x, y, 16 * k, 4 * k, 0)
    cy = y - (12 + 6 * leap) * k
    tail = [(x + 11 * k, cy), (x + 20 * k, cy - 8 * k), (x + 19 * k, cy + 8 * k)]
    poly(s, fin, tail, 2)
    poly(s, fin, [(x - 2 * k, cy - 8 * k), (x + 6 * k, cy - 13 * k), (x + 8 * k, cy - 6 * k)], 2)   # спинной плавник
    ellipse(s, back, x, cy, 26 * k, 17 * k)
    ellipse(s, belly, x - 1 * k, cy + 3 * k, 20 * k, 8 * k, 0)
    if mark == "stripes":
        for dx in (-3, 2, 7):
            pygame.draw.line(s, (70, 100, 50), (P(x + dx * k), P(cy - 7 * k)), (P(x + dx * k - 1), P(cy + 2 * k)),
                             max(1, P(2 * k)))
    elif mark == "spots":
        for dx, dy in ((-2, -4), (4, -3), (7, 0), (1, 1)):
            pygame.draw.circle(s, (60, 80, 70), (P(x + dx * k), P(cy + dy * k)), max(1, P(1.2 * k)))
    elif mark == "scales":
        for dx in (-1, 4, 9):
            pygame.draw.arc(s, (140, 100, 50), pygame.Rect(P(x + dx * k - 3 * k), P(cy - 4 * k), max(2, P(6 * k)),
                                                           max(2, P(6 * k))), 3.4, 6.0, 1)
    elif mark == "koi":
        for dx, dy, r in ((-3, -3, 4), (6, 1, 3.5)):
            pygame.draw.circle(s, (235, 80, 50), (P(x + dx * k), P(cy + dy * k)), max(1, P(r * k)))
    elif mark == "crown":
        poly(s, (255, 225, 90), [(x - 6 * k, cy - 7 * k), (x - 5 * k, cy - 13 * k), (x - 2 * k, cy - 9 * k),
                                 (x + 1 * k, cy - 14 * k), (x + 3 * k, cy - 8 * k)], 1)
    face(s, x - 6 * k, cy - 1 * k, k * 0.75)


def _fish_plant(key):
    def plant(s, x, y, k):
        draw_fish(s, x, y, k, key)
    plant.__name__ = f"plant_{key}"
    return plant


FISH_PLANTS = {key: _fish_plant(key) for key in FISH_LOOKS}


def draw_pond_tile(s, cx, cy, locked, corners, t=0.0):
    """Участок пруда: вода за сеткой на колышках (закрытый — заросшее болото). corners — 4 угла ромба."""
    top, right, bottom, left = corners
    d = 8
    side = (110, 86, 64)                                          # дощатый бортик
    poly(s, side, [left, bottom, (bottom[0], bottom[1] + d), (left[0], left[1] + d)])
    poly(s, tuple(max(0, c - 18) for c in side), [bottom, right, (right[0], right[1] + d), (bottom[0], bottom[1] + d)])
    if locked:
        poly(s, (104, 112, 78), [top, right, bottom, left], 3)
        for i, (u, v) in enumerate(((0.3, 0.4), (0.6, 0.3), (0.45, 0.65), (0.7, 0.6))):
            px = left[0] + (right[0] - left[0]) * u
            py = top[1] + (bottom[1] - top[1]) * v
            ellipse(s, (88, 96, 66), px, py, 22, 8, 0)
            for dx in (-4, 0, 4):                                 # камыш
                pygame.draw.line(s, (90, 120, 70), (P(px + dx), P(py)), (P(px + dx * 1.6), P(py - 14 - i % 2 * 4)), 2)
            pygame.draw.circle(s, (120, 85, 55), (P(px + 6), P(py - 16)), 2)
        return
    poly(s, THEME["soil"], [top, right, bottom, left], 3)
    for i in range(3):                                            # блики и рябь
        u = (i + 0.5) / 3
        px = left[0] + (right[0] - left[0]) * u
        py = cy + math.sin(t * 1.3 + i * 2) * 3
        pygame.draw.arc(s, (150, 190, 215), pygame.Rect(P(px - 12), P(py - 3), 24, 8), 0.3, 2.8, 2)
    # сетка по краю: верёвка с поплавками и колышки по углам
    for a, b in ((top, right), (right, bottom), (bottom, left), (left, top)):
        pygame.draw.line(s, (235, 225, 200), (P(a[0]), P(a[1] - 3)), (P(b[0]), P(b[1] - 3)), 2)
        for u in (0.33, 0.66):
            fx, fy = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u - 3
            pygame.draw.circle(s, OUT, (P(fx), P(fy)), 4)
            pygame.draw.circle(s, (230, 80, 60), (P(fx), P(fy)), 3)
    for px, py in corners:
        pygame.draw.line(s, OUT, (P(px), P(py + 2)), (P(px), P(py - 12)), 5)
        pygame.draw.line(s, (150, 110, 70), (P(px), P(py + 1)), (P(px), P(py - 11)), 3)


def draw_crab(s, x, y, d, hop=0.0, golden=False, t=0.0, sx=1.0, sy=1.0, angle=0.0, alpha=None, pivot="midbottom"):
    """Краб вместо белки: бежит боком, щёлкает клешнями. Та же подпись, что у draw_squirrel."""
    name = "creatures/crab_gold" if golden else "creatures/crab"
    if blit_tf(s, [name, "creatures/crab"], x, y - hop, 0.6, flip=d < 0, sx=sx, sy=sy, angle=angle, pivot=pivot,
               alpha=alpha):
        return
    body = (245, 200, 60) if golden else (225, 85, 60)
    dark = tuple(max(0, c - 50) for c in body)
    by = y - hop - 9
    if pivot == "center":
        by = y
    snap = 0.3 * math.sin(t * 12)
    for side in (-1, 1):                                          # ножки
        for i in range(3):
            lx = x + side * (7 + i * 4)
            pygame.draw.line(s, dark, (P(lx), P(by + 2)), (P(lx + side * 6), P(by + 8 + (i % 2) * 2)), 2)
    ellipse(s, body, x, by, 28 * sx, 17 * sy)
    for side in (-1, 1):                                          # клешни
        cx, cy = x + side * 17, by - 8
        pygame.draw.line(s, dark, (P(x + side * 10), P(by - 3)), (P(cx), P(cy + 3)), 3)
        poly(s, body, [(cx - 5, cy), (cx + 5, cy), (cx + side * 6, cy - 8 - snap * 6), (cx, cy - 4)], 2)
    for side in (-1, 1):                                          # глаза на стебельках
        ex = x + side * 5
        pygame.draw.line(s, OUT, (P(ex), P(by - 6)), (P(ex), P(by - 12)), 2)
        pygame.draw.circle(s, WHITE, (P(ex), P(by - 13)), 3)
        pygame.draw.circle(s, OUT, (P(ex + (1 if d > 0 else -1)), P(by - 13)), 1)
    pygame.draw.arc(s, OUT, pygame.Rect(P(x - 4), P(by - 2), 8, 5), math.pi + 0.3, 2 * math.pi - 0.3, 1)
    if golden:
        _light(s, x, by, 46, (255, 230, 120), 120)


def draw_gull(s, x, y, d, t=0.0, flying=False, peck=0.0, k=1.4, wings_up=True, sx=1.0, sy=1.0, angle=0.0):
    """Чайка вместо вороны (та же подпись, что у draw_crow)."""
    names = ["creatures/gull_fly", "creatures/gull"] if flying and wings_up else ["creatures/gull"]
    if blit_tf(s, names, x, y, 0.55 * k / 1.4, flip=d > 0, sx=sx, sy=sy, angle=angle):
        return
    body, wing = (248, 248, 245), (175, 185, 195)
    ellipse(s, body, x, y - 12 * k, 22 * k * sx, 13 * k * sy)
    hx = x - d * 10 * k
    blob(s, body, [(hx, y - 20 * k + peck * 6 * k, 6 * k)], 2)
    poly(s, (245, 190, 50), [(hx - d * 5 * k, y - 21 * k + peck * 6 * k), (hx - d * 12 * k, y - 19 * k + peck * 8 * k),
                             (hx - d * 5 * k, y - 18 * k + peck * 6 * k)], 1)
    pygame.draw.circle(s, OUT, (P(hx - d * 2 * k), P(y - 22 * k + peck * 6 * k)), max(1, P(1.2 * k)))
    if flying:
        up = -1 if wings_up else 0.4
        for side in (-1, 1):
            poly(s, wing, [(x - 3 * k, y - 14 * k), (x + side * 18 * k, y - 14 * k + up * 12 * k), (x + 5 * k, y - 12 * k)], 2)
    else:
        poly(s, wing, [(x - 4 * k, y - 15 * k), (x + d * 12 * k, y - 10 * k), (x - 2 * k, y - 8 * k)], 2)
        for dx in (-3, 3):
            pygame.draw.line(s, (245, 190, 50), (P(x + dx * k), P(y - 5 * k)), (P(x + dx * k), P(y)), 2)


def _light(s, x, y, size, color, peak):
    from .art_field import blit_light          # art_field импортирует этот модуль — берём при вызове
    blit_light(s, x, y, size, color, peak, 0.0)


def draw_fisherman_head(s, x, y, k=1.0):
    """Значок рыбака (артель Рыбацкой деревни): лицо, борода, жёлтая зюйдвестка."""
    if blit_icon_name(s, "icons/fisherman", x, y, k):
        return
    blob(s, (150, 120, 95), [(x, y + 5 * k, 6.5 * k), (x - 4 * k, y + 3 * k, 4.5 * k), (x + 4 * k, y + 3 * k, 4.5 * k)], 2)
    blob(s, (245, 205, 170), [(x, y - 1 * k, 6 * k)], 2)
    poly(s, (245, 200, 50), [(x - 11 * k, y - 2 * k), (x + 11 * k, y - 2 * k), (x + 7 * k, y - 6 * k),
                             (x + 4 * k, y - 13 * k), (x - 4 * k, y - 13 * k), (x - 7 * k, y - 6 * k)], 2)
    pygame.draw.circle(s, OUT, (P(x - 2.5 * k), P(y - 1 * k)), max(1, P(1.2 * k)))
    pygame.draw.circle(s, OUT, (P(x + 2.5 * k), P(y - 1 * k)), max(1, P(1.2 * k)))


def blit_icon_name(s, name, x, y, k):
    from .art_world import blit_icon
    return blit_icon(s, name, x, y, k)


def draw_fisher(s, x, y, k=1.0, t=0.0, flip=False, rod=True, alpha=None, cheer=False, n=0):
    """Рыбак в полный рост в жёлтом дождевике: с удочкой (работник фестиваля) или с поднятой рыбой (плясун)."""
    name = "characters/fisher_dancer" if cheer else "characters/fisher_worker"
    bob = abs(math.sin(t * (6 if cheer else 2))) * (4 if cheer else 1) * k
    if blit_tf(s, [f"{name}_{n % 2 + 1}", name], x, y - bob, 0.5 * k, flip=flip, alpha=alpha):
        return
    d = -1 if flip else 1
    y -= bob
    for dx in (-4, 4):                                            # сапоги
        ellipse(s, (60, 70, 80), x + dx * k, y - 2 * k, 8 * k, 5 * k, 1)
    poly(s, (245, 200, 50), [(x - 9 * k, y - 4 * k), (x + 9 * k, y - 4 * k), (x + 6 * k, y - 24 * k), (x - 6 * k, y - 24 * k)], 2)
    draw_fisherman_head(s, x, y - 30 * k, 0.9 * k)
    if cheer:                                                     # держит над головой большую рыбу
        pygame.draw.line(s, OUT, (P(x - 6 * k), P(y - 22 * k)), (P(x - 8 * k), P(y - 44 * k)), max(2, P(3 * k)))
        pygame.draw.line(s, OUT, (P(x + 6 * k), P(y - 22 * k)), (P(x + 8 * k), P(y - 44 * k)), max(2, P(3 * k)))
        draw_fish(s, x, y - 34 * k, 0.9 * k, "salmon", 0.6)
    elif rod:
        sway = 4 * math.sin(t * 1.7)
        tip = (x + d * 30 * k, y - 42 * k + sway)
        pygame.draw.line(s, (120, 85, 55), (P(x + d * 5 * k), P(y - 16 * k)), (P(tip[0]), P(tip[1])), max(2, P(2 * k)))
        pygame.draw.line(s, (220, 220, 220), (P(tip[0]), P(tip[1])), (P(tip[0] + d * 6 * k), P(y + 6 * k)), 1)
        pygame.draw.circle(s, (230, 80, 60), (P(tip[0] + d * 6 * k), P(y + 6 * k)), max(2, P(2.5 * k)))


def draw_fish_cargo(s, x, y):
    """Груз повозки рыботорговца: бочки и рыбьи хвосты над бортом."""
    for cx in (-38, -8, 22, 50):
        ellipse(s, (150, 110, 70), x + cx, y - 64, 24, 18)
        pygame.draw.line(s, (100, 75, 50), (P(x + cx - 12), P(y - 64)), (P(x + cx + 12), P(y - 64)), 2)
    for cx in (-22, 8, 36):
        poly(s, (170, 190, 205), [(x + cx, y - 72), (x + cx - 6, y - 84), (x + cx + 6, y - 84)], 2)


# 3.37: хищники садка 2 — (спина, брюхо, плавники, узор, длина тела)
PRED_LOOKS = {
    "pike": ((96, 130, 80), (220, 225, 180), (150, 120, 70), "spots", 1.5),
    "asp": ((120, 140, 155), (230, 235, 240), (190, 110, 100), None, 1.3),
    "zander": ((140, 150, 130), (230, 228, 210), (110, 110, 100), "stripes", 1.4),
    "burbot": ((110, 100, 70), (200, 190, 150), (90, 80, 55), "spots", 1.5),
    "catfish": ((80, 85, 90), (190, 185, 175), (70, 70, 75), "whiskers", 1.6),
    "eel": ((90, 110, 80), (210, 205, 160), (80, 95, 70), None, 2.2),
    "taimen": ((150, 100, 90), (235, 205, 190), (190, 80, 70), "spots", 1.5),
    "sturgeon": ((110, 120, 135), (225, 225, 220), (95, 105, 120), "plates", 1.8),
    "beluga": ((150, 160, 170), (240, 240, 238), (130, 140, 150), "plates", 1.9),
    "swordfish": ((60, 90, 150), (215, 225, 240), (50, 70, 120), "sword", 1.7),
}


def draw_predator(s, x, y, k, pid, t=0.0, flip=False):
    """Хищник в садке: плывёт, чуть виляя хвостом. (x, y) — центр. Картинка fish/<id> (смотрит влево) или кодом."""
    wig = math.sin(t * 5) * 4 * k
    if blit_tf(s, f"fish/{pid}", x, y, 0.45 * k, flip=flip, angle=math.sin(t * 2) * 3, pivot="center"):
        return
    back, belly, fin, mark, ln = PRED_LOOKS.get(pid, PRED_LOOKS["pike"])
    d = 1 if flip else -1                     # куда смотрит голова: -1 влево
    L, Hh = 30 * ln * k, 14 * k
    tx = x - d * L * 0.55
    poly(s, fin, [(tx, y), (tx - d * 14 * k, y - 11 * k + wig), (tx - d * 14 * k, y + 11 * k + wig)], 2)
    poly(s, fin, [(x - d * 4 * k, y - Hh * 0.45), (x - d * 16 * k, y - Hh * 0.9), (x - d * 20 * k, y - Hh * 0.4)], 2)
    ellipse(s, back, x, y, L * 1.1, Hh * 1.6)
    ellipse(s, belly, x + d * 2 * k, y + Hh * 0.3, L * 0.9, Hh * 0.6, 0)
    if mark == "spots":
        for dx, dy in ((-0.2, -0.3), (0.05, -0.1), (0.25, -0.35), (-0.05, -0.45)):
            pygame.draw.circle(s, tuple(max(0, c - 45) for c in back), (P(x + dx * L), P(y + dy * Hh)), max(1, P(2 * k)))
    elif mark == "stripes":
        for dx in (-0.2, 0.0, 0.2):
            pygame.draw.line(s, tuple(max(0, c - 50) for c in back), (P(x + dx * L), P(y - Hh * 0.7)),
                             (P(x + dx * L), P(y + Hh * 0.1)), max(1, P(2 * k)))
    elif mark == "plates":
        for dx in (-0.25, -0.05, 0.15, 0.35):
            poly(s, (225, 220, 200), [(x + dx * L - 3 * k, y - Hh * 0.6), (x + dx * L, y - Hh * 0.85),
                                      (x + dx * L + 3 * k, y - Hh * 0.6)], 1)
    hx = x + d * L * 0.48
    if mark == "sword":
        pygame.draw.line(s, OUT, (P(hx), P(y - 2 * k)), (P(hx + d * 30 * k), P(y - 4 * k)), max(3, P(4 * k)))
        pygame.draw.line(s, (200, 210, 225), (P(hx), P(y - 2 * k)), (P(hx + d * 30 * k), P(y - 4 * k)), max(1, P(2 * k)))
    if mark == "whiskers":
        for dy in (-1, 3):
            pygame.draw.line(s, OUT, (P(hx), P(y + dy * k)), (P(hx + d * 14 * k), P(y + (dy * 3 + 6) * k)), 1)
    ex = x + d * L * 0.32
    pygame.draw.circle(s, WHITE, (P(ex), P(y - 4 * k)), max(2, P(3.5 * k)))
    pygame.draw.circle(s, OUT, (P(ex + d * 1 * k), P(y - 4 * k)), max(1, P(1.8 * k)))
    pygame.draw.line(s, OUT, (P(ex - 3 * k), P(y - 9 * k)), (P(ex + d * 4 * k), P(y - 7 * k)), max(1, P(1.5 * k)))  # бровь
    for n in range(3):                                            # зубки
        zx = hx - d * (3 + n * 4) * k
        poly(s, WHITE, [(zx - 1.5 * k, y + 2 * k), (zx + 1.5 * k, y + 2 * k), (zx, y + 5 * k)], 0)


def draw_swim_fish(s, x, y, k, key, d=-1, t=0.0, glow=False):
    """3.38: рыбка в аквариуме (без кругов на воде). (x, y) — центр тела, d: -1 смотрит влево, +1 вправо."""
    if glow and has_sprite(f"fish/swim_{key}"):
        pygame.draw.circle(s, (255, 245, 190), (P(x), P(y)), max(2, P(21 * k)), max(1, P(1.5 * k)))
    if blit_tf(s, f"fish/swim_{key}", x, y, 0.22 * k, flip=d > 0, angle=math.sin(t * 3) * 4, pivot="center"):
        return                               # 3.45: своя картинка fish/swim_<вид> (смотрит влево) или лист fish/swim_sheet
    back, belly, fin, mark = FISH_LOOKS.get(key, FISH_LOOKS["roach"])
    m = -d                                   # +1 — как в draw_fish (голова слева)
    w = math.sin(t * 6) * 2.5 * k            # виляет хвостом
    if glow:                                 # взрослая — можно продавать
        pygame.draw.circle(s, (255, 245, 190), (P(x), P(y)), max(2, P(19 * k)), max(1, P(1.5 * k)))
    tail = [(x + m * 11 * k, y), (x + m * 20 * k, y - 8 * k + w), (x + m * 19 * k, y + 8 * k + w)]
    poly(s, fin, tail, 2)
    poly(s, fin, [(x - m * 2 * k, y - 8 * k), (x + m * 6 * k, y - 13 * k), (x + m * 8 * k, y - 6 * k)], 2)
    ellipse(s, back, x, y, 26 * k, 17 * k)
    ellipse(s, belly, x - m * 1 * k, y + 3 * k, 20 * k, 8 * k, 0)
    if mark == "stripes":
        for dx in (-3, 2, 7):
            pygame.draw.line(s, (70, 100, 50), (P(x + m * dx * k), P(y - 7 * k)), (P(x + m * dx * k), P(y + 2 * k)),
                             max(1, P(2 * k)))
    elif mark == "spots":
        for dx, dy in ((-2, -4), (4, -3), (7, 0), (1, 1)):
            pygame.draw.circle(s, (60, 80, 70), (P(x + m * dx * k), P(y + dy * k)), max(1, P(1.2 * k)))
    elif mark == "scales":
        for dx in (-1, 4, 9):
            pygame.draw.circle(s, (140, 100, 50), (P(x + m * dx * k), P(y - 1 * k)), max(1, P(2.6 * k)), 1)
    elif mark == "koi":
        for dx, dy, r in ((-3, -3, 4), (6, 1, 3.5)):
            pygame.draw.circle(s, (235, 80, 50), (P(x + m * dx * k), P(y + dy * k)), max(1, P(r * k)))
    elif mark == "crown":
        cx = x - m * 2 * k
        poly(s, (255, 225, 90), [(cx - 4 * k, y - 7 * k), (cx - 3 * k, y - 13 * k), (cx, y - 9 * k),
                                 (cx + 3 * k, y - 14 * k), (cx + 5 * k, y - 8 * k)], 1)
    face(s, x - m * 6 * k, y - 1 * k, k * 0.75)


def draw_roe(s, x, y, k, t, ripe):
    """3.38: икра — гроздь оранжевых икринок, чуть покачивается; ripe 0..1 — скоро малёк (внутри темнеют глазки)."""
    sway = math.sin(t * 1.3 + x * 0.05) * 2 * k
    for n, (dx, dy) in enumerate(((0, 0), (-5, 3), (5, 3), (-2, 7), (3, -4), (-6, -3), (7, -2))):
        cx, cy = x + dx * k + sway * (dy + 8) / 15, y + dy * k
        pygame.draw.circle(s, (230, 120, 60), (P(cx), P(cy)), max(2, P(3.6 * k)))
        pygame.draw.circle(s, (255, 190, 120), (P(cx), P(cy)), max(1, P(2.6 * k)))
        if ripe > 0.5:
            pygame.draw.circle(s, OUT, (P(cx + 0.6 * k), P(cy)), max(1, P(0.9 * k)))


# 3.38.1: лодка рыботорговца (решение пользователя 26.11: лодка вместо повозки) — 3 уровня, нос влево.
BOAT_LOOKS = [   # длина, высота борта, корпус, кромка, мачта, парус
    (150, 24, (132, 92, 60), (170, 125, 85), 0, None),
    (205, 30, (118, 84, 58), (160, 118, 80), 80, (225, 215, 190)),
    (245, 34, (60, 92, 150), (232, 192, 72), 112, (245, 238, 215)),
]


def draw_boat(s, x, y, tier, cargo=False, bob=0.0, t=0.0):
    """Лодка рыботорговца: (x, y) — вода у борта (линия земли машины). Картинки vehicles/boat_<уровень> нет — кодом."""
    L, hh, hull, rim, mast, sail = BOAT_LOOKS[max(0, min(2, tier))]
    wy = y - 6                                   # линия воды
    for n, (dx, w) in enumerate(((-L * 0.45, 40), (L * 0.1, 60), (L * 0.55, 36))):   # блики волн у борта
        ox = 6 * math.sin(t * 1.3 + n * 2)
        pygame.draw.line(s, (205, 228, 240), (P(x + dx - w / 2 + ox), P(wy + 6 + n % 2 * 3)),
                         (P(x + dx + w / 2 + ox), P(wy + 6 + n % 2 * 3)), 2)
    y = wy - bob
    bow, stern = x - L / 2, x + L / 2
    body = []                                    # корпус: прямая кромка, круглое днище, нос задран
    for n in range(13):
        u = n / 12
        body.append((stern - (stern - bow + 14) * u, y - hh + (-8) * u ** 2))
    for n in range(13):
        u = 1 - n / 12                           # обратно по днищу: от носа к корме
        bx = stern - 6 - (stern - 6 - bow + 14) * u
        by = y + 7 - (hh + 15) * u ** 4 - 4 * math.sin(math.pi * u) * 0
        body.append((bx, by))
    if mast:                                     # мачта и парус — позади груза
        mx = x + L * 0.05
        pygame.draw.line(s, OUT, (P(mx), P(y - hh)), (P(mx), P(y - hh - mast)), max(3, P(6)))
        pygame.draw.line(s, (120, 85, 55), (P(mx), P(y - hh)), (P(mx), P(y - hh - mast)), max(2, P(4)))
        if tier == 1:                            # баркас: парус свёрнут на рее
            pygame.draw.line(s, (110, 80, 52), (P(mx - 46), P(y - hh - mast + 22)), (P(mx + 46), P(y - hh - mast + 22)), 4)
            ellipse(s, sail, mx, y - hh - mast + 22, 92, 14)
        else:                                    # королевский: большой парус с полосой и флажок
            billow = 6 * math.sin(t * 1.5)
            top, bot = y - hh - mast + 14, y - hh - 18
            pts = [(mx - 58, top), (mx + 58, top), (mx + 64 + billow, bot), (mx - 52 + billow, bot)]
            poly(s, sail, pts, 3)
            poly(s, (70, 105, 170), [(mx - 56, top + (bot - top) * 0.42), (mx + 60, top + (bot - top) * 0.42),
                                     (mx + 62 + billow * 0.7, top + (bot - top) * 0.58),
                                     (mx - 54 + billow * 0.7, top + (bot - top) * 0.58)], 0)
            cy = top + (bot - top) * 0.25
            poly(s, (232, 192, 72), [(mx - 12, cy + 8), (mx - 12, cy - 4), (mx - 6, cy + 2), (mx, cy - 8),
                                     (mx + 6, cy + 2), (mx + 12, cy - 4), (mx + 12, cy + 8)], 2)   # корона
            wv = 4 * math.sin(t * 6)
            poly(s, (215, 70, 60), [(mx, y - hh - mast), (mx + 30, y - hh - mast + 5 + wv), (mx, y - hh - mast + 12)], 2)
    if cargo:                                    # улов: ящики и рыбьи хвосты над бортом
        for cx in range(-int(L * 0.32), int(L * 0.32) + 1, 30):
            pygame.draw.rect(s, OUT, (P(x + cx - 13), P(y - hh - 16), P(26), P(18)))
            pygame.draw.rect(s, (175, 130, 85), (P(x + cx - 11), P(y - hh - 14), P(22), P(14)))
            poly(s, (170, 190, 205), [(x + cx, y - hh - 16), (x + cx - 6, y - hh - 28), (x + cx + 6, y - hh - 28)], 2)
    elif tier == 0:                              # пустая лодочка: бочка для улова
        ellipse(s, (150, 110, 70), x + 20, y - hh - 6, 24, 26)
        pygame.draw.line(s, (100, 75, 50), (P(x + 8), P(y - hh - 6)), (P(x + 32), P(y - hh - 6)), 2)
    poly(s, hull, body, 3)
    dark = tuple(max(0, c - 35) for c in hull)
    for k in (0.4, 0.72):                        # доски
        pts = [(stern - 4 - (stern - bow) * u, y - hh + (hh + 7) * k - (hh * 0.9) * k * u ** 3 - 6 * u ** 2 * (1 - k))
               for u in [i / 10 for i in range(10)]]
        pygame.draw.lines(s, dark, False, [(P(a), P(b)) for a, b in pts], 2)
    pygame.draw.lines(s, rim, False, [(P(a), P(b + 2)) for a, b in body[:12]], max(2, P(4)))
    if tier == 0:                                # весло
        pygame.draw.line(s, OUT, (P(x + L * 0.25), P(y - hh - 10)), (P(x + L * 0.45), P(y + 14)), max(3, P(5)))
        pygame.draw.line(s, (190, 150, 100), (P(x + L * 0.25), P(y - hh - 10)), (P(x + L * 0.45), P(y + 14)), max(1, P(3)))
