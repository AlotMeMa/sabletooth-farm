# -*- coding: utf-8 -*-
"""Сарай: стойла зверей, покупки, фон сарая и мельницы, экран сарая.

Примесь к App (3.15: вынесено из app.py без изменений). Общие импорты и константы — ui_common.
"""
from .ui_common import *  # noqa: F401,F403


class BarnUI:
    # ------------------------------------------------------------ сарай
    def toggle_barn(self):
        if self.view not in ("field", "barn"):
            return
        self.view = "field" if self.view == "barn" else "barn"
        self.mode = "normal"

    def barn_attention(self):
        f = self.farm
        if self.farm_info()["barn"] == "mill":
            return f.bread > 0 or any(f.m_levels[b] == 0 and f.mill_can_build(b) and f.money >= f.mill_building_cost(b)
                                      for b in (0, 1))
        if f.any_product_ready():
            return True
        return any(f.a_levels[a] == 0 and f.animal_crop_ready(a) and f.money >= f.animal_cost(a)
                   for a in range(N_ANIMALS))

    def do_buy_animal(self, a):
        f = self.farm
        was = f.a_levels[a]
        if f.buy_animal(a):
            self.sfx.play("levelup" if was else "buy")
            self.toast(f"{ANIMALS[a]['name']}: " + ("теперь живёт в сарае!" if was == 0 else f"уровень {f.a_levels[a]}!"), 2)
        else:
            self.toast(f"Не хватает денег: нужно ${fmt(f.animal_cost(a))}, у тебя ${fmt(f.money)}", 2.5)

    def do_buy_keeper(self, a):
        f = self.farm
        if f.buy_keeper(a):
            self.sfx.play("buy")
            self.toast(f"Скотник нанят: сам кормит, {ANIMALS[a]['name'].lower()} не голодает", 2.5)
        else:
            self.toast(f"Не хватает денег: нужно ${fmt(f.keeper_cost(a))}", 2)

    def do_feed(self, a):
        f = self.farm
        crop = ANIMALS[a]["crop"]
        took = f.feed_animal(a)
        if took > 0:
            self.quest("feed")
            self.sfx.play("feed")
            self.floater(self.pen_rect(a).centerx, self.pen_rect(a).y + 205, "корм +$" + fmt(took), (190, 240, 140))
        elif f.stash[crop] <= 0:
            self.toast(f"На грядке «{CROPS[crop]['name']}» пусто — подожди урожай", 2)
        else:
            self.toast("Кормушка полная!", 1.5)

    def do_collect_product(self, a):
        amt = self.farm.collect_product(a)
        if amt:
            self.quest("product")
            self.sfx.play("product")
            r = self.pen_rect(a)
            self.floater(r.centerx, r.y + 60, "+$" + fmt(amt))
            self.toast(f"{ANIMALS[a]['product']}: +$" + fmt(amt), 2)

    def pen_rect(self, a):
        w, gap = 228, 12
        x0 = (W - (N_ANIMALS * w + (N_ANIMALS - 1) * gap)) // 2
        return pygame.Rect(x0 + a * (w + gap), 160, w, 386)

    def build_barn_background(self):
        bg = hd.Surface((W, H))
        if blit_sprite(bg, "backgrounds/barn_inside", 0, 0, 1, "topleft"):
            return bg
        bg.fill((178, 84, 66))
        for x in range(0, W, 44):
            pygame.draw.line(bg, (150, 66, 52), (x, 0), (x, H), 3)
            for y in (60, 230, 400):
                pygame.draw.circle(bg, (130, 60, 48), (x + 22, y + (x // 44) % 3 * 7), 2)
        pygame.draw.rect(bg, (115, 70, 45), (0, 132, W, 18))
        pygame.draw.rect(bg, OUT, (0, 132, W, 18), 3)
        floor = [(0, 470), (W, 470), (W, H), (0, H)]
        poly(bg, (205, 160, 105), floor, 0)
        for y in range(478, H, 22):
            pygame.draw.line(bg, (180, 135, 85), (0, y), (W, y), 2)
        # окно и сено
        rounded(bg, (170, 220, 245), (W // 2 - 50, 20, 100, 80), 4, 4)
        pygame.draw.line(bg, OUT, (W // 2, 20), (W // 2, 100), 3)
        pygame.draw.line(bg, OUT, (W // 2 - 50, 60), (W // 2 + 50, 60), 3)
        for hx, hy in ((W - 230, 70), (W - 175, 95)):
            rounded(bg, (240, 205, 100), (hx, hy, 70, 40), 6, 3)
            for yy in (hy + 13, hy + 26):
                pygame.draw.line(bg, (205, 165, 70), (hx + 6, yy), (hx + 64, yy), 2)
        return bg

    def draw_pen_caption(self, r, text, active):
        """Подпись «Ест: ... -> ...» поверх картинки зверя, на плашке — чтобы её не закрывал крупный спрайт."""
        size = 12
        while size > 8 and render_text(text, size, (140, 110, 95), None).get_width() > r.w - 16:   # 3.24: длинные
            size -= 1                                                                            # зимние названия
        img = render_text(text, size, (140, 110, 95), None)
        box = img.get_rect(center=(r.centerx, r.y + 46)).inflate(12, 4)
        plate = hd.Surface(box.size, pygame.SRCALPHA)
        plate.fill((238, 220, 186, 215) if active else (205, 190, 170, 215))
        self.screen.blit(plate, box)
        self.screen.blit(img, img.get_rect(center=box.center))

    def draw_pen(self, a):
        s, f = self.screen, self.farm
        an = ANIMALS[a]
        r = self.pen_rect(a)
        lvl = f.a_levels[a]
        crop = an["crop"]
        brown, soft = (90, 70, 60), (140, 110, 95)
        rounded(s, (238, 220, 186) if lvl else (205, 190, 170), r, 12, 3)
        head = pygame.Rect(r.x, r.y, r.w, 34)
        pygame.draw.rect(s, (150, 98, 62), head, border_top_left_radius=12, border_top_right_radius=12)
        pygame.draw.rect(s, OUT, head, 3, border_top_left_radius=12, border_top_right_radius=12)
        draw_text(s, an["name"] + (f"  ур. {lvl}" if lvl else ""), 17, head.center)

        # стойло и животное
        ellipse(s, (240, 210, 110), r.centerx, r.y + 150, 170, 34, ow=0)
        hungry = lvl > 0 and f.a_feed[a] <= 0
        if lvl:
            ANIMAL_DRAW[a](s, r.centerx - (10 if a in (1, 2) else 0), r.y + 156, 1.15, self.t + a, not hungry, THEME["snow"])
        else:
            ANIMAL_DRAW[a](s, r.centerx - (10 if a in (1, 2) else 0), r.y + 156, 1.15, 0, False, THEME["snow"])
            shade = hd.Surface((r.w - 20, 110), pygame.SRCALPHA)
            shade.fill((205, 190, 170, 170))
            s.blit(shade, (r.x + 10, r.y + 56))
        self.draw_pen_caption(r, f"Ест: {CROPS[crop]['name']}  ->  {an['product']} x{f.product_ratio(a, max(1, lvl)):.1f}", lvl > 0)
        # забор стойла
        for xx in range(r.x + 14, r.right - 10, 26):
            pygame.draw.rect(s, OUT, (xx - 1, r.y + 150, 8, 26))
            pygame.draw.rect(s, (225, 200, 160), (xx + 1, r.y + 152, 4, 22))
        pygame.draw.line(s, OUT, (r.x + 10, r.y + 160), (r.right - 10, r.y + 160), 5)
        pygame.draw.line(s, (225, 200, 160), (r.x + 10, r.y + 160), (r.right - 10, r.y + 160), 2)

        if lvl == 0:
            if not f.animal_crop_ready(a):
                draw_text(s, f"Сначала посади: {CROPS[crop]['name']}", 14, (r.centerx, r.y + 220), (190, 80, 70), outline=None)
            else:
                draw_text(s, f"Будет есть: {CROPS[crop]['name']}", 14, (r.centerx, r.y + 210), brown, outline=None)
                draw_text_fit(s, f"продукт в {an['ratio']:g} раза дороже корма", 12, (r.centerx, r.y + 232), r.w - 20,
                              soft, outline=None)
                draw_text_fit(s, "с уровнем ест меньше, а продукт дороже", 11, (r.centerx, r.y + 252), r.w - 20,
                              soft, outline=None)
            b = pygame.Rect(r.x + 16, r.bottom - 64, r.w - 32, 46)
            ok = f.animal_crop_ready(a) and f.money >= f.animal_cost(a)
            rounded(s, BTN_GREEN if ok else BTN_GREY, b, 10, 3)
            draw_text(s, "Купить $" + fmt(f.animal_cost(a)), 18, b.center)
            if f.animal_crop_ready(a):
                self.zone_btn(b, lambda a=a: self.do_buy_animal(a))
            return

        # готовые продукты
        if f.a_store[a] > 0:
            px, py = r.right - 36, r.y + 76 + math.sin(self.t * 4 + a) * 3
            pygame.draw.circle(s, OUT, (P(px), P(py)), 22)
            pygame.draw.circle(s, (255, 245, 200), (P(px), P(py)), 20)
            draw_product(s, a, px, py, 1.2)
            draw_text(s, "$" + fmt(f.a_store[a]), 15, (px, py + 30), (255, 235, 120))
        if hungry:
            draw_text(s, "Голодн" + ("ы" if a == 3 else "а") + "!", 15, (r.centerx - 50, r.y + 76), (255, 200, 190))
        self.zone((r.x + 8, r.y + 56, r.w - 16, 120), lambda a=a: self.do_collect_product(a) if self.farm.a_store[a] > 0 else self.do_feed(a))

        # полоски: производство и кормушка
        bar_w = r.w - 40
        t = an["time"]
        draw_bar(s, (r.x + 20, r.y + 184, bar_w, 12), f.a_prog[a] / t if f.a_feed[a] > 0 else 0, GOLD)
        cap = f.feeder_cap(a)
        draw_text(s, f"Корм: ${fmt(f.a_feed[a])} / ${fmt(cap)}", 12, (r.centerx, r.y + 209), brown, outline=None)
        draw_bar(s, (r.x + 20, r.y + 219, bar_w, 12), f.a_feed[a] / cap if cap > 0 else 0, (150, 210, 90))
        draw_text_fit(s, f"Ест ${fmt(f.eat_rate(a))}/с, даёт ${fmt(f.animal_income(a))}/с · на грядке ${fmt(f.stash[crop])}",
                      11, (r.centerx, r.y + 244), r.w - 16, soft, outline=None)

        # кнопки
        b1 = pygame.Rect(r.x + 14, r.y + 258, r.w - 28, 36)
        if f.a_keeper[a]:
            rounded(s, (200, 230, 180), b1, 9, 2)
            left = max(0.0, KEEPER_INTERVAL - f.a_keeper_t[a])
            draw_text(s, f"Скотник придёт через {math.ceil(left)} с", 14, b1.center, (60, 120, 50), outline=None)
        else:
            ok = f.stash[crop] > 0 and f.a_feed[a] < cap
            rounded(s, BTN_GREEN if ok else BTN_GREY, b1, 9, 3)
            draw_text(s, "Покормить", 16, b1.center)
            self.zone_btn(b1, lambda a=a: self.do_feed(a), 9)
        b2 = pygame.Rect(r.x + 14, r.y + 300, r.w - 28, 36)
        if lvl >= ANIMAL_MAX_LVL:
            skin.draw_max(s, b2, 15)
        else:
            price = f.animal_cost(a)
            rounded(s, BTN_BLUE if f.money >= price else BTN_GREY, b2, 9, 3)
            # следующий уровень: еды −10%, продукт дороже
            draw_text_fit(s, f"Ур. {lvl + 1}: x{f.product_ratio(a, lvl + 1):.1f}, еды -10%  ${fmt(price)}", 14, b2.center, b2.w - 12)
            self.zone_btn(b2, lambda a=a: self.do_buy_animal(a), 9)
        if not f.a_keeper[a]:
            b3 = pygame.Rect(r.x + 14, r.y + 342, r.w - 28, 36)
            price = f.keeper_cost(a)
            rounded(s, (235, 170, 70) if f.money >= price else BTN_GREY, b3, 9, 3)
            draw_text(s, f"Скотник: ${fmt(price)}", 15, b3.center)
            self.zone_btn(b3, lambda a=a: self.do_buy_keeper(a), 9)

    # ------------------------------------------------------------ мельница и пекарня
    def build_mill_background(self):
        bg = hd.Surface((W, H))
        if blit_sprite(bg, "backgrounds/mill_inside", 0, 0, 1, "topleft"):
            return bg
        bg.fill((150, 140, 128))
        for row, y in enumerate(range(0, 470, 34)):
            for x in range(-40 if row % 2 else 0, W, 80):
                shade = 160 + (x * 7 + y * 3) % 25
                rounded(bg, (shade, shade - 8, shade - 18), (x + 2, y + 2, 76, 30), 4, 2, (110, 100, 90))
        pygame.draw.rect(bg, (115, 75, 45), (0, 132, W, 18))
        pygame.draw.rect(bg, OUT, (0, 132, W, 18), 3)
        poly(bg, (190, 145, 95), [(0, 470), (W, 470), (W, H), (0, H)], 0)
        for y in range(478, H, 22):
            pygame.draw.line(bg, (165, 120, 75), (0, y), (W, y), 2)
        for sx in (W - 240, W - 180):   # мешки с мукой
            blob(bg, (240, 232, 215), [(sx, 100, 26), (sx + 4, 74, 18)], 3)
            draw_text(bg, "МУКА", 11, (sx, 102), (150, 120, 90), outline=None)
        rounded(bg, (170, 220, 245), (W // 2 - 50, 20, 100, 80), 4, 4)
        pygame.draw.line(bg, OUT, (W // 2, 20), (W // 2, 100), 3)
        return bg

    def draw_barn_view(self):
        if self.farm_info()["barn"] == "mill":
            self.draw_mill_view()
            return
        s = self.screen
        s.blit(self.barn_bg, (0, 0))
        self.draw_banner((W // 2 + 70, 26, 200, 44), "САРАЙ", 22)          # 3.20: текст по полосе ленты
        for a in range(N_ANIMALS):
            self.draw_pen(a)
        for x, y, text, life, color in self.floaters:
            draw_text(s, text, 18, (x, y), color)
