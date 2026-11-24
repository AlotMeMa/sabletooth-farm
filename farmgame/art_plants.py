# -*- coding: utf-8 -*-
"""Растения кодом: летние, зимние и средневековые культуры.

Часть art.py (3.17: вынесено без изменений). Снаружи всё берётся как раньше: from .art import ...
"""
import math
import os
import random

import pygame

from . import spritefit
from . import hd
from .config import *  # noqa: F401,F403
from .art_base import *  # noqa: F401,F403


# ---------- растения ----------
def plant_potato(s, x, y, k):
    g = (90, 185, 70)
    leaf(s, x, y - 10 * k, 100, 16 * k, 8 * k, g)
    leaf(s, x, y - 10 * k, 55, 14 * k, 7 * k, g)
    leaf(s, x, y - 10 * k, 140, 14 * k, 7 * k, g)
    ellipse(s, (215, 160, 100), x, y - 5 * k, 26 * k, 18 * k)
    pygame.draw.circle(s, (185, 128, 75), (P(x + 8 * k), P(y - 9 * k)), max(1, P(1.5 * k)))
    pygame.draw.circle(s, (185, 128, 75), (P(x - 9 * k), P(y - 3 * k)), max(1, P(1.3 * k)))
    face(s, x, y - 5 * k, k * 0.9)


def plant_carrot(s, x, y, k, body=(250, 140, 40), stripe=(205, 100, 25), g=(95, 195, 70)):
    for a in (65, 90, 115):
        leaf(s, x, y - 13 * k, a, 18 * k, 6 * k, g)
    poly(s, body, [(x - 10 * k, y - 14 * k), (x + 10 * k, y - 14 * k), (x + 2 * k, y + 5 * k), (x - 2 * k, y + 5 * k)])
    pygame.draw.line(s, stripe, (P(x + 4 * k), P(y - 4 * k)), (P(x + 7 * k), P(y - 4 * k)), 1)
    face(s, x, y - 8 * k, k * 0.8)


def plant_wheat(s, x, y, k, stalk=(190, 150, 60), ear=(242, 200, 90), grain=(200, 155, 60), awns=False, h=28):
    for dx in (-7, 0, 7):
        top = (x + dx * 1.6 * k, y - h * k)
        pygame.draw.line(s, stalk, (P(x + dx * k), P(y)), (P(top[0]), P(top[1])), max(1, P(2 * k)))
        ellipse(s, ear, top[0], top[1] - 6 * k, 9 * k, 19 * k)
        for t in (-1, 1):
            pygame.draw.line(s, grain, (P(top[0]), P(top[1] - 6 * k)), (P(top[0] + t * 4 * k), P(top[1] - 11 * k)), 1)
        if awns:   # усики ячменя
            for t in (-1, 0, 1):
                pygame.draw.line(s, grain, (P(top[0] + t * 2 * k), P(top[1] - 14 * k)), (P(top[0] + t * 6 * k), P(top[1] - 26 * k)), 1)
    leaf(s, x, y, 130, 14 * k, 5 * k, (150, 190, 70))


def plant_corn(s, x, y, k):
    g = (80, 175, 65)
    leaf(s, x, y - 3 * k, 145, 22 * k, 7 * k, g)
    leaf(s, x, y - 3 * k, 35, 22 * k, 7 * k, g)
    pygame.draw.line(s, (70, 150, 55), (P(x), P(y)), (P(x), P(y - 18 * k)), max(1, P(3 * k)))
    ellipse(s, (250, 215, 60), x, y - 28 * k, 13 * k, 28 * k)
    for r in range(3):
        for c in (-1, 1):
            pygame.draw.circle(s, (230, 180, 30), (P(x + c * 3 * k), P(y - 36 * k + r * 5 * k)), max(1, P(1.2 * k)))
    leaf(s, x, y - 14 * k, 108, 20 * k, 8 * k, (120, 205, 85))
    leaf(s, x, y - 14 * k, 72, 20 * k, 8 * k, (120, 205, 85))
    face(s, x, y - 26 * k, k * 0.7)


