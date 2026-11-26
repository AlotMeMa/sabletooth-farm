# -*- coding: utf-8 -*-
"""3.43: игра в кости «Больше / меньше / 7» в Игровой (решения пользователя 27.11). Без pygame.

Две кости. Ставишь жетоны на одно или несколько полей: «Меньше 7» (сумма 2–6), «Ровно 7», «Больше 7» (8–12).
Ведёт юная драконица Искра. Игра открывается в главе 5 — горной деревне драконов (пока её нет — только в
режиме разработчика). Коэффициенты подобраны так, что в среднем игроку возвращается около 95% (как у рулетки
и улиток): «меньше»/«больше» — шанс 15/36, x2.3; «ровно 7» — шанс 6/36, x5.7.
"""
import random

MIN_BET = 5
UNLOCK_FARM = "dragons"
AREAS = [
    dict(id="under", name="Меньше 7", sub="2 – 6", k=2.3),
    dict(id="seven", name="Ровно 7", sub="7", k=5.7),
    dict(id="over", name="Больше 7", sub="8 – 12", k=2.3),
]
FORCE_NEXT = None        # режим разработчика: (a, b) — так выпадут кости в следующий раз


def area_wins(area_id, total):
    return {"under": total < 7, "seven": total == 7, "over": total > 7}[area_id]


def chance(area_id):
    """Шанс поля (из 36 исходов)."""
    return sum(1 for a in range(1, 7) for b in range(1, 7) if area_wins(area_id, a + b)) / 36


def unlocked(farm_index):
    from .config import FARMS
    idx = next((n for n, fm in enumerate(FARMS) if fm["id"] == UNLOCK_FARM), len(FARMS))
    return farm_index >= idx


class DiceGame:
    def __init__(self, rng=random):
        self.state = "bet"
        self.bets = {a["id"]: 0 for a in AREAS}
        self.dice = None           # (a, b) после броска
        self.paid = 0              # сколько вернулось игроку (со ставками)
        self.history = []          # последние суммы

    @property
    def bet(self):
        return sum(self.bets.values())

    def add_bet(self, tavern, area_id, amount):
        if self.state != "bet" or area_id not in self.bets or amount <= 0 or tavern.tokens < amount:
            return False
        tavern.tokens -= amount
        self.bets[area_id] += amount
        return True

    def clear_bet(self, tavern, area_id=None):
        if self.state != "bet":
            return
        for k in (self.bets if area_id is None else [area_id]):
            tavern.tokens += self.bets[k]
            self.bets[k] = 0

    def total(self):
        return sum(self.dice) if self.dice else 0

    def roll(self, tavern, rng=random):
        """Бросок: итог решается и выплачивается сразу (анимацию рисует экран). False — на столе меньше MIN_BET."""
        global FORCE_NEXT
        if self.state != "bet" or self.bet < MIN_BET:
            return False
        if FORCE_NEXT is not None:
            self.dice, FORCE_NEXT = tuple(FORCE_NEXT), None
        else:
            self.dice = (rng.randint(1, 6), rng.randint(1, 6))
        t = self.total()
        self.paid = sum(int(round(self.bets[a["id"]] * a["k"])) for a in AREAS if area_wins(a["id"], t))
        tavern.tokens += self.paid
        self.history = [t] + self.history[:9]
        self.state = "roll"
        return True

    def finish(self):
        if self.state == "roll":
            self.state = "done"

    def winning_area(self):
        t = self.total()
        return next((a["id"] for a in AREAS if area_wins(a["id"], t)), None) if self.dice else None

    def won(self):
        """Выиграло хоть одно поле с нашими фишками (в плюсе ли — см. net)."""
        w = self.winning_area()
        return bool(w) and self.bets[w] > 0

    def net(self):
        return self.paid - self.bet if self.dice else 0

    def next_round(self, tavern, same_bet=True):
        """После броска: те же ставки на те же поля (если хватает жетонов)."""
        if self.state not in ("roll", "done"):
            return False
        last = dict(self.bets)
        self.state, self.paid, self.dice = "bet", 0, None
        self.bets = {a["id"]: 0 for a in AREAS}
        if same_bet and sum(last.values()) and tavern.tokens >= sum(last.values()):
            tavern.tokens -= sum(last.values())
            self.bets = last
        return True

    def refund(self, tavern):
        """Ушли от стола: несыгранные ставки — назад; брошенное уже оплачено."""
        if self.state == "bet":
            self.clear_bet(tavern)
        else:
            self.finish()
