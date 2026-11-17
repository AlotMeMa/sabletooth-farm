# -*- coding: utf-8 -*-
"""Вся графика: текст, примитивы, процедурные рисунки и загрузка спрайтов из assets/."""
import math
import os
import random

import pygame

from . import spritefit
from . import hd
from .config import *  # noqa: F401,F403


# ======================================================================
#                 СПРАЙТЫ: картинки из assets/ (если есть)
# ======================================================================
# Любой объект сначала ищет свою картинку в папке assets/ (см. docs/SPRITES.md).
# Если картинки нет — рисуется как раньше, кодом. Так графику можно менять по одному файлу.
USE_SPRITES = [True]
_sprite_cache = {}
_sprite_scaled = {}
SCALE_STEP = 0.02


IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def find_asset_file(name):
    """assets/<name>.png (или .jpg/.jpeg/.webp/.bmp, регистр букв не важен). None — если нет."""
    folder = os.path.join(ASSET_DIR, *name.split("/")[:-1])
    base = name.split("/")[-1].lower()
    if not os.path.isdir(folder):
        return None
    found = []
    for fn in sorted(os.listdir(folder)):
        stem, ext = os.path.splitext(fn)
        if stem.lower() == base and ext.lower() in IMAGE_EXTS:
            found.append(os.path.join(folder, fn))
    for path in found:          # два файла с одним именем (.png и .jpg): своя картинка важнее копии шаблона
        if not is_template_copy(name, path):
            return path
    return found[0] if found else None


def sprite(name):
    """PNG из assets/<name>.png или None. Загружается один раз."""
    if not USE_SPRITES[0]:
        return None
    if name in _sprite_cache:
        return _sprite_cache[name]
    img = None
    try:
        img = hd.wrap(_load_sprite(name))     # в HD картинка подогнана крупнее — снаружи она «логического» размера
    except Exception as e:  # битый файл не должен ронять игру
        print(f"Не удалось загрузить спрайт {name}: {e}")
        img = None
    _sprite_cache[name] = img
    return img


def is_template_copy(name, path):
    """True, если файл в assets/ — просто копия шаблона из assets_templates/ (байт в байт).
    Такие файлы игра пропускает: они ничего не меняют, но мешают полоскам и листам (их «перекрывают»)."""
    tpl = os.path.join(BASE_DIR, "assets_templates", *name.split("/")) + ".png"
    try:
        if not os.path.exists(tpl) or os.path.getsize(tpl) != os.path.getsize(path):
            return False
        with open(tpl, "rb") as a, open(path, "rb") as b:
            return a.read() == b.read()
    except OSError:
        return False


def _load_sprite(name):
    """Свой файл; иначе — стадия из полоски crops/<ферма>/<культура>.png или иконка из icons/sheet.png."""
    path = find_asset_file(name)
    if path and is_template_copy(name, path):
        path = None
    parts = name.split("/")
    if path:
        if parts[0] == "crops" and len(parts) == 3 and not parts[2][-2:] in ("_1", "_2", "_3"):
            if spritefit.is_strip(pygame.image.load(path), path):
                return sprite(name + "_3")      # одна картинка-полоска: показываем спелую стадию
        return spritefit.load_fitted(name, path)
    if parts[0] == "crops" and len(parts) == 3 and parts[2][-2:] in ("_1", "_2", "_3"):
        strip = find_asset_file(name[:-2])
        if strip and spritefit.is_strip(pygame.image.load(strip), strip):
            return spritefit.load_fitted(name, strip, ("strip", int(name[-1])))
        return None
    for sheet_name, (prefix, order) in spritefit.SHEETS.items():   # иконка/кнопка из листа 3×3
        if name.startswith(prefix) and name[len(prefix):] in order:
            sheet = find_asset_file(sheet_name)
            if sheet:
                return spritefit.load_fitted(name, sheet, ("sheet", order.index(name[len(prefix):]), prefix, order))
    return None


