# -*- coding: utf-8 -*-
"""3.47: украшения и эффекты призовой стойки для глав 3–5 (зима, деревня, драконы).

Каждое украшение сначала ищет свою картинку decor/<id> (промпт — в доке промптов), без неё рисуется кодом.
Эффекты зала (снегопад, медузы, огненные бабочки) и кусочки шлейфов курсора — только кодом.
"""
import math

import pygame

from .art import OUT, ellipse, poly, blit_light, blit_sprite


def _sprite(s, pid, x, y, k):
    return blit_sprite(s, f"decor/{pid}", x, y, k, "midbottom")


# ---------------------------------------------------------------- зима
def draw_snow_globe(s, x, y, k=1.0, t=0.0):
    if _sprite(s, "snow_globe", x, y, k):
        return
    poly(s, (120, 80, 50), [(x - 16 * k, y), (x + 16 * k, y), (x + 12 * k, y - 8 * k), (x - 12 * k, y - 8 * k)], 2)
    cx, cy, r = x, y - 22 * k, 16 * k
    pygame.draw.circle(s, OUT, (int(cx), int(cy)), int(r) + 2)
    pygame.draw.circle(s, (190, 225, 245), (int(cx), int(cy)), int(r))
    poly(s, (200, 90, 70), [(cx - 6 * k, cy + 10 * k), (cx + 6 * k, cy + 10 * k), (cx + 6 * k, cy + 2 * k),
                            (cx, cy - 4 * k), (cx - 6 * k, cy + 2 * k)], 1)
    for i in range(7):                                # снег кружит внутри
        a = t * (0.8 + 0.1 * i) + i * 0.9
        px, py = cx + math.cos(a) * r * 0.6, cy + ((t * 0.3 + i * 0.37) % 1.0 - 0.5) * r * 1.4
        pygame.draw.circle(s, (255, 255, 255), (int(px), int(py)), max(1, int(1.5 * k)))
    pygame.draw.circle(s, (255, 255, 255), (int(cx - r * 0.45), int(cy - r * 0.45)), max(1, int(3 * k)))


def draw_antlers(s, x, y, k=1.0, t=0.0):
    if _sprite(s, "antlers", x, y, k):
        return
    ellipse(s, (130, 85, 50), x, y - 8 * k, 26 * k, 18 * k)                # дощечка
    for side in (-1, 1):
        pts = [(x + side * 6 * k, y - 12 * k), (x + side * 22 * k, y - 34 * k), (x + side * 34 * k, y - 46 * k)]
        for a, b in zip(pts, pts[1:]):
            pygame.draw.line(s, OUT, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), max(3, int(7 * k)))
            pygame.draw.line(s, (225, 205, 170), (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), max(2, int(4 * k)))
        for (bx, by), (ex, ey) in (((x + side * 16 * k, y - 26 * k), (x + side * 10 * k, y - 44 * k)),
                                   ((x + side * 26 * k, y - 38 * k), (x + side * 22 * k, y - 54 * k))):
            pygame.draw.line(s, OUT, (int(bx), int(by)), (int(ex), int(ey)), max(3, int(6 * k)))
            pygame.draw.line(s, (225, 205, 170), (int(bx), int(by)), (int(ex), int(ey)), max(2, int(3 * k)))


def draw_ice_chandelier(s, x, y, k=1.0, t=0.0):
    """Висит: (x, y) — точка подвеса."""
    if blit_sprite(s, "decor/ice_chandelier", x, y, k, "midtop"):
        return
    pygame.draw.line(s, (70, 60, 55), (int(x), int(y)), (int(x), int(y + 24 * k)), max(1, int(2 * k)))
    ellipse(s, (170, 210, 235), x, y + 30 * k, 60 * k, 12 * k)
    for i in range(7):
        u = (i + 0.5) / 7
        ix = x - 28 * k + 56 * k * u
        ln = (14 + 10 * math.sin(i * 1.7) ** 2) * k
        poly(s, (205, 235, 250), [(ix - 4 * k, y + 32 * k), (ix + 4 * k, y + 32 * k), (ix, y + 32 * k + ln)], 1)
        glow = 0.5 + 0.5 * math.sin(t * 1.6 + i * 1.1)
        blit_light(s, ix, y + 34 * k + ln * 0.6, 18 * k, (170, 220, 255), 60 + 80 * glow, 0.0)


