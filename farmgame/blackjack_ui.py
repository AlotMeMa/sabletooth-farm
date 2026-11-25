# -*- coding: utf-8 -*-
"""3.28: экран блэкджека в Игровой. Логика — blackjack.py.

Дилер — рыжий гном Ворчун (решение пользователя 25.11: «бормотун, вечно недовольный»). Стол — свой фон
backgrounds/blackjack или стол рулетки кодом. Карты: свои картинки props/card_back, props/card_face (пустое лицо),
icons/suit_* и props/card_shoe (лист icons/cards_sheet) или кодом. Дилер: characters/dealer_gnome (по пояс, низ =
край стола) или кодом. Цифры и масти на картах всегда рисует игра.
"""
import math
import random

import pygame

from .ui_common import *  # noqa: F401,F403
from .tavern_ui import draw_token
from .casino_ui import draw_chip, chip_for, draw_side_bubble
from . import casino as cs
from . import blackjack as bj

BJ = dict(dealer=(500, 238), dealer_k=2.5, shoe=(812, 258),
          dealer_cards=(500, 318), player_cards=(500, 476), card_w=66, card_h=94, gap=44,
          chips_y=565, chips_x=150, bet=(500, 404),
          deal=pygame.Rect(748, 540, 175, 48), hit=pygame.Rect(608, 540, 150, 48), stand=pygame.Rect(768, 540, 155, 48),
          clear=pygame.Rect(300, 546, 88, 38), msg=(500, 404))
# 3.28.2: раскладка под нарисованный стол пользователя backgrounds/blackjack (полукруг, лоток и башмак на картинке):
# карты дилера — на прямоугольнике, ставка — в средней дуге игрока, карты игрока — над ней, Ворчун — за лотком
BJ_PAINTED = dict(dealer=(500, 232), shoe=None, dealer_cards=(500, 336), player_cards=(500, 450), bet=(500, 508),
                  result=(500, 574), side_bet=(612, 508), chips_y=560, chips_x=262,
                  clear=pygame.Rect(236, 580, 88, 32), rules=(175, 292), history=(112, 500))
BJ_CODE = dict(shoe=(812, 258), result=(500, 404), side_bet=(720, 404), rules=None, history=(70, 470))
CARD_STEP = 0.32          # через сколько секунд выкладывается следующая карта
DEALER_NAME = "Ворчун"
DEALER_INTRO = [
    "Ну, чего уставился? Я Ворчун, тут я раздаю. Правила простые — даже ты поймёшь.",
    "Набери больше меня, но не больше 21. Картинки — по 10, туз — 1 или 11. Перебрал — жетоны мои.",
    "«Взять» — ещё карта, «Хватит» — мой ход. Я беру, пока меньше 17. Выиграл — плачу вдвое, "
    "очко с раздачи — в два с половиной. Всё, ставь давай.",
]
DEALER_HELLO = ["Опять ты... Ну садись, раз пришёл.", "Ставь давай, у меня борода стынет.",
                "Карты не трогать! Я сам раздаю.", "Ходят тут всякие... Ставку клади."]
DEALER_SAY = {
    "win": ["Хм. Повезло. Не привыкай.", "Тьфу ты! Колода сегодня против меня.", "Забирай. И не ухмыляйся."],
    "blackjack": ["Очко?! С раздачи?! Да кто так играет...", "Ну конечно, очко. Как же иначе. Бр-р-р."],
    "lose": ["Ха! А я говорил.", "Жетончики — к Ворчуну. Всё по-честному.", "Не твой день. И не твоя ночь."],
    "bust": ["Перебор! Жадность — плохая советчица.", "Двадцать два, двадцать три... Считать учись!"],
    "push": ["Ничья. Скукота.", "Ни нашим, ни вашим. Тьфу."],
    "poke": ["Не тычь в меня пальцем!", "Я на работе. Ставь или уходи.", "Чего надо? Борода не для потрогать.",
             "В молодости я раздавал самому королю. Он тоже проигрывал."],
}
RESULT_TEXT = {"win": ("Ты выиграл! +{p}", (140, 230, 120)), "blackjack": ("Очко! +{p}", (255, 220, 90)),
               "push": ("Ничья — ставка назад", (235, 225, 200)), "lose": ("Дилер выиграл", (240, 150, 140)),
               "bust": ("Перебор!", (240, 150, 140))}


