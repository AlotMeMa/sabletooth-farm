# -*- coding: utf-8 -*-
"""3.19: посиделки у камина — рисунки: живой огонь, фон «крупным планом», украшения (кот, котелок, цветы, коврик).

Всё рисуется кодом; свои картинки (необязательно) — assets/backgrounds/fireside.png и assets/decor/<имя>.png.
"""
import math
import random

import pygame

from .config import W, H
from .art import OUT, ellipse, poly, blit_light, blit_sprite, blit_tf, has_sprite
from .particles import draw_shadow
from . import hd

# Разметка сцены у камина (в координатах экрана 1000×640). Свой фон backgrounds/fireside —
# поправь числа в assets/backgrounds/fireside.json (те же ключи).
FIRESIDE_LAYOUT = dict(
    crop=[103, 322, 250, 160],    # какой кусок зала таверны увеличить, если своего фона нет (x, y, ширина, высота)
    fire=[478, 498],              # низ огня (середина углей)
    fire_w=150, fire_h=190,       # ширина и высота пламени
    kettle=[482, 352],            # котелок: низ по центру (языки огня лижут дно)
    chain_top=150,                # где висит цепь котелка
    rug=[440, 566],               # коврик: центр
    cat=[392, 566],               # кот: низ по центру
    flowers=[612, 150],           # кувшин с цветами на каминной полке: низ по центру
)

def _ell(s, col, rect, ow=2):
    """Эллипс по прямоугольнику (x, y, w, h) с обводкой ow (0 — без)."""
    x, y, w, h = rect
    ellipse(s, col, x + w / 2, y + h / 2, w, h, ow)


FLAME_LAYERS = (            # (языков, высота, ширина, цвет) — от внешнего тёмного к белому ядру
    (5, 1.0, 1.0, (206, 66, 26)),
    (4, 0.84, 0.8, (244, 128, 36)),
    (3, 0.64, 0.58, (255, 196, 74)),
    (2, 0.42, 0.34, (255, 240, 182)),
)


def draw_flames(s, x, y, w, h, t, power=1.0):
    """Живое пламя: языки качаются, растут и опадают каждый сам по себе. (x, y) — низ огня по центру."""
    for li, (n, hk, wk, col) in enumerate(FLAME_LAYERS):
        tw = w * wk / n * 1.3
        for i in range(n):
            off = ((i - (n - 1) / 2) / max(1, n - 1)) * w * wk * 0.62 if n > 1 else 0.0
            seed = li * 7.31 + i * 2.17
            edge = 1.0 - 0.38 * abs(off) / (w * 0.5 + 1)
            hh = h * hk * power * edge * (0.72 + 0.18 * math.sin(t * 3.1 + seed) + 0.1 * math.sin(t * 7.7 + seed * 1.7))
            sway = math.sin(t * 2.2 + seed) * tw * 0.35 + math.sin(t * 5.3 + seed * 0.7) * tw * 0.12
            left, right = [], []
            for j in range(12):
                u = j / 11
                hw = tw * 0.5 * (1 - u) ** 0.85 * (0.78 + 0.22 * min(1.0, u * 4))
                cx = x + off + sway * u ** 1.6 + math.sin(t * 9 + seed + u * 5) * tw * 0.07 * u
                yy = y - u * hh
                left.append((cx - hw, yy))
                right.append((cx + hw, yy))
            bottom = [(x + off + tw * 0.32, y + tw * 0.12), (x + off, y + tw * 0.18), (x + off - tw * 0.32, y + tw * 0.12)]
            pygame.draw.polygon(s, col, left + right[::-1] + bottom)


def draw_coals(s, x, y, w, t):
    """Угли под огнём: тёмная горка с мерцающими красными точками."""
    _ell(s, (60, 28, 18), (x - w * 0.55, y - 10, w * 1.1, 24), 0)
    rnd = random.Random(3)
    for i in range(16):
        cx = x + rnd.uniform(-0.48, 0.48) * w
        cy = y + rnd.uniform(-4, 8)
        k = 0.5 + 0.5 * math.sin(t * rnd.uniform(1.5, 3.5) + i)
        col = (255, int(70 + 110 * k), int(20 + 30 * k))
        pygame.draw.circle(s, col, (int(cx), int(cy)), 2 + int(rnd.random() * 2.5))


