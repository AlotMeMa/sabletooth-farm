"""Заглушка pygame на PIL: рисует по-настоящему (в картинку), чтобы проверять игру без pygame и смотреть кадры.

Повторяет поведение pygame, важное для игры:
  * pygame.draw.* пишет цвет как есть (с альфой), без смешивания — как в pygame;
  * blit смешивает по альфе; set_alpha(a) у картинки умножает её альфу; set_alpha(None) у SRCALPHA-картинки
    делает её сплошной (как в pygame 2 — на этом ловили синий фон в 3.2.1);
  * поверхность без SRCALPHA — непрозрачная (альфа всегда 255);
  * rotate: положительный угол — против часовой стрелки, картинка расширяется.
Без сглаживания линий и кругов (как и в pygame.draw).
"""
import math
import os
import types

from PIL import Image, ImageDraw, ImageFont

SRCALPHA, SCALED, RESIZABLE, FULLSCREEN, NOFRAME, HWSURFACE, DOUBLEBUF = 65536, 512, 16, 1, 32, 1, 1073741824
QUIT, KEYDOWN, KEYUP, MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION, MOUSEWHEEL = 256, 768, 769, 1025, 1026, 1024, 1027
VIDEORESIZE, WINDOWRESIZED, ACTIVEEVENT = 16, 32769, 32768
K_ESCAPE, K_F1, K_F11, K_b, K_m, K_s, K_t, K_u, K_RETURN, K_SPACE = 27, 1073741882, 1073741892, 98, 109, 115, 116, 117, 13, 32
SYSTEM_CURSOR_ARROW, SYSTEM_CURSOR_HAND = 0, 11
BLEND_RGBA_MULT, BLEND_RGB_ADD, BLEND_RGBA_ADD, BLEND_PREMULTIPLIED = 8, 1, 6, 17
STATS = {}


class error(Exception):
    pass


def _stat(name):
    STATS[name] = STATS.get(name, 0) + 1


