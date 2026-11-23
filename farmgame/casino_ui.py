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
CASINO_LAYOUT = dict(
    wheel=(250, 318), wheel_r=165,
    board=pygame.Rect(470, 178, 520, 222),        # зеро + 12x3 чисел + дюжины + ставки 1 к 1
    chips_y=452, spin=pygame.Rect(800, 428, 186, 52), clear=pygame.Rect(712, 434, 82, 40),
)


def cell_color(n):
    return {"green": CS_GREEN, "red": CS_RED, "black": CS_BLACK}[cs.color_of(n)]


def board_cells():
    """[(ключ ставки, Rect, подпись, цвет)] — поле ставок по раскладке."""
    b = CASINO_LAYOUT["board"]
    zw, cw, ch = 40, 40, 48
    cells = [(("num", 0), pygame.Rect(b.x, b.y, zw, ch * 3), "0", CS_GREEN)]
    for c in range(12):
        for r in range(3):
            n = 3 * c + (3 - r)
            cells.append((("num", n), pygame.Rect(b.x + zw + c * cw, b.y + r * ch, cw, ch), str(n), cell_color(n)))
    y = b.y + ch * 3 + 4
    for d in range(3):
        cells.append((("dozen", d + 1), pygame.Rect(b.x + zw + d * 160, y, 160, 34), cs.bet_name(("dozen", d + 1)), FELT))
    y += 38
    for i, kind in enumerate(("low", "even", "red", "black", "odd", "high")):
        col = CS_RED if kind == "red" else CS_BLACK if kind == "black" else FELT
        cells.append(((kind,), pygame.Rect(b.x + zw + i * 80, y, 80, 34), cs.BET_NAMES[kind], col))
    return cells


