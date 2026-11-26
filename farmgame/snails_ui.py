# -*- coding: utf-8 -*-
"""3.40: экран скачек улиток в Игровой. Логика — snails.py.

Ведёт моряк Старый Якорь (решение пользователя 26.11): седой, одноглазый, травит байки про море, любит выпить и
поиграть. Стол — общий стол Игровой («все игры на одном столе»): на сукне пять дорожек, старт слева, финиш справа.
Свои картинки (необязательно): characters/sailor (по пояс, низ = край стола), characters/snail_1..5 (улитки, смотрят
вправо; лист characters/snails_sheet), icons/game_snails (значок на карте Игровой). Без них — кодом.
"""
import math
import random

import pygame

from .ui_common import *  # noqa: F401,F403
from .tavern_ui import draw_token
from .casino_ui import draw_chip, chip_for, draw_side_bubble
from . import casino as cs
from . import snails as sn

SAILOR = (500, 238)              # где Якорь: середина низа = край стола
SAILOR_NAME = "Старый Якорь"
LANE_Y0, LANE_STEP, LANE_H = 300, 46, 38
START_X, FINISH_X = 182, 790
COUNTDOWN = 1.4                  # «На старт... Марш!» перед забегом, с
SN_LAYOUT = dict(chips_y=565, chips_x=150, clear=pygame.Rect(300, 546, 88, 38), go=pygame.Rect(748, 540, 175, 48),
                 history=(70, 470))

SAILOR_INTRO = [
    "Ха! Свежая душа на скачках! Я — Старый Якорь. Сорок лет по морям, один глаз оставил кракену.",
    "Щёлкни по дорожке — выберешь улитку, ещё щелчок — фишка. Ставить можно на нескольких сразу.",
    "Справа — множитель, если придёт первой. «В ударе» — резвее, «сонная» — тащится. Жми «Старт!» и болей!",
]
SAILOR_HELLO = ["Ого, снова ты! Наливай... то есть ставь!", "Улитки размяты, ром налит. Ставим?",
                "Ветер попутный — к большому выигрышу. А может, и нет. Ха!", "Садись, юнга. Сегодня Молния злая."]
SAILOR_SAY = {
    "poke": ["Однажды улитка обогнала мою шхуну. Правда, шхуна стояла на якоре... Ха!",
             "В Кривой Бухте улиток кормят морской капустой — бегут как ошпаренные.",
             "Глаз? Кракен. Ногу? Тоже кракен. А ром — это уже я сам.",
             "Бабушка Улита старше меня. И быстрее, когда никто не видит.",
             "Не ставь на ту, что «сонная». Хотя... я как-то поставил — и купил лодку!"],
    "start": ["На старт... Внимание... Марш!", "Поползли, родные!", "Улитки пошли!"],
    "win": ["Ха-ха! Твоя пришла! Наливаю за счёт заведения... шучу, жетоны держи.",
            "Вот это заплыв! Забирай выигрыш, юнга!", "Тысяча медуз — она первая! Повезло тебе."],
    "lose": ["Эх, не твой ветер. Ещё забег?", "Ха! Улитки — они как море: никогда не знаешь.",
             "Не горюй, юнга. Я раз проиграл корабль. Целый!"],
    "partial": ["Угадал, юнга! Да только остальные ставки — мои. Ха!",
                "На всех ставить — что сеть рвать: рыба есть, а прибыли нет.",
                "Пришла твоя, а карман всё равно легче. Море не обманешь!"],
}
RESULT_COLORS = {True: (255, 220, 90), False: (230, 200, 190)}