def draw_logs(s, x, y, w):
    """Два перекрещенных полена перед огнём (передний план)."""
    for ang, dx in ((-0.16, -0.12), (0.2, 0.14)):
        cx, cy = x + dx * w, y + 6
        lw, lh = w * 0.62, 15
        ca, sa = math.cos(ang), math.sin(ang)
        pts = [(-lw / 2, -lh / 2), (lw / 2, -lh / 2), (lw / 2, lh / 2), (-lw / 2, lh / 2)]
        pts = [(cx + px * ca - py * sa, cy + px * sa + py * ca) for px, py in pts]
        poly(s, (104, 64, 38), pts, 2)
        for end in (-1, 1):                      # торцы: годовые кольца и тлеющая кромка
            ex, ey = cx + end * lw / 2 * ca, cy + end * lw / 2 * sa
            _ell(s, (196, 140, 86), (ex - 5, ey - lh / 2, 10, lh), 2)
            pygame.draw.circle(s, (255, 120, 40), (int(ex), int(ey)), 2)


def draw_cat(s, x, y, k, t, twitch=0.0, purr=0.0):
    """Рыжий кот спит клубком. (x, y) — низ по центру. twitch — дёрнуть ухом (0..1), purr — мурчит (дышит чаще)."""
    if blit_tf(s, "decor/cat", x, y, k * 0.5, sy=1 + 0.03 * math.sin(t * (2.6 if purr else 1.6))):
        return
    br = 1 + 0.05 * math.sin(t * (2.6 if purr else 1.6))
    bw, bh = 46 * k, 22 * k * br
    draw_shadow(s, x, y, bw * 1.1, 10 * k, 80)
    fur, dark = (228, 138, 58), (184, 96, 38)
    _ell(s, fur, (x - bw / 2, y - bh, bw, bh), 2)
    for i in range(3):                          # полоски на спине
        cx = x - bw * 0.22 + i * bw * 0.16
        pygame.draw.arc(s, dark, (int(cx - 6 * k), int(y - bh + 1), int(12 * k), int(10 * k)), 0.4, 2.7, max(1, int(2 * k)))
    # хвост обвивает лапы спереди
    wag = math.sin(t * 0.9) * 2 * k
    pts = [(x - bw * 0.46, y - 6 * k), (x - bw * 0.36, y - 1 * k), (x - bw * 0.1, y + 1 * k),
           (x + bw * 0.16, y - 1 * k), (x + bw * 0.3 + wag, y - 4 * k)]
    pts = [(int(px), int(py)) for px, py in pts]
    pygame.draw.lines(s, OUT, False, pts, max(3, int(8 * k)))
    pygame.draw.lines(s, fur, False, pts, max(2, int(5 * k)))
    # голова на лапах
    hx, hy, hr = x + bw * 0.34, y - bh * 0.5, 11 * k
    ear = twitch * 3 * k
    for ex in (-1, 1):
        tip = (hx + ex * 6 * k, hy - hr - 6 * k - (ear if ex < 0 else 0))
        poly(s, fur, [(hx + ex * 2 * k, hy - hr * 0.7), tip, (hx + ex * 10 * k, hy - hr * 0.35)], 2)
    pygame.draw.circle(s, OUT, (int(hx), int(hy)), int(hr) + 2)
    pygame.draw.circle(s, fur, (int(hx), int(hy)), int(hr))
    for ex in (-1, 1):                          # закрытые глаза — дужки
        pygame.draw.arc(s, OUT, (int(hx + ex * 4.5 * k - 3 * k), int(hy - 3 * k), int(6 * k), int(5 * k)),
                        3.4, 6.0, max(1, int(1.6 * k)))
    pygame.draw.circle(s, (240, 140, 150), (int(hx), int(hy + 3 * k)), max(1, int(1.6 * k)))


def draw_kettle(s, x, y, k, t, top=None, boil=1.0):
    """Чугунный котелок на цепи. (x, y) — низ по центру; top — докуда тянется цепь. Крышка подпрыгивает."""
    if top is not None:
        for yy in range(int(top), int(y - 40 * k), max(4, int(8 * k))):      # цепь — звенья
            _ell(s, (70, 66, 64), (x - 2.5 * k, yy, 5 * k, 7 * k), 1)
    if blit_sprite(s, "decor/kettle", x, y, k * 0.5, "midbottom"):
        return
    w, h = 54 * k, 40 * k
    pygame.draw.arc(s, OUT, (int(x - w * 0.42), int(y - h - 18 * k), int(w * 0.84), int(34 * k)), 0.2, 2.94,
                    max(2, int(3 * k)))                                       # дужка
    _ell(s, (52, 50, 54), (x - w / 2, y - h, w, h), 2)
    _ell(s, (96, 92, 98), (x - w * 0.36, y - h * 0.82, w * 0.22, h * 0.3), 0)   # блик
    hop = 2.5 * k * max(0.0, math.sin(t * 8.5)) ** 8 * boil
    _ell(s, (70, 68, 72), (x - w * 0.44, y - h - 5 * k - hop, w * 0.88, 11 * k), 2)   # крышка
    pygame.draw.circle(s, OUT, (int(x), int(y - h - 6 * k - hop)), max(2, int(3 * k)))
    for ex in (-1, 1):                                                           # ножки-ушки
        pygame.draw.circle(s, (40, 38, 42), (int(x + ex * w * 0.5), int(y - h * 0.55)), max(2, int(3 * k)))


