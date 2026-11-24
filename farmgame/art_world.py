# -*- coding: utf-8 -*-
"""Декор, здания, существа, звери, повозки, экран загрузки; смена фермы (apply_farm).

Часть art.py (3.17: вынесено без изменений). Снаружи всё берётся как раньше: from .art import ...
"""
import math
import os
import random

import pygame

from . import spritefit
from . import hd
from .config import *  # noqa: F401,F403
from .art_plants import *  # noqa: F401,F403


# ---------- фермы ----------


# ---------- декор ----------
def draw_tree(s, x, y, r):
    if blit_any(s, farm_names("props", "tree"), x, y + r * 0.4, r / 52):
        return
    pygame.draw.rect(s, OUT, (P(x - r * 0.18) - 2, P(y - r * 0.5), P(r * 0.36) + 4, P(r * 0.9) + 2))
    pygame.draw.rect(s, (130, 85, 55), (P(x - r * 0.18), P(y - r * 0.5), P(r * 0.36), P(r * 0.9)))
    blob(s, THEME["tree"], [(x - r * 0.55, y - r * 0.9, r * 0.6), (x + r * 0.55, y - r * 0.9, r * 0.6), (x, y - r * 1.35, r * 0.75)], 3)
    if THEME["snow"]:   # снежные шапки
        blob(s, THEME["tree_light"], [(x - r * 0.2, y - r * 1.8, r * 0.42), (x + r * 0.3, y - r * 1.75, r * 0.38),
                                      (x - r * 0.75, y - r * 1.25, r * 0.28), (x + r * 0.8, y - r * 1.25, r * 0.26)], 2)
    else:
        pygame.draw.circle(s, THEME["tree_light"], (P(x - r * 0.25), P(y - r * 1.5)), P(r * 0.25))


def draw_bush(s, x, y, r):
    if blit_any(s, farm_names("props", "bush"), x, y + r * 0.7, r / 30):
        return
    blob(s, THEME["bush"], [(x - r * 0.6, y, r * 0.6), (x + r * 0.6, y, r * 0.6), (x, y - r * 0.35, r * 0.75)], 3)
    if THEME["snow"]:
        blob(s, THEME["bush_light"], [(x - r * 0.15, y - r * 0.85, r * 0.45), (x + r * 0.5, y - r * 0.5, r * 0.3)], 2)
    else:
        pygame.draw.circle(s, THEME["bush_light"], (P(x - r * 0.25), P(y - r * 0.55)), max(2, P(r * 0.22)))


WALL_STONES = ((178, 170, 156), (164, 156, 144), (190, 182, 166), (152, 146, 138), (172, 160, 142))


def _stone(s, base, d, cx, cy, w, h, color, rnd):
    """Камень: скруглённый прямоугольник, скошенный вдоль стены (d — единичный вектор вдоль), с бликом сверху."""
    pts = []
    for i in range(16):
        a = i * math.pi / 8
        c, sn = math.cos(a), math.sin(a)
        u = math.copysign(abs(c) ** 0.55, c) * w / 2 * (1 + rnd.uniform(-0.05, 0.05))
        v = math.copysign(abs(sn) ** 0.55, sn) * h / 2 * (1 + rnd.uniform(-0.06, 0.06))
        pts.append((cx + d[0] * u, cy + d[1] * u - v))
    poly(s, color, pts, 2)
    light = tuple(min(255, c + 22) for c in color)       # блик по верху камня
    top = [(cx + d[0] * u * 0.7, cy + d[1] * u * 0.7 - h * 0.28) for u in (-w / 2, w / 2)]
    pygame.draw.line(s, light, (P(top[0][0]), P(top[0][1])), (P(top[1][0]), P(top[1][1])), max(2, P(2)))
    if rnd.random() < 0.18:                              # мох
        mx = cx + d[0] * rnd.uniform(-w / 4, w / 4)
        my = cy + d[1] * rnd.uniform(-w / 4, w / 4) - h * 0.35
        blob(s, (118, 150, 78), [(mx, my, 3.2), (mx + 4, my + 1, 2.6)], 0)


def draw_stone_wall(s, a, b):
    """3.13.2: низкая каменная кладка вдоль края поля: тёмный раствор, два ряда скруглённых камней разного размера
    и цвета, сверху плоские камни-накрывки, кое-где мох. Раньше — ровные серые параллелограммы."""
    import random as _r
    ax, ay = a
    bx, by = b
    ln = math.hypot(bx - ax, by - ay)
    if ln < 4:
        return
    d = ((bx - ax) / ln, (by - ay) / ln)
    rnd = _r.Random(int(ax * 7 + ay * 13 + bx))
    H = 24
    body = [(ax, ay), (bx, by), (bx, by - H), (ax, ay - H)]
    poly(s, (104, 96, 88), body, 3)                       # раствор между камнями
    for row, (yc, hgt) in enumerate(((-6, 11), (-16, 10))):
        t = rnd.uniform(0, 8) if row else 2.0
        while t < ln - 4:
            w = rnd.uniform(14, 24)
            w = min(w, ln - 2 - t)
            if w < 7:
                break
            cx, cy = ax + d[0] * (t + w / 2), ay + d[1] * (t + w / 2) + yc
            _stone(s, (ax, ay), d, cx, cy, w - 2, hgt, rnd.choice(WALL_STONES), rnd)
            t += w
    t = 0.0                                               # накрывки
    while t < ln - 2:
        w = min(rnd.uniform(20, 30), ln - t)
        if w < 8:
            break
        cx, cy = ax + d[0] * (t + w / 2), ay + d[1] * (t + w / 2) - H
        _stone(s, (ax, ay), d, cx, cy, w, 8, (196, 188, 174), rnd)
        t += w - 1


