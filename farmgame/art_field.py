# -*- coding: utf-8 -*-
"""Поле: культуры, грядки, фон, передний забор, солнце и тучка, свет и подсветка, шлейф курсора.

Часть art.py (3.17: вынесено без изменений). Снаружи всё берётся как раньше: from .art import ...
"""
import math
import os
import random

import pygame

from . import spritefit
from . import hd
from .config import *  # noqa: F401,F403
from .art_world import *  # noqa: F401,F403


# ======================================================================
#          ПОЛЕ: грядки, растения, фон, забор (спрайт или рисунок кодом)
# ======================================================================
CROP_STAGE_K = {1: 0.94, 2: 1.2, 3: 1.6}   # размер процедурного растения на стадиях 1-3


# Картинки растений вписываются в холст 110×120 целиком, а грядка вмещает три растения.
# Поэтому в игре они рисуются уменьшенными — примерно как растения, нарисованные кодом.
CROP_SPRITE_K = 0.55


def crop_stage(grow):
    return 1 if grow < 0.34 else 2 if grow < 0.67 else 3


def draw_crop(s, k, x, y, kscale, grow=1.0, sway=0.0):
    """Одно растение культуры k в точке (x, y) — у основания стебля. sway — наклон на ветру, градусы."""
    key = CROP_KEYS[k]
    stage = crop_stage(grow)
    base = 1.6 * (0.5 + 0.5 * grow)
    if blit_sprite(s, f"crops/{FARM_ID[0]}/{key}_{stage}", x, y, kscale / base * CROP_SPRITE_K, sway=sway):
        return
    if blit_sprite(s, f"crops/{FARM_ID[0]}/{key}", x, y, kscale / 1.6 * CROP_SPRITE_K, sway=sway):
        return
    PLANTS[k](s, x, y, kscale)


def tile_corners_at(cx, cy, shrink=0.92):
    hw, hh = TW / 2 * shrink, TH / 2 * shrink
    return (cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)


def draw_soil_tile(s, cx, cy, locked):
    if blit_any(s, farm_names("tiles", "soil_locked" if locked else "soil"), cx, cy + 5, 1, "center"):
        return
    if THEME.get("pond"):                           # 3.36: Рыбацкая деревня — пруд за сеткой / болото
        from .art_fishing import draw_pond_tile
        draw_pond_tile(s, cx, cy, locked, tile_corners_at(cx, cy))
        return
    top, right, bottom, left = tile_corners_at(cx, cy)
    d = 10
    side = (150, 120, 95) if locked else THEME["soil_side"]
    poly(s, side, [left, bottom, (bottom[0], bottom[1] + d), (left[0], left[1] + d)])
    poly(s, tuple(max(0, c - 15) for c in side), [bottom, right, (right[0], right[1] + d), (bottom[0], bottom[1] + d)])
    poly(s, (196, 165, 130) if locked else THEME["soil"], [top, right, bottom, left], 3)
    furrow = (175, 145, 115) if locked else THEME["soil_dark"]
    for t in (0.3, 0.55, 0.8):
        a = (left[0] + (top[0] - left[0]) * t, left[1] + (top[1] - left[1]) * t)
        b = (bottom[0] + (right[0] - bottom[0]) * t, bottom[1] + (right[1] - bottom[1]) * t)
        pygame.draw.line(s, furrow, (P(a[0] + 6), P(a[1] + 3)), (P(b[0] - 6), P(b[1] - 3)), 3)


