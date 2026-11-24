# -*- coding: utf-8 -*-
"""Баланс и данные игры: числа, культуры, животные, деревья улучшений, фермы. Без графики."""
import math
import os
import sys

W, H = 1000, 640
FPS = 60
GAME_VERSION = "3.26"   # версия игры: видна в «Настройках» и в заголовке окна
SAVE_VERSION = 2
DEV = "--dev" in sys.argv     # режим разработчика: python farm_idle.py --dev
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # папка, где лежит farm_idle.py
ASSET_DIR = os.path.join(BASE_DIR, "assets")
SAVE_FILE = os.path.join(BASE_DIR,
                         "farm_save_dev.json" if DEV else "farm_save.json")

# ======================================================================
#                               БАЛАНС
# ======================================================================
# cost — цена первого уровня, mult — рост цены за уровень,
# income — доход за цикл на 1 уровень, time — длительность цикла (сек),
# farmer — цена фермера (грядка растёт без остановки, урожай копится на ней)
CROPS = [
    dict(name="Картофель", cost=4,             mult=1.07, income=3,             time=1.0,   farmer=1_000),
    dict(name="Морковь",   cost=60,            mult=1.15, income=60,            time=3.0,   farmer=15_000),
    dict(name="Пшеница",   cost=720,           mult=1.14, income=540,           time=6.0,   farmer=100_000),
    dict(name="Томаты",    cost=8_640,         mult=1.13, income=4_320,         time=12.0,  farmer=500_000),
    dict(name="Огурцы",    cost=103_680,       mult=1.12, income=51_840,        time=24.0,  farmer=1_200_000),
    dict(name="Кукуруза",  cost=1_244_160,     mult=1.11, income=622_080,       time=48.0,  farmer=10_000_000),
    dict(name="Свёкла",    cost=14_929_920,    mult=1.10, income=7_464_960,     time=96.0,  farmer=111_111_111),
    dict(name="Капуста",   cost=179_159_040,   mult=1.09, income=89_579_520,    time=192.0, farmer=555_555_555),
    dict(name="Тыква",     cost=2_149_908_480, mult=1.08, income=1_074_954_240, time=384.0, farmer=10_000_000_000),
]
N_CROPS = len(CROPS)

# Вехи: на каждой рост ускоряется в 2 раза (когда цикл короче MIN_CYCLE — прибыль x2)
MILESTONES = [10, 25, 50, 100, 150, 200, 300, 400, 500, 600, 700, 800, 900, 1000] + list(range(1250, 10001, 250))
MIN_CYCLE = 0.25

FERT_BASE = 2_500      # первое удобрение стоит cost * FERT_BASE
FERT_STEP = 1_000      # каждое следующее дороже в FERT_STEP раз

# Грузовик / престиж: листья = floor(10 * sqrt(заработано_за_забег / 1B))
LEAF_UNIT = 1_000_000_000
LEAF_FACTOR = 10
LEAF_BONUS = 0.02      # +2% дохода за каждый лист
TRUCK_MIN_LEAVES = 5   # грузовик приезжает, когда можно получить хотя бы столько

RAIN_TIME, RAIN_COOLDOWN, RAIN_SPEED = 60.0, 240.0, 2.0
SUN_COOLDOWN, SUN_SECONDS, SUN_MIN = 180.0, 60.0, 25.0
# Белка: появляется раз в SQUIRREL_MIN..SQUIRREL_MAX секунд,
# награда = SQUIRREL_SHARE * (доход за SQUIRREL_SECONDS), дождь не учитывается
SQUIRREL_MIN, SQUIRREL_MAX = 120.0, 300.0
SQUIRREL_SHARE, SQUIRREL_SECONDS, SQUIRREL_REWARD_MIN = 0.40, 300.0, 50.0
SQUIRREL_SPEED, SQUIRREL_SIT = 170.0, 1.6
GOLDEN_CHANCE, GOLDEN_MULT = 0.10, 5          # золотая белка: шанс и множитель награды