def plant_tomato(s, x, y, k, bush=(70, 165, 70), fruit=(235, 70, 60), fr=5.5):
    blob(s, bush, [(x - 9 * k, y - 9 * k, 9 * k), (x + 9 * k, y - 9 * k, 9 * k), (x, y - 18 * k, 10 * k), (x, y - 5 * k, 9 * k)])
    for tx, ty in ((-8, -7), (8, -12), (1, -22), (2, -4)):
        cx, cy = x + tx * k, y + ty * k
        pygame.draw.circle(s, OUT, (P(cx), P(cy)), P(fr * k) + 1)
        pygame.draw.circle(s, fruit, (P(cx), P(cy)), max(1, P(fr * k)))
        pygame.draw.circle(s, WHITE, (P(cx - 2 * k), P(cy - 2 * k)), max(1, P(1.2 * k)))
    face(s, x + 2 * k, y - 4 * k, k * 0.5)


def plant_cucumber(s, x, y, k):
    g = (75, 165, 70)
    for a, l in ((60, 18), (120, 18), (90, 15)):
        leaf(s, x, y - 6 * k, a, l * k, 13 * k, g, vein=(50, 120, 50))
    for cx, cy, ang in ((-6, -9, 0), (7, -6, 0)):
        ellipse(s, (60, 150, 60), x + cx * k, y + cy * k, 9 * k, 22 * k)
        for dy in (-6, 0, 6):
            pygame.draw.circle(s, (150, 215, 120), (P(x + cx * k + 2 * k), P(y + (cy + dy) * k)), max(1, P(1.1 * k)))
    pygame.draw.circle(s, OUT, (P(x + 12 * k), P(y - 20 * k)), P(4 * k) + 1)
    pygame.draw.circle(s, (255, 220, 60), (P(x + 12 * k), P(y - 20 * k)), max(1, P(4 * k)))
    face(s, x - 6 * k, y - 11 * k, k * 0.6)


def plant_beet(s, x, y, k):
    for a in (70, 95, 120):
        leaf(s, x, y - 14 * k, a, 21 * k, 10 * k, (60, 150, 70), vein=(190, 40, 90))
    poly(s, (160, 40, 110), [(x - 2 * k, y), (x + 2 * k, y), (x, y + 6 * k)], 1)
    blob(s, (180, 55, 125), [(x, y - 8 * k, 10 * k)])
    face(s, x, y - 8 * k, k * 0.85)


def plant_radish(s, x, y, k, top=(238, 100, 155)):
    for a in (75, 105):
        leaf(s, x, y - 14 * k, a, 18 * k, 9 * k, (130, 210, 90), vein=(80, 150, 60))
    poly(s, (250, 245, 245), [(x - 5 * k, y - 3 * k), (x + 5 * k, y - 3 * k), (x, y + 7 * k)], 1)
    blob(s, top, [(x, y - 8 * k, 9 * k)])
    ellipse(s, (255, 230, 240), x, y - 2 * k, 10 * k, 5 * k, ow=0)
    face(s, x, y - 9 * k, k * 0.8)


def plant_cabbage(s, x, y, k, outer=(105, 185, 80), inner=(170, 228, 125), vein=(110, 180, 80)):
    blob(s, outer, [(x - 10 * k, y - 8 * k, 10 * k), (x + 10 * k, y - 8 * k, 10 * k), (x, y - 13 * k, 12 * k)])
    blob(s, inner, [(x, y - 11 * k, 8 * k)], ow=1)
    pygame.draw.arc(s, vein, pygame.Rect(P(x - 6 * k), P(y - 18 * k), max(2, P(12 * k)), max(2, P(10 * k))), 0.3, 2.8, 1)
    face(s, x, y - 10 * k, k * 0.8)


def plant_pumpkin(s, x, y, k, side=(235, 125, 25), mid=(250, 150, 40)):
    leaf(s, x + 2 * k, y - 16 * k, 40, 15 * k, 9 * k, (80, 170, 70))
    pygame.draw.line(s, (110, 90, 40), (P(x), P(y - 16 * k)), (P(x + 2 * k), P(y - 22 * k)), max(1, P(3 * k)))
    ellipse(s, side, x - 8 * k, y - 8 * k, 13 * k, 17 * k)
    ellipse(s, side, x + 8 * k, y - 8 * k, 13 * k, 17 * k)
    ellipse(s, mid, x, y - 8 * k, 14 * k, 19 * k)
    face(s, x, y - 8 * k, k * 0.85)


