# -*- coding: utf-8 -*-
"""3.37: экран рыборазводни (Рыбацкая деревня, кнопка «Садки» вместо сарая/мельницы).

Две карточки, как у мельницы: слева — нерестовый садок (выбираешь, какую рыбу запустить; она мечет икру и множится
сама), справа — садок хищников (3 места; хищник ест рыбу из первого садка, толстеет, его вылавливают и продают).
Своя картинка фона — backgrounds/fishery; хищники — fish/<id>; иначе всё кодом.
"""
import math
import random

import pygame

from .ui_common import *  # noqa: F401,F403
from .art_fishing import draw_fish, draw_predator
from .tavern_art import draw_star

CARD_Y, CARD_H = 148, 410        # ниже плашек денег слева


class FisheryUI:
    def fishery_init(self):
        self.fy_pick = 0                            # какую рыбу показывает выбор слева
        self.fy_pred_pick = [0] * FISH_SLOTS        # какого хищника предлагает пустое место
        self.fy_bg = None

    def fy_open_species(self):
        return [i for i in range(N_CROPS) if self.farm.levels[i] > 0]

    def fy_build_bg(self):
        bg = hd.Surface((W, H))
        img = sprite("backgrounds/fishery")
        if img is not None:
            bg.blit(pygame.transform.smoothscale(img, (W, H)) if img.get_size() != (W, H) else img, (0, 0))
            return bg
        for y in range(0, H, 8):                    # глубина: сверху светлее
            k = y / H
            pygame.draw.rect(bg, (int(70 - 30 * k), int(110 - 40 * k), int(135 - 35 * k)), (0, y, W, 8))
        rnd = random.Random(5)
        for _ in range(30):                         # водоросли по дну
            x = rnd.randint(0, W)
            hgt = rnd.randint(30, 90)
            pygame.draw.line(bg, (50, 95, 80), (x, H), (x + rnd.randint(-15, 15), H - hgt), 4)
        return bg

    # ------------------------------------------------------------ действия
    def fy_stock(self, i):
        if self.farm.stock_fish(i):
            self.sfx.play("feed")
            self.quest("fish_stock")
            self.toast(f"В садок запущена стайка: {CROPS[i]['name'].lower()}", 2)
            self.save()

    def fy_upgrade(self):
        if self.farm.upgrade_fish_pond():
            self.sfx.play("buy")
            self.toast(f"Садок больше: до {self.farm.fish_cap()} рыб", 2)

    def fy_buy_slot(self):
        if self.farm.buy_fish_slot():
            self.sfx.play("buy")
            self.toast("Ещё одно место для хищника!", 2)

    def fy_buy_pred(self, slot):
        t = self.fy_pred_pick[slot]
        if self.farm.buy_predator(slot, t):
            self.sfx.play("buy")
            self.quest("pred_buy")
            self.toast(f"В садок выпущен малёк: {PREDATORS[t]['name'].lower()}", 2)
            self.save()

    def fy_catch(self, slot):
        """3.37: вылов кнопкой; в 3.38 сюда встанет мини-игра."""
        got = self.farm.catch_predator(slot)
        if not got:
            return
        amt, p = got
        self.sfx.play("coin_big")
        self.quest("pred_catch")
        self.quest(f"caught_{p['id']}")
        self.toast(f"Выловлен{'а' if p['name'][-1] in 'аь' else ''} {p['name'].lower()}! +${fmt(amt)}", 3)
        self.save()

    # ------------------------------------------------------------ рисование
    def draw_fishery_view(self):
        s, f, t = self.screen, self.farm, self.t_real
        if self.fy_bg is None:
            self.fy_bg = self.fy_build_bg()
        s.blit(self.fy_bg, (0, 0))
        self.draw_banner((W // 2 - 110, 22, 220, 46), "САДКИ", 22)
        self.draw_spawn_card(pygame.Rect(40, CARD_Y, 430, CARD_H), t)
        self.draw_pred_card(pygame.Rect(490, CARD_Y, 470, CARD_H), t)
        for x, y, text, life, color in self.floaters:
            draw_text(s, text, 18, (x, y), color)

    def draw_spawn_card(self, r, t):
        s, f = self.screen, self.farm
        brown, soft = (90, 70, 60), (140, 110, 95)
        rounded(s, (238, 226, 200), r, 14, 3, skin="card")
        draw_text(s, "Нерестовый садок", 20, (r.centerx, r.y + 26), brown, outline=None)
        opened = self.fy_open_species()
        if not opened:
            draw_text(s, "Открой участок пруда — будет кого разводить", 14, r.center, soft, outline=None)
            return
        if f.fy_species and (f.fy_species - 1) in opened and self.fy_pick not in opened:
            self.fy_pick = f.fy_species - 1
        if self.fy_pick not in opened:
            self.fy_pick = opened[-1]
        i = self.fy_pick
        # вода садка с рыбками
        water = pygame.Rect(r.x + 24, r.y + 46, r.w - 48, 130)
        rounded(s, (86, 128, 156), water, 12, 3, skin=None)
        n_show = 0 if not f.fy_species else min(14, int(f.fy_pop + 0.5))
        rnd = random.Random(3)
        for n in range(n_show):
            ph = rnd.uniform(0, 6.3)
            fx = water.x + 30 + (water.w - 60) * (0.5 + 0.45 * math.sin(t * 0.3 + ph))
            fy = water.y + 30 + (water.h - 60) * (0.5 + 0.4 * math.sin(t * 0.47 + ph * 1.7))
            draw_fish(s, fx, fy + 12, 0.75, CROP_KEYS[f.fy_species - 1], 0.0)
        for n in range(3 if f.fy_species else 0):          # икринки
            ex = water.x + 40 + n * 22 + 6 * math.sin(t + n)
            pygame.draw.circle(s, (250, 170, 110), (int(ex), water.bottom - 16), 4)
        if f.fy_species:
            draw_bar(s, (water.x, water.bottom + 10, water.w, 20), f.fy_pop / f.fish_cap(), (120, 190, 220))
            hx = water.x + int(water.w * f.fish_floor() / f.fish_cap())          # граница маточного стада
            pygame.draw.line(s, (250, 240, 200), (hx, water.bottom + 8), (hx, water.bottom + 31), 2)
            draw_text(s, f"{CROPS[f.fy_species - 1]['name']}: {int(f.fy_pop)} из {f.fish_cap()}", 13,
                      (water.centerx, water.bottom + 20))
        else:
            draw_text(s, "Садок пуст — запусти стайку", 15, water.center, (230, 240, 245))
        # выбор рыбы
        y0 = water.bottom + 40
        k = opened.index(i)
        if len(opened) > 1:
            self.button((r.x + 24, y0, 40, 40), "<", lambda: self.fy_cycle(-1), BTN_BLUE, True, 18)
            self.button((r.right - 64, y0, 40, 40), ">", lambda: self.fy_cycle(1), BTN_BLUE, True, 18)
        draw_fish(s, r.centerx - 90, y0 + 32, 1.3, CROP_KEYS[i], 0.4)
        draw_text(s, CROPS[i]["name"], 18, (r.centerx + 20, y0 + 10), brown, outline=None)
        draw_text(s, f"рыбка ≈ ${fmt(f.fish_value(i))}", 13, (r.centerx + 20, y0 + 32), soft, outline=None)
        cost = f.fish_stock_cost(i)
        same = f.fy_species == i + 1
        label = f"Запустить стайку  ${fmt(cost)}"
        self.button((r.x + 24, y0 + 56, r.w - 48, 42), label, lambda: self.fy_stock(i), BTN_GREEN, f.can_stock(i), 16)
        if f.fy_species and not same:
            draw_text(s, f"Сейчас в садке {CROPS[f.fy_species - 1]['name'].lower()} — уплывёт на волю", 12,
                      (r.centerx, y0 + 108), (190, 80, 70), outline=None)
        else:
            draw_text(s, "Половина садка — маточное стадо, её не едят", 12, (r.centerx, y0 + 108), soft,
                      outline=None)
        up = f.fish_pond_cost()
        if up is None:
            skin.draw_max(s, pygame.Rect(r.x + 24, r.bottom - 58, r.w - 48, 42), 14, "Садок самый большой")
        else:
            nxt = FISH_POND_CAP[f.fy_lvl]
            self.button((r.x + 24, r.bottom - 58, r.w - 48, 42), f"Садок до {nxt} рыб  ${fmt(up)}",
                        self.fy_upgrade, BTN_BLUE, f.money >= up, 15)

    def fy_cycle(self, d):
        opened = self.fy_open_species()
        if opened:
            k = opened.index(self.fy_pick) if self.fy_pick in opened else 0
            self.fy_pick = opened[(k + d) % len(opened)]

    def draw_pred_card(self, r, t):
        s, f = self.screen, self.farm
        brown, soft = (90, 70, 60), (140, 110, 95)
        rounded(s, (238, 226, 200), r, 14, 3, skin="card")
        draw_text(s, "Садок хищников", 20, (r.centerx, r.y + 26), brown, outline=None)
        hungry = f.fy_pop <= f.fish_floor() + 0.5
        for slot in range(FISH_SLOTS):
            row = pygame.Rect(r.x + 16, r.y + 46 + slot * 120, r.w - 32, 112)
            rounded(s, (220, 232, 236), row, 10, 2, skin=None)
            if slot >= f.fy_slots:
                cost = f.fish_slot_cost() if slot == f.fy_slots else None
                if cost is None:
                    draw_text(s, "закрыто", 15, row.center, soft, outline=None)
                else:
                    self.button(row.inflate(-120, -60), f"Открыть место  ${fmt(cost)}", self.fy_buy_slot, BTN_BLUE,
                                f.money >= cost, 15)
                continue
            p = f.predator(slot)
            if p is None:
                self.draw_pred_shop(row, slot, t)
                continue
            water = pygame.Rect(row.x + 8, row.y + 8, 176, row.h - 16)
            rounded(s, (86, 128, 156), water, 8, 2, skin=None)
            size = 0.8 + 0.7 * f.predator_kg(slot) / p["kg"]
            bob = 4 * math.sin(t * 1.4 + slot)
            draw_predator(s, water.centerx + 8 * math.sin(t * 0.5 + slot), water.centery + bob, size, p["id"], t + slot)
            x = water.right + 14
            draw_text(s, p["name"], 18, (x, row.y + 16), brown, anchor="midleft", outline=None)
            draw_text(s, PRED_RANK_NAMES[p["rank"]], 12, (x, row.y + 34), soft, anchor="midleft", outline=None)
            full = f.predator_full(slot)
            draw_bar(s, (x, row.y + 44, row.right - x - 12, 16), f.fy_eaten[slot] / p["fish"],
                     (240, 190, 70) if full else (120, 190, 90))
            draw_text(s, f"{f.predator_kg(slot):.1f} из {p['kg']} кг", 11, (x + (row.right - x - 12) // 2, row.y + 52))
            status = "наелся!" if full else ("ждёт: мало рыбы" if hungry else "ест и растёт")
            draw_text(s, f"${fmt(f.fy_value[slot])} · {status}", 12, (x, row.y + 72),
                      (190, 80, 70) if (hungry and not full) else soft, anchor="midleft", outline=None)
            self.button((x, row.bottom - 32, row.right - x - 12, 26), "Выловить" if full else "Выловить сейчас",
                        lambda sl=slot: self.fy_catch(sl), BTN_GREEN if full else BTN_GREY, f.fy_eaten[slot] > 0, 14)

    def draw_pred_shop(self, row, slot, t):
        s, f = self.screen, self.farm
        brown, soft = (90, 70, 60), (140, 110, 95)
        k = self.fy_pred_pick[slot] % len(PREDATORS)
        p = PREDATORS[k]
        self.button((row.x + 8, row.centery - 18, 32, 36), "<",
                    lambda: self.fy_pred_step(slot, -1), BTN_BLUE, True, 15)
        self.button((row.x + 192, row.centery - 18, 32, 36), ">",
                    lambda: self.fy_pred_step(slot, 1), BTN_BLUE, True, 15)
        draw_predator(s, row.x + 116, row.centery, 1.1, p["id"], t)
        x = row.x + 236
        draw_text(s, p["name"], 18, (x, row.y + 16), brown, anchor="midleft", outline=None)
        draw_text(s, f"{PRED_RANK_NAMES[p['rank']]} · до {p['kg']} кг", 11, (x, row.y + 34), soft,
                  anchor="midleft", outline=None)
        draw_text(s, f"рыба дороже в {p['ratio']:g} раза", 11, (x, row.y + 50), soft, anchor="midleft", outline=None)
        for n in range(5):                                   # сложность вылова (пригодится в 3.38)
            draw_star(s, row.right - 20 - (4 - n) * 15, row.y + 17, 6, GOLD if n < p["rank"] else (205, 195, 180))
        cost = f.predator_cost(k)
        self.button((x, row.bottom - 38, row.right - x - 12, 30), f"Купить малька  ${fmt(cost)}",
                    lambda: self.fy_buy_pred(slot), BTN_GREEN, f.money >= cost, 14)

    def fy_pred_step(self, slot, d):
        self.fy_pred_pick[slot] = (self.fy_pred_pick[slot] + d) % len(PREDATORS)

    def fishery_attention(self):
        f = self.farm
        return any(f.predator_full(sl) for sl in range(f.fy_slots)) or (
            not f.fy_species and any(f.can_stock(i) for i in self.fy_open_species()))
