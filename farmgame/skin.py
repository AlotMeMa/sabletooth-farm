# -*- coding: utf-8 -*-
"""Оформление окон и кнопок (3.4): «дерево + пергамент».

Есть картинка в assets/ui/ — игра растягивает её под любой размер, не трогая углы:
  panel.png        — окно (деревянная рамка, пергамент внутри), режется на 9 частей;
  panel_header.png — табличка заголовка, режется на 3 части (левый край, середина, правый край);
  card.png         — карточка-строка в окне, 9 частей;
  button_<цвет>.png — кнопка (green, blue, orange, red, grey), 3 части;
  slider_knob.png  — ручка ползунка.
Нет картинки — то же самое рисуется кодом (draw_*_fallback), так что игра выглядит цельно и без них.
"""
import colorsys

import pygame

from . import hd
from .art import (BTN_BLUE, BTN_GREEN, BTN_GREY, OUT, PANEL, WHITE, P, has_sprite, rounded, sprite)

BTN_ORANGE = (245, 175, 50)
BTN_RED = (225, 95, 85)
BUTTON_COLORS = {"green": BTN_GREEN, "blue": BTN_BLUE, "orange": BTN_ORANGE, "red": BTN_RED, "grey": BTN_GREY}

CARD = (255, 245, 190)
# цвета, которыми окна и кнопки рисовались раньше: rounded() с таким цветом рисует оформление
AUTO = {BTN_GREEN: "button_green", BTN_BLUE: "button_blue", BTN_GREY: "button_grey",
        (245, 175, 50): "button_orange", (240, 180, 60): "button_orange", (235, 170, 70): "button_orange",
        (230, 90, 80): "button_red", (230, 110, 100): "button_red",
        CARD: "card", PANEL: "card"}

# как резать картинку: (части, доля края в картинке, ширина края на экране в логических px или None)
#   "9" — углы и края не тянутся, середина тянется; "3" — картинка по высоте кнопки, тянется только середина
SLICE = {"panel": ("9", 0.17, 36), "card": ("9", 0.22, 14), "panel_header": ("3", 0.48, None),
         "button": ("3", 0.45, None), "slider_knob": ("1", 0, None),
         # 3.16: записки доски заданий, свиток недели, табличка на поле, облачко речи
         "quest_note_1": ("9", 0.12, 14), "quest_note_2": ("9", 0.12, 14), "quest_note_3": ("9", 0.12, 14),
         "quest_weekly": ("9", 0.14, 30), "sign": ("9", 0.2, 12), "bubble": ("9", 0.3, 14),
         # 3.18: плашки счёта, сообщения, баннер, полоски, указатели таверны
         "pill": ("3", 0.45, None), "toast": ("3", 0.45, None), "banner": ("3", 1.0, None),   # у ленты концы-«хвосты» широкие
         "bar_frame": ("3", 0.5, None), "bar_fill": ("3", 0.5, None),
         "sign_board": ("1", 0, None), "sign_casino": ("1", 0, None)}

PANEL_OUTSET = 10    # окно-картинка рисуется на столько px шире с каждой стороны (рамка не наезжает на содержимое)
_cache = {}


def button_skin(color):
    """Ближайший по оттенку цвет кнопки: любой старый цвет кнопки -> green/blue/orange/red/grey."""
    color = tuple(color[:3])
    if color in AUTO and AUTO[color].startswith("button_"):
        return AUTO[color]
    r, g, b = (c / 255 for c in color)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if s < 0.22:
        return "button_grey"
    deg = h * 360
    if deg < 22 or deg >= 330:
        return "button_red"
    if deg < 60:
        return "button_orange"
    if deg < 170:
        return "button_green"
    return "button_blue"


def _slice_rule(name):
    return SLICE.get(name) or SLICE["button" if name.startswith("button_") else "card"]


def _smooth(img, size):
    return pygame.transform.smoothscale(img, (max(1, size[0]), max(1, size[1])))


