# -*- coding: utf-8 -*-
"""Экран мельницы (3.7): живая сцена в разрезе вместо двух карточек.

Слева — мельница: бункер с горкой зерна (по закромам), колесо-жернов в каменной чаше (крутится, пока
мельники мелют), мешки муки 1/2/3 (по запасу), мельник носит мешки. Справа — пекарня: печь с огнём и дымом
из трубы, стеллаж с буханками (по запасу хлеба), пекарь с лопатой. Внизу — две пергаментные карточки
с цифрами и кнопками. Нажимать можно и на саму сцену: бункер — засыпать зерно, мешки — продать муку,
стеллаж — продать хлеб.

Подмешивается в App (class App(TavernUI, MillUI, ...)). Логика — в logic.py (Farm.fill_hopper, _run_mill ...).
Свои картинки (необязательно, без них всё рисуется кодом; промпты — в доке «Промпты для Gemini»):
    props/millstone, mill_bed, mill_hopper, grain_heap, flour_sacks_1..3, oven, oven_fire, bread_shelf;
    characters/miller, characters/baker (100x150, в полный рост); icons/grain, icons/flour, icons/bread.
"""
import math
import random

import pygame

from .config import W, H, fmt, MILL_MAX_LVL, CROPS, GRAIN, BREAD_RATIO, BAKE_TIME, FLOUR_RATIO
from .art import (OUT, WHITE, BTN_GREEN, BTN_BLUE, BTN_GREY, P, poly, ellipse, blob, rounded, draw_text,
                  draw_text_fit, draw_bar, has_sprite, blit_sprite, blit_tf, blit_light, draw_peasant_head)
from .particles import soft_dot, draw_shadow
from .tavern_ui import draw_person
from . import hd

BROWN, SOFT = (90, 70, 60), (140, 110, 95)
RED, OK_GREEN = (190, 80, 70), (60, 130, 50)
CARD = (238, 222, 192)          # цвет карточки: с картинкой ui/card рисуется пергаментом (skin.AUTO)
FLOUR_WHITE = (246, 240, 226)

# --- раскладка сцены (логические 1000x640; пол на фоне mill_inside — от y≈535) ---
FLOOR = 548
MILL_CARD = pygame.Rect(96, 556, 440, 78)
BAKE_CARD = pygame.Rect(552, 556, 440, 78)
HOPPER_X, HOPPER_TOP = 165, 352          # бункер на ножках: верх воронки, низ — на полу
WHEEL = (338, 468)                        # ось колеса-жернова
WHEEL_R = 62
BED = pygame.Rect(218, 472, 240, 76)       # каменная чаша (передняя стенка закрывает низ колеса)
SACKS_X = 500
OVEN_X = 688                              # середина печи
OVEN_MOUTH = (688, 500)                   # устье печи (огонь)
CHIMNEY = (740, 300)                      # откуда идёт дым (верх трубы)
SHELF_X = 902
MILLER_PATH = (232, 438)                  # мельник ходит от бункера к мешкам
BAKER_SPOTS = (792, 846)                  # у печи / у стеллажа
SCENE_ZONES = {
    "hopper": pygame.Rect(HOPPER_X - 70, HOPPER_TOP - 6, 140, 130),
    "sacks": pygame.Rect(SACKS_X - 72, FLOOR - 104, 144, 104),
    "shelf": pygame.Rect(SHELF_X - 86, FLOOR - 160, 172, 160),
}
MILLER_LOOK = dict(top=(222, 212, 192), legs=(120, 95, 70), hair=(120, 80, 50), style="short", mustache=True)
BAKER_LOOK = dict(top=(240, 236, 228), legs=(110, 90, 75), hair=(70, 50, 40), style="bald", apron=True,
                  skin=(240, 195, 160))


def flour_sacks(flour, rate):
    """Сколько мешков муки показать (0..3): мешок — около минуты работы мельницы."""
    if flour <= 0:
        return 0
    if rate <= 0:
        return 3
    minutes = flour / (rate * 60)
    return 1 if minutes < 1 else (2 if minutes < 3 else 3)


def bread_loaves(bread, batch):
    """Сколько буханок на стеллаже (0..9): партия печи — три буханки."""
    if bread <= 0:
        return 0
    if batch <= 0:
        return 9
    return max(1, min(9, int(math.ceil(bread / batch * 3))))


