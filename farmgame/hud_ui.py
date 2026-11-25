# -*- coding: utf-8 -*-
"""Плашки сверху (деньги, доход, валюта, крестьяне, бафы), кнопки снизу, шестерёнка.

Примесь к App (3.15: вынесено из app.py без изменений). Общие импорты и константы — ui_common.
"""
from .ui_common import *  # noqa: F401,F403


class HudUI:
    def draw_hud(self):
        s, f = self.screen, self.farm
        board = self.view in ("board", "casino", "gameroom", "blackjack")     # на доске заданий плашки денег закрыли бы записки
        # плашки подстраиваются под длину текста
        def pill(y, h, text, size, icon):
            img = render_text(text, size, WHITE, OUT)
            w = max(h + 30, 58 + img.get_width() + 14)
            if not skin.plate(s, "pill", (14, y, w, h)):          # 3.18: своя плашка ui/pill
                rounded(s, PILL, (14, y, w, h), h // 2, 3)
            icon(34, y + h / 2)
            s.blit(img, img.get_rect(midleft=(58, y + h // 2)))
            return pygame.Rect(14, y, w, h)

        if board:
            pill = lambda *a: pygame.Rect(0, 0, 0, 0)
            self.draw_tokens_pill(14, 12)
        shown = f.money if self.money_shown is None else self.money_shown
        bump = math.sin(min(1.0, 1 - self.money_bump) * math.pi) * 0.22 if self.money_bump > 0 else 0.0
        money_rect = pill(12, 40, "$" + fmt(shown), 20, lambda x, y: draw_coin(s, x, y, 17 * (1 + bump)))
        self.tip(money_rect, "Деньги. Урожай собирай с грядок — монетки прилетят сюда")
        inc_rect = pill(58, 36, "$" + fmt(f.total_income()) + " /с", 17, lambda x, y: draw_coin(s, x, y, 15, (200, 215, 240)))
        self.tip(inc_rect, "Доход в секунду со всех грядок")
        leaf_rect = pill(100, 36, f"{f.leaves}  {fmt_mult(f.home_leaves)}", 17, lambda x, y: draw_cur_icon(s, x, y, 0.95))
        if not board:
            self.zone_btn(leaf_rect, lambda: self.open_modal("tree"), 18)
            self.tip(leaf_rect, f"{CUR['title']}: множитель дохода. Щёлкни — дерево улучшений")
        if self.farm_info()["peasants"] and not board and self.view != "barn":   # 3.26.1: в сарае налезала на карточку
            pr = pill(142, 32, f"свободно {f.free_peasants()} из {f.peasants}", 15,
                      lambda x, y: draw_helper_head(s, x, y + 1, 1.1))
            self.zone_btn(pr, lambda: (self.open_modal("shop"), setattr(self, "shop_tab", "farm")), 16)
            self.tip(pr, f"Свободные {self.helpers()['title'].lower()}. Щёлкни — нанять ещё")
        if not board:
            # 3.13.2: на поле — столбиком слева; в сарае, мельнице, таверне — справа под шестерёнкой,
            # чтобы не налезать на карточки
            center = None
            if self.view == "field":
                y, right = (180 if self.farm_info()["peasants"] else 142), None
            elif self.view == "tavern":                  # 3.20: в зале — сверху по центру, над сценой
                y, right, center = 12, None, W // 2
            else:
                y, right = 70, W - 14
            y += self.draw_boost_pill(y, right, center)
            self.draw_song_pill(y, right, center)

        # шестерёнка
        g = pygame.Rect(W - 62, 12, 50, 50)

        def gear(r):
            for k in range(8):
                a = k * math.pi / 4
                pygame.draw.circle(s, OUT, (P(r.centerx + math.cos(a) * 14), P(r.centery + math.sin(a) * 14)), 6)
            pygame.draw.circle(s, OUT, r.center, 14)
            pygame.draw.circle(s, BTN_BLUE, r.center, 6)
        self.icon_button(g, "settings", gear, lambda: self.open_modal("settings"), tip="Настройки: звук, экран, игра")
        if self.view == "tavern":
            self.draw_tokens_pill(14, 180 if self.farm_info()["peasants"] else 142)
            self.draw_tavern_back("На поле", self.leave_tavern)
            self.draw_prizes_button()
            self.draw_achievements_button()      # 3.34
            self.draw_barman_menu()              # 3.34: темы для разговора с барменом
            return
        if board:
            if self.view == "casino":       # 3.14.2: над столом слева; 3.27: из рулетки — назад в Игровую
                self.draw_tavern_back("В игровую", lambda: setattr(self, "view", "gameroom"), 170, (14, 60), 46)
            elif self.view == "blackjack":
                self.draw_tavern_back("В игровую", self.bj_leave, 170, (14, 60), 46)
            elif self.view == "gameroom":
                self.draw_tavern_back("В таверну", lambda: setattr(self, "view", "tavern"), 170, (14, 60), 46)
            else:
                self.draw_tavern_back("В таверну", lambda: setattr(self, "view", "tavern"), 170)
            return

        if DEV:
            tag = draw_text(s, f"DEV  F1   скорость x{self.time_scale}", 14, (W // 2, 628), (255, 120, 120))
        # нижние кнопки (картинки — assets/ui/btn_*.png или лист assets/ui/buttons.png)
        if self.view == "barn":
            if has_sprite("ui/btn_field"):
                self.icon_button(pygame.Rect(16, 560, 62, 56), "field", None, self.toggle_barn, "На поле")
            else:
                back = pygame.Rect(16, 560, 134, 56)
                rounded(s, BTN_GREEN, back, 10, 3)
                draw_text(s, "<  На поле", 18, back.center)
                self.zone_btn(back, self.toggle_barn)
            return

        def cart(r):
            x, y = r.x - 16, r.y - 560
            pygame.draw.lines(s, OUT, False, [(x + 26, y + 573), (x + 34, y + 573), (x + 40, y + 598), (x + 64, y + 598),
                                              (x + 68, y + 581), (x + 37, y + 581)], 4)
            pygame.draw.circle(s, OUT, (x + 43, y + 606), 4)
            pygame.draw.circle(s, OUT, (x + 61, y + 606), 4)

        def shovel(r):
            x, y = r.x - 88, r.y - 560
            pygame.draw.line(s, OUT, (x + 102, y + 572), (x + 122, y + 594), 5)
            poly(s, (120, 120, 130), [(x + 118, y + 590), (x + 132, y + 578), (x + 142, y + 600), (x + 130, y + 606)])

        def barn_icon(r):
            x = r.x - 232
            if self.farm_info()["barn"] == "mill":
                poly(s, (210, 195, 170), [(x + 253, 610), (x + 273, 610), (x + 269, 586), (x + 257, 586)], 2)
                draw_mill_blades(s, x + 263, 584, self.t * 0.8, 20)
            else:
                poly(s, (225, 75, 70), [(x + 244, 590), (x + 263, 576), (x + 282, 590), (x + 282, 607), (x + 244, 607)])
                rounded(s, (240, 235, 230), (x + 256, 594, 14, 13), 1, 2)

        def move_icon(r):
            c = r.center
            if FARMS[f.farm_index + 1]["peasants"]:   # башенка — следующая глава средневековая
                poly(s, (200, 195, 188), [(c[0] - 12, c[1] + 18), (c[0] + 12, c[1] + 18), (c[0] + 12, c[1] - 10), (c[0] - 12, c[1] - 10)], 2)
                for dx in (-12, -2, 8):
                    poly(s, (200, 195, 188), [(c[0] + dx, c[1] - 10), (c[0] + dx + 5, c[1] - 10), (c[0] + dx + 5, c[1] - 16), (c[0] + dx, c[1] - 16)], 2)
                pygame.draw.line(s, OUT, (c[0], c[1] - 16), (c[0], c[1] - 26), 2)
                poly(s, (220, 60, 60), [(c[0], c[1] - 26), (c[0] + 10, c[1] - 22), (c[0], c[1] - 18)], 1)
                rounded(s, (110, 75, 50), (c[0] - 4, c[1] + 6, 8, 12), 3, 1)
            else:
                for k in range(3):   # снежинка — следующая ферма зимняя
                    ang = k * math.pi / 3
                    dx, dy = math.cos(ang) * 17, math.sin(ang) * 17
                    pygame.draw.line(s, OUT, (P(c[0] - dx), P(c[1] - dy)), (P(c[0] + dx), P(c[1] + dy)), 6)
                    pygame.draw.line(s, WHITE, (P(c[0] - dx), P(c[1] - dy)), (P(c[0] + dx), P(c[1] + dy)), 3)

        upgrade_on = self.mode == "upgrade"
        self.draw_tavern_button()
        self.icon_button(pygame.Rect(16, 560, 62, 56), "shop", cart, lambda: self.open_modal("shop"), "Магазин",
                         badge=self.shop_has_affordable(),
                         tip="Магазин: удобрения (прибыль x3) и " + (self.helpers()["title"].lower() if self.farm_info()["peasants"] else "фермеры") + "   (S)")
        self.icon_button(pygame.Rect(88, 560, 62, 56), "upgrade", shovel,
                         lambda: setattr(self, "mode", "normal" if self.mode == "upgrade" else "upgrade"), "Прокачка",
                         active=upgrade_on, tip="Прокачка грядок: по 1, по 10, до вехи или на все деньги   (U)")
        self.icon_button(pygame.Rect(160, 560, 62, 56), "tree", lambda r: draw_cur_icon(s, r.centerx, r.centery, 1.2),
                         lambda: self.open_modal("tree"), CUR.get("short", CUR["title"]), badge=f.any_tree_affordable(),
                         tip=f"Дерево улучшений: постоянные бонусы за {CUR['title'].lower()}")
        mill = self.farm_info()["barn"] == "mill"
        self.icon_button(pygame.Rect(232, 560, 62, 56), "mill" if mill else "barn", barn_icon, self.toggle_barn,
                         "Мельница" if mill else "Сарай", badge=self.barn_attention(),
                         tip=("Мельница и пекарня: зерно — мука — хлеб" if mill
                              else "Сарай: звери едят урожай и дают продукты дороже") + "   (B)")
        # 3.23: кнопка есть всегда — открывает карту глав (на последней готовой ферме — посмотреть, что дальше)
        self.icon_button(pygame.Rect(304, 560, 62, 56), "move", move_icon, lambda: self.open_modal("move"), "Переезд",
                         badge=f.can_move(), active=f.can_move(),
                         tip=("Карта глав и переезд на новую ферму: всё с нуля, но доход x2 и трофей"
                              if f.has_next_farm() else "Карта глав: где ты и что будет дальше"))