# 3.8: песни барда — заказываются в таверне за жетоны, играют song minutes минут (идут и в офлайне, как буст x2).
# Одновременно играет одна песня. income — множитель дохода грядок, squirrel — белки чаще во столько раз,
# golden — шанс золотой белки во столько раз.
SONGS = [
    dict(id=1, name="Весёлая плясовая", cost=5, minutes=15, income=1.25, squirrel=1.0, golden=1.0,
         effect="доход грядок +25%", line="Эх, раз, ещё раз! Ноги сами в пляс!"),
    dict(id=2, name="Баллада о золотой белке", cost=10, minutes=15, income=1.0, squirrel=2.0, golden=3.0,
         effect="белки вдвое чаще, золотые — втрое", line="Слушайте, люди, сказ о белке золотой..."),
    dict(id=3, name="Гимн урожаю", cost=20, minutes=30, income=1.5, squirrel=1.0, golden=1.0,
         effect="доход грядок +50%", line="Славься, поле, славься, хлеб! Королю и нам на век!"),
]
# 3.14: казино для игроков. Открывается навсегда, когда жетонов впервые набирается CASINO_UNLOCK_TOKENS
CASINO_UNLOCK_TOKENS = 100
# Призовая стойка таверны — только косметика (решение автора 24.11: «магазин таверны — исключительно косметика»):
# kind — trophy (навсегда, встаёт в таверне), cosmetic (навсегда, вкл/выкл). Бафы «Счастливая монета» и «Клевер»
# (3.14–3.17) убраны.
PRIZES = [
    dict(id="horseshoe", kind="trophy", name="Бронзовая подкова", cost=50, text="первый трофей для таверны"),
    dict(id="cup", kind="trophy", name="Серебряный кубок", cost=150, text="кубок удачливого фермера"),
    dict(id="statue", kind="trophy", name="Золотой крестьянин", cost=500, text="статуэтка с кривым зубом"),
    dict(id="crystal", kind="trophy", name="Хрустальный колос", cost=1500, text="для настоящих завсегдатаев"),
    dict(id="gold_notes", kind="cosmetic", name="Нарядные ноты", cost=80, text="ноты барда золотые и блестят"),
    dict(id="gold_trail", kind="cosmetic", name="Золотой шлейф", cost=120, text="за курсором тянется золото"),
    dict(id="garland", kind="cosmetic", name="Гирлянда в таверне", cost=200, text="огоньки под балконом таверны"),
    # 3.19: уют у камина (видно в зале и в «посиделках у камина»)
    dict(id="flowers", kind="cosmetic", name="Полевые цветы", cost=60, text="кувшин с цветами на столе в зале"),
    dict(id="rug", kind="cosmetic", name="Коврик у огня", cost=90, text="тканый коврик — когда сидишь у камина"),
    dict(id="kettle", kind="cosmetic", name="Котелок над огнём", cost=120, text="булькает над огнём и пускает пар"),
    dict(id="cat", kind="cosmetic", name="Кот у камина", cost=150, text="спит у огня; его можно погладить"),
    dict(id="bard_girl", kind="cosmetic", name="Певица Мила", cost=300, stage="tavern_girl", timing="music_girl",
         text="крестьянка поёт свою песню вместо барда"),
    # 3.23: ещё артисты на сцену. stage — имя своей песни (assets/music/<имя>.ogg; нет файла — музыка таверны),
    # timing — ключ темпа в разметке таверны. На сцене один артист: включил одного — остальные выключились.
    dict(id="fiddler", kind="cosmetic", name="Скрипач Тимоха", cost=400, stage="tavern_fiddler", timing="music_fiddler",
         text="весёлый парень со скрипкой вместо барда"),
    dict(id="bagpiper", kind="cosmetic", name="Волынщик Ерёма", cost=500, stage="tavern_bagpipe", timing="music_bagpipe",
         text="старый волынщик с бородой до пояса"),
]
# лист призов 3×3 (assets/icons/prizes) — порядок клеток картинки пользователя (23.11), не зависит от PRIZES
PRIZE_SHEET_IDS = ["horseshoe", "cup", "statue", "crystal", "lucky_coin", "clover", "gold_notes", "gold_trail", "garland"]
GOLDEN_SPEED, GOLDEN_SIT = 1.35, 1.0          # она быстрее и сидит меньше
# Ворона: реже белки, останавливает грядку, пока её не прогонят (только пока игра открыта)
CROW_MIN, CROW_MAX = 300.0, 600.0
OFFLINE_CAP = 3 * 3600
OFFLINE_AUTOMATION = True   # в офлайне скотники кормят зверей, мельники и пекари работают — как при открытой игре.
                            # False — как до версии 2.8: звери только доедают кормушку, мельница домалывает закрома.