def draw_icon(s, kind, x, y, k=1.0):
    """Иконка зерна/муки/хлеба: картинка icons/<kind> или кодом."""
    if blit_sprite(s, "icons/" + kind, x, y, 0.5 * k, "center"):
        return
    if kind == "grain":
        for dx, dy, a in ((-4, 2, -0.5), (0, -2, 0), (4, 2, 0.5)):
            ellipse(s, (232, 190, 90), x + dx * k, y + dy * k, 6 * k, 11 * k, 1)
    elif kind == "flour":
        blob(s, FLOUR_WHITE, [(x, y + 2 * k, 8 * k), (x, y - 6 * k, 5 * k)], 2)
        pygame.draw.line(s, (170, 130, 90), (P(x - 5 * k), P(y - 3 * k)), (P(x + 5 * k), P(y - 3 * k)), 2)
    else:
        ellipse(s, (215, 150, 80), x, y, 20 * k, 12 * k, 2)
        pygame.draw.line(s, (170, 110, 50), (P(x - 4 * k), P(y - 3 * k)), (P(x + 2 * k), P(y + 3 * k)), 1)


def draw_sack(s, x, y, k=1.0, tilt=0.0):
    """Мешок муки: (x, y) — середина низа."""
    sh = math.sin(tilt) * 4 * k
    blob(s, FLOUR_WHITE, [(x + sh * 0.3, y - 14 * k, 17 * k), (x + sh * 0.6, y - 27 * k, 13 * k)], 2)
    poly(s, (232, 222, 200), [(x - 5 * k + sh, y - 38 * k), (x + 5 * k + sh, y - 38 * k), (x + 7 * k + sh, y - 46 * k),
                              (x - 7 * k + sh, y - 46 * k)], 2)
    pygame.draw.line(s, (170, 120, 70), (P(x - 8 * k + sh), P(y - 37 * k)), (P(x + 8 * k + sh), P(y - 37 * k)), max(2, P(3 * k)))
    if k >= 0.9:
        draw_text(s, "МУКА", max(8, int(9 * k)), (x + sh * 0.3, y - 14 * k), (170, 135, 100), outline=None)


def draw_loaf(s, x, y, k=1.0):
    ellipse(s, (212, 145, 72), x, y, 30 * k, 16 * k, 2)
    for i in (-1, 0, 1):
        pygame.draw.line(s, (240, 200, 130), (P(x + i * 7 * k - 2 * k), P(y - 4 * k)), (P(x + i * 7 * k + 2 * k), P(y + 2 * k)), 2)


def draw_toque(s, x, y, k=1.0):
    """Поварской колпак на голове с центром (x, y)."""
    rounded(s, WHITE, (P(x - 11 * k), P(y - 17 * k), P(22 * k), P(9 * k)), 3, 2)
    blob(s, WHITE, [(x - 8 * k, y - 23 * k, 8 * k), (x + 8 * k, y - 23 * k, 8 * k), (x, y - 28 * k, 10 * k)], 2)


def draw_beret(s, x, y, k=1.0):
    """Берет мельника, присыпанный мукой."""
    blob(s, (235, 228, 210), [(x - 4 * k, y - 11 * k, 11 * k), (x + 6 * k, y - 12 * k, 8 * k)], 2)


