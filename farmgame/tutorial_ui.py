# -*- coding: utf-8 -*-
"""Обучение на экране (3.9): бармен в окошке внизу, стрелка и мягкий свет над тем, куда нажать.

Подмешивается в App. Логика шагов — tutorial.py. Обучение только на первой ферме и только на поле;
пока открыто окно (магазин и т. п.), окошко бармена прячется. «Пропустить» — в любой момент,
«Обучение заново» — в «Настройках» → «Игра».
"""
import math

import pygame

from .config import W, H, fmt, CROPS
from .art import (OUT, WHITE, GOLD, BTN_GREEN, BTN_BLUE, P, poly, rounded, draw_text, render_text, blit_tf,
                  blit_light, crop_center)
from .tavern_ui import draw_person, draw_mug, wrap
from .tutorial import Tutorial, STEPS
from . import hd

BROWN, SOFT = (90, 70, 60), (140, 110, 95)
CARD = (238, 222, 192)
BOX = pygame.Rect(404, 494, 584, 136)
SHOP_BTN = pygame.Rect(16, 560, 62, 56)
UPGRADE_BTN = pygame.Rect(88, 560, 62, 56)
TYPE_SPEED = 55          # букв в секунду: текст «печатается», клик по окошку — показать сразу
BARMAN_LOOK = dict(top=(200, 210, 225), apron=True, hair=(70, 50, 40), style="bald", mustache=True)


