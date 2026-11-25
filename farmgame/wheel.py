# -*- coding: utf-8 -*-
"""3.27: ежедневное колесо фортуны в Игровой (без графики — экран в gameroom_ui.py).

Крутить можно раз в день (по дате компьютера). Выпадает: ничего, жетоны или ДЖЕКПОТ.
Джекпот меняется каждую неделю (по номеру недели): много жетонов или скин, который не продаётся.
Скин уже есть — вместо него JACKPOT_OWNED_TOKENS жетонов. Состояние живёт в Tavern (wheel_day, wheel_last):
таверна, жетоны и призы переезжают с фермы на ферму — колесо тоже.
"""
import datetime
import random

# сектора по кругу (по часовой стрелке от стрелки сверху): (что, сколько, подпись)
SEGMENTS = [("none", 0, "Пусто"), ("tokens", 5, "5"), ("none", 0, "Пусто"), ("tokens", 10, "10"),
            ("tokens", 20, "20"), ("none", 0, "Пусто"), ("tokens", 50, "50"), ("jackpot", 0, "ДЖЕКПОТ")]
WEIGHTS = [16, 22, 16, 16, 10, 12, 6, 2]          # шансы, % (джекпот — 2 %)
# джекпот недели — по кругу: неделя 1 — первый, 2 — второй, ...
JACKPOTS = [dict(kind="tokens", amount=300, name="300 жетонов"),
            dict(kind="prize", prize="rainbow_notes", name="скин «Радужные ноты»"),
            dict(kind="tokens", amount=500, name="500 жетонов"),
            dict(kind="prize", prize="star_trail", name="скин «Звёздный шлейф»")]
JACKPOT_OWNED_TOKENS = 250    # скин уже есть — жетоны вместо него


def today(d=None):
    return d or datetime.date.today()


def day_key(d=None):
    return today(d).isoformat()


def week_index(d=None):
    y, w, _ = today(d).isocalendar()
    return y * 53 + w


def jackpot_for(d=None):
    return JACKPOTS[week_index(d) % len(JACKPOTS)]


def can_spin(tavern, d=None):
    return tavern.wheel_day != day_key(d)


def seconds_to_next(now=None):
    """Сколько секунд до полуночи — тогда колесо снова можно крутить."""
    now = now or datetime.datetime.now()
    nxt = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.time())
    return max(0, int((nxt - now).total_seconds()))


def pick(rng=random):
    return rng.choices(range(len(SEGMENTS)), weights=WEIGHTS)[0]


def spin(tavern, d=None, rng=random):
    """Крутит колесо: (номер сектора, награда {kind, amount, prize, text}) или None, если сегодня уже крутили.
    Награда сразу начисляется (экран только показывает, как колесо до неё доезжает)."""
    if not can_spin(tavern, d):
        return None
    idx = pick(rng)
    kind, amount, _label = SEGMENTS[idx]
    reward = dict(kind=kind, amount=0, prize=None, text="Пусто... Завтра повезёт!")
    if kind == "tokens":
        reward.update(amount=amount, text=f"+{amount} жетонов!")
    elif kind == "jackpot":
        jp = jackpot_for(d)
        if jp["kind"] == "prize" and not tavern.prizes.get(jp["prize"]):
            reward.update(kind="prize", prize=jp["prize"], text=f"ДЖЕКПОТ! {jp['name'].capitalize()}!")
        else:
            amt = jp["amount"] if jp["kind"] == "tokens" else JACKPOT_OWNED_TOKENS
            reward.update(kind="tokens", amount=amt, jackpot=True, text=f"ДЖЕКПОТ! +{amt} жетонов!")
    if reward["amount"]:
        tavern.tokens += reward["amount"]
    if reward["prize"]:
        tavern.prizes[reward["prize"]] = True
    tavern.wheel_day = day_key(d)
    tavern.wheel_last = {"text": reward["text"]}
    return idx, reward
