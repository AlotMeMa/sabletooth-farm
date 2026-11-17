# -*- coding: utf-8 -*-
"""Экран мельницы (3.12): три карточки в стиле сарая — Мельница, Мука, Пекарня.

До 3.12 тут была «живая сцена в разрезе» (3.7–3.11.3): отдельные картинки из Gemini не стыковались по ракурсу,
поэтому решение пользователя (17.11) — карточки, как стойла в сарае: шапка, картинка на подстилке, полоски,
работники и кнопки.

Подмешивается в App (class App(TavernUI, MillUI, ...)). Логика — в logic.py (Farm.fill_hopper, _run_mill ...).
Свои картинки (необязательно): props/millstone (жернов, крутится), props/grain_heap (горка в закромах),
props/flour_sacks_1..3 (мешки по запасу муки), props/oven. Нет — рисуется кодом.
"""
import math

import pygame

from .config import W, fmt, MILL_MAX_LVL, CROPS, GRAIN, BREAD_RATIO, BAKE_TIME, FLOUR_RATIO
from .art import (OUT, BTN_GREEN, BTN_BLUE, P, poly, ellipse, blob, rounded, draw_text, draw_text_fit, draw_bar,
                  blit_sprite, blit_tf, blit_light, render_text, draw_peasant_head, has_sprite, sprite)
from . import hd

BROWN, SOFT = (90, 70, 60), (140, 110, 95)
RED, OK_GREEN = (190, 80, 70), (60, 130, 50)
CARD_ON, CARD_OFF, HEAD = (238, 220, 186), (205, 190, 170), (150, 98, 62)   # как стойла в сарае
FLOUR_WHITE = (246, 240, 226)
ORANGE = (235, 170, 70)
CARD_W, CARD_GAP, CARD_Y, CARD_H = 300, 12, 190, 368   # ниже плашек слева (у средневековья их 4)
VIGNETTE_K = 0.66                # props/mill_card, props/bakery_card: холст 360x130 -> ~240x86 в карточке
OVEN_FIRE = (0.31, 0.55)         # где огонь на картинке bakery_card (доля ширины/высоты) — там мерцает свет
PIC_Y = 128                      # пол «картинки» в карточке (от верха карточки)


def card_rect(n):
    x0 = (W - (3 * CARD_W + 2 * CARD_GAP)) // 2
    return pygame.Rect(x0 + n * (CARD_W + CARD_GAP), CARD_Y, CARD_W, CARD_H)


def flour_sacks(flour, rate):
    """Сколько мешков муки показать (0..3): мешок — около минуты работы мельницы."""
    if flour <= 0:
        return 0
    if rate <= 0:
        return 3
    minutes = flour / (rate * 60)
    return 1 if minutes < 1 else (2 if minutes < 3 else 3)


def bread_loaves(bread, batch):
    """Сколько буханок показать (0..6): партия печи — три буханки."""
    if bread <= 0:
        return 0
    if batch <= 0:
        return 6
    return max(1, min(6, int(math.ceil(bread / batch * 3))))


def draw_sack(s, x, y, k=1.0):
    """Мешок муки кодом: (x, y) — середина низа."""
    blob(s, FLOUR_WHITE, [(x, y - 14 * k, 17 * k), (x, y - 27 * k, 13 * k)], 2)
    poly(s, (232, 222, 200), [(x - 5 * k, y - 38 * k), (x + 5 * k, y - 38 * k), (x + 7 * k, y - 46 * k),
                              (x - 7 * k, y - 46 * k)], 2)
    pygame.draw.line(s, (170, 120, 70), (P(x - 8 * k), P(y - 37 * k)), (P(x + 8 * k), P(y - 37 * k)), max(2, P(3 * k)))


def draw_loaf(s, x, y, k=1.0):
    ellipse(s, (212, 145, 72), x, y, 30 * k, 16 * k, 2)
    for i in (-1, 0, 1):
        pygame.draw.line(s, (240, 200, 130), (P(x + i * 7 * k - 2 * k), P(y - 4 * k)), (P(x + i * 7 * k + 2 * k), P(y + 2 * k)), 2)


