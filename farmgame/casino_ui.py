# -*- coding: utf-8 -*-
"""Казино на экране: зал с рулеткой, крупье, призовая стойка. Логика ставок — casino.py, призы — tavern.py.

3.14: открыто для игроков — дверь в таверне открывается, когда жетонов впервые набирается 100.
Крупье при первом визите рассказывает правила (щелчок по нему — дальше). Всё рисуется кодом; свои картинки
(необязательно): backgrounds/casino (1000x640, без колеса и стола), props/roulette_wheel (квадрат, ноль — сверху,
без цифр — их рисует игра), props/roulette_ball, ui/chip_5|10|25|50, characters/croupier (по пояс, низ = край стола),
icons/prize_<id> (призы).
Раскладка — в CASINO_LAYOUT (колесо слева, поле ставок справа, фишки и «Крутить!» снизу).
"""
import math
import random

import pygame

from .config import W, H, PRIZES
from .art import (OUT, WHITE, GOLD, BTN_GREEN, BTN_BLUE, BTN_GREY, P, poly, rounded, draw_text, render_text,
                  draw_text_fit, blit_sprite, blit_tf, blit_light, has_sprite, ellipse)
from .tavern_ui import draw_token, draw_person, draw_bubble
from . import casino as cs
from . import anim
from . import hd

FELT, FELT_DARK = (40, 120, 70), (30, 92, 54)
WOOD, WOOD_DARK = (120, 70, 40), (86, 48, 28)
CS_RED, CS_BLACK, CS_GREEN = (196, 52, 48), (38, 34, 36), (40, 150, 80)
SPIN_TIME = 5.5
# 3.14.2: всё на столе — внутри зелёного сукна фона (у фона пользователя сукно x 76–933, y 239–587)
CASINO_LAYOUT = dict(
    felt=pygame.Rect(76, 239, 857, 348),
    wheel=(236, 413), wheel_r=148,
    ring=(0.46, 0.86),                             # кольцо ячеек: доли радиуса колеса (внутр., внешн.)
    board=pygame.Rect(410, 252, 513, 178),        # зеро + 12x3 чисел + дюжины + ставки 1 к 1
    chips_y=466, chips_x=510, spin=pygame.Rect(748, 442, 175, 48), clear=pygame.Rect(652, 447, 88, 38),
    msg=(668, 532), history=(520, 566),
)
WHEEL_SPRITE_R = 168      # радиус колеса на картинке props/roulette_wheel после подгонки (холст 338)


def cell_color(n):
    return {"green": CS_GREEN, "red": CS_RED, "black": CS_BLACK}[cs.color_of(n)]


def board_cells():
    """[(ключ ставки, Rect, подпись, цвет)] — поле ставок по раскладке."""
    b = CASINO_LAYOUT["board"]
    zw, cw, ch = 33, 40, 38
    cells = [(("num", 0), pygame.Rect(b.x, b.y, zw, ch * 3), "0", CS_GREEN)]
    for c in range(12):
        for r in range(3):
            n = 3 * c + (3 - r)
            cells.append((("num", n), pygame.Rect(b.x + zw + c * cw, b.y + r * ch, cw, ch), str(n), cell_color(n)))
    y = b.y + ch * 3 + 4
    for d in range(3):
        cells.append((("dozen", d + 1), pygame.Rect(b.x + zw + d * 160, y, 160, 28), cs.bet_name(("dozen", d + 1)), FELT))
    y += 32
    for i, kind in enumerate(("low", "even", "red", "black", "odd", "high")):
        col = CS_RED if kind == "red" else CS_BLACK if kind == "black" else FELT
        cells.append(((kind,), pygame.Rect(b.x + zw + i * 80, y, 80, 28), cs.BET_NAMES[kind], col))
    return cells


def draw_chip(s, x, y, value, k=1.0, label=None):
    col = {5: (210, 60, 60), 10: (60, 110, 210), 25: (60, 160, 80), 50: (40, 40, 44)}.get(value, (200, 160, 60))
    if blit_sprite(s, f"ui/chip_{value}", x, y, 0.5 * k, "center"):
        # своя фишка — с пустой серединой: число пишет игра (цвета фишки, как у фишки кодом)
        draw_text(s, label or str(value), max(8, int(13 * k)), (x, y + 1), col, outline=None)
        return
    r = 16 * k
    pygame.draw.circle(s, OUT, (P(x), P(y)), P(r) + 2)
    pygame.draw.circle(s, col, (P(x), P(y)), P(r))
    for i in range(6):                       # полоски по краю фишки
        a = i * math.pi / 3
        pygame.draw.line(s, WHITE, (P(x + math.cos(a) * r * 0.62), P(y + math.sin(a) * r * 0.62)),
                         (P(x + math.cos(a) * r * 0.95), P(y + math.sin(a) * r * 0.95)), max(2, P(3 * k)))
    pygame.draw.circle(s, WHITE, (P(x), P(y)), P(r * 0.55))
    draw_text(s, label or str(value), int(12 * k), (x, y), col, outline=None)


