# -*- coding: utf-8 -*-
"""HD-режим: игра «думает» в координатах 1000x640, а рисует сразу в разрешении экрана.

Как это устроено:
  * HiSurf — поверхность, которая снаружи выглядит как 1000x640 (get_size, get_rect, координаты blit
    и рисования — логические), а внутри хранит настоящую картинку в K раз больше;
  * pygame.draw.* и pygame.transform.* подменяются обёртками: если им дали HiSurf, координаты, толщины
    и радиусы умножаются на K, иначе всё работает как обычно (spritefit и шаблоны этого не замечают);
  * шрифт рендерится крупным (art.render_text), спрайты подгоняются в K раз крупнее (spritefit.FIT_SCALE),
    фоны берутся в полном качестве.
K = 1 — HD выключен, всё как раньше (обычные pygame.Surface, никаких подмен).
"""
import sys

import pygame

K = [1.0]
MAX_SCALE = 2.0      # выше — картинка уже не станет заметно чётче, а кадр рисуется дольше (4K-экраны)
MIN_SCALE = 1.15     # меньше — HD не нужен (маленький экран)
_orig = {}
_warned = set()


def scale():
    return K[0]


def _pt(p, k):
    return (int(round(p[0] * k)), int(round(p[1] * k)))


def _w(width, k):
    return 0 if not width else max(1, int(round(width * k)))


def phys_rect(r, k):
    r = pygame.Rect(r)
    x0, y0 = int(round(r.x * k)), int(round(r.y * k))
    x1, y1 = int(round((r.x + r.w) * k)), int(round((r.y + r.h) * k))
    return pygame.Rect(x0, y0, max(0, x1 - x0), max(0, y1 - y0))


_ANCH_X = {"left": 0, "right": 1, "centerx": 0.5, "x": 0}
_ANCH = {"center": (.5, .5), "midleft": (0, .5), "midright": (1, .5), "midtop": (.5, 0), "midbottom": (.5, 1),
         "topleft": (0, 0), "topright": (1, 0), "bottomleft": (0, 1), "bottomright": (1, 1)}