def extended_down(name, ext, from_frac=0.7):
    """Спрайт name, у которого низ продлён вниз на ext логических px: каждый столбец, дошедший ниже
    from_frac высоты, тянется своим цветом (чуть выше края) до нового низа. Так персонаж «по пояс»
    (бармен) уходит за стойку целиком — без щели под локтями. Имя результата: name + "#down".
    None — если картинки нет."""
    key = name + "#down"
    if key in _sprite_cache:
        return key if _sprite_cache[key] is not None else None
    img = sprite(name)
    if img is None:
        _sprite_cache[key] = None
        return None
    src = hd.real(img)
    k = hd.scale()
    px = spritefit.Pix(src)
    w, h, b = px.w, px.h, px.buf
    e = max(1, int(round(ext * k)))
    out = bytearray(b) + bytearray(w * e * 4)
    nh = h + e
    lift = max(1, int(round(2 * k)))
    for x in range(w):
        yb = -1
        for y in range(h - 1, -1, -1):
            if b[(y * w + x) * 4 + 3] > 128:
                yb = y
                break
        if yb < h * from_frac:
            continue
        sy = max(0, yb - lift)
        pix = bytes(b[(sy * w + x) * 4:(sy * w + x) * 4 + 3]) + b"\xff"
        for y in range(yb + 1, nh):
            i = (y * w + x) * 4
            out[i:i + 4] = pix
    surf = spritefit._frombytes(bytes(out), (w, nh))
    _sprite_cache[key] = hd.wrap(surf) if k != 1 else surf
    return key


def has_sprite(name):
    return sprite(name) is not None


def blit_sprite(surf, name, x, y, scale=1.0, anchor="midbottom", flip=False, angle=0.0, sway=0.0):
    """Рисует спрайт с привязкой anchor в точке (x, y). Возвращает False, если картинки нет.
    angle — повернуть вокруг центра; sway — наклонить (в градусах) вокруг низа картинки, как растение на ветру."""
    img = sprite(name)
    if img is None:
        return False
    # масштаб округляем до шага 2%: растущие растения меняют размер каждый кадр, а так
    # уменьшенная копия картинки берётся из кэша, а не пересчитывается заново
    scale = round(scale / SCALE_STEP) * SCALE_STEP or SCALE_STEP
    key = (name, round(scale, 3), flip)
    out = _sprite_scaled.get(key)
    if out is None:
        out = img
        if flip:
            out = pygame.transform.flip(out, True, False)
        if abs(scale - 1.0) > 1e-3:
            out = pygame.transform.smoothscale(out, (max(1, int(out.get_width() * scale + 0.5)),
                                                     max(1, int(out.get_height() * scale + 0.5))))
        if len(_sprite_scaled) > 3000:
            _sprite_scaled.clear()
        _sprite_scaled[key] = out
    if sway and anchor == "midbottom":
        # поворот вокруг середины низа: центр повёрнутой картинки сдвигается так, чтобы низ остался на месте
        h2 = out.get_height() / 2
        a = math.radians(sway)
        out = pygame.transform.rotate(out, sway)
        cx, cy = x - h2 * math.sin(a), y - h2 * math.cos(a)
        surf.blit(out, out.get_rect(center=(int(round(cx)), int(round(cy)))))
        return True
    if angle:
        out = pygame.transform.rotate(out, angle)
        anchor = "center"
    r = out.get_rect(**{anchor: (int(round(x)), int(round(y)))})
    surf.blit(out, r)
    return True


