# -*- coding: utf-8 -*-
"""3.33: новые призы стойки — рисунки кодом (свои картинки подставляются по именам, если есть):

    decor/wreath, decor/lantern, decor/rocking_chair, decor/own_mug — украшения;
    characters/dog, characters/owl — персонажи;
    светлячки и шлейфы «Листопад» / «Мыльные пузыри» — только кодом.
Всё рисуется в координатах экрана 1000×640; k — масштаб.
"""
import math

import pygame

from .art import OUT, ellipse, poly, blit_light, blit_sprite, blit_tf
from .particles import draw_shadow

WHEAT = (232, 186, 92)
WHEAT_DARK = (196, 146, 62)
RIBBON = (205, 70, 60)


def draw_wreath(s, x, y, k=1.0, t=0.0):
    """Венок из колосьев с красной лентой; (x, y) — центр. Чуть покачивается на гвозде."""
    if blit_tf(s, "decor/wreath", x, y, k * 0.5, angle=1.5 * math.sin(t * 0.7), pivot="center"):
        return
    r = 30 * k
    for i in range(20):
        a = i / 20 * math.tau + 0.15 * math.sin(t * 0.7)
        cx, cy = x + math.cos(a) * r, y + math.sin(a) * r
        ang = a + math.pi / 2
        dx, dy = math.cos(ang) * 9 * k, math.sin(ang) * 9 * k
        poly(s, WHEAT if i % 2 else WHEAT_DARK,
             [(cx - dx, cy - dy), (cx - dy * 0.4, cy + dx * 0.4), (cx + dx, cy + dy), (cx + dy * 0.4, cy - dx * 0.4)], 2)
    pygame.draw.circle(s, OUT, (int(x), int(y - r - 6 * k)), max(2, int(3 * k)))          # гвоздь
    poly(s, RIBBON, [(x - 10 * k, y + r - 4 * k), (x, y + r + 4 * k), (x + 10 * k, y + r - 4 * k),
                     (x + 4 * k, y + r + 18 * k), (x, y + r + 8 * k), (x - 4 * k, y + r + 18 * k)], 2)


def draw_lantern(s, x, y, k=1.0, t=0.0, ph=0.0):
    """Фонарь на верёвке; (x, y) — где верёвка крепится к балке. Мягко качается и светит."""
    sway = 4 * math.sin(t * 0.9 + ph)
    length = 34 * k
    lx, ly = x + sway, y + length
    flick = 0.8 + 0.2 * math.sin(t * 9 + ph * 3) * math.sin(t * 5.3 + ph)
    blit_light(s, lx, ly + 10 * k, 70 * k, (255, 196, 110), 110 * flick, 0.0)
    pygame.draw.line(s, (60, 45, 35), (int(x), int(y)), (int(lx), int(ly)), 2)
    if blit_tf(s, "decor/lantern", lx, ly, k * 0.5, angle=-sway * 1.5, pivot="midtop"):
        return
    body = pygame.Rect(0, 0, int(18 * k), int(22 * k))
    body.midtop = (int(lx), int(ly + 4 * k))
    pygame.draw.rect(s, OUT, body.inflate(4, 4), border_radius=int(4 * k))
    pygame.draw.rect(s, (255, 214, 120), body, border_radius=int(3 * k))
    pygame.draw.rect(s, (255, 245, 200), body.inflate(-int(8 * k), -int(8 * k)), border_radius=int(2 * k))
    poly(s, (90, 70, 55), [(lx - 12 * k, ly + 5 * k), (lx, ly - 2 * k), (lx + 12 * k, ly + 5 * k)], 2)
    pygame.draw.rect(s, (90, 70, 55), (int(lx - 10 * k), body.bottom, int(20 * k), max(3, int(4 * k))))