# ---------------------------------------------------------------- рыбацкая деревня
def draw_ship_wheel(s, x, y, k=1.0, t=0.0):
    """Висит на стене: (x, y) — центр."""
    if blit_sprite(s, "decor/ship_wheel", x, y, k, "center"):
        return
    a0 = 0.15 * math.sin(t * 0.4)
    for i in range(8):
        a = a0 + i * math.pi / 4
        ex, ey = x + math.cos(a) * 30 * k, y + math.sin(a) * 30 * k
        pygame.draw.line(s, OUT, (int(x), int(y)), (int(ex), int(ey)), max(3, int(6 * k)))
        pygame.draw.line(s, (165, 110, 60), (int(x), int(y)), (int(ex), int(ey)), max(2, int(4 * k)))
        pygame.draw.circle(s, OUT, (int(ex), int(ey)), int(4 * k) + 1)
        pygame.draw.circle(s, (190, 130, 70), (int(ex), int(ey)), int(4 * k))
    pygame.draw.circle(s, OUT, (int(x), int(y)), int(22 * k) + 2, max(3, int(6 * k)))
    pygame.draw.circle(s, (180, 120, 65), (int(x), int(y)), int(22 * k), max(2, int(4 * k)))
    pygame.draw.circle(s, OUT, (int(x), int(y)), int(6 * k) + 1)
    pygame.draw.circle(s, (210, 170, 90), (int(x), int(y)), int(6 * k))


def draw_goldfish_bowl(s, x, y, k=1.0, t=0.0):
    if _sprite(s, "goldfish_bowl", x, y, k):
        return
    cx, cy, r = x, y - 18 * k, 18 * k
    pygame.draw.circle(s, OUT, (int(cx), int(cy)), int(r) + 2)
    pygame.draw.circle(s, (175, 220, 240), (int(cx), int(cy)), int(r))
    pygame.draw.line(s, (120, 180, 220), (int(cx - r * 0.85), int(cy - r * 0.35)), (int(cx + r * 0.85), int(cy - r * 0.35)), 2)
    fx = cx + math.sin(t * 0.9) * r * 0.45
    d = 1 if math.cos(t * 0.9) > 0 else -1
    ellipse(s, (250, 150, 40), fx, cy + 3 * k, 12 * k, 8 * k)
    poly(s, (250, 120, 40), [(fx - d * 6 * k, cy + 3 * k), (fx - d * 12 * k, cy - 1 * k), (fx - d * 12 * k, cy + 7 * k)], 1)
    pygame.draw.circle(s, (255, 255, 255), (int(cx - r * 0.45), int(cy - r * 0.5)), max(1, int(3 * k)))


def draw_nets(s, xs, y0, t=0.0):
    """Сети с ракушками провисают под балконом между точками xs (как гирлянда)."""
    if blit_sprite(s, "decor/nets", (xs[0] + xs[-1]) / 2, y0 - 4, 1.0, "midtop"):
        return
    shells = ((250, 210, 190), (240, 190, 120), (230, 235, 245))
    n = 0
    for a, b in zip(xs, xs[1:]):
        for row in range(3):
            pts = []
            for i in range(11):
                u = i / 10
                sag = (26 - row * 6) * 4 * u * (1 - u)
                pts.append((a + (b - a) * u, y0 + row * 6 + sag))
            pygame.draw.lines(s, (95, 75, 55), False, [(int(px), int(py)) for px, py in pts], 2)
        for i in range(1, 10):
            u = i / 10
            px = a + (b - a) * u
            pygame.draw.line(s, (95, 75, 55), (int(px), int(y0 + 26 * 4 * u * (1 - u))),
                             (int(px), int(y0 + 12 + 14 * 4 * u * (1 - u))), 2)
        for u in (0.3, 0.7):
            px, py = a + (b - a) * u, y0 + 26 * 4 * u * (1 - u) + 4
            col = shells[n % len(shells)]
            poly(s, col, [(px - 6, py), (px + 6, py), (px, py + 9)], 1)
            n += 1