def blit_tf(surf, names, x, y, scale=1.0, flip=False, sx=1.0, sy=1.0, angle=0.0, pivot="midbottom", alpha=None):
    """Спрайт «как живой» (3.3): сплющить/вытянуть (sx, sy), наклонить на angle градусов (+ — против часовой)
    вокруг середины низа (pivot="midbottom": лапы стоят на месте) или центра (pivot="center"), сделать
    полупрозрачным (alpha 0..255). (x, y) — точка pivot. names — имя или список (берётся первый, что есть).
    Возвращает False, если ни одной картинки нет (тогда рисуем кодом)."""
    for name in ([names] if isinstance(names, str) else names):
        img = sprite(name)
        if img is None:
            continue
        kx = round(scale * sx / SCALE_STEP) * SCALE_STEP or SCALE_STEP
        ky = round(scale * sy / SCALE_STEP) * SCALE_STEP or SCALE_STEP
        key = ("tf", name, round(kx, 3), round(ky, 3), flip)
        out = _sprite_scaled.get(key)
        if out is None:
            out = img
            if flip:
                out = pygame.transform.flip(out, True, False)
            if abs(kx - 1.0) > 1e-3 or abs(ky - 1.0) > 1e-3:
                out = pygame.transform.smoothscale(out, (max(1, int(out.get_width() * kx + 0.5)),
                                                         max(1, int(out.get_height() * ky + 0.5))))
            if len(_sprite_scaled) > 3000:
                _sprite_scaled.clear()
            _sprite_scaled[key] = out
        h2 = out.get_height() / 2
        rot = out
        if abs(angle) > 0.05:
            rot = pygame.transform.rotate(out, angle)
        if alpha is not None and alpha < 255:
            if rot is out:
                rot = out.copy()          # картинка из кэша — её прозрачность не трогаем
            hd.real(rot).set_alpha(max(0, int(alpha)))     # только число: set_alpha(None) делает картинку сплошной
        if pivot == "midbottom":
            a = math.radians(angle)
            cx, cy = x - h2 * math.sin(a), y - h2 * math.cos(a)
        else:
            cx, cy = x, y
        surf.blit(rot, rot.get_rect(center=(int(round(cx)), int(round(cy)))))
        return True
    return False


def blit_any(surf, names, *args, **kwargs):
    """Пробует несколько имён по очереди (например, сначала зимний вариант, потом обычный)."""
    for name in names:
        if blit_sprite(surf, name, *args, **kwargs):
            return True
    return False


def farm_names(folder, file):
    """Сначала картинка для текущей фермы, потом общая: tiles/summer/soil -> tiles/soil."""
    return [f"{folder}/{FARM_ID[0]}/{file}", f"{folder}/{file}"]

# ======================================================================
#                              ГРАФИКА
# ======================================================================
OUT = (60, 40, 35)
WHITE = (255, 255, 255)
GOLD = (255, 205, 50)
GREEN = (80, 180, 70)
GRASS = (156, 222, 118)
SAND = (245, 230, 140)
SOIL = (226, 146, 86)
SOIL_DARK = (198, 118, 64)
SOIL_SIDE = (168, 98, 55)
BTN_BLUE = (70, 170, 230)
BTN_GREEN = (110, 200, 90)
BTN_GREY = (165, 165, 170)
PANEL = (240, 222, 212)
PILL = (160, 228, 245)

TW, TH = 180, 90            # размер изометрической клетки
OX, OY = 500, 215           # центр клетки (0,0)
# Поле — матрица 3x3, повёрнутая ромбом: 11 сверху, 13 справа, 31 слева, 33 снизу.
# Культуры открываются по порядку: 33, 32, 31, 23, 22, 21, 13, 12, 11.
UNLOCK_ORDER = ["33", "32", "31", "23", "22", "21", "13", "12", "11"]
# клетка "rc" (строка, столбец) -> координаты сетки (i, j): i = столбец-1, j = строка-1
SLOT = [(int(rc[1]) - 1, int(rc[0]) - 1) for rc in UNLOCK_ORDER]
DRAW_ORDER = sorted(range(N_CROPS), key=lambda k: (SLOT[k][0] + SLOT[k][1], SLOT[k][0]))
BAR_W = 50                  # ширина полоски прогресса под грядкой
PLANT_SPOTS = [(0, -16), (-42, 8), (42, 8)]

TRUCK_PARK_X = 830
TRUCK_GROUND = 592


def P(v):
    return int(round(v))


def tile_center(i, j):
    return OX + (i - j) * TW / 2, OY + (i + j) * TH / 2


def crop_center(k):
    return tile_center(*SLOT[k])


