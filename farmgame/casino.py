# -*- coding: utf-8 -*-
"""Казино таверны: рулетка на жетоны (заготовка, 3.10). Без графики — экран в casino_ui.py.

Европейская рулетка: 37 ячеек (0 и 1–36), зеро — зелёное. Ставки:
    ("num", n)           — на число:        выигрыш 35 к 1 (возвращается ставка x36)
    ("red",) ("black",)  — на цвет:         1 к 1 (x2)
    ("even",) ("odd",)   — чёт / нечет:     1 к 1 (x2)
    ("low",) ("high",)   — 1–18 / 19–36:    1 к 1 (x2)
    ("dozen", 1|2|3)     — дюжина:          2 к 1 (x3)
На зеро все внешние ставки проигрывают (как в настоящей европейской рулетке).

Пока казино открывается только в режиме разработчика: правила и цены — решение за автором игры.
"""
import random

WHEEL = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9,
         22, 18, 29, 7, 28, 12, 35, 3, 26]           # порядок ячеек на колесе (по часовой)
RED = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
CHIPS = (1, 5, 10, 25)                                # номиналы фишек (жетоны)
MAX_BET_TOTAL = 200                                   # больше за один спин не поставить
BET_NAMES = {"red": "Красное", "black": "Чёрное", "even": "Чёт", "odd": "Нечет", "low": "1–18", "high": "19–36"}


def color_of(n):
    return "green" if n == 0 else ("red" if n in RED else "black")


def bet_name(key):
    if key[0] == "num":
        return str(key[1])
    if key[0] == "dozen":
        return ("1–12", "13–24", "25–36")[key[1] - 1]
    return BET_NAMES[key[0]]


def payout(key, result):
    """Сколько вернётся за ставку 1 (вместе с самой ставкой). 0 — проигрыш."""
    kind = key[0]
    if kind == "num":
        return 36 if result == key[1] else 0
    if result == 0:
        return 0
    if kind == "red":
        return 2 if result in RED else 0
    if kind == "black":
        return 2 if result not in RED else 0
    if kind == "even":
        return 2 if result % 2 == 0 else 0
    if kind == "odd":
        return 2 if result % 2 == 1 else 0
    if kind == "low":
        return 2 if result <= 18 else 0
    if kind == "high":
        return 2 if result >= 19 else 0
    if kind == "dozen":
        return 3 if (result - 1) // 12 + 1 == key[1] else 0
    return 0


def valid_key(key):
    if not isinstance(key, tuple) or not key:
        return False
    if key[0] == "num":
        return len(key) == 2 and isinstance(key[1], int) and 0 <= key[1] <= 36
    if key[0] == "dozen":
        return len(key) == 2 and key[1] in (1, 2, 3)
    return len(key) == 1 and key[0] in BET_NAMES


class Roulette:
    """Ставки текущего спина. Жетоны списываются сразу при ставке и возвращаются, если ставки убрать."""

    def __init__(self, rng=None):
        self.bets = {}            # ключ ставки -> жетонов
        self.rng = rng or random.Random()
        self.history = []         # последние выпавшие числа (новые в начале)

    def total(self):
        return sum(self.bets.values())

    def place(self, tavern, key, amount):
        """Поставить amount жетонов на key. (получилось, причина отказа)."""
        if not valid_key(key) or amount <= 0:
            return False, "Так поставить нельзя"
        if tavern.tokens < amount:
            return False, "Не хватает жетонов"
        if self.total() + amount > MAX_BET_TOTAL:
            return False, f"За один спин — не больше {MAX_BET_TOTAL} жетонов"
        tavern.tokens -= amount
        self.bets[key] = self.bets.get(key, 0) + amount
        return True, ""

    def clear(self, tavern):
        """Убрать все ставки (до спина): жетоны возвращаются."""
        tavern.tokens += self.total()
        self.bets = {}

    def spin(self):
        """Выбросить число. Ставки остаются до settle (пока крутится колесо)."""
        return self.rng.randrange(37)

    def settle(self, tavern, result):
        """Рассчитать ставки по выпавшему числу: выигрыш — в жетоны. Возвращает (выигрыш, поставлено)."""
        won = sum(amount * payout(key, result) for key, amount in self.bets.items())
        staked = self.total()
        tavern.tokens += won
        self.bets = {}
        self.history = ([result] + self.history)[:12]
        return won, staked