def build_field_background():
    """Фон поля. Если есть assets/backgrounds/<ферма>.png — он целиком (с амбаром и задним забором)."""
    bg = hd.Surface((W, H))
    img = sprite(f"backgrounds/{FARM_ID[0]}")
    if img is not None:
        bg.blit(pygame.transform.smoothscale(img, (W, H)) if img.get_size() != (W, H) else img, (0, 0))
        return bg
    th = THEME
    bg.fill(th["ground"])
    rnd = random.Random(7)
    for _ in range(40):
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        ellipse(bg, th["ground2"], x, y, rnd.randint(30, 90), rnd.randint(12, 30), ow=0)
    # песок (снег) под амбаром и дорога
    poly(bg, th["path"], [(70, 175), (320, 160), (440, 230), (200, 265)], 0)
    pygame.draw.rect(bg, th["path_edge"], (0, 546, W, 60))
    pygame.draw.rect(bg, th["path"], (0, 550, W, 52))
    for _ in range(25):
        ellipse(bg, th["path2"], rnd.randint(0, W), rnd.randint(556, 596), rnd.randint(14, 40), 6, ow=0)
    for x, y, w in ((300, 235, 34), (270, 262, 26), (205, 290, 30), (150, 330, 38), (120, 372, 30), (830, 330, 36), (860, 360, 28)):
        ellipse(bg, th["stone"], x, y, w, w * 0.55)
    for x, y in ((360, 470), (640, 480), (90, 420), (940, 300), (700, 150), (330, 140)):
        for a in (60, 90, 120):
            leaf(bg, x, y, a, 14, 5, th["tuft"])
    if THEME.get("castle"):
        draw_castle(bg, 715, 175)
    else:
        draw_tree(bg, 720, 150, 52)
    draw_tree(bg, 70, 520, 40)
    barn = hd.Surface((340, 230), pygame.SRCALPHA)
    (draw_windmill if THEME.get("building") == "mill" else draw_barn)(barn)
    bg.blit(barn, (60, 18))
    for x, y, r in ((900, 250, 26), (210, 430, 30), (950, 480, 24), (330, 520, 22), (640, 525, 22)):
        draw_bush(bg, x, y, r)
    if THEME.get("fence", True):
        oy = grid_oy()
        draw_fence(bg, (OX, oy - TH / 2), (OX + TW + TW / 2, oy + TH), (8, -14))   # задний забор
    return bg


FENCE_STRIP_H = {"fence": 36, "wall": 30}   # высота забора / каменной стены из картинки на экране, px
_fence_layers = {}


def front_fence_segments():
    """Два передних края поля, вдоль которых стоит забор: [(начало, конец)], x начала < x конца."""
    oy = grid_oy()
    left = (OX - TW - TW / 2, oy + TH)
    bottom = (OX, oy + 2 * TH + TH / 2)
    right = (OX + TW + TW / 2, oy + TH)
    return [((left[0] - 6, left[1] + 16), (bottom[0] - 30 - 6, bottom[1] - 15 + 16)),
            ((bottom[0] + 30 + 6, bottom[1] - 15 + 16), (right[0] + 6, right[1] + 16))]