def draw_rocking_chair(s, x, y, k=1.0, t=0.0):
    """Кресло-качалка сбоку; (x, y) — середина полозьев на полу. Само покачивается."""
    a = 5 * math.sin(t * 0.8)
    draw_shadow(s, x, y + 2, 120 * k, 16, 70)
    if blit_tf(s, "decor/rocking_chair", x, y, k * 0.5, angle=a, pivot="midbottom"):
        return
    rad = math.radians(a)

    def rot(px, py):
        return (x + px * math.cos(rad) - py * math.sin(rad), y + px * math.sin(rad) + py * math.cos(rad))

    wood, dark = (150, 98, 58), (118, 74, 44)
    rocker = pygame.Rect(x - 62 * k, y - 46 * k + 2 * k * math.sin(rad * 6), 124 * k, 46 * k)    # низ дуги — на полу
    pygame.draw.arc(s, OUT, rocker, math.pi * 1.1, math.pi * 1.9, max(4, int(9 * k)))
    pygame.draw.arc(s, dark, rocker, math.pi * 1.1, math.pi * 1.9, max(3, int(6 * k)))
    for p0, p1 in (((-30, -6), (-26, -50)), ((26, -6), (22, -50)), ((-26, -50), (26, -50)),
                   ((22, -50), (36, -118)), ((-26, -50), (-30, -78)), ((36, -118), (30, -122))):
        pygame.draw.line(s, OUT, rot(*[v * k for v in p0]), rot(*[v * k for v in p1]), max(5, int(11 * k)))
        pygame.draw.line(s, wood, rot(*[v * k for v in p0]), rot(*[v * k for v in p1]), max(3, int(7 * k)))
    for i in range(4):          # перекладины спинки
        u = 0.2 + i * 0.2
        p0 = (22 + 14 * u, -50 - 68 * u)
        pygame.draw.line(s, dark, rot(p0[0] * k, p0[1] * k), rot((p0[0] - 34) * k, (p0[1] + 4) * k), max(2, int(4 * k)))
    poly(s, (196, 80, 70), [rot(-26 * k, -56 * k), rot(24 * k, -56 * k), rot(26 * k, -48 * k), rot(-28 * k, -48 * k)], 2)


def draw_dog(s, x, y, k=1.0, t=0.0, wag=0.0, awake=False):
    """Пёс спит, свернувшись; (x, y) — низ по центру. wag 0..1 — виляет хвостом (после ласки)."""
    breath = math.sin(t * 1.7)
    draw_shadow(s, x, y, 120 * k, 14, 70)
    if blit_tf(s, "characters/dog", x, y, k * 0.5, sy=1 + 0.03 * breath, pivot="midbottom"):
        return
    fur, dark, light = (176, 120, 70), (140, 90, 52), (226, 190, 150)
    tail = math.sin(t * 14) * 0.6 * wag
    tx, ty = x + 52 * k, y - 14 * k
    ex, ey = tx + math.cos(-0.8 + tail) * 26 * k, ty + math.sin(-0.8 + tail) * 26 * k
    pygame.draw.line(s, OUT, (tx, ty), (ex, ey), max(6, int(12 * k)))
    pygame.draw.line(s, fur, (tx, ty), (ex, ey), max(4, int(8 * k)))
    ellipse(s, fur, x + 6 * k, y - 20 * k, 100 * k, (40 + 2 * breath) * k)               # тело
    ellipse(s, light, x + 4 * k, y - 10 * k, 60 * k, 14 * k, 0)
    hx, hy = x - 40 * k, y - 22 * k
    ellipse(s, fur, hx, hy, 42 * k, 32 * k)                                               # голова
    ellipse(s, light, hx - 14 * k, hy + 6 * k, 22 * k, 16 * k)                            # морда
    pygame.draw.circle(s, OUT, (int(hx - 24 * k), int(hy + 3 * k)), max(2, int(4 * k)))   # нос
    ear = 0.25 * math.sin(t * 0.6) * (1 if awake else 0.3)
    ellipse(s, dark, hx + 8 * k, hy + 2 * k + ear * 6 * k, 14 * k, 26 * k)                # висячее ухо
    if awake:
        pygame.draw.circle(s, OUT, (int(hx - 8 * k), int(hy - 3 * k)), max(2, int(3 * k)))
    else:
        pygame.draw.arc(s, OUT, pygame.Rect(hx - 13 * k, hy - 6 * k, 10 * k, 6 * k), math.pi, 2 * math.pi, 2)


def draw_owl(s, x, y, k=1.0, t=0.0, hoot=0.0):
    """Сова на насесте; (x, y) — лапы. Моргает, иногда поворачивает голову; hoot — «Уху!» (0..1)."""
    blink = (t % 4.3) < 0.14
    turn = 6 * math.sin(t * 0.35) if (t % 11) > 7 else 0.0
    bob = 2 * hoot * math.sin(t * 20)
    if blit_tf(s, "characters/owl", x, y - bob, k * 0.5, sy=0.98 if blink else 1.0, angle=turn * 0.5,
               pivot="midbottom"):
        return
    body, belly, dark = (150, 112, 78), (226, 200, 160), (110, 80, 54)
    ellipse(s, body, x, y - 22 * k - bob, 36 * k, 42 * k)
    ellipse(s, belly, x, y - 18 * k - bob, 22 * k, 28 * k, 0)
    hx, hy = x + turn, y - 46 * k - bob
    ellipse(s, body, hx, hy, 36 * k, 28 * k)
    for sx in (-1, 1):
        poly(s, dark, [(hx + sx * 16 * k, hy - 8 * k), (hx + sx * 13 * k, hy - 20 * k), (hx + sx * 6 * k, hy - 10 * k)], 2)
        ex = hx + sx * 8 * k
        pygame.draw.circle(s, OUT, (int(ex), int(hy)), int(8 * k) + 1)
        pygame.draw.circle(s, (250, 240, 210), (int(ex), int(hy)), int(8 * k))
        if blink:
            pygame.draw.line(s, OUT, (ex - 6 * k, hy), (ex + 6 * k, hy), 2)
        else:
            pygame.draw.circle(s, (245, 170, 40), (int(ex), int(hy)), int(5 * k))
            pygame.draw.circle(s, OUT, (int(ex), int(hy)), max(1, int(2.5 * k)))
    poly(s, (240, 170, 60), [(hx - 3 * k, hy + 6 * k), (hx + 3 * k, hy + 6 * k), (hx, hy + 12 * k)], 1)
    for sx in (-1, 1):
        pygame.draw.line(s, (240, 170, 60), (x + sx * 6 * k, y - 4 * k), (x + sx * 7 * k, y), max(2, int(3 * k)))


