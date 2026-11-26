# -*- coding: utf-8 -*-
"""3.39: мини-игра вылова хищника, как в Stardew Valley. Без графики — только «физика», её проверяют тесты.

Вертикальная шкала высотой 1.0. Зелёная зона (поплавок) поднимается, пока игрок держит кнопку мыши или пробел,
и падает, когда отпускает (о дно — отскок). Рыба мечется вверх-вниз: чем сложнее хищник, тем быстрее и резче.
Рыба в зоне — шкала улова растёт, вне зоны — падает. Полная — выловил, пустая — сорвался.
"""
import random

CATCH_ZONE = 0.26          # высота зелёной зоны (доля шкалы)
CATCH_UP, CATCH_DOWN = 2.8, 2.3       # ускорение зоны вверх (держишь) и вниз (отпустил), шкал/с²
CATCH_VMAX = 1.25          # предельная скорость зоны
CATCH_BOUNCE = 0.4         # отскок от дна
CATCH_START = 0.3          # с чего начинается шкала улова
CATCH_GAIN, CATCH_LOSS = 0.30, 0.22   # рост шкалы, когда рыба в зоне, и потеря, когда нет (в секунду)
CATCH_SNOWFLAKE = 0.8      # трофей зимы «Снежинка»: рыба мечется на 20% медленнее
CATCH_FAT, CATCH_FAT_MAX = 0.025, 1.4   # каждая съеденная рыбка — +2.5% к сложности (растолстел), не больше x1.4


class Catch:
    def __init__(self, diff, slow=1.0, rnd=None):
        self.rnd = rnd or random.Random()
        self.diff = max(0.5, diff)
        self.slow = slow                      # 0.8 со «Снежинкой»
        self.zone = 0.0                       # низ зелёной зоны (0 — у дна)
        self.zone_v = 0.0
        self.fish = 0.5                       # где рыба (0 — дно, 1 — верх)
        self.target = 0.5
        self.retarget = 0.6
        self.progress = CATCH_START
        self.result = None                    # None — идёт, True — выловил, False — сорвался
        self.t = 0.0

    def fish_speed(self):
        return (0.22 + 0.16 * self.diff) * self.slow

    def in_zone(self):
        return self.zone <= self.fish <= self.zone + CATCH_ZONE

    def step(self, dt, holding):
        if self.result is not None:
            return self.result
        dt = min(dt, 0.05)
        self.t += dt
        # зона
        self.zone_v += (CATCH_UP if holding else -CATCH_DOWN) * dt
        self.zone_v = max(-CATCH_VMAX, min(CATCH_VMAX, self.zone_v))
        self.zone += self.zone_v * dt
        if self.zone < 0:
            self.zone, self.zone_v = 0.0, -self.zone_v * CATCH_BOUNCE
        top = 1.0 - CATCH_ZONE
        if self.zone > top:
            self.zone, self.zone_v = top, 0.0
        # рыба: выбирает, куда рвануть; сложная — чаще и дальше, иногда резкий бросок
        self.retarget -= dt
        if self.retarget <= 0:
            r = self.rnd
            self.retarget = max(0.3, r.uniform(0.9, 1.8) - 0.22 * self.diff) / self.slow
            reach = min(0.9, 0.25 + 0.12 * self.diff)
            self.target = min(0.98, max(0.02, self.fish + r.uniform(-reach, reach)))
            if r.random() < 0.08 * self.diff:
                self.target = r.choice((0.03, 0.97))
        sp = self.fish_speed()
        d = self.target - self.fish
        step = sp * dt * (1.6 if abs(d) > 0.4 else 1.0)
        self.fish = self.target if abs(d) <= step else self.fish + step * (1 if d > 0 else -1)
        # шкала улова
        self.progress += (CATCH_GAIN if self.in_zone() else -CATCH_LOSS) * dt
        if self.progress >= 1.0:
            self.progress, self.result = 1.0, True
        elif self.progress <= 0.0:
            self.progress, self.result = 0.0, False
        return self.result


def bot_win_rate(diff, slow=1.0, games=200, react=0.12, seed=1):
    """Для подбора баланса: как часто ловит простой «игрок» с запаздыванием реакции react секунд."""
    wins = 0
    for g in range(games):
        c = Catch(diff, slow, random.Random(seed * 1000 + g))
        seen, lag, dt = c.fish, 0.0, 1 / 60
        while c.result is None and c.t < 120:
            lag += dt
            if lag >= react:
                lag, seen = 0.0, c.fish
            centre = c.zone + CATCH_ZONE / 2
            c.step(dt, seen > centre - 0.02 + c.zone_v * 0.18)
        wins += c.result is True
    return wins / games