PLANTS = [plant_potato, plant_carrot, plant_wheat, plant_tomato, plant_cucumber,
          plant_corn, plant_beet, plant_cabbage, plant_pumpkin]


# ---------- зимние культуры ----------
def plant_garlic(s, x, y, k):
    for a in (65, 82, 98, 115):
        leaf(s, x, y - 12 * k, a, 22 * k, 5 * k, (110, 190, 90))
    blob(s, (248, 244, 236), [(x - 5 * k, y - 7 * k, 7 * k), (x + 5 * k, y - 7 * k, 7 * k), (x, y - 9 * k, 8 * k)], 2)
    poly(s, (248, 244, 236), [(x - 3 * k, y - 15 * k), (x + 3 * k, y - 15 * k), (x, y - 21 * k)], 1)
    face(s, x, y - 7 * k, k * 0.8)


def plant_parsnip(s, x, y, k):
    plant_carrot(s, x, y, k, body=(245, 228, 185), stripe=(205, 185, 140), g=(110, 185, 100))


def plant_turnip(s, x, y, k):
    plant_radish(s, x, y, k, top=(160, 95, 205))


def plant_cranberry(s, x, y, k):
    plant_tomato(s, x, y, k, bush=(55, 125, 85), fruit=(205, 25, 60), fr=4.2)


def plant_leek(s, x, y, k):
    for dx in (-7, 0, 7):
        bx = x + dx * k
        leaf(s, bx, y - 14 * k, 90 - dx * 3, 21 * k, 8 * k, (75, 160, 95))
        poly(s, (240, 246, 232), [(bx - 3 * k, y), (bx + 3 * k, y), (bx + 3 * k, y - 15 * k), (bx - 3 * k, y - 15 * k)], 2)
    face(s, x, y - 6 * k, k * 0.6)


def plant_kohlrabi(s, x, y, k):
    for a in (60, 90, 120):
        leaf(s, x, y - 14 * k, a, 22 * k, 8 * k, (120, 190, 110))
    blob(s, (190, 228, 150), [(x, y - 9 * k, 10 * k)])
    face(s, x, y - 9 * k, k * 0.85)


def plant_kale(s, x, y, k):
    plant_cabbage(s, x, y, k, outer=(115, 85, 155), inner=(165, 125, 205), vein=(90, 60, 130))


def plant_brussels(s, x, y, k):
    pygame.draw.line(s, OUT, (P(x), P(y)), (P(x), P(y - 30 * k)), max(3, P(4 * k)))
    pygame.draw.line(s, (125, 175, 95), (P(x), P(y)), (P(x), P(y - 30 * k)), max(1, P(2 * k)))
    for dx, dy in ((-5, -6), (5, -11), (-5, -16), (5, -21), (-4, -26)):
        blob(s, (135, 205, 95), [(x + dx * k, y + dy * k, 4.5 * k)], 1)
    leaf(s, x, y - 30 * k, 55, 14 * k, 9 * k, (90, 170, 80))
    leaf(s, x, y - 30 * k, 125, 14 * k, 9 * k, (90, 170, 80))
    face(s, x + 5 * k, y - 11 * k, k * 0.5)


def plant_icepumpkin(s, x, y, k):
    plant_pumpkin(s, x, y, k, side=(170, 200, 230), mid=(200, 222, 245))


# ---------- средневековые культуры ----------
def plant_peas(s, x, y, k):
    pygame.draw.arc(s, (80, 160, 70), pygame.Rect(P(x - 8 * k), P(y - 30 * k), P(16 * k), P(16 * k)), 0, 4.5, 2)
    for a in (60, 120, 90):
        leaf(s, x, y - 8 * k, a, 18 * k, 10 * k, (95, 180, 80), vein=(60, 130, 55))
    for px, py, ang in ((-8, -12, 0), (8, -16, 0), (1, -24, 0)):
        ellipse(s, (130, 205, 95), x + px * k, y + py * k, 16 * k, 8 * k)
        for d in (-4, 0, 4):
            pygame.draw.circle(s, (100, 175, 75), (P(x + (px + d) * k), P(y + py * k)), max(1, P(1.5 * k)))
    blob(s, WHITE, [(x - 12 * k, y - 26 * k, 3 * k)], 1)
    face(s, x - 8 * k, y - 12 * k, k * 0.45)


