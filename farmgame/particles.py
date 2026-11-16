# -*- coding: utf-8 -*-
"""Частицы: монетки, летящие в счётчик, искорки и прочие мелкие эффекты.

Одна система на всю игру (App.fx). Частиц не больше MAX_PARTICLES — чтобы держать кадры.
Время — настоящее (не ускоряется в режиме разработчика), координаты — игровые (1000x640).
"""
import math
import random

import pygame

from . import anim

MAX_PARTICLES = 300


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
            elif p["kind"] == "ring":
                if p["t"] >= p["life"]:
                    continue
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
            else:
                k = p["t"] / p["life"]
                r = max(1, int(round(p["r"] * (1 - k * 0.6))))
                c = p["color"]
                pygame.draw.circle(surf, c, (int(round(p["x"])), int(round(p["y"]))), r)
