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
