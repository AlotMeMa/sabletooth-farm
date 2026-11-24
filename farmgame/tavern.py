# -*- coding: utf-8 -*-
"""Таверна: доска заданий (ежедневные + еженедельное), жетоны таверны. Без графики.

Таверна общая для всех ферм: задания, прогресс и жетоны не сбрасываются ни грузовиком, ни переездом.
Открывается на средневековом поле (и остаётся открытой дальше).
Ежедневные задания обновляются в полночь (по часам компьютера), еженедельное — в ночь на понедельник.
Выполненное, но не забранное задание при смене дня/недели не сгорает: награда записывается в Tavern.owed
и выдаётся автоматически (деньги, листья и буст — в tavern_ui.pay_owed).
"""
import datetime
import random
import re

DAILY_COUNT = 4
TAVERN_FROM_FARM = 1          # индекс фермы, с которой открывается таверна (1 — средневековье)

# Награда за ежедневное задание: минуты дохода фермы (считаются в момент получения) + жетоны.
DAILY_REWARD = {1: (15, 5), 2: (25, 10), 3: (40, 15)}        # сложность -> (минут дохода, жетонов)
WEEKLY_REWARD = dict(minutes=180, tokens=60, prestige=15, boost_minutes=30)

# Шаблоны заданий: событие, текст, цели по сложности, при каком условии фермы доступно.
# need: None — везде; "crow"/"bandits"/"peasants" — флаг фермы; "animals"/"mill" — что стоит вместо сарая.
QUESTS = [
    dict(id="collect", event="collect", need=None, title="Жатва", text="Собери урожай с грядок {n|раз|раза|раз}",
         targets={1: (40, 60), 2: (80, 120), 3: (150, 200)}),
    dict(id="buy", event="buy_levels", need=None, title="Расширение", text="Купи {n|уровень|уровня|уровней} грядок",
         targets={1: (30, 50), 2: (80, 120), 3: (180, 250)}),
    dict(id="milestone", event="milestone", need=None, title="Быстрый рост", text="Достигни {n|веху|вехи|вех} на грядках",
         targets={2: (2, 3), 3: (4, 6)}),
    dict(id="squirrel", event="squirrel", need=None, title="Ловкие руки", text="Поймай {n|белку|белки|белок}",
         targets={1: (1, 1), 2: (2, 3), 3: (4, 5)}),
    dict(id="golden", event="golden", need=None, title="Золотая охота", text="Поймай золотую белку",
         targets={3: (1, 1)}),
    dict(id="crow", event="crow", need="crow", title="Пугало", text="Прогони {n|ворону|вороны|ворон}",
         targets={1: (1, 2), 2: (3, 4)}),
    dict(id="bandit", event="bandit", need="bandits", title="Стража", text="Прогони {n|разбойника|разбойника|разбойников}",
         targets={1: (1, 2), 2: (3, 4), 3: (5, 7)}),
    dict(id="weather", event="weather", need=None, title="Гуляния", text="{weather} {n|раз|раза|раз}",
         targets={1: (1, 1), 2: (2, 3)}),
    dict(id="sun", event="sun", need=None, title="Солнышко", text="Забери солнечный бонус {n|раз|раза|раз}",
         targets={1: (2, 3), 2: (4, 5)}),
    dict(id="tree", event="tree", need=None, title="Мудрость", text="Купи {n|улучшение|улучшения|улучшений} в дереве",
         targets={2: (1, 2), 3: (3, 4)}),
    dict(id="truck", event="truck", need=None, title="Большая сделка", text="Продай ферму {buyer}",
         targets={3: (1, 1)}),
    dict(id="feed", event="feed", need="animals", title="Скотник", text="Покорми зверей {n|раз|раза|раз}",
         targets={1: (5, 8), 2: (12, 18)}),
    dict(id="product", event="product", need="animals", title="Ярмарка", text="Собери продукты сарая {n|раз|раза|раз}",
         targets={1: (5, 8), 2: (12, 18), 3: (25, 30)}),
    dict(id="bread", event="bread", need="mill", title="Пекарь", text="Продай хлеб {n|раз|раза|раз}",
         targets={1: (3, 5), 2: (8, 12), 3: (15, 20)}),
    dict(id="grain", event="flour_sell", need="mill", title="Мельник", text="Продай муку {n|раз|раза|раз}",
         targets={1: (2, 3), 2: (5, 7)}),
    dict(id="build", event="build", need="mill", title="Строитель", text="Построй или улучши мельницу/пекарню {n|раз|раза|раз}",
         targets={2: (1, 2), 3: (3, 3)}),
    dict(id="peasant", event="peasant", need="peasants", title="Новые руки", text="Найми {n|крестьянина|крестьянина|крестьян}",
         targets={2: (1, 1), 3: (2, 2)}),
]

