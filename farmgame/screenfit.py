# -*- coding: utf-8 -*-
"""3.10: полный экран без чёрных полос — сколько места добавить по краям (без pygame, проверяется тестами).

Игра рисует картинку canvas (пропорции 1000x640 = 1.5625). У экрана 16:9 пропорции шире, у 4:3 — уже.
Вместо чёрных полос окно в полном экране делается в пропорциях экрана, игра рисуется посередине,
а по краям — размытое зеркальное продолжение её же картинки (app.present_wide).
"""

MIN_MARGIN = 4      # меньше — полосы почти не видно: незачем городить


def wide_geometry(canvas, desktop):
    """((ширина, высота) окна в пропорциях экрана, (сдвиг x, сдвиг y) картинки игры) или None, если не нужно."""
    cw, ch = int(canvas[0]), int(canvas[1])
    dw, dh = int(desktop[0]), int(desktop[1])
    if cw <= 0 or ch <= 0 or dw <= 0 or dh <= 0:
        return None
    aspect = dw / dh
    if aspect >= cw / ch:                       # экран шире — поля слева и справа
        ww, wh = int(round(ch * aspect)), ch
    else:                                       # экран уже — поля сверху и снизу
        ww, wh = cw, int(round(cw / aspect))
    ox, oy = (ww - cw) // 2, (wh - ch) // 2
    if max(ox, oy) < MIN_MARGIN:
        return None
    return (ww, wh), (ox, oy)


def to_game(pos, offset, k):
    """Мышь в окне -> координаты игры 1000x640 (с учётом полей и HD-масштаба k)."""
    return int((pos[0] - offset[0]) / k), int((pos[1] - offset[1]) / k)