# ---------- текст ----------
_fonts = {}
_texts = {}
SYS_FONTS = "segoeui,arial,verdana,dejavusans,liberationsans,freesans"
FONT_EXTS = (".ttf", ".otf")
FONT_SAMPLE = "Весёлая ферма: $1.23M, урожай x10!"
_font_files = {}
_font_ratio = {}


def font_files():
    """Свой шрифт из assets/fonts/: {"title": путь, "body": путь} (None — системный).
    title — для надписей с обводкой (кнопки, заголовки): файл с Black/Heavy в имени;
    body — для обычного текста: ExtraBold/Bold. Один файл — он для всего."""
    if _font_files:
        return _font_files
    found = []
    folder = os.path.join(ASSET_DIR, "fonts")
    if os.path.isdir(folder):
        found = [os.path.join(folder, fn) for fn in sorted(os.listdir(folder)) if fn.lower().endswith(FONT_EXTS)]

    def pick(*words):
        for w in words:
            for path in found:
                if w in os.path.basename(path).lower().replace("-", "").replace("_", ""):
                    return path
        return None
    body = pick("extrabold", "bold", "semibold", "black", "heavy") or (found[0] if found else None)
    title = pick("black", "heavy", "extrabold") or body
    _font_files.update(title=title, body=body)
    if found:
        print("Шрифт:", ", ".join(os.path.basename(p) for p in {title, body} if p))
    return _font_files


def _sys_font(size):
    return pygame.font.SysFont(SYS_FONTS, size, bold=True)


def _ratio(kind, path):
    """Свой шрифт подгоняем по ширине под прежний (системный): все надписи остаются в своих кнопках."""
    r = _font_ratio.get(kind)
    if r is None:
        try:
            a = _sys_font(40).size(FONT_SAMPLE)[0]
            b = pygame.font.Font(path, 40).size(FONT_SAMPLE)[0]
            r = max(0.8, min(1.15, a / b)) if a > 0 and b > 0 else 1.0
        except Exception:
            r = 1.0
        _font_ratio[kind] = r
    return r


def font(size, kind="body"):
    key = (size, kind)
    f = _fonts.get(key)
    if f is None:
        path = font_files().get(kind)
        f = None
        if path:
            try:
                f = pygame.font.Font(path, max(1, int(round(size * _ratio(kind, path)))))
            except Exception as e:      # битый файл шрифта не должен ронять игру
                print(f"Шрифт {os.path.basename(path)} не загрузился: {e}")
                _font_files[kind] = None
        if f is None:
            f = _sys_font(size)
        _fonts[key] = f
    return f


def render_text(s, size, color, outline):
    key = (s, size, color, outline, hd.K[0])
    img = _texts.get(key)
    if img is not None:
        return img
    k = hd.K[0]
    # HD: буквы рендерятся шрифтом в k раз крупнее — текст чёткий, а снаружи он прежнего размера
    kind = "title" if outline else "body"    # с обводкой — жирнее (Black), обычный текст — ExtraBold
    f = font(size, kind) if k == 1 else font(max(1, int(round(size * k))), kind)
    base = f.render(s, True, color)
    if outline:
        o = 2 if size >= 16 else 1
        if k != 1:
            o = max(1, int(round(o * k)))
        w, h = base.get_size()
        img = pygame.Surface((w + 2 * o, h + 2 * o), pygame.SRCALPHA)
        ol = f.render(s, True, outline)
        for dx in range(-o, o + 1):
            for dy in range(-o, o + 1):
                if (dx or dy) and (k == 1 or dx * dx + dy * dy <= o * o + o):   # в HD обводка круглая
                    img.blit(ol, (dx + o, dy + o))
        img.blit(base, (o, o))
    else:
        img = base
    if k != 1:
        img = hd.HiSurf(img, k)
    if len(_texts) > 1500:
        _texts.clear()
    _texts[key] = img
    return img


def draw_text(surf, s, size, pos, color=WHITE, anchor="center", outline=OUT):
    img = render_text(s, size, color, outline)
    r = img.get_rect(**{anchor: (P(pos[0]), P(pos[1]))})
    surf.blit(img, r)
    return r


