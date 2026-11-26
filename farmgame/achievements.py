# -*- coding: utf-8 -*-
"""3.34: достижения. Без графики.

Счётчики событий живут в таверне (Tavern.stats) — они общие для всех ферм и не сбрасываются ни грузовиком,
ни переездом, и считаются с самого начала игры (даже пока таверна закрыта). Часть достижений смотрит на ферму
(заработано за всю игру, до какой главы дошёл) или на таверну (сколько призов собрано).

Каждое достижение: id, раздел (sec), название, что сделать, откуда брать число (stat — счётчик события, или
особые ключи ниже), цель (target), награда в жетонах (tokens) и, иногда, трофей (prize — id из PRIZES с
achievement=<id достижения>). Награду забирают в окне «Достижения» (кнопка в «Настройках» и в таверне).
"""

SECTIONS = (("field", "Поле"), ("farm", "Хозяйство"), ("tavern", "Таверна"), ("games", "Игровая"))


def A(id, sec, title, text, stat, target, tokens, prize=None):
    return dict(id=id, sec=sec, title=title, text=text, stat=stat, target=target, tokens=tokens, prize=prize)


ACHIEVEMENTS = [
    # --- поле
    A("collect_1", "field", "Первый урожай", "Собери урожай 100 раз", "collect", 100, 5),
    A("collect_2", "field", "Жнец", "Собери урожай 2 000 раз", "collect", 2000, 15),
    A("collect_3", "field", "Хозяин полей", "Собери урожай 20 000 раз", "collect", 20000, 40),
    A("buy_1", "field", "Стройка", "Купи 1 000 уровней грядок", "buy_levels", 1000, 10),
    A("buy_2", "field", "Большая стройка", "Купи 20 000 уровней грядок", "buy_levels", 20000, 30),
    A("milestone_1", "field", "Быстрый рост", "Достигни 50 вех на грядках", "milestone", 50, 15),
    A("squirrel_1", "field", "Ловкие руки", "Поймай 10 белок", "squirrel", 10, 10),
    A("squirrel_2", "field", "Беличий друг", "Поймай 50 белок", "squirrel", 50, 25),
    A("squirrel_3", "field", "Повелитель белок", "Поймай 100 белок", "squirrel", 100, 50, "golden_squirrel"),
    A("golden_1", "field", "Золотоискатель", "Поймай 10 золотых белок", "golden", 10, 20),
    A("crow_1", "field", "Пугало на ножках", "Прогони 30 ворон", "crow", 30, 15),
    A("bandit_1", "field", "Гроза разбойников", "Прогони 50 разбойников", "bandit", 50, 25),
    A("sun_1", "field", "Солнечный зайчик", "Забери солнечный бонус 100 раз", "sun", 100, 15),
    A("weather_1", "field", "Любитель праздников", "Вызови дождь или праздник 30 раз", "weather", 30, 15),
    # --- хозяйство
    A("truck_1", "farm", "Первая сделка", "Продай ферму скупщику", "truck", 1, 10),
    A("truck_2", "farm", "Купец", "Продай ферму 25 раз", "truck", 25, 30),
    A("tree_1", "farm", "Мудрец", "Купи 25 улучшений в дереве", "tree", 25, 20),
    A("earned_1", "farm", "Первый миллион", "Заработай $1M за всю игру", "earned", 1e6, 5),
    A("earned_2", "farm", "Миллиардер", "Заработай $1B за всю игру", "earned", 1e9, 15),
    A("earned_3", "farm", "Триллионер", "Заработай $1T за всю игру", "earned", 1e12, 30),
    A("earned_4", "farm", "Золотые вилы", "Заработай $1aa за всю игру", "earned", 1e15, 60, "golden_pitchfork"),
    A("chapter_1", "farm", "Новая глава", "Переедь на Средневековое поле", "chapter", 1, 30),
    A("chapter_2", "farm", "Зимовка", "Переедь на Зимнее поле", "chapter", 2, 50),
    A("feed_1", "farm", "Скотник", "Покорми зверей 200 раз", "feed", 200, 15),
    A("product_1", "farm", "Ярмарочный день", "Собери продукты сарая 500 раз", "product", 500, 25),
    A("bread_1", "farm", "Пекарь", "Продай хлеб 100 раз", "bread", 100, 20),
    A("peasant_1", "farm", "Артель", "Найми 30 помощников", "peasant", 30, 20),
    # --- таверна
    A("daily_1", "tavern", "Завсегдатай", "Выполни 10 заданий с доски", "daily_done", 10, 15),
    A("daily_2", "tavern", "Душа таверны", "Выполни 100 заданий с доски", "daily_done", 100, 60),
    A("song_1", "tavern", "Меценат", "Закажи 10 песен", "song", 10, 15),
    A("talk_1", "tavern", "Свой человек", "Поговори с барменом 30 раз", "barman_talk", 30, 15),
    A("prize_1", "tavern", "Коллекционер", "Собери 10 призов", "prizes", 10, 30),
    A("prize_2", "tavern", "Всё для дома", "Купи все призы стойки", "prizes_all", 1, 100),
    A("cat_1", "tavern", "Кошатник", "Погладь кота 50 раз", "pet_cat", 50, 10),
    A("dog_1", "tavern", "Лучший друг", "Погладь пса 50 раз", "pet_dog", 50, 10),
    A("fire_1", "tavern", "Хранитель очага", "Подбрось полено 100 раз", "fire_poke", 100, 10),
    # --- игровая
    A("wheel_1", "games", "Крутим-вертим", "Покрути колесо фортуны 7 раз", "wheel_spin", 7, 15),
    A("wheel_2", "games", "Джекпот!", "Выиграй джекпот колеса фортуны", "wheel_jackpot", 1, 30),
    A("roulette_1", "games", "Ставки сделаны", "Сыграй в рулетку 50 раз", "roulette_spin", 50, 15),
    A("roulette_2", "games", "Тридцать пять к одному", "Угадай число в рулетке", "roulette_number", 1, 30),
    A("bj_1", "games", "Ворчун ворчит", "Выиграй у Ворчуна 25 раз", "bj_win", 25, 25),
    A("bj_2", "games", "Очко!", "Набери 21 с раздачи в блэкджеке", "bj_natural", 1, 20),
    # 3.35: финал известной части игры — пройти последнюю открытую главу (заработать порог переезда за забег)
    A("final_1", "farm", "Покоритель зимы", "Заработай за один забег на Зимнем поле столько, сколько нужно для переезда",
      "final_run", 1, 100),
    # 3.39: Рыбацкая деревня — аквариум и вылов (лист медалей 6; в листах 1–5 после 43-го — две запасные клетки)
    A("fish_buy_1", "farm", "Первая рыбка", "Купи 10 рыбок в аквариум", "fish_buy", 10, 5),
    A("fish_sell_1", "farm", "Рыбный рынок", "Продай 200 рыбок из аквариума", "fish_sell", 200, 15),
    A("fish_hatch_1", "farm", "Икорка", "Дождись 25 мальков из икры", "fish_hatch", 25, 15),
    A("pred_1", "farm", "Первый улов", "Вылови хищника", "pred_catch", 1, 10),
    A("pred_2", "farm", "Гроза хищников", "Вылови 50 хищников", "pred_catch", 50, 30),
    A("pred_all", "farm", "Рыбак-коллекционер", "Вылови хищников всех 10 видов", "pred_all", 10, 50),
    A("pred_legend", "farm", "Легенда глубин", "Вылови хищника ранга «Легенда»", "pred_rank5", 1, 30),
    A("pred_feast", "farm", "Обжора", "Вылови хищника, который съел 15 рыбок", "pred_feast", 1, 25),
    A("tank_full", "farm", "Полный аквариум", "Расширь аквариум до 25 мест", "tank_full", 1, 20),
    # 3.40: скачки улиток (лист медалей 7)
    A("snail_1", "games", "Болельщик", "Посмотри 30 забегов улиток", "snail_race", 30, 15),
    A("snail_2", "games", "Тёмная лошадка", "Выиграй на улитке с коэффициентом от x8", "snail_long", 1, 30),
]
BY_ID = {a["id"]: a for a in ACHIEVEMENTS}