class Rect:
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, *a):
        if len(a) == 1:
            a = a[0]
            if isinstance(a, Rect):
                a = (a.x, a.y, a.w, a.h)
        if len(a) == 2:
            a = (a[0][0], a[0][1], a[1][0], a[1][1])
        if len(a) != 4:
            raise TypeError(f"Rect: плохие аргументы {a!r}")
        for v in a:
            if not isinstance(v, (int, float)) or v != v:
                raise TypeError(f"Rect: не число {a!r}")
        self.x, self.y, self.w, self.h = (int(v) for v in a)

    width = property(lambda s: s.w, lambda s, v: setattr(s, "w", int(v)))
    height = property(lambda s: s.h, lambda s, v: setattr(s, "h", int(v)))
    left = property(lambda s: s.x, lambda s, v: setattr(s, "x", int(v)))
    top = property(lambda s: s.y, lambda s, v: setattr(s, "y", int(v)))
    right = property(lambda s: s.x + s.w, lambda s, v: setattr(s, "x", int(v) - s.w))
    bottom = property(lambda s: s.y + s.h, lambda s, v: setattr(s, "y", int(v) - s.h))
    centerx = property(lambda s: s.x + s.w // 2, lambda s, v: setattr(s, "x", int(v) - s.w // 2))
    centery = property(lambda s: s.y + s.h // 2, lambda s, v: setattr(s, "y", int(v) - s.h // 2))
    size = property(lambda s: (s.w, s.h), lambda s, v: (setattr(s, "w", int(v[0])), setattr(s, "h", int(v[1]))))

    def _pair(gx, gy):
        def get(s):
            return (getattr(s, gx), getattr(s, gy))

        def put(s, v):
            setattr(s, gx, v[0])
            setattr(s, gy, v[1])
        return property(get, put)

    center = _pair("centerx", "centery")
    topleft = _pair("left", "top")
    topright = _pair("right", "top")
    bottomleft = _pair("left", "bottom")
    bottomright = _pair("right", "bottom")
    midtop = _pair("centerx", "top")
    midbottom = _pair("centerx", "bottom")
    midleft = _pair("left", "centery")
    midright = _pair("right", "centery")
    del _pair

    def copy(self):
        return Rect(self)

    def move(self, dx, dy):
        return Rect(self.x + dx, self.y + dy, self.w, self.h)

    def move_ip(self, dx, dy):
        self.x += int(dx)
        self.y += int(dy)

    def inflate(self, dx, dy):
        return Rect(self.x - int(dx) // 2, self.y - int(dy) // 2, self.w + int(dx), self.h + int(dy))

    def inflate_ip(self, dx, dy):
        r = self.inflate(dx, dy)
        self.x, self.y, self.w, self.h = r.x, r.y, r.w, r.h

    def collidepoint(self, *p):
        if len(p) == 1:
            p = p[0]
        return self.x <= p[0] < self.x + self.w and self.y <= p[1] < self.y + self.h

    def colliderect(self, o):
        o = Rect(o)
        return self.x < o.right and o.x < self.right and self.y < o.bottom and o.y < self.bottom

    def contains(self, o):
        o = Rect(o)
        return self.x <= o.x and self.y <= o.y and o.right <= self.right and o.bottom <= self.bottom

    def clip(self, o):
        o = Rect(o)
        x0, y0 = max(self.x, o.x), max(self.y, o.y)
        x1, y1 = min(self.right, o.right), min(self.bottom, o.bottom)
        if x1 <= x0 or y1 <= y0:
            return Rect(self.x, self.y, 0, 0)
        return Rect(x0, y0, x1 - x0, y1 - y0)

    def union(self, o):
        o = Rect(o)
        x, y = min(self.x, o.x), min(self.y, o.y)
        return Rect(x, y, max(self.right, o.right) - x, max(self.bottom, o.bottom) - y)

    def clamp(self, o):
        o = Rect(o)
        r = Rect(self)
        r.x = max(o.x, min(r.x, o.right - r.w))
        r.y = max(o.y, min(r.y, o.bottom - r.h))
        return r

    def __iter__(self):
        return iter((self.x, self.y, self.w, self.h))

    def __len__(self):
        return 4

    def __getitem__(self, i):
        return (self.x, self.y, self.w, self.h)[i]

    def __eq__(self, o):
        try:
            return tuple(self) == tuple(Rect(o))
        except Exception:
            return False

    def __bool__(self):
        return self.w > 0 and self.h > 0

    def __hash__(self):
        return hash(tuple(self))

    def __repr__(self):
        return f"<rect({self.x}, {self.y}, {self.w}, {self.h})>"


def _col(c):
    if isinstance(c, str):
        from PIL import ImageColor
        c = ImageColor.getrgb(c)
    if not (hasattr(c, "__len__") and len(c) in (3, 4)):
        raise ValueError(f"плохой цвет {c!r}")
    for v in c:
        if not isinstance(v, (int, float)) or not 0 <= v <= 255:
            raise ValueError(f"плохой цвет {c!r}")
    c = tuple(int(v) for v in c)
    return c if len(c) == 4 else c + (255,)


def _pt(p):
    if not (hasattr(p, "__len__") and len(p) == 2):
        raise TypeError(f"плохая точка {p!r}")
    x, y = p
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)) or x != x or y != y:
        raise TypeError(f"плохая точка {p!r}")
    return (int(x), int(y))


class Surface:
    def __init__(self, size, flags=0, *a, _img=None):
        if _img is None:
            w, h = _pt(size)
            if w < 0 or h < 0:
                raise error(f"Invalid resolution for Surface {size!r}")
            alpha = bool(flags & SRCALPHA)
            _img = Image.new("RGBA", (w, h), (0, 0, 0, 0 if alpha else 255))
            self._alpha_px = alpha
        else:
            self._alpha_px = True
        self.img = _img
        self._alpha = None
        self._solid = False

    def get_size(self):
        return self.img.size

    def get_width(self):
        return self.img.size[0]

    def get_height(self):
        return self.img.size[1]

    def get_rect(self, **kw):
        r = Rect(0, 0, *self.img.size)
        for k, v in kw.items():
            setattr(r, k, v)
        return r

    def get_flags(self):
        return SRCALPHA if self._alpha_px else 0

    def get_bitsize(self):
        return 32

    def set_alpha(self, a, flags=0):
        if a is None:
            self._alpha = None
            if self._alpha_px:
                self._solid = True
            return
        self._alpha = max(0, min(255, int(a)))
        self._solid = False

    def get_alpha(self):
        return self._alpha if self._alpha is not None else (255 if not self._alpha_px else None)

    def set_colorkey(self, *a):
        pass

    def get_at(self, p):
        return self.img.getpixel(_pt(p))

    def set_at(self, p, c):
        x, y = _pt(p)
        if 0 <= x < self.img.size[0] and 0 <= y < self.img.size[1]:
            c = _col(c)
            self.img.putpixel((x, y), c if self._alpha_px else c[:3] + (255,))

    def copy(self):
        s = Surface((0, 0), _img=self.img.copy())
        s._alpha_px, s._alpha, s._solid = self._alpha_px, self._alpha, self._solid
        return s

    def convert(self, *a):
        s = self.copy()
        s._alpha_px = False
        s.img.putalpha(255)
        return s

    def convert_alpha(self, *a):
        s = self.copy()
        s._alpha_px = True
        return s

    def subsurface(self, *r):
        r = Rect(*r)
        s = Surface((0, 0), _img=self.img.crop((r.x, r.y, r.right, r.bottom)))
        s._alpha_px = self._alpha_px
        return s

    def lock(self):
        pass

    def unlock(self):
        pass

    def fill(self, color, rect=None, special_flags=0):
        c = _col(color)
        if not self._alpha_px:
            c = c[:3] + (255,)
        if rect is None:
            r = Rect(0, 0, *self.img.size)
        else:
            r = Rect(rect).clip(Rect(0, 0, *self.img.size))
        if r.w > 0 and r.h > 0:
            if special_flags == BLEND_RGBA_MULT:
                from PIL import ImageChops
                box = (r.x, r.y, r.right, r.bottom)
                part = self.img.crop(box).convert("RGBA")
                part = ImageChops.multiply(part, Image.new("RGBA", part.size, _col(color)))
                self.img.paste(part, box)
            else:
                self.img.paste(c, (r.x, r.y, r.right, r.bottom))
        return r

    def _source_img(self):
        img = self.img
        if not self._alpha_px or self._solid:
            img = img.copy()
            img.putalpha(255)
        if self._alpha is not None and self._alpha < 255:
            a = img.getchannel("A").point(lambda v, k=self._alpha: v * k // 255)
            img = img.copy()
            img.putalpha(a)
        return img

    def blit(self, src, dest, area=None, special_flags=0):
        _stat("blit")
        if not isinstance(src, Surface):
            raise TypeError(f"blit: это не поверхность: {src!r}")
        if isinstance(dest, Rect):
            dx, dy = dest.x, dest.y
        else:
            dx, dy = _pt(dest)
        img = src._source_img()
        if area is not None:
            a = Rect(area)
            img = img.crop((a.x, a.y, a.right, a.bottom))
        w, h = img.size
        r = Rect(dx, dy, w, h).clip(Rect(0, 0, *self.img.size))
        if r.w <= 0 or r.h <= 0:
            return Rect(dx, dy, 0, 0)
        piece = img.crop((r.x - dx, r.y - dy, r.x - dx + r.w, r.y - dy + r.h))
        if special_flags:
            _stat("blit_special_flags")
        base = self.img.crop((r.x, r.y, r.right, r.bottom))
        if special_flags in (BLEND_RGB_ADD, BLEND_RGBA_ADD):
            # как в pygame: цвета источника прибавляются к цветам картинки (свет), прозрачность не смешивается
            from PIL import ImageChops
            src = piece if src._alpha_px else piece
            added = ImageChops.add(base.convert("RGB"), src.convert("RGB"))
            out = added.convert("RGBA")
            out.putalpha(base.getchannel("A"))
            self.img.paste(out, (r.x, r.y))
            return r
        out = Image.alpha_composite(base, piece)
        if not self._alpha_px:
            out.putalpha(255)
        self.img.paste(out, (r.x, r.y))
        return r

    def blits(self, seq, doreturn=1):
        return [self.blit(*item) for item in seq]


def _target(surf):
    if not isinstance(surf, Surface):
        raise TypeError(f"draw: это не поверхность: {surf!r}")
    return surf


def _dcol(surf, color):
    c = _col(color)
    return c if surf._alpha_px else c[:3] + (255,)


def _bbox_of(points, width):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    pad = max(1, width)
    return Rect(min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad + 1, max(ys) - min(ys) + 2 * pad + 1)


def _rect(surf, color, rect, width=0, border_radius=0, border_top_left_radius=-1, border_top_right_radius=-1,
          border_bottom_left_radius=-1, border_bottom_right_radius=-1):
    _stat("draw.rect")
    s = _target(surf)
    r = Rect(rect)
    width, border_radius = int(width), int(border_radius)
    if r.w <= 0 or r.h <= 0 or width < 0:
        return Rect(r.x, r.y, 0, 0)
    d = ImageDraw.Draw(s.img)
    c = _dcol(s, color)
    corners = [border_top_left_radius, border_top_right_radius, border_bottom_right_radius, border_bottom_left_radius]
    rad = max(0, min(border_radius, min(r.w, r.h) // 2))
    box = (r.x, r.y, r.right - 1, r.bottom - 1)
    if rad <= 0 and all(cr <= 0 for cr in corners):
        if width == 0:
            d.rectangle(box, fill=c)
        else:
            d.rectangle(box, outline=c, width=width)
    else:
        rads = [min(cr, min(r.w, r.h) // 2) if cr >= 0 else rad for cr in corners]
        R = max(rads)
        kw = dict(fill=c) if width == 0 else dict(outline=c, width=width)
        d.rounded_rectangle(box, radius=R, corners=tuple(x > 0 for x in rads), **kw)
    return r


def _circle(surf, color, center, radius, width=0, draw_top_right=None, draw_top_left=None, draw_bottom_left=None,
            draw_bottom_right=None):
    _stat("draw.circle")
    s = _target(surf)
    cx, cy = _pt(center)
    radius = float(radius)
    width = int(width)
    if radius < 1 or width < 0:
        return Rect(cx, cy, 0, 0)
    rr = int(radius)
    d = ImageDraw.Draw(s.img)
    c = _dcol(s, color)
    box = (cx - rr, cy - rr, cx + rr, cy + rr)
    if width == 0 or width >= rr:
        d.ellipse(box, fill=c)
    else:
        d.ellipse(box, outline=c, width=width)
    return Rect(cx - rr, cy - rr, 2 * rr, 2 * rr)


def _ellipse(surf, color, rect, width=0):
    _stat("draw.ellipse")
    s = _target(surf)
    r = Rect(rect)
    width = int(width)
    if r.w <= 0 or r.h <= 0 or width < 0:
        return Rect(r.x, r.y, 0, 0)
    d = ImageDraw.Draw(s.img)
    c = _dcol(s, color)
    box = (r.x, r.y, r.right - 1, r.bottom - 1)
    if width == 0 or width * 2 >= min(r.w, r.h):
        d.ellipse(box, fill=c)
    else:
        d.ellipse(box, outline=c, width=width)
    return r


def _arc(surf, color, rect, start, stop, width=1):
    _stat("draw.arc")
    s = _target(surf)
    r = Rect(rect)
    if r.w <= 1 or r.h <= 1:
        return Rect(r.x, r.y, 0, 0)
    d = ImageDraw.Draw(s.img)
    a0, a1 = -math.degrees(float(stop)), -math.degrees(float(start))
    d.arc((r.x, r.y, r.right - 1, r.bottom - 1), a0, a1, fill=_dcol(s, color), width=max(1, int(width)))
    return r


def _line(surf, color, start, end, width=1):
    _stat("draw.line")
    s = _target(surf)
    a, b = _pt(start), _pt(end)
    width = int(width)
    if width < 1:
        return Rect(a[0], a[1], 0, 0)
    ImageDraw.Draw(s.img).line([a, b], fill=_dcol(s, color), width=width)
    return _bbox_of([a, b], width)


def _lines(surf, color, closed, points, width=1):
    _stat("draw.lines")
    s = _target(surf)
    pts = [_pt(p) for p in points]
    if len(pts) < 2:
        raise ValueError("points argument must contain 2 or more points")
    if closed:
        pts = pts + [pts[0]]
    ImageDraw.Draw(s.img).line(pts, fill=_dcol(s, color), width=max(1, int(width)), joint="curve")
    return _bbox_of(pts, int(width))


def _polygon(surf, color, points, width=0):
    _stat("draw.polygon")
    s = _target(surf)
    pts = [_pt(p) for p in points]
    if len(pts) < 3:
        raise ValueError("points argument must contain more than 2 points")
    width = int(width)
    d = ImageDraw.Draw(s.img)
    c = _dcol(s, color)
    if width == 0:
        d.polygon(pts, fill=c)
    else:
        d.line(pts + [pts[0]], fill=c, width=width, joint="curve")
    return _bbox_of(pts, width)


def _aaline(surf, color, start, end, blend=1):
    return _line(surf, color, start, end, 1)


draw = types.SimpleNamespace(rect=_rect, circle=_circle, ellipse=_ellipse, arc=_arc, line=_line, lines=_lines,
                             polygon=_polygon, aaline=_aaline, aalines=lambda s, c, cl, p, b=1: _lines(s, c, cl, p, 1))


def _new_like(src, img):
    s = Surface((0, 0), _img=img)
    s._alpha_px = src._alpha_px
    return s


def _size(size):
    w, h = _pt(size)
    if w < 0 or h < 0:
        raise ValueError(f"Cannot scale to negative size {size!r}")
    return max(0, w), max(0, h)


def _smoothscale(src, size, dest=None):
    _stat("smoothscale")
    w, h = _size(size)
    if w == 0 or h == 0:
        return _new_like(src, Image.new("RGBA", (w, h)))
    img = src.img
    if img.size == (w, h):
        return _new_like(src, img.copy())
    pm = img.convert("RGBa").resize((w, h), Image.BILINEAR if (w >= img.size[0]) else Image.BOX)
    return _new_like(src, pm.convert("RGBA"))


def _scale(src, size, dest=None):
    _stat("scale")
    w, h = _size(size)
    return _new_like(src, src.img.resize((w, h), Image.NEAREST) if w and h else Image.new("RGBA", (w, h)))


def _rotate(src, angle):
    _stat("rotate")
    img = src.img
    if not src._alpha_px:
        img = img.copy()
        img.putalpha(255)
    out = img.convert("RGBa").rotate(float(angle), resample=Image.NEAREST, expand=True).convert("RGBA")
    s = Surface((0, 0), _img=out)
    s._alpha_px = True
    return s


def _rotozoom(src, angle, k):
    r = _rotate(src, angle)
    w, h = r.get_size()
    return _smoothscale(r, (max(1, int(w * k)), max(1, int(h * k))))


def _flip(src, fx, fy):
    _stat("flip")
    img = src.img
    if fx:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if fy:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    if img is src.img:
        img = img.copy()
    return _new_like(src, img)


def _gaussian_blur(src, radius, repeat_edge_pixels=True, dest=None):
    from PIL import ImageFilter
    return _new_like(src, src.img.filter(ImageFilter.GaussianBlur(radius)))


def _box_blur(src, radius, repeat_edge_pixels=True, dest=None):
    from PIL import ImageFilter
    return _new_like(src, src.img.filter(ImageFilter.BoxBlur(radius)))


transform = types.SimpleNamespace(smoothscale=_smoothscale, scale=_scale, rotate=_rotate, rotozoom=_rotozoom,
                                  flip=_flip, scale2x=lambda s: _scale(s, (s.get_width() * 2, s.get_height() * 2)))


def _load(path, namehint=""):
    _stat("image.load")
    try:
        im = Image.open(path)
        im.load()
    except Exception as e:
        raise error(str(e))
    has_alpha = im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info)
    s = Surface((0, 0), _img=im.convert("RGBA"))
    s._alpha_px = has_alpha
    return s


def _save(surf, path, namehint=""):
    img = surf.img
    if str(path).lower().endswith((".jpg", ".jpeg")):
        img = img.convert("RGB")
    img.save(path)


def _tobytes(surf, fmt="RGBA", flipped=False):
    if fmt != "RGBA":
        raise ValueError(fmt)
    img = surf.img
    if not surf._alpha_px:
        img = img.copy()
        img.putalpha(255)
    return img.tobytes()


def _frombytes(buf, size, fmt="RGBA", flipped=False):
    if fmt != "RGBA":
        raise ValueError(fmt)
    s = Surface((0, 0), _img=Image.frombytes("RGBA", _pt(size), bytes(buf)))
    s._alpha_px = True
    return s


image = types.SimpleNamespace(load=_load, save=_save, tostring=_tobytes, tobytes=_tobytes, fromstring=_frombytes,
                              frombytes=_frombytes, get_extended=lambda: True)

_SYS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]


def _find_sys():
    for p in _SYS:
        if os.path.exists(p):
            return p
    for root, _d, files in os.walk("/usr/share/fonts"):
        for fn in files:
            if fn.lower().endswith(".ttf"):
                return os.path.join(root, fn)
    return None


class Font:
    def __init__(self, path=None, size=12):
        self.size_px = max(1, int(size))
        path = path or _find_sys()
        try:
            self.f = ImageFont.truetype(path, self.size_px)
        except Exception as e:
            raise error(f"не открыть шрифт {path}: {e}")
        asc, desc = self.f.getmetrics()
        self.asc, self.h = asc, asc + desc

    def render(self, text, antialias, color, background=None):
        _stat("font.render")
        if not isinstance(text, str):
            raise TypeError(f"text must be a str, not {type(text).__name__}")
        if "\n" in text or "\x00" in text:
            raise ValueError("text has invalid characters")
        w = max(1, int(math.ceil(self.f.getlength(text)))) if text else 1
        img = Image.new("RGBA", (w, self.h), (0, 0, 0, 0) if background is None else _col(background))
        ImageDraw.Draw(img).text((0, 0), text, font=self.f, fill=_col(color))
        s = Surface((0, 0), _img=img)
        s._alpha_px = background is None
        return s

    def size(self, text):
        return (int(math.ceil(self.f.getlength(text))) if text else 0, self.h)

    def get_linesize(self):
        return self.h

    def get_height(self):
        return self.h

    def get_ascent(self):
        return self.asc

    def set_bold(self, v):
        pass


def SysFont(name, size, bold=False, italic=False):
    return Font(_find_sys(), size)


font = types.SimpleNamespace(Font=Font, SysFont=SysFont, init=lambda: None, get_init=lambda: True)


class _Sound:
    def __init__(self, *a, **kw):
        self.v = 1.0

    def set_volume(self, v):
        self.v = float(v)

    def get_volume(self):
        return self.v

    def play(self, loops=0, maxtime=0, fade_ms=0):
        _stat("sound.play")

    def fadeout(self, ms):
        pass

    def stop(self):
        pass

    def get_length(self):
        return 1.0


_mixer = {"init": None}
mixer = types.SimpleNamespace(
    get_init=lambda: _mixer["init"], init=lambda *a, **k: _mixer.update(init=(44100, -16, 2)), Sound=_Sound,
    quit=lambda: None, set_num_channels=lambda n: None, pre_init=lambda *a, **k: None,
    music=types.SimpleNamespace(stop=lambda: None, load=lambda p: None, set_volume=lambda v: float(v),
                                play=lambda *a, **kw: None, fadeout=lambda ms: None, get_busy=lambda: False,
                                get_pos=lambda: -1),
)

STATE = {"mouse": (500, 320), "events": [], "tick": 16, "screen": None}


class _Clock:
    def tick(self, fps=0):
        return STATE["tick"]

    def get_fps(self):
        return 60.0


time = types.SimpleNamespace(Clock=_Clock, get_ticks=lambda: 0, wait=lambda ms: None, delay=lambda ms: None)


def _events(*a, **k):
    ev, STATE["events"] = STATE["events"], []
    return ev


event = types.SimpleNamespace(get=_events, pump=lambda: None, Event=lambda t, **kw: types.SimpleNamespace(type=t, **kw),
                              post=lambda e: STATE["events"].append(e))
mouse = types.SimpleNamespace(get_pos=lambda: STATE["mouse"], set_cursor=lambda *a: None, set_visible=lambda v: None,
                              get_pressed=lambda *a: (False, False, False))
cursors = types.SimpleNamespace(Cursor=lambda *a: object())


def _set_mode(size=(0, 0), flags=0, *a, **kw):
    s = Surface(size)
    STATE["screen"] = s
    return s


display = types.SimpleNamespace(
    set_mode=_set_mode, set_caption=lambda *a: None, flip=lambda: _stat("flip"), update=lambda *a: None,
    toggle_fullscreen=lambda: 1, quit=lambda: _stat("display_quit"), init=lambda: _stat("display_init"),
    get_desktop_sizes=lambda: [STATE.get("desktop", (1920, 1080))],
    Info=lambda: types.SimpleNamespace(current_w=STATE.get("desktop", (1920, 1080))[0],
                                       current_h=STATE.get("desktop", (1920, 1080))[1]),
    get_surface=lambda: STATE["screen"], set_icon=lambda s: None, get_window_size=lambda: STATE["screen"].get_size(),
)
version = types.SimpleNamespace(ver="2.5.0-pilstub", vernum=(2, 5, 0))
key = types.SimpleNamespace(get_pressed=lambda: [False] * 512, get_mods=lambda: 0)


def init():
    return (6, 0)


def quit():
    pass