OFFLINE_STEP = 5.0          # шаг офлайн-расчёта, с (кратен походу скотника и партии хлеба)
MONEY_CAP = 1e300           # потолок денег: дальше числа с плавающей точкой превращаются в «бесконечность»
# Переезд на новую ферму
MOVE_THRESHOLD = 1e15   # $1aa за один забег
FARM_BONUS = 2          # каждая пройденная ферма: доход x2 навсегда (кроме трофея — единственное, что переносится)
FARM_PRICE = 1          # множитель цен новой фермы. При переезде ВСЁ начинается с нуля (деньги,
                        # валюта престижа, дерево), поэтому дополнительная инфляция не нужна.
TROPHY_START_LEVEL = 10 # трофей летней фермы «Золотая картофелина»: первая грядка новой фермы сразу 10 ур.
# Средневековое поле: крестьяне, мельница с пекарней, разбойники
PEASANT_START = 1               # бесплатных крестьян в начале забега
PEASANT_BASE, PEASANT_STEP = 400, 9   # цена найма: 400, 3.6K, 32K, ... (каждый следующий x9)
PEASANT_MAX = 16
GRAIN = [2, 4, 7]               # зерновые грядки средневековья: рожь, ячмень, полба
MILL_EAT = 0.2                  # 1 мельник перемалывает 20% того, что дают зерновые грядки: полная мельница
                                # (5 мельников) мелет всё зерно. До 3.6 было 0.4 — и 4-5 уровни ничего не давали
FLOUR_RATIO, BREAD_RATIO = 1.5, 2.5   # мука дороже зерна в 1.5 раза, хлеб дороже муки в 2.5 раза
BAKE_TIME = 20.0                # пекарня печёт партиями: одна партия = 20 с
BAKE_SPEED = 1.0                # 1 пекарь успевает за 1 мельником (до 3.6 было 0.5 при мельнике 0.4 — то же самое)
MILL_COST = [20_000, 1_000_000]       # мельница, пекарня (каждый уровень = +1 место, дороже в MILL_LVL_MULT)
MILL_LVL_MULT, MILL_MAX_LVL = 8, 5
HOPPER_SECONDS = 60               # 3.13: закрома = минута помола нынешних мельников (мельники сами держат их полными)
BANDIT_MIN, BANDIT_MAX = 150.0, 300.0
BANDIT_STEAL, BANDIT_TIME = 0.15, 25.0   # крадёт 15% урожая грядки в секунду, через 25 с убегает с мешком
# Мороз (зимняя ферма): замораживает грядки, лёд разбивается FROST_HITS кликами
FROST_MIN, FROST_MAX, FROST_HITS = 90.0, 180.0, 3


def safe_pow(a, b):
    try:
        return a ** b
    except OverflowError:
        return float("inf")


def next_milestone(level):
    for m in MILESTONES:
        if m > level:
            return m
    return None


def prev_milestone(level):
    p = 0
    for m in MILESTONES:
        if m <= level:
            p = m
    return p


SUFFIXES = ["", "K", "M", "B", "T"]