def draw_text_fit(surf, s, size, pos, maxw, color=WHITE, anchor="center", outline=OUT):
    """Как draw_text, но уменьшает шрифт, пока текст не влезет в maxw."""
    while size > 8 and render_text(s, size, color, outline).get_width() > maxw:
        size -= 1
    return draw_text(surf, s, size, pos, color, anchor, outline)


# ---------- примитивы ----------
def poly(surf, color, pts, w=2):
    pts = [(P(x), P(y)) for x, y in pts]
    pygame.draw.polygon(surf, color, pts)
    if w:
        pygame.draw.polygon(surf, OUT, pts, w)


def ellipse(surf, color, cx, cy, w, h, ow=2):
    r = pygame.Rect(P(cx - w / 2), P(cy - h / 2), max(1, P(w)), max(1, P(h)))
    pygame.draw.ellipse(surf, color, r)
    if ow and r.w >= 6 and r.h >= 6:
        pygame.draw.ellipse(surf, OUT, r, ow)


def blob(surf, color, circles, ow=2):
    """Несколько кругов с общей обводкой: (x, y, r)."""
    for x, y, r in circles:
        pygame.draw.circle(surf, OUT, (P(x), P(y)), P(r) + ow)
    for x, y, r in circles:
        pygame.draw.circle(surf, color, (P(x), P(y)), max(1, P(r)))


def leaf(surf, x, y, ang_deg, length, width, color, vein=None):
    a = math.radians(ang_deg)
    dx, dy = math.cos(a), -math.sin(a)
    nx, ny = -dy, dx
    pts = [(x, y),
           (x + dx * length * 0.5 + nx * width / 2, y + dy * length * 0.5 + ny * width / 2),
           (x + dx * length, y + dy * length),
           (x + dx * length * 0.5 - nx * width / 2, y + dy * length * 0.5 - ny * width / 2)]
    poly(surf, color, pts, 2 if length > 8 else 1)
    if vein and length > 8:
        pygame.draw.line(surf, vein, (P(x), P(y)), (P(x + dx * length * 0.8), P(y + dy * length * 0.8)), 1)


def face(surf, x, y, s):
    if s < 0.45:
        return
    er = max(1, P(1.7 * s))
    pygame.draw.circle(surf, OUT, (P(x - 4 * s), P(y - 1 * s)), er)
    pygame.draw.circle(surf, OUT, (P(x + 4 * s), P(y - 1 * s)), er)
    r = pygame.Rect(P(x - 3 * s), P(y - 1 * s), max(2, P(6 * s)), max(2, P(5 * s)))
    pygame.draw.arc(surf, OUT, r, math.pi + 0.3, 2 * math.pi - 0.3, 1)
    if s >= 0.9:  # румянец
        pygame.draw.circle(surf, (255, 140, 150), (P(x - 7 * s), P(y + 2 * s)), max(1, P(1.6 * s)))
        pygame.draw.circle(surf, (255, 140, 150), (P(x + 7 * s), P(y + 2 * s)), max(1, P(1.6 * s)))


def rounded(surf, color, rect, radius=10, border=3, border_color=OUT, skin="auto"):
    """Скруглённый прямоугольник. Цвет старой кнопки/карточки (см. skin.AUTO) — рисуется оформлением
    «дерево + пергамент» (картинка из assets/ui/ или то же кодом); skin=None — всегда просто цветом."""
    rect = pygame.Rect(rect)
    if skin:
        from . import skin as _skin
        name = _skin.AUTO.get(tuple(color[:3])) if skin == "auto" else skin
        if name and border:
            _skin.draw(surf, name, rect)
            return
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)


def draw_coin(surf, x, y, r, color=GOLD):
    if blit_sprite(surf, "icons/coin" if color == GOLD else "icons/coin_silver", x, y, r / 17, "center"):
        return
    pygame.draw.circle(surf, OUT, (P(x), P(y)), P(r) + 2)
    pygame.draw.circle(surf, color, (P(x), P(y)), P(r))
    lighter = tuple(min(255, c + 35) for c in color)
    pygame.draw.circle(surf, lighter, (P(x), P(y)), max(1, P(r * 0.72)))
    draw_text(surf, "$", max(10, P(r * 1.25)), (x, y), (190, 120, 10) if color == GOLD else (90, 110, 150), outline=None)