def draw_sailor(s, x, wy, k=2.5, t=0.0, talking=False):
    """Старый Якорь по пояс за столом: бушлат, седая борода, повязка на глазу, капитанская фуражка, трубка."""
    if blit_tf(s, "characters/sailor", x, wy + 2, 1.3 * k / 2.5, angle=math.sin(t * 0.9) * 1.5):
        return
    u = k / 2.0
    sway = math.sin(t * 0.9) * 2 * u                                  # чуть покачивается — «на палубе»
    breath = math.sin(t * 1.4) * 1.2
    coat, gold = (40, 55, 90), (230, 190, 80)
    poly(s, coat, [(x - 56 * u, wy), (x + 56 * u, wy), (x + 42 * u + sway, wy - 64 * u + breath),
                   (x - 42 * u + sway, wy - 64 * u + breath)], 3)
    for dy in (14, 30, 46):                                           # пуговицы
        pygame.draw.circle(s, gold, (P(x + sway * 0.5 - 10 * u), P(wy - dy * u)), max(2, P(3 * u)))
        pygame.draw.circle(s, gold, (P(x + sway * 0.5 + 10 * u), P(wy - dy * u)), max(2, P(3 * u)))
    for sx in (-1, 1):                                                # руки на столе
        ellipse(s, coat, x + sx * 48 * u, wy - 10 * u, 26 * u, 34 * u, 2)
        pygame.draw.circle(s, OUT, (P(x + sx * 48 * u), P(wy + 6 * u)), P(9 * u) + 2)
        pygame.draw.circle(s, (225, 180, 150), (P(x + sx * 48 * u), P(wy + 6 * u)), P(9 * u))
    mx, my = x + 70 * u, wy - 4 * u                                   # кружка
    rounded(s, (190, 190, 200), (P(mx - 10 * u), P(my - 26 * u), P(20 * u), P(26 * u)), max(2, P(3 * u)), 2, skin=None)
    ellipse(s, (250, 245, 230), mx, my - 26 * u, 20 * u, 8 * u, 2)
    hx, hy = x + sway, wy - 96 * u + breath
    blob(s, (225, 225, 228), [(hx, hy + 30 * u, 26 * u), (hx - 18 * u, hy + 18 * u, 17 * u), (hx + 18 * u, hy + 18 * u, 17 * u),
                              (hx, hy + 48 * u, 15 * u)], 3)                                # седая борода
    blob(s, (225, 180, 150), [(hx, hy, 22 * u)], 3)
    pygame.draw.circle(s, (210, 130, 110), (P(hx + 1 * u), P(hy + 6 * u)), P(7 * u))      # красный нос
    pygame.draw.circle(s, OUT, (P(hx + 9 * u), P(hy - 3 * u)), max(1, P(2.4 * u)))       # глаз
    pygame.draw.line(s, OUT, (P(hx - 22 * u), P(hy - 14 * u)), (P(hx + 18 * u), P(hy - 4 * u)), max(2, P(2.5 * u)))
    ellipse(s, (35, 35, 40), hx - 9 * u, hy - 3 * u, 12 * u, 10 * u, 2)                     # повязка
    mouth = 3 * u if talking else 0
    pygame.draw.arc(s, OUT, pygame.Rect(P(hx - 8 * u), P(hy + 12 * u - mouth), P(16 * u), P(8 * u + mouth)),
                    math.pi + 0.3, 2 * math.pi - 0.3, max(2, P(2 * u)))                  # улыбается
    px, py = hx + 10 * u, hy + 16 * u                                 # трубка и дымок
    pygame.draw.line(s, (90, 60, 40), (P(px), P(py)), (P(px + 16 * u), P(py + 4 * u)), max(2, P(3 * u)))
    rounded(s, (110, 70, 45), (P(px + 14 * u), P(py - 6 * u), P(9 * u), P(11 * u)), max(1, P(2 * u)), 2, skin=None)
    for n in range(3):
        a = (t * 0.7 + n / 3) % 1
        pygame.draw.circle(s, (215, 215, 220), (P(px + 18 * u + 6 * u * math.sin(a * 6 + n)), P(py - 10 * u - a * 30 * u)),
                           max(1, P((2 + 3 * a) * u)), 1)
    rounded(s, (30, 35, 60), (P(hx - 28 * u), P(hy - 24 * u), P(56 * u), P(12 * u)), max(2, P(4 * u)), 2, skin=None)
    poly(s, (245, 245, 245), [(hx - 26 * u, hy - 22 * u), (hx + 26 * u, hy - 22 * u), (hx + 22 * u, hy - 40 * u),
                              (hx - 22 * u, hy - 40 * u)], 3)                               # фуражка
    pygame.draw.circle(s, gold, (P(hx), P(hy - 30 * u)), max(2, P(4 * u)))