# ---------------------------------------------------------------- горы драконов
def draw_dragon_egg(s, x, y, k=1.0, t=0.0):
    if _sprite(s, "dragon_egg", x, y, k):
        return
    wob = 3 * math.sin(t * 9) if (t % 7.0) < 0.8 else 0.0          # иногда шевелится
    poly(s, (90, 70, 60), [(x - 14 * k, y), (x + 14 * k, y), (x + 10 * k, y - 6 * k), (x - 10 * k, y - 6 * k)], 2)
    blit_light(s, x, y - 22 * k, 40 * k, (255, 140, 60), 90, 0.0)
    egg = pygame.Rect(0, 0, int(26 * k), int(34 * k))
    egg.midbottom = (int(x + wob), int(y - 4 * k))
    pygame.draw.ellipse(s, OUT, egg.inflate(4, 4))
    pygame.draw.ellipse(s, (190, 60, 50), egg)
    for i in range(4):
        cx, cy = egg.x + egg.w * (0.3 + 0.15 * (i % 2)), egg.y + egg.h * (0.25 + 0.18 * i)
        pygame.draw.circle(s, (240, 150, 60), (int(cx + wob), int(cy)), max(1, int(3 * k)))


def draw_dragon_shield(s, x, y, k=1.0, t=0.0):
    """Висит на стене: (x, y) — центр."""
    if blit_sprite(s, "decor/dragon_shield", x, y, k, "center"):
        return
    pts = [(x - 24 * k, y - 26 * k), (x + 24 * k, y - 26 * k), (x + 22 * k, y + 6 * k), (x, y + 30 * k), (x - 22 * k, y + 6 * k)]
    poly(s, (150, 40, 40), pts, 3)
    inner = [(px * 0.78 + x * 0.22, py * 0.78 + y * 0.22) for px, py in pts]
    pygame.draw.lines(s, (230, 190, 80), True, [(int(px), int(py)) for px, py in inner], max(1, int(2 * k)))
    poly(s, (230, 190, 80), [(x - 8 * k, y + 8 * k), (x - 2 * k, y - 14 * k), (x + 10 * k, y - 10 * k), (x + 4 * k, y - 4 * k),
                             (x + 10 * k, y + 6 * k)], 1)          # силуэт дракона


def draw_brazier(s, x, y, k=1.0, t=0.0):
    if _sprite(s, "brazier", x, y, k):
        return
    for dx in (-12, 0, 12):
        pygame.draw.line(s, OUT, (int(x + dx * k * 0.6), int(y - 20 * k)), (int(x + dx * k), int(y)), max(2, int(4 * k)))
    poly(s, (70, 60, 60), [(x - 22 * k, y - 26 * k), (x + 22 * k, y - 26 * k), (x + 14 * k, y - 14 * k), (x - 14 * k, y - 14 * k)], 2)
    blit_light(s, x, y - 34 * k, 70 * k, (255, 140, 50), 130 + 40 * math.sin(t * 7), 0.0)
    for i in range(4):
        h = (14 + 8 * math.sin(t * 8 + i * 1.9)) * k
        bx = x - 12 * k + i * 8 * k
        poly(s, (255, 150 + 20 * (i % 2), 40), [(bx - 5 * k, y - 26 * k), (bx + 5 * k, y - 26 * k), (bx, y - 26 * k - h)], 1)


DECOR_DRAW = {"snow_globe": draw_snow_globe, "antlers": draw_antlers, "ice_chandelier": draw_ice_chandelier,
              "ship_wheel": draw_ship_wheel, "goldfish_bowl": draw_goldfish_bowl,
              "dragon_egg": draw_dragon_egg, "dragon_shield": draw_dragon_shield, "brazier": draw_brazier}