def draw_leaf_icon(surf, x, y, s=1.0):
    if blit_sprite(surf, "icons/leaf", x, y, s, "center"):
        return
    pygame.draw.circle(surf, OUT, (P(x), P(y)), P(16 * s) + 2)
    pygame.draw.circle(surf, (120, 210, 110), (P(x), P(y)), P(16 * s))
    leaf(surf, x - 7 * s, y + 7 * s, 45, 19 * s, 11 * s, (60, 160, 60), vein=(30, 100, 30))


def draw_seal_icon(surf, x, y, s=1.0):
    """Королевская печать: красный сургуч с короной."""
    if blit_sprite(surf, "icons/seal", x, y, s, "center"):
        return
    blob(surf, (200, 45, 50), [(x + math.cos(a) * 11 * s, y + math.sin(a) * 11 * s, 7 * s) for a in
                               [i * math.pi / 4 for i in range(8)]] + [(x, y, 13 * s)], 2)
    pygame.draw.circle(surf, (165, 30, 40), (P(x), P(y)), P(10 * s))
    poly(surf, (250, 205, 70), [(x - 7 * s, y + 4 * s), (x - 7 * s, y - 5 * s), (x - 3.5 * s, y - 1 * s), (x, y - 7 * s),
                                (x + 3.5 * s, y - 1 * s), (x + 7 * s, y - 5 * s), (x + 7 * s, y + 4 * s)], 1)


def draw_cur_icon(surf, x, y, s=1.0):
    """Иконка валюты престижа текущей фермы (лист или печать)."""
    (draw_seal_icon if CUR.get("icon") == "seal" else draw_leaf_icon)(surf, x, y, s)


