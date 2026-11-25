# -*- coding: utf-8 -*-
"""3.28: блэкджек («Очко») в Игровой — упрощённые правила, игрок против дилера (рыжего гнома-ворчуна).
Без графики — экран в blackjack_ui.py.

Решения пользователя 25.11: открывается только зимой (с главы «Зимнее поле»), дилер — новый персонаж,
упрощённые правила, без удвоения и разделения.

Правила:
- ставка жетонами, от MIN_BET, без лимита (как в рулетке);
- игроку и дилеру по 2 карты, вторая карта дилера закрыта;
- туз — 11 или 1, картинки — 10; перебор (больше 21) — проигрыш;
- «Взять» — ещё карта, «Хватит» — ход дилера: он добирает, пока у него меньше 17;
- выигрыш платит 1:1, «очко с раздачи» (21 двумя картами) — 3:2, ничья — ставка назад.
Каждая раздача — из свежей перемешанной колоды (52 карты), считать карты бесполезно.
"""
import random

MIN_BET = 5
DEALER_STANDS = 17
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
SUITS = ("hearts", "diamonds", "clubs", "spades")
RED_SUITS = ("hearts", "diamonds")
UNLOCK_FARM = "winter"            # id фермы, с которой открывается блэкджек


def card_value(card):
    rank = card[0]
    if rank == "A":
        return 11
    if rank in ("J", "Q", "K"):
        return 10
    return int(rank)


def hand_value(cards):
    """Очки руки (лучшие: тузы считаются за 11, пока нет перебора)."""
    total = sum(card_value(c) for c in cards)
    aces = sum(1 for c in cards if c[0] == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def is_natural(cards):
    return len(cards) == 2 and hand_value(cards) == 21


def new_deck(rng=random):
    deck = [(r, s) for s in SUITS for r in RANKS]
    rng.shuffle(deck)
    return deck


def unlocked(farm_index):
    from .config import FARMS
    idx = next((n for n, fm in enumerate(FARMS) if fm["id"] == UNLOCK_FARM), len(FARMS))
    return farm_index >= idx


class Blackjack:
    """Одна раздача за раз. state: bet (ставим) → player (ход игрока) → done (итог)."""

    def __init__(self):
        self.state = "bet"
        self.bet = 0              # ставка на столе (жетоны уже сняты с игрока)
        self.player, self.dealer = [], []
        self.deck = []
        self.result = None        # win | blackjack | push | lose | bust
        self.paid = 0             # сколько вернулось игроку (со ставкой)
        self.history = []         # последние итоги: "win"/"lose"/...

    # ---------- ставки ----------
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

    # ---------- раздача ----------
    def deal(self, tavern, rng=random):
        """Раздать. False — ставка меньше MIN_BET или уже идёт раздача."""
        if self.state != "bet" or self.bet < MIN_BET:
            return False
        self.deck = new_deck(rng)
        self.player = [self.deck.pop(), self.deck.pop()]
        self.dealer = [self.deck.pop(), self.deck.pop()]
        self.result, self.paid = None, 0
        self.state = "player"
        if is_natural(self.player) or is_natural(self.dealer):
            self._settle(tavern)
        return True

    def hit(self, tavern):
        if self.state != "player":
            return False
        self.player.append(self.deck.pop())
        if hand_value(self.player) > 21:
            self._settle(tavern)
        elif hand_value(self.player) == 21:
            self.stand(tavern)                 # 21 — дальше брать незачем
        return True

    def stand(self, tavern):
        if self.state != "player":
            return False
        while hand_value(self.dealer) < DEALER_STANDS:
            self.dealer.append(self.deck.pop())
        self._settle(tavern)
        return True

    def _settle(self, tavern):
        p, d = hand_value(self.player), hand_value(self.dealer)
        if is_natural(self.player) and not is_natural(self.dealer):
            self.result, self.paid = "blackjack", self.bet + (self.bet * 3) // 2
        elif is_natural(self.player) and is_natural(self.dealer):
            self.result, self.paid = "push", self.bet
        elif is_natural(self.dealer):
            self.result, self.paid = "lose", 0
        elif p > 21:
            self.result, self.paid = "bust", 0
        elif d > 21 or p > d:
            self.result, self.paid = "win", self.bet * 2
        elif p == d:
            self.result, self.paid = "push", self.bet
        else:
            self.result, self.paid = "lose", 0
        tavern.tokens += self.paid
        self.state = "done"
        self.history = [self.result] + self.history[:9]

    def next_round(self, tavern, same_bet=True):
        """После итога: снова к ставкам; same_bet — поставить столько же (если хватает жетонов)."""
        if self.state != "done":
            return False
        last = self.bet
        self.state, self.bet = "bet", 0
        self.player, self.dealer, self.result, self.paid = [], [], None, 0
        if same_bet and last and tavern.tokens >= last:
            self.add_bet(tavern, last)
        return True

    def refund(self, tavern):
        """Ушли из-за стола: несыгранная ставка — назад; идущая раздача доигрывается за игрока «Хватит»."""
        if self.state == "bet":
            self.clear_bet(tavern)
        elif self.state == "player":
            self.stand(tavern)