def chip_for(amount):
    """Какой фишкой показать сумму ставки (самая крупная, что в неё влезает)."""
    for v in reversed(cs.CHIPS):
        if amount >= v:
            return v
    return cs.CHIPS[0]


class CasinoUI:
    def init_casino(self):
        self.roulette = cs.Roulette()
        self.cs_chip = cs.CHIPS[1]
        self.cs_angle = 0.0             # поворот колеса
        self.cs_spin = None             # dict(t, result, rel0) — пока крутится
        self.cs_ball = None             # (угол, радиус) шарика
        self.cs_msg = ("Делай ставки и жми «Крутить!»", (255, 240, 200))
        self.cs_wheel_img = None
        self.cs_bg = None
        self.cs_say = None              # [текст, секунд осталось] — облачко крупье
        self.cs_intro = 0               # номер подсказки правил (пока крупье рассказывает)
        self.prize_tab = "trophy"

    def open_casino(self):
        """Казино — за дверью таверны: зал таверны готовим тоже (кнопка «В таверну» ведёт туда)."""
        self.tavern.unlocked = True
        self.open_tavern()
        self.view = "casino"
        self.modal = None
        if not self.tavern.casino_intro:
            self.cs_intro = 0
            self.cs_say = [CROUPIER_INTRO[0], 1e9]
        else:
            self.cs_say = [random.choice(CROUPIER_HELLO), 3.5]

    # ------------------------------------------------------------ крупье
    def poke_croupier(self):
        """Щелчок по крупье: следующая подсказка правил, а после них — просто реплика."""
        if not self.tavern.casino_intro:
            self.cs_intro += 1
            if self.cs_intro >= len(CROUPIER_INTRO):
                self.tavern.casino_intro = True
                self.cs_say = ["Делайте ваши ставки!", 3.0]
                self.save()
            else:
                self.cs_say = [CROUPIER_INTRO[self.cs_intro], 1e9]
            return
        self.cs_say = [random.choice(CROUPIER_LINES), 4.0]

    def cs_rules(self):
        self.tavern.casino_intro = False
        self.cs_intro = 0
        self.cs_say = [CROUPIER_INTRO[0], 1e9]

    # ------------------------------------------------------------ ход игры
    def cs_place(self, key):
        if self.cs_spin:
            return
        ok, why = self.roulette.place(self.tavern, key, self.cs_chip)
        if ok:
            self.sfx.play("buy")
        else:
            self.toast(why, 2)

    def cs_clear(self):
        if self.cs_spin or not self.roulette.bets:
            return
        self.roulette.clear(self.tavern)
        self.cs_msg = ("Ставки убраны — жетоны вернулись", (255, 240, 200))

    def cs_start(self):
        if self.cs_spin or not self.roulette.bets:
            return
        result = self.roulette.spin()
        idx = cs.WHEEL.index(result)
        self.cs_spin = dict(t=0.0, result=result, idx=idx)
        self.cs_msg = ("Ставок больше нет!", (255, 240, 200))
        self.sfx.play("hover")

    def casino_tick(self, dt):
        if self.cs_say and self.cs_say[1] < 1e8:
            self.cs_say[1] -= min(dt, 0.25)
            if self.cs_say[1] <= 0:
                self.cs_say = None
        if self.view != "casino":            # ушли из казино: спин досчитывается сразу, несыгранные ставки — назад
            if self.cs_spin:
                self.cs_finish()
            elif self.roulette.bets:
                self.roulette.clear(self.tavern)
            return
        dt = min(dt, 0.05)
        sp = self.cs_spin
        if sp is None:
            self.cs_angle += 0.25 * dt
            return
        sp["t"] += dt
        u = min(1.0, sp["t"] / SPIN_TIME)
        self.cs_angle += (0.25 + 3.2 * (1 - u) ** 2) * dt
        step = 2 * math.pi / len(cs.WHEEL)
        rel_end = sp["idx"] * step
        rel = rel_end - 2 * math.pi * 6 * (1 - anim.ease_out_cubic(u))      # шарик бежит против колеса
        r = CASINO_LAYOUT["wheel_r"]
        drop = max(0.0, (u - 0.7) / 0.3)
        r0, r1 = CASINO_LAYOUT["ring"]
        rest = (r0 + r1) / 2 - 0.04                # шарик ложится в ячейку, ближе к внутреннему краю
        radius = r * (0.93 - (0.93 - rest) * anim.ease_out_cubic(drop)) + 3 * math.sin(sp["t"] * 30) * drop * (1 - drop)
        self.cs_ball = (rel, radius)
        if u >= 1.0:
            self.cs_finish()

    def cs_finish(self):
        result = self.cs_spin["result"]
        self.cs_spin = None
        won, staked = self.roulette.settle(self.tavern, result)
        name = {"green": "зеро", "red": "красное", "black": "чёрное"}[cs.color_of(result)]
        if won > 0:
            self.cs_msg = (f"Выпало {result} ({name})! Выигрыш: {won} жет.", GOLD)
            self.sfx.play("fanfare")
            wx, wy = CASINO_LAYOUT["wheel"]
            self.fx.sparks(wx, wy, n=16, up=80)
            self.fx.ring(wx, wy, r0=30, r1=200, life=0.7)
            if self.tavern.casino_intro:
                self.cs_say = [("Джекпот! Вот это да!" if won >= 36 * 5 and won >= staked * 10
                                else random.choice(CROUPIER_WIN)), 3.5]
        else:
            self.cs_msg = (f"Выпало {result} ({name}). В этот раз не повезло", (255, 210, 190))
            if self.tavern.casino_intro and random.random() < 0.4:
                self.cs_say = [random.choice(CROUPIER_LOSE), 3.0]

    # ------------------------------------------------------------ рисование
    def build_casino_background(self):
        bg = hd.Surface((W, H))
        if blit_sprite(bg, "backgrounds/casino", 0, 0, 1, "topleft"):
            return bg
        bg.fill((92, 26, 36))
        for x in range(0, W, 50):                # обои в полоску
            pygame.draw.rect(bg, (104, 32, 42), (x, 0, 25, 150))
        pygame.draw.rect(bg, WOOD_DARK, (0, 140, W, 14))
        pygame.draw.rect(bg, GOLD, (0, 140, W, 3))
        felt = CASINO_LAYOUT["felt"]
        rounded(bg, WOOD, felt.inflate(76, 80), 40, 4)              # стол (сукно — там же, где у картинки фона)
        rounded(bg, FELT, felt, 26, 3)
        for i in range(3):                                          # лампы над столом
            x = 220 + i * 280
            pygame.draw.line(bg, OUT, (x, 0), (x, 46), 3)
            poly(bg, (60, 90, 60), [(x - 40, 70), (x + 40, 70), (x + 22, 46), (x - 22, 46)], 3)
        return bg

    def build_wheel_image(self, numbers_only=False):
        """Колесо без поворота (ноль сверху): обод, ячейки с числами, конус посередине.
        numbers_only — только кольцо ячеек с цифрами на прозрачном: кладётся поверх своей картинки колеса
        (у картинки из нейросети ячеек не ровно 37 и цвета не по порядку — кольцо игры их закрывает)."""
        R = CASINO_LAYOUT["wheel_r"]
        size = 2 * R + 8
        img = hd.Surface((size, size), pygame.SRCALPHA)
        img.fill((0, 0, 0, 0))
        c = size / 2
        if not numbers_only:
            pygame.draw.circle(img, OUT, (P(c), P(c)), R + 3)
            pygame.draw.circle(img, WOOD, (P(c), P(c)), R)
            pygame.draw.circle(img, WOOD_DARK, (P(c), P(c)), int(R * 0.9), 3)
        step = 2 * math.pi / len(cs.WHEEL)
        r0, r1 = R * CASINO_LAYOUT["ring"][0], R * CASINO_LAYOUT["ring"][1]
        for i, n in enumerate(cs.WHEEL):
            a0, a1 = -math.pi / 2 + (i - 0.5) * step, -math.pi / 2 + (i + 0.5) * step
            pts = [(c + math.cos(a0) * r0, c + math.sin(a0) * r0), (c + math.cos(a0) * r1, c + math.sin(a0) * r1),
                   (c + math.cos(a1) * r1, c + math.sin(a1) * r1), (c + math.cos(a1) * r0, c + math.sin(a1) * r0)]
            poly(img, cell_color(n), pts, 1)
            if numbers_only:                                 # золотая перегородка между ячейками
                pygame.draw.line(img, (220, 180, 90), (P(pts[0][0]), P(pts[0][1])), (P(pts[1][0]), P(pts[1][1])), 2)
            am = -math.pi / 2 + i * step
            t = render_text(str(n), 10, WHITE, None)
            t = pygame.transform.rotate(t, -math.degrees(am + math.pi / 2))
            rm = r0 + (r1 - r0) * 0.74
            img.blit(t, t.get_rect(center=(int(c + math.cos(am) * rm), int(c + math.sin(am) * rm))))
        if numbers_only:                                     # золотые края кольца
            pygame.draw.circle(img, OUT, (P(c), P(c)), int(r1) + 3, 4)
            pygame.draw.circle(img, (220, 180, 90), (P(c), P(c)), int(r1) + 2, 2)
            pygame.draw.circle(img, OUT, (P(c), P(c)), int(r0) + 1, 3)
            pygame.draw.circle(img, (220, 180, 90), (P(c), P(c)), int(r0), 1)
            return img
        pygame.draw.circle(img, OUT, (P(c), P(c)), int(r0) + 1, 2)
        pygame.draw.circle(img, (150, 95, 55), (P(c), P(c)), int(r0 - 2))
        pygame.draw.circle(img, (176, 120, 70), (P(c), P(c)), int(R * 0.4))
        for k in range(4):                       # крестовина
            a = k * math.pi / 2
            pygame.draw.line(img, GOLD, (P(c), P(c)), (P(c + math.cos(a) * R * 0.34), P(c + math.sin(a) * R * 0.34)), 5)
        pygame.draw.circle(img, OUT, (P(c), P(c)), 11)
        pygame.draw.circle(img, GOLD, (P(c), P(c)), 9)
        return img

    def cs_draw_wheel(self, s):
        wx, wy = CASINO_LAYOUT["wheel"]
        R = CASINO_LAYOUT["wheel_r"]
        deg = -math.degrees(self.cs_angle)
        blit_light(s, wx, wy, 2 * R + 120, (255, 236, 170), 70)
        if blit_tf(s, "props/roulette_wheel", wx, wy, (R + 3) / WHEEL_SPRITE_R, angle=deg, pivot="center"):
            # своё колесо — без цифр: цифры рисует игра поверх и крутит вместе с колесом
            if getattr(self, "cs_numbers_img", None) is None:
                self.cs_numbers_img = self.build_wheel_image(numbers_only=True)
            rot = pygame.transform.rotate(self.cs_numbers_img, deg)
            s.blit(rot, rot.get_rect(center=(wx, wy)))
        else:
            if self.cs_wheel_img is None:
                self.cs_wheel_img = self.build_wheel_image()
            rot = pygame.transform.rotate(self.cs_wheel_img, deg)
            s.blit(rot, rot.get_rect(center=(wx, wy)))
        # шарик
        if self.cs_spin or self.cs_ball:
            rel, rad = self.cs_ball if self.cs_ball else (0.0, R * (sum(CASINO_LAYOUT["ring"]) / 2 - 0.04))
            a = -math.pi / 2 + self.cs_angle + rel
            bx, by = wx + math.cos(a) * rad, wy + math.sin(a) * rad
            if not blit_sprite(s, "props/roulette_ball", bx, by, 0.4, "center"):
                pygame.draw.circle(s, OUT, (P(bx), P(by)), 7)
                pygame.draw.circle(s, (250, 250, 245), (P(bx), P(by)), 6)
                pygame.draw.circle(s, WHITE, (P(bx - 2), P(by - 2)), 2)

    def draw_casino_view(self):
        s = self.screen
        if self.cs_bg is None:
            self.cs_bg = self.build_casino_background()
        s.blit(self.cs_bg, (0, 0))
        plate = pygame.Rect(196, 120, 230, 48)               # 3.14.2: слева — посередине стоит крупье
        rounded(s, WOOD, plate, 10, 3)
        draw_text(s, "РУЛЕТКА", 24, (plate.centerx, plate.centery - 1), GOLD)
        self.cs_draw_croupier(s)
        self.cs_draw_wheel(s)
        busy = self.cs_spin is not None
        # поле ставок
        for key, r, label, col in board_cells():
            rounded(s, col, r, 4, 2, (230, 210, 150))
            draw_text(s, label, 15 if key[0] == "num" else 13, r.center)
            if not busy:
                self.zone_btn(r, lambda key=key: self.cs_place(key), 4)
            amt = self.roulette.bets.get(key)
            if amt:
                draw_chip(s, r.right - 9, r.y + 9, chip_for(amt), 0.62, str(amt))   # в углу — число видно
            if self.cs_spin is None and self.roulette.history and key == ("num", self.roulette.history[0]):
                pygame.draw.rect(s, GOLD, r.inflate(4, 4), 3, border_radius=5)
        # фишки
        y, x0 = CASINO_LAYOUT["chips_y"], CASINO_LAYOUT["chips_x"]
        draw_text(s, "Фишка:", 16, (x0 - 100, y), WHITE, anchor="midleft")
        for i, v in enumerate(cs.CHIPS):
            x = x0 + i * 38
            rect = pygame.Rect(x - 19, y - 19, 38, 38)
            if v == self.cs_chip:
                blit_light(s, x, y, 64, (255, 230, 140), 200)
            draw_chip(s, x, y, v, 1.05 if v == self.cs_chip else 0.9)
            self.zone_btn(rect, lambda v=v: setattr(self, "cs_chip", v), 19)
        total = self.roulette.total()
        self.button(CASINO_LAYOUT["clear"], "Убрать", self.cs_clear, BTN_BLUE, total > 0 and not busy, 16)
        self.button(CASINO_LAYOUT["spin"], "Крутить!" if not busy else "Крутится...", self.cs_start, BTN_GREEN,
                    total > 0 and not busy, 20)
        draw_text(s, f"На столе: {total}", 15, (CASINO_LAYOUT["spin"].centerx, CASINO_LAYOUT["spin"].bottom + 14),
                  WHITE)
        # сообщение и история
        text, col = self.cs_msg
        mx, my = CASINO_LAYOUT["msg"]
        draw_text_fit(s, text, 17, (mx, my), CASINO_LAYOUT["felt"].right - 420 - 10, col)
        hx, hy = CASINO_LAYOUT["history"]
        for i, n in enumerate(self.roulette.history[:10]):
            x = hx + i * 30
            pygame.draw.circle(s, OUT, (x, hy), 13)
            pygame.draw.circle(s, cell_color(n), (x, hy), 11)
            draw_text(s, str(n), 11, (x, hy))
        if self.roulette.history:
            draw_text(s, "последние:", 13, (hx - 20, hy), (220, 230, 210), anchor="midright", outline=None)
        for x, yy, t, life, color in self.floaters:
            draw_text(s, t, 18, (x, yy), color)
        # жетоны, призы, облачко крупье
        pb = pygame.Rect(14, 112, 170, 46)                  # 3.14.2: над столом, под «В таверну»
        self.button(pb, "Призы", lambda: self.open_modal("prizes"), (245, 175, 50), True, 19)
        draw_token(s, pb.x + 28, pb.centery, 0.7)
        self.tip(pb, "Призовая стойка: трофеи и украшения за жетоны")
        if self.cs_say:
            hint = None if self.tavern.casino_intro else \
                f"щёлкни по крупье — дальше ({self.cs_intro + 1}/{len(CROUPIER_INTRO)})"
            draw_side_bubble(s, CROUPIER["x"] + 62, CROUPIER["waist"] - 150, self.cs_say[0], hint)

    def cs_draw_croupier(self, s):
        """Крупье по пояс за столом (справа от надписи): своя картинка characters/croupier или кодом."""
        c, tt = CROUPIER, self.t_real
        x, wy = c["x"], c["waist"]
        sway = math.sin(tt * 1.3) * 1.2
        if not blit_tf(s, "characters/croupier", x, wy + 2, c["sprite_scale"], angle=sway * 0.8):
            look = dict(top=(40, 40, 46), apron=False, hair=(40, 30, 28), style="short", mustache=True,
                        skin=(240, 200, 168))
            talking = self.cs_say is not None and int(tt * 6) % 2 == 0
            spin = self.cs_spin is not None
            hands = draw_person(s, x, wy, c["k"], look, tt, talking, upper=True,
                                arms=(0.5, -0.9 if spin else 0.45 + 0.1 * math.sin(tt * 2)))
            for hx, hy in hands:                      # белые манжеты
                pygame.draw.circle(s, WHITE, (int(hx), int(hy) - 4), 4)
            # бабочка
            bx, by = x, wy - 70 * c["k"]
            poly(s, (190, 40, 50), [(bx, by), (bx - 9, by - 5), (bx - 9, by + 5)], 2)
            poly(s, (190, 40, 50), [(bx, by), (bx + 9, by - 5), (bx + 9, by + 5)], 2)
        zone = pygame.Rect(x - 75, wy - 185, 150, 185)
        self.zone_btn(zone, self.poke_croupier, 12)
        self.tip(zone, "Крупье: щёлкни, чтобы поговорить" if self.tavern.casino_intro else "Крупье рассказывает правила")
        q = pygame.Rect(x + 92, wy - 46, 32, 32)
        self.button(q, "?", self.cs_rules, BTN_BLUE, True, 16)
        self.tip(q, "Правила рулетки ещё раз")

    # ------------------------------------------------------------ призовая стойка
    def draw_prizes(self):
        s, t = self.screen, self.tavern
        r = self.panel(640, 480, "ПРИЗОВАЯ СТОЙКА")
        draw_text(s, f"У тебя жетонов: {t.tokens}", 15, (r.centerx, r.y + 56), (90, 70, 60), outline=None)
        tabs = (("trophy", "Трофеи"), ("cosmetic", "Украшения"))
        tw = (r.w - 60 - 10) // 2
        for i, (key, title) in enumerate(tabs):
            on = self.prize_tab == key
            self.button((r.x + 30 + i * (tw + 10), r.y + 74, tw, 38), title, lambda k=key: setattr(self, "prize_tab", k),
                        (245, 175, 50) if on else BTN_BLUE, True, 17)
        if self.prize_tab not in ("trophy", "cosmetic"):
            self.prize_tab = "trophy"
        items = sorted((p for p in PRIZES if p["kind"] == self.prize_tab), key=lambda p: p["cost"])
        per = 4
        pages = max(1, (len(items) + per - 1) // per)
        self.prize_page = min(getattr(self, "prize_page", 0), pages - 1) if self.prize_tab == getattr(
            self, "prize_page_tab", None) else 0
        self.prize_page_tab = self.prize_tab
        for n, p in enumerate(items[self.prize_page * per:(self.prize_page + 1) * per]):
            card = pygame.Rect(r.x + 30, r.y + 124 + n * 74, r.w - 60, 66)
            rounded(s, (238, 222, 192), card, 10, 2, skin="card")
            draw_prize_icon(s, p, card.x + 38, card.centery)
            draw_text_fit(s, p["name"], 17, (card.x + 76, card.y + 22), card.w - 270, (90, 70, 60), anchor="midleft",
                          outline=None)
            draw_text_fit(s, p["text"], 13, (card.x + 76, card.y + 45), card.w - 270, (60, 130, 50), anchor="midleft",
                          outline=None)
            bt = pygame.Rect(card.right - 170, card.y + 12, 156, 42)
            state = t.prize_state(p)
            if state == "owned" and p["kind"] == "cosmetic":
                on = t.prize_on(p["id"])
                self.button(bt, "Включено" if on else "Выключено", lambda pid=p["id"]: self.toggle_prize(pid),
                            BTN_GREEN if on else BTN_GREY, True, 16)
            elif state == "owned":
                skin_max(s, bt, "В таверне")
            else:
                can = t.tokens >= p["cost"]
                self.button(bt, f"{p['cost']}", lambda pid=p["id"]: self.buy_prize(pid), BTN_GREEN, can, 18)
                draw_token(s, bt.x + 40, bt.centery, 0.75)
                if not can:
                    self.tip(bt, f"Нужно жетонов: {p['cost']}")
        owned = sum(1 for p in items if t.prizes.get(p["id"]))
        draw_text(s, f"Собрано: {owned} из {len(items)}", 14, (r.x + 40, r.bottom - 46), (140, 110, 95),
                  anchor="midleft", outline=None)
        if pages > 1:
            draw_text(s, f"{self.prize_page + 1} / {pages}", 15, (r.centerx, r.bottom - 46), (90, 70, 60), outline=None)
            if self.prize_page > 0:
                self.button((r.centerx - 92, r.bottom - 66, 40, 36), "<",
                            lambda: setattr(self, "prize_page", self.prize_page - 1), BTN_BLUE)
            if self.prize_page < pages - 1:
                self.button((r.centerx + 52, r.bottom - 66, 40, 36), ">",
                            lambda: setattr(self, "prize_page", self.prize_page + 1), BTN_BLUE)

    def buy_prize(self, pid):
        ok, why = self.tavern.buy_prize(self.farm, pid)
        if not ok:
            self.toast(why, 2.5)
            return
        p = next(p for p in PRIZES if p["id"] == pid)
        self.sfx.play("fanfare" if p["kind"] == "trophy" else "buy")
        self.toast(f"Приз: «{p['name']}»!" + (f" {p['text'].capitalize()}" if p["kind"] != "trophy" else ""), 3.5)
        cx = self.panel_rect.centerx if getattr(self, "panel_rect", None) else W // 2
        self.fx.sparks(cx, H // 2, n=14, up=70)
        self.save()

    def toggle_prize(self, pid):
        if self.tavern.toggle_prize(pid):
            self.sfx.play("hover")
            self.save()



# ----------------------------------------------------------------------
#                      крупье и призы (3.14)
# ----------------------------------------------------------------------
CROUPIER = dict(x=520, waist=232, k=2.1, sprite_scale=1.3)   # 3.14.2: посередине над столом, крупнее
CROUPIER_INTRO = [      # 3.15.1: крупье со всеми на «вы» (было вперемешку), «Призы» — слева вверху (кнопку переносили)
    "Добро пожаловать в игорный зал! Я крупье и расскажу, как играть в рулетку.",
    "Выберите фишку внизу и щёлкните по полю: на число, цвет, чёт или нечет, половину или дюжину.",
    "Угадали число — выигрыш 35 к 1, ставка возвращается. Цвет, чёт или половина — 1 к 1, дюжина — 2 к 1.",
    "Зелёное зеро — счастье заведения: на нём проигрывают все ставки, кроме ставки на сам ноль.",
    "Выигрыш меняйте на призы: кнопка «Призы» слева вверху. Трофеи украсят таверну. Удачи!",
]
CROUPIER_HELLO = ["Рад видеть вас снова! Ставки принимаются.", "Колесо ждёт, господин фермер.", "Чувствую, сегодня ваш день!"]
CROUPIER_LINES = ["Ставок больше нет — шучу, ставьте!", "Зеро любит смелых.", "Красное или чёрное? Решать вам.",
                  "Один фермер собрал все четыре трофея. Говорят, до сих пор всем ими хвастается.",
                  "Призы на стойке не кусаются.", "Колесо честное, клянусь своей бабочкой."]
CROUPIER_WIN = ["Поздравляю!", "Удача на вашей стороне!", "Браво! Жетоны ваши."]
CROUPIER_LOSE = ["В следующий раз повезёт.", "Колесо капризное сегодня.", "Не грустите — ещё спин?"]


def draw_side_bubble(s, x, y, text, hint=None, size=14, maxw=230):
    """Облачко справа от говорящего: (x, y) — кончик хвостика слева. Не закрывает самого крупье."""
    from .tavern_ui import wrap
    lines = wrap(text, size, maxw, 5)
    imgs = [render_text(line, size, (90, 70, 60), None) for line in lines]
    himg = render_text(hint, 11, (150, 120, 100), None) if hint else None
    w = max([i.get_width() for i in imgs] + ([himg.get_width()] if himg else [])) + 24
    h = len(imgs) * (size + 4) + 16 + (16 if himg else 0)
    bx = min(W - w - 8, x + 12)
    by = max(70, min(y - h // 2, H - h - 8))
    ty = max(by + 12, min(y, by + h - 12))
    from .tavern_ui import draw_bubble_skin
    if not draw_bubble_skin(s, (bx, by, w, h), (x, ty), "left"):   # 3.16: облачко-картинка ui/bubble
        rounded(s, WHITE, (bx, by, w, h), 12, 2, skin=None)
        poly(s, WHITE, [(bx + 2, ty - 8), (bx + 2, ty + 8), (x, ty)], 2)
        pygame.draw.polygon(s, WHITE, [(bx + 3, ty - 6), (bx + 3, ty + 6), (x + 3, ty)])
    for n, img in enumerate(imgs):
        s.blit(img, img.get_rect(midleft=(bx + 12, by + 8 + (size + 4) * n + (size + 4) // 2)))
    if himg:
        s.blit(himg, himg.get_rect(midleft=(bx + 12, by + h - 14)))


def skin_max(s, rect, label):
    """Неактивная «золотая» дощечка с подписью (уже куплено, действует)."""
    from .skin import draw_max
    draw_max(s, rect, 15, label)


def draw_prize_icon(s, prize, x, y, k=1.0):
    """Значок приза: картинка icons/prize_<id> или кодом."""
    if blit_sprite(s, f"icons/prize_{prize['id']}", x, y, k, "center"):
        return
    pid = prize["id"]
    if pid == "horseshoe":
        rect = pygame.Rect(0, 0, int(34 * k), int(36 * k))
        rect.center = (x, y)
        pygame.draw.arc(s, OUT, rect.inflate(4, 4), 0.0, math.pi, max(2, int(10 * k)))
        pygame.draw.arc(s, (205, 127, 50), rect, 0.0, math.pi, max(2, int(7 * k)))
        for sx in (rect.x + 4 * k, rect.right - 4 * k):
            pygame.draw.line(s, OUT, (int(sx), y), (int(sx), int(y + 14 * k)), max(3, int(9 * k)))
            pygame.draw.line(s, (205, 127, 50), (int(sx), y), (int(sx), int(y + 14 * k)), max(2, int(6 * k)))
    elif pid == "cup":
        poly(s, (200, 205, 215), [(x - 15 * k, y - 16 * k), (x + 15 * k, y - 16 * k), (x + 8 * k, y + 4 * k),
                                  (x - 8 * k, y + 4 * k)], 2)
        rounded(s, (200, 205, 215), (int(x - 3 * k), int(y + 3 * k), int(6 * k), int(9 * k)), 1, 2, skin=None)
        rounded(s, (170, 175, 190), (int(x - 11 * k), int(y + 11 * k), int(22 * k), int(6 * k)), 2, 2, skin=None)
    elif pid == "statue":
        rounded(s, (200, 150, 40), (int(x - 12 * k), int(y + 10 * k), int(24 * k), int(8 * k)), 2, 2, skin=None)
        ellipse(s, (245, 200, 60), x, y + 1 * k, 16 * k, 20 * k)
        pygame.draw.circle(s, OUT, (int(x), int(y - 12 * k)), int(8 * k) + 2)
        pygame.draw.circle(s, (250, 210, 70), (int(x), int(y - 12 * k)), int(8 * k))
        ellipse(s, (235, 185, 50), x, y - 18 * k, 22 * k, 6 * k)
    elif pid == "crystal":
        for i in range(5):
            a = -0.5 + i * 0.25
            ex, ey = x + math.sin(a) * 6 * k, y - 4 * k - i * 5 * k
            poly(s, (190, 235, 250), [(ex - 4 * k, ey), (ex, ey - 7 * k), (ex + 4 * k, ey), (ex, ey + 6 * k)], 2)
        pygame.draw.line(s, (150, 210, 235), (x, int(y + 16 * k)), (x, int(y - 4 * k)), max(2, int(3 * k)))
    elif pid == "lucky_coin":
        pygame.draw.circle(s, OUT, (x, y), int(15 * k) + 2)
        pygame.draw.circle(s, GOLD, (x, y), int(15 * k))
        pygame.draw.circle(s, (255, 230, 120), (x, y), int(10 * k))
        draw_text(s, "7", max(9, int(16 * k)), (x, y), (190, 120, 10), outline=None)
    elif pid == "clover":
        for a in range(4):
            ang = a * math.pi / 2 + math.pi / 4
            cx, cy = x + math.cos(ang) * 7 * k, y - 2 * k + math.sin(ang) * 7 * k
            pygame.draw.circle(s, OUT, (int(cx), int(cy)), int(8 * k) + 1)
            pygame.draw.circle(s, (90, 180, 80), (int(cx), int(cy)), int(8 * k))
        pygame.draw.line(s, (60, 130, 50), (x, y), (int(x + 5 * k), int(y + 15 * k)), max(2, int(3 * k)))
    elif pid == "gold_notes":
        from .tavern_ui import draw_note
        draw_note(s, x - 8, y + 8, color=(255, 214, 90))
        blit_light(s, x + 8, y - 10, 20, (255, 236, 150), 200, 0.0)
    elif pid == "gold_trail":
        for i in range(5):
            pygame.draw.circle(s, (255, 212, 80), (int(x - 14 * k + i * 6 * k), int(y + 8 * k - i * 4 * k)),
                               max(1, int((1 + i) * k)))
        poly(s, WHITE, [(x + 10 * k, y - 14 * k), (x + 10 * k, y + 4 * k), (x + 15 * k, y - 1 * k), (x + 20 * k, y - 1 * k)], 2)
    elif pid == "bard_girl":
        from .tavern_ui import draw_person
        look = dict(top=(230, 225, 205), dress=(190, 90, 80), hair=(200, 140, 70), style="long", girl=True)
        draw_person(s, x, y + 16 * k, 0.42 * k, look)
    elif pid in ("flowers", "rug", "kettle", "cat"):        # 3.19: украшения у камина
        from .fireside_art import draw_cat, draw_kettle, draw_flowers, draw_rug
        if pid == "flowers":
            draw_flowers(s, x, y + 16 * k, 0.62 * k, 0.0)
        elif pid == "rug":
            draw_rug(s, x, y, 0.13 * k, 0.62)
        elif pid == "kettle":
            draw_kettle(s, x, y + 14 * k, 0.5 * k, 0.0)
        else:
            draw_cat(s, x - 5 * k, y + 10 * k, 0.62 * k, 0.0)
    elif pid == "garland":
        pygame.draw.arc(s, OUT, pygame.Rect(x - 20 * k, y - 14 * k, 40 * k, 20 * k), math.pi, 2 * math.pi, 2)
        for i, col in enumerate(((255, 90, 80), (255, 210, 80), (110, 220, 120), (110, 170, 255))):
            u = (i + 0.5) / 4
            bx = x - 18 * k + 36 * k * u
            by = y - 4 * k + 10 * k * 4 * u * (1 - u)
            pygame.draw.circle(s, OUT, (int(bx), int(by + 4 * k)), int(5 * k) + 1)
            pygame.draw.circle(s, col, (int(bx), int(by + 4 * k)), int(5 * k))