def draw_snail(s, x, y, k, i, t=0.0, moving=False):
    """Улитка номер i смотрит вправо; (x, y) — где она касается дорожки (середина)."""
    if blit_tf(s, f"characters/snail_{i + 1}", x, y + 2, 0.5 * k, sy=1 + (0.06 * math.sin(t * 10) if moving else 0)):
        return
    look = sn.SNAILS[i]
    stretch = (1 + 0.12 * math.sin(t * 8)) if moving else 1.0
    body = [(x - 22 * k * stretch, y), (x + 18 * k * stretch, y), (x + 22 * k * stretch, y - 8 * k),
            (x + 14 * k * stretch, y - 14 * k), (x - 18 * k, y - 6 * k)]
    poly(s, look["body"], body, 2)
    hx = x + 18 * k * stretch
    for dx, dy in ((-2, -24), (5, -22)):                              # рожки с глазками
        pygame.draw.line(s, OUT, (P(hx - 2 * k), P(y - 12 * k)), (P(hx + dx * k), P(y + dy * k)), max(1, P(2 * k)))
        pygame.draw.circle(s, OUT, (P(hx + dx * k), P(y + dy * k)), max(2, P(2.4 * k)))
    pygame.draw.circle(s, OUT, (P(hx + 3 * k), P(y - 8 * k)), max(1, P(1.2 * k)))
    cx, cy, r = x - 4 * k, y - 15 * k, 13 * k                         # раковина со спиралью
    pygame.draw.circle(s, OUT, (P(cx), P(cy)), P(r) + 2)
    pygame.draw.circle(s, look["shell"], (P(cx), P(cy)), P(r))
    pts = [(cx + math.cos(a) * r * (0.85 - a / 16), cy + math.sin(a) * r * (0.85 - a / 16)) for a in
           [n * 0.35 for n in range(30)]]
    pygame.draw.lines(s, tuple(max(0, c - 60) for c in look["shell"]), False, [(P(a), P(b)) for a, b in pts],
                      max(1, P(2 * k)))


