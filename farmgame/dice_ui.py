# -*- coding: utf-8 -*-
"""3.43: экран игры в кости «Больше / меньше / 7» в Игровой. Логика — dice.py.

Ведёт юная драконица Искра (решение пользователя 27.11): хитрая и весёлая, играет ради азарта. Стол — общий стол
Игровой: три поля ставок, кости летят из лап Искры и катятся по сукну. Свои картинки (необязательно):
characters/dragoness (по пояс, низ = край стола), icons/game_dice (значок на карте Игровой). Без них — кодом.
"""
import math
import random

import pygame

from .ui_common import *  # noqa: F401,F403
from .tavern_ui import draw_token
from .casino_ui import draw_chip, chip_for, draw_side_bubble
from . import casino as cs
from . import dice as dc

HOST = (500, 238)                # где Искра: середина низа = край стола
HOST_NAME = "Искра"
ROLL_TIME = 1.35                 # сколько летят и катятся кости, с
AREA_Y, AREA_H = 300, 112        # поля ставок
AREA_RECTS = [pygame.Rect(140, AREA_Y, 232, AREA_H), pygame.Rect(388, AREA_Y, 224, AREA_H),
              pygame.Rect(628, AREA_Y, 232, AREA_H)]
AREA_COLORS = [(70, 120, 160), (175, 120, 50), (160, 80, 80)]
DICE_Y = 478                     # где кости останавливаются
DICE_X = (462, 538)
DC_LAYOUT = dict(chips_y=565, chips_x=150, clear=pygame.Rect(300, 546, 88, 38), go=pygame.Rect(748, 540, 175, 48),
                 history=(70, 300))

HOST_INTRO = [
    "Ой, новенький! Я Искра. Не бойся, я кусаюсь только по праздникам. Сыграем в кости?",
    "Щёлкни по полю — положишь фишку: «Меньше 7», «Ровно 7» или «Больше 7». Можно на несколько полей.",
    "Жми «Бросить!» — я кину две кости. «Меньше» и «больше» платят x2.3, семёрка — x5.7. Хи-хи!",
]
HOST_HELLO = ["Опять ты! Кости уже тёплые — я на них дышала.", "Ставки, ставки! Я сегодня везучая... а ты?",
              "Хи-хи, проиграешь — не плачь: слёзы тушат мой огонь."]
HOST_SAY = {
    "poke": ["Мама говорит, драконам нельзя играть в кости. Поэтому я играю с тобой!",
             "Однажды я выкинула семь семёрок подряд. Ну ладно, три. Ну ладно, одну.",
             "Чешуйки чешутся — к удаче!", "Хочешь, подую на кости? Только они потом горячие.",
             "Дедушка спит на золоте, а я — на жетонах. Мягче!"],
    "roll": ["Лови!", "Бросаю! Фух!", "Хоп — и покатились!"],
    "win": ["Ух ты, повезло! Держи жетоны.", "Нечестно! То есть... поздравляю!", "Хи-хи, ну ты и счастливчик!"],
    "lose": ["Хи-хи, мои!", "Не повезло. Ещё разок?", "Кости любят меня больше. Но ты не сдавайся!"],
    "partial": ["Угадал — но остальные поля мои. Хи-хи!", "Пришло твоё поле, а карман всё равно легче!"],
}
PIPS = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)], 4: [(-1, -1), (1, -1), (-1, 1), (1, 1)],
        5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)], 6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}


def draw_die(s, cx, cy, size, value, tilt=0.0):
    """Игральная кость: скруглённый квадрат с точками. tilt (-1..1) — сплющивается, будто кувыркается."""
    w = size * (1 - 0.35 * abs(tilt))
    h = size
    r = pygame.Rect(0, 0, P(w), P(h))
    r.center = (P(cx), P(cy))
    rounded(s, (250, 246, 236), r, max(4, P(size * 0.18)), 3, skin=None)
    for px, py in PIPS.get(value, []):
        pygame.draw.circle(s, (200, 40, 40) if value == 1 else (40, 32, 30),
                           (P(cx + px * w * 0.27), P(cy + py * h * 0.27)), max(2, P(size * 0.085)))