def stretched(name, w, h):
    """Картинка ui/<name>, растянутая под w×h (логические px) без искажения углов. None — если её нет."""
    img = sprite("ui/" + name)
    if img is None or w < 2 or h < 2:
        return None
    k = hd.scale()
    key = (name, int(w), int(h), k)
    out = _cache.get(key)
    if out is not None:
        return out
    src = hd.real(img)
    sw, sh = src.get_size()
    tw, th = max(1, int(round(w * k))), max(1, int(round(h * k)))
    canvas = pygame.Surface((tw, th), pygame.SRCALPHA)
    mode, frac, corner = _slice_rule(name)
    if mode == "1":
        canvas.blit(_smooth(src, (tw, th)), (0, 0))
    elif mode == "3":
        cs = max(1, min(int(sh * frac), sw // 2 - 1))          # края в исходнике
        c = min(int(round(cs * th / sh)), tw // 2)             # края на экране: картинка по высоте кнопки
        canvas.blit(_smooth(src.subsurface((0, 0, cs, sh)), (c, th)), (0, 0))
        canvas.blit(_smooth(src.subsurface((sw - cs, 0, cs, sh)), (c, th)), (tw - c, 0))
        if tw - 2 * c > 0 and sw - 2 * cs > 0:
            canvas.blit(_smooth(src.subsurface((cs, 0, sw - 2 * cs, sh)), (tw - 2 * c, th)), (c, 0))
    else:
        cs = max(1, min(int(min(sw, sh) * frac), sw // 2 - 1, sh // 2 - 1))
        c = max(1, min(int(round(corner * k)), tw // 2, th // 2))
        mw, mh = sw - 2 * cs, sh - 2 * cs
        tmw, tmh = tw - 2 * c, th - 2 * c
        cols = ((0, cs, 0, c), (cs, mw, c, tmw), (sw - cs, cs, tw - c, c))
        rows = ((0, cs, 0, c), (cs, mh, c, tmh), (sh - cs, cs, th - c, c))
        for sx, sw_, dx, dw in cols:
            for sy, sh_, dy, dh in rows:
                if sw_ > 0 and sh_ > 0 and dw > 0 and dh > 0:
                    canvas.blit(_smooth(src.subsurface((sx, sy, sw_, sh_)), (dw, dh)), (dx, dy))
    out = canvas if k == 1 else hd.HiSurf(canvas, k, (int(w), int(h)))
    if len(_cache) > 400:
        _cache.clear()
    _cache[key] = out
    return out


def draw(surf, name, rect):
    """Нарисовать элемент оформления name в rect (картинкой или кодом). Возвращает True."""
    rect = pygame.Rect(rect)
    if name == "panel" and has(name):
        rect = rect.inflate(2 * PANEL_OUTSET, 2 * PANEL_OUTSET)   # рамка-картинка — снаружи, чтобы не наезжать на кнопки
    img = stretched(name, rect.w, rect.h)
    if img is not None:
        if name in ("panel", "panel_header"):
            surf.blit(shadow_of(img), (rect.x + 4, rect.y + 6))
        surf.blit(img, rect.topleft)
        return True
    if name.startswith("button_"):
        draw_button_fallback(surf, rect, BUTTON_COLORS.get(name[7:], BTN_BLUE))
    elif name == "panel":
        draw_panel_fallback(surf, rect)
    elif name == "panel_header":
        draw_header_fallback(surf, rect)
    else:
        draw_card_fallback(surf, rect)
    return True


def plate(surf, name, rect):
    """3.18: растянутая картинка ui/<name> в rect (плашка счёта, сообщение, баннер, указатель).
    False — картинки нет: вызывающий рисует кодом."""
    rect = pygame.Rect(rect)
    img = stretched(name, rect.w, rect.h)
    if img is None:
        return False
    surf.blit(img, rect.topleft)
    return True


def _tinted(img, color):
    """Копия картинки, перекрашенная умножением на color (белая заливка полоски -> нужный цвет)."""
    key = ("tint", id(img), tuple(color[:3]))
    out = _cache.get(key)
    if out is None:
        out = img.copy()
        hd.real(out).fill(tuple(color[:3]) + (255,), special_flags=pygame.BLEND_RGBA_MULT)
        _cache[key] = out
    return out


def bar(surf, rect, frac, color):
    """3.18: полоска прогресса картинками ui/bar_frame (пустая рамка) и ui/bar_fill (белая заливка,
    красится в color). Заливка не пересчитывается каждый кадр: рисуется кусок полной полоски и её
    закруглённый конец. False — рамки-картинки нет."""
    rect = pygame.Rect(rect)
    frame = stretched("bar_frame", rect.w, rect.h)
    if frame is None:
        return False
    surf.blit(frame, rect.topleft)
    frac = max(0.0, min(1.0, frac))
    inset = max(2, int(round(rect.h * 0.15)))   # толщина деревянного края рамки
    inner = rect.inflate(-2 * inset, -2 * inset)
    if frac <= 0 or inner.w < 3 or inner.h < 2:
        return True
    fw = max(inner.h, int(round(inner.w * frac)))
    fill = stretched("bar_fill", inner.w, inner.h)
    if fill is None:
        pygame.draw.rect(surf, color, (inner.x, inner.y, fw, inner.h), border_radius=inner.h // 2)
        return True
    full = _tinted(fill, color)
    cap = min(inner.h // 2 + 1, fw // 2)
    surf.blit(full, inner.topleft, pygame.Rect(0, 0, fw - cap, inner.h))
    surf.blit(full, (inner.x + fw - cap, inner.y), pygame.Rect(inner.w - cap, 0, cap, inner.h))
    return True


def shadow_of(img):
    """Полупрозрачная тёмная копия по силуэту картинки (тень окна)."""
    key = ("shadow", id(img))
    out = _cache.get(key)
    if out is None:
        out = img.copy()
        hd.real(out).fill((30, 20, 20, 110), special_flags=pygame.BLEND_RGBA_MULT)
        _cache[key] = out
    return out


def has(name):
    return has_sprite("ui/" + name)


# ----------------------------------------------------------------------
#                  то же самое кодом (если картинок нет)
# ----------------------------------------------------------------------
def _mix(c, to, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c, to))


def draw_button_fallback(s, r, color):
    """Крашеная дощечка: тёмный низ (кнопка чуть выпуклая), светлый блик сверху, тёмный контур."""
    rad = min(12, r.h // 2)
    lip = max(3, r.h // 9)
    pygame.draw.rect(s, _mix(color, (40, 25, 20), 0.35), r, border_radius=rad)
    face = pygame.Rect(r.x, r.y, r.w, r.h - lip)
    pygame.draw.rect(s, color, face, border_radius=rad)
    if r.w > 2 * rad + 8 and r.h >= 18:
        hl = pygame.Rect(r.x + rad, r.y + 3, r.w - 2 * rad, max(2, r.h // 7))
        pygame.draw.rect(s, _mix(color, WHITE, 0.4), hl, border_radius=hl.h // 2)
    pygame.draw.rect(s, OUT, r, 3, border_radius=rad)


WOOD = (156, 104, 62)
WOOD_DARK = (122, 78, 44)
PARCHMENT = (247, 236, 208)


def draw_panel_fallback(s, r):
    """Окно: деревянная рамка с прожилками и заклёпками, внутри пергамент."""
    t = 13
    pygame.draw.rect(s, (40, 30, 30), r.move(5, 6), border_radius=16)
    rounded(s, WOOD, r, 16, 4, skin=None)
    for dy in (5, 9):
        pygame.draw.line(s, WOOD_DARK, (r.x + 18, r.y + dy), (r.right - 18, r.y + dy), 1)
        pygame.draw.line(s, WOOD_DARK, (r.x + 18, r.bottom - dy - 1), (r.right - 18, r.bottom - dy - 1), 1)
    for dx in (5, 9):
        pygame.draw.line(s, WOOD_DARK, (r.x + dx, r.y + 18), (r.x + dx, r.bottom - 18), 1)
        pygame.draw.line(s, WOOD_DARK, (r.right - dx - 1, r.y + 18), (r.right - dx - 1, r.bottom - 18), 1)
    inner = r.inflate(-2 * t, -2 * t)
    rounded(s, PARCHMENT, inner, 8, 3, skin=None)
    pygame.draw.rect(s, (226, 205, 165), inner.inflate(-12, -12), 1, border_radius=6)
    for cx, cy in ((r.x + 7, r.y + 7), (r.right - 8, r.y + 7), (r.x + 7, r.bottom - 8), (r.right - 8, r.bottom - 8)):
        pygame.draw.circle(s, OUT, (cx, cy), 4)
        pygame.draw.circle(s, (196, 192, 186), (cx, cy), 2)


def draw_header_fallback(s, r):
    """Табличка заголовка: золотистая доска с закруглёнными краями и двумя гвоздиками."""
    rad = r.h // 2
    pygame.draw.rect(s, (40, 30, 30), r.move(3, 4), border_radius=rad)
    pygame.draw.rect(s, (178, 118, 62), r, border_radius=rad)
    face = pygame.Rect(r.x, r.y, r.w, r.h - 4)
    pygame.draw.rect(s, (214, 158, 90), face, border_radius=rad)
    for dy in (r.h // 3, r.h * 2 // 3):
        pygame.draw.line(s, (190, 132, 72), (r.x + rad, r.y + dy), (r.right - rad, r.y + dy), 1)
    pygame.draw.rect(s, OUT, r, 3, border_radius=rad)
    for cx in (r.x + rad - 4, r.right - rad + 3):
        pygame.draw.circle(s, OUT, (cx, r.centery - 1), 4)
        pygame.draw.circle(s, (200, 196, 190), (cx, r.centery - 1), 2)


def draw_card_fallback(s, r):
    """Карточка-строка: светлый пергамент с тонкой внутренней линией."""
    rad = min(10, r.h // 3)
    rounded(s, (252, 242, 214), r, rad, 3, skin=None)
    if r.w > 30 and r.h > 24:
        pygame.draw.rect(s, (222, 198, 152), r.inflate(-10, -10), 1, border_radius=max(2, rad - 3))


def draw_knob(s, x, y, muted=False):
    """Ручка ползунка: картинка ui/slider_knob или деревянный кружок."""
    img = stretched("slider_knob", 32, 32)
    if img is not None:
        s.blit(img, (int(x) - 16, int(y) - 16))
        return
    pygame.draw.circle(s, OUT, (P(x), P(y)), 15)
    pygame.draw.circle(s, (170, 160, 150) if muted else (176, 120, 70), (P(x), P(y)), 12)
    pygame.draw.circle(s, (200, 190, 182) if muted else (214, 162, 104), (P(x - 3), P(y - 3)), 6)


def draw_max(surf, rect, size=15, text="Макс. уровень"):
    """3.13.2: «Макс. уровень» — золотая дощечка со звёздами (не кнопка: не нажимается и не подсвечивается).
    Раньше — плоский жёлтый прямоугольник."""
    import math
    from .art import draw_text, poly, GOLD
    rect = pygame.Rect(rect)
    draw(surf, "button_orange", rect)
    glaze = hd.Surface(rect.size, pygame.SRCALPHA)
    glaze.fill((0, 0, 0, 0))
    pygame.draw.rect(glaze, (255, 236, 150, 70), glaze.get_rect(), border_radius=max(4, rect.h // 3))
    surf.blit(glaze, rect.topleft)
    draw_text(surf, text, size, (rect.centerx, rect.centery - 1))
    for sx in (rect.x + 20, rect.right - 20):
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            rr = 8 if i % 2 == 0 else 3.6
            pts.append((sx + math.cos(a) * rr, rect.centery - 1 + math.sin(a) * rr))
        poly(surf, GOLD, pts, 2)
