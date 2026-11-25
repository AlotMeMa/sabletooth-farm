# -*- coding: utf-8 -*-
"""3.38: аквариум Рыбацкой деревни (кнопка «Садки» вместо сарая/мельницы).

Один общий аквариум: песок, камушки, водоросли, пузырьки. Рыбок покупаешь по одной в лавке, они плавают и растут
(больше и со светлым ободком — взрослая), щелчок по рыбке — продать. Две взрослые одного вида откладывают икру.
Под лентой «САДКИ» — полоска-таймер до хищника; хищник плавает и ест рыбок, щелчок по нему или кнопка — выловить.
Съел всех — полоска тлеет (сколько осталось, не пишем), потом он уплывает.
Своя картинка фона — backgrounds/fishery; хищники — fish/<id>; иначе всё кодом.
"""
import math
import random

import pygame

from .ui_common import *  # noqa: F401,F403
from .art_fishing import draw_swim_fish, draw_predator, draw_roe
from .tavern_art import draw_star

SWIM = pygame.Rect(50, 160, 900, 340)      # где плавают центры рыб
SAND_Y = 528                               # верх песка
BAR = pygame.Rect(W // 2 - 95, 72, 190, 16)  # таймер хищника — прямо под лентой «САДКИ»
SHOP = pygame.Rect(140, 386, 840, 172)     # лавка рыб над кнопками


def _mmss(sec):
    sec = max(0, int(math.ceil(sec)))
    return f"{sec // 60}:{sec % 60:02d}"


class FisheryUI:
    def fishery_init(self):
        self.fy_bg = None
        self.fy_shop = False

    # ------------------------------------------------------------ события логики (идут и на других экранах)
    def fishery_tick(self, dt):
        f = self.farm
        if not f.fy_events:
            return
        here = self.view == "barn" and self.farm_info()["barn"] == "fishery"
        for ev in f.fy_events:
            kind = ev[0]
            if kind == "arrive":
                p = ev[1]
                self.sfx.play("bandit")
                self.toast(f"В садки приплыл{self._fem(p)} {p['name'].lower()}! Лови, пока не съел{self._fem(p)} рыбу", 3)
            elif kind == "bite" and here:
                x, y, _d = self.fy_pred_pos()
                self.sfx.play("feed")
                self.floater(x, y - 30, f"ам! +${fmt(ev[2])}", (255, 220, 120))
            elif kind == "left":
                p = ev[1]
                self.toast(f"{p['name']} съел{self._fem(p)} всех рыбок и уплыл{self._fem(p)}…", 3)
            elif kind == "egg" and here:
                x, y = self.fy_to_screen(ev[2], ev[3])
                self.floater(x, y - 16, "икра!", (255, 190, 120))
            elif kind == "hatch":
                self.quest("fish_hatch")
                if here:
                    x, y = self.fy_to_screen(ev[2], ev[3])
                    self.floater(x, y - 16, "малёк!", (200, 240, 255))
        f.fy_events.clear()

    @staticmethod
    def _fem(p):
        return "а" if p["name"][-1] in "аь" and p["id"] != "burbot" else ""

    # ------------------------------------------------------------ геометрия
    def fy_to_screen(self, fx, fy):
        return SWIM.x + fx * SWIM.w, SWIM.y + fy * SWIM.h

    def fy_pred_pos(self):
        f = self.farm
        fx, fy, d = f.fish_swim(f.fy_pred * 131 + 7, f.fy_clock, 1.4)
        x, y = self.fy_to_screen(fx, fy)
        return x, y, d

    # ------------------------------------------------------------ действия
    def fy_buy(self, i):
        if self.farm.buy_fish(i):
            self.sfx.play("buy")
            self.quest("fish_buy")
            self.save()

    def fy_sell(self, n):
        f = self.farm
        if not 0 <= n < len(f.fy_fish):
            return
        fish = f.fy_fish[n]
        x, y, _d = f.fish_swim(fish[3], f.fy_clock)
        amt = f.sell_fish(n)
        if amt:
            self.sfx.play("sell" if fish[2] >= 1 else "click")
            self.quest("fish_sell")
            sx, sy = self.fy_to_screen(x, y)
            self.floater(sx, sy - 20, f"+${fmt(amt)}")

    def fy_sell_adults(self):
        amt, n = self.farm.sell_adults()
        if n:
            self.sfx.play("coin_big")
            for _ in range(n):
                self.quest("fish_sell")
            self.toast(f"Продано взрослых рыб: {n}  +${fmt(amt)}", 2)
            self.save()

    def fy_upgrade(self):
        if self.farm.upgrade_tank():
            self.sfx.play("buy")
            self.toast(f"Аквариум больше: {self.farm.fy_cap} мест", 2)

    def fy_catch(self):
        """3.38: вылов кнопкой; в 3.39 здесь будет мини-игра."""
        f = self.farm
        if not f.fy_pred:
            return
        x, y, _d = self.fy_pred_pos()
        amt, p = f.catch_predator()
        self.sfx.play("coin_big")
        self.quest("pred_catch")
        self.quest(f"caught_{p['id']}")
        self.floater(x, y - 30, f"+${fmt(amt)}")
        self.toast(f"Выловлен{self._fem(p)} {p['name'].lower()}! +${fmt(amt)}", 3)
        self.save()

    def fishery_attention(self):
        f = self.farm
        return bool(f.fy_pred) or bool(f.adults())

    # ------------------------------------------------------------ фон
    def fy_build_bg(self):
        bg = hd.Surface((W, H))
        img = sprite("backgrounds/fishery")
        if img is not None:
            bg.blit(pygame.transform.smoothscale(img, (W, H)) if img.get_size() != (W, H) else img, (0, 0))
            return bg, True
        for y in range(0, H, 4):                              # вода: сверху светлее
            k = y / H
            pygame.draw.rect(bg, (int(92 - 50 * k), int(150 - 60 * k), int(172 - 55 * k)), (0, y, W, 4))
        for n in range(5):                                    # косые лучи света
            x0 = 160 + n * 200
            col = (int(104 - 6 * n), int(160 - 5 * n), int(182 - 4 * n))
            pygame.draw.polygon(bg, col, [(x0, 0), (x0 + 40, 0), (x0 - 70, SAND_Y), (x0 - 130, SAND_Y)])
        sand = [(0, H)] + [(x, SAND_Y + 8 * math.sin(x / 70) + 4 * math.sin(x / 23)) for x in range(0, W + 20, 20)] + [(W, H)]
        pygame.draw.polygon(bg, (214, 192, 146), sand)
        pygame.draw.lines(bg, (160, 135, 95), False, sand[1:-1], 3)
        rnd = random.Random(11)
        for _ in range(140):                                  # песчинки
            x, y = rnd.randint(0, W), rnd.randint(SAND_Y + 14, H)
            pygame.draw.circle(bg, rnd.choice([(190, 168, 125), (230, 212, 170), (175, 150, 110)]), (x, y), rnd.randint(1, 3))
        for x, y, w, h, c in ((70, 540, 120, 60, (120, 125, 130)), (300, 548, 70, 40, (140, 140, 135)),
                              (720, 536, 150, 70, (110, 118, 125)), (900, 552, 80, 46, (135, 130, 125))):
            ellipse(bg, c, x, y, w, h, 3)                     # камни
            ellipse(bg, tuple(min(255, v + 30) for v in c), x - w * 0.15, y - h * 0.2, w * 0.35, h * 0.25, 0)
        return bg, False

    def draw_algae(self, s, t):
        for n, (x, hgt, col) in enumerate(((30, 230, (60, 130, 80)), (175, 170, (80, 150, 90)), (250, 120, (50, 120, 90)),
                                           (520, 190, (70, 140, 85)), (640, 110, (90, 160, 95)), (820, 250, (55, 125, 80)),
                                           (965, 160, (75, 145, 90)))):
            base = SAND_Y + 14
            pts = [(x + math.sin(t * 1.1 + n + j / 8 * 3) * 14 * j / 8, base - hgt * j / 8) for j in range(9)]
            pygame.draw.lines(s, OUT, False, [(P(px), P(py)) for px, py in pts], max(1, P(9)))
            pygame.draw.lines(s, col, False, [(P(px), P(py)) for px, py in pts], max(1, P(6)))

    def draw_bubbles(self, s, t):
        for n, x0 in enumerate((80, 330, 470, 700, 760, 905)):
            for j in range(4):
                ph = (t * (26 + n * 3) + j * 110 + n * 37) % (SAND_Y - 40)
                x = x0 + 5 * math.sin(t * 2 + j + n)
                pygame.draw.circle(s, (215, 240, 250), (P(x), P(SAND_Y + 10 - ph)), max(1, P(2 + (j + n) % 3)), 1)

    # ------------------------------------------------------------ рисование
    def draw_fishery_view(self):
        s, f, t = self.screen, self.farm, self.t_real
        if self.fy_bg is None:
            self.fy_bg = self.fy_build_bg()
        bg, is_pic = self.fy_bg
        s.blit(bg, (0, 0))
        if not is_pic:
            self.draw_algae(s, t)
        self.draw_bubbles(s, t)
        for e in f.fy_eggs:
            x, y = self.fy_to_screen(e[1], e[2])
            draw_roe(s, x, y, 1.0, t, 1 - e[3] / FISH_HATCH)
            self.tip(pygame.Rect(x - 12, y - 10, 24, 22), f"Икра: {CROPS[e[0] - 1]['name'].lower()}. Хищники её не трогают")
        for n, fish in enumerate(f.fy_fish):
            fx, fy, d = f.fish_swim(fish[3], f.fy_clock)
            x, y = self.fy_to_screen(fx, fy)
            g = fish[2]
            k = 0.6 + 0.7 * g
            draw_swim_fish(s, x, y, k, CROP_KEYS[fish[0] - 1], d, t + fish[3], glow=g >= 1)
            r = pygame.Rect(x - 18 * k, y - 12 * k, 36 * k, 24 * k)
            self.zone(r, lambda n=n: self.fy_sell(n))
            word = "взрослая" if g >= 1 else f"растёт {int(g * 100)}%"
            self.tip(r, f"{CROPS[fish[0] - 1]['name']}: {word} · ${fmt(f.fish_worth(fish))} — щёлкни, чтобы продать")
        if f.fy_pred:
            self.draw_tank_predator(s, t)
        self.draw_banner((W // 2 - 110, 22, 220, 46), "САДКИ", 22)
        self.draw_pred_timer(s, t)
        self.draw_tank_buttons(s)
        if self.fy_shop:
            self.draw_fish_shop(s, t)
        for x, y, text, life, color in self.floaters:
            draw_text(s, text, 18, (x, y), color)

    def draw_tank_predator(self, s, t):
        f = self.farm
        p = f.predator()
        x, y, d = self.fy_pred_pos()
        k = 1.25 + 0.15 * p["rank"] + 0.03 * min(10, f.fy_pred_eaten)
        draw_predator(s, x, y, k, p["id"], t, flip=d > 0)
        r = pygame.Rect(x - 40 * k, y - 22 * k, 80 * k, 44 * k)
        self.zone(r, self.fy_catch)
        self.tip(r, f"{p['name']} ({PRED_RANK_NAMES[p['rank']].lower()}): {f.predator_kg():.1f} кг, "
                    f"${fmt(f.fy_pred_val)}. Щёлкни — выловить")
        draw_text(s, p["name"], 15, (x, y - 22 * k - 26))
        for n in range(p["rank"]):
            draw_star(s, x - (p["rank"] - 1) * 7 + n * 14, y - 22 * k - 10, 6, GOLD)

    def draw_pred_timer(self, s, t):
        f = self.farm
        rounded(s, (40, 50, 60), BAR.inflate(4, 4), 9, 2, skin=None)
        grace = f.grace_left()
        if grace is not None:                                   # тлеет: сколько осталось, не пишем
            w = int(BAR.w * grace)
            if w > 0:
                fl = 0.5 + 0.5 * math.sin(t * 23) * math.sin(t * 7.3)
                col = (int(230 + 25 * fl), int(90 + 60 * fl), int(30 + 20 * fl))
                rounded(s, col, pygame.Rect(BAR.x, BAR.y, w, BAR.h), 8, 0, skin=None)
                rnd = random.Random(int(t * 12))
                for _ in range(4):
                    pygame.draw.circle(s, (255, 200, 90), (P(BAR.x + w - rnd.randint(0, 14)),
                                                           P(BAR.y - rnd.randint(0, 9))), max(1, P(1.5)))
            self.fy_catch_button()
            return
        if f.fy_pred:
            rounded(s, (200, 70, 60), BAR, 8, 0, skin=None)
            draw_text(s, f"{f.predator()['name']} в садке!", 12, BAR.center)
            self.fy_catch_button()
            return
        draw_bar(s, BAR, 1 - f.fy_timer / FISH_PRED_EVERY, (120, 190, 220))
        draw_text(s, f"хищник через {_mmss(f.fy_timer)}" if f.fy_fish else "хищник ждёт рыбу", 11, BAR.center)
        self.tip(BAR, "Раз в 5 минут, пока в аквариуме есть рыба, приплывает хищник")

    def fy_catch_button(self):
        f = self.farm
        self.button((W // 2 - 120, BAR.bottom + 8, 240, 34), f"Выловить: ${fmt(f.fy_pred_val)}", self.fy_catch,
                    skin.BTN_RED if f.grace_left() is not None else BTN_GREEN, True, 15)

    def draw_tank_buttons(self, s):
        f = self.farm
        y = 580
        self.button((140, y, 230, 46), "Закрыть лавку" if self.fy_shop else "Купить рыбу",
                    lambda: setattr(self, "fy_shop", not self.fy_shop), BTN_BLUE, True, 17)
        adults = f.adults()
        amt = sum(f.fish_worth(f.fy_fish[n]) for n in adults)
        self.button((385, y, 270, 46), f"Продать взрослых  ${fmt(amt)}" if adults else "Взрослых пока нет",
                    self.fy_sell_adults, BTN_GREEN, bool(adults), 16)
        cost = f.tank_cost()
        used = f"Мест: {f.tank_used()}/{f.fy_cap}"
        if cost is None:
            skin.draw_max(s, pygame.Rect(670, y, 300, 46), 15, used + " — больше некуда")
        else:
            self.button((670, y, 300, 46), f"{used}  ·  +{FISH_TANK_STEP} за ${fmt(cost)}", self.fy_upgrade,
                        BTN_BLUE, f.money >= cost, 15)

    def draw_fish_shop(self, s, t):
        f = self.farm
        rounded(s, (238, 226, 200), SHOP, 14, 3, skin="card")
        full = f.tank_used() >= f.fy_cap
        title = "Аквариум полон — продай кого-нибудь" if full else f"Лавка: малёк вырастет — и стоит x{FISH_ADULT_MULT:g}"
        draw_text(s, title, 14, (SHOP.centerx, SHOP.y + 16), (90, 70, 60), outline=None)
        cw, gap = 86, 6
        x0 = SHOP.x + (SHOP.w - (N_CROPS * cw + (N_CROPS - 1) * gap)) // 2
        for i in range(N_CROPS):
            r = pygame.Rect(x0 + i * (cw + gap), SHOP.y + 32, cw, SHOP.h - 42)
            if f.levels[i] <= 0:
                rounded(s, (215, 205, 185), r, 10, 2, skin=None)
                draw_text(s, "?", 26, r.center, (170, 155, 135), outline=None)
                self.tip(r, "Открой этот участок пруда — рыбка появится в лавке")
                continue
            ok = f.can_buy_fish(i)
            rounded(s, (250, 242, 222) if ok else (225, 215, 195), r, 10, 2, skin=None)
            draw_swim_fish(s, r.centerx, r.y + 30, 1.1, CROP_KEYS[i], -1, t + i)
            draw_text_fit(s, CROPS[i]["name"], 13, (r.centerx, r.y + 58), cw - 6, (90, 70, 60), outline=None)
            draw_text_fit(s, f"растёт {FISH_GROW[i] // 60} мин", 11, (r.centerx, r.y + 76), cw - 10, (140, 110, 95),
                          outline=None)
            self.button((r.x + 4, r.bottom - 34, cw - 8, 30), f"${fmt(f.fish_price(i))}", lambda i=i: self.fy_buy(i),
                        BTN_GREEN, ok, 12)