class MillUI:
    """Экран мельницы и пекарни (вид «barn» на ферме с мельницей)."""

    def init_mill(self):
        self.mill_smoke = []         # [x, y, vx, vy, возраст, жизнь, радиус]
        self.mill_angle = 0.0        # поворот колеса-жернова
        self.mill_walk = 0.0         # путь мельника: 0..2 (туда с мешком и обратно пустым)
        self.mill_puff = 0.0
        self.mill_dust_t = 0.0
        self.baker_x = BAKER_SPOTS[1]
        self.baker_carry = 0.0       # 3.7: пекарь несёт готовую партию на стеллаж (секунды)
        self.mill_prev_bread = 0.0

    # ------------------------------------------------------------ состояние
    def mill_working(self):
        f = self.farm
        return f.m_levels[0] > 0 and f.m_workers[0] > 0 and f.hopper > 0

    def oven_working(self):
        f = self.farm
        return f.m_levels[1] > 0 and f.m_workers[1] > 0 and f.oven_load > 0

    def mill_rate(self):
        """Сколько муки (в $) мельница даёт в секунду."""
        f = self.farm
        return f.mill_speed() * f.m_workers[0] * FLOUR_RATIO

    def bread_batch(self):
        f = self.farm
        return f.bake_rate() * BAKE_TIME * BREAD_RATIO * (1 + 0.25 * f.up("baker"))

    def mill_tick(self, dt):
        """Анимация сцены мельницы (только пока она на экране)."""
        if self.view != "barn" or self.farm_info()["barn"] != "mill":
            self.mill_prev_bread = self.farm.bread
            return
        dt = min(dt, 0.1)
        f = self.farm
        working = self.mill_working()
        spin = 0.9 + 0.25 * f.m_workers[0] if working else 0.0
        self.mill_angle = (self.mill_angle + spin * dt) % (2 * math.pi)
        if f.m_workers[0] > 0:
            self.mill_walk = (self.mill_walk + dt / 4.5) % 2.0
        if working:
            self.mill_dust_t += dt
            if self.mill_dust_t > 0.22:
                self.mill_dust_t = 0.0
                self.fx.dust(WHEEL[0] + random.uniform(-40, 40), BED.y + 4, n=1, color=FLOUR_WHITE, size=(3, 6),
                             spread=6, up=14, alpha=150, life=(0.5, 0.9))
        # дым из трубы: гуще, пока печь печёт
        baking = self.oven_working()
        self.mill_puff += dt * (2.6 if baking else 0.5 if f.m_levels[1] else 0.0)
        while self.mill_puff >= 1.0:
            self.mill_puff -= 1.0
            self.mill_smoke.append([CHIMNEY[0] + random.uniform(-4, 4), CHIMNEY[1], random.uniform(4, 14),
                                    random.uniform(-26, -18), 0.0, random.uniform(2.6, 3.6), random.uniform(7, 10)])
        for p in self.mill_smoke:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] += dt
        self.mill_smoke = [p for p in self.mill_smoke if p[4] < p[5]][-40:]
        # пекарь: у печи, пока печёт; когда партия готова — относит хлеб на стеллаж
        if f.bread > self.mill_prev_bread + 1e-9 and f.m_workers[1] > 0:
            self.baker_carry = 2.4
        self.mill_prev_bread = f.bread
        self.baker_carry = max(0.0, self.baker_carry - dt)
        target = BAKER_SPOTS[1] if self.baker_carry > 0 or not baking else BAKER_SPOTS[0]
        step = 70 * dt
        self.baker_x += max(-step, min(step, target - self.baker_x))

    # ------------------------------------------------------------ действия (кнопки и сцена)
    def do_build(self, b):
        f = self.farm
        was = f.m_levels[b]
        price = f.mill_building_cost(b)
        if f.buy_mill_building(b):
            self.quest("build")
            self.sfx.play("buy")
            name = ("Мельница", "Пекарня")[b]
            self.toast(f"{name}: " + ("построена!" if was == 0 else f"уровень {f.m_levels[b]} (+1 место)"), 2)
            x = WHEEL[0] if b == 0 else OVEN_X
            self.fx.sparks(x, FLOOR - 90, n=10, up=60)
            self.fx.ring(x, FLOOR - 8, r0=20, r1=150, life=0.6)
        else:
            self.toast(f"Не хватает денег: нужно ${fmt(price)}", 2)

    def do_workers(self, b, delta):
        f = self.farm
        if not f.set_mill_workers(b, delta):
            if delta > 0 and f.m_workers[b] >= f.m_levels[b]:
                self.toast("Нет мест: улучши здание", 2)
            elif delta > 0:
                self.toast("Нет свободных крестьян: найми или сними с грядки", 2.5)

    def do_fill(self):
        took = self.farm.fill_hopper()
        if took > 0:
            self.quest("feed")
            self.sfx.play("feed")
            self.floater(HOPPER_X, HOPPER_TOP - 20, "зерно +$" + fmt(took), (240, 220, 150))
            self.fx.dust(HOPPER_X, HOPPER_TOP + 10, n=5, color=(232, 200, 120), size=(3, 6), spread=30, up=30)
        else:
            self.toast("Зерна на грядках нет или закрома полны", 2)

    def do_sell_flour(self):
        amt = self.farm.sell_flour()
        if amt:
            self.sfx.play("product")
            self.floater(SACKS_X, FLOOR - 120, "+$" + fmt(amt))
            self.coins_to_counter(SACKS_X, FLOOR - 60, amt)
            self.fx.dust(SACKS_X, FLOOR - 4, n=6, color=FLOUR_WHITE, size=(4, 8), spread=40, up=20)

    def do_collect_bread(self):
        amt = self.farm.collect_bread()
        if amt:
            self.quest("bread")
            self.sfx.play("product")
            self.floater(SHELF_X, FLOOR - 175, "+$" + fmt(amt))
            self.coins_to_counter(SHELF_X, FLOOR - 90, amt)
            self.toast("Хлеб продан: +$" + fmt(amt), 2)

    # ------------------------------------------------------------ сцена: мельница
    def draw_hopper(self, s, fill, working):
        """Бункер на ножках: горка зерна сверху (по закромам), из воронки сыплется зерно к колесу."""
        hx, top = HOPPER_X, HOPPER_TOP
        heap_k = 0.25 + 0.75 * max(0.0, min(1.0, fill))
        if fill > 0.001:             # горка — ЗА стенкой бункера, торчит над ним тем выше, чем полнее закрома
            if not blit_tf(s, "props/grain_heap", hx, top + 34, 0.85, sy=heap_k):
                h = 46 * heap_k
                poly(s, (226, 184, 90), [(hx - 58, top + 34), (hx - 30, top + 30 - h * 0.7), (hx, top + 28 - h),
                                         (hx + 30, top + 30 - h * 0.7), (hx + 58, top + 34)], 2)
                for i in range(9):
                    gx = hx - 40 + (i * 37) % 80
                    gy = top + 28 - h * 0.45 + (i * 13) % 14
                    if gy > top + 26 - h + 6:
                        ellipse(s, (250, 215, 120), gx, gy, 6, 4, 0)
        if working:                  # струйка зерна из воронки к колесу
            x0, y0 = hx + 22, top + 128
            for i in range(7):
                u = ((self.t * 2.2 + i / 7) % 1.0)
                gx = x0 + (WHEEL[0] - 40 - x0) * u
                gy = y0 + 30 * u + 26 * u * u
                pygame.draw.circle(s, (232, 190, 95), (P(gx), P(gy)), 2)
        if blit_sprite(s, "props/mill_hopper", hx, FLOOR, 0.85, "midbottom"):
            return
        wood, dark = (176, 122, 72), (140, 92, 52)
        for lx in (-44, 44):        # ножки
            rounded(s, dark, (hx + lx - 5, top + 110, 10, FLOOR - top - 110), 3, 2)
        pygame.draw.line(s, OUT, (hx - 44, FLOOR - 40), (hx + 44, FLOOR - 40), 5)
        pygame.draw.line(s, dark, (hx - 44, FLOOR - 40), (hx + 44, FLOOR - 40), 3)
        poly(s, wood, [(hx - 64, top + 30), (hx + 64, top + 30), (hx + 30, top + 112), (hx - 30, top + 112)], 3)
        for k in range(1, 4):       # доски
            y = top + 30 + k * 20
            half = 64 - (64 - 30) * (y - top - 30) / 82
            pygame.draw.line(s, dark, (P(hx - half + 3), P(y)), (P(hx + half - 3), P(y)), 2)
        poly(s, dark, [(hx + 14, top + 108), (hx + 34, top + 108), (hx + 40, top + 130), (hx + 22, top + 132)], 2)

    def draw_wheel(self, s, working):
        """Колесо-жернов на ребре, вращается вокруг оси (рисуется ДО чаши — чаша закрывает его низ)."""
        cx, cy = WHEEL
        deg = -math.degrees(self.mill_angle)
        if blit_tf(s, "props/millstone", cx, cy, 0.8, angle=deg, pivot="center"):
            return
        r = WHEEL_R
        blob(s, (172, 168, 160), [(cx, cy, r)], 3)
        pygame.draw.circle(s, (150, 146, 140), (cx, cy), r - 12, 2)
        for i in range(8):              # борозды жернова
            a = self.mill_angle + i * math.pi / 4
            pygame.draw.line(s, (130, 126, 120), (P(cx + math.cos(a) * 18), P(cy + math.sin(a) * 18)),
                             (P(cx + math.cos(a) * (r - 6)), P(cy + math.sin(a) * (r - 6))), 2)
        pygame.draw.circle(s, OUT, (cx, cy), 15)
        pygame.draw.circle(s, (120, 90, 60), (cx, cy), 12)
        # деревянный вал сверху
        rounded(s, (150, 100, 60), (cx - 7, cy - r - 70, 14, 72), 4, 2)

    def draw_bed(self, s):
        if blit_sprite(s, "props/mill_bed", WHEEL[0], FLOOR, 0.92, "midbottom"):
            return
        r = BED
        rounded(s, (158, 152, 144), r, 14, 3)
        for i in range(5):
            x = r.x + 18 + i * 46
            rounded(s, (170, 164, 156), (x, r.y + 12, 40, 22), 5, 2, (120, 114, 108))
            rounded(s, (164, 158, 150), (x + 20 - (i % 2) * 18, r.y + 40, 40, 22), 5, 2, (120, 114, 108))
        pygame.draw.line(s, FLOUR_WHITE, (r.x + 16, r.y + 4), (r.right - 16, r.y + 4), 4)

    def draw_sacks(self, s, n):
        if n <= 0:
            return
        draw_shadow(s, SACKS_X, FLOOR - 2, 50 + 30 * n, 12, 60)
        if blit_sprite(s, f"props/flour_sacks_{n}", SACKS_X, FLOOR, 0.85, "midbottom"):
            return
        spots = ((0, 0), (-30, 4), (30, 4))[:n]
        if n == 3:
            spots = ((-28, 4), (28, 4), (0, -34))
        for dx, dy in sorted(spots, key=lambda p: p[1]):
            draw_sack(s, SACKS_X + dx, FLOOR - 2 + dy, 1.0, tilt=dx / 30)

    def draw_miller(self, s, n_workers, working):
        if n_workers <= 0:
            return
        x0, x1 = MILLER_PATH
        u = self.mill_walk
        carry = u < 1.0 and working
        frac = u if u < 1.0 else 2.0 - u
        if not working:                      # мельница стоит — мельник ждёт у бункера
            frac, carry = 0.15, False
        x = x0 + (x1 - x0) * (0.5 - 0.5 * math.cos(frac * math.pi))
        moving = working and 0.06 < frac < 0.94
        bob = abs(math.sin(self.t * 7)) * 3 if moving else 0.0
        face = (1 if u < 1.0 else -1) if moving else 0
        draw_shadow(s, x, FLOOR - 2, 46, 10, 70)
        if blit_tf(s, "characters/miller", x, FLOOR - bob, 0.85, flip=(face < 0)):
            if carry:
                draw_sack(s, x + 6 * (face or 1), FLOOR - bob - 104, 0.7)
            return
        k = 0.95
        if carry:                              # мешок на плече — за спиной (рисуется до человечка)
            draw_sack(s, x - 15 * (face or 1), FLOOR - bob - 56, 0.7, tilt=-0.5 * (face or 1))
        arms = ((-2.6, 0.3) if face >= 0 else (-0.3, 2.6)) if carry else (0.25, -0.25)
        draw_person(s, x, FLOOR - bob, k, MILLER_LOOK, self.t, arms=arms, face=face)
        draw_beret(s, x + face * 1.5 * k, FLOOR - bob - 81 * k, k)
        if n_workers > 1:                      # подсказка, что мельников несколько
            draw_text(s, f"x{n_workers}", 14, (x + 22, FLOOR - bob - 104), WHITE)

    # ------------------------------------------------------------ сцена: пекарня
    def draw_oven(self, s, baking):
        f = self.farm
        mx, my = OVEN_MOUTH
        warm = 1.0 if baking else (0.35 if f.m_levels[1] else 0.0)
        if warm > 0:                           # свет от огня на полу и стене
            flick = 0.85 + 0.15 * math.sin(self.t * 9) * math.sin(self.t * 3.7)
            blit_light(s, mx, my + 10, 260 * warm * flick + 60, (255, 170, 90), int(110 * warm))
        has_oven = blit_sprite(s, "props/oven", OVEN_X, FLOOR, 0.9, "midbottom")
        if not has_oven:
            brick, dark = (190, 98, 72), (150, 72, 52)
            rounded(s, (130, 118, 108), (CHIMNEY[0] - 16, CHIMNEY[1], 32, 110), 4, 3)   # труба
            pygame.draw.rect(s, (100, 90, 82), (CHIMNEY[0] - 19, CHIMNEY[1] - 4, 38, 10))
            pygame.draw.rect(s, OUT, (CHIMNEY[0] - 19, CHIMNEY[1] - 4, 38, 10), 2)
            ellipse(s, brick, OVEN_X, FLOOR - 120, 210, 150, 3)
            rounded(s, brick, (OVEN_X - 105, FLOOR - 122, 210, 122), 8, 3)
            pygame.draw.rect(s, brick, (OVEN_X - 102, FLOOR - 128, 204, 14))
            for row in range(5):                  # кирпичи
                y = FLOOR - 112 + row * 22
                for i in range(5):
                    x = OVEN_X - 96 + i * 40 + (20 if row % 2 else 0)
                    if x + 34 < OVEN_X + 100:
                        rounded(s, dark, (x, y, 34, 16), 3, 1, (120, 60, 45))
            ellipse(s, (60, 38, 32), mx, my + 6, 92, 76, 3)          # устье
            pygame.draw.rect(s, (60, 38, 32), (mx - 44, my + 6, 88, FLOOR - my - 14))
            pygame.draw.line(s, OUT, (mx - 46, my + 6), (mx - 46, FLOOR - 8), 3)
            pygame.draw.line(s, OUT, (mx + 46, my + 6), (mx + 46, FLOOR - 8), 3)
            rounded(s, (120, 110, 100), (OVEN_X - 112, FLOOR - 12, 224, 14), 4, 2)
        # огонь
        if warm > 0:
            flick = math.sin(self.t * 11) * 0.5 + math.sin(self.t * 17 + 1) * 0.5
            if not blit_tf(s, "props/oven_fire", mx, FLOOR - 14, 0.9 * (0.6 + 0.4 * warm), sy=1.0 + 0.08 * flick,
                           alpha=int(255 * min(1.0, 0.45 + warm))):
                hgt = (26 + 8 * flick) * warm + 6
                for dx, col, w in ((-18, (240, 120, 50), 16), (16, (240, 120, 50), 16), (0, (255, 175, 60), 22),
                                   (0, (255, 230, 120), 10)):
                    sway = math.sin(self.t * 8 + dx) * 3
                    poly(s, col, [(mx + dx - w, FLOOR - 16), (mx + dx + w, FLOOR - 16),
                                  (mx + dx + sway, FLOOR - 16 - hgt * (1.3 if w < 15 else 1.0))], 0)
                for dx in (-24, -8, 10, 26):            # угли
                    ellipse(s, (250, 120, 50) if baking else (180, 70, 40), mx + dx, FLOOR - 15, 14, 7, 1)
        if baking:                                       # пока печёт — искорки
            if random.random() < 0.08:
                self.fx.sparks(mx + random.uniform(-20, 20), my + 20, n=1, colors=((255, 200, 90),),
                               speed=(20, 50), life=(0.4, 0.8), gravity=-30, up=40)

    def draw_smoke(self, s):
        for x, y, vx, vy, age, life, r in self.mill_smoke:
            u = age / life
            a = int(150 * (1 - u) * min(1.0, age * 3))
            if a > 8:
                img = soft_dot(r * (1 + 1.8 * u), (215, 210, 205), a)
                s.blit(img, img.get_rect(center=(int(x), int(y))))

    def draw_shelf(self, s, loaves):
        if not blit_sprite(s, "props/bread_shelf", SHELF_X, FLOOR, 0.85, "midbottom"):
            wood, dark = (170, 115, 70), (130, 85, 50)
            for lx in (-74, 74):
                rounded(s, dark, (SHELF_X + lx - 6, FLOOR - 160, 12, 160), 3, 2)
            for y in (FLOOR - 112, FLOOR - 62, FLOOR - 14):
                rounded(s, wood, (SHELF_X - 82, y, 164, 10), 3, 2)
        rows = (FLOOR - 18, FLOOR - 66, FLOOR - 116)
        for i in range(loaves):
            row, col = divmod(i, 3)
            draw_loaf(s, SHELF_X - 46 + col * 46, rows[row] - 7, 1.0)

    def draw_baker(self, s, n_workers, baking):
        if n_workers <= 0:
            return
        x = self.baker_x
        moving = abs(x - BAKER_SPOTS[0]) > 2 and abs(x - BAKER_SPOTS[1]) > 2
        bob = abs(math.sin(self.t * 7)) * 3 if moving else 0.0
        at_oven = abs(x - BAKER_SPOTS[0]) < 3 and baking
        push = math.sin(self.t * 2.4) * 8 if at_oven else 0.0
        draw_shadow(s, x, FLOOR - 2, 46, 10, 70)
        carrying = self.baker_carry > 0
        if not blit_tf(s, "characters/baker", x, FLOOR - bob, 0.85, flip=not carrying):
            k = 0.95
            face = 1 if carrying else -1
            hands = draw_person(s, x, FLOOR - bob, k, BAKER_LOOK, self.t, arms=(0.9, -1.2) if not carrying else (-1.6, 1.6),
                                face=face)
            draw_toque(s, x + face * 1.5 * k, FLOOR - bob - 81 * k, k)
        else:
            hands = [(x - 18, FLOOR - bob - 70), (x + 18, FLOOR - bob - 70)]
        if carrying:                       # корзинка с горячим хлебом
            bx, by = x, FLOOR - bob - 72
            rounded(s, (190, 140, 80), (P(bx - 22), P(by), 44, 18), 6, 2)
            for dx in (-10, 8):
                draw_loaf(s, bx + dx, by - 1, 0.6)
        else:                               # лопата для хлеба — в печь
            hx, hy = hands[0]
            tip_x = hx - 74 + push
            pygame.draw.line(s, OUT, (P(hx + 8), P(hy - 4)), (P(tip_x), P(hy + 6)), 6)
            pygame.draw.line(s, (176, 128, 80), (P(hx + 8), P(hy - 4)), (P(tip_x), P(hy + 6)), 3)
            poly(s, (190, 140, 90), [(tip_x, hy + 1), (tip_x, hy + 12), (tip_x - 28, hy + 14), (tip_x - 30, hy + 2)], 2)
        if n_workers > 1:
            draw_text(s, f"x{n_workers}", 14, (x + 22, FLOOR - bob - 104), WHITE)

    # ------------------------------------------------------------ подсказки и ярлычки на сцене
    def scene_tag(self, x, y, kind, text, sub, cb, enabled, tip):
        """Деревянная табличка над предметом: иконка, сумма, подпись «нажми». Нажимается вся."""
        s = self.screen
        r = pygame.Rect(0, 0, 150, 42)
        r.midbottom = (int(x), int(y))
        r.x = max(96, min(W - 8 - r.w, r.x))
        grow = self.btn_anim(r, enabled) if enabled else 0.0
        look = r.inflate(int(round(6 * grow)), int(round(4 * grow)))
        rounded(s, CARD if enabled else (214, 204, 186), look, 9, 2)
        draw_icon(s, kind, look.x + 20, look.centery)
        draw_text_fit(s, text, 14, (look.x + 36, look.centery - 8), look.w - 42, BROWN, anchor="midleft", outline=None)
        draw_text_fit(s, sub, 11, (look.x + 36, look.centery + 10), look.w - 42, OK_GREEN if enabled and "пуст" not in sub else SOFT,
                      anchor="midleft", outline=None)
        if enabled:
            self.zone_btn(r, cb, 9)
        self.tip(r, tip)

    def draw_station_ghost(self, key, draw_fn, alpha=95):
        """Ещё не построенное здание — полупрозрачным силуэтом (он не двигается — рисуется один раз)."""
        cache = self.__dict__.setdefault("_mill_ghosts", {})
        layer = cache.get((key, hd.scale()))
        if layer is None:
            layer = hd.Surface((W, H), pygame.SRCALPHA)
            layer.fill((0, 0, 0, 0))
            draw_fn(layer)
            hd.real(layer).set_alpha(alpha)
            cache[(key, hd.scale())] = layer
        self.screen.blit(layer, (0, 0))

    def draw_build_sign(self, b, x, y):
        s, f = self.screen, self.farm
        can = f.mill_can_build(b)
        price = f.mill_building_cost(b)
        r = pygame.Rect(0, 0, 250, 92)
        r.center = (x, y)
        rounded(s, CARD, r, 12, 3)
        name = ("Мельница", "Пекарня")[b]
        if can:
            draw_text_fit(s, (name + ": мелет зерно в муку") if b == 0 else (name + ": печёт хлеб из муки"), 14,
                          (r.centerx, r.y + 18), r.w - 20, BROWN, outline=None)
            self.button((r.x + 18, r.y + 38, r.w - 36, 42), "Построить $" + fmt(price), lambda b=b: self.do_build(b),
                        BTN_GREEN, f.money >= price, 17)
        else:
            msg = ("Сначала посади: " + CROPS[GRAIN[0]]["name"]) if b == 0 else "Сначала построй мельницу"
            draw_text(s, name, 17, (r.centerx, r.y + 26), BROWN, outline=None)
            draw_text_fit(s, msg, 14, (r.centerx, r.y + 58), r.w - 24, RED, outline=None)

    # ------------------------------------------------------------ карточки внизу
    def draw_workers_row(self, r, b, label):
        s, f = self.screen, self.farm
        lvl = f.m_levels[b]
        y = r.y + 54
        draw_text(s, label, 13, (r.x + 14, y), BROWN, anchor="midleft", outline=None)
        x0 = r.x + 104
        for k in range(lvl):
            if k < f.m_workers[b]:
                draw_peasant_head(s, x0 + k * 22, y, 0.95)
            else:
                pygame.draw.circle(s, (205, 195, 180), (x0 + k * 22, y), 8)
        bx = x0 + MILL_MAX_LVL * 22 + 2
        self.button((bx, y - 15, 32, 30), "-", lambda b=b: self.do_workers(b, -1), BTN_BLUE, f.m_workers[b] > 0, 18)
        self.button((bx + 36, y - 15, 32, 30), "+", lambda b=b: self.do_workers(b, +1), BTN_GREEN, True, 18)
        self.tip(pygame.Rect(bx, y - 15, 68, 30), f"Свободных крестьян: {f.free_peasants()}")
        ub = pygame.Rect(r.right - 152, y - 16, 142, 32)
        if lvl >= MILL_MAX_LVL:
            rounded(s, (250, 212, 90), ub, 9, 2)
            draw_text(s, "Макс. уровень", 14, ub.center, BROWN, outline=None)
        else:
            price = f.mill_building_cost(b)
            self.button(ub, f"Ур.{lvl + 1}: ${fmt(price)}", lambda b=b: self.do_build(b), BTN_BLUE, f.money >= price, 14)
            self.tip(ub, "Улучшить: +1 место для работника")

    def draw_mill_cards(self):
        s, f = self.screen, self.farm
        for b, r in ((0, MILL_CARD), (1, BAKE_CARD)):
            rounded(s, CARD if f.m_levels[b] else (214, 204, 186), r, 12, 3)
            lvl = f.m_levels[b]
            name = ("Мельница", "Пекарня")[b]
            draw_text(s, name + (f"  ур. {lvl}" if lvl else ""), 16, (r.x + 14, r.y + 19), BROWN, anchor="midleft",
                      outline=None)
            if not lvl:
                sub = ("Зерно (рожь, ячмень, полба) -> мука x1.5", f"Мука -> хлеб x{BREAD_RATIO:g}, партиями по {BAKE_TIME:g} с")[b]
                draw_text_fit(s, sub, 13, (r.x + 14, r.y + 52), r.w - 28, SOFT, anchor="midleft", outline=None)
                continue
            if b == 0:
                speed = f.mill_speed() * f.m_workers[0]
                if not f.m_workers[0]:
                    msg, col = "Стоит: нет мельников", RED
                elif f.hopper <= 0:
                    msg, col = "Стоит: закрома пусты", RED
                else:
                    share = min(100, round(speed / max(1e-9, f.grain_rate()) * 100))
                    msg, col = f"Мелет ${fmt(speed)}/с ({share}% зерна)", OK_GREEN
            else:
                if not f.m_workers[1]:
                    msg, col = "Стоит: нет пекарей", RED
                elif f.oven_load > 0:
                    msg, col = f"Печёт: {int(f.oven_prog / BAKE_TIME * 100)}%", OK_GREEN
                elif f.flour > 0:
                    msg, col = f"Копит муку: {min(99, int(f.flour / max(1e-9, f.bake_rate() * BAKE_TIME) * 100))}%", (150, 120, 60)
                else:
                    msg, col = "Ждёт муку", RED
            draw_text_fit(s, msg, 13, (r.right - 12, r.y + 19), r.w - 190, col, anchor="midright", outline=None)
            self.draw_workers_row(r, b, ("Мельники", "Пекари")[b])

    # ------------------------------------------------------------ весь экран
    def draw_mill_view(self):
        s, f = self.screen, self.farm
        s.blit(self.mill_bg, (0, 0))
        plate = pygame.Rect(W // 2 + 70, 26, 220, 44)
        rounded(s, (240, 222, 212), plate, 8, 3)
        draw_text(s, "МЕЛЬНИЦА", 22, plate.center, BROWN, outline=None)
        mill_on, bake_on = f.m_levels[0] > 0, f.m_levels[1] > 0
        working, baking = self.mill_working(), self.oven_working()
        cap = f.hopper_cap()
        fill = f.hopper / cap if cap > 0 else 0.0

        # --- пекарня (дальше от зрителя — рисуем первой: дым уходит за плашки)
        def bakery(layer):
            self.draw_oven(layer, baking)
            self.draw_shelf(layer, bread_loaves(f.bread, self.bread_batch()))
        if bake_on:
            self.draw_smoke(s)
            bakery(s)
            self.draw_baker(s, f.m_workers[1], baking)
            if baking:                                      # полоска партии над печью
                draw_bar(s, (OVEN_X - 50, OVEN_MOUTH[1] - 74, 100, 10), f.oven_prog / BAKE_TIME, (240, 150, 70))
            self.zone(SCENE_ZONES["shelf"], self.do_collect_bread) if f.bread > 0 else None
            self.scene_tag(SHELF_X, FLOOR - 166, "bread", "Хлеб: $" + fmt(f.bread),
                           "нажми — продать" if f.bread > 0 else "пока пусто", self.do_collect_bread, f.bread > 0,
                           "Продать весь хлеб со стеллажа")
        else:
            self.draw_station_ghost("bakery", bakery)
            self.draw_build_sign(1, 790, 420)

        # --- мельница
        def mill(layer):
            self.draw_hopper(layer, fill, working)
            self.draw_wheel(layer, working)
            self.draw_bed(layer)
            self.draw_sacks(layer, flour_sacks(f.flour, self.mill_rate()))
        if mill_on:
            mill(s)
            self.draw_miller(s, f.m_workers[0], working)
            # закрома: полоска на бункере и табличка «засыпать»
            draw_bar(s, (HOPPER_X - 46, HOPPER_TOP + 60, 92, 11), fill, (230, 200, 110))
            self.zone_btn(SCENE_ZONES["hopper"], self.do_fill, 10)
            self.tip(SCENE_ZONES["hopper"], f"Закрома: ${fmt(f.hopper)} из ${fmt(cap)}. Нажми — засыпать зерно с грядок")
            grain = sum(f.stash[i] for i in GRAIN)
            self.scene_tag(HOPPER_X, HOPPER_TOP - 8, "grain", "Засыпать зерно",
                           ("на грядках $" + fmt(grain)) if grain > 0 else "на грядках пусто", self.do_fill, True,
                           "Засыпать зерно с грядок в закрома (сколько влезет)")
            self.zone(SCENE_ZONES["sacks"], self.do_sell_flour) if f.flour > 0 else None
            self.scene_tag(SACKS_X, FLOOR - 112, "flour", "Мука: $" + fmt(f.flour),
                           "нажми — продать" if f.flour > 0 else "пока пусто", self.do_sell_flour, f.flour > 0,
                           "Продать муку. Пекарня берёт муку сама — продавай лишнюю")
        else:
            self.draw_station_ghost("mill", mill)
            self.draw_build_sign(0, 330, 420)

        self.draw_mill_cards()
        for x, y, text, life, color in self.floaters:
            draw_text(s, text, 18, (x, y), color)