WEEKLY = [
    dict(id="w_collect", event="collect", need=None, title="Великая жатва", text="Собери урожай {n|раз|раза|раз}", n=(700, 900)),
    dict(id="w_buy", event="buy_levels", need=None, title="Большая стройка", text="Купи {n|уровень|уровня|уровней} грядок", n=(1500, 2000)),
    dict(id="w_squirrel", event="squirrel", need=None, title="Беличья неделя", text="Поймай {n|белку|белки|белок}", n=(12, 15)),
    dict(id="w_bandit", event="bandit", need="bandits", title="Гроза разбойников", text="Прогони {n|разбойника|разбойника|разбойников}", n=(20, 25)),
    dict(id="w_weather", event="weather", need=None, title="Неделя праздников", text="{weather} {n|раз|раза|раз}", n=(12, 15)),
    dict(id="w_truck", event="truck", need=None, title="Купец недели", text="Продай ферму {buyer} {n|раз|раза|раз}", n=(3, 4)),
    dict(id="w_daily", event="daily_done", need=None, title="Завсегдатай", text="Выполни {n|ежедневное задание|ежедневных задания|ежедневных заданий}", n=(12, 16)),
]

BARMAN_LINES = [
    "Добро пожаловать в «Хмельной колос»! Доска заданий — слева, на стене.",
    "Задания на доске меняются каждую ночь. Не проспи!",
    "Видишь большой свиток на доске? Это задание недели. Награда — королевская.",
    "Устал? Ничего. Садись у очага, погрейся — ферма и без тебя поработает.",
    "Жетоны можно отдать барду — нажми на него и закажи песню.",
    "Подбрось полено в камин — огонь любит, когда о нём заботятся.",
    "За жетоны можно украсить зал. Загляни в «Призы» — внизу слева.",
    "Бард сегодня в ударе. Ещё кружечку?",
]
# 3.20: реплики по обстоятельствам — добавляются к общим, когда в таверне это есть
BARMAN_EXTRA = {
    "casino_closed": "Говорят, за дверью справа скоро откроют игорный зал...",
    "casino_open": "Игорный зал — за красной занавеской справа. Только рубаху не проиграй!",
    "cat": "Кот? Это Рыжик. Пришёл погреться разок — да так и остался.",
    "kettle": "В котелке над огнём — похлёбка по бабушкиному рецепту. Рецепт не скажу!",
    "bard_girl": "Мила поёт — и даже Рыжик у очага ухом ведёт.",
    "trophies": "Трофеи над камином — твои. Гости спрашивают, где ты их взял!",
}


def barman_lines(tavern):
    """Что бармен может сказать сейчас: общие реплики и то, что подходит к залу (3.20)."""
    from .config import PRIZES
    out = list(BARMAN_LINES)
    out.insert(4, BARMAN_EXTRA["casino_open" if tavern.casino_open else "casino_closed"])
    for key in ("cat", "kettle", "bard_girl"):
        if tavern.prize_on(key):
            out.append(BARMAN_EXTRA[key])
    if any(tavern.prizes.get(p["id"]) for p in PRIZES if p["kind"] == "trophy"):
        out.append(BARMAN_EXTRA["trophies"])
    return out


GIRL_LINES = [   # 3.15.2: певица Мила (скин барда из призов казино)
    "Ой, люли-люли, поле золотое!", "Спою вам про луга и речку!", "Подпевайте, кто знает слова!",
    "Эту песню пела ещё моя бабушка.", "Для вас — самая весёлая!",
]
BARD_LINES = [
    "Бард затягивает балладу о золотой белке.",
    "Бард играет весёлую плясовую — гости стучат кружками в такт.",
    "Бард поёт о разбойнике, который украл репу у самого короля.",
]


def plural(n, one, few, many):
    """1 белку, 2 белки, 5 белок; 21 белку, 11 белок."""
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def day_key(now=None):
    now = now or datetime.datetime.now()
    return now.strftime("%Y-%m-%d")


def week_key(now=None):
    now = now or datetime.datetime.now()
    y, w, _ = now.isocalendar()
    return f"{y}-W{w:02d}"


