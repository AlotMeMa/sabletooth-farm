# -*- coding: utf-8 -*-
"""Казино на экране (заготовка, 3.10): зал с рулеткой. Логика ставок — casino.py.

Пока открывается только в режиме разработчика (F1 → «Казино (заготовка)» или дверь «Казино» в таверне с --dev):
для всех игроков дверь по-прежнему «скоро». Всё рисуется кодом; свои картинки (необязательно):
    backgrounds/casino (1000x640, без колеса и стола), props/roulette_wheel (квадрат, ноль — сверху),
    props/roulette_ball, ui/chip_1|5|10|25.
Раскладка — в CASINO_LAYOUT (колесо слева, поле ставок справа, фишки и «Крутить!» снизу).
"""
import math

import pygame

from .config import W, H
from .art import (OUT, WHITE, GOLD, BTN_GREEN, BTN_BLUE, BTN_GREY, P, poly, rounded, draw_text, render_text,
                  blit_sprite, blit_tf, blit_light)
from .tavern_ui import draw_token
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
    chips_y=452, spin=pygame.Rect(800, 428, 186, 52), clear=pygame.Rect(696, 434, 96, 40),
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
    col = {1: (235, 235, 230), 5: (210, 60, 60), 10: (60, 110, 210), 25: (60, 160, 80)}.get(value, (200, 160, 60))
    r = 16 * k
    pygame.draw.circle(s, OUT, (P(x), P(y)), P(r) + 2)
    pygame.draw.circle(s, col, (P(x), P(y)), P(r))
    for i in range(6):                       # полоски по краю фишки
        a = i * math.pi / 3
        pygame.draw.line(s, WHITE, (P(x + math.cos(a) * r * 0.62), P(y + math.sin(a) * r * 0.62)),
                         (P(x + math.cos(a) * r * 0.95), P(y + math.sin(a) * r * 0.95)), max(2, P(3 * k)))
    pygame.draw.circle(s, WHITE, (P(x), P(y)), P(r * 0.55))
    draw_text(s, label or str(value), int(12 * k), (x, y), OUT if value == 1 else col, outline=None)


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

    def open_casino(self):
        """Казино — за дверью таверны: зал таверны готовим тоже (кнопка «В таверну» ведёт туда)."""
        self.tavern.unlocked = True
        self.open_tavern()
        self.view = "casino"
        self.modal = None

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
        else:
            self.cs_msg = (f"Выпало {result} ({name}). В этот раз не повезло", (255, 210, 190))

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

    def build_wheel_image(self):
        """Колесо без поворота (ноль сверху): обод, ячейки с числами, конус посередине."""
        R = CASINO_LAYOUT["wheel_r"]
        size = 2 * R + 8
        img = hd.Surface((size, size), pygame.SRCALPHA)
        img.fill((0, 0, 0, 0))
        c = size / 2
        pygame.draw.circle(img, OUT, (P(c), P(c)), R + 3)
        pygame.draw.circle(img, WOOD, (P(c), P(c)), R)
        pygame.draw.circle(img, WOOD_DARK, (P(c), P(c)), int(R * 0.9), 3)
        step = 2 * math.pi / len(cs.WHEEL)
        r0, r1 = R * 0.62, R * 0.86
        for i, n in enumerate(cs.WHEEL):
            a0, a1 = -math.pi / 2 + (i - 0.5) * step, -math.pi / 2 + (i + 0.5) * step
            pts = [(c + math.cos(a0) * r0, c + math.sin(a0) * r0), (c + math.cos(a0) * r1, c + math.sin(a0) * r1),
                   (c + math.cos(a1) * r1, c + math.sin(a1) * r1), (c + math.cos(a1) * r0, c + math.sin(a1) * r0)]
            poly(img, cell_color(n), pts, 1)
            am = -math.pi / 2 + i * step
            t = render_text(str(n), 12, WHITE, None)
            t = pygame.transform.rotate(t, -math.degrees(am + math.pi / 2))
            rm = R * 0.78
            img.blit(t, t.get_rect(center=(int(c + math.cos(am) * rm), int(c + math.sin(am) * rm))))
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
        if not blit_tf(s, "props/roulette_wheel", wx, wy, 1.0, angle=deg, pivot="center"):
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
        plate = pygame.Rect(W // 2 - 150, 74, 300, 50)
        rounded(s, WOOD, plate, 10, 3)
        draw_text(s, "РУЛЕТКА", 26, (plate.centerx, plate.centery - 1), GOLD)
        draw_text(s, "заготовка — только в режиме разработчика", 12, (plate.centerx, plate.bottom + 10), (255, 220, 200))
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
            x = 548 + i * 40
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