def draw_suit(s, suit, x, y, k=1.0):
    """Масть: картинка icons/suit_<масть> или кодом (символы ♥♠ есть не во всех шрифтах)."""
    if blit_sprite(s, f"icons/suit_{suit}", x, y, 0.5 * k, "center"):
        return
    col = (200, 40, 50) if suit in bj.RED_SUITS else (40, 34, 36)
    r = 6 * k
    if suit == "diamonds":
        poly(s, col, [(x, y - r * 1.5), (x + r, y), (x, y + r * 1.5), (x - r, y)], 0)
    elif suit == "hearts":
        pygame.draw.circle(s, col, (P(x - r * 0.55), P(y - r * 0.3)), max(1, P(r * 0.62)))
        pygame.draw.circle(s, col, (P(x + r * 0.55), P(y - r * 0.3)), max(1, P(r * 0.62)))
        poly(s, col, [(x - r * 1.15, y - r * 0.1), (x + r * 1.15, y - r * 0.1), (x, y + r * 1.3)], 0)
    elif suit == "spades":
        pygame.draw.circle(s, col, (P(x - r * 0.55), P(y + r * 0.2)), max(1, P(r * 0.62)))
        pygame.draw.circle(s, col, (P(x + r * 0.55), P(y + r * 0.2)), max(1, P(r * 0.62)))
        poly(s, col, [(x - r * 1.15, y + r * 0.05), (x + r * 1.15, y + r * 0.05), (x, y - r * 1.3)], 0)
        poly(s, col, [(x, y + r * 0.3), (x - r * 0.5, y + r * 1.3), (x + r * 0.5, y + r * 1.3)], 0)
    else:   # clubs
        for dx, dy in ((0, -0.55), (-0.62, 0.2), (0.62, 0.2)):
            pygame.draw.circle(s, col, (P(x + dx * r), P(y + dy * r)), max(1, P(r * 0.55)))
        poly(s, col, [(x, y + r * 0.2), (x - r * 0.5, y + r * 1.3), (x + r * 0.5, y + r * 1.3)], 0)


def draw_card(s, x, y, card, face_up=True, k=1.0, back="props/card_back"):
    """Карта с центром (x, y): лицо (ранг и масть рисует игра) или рубашка."""
    w, h = BJ["card_w"] * k, BJ["card_h"] * k
    rect = pygame.Rect(0, 0, P(w), P(h))
    rect.center = (P(x), P(y))
    draw_shadow(s, x + 3, rect.bottom, w * 0.9, 10, 60)
    if not face_up:
        if not blit_sprite(s, back, x, y, w / 84, "center"):
            rounded(s, (170, 45, 50), rect, max(4, P(7 * k)), 2, skin=None)
            rounded(s, (205, 80, 70), rect.inflate(-P(10 * k), -P(10 * k)), max(3, P(5 * k)), 2, (240, 200, 120), skin=None)
            pygame.draw.circle(s, (240, 200, 120), rect.center, max(3, P(10 * k)), 2)
        return rect
    if not blit_sprite(s, "props/card_face", x, y, w / 84, "center"):
        rounded(s, (252, 248, 238), rect, max(4, P(7 * k)), 2, skin=None)
    rank, suit = card
    col = (200, 40, 50) if suit in bj.RED_SUITS else (40, 34, 36)
    draw_text(s, rank, max(10, P(17 * k)), (rect.x + P(13 * k), rect.y + P(14 * k)), col, outline=None)
    draw_suit(s, suit, rect.x + P(13 * k), rect.y + P(32 * k), 0.75 * k)
    draw_suit(s, suit, rect.centerx + P(4 * k), rect.centery + P(8 * k), 2.0 * k)
    return rect