def anchored_rect(w, h, **kw):
    """Rect(0, 0, w, h), сдвинутый по якорю (center=..., midbottom=..., topleft=... и т. п.)."""
    x, y = 0, 0
    for key, v in kw.items():
        if key in _ANCH:
            fx, fy = _ANCH[key]
            x = int(v[0]) - (w // 2 if fx == .5 else int(w * fx))
            y = int(v[1]) - (h // 2 if fy == .5 else int(h * fy))
        elif key in ("x", "left"):
            x = int(v)
        elif key in ("y", "top"):
            y = int(v)
        elif key == "right":
            x = int(v) - w
        elif key == "bottom":
            y = int(v) - h
        elif key == "centerx":
            x = int(v) - w // 2
        elif key == "centery":
            y = int(v) - h // 2
    return pygame.Rect(x, y, w, h)


class HiSurf:
    """Поверхность в логических координатах; .surf — настоящая, в k раз больше."""
    __slots__ = ("surf", "k", "_size")

    def __init__(self, surf, k=None, size=None):
        self.surf = surf
        self.k = k or K[0]
        if size is None:
            w, h = surf.get_size()
            size = (max(1, int(round(w / self.k))), max(1, int(round(h / self.k))))
        self._size = (int(size[0]), int(size[1]))

    def get_size(self):
        return self._size

    def get_width(self):
        return self._size[0]

    def get_height(self):
        return self._size[1]

    def get_rect(self, **kw):
        return anchored_rect(self._size[0], self._size[1], **kw)

    def fill(self, color, rect=None):
        if rect is None:
            return self.surf.fill(color)
        return self.surf.fill(color, phys_rect(rect, self.k))

    def blit(self, src, dest, area=None, special_flags=0):
        if isinstance(dest, pygame.Rect):
            x, y = dest.x, dest.y
        else:
            x, y = dest[0], dest[1]
        real = physical(src, self.k)
        pos = _pt((x, y), self.k)
        if area is None and not special_flags:
            self.surf.blit(real, pos)
        else:
            self.surf.blit(real, pos, phys_rect(area, self.k) if area is not None else None, special_flags)
        return pygame.Rect(int(x), int(y), *(src.get_size() if hasattr(src, "get_size") else (0, 0)))

    def copy(self):
        return HiSurf(self.surf.copy(), self.k, self._size)

    def convert_alpha(self):
        try:
            return HiSurf(self.surf.convert_alpha(), self.k, self._size)
        except Exception:
            return self

    def convert(self):
        return self.convert_alpha()


def real(s):
    """Настоящая pygame.Surface (для пиксельной работы: spritefit.Pix и т. п.)."""
    return s.surf if isinstance(s, HiSurf) else s


def physical(src, k):
    """Картинку-источник для blit на HiSurf: HiSurf — как есть; обычную считаем логической и увеличиваем.
    (Так быть не должно — пишем в консоль один раз, чтобы найти место.)"""
    if isinstance(src, HiSurf):
        return src.surf
    if k == 1:
        return src
    key = id(src)
    if key not in _warned:
        _warned.add(key)
        print("HD: обычная картинка нарисована на HD-поверхности, увеличиваю на лету", src.get_size())
    w, h = src.get_size()
    return _orig["smoothscale"](src, (max(1, int(round(w * k))), max(1, int(round(h * k)))))


def Surface(size, flags=0):
    """Новая поверхность размером size в логических координатах (в HD — HiSurf)."""
    k = K[0]
    if k == 1:
        return pygame.Surface(size, flags)
    w, h = int(size[0]), int(size[1])
    return HiSurf(pygame.Surface((max(1, int(round(w * k))), max(1, int(round(h * k)))), flags), k, (w, h))


def wrap(img):
    """Картинку физического размера (уже подогнанную в K раз крупнее) — в HiSurf."""
    if img is None or K[0] == 1 or isinstance(img, HiSurf):
        return img
    return HiSurf(img, K[0])


def to_logical(img):
    """HiSurf -> обычная поверхность логического размера (для курсора мыши)."""
    if not isinstance(img, HiSurf):
        return img
    return _orig["smoothscale"](img.surf, img.get_size())


# ----------------------------------------------------------------------
#                 подмены pygame.draw / transform / mouse
# ----------------------------------------------------------------------
def _back(r, k):
    """Прямоугольник, который вернул pygame.draw, — обратно в логические координаты."""
    try:
        return pygame.Rect(int(r.x / k), int(r.y / k), int(r.w / k) + 1, int(r.h / k) + 1)
    except Exception:
        return r


def _draw_rect(surf, color, rect, width=0, border_radius=0, *a, **kw):
    if isinstance(surf, HiSurf):
        k = surf.k
        kw = {key: (int(round(v * k)) if isinstance(v, (int, float)) and v > 0 else v) for key, v in kw.items()}
        a = tuple(int(round(v * k)) if isinstance(v, (int, float)) and v > 0 else v for v in a)
        r = _orig["rect"](surf.surf, color, phys_rect(rect, k), _w(width, k),
                          int(round(border_radius * k)) if border_radius > 0 else border_radius, *a, **kw)
        return _back(r, k)
    return _orig["rect"](surf, color, rect, width, border_radius, *a, **kw)


def _draw_line(surf, color, start, end, width=1):
    if isinstance(surf, HiSurf):
        k = surf.k
        return _back(_orig["line"](surf.surf, color, _pt(start, k), _pt(end, k), _w(width, k)), k)
    return _orig["line"](surf, color, start, end, width)


def _draw_lines(surf, color, closed, points, width=1):
    if isinstance(surf, HiSurf):
        k = surf.k
        return _back(_orig["lines"](surf.surf, color, closed, [_pt(p, k) for p in points], _w(width, k)), k)
    return _orig["lines"](surf, color, closed, points, width)


def _draw_polygon(surf, color, points, width=0):
    if isinstance(surf, HiSurf):
        k = surf.k
        return _back(_orig["polygon"](surf.surf, color, [_pt(p, k) for p in points], _w(width, k)), k)
    return _orig["polygon"](surf, color, points, width)


def _draw_circle(surf, color, center, radius, width=0, *a, **kw):
    if isinstance(surf, HiSurf):
        k = surf.k
        rad = max(1, int(round(radius * k))) if radius > 0 else 0
        return _back(_orig["circle"](surf.surf, color, _pt(center, k), rad, _w(width, k), *a, **kw), k)
    return _orig["circle"](surf, color, center, radius, width, *a, **kw)


def _draw_ellipse(surf, color, rect, width=0):
    if isinstance(surf, HiSurf):
        k = surf.k
        return _back(_orig["ellipse"](surf.surf, color, phys_rect(rect, k), _w(width, k)), k)
    return _orig["ellipse"](surf, color, rect, width)


def _draw_arc(surf, color, rect, start, stop, width=1):
    if isinstance(surf, HiSurf):
        k = surf.k
        return _back(_orig["arc"](surf.surf, color, phys_rect(rect, k), start, stop, _w(width, k)), k)
    return _orig["arc"](surf, color, rect, start, stop, width)


def _tr_smoothscale(surf, size, *a):
    if isinstance(surf, HiSurf):
        k = surf.k
        phys = (max(1, int(round(size[0] * k))), max(1, int(round(size[1] * k))))
        return HiSurf(_orig["smoothscale"](surf.surf, phys), k, (int(size[0]), int(size[1])))
    return _orig["smoothscale"](surf, size, *a)


def _tr_scale(surf, size, *a):
    if isinstance(surf, HiSurf):
        k = surf.k
        phys = (max(1, int(round(size[0] * k))), max(1, int(round(size[1] * k))))
        return HiSurf(_orig["scale"](surf.surf, phys), k, (int(size[0]), int(size[1])))
    return _orig["scale"](surf, size, *a)


def _tr_rotate(surf, angle):
    if isinstance(surf, HiSurf):
        return HiSurf(_orig["rotate"](surf.surf, angle), surf.k)
    return _orig["rotate"](surf, angle)


def _tr_flip(surf, fx, fy):
    if isinstance(surf, HiSurf):
        return HiSurf(_orig["flip"](surf.surf, fx, fy), surf.k, surf.get_size())
    return _orig["flip"](surf, fx, fy)


OFFSET = [0, 0]      # 3.10: где в окне начинается картинка игры (полный экран с полями по краям)


def _mouse_get_pos():
    x, y = _orig["get_pos"]()
    k = K[0]
    return int((x - OFFSET[0]) / k), int((y - OFFSET[1]) / k)


def to_logical_pos(pos):
    k = K[0]
    return int((pos[0] - OFFSET[0]) / k), int((pos[1] - OFFSET[1]) / k)


def set_offset(ox, oy):
    """Картинка игры сдвинута в окне на (ox, oy) настоящих пикселей: мышь пересчитывается с учётом сдвига."""
    OFFSET[0], OFFSET[1] = int(ox), int(oy)
    if "get_pos" not in _orig:          # без HD мышь не подменялась — подменяем сейчас
        _orig["get_pos"] = pygame.mouse.get_pos
        pygame.mouse.get_pos = _mouse_get_pos


class plain_scale:
    """with hd.plain_scale(): ... — временно обычная чёткость (выгрузка шаблонов 1:1 из запущенной игры)."""

    def __enter__(self):
        self.k = K[0]
        K[0] = 1.0
        return self

    def __exit__(self, *exc):
        K[0] = self.k
        return False


def install(k):
    """Включить HD с масштабом k (до создания окна и загрузки картинок)."""
    K[0] = float(k)
    if k == 1 or _orig:
        return
    for name, fn in (("rect", _draw_rect), ("line", _draw_line), ("lines", _draw_lines), ("polygon", _draw_polygon),
                     ("circle", _draw_circle), ("ellipse", _draw_ellipse), ("arc", _draw_arc)):
        _orig[name] = getattr(pygame.draw, name)
        setattr(pygame.draw, name, fn)
    for name, fn in (("smoothscale", _tr_smoothscale), ("scale", _tr_scale), ("rotate", _tr_rotate),
                     ("flip", _tr_flip)):
        _orig[name] = getattr(pygame.transform, name)
        setattr(pygame.transform, name, fn)
    _orig["get_pos"] = pygame.mouse.get_pos
    pygame.mouse.get_pos = _mouse_get_pos


def make_dpi_aware():
    """Windows с масштабом 125%/150%: без этого система растягивает окно игры сама — мыльно.
    Вызывать ДО pygame.init(). True — получилось (тогда размеры экрана — настоящие пиксели)."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        try:
            return ctypes.windll.shcore.SetProcessDpiAwareness(1) == 0     # 0 = S_OK
        except Exception:
            return bool(ctypes.windll.user32.SetProcessDPIAware())
    except Exception:
        return False


def dpi_scale():
    """Масштаб Windows (1.0 = 100%, 1.5 = 150%). Нужен, чтобы курсор был привычного размера."""
    if sys.platform != "win32":
        return 1.0
    try:
        import ctypes
        try:
            dpi = ctypes.windll.user32.GetDpiForSystem()
        except Exception:
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)               # LOGPIXELSX
            ctypes.windll.user32.ReleaseDC(0, hdc)
        return max(1.0, min(3.0, dpi / 96.0)) if dpi else 1.0
    except Exception:
        return 1.0


def work_area():
    """Сколько места есть под окно: рабочий стол без панели задач и без заголовка окна. -> (w, h) или None."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            u = ctypes.windll.user32
            r = wintypes.RECT()
            if u.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0):           # SPI_GETWORKAREA
                title = u.GetSystemMetrics(4) + 2 * u.GetSystemMetrics(33) + 2 * u.GetSystemMetrics(92)
                side = 2 * u.GetSystemMetrics(32) + 2 * u.GetSystemMetrics(92)
                return r.right - r.left - side, r.bottom - r.top - title
        except Exception:
            pass
    sizes = None
    try:
        sizes = pygame.display.get_desktop_sizes()
    except Exception:
        sizes = None
    if sizes:
        dw, dh = sizes[0]
    else:
        try:
            info = pygame.display.Info()
            dw, dh = info.current_w, info.current_h
        except Exception:
            return None
    if not dw or not dh or dw <= 0 or dh <= 0:
        return None
    return int(dw * 0.98), int(dh * 0.9)      # примерно: панель задач и заголовок окна


def choose_scale(w, h, cap=MAX_SCALE):
    """Масштаб HD: самое большое окно, которое целиком влезает на экран (вместе с заголовком).
    Во весь экран (F11) картинка потом растягивается совсем чуть-чуть. Маленький экран — 1 (HD не нужен)."""
    area = work_area()
    if not area:
        return 1.0
    k = min(area[0] / w, area[1] / h)
    if k < MIN_SCALE:
        return 1.0
    return int(min(k, cap) * 100) / 100.0     # вниз до сотых: окно точно влезет
