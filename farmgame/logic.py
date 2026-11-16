# -*- coding: utf-8 -*-
"""Логика фермы (класс Farm): доход, покупки, сарай, мельница, крестьяне, престиж. Без графики."""
import bisect
import math
import random

from .config import *  # noqa: F401,F403
from .config import _rain_time, _rain_cd, _rain_speed

# ======================================================================
#                          ЛОГИКА (без графики)
# ======================================================================
class Farm:
    def __init__(self):
        self.reset_all()

    def reset_all(self):
        self.leaves = 0              # все непотраченные листья (их можно тратить в дереве)
        self.home_leaves = 0         # из них заработаны на ЭТОЙ ферме — только они дают +2% дохода
        self.leaves_earned = 0       # сколько всего получено за всю игру
        self.tree = {}               # id улучшения -> уровень (не сбрасывается грузовиком)
        self.last_lucky = False
        self.farm_index = 0          # 0 — летняя ферма, 1 — средневековое поле, 2 — зима (позже)
        self.prestiges = 0
        self.total_earned = 0.0
        self.rain_left = 0.0
        self.rain_cd = 0.0
        self.sun_cd = SUN_COOLDOWN / 3
        self.boost_left = 0.0        # награда таверны: доход x2, секунд осталось
        self.reset_run()

    def reset_run(self):
        self.money = start_money(self.up("capital")) * FARM_PRICE ** self.farm_index
        self.run_earned = 0.0
        self.levels = [1] + [0] * (N_CROPS - 1)
        if self.farm_index >= 1:          # трофей летней фермы «Золотая картофелина»
            self.levels[0] = TROPHY_START_LEVEL
        self.fert = [0] * N_CROPS
        self.farmers = [False] * N_CROPS
        self.progress = [0.0] * N_CROPS
        self.ready = [False] * N_CROPS      # грядка без фермера созрела и ждёт сбора
        self.stash = [0.0] * N_CROPS        # урожай, накопленный на грядке (ещё не в банке)
        self.blocked = [False] * N_CROPS    # на грядке сидит ворона (не сохраняется)
        self.frozen = [0] * N_CROPS         # грядка во льду: сколько ударов осталось (не сохраняется)
        self.farmers[0] = self.up("farmers") >= 1
        # средневековье: крестьяне (farmers[i] = на грядке стоит крестьянин), мельница и пекарня
        self.peasants = PEASANT_START + self.up("serfs")
        self.m_levels = [0, 0]              # мельница, пекарня (уровень = мест для работников)
        self.m_workers = [0, 0]
        self.hopper = 0.0                   # зерно в закромах мельницы (в $)
        self.flour = 0.0
        self.bread = 0.0                    # готовый хлеб, ждёт сбора
        self.oven_load = 0.0                # мука в печи (текущая партия)
        self.oven_prog = 0.0
        self.oven_wait = 0.0                # сколько печь ждёт муку на полную партию
        self.m_carry_t = 0.0
        # сарай
        self.a_levels = [0] * N_ANIMALS
        self.a_feed = [0.0] * N_ANIMALS     # корм в кормушке (в деньгах)
        self.a_prog = [0.0] * N_ANIMALS
        self.a_store = [0.0] * N_ANIMALS    # готовые продукты (в деньгах), ждут сбора
        self.a_keeper = [False] * N_ANIMALS
        self.a_keeper_t = [0.0] * N_ANIMALS  # сколько прошло с прошлого похода скотника

    # ---------- дерево листьев ----------
    def up(self, node_id):
        return self.tree.get(node_id, 0)

    def farm_def(self):
        return FARMS[min(self.farm_index, len(FARMS) - 1)]

    def nodes(self):
        return TREE_NODE_MAP[self.farm_def()["tree"]]

    def tree_cost(self, node_id):
        node = self.nodes()[node_id]
        lvl = self.up(node_id)
        return node["costs"][lvl] if lvl < len(node["costs"]) else None

    def tree_available(self, node_id):
        prev = self.nodes()[node_id]["prev"]
        return prev is None or self.up(prev) >= 1

    def can_buy_tree(self, node_id):
        cost = self.tree_cost(node_id)
        return cost is not None and self.tree_available(node_id) and self.leaves >= cost

    def buy_tree(self, node_id):
        if not self.can_buy_tree(node_id):
            return False
        cost = self.tree_cost(node_id)
        old = self.leaves - self.home_leaves          # сначала тратятся листья с прошлых ферм
        self.home_leaves -= max(0, cost - old)
        self.leaves -= cost
        self.tree[node_id] = self.up(node_id) + 1
        if node_id == "serfs":
            self.peasants += 1
        if node_id == "farmers":  # сразу нанимаем на уже посаженных грядках
            for i in range(min(N_CROPS, self.up("farmers"))):
                if self.levels[i] > 0 and not self.farmers[i]:
                    self.farmers[i] = True
                    if self.ready[i]:
                        self.ready[i] = False
                        self.progress[i] = 0.0
        return True

    # ---------- цены текущей фермы ----------
    @property
    def price_mult(self):
        return FARM_PRICE ** self.farm_index

    def farmer_cost(self, i):
        return CROPS[i]["farmer"] * self.price_mult

    def keeper_cost(self, a):
        return ANIMALS[a]["keeper"] * self.price_mult

    def move_threshold(self):
        return MOVE_THRESHOLD * self.price_mult

    def any_tree_affordable(self):
        return any(self.can_buy_tree(n) for n in self.nodes())
    # ---------- доход ----------
    @property
    def leaf_mult(self):
        return 1 + LEAF_BONUS * self.home_leaves

    def speed_steps(self, i):
        return bisect.bisect_right(MILESTONES, self.levels[i])

    def _raw_time(self, i):
        return CROPS[i]["time"] / (2 ** self.speed_steps(i))

    def cycle_time(self, i):
        return max(MIN_CYCLE, self._raw_time(i))

    def overflow_mult(self, i):
        return max(1.0, MIN_CYCLE / self._raw_time(i))

    def cycle_income(self, i):
        c = CROPS[i]
        return (c["income"] * self.levels[i] * safe_pow(3, self.fert[i]) * self.overflow_mult(i)
                * self.leaf_mult * 2 ** self.up("fertile") * FARM_BONUS ** self.farm_index
                * (2 if self.boost_left > 0 else 1))

    def growth_speed(self):
        return _rain_speed(self.up("rain_power")) if self.rain_left > 0 else 1.0

    # ---------- сарай ----------
    def eat_rate(self, a, lvl=None):
        """Сколько корма (в $) животное съедает в секунду. С каждым уровнем — меньше."""
        lvl = self.a_levels[a] if lvl is None else lvl
        if lvl <= 0:
            return 0.0
        crop = ANIMALS[a]["crop"]
        return self.income_per_sec(crop, with_rain=False) * ANIMAL_EAT * ANIMAL_FOOD_STEP ** (lvl - 1)

    def feeder_cap(self, a):
        return self.eat_rate(a) * FEEDER_SECONDS

    def product_ratio(self, a, lvl=None):
        """Во сколько раз продукт дороже съеденного корма. С каждым уровнем — дороже."""
        lvl = self.a_levels[a] if lvl is None else lvl
        return ANIMALS[a]["ratio"] * ANIMAL_VALUE_STEP ** max(0, lvl - 1)

    def animal_income(self, a, lvl=None):
        """Сколько $ в секунду приносит животное (при полной кормушке)."""
        return self.eat_rate(a, lvl) * self.product_ratio(a, lvl)

    def animal_cost(self, a):
        return ANIMALS[a]["cost"] * ANIMAL_LVL_MULT ** self.a_levels[a] * self.price_mult

    def animal_crop_ready(self, a):
        return self.levels[ANIMALS[a]["crop"]] > 0

    def buy_animal(self, a):
        if self.a_levels[a] >= ANIMAL_MAX_LVL or not self.animal_crop_ready(a):
            return False
        price = self.animal_cost(a)
        if self.money < price:
            return False
        self.money -= price
        self.a_levels[a] += 1
        return True

    def buy_keeper(self, a):
        price = self.keeper_cost(a)
        if self.a_keeper[a] or self.a_levels[a] == 0 or self.money < price:
            return False
        self.money -= price
        self.a_keeper[a] = True
        return True

    def feed_animal(self, a):
        """Перекладывает урожай с грядки в кормушку (сколько влезет). Возвращает сколько."""
        if self.a_levels[a] == 0:
            return 0.0
        crop = ANIMALS[a]["crop"]
        take = min(self.stash[crop], max(0.0, self.feeder_cap(a) - self.a_feed[a]))
        if take <= 0:
            return 0.0
        self.stash[crop] -= take
        self.a_feed[a] += take
        if self.stash[crop] <= self.cycle_income(crop) * 1e-9 and not self.farmers[crop]:
            self.stash[crop] = 0.0
            self.ready[crop] = False
            self.progress[crop] = 0.0
        return take

    def collect_product(self, a):
        amt = self.a_store[a]
        if amt <= 0:
            return None
        self.earn(amt)
        self.a_store[a] = 0.0
        return amt

    def _run_animals(self, dt, use_keepers=True):
        for a in range(N_ANIMALS):
            if self.a_levels[a] == 0:
                continue
            if use_keepers and self.a_keeper[a]:
                self.a_keeper_t[a] += dt
                if self.a_keeper_t[a] >= KEEPER_INTERVAL:
                    self.a_keeper_t[a] = 0.0
                    self.feed_animal(a)
            if self.a_feed[a] <= 0:
                continue
            t = ANIMALS[a]["time"]
            self.a_prog[a] += dt
            if self.a_prog[a] >= t:
                k = int(self.a_prog[a] // t)
                self.a_prog[a] -= k * t
                eaten = min(self.a_feed[a], self.eat_rate(a) * t * k)
                self.a_feed[a] -= eaten
                self.a_store[a] += eaten * self.product_ratio(a)
                if self.a_feed[a] <= 0:
                    self.a_feed[a] = 0.0
                    self.a_prog[a] = 0.0

    # ---------- крестьяне ----------
    def busy_peasants(self):
        return sum(1 for x in self.farmers if x) + sum(self.m_workers)

    def free_peasants(self):
        return self.peasants - self.busy_peasants()

    def peasant_cost(self):
        hired = self.peasants - PEASANT_START - self.up("serfs")
        return PEASANT_BASE * PEASANT_STEP ** max(0, hired) * self.price_mult

    def hire_peasant(self):
        price = self.peasant_cost()
        if self.peasants >= PEASANT_MAX or self.money < price:
            return False
        self.money -= price
        self.peasants += 1
        return True

    def toggle_peasant(self, i):
        """Поставить крестьянина на грядку или снять. Возвращает True, если что-то поменялось."""
        if self.levels[i] == 0:
            return False
        if self.farmers[i]:
            self.farmers[i] = False
            return True
        if self.free_peasants() <= 0:
            return False
        self.farmers[i] = True
        if self.ready[i]:
            self.ready[i] = False
            self.progress[i] = 0.0
        return True

    # ---------- мельница и пекарня ----------
    def grain_rate(self):
        return sum(self.income_per_sec(i, with_rain=False) for i in GRAIN if self.levels[i] > 0)

    def mill_speed(self):
        return MILL_EAT * self.grain_rate() * (1 + 0.25 * self.up("diligence"))

    def hopper_cap(self):
        return MILL_EAT * self.grain_rate() * max(1, self.m_levels[0]) * HOPPER_SECONDS * 2 ** self.up("hopper")

    def mill_building_cost(self, b):
        return MILL_COST[b] * MILL_LVL_MULT ** self.m_levels[b] * self.price_mult

    def mill_can_build(self, b):
        if b == 0:
            return self.levels[GRAIN[0]] > 0
        return self.m_levels[0] > 0

    def buy_mill_building(self, b):
        if self.m_levels[b] >= MILL_MAX_LVL or not self.mill_can_build(b):
            return False
        price = self.mill_building_cost(b)
        if self.money < price:
            return False
        self.money -= price
        self.m_levels[b] += 1
        return True

    def set_mill_workers(self, b, delta):
        new = self.m_workers[b] + delta
        if new < 0 or new > self.m_levels[b]:
            return False
        if delta > 0 and self.free_peasants() < delta:
            return False
        self.m_workers[b] = new
        return True

    def fill_hopper(self):
        """Засыпать зерно со всех зерновых грядок в закрома (сколько влезет)."""
        space = max(0.0, self.hopper_cap() - self.hopper)
        moved = 0.0
        for i in GRAIN:
            if space <= 0:
                break
            take = min(self.stash[i], space)
            if take <= 0:
                continue
            self.stash[i] -= take
            space -= take
            moved += take
            if self.stash[i] <= self.cycle_income(i) * 1e-9 and not self.farmers[i]:
                self.stash[i] = 0.0
                self.ready[i] = False
                self.progress[i] = 0.0
        self.hopper += moved
        return moved

    def _run_mill(self, dt, carry=True):
        if self.m_levels[0] == 0:
            return
        if carry and self.m_workers[0] > 0:      # мельники сами носят зерно раз в 5 с
            self.m_carry_t += dt
            if self.m_carry_t >= KEEPER_INTERVAL:
                self.m_carry_t = 0.0
                self.fill_hopper()
        g = min(self.hopper, self.mill_speed() * self.m_workers[0] * dt)
        self.hopper -= g
        self.flour += g * FLOUR_RATIO
        if self.m_levels[1] == 0 or self.m_workers[1] == 0:
            return
        ratio = BREAD_RATIO * (1 + 0.25 * self.up("baker"))
        if dt >= BAKE_TIME:   # офлайн / большой шаг: считаем без партий
            take = min(self.flour + self.oven_load, self.bake_rate() * dt)
            from_oven = min(self.oven_load, take)
            self.oven_load -= from_oven
            self.flour -= take - from_oven
            self.bread += take * ratio
            return
        full = self.bake_rate() * BAKE_TIME
        # новую партию ставим, когда муки хватает на полную печь; если мельница стоит
        # или ждём дольше 3 партий — печём что есть
        if self.oven_load <= 0 and self.flour > 0:
            self.oven_wait += dt
        if self.oven_load <= 0 and self.flour > 0 and (
                self.flour >= full or self.m_workers[0] == 0 or self.oven_wait >= BAKE_TIME * 3):
            self.oven_wait = 0.0
            load = min(self.flour, full)
            self.flour -= load
            self.oven_load = load
            self.oven_prog = 0.0
        if self.oven_load > 0:
            self.oven_prog += dt
            if self.oven_prog >= BAKE_TIME:
                self.bread += self.oven_load * ratio
                self.oven_load = 0.0
                self.oven_prog = 0.0

    def bake_rate(self):
        """Сколько муки (в $) пекарня перерабатывает в секунду."""
        return self.mill_speed() * FLOUR_RATIO * BAKE_SPEED * self.m_workers[1]

    def sell_flour(self):
        amt = self.flour
        if amt <= 0:
            return None
        self.earn(amt)
        self.flour = 0.0
        return amt

    def collect_bread(self):
        amt = self.bread
        if amt <= 0:
            return None
        self.earn(amt)
        self.bread = 0.0
        return amt

    def any_product_ready(self):
        return any(v > 0 for v in self.a_store) or self.bread > 0

    def income_per_sec(self, i, with_rain=True):
        if self.levels[i] == 0:
            return 0.0
        sp = self.growth_speed() if with_rain else 1.0
        return self.cycle_income(i) / self.cycle_time(i) * sp

    def total_income(self):
        return sum(self.income_per_sec(i) for i in range(N_CROPS))

    # ---------- покупки ----------
    def cost(self, i, n):
        c = CROPS[i]
        r = c["mult"]
        return c["cost"] * self.price_mult * safe_pow(r, self.levels[i]) * (safe_pow(r, n) - 1) / (r - 1)

    def max_affordable(self, i):
        c = CROPS[i]
        r = c["mult"]
        first = c["cost"] * self.price_mult * safe_pow(r, self.levels[i])
        if self.money < first:
            return 0
        try:
            n = min(100_000, int(math.log(self.money * (r - 1) / first + 1, r)))
        except (OverflowError, ValueError, ZeroDivisionError):   # деньги или цена ушли в бесконечность
            return 0
        while n > 0 and self.cost(i, n) > self.money:
            n -= 1
        return max(n, 0)

    def buy_amount(self, i, mode):
        if mode == "max":
            return max(1, self.max_affordable(i))
        if mode == "next":
            nm = next_milestone(self.levels[i])
            return nm - self.levels[i] if nm else 1
        return int(mode)

    def buy(self, i, n):
        price = self.cost(i, n)
        if n <= 0 or not math.isfinite(price) or self.money < price:
            return False
        self.money -= price
        was_locked = self.levels[i] == 0
        self.levels[i] += n
        if was_locked and i < self.up("farmers"):
            self.farmers[i] = True
        return True

    def fert_cost(self, i):
        return CROPS[i]["cost"] * self.price_mult * FERT_BASE * safe_pow(FERT_STEP, self.fert[i])

    def buy_fert(self, i):
        price = self.fert_cost(i)
        if self.levels[i] == 0 or self.money < price:
            return False
        self.money -= price
        self.fert[i] += 1
        return True

    def buy_farmer(self, i):
        if self.farm_def()["peasants"]:
            return False
        price = self.farmer_cost(i)
        if self.farmers[i] or self.levels[i] == 0 or self.money < price:
            return False
        self.money -= price
        self.farmers[i] = True
        if self.ready[i]:  # грядка снова растёт, созревшее остаётся лежать
            self.ready[i] = False
            self.progress[i] = 0.0
        return True

    # ---------- время ----------
    def earn(self, x):
        if x != x or x <= 0:            # NaN или нечего добавлять
            return
        self.money = min(MONEY_CAP, self.money + x)
        self.run_earned = min(MONEY_CAP, self.run_earned + x)
        self.total_earned = min(MONEY_CAP, self.total_earned + x)

    def update(self, dt, automation=True):
        """Урожай копится на грядках (stash). В банк он попадает только через collect().
        automation=False — скотники и мельники не носят урожай (так считался офлайн до версии 2.8)."""
        if self.rain_left > 0:
            self.rain_left = max(0.0, self.rain_left - dt)
        elif self.rain_cd > 0:
            self.rain_cd = max(0.0, self.rain_cd - dt)
        self.sun_cd = max(0.0, self.sun_cd - dt)
        self.boost_left = max(0.0, self.boost_left - dt)
        self._run_animals(dt, automation)
        self._run_mill(dt, automation)

        sp = self.growth_speed()
        for i in range(N_CROPS):
            if self.levels[i] == 0 or self.blocked[i] or self.frozen[i] > 0:
                continue
            t = self.cycle_time(i)
            if self.farmers[i]:
                self.progress[i] += dt * sp
                if self.progress[i] >= t:
                    k = int(self.progress[i] // t)
                    self.progress[i] -= k * t
                    self.stash[i] += k * self.cycle_income(i)
            elif not self.ready[i]:
                self.progress[i] += dt * sp
                if self.progress[i] >= t:
                    self.progress[i] = t
                    self.ready[i] = True
                    self.stash[i] += self.cycle_income(i)

    def collect(self, i):
        """Переносит урожай с грядки в банк. Время цикла не меняется."""
        amt = self.stash[i]
        self.last_lucky = False
        if amt <= 0:
            return None
        if random.random() < 0.02 * self.up("lucky"):
            amt *= 10
            self.last_lucky = True
        self.earn(amt)
        self.stash[i] = 0.0
        if not self.farmers[i]:
            self.ready[i] = False
            self.progress[i] = 0.0
        return amt

    def total_stash(self):
        return sum(self.stash)

    # ---------- дождь и солнце ----------
    def rain_available(self):
        return self.rain_left <= 0 and self.rain_cd <= 0

    def start_rain(self):
        if not self.rain_available():
            return False
        self.rain_left = _rain_time(self.up("rain_len"))
        self.rain_cd = _rain_cd(self.up("rain_cd"))
        return True

    def squirrel_reward(self):
        base = sum(self.income_per_sec(i, with_rain=False) for i in range(N_CROPS))
        return max(SQUIRREL_REWARD_MIN * self.price_mult, SQUIRREL_SHARE * base * SQUIRREL_SECONDS)

    def catch_squirrel(self, mult=1):
        amt = self.squirrel_reward() * mult
        self.earn(amt)
        return amt

    def sun_click(self):
        if self.sun_cd > 0:
            return None
        base = sum(self.income_per_sec(i, with_rain=False) for i in range(N_CROPS))  # как у белки: без дождя
        amt = max(SUN_MIN * self.price_mult, base * (SUN_SECONDS + 30 * self.up("sun")))
        self.earn(amt)
        self.sun_cd = SUN_COOLDOWN
        return amt

    # ---------- грузовик (престиж) ----------
    @staticmethod
    def leaves_for(earned):
        return int(LEAF_FACTOR * math.sqrt(max(0.0, earned) / LEAF_UNIT))

    def run_total(self):
        """Заработок забега вместе с несобранным урожаем — его тоже забирает грузовик."""
        return (self.run_earned + self.total_stash() + sum(self.a_feed) + sum(self.a_store)
                + self.hopper + self.flour + self.bread + self.oven_load)

    def truck_mult(self):
        return 1 + 0.1 * self.up("truck")

    def potential_leaves(self):
        raw = LEAF_FACTOR * math.sqrt(max(0.0, self.run_total()) / (LEAF_UNIT * self.price_mult))
        return int(raw * self.truck_mult() + 1e-9)

    def money_for_next_leaf(self):
        p = self.potential_leaves() + 1
        need = (p / self.truck_mult() / LEAF_FACTOR) ** 2 * LEAF_UNIT * self.price_mult
        return max(0.0, need - self.run_total())

    def truck_ready(self):
        return self.potential_leaves() >= TRUCK_MIN_LEAVES

    def farm_value(self):
        """Всё, что лежит на ферме и ещё не в банке: урожай на грядках, корм и продукты сарая, зерно, мука, хлеб."""
        return self.run_total() - self.run_earned

    def sell_to_truck(self):
        """Продажа фермы. Листьев даётся ровно столько, сколько показывало окно (potential_leaves):
        несобранное засчитывается один раз, «гигантский урожай x10» при продаже не срабатывает."""
        gained = self.potential_leaves()
        if gained <= 0:
            return 0
        self.last_lucky = False
        self.earn(self.farm_value())       # несобранное тоже идёт в статистику «всего заработано»
        self.leaves += gained
        self.home_leaves += gained
        self.leaves_earned += gained
        self.prestiges += 1
        self.reset_run()
        return gained

    # ---------- переезд ----------
    def has_next_farm(self):
        return self.farm_index + 1 < len(FARMS) and FARMS[self.farm_index + 1]["ready"]

    def can_move(self):
        return self.has_next_farm() and self.run_total() >= self.move_threshold()

    def move_farm(self):
        """Переезд: всё с нуля. С собой — только трофей прошлой фермы и x2 к доходу за неё."""
        if not self.can_move():
            return False
        self.farm_index += 1
        self.leaves = 0
        self.home_leaves = 0
        self.tree = {}
        self.rain_left = self.rain_cd = 0.0
        self.sun_cd = SUN_COOLDOWN / 3
        self.reset_run()
        return True

    # ---------- офлайн ----------
    def offline_cap(self):
        return OFFLINE_CAP + 7200 * self.up("offline")

    def offline_earn(self, seconds):
        """Пока игры не было, ферма работала сама — тем же кодом, что и при открытой игре, шагами по OFFLINE_STEP с:
        грядки с фермерами копят урожай, скотники кормят зверей, мельники и пекари работают (OFFLINE_AUTOMATION),
        а дождь, солнце и доход x2 из таверны тикают и заканчиваются вовремя (раньше x2 действовал на весь офлайн).
        Вороны, разбойники и мороз в офлайне не приходят. Возвращает, на сколько выросло добро на ферме."""
        if seconds != seconds:              # NaN из испорченного сохранения
            return 0.0
        seconds = max(0.0, min(self.offline_cap(), seconds))
        before = self.farm_value()
        left = seconds
        while left > 1e-6:
            dt = min(OFFLINE_STEP, left)
            self.update(dt, automation=OFFLINE_AUTOMATION)
            left -= dt
        return max(0.0, self.farm_value() - before)

    # ---------- сохранение ----------
    FIELDS = ["leaves", "leaves_earned", "tree", "farm_index", "home_leaves", "prestiges", "total_earned", "rain_left", "rain_cd", "sun_cd",
              "boost_left",
              "money", "run_earned", "levels", "fert", "farmers", "progress", "ready", "stash",
              "a_levels", "a_feed", "a_prog", "a_store", "a_keeper",
              "peasants", "m_levels", "m_workers", "hopper", "flour", "bread", "oven_load", "oven_prog"]

    def to_dict(self):
        return {k: getattr(self, k) for k in self.FIELDS}

    @staticmethod
    def _clean(default, v):
        """Значение из сохранения приводим к типу поля. Не подходит — ValueError (поле останется как было)."""
        if isinstance(default, bool):
            if isinstance(v, (bool, int)):
                return bool(v)
            raise ValueError(v)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
            raise ValueError(v)
        if isinstance(default, int):
            if v in (float("inf"), float("-inf")):
                raise ValueError(v)
            return max(0, int(v))
        return max(0.0, min(MONEY_CAP, float(v)))

    def from_dict(self, d):
        """Читает сохранение. Каждое поле проверяется: испорченное значение пропускается (остаётся значение
        новой игры), а не роняет игру и не стирает весь прогресс."""
        if not isinstance(d, dict):
            raise ValueError("сохранение — не словарь")
        for k in self.FIELDS:
            if k not in d:
                continue
            v, cur = d[k], getattr(self, k)
            if isinstance(cur, dict):                       # дерево улучшений: id -> уровень
                if isinstance(v, dict):
                    tree = {}
                    for key, lvl in v.items():
                        try:
                            tree[str(key)] = self._clean(0, lvl)
                        except ValueError:
                            pass
                    setattr(self, k, tree)
            elif isinstance(cur, list):                     # списки по грядкам / зверям / зданиям
                if isinstance(v, list):
                    out = list(cur)
                    for j in range(min(len(cur), len(v))):
                        try:
                            out[j] = self._clean(cur[j], v[j])
                        except ValueError:
                            pass
                    setattr(self, k, out)
            else:
                try:
                    setattr(self, k, self._clean(cur, v))
                except ValueError:
                    pass
        # значения в разумных границах
        self.farm_index = min(self.farm_index, len(FARMS) - 1)
        self.a_levels = [min(ANIMAL_MAX_LVL, x) for x in self.a_levels]
        self.m_levels = [min(MILL_MAX_LVL, x) for x in self.m_levels]
        self.m_workers = [min(w, lvl) for w, lvl in zip(self.m_workers, self.m_levels)]
        self.a_keeper = [k and lvl > 0 for k, lvl in zip(self.a_keeper, self.a_levels)]
        if self.farm_def()["peasants"]:                     # крестьян занято не больше, чем нанято
            self.peasants = max(self.peasants, PEASANT_START)   # сверху не режем: «Крепостные» дают крестьян сверх найма
            for b in (1, 0):
                while self.free_peasants() < 0 and self.m_workers[b] > 0:
                    self.m_workers[b] -= 1
            for i in reversed(range(N_CROPS)):
                if self.free_peasants() >= 0:
                    break
                self.farmers[i] = False
        if "home_leaves" not in d:   # сохранения до разделения листьев
            self.home_leaves = self.leaves if self.farm_index == 0 else 0
        self.home_leaves = min(self.home_leaves, self.leaves)
        # старые сохранения: созревшая грядка без накопленного урожая
        for i in range(N_CROPS):
            if self.ready[i] and self.stash[i] <= 0 and self.levels[i] > 0:
                self.stash[i] = self.cycle_income(i)