def draw_own_mug(s, x, y, k=1.0, t=0.0):
    """Своя кружка с сердечком; (x, y) — дно по центру."""
    if blit_sprite(s, "decor/own_mug", x, y, k * 0.5, "midbottom"):
        return
    body = pygame.Rect(0, 0, int(20 * k), int(24 * k))
    body.midbottom = (int(x), int(y))
    pygame.draw.circle(s, OUT, (body.right + int(3 * k), body.centery), int(7 * k) + 1, max(2, int(4 * k)))
    pygame.draw.circle(s, (225, 190, 110), (body.right + int(3 * k), body.centery), int(7 * k), max(1, int(2 * k)))
    pygame.draw.rect(s, OUT, body.inflate(4, 4), border_radius=3)
    pygame.draw.rect(s, (235, 200, 120), body, border_radius=3)
    pygame.draw.rect(s, (250, 248, 238), (body.x, body.y - int(4 * k), body.w, int(6 * k)), border_radius=3)
    hx, hy = body.centerx, body.centery + 2 * k
    for dx in (-3, 3):
        pygame.draw.circle(s, (215, 60, 70), (int(hx + dx * k), int(hy - 2 * k)), max(2, int(3.4 * k)))
    poly(s, (215, 60, 70), [(hx - 6.2 * k, hy - 1 * k), (hx + 6.2 * k, hy - 1 * k), (hx, hy + 6 * k)], 0)


def draw_fireflies(s, t, area, n=10, seed=1):
    """Светлячки порхают в прямоугольнике area (x0, y0, x1, y1): мерцают и плавают по своим «восьмёркам»."""
    x0, y0, x1, y1 = area
    for i in range(n):
        ph = seed * 7.13 + i * 2.39
        u = 0.5 + 0.45 * math.sin(t * (0.11 + 0.013 * (i % 5)) + ph)
        v = 0.5 + 0.45 * math.sin(t * (0.17 + 0.011 * (i % 3)) + ph * 1.7)
        x = x0 + (x1 - x0) * u + 12 * math.sin(t * 1.3 + ph)
        y = y0 + (y1 - y0) * v + 8 * math.sin(t * 1.7 + ph * 2)
        glow = max(0.0, math.sin(t * (0.9 + 0.1 * (i % 4)) + ph * 3))
        if glow < 0.05:
            continue
        blit_light(s, x, y, 26, (200, 255, 120), 150 * glow, 0.0)
        pygame.draw.circle(s, (240, 255, 190), (int(x), int(y)), 2)


TRAIL_LEAVES = ((120, 180, 70), (230, 160, 50), (210, 100, 50), (170, 200, 80))


def trail_leaf(layer, mx, my, k, col, ang):
    """Листик для шлейфа «Листопад»: (mx, my) — центр, k 0..1 — свежесть."""
    r = 5 + 7 * k
    c, sn = math.cos(ang), math.sin(ang)
    pts = [(mx + c * r, my + sn * r), (mx - sn * r * 0.45, my + c * r * 0.45),
           (mx - c * r, my - sn * r), (mx + sn * r * 0.45, my - c * r * 0.45)]
    pygame.draw.polygon(layer, col + (int(235 * k),), pts)
    pygame.draw.line(layer, (90, 70, 40, int(160 * k)), pts[0], pts[2], 1)      # прожилка


def trail_bubble(layer, mx, my, k, n):
    """Пузырёк для шлейфа «Мыльные пузыри»."""
    r = int(5 + 7 * (1 - k) + (n % 3))
    pygame.draw.circle(layer, (210, 240, 255, int(60 * k)), (int(mx), int(my)), r)
    pygame.draw.circle(layer, (120, 190, 240, int(220 * k)), (int(mx), int(my)), r, 2)
    pygame.draw.circle(layer, (255, 255, 255, int(200 * k)), (int(mx - r * 0.35), int(my - r * 0.35)), max(1, r // 4))
