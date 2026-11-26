# -*- coding: utf-8 -*-
"""3.40: скачки улиток в Игровой — вместо «???». Без графики — экран в snails_ui.py.

Решения пользователя 26.11: в Игровой, открываются в Рыбацкой деревне, ставка жетонами, «ставка и смотрим»:
5 улиток с разными шансами и коэффициентами, гонка идёт сама. Ведёт моряк Старый Якорь (седой, одноглазый,
травит байки про море; пьющий и азартный).

Правила:
- перед каждым забегом у улиток своя «форма» — шансы и коэффициенты на табло (коэффициент = выплата вместе со
  ставкой; около 95% возврата в среднем, как в рулетке);
- ставка жетонами (от MIN_BET) на одну улитку; победила она — ставка x коэффициент, иначе ставка у Якоря;
- итог решается в момент старта (честный розыгрыш по шансам), гонка на экране показывает его: каждая улитка
  ползёт рывками, с остановками, обгонами и финиширует в свой срок.
"""
import math
import random

MIN_BET = 5
RTP = 0.95                       # сколько в среднем возвращается со ставок
UNLOCK_FARM = "fishing"          # открываются в Рыбацкой деревне
RACE_TIME = (9.0, 11.5)          # за сколько секунд финиширует победитель
FINISH_GAP = (0.35, 1.4)         # отставание следующих на финише, с
SEGMENTS = 9                     # из стольких «рывков» состоит забег улитки
FORCE_NEXT = None                # режим разработчика: True — следующий забег выигрывает ставка, False — проигрывает

SNAILS = [   # имя, цвет раковины, цвет тела, базовая резвость
    dict(name="Молния", shell=(230, 190, 60), body=(235, 215, 170), base=1.6),
    dict(name="Ракушка", shell=(220, 120, 140), body=(240, 210, 200), base=1.25),
    dict(name="Тихоня", shell=(120, 170, 110), body=(220, 225, 180), base=1.0),
    dict(name="Слизень Вася", shell=(110, 150, 210), body=(200, 215, 225), base=0.8),
    dict(name="Бабушка Улита", shell=(160, 110, 80), body=(215, 200, 170), base=0.55),
]


def unlocked(farm_index):
    from .config import FARMS
    idx = next((n for n, fm in enumerate(FARMS) if fm["id"] == UNLOCK_FARM), len(FARMS))
    return farm_index >= idx


def make_odds(rng=random):
    """Шансы и коэффициенты на один забег: базовая резвость x случайная форма 0.6–1.5."""
    forms = [rng.uniform(0.6, 1.5) for _ in SNAILS]
    w = [sn["base"] * fm for sn, fm in zip(SNAILS, forms)]
    total = sum(w)
    out = []
    for p_raw, fm in zip(w, forms):
        p = p_raw / total
        k = max(1.2, math.floor(RTP / p * 10) / 10)
        mood = "в ударе" if fm > 1.3 else ("сонная" if fm < 0.75 else "")
        out.append(dict(p=p, k=k, mood=mood))
    return out


def finish_order(odds, rng=random):
    """Порядок на финише: по очереди тянем улиток с весами-шансами (первая — победитель)."""
    left = list(range(len(odds)))
    order = []
    while left:
        ws = [odds[i]["p"] for i in left]
        r = rng.random() * sum(ws)
        for i, wv in zip(left, ws):
            r -= wv
            if r <= 0:
                break
        order.append(i)
        left.remove(i)
    return order


class SnailRace:
    """state: bet (ставим) → race (бегут; итог уже известен и выплачен) → done (итог показан)."""

    def __init__(self, rng=random):
        self.state = "bet"
        self.odds = make_odds(rng)
        self.pick = None           # на кого ставка (номер улитки)
        self.bet = 0               # жетоны на столе (уже сняты с игрока)
        self.order = []            # порядок на финише
        self.times = []            # время финиша каждой улитки (по номеру), с
        self.legs = []             # для каждой улитки — доли пути на каждом «рывке» (сумма 1)
        self.paid = 0              # сколько вернулось игроку (со ставкой)
        self.history = []          # последние победители (номера)

    # ---------- ставки ----------
    def select(self, i):
        if self.state == "bet" and 0 <= i < len(SNAILS):
            self.pick = i
            return True
        return False

    def add_bet(self, tavern, amount):
        if self.state != "bet" or amount <= 0 or tavern.tokens < amount:
            return False
        tavern.tokens -= amount
        self.bet += amount
        return True

    def clear_bet(self, tavern):
        if self.state != "bet":
            return
        tavern.tokens += self.bet
        self.bet = 0

    # ---------- забег ----------
    def start(self, tavern, rng=random):
        """Старт. False — нет ставки от MIN_BET или не выбрана улитка. Итог решается и выплачивается сразу."""
        if self.state != "bet" or self.bet < MIN_BET or self.pick is None:
            return False
        global FORCE_NEXT
        self.order = finish_order(self.odds, rng)
        if FORCE_NEXT is not None:            # режим разработчика: выбранная улитка первая / не первая
            rest = [i for i in self.order if i != self.pick]
            self.order = [self.pick] + rest if FORCE_NEXT else rest[:1] + [self.pick] + rest[1:]
            FORCE_NEXT = None
        t = rng.uniform(*RACE_TIME)
        self.times = [0.0] * len(SNAILS)
        for place, i in enumerate(self.order):
            self.times[i] = t
            t += rng.uniform(*FINISH_GAP)
        self.legs = []
        for _ in SNAILS:                      # рывки: то ползёт, то замирает, то спешит
            sp = [rng.choice((0.15, rng.uniform(0.4, 1.0), rng.uniform(0.9, 1.8))) for _ in range(SEGMENTS)]
            total = sum(sp)
            self.legs.append([v / total for v in sp])
        win = self.order[0] == self.pick
        self.paid = int(round(self.bet * self.odds[self.pick]["k"])) if win else 0
        tavern.tokens += self.paid
        self.state = "race"
        self.history = [self.order[0]] + self.history[:9]
        return True

    def winner(self):
        return self.order[0] if self.order else None

    def won(self):
        return bool(self.order) and self.order[0] == self.pick

    def progress(self, i, t):
        """Доля пути улитки i через t секунд после старта (0..1): рывки разной скорости, финиш ровно в свой срок."""
        if self.state == "bet" or not self.times:
            return 0.0
        T = self.times[i]
        if t >= T:
            return 1.0
        u = max(0.0, t / T) * SEGMENTS
        n = int(u)
        legs = self.legs[i]
        return min(1.0, sum(legs[:n]) + legs[n] * (u - n))

    def race_length(self):
        return max(self.times) if self.times else 0.0

    def first_time(self):
        """Когда доползает победитель: тогда и объявляем итог (остальные доползают уже после)."""
        return min(self.times) if self.times else 0.0

    def finish(self):
        if self.state == "race":
            self.state = "done"

    def next_round(self, tavern, same_bet=True, rng=random):
        """После итога: новые шансы, ставка на ту же улитку (если хватает жетонов)."""
        if self.state != "done":
            return False
        last = self.bet
        self.state, self.bet, self.paid = "bet", 0, 0
        self.order, self.times, self.legs = [], [], []
        self.odds = make_odds(rng)
        if same_bet and last and tavern.tokens >= last:
            self.add_bet(tavern, last)
        return True

    def refund(self, tavern):
        """Ушли от дорожки: несыгранная ставка — назад; идущий забег уже решён и оплачен."""
        if self.state == "bet":
            self.clear_bet(tavern)
        elif self.state == "race":
            self.finish()