def seconds_to_midnight(now=None):
    now = now or datetime.datetime.now()
    tomorrow = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return (tomorrow - now).total_seconds()


def seconds_to_monday(now=None):
    now = now or datetime.datetime.now()
    days = 7 - now.weekday()
    nxt = (now + datetime.timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    return (nxt - now).total_seconds()


def farm_has(fm, need):
    if need is None:
        return True
    if need in ("animals", "mill"):
        return fm.get("barn") == need
    return bool(fm.get(need))


class Tavern:
    def __init__(self):
        self.unlocked = False
        self.tokens = 0
        self.day = ""
        self.week = ""
        self.daily = []          # [{id, title, text, event, need, diff, target, progress, claimed}]
        self.weekly = None
        self.daily_done_total = 0
        self.just_done = []      # задания недели, выполненные последним claim() («Завсегдатай»)
        self.owed = []           # награды за сменившиеся незабранные задания: [{title, weekly, minutes, tokens, prestige, boost}]
        # 3.14: казино
        self.casino_open = False # открылось навсегда (жетонов впервые стало CASINO_UNLOCK_TOKENS)
        self.casino_intro = False   # крупье уже рассказал правила
        self.prizes = {}         # id приза -> True (трофеи, косметика)
        self.prize_off = []      # купленная косметика, которую игрок выключил
        self.prize_day = {}      # id бафа -> день покупки (бафы — раз в день)

    # ---------- казино (3.14) ----------
    def check_casino(self):
        """True, если казино открылось только что (жетонов впервые набралось достаточно)."""
        from .config import CASINO_UNLOCK_TOKENS
        if not self.casino_open and self.tokens >= CASINO_UNLOCK_TOKENS:
            self.casino_open = True
            return True
        return False

    def prize_state(self, prize, today=None):
        """owned — куплен, can — можно купить (с 3.19 все призы — навсегда)."""
        return "owned" if self.prizes.get(prize["id"]) else "can"

    def prize_on(self, pid):
        """Косметика куплена и не выключена."""
        return bool(self.prizes.get(pid)) and pid not in self.prize_off

    def toggle_prize(self, pid):
        if not self.prizes.get(pid):
            return False
        if pid in self.prize_off:
            self.prize_off.remove(pid)
        else:
            self.prize_off.append(pid)
        return True

    def buy_prize(self, farm, pid, today=None):
        """Купить приз за жетоны. Возвращает (получилось, причина отказа)."""
        from .config import PRIZES
        prize = next((p for p in PRIZES if p["id"] == pid), None)
        if prize is None:
            return False, "Такого приза нет"
        state = self.prize_state(prize, today)
        if state == "owned":
            return False, "Уже есть"
        if self.tokens < prize["cost"]:
            return False, f"Нужно жетонов: {prize['cost']}"
        self.tokens -= prize["cost"]
        self.prizes[pid] = True
        return True, ""

    # ---------- генерация ----------
    def _quest_text(self, tpl, n, fm):
        text = re.sub(r"\{n\|([^|}]*)\|([^|}]*)\|([^|}]*)\}", lambda m: f"{n} {plural(n, *m.groups())}", tpl["text"])
        return text.format(n=n, weather=_weather_verb(fm), buyer=_buyer_dat(fm))

    def make_daily(self, fm, rnd=None, blocked=()):
        """blocked — id заданий, которые сейчас не выполнить (например, все крестьяне уже наняты)."""
        rnd = rnd or random.Random()
        pool = [q for q in QUESTS if farm_has(fm, q["need"]) and q["id"] not in blocked]
        rnd.shuffle(pool)
        picked, used_events = [], set()
        for q in pool:                      # разные события — чтобы задания не повторяли друг друга
            if q["event"] in used_events and q["event"] != "feed":
                continue
            picked.append(q)
            used_events.add(q["event"])
            if len(picked) == DAILY_COUNT:
                break
        # сложности: 1, 2, 2, 3 (лёгкое, два средних, трудное), по возможности
        want = [1, 2, 2, 3]
        out = []
        for q, d in zip(picked, want):
            diffs = sorted(q["targets"])
            diff = min(diffs, key=lambda x: abs(x - d))
            lo, hi = q["targets"][diff]
            n = rnd.randint(lo, hi)
            out.append(dict(id=q["id"], title=q["title"], text=self._quest_text(q, n, fm), event=q["event"],
                            need=q["need"], diff=diff, target=n, progress=0, claimed=False))
        self.daily = out

    def make_weekly(self, fm, rnd=None):
        rnd = rnd or random.Random()
        pool = [q for q in WEEKLY if farm_has(fm, q["need"])]
        q = rnd.choice(pool)
        n = rnd.randint(*q["n"])
        self.weekly = dict(id=q["id"], title=q["title"], text=self._quest_text(q, n, fm), event=q["event"],
                           need=q["need"], target=n, progress=0, claimed=False)

    def refresh(self, fm, now=None, blocked=()):
        """Новый день — новые задания; новая неделя — новое большое задание. Возвращает True, если обновилось."""
        changed = False
        dk, wk = day_key(now), week_key(now)
        if self.day != dk or not self.daily:
            self._expire(list(self.daily))      # сначала дневные: они ещё идут в зачёт «Завсегдатаю» этой недели
            self.day = dk
            self.make_daily(fm, blocked=blocked)
            changed = True
        if self.week != wk or self.weekly is None:
            if self.weekly:
                self._expire([self.weekly])
            self.week = wk
            self.make_weekly(fm)
            changed = True
        return changed

    def _expire(self, quests):
        """Задания уходят с доски. Выполненные, но не забранные не сгорают: жетоны начисляются сразу,
        остальное (деньги, валюта престижа, буст) записывается в owed — игра выдаст это сама."""
        for q in quests:
            weekly = q is self.weekly
            reward = self.claim(q)
            if reward:
                self.owed.append(dict(title=q["title"], weekly=weekly, minutes=reward[0], tokens=reward[1],
                                      prestige=reward[2], boost=reward[3]))

    def take_owed(self):
        """Забрать список наград, выданных автоматически (и очистить его)."""
        owed, self.owed = self.owed, []
        return owed

    def replace_impossible(self, fm, rnd=None, blocked=()):
        """После переезда: невыполненные задания, которые на новой ферме сделать нельзя
        (например, разбойники на ферме без разбойников), меняются на другие того же уровня."""
        rnd = rnd or random.Random()
        changed = False
        for idx, q in enumerate(self.daily):
            if q["claimed"] or q["progress"] >= q["target"] or farm_has(fm, q["need"]):
                continue
            used = {d["event"] for d in self.daily}
            pool = [t for t in QUESTS if farm_has(fm, t["need"]) and t["event"] not in used and t["id"] not in blocked]
            if not pool:
                continue
            t = rnd.choice(pool)
            diff = min(sorted(t["targets"]), key=lambda x: abs(x - q["diff"]))
            n = rnd.randint(*t["targets"][diff])
            self.daily[idx] = dict(id=t["id"], title=t["title"], text=self._quest_text(t, n, fm), event=t["event"],
                                   need=t["need"], diff=diff, target=n, progress=0, claimed=False)
            changed = True
        w = self.weekly
        if w and not w["claimed"] and w["progress"] < w["target"] and not farm_has(fm, w["need"]):
            self.make_weekly(fm, rnd)
            changed = True
        return changed

    # ---------- прогресс ----------
    def on(self, event, n=1):
        """Игровое событие (собрал урожай, поймал белку...). Возвращает список только что выполненных заданий."""
        if not self.unlocked:
            return []
        done = []
        for q in self.daily + ([self.weekly] if self.weekly else []):
            if q["claimed"] or q["event"] != event or q["progress"] >= q["target"]:
                continue
            q["progress"] = min(q["target"], q["progress"] + n)
            if q["progress"] >= q["target"]:
                done.append(q)
        return done

    def claimable(self):
        qs = self.daily + ([self.weekly] if self.weekly else [])
        return [q for q in qs if not q["claimed"] and q["progress"] >= q["target"]]

    def reward_of(self, q):
        """(минут дохода, жетонов, валюты престижа, минут буста x2)."""
        if q is self.weekly:
            r = WEEKLY_REWARD
            return r["minutes"], r["tokens"], r["prestige"], r["boost_minutes"]
        minutes, tokens = DAILY_REWARD[q["diff"]]
        return minutes, tokens, 0, 0

    def claim(self, q):
        """Отмечает задание полученным. Возвращает награду (как reward_of) или None."""
        if q["claimed"] or q["progress"] < q["target"]:
            return None
        q["claimed"] = True
        reward = self.reward_of(q)
        self.tokens += reward[1]
        self.just_done = []
        if q is not self.weekly:
            self.daily_done_total += 1
            self.just_done = self.on("daily_done")     # «Завсегдатай» (задание недели) мог выполниться
        return reward

    # ---------- сохранение ----------
    def to_dict(self):
        return dict(unlocked=self.unlocked, tokens=self.tokens, day=self.day, week=self.week,
                    daily=self.daily, weekly=self.weekly, daily_done_total=self.daily_done_total, owed=self.owed,
                    casino_open=self.casino_open, casino_intro=self.casino_intro, prizes=self.prizes,
                    prize_off=self.prize_off, prize_day=self.prize_day)

    def from_dict(self, d):
        """Читает таверну из сохранения. Испорченные записи пропускаются — задания тогда просто выдадутся заново."""
        if not isinstance(d, dict):
            return
        self.unlocked = bool(d.get("unlocked", self.unlocked))
        self.tokens = _int(d.get("tokens"), self.tokens)
        self.daily_done_total = _int(d.get("daily_done_total"), self.daily_done_total)
        for k in ("day", "week"):
            if isinstance(d.get(k), str):
                setattr(self, k, d[k])
        if isinstance(d.get("daily"), list):
            self.daily = [q for q in (_clean_quest(q) for q in d["daily"]) if q][:DAILY_COUNT]
        if "weekly" in d:
            self.weekly = _clean_quest(d["weekly"], weekly=True)
        from .config import PRIZES
        ids = {p["id"] for p in PRIZES}
        self.casino_open = bool(d.get("casino_open", self.casino_open))
        self.casino_intro = bool(d.get("casino_intro", self.casino_intro))
        if isinstance(d.get("prizes"), dict):
            self.prizes = {k: True for k, v in d["prizes"].items() if isinstance(k, str) and k in ids and v}
        if isinstance(d.get("prize_off"), list):
            self.prize_off = [k for k in d["prize_off"] if isinstance(k, str) and k in ids]
        if isinstance(d.get("prize_day"), dict):
            self.prize_day = {k: v for k, v in d["prize_day"].items()
                              if isinstance(k, str) and k in ids and isinstance(v, str)}
        if isinstance(d.get("owed"), list):
            self.owed = [dict(title=str(o.get("title", "")), weekly=bool(o.get("weekly")),
                              minutes=_int(o.get("minutes"), 0), tokens=_int(o.get("tokens"), 0),
                              prestige=_int(o.get("prestige"), 0), boost=_int(o.get("boost"), 0))
                         for o in d["owed"] if isinstance(o, dict)]


def order_song(tavern, farm, song_id):
    """3.8: заказать песню барду за жетоны. Возвращает (получилось, причина отказа).
    Песня даёт эффект на song minutes минут (см. config.SONGS); пока играет одна — другую не заказать."""
    from .config import SONGS
    song = next((sg for sg in SONGS if sg["id"] == song_id), None)
    if song is None:
        return False, "Такой песни бард не знает"
    if farm.song_left > 0 and farm.song:
        return False, "Бард ещё играет прошлый заказ"
    if tavern.tokens < song["cost"]:
        return False, f"Нужно жетонов: {song['cost']}"
    tavern.tokens -= song["cost"]
    farm.song = song["id"]
    farm.song_left = song["minutes"] * 60.0
    return True, ""


def _int(v, default=0):
    """Неотрицательное целое из сохранения (или default, если там мусор)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v in (float("inf"), float("-inf")):
        return default
    return max(0, int(v))


def _clean_quest(q, weekly=False):
    """Задание из сохранения -> словарь с проверенными полями. None — запись испорчена."""
    if not isinstance(q, dict):
        return None
    try:
        out = dict(id=str(q["id"]), title=str(q["title"]), text=str(q["text"]), event=str(q["event"]),
                   need=q.get("need") if isinstance(q.get("need"), str) else None,
                   target=max(1, _int(q["target"], 1)), progress=_int(q.get("progress"), 0),
                   claimed=bool(q.get("claimed", False)))
    except KeyError:
        return None
    if not weekly:
        diff = q.get("diff")
        out["diff"] = diff if isinstance(diff, int) and not isinstance(diff, bool) and diff in DAILY_REWARD else 1
    return out


def _weather_verb(fm):
    w = fm.get("weather", "Дождь")
    return {"Дождь": "Вызови дождь", "Праздник урожая": "Устрой праздник урожая",
            "Оттепель": "Вызови оттепель"}.get(w, "Вызови " + w.lower())


def _buyer_dat(fm):
    return {"скупщик": "скупщику", "сборщик податей": "сборщику податей"}.get(fm.get("buyer", ""), fm.get("buyer", ""))
