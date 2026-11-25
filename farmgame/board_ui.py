# -*- coding: utf-8 -*-
"""Доска заданий: записки дня, свиток недели, награды.

Примесь к App (3.17: вынесено из tavern_ui.py без изменений). Разметка и рисунки — tavern_art.
"""
from .tavern_art import *  # noqa: F401,F403


class BoardUI:
    # ---------- экран: доска ----------
    def draw_board_view(self):
        s = self.screen
        s.blit(self.board_bg, (0, 0))
        plate = pygame.Rect(W // 2 - 190, 6, 380, 58)
        for x in (plate.x + 30, plate.right - 30):
            pygame.draw.line(s, OUT, (x, 0), (x, plate.y + 4), 3)
        rounded(s, (176, 120, 70), plate, 8, 3)
        draw_text(s, "ДОСКА ЗАДАНИЙ", 24, (plate.centerx, plate.y + 21))
        draw_text(s, "новые задания через " + fmt_long(tv.seconds_to_midnight()), 13, (plate.centerx, plate.y + 45),
                  (255, 235, 200))
        for q, r in zip(self.tavern.daily, NOTE_RECTS):
            self.draw_note_card(q, r)
        if self.tavern.weekly:
            self.draw_weekly_card(self.tavern.weekly, WEEKLY_RECT)
        for x, y, text, life, color in self.floaters:
            draw_text(s, text, 18, (x, y), color)

    def draw_reward_line(self, q, cx, y, size=15):
        """$ и жетоны в одну строку по центру."""
        s = self.screen
        minutes, tokens, _p, _b = self.tavern.reward_of(q)
        money = render_text("$" + fmt(self.quest_money(minutes)), size, BROWN, None)
        tok = render_text(str(tokens), size, BROWN, None)
        w = 22 + money.get_width() + 18 + 22 + tok.get_width()
        x = cx - w // 2
        draw_coin(s, x + 9, y, 9)
        s.blit(money, money.get_rect(midleft=(x + 22, y)))
        x += 22 + money.get_width() + 18
        draw_token(s, x + 9, y, 0.6)
        s.blit(tok, tok.get_rect(midleft=(x + 22, y)))

    def draw_claim_area(self, q, rect, size=16):
        s = self.screen
        if q["claimed"]:
            box = rect.inflate(-16, -4)
            pygame.draw.rect(s, (60, 150, 70), box, 3, border_radius=8)
            draw_text(s, "ВЫПОЛНЕНО", size, box.center, (60, 150, 70), outline=None)
        elif q["progress"] >= q["target"]:
            b = rect                      # размер не меняем: иначе «звук наведения» щёлкал бы каждый кадр
            glow = 0.5 + 0.5 * math.sin(self.t_real * 5)
            rounded(s, (255, 230, 120), b.inflate(8, 8), 13, 0)
            rounded(s, tuple(int(c + (255 - c) * 0.25 * glow) for c in BTN_GREEN), b, 10, 3)
            draw_text(s, "Забрать награду!", size, b.center)
            self.zone_btn(b, lambda: self.claim_quest(q, b.center))
        else:
            draw_text(s, "выполняется…", size - 2, rect.center, SOFT, outline=None)

    def draw_note_card(self, q, r):
        """Записка дня 245x167: звёзды сложности, название, задание, прогресс, награда, кнопка."""
        s = self.screen
        from . import skin
        img = skin.stretched(f"quest_note_{q['diff']}", r.w, r.h)   # 3.16: своя бумажка (ui/quest_note_1..3)
        if img is not None:
            s.blit(skin.shadow_of(img), (r.x + 3, r.y + 4))
            s.blit(img, r.topleft)
        else:
            paper = {1: (250, 242, 210), 2: (246, 232, 192), 3: (242, 222, 178)}[q["diff"]]
            pygame.draw.rect(s, (60, 40, 30), r.move(3, 4), border_radius=6)
            rounded(s, paper, r, 6, 2)
        if not blit_sprite(s, "ui/pin", r.centerx, r.y + 8, 0.8, "center"):     # булавка
            pygame.draw.circle(s, OUT, (r.centerx, r.y + 8), 7)
            pygame.draw.circle(s, (210, 60, 60), (r.centerx, r.y + 8), 5)
        for i in range(q["diff"]):
            draw_star(s, r.x + 14 + i * 16, r.y + 13, 7)
        draw_text_fit(s, q["title"], 17, (r.centerx, r.y + 31), r.w - 24, BROWN, outline=None)
        for n, line in enumerate(wrap(q["text"], 14, r.w - 22, 2)):
            draw_text(s, line, 14, (r.centerx, r.y + 52 + n * 17), SOFT, outline=None)
        bar = pygame.Rect(r.x + 14, r.y + 84, r.w - 28, 16)
        draw_bar(s, bar, q["progress"] / max(1, q["target"]), (120, 200, 90))
        draw_text(s, f"{fmt(q['progress'])} / {fmt(q['target'])}", 12, bar.center)
        self.draw_reward_line(q, r.centerx, r.y + 115, 14)
        self.draw_claim_area(q, pygame.Rect(r.x + 14, r.y + 131, r.w - 28, 28), 15)

    def draw_weekly_card(self, q, r):
        """Свиток недели 230x350."""
        s = self.screen
        from . import skin
        img = skin.stretched("quest_weekly", r.w + 14, r.h + 16)   # 3.16: свой свиток (ui/quest_weekly) с валиками
        if img is not None:
            s.blit(skin.shadow_of(img), (r.x - 3, r.y - 3))
            s.blit(img, (r.x - 7, r.y - 8))
        else:
            pygame.draw.rect(s, (60, 40, 30), r.move(4, 5), border_radius=8)
            rounded(s, (248, 236, 200), r, 8, 3)
            for y in (r.y, r.bottom):                         # деревянные валики свитка
                rounded(s, (130, 85, 50), (r.x - 7, y - 8, r.w + 14, 16), 8, 3)
        # 3.16.2: всё — внутри бумаги между валиками (раньше текст налезал на валики, печать — на заголовок,
        # строки награды вылезали за край свитка)
        y0 = r.y + 40
        sx, sy = r.right - 34, y0 + 8
        if not blit_sprite(s, "ui/wax_seal", sx, sy, 0.6, "center"):     # сургучная печать
            blob(s, (200, 45, 50), [(sx + math.cos(a) * 7, sy + math.sin(a) * 7, 5)
                                    for a in [i * math.pi / 4 for i in range(8)]] + [(sx, sy, 9)], 2)
            draw_star(s, sx, sy, 6, (250, 205, 70))
        draw_text(s, "ЗАДАНИЕ", 15, (r.centerx - 16, y0), (190, 60, 50), outline=None)
        draw_text(s, "НЕДЕЛИ", 15, (r.centerx - 16, y0 + 17), (190, 60, 50), outline=None)
        inner = r.w - 40
        draw_text_fit(s, q["title"], 17, (r.centerx, y0 + 42), inner, BROWN, outline=None)
        for n, line in enumerate(wrap(q["text"], 13, inner, 2)):
            draw_text_fit(s, line, 13, (r.centerx, y0 + 62 + n * 15), inner, SOFT, outline=None)
        bar = pygame.Rect(r.x + 20, y0 + 90, r.w - 40, 16)
        draw_bar(s, bar, q["progress"] / max(1, q["target"]), (230, 170, 60))
        draw_text(s, f"{fmt(q['progress'])} / {fmt(q['target'])}", 12, bar.center)
        minutes, tokens, prestige, boost = self.tavern.reward_of(q)
        draw_text(s, "Награда:", 14, (r.centerx, y0 + 124), BROWN, outline=None)
        rows = [(lambda x, y: draw_coin(s, x, y, 8), "$" + fmt(self.quest_money(minutes))),
                (lambda x, y: draw_token(s, x, y, 0.55), f"{tokens} жетонов"),
                (lambda x, y: draw_cur_icon(s, x, y, 0.5), f"{prestige} {CUR['gen']}"),
                (lambda x, y: draw_text(s, "x2", 12, (x, y), GOLD), f"доход x2 на {boost} мин")]
        for n, (icon, text) in enumerate(rows):
            y = y0 + 144 + n * 20
            icon(r.x + 30, y)
            draw_text_fit(s, text, 13, (r.x + 46, y), r.w - 66, BROWN, anchor="midleft", outline=None)
        self.draw_claim_area(q, pygame.Rect(r.x + 20, y0 + 222, r.w - 40, 28), 14)
        draw_text_fit(s, "новое через " + fmt_long(tv.seconds_to_monday()), 11, (r.centerx, y0 + 266), inner, SOFT,
                      outline=None)