def draw_bar(surf, rect, frac, color=(255, 200, 40)):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, OUT, rect, border_radius=rect.h // 2)
    inner = rect.inflate(-4, -4)
    pygame.draw.rect(surf, (90, 70, 60), inner, border_radius=inner.h // 2)
    frac = max(0.0, min(1.0, frac))
    if frac > 0:
        fill = pygame.Rect(inner.x, inner.y, max(inner.h, P(inner.w * frac)), inner.h)
        pygame.draw.rect(surf, color, fill, border_radius=inner.h // 2)


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


def draw_fence(s, a, b, off):
    ax, ay = a[0] + off[0], a[1] + off[1]
    bx, by = b[0] + off[0], b[1] + off[1]
    if THEME.get("wall"):   # средневековье: низкая каменная стена
        n = max(1, int(math.hypot(bx - ax, by - ay) / 20))
        for row, (h, shift) in enumerate(((0, 0.0), (11, 0.5))):
            for k in range(n):
                t0, t1 = (k + shift) / n, min(1.0, (k + shift + 1) / n)
                if t0 >= 1:
                    continue
                x0, y0 = ax + (bx - ax) * t0, ay + (by - ay) * t0 - h
                x1, y1 = ax + (bx - ax) * t1, ay + (by - ay) * t1 - h
                shade = 165 + (k * 37 + row * 11) % 30
                poly(s, (shade, shade - 5, shade - 12), [(x0 + 1, y0), (x1 - 1, y1), (x1 - 1, y1 - 11), (x0 + 1, y0 - 11)], 2)
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


def draw_peasant_head(s, x, y, k=1.0):
    if blit_sprite(s, "icons/peasant", x, y, k, "center"):
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


ANIMAL_DRAW = [draw_chicken, draw_cow, draw_pig, draw_hive]


def draw_product(s, a, x, y, k=1.0):
    if blit_sprite(s, "icons/" + ("egg", "milk", "truffle", "honey")[a], x, y, k, "center"):
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
    "peas": plant_peas, "rye": plant_rye, "barley": plant_barley, "spelt": plant_spelt,
    "flax": plant_flax, "hops": plant_hops, "grapes": plant_grapes,
}
CROP_KEYS = list(FARMS[0]["plants"])   # ключи культур текущей фермы (для спрайтов)
FARM_ID = [FARMS[0]["id"]]             # id текущей фермы (папка спрайтов)


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
    TREE_NODES.clear()
    TREE_NODES.update(TREE_NODE_MAP[fm["tree"]])
    for i, name in enumerate(fm["tiers"]):
        TRUCK_TIERS[i] = (name,) + tuple(TRUCK_TIERS[i][1:])
    return fm


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
    draw_fence(bg, (OX, OY - TH / 2), (OX + TW + TW / 2, OY + TH), (8, -14))   # задний забор
    return bg


FENCE_STRIP_H = {"fence": 36, "wall": 30}   # высота забора / каменной стены из картинки на экране, px
_fence_layers = {}


def front_fence_segments():
    """Два передних края поля, вдоль которых стоит забор: [(начало, конец)], x начала < x конца."""
    left = (OX - TW - TW / 2, OY + TH)
    bottom = (OX, OY + 2 * TH + TH / 2)
    right = (OX + TW + TW / 2, OY + TH)
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
    x0 = int(min(a[0] for a, b in segs))
    x1 = int(max(b[0] for a, b in segs)) + 1
    y0 = int(min(min(a[1], b[1]) for a, b in segs)) - hgt - 2
    y1 = int(max(max(a[1], b[1]) for a, b in segs)) + 2
    ow, oh = int(round((x1 - x0) * kk)), int(round((y1 - y0) * kk))
    # прозрачные пиксели — цвета контура: при сглаживании край темнеет к контуру, а не к чёрному
    out = bytearray(bytes((70, 45, 35, 0)) * (ow * oh))
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
                if 0 <= oy < oh:
                    si, oi = (y * sw + sx) * 4, (oy * ow + ox) * 4
                    if sb[si + 3]:
                        out[oi:oi + 4] = sb[si:si + 4]
    big = _frombytes(out, (ow, oh))
    pw, ph = max(1, int(round((x1 - x0) * hd.K[0]))), max(1, int(round((y1 - y0) * hd.K[0])))
    small = hd._orig.get("smoothscale", pygame.transform.smoothscale)(big, (pw, ph))
    return hd.wrap(small) if hd.K[0] != 1 else small, (x0, y0)


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
    (a1, b1), (a2, b2) = front_fence_segments()
    draw_fence(s, a1, b1, (0, 0))
    draw_fence(s, a2, b2, (0, 0))


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


VEHICLE_OFFSET = {"truck": -5, "cart": -30}   # где середина низа картинки относительно точки (x, y) машины


def draw_vehicle_at(s, vehicle, tier, x, y, color, cargo=False, bob=0.0, angle=0.0, sy=1.0):
    """Машина (телега) смотрит влево. angle — наклон (+ — нос вниз), sy — осела на рессорах (3.3)."""
    names = ([f"vehicles/{vehicle}_{tier}_cargo"] if cargo else []) + [f"vehicles/{vehicle}_{tier}", f"vehicles/{vehicle}"]
    if blit_tf(s, names, x + VEHICLE_OFFSET[vehicle], y + 4 - bob, 1, sy=sy, angle=angle):
        return
    (draw_cart if vehicle == "cart" else draw_truck)(s, x, y, color, cargo, bob)


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


def draw_trail(surf, points, now, life=0.28, color=(255, 250, 225)):
    """Тонкий исчезающий шлейф за курсором. points = [(x, y, время)].
    Слой — только размером со сам шлейф (а не весь экран): в HD так заметно быстрее."""
    pts = [(x, y, now - t) for x, y, t in points if now - t < life]
    if len(pts) < 2:
        return
    pad = 8
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
        pygame.draw.line(layer, color + (int(40 * k),), a, b, width + 4)   # мягкое свечение
        pygame.draw.line(layer, color + (int(200 * k),), a, b, width)
    surf.blit(layer, (lx, ly))