def fmt(n):
    """1234567 -> 1.23M, дальше T идут aa, ab, ac ..."""
    if n != n or n == float("inf"):
        return "∞"
    if n < 1000:
        return f"{n:.0f}" if n >= 100 or float(n).is_integer() else f"{n:.1f}"
    e = int(math.log10(n) // 3)
    v = n / 1000 ** e
    if v >= 999.995:
        e += 1
        v = n / 1000 ** e
    if e < len(SUFFIXES):
        suf = SUFFIXES[e]
    else:
        k = e - len(SUFFIXES)
        suf = chr(97 + (k // 26) % 26) + chr(97 + k % 26)
    return f"{v:.2f}{suf}"


def fmt_mult(leaves):
    v = 1 + LEAF_BONUS * leaves
    return f"x{v:.2f}" if v < 1000 else "x" + fmt(v)


def fmt_time(sec):
    sec = int(max(0, sec))
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ======================================================================
#                          САРАЙ С ЖИВОТНЫМИ
# ======================================================================
# crop — какую грядку ест (индекс в CROPS), ratio — во сколько раз продукт дороже корма,
# time — цикл производства, cost — цена покупки (каждый уровень дороже в ANIMAL_LVL_MULT раз),
# keeper — цена скотника (сам перекладывает урожай с грядки в кормушку)
ANIMALS_SUMMER = [   # key — имя картинки animals/<key>, icon — картинка продукта icons/<icon>
    dict(key="chicken", icon="egg", name="Курица", product="Яйца", crop=0, ratio=2.0, time=6.0, cost=500,
         keeper=25_000),
    dict(key="cow", icon="milk", name="Корова", product="Молоко", crop=2, ratio=2.5, time=10.0, cost=100_000,
         keeper=5_000_000),
    dict(key="pig", icon="truffle", name="Свинья", product="Трюфели", crop=5, ratio=3.0, time=15.0, cost=200_000_000,
         keeper=5_000_000_000),
    dict(key="bees", icon="honey", name="Пчёлы", product="Мёд", crop=6, ratio=4.0, time=20.0, cost=3_000_000_000,
         keeper=100_000_000_000),
]
# 3.24: зимний сарай (глава 3) — звери едят зимние грядки 0, 2, 5, 6; цены и время — как летом
ANIMALS_WINTER = [
    dict(ANIMALS_SUMMER[0], key="goose", icon="down", name="Гусь", product="Гусиный пух"),           # ест клюкву
    dict(ANIMALS_SUMMER[1], key="yak", icon="wool", name="Як", product="Шерсть яка"),                # ест кейл
    dict(ANIMALS_SUMMER[2], key="reindeer", icon="cheese", name="Северный олень", product="Олений сыр"),  # морошку
    dict(ANIMALS_SUMMER[3], key="bearcub", icon="jam", name="Медвежонок", product="Облепиховое варенье"),  # облепиху
]
ANIMAL_SETS = {"summer": ANIMALS_SUMMER, "winter": ANIMALS_WINTER}
ANIMALS = [dict(a) for a in ANIMALS_SUMMER]   # звери текущей фермы (меняет apply_farm, на месте)
N_ANIMALS = len(ANIMALS)
ANIMAL_MAX_LVL = 10
ANIMAL_LVL_MULT = 1.8
ANIMAL_EAT = 0.3        # на 1 уровне животное съедает 30% того, что производит его грядка
ANIMAL_FOOD_STEP = 0.9  # каждый уровень: еды нужно на 10% меньше...
ANIMAL_VALUE_STEP = 1.3 # ...а продукт из неё на 30% дороже (ур.10: еды 39% от ур.1, продукт x10.6 от базы)
FEEDER_SECONDS = 120    # кормушка вмещает 2 минуты еды
KEEPER_INTERVAL = 5.0   # скотник ходит за урожаем раз в 5 секунд (а не каждый кадр)


# ======================================================================
#                      ДЕРЕВО УЛУЧШЕНИЙ ЗА ЛИСТЬЯ
# ======================================================================
def start_money(lvl):
    return 0.0 if lvl == 0 else 4 * 30.0 ** lvl           # $120, $3.6K, $108K, $3.2M, $97M (меньше порога грузовика)


def _rain_time(l): return RAIN_TIME + 20 * l
def _rain_cd(l): return RAIN_COOLDOWN * (1 - 0.2 * l)
def _rain_speed(l): return RAIN_SPEED + 0.5 * l


# Ветки дерева. Узел открывается, когда у предыдущего в ветке есть хотя бы 1 уровень.
# costs — цена каждого уровня в валюте престижа, eff(уровень) — текст эффекта.
# Одинаковые id на разных фермах дают одинаковый эффект (capital, fertile, lucky, rain_*, offline, truck, sq_often).
TREE_SUMMER = [
    ("Урожай", [
        dict(id="capital", name="Стартовый капитал", costs=[3, 10, 30, 90, 270],
             eff=lambda l: f"забег начинается с ${fmt(start_money(l))}"),
        dict(id="farmers", name="Наёмные фермеры", costs=[5, 10, 20, 40, 80, 160, 320, 640, 1280],
             eff=lambda l: f"бесплатный фермер на первых {l} грядках" if l else "бесплатных фермеров нет"),
        dict(id="lucky", name="Счастливый урожай", costs=[8, 24, 72, 216, 648],
             eff=lambda l: f"{2 * l}% шанс собрать гигантский урожай x10"),
        dict(id="fertile", name="Плодородие", costs=[20, 80, 320, 1280, 5120],
             eff=lambda l: f"весь доход x{2 ** l}"),
    ]),
    ("Погода", [
        dict(id="rain_len", name="Затяжной дождь", costs=[3, 9, 27],
             eff=lambda l: f"дождь длится {_rain_time(l):.0f} с"),
        dict(id="rain_cd", name="Тучка рядом", costs=[5, 15, 45],
             eff=lambda l: f"дождь перезаряжается за {fmt_time(_rain_cd(l))}"),
        dict(id="rain_power", name="Тёплый дождь", costs=[30, 120],
             eff=lambda l: f"в дождь всё растёт x{_rain_speed(l):g}"),
        dict(id="sun", name="Яркое солнце", costs=[6, 18, 54],
             eff=lambda l: f"солнце даёт {SUN_SECONDS + 30 * l:g} с дохода"),
    ]),
    ("Звери", [
        dict(id="sq_often", name="Орешки для белок", costs=[4, 12, 36],
             eff=lambda l: f"белка раз в {SQUIRREL_MIN * 0.9 ** l / 60:.1f}-{SQUIRREL_MAX * 0.9 ** l / 60:.1f} мин"),
        dict(id="sq_sit", name="Ленивые белки", costs=[8, 24],
             eff=lambda l: f"белка сидит {SQUIRREL_SIT + l:g} с (золотая {GOLDEN_SIT + l:g} с)"),
        dict(id="golden", name="Золотые жёлуди", costs=[10, 30, 90, 270],
             eff=lambda l: f"золотая белка в {round((GOLDEN_CHANCE + 0.04 * l) * 100)}% случаев"),
        dict(id="scarecrow", name="Пугало", costs=[6, 18, 54],
             eff=lambda l: f"ворона раз в {CROW_MIN * 1.5 ** l / 60:.1f}-{CROW_MAX * 1.5 ** l / 60:.1f} мин"),
    ]),
    ("Склад", [
        dict(id="offline", name="Большой амбар", costs=[3, 6, 12, 24, 48],
             eff=lambda l: f"урожай копится офлайн до {(OFFLINE_CAP + 7200 * l) // 3600} ч"),
        dict(id="truck", name="Щедрый скупщик", costs=[15, 45, 135, 405, 1215],
             eff=lambda l: f"листьев от грузовика +{10 * l}%"),
    ]),
]
TREE_MEDIEVAL = [
    ("Казна", [
        dict(id="capital", name="Королевская казна", costs=[3, 10, 30, 90, 270],
             eff=lambda l: f"забег начинается с ${fmt(start_money(l))}"),
        dict(id="serfs", name="Крепостные", costs=[4, 12, 36, 108, 324],
             eff=lambda l: f"бесплатных крестьян в начале: {PEASANT_START + l}"),
        dict(id="fertile", name="Королевский указ", costs=[20, 80, 320, 1280, 5120],
             eff=lambda l: f"весь доход x{2 ** l}"),
        dict(id="lucky", name="Урожайный год", costs=[8, 24, 72, 216, 648],
             eff=lambda l: f"{2 * l}% шанс собрать гигантский урожай x10"),
    ]),
    ("Мельница", [
        dict(id="diligence", name="Трудолюбие", costs=[5, 15, 45, 135],
             eff=lambda l: f"мельники и пекари работают на {25 * l}% быстрее"),
        dict(id="hopper", name="Большие закрома", costs=[6, 18, 54],
             eff=lambda l: f"закрома мельницы x{2 ** l}"),
        dict(id="baker", name="Королевский пекарь", costs=[10, 30, 90, 270],
             eff=lambda l: f"хлеб дороже на {25 * l}%"),
    ]),
    ("Защита", [
        dict(id="guards", name="Стража", costs=[5, 15, 45],
             eff=lambda l: f"разбойники раз в {BANDIT_MIN * 1.5 ** l / 60:.1f}-{BANDIT_MAX * 1.5 ** l / 60:.1f} мин"),
        dict(id="traps", name="Капканы", costs=[6, 18],
             eff=lambda l: f"разбойники крадут {BANDIT_STEAL * 0.7 ** l * 100:.0f}% в секунду"),
        dict(id="rain_len", name="Долгие гуляния", costs=[3, 9, 27],
             eff=lambda l: f"праздник урожая длится {_rain_time(l):.0f} с"),
        dict(id="rain_cd", name="Глашатай", costs=[5, 15, 45],
             eff=lambda l: f"новый праздник через {fmt_time(_rain_cd(l))}"),
    ]),
    ("Торговля", [
        dict(id="offline", name="Погреба", costs=[3, 6, 12, 24, 48],
             eff=lambda l: f"урожай копится офлайн до {(OFFLINE_CAP + 7200 * l) // 3600} ч"),
        dict(id="truck", name="Ярмарка", costs=[15, 45, 135, 405, 1215],
             eff=lambda l: f"печатей от сборщика +{10 * l}%"),
        dict(id="sq_often", name="Орешки для белок", costs=[4, 12, 36],
             eff=lambda l: f"белка раз в {SQUIRREL_MIN * 0.9 ** l / 60:.1f}-{SQUIRREL_MAX * 0.9 ** l / 60:.1f} мин"),
    ]),
]


def _index_tree(tree):
    nodes = {}
    for _bname, _nodes in tree:
        for _ni, _node in enumerate(_nodes):
            _node["prev"] = _nodes[_ni - 1]["id"] if _ni else None
            nodes[_node["id"]] = _node
    return nodes


GNOME_RUSH = "Гномье пришествие"   # 3.26: зимняя «погода» (была «Оттепель», решение пользователя 24.11)


def _winter_tree():
    """3.24: Зимнее дерево — пока как Дерево листьев (те же эффекты), ветка погоды — «Гномье пришествие» (3.26)."""
    out = []
    for bname, nodes in TREE_SUMMER:
        out.append((GNOME_RUSH if bname == "Погода" else bname, [dict(n) for n in nodes]))
    return out


TREE_WINTER = _winter_tree()
TREES = {"summer": TREE_SUMMER, "medieval": TREE_MEDIEVAL, "winter": TREE_WINTER}
TREE_NODE_MAP = {key: _index_tree(t) for key, t in TREES.items()}
TREE = list(TREE_SUMMER)                      # дерево текущей фермы (переключает apply_farm)
TREE_NODES = dict(TREE_NODE_MAP["summer"])


# ======================================================================
#                    ФЕРМЫ (ГЛАВЫ) И ИХ ОФОРМЛЕНИЕ
# ======================================================================
TRUCK_TIERS = [
    ("Пикап скупщика", (80, 150, 230), 0),
    ("Грузовик скупщика", (230, 80, 70), 50),
    ("Золотая фура", (245, 195, 40), 500),
]

THEME_MEDIEVAL = dict(ground=(146, 182, 96), ground2=(160, 194, 108), path=(196, 165, 120), path_edge=(170, 140, 100),
                      path2=(182, 150, 108), tree=(80, 135, 75), tree_light=(110, 165, 95), bush=(85, 140, 80),
                      bush_light=(115, 170, 105), tuft=(90, 135, 75), stone=(170, 165, 158),
                      soil=(170, 118, 78), soil_dark=(145, 98, 62), soil_side=(118, 80, 52), snow=False,
                      wall=True, building="mill", castle=True)
THEME_SUMMER = dict(ground=(156, 222, 118), ground2=(168, 230, 130), path=(245, 230, 140), path_edge=(232, 212, 120),
                    path2=(235, 215, 120), tree=(70, 165, 120), tree_light=(100, 195, 145), bush=(70, 170, 125),
                    bush_light=(105, 200, 150), tuft=(80, 170, 110), stone=(215, 195, 200),
                    soil=(226, 146, 86), soil_dark=(198, 118, 64), soil_side=(168, 98, 55), snow=False)
THEME_WINTER = dict(ground=(228, 238, 250), ground2=(244, 249, 255), path=(205, 220, 236), path_edge=(185, 204, 226),
                    path2=(216, 229, 242), tree=(70, 130, 125), tree_light=(245, 250, 255), bush=(95, 145, 145),
                    bush_light=(245, 250, 255), tuft=(150, 180, 195), stone=(190, 200, 215),
                    soil=(196, 150, 128), soil_dark=(170, 125, 105), soil_side=(140, 98, 82), snow=True)
CURRENCIES = {
    "leaf": dict(icon="leaf", title="Листья", gen="листьев", one="лист", tree="ДЕРЕВО ЛИСТЬЕВ"),
    "seal": dict(icon="seal", title="Печати", gen="печатей", one="печать", tree="ПРИВИЛЕГИИ КОРОЛЯ"),
    # 3.24: зима — голубые листочки и Зимнее дерево (решение пользователя 24.11)
    "frost": dict(icon="frostleaf", title="Голубые листочки", gen="голубых листочков", one="голубой листочек",
                  tree="ЗИМНЕЕ ДЕРЕВО", short="Листочки"),   # short — подпись кнопки внизу (полное не влезает)
}
_SUMMER_BUYER = dict(buyer="скупщик", buyer_cap="Скупщик", arrive="Би-би! Приехал скупщик урожая!",
                     tiers=["Пикап скупщика", "Грузовик скупщика", "Золотая фура"], vehicle="truck")
# 3.25: помощники-артель (крестьяне в средневековье, гномы зимой): как их называть и какой значок
HELPERS = {
    "peasants": dict(title="Крестьяне", gen="крестьян", one="крестьянин", acc="крестьянина", icon="peasant",
                     plural=("крестьянина", "крестьянина", "крестьян")),
    "gnomes": dict(title="Гномы", gen="гномов", one="гном", acc="гнома", icon="gnome",
                   plural=("гнома", "гнома", "гномов")),
}
WEATHER_BUTTON = {"Праздник урожая": "festival", GNOME_RUSH: "shaman"}   # погода кнопкой (не тучкой): имя кнопки
# 3.26: «Гномье пришествие» — из леса выходят ещё гномы и работают на ВСЕХ грядках (и без своего гнома),
# а на лужайке справа гномы-шаманы пляшут с бубнами. Кнопка — ui/btn_shaman, гномы — characters/gnome_*.
SHAMAN_SPOTS = [(862, 372), (936, 418)]    # где пляшут шаманы (лужайка справа от поля, логические координаты)
FARMS = [
    dict(id="summer", name="Летняя ферма", names=[c["name"] for c in CROPS],
         plants=["potato", "carrot", "wheat", "tomato", "cucumber", "corn", "beet", "cabbage", "pumpkin"],
         theme=THEME_SUMMER, weather="Дождь", crow=True, frost=False, bandits=False, peasants=False,
         barn="animals", tree="summer", cur="leaf", ready=True,
         trophy=dict(name="Золотая картофелина", text="первая грядка новой фермы сразу 10 уровня"), **_SUMMER_BUYER),
    dict(id="medieval", name="Средневековое поле",
         names=["Репа", "Горох", "Рожь", "Капуста", "Ячмень", "Лён", "Хмель", "Полба", "Виноград"],
         plants=["turnip", "peas", "rye", "cabbage", "barley", "flax", "hops", "spelt", "grapes"],
         theme=THEME_MEDIEVAL, weather="Праздник урожая", crow=False, frost=False, bandits=True, peasants=True,
         helpers="peasants",
         barn="mill", tree="medieval", cur="seal", ready=True,
         trophy=dict(name="Королевский штандарт", text="(для следующей главы)"),
         buyer="сборщик податей", buyer_cap="Сборщик податей", arrive="Трубы трубят! Прибыл сборщик податей!",
         tiers=["Телега сборщика", "Обоз сборщика", "Королевский обоз"], vehicle="cart"),
    # 3-я глава (решения пользователя 24.11): зимнее поле, яркие зимние растения, сарай остаётся (звери под
    # зимние грядки), голубые листочки и Зимнее дерево, за урожаем приезжает собачья упряжка. Пока закрыта.
    dict(id="winter", name="Зимнее поле",
         names=["Клюква", "Имбирь", "Фиолетовый кейл", "Морозная мята", "Арбузная редиска", "Морошка", "Облепиха",
                "Голубой картофель", "Ледяная тыква"],
         plants=["cranberry", "ginger", "kale", "frostmint", "pinkradish", "cloudberry", "seabuckthorn", "bluepotato",
                 "icepumpkin"],
         # 3.25 (решения пользователя): помощники — гномы, как крестьяне (общая артель); вместо дождя — кнопка
         # «Гномье пришествие» (3.26, было «Оттепель»), как «Праздник урожая» в средневековье;
         # rush_helpers: пока оно идёт, все грядки работают сами, будто на каждой стоит гном
         theme=THEME_WINTER, weather=GNOME_RUSH, rush_helpers=True, crow=False, frost=True, bandits=False, peasants=True,
         helpers="gnomes", barn="animals", animals="winter", tree="winter", cur="frost", ready=False,
         trophy=dict(name="Снежинка", text=""),
         buyer="каюр", buyer_cap="Каюр", arrive="Гав-гав! Примчалась собачья упряжка!",
         tiers=["Упряжка из трёх лаек", "Упряжка из шести лаек", "Королевская упряжка"], vehicle="sled"),
]
THEME = dict(THEME_SUMMER)
CUR = dict(CURRENCIES["leaf"])