def _seamless_crop(px, bb):
    """Кусок забора от нейросети редко «бесшовный»: поля слева и справа разные, и на стыке выходит двойной
    промежуток. Ищем штакетины/столбы по верхней полосе (там только они, перекладины ниже) и режем ровно
    посередине промежутков: от первого до последнего — тогда при повторе шаг везде одинаковый."""
    x0, y0, x1, y1 = bb
    band = (x0, y0, x1, y0 + max(2, int((y1 - y0) * 0.22)))
    occ = px.occupancy("x", band)
    runs, start = [], None
    for i, v in enumerate(occ + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= 2:
                runs.append((start, i))
            start = None
    if len(runs) < 3:
        return bb                                   # каменная стена и т. п. — режем как есть
    gaps = [(runs[n][1] + runs[n + 1][0]) // 2 for n in range(len(runs) - 1)]
    if gaps[-1] - gaps[0] < (x1 - x0) * 0.4:
        return bb
    return (x0 + gaps[0], y0, x0 + gaps[-1], y1)


SHADOW_DX, SHADOW_DY, SHADOW_ALPHA = 0.3, 0.5, 170   # 3.20: тень забора — вниз и чуть влево, полупрозрачная
FENCE_SUPERSAMPLE = 3   # наклон считаем в 3 раза крупнее и сглаживаем — без «лесенки» на перекладинах


def fence_supersample():
    """В HD экран и так крупнее: хватает 2-кратного запаса (иначе слой забора считается в разы дольше)."""
    return FENCE_SUPERSAMPLE if hd.K[0] < 1.4 else 2


def build_fence_strip_layer(strip):
    """Кусок забора анфас (props/<ферма>/fence_strip) -> слой забора вдоль передних краёв поля:
    кусок повторяется по длине и «наклоняется» столбиками пикселей по диагонали края. -> (картинка, позиция)."""
    from .spritefit import Pix, _frombytes
    px = Pix(hd.real(strip))
    bb = px.bbox()
    if bb is None:
        return None
    piece = px.surface(_seamless_crop(px, bb))
    kk = hd.K[0] * fence_supersample()            # во сколько раз крупнее экранных координат строим слой
    hgt = FENCE_STRIP_H["wall" if THEME.get("wall") else "fence"]
    hs = max(1, int(round(hgt * kk)))
    ws = max(1, int(round(piece.get_width() * hs / piece.get_height())))
    piece = hd._orig.get("smoothscale", pygame.transform.smoothscale)(piece, (ws, hs))
    src = Pix(piece)
    segs = front_fence_segments()
    x0 = int(min(a[0] for a, b in segs)) - int(hgt * SHADOW_DX) - 4
    x1 = int(max(b[0] for a, b in segs)) + 1
    y0 = int(min(min(a[1], b[1]) for a, b in segs)) - hgt - 2
    y1 = int(max(max(a[1], b[1]) for a, b in segs)) + int(hgt * SHADOW_DY) + 6
    ow, oh = int(round((x1 - x0) * kk)), int(round((y1 - y0) * kk))
    # прозрачные пиксели — цвета контура: при сглаживании край темнеет к контуру, а не к чёрному
    out = bytearray(bytes((70, 45, 35, 0)) * (ow * oh))
    shadow = bytearray(bytes((40, 52, 26, 0)) * (ow * oh))   # 3.20: тень забора на траве (солнце за полем)
    sb, sw = src.buf, src.w
    for (ax, ay), (bx, by) in segs:
        span = int(round((bx - ax) * kk))
        for x in range(span):
            sx = x % sw                                  # кусок повторяется по длине края
            base = int(round((ay - y0) * kk + (by - ay) * kk * x / span))   # низ забора в этом столбике
            ox = int(round((ax - x0) * kk)) + x
            if not 0 <= ox < ow:
                continue
            for y in range(hs):
                oy = base - hs + y
                si = (y * sw + sx) * 4
                if not sb[si + 3]:
                    continue
                if 0 <= oy < oh:
                    oi = (oy * ow + ox) * 4
                    out[oi:oi + 4] = sb[si:si + 4]
                up = hs - y                                  # высота точки над землёй -> куда падает её тень
                tx, ty = ox - int(up * SHADOW_DX), base + int(up * SHADOW_DY)
                if 0 <= tx < ow and 0 <= ty < oh:
                    shadow[(ty * ow + tx) * 4 + 3] = SHADOW_ALPHA
    scale = hd._orig.get("smoothscale", pygame.transform.smoothscale)
    pw, ph = max(1, int(round((x1 - x0) * hd.K[0]))), max(1, int(round((y1 - y0) * hd.K[0])))
    small = scale(_frombytes(out, (ow, oh)), (pw, ph))
    # тень мягкая: уменьшить в 5 раз и растянуть обратно — края размываются
    blur = scale(_frombytes(shadow, (ow, oh)), (max(1, pw // 5), max(1, ph // 5)))
    layer = pygame.Surface((pw, ph), pygame.SRCALPHA)
    layer.fill((0, 0, 0, 0))
    layer.blit(scale(blur, (pw, ph)), (0, 0))
    layer.blit(small, (0, 0))
    return hd.wrap(layer) if hd.K[0] != 1 else layer, (x0, y0)


_wide_front = {}


def _fence_front_as_strip(name):
    """props/.../fence_front, который на самом деле кусок забора (сильно вытянутая полоска, не 25:16):
    такую путаницу исправляем сами — берём файл как fence_strip. -> картинка или None."""
    if name in _wide_front:
        return _wide_front[name]
    out = None
    path = find_asset_file(name)
    if path and not is_template_copy(name, path):
        try:
            w, h = pygame.image.load(path).get_size()
            if w > 2.5 * h:
                print(f"assets/{name}: это кусок забора, а не слой во весь экран — беру его как fence_strip")
                out = hd.wrap(spritefit.load_fitted(name.replace("fence_front", "fence_strip"), path))
        except Exception as e:
            print(f"Забор {name}: {e}")
    _wide_front[name] = out
    return out


def draw_front_fence_layer(s):
    if not THEME.get("fence", True):          # 3.38.1: в Рыбацкой деревне забора нет — у прудов свои сетки
        return
    strips = []
    for name in farm_names("props", "fence_front"):
        wide = _fence_front_as_strip(name)
        if wide is not None:
            strips.append((name, wide))
            break
        if blit_sprite(s, name, 0, 0, 1, "topleft"):
            return
    for name in farm_names("props", "fence_strip"):
        strips.append((name, sprite(name)))
    for name, strip in strips:
        if strip is None:
            continue
        key = (name, id(strip))
        if key not in _fence_layers:
            try:
                _fence_layers[key] = build_fence_strip_layer(strip)
            except Exception as e:   # что-то не так с картинкой — рисуем забор кодом
                print(f"Забор из {name} не собрался: {e}")
                _fence_layers[key] = None
        layer = _fence_layers[key]
        if layer:
            s.blit(*layer)
            return
        break
    key = ("code", FARM_ID[0], hd.scale())
    if key not in _fence_layers:               # забор кодом не двигается — рисуем один раз
        layer = hd.Surface((W, H), pygame.SRCALPHA)
        layer.fill((0, 0, 0, 0))
        (a1, b1), (a2, b2) = front_fence_segments()
        hgt = FENCE_STRIP_H["wall" if THEME.get("wall") else "fence"]
        dx, dy = hgt * SHADOW_DX, hgt * SHADOW_DY
        for a, b in ((a1, b1), (a2, b2)):            # 3.20: тень на траве, как у забора-картинки
            pygame.draw.polygon(layer, (40, 52, 26, 80), [a, b, (b[0] - dx, b[1] + dy), (a[0] - dx, a[1] + dy)])
        draw_fence(layer, a1, b1, (0, 0))
        draw_fence(layer, a2, b2, (0, 0))
        _fence_layers[key] = (layer, (0, 0))
    s.blit(*_fence_layers[key])


def draw_sun_rays(s, x, y, t, strength=0.5):
    """Мягкие лучи за солнцем: медленно вращаются и «дышат». strength 0..1 — насколько ярко."""
    size = 250
    layer = hd.Surface((size, size), pygame.SRCALPHA)
    layer.fill((0, 0, 0, 0))
    c = size / 2
    alpha = int(40 + 50 * strength)
    for r in range(10):
        a = t * 0.12 + r * math.pi / 5
        ln = (86 + 24 * strength) * (1 + 0.08 * math.sin(t * 1.3 + r * 1.7))
        w = 0.11
        pts = [(c + math.cos(a - w) * 30, c + math.sin(a - w) * 30), (c + math.cos(a) * ln, c + math.sin(a) * ln),
               (c + math.cos(a + w) * 30, c + math.sin(a + w) * 30)]
        pygame.draw.polygon(layer, (255, 244, 170, alpha), pts)
    pygame.draw.circle(layer, (255, 248, 200, int(30 + 40 * strength)), (int(c), int(c)), 66)
    s.blit(layer, (int(x - c), int(y - c)))


def draw_sun_body(s, x, y, t):
    if blit_sprite(s, "props/sun", x, y, 1, "center"):
        return
    for r in range(12):
        a = t * 0.5 + r * math.pi / 6
        p1 = (x + math.cos(a - 0.13) * 36, y + math.sin(a - 0.13) * 36)
        p2 = (x + math.cos(a) * 50, y + math.sin(a) * 50)
        p3 = (x + math.cos(a + 0.13) * 36, y + math.sin(a + 0.13) * 36)
        poly(s, (255, 205, 50), [p1, p2, p3])
    blob(s, (255, 225, 70), [(x, y, 36)], 3)
    face(s, x, y + 2, 2.2)


def draw_cloud_body(s, x, y, raining):
    if blit_any(s, (["props/cloud_rain"] if raining else []) + ["props/cloud"], x, y, 1, "center"):
        return
    col = (205, 225, 245) if raining else WHITE
    blob(s, col, [(x - 34, y + 8, 24), (x - 8, y - 8, 32), (x + 26, y + 4, 26), (x, y + 14, 24)], 3)
    face(s, x - 4, y + 4, 2.0)


VEHICLE_OFFSET = {"truck": -5, "cart": -30, "sled": -30, "fishcart": -30, "boat": -10}   # 3.38.1: лодка   # 3.36: повозка рыботорговца   # 3.24: sled — собачья упряжка (зима)   # где середина низа картинки относительно точки (x, y) машины
VEHICLE_FAR = W + 400.0    # 3.26.2: откуда приезжает машина (за правым краем: длинная упряжка не «выскакивает»)
VEHICLE_WIDTH = {"sled_1": 430, "sled_2": 430}   # 3.26.2: длинные упряжки (по умолчанию 270): сани на том же месте, собаки — левее


def vehicle_shift(vehicle, tier):
    """Насколько середина картинки левее обычной: длинная упряжка растёт влево (сани стоят где и телега)."""
    key = f"{vehicle}_{tier}"
    if key in VEHICLE_WIDTH and has_sprite(f"vehicles/{key}"):
        return (VEHICLE_WIDTH[key] - 270) / 2
    return 0.0


def draw_vehicle_at(s, vehicle, tier, x, y, color, cargo=False, bob=0.0, angle=0.0, sy=1.0):
    """Машина (телега) смотрит влево. angle — наклон (+ — нос вниз), sy — осела на рессорах (3.3)."""
    names = ([f"vehicles/{vehicle}_{tier}_cargo"] if cargo else []) + [f"vehicles/{vehicle}_{tier}", f"vehicles/{vehicle}"]
    if blit_tf(s, names, x + VEHICLE_OFFSET[vehicle] - vehicle_shift(vehicle, tier), y + 4 - bob, 1, sy=sy, angle=angle):
        return
    if vehicle == "boat":                            # 3.38.1: лодка рыботорговца (Рыбацкая деревня)
        from .art_fishing import draw_boat
        draw_boat(s, x, y, tier, cargo, bob, pygame.time.get_ticks() / 1000)
        return
    (draw_cart if vehicle in ("cart", "sled", "fishcart") else draw_truck)(s, x, y, color, cargo and vehicle != "fishcart", bob)
    if vehicle == "fishcart" and cargo:              # 3.36: бочки и рыбьи хвосты над бортом
        from .art_fishing import draw_fish_cargo
        draw_fish_cargo(s, x, y - bob)


def draw_cursor_template(s, hover=False):
    """Шаблон курсора 40×40: стрелка, кончик ровно в левом верхнем углу (0, 0) — это точка клика."""
    fill = (255, 215, 90) if hover else (250, 244, 232)
    pts = [(1, 1), (1, 27), (8, 21), (13, 31), (18, 29), (13, 19), (22, 19)]
    pygame.draw.polygon(s, fill, pts)
    pygame.draw.polygon(s, OUT, pts, 2)
    if hover:   # искорка: «сюда можно нажать»
        poly(s, (255, 250, 200), [(29, 4), (31, 9), (36, 11), (31, 13), (29, 18), (27, 13), (22, 11), (27, 9)], 1)


_glows = {}


def blit_glow(surf, name, x, y, scale=1.0, color=(255, 248, 210), radius=4):
    """Светлый ореол по контуру спрайта (рисуется ДО самого спрайта, в той же точке, anchor=center)."""
    img = sprite(name)
    if img is None:
        return False
    scale = round(scale / SCALE_STEP) * SCALE_STEP or SCALE_STEP
    key = (name, round(scale, 3), color, radius)
    glow = _glows.get(key)
    if glow is None:
        base = img
        if abs(scale - 1.0) > 1e-3:
            base = pygame.transform.smoothscale(img, (max(1, int(img.get_width() * scale + 0.5)),
                                                      max(1, int(img.get_height() * scale + 0.5))))
        glow = spritefit.make_glow(base, color, radius)
        _glows[key] = glow
    surf.blit(glow, glow.get_rect(center=(int(round(x)), int(round(y)))))
    return True


_lights = {}
LIGHT_BASE = 96      # размер заготовки светового пятна (логические px)
LIGHT_CORE = 0.45    # доля радиуса с ровным светом (она почти вся под кнопкой)


def _light_disc(color, peak=240, core=LIGHT_CORE):
    """Круглое мягкое пятно света: ровно до core радиуса, дальше плавно в ноль. Считается один раз."""
    key = ("disc", color, peak, core)
    disc = _lights.get(key)
    if disc is None:
        n = LIGHT_BASE
        disc = hd.Surface((n, n), pygame.SRCALPHA)
        steps = 48
        for i in range(steps):              # от края к центру: каждый круг меньше и непрозрачнее
            t = 1 - i / steps                # 1 — край, 0 — центр
            u = max(0.0, (t - core) / (1 - core))
            a = int(peak * (1 - u * u * (3 - 2 * u)))
            pygame.draw.circle(disc, color + (a,), (n // 2, n // 2), max(1, int(n / 2 * t)))
        _lights[key] = disc
    return disc


def blit_light(surf, x, y, size, color=(255, 244, 200), peak=240, core=LIGHT_CORE):
    """Мягкое пятно света диаметром size с центром (x, y). Размер округляется до 4 px, яркость peak —
    до 16 ступеней: готовые пятна берутся из кэша, мерцание огня и подсветка кнопок не тормозят."""
    size = max(8, int(round(size / 4)) * 4)
    peak = max(16, min(255, int(peak) // 16 * 16))
    key = (color, size, peak, core)
    img = _lights.get(key)
    if img is None:
        img = pygame.transform.smoothscale(_light_disc(color, peak, core), (size, size))
        if len(_lights) > 300:
            _lights.clear()
        _lights[key] = img
    surf.blit(img, (int(round(x)) - size // 2, int(round(y)) - size // 2))


def blit_backlight(surf, x, y, size, color=(255, 244, 200)):
    """Подсветка «сзади» кнопки: рисуется ДО кнопки (3.4.1)."""
    blit_light(surf, x, y, size, color)


def draw_hover_ring(surf, rect, radius=10, color=(255, 248, 210)):
    """Подсветка кнопки: светлая рамка СНАРУЖИ чёрного контура (сам контур остаётся)."""
    r = pygame.Rect(rect).inflate(8, 8)
    pygame.draw.rect(surf, color, r, 3, border_radius=radius + 4)
    soft = hd.Surface((r.w + 8, r.h + 8), pygame.SRCALPHA)
    pygame.draw.rect(soft, color + (90,), soft.get_rect(), 4, border_radius=radius + 8)
    surf.blit(soft, (r.x - 4, r.y - 4))


RAINBOW = ((255, 90, 80), (255, 170, 60), (255, 225, 80), (110, 220, 120), (90, 180, 255), (180, 120, 255))


def draw_trail(surf, points, now, life=0.28, color=(255, 250, 225), stars=False, style=None):
    """Тонкий исчезающий шлейф за курсором. points = [(x, y, время)].
    Слой — только размером со сам шлейф (а не весь экран): в HD так заметно быстрее."""
    pts = [(x, y, now - t) for x, y, t in points if now - t < life]
    if len(pts) < 2:
        return
    pad = 8 if not style else 22
    lx, ly = int(min(p[0] for p in pts)) - pad, int(min(p[1] for p in pts)) - pad
    lw, lh = int(max(p[0] for p in pts)) - lx + pad + 1, int(max(p[1] for p in pts)) - ly + pad + 1
    layer = hd.Surface((lw, lh), pygame.SRCALPHA)
    layer.fill((0, 0, 0, 0))
    for (x0, y0, a0), (x1, y1, a1) in zip(pts, pts[1:]):
        k = 1 - max(a0, a1) / life               # 1 у курсора -> 0 в хвосте
        if k <= 0:
            continue
        width = max(1, int(1 + 4 * k))
        a, b = (x0 - lx, y0 - ly), (x1 - lx, y1 - ly)
        if style in ("leaves", "bubbles"):     # 3.33: «Листопад» и «Мыльные пузыри» — через отрезок, чтобы не сливались
            n = int(x0 * 0.7 + y0 * 1.3)
            if n % 2:
                continue
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + (1 - k) * 10 * (1 if style == "leaves" else -1)
            from .decor_art import trail_leaf, trail_bubble, TRAIL_LEAVES
            if style == "leaves":
                trail_leaf(layer, mx + math.sin(now * 5 + n) * 4 * (1 - k), my, k,
                           TRAIL_LEAVES[(n // 2) % len(TRAIL_LEAVES)], n * 0.7 + now * 3)
            else:
                trail_bubble(layer, mx, my, k, n)
            continue
        if stars:            # 3.27: джекпот «Звёздный шлейф» — разноцветные звёздочки вместо линии
            col = RAINBOW[int(x0 * 0.05 + y0 * 0.03 + now * 6) % len(RAINBOW)]
            r = 2 + 4 * k
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            pts4 = [(mx + math.cos(i * math.pi / 4) * (r if i % 2 == 0 else r * 0.4),
                     my + math.sin(i * math.pi / 4) * (r if i % 2 == 0 else r * 0.4)) for i in range(8)]
            pygame.draw.polygon(layer, col + (int(230 * k),), pts4)
            continue
        pygame.draw.line(layer, color + (int(40 * k),), a, b, width + 4)   # мягкое свечение
        pygame.draw.line(layer, color + (int(200 * k),), a, b, width)
    surf.blit(layer, (lx, ly))
