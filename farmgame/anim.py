# -*- coding: utf-8 -*-
"""Плавность: кривые движения (easing) и «догонялки» значений. Всё — чистая математика, без pygame."""
import math


def clamp01(t):
    return 0.0 if t <= 0 else 1.0 if t >= 1 else t


def ease_out_cubic(t):
    t = clamp01(t)
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = clamp01(t)
    return 3 * t * t - 2 * t * t * t


def ease_out_back(t, s=1.2):
    """Выезжает чуть дальше и мягко возвращается (пружинка). s — сила перелёта (1.2 — едва заметно)."""
    t = clamp01(t) - 1
    return 1 + t * t * ((s + 1) * t + s)


def approach(cur, target, rate, dt):
    """Плавно подтягивает cur к target: за 1/rate секунды проходит ~63% пути. Не зависит от частоты кадров."""
    return target + (cur - target) * math.exp(-rate * max(0.0, dt))


def bezier(p0, p1, p2, t):
    """Точка на дуге (квадратичная кривая Безье): p0 — старт, p1 — «вершина», p2 — финиш."""
    u = 1 - t
    return (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])