def draw_flowers(s, x, y, k, t):
    """Глиняный кувшин с полевыми цветами. (x, y) — низ по центру."""
    if blit_tf(s, "decor/flowers", x, y, k * 0.5, angle=1.2 * math.sin(t * 0.8)):
        return
    heads = ((-9, -42, (232, 72, 70)), (0, -50, (250, 214, 70)), (9, -40, (120, 150, 235)),
             (-4, -36, (246, 244, 236)), (5, -46, (232, 110, 160)))
    for n, (dx, dy, col) in enumerate(heads):
        sw = math.sin(t * 1.1 + n * 1.3) * 1.5
        top = (x + (dx + sw) * k, y + dy * k)
        pygame.draw.line(s, (70, 130, 60), (int(x + dx * 0.3 * k), int(y - 20 * k)), (int(top[0]), int(top[1])),
                         max(1, int(2 * k)))
        pygame.draw.circle(s, OUT, (int(top[0]), int(top[1])), int(5 * k) + 1)
        pygame.draw.circle(s, col, (int(top[0]), int(top[1])), int(5 * k))
        pygame.draw.circle(s, (250, 200, 80) if col[2] > 200 else (255, 240, 180), (int(top[0]), int(top[1])),
                           max(1, int(1.6 * k)))
    poly(s, (176, 104, 66), [(x - 7 * k, y - 24 * k), (x + 7 * k, y - 24 * k), (x + 11 * k, y - 10 * k),
                             (x + 8 * k, y), (x - 8 * k, y), (x - 11 * k, y - 10 * k)], 2)
    pygame.draw.line(s, (210, 150, 100), (int(x - 6 * k), int(y - 14 * k)), (int(x + 6 * k), int(y - 14 * k)),
                     max(1, int(2 * k)))


def draw_rug(s, x, y, k, flat=0.21):
    """Тканый круглый коврик на полу. (x, y) — центр; flat — насколько сплющен (вид сбоку)."""
    if blit_sprite(s, "decor/rug", x, y, k * 0.5, "center"):
        return
    w = 300 * k
    h = w * flat
    draw_shadow(s, x, y + 4 * k, w * 1.04, h * 1.1, 70)
    for n, (col, f) in enumerate((((132, 50, 42), 1.0), ((190, 142, 76), 0.84), ((148, 62, 46), 0.7),
                                   ((84, 104, 130), 0.52), ((198, 164, 108), 0.36))):
        _ell(s, col, (x - w * f / 2, y - h * f / 2, w * f, h * f), 2 if n == 0 else 0)


def build_fireside_background(tavern_bg, layout):
    """Фон сцены: свой backgrounds/fireside или — без него — кусок зала таверны с камином крупным планом,
    чуть приглушённый, с тёмными краями (свет даёт сам огонь). Возвращает (фон, свой_ли)."""
    bg = hd.Surface((W, H))
    if blit_sprite(bg, "backgrounds/fireside", 0, 0, 1, "topleft"):
        return bg, True
    src = hd.real(tavern_bg)
    k = src.get_width() / W
    cx, cy, cw, ch = layout["crop"]
    box = pygame.Rect(int(cx * k), int(cy * k), int(cw * k), int(ch * k)).clip(src.get_rect())
    phys = (int(round(W * k)), int(round(H * k)))
    big = pygame.transform.smoothscale(src.subsurface(box).copy(), phys)
    big.fill((172, 140, 118, 255), None, pygame.BLEND_RGBA_MULT)                # вечер: теплее и темнее
    # виньетка: маленькая картинка с прозрачностью от центра к краям, растянутая на весь экран
    vw, vh = 40, 26
    vig = pygame.Surface((vw, vh), pygame.SRCALPHA)
    fx, fy = layout["fire"]
    for j in range(vh):
        for i in range(vw):
            dx = (i + 0.5) / vw - fx / W
            dy = ((j + 0.5) / vh - (fy - 120) / H) * 1.25
            d = math.hypot(dx, dy)
            vig.set_at((i, j), (14, 6, 2, int(max(0.0, min(1.0, (d - 0.18) * 1.7)) ** 1.3 * 225)))
    big.blit(pygame.transform.smoothscale(vig, phys), (0, 0))
    return hd.wrap(big), False