def value(a, farm, tavern):
    """Сколько уже сделано для достижения a."""
    st = a["stat"]
    if st == "earned":
        return farm.total_earned
    if st == "chapter":
        return farm.farm_index
    if st == "truck":            # продажи до 3.34 тоже считаются
        return max(tavern.stats.get(st, 0), farm.prestiges)
    if st == "final_run":        # доля порога переезда за текущий забег на последней открытой главе (3-й и дальше)
        if farm.farm_def()["id"] != "winter":     # 3.36: именно зима (после неё уже есть Рыбацкая деревня)
            return tavern.stats.get(st, 0)
        if farm.run_total() >= farm.move_threshold():
            tavern.stats[st] = 1
        return tavern.stats.get(st, 0)
    if st == "pred_all":         # 3.39: сколько видов хищников уже выловлено
        from .config import PREDATORS
        return sum(1 for p in PREDATORS if tavern.stats.get(f"caught_{p['id']}", 0) > 0)
    if st == "daily_done":
        return max(tavern.stats.get(st, 0), tavern.daily_done_total)
    if st == "prizes":
        return sum(1 for v in tavern.prizes.values() if v)
    if st == "prizes_all":
        from .config import PRIZES
        shop = [p["id"] for p in PRIZES if not (p.get("jackpot") or p.get("achievement"))]
        return 1 if all(tavern.prizes.get(pid) for pid in shop) else 0
    return tavern.stats.get(st, 0)


def check(farm, tavern):
    """Отмечает выполненные достижения. Возвращает список только что выполненных (для тоста).
    Трофей за достижение выдаётся сразу (жетоны — по кнопке «Забрать»)."""
    new = []
    for a in ACHIEVEMENTS:
        if a["id"] in tavern.ach_done:
            continue
        if value(a, farm, tavern) >= a["target"]:
            tavern.ach_done.append(a["id"])
            if a["prize"]:
                tavern.prizes[a["prize"]] = True
            new.append(a)
    return new


def claimable(tavern):
    return [aid for aid in tavern.ach_done if aid not in tavern.ach_claimed and aid in BY_ID]


def claim(tavern, aid):
    """Забрать жетоны за выполненное достижение. Возвращает число жетонов (0 — нечего забирать)."""
    if aid not in tavern.ach_done or aid in tavern.ach_claimed or aid not in BY_ID:
        return 0
    tavern.ach_claimed.append(aid)
    tokens = BY_ID[aid]["tokens"]
    tavern.tokens += tokens
    return tokens


def claim_all(tavern):
    return sum(claim(tavern, aid) for aid in claimable(tavern))