def draw_dragoness(s, x, wy, k=2.5, t=0.0, talking=False, throw=0.0):
    """Юная драконица Искра по пояс за столом: коралловая чешуя, светлое брюшко, рожки, крылышки, большие глаза.
    throw (0..1) — взмах лапы при броске."""
    if blit_tf(s, "characters/dragoness", x, wy + 2, 1.3 * k / 2.5, angle=math.sin(t * 1.1) * 2):
        return
    u = k / 2.0
    sway = math.sin(t * 1.1) * 2 * u
    breath = math.sin(t * 1.6) * 1.2
    scale, belly, dark = (235, 110, 90), (250, 220, 170), (190, 70, 60)
    for sx in (-1, 1):                                              # крылышки за спиной
        flap = math.sin(t * 3 + sx) * 4 * u
        poly(s, (220, 95, 85), [(x + sx * 30 * u, wy - 66 * u), (x + sx * 64 * u, wy - 104 * u - flap),
                                (x + sx * 60 * u, wy - 80 * u), (x + sx * 70 * u, wy - 70 * u - flap * 0.5),
                                (x + sx * 42 * u, wy - 46 * u)], 3)
    blob(s, scale, [(x + sway * 0.5, wy - 34 * u + breath, 40 * u), (x - 22 * u, wy - 12 * u, 26 * u),
                    (x + 22 * u, wy - 12 * u, 26 * u)], 3)                                  # тело
    pygame.draw.rect(s, scale, (P(x - 44 * u), P(wy - 14 * u), P(88 * u), P(14 * u)))
    ellipse(s, belly, x + sway * 0.6, wy - 26 * u, 46 * u, 50 * u, 2)                   # брюшко
    for dy in (12, 24, 36):
        pygame.draw.line(s, (225, 190, 140), (P(x + sway * 0.6 - 16 * u), P(wy - dy * u)),
                         (P(x + sway * 0.6 + 16 * u), P(wy - dy * u)), max(1, P(1.5 * u)))
    for sx in (-1, 1):                                              # лапки на столе (правая взмахивает при броске)
        lift = 30 * u * math.sin(min(1.0, throw) * math.pi) if sx > 0 else 0
        ellipse(s, scale, x + sx * 42 * u, wy - 10 * u - lift, 22 * u, 30 * u, 2)
        for c in (-6, 0, 6):
            pygame.draw.circle(s, OUT, (P(x + sx * 42 * u + c * u), P(wy + 4 * u - lift)), max(2, P(3.4 * u)))
            pygame.draw.circle(s, (250, 240, 225), (P(x + sx * 42 * u + c * u), P(wy + 4 * u - lift)), max(1, P(2.4 * u)))
    hx, hy = x + sway, wy - 94 * u + breath
    for sx in (-1, 1):                                              # рожки
        poly(s, (250, 230, 190), [(hx + sx * 10 * u, hy - 22 * u), (hx + sx * 22 * u, hy - 46 * u),
                                  (hx + sx * 22 * u, hy - 20 * u)], 2)
    blob(s, scale, [(hx, hy, 26 * u), (hx, hy + 14 * u, 20 * u)], 3)                    # голова и мордочка
    ellipse(s, belly, hx, hy + 16 * u, 30 * u, 18 * u, 0)
    for sx in (-1, 1):                                              # большие глаза с бликом
        ex = hx + sx * 11 * u
        ellipse(s, (255, 255, 255), ex, hy - 4 * u, 14 * u, 17 * u, 2)
        pygame.draw.circle(s, (60, 140, 90), (P(ex + 1 * u), P(hy - 3 * u)), max(2, P(5 * u)))
        pygame.draw.circle(s, OUT, (P(ex + 1 * u), P(hy - 3 * u)), max(1, P(2.6 * u)))
        pygame.draw.circle(s, (255, 255, 255), (P(ex + 3 * u), P(hy - 6 * u)), max(1, P(1.6 * u)))
        pygame.draw.line(s, OUT, (P(ex + sx * 4 * u), P(hy - 12 * u)), (P(ex + sx * 9 * u), P(hy - 16 * u)),
                         max(1, P(1.4 * u)))                       # ресничка
    pygame.draw.circle(s, dark, (P(hx - 5 * u), P(hy + 12 * u)), max(1, P(1.6 * u)))   # ноздри
    pygame.draw.circle(s, dark, (P(hx + 5 * u), P(hy + 12 * u)), max(1, P(1.6 * u)))
    mouth = 3 * u if talking else 0
    pygame.draw.arc(s, OUT, pygame.Rect(P(hx - 9 * u), P(hy + 14 * u - mouth), P(18 * u), P(8 * u + mouth)),
                    math.pi + 0.3, 2 * math.pi - 0.3, max(2, P(2 * u)))
    for sx in (-1, 1):                                              # румянец
        ellipse(s, (255, 150, 140), hx + sx * 19 * u, hy + 8 * u, 8 * u, 5 * u, 0)
    for n in range(2):                                              # искорки из ноздрей, когда смеётся
        if talking:
            a = (t * 2 + n / 2) % 1
            pygame.draw.circle(s, (255, 200, 80), (P(hx + (n * 2 - 1) * 6 * u), P(hy + 6 * u - a * 18 * u)),
                               max(1, P((2.5 - 2 * a) * u)))


