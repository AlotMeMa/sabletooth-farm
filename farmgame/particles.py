# -*- coding: utf-8 -*-
"""Частицы: монетки, летящие в счётчик, искорки и прочие мелкие эффекты.

Одна система на всю игру (App.fx). Частиц не больше MAX_PARTICLES — чтобы держать кадры.
Время — настоящее (не ускоряется в режиме разработчика), координаты — игровые (1000x640).
"""
import math
import random

import pygame

from . import anim
from . import hd

MAX_PARTICLES = 300
_soft = {}          # мягкие кружки/тени с прозрачностью: (вид, размеры, цвет, прозрачность) -> картинка


def soft_dot(r, color, alpha):
    """Мягкий полупрозрачный кружок радиуса r (пыль, пар). pygame.draw не смешивает прозрачность,
    поэтому кружок рисуется в отдельную картинку и кладётся поверх. Картинки кэшируются."""
    r = max(1, int(round(r)))
    alpha = max(0, min(255, int(alpha) // 16 * 16))
    key = ("dot", r, color, alpha)
    img = _soft.get(key)
    if img is None:
        img = hd.Surface((2 * r + 2, 2 * r + 2), pygame.SRCALPHA)
        img.fill((0, 0, 0, 0))
        pygame.draw.circle(img, color + (alpha // 2,), (r + 1, r + 1), r)
        pygame.draw.circle(img, color + (alpha,), (r + 1, r + 1), max(1, int(r * 0.7)))
        if len(_soft) > 600:
            _soft.clear()
        _soft[key] = img
    return img


def soft_shadow(w, h, alpha=70, color=(40, 50, 25)):
    """Мягкая тень-овал под существом или машиной (три кольца — край растушёван)."""
    w, h = max(4, int(round(w / 2)) * 2), max(2, int(round(h / 2)) * 2)
    alpha = max(0, min(255, int(alpha) // 8 * 8))
    key = ("shadow", w, h, alpha, color)
    img = _soft.get(key)
    if img is None:
        img = hd.Surface((w, h), pygame.SRCALPHA)
        img.fill((0, 0, 0, 0))
        for k, a in ((1.0, 0.35), (0.8, 0.65), (0.6, 1.0)):
            rw, rh = max(2, int(w * k)), max(1, int(h * k))
            pygame.draw.ellipse(img, color + (int(alpha * a),), ((w - rw) // 2, (h - rh) // 2, rw, rh))
        if len(_soft) > 600:
            _soft.clear()
        _soft[key] = img
    return img


def draw_shadow(surf, x, y, w, h, alpha=70):
    """Тень с центром в (x, y)."""
    if w < 2 or h < 1 or alpha <= 0:
        return
    img = soft_shadow(w, h, alpha)
    surf.blit(img, (int(round(x - img.get_width() / 2)), int(round(y - img.get_height() / 2))))


def fx_image(name, color=None):
    """3.16: картинка частицы assets/fx/<name> (лист fx/sheet), перекрашенная умножением в color.
    Светлые частицы (пыль, искра) рисуй белыми — так их можно красить. None — картинки нет."""
    from .art import sprite
    img = sprite("fx/" + name)
    if img is None or color is None:
        return img
    key = ("fx", name, tuple(color[:3]), id(img))
    out = _soft.get(key)
    if out is None:
        out = img.copy()
        hd.real(out).fill(tuple(color[:3]) + (255,), special_flags=pygame.BLEND_RGBA_MULT)
        _soft[key] = out
    return out


def _blit_fx(surf, img, x, y, size, alpha=255, angle=0.0):
    """Картинка частицы по центру (x, y), шириной size логических px, прозрачность alpha, поворот angle."""
    w = img.get_width()
    k = max(0.05, size / max(1, w))
    out = pygame.transform.smoothscale(img, (max(1, int(round(w * k))), max(1, int(round(img.get_height() * k)))))
    if abs(angle) > 0.5:
        out = pygame.transform.rotate(out, angle)
    if alpha < 255:
        hd.real(out).set_alpha(max(0, int(alpha)))
    surf.blit(out, (int(round(x - out.get_width() / 2)), int(round(y - out.get_height() / 2))))


class Particles:
    def __init__(self):
        self.items = []

    def __len__(self):
        return len(self.items)

    def clear(self):
        for p in self.items:          # монетки, которые не долетели, всё равно «засчитываем»
            if p.get("arrive"):
                p["arrive"]()
        self.items = []

    def _add(self, p):
        if len(self.items) >= MAX_PARTICLES:
            return False
        self.items.append(p)
        return True

    # ---------------------------------------------------------- виды частиц
    def fly(self, start, end, draw, dur=0.65, delay=0.0, arrive=None, lift=90.0, spread=30.0, size=1.0, shrink=0.7):
        """Предмет летит дугой из start в end (монетка в счётчик денег и т. п.).
        draw(surf, x, y, scale) рисует предмет; arrive() вызывается, когда долетел."""
        sx, sy = start
        ex, ey = end
        mid = ((sx + ex) / 2 + random.uniform(-spread, spread), min(sy, ey) - lift + random.uniform(-20, 20))
        p = dict(kind="fly", p0=(sx, sy), p1=mid, p2=(ex, ey), t=-delay, dur=dur, draw=draw, arrive=arrive,
                 size=size, shrink=shrink)
        if not self._add(p) and arrive:
            arrive()

    def sparks(self, x, y, n=5, colors=((255, 230, 120), (255, 255, 230)), speed=(40, 110), life=(0.25, 0.45),
               size=(2, 4), gravity=60.0, up=0.0):
        """Мягкие искорки во все стороны (up > 0 — с уклоном вверх)."""
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(*speed)
            ln = random.uniform(*life)
            self._add(dict(kind="spark", x=x, y=y, vx=math.cos(a) * v, vy=math.sin(a) * v - up, g=gravity,
                           t=0.0, life=ln, r=random.uniform(*size), color=random.choice(colors)))

    def ring(self, x, y, r0=8, r1=60, life=0.5, color=(255, 225, 110), width=3, flat=0.55):
        """Расходящееся кольцо (сплюснутое — как будто лежит на земле)."""
        self._add(dict(kind="ring", x=x, y=y, r0=r0, r1=r1, t=0.0, life=life, color=color, w=width, flat=flat))

    def splash(self, x, y, color=(170, 210, 245)):
        """Капля дождя ударилась о землю: маленький расходящийся овал и две брызги вверх."""
        if len(self.items) > MAX_PARTICLES - 40:     # в ливень не забиваем всё брызгами
            return
        self._add(dict(kind="ring", x=x, y=y, r0=2, r1=9, t=0.0, life=0.25, color=color, w=1, flat=0.4))
        for side in (-1, 1):
            self._add(dict(kind="spark", x=x, y=y, vx=side * random.uniform(15, 35), vy=-random.uniform(50, 90),
                           g=420.0, t=0.0, life=0.22, r=1.2, color=color))

    def dust(self, x, y, n=3, color=(214, 196, 150), size=(4, 7), spread=10, up=12, life=(0.35, 0.55), alpha=150,
             drift=0.0):
        """Облачко пыли у земли (прыжок белки, шаг разбойника, колёса). drift — сдвиг вбок (против движения)."""
        if len(self.items) > MAX_PARTICLES - 30:
            return
        for _ in range(n):
            r = random.uniform(*size)
            self._add(dict(kind="puff", x=x + random.uniform(-spread, spread), y=y - random.uniform(0, 3),
                           vx=drift + random.uniform(-12, 12), vy=-random.uniform(up * 0.5, up), t=0.0,
                           life=random.uniform(*life), r0=r * 0.6, r1=r * 1.5, color=color, alpha=alpha))

    def feathers(self, x, y, n=5, color=(68, 68, 86), vein=(135, 135, 155)):
        """Перья кружатся и плавно падают (ворону прогнали)."""
        for _ in range(n):
            self._add(dict(kind="feather", x=x + random.uniform(-14, 14), y=y + random.uniform(-14, 8), x0=0.0,
                           vy=random.uniform(22, 38), vx=random.uniform(-40, 40), ph=random.uniform(0, 6.3),
                           sw=random.uniform(10, 18), t=0.0, life=random.uniform(1.4, 2.0),
                           ln=random.uniform(15, 20), color=color, vein=vein))

    def drop(self, x, y, draw, ground, vx=0.0, vy=-160.0, life=1.0, size=1.0):
        """Предмет падает с подскоком (монетка выпала из мешка) и тает. ground — где земля."""
        self._add(dict(kind="drop", x=x, y=y, vx=vx, vy=vy, g=900.0, ground=ground, t=0.0, life=life,
                       draw=draw, size=size, bounced=False))

    def twinkle(self, x, y, r=6, color=(255, 245, 170), life=0.5):
        """Звёздочка-блик: вспыхивает и гаснет (золотая белка)."""
        self._add(dict(kind="twinkle", x=x, y=y, r=r, t=0.0, life=life, color=color))

    # ---------------------------------------------------------- кадр
    def update(self, dt):
        alive = []
        for p in self.items:
            p["t"] += dt
            if p["kind"] == "fly":
                if p["t"] >= p["dur"]:
                    if p["arrive"]:
                        p["arrive"]()
                    continue
            elif p["kind"] in ("ring", "twinkle"):
                if p["t"] >= p["life"]:
                    continue
            elif p["kind"] == "puff":
                if p["t"] >= p["life"]:
                    continue
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["vx"] *= max(0.0, 1 - 3 * dt)
                p["vy"] *= max(0.0, 1 - 2 * dt)
            elif p["kind"] == "feather":
                if p["t"] >= p["life"]:
                    continue
                p["y"] += p["vy"] * dt
                p["x0"] += p["vx"] * dt
                p["vx"] *= max(0.0, 1 - 1.5 * dt)
            elif p["kind"] == "drop":
                if p["t"] >= p["life"]:
                    continue
                p["vy"] += p["g"] * dt
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                if p["y"] >= p["ground"] and p["vy"] > 0:
                    p["y"] = p["ground"]
                    if p["bounced"]:
                        p["vy"], p["vx"] = 0.0, p["vx"] * 0.5
                        p["g"] = 0.0
                    else:
                        p["vy"], p["vx"], p["bounced"] = -p["vy"] * 0.35, p["vx"] * 0.6, True
            else:
                if p["t"] >= p["life"]:
                    continue
                p["vy"] += p["g"] * dt
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
            alive.append(p)
        self.items = alive

    def draw(self, surf):
        for p in self.items:
            if p["kind"] == "fly":
                if p["t"] < 0:
                    continue
                k = anim.ease_in_out(p["t"] / p["dur"])
                x, y = anim.bezier(p["p0"], p["p1"], p["p2"], k)
                p["draw"](surf, x, y, p["size"] * (1 - (1 - p["shrink"]) * k))
            elif p["kind"] == "ring":
                k = anim.ease_out_cubic(p["t"] / p["life"])
                r = p["r0"] + (p["r1"] - p["r0"]) * k
                w = max(1, int(round(p["w"] * (1 - k) + 0.5)))
                rect = pygame.Rect(0, 0, max(2, int(r * 2)), max(2, int(r * 2 * p["flat"])))
                rect.center = (int(round(p["x"])), int(round(p["y"])))
                pygame.draw.ellipse(surf, p["color"], rect, w)
            elif p["kind"] == "puff":
                k = p["t"] / p["life"]
                r = p["r0"] + (p["r1"] - p["r0"]) * anim.ease_out_cubic(k)
                pic = fx_image("puff", p["color"])
                if pic is not None:
                    _blit_fx(surf, pic, p["x"], p["y"], r * 2.6, p["alpha"] * (1 - k))
                    continue
                img = soft_dot(r, p["color"], p["alpha"] * (1 - k))
                surf.blit(img, (int(round(p["x"] - img.get_width() / 2)), int(round(p["y"] - img.get_height() / 2))))
            elif p["kind"] == "feather":
                self._draw_feather(surf, p)
            elif p["kind"] == "drop":
                k = p["t"] / p["life"]
                fade = 1.0 if k < 0.7 else max(0.0, 1 - (k - 0.7) / 0.3)
                if fade > 0.05:
                    p["draw"](surf, p["x"], p["y"], p["size"] * (0.4 + 0.6 * fade))
            elif p["kind"] == "twinkle":
                k = p["t"] / p["life"]
                r = p["r"] * math.sin(math.pi * k)
                pic = fx_image("star")
                if pic is not None:
                    if r >= 0.5:
                        _blit_fx(surf, pic, p["x"], p["y"], r * 4.2, 255, k * 60)
                    continue
                if r >= 1:
                    x, y, c = p["x"], p["y"], p["color"]
                    pts = [(x, y - r * 1.7), (x + r * 0.4, y - r * 0.4), (x + r * 1.7, y), (x + r * 0.4, y + r * 0.4),
                           (x, y + r * 1.7), (x - r * 0.4, y + r * 0.4), (x - r * 1.7, y), (x - r * 0.4, y - r * 0.4)]
                    pygame.draw.polygon(surf, c, [(int(round(a)), int(round(b))) for a, b in pts])
            else:
                k = p["t"] / p["life"]
                pic = fx_image("spark", p["color"]) if p["r"] >= 1.8 else None   # брызги дождя — точками
                if pic is not None:
                    _blit_fx(surf, pic, p["x"], p["y"], p["r"] * (1 - k * 0.6) * 3.4, 255 * min(1.0, 2.5 * (1 - k)))
                    continue
                r = max(1, int(round(p["r"] * (1 - k * 0.6))))
                c = p["color"]
                pygame.draw.circle(surf, c, (int(round(p["x"])), int(round(p["y"]))), r)

    @staticmethod
    def _draw_feather(surf, p):
        """Перо: вытянутый ромб с тёмным контуром, раскачивается как маятник и кружится."""
        k = p["t"] / p["life"]
        sway = math.sin(p["t"] * 3.2 + p["ph"])
        x = p["x"] + p["x0"] + sway * p["sw"]
        y = p["y"] + abs(sway) * 3                       # на краях размаха перо чуть приподнимается
        ang = math.radians(90 + sway * 50 + p["t"] * 40)
        ln = p["ln"] * (1.0 if k < 0.8 else max(0.0, 1 - (k - 0.8) / 0.2))
        if ln < 2:
            return
        pic = fx_image("feather")                        # 3.16: своё перо fx/feather (лежит по диагонали)
        if pic is not None:
            _blit_fx(surf, pic, x, y, ln * 1.3, 255, -math.degrees(ang) - 45)
            return
        dx, dy = math.cos(ang), math.sin(ang)
        nx, ny = -dy, dx
        wd = ln * 0.17
        pts = [(x - dx * ln / 2, y - dy * ln / 2), (x + nx * wd, y + ny * wd), (x + dx * ln / 2, y + dy * ln / 2),
               (x - nx * wd, y - ny * wd)]
        pts = [(int(round(a)), int(round(b))) for a, b in pts]
        pygame.draw.polygon(surf, p["color"], pts)
        pygame.draw.polygon(surf, (30, 30, 40), pts, 1)
        pygame.draw.line(surf, p["vein"], pts[0], pts[2], 1)