def plant_rye(s, x, y, k):
    plant_wheat(s, x, y, k, stalk=(165, 140, 85), ear=(205, 175, 105), grain=(150, 120, 70), h=32)


def plant_barley(s, x, y, k):
    plant_wheat(s, x, y, k, stalk=(185, 160, 80), ear=(236, 214, 130), grain=(190, 160, 80), awns=True, h=26)


def plant_spelt(s, x, y, k):
    plant_wheat(s, x, y, k, stalk=(175, 120, 70), ear=(215, 145, 90), grain=(165, 95, 55), h=30)


def plant_flax(s, x, y, k):
    for dx in (-9, -3, 3, 9):
        top = (x + dx * 1.3 * k, y - (26 + abs(dx)) * k)
        pygame.draw.line(s, (90, 160, 80), (P(x + dx * 0.5 * k), P(y)), (P(top[0]), P(top[1])), max(1, P(1.6 * k)))
        for a in range(5):
            ang = a * 2 * math.pi / 5
            pygame.draw.circle(s, (110, 150, 235), (P(top[0] + math.cos(ang) * 3 * k), P(top[1] + math.sin(ang) * 3 * k)), max(1, P(2.6 * k)))
        pygame.draw.circle(s, (250, 220, 90), (P(top[0]), P(top[1])), max(1, P(1.5 * k)))
    leaf(s, x, y - 6 * k, 60, 12 * k, 4 * k, (100, 170, 85))
    leaf(s, x, y - 6 * k, 120, 12 * k, 4 * k, (100, 170, 85))


def plant_hops(s, x, y, k):
    pygame.draw.line(s, OUT, (P(x), P(y)), (P(x), P(y - 40 * k)), max(3, P(4 * k)))
    pygame.draw.line(s, (150, 105, 60), (P(x), P(y)), (P(x), P(y - 40 * k)), max(1, P(2 * k)))
    for i, (dx, dy) in enumerate(((-6, -12), (6, -20), (-6, -28), (5, -35))):
        leaf(s, x, y + dy * k, 150 if dx < 0 else 30, 12 * k, 8 * k, (85, 160, 75))
    for cx, cy in ((-8, -16), (8, -26), (-7, -33)):
        ellipse(s, (180, 225, 120), x + cx * k, y + cy * k, 9 * k, 13 * k)
        pygame.draw.line(s, (130, 180, 90), (P(x + (cx - 3) * k), P(y + cy * k)), (P(x + (cx + 3) * k), P(y + cy * k)), 1)
    face(s, x - 8 * k, y - 16 * k, k * 0.45)


def plant_grapes(s, x, y, k):
    pygame.draw.line(s, OUT, (P(x - 12 * k), P(y)), (P(x - 12 * k), P(y - 34 * k)), max(3, P(4 * k)))
    pygame.draw.line(s, (130, 90, 55), (P(x - 12 * k), P(y)), (P(x - 12 * k), P(y - 34 * k)), max(1, P(2 * k)))
    leaf(s, x - 12 * k, y - 32 * k, 20, 22 * k, 16 * k, (95, 165, 75), vein=(60, 120, 50))
    berries = [(-4, -26), (4, -26), (-8, -19), (0, -19), (8, -19), (-4, -12), (4, -12), (0, -5)]
    blob(s, (125, 65, 155), [(x + bx * k, y + by * k, 4.6 * k) for bx, by in berries], 1)
    for bx, by in berries[:3]:
        pygame.draw.circle(s, (190, 150, 215), (P(x + (bx - 1.5) * k), P(y + (by - 1.5) * k)), max(1, P(1.2 * k)))
    face(s, x, y - 18 * k, k * 0.6)