class TutorialUI:
    def init_tutorial(self):
        self.tut = Tutorial()           # новая игра — учим; из сохранения — см. apply_save
        self.tut_typed = 0.0            # сколько букв уже «напечатано»
        self.tut_shown = None           # текст, который печатается

    # ------------------------------------------------------------ состояние
    def tut_visible(self):
        return (not self.tut.done and self.farm.farm_index == 0 and self.view == "field" and self.modal is None
                and not self.closing)

    def tut_tick(self, dt):
        if self.tut.done:
            return
        if self.farm.farm_index != 0:      # уже на другой ферме (переезд) — обучение не нужно
            self.tut.finish()
            return
        if self.tut_visible():
            self.tut.tick(dt)
            self.tut_typed += dt * TYPE_SPEED

    def tut_event(self, event):
        """Игрок сделал что-то, чего ждёт обучение (собрал, посадил, прокачал, открыл магазин)."""
        if self.tut.done or self.farm.farm_index != 0:
            return
        if self.tut.on(event):
            self.sfx.play("quest")
            box = self.tut_box()
            self.fx.sparks(box.x + 70, box.y + 10, n=8, up=50)
            self.tut_typed = 0.0

    def tut_next(self):
        self.tut.next()
        self.tut_typed = 0.0
        if self.tut.done:
            self.sfx.play("fanfare")
            self.save()

    def tut_skip(self):
        self.tut.finish()
        self.toast("Обучение пропущено. Вернуть его — «Настройки» → «Игра»", 3.5)
        self.save()

    def tut_restart(self):
        self.tut.restart()
        self.tut_typed = 0.0
        self.modal = None
        self.view = "field"
        if self.farm.farm_index != 0:
            self.toast("Обучение — на первой ферме. Здесь бармен ждёт тебя в таверне!", 3.5)
        self.save()

    def tut_box(self):
        """Окошко бармена: в режиме прокачки — выше, чтобы не закрывать кнопки 1X/10X/ВЕХА/MAX."""
        return BOX.move(0, -68) if self.mode == "upgrade" else BOX

    def tut_click_box(self):
        self.tut_typed = 9999.0             # показать текст целиком

    # ------------------------------------------------------------ текст и цель шага
    def tut_text_and_target(self):
        """(текст бармена, цель: Rect или (x, y) или None)."""
        f = self.farm
        sid = self.tut.current["id"]
        if sid == "hello":
            return ("Здорово, сосед! Я бармен из таверны «Хмельной колос». Покажу, как тут всё устроено, — "
                    "это быстро."), None
        if sid == "collect":
            ripe = [k for k in range(len(f.levels)) if f.levels[k] > 0 and f.stash[k] > 0]
            if ripe:
                return ("Урожай созрел — видишь монетку над грядкой? Нажми на грядку или просто проведи по ней "
                        "мышкой."), self.coin_pos(ripe[0])
            return ("Картошка растёт: полоска под грядкой. Как появится монетка — нажми на грядку или проведи "
                    "по ней мышкой."), crop_center(0)
        if sid == "plant":
            if 0 not in f.levels:
                return "Все грядки уже посажены — вот это хватка! Жми «Дальше».", None
            k = f.levels.index(0)
            cx, cy = crop_center(k)
            price = f.cost(k, 1)
            if f.money >= price:
                text = (f"Деньги есть — сажай новое! Нажми на табличку «{CROPS[k]['name']}». "
                        "Каждая новая культура приносит больше прежней.")
            else:
                text = (f"Копим на новую грядку: нужно ${fmt(price)}. Собери урожай ещё пару раз и нажми "
                        f"на табличку «{CROPS[k]['name']}».")
            return text, pygame.Rect(cx - 56, cy - 34, 112, 56)
        if sid == "upgrade":
            if self.mode != "upgrade":
                return ("Теперь прокачка. Нажми на лопату внизу — над грядками появятся кнопки улучшения."), UPGRADE_BTN
            return ("Нажми на кнопку над грядкой. Каждый уровень — больше денег, а на вехах 10, 25, 50... "
                    "грядка растёт вдвое быстрее. Лопата ещё раз — назад к сбору."), crop_center(0)
        if sid == "shop":
            return ("Загляни в магазин. Удобрения дают доход x3, а фермеры собирают урожай сами — даже когда "
                    "тебя нет."), SHOP_BTN
        return ("Дальше сам! Копи на сарай со зверями и на переезд. А доберёшься до средневековья — заходи "
                "ко мне в таверну, налью за счёт заведения!"), None

    # ------------------------------------------------------------ рисование
    def draw_tut_pointer(self, target):
        s, tr = self.screen, self.t_real
        if isinstance(target, pygame.Rect):
            tx, ty = target.centerx, target.y
            ring = target.inflate(16, 16)
            cx, cy = target.center
        else:
            tx, ty = target[0], target[1] - 22
            ring = pygame.Rect(0, 0, 120, 64)
            ring.center = (target[0], target[1] + 6)
            cx, cy = ring.center
        pulse = 0.5 + 0.5 * math.sin(tr * 4)
        blit_light(s, cx, cy, max(ring.w, ring.h) * (1.25 + 0.15 * pulse), (255, 226, 120), 120)
        pygame.draw.ellipse(s, (255, 236, 150), ring.inflate(int(8 * pulse), int(6 * pulse)), 3)
        bob = 7 * abs(math.sin(tr * 3.2))
        ay = ty - 14 - bob
        if ay < 70:                          # у верхнего края — стрелка снизу, вверх
            by = (ring.bottom if isinstance(target, pygame.Rect) else ring.bottom) + 14 + bob
            poly(s, GOLD, [(tx - 15, by + 22), (tx + 15, by + 22), (tx, by)], 3)
            rounded(s, GOLD, (tx - 6, by + 20, 12, 18), 3, 3)
        else:
            poly(s, GOLD, [(tx - 15, ay - 22), (tx + 15, ay - 22), (tx, ay)], 3)
            rounded(s, GOLD, (tx - 6, ay - 40, 12, 20), 3, 3)

    def draw_tut_barman(self, x, y):
        """Бармен по пояс у левого края окошка: (x, y) — середина низа."""
        wave = math.sin(self.t_real * 2.2)
        if blit_tf(self.screen, "characters/barman", x, y + 4, 0.78, angle=1.5 * wave):
            return
        talking = self.tut_typed < len(self.tut_shown or "")
        hands = draw_person(self.screen, x, y - 6, 1.1, BARMAN_LOOK, self.t_real, talking, upper=True,
                            arms=(0.6, -2.2 + 0.3 * wave))
        draw_mug(self.screen, hands[0][0] + 4, hands[0][1] - 6, 0.75)

    def draw_tutorial(self):
        if not self.tut_visible():
            return
        s = self.screen
        text, target = self.tut_text_and_target()
        if text != self.tut_shown:
            if self.tut_shown is not None and self.tut_shown[:20] == text[:20]:
                self.tut_typed = max(self.tut_typed, len(text))      # тот же шаг, текст поменялся — без «печати»
            self.tut_shown = text
        if target is not None:
            self.draw_tut_pointer(target)
        box = self.tut_box()
        shadow = hd.Surface((box.w, box.h), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 0))
        pygame.draw.rect(shadow, (30, 20, 15, 70), shadow.get_rect(), border_radius=14)
        s.blit(shadow, (box.x + 4, box.y + 6))
        rounded(s, CARD, box, 14, 3, skin="card")
        self.zone(box, self.tut_click_box)
        self.draw_tut_barman(box.x + 66, box.bottom - 6)
        plate = pygame.Rect(box.x + 128, box.y - 14, 96, 26)
        rounded(s, (176, 120, 70), plate, 8, 2)
        draw_text(s, "Бармен", 15, plate.center)
        # текст печатается
        shown = text[:int(self.tut_typed)]
        lines = wrap(text, 16, box.w - 156, 4)
        y, used = box.y + 24, 0
        for line in lines:
            part = shown[used:used + len(line)]
            used += len(line) + 1
            if part:
                img = render_text(part, 16, BROWN, None)
                s.blit(img, (box.x + 136, y - img.get_height() // 2))
            y += 21
        # точки шагов
        for i in range(len(STEPS)):
            col = (240, 170, 60) if i == self.tut.step else (205, 190, 165)
            pygame.draw.circle(s, col, (box.x + 140 + i * 14, box.bottom - 18), 4)
        # кнопки
        sid = self.tut.current["id"]
        if self.tut.current["wait"] is None:
            label = {"hello": "Поехали!", "bye": "Удачи!"}.get(sid, "Дальше")
            self.button((box.right - 150, box.bottom - 48, 136, 38), label, self.tut_next, BTN_GREEN, True, 17)
        elif self.tut.can_skip_step() or (sid == "plant" and 0 not in self.farm.levels):
            self.button((box.right - 130, box.bottom - 46, 116, 34), "Дальше", self.tut_next, BTN_BLUE, True, 15)
        if sid != "bye":
            sk = pygame.Rect(box.x + 140 + len(STEPS) * 14 + 8, box.bottom - 30, 170, 24)
            draw_text(s, "пропустить обучение", 12, sk.midleft, SOFT, anchor="midleft", outline=None)
            self.zone_btn(sk, self.tut_skip, 6)