class DiceUI:
    def init_dice(self):
        self.dc = dc.DiceGame()
        self.dc_chip = cs.CHIPS[1]
        self.dc_t = -99.0                # когда (t_real) брошены кости
        self.dc_say = None
        self.dc_intro = 0
        self.dc_shown = False
        self.dc_bg = None
        self.dc_tumble = [(1, 1), 0.0]   # что показывать в полёте, когда менять

    def open_dice(self, force=False):
        """force — режим разработчика: глава 5 ещё не открыта, а сыграть хочется."""
        if not force and not dc.unlocked(self.farm.farm_index):
            self.toast("Кости откроются в горной деревне драконов", 3)
            return
        self.view = "dice"
        self.modal = None
        if not getattr(self.tavern, "dc_intro", False):
            self.dc_intro = 0
            self.dc_say = [HOST_INTRO[0], 1e9]
        else:
            self.dc_say = [random.choice(HOST_HELLO), 3.5]

    # ------------------------------------------------------------ действия
    def dc_poke(self):
        if not getattr(self.tavern, "dc_intro", False):
            self.dc_intro += 1
            if self.dc_intro >= len(HOST_INTRO):
                self.tavern.dc_intro = True
                self.dc_say = ["Всё, хватит болтать — ставь!", 2.5]
                self.save()
            else:
                self.dc_say = [HOST_INTRO[self.dc_intro], 1e9]
            return
        self.dc_say = [random.choice(HOST_SAY["poke"]), 4]
        self.sfx.play("hover")

    def dc_rules(self):
        self.tavern.dc_intro = False
        self.dc_intro = 0
        self.dc_say = [HOST_INTRO[0], 1e9]

    def dc_area_click(self, area_id):
        if self.dc.state != "bet":
            return
        if self.dc.add_bet(self.tavern, area_id, self.dc_chip):
            self.sfx.play("feed")
        else:
            self.toast("Не хватает жетонов", 1.5)

    def dc_clear(self):
        self.dc.clear_bet(self.tavern)

    def dc_roll(self):
        g = self.dc
        if g.bet < dc.MIN_BET:
            self.toast(f"Поставь от {dc.MIN_BET} жетонов: щёлкни по полю", 2.5)
            return
        if g.roll(self.tavern):
            self.dc_t, self.dc_shown = self.t_real, False
            self.dc_say = [random.choice(HOST_SAY["roll"]), ROLL_TIME + 0.6]
            self.sfx.play("click")
            self.quest("dice_roll")
            if not getattr(self.tavern, "dc_intro", False):
                self.tavern.dc_intro = True
            self.save()

    def dc_again(self):
        self.dc.next_round(self.tavern, same_bet=True)
        self.dc_shown = False

    def dc_leave(self):
        self.dc.refund(self.tavern)
        self.view = "gameroom"
        self.save()

    def dc_elapsed(self):
        return self.t_real - self.dc_t

    def dice_tick(self, dt):
        if self.dc_say and self.dc_say[1] < 1e8:
            self.dc_say[1] -= dt
            if self.dc_say[1] <= 0:
                self.dc_say = None
        g = self.dc
        if self.view != "dice":
            if g.state == "bet" and g.bet or g.state == "roll":
                g.refund(self.tavern)
                self.dc_shown = True
            return
        if g.state == "roll":
            el = self.dc_elapsed()
            if el < ROLL_TIME and el >= self.dc_tumble[1]:          # в полёте грани мелькают
                self.dc_tumble = [(random.randint(1, 6), random.randint(1, 6)), el + 0.09]
            if el >= ROLL_TIME + 0.35:
                g.finish()
        if g.state == "done" and not self.dc_shown:
            self.dc_shown = True
            w = g.winning_area()
            if g.net() > 0:
                self.quest("dice_win")
                if w == "seven" and g.bets["seven"]:
                    self.quest("dice_seven")
                self.sfx.play("coin_big")
                rect = AREA_RECTS[[a["id"] for a in dc.AREAS].index(w)]
                self.fx.sparks(rect.centerx, rect.centery, n=14, up=70)
                self.dc_say = [random.choice(HOST_SAY["win"]), 4]
            elif g.won():
                self.sfx.play("coin")
                self.dc_say = [random.choice(HOST_SAY["partial"]), 4.5]
            else:
                self.sfx.play("shoo")
                self.dc_say = [random.choice(HOST_SAY["lose"]), 4]

    # ------------------------------------------------------------ рисование
    def dice_positions(self):
        """Где сейчас кости и какой стороной: [(x, y, value, tilt)] или [] (ещё не брошены)."""
        g = self.dc
        if g.state == "bet" or not g.dice:
            return []
        el = self.dc_elapsed()
        out = []
        for n in range(2):
            u = min(1.0, el / ROLL_TIME)
            x0, y0 = HOST[0] + (n * 2 - 1) * 30, HOST[1] - 20
            x1 = DICE_X[n]
            x = x0 + (x1 - x0) * (1 - (1 - u) ** 2)
            # полёт и два затухающих отскока
            base = y0 + (DICE_Y - y0) * min(1.0, u * 1.6)
            hop = 0.0 if u * 1.6 < 1 else abs(math.sin((u * 1.6 - 1) / 0.6 * 2 * math.pi)) * 26 * (1 - u)
            y = base - hop
            rolling = u < 1.0
            v = self.dc_tumble[0][n] if rolling else g.dice[n]
            tilt = math.sin(el * 18 + n) if rolling else 0.0
            out.append((x, y, v, tilt))
        return out

    def draw_dice_view(self):
        s, g, t = self.screen, self.dc, self.t_real
        if self.cs_bg is None:
            self.cs_bg = self.build_casino_background()
        s.blit(self.cs_bg, (0, 0))
        if has_sprite("ui/banner"):
            self.draw_banner((206, 118, 250, 48), "КОСТИ ИСКРЫ", 20)
        else:
            plate = pygame.Rect(206, 120, 250, 44)
            rounded(s, (120, 70, 40), plate, 10, 3)
            draw_text(s, "КОСТИ ИСКРЫ", 20, plate.center, GOLD)
        pb = pygame.Rect(14, 112, 170, 46)
        self.button(pb, "Призы", lambda: self.open_modal("prizes"), (245, 175, 50), True, 19)
        draw_token(s, pb.x + 28, pb.centery, 0.7)
        self.tip(pb, "Призовая стойка: трофеи и украшения за жетоны")
        hx, hy = HOST
        el = self.dc_elapsed()
        throw = el / 0.5 if g.state == "roll" and el < 0.5 else 0.0
        draw_dragoness(s, hx, hy, 2.5, t, self.dc_say is not None and int(t * 6) % 2 == 0, throw)
        zone = pygame.Rect(hx - 80, hy - 230, 160, 230)
        self.zone_btn(zone, self.dc_poke, 12)
        self.tip(zone, f"{HOST_NAME}: щёлкни — поболтает")
        q = pygame.Rect(hx + 100, hy - 44, 32, 32)
        self.button(q, "?", self.dc_rules, BTN_BLUE, True, 16)
        self.tip(q, "Правила ещё раз")
        win = g.winning_area() if g.state == "done" else None
        for a, rect, col in zip(dc.AREAS, AREA_RECTS, AREA_COLORS):
            lit = win == a["id"]
            if lit:
                blit_light(s, rect.centerx, rect.centery, 150, (255, 230, 140), 160)
            rounded(s, tuple(min(255, c + 40) for c in col) if lit else col, rect, 12, 3, skin=None)
            pygame.draw.rect(s, (255, 235, 170) if lit else (235, 220, 190), rect.inflate(-10, -10), 2, border_radius=9)
            draw_text(s, a["name"], 20, (rect.centerx, rect.y + 26), WHITE)
            draw_text(s, a["sub"], 15, (rect.centerx, rect.y + 52), (245, 235, 210), outline=None)
            draw_text(s, f"x{a['k']:g}", 18, (rect.centerx, rect.y + 80), GOLD)
            bet = g.bets[a["id"]]
            if bet:
                draw_chip(s, rect.x + 30, rect.bottom - 26, chip_for(bet), 0.8, str(bet))
                if g.state == "bet":                     # чем кончится, если выпадет это поле
                    net = int(round(bet * a["k"])) - g.bet
                    draw_text(s, f"{net:+d}", 14, (rect.right - 30, rect.bottom - 26),
                              (170, 240, 150) if net > 0 else (255, 190, 170))
            if g.state == "bet" and self.modal is None:
                self.zone(rect, lambda i=a["id"]: self.dc_area_click(i))
                self.tip(rect, f"{a['name']} ({a['sub']}): щёлкни — положить фишку")
        for x, y, v, tilt in self.dice_positions():
            draw_shadow(s, x, DICE_Y + 24, 48, 10, 70)
            draw_die(s, x, y, 46, v, tilt)
        if g.state == "done":
            tot, net = g.total(), g.net()
            if net > 0:
                msg = f"Выпало {tot}! +{net} чистыми (выплата {g.paid} за {g.bet})"
            elif g.won() and net == 0:
                msg = f"Выпало {tot}. Выплата {g.paid} — ровно в ноль"
            elif g.won():
                msg = f"Выпало {tot}. Вернулось {g.paid} из {g.bet} ({net})"
            else:
                msg = f"Выпало {tot}. Ставки у Искры (−{g.bet})"
            plate = pygame.Rect(0, 0, 480, 44)
            plate.center = (500, 540)
            if not skin.plate(s, "toast", plate):
                rounded(s, (40, 30, 28), plate, 12, 2, skin=None)
            draw_text_fit(s, msg, 18, plate.center, plate.w - 20, (255, 220, 90) if net > 0 else (230, 200, 190))
        L = DC_LAYOUT
        x0, y = L["chips_x"], L["chips_y"]
        if g.state == "bet":
            draw_text(s, "Фишка:", 16, (x0 - 60, y), WHITE, anchor="midright")
            for i, v in enumerate(cs.CHIPS):
                x = x0 + i * 38
                rect = pygame.Rect(x - 19, y - 19, 38, 38)
                if v == self.dc_chip:
                    blit_light(s, x, y, 64, (255, 230, 140), 200)
                draw_chip(s, x, y, v, 1.05 if v == self.dc_chip else 0.9)
                self.zone_btn(rect, lambda v=v: setattr(self, "dc_chip", v), 19)
            self.button(L["clear"], "Убрать", self.dc_clear, BTN_BLUE, g.bet > 0, 16)
            self.tip(L["clear"], "Снять все фишки со стола")
            self.button(L["go"], "Бросить!", self.dc_roll, BTN_GREEN, g.bet >= dc.MIN_BET, 20)
            line = f"На столе {g.bet} (от {dc.MIN_BET})" if g.bet else "Щёлкни по полю — положишь фишку"
            draw_text_fit(s, line, 14, (560, y), 330, (240, 225, 180), outline=None)
        elif g.state == "done":
            self.button(L["go"], "Ещё бросок", self.dc_again, BTN_GREEN, True, 20)
            self.tip(L["go"], "Те же ставки на те же поля")
        hx2, hy2 = L["history"]
        shown = g.history[1:] if g.state == "roll" else g.history     # не подсказываем итог броска в полёте
        for n, tot in enumerate(shown[:8]):
            r = pygame.Rect(0, 0, 36, 24)
            r.center = (hx2, hy2 + n * 28)
            col = AREA_COLORS[0] if tot < 7 else AREA_COLORS[1] if tot == 7 else AREA_COLORS[2]
            rounded(s, col, r, 7, 2, skin=None)
            draw_text(s, str(tot), 14, r.center, WHITE)
        if shown:
            draw_text(s, "было", 12, (hx2, hy2 - 22), (220, 230, 210), outline=None)
        if self.dc_say:
            hint = None if getattr(self.tavern, "dc_intro", False) else \
                f"щёлкни по Искре — дальше ({self.dc_intro + 1}/{len(HOST_INTRO)})"
            draw_side_bubble(s, hx + 80, hy - 170, self.dc_say[0], hint)