class MillUI:
    """Экран мельницы и пекарни (вид «barn» на ферме с мельницей)."""

    def init_mill(self):
        self.mill_angle = 0.0        # поворот жернова
        self.mill_spin = 0.0         # скорость жернова: плавно разгоняется и тормозит

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
        if self.view != "barn" or self.farm_info()["barn"] != "mill":
            return
        dt = min(dt, 0.1)
        want = 1.0 + 0.3 * self.farm.m_workers[0] if self.mill_working() else 0.0
        step = 1.5 * dt
        self.mill_spin += max(-step, min(step, want - self.mill_spin))
        self.mill_angle = (self.mill_angle + self.mill_spin * dt) % (2 * math.pi)

    # ------------------------------------------------------------ действия
    def do_build(self, b):
        f = self.farm
        was = f.m_levels[b]
        price = f.mill_building_cost(b)
        if f.buy_mill_building(b):
            self.quest("build")
            self.sfx.play("buy")
            name = ("Мельница", "Пекарня")[b]
            self.toast(f"{name}: " + ("построена!" if was == 0 else f"уровень {f.m_levels[b]} (+1 место)"), 2)
            r = card_rect(0 if b == 0 else 2)
            self.fx.sparks(r.centerx, r.y + PIC_Y - 30, n=10, up=60)
            self.fx.ring(r.centerx, r.y + PIC_Y, r0=20, r1=130, life=0.6)
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
        r = card_rect(0)
        if took > 0:
            self.quest("feed")
            self.sfx.play("feed")
            self.floater(r.centerx, r.y + 70, "зерно +$" + fmt(took), (240, 220, 150))
            self.fx.dust(r.centerx - 60, r.y + PIC_Y, n=5, color=(232, 200, 120), size=(3, 6), spread=24, up=24)
        else:
            self.toast("Зерна на грядках нет или закрома полны", 2)

    def do_sell_flour(self):
        amt = self.farm.sell_flour()
        if amt:
            r = card_rect(1)
            self.quest("flour_sell")
            self.sfx.play("product")
            self.floater(r.centerx, r.y + 70, "+$" + fmt(amt))
            self.coins_to_counter(r.centerx, r.y + PIC_Y - 30, amt)
            self.fx.dust(r.centerx, r.y + PIC_Y, n=6, color=FLOUR_WHITE, size=(4, 8), spread=40, up=20)

    def do_collect_bread(self):
        amt = self.farm.collect_bread()
        if amt:
            r = card_rect(2)
            self.quest("bread")
            self.sfx.play("product")
            self.floater(r.centerx, r.y + 70, "+$" + fmt(amt))
            self.coins_to_counter(r.centerx, r.y + PIC_Y - 30, amt)
            self.toast("Хлеб продан: +$" + fmt(amt), 2)

    # ------------------------------------------------------------ части карточки
    def card_frame(self, r, title, active, floor=True):
        """Карточка как стойло в сарае: шапка, подстилка под картинкой, подпись на плашке."""
        s = self.screen
        rounded(s, CARD_ON if active else CARD_OFF, r, 12, 3, skin=None)
        head = pygame.Rect(r.x, r.y, r.w, 34)
        pygame.draw.rect(s, HEAD, head, border_top_left_radius=12, border_top_right_radius=12)
        pygame.draw.rect(s, OUT, head, 3, border_top_left_radius=12, border_top_right_radius=12)
        draw_text(s, title, 17, head.center)
        if floor:                 # подстилка, как в стойле (у своих сценок пол нарисован — без неё)
            ellipse(s, (240, 210, 110), r.centerx, r.y + PIC_Y + 8, 210, 34, ow=0)

    def card_caption(self, r, caption, active):
        """Подпись на плашке — поверх картинки (как в сарае)."""
        s = self.screen
        img = render_text(caption, 12, SOFT, None)
        box = img.get_rect(center=(r.centerx, r.y + 46)).inflate(12, 4)
        plate = hd.Surface(box.size, pygame.SRCALPHA)
        plate.fill((238, 220, 186, 215) if active else (205, 190, 170, 215))
        s.blit(plate, box)
        s.blit(img, img.get_rect(center=box.center))

    def card_shade(self, r):
        """Не построено — картинка под полупрозрачной пеленой."""
        shade = hd.Surface((r.w - 20, 96), pygame.SRCALPHA)
        shade.fill((205, 190, 170, 170))
        self.screen.blit(shade, (r.x + 10, r.y + 58))

    def workers_row(self, r, b, y, label):
        s, f = self.screen, self.farm
        lvl = f.m_levels[b]
        draw_text(s, label, 14, (r.x + 16, y + 18), BROWN, anchor="midleft", outline=None)
        x0 = r.x + 112
        for k in range(MILL_MAX_LVL):
            cx = x0 + k * 17
            if k < f.m_workers[b]:
                draw_peasant_head(s, cx, y + 18, 0.85)
            elif k < lvl:
                pygame.draw.circle(s, (205, 195, 180), (cx, y + 18), 7)
        self.button((r.right - 84, y + 2, 34, 32), "-", lambda b=b: self.do_workers(b, -1), BTN_BLUE, f.m_workers[b] > 0, 18)
        self.button((r.right - 46, y + 2, 34, 32), "+", lambda b=b: self.do_workers(b, +1), BTN_GREEN, True, 18)
        self.tip(pygame.Rect(r.x + 8, y + 2, r.w - 96, 32), f"{label}: {f.m_workers[b]} из {lvl} мест")
        self.tip(pygame.Rect(r.right - 84, y + 2, 72, 32), f"Свободных крестьян: {f.free_peasants()}")

    def upgrade_button(self, r, b, y):
        s, f = self.screen, self.farm
        bu = pygame.Rect(r.x + 14, y, r.w - 28, 36)
        lvl = f.m_levels[b]
        if lvl >= MILL_MAX_LVL:
            rounded(s, (250, 212, 90), bu, 9, 2)
            draw_text(s, "Макс. уровень", 15, bu.center, BROWN, outline=None)
            return
        price = f.mill_building_cost(b)
        self.button(bu, f"Ур. {lvl + 1} (+1 место): ${fmt(price)}", lambda b=b: self.do_build(b), BTN_BLUE,
                    f.money >= price, 15)

    def build_block(self, r, b, can, why):
        s, f = self.screen, self.farm
        price = f.mill_building_cost(b)
        if not can:
            draw_text_fit(s, why, 14, (r.centerx, r.y + 200), r.w - 20, RED, outline=None)
        else:
            text = ("Мелет зерно с грядок в муку", "Печёт хлеб из муки")[b]
            draw_text(s, text, 14, (r.centerx, r.y + 190), BROWN, outline=None)
            draw_text_fit(s, ("работают крестьяне: 1 место на уровень", "хлеб дороже муки в 2.5 раза")[b], 12,
                          (r.centerx, r.y + 212), r.w - 20, SOFT, outline=None)
        b_rect = pygame.Rect(r.x + 16, r.bottom - 64, r.w - 32, 46)
        self.button(b_rect, "Построить $" + fmt(price), lambda b=b: self.do_build(b), BTN_GREEN,
                    can and f.money >= price, 18)

    # ------------------------------------------------------------ картинки
    def vignette(self, r, name, active):
        """Своя картинка карточки (props/mill_card, props/bakery_card) — одна сценка вместо набора предметов.
        Пока здание работает, чуть «дышит». False — картинки нет."""
        k = 1.0 + (0.012 * math.sin(self.t_real * 3) if active else 0.0)
        return blit_tf(self.screen, name, r.centerx, r.y + PIC_Y + 12, VIGNETTE_K, sx=k, sy=2 - k)

    def pic_mill(self, r, active):
        s, f = self.screen, self.farm
        cx, floor = r.centerx + 30, r.y + PIC_Y
        if self.vignette(r, "props/mill_card", active and self.mill_spin > 0.3):
            if active and self.mill_spin > 0.3 and int(self.t_real * 5) % 2 == 0:
                self.fx.dust(r.centerx + (-50 if int(self.t_real * 7) % 2 else 50), floor + 8, n=1, color=FLOUR_WHITE,
                             size=(3, 5), spread=8, up=12, alpha=140, life=(0.4, 0.7))
            return
        cap = f.hopper_cap()
        fill = f.hopper / cap if cap > 0 else 0.0
        # горка зерна слева — растёт с закромами
        hx = r.centerx - 78
        if fill > 0.01 or not active:
            k = 0.3 + 0.7 * min(1.0, fill) if active else 0.7
            if not blit_tf(s, "props/grain_heap", hx, floor + 4, 0.55, sy=k):
                hgt = 34 * k
                poly(s, (226, 184, 90), [(hx - 46, floor + 4), (hx, floor + 2 - hgt), (hx + 46, floor + 4)], 2)
        # жернов: крутится, пока мелют
        deg = -math.degrees(self.mill_angle)
        if not blit_tf(s, "props/millstone", cx, floor - 30, 0.4, angle=deg, pivot="center"):
            R = 30
            blob(s, (172, 168, 160), [(cx, floor - 30, R)], 3)
            for i in range(8):
                a = self.mill_angle + i * math.pi / 4
                pygame.draw.line(s, (138, 132, 126), (P(cx + math.cos(a) * 14), P(floor - 30 + math.sin(a) * 14)),
                                 (P(cx + math.cos(a) * (R - 5)), P(floor - 30 + math.sin(a) * (R - 5))), 2)
            pygame.draw.circle(s, OUT, (P(cx), P(floor - 30)), 11)
            pygame.draw.circle(s, (120, 90, 60), (P(cx), P(floor - 30)), 9)
        if active and self.mill_spin > 0.3 and int(self.t_real * 5) % 2 == 0:
            self.fx.dust(cx + (-30 if int(self.t_real * 7) % 2 else 30), floor - 4, n=1, color=FLOUR_WHITE,
                         size=(3, 5), spread=6, up=12, alpha=140, life=(0.4, 0.7))

    def pic_flour(self, r, n):
        s = self.screen
        cx, floor = r.centerx, r.y + PIC_Y + 8
        if n <= 0:
            draw_text(s, "пусто", 14, (cx, floor - 30), SOFT, outline=None)
            return
        if blit_sprite(s, f"props/flour_sacks_{n}", cx, floor, 0.62, "midbottom"):
            return
        spots = ((0, 0),) if n == 1 else ((-22, 0), (22, 0)) if n == 2 else ((-30, 0), (30, 0), (0, -30))
        for dx, dy in sorted(spots, key=lambda p: -p[1]):
            draw_sack(s, cx + dx, floor + dy, 1.0)

    def pic_bakery(self, r, baking, loaves, active):
        s = self.screen
        ox, floor = r.centerx - 54, r.y + PIC_Y + 8
        warm = 1.0 if baking else (0.3 if active else 0.0)
        if self.vignette(r, "props/bakery_card", baking):
            if warm > 0:            # огонь в нарисованной печи мерцает
                img = sprite("props/bakery_card")
                w, h = img.get_width() * VIGNETTE_K, img.get_height() * VIGNETTE_K
                fx = r.centerx - w / 2 + w * OVEN_FIRE[0]
                fy = r.y + PIC_Y + 12 - h + h * OVEN_FIRE[1]
                fl = 0.8 + 0.2 * math.sin(self.t_real * 9) * math.sin(self.t_real * 3.7)
                blit_light(s, fx, fy, 70 * fl * warm + 20, (255, 190, 100), int(120 * warm))
            return
        if warm > 0:
            fl = 0.85 + 0.15 * math.sin(self.t_real * 9) * math.sin(self.t_real * 3.7)
            blit_light(s, ox, floor - 18, 90 * warm * fl + 30, (255, 170, 90), int(110 * warm))
        if not blit_sprite(s, "props/oven", ox, floor, 0.3, "midbottom"):
            brick = (190, 98, 72)
            ellipse(s, brick, ox, floor - 36, 74, 54, 3)
            rounded(s, brick, (P(ox - 37), P(floor - 38), 74, 38), 5, 3)
            pygame.draw.rect(s, brick, (P(ox - 34), P(floor - 41), 68, 6))
            ellipse(s, (60, 38, 32), ox, floor - 17, 34, 28, 2)
            pygame.draw.rect(s, (60, 38, 32), (P(ox - 16), P(floor - 17), 32, 13))
        if warm > 0:
            fx = math.sin(self.t_real * 11) * 0.5 + math.sin(self.t_real * 17 + 1) * 0.5
            hgt = (11 + 4 * fx) * warm + 3
            for dx, col, w in ((-6, (240, 120, 50), 6), (6, (240, 120, 50), 6), (0, (255, 180, 60), 8), (0, (255, 230, 120), 3)):
                poly(s, col, [(ox + dx - w, floor - 6), (ox + dx + w, floor - 6), (ox + dx, floor - 6 - hgt)], 0)
        # буханки на подносе справа
        tx = r.centerx + 66
        rounded(s, (176, 120, 70), (P(tx - 44), P(floor - 6), 88, 10), 4, 2)
        for i in range(loaves):
            row, col = divmod(i, 3)
            draw_loaf(s, tx - 26 + col * 26 + (13 if row else 0), floor - 12 - row * 12, 0.85)
        if loaves == 0 and active:
            draw_text(s, "пусто", 12, (tx, floor - 22), SOFT, outline=None)

    # ------------------------------------------------------------ карточки
    def card_mill(self):
        s, f = self.screen, self.farm
        r = card_rect(0)
        lvl = f.m_levels[0]
        self.card_frame(r, "Мельница" + (f"  ур. {lvl}" if lvl else ""), lvl > 0, not has_sprite("props/mill_card"))
        self.pic_mill(r, lvl > 0)
        self.card_caption(r, "Рожь, ячмень, полба  ->  мука x1.5", lvl > 0)
        if not lvl:
            self.card_shade(r)
            self.build_block(r, 0, f.mill_can_build(0), "Сначала посади: " + CROPS[GRAIN[0]]["name"])
            return
        cap = f.hopper_cap()
        draw_bar(s, (r.x + 20, r.y + 154, r.w - 40, 12), f.hopper / cap if cap > 0 else 0, (230, 200, 110))
        sec = f.hopper_seconds()
        left = f"зерна на {int(sec // 60)}:{int(sec % 60):02d} помола" if sec != float("inf") else f"${fmt(f.hopper)} зерна"
        draw_text(s, "Закрома: " + left, 12, (r.centerx, r.y + 177), BROWN, outline=None)
        self.tip(pygame.Rect(r.x + 20, r.y + 148, r.w - 40, 38),
                 f"В закромах ${fmt(f.hopper)} из ${fmt(cap)}. Мельники сами носят зерно с грядок")
        speed = f.mill_speed() * f.m_workers[0]
        if not f.m_workers[0]:
            msg, col = "Стоит: нет мельников", RED
        elif f.hopper <= 0:
            msg, col = "Ждёт зерно с грядок", (150, 120, 60)
        else:
            share = min(100, round(speed / max(1e-9, f.grain_rate()) * 100))
            msg, col = f"Мелет ${fmt(speed)}/с  ({share}% зерна)", OK_GREEN
        draw_text_fit(s, msg, 13, (r.centerx, r.y + 197), r.w - 16, col, outline=None)
        grain = sum(f.stash[i] for i in GRAIN)
        draw_text_fit(s, f"Зерно на грядках: ${fmt(grain)}", 11, (r.centerx, r.y + 215), r.w - 16, SOFT, outline=None)
        self.workers_row(r, 0, r.y + 230, "Мельники")
        draw_text_fit(s, "Мельники сами носят зерно с грядок" if f.m_workers[0] else "Поставь мельников — зерно понесут сами",
                      12, (r.centerx, r.y + 294), r.w - 20, SOFT if f.m_workers[0] else RED, outline=None)
        self.zone((r.x + 8, r.y + 56, r.w - 16, 84), self.do_fill)   # клик по картинке — подсыпать вручную
        self.upgrade_button(r, 0, r.y + 326)

    def card_flour(self):
        s, f = self.screen, self.farm
        r = card_rect(1)
        on = f.m_levels[0] > 0
        self.card_frame(r, "Мука", on)
        self.pic_flour(r, flour_sacks(f.flour, self.mill_rate()) if on else 1)
        self.card_caption(r, "Пекарня берёт муку сама — лишнюю продай", on)
        if not on:
            self.card_shade(r)
            draw_text_fit(s, "Сначала построй мельницу", 14, (r.centerx, r.y + 200), r.w - 20, RED, outline=None)
            return
        draw_text_fit(s, "$" + fmt(f.flour), 26, (r.centerx, r.y + 172), r.w - 20, (255, 235, 120))
        rate = self.mill_rate()
        draw_text_fit(s, f"мельница: +${fmt(rate)}/с" if rate > 0 and self.mill_working() else "мельница стоит", 12,
                      (r.centerx, r.y + 197), r.w - 16, SOFT, outline=None)
        use = f.bake_rate() if f.m_levels[1] and f.m_workers[1] else 0.0
        draw_text_fit(s, f"пекарня берёт: ${fmt(use)}/с" if use > 0 else "пекарня муку не берёт", 12,
                      (r.centerx, r.y + 215), r.w - 16, SOFT, outline=None)
        self.button((r.x + 14, r.y + 280, r.w - 28, 36), "Продать муку" + (f": ${fmt(f.flour)}" if f.flour > 0 else ""),
                    self.do_sell_flour, ORANGE, f.flour > 0, 15)
        if f.flour > 0:
            self.zone((r.x + 8, r.y + 56, r.w - 16, 84), self.do_sell_flour)

    def card_bakery(self):
        s, f = self.screen, self.farm
        r = card_rect(2)
        lvl = f.m_levels[1]
        baking = self.oven_working()
        self.card_frame(r, "Пекарня" + (f"  ур. {lvl}" if lvl else ""), lvl > 0, not has_sprite("props/bakery_card"))
        self.pic_bakery(r, baking, bread_loaves(f.bread, self.bread_batch()) if lvl else 3, lvl > 0)
        self.card_caption(r, f"Мука  ->  хлеб x{BREAD_RATIO:g}, партиями по {BAKE_TIME:g} с", lvl > 0)
        if not lvl:
            self.card_shade(r)
            self.build_block(r, 1, f.mill_can_build(1), "Сначала построй мельницу")
            return
        draw_bar(s, (r.x + 20, r.y + 154, r.w - 40, 12), f.oven_prog / BAKE_TIME if f.oven_load > 0 else 0, (240, 150, 70))
        if not f.m_workers[1]:
            msg, col = "Стоит: нет пекарей", RED
        elif f.oven_load > 0:
            msg, col = f"Печёт партию: {int(f.oven_prog / BAKE_TIME * 100)}%", OK_GREEN
        elif f.flour > 0:
            msg, col = f"Копит муку на партию: {min(99, int(f.flour / max(1e-9, f.bake_rate() * BAKE_TIME) * 100))}%", (150, 120, 60)
        else:
            msg, col = "Ждёт муку", RED
        draw_text_fit(s, msg, 13, (r.centerx, r.y + 177), r.w - 16, col, outline=None)
        draw_text_fit(s, f"Хлеб: ${fmt(f.bread)}", 18, (r.centerx, r.y + 202), r.w - 16, (150, 95, 40), outline=None)
        self.workers_row(r, 1, r.y + 230, "Пекари")
        self.button((r.x + 14, r.y + 280, r.w - 28, 36), "Продать хлеб" + (f": ${fmt(f.bread)}" if f.bread > 0 else ""),
                    self.do_collect_bread, ORANGE, f.bread > 0, 15)
        if f.bread > 0:
            self.zone((r.x + 8, r.y + 56, r.w - 16, 84), self.do_collect_bread)
        self.upgrade_button(r, 1, r.y + 326)

    # ------------------------------------------------------------ весь экран
    def draw_mill_view(self):
        s = self.screen
        s.blit(self.mill_bg, (0, 0))
        plate = pygame.Rect(W // 2 + 70, 26, 220, 44)
        rounded(s, (240, 222, 212), plate, 8, 3)
        draw_text(s, "МЕЛЬНИЦА", 22, plate.center, BROWN, outline=None)
        self.card_mill()
        self.card_flour()
        self.card_bakery()
        for x, y, text, life, color in self.floaters:
            draw_text(s, text, 18, (x, y), color)