def draw_fence(s, a, b, off):
    ax, ay = a[0] + off[0], a[1] + off[1]
    bx, by = b[0] + off[0], b[1] + off[1]
    if THEME.get("wall"):   # средневековье: низкая каменная стена
        draw_stone_wall(s, (ax, ay), (bx, by))
        return
    for h in (9, 19):
        pygame.draw.line(s, OUT, (P(ax), P(ay - h)), (P(bx), P(by - h)), 6)
        pygame.draw.line(s, (235, 225, 220), (P(ax), P(ay - h)), (P(bx), P(by - h)), 3)
    n = max(1, int(math.hypot(bx - ax, by - ay) / 24))
    for k in range(n + 1):
        px, py = ax + (bx - ax) * k / n, ay + (by - ay) * k / n
        poly(s, (245, 238, 235), [(px - 4, py), (px - 4, py - 24), (px, py - 29), (px + 4, py - 24), (px + 4, py)])


def draw_windmill(s):
    """Ветряная мельница (без лопастей — они крутятся отдельно). Координаты как у амбара."""
    if blit_sprite(s, "buildings/windmill", 0, 0, 1, "topleft"):
        return
    poly(s, (210, 195, 170), [(110, 205), (270, 205), (240, 70), (140, 70)], 3)          # каменная башня
    for yy in (100, 130, 160, 190):
        pygame.draw.line(s, (180, 165, 140), (125 + (205 - yy) // 6, yy), (255 - (205 - yy) // 6, yy), 2)
    poly(s, (150, 90, 55), [(125, 75), (255, 75), (190, 10)], 3)                           # крыша
    rounded(s, (120, 80, 50), (170, 150, 40, 55), 4, 3)                                    # дверь
    rounded(s, (170, 220, 245), (178, 95, 24, 24), 3, 3)                                   # окошко


MILL_HUB = (60 + 190, 18 + 55)   # центр лопастей на экране (амбар/мельница рисуется со сдвигом 60, 18)


def draw_mill_blades(s, cx, cy, ang, r=78):
    if blit_sprite(s, "buildings/windmill_blades", cx, cy, r / 78, "center", angle=-math.degrees(ang)):
        return
    for i in range(4):
        a = ang + i * math.pi / 2
        dx, dy = math.cos(a), math.sin(a)
        nx, ny = -dy, dx
        tip = (cx + dx * r, cy + dy * r)
        base = (cx + dx * 14, cy + dy * 14)
        pygame.draw.line(s, OUT, (P(cx), P(cy)), (P(tip[0]), P(tip[1])), 6)
        pygame.draw.line(s, (120, 85, 55), (P(cx), P(cy)), (P(tip[0]), P(tip[1])), 3)
        sail = [(base[0] + nx * 3, base[1] + ny * 3), (tip[0] + nx * 3, tip[1] + ny * 3),
                (tip[0] + nx * 17, tip[1] + ny * 17), (base[0] + nx * 13, base[1] + ny * 13)]
        poly(s, (245, 235, 215), sail, 2)
    blob(s, (150, 90, 55), [(cx, cy, 8)], 3)


def draw_castle(s, x, y):
    """Замок на холме на заднем плане. (x, y) — подножие холма по центру."""
    if blit_sprite(s, "props/castle", x, y + 30):
        return
    ellipse(s, (130, 170, 90), x, y, 210, 60, ow=0)
    stone, dark = (190, 185, 178), (160, 155, 148)
    poly(s, stone, [(x - 60, y - 10), (x + 60, y - 10), (x + 60, y - 60), (x - 60, y - 60)], 3)
    for cx in range(-56, 60, 16):
        poly(s, stone, [(x + cx, y - 60), (x + cx + 9, y - 60), (x + cx + 9, y - 68), (x + cx, y - 68)], 2)
    for tx, h in ((-62, 95), (62, 95), (0, 120)):
        poly(s, stone, [(x + tx - 16, y - 10), (x + tx + 16, y - 10), (x + tx + 16, y - h), (x + tx - 16, y - h)], 3)
        poly(s, (70, 90, 160), [(x + tx - 20, y - h), (x + tx + 20, y - h), (x + tx, y - h - 30)], 3)
        pygame.draw.line(s, OUT, (P(x + tx), P(y - h - 30)), (P(x + tx), P(y - h - 46)), 2)
        poly(s, (220, 60, 60), [(x + tx, y - h - 46), (x + tx + 14, y - h - 41), (x + tx, y - h - 36)], 1)
        rounded(s, (60, 50, 50), (P(x + tx - 4), P(y - h + 14), 8, 12), 3, 1)
    rounded(s, (110, 75, 50), (P(x - 13), P(y - 38), 26, 28), 10, 3)
    pygame.draw.line(s, dark, (P(x - 60), P(y - 35)), (P(x + 60), P(y - 35)), 1)


def draw_chapel(s, x, y, t=0.0, ringing=False):
    """Часовня с колоколом (вместо тучки). (x, y) — центр."""
    if blit_any(s, (["props/chapel_ringing"] if ringing else []) + ["props/chapel"], x, y + 30):
        return
    poly(s, (225, 215, 195), [(x - 34, y + 30), (x + 34, y + 30), (x + 34, y - 4), (x - 34, y - 4)], 3)
    poly(s, (150, 80, 60), [(x - 42, y - 2), (x + 42, y - 2), (x, y - 34)], 3)
    poly(s, (225, 215, 195), [(x - 12, y - 30), (x + 12, y - 30), (x + 12, y - 62), (x - 12, y - 62)], 3)
    poly(s, (150, 80, 60), [(x - 16, y - 60), (x + 16, y - 60), (x, y - 80)], 3)
    pygame.draw.line(s, OUT, (P(x), P(y - 80)), (P(x), P(y - 96)), 3)
    pygame.draw.line(s, OUT, (P(x - 6), P(y - 90)), (P(x + 6), P(y - 90)), 3)
    swing = math.sin(t * 9) * 0.5 if ringing else 0.0
    bx, by = x + math.sin(swing) * 6, y - 46
    poly(s, (245, 195, 60), [(bx - 7, by + 8), (bx + 7, by + 8), (bx + 4, by - 6), (bx - 4, by - 6)], 2)
    rounded(s, (120, 80, 50), (P(x - 9), P(y + 8), 18, 22), 8, 2)


def draw_cart(s, x, y, color, cargo=False, bob=0.0):
    """Телега с лошадью (вместо грузовика), едет влево. (x, y) — земля под колёсами."""
    y = y - bob
    ellipse(s, (125, 150, 90), x - 20, y + 2 + bob, 220, 18, ow=0)
    # лошадь
    hx = x - 110
    for lx in (-16, -6, 10, 18):
        pygame.draw.line(s, OUT, (P(hx + lx), P(y - 22)), (P(hx + lx), P(y - 2)), 6)
        pygame.draw.line(s, (150, 100, 60), (P(hx + lx), P(y - 22)), (P(hx + lx), P(y - 3)), 3)
    ellipse(s, (160, 105, 65), hx, y - 32, 52, 26)
    poly(s, (160, 105, 65), [(hx - 18, y - 38), (hx - 30, y - 62), (hx - 22, y - 66), (hx - 8, y - 42)])
    ellipse(s, (160, 105, 65), hx - 32, y - 62, 24, 14)
    poly(s, (80, 55, 40), [(hx - 20, y - 66), (hx - 10, y - 46), (hx - 14, y - 44), (hx - 24, y - 62)], 2)
    pygame.draw.circle(s, OUT, (P(hx - 34), P(y - 64)), 2)
    pygame.draw.line(s, (110, 75, 45), (P(hx + 24), P(y - 30)), (P(x - 50), P(y - 30)), 3)
    # телега
    dark = tuple(max(0, c - 50) for c in color)
    poly(s, color, [(x - 55, y - 20), (x + 70, y - 20), (x + 78, y - 58), (x - 62, y - 58)], 3)
    for px in range(-45, 70, 22):
        pygame.draw.line(s, dark, (P(x + px), P(y - 22)), (P(x + px + 2), P(y - 56)), 2)
    if cargo:
        for cx in (-40, -12, 16, 44):
            ellipse(s, (215, 185, 130), x + cx, y - 66, 26, 20)
    for wx in (x - 30, x + 45):
        pygame.draw.circle(s, OUT, (P(wx), P(y - 12)), 17)
        pygame.draw.circle(s, (150, 105, 65), (P(wx), P(y - 12)), 14)
        for a in range(4):
            ang = a * math.pi / 4
            pygame.draw.line(s, OUT, (P(wx - math.cos(ang) * 13), P(y - 12 - math.sin(ang) * 13)),
                             (P(wx + math.cos(ang) * 13), P(y - 12 + math.sin(ang) * 13)), 2)


LOADING_RING_R = 80          # радиус колеса на экране загрузки, px


def draw_loading_wheel(s, cx, cy, r, ang):
    """Деревянное тележное колесо (если нет картинки ui/loading_ring). ang — угол поворота в радианах."""
    for i in range(8):
        a = ang + i * math.pi / 4
        x1, y1 = cx + math.cos(a) * r * 0.86, cy + math.sin(a) * r * 0.86
        pygame.draw.line(s, OUT, (P(cx), P(cy)), (P(x1), P(y1)), max(3, P(r * 0.13)))
        pygame.draw.line(s, (176, 120, 70), (P(cx), P(cy)), (P(x1), P(y1)), max(1, P(r * 0.08)))
    pygame.draw.circle(s, OUT, (P(cx), P(cy)), P(r), max(3, P(r * 0.2)))
    pygame.draw.circle(s, (150, 98, 58), (P(cx), P(cy)), P(r * 0.95), max(2, P(r * 0.12)))
    pygame.draw.circle(s, (120, 120, 128), (P(cx), P(cy)), P(r * 1.0), max(1, P(r * 0.04)))
    # метка на ободе (пучок колосьев) — чтобы было видно, что колесо крутится
    mx, my = cx + math.cos(ang) * r * 0.95, cy + math.sin(ang) * r * 0.95
    blob(s, (245, 205, 90), [(mx, my, r * 0.12)], 2)
    blob(s, (150, 98, 58), [(cx, cy, r * 0.2)], 2)


def draw_loading_screen(s, frac, t, title, hint):
    """Экран загрузки: фон, логотип, крутящееся колесо с талисманом, полоска.
    Картинки (все необязательные): backgrounds/loading, ui/logo, ui/loading_ring, ui/loading_center."""
    if not blit_sprite(s, "backgrounds/loading", 0, 0, 1, "topleft"):
        s.fill((120, 160, 90))
    if not blit_sprite(s, "ui/logo", W // 2, 150, 1, "center"):
        draw_text(s, title, 46, (W // 2, 150))
    cx, cy, r = W // 2, 330, LOADING_RING_R
    ang = t * 2.2                                     # оборот примерно за 3 секунды
    if not blit_sprite(s, "ui/loading_ring", cx, cy, r / 98, "center", angle=-math.degrees(ang)):
        draw_loading_wheel(s, cx, cy, r, ang)
    bob = math.sin(t * 4) * 3                         # талисман не крутится, а покачивается
    if not blit_sprite(s, "ui/loading_center", cx, cy + bob, r / 98, "center"):
        draw_peasant_head(s, cx, cy + bob, 3.2)
    draw_text(s, "Готовлю картинки…", 18, (W // 2, cy + r + 36))
    draw_bar(s, (W // 2 - 200, cy + r + 56, 400, 20), frac, GOLD)
    draw_text(s, hint, 13, (W // 2, cy + r + 96), (235, 245, 220), outline=None)


def blit_icon(s, name, x, y, k=1.0):
    """Иконка с центром (x, y) в масштабе k. Крупно (k > 1.25) — из вдвое более крупной подгонки, чтобы не мылилась."""
    if k > 1.25 and blit_sprite(s, name + spritefit.HI, x, y, k / 2, "center"):
        return True
    return blit_sprite(s, name, x, y, k, "center")


def draw_peasant_head(s, x, y, k=1.0):
    if blit_icon(s, "icons/peasant", x, y, k):
        return
    blob(s, (245, 205, 170), [(x, y + 1 * k, 8 * k)], 2)
    poly(s, (140, 100, 60), [(x - 10 * k, y + 2 * k), (x - 8 * k, y - 7 * k), (x, y - 11 * k), (x + 8 * k, y - 7 * k), (x + 10 * k, y + 2 * k), (x + 6 * k, y - 3 * k), (x - 6 * k, y - 3 * k)], 2)
    pygame.draw.circle(s, OUT, (P(x - 3 * k), P(y + 1 * k)), max(1, P(1.4 * k)))
    pygame.draw.circle(s, OUT, (P(x + 3 * k), P(y + 1 * k)), max(1, P(1.4 * k)))


def draw_bandit(s, x, y, d, t=0.0, sack=0.0, running=False, pose=None):
    """Разбойник в капюшоне с мешком. (x, y) — точка у ног, d — куда смотрит.
    pose — (подскок, sx, sy, наклон) из App.bandit_pose (3.3); без него — старое покачивание."""
    if pose is None:
        pose = (abs(math.sin(t * 14)) * 4 if running else 0, 1.0, 1.0, 0.0)
    hop, sx, sy, ang = pose
    if blit_tf(s, (["creatures/bandit_sack"] if sack > 0 else []) + ["creatures/bandit"], x, y - hop, 1,
               flip=d < 0, sx=sx, sy=sy, angle=ang):
        return
    def X(dx):
        return x + dx * d
    hop = abs(math.sin(t * 14)) * 4 if running else 0
    y = y - hop
    ellipse(s, (110, 120, 80), x, y + hop + 1, 34, 8, ow=0)
    for lx in (-5, 5):
        pygame.draw.line(s, OUT, (P(X(lx)), P(y - 14)), (P(X(lx + (3 if running else 0))), P(y)), 5)
    poly(s, (60, 100, 70), [(X(-14), y - 10), (X(14), y - 10), (X(9), y - 40), (X(-9), y - 40)])     # плащ
    if sack > 0:   # мешок на спине
        ss = min(16, 9 + math.log10(1 + sack) * 0.6)
        blob(s, (190, 150, 95), [(X(-14), y - 30, ss)], 2)
        draw_text(s, "$", 12, (X(-14), y - 30), (120, 85, 40), outline=None)
    blob(s, (60, 100, 70), [(X(1), y - 48, 12)], 2)                                                   # капюшон
    pygame.draw.circle(s, (245, 205, 170), (P(X(4)), P(y - 47)), 8)
    pygame.draw.rect(s, (40, 40, 45), (P(X(4) - 9), P(y - 51), 18, 6))                                # маска
    pygame.draw.circle(s, WHITE, (P(X(2)), P(y - 48)), 2)
    pygame.draw.circle(s, WHITE, (P(X(7)), P(y - 48)), 2)


def draw_barn(s):
    if blit_any(s, farm_names("buildings", "barn"), 0, 0, 1, "topleft"):
        return
    # стена
    poly(s, (225, 75, 70), [(70, 70), (250, 70), (250, 200), (70, 200)], 3)
    # боковая стена
    poly(s, (190, 55, 55), [(250, 70), (310, 105), (310, 215), (250, 200)], 3)
    # крыша
    poly(s, (70, 110, 200), [(55, 78), (160, 5), (265, 78)], 3)
    poly(s, (90, 130, 220), [(160, 5), (265, 78), (325, 112), (225, 40)], 3)
    # ворота
    rounded(s, (240, 235, 230), (110, 120, 100, 80), 2, 3)
    pygame.draw.line(s, OUT, (113, 123), (207, 197), 3)
    pygame.draw.line(s, OUT, (207, 123), (113, 197), 3)
    # окно
    rounded(s, (170, 220, 245), (140, 60, 40, 34), 2, 3)
    pygame.draw.line(s, OUT, (160, 60), (160, 94), 2)
    if THEME["snow"]:  # снег на крыше
        poly(s, (248, 252, 255), [(55, 78), (160, 5), (225, 40), (245, 55), (200, 40), (160, 22), (110, 55), (70, 80)], 2)
        poly(s, (248, 252, 255), [(160, 5), (225, 40), (325, 112), (300, 112), (215, 55), (170, 20)], 2)


def draw_squirrel(s, x, y, d, hop=0.0, golden=False, t=0.0, sx=1.0, sy=1.0, angle=0.0, alpha=None, pivot="midbottom"):
    """Белка. (x, y) — точка на земле, d = 1 смотрит вправо, -1 влево.
    sx, sy, angle — сплющить/вытянуть и наклонить (3.3: прыжки дугами, кувырок при поимке)."""
    if blit_tf(s, "creatures/squirrel_golden" if golden else "creatures/squirrel", x, y - hop, 1, flip=d < 0,
               sx=sx, sy=sy, angle=angle, alpha=alpha, pivot=pivot):
        return
    def X(dx):
        return x + dx * d
    ellipse(s, (110, 160, 90), x, y + 1, 40, 8, ow=0)  # тень
    y = y - hop
    if golden:
        fur, light, dark = (245, 195, 40), (255, 235, 130), (205, 150, 20)
    else:
        fur, light, dark = (205, 115, 55), (235, 160, 90), (165, 85, 40)
    blob(s, fur, [(X(-20), y - 26, 14), (X(-26), y - 42, 12), (X(-17), y - 54, 9)], 2)
    pygame.draw.circle(s, light, (P(X(-23)), P(y - 40)), 6)
    ellipse(s, dark, X(-6), y - 3, 12, 7)
    ellipse(s, dark, X(10), y - 3, 12, 7)
    ellipse(s, fur, X(0), y - 15, 32, 24)
    ellipse(s, (245, 220, 175), X(7), y - 13, 13, 14, ow=0)
    poly(s, fur, [(X(9), y - 37), (X(13), y - 50), (X(18), y - 38)])
    blob(s, fur, [(X(16), y - 29, 11)], 2)
    pygame.draw.circle(s, OUT, (P(X(20)), P(y - 31)), 3)
    pygame.draw.circle(s, WHITE, (P(X(21)), P(y - 32)), 1)
    pygame.draw.circle(s, OUT, (P(X(27)), P(y - 27)), 2)
    pygame.draw.circle(s, (255, 150, 150), (P(X(17)), P(y - 24)), 2)
    # жёлудь в лапках
    ellipse(s, (160, 100, 45), X(21), y - 13, 9, 11)
    ellipse(s, (105, 70, 35), X(21), y - 18, 11, 6)
    if golden:  # искорки
        for k in range(4):
            a = t * 3 + k * math.pi / 2
            sx, sy = x + math.cos(a) * 34, y - 28 + math.sin(a) * 26
            r = 4 + 2 * math.sin(t * 9 + k)
            poly(s, (255, 250, 180), [(sx, sy - r * 1.6), (sx + r * 0.5, sy), (sx, sy + r * 1.6), (sx - r * 0.5, sy)], 1)


def draw_crow(s, x, y, d, t=0.0, flying=False, peck=0.0, k=1.4, wings_up=True, sx=1.0, sy=1.0, angle=0.0):
    """Ворона. (x, y) — точка под лапами, d = 1 смотрит вправо, k — масштаб.
    В полёте (3.3) крылья машут: wings_up — картинка crow_fly (крылья вверх), иначе crow (сложены)."""
    name = "creatures/crow_fly" if flying and wings_up else "creatures/crow"
    if blit_tf(s, [name, "creatures/crow"], x, y, k / 1.4, flip=d < 0, sx=sx, sy=sy, angle=angle):
        return
    def X(dx):
        return x + dx * k * d

    def Y(dy):
        return y + dy * k
    black, wing, dark = (50, 50, 65), (75, 75, 95), (30, 30, 40)
    if not flying:
        ellipse(s, (170, 100, 60), x, y + 1, 30 * k, 7 * k, ow=0)
        for lx in (-4, 4):
            pygame.draw.line(s, (240, 150, 40), (P(X(lx)), P(Y(-6))), (P(X(lx)), P(y)), 3)
            pygame.draw.line(s, (240, 150, 40), (P(X(lx)), P(y)), (P(X(lx + 4)), P(y)), 3)
    poly(s, dark, [(X(-12), Y(-16)), (X(-28), Y(-10)), (X(-27), Y(-22))])          # хвост
    ellipse(s, black, X(-1), Y(-17), 30 * k, 22 * k)                                   # тело
    hx, hy = X(12), Y(-29 + peck)                                                      # голова
    if flying:
        flap = math.sin(t * 18)
        poly(s, wing, [(X(-8), Y(-20)), (X(6), Y(-20)), (X(-4), Y(-20 - 26 * flap)), (X(-18), Y(-20 - 20 * flap))])
    else:
        ellipse(s, wing, X(-3), Y(-18), 20 * k, 12 * k)
    blob(s, black, [(hx, hy, 10 * k)], 2)
    poly(s, (245, 170, 40), [(hx + 7 * k * d, hy - 3 * k), (hx + 21 * k * d, hy + 1 * k), (hx + 7 * k * d, hy + 4 * k)])
    pygame.draw.circle(s, WHITE, (P(hx + 3 * k * d), P(hy - 3 * k)), P(4 * k))
    pygame.draw.circle(s, OUT, (P(hx + 4 * k * d), P(hy - 3 * k)), P(2 * k))
    pygame.draw.line(s, OUT, (P(hx - 2 * k * d), P(hy - 9 * k)), (P(hx + 7 * k * d), P(hy - 6 * k)), 3)  # сердитая бровь


def _eye(s, x, y, k):
    pygame.draw.circle(s, OUT, (P(x), P(y)), max(2, P(3 * k)))
    pygame.draw.circle(s, WHITE, (P(x + k), P(y - k)), max(1, P(1.1 * k)))


def _beanie(s, x, y, k, color, w=22):
    """Вязаная шапка с помпоном. (x, y) — низ шапки по центру."""
    ellipse(s, color, x, y - 5 * k, w * k, 14 * k)
    rounded(s, WHITE, (P(x - w * k / 2), P(y - 3 * k), P(w * k), P(6 * k)), 3, 2)
    blob(s, WHITE, [(x, y - 13 * k, 4.5 * k)], 2)


def _scarf(s, x, y, k, color, w=20, tail=1):
    ellipse(s, color, x, y, w * k, 8 * k)
    poly(s, color, [(x + tail * 2 * k, y), (x + tail * 8 * k, y), (x + tail * 6 * k, y + 14 * k), (x + tail * 1 * k, y + 13 * k)])
    pygame.draw.line(s, WHITE, (P(x + tail * 2 * k), P(y + 7 * k)), (P(x + tail * 7 * k), P(y + 7 * k)), 2)


ANIMAL_SPRITE_K = 0.85   # картинки зверей чуть меньше холста: в загоне под ними подпись и забор


def animal_pose(key, t, active):
    """Как двигается зверь в загоне (3.3) -> (подскок, sx, sy, наклон°). Картинки смотрят вправо:
    наклон вперёд — по часовой, то есть отрицательный угол. Голодный зверь стоит тихо и чуть «сник»."""
    if not active:
        return 0.0, 1.0, 0.985, 0.0
    if key == "chicken":             # клюёт зёрнышки: каждые 1.8 с — два быстрых клевка, между ними оглядывается
        c = t % 1.8
        peck = max(0.0, math.sin(c / 0.32 * math.pi)) if c < 0.64 else 0.0
        look = 2.5 * math.sin(t * 2.3) if c >= 0.64 else 0.0
        hop = 2.0 * max(0.0, math.sin((c - 1.1) / 0.3 * math.pi)) if 1.1 <= c < 1.4 else 0.0
        return hop, 1.0, 1.0 - 0.03 * peck, -16 * peck + look
    if key == "cow":                 # жуёт: медленно дышит, раз в 5 с наклоняется к сену
        c = t % 5.0
        graze = math.sin((c - 3.2) / 1.6 * math.pi) if 3.2 <= c < 4.8 else 0.0
        chew = 0.012 * math.sin(t * 7)       # челюсть: мелкая частая «жвачка»
        return 0.0, 1.0 - chew * 0.5, 1.0 + 0.012 * math.sin(t * 1.8) + chew, -4.5 * graze + 0.8 * math.sin(t * 0.9)
    if key == "pig":                 # довольно пританцовывает: подпрыгивает и виляет
        c = t % 2.6
        hop = 5.0 * math.sin(c / 0.42 * math.pi) if c < 0.42 else 0.0
        land = max(0.0, 1 - abs(c - 0.48) / 0.1) if 0.38 < c < 0.58 else 0.0
        return hop, 1.0 + 0.06 * land, 1.0 - 0.07 * land + 0.015 * math.sin(t * 3), 2.2 * math.sin(t * 6.3)
    if key == "bees":                # улей «дышит» — внутри кипит работа
        return 0.0, 1.0 - 0.008 * math.sin(t * 4), 1.0 + 0.012 * math.sin(t * 4), 0.0
    return abs(math.sin(t * 6)) * 2, 1.0, 1.0, 0.0


def draw_bees(s, x, y, k, t, n):
    """Пчёлки летают вокруг улья петлями: жёлтое брюшко с полоской, крылышки машут. (x, y) — низ улья."""
    for i in range(n):
        a = t * (1.6 + i * 0.37) + i * 2.4
        bx = x + math.sin(a) * (52 + 10 * (i % 2)) * k
        by = y - 52 * k + math.sin(a * 2 + i) * 22 * k - 8 * math.sin(t * 9 + i) * 0.4
        d = 1 if math.cos(a) > 0 else -1                   # летит туда, куда смотрит
        flap = abs(math.sin(t * 40 + i))
        wing = (235, 245, 255)
        pygame.draw.ellipse(s, wing, (P(bx - 4 * k), P(by - (5 + 3 * flap) * k), max(2, P(5 * k)), max(2, P((4 + 3 * flap) * k))))
        pygame.draw.ellipse(s, OUT, (P(bx - 5 * k), P(by - 3 * k), max(3, P(10 * k)), max(2, P(7 * k))))
        pygame.draw.ellipse(s, (250, 205, 50), (P(bx - 4 * k), P(by - 2 * k), max(2, P(8 * k)), max(2, P(5 * k))))
        pygame.draw.line(s, OUT, (P(bx + d * 0.5 * k), P(by - 2 * k)), (P(bx + d * 0.5 * k), P(by + 2 * k)), max(1, P(1.5 * k)))
        pygame.draw.circle(s, OUT, (P(bx + d * 5 * k), P(by)), max(1, P(2 * k)))


def _animal_sprite(s, key, x, y, k, t, active, winter):
    hop, sx, sy, ang = animal_pose(key, t, active)
    names = ([f"animals/{key}_winter"] if winter else []) + [f"animals/{key}"]
    if not blit_tf(s, names, x, y - hop * k, k / 1.15 * ANIMAL_SPRITE_K, sx=sx, sy=sy, angle=ang):
        return False
    if key == "bees":
        draw_bees(s, x, y, k, t, 4 if active else 1)
    return True


def draw_chicken(s, x, y, k=1.0, t=0.0, active=True, winter=False):
    if _animal_sprite(s, "chicken", x, y, k, t, active, winter):
        return
    b = math.sin(t * 9) * 2 * k if active else 0
    for lx in (-6, 6):
        pygame.draw.line(s, (240, 160, 40), (P(x + lx * k), P(y - 10 * k)), (P(x + lx * k), P(y)), max(2, P(3 * k)))
    poly(s, (235, 235, 240), [(x - 18 * k, y - 26 * k + b), (x - 34 * k, y - 46 * k + b), (x - 26 * k, y - 22 * k + b)])
    blob(s, WHITE, [(x - 2 * k, y - 24 * k + b, 19 * k), (x + 13 * k, y - 40 * k + b, 12 * k)], 3)
    ellipse(s, (232, 232, 238), x - 4 * k, y - 22 * k + b, 22 * k, 14 * k)
    blob(s, (235, 70, 70), [(x + 9 * k, y - 53 * k + b, 4 * k), (x + 14 * k, y - 55 * k + b, 4.5 * k), (x + 19 * k, y - 52 * k + b, 4 * k)], 2)
    poly(s, (250, 190, 50), [(x + 23 * k, y - 43 * k + b), (x + 32 * k, y - 39 * k + b), (x + 23 * k, y - 36 * k + b)])
    ellipse(s, (235, 70, 70), x + 23 * k, y - 32 * k + b, 6 * k, 8 * k)
    _eye(s, x + 16 * k, y - 43 * k + b, k)
    if winter:
        _scarf(s, x + 8 * k, y - 31 * k + b, k, (80, 140, 225), 18, -1)
        _beanie(s, x + 13 * k, y - 47 * k + b, k, (225, 65, 75), 20)


def draw_cow(s, x, y, k=1.0, t=0.0, active=True, winter=False):
    if _animal_sprite(s, "cow", x, y, k, t, active, winter):
        return
    b = math.sin(t * 5) * 2 * k if active else 0
    for lx in (-22, -10, 12, 24):
        pygame.draw.rect(s, OUT, (P(x + lx * k - 5 * k), P(y - 22 * k), P(10 * k), P(22 * k)))
        pygame.draw.rect(s, WHITE, (P(x + lx * k - 3 * k), P(y - 22 * k), P(6 * k), P(20 * k)))
    pygame.draw.line(s, OUT, (P(x - 34 * k), P(y - 34 * k)), (P(x - 42 * k), P(y - 16 * k)), 3)
    ellipse(s, OUT, x - 42 * k, y - 14 * k, 7 * k, 9 * k)
    ellipse(s, WHITE, x, y - 34 * k, 72 * k, 38 * k)
    for sx, sy, w, h in ((-14, -40, 18, 12), (8, -28, 14, 10), (-24, -26, 10, 8)):
        ellipse(s, (60, 55, 60), x + sx * k, y + sy * k, w * k, h * k, ow=0)
    pygame.draw.circle(s, OUT, (P(x + 4 * k), P(y - 12 * k)), P(6 * k))
    pygame.draw.circle(s, (250, 210, 60), (P(x + 4 * k), P(y - 12 * k)), P(4.5 * k))
    hx, hy = x + 36 * k, y - 46 * k + b
    poly(s, (245, 235, 210), [(hx - 10 * k, hy - 14 * k), (hx - 14 * k, hy - 26 * k), (hx - 4 * k, hy - 16 * k)])
    poly(s, (245, 235, 210), [(hx + 8 * k, hy - 14 * k), (hx + 14 * k, hy - 26 * k), (hx + 2 * k, hy - 16 * k)])
    ellipse(s, (240, 240, 240), hx - 18 * k, hy - 6 * k, 14 * k, 8 * k)
    blob(s, WHITE, [(hx, hy, 17 * k)], 3)
    ellipse(s, (250, 180, 190), hx + 6 * k, hy + 10 * k, 24 * k, 14 * k)
    for nx in (1, 11):
        pygame.draw.circle(s, (180, 100, 110), (P(hx + nx * k), P(hy + 10 * k)), max(1, P(2 * k)))
    _eye(s, hx - 4 * k, hy - 4 * k, k)
    _eye(s, hx + 8 * k, hy - 4 * k, k)
    if winter:
        _scarf(s, x + 24 * k, y - 34 * k + b, k, (225, 65, 75), 22, -1)
        _beanie(s, hx + 1 * k, hy - 13 * k, k, (90, 180, 110), 20)


def draw_pig(s, x, y, k=1.0, t=0.0, active=True, winter=False):
    if _animal_sprite(s, "pig", x, y, k, t, active, winter):
        return
    b = math.sin(t * 7) * 2 * k if active else 0
    pink, dark = (248, 175, 185), (225, 130, 150)
    for lx in (-18, -6, 10, 20):
        pygame.draw.rect(s, OUT, (P(x + lx * k - 5 * k), P(y - 14 * k), P(10 * k), P(14 * k)))
        pygame.draw.rect(s, pink, (P(x + lx * k - 3 * k), P(y - 14 * k), P(6 * k), P(12 * k)))
    pygame.draw.arc(s, OUT, pygame.Rect(P(x - 40 * k), P(y - 38 * k), P(12 * k), P(12 * k)), 0, 5, 3)
    ellipse(s, pink, x, y - 28 * k, 64 * k, 40 * k)
    hx, hy = x + 26 * k, y - 34 * k + b
    poly(s, dark, [(hx - 10 * k, hy - 10 * k), (hx - 14 * k, hy - 26 * k), (hx - 1 * k, hy - 14 * k)])
    poly(s, dark, [(hx + 6 * k, hy - 12 * k), (hx + 14 * k, hy - 26 * k), (hx + 13 * k, hy - 8 * k)])
    blob(s, pink, [(hx, hy, 17 * k)], 3)
    ellipse(s, dark, hx + 9 * k, hy + 5 * k, 16 * k, 12 * k)
    for nx in (5, 12):
        pygame.draw.circle(s, (170, 80, 100), (P(hx + nx * k), P(hy + 5 * k)), max(1, P(2 * k)))
    _eye(s, hx - 5 * k, hy - 5 * k, k)
    _eye(s, hx + 6 * k, hy - 6 * k, k)
    if winter:
        _scarf(s, x + 14 * k, y - 22 * k + b, k, (245, 200, 60), 20, -1)
        _beanie(s, hx - 1 * k, hy - 13 * k, k, (80, 130, 220), 22)


def draw_hive(s, x, y, k=1.0, t=0.0, active=True, winter=False):
    if _animal_sprite(s, "bees", x, y, k, t, active, winter):
        return
    pygame.draw.rect(s, (140, 95, 60), (P(x - 30 * k), P(y - 6 * k), P(60 * k), P(6 * k)))
    for w, h, yy in ((54, 18, -12), (48, 18, -26), (38, 16, -39), (24, 14, -50)):
        ellipse(s, (245, 195, 60), x, y + yy * k, w * k, h * k)
    ellipse(s, (90, 60, 40), x, y - 16 * k, 14 * k, 10 * k, ow=0)
    if winter:   # снежная шапка и сосульки
        blob(s, (248, 252, 255), [(x - 8 * k, y - 55 * k, 9 * k), (x + 6 * k, y - 56 * k, 10 * k), (x, y - 50 * k, 12 * k)], 2)
        for ix in (-16, -6, 6, 16):
            poly(s, (220, 240, 255), [(x + (ix - 2) * k, y - 33 * k), (x + (ix + 2) * k, y - 33 * k), (x + ix * k, y - 26 * k)], 1)
    n = 3 if active else 1
    for i in range(n):
        a = t * (2.5 + i * 0.6) + i * 2.1
        bx, by = x + math.cos(a) * 40 * k, y - 40 * k + math.sin(a * 1.3) * 18 * k
        pygame.draw.circle(s, (230, 240, 255), (P(bx - 2 * k), P(by - 5 * k)), max(2, P(4 * k)))
        pygame.draw.circle(s, (230, 240, 255), (P(bx + 3 * k), P(by - 5 * k)), max(2, P(4 * k)))
        ellipse(s, (250, 210, 50), bx, by, 13 * k, 9 * k)
        pygame.draw.line(s, OUT, (P(bx), P(by - 4 * k)), (P(bx), P(by + 4 * k)), 2)
        if winter:  # крошечный шарфик
            pygame.draw.line(s, (225, 65, 75), (P(bx + 3 * k), P(by - 4 * k)), (P(bx + 3 * k), P(by + 4 * k)), 3)


_ANIMAL_CODE = [draw_chicken, draw_cow, draw_pig, draw_hive]   # летние звери кодом (запасной рисунок)


def _animal_drawer(a):
    """3.24: зверь a текущей фермы: своя картинка animals/<key> (зимние — гусь, як, олень, медвежонок),
    без неё — летний зверь кодом (временно, пока нет картинки)."""
    def draw(s, x, y, k=1.0, t=0.0, active=True, winter=False):
        key = ANIMALS[a].get("key")
        if key and key != ("chicken", "cow", "pig", "bees")[a] and _animal_sprite(s, key, x, y, k, t, active, False):
            return
        _ANIMAL_CODE[a](s, x, y, k, t, active, winter)
    return draw


ANIMAL_DRAW = [_animal_drawer(a) for a in range(len(_ANIMAL_CODE))]


def draw_product(s, a, x, y, k=1.0):
    if blit_sprite(s, "icons/" + ANIMALS[a].get("icon", ("egg", "milk", "truffle", "honey")[a]), x, y, k, "center"):
        return
    if a == 0:    # яйцо
        ellipse(s, (252, 246, 228), x, y, 15 * k, 19 * k)
    elif a == 1:  # молоко
        rounded(s, WHITE, (P(x - 7 * k), P(y - 8 * k), P(14 * k), P(18 * k)), 3, 2)
        rounded(s, (90, 150, 230), (P(x - 5 * k), P(y - 13 * k), P(10 * k), P(6 * k)), 2, 2)
    elif a == 2:  # трюфель
        blob(s, (110, 75, 55), [(x - 4 * k, y + 1 * k, 7 * k), (x + 4 * k, y - 2 * k, 7 * k), (x, y + 4 * k, 6 * k)], 2)
    else:         # мёд
        rounded(s, (245, 170, 40), (P(x - 8 * k), P(y - 6 * k), P(16 * k), P(16 * k)), 4, 2)
        rounded(s, (200, 70, 60), (P(x - 9 * k), P(y - 11 * k), P(18 * k), P(6 * k)), 2, 2)


def draw_truck(s, x, y, color, cargo=False, bob=0.0):
    """Грузовик смотрит влево. (x, y) — точка между колёсами на земле."""
    y = y - bob
    dark = tuple(max(0, c - 50) for c in color)
    ellipse(s, (120, 150, 90), x, y + 2 + bob, 190, 18, ow=0)  # тень
    # кузов
    rounded(s, color, (P(x - 30), P(y - 72), 110, 56), 6, 3, skin=None)
    pygame.draw.rect(s, dark, (P(x - 26), P(y - 30), 102, 8))
    draw_text(s, "ФЕРМА", 14, (x + 25, y - 50), WHITE)
    if cargo:
        for cx in (-18, 12, 42):
            rounded(s, (200, 150, 90), (P(x + cx), P(y - 92), 26, 22), 2, 2)
            pygame.draw.line(s, OUT, (P(x + cx + 3), P(y - 81)), (P(x + cx + 23), P(y - 81)), 1)
    # кабина
    poly(s, color, [(x - 35, y - 16), (x - 35, y - 62), (x - 70, y - 62), (x - 88, y - 38), (x - 100, y - 36), (x - 100, y - 16)], 3)
    poly(s, (180, 225, 250), [(x - 40, y - 56), (x - 40, y - 40), (x - 80, y - 40), (x - 68, y - 56)], 2)
    pygame.draw.circle(s, (255, 240, 150), (P(x - 96), P(y - 28)), 4)
    rounded(s, (90, 90, 95), (P(x - 104), P(y - 20), 72, 8), 3, 2)
    rounded(s, (90, 90, 95), (P(x - 34), P(y - 20), 116, 8), 3, 2)
    for wx in (x - 72, x + 50):
        pygame.draw.circle(s, OUT, (P(wx), P(y - 8)), 15)
        pygame.draw.circle(s, (70, 70, 75), (P(wx), P(y - 8)), 13)
        pygame.draw.circle(s, (200, 200, 205), (P(wx), P(y - 8)), 6)


PLANT_FUNCS = {
    "potato": plant_potato, "carrot": plant_carrot, "wheat": plant_wheat, "tomato": plant_tomato,
    "cucumber": plant_cucumber, "corn": plant_corn, "beet": plant_beet, "radish": plant_radish,
    "cabbage": plant_cabbage, "pumpkin": plant_pumpkin,
    "garlic": plant_garlic, "parsnip": plant_parsnip, "turnip": plant_turnip, "cranberry": plant_cranberry,
    "leek": plant_leek, "kohlrabi": plant_kohlrabi, "kale": plant_kale, "brussels": plant_brussels,
    "icepumpkin": plant_icepumpkin,
    # 3.24: зимнее поле — пока кодом похожими растениями (до картинок crops/winter/<ключ>)
    "ginger": plant_parsnip, "frostmint": plant_leek, "pinkradish": plant_radish, "cloudberry": plant_cranberry,
    "seabuckthorn": plant_cranberry, "bluepotato": plant_potato,
    "peas": plant_peas, "rye": plant_rye, "barley": plant_barley, "spelt": plant_spelt,
    "flax": plant_flax, "hops": plant_hops, "grapes": plant_grapes,
}


def apply_farm(idx):
    """Переключает названия, рисунки культур и цвета под ферму idx."""
    fm = FARMS[min(idx, len(FARMS) - 1)]
    for i, name in enumerate(fm["names"]):
        CROPS[i]["name"] = name
    PLANTS[:] = [PLANT_FUNCS[key] for key in fm["plants"]]
    CROP_KEYS[:] = fm["plants"]
    FARM_ID[0] = fm["id"]
    THEME.clear()
    THEME.update(fm["theme"])
    CUR.clear()
    CUR.update(CURRENCIES[fm["cur"]])
    TREE[:] = TREES[fm["tree"]]
    for i, an in enumerate(ANIMAL_SETS[fm.get("animals", "summer")]):   # 3.24: звери — свои у фермы
        ANIMALS[i].clear()
        ANIMALS[i].update(an)
    TREE_NODES.clear()
    TREE_NODES.update(TREE_NODE_MAP[fm["tree"]])
    for i, name in enumerate(fm["tiers"]):
        TRUCK_TIERS[i] = (name,) + tuple(TRUCK_TIERS[i][1:])
    return fm