def draw_dealer_gnome(s, x, wy, k=2.0, t=0.0, talking=False, grumpy=0.0):
    """Рыжий гном-дилер по пояс за столом: зелёный колпак, жилет с бабочкой, нахмуренные брови."""
    if blit_tf(s, "characters/dealer_gnome", x, wy + 2, 1.3 * k / 2.5, angle=math.sin(t * 1.1) * 1.0):
        return
    breath = math.sin(t * 1.6) * 1.2
    u = k / 2.0
    # плечи и жилет
    poly(s, (110, 40, 40), [(x - 52 * u, wy), (x + 52 * u, wy), (x + 40 * u, wy - 62 * u + breath),
                            (x - 40 * u, wy - 62 * u + breath)], 3)
    poly(s, (245, 240, 230), [(x - 12 * u, wy - 62 * u + breath), (x + 12 * u, wy - 62 * u + breath), (x, wy - 20 * u)], 2)
    bx, by = x, wy - 58 * u + breath
    poly(s, (40, 40, 46), [(bx, by), (bx - 9 * u, by - 5 * u), (bx - 9 * u, by + 5 * u)], 2)
    poly(s, (40, 40, 46), [(bx, by), (bx + 9 * u, by - 5 * u), (bx + 9 * u, by + 5 * u)], 2)
    for sx in (-1, 1):                                              # руки на столе
        ellipse(s, (110, 40, 40), x + sx * 46 * u, wy - 10 * u, 26 * u, 34 * u, 2)
        pygame.draw.circle(s, OUT, (P(x + sx * 46 * u), P(wy + 6 * u)), P(9 * u) + 2)
        pygame.draw.circle(s, (240, 195, 160), (P(x + sx * 46 * u), P(wy + 6 * u)), P(9 * u))
    # голова и рыжая борода
    hy = wy - 92 * u + breath
    blob(s, (215, 105, 40), [(x, hy + 30 * u, 26 * u), (x - 18 * u, hy + 20 * u, 18 * u), (x + 18 * u, hy + 20 * u, 18 * u),
                            (x, hy + 46 * u, 16 * u)], 3)
    blob(s, (240, 195, 160), [(x, hy, 22 * u)], 3)
    pygame.draw.circle(s, (225, 140, 120), (P(x), P(hy + 6 * u)), P(7 * u))          # нос картошкой
    for sx in (-1, 1):                                               # глаза и нахмуренные брови
        ex = x + sx * 9 * u
        pygame.draw.circle(s, OUT, (P(ex), P(hy - 3 * u)), max(1, P(2.4 * u)))
        dy = (2 + 2 * grumpy) * u
        pygame.draw.line(s, (180, 80, 30), (P(ex - sx * 7 * u), P(hy - 12 * u - dy)), (P(ex + sx * 6 * u), P(hy - 8 * u)),
                         max(2, P(3.2 * u)))
    mouth = 3 * u if talking else 0
    pygame.draw.arc(s, OUT, pygame.Rect(P(x - 8 * u), P(hy + 14 * u - mouth), P(16 * u), P(8 * u + mouth)),
                    0.3, math.pi - 0.3, max(2, P(2 * u)))                  # уголки вниз — недоволен
    # колпак
    poly(s, (50, 110, 60), [(x - 26 * u, hy - 12 * u), (x + 26 * u, hy - 12 * u), (x + 14 * u, hy - 66 * u)], 3)
    pygame.draw.circle(s, (240, 200, 90), (P(x + 14 * u), P(hy - 68 * u)), max(3, P(5 * u)))
    rounded(s, (35, 80, 45), (P(x - 28 * u), P(hy - 18 * u), P(56 * u), P(10 * u)), max(2, P(4 * u)), 2, skin=None)


def draw_shoe(s, x, y, k=1.0):
    if blit_sprite(s, "props/card_shoe", x, y, 0.8 * k, "midbottom"):
        return
    poly(s, (110, 64, 36), [(x - 50 * k, y), (x + 40 * k, y), (x + 50 * k, y - 34 * k), (x - 34 * k, y - 50 * k)], 3)
    draw_card(s, x - 26 * k, y - 46 * k, None, False, 0.45 * k)


def bj_layout():
    """Раскладка стола: под свою картинку backgrounds/blackjack или под стол, нарисованный кодом."""
    return dict(BJ, **(BJ_PAINTED if has_sprite("backgrounds/blackjack") else BJ_CODE))