def draw_chip(s, x, y, value, k=1.0, label=None):
    if blit_sprite(s, f"ui/chip_{value}", x, y, 0.5 * k, "center"):
        if label:
            draw_text(s, label, int(12 * k), (x, y))
        return
    col = {5: (210, 60, 60), 10: (60, 110, 210), 25: (60, 160, 80), 50: (40, 40, 44)}.get(value, (200, 160, 60))
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
        radius = r * (0.9 - 0.13 * anim.ease_out_cubic(drop)) + 3 * math.sin(sp["t"] * 30) * drop * (1 - drop)
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
        rounded(bg, WOOD, (16, 150, W - 32, 470), 40, 4)           # стол
        rounded(bg, FELT, (34, 166, W - 68, 438), 32, 3)
        for i in range(3):                                          # лампы над столом
            x = 220 + i * 280
            pygame.draw.line(bg, OUT, (x, 0), (x, 46), 3)
            poly(bg, (60, 90, 60), [(x - 40, 70), (x + 40, 70), (x + 22, 46), (x - 22, 46)], 3)
        return bg

    def build_wheel_image(self, numbers_only=False):
        """Колесо без поворота (ноль сверху): обод, ячейки с числами, конус посередине.
        numbers_only — только цифры на прозрачном (поверх своей картинки колеса без цифр)."""
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
        r0, r1 = R * 0.62, R * 0.86
        for i, n in enumerate(cs.WHEEL):
            a0, a1 = -math.pi / 2 + (i - 0.5) * step, -math.pi / 2 + (i + 0.5) * step
            pts = [(c + math.cos(a0) * r0, c + math.sin(a0) * r0), (c + math.cos(a0) * r1, c + math.sin(a0) * r1),
                   (c + math.cos(a1) * r1, c + math.sin(a1) * r1), (c + math.cos(a1) * r0, c + math.sin(a1) * r0)]
            if not numbers_only:
                poly(img, cell_color(n), pts, 1)
            am = -math.pi / 2 + i * step
            t = render_text(str(n), 12, WHITE, OUT if numbers_only else None)
            t = pygame.transform.rotate(t, -math.degrees(am + math.pi / 2))
            rm = R * 0.78
            img.blit(t, t.get_rect(center=(int(c + math.cos(am) * rm), int(c + math.sin(am) * rm))))
        if numbers_only:
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
        if blit_tf(s, "props/roulette_wheel", wx, wy, 1.0, angle=deg, pivot="center"):
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
            rel, rad = self.cs_ball if self.cs_ball else (0.0, R * 0.77)
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
        plate = pygame.Rect(W // 2 - 210, 74, 300, 50)       # 3.14: левее — справа стоит крупье
        rounded(s, WOOD, plate, 10, 3)
        draw_text(s, "РУЛЕТКА", 26, (plate.centerx, plate.centery - 1), GOLD)
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
                draw_chip(s, r.centerx + 8, r.centery - 8, chip_for(amt), 0.8, str(amt))
            if self.cs_spin is None and self.roulette.history and key == ("num", self.roulette.history[0]):
                pygame.draw.rect(s, GOLD, r.inflate(4, 4), 3, border_radius=5)
        # фишки
        y = CASINO_LAYOUT["chips_y"]
        draw_text(s, "Фишка:", 16, (476, y), WHITE, anchor="midleft")
        for i, v in enumerate(cs.CHIPS):
            x = 566 + i * 40
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
        draw_text(s, text, 18, (250, 520), col)
        for i, n in enumerate(self.roulette.history[:10]):
            x = 486 + i * 32
            pygame.draw.circle(s, OUT, (x, 530), 13)
            pygame.draw.circle(s, cell_color(n), (x, 530), 11)
            draw_text(s, str(n), 11, (x, 530))
        if self.roulette.history:
            draw_text(s, "последние", 12, (486 - 16, 552), (220, 230, 210), anchor="midleft", outline=None)
        for x, yy, t, life, color in self.floaters:
            draw_text(s, t, 18, (x, yy), color)
        # жетоны, призы, облачко крупье
        pb = pygame.Rect(198, 560, 170, 56)
        self.button(pb, "Призы", lambda: self.open_modal("prizes"), (245, 175, 50), True, 20)
        draw_token(s, pb.x + 28, pb.centery, 0.75)
        self.tip(pb, "Призовая стойка: трофеи, удача и украшения за жетоны")
        if self.cs_say:
            cx, wy = CROUPIER["x"], CROUPIER["waist"]
            draw_bubble(s, cx - 48, wy - 150 * CROUPIER["k"] / 1.6, self.cs_say[0], 14, 250)
            if not self.tavern.casino_intro:
                draw_text(s, f"щёлкни по крупье — дальше  ({self.cs_intro + 1}/{len(CROUPIER_INTRO)})", 14,
                          (250, 546), (255, 236, 190))

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
        zone = pygame.Rect(x - 70, wy - 170, 140, 170)
        self.zone_btn(zone, self.poke_croupier, 12)
        self.tip(zone, "Крупье: щёлкни, чтобы поговорить" if self.tavern.casino_intro else "Крупье рассказывает правила")
        q = pygame.Rect(x + 70, wy - 44, 32, 32)
        self.button(q, "?", self.cs_rules, BTN_BLUE, True, 16)
        self.tip(q, "Правила рулетки ещё раз")

    # ------------------------------------------------------------ призовая стойка
    def draw_prizes(self):
        s, t = self.screen, self.tavern
        r = self.panel(640, 480, "ПРИЗОВАЯ СТОЙКА")
        draw_text(s, f"У тебя жетонов: {t.tokens}", 15, (r.centerx, r.y + 56), (90, 70, 60), outline=None)
        tabs = (("trophy", "Трофеи"), ("buff", "Удача"), ("cosmetic", "Украшения"))
        tw = (r.w - 60 - 20) // 3
        for i, (key, title) in enumerate(tabs):
            on = self.prize_tab == key
            self.button((r.x + 30 + i * (tw + 10), r.y + 74, tw, 38), title, lambda k=key: setattr(self, "prize_tab", k),
                        (245, 175, 50) if on else BTN_BLUE, True, 17)
        items = [p for p in PRIZES if p["kind"] == self.prize_tab]
        for n, p in enumerate(items):
            card = pygame.Rect(r.x + 30, r.y + 124 + n * 78, r.w - 60, 70)
            rounded(s, (238, 222, 192), card, 10, 2, skin="card")
            draw_prize_icon(s, p, card.x + 38, card.centery)
            draw_text_fit(s, p["name"], 17, (card.x + 76, card.y + 22), card.w - 270, (90, 70, 60), anchor="midleft",
                          outline=None)
            sub = p["text"] + (", раз в день" if p["kind"] == "buff" else "")
            draw_text_fit(s, sub, 13, (card.x + 76, card.y + 48), card.w - 270, (60, 130, 50), anchor="midleft",
                          outline=None)
            bt = pygame.Rect(card.right - 170, card.y + 14, 156, 42)
            state = t.prize_state(p)
            if state == "owned" and p["kind"] == "cosmetic":
                on = t.prize_on(p["id"])
                self.button(bt, "Включено" if on else "Выключено", lambda pid=p["id"]: self.toggle_prize(pid),
                            BTN_GREEN if on else BTN_GREY, True, 16)
            elif state == "owned":
                skin_max(s, bt, "На полке")
            elif state == "today":
                left = self.farm.lucky_left if p["id"] == "lucky_coin" else self.farm.clover_left
                label = f"ещё {int(left // 60)}:{int(left % 60):02d}" if left > 0 else "завтра"
                skin_max(s, bt, label)
            else:
                can = t.tokens >= p["cost"]
                self.button(bt, f"{p['cost']}", lambda pid=p["id"]: self.buy_prize(pid), BTN_GREEN, can, 18)
                draw_token(s, bt.x + 40, bt.centery, 0.75)
                if not can:
                    self.tip(bt, f"Нужно жетонов: {p['cost']}")
        if self.prize_tab == "trophy":
            owned = sum(1 for p in items if t.prizes.get(p["id"]))
            draw_text(s, f"На полке трофеев: {owned} из {len(items)}", 14, (r.centerx, r.bottom - 40),
                      (140, 110, 95), outline=None)

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

    def draw_prize_pills(self, y, right=None):
        """Плашки купленных бафов казино с таймером (как у песни барда)."""
        f, s = self.farm, self.screen
        for pid, left in (("lucky_coin", f.lucky_left), ("clover", f.clover_left)):
            if left <= 0:
                continue
            p = next(p for p in PRIZES if p["id"] == pid)
            img = render_text(f"{p['name']}   {int(left // 60)}:{int(left % 60):02d}", 14, WHITE, OUT)
            r = pygame.Rect(14, y, 50 + img.get_width() + 14, 30)
            if right is not None:
                r.right = right
            rounded(s, (150, 200, 110) if pid == "clover" else (240, 196, 80), r, 15, 3)
            draw_prize_icon(s, p, r.x + 24, r.centery, 0.55)
            s.blit(img, img.get_rect(midleft=(r.x + 46, r.centery)))
            self.tip(r, f"Приз казино: {p['text']}")
            y += 36


# ----------------------------------------------------------------------
#                      крупье и призы (3.14)
# ----------------------------------------------------------------------
CROUPIER = dict(x=760, waist=180, k=1.6, sprite_scale=0.9)
CROUPIER_INTRO = [
    "Добро пожаловать в игорный зал! Я крупье. Расскажу, как играть в рулетку.",
    "Выбери фишку внизу и щёлкни по полю: на число, цвет, чёт или нечет, половину или дюжину.",
    "Угадал число — получишь ставку x36. Цвет, чёт или половина — x2, дюжина — x3.",
    "Зелёное зеро — счастье заведения: на нём проигрывают все ставки, кроме ставки на сам ноль.",
    "Выигрыш меняй на призы: стойка «Призы» внизу слева. Удачи!",
]
CROUPIER_HELLO = ["Рад видеть снова! Ставки принимаются.", "Колесо ждёт, господин фермер.", "Чувствую, сегодня ваш день!"]
CROUPIER_LINES = ["Ставок больше нет — шучу, ставьте!", "Зеро любит смелых.", "Красное или чёрное? Решать вам.",
                  "Один фермер выиграл тут золотую статуэтку. Говорят, до сих пор ею хвастается.",
                  "Призы на стойке не кусаются.", "Колесо честное, клянусь своей бабочкой."]
CROUPIER_WIN = ["Поздравляю!", "Удача на вашей стороне!", "Браво! Жетоны ваши."]
CROUPIER_LOSE = ["В следующий раз повезёт.", "Колесо капризное сегодня.", "Не грустите — ещё спин?"]


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
    elif pid == "garland":
        pygame.draw.arc(s, OUT, pygame.Rect(x - 20 * k, y - 14 * k, 40 * k, 20 * k), math.pi, 2 * math.pi, 2)
        for i, col in enumerate(((255, 90, 80), (255, 210, 80), (110, 220, 120), (110, 170, 255))):
            u = (i + 0.5) / 4
            bx = x - 18 * k + 36 * k * u
            by = y - 4 * k + 10 * k * 4 * u * (1 - u)
            pygame.draw.circle(s, OUT, (int(bx), int(by + 4 * k)), int(5 * k) + 1)
            pygame.draw.circle(s, col, (int(bx), int(by + 4 * k)), int(5 * k))