class SnailsUI:
    def init_snails(self):
        self.sn = sn.SnailRace()
        self.sn_chip = cs.CHIPS[1]
        self.sn_t = 0.0                  # когда (t_real) улитки сорвались с места
        self.sn_say = None               # [текст, секунд] — облачко Якоря
        self.sn_intro = 0
        self.sn_shown = False            # итог забега уже объявлен
        self.sn_bg = None

    def open_snails(self):
        if not sn.unlocked(self.farm.farm_index):
            self.toast("Скачки улиток откроются в Рыбацкой деревне", 3)
            return
        self.view = "snails"
        self.modal = None
        if not getattr(self.tavern, "sn_intro", False):
            self.sn_intro = 0
            self.sn_say = [SAILOR_INTRO[0], 1e9]
        else:
            self.sn_say = [random.choice(SAILOR_HELLO), 3.5]

    # ------------------------------------------------------------ действия
    def sn_poke(self):
        if not getattr(self.tavern, "sn_intro", False):
            self.sn_intro += 1
            if self.sn_intro >= len(SAILOR_INTRO):
                self.tavern.sn_intro = True
                self.sn_say = ["Всё, юнга, хватит трепаться — ставь!", 2.5]
                self.save()
            else:
                self.sn_say = [SAILOR_INTRO[self.sn_intro], 1e9]
            return
        self.sn_say = [random.choice(SAILOR_SAY["poke"]), 4]
        self.sfx.play("hover")

    def sn_rules(self):
        self.tavern.sn_intro = False
        self.sn_intro = 0
        self.sn_say = [SAILOR_INTRO[0], 1e9]

    def sn_select(self, i):
        if self.sn.select(i):
            self.sfx.play("click")

    def sn_place(self):
        if self.sn.pick is None:
            self.toast("Сначала выбери улитку — щёлкни по её дорожке", 2)
            return
        if self.sn.add_bet(self.tavern, self.sn_chip):
            self.sfx.play("feed")
        else:
            self.toast("Не хватает жетонов", 1.5)

    def sn_lane_click(self, i):
        """Щелчок по дорожке: выбрать улитку; по уже выбранной — добавить фишку."""
        if self.sn.state != "bet":
            return
        if self.sn.pick == i:
            self.sn_place()
        else:
            self.sn_select(i)

    def sn_clear(self):
        """«Убрать»: фишки с выбранной улитки; если на ней пусто — со всех."""
        g = self.sn
        g.clear_bet(self.tavern, g.pick if g.bet_on(g.pick) else None)

    def sn_start(self):
        g = self.sn
        if g.bet < sn.MIN_BET:
            self.toast(f"Выбери улитку и поставь от {sn.MIN_BET} жетонов", 2.5)
            return
        if g.start(self.tavern):
            self.sn_t, self.sn_shown = self.t_real + COUNTDOWN, False
            self.sn_say = [random.choice(SAILOR_SAY["start"]), COUNTDOWN + 1.0]
            self.sfx.play("fanfare")
            self.quest("snail_race")
            if not getattr(self.tavern, "sn_intro", False):
                self.tavern.sn_intro = True
            self.save()

    def sn_again(self):
        self.sn.next_round(self.tavern, same_bet=True)
        self.sn_shown = False

    def sn_leave(self):
        self.sn.refund(self.tavern)
        self.view = "gameroom"
        self.save()

    def sn_elapsed(self):
        return self.t_real - self.sn_t

    def snails_tick(self, dt):
        if self.sn_say and self.sn_say[1] < 1e8:
            self.sn_say[1] -= dt
            if self.sn_say[1] <= 0:
                self.sn_say = None
        g = self.sn
        if self.view != "snails":
            if g.state in ("bet", "race") and (g.bet or g.state == "race"):
                g.refund(self.tavern)                 # ушли — несыгранная ставка назад, забег уже оплачен
                self.sn_shown = True
            return
        if g.state == "race" and self.sn_elapsed() >= g.first_time() + 0.5:
            g.finish()
        if g.state == "done" and not self.sn_shown:
            self.sn_shown = True
            w = g.winner()
            if g.net() > 0:                       # 3.40.3: выигрыш — только если в плюсе чистыми
                self.quest("snail_win")
                if g.odds[w]["k"] >= 8:
                    self.quest("snail_long")
                self.sfx.play("coin_big")
                self.fx.sparks(FINISH_X, LANE_Y0 + w * LANE_STEP, n=14, up=70)
                self.sn_say = [random.choice(SAILOR_SAY["win"]), 4]
            elif g.won():                          # угадал, но остальные ставки съели выигрыш
                self.sfx.play("coin")
                self.sn_say = [random.choice(SAILOR_SAY["partial"]), 4.5]
            else:
                self.sfx.play("shoo")
                self.sn_say = [random.choice(SAILOR_SAY["lose"]), 4]

    # ------------------------------------------------------------ рисование
    def build_snails_background(self):
        """Общий стол Игровой и пять дорожек поверх сукна: старт слева, клетчатый финиш справа."""
        bg = hd.Surface((W, H))
        if self.cs_bg is None:
            self.cs_bg = self.build_casino_background()
        bg.blit(self.cs_bg, (0, 0))
        for i in range(len(sn.SNAILS)):
            y = LANE_Y0 + i * LANE_STEP
            lane = pygame.Rect(START_X - 40, y - LANE_H // 2, FINISH_X - START_X + 60, LANE_H)
            rounded(bg, (52, 110, 70) if i % 2 else (60, 124, 80), lane, 8, 0, skin=None)
            for x in range(START_X + 30, FINISH_X, 40):              # разметка
                pygame.draw.line(bg, (95, 150, 105), (x, y + LANE_H // 2 - 4), (x + 16, y + LANE_H // 2 - 4), 2)
        top, bottom = LANE_Y0 - LANE_H // 2, LANE_Y0 + (len(sn.SNAILS) - 1) * LANE_STEP + LANE_H // 2
        pygame.draw.line(bg, (240, 230, 200), (START_X, top), (START_X, bottom), 3)
        for row, y in enumerate(range(top, bottom, 10)):              # клетчатый финиш
            for col in range(2):
                c = (245, 245, 245) if (row + col) % 2 else (40, 40, 44)
                pygame.draw.rect(bg, c, (FINISH_X + col * 10, y, 10, min(10, bottom - y)))
        draw_text(bg, "СТАРТ", 12, (START_X, bottom + 12), (240, 230, 200), outline=None)
        draw_text(bg, "ФИНИШ", 12, (FINISH_X + 10, bottom + 12), (240, 230, 200), outline=None)
        return bg

    def draw_snails_view(self):
        s, g, t = self.screen, self.sn, self.t_real
        if self.sn_bg is None:
            self.sn_bg = self.build_snails_background()
        s.blit(self.sn_bg, (0, 0))
        if has_sprite("ui/banner"):
            self.draw_banner((206, 118, 250, 48), "СКАЧКИ УЛИТОК", 20)
        else:
            plate = pygame.Rect(206, 120, 250, 44)
            rounded(s, (120, 70, 40), plate, 10, 3)
            draw_text(s, "СКАЧКИ УЛИТОК", 20, plate.center, GOLD)
        pb = pygame.Rect(14, 112, 170, 46)
        self.button(pb, "Призы", lambda: self.open_modal("prizes"), (245, 175, 50), True, 19)
        draw_token(s, pb.x + 28, pb.centery, 0.7)
        self.tip(pb, "Призовая стойка: трофеи и украшения за жетоны")
        dx, dy = SAILOR
        talking = self.sn_say is not None and int(t * 6) % 2 == 0
        draw_sailor(s, dx, dy, 2.5, t, talking)
        zone = pygame.Rect(dx - 80, dy - 230, 160, 230)
        self.zone_btn(zone, self.sn_poke, 12)
        self.tip(zone, f"{SAILOR_NAME}: щёлкни — расскажет байку")
        q = pygame.Rect(dx + 100, dy - 44, 32, 32)
        self.button(q, "?", self.sn_rules, BTN_BLUE, True, 16)
        self.tip(q, "Правила ещё раз")
        el = self.sn_elapsed() if g.state != "bet" else 0.0
        for i, look in enumerate(sn.SNAILS):
            y = LANE_Y0 + i * LANE_STEP
            lane = pygame.Rect(START_X - 40, y - LANE_H // 2, FINISH_X - START_X + 60, LANE_H)
            if g.pick == i:
                pygame.draw.rect(s, (255, 230, 140), lane.inflate(4, 4), 3, border_radius=9)
            if g.state == "bet" and self.modal is None:
                self.zone(lane, lambda i=i: self.sn_lane_click(i))
                self.tip(lane, f"{look['name']}: щёлкни — выбрать, ещё раз — поставить фишку")
            pygame.draw.circle(s, OUT, (START_X - 58, y), 13)
            pygame.draw.circle(s, look["shell"], (START_X - 58, y), 11)
            draw_text(s, str(i + 1), 13, (START_X - 58, y), WHITE)
            prog = g.progress(i, max(0.0, el))
            moving = g.state == "race" and 0 < prog < 1 and el > 0
            x = START_X + 24 + (FINISH_X - START_X - 34) * prog
            draw_snail(s, x, y + 12, 1.0, i, t + i, moving)
            if g.bets[i]:                                            # фишки лежат на своей улитке
                draw_chip(s, START_X - 20, y, chip_for(g.bets[i]), 0.8, str(g.bets[i]))
                if g.state == "bet":                                  # 3.40.3: чем кончится, если придёт она
                    net = int(round(g.bets[i] * g.odds[i]["k"])) - g.bet
                    col = (170, 240, 150) if net > 0 else (255, 190, 170)
                    draw_text(s, f"придёт первой: {net:+d}", 13, (START_X + 72, y), col, anchor="midleft")
            od = g.odds[i]
            tx = FINISH_X + 34
            draw_text(s, look["name"], 13, (tx, y - 8), WHITE, anchor="midleft")
            tail = f"x{od['k']:g}" + (f" · {od['mood']}" if od["mood"] else "")
            draw_text(s, tail, 12, (tx, y + 9), (255, 220, 120) if od["mood"] == "в ударе" else (220, 230, 210),
                      anchor="midleft")
            if g.state != "bet" and prog >= 1:                       # место — медалька слева от улитки
                place = g.order.index(i) + 1
                bx = FINISH_X - 66
                col = {1: (245, 200, 60), 2: (200, 205, 215), 3: (205, 135, 75)}.get(place, (120, 130, 120))
                pygame.draw.circle(s, OUT, (bx, y), 12)
                pygame.draw.circle(s, col, (bx, y), 10)
                draw_text(s, str(place), 13, (bx, y), WHITE)
        if g.state == "race" and el < 0:                                  # «На старт...»
            draw_text(s, str(max(1, math.ceil(-el / (COUNTDOWN / 3)))), 44, (500, 400), WHITE)
        if g.state == "done":
            w = g.winner()
            name = sn.SNAILS[w]["name"]
            net = g.net()
            if net > 0:
                msg = f"{name} — первая! +{net} чистыми (выплата {g.paid} за {g.bet})"
            elif g.won() and net == 0:
                msg = f"{name} — первая. Выплата {g.paid} — ровно в ноль"
            elif g.won():
                msg = f"{name} — первая. Вернулось {g.paid} из {g.bet} ({net})"
            else:
                msg = f"Первой пришла {name}. Ставки у Якоря (−{g.bet})"
            plate = pygame.Rect(0, 0, 480, 44)
            plate.center = (500, 540)
            if not skin.plate(s, "toast", plate):
                rounded(s, (40, 30, 28), plate, 12, 2, skin=None)
            draw_text_fit(s, msg, 18, plate.center, plate.w - 20, RESULT_COLORS[net > 0])
        L = SN_LAYOUT
        x0, y = L["chips_x"], L["chips_y"]
        if g.state == "bet":
            draw_text(s, "Фишка:", 16, (x0 - 60, y), WHITE, anchor="midright")
            for i, v in enumerate(cs.CHIPS):
                x = x0 + i * 38
                rect = pygame.Rect(x - 19, y - 19, 38, 38)
                if v == self.sn_chip:
                    blit_light(s, x, y, 64, (255, 230, 140), 200)
                draw_chip(s, x, y, v, 1.05 if v == self.sn_chip else 0.9)
                self.zone_btn(rect, lambda v=v: setattr(self, "sn_chip", v), 19)
            self.button(L["clear"], "Убрать", self.sn_clear, BTN_BLUE, g.bet > 0, 16)
            self.tip(L["clear"], "Снять фишки с выбранной улитки (если на ней пусто — со всех)")
            ok = g.bet >= sn.MIN_BET
            self.button(L["go"], "Старт!", self.sn_start, BTN_GREEN, ok, 20)
            if g.pick is None:
                line = "Выбери улитку: щёлкни по дорожке"
            else:
                many = sum(1 for b in g.bets if b)
                line = f"Выбрана: {sn.SNAILS[g.pick]['name']}"
                if g.bet:
                    word = "улитки" if many < 5 else "улиток"
                    line += f" · на столе {g.bet}" + (f" ({many} {word})" if many > 1 else "")
            draw_text_fit(s, line, 14, (560, y), 330, (240, 225, 180), outline=None)
        elif g.state == "done":
            self.button(L["go"], "Ещё забег", self.sn_again, BTN_GREEN, True, 20)
            self.tip(L["go"], "Новые шансы, те же ставки на тех же улиток")
        hx, hy = L["history"]
        shown = g.history[1:] if g.state == "race" else g.history      # не подсказываем итог идущего забега
        for n, w in enumerate(shown[:6]):
            pygame.draw.circle(s, OUT, (hx, hy - n * 22), 9)
            pygame.draw.circle(s, sn.SNAILS[w]["shell"], (hx, hy - n * 22), 7)
        if shown:
            draw_text(s, "первые", 12, (hx, hy + 20), (220, 230, 210), outline=None)
        if self.sn_say:
            hint = None if getattr(self.tavern, "sn_intro", False) else \
                f"щёлкни по Якорю — дальше ({self.sn_intro + 1}/{len(SAILOR_INTRO)})"
            draw_side_bubble(s, dx + 80, dy - 170, self.sn_say[0], hint)