class BlackjackUI:
    def init_blackjack(self):
        self.bj = bj.Blackjack()
        self.bj_chip = cs.CHIPS[1]
        self.bj_t = 0.0                  # время начала показа текущей раздачи
        self.bj_say = None               # [текст, секунд] — облачко Ворчуна
        self.bj_intro = 0
        self.bj_shown_res = None         # какой итог уже объявлен (звук, облачко)

    def open_blackjack(self):
        if not bj.unlocked(self.farm.farm_index):
            self.toast("Блэкджек откроется зимой — на главе «Зимнее поле»", 3)
            return
        self.view = "blackjack"
        self.modal = None
        if not getattr(self.tavern, "bj_intro", False):
            self.bj_intro = 0
            self.bj_say = [DEALER_INTRO[0], 1e9]
        else:
            self.bj_say = [random.choice(DEALER_HELLO), 3.5]

    # ------------------------------------------------------------ действия
    def bj_poke(self):
        if not getattr(self.tavern, "bj_intro", False):
            self.bj_intro += 1
            if self.bj_intro >= len(DEALER_INTRO):
                self.tavern.bj_intro = True
                self.bj_say = ["Всё. Хватит болтать — ставь.", 2.5]
                self.save()
            else:
                self.bj_say = [DEALER_INTRO[self.bj_intro], 1e9]
            return
        self.bj_say = [random.choice(DEALER_SAY["poke"]), 3]
        self.sfx.play("hover")

    def bj_rules(self):
        self.tavern.bj_intro = False
        self.bj_intro = 0
        self.bj_say = [DEALER_INTRO[0], 1e9]

    def bj_place(self):
        if self.bj.add_bet(self.tavern, self.bj_chip):
            self.sfx.play("feed")
        else:
            self.toast("Не хватает жетонов", 1.5)

    def bj_clear(self):
        self.bj.clear_bet(self.tavern)

    def bj_deal(self):
        if self.bj.bet < bj.MIN_BET:
            self.toast(f"Ставка — от {bj.MIN_BET} жетонов: щёлкни по фишке, потом по кругу ставки", 2.5)
            return
        if self.bj.deal(self.tavern):
            self.bj_t, self.bj_shown_res = self.t_real, None
            self.sfx.play("click")
            if not getattr(self.tavern, "bj_intro", False):        # начал играть — правила понятны
                self.tavern.bj_intro = True
            self.bj_say = None
            self.save()

    def bj_hit(self):
        self.bj_act(lambda: self.bj.hit(self.tavern))
        self.sfx.play("click")
        if self.bj.state == "done":
            self.save()

    def bj_stand(self):
        self.bj_act(lambda: self.bj.stand(self.tavern))
        self.save()

    def bj_again(self):
        self.bj.next_round(self.tavern, same_bet=True)
        self.bj_shown_res = None

    def bj_leave(self):
        """Ушли из-за стола: раздача доигрывается «Хватит», несыгранная ставка — назад."""
        self.bj.refund(self.tavern)
        self.view = "gameroom"
        self.save()

    # ------------------------------------------------------------ показ карт по одной
    def bj_order(self):
        """Порядок выкладки: игрок, дилер, игрок, дилер, добор игрока; после итога — вскрытие и добор дилера."""
        g = self.bj
        if not (g.player or g.dealer):
            return []
        order = [("p", 0), ("d", 0), ("p", 1), ("d", 1)] + [("p", i) for i in range(2, len(g.player))]
        if g.state == "done":
            order += [("reveal", 0)] + [("d", i) for i in range(2, len(g.dealer))]
        return order

    def bj_steps(self):
        return int((self.t_real - self.bj_t) / CARD_STEP) + 1

    def bj_counts(self):
        """Сколько карт игрока и дилера уже лежит на столе и открыта ли вторая карта дилера."""
        shown = self.bj_order()[:self.bj_steps()]
        return (sum(1 for w, _ in shown if w == "p"), sum(1 for w, _ in shown if w == "d"),
                any(w == "reveal" for w, _ in shown))

    def bj_busy(self):
        order = self.bj_order()
        return bool(order) and self.bj_steps() < len(order)

    def bj_act(self, action):
        """«Взять»/«Хватит»: новые карты выкладываются по одной после уже лежащих (а не все сразу)."""
        if self.bj_busy():
            return
        before = len(self.bj_order())
        action()
        self.bj_t = self.t_real - (before - 1) * CARD_STEP

    def blackjack_tick(self, dt):
        if self.bj_say and self.bj_say[1] < 1e8:
            self.bj_say[1] -= dt
            if self.bj_say[1] <= 0:
                self.bj_say = None
        if self.view != "blackjack":
            if self.bj.state in ("bet", "player") and (self.bj.bet or self.bj.player):
                self.bj.refund(self.tavern)            # ушли (Esc, переезд) — без потерь
            return
        g = self.bj
        if g.state == "done" and self.bj_shown_res is None and not self.bj_busy():
            self.bj_shown_res = g.result
            self.bj_say = [random.choice(DEALER_SAY[g.result]), 3.5]
            if g.result in ("win", "blackjack"):
                self.sfx.play("coin_big" if g.result == "blackjack" else "coin")
                self.fx.sparks(500, bj_layout()["player_cards"][1] - 40, n=16 if g.result == "blackjack" else 9, up=70)
            elif g.result in ("lose", "bust"):
                self.sfx.play("shoo")

    # ------------------------------------------------------------ рисование
    def draw_blackjack_view(self):
        s, g, t = self.screen, self.bj, self.t_real
        L = bj_layout()
        if getattr(self, "bj_bg", None) is None:
            self.bj_bg = self.build_blackjack_background()
        s.blit(self.bj_bg, (0, 0))
        if has_sprite("ui/banner"):            # лента слева, как «РУЛЕТКА» (над головой Ворчуна — колпак)
            self.draw_banner((24, 118, 220, 48), "БЛЭКДЖЕК", 22)
        else:
            plate = pygame.Rect(30, 120, 200, 44)
            rounded(s, (120, 70, 40), plate, 10, 3)
            draw_text(s, "БЛЭКДЖЕК", 22, plate.center, GOLD)
        np_, nd, reveal = self.bj_counts()
        grumpy = 1.0 if self.bj_shown_res in ("win", "blackjack") else 0.4
        talking = self.bj_say is not None and int(t * 6) % 2 == 0
        dx, dy = L["dealer"]
        draw_dealer_gnome(s, dx, dy, L["dealer_k"], t, talking, grumpy)
        zone = pygame.Rect(dx - 80, dy - 230, 160, 230)
        self.zone_btn(zone, self.bj_poke, 12)
        self.tip(zone, f"{DEALER_NAME}: щёлкни — проворчит что-нибудь")
        q = pygame.Rect(dx + 100, dy - 44, 32, 32)
        self.button(q, "?", self.bj_rules, BTN_BLUE, True, 16)
        self.tip(q, "Правила ещё раз")
        if L["shoe"]:
            draw_shoe(s, *L["shoe"])
        # карты дилера и игрока
        self.bj_draw_hand(s, g.dealer[:nd], L["dealer_cards"], hide_second=not reveal, t=t)
        self.bj_draw_hand(s, g.player[:np_], L["player_cards"], t=t)
        if g.dealer[:nd]:
            val = bj.hand_value(g.dealer[:nd]) if reveal else bj.card_value(g.dealer[0])
            self.bj_value_tag(s, L["dealer_cards"], val, nd, not reveal)
        if g.player[:np_]:
            self.bj_value_tag(s, L["player_cards"], bj.hand_value(g.player[:np_]), np_)
        # ставка — круг посередине стола
        bx, by = L["bet"]
        busy = self.bj_busy()
        if g.state == "bet":
            rr = 36 if L["shoe"] is None else 44     # на своём столе — в дуге игрока, кольцо поменьше
            ring = pygame.Rect(bx - rr, by - rr, 2 * rr, 2 * rr)
            pygame.draw.circle(s, (240, 210, 130), (bx, by), rr, 3)
            if g.bet:
                draw_chip(s, bx, by, chip_for(g.bet), 1.25, str(g.bet))
            else:
                draw_text(s, "ставка", 15, (bx, by - 8), (240, 225, 180), outline=None)
                draw_text(s, f"от {bj.MIN_BET}", 14, (bx, by + 10), (240, 225, 180), outline=None)
            self.zone_btn(ring, self.bj_place, 44)
            self.tip(ring, "Щёлкни — поставить выбранную фишку")
        elif g.bet:
            draw_chip(s, *L["side_bet"], chip_for(g.bet), 1.0, str(g.bet))
        # итог
        if g.state == "done" and not busy:
            text, col = RESULT_TEXT[g.result]
            msg = text.format(p=g.paid - g.bet if g.result in ("win", "blackjack") else g.paid)
            plate = pygame.Rect(0, 0, 300, 44)
            plate.center = L["result"]
            if not skin.plate(s, "toast", plate):
                rounded(s, (40, 30, 28), plate, 12, 2, skin=None)
            draw_text(s, msg, 20, plate.center, col)
        # фишки
        x0, y = L["chips_x"], L["chips_y"]
        if g.state == "bet":
            draw_text(s, "Фишка:", 16, (x0 - 60, y), WHITE, anchor="midright")
            for i, v in enumerate(cs.CHIPS):
                x = x0 + i * 38
                rect = pygame.Rect(x - 19, y - 19, 38, 38)
                if v == self.bj_chip:
                    blit_light(s, x, y, 64, (255, 230, 140), 200)
                draw_chip(s, x, y, v, 1.05 if v == self.bj_chip else 0.9)
                self.zone_btn(rect, lambda v=v: setattr(self, "bj_chip", v), 19)
            self.button(L["clear"], "Убрать", self.bj_clear, BTN_BLUE, g.bet > 0, 16)
            self.button(L["deal"], "Раздать", self.bj_deal, BTN_GREEN, g.bet >= bj.MIN_BET, 20)
        elif g.state == "player":
            self.button(L["hit"], "Взять", self.bj_hit, BTN_GREEN, not busy, 20)
            self.button(L["stand"], "Хватит", self.bj_stand, (245, 175, 50), not busy, 20)
        elif not busy:
            self.button(L["deal"], "Ещё раз", self.bj_again, BTN_GREEN, True, 20)
            self.tip(L["deal"], "Новая раздача с той же ставкой")
        # последние итоги
        if L["rules"]:                           # на своём фоне правила пишет игра (на столе кодом — в самом фоне)
            for n, line in enumerate(("Дилер берёт до 17", "Выигрыш — 1 к 1", "Очко с раздачи — 3 к 2")):
                draw_text(s, line, 13, (L["rules"][0], L["rules"][1] + n * 19), (235, 205, 120), outline=None)
        hx, hy = L["history"]
        for i, r in enumerate(g.history[:6 if L["shoe"] is None else 8]):
            col = {"win": (110, 200, 90), "blackjack": (255, 205, 60), "push": (200, 190, 170)}.get(r, (200, 80, 70))
            pygame.draw.circle(s, OUT, (hx, hy - i * 22), 9)
            pygame.draw.circle(s, col, (hx, hy - i * 22), 7)
        if g.history:
            draw_text(s, "итоги", 12, (hx, hy + 20), (220, 230, 210), outline=None)
        if self.bj_say:
            hint = None if getattr(self.tavern, "bj_intro", False) else \
                f"щёлкни по {DEALER_NAME}у — дальше ({self.bj_intro + 1}/{len(DEALER_INTRO)})"
            draw_side_bubble(s, dx + 80, dy - 170, self.bj_say[0], hint)

    def bj_draw_hand(self, s, cards, center, hide_second=False, t=0.0):
        cx, cy = center
        n = len(cards)
        x0 = cx - (n - 1) * BJ["gap"] / 2
        for i, c in enumerate(cards):
            face = not (hide_second and i == 1)
            draw_card(s, x0 + i * BJ["gap"], cy, c, face, 1.0)

    def bj_value_tag(self, s, center, value, n, partial=False):
        cx, cy = center
        x = cx - (n - 1) * BJ["gap"] / 2 - BJ["card_w"] / 2 - 26
        txt = f"{value}+" if partial else str(value)
        col = (240, 120, 110) if value > 21 else ((255, 215, 90) if value == 21 else WHITE)
        pygame.draw.circle(s, OUT, (P(x), P(cy)), 20)
        pygame.draw.circle(s, (40, 70, 50), (P(x), P(cy)), 18)
        draw_text(s, txt, 16, (P(x), P(cy)), col)

    def build_blackjack_background(self):
        """Свой фон backgrounds/blackjack или стол рулетки, только сукно без разметки."""
        bg = hd.Surface((W, H))
        if blit_sprite(bg, "backgrounds/blackjack", 0, 0, 1, "topleft"):
            return bg
        if self.cs_bg is None:
            self.cs_bg = self.build_casino_background()
        bg.blit(self.cs_bg, (0, 0))
        felt = pygame.Rect(76, 239, 857, 348)
        for x0, x1 in ((340, 660),):                                 # дуга для карт игрока
            pygame.draw.arc(bg, (235, 205, 120), pygame.Rect(x0 - 60, 400, x1 - x0 + 120, 170), math.pi, 2 * math.pi, 2)
        pygame.draw.rect(bg, (235, 205, 120), pygame.Rect(390, 262, 220, 112), 2, border_radius=10)
        for n, line in enumerate(("Дилер берёт до 17", "Выигрыш — 1 к 1", "Очко с раздачи — 3 к 2")):
            draw_text(bg, line, 14, (210, 300 + n * 22), (235, 205, 120), outline=None)
        return bg