# ---------------------------------------------------------------- эффекты зала
def draw_ambient(s, t, area, kind, n=12, seed=1):
    """Снегопад, медузы или огненные бабочки в прямоугольнике area (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = area
    for i in range(n):
        ph = seed * 5.71 + i * 2.13
        if kind == "snowfall":
            u = (i * 0.618 + 0.03 * math.sin(t * 0.7 + ph)) % 1.0
            v = (t * (0.05 + 0.01 * (i % 4)) + ph * 0.37) % 1.0
            x, y = x0 + (x1 - x0) * u + 10 * math.sin(t + ph), y0 + (y1 - y0) * v
            pygame.draw.circle(s, (250, 252, 255), (int(x), int(y)), 2 + (i % 2))
            continue
        u = 0.5 + 0.45 * math.sin(t * (0.07 + 0.01 * (i % 5)) + ph)
        v = 0.5 + 0.45 * math.sin(t * (0.1 + 0.012 * (i % 3)) + ph * 1.7)
        x, y = x0 + (x1 - x0) * u, y0 + (y1 - y0) * v
        if kind == "jellyfish":
            pulse = 0.5 + 0.5 * math.sin(t * 2.2 + ph)
            blit_light(s, x, y, 34, (255, 130, 200), 90 + 70 * pulse, 0.0)
            r = 7 + 2 * pulse
            pygame.draw.ellipse(s, (255, 170, 220), (int(x - r), int(y - r * 0.7), int(2 * r), int(r * 1.2)))
            for j in (-1, 0, 1):
                tx = x + j * 4
                pygame.draw.line(s, (255, 190, 230), (int(tx), int(y + 3)),
                                 (int(tx + 3 * math.sin(t * 3 + j + ph)), int(y + 14)), 1)
        else:                                          # fire_butterflies
            flap = abs(math.sin(t * 9 + ph))
            blit_light(s, x, y, 26, (255, 150, 50), 120, 0.0)
            w = 7 * (0.3 + 0.7 * flap)
            for side in (-1, 1):
                poly(s, (255, 140 + 40 * (i % 2), 40), [(x, y), (x + side * w, y - 6), (x + side * w * 0.8, y + 4)], 0)
            pygame.draw.line(s, (90, 40, 20), (int(x), int(y - 4)), (int(x), int(y + 4)), 2)


AMBIENT = {"snowfall": "snowfall", "jellyfish": "jellyfish", "fire_butterflies": "fire_butterflies"}


# ---------------------------------------------------------------- шлейфы курсора
def trail_piece(layer, style, mx, my, k, n, now):
    """Кусочек шлейфа: snow — снежинка, starfish — морская звезда, embers — искра. k 0..1 — свежесть."""
    a = int(230 * k)
    if style == "snow":
        r = 3 + 3 * (1 - k)
        ang = n * 0.7 + now * 2
        for i in range(3):
            q = ang + i * math.pi / 3
            dx, dy = math.cos(q) * r, math.sin(q) * r
            pygame.draw.line(layer, (235, 245, 255, a), (int(mx - dx), int(my - dy)), (int(mx + dx), int(my + dy)), 2)
    elif style == "starfish":
        r = 4 + 3 * (1 - k)
        pts = []
        for i in range(10):
            q = n * 0.5 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.45
            pts.append((mx + math.cos(q) * rr, my + math.sin(q) * rr))
        pygame.draw.polygon(layer, (250, 140, 90, a), [(int(px), int(py)) for px, py in pts])
    else:                                              # embers
        r = max(1, int(1 + 3 * k))
        pygame.draw.circle(layer, (255, 200, 80, int(120 * k)), (int(mx), int(my)), r + 3)
        pygame.draw.circle(layer, (255, 120 + (n % 3) * 40, 40, a), (int(mx), int(my)), r)


NOTE_SKIN_COLORS = {"frost_notes": ((190, 235, 255), (150, 210, 255)),
                    "pearl_notes": ((250, 240, 245), (230, 210, 255)),
                    "fire_notes": ((255, 150, 50), (255, 200, 80))}
