# -*- coding: utf-8 -*-
"""Бот-экономист: проходит главу «идеальной» игрой и печатает темп по забегам.

    python devtools/economy_bot.py [ферма 0|1|2|3] [политика spend|half] [инфляция дерева, напр. 0.1] [аквариум]

аквариум (только деревня, 3.41): off — не трогает; fast — ловит хищника сразу; feed — даёт ему поесть
(ловит, когда съел FEED_BITES рыбок или рыбы осталось мало). Ловля удаётся с вероятностью catch.bot_win_rate.

Бот каждую секунду собирает урожай, жмёт солнце и дождь, покупает то, что быстрее окупается
(уровни грядок до ближайшей вехи, удобрения, фермеры), продаёт ферму, когда листья за секунду
начинают падать, и тратит листья по политике:
    spend — всё, что по карману, самое дешёвое первым (как сейчас играет почти любой игрок);
    half  — покупает, только если после покупки останется не меньше половины листьев.
Белок, ворон, сарая и мельницы бот не трогает — сравнивать варианты баланса между собой, а не с живой игрой.
"""
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "devtools", "fake_pygame"), ROOT]

from farmgame import config as C  # noqa: E402
from farmgame import logic as L   # noqa: E402


def best_purchase(f):
    """(окупаемость, действие) самой выгодной покупки или None."""
    best = None
    for i in range(C.N_CROPS):
        if f.levels[i] and not f.farmers[i] and not f.farm_def()["peasants"]:
            p = f.farmer_cost(i)
            if p <= f.money:
                return (0, ("farmer", i, 1))
        nm = C.next_milestone(f.levels[i]) or f.levels[i] + 25
        n = max(1, nm - f.levels[i])
        cost = f.cost(i, n)
        before = f.income_per_sec(i, with_rain=False)
        f.levels[i] += n
        after = f.income_per_sec(i, with_rain=False)
        f.levels[i] -= n
        gain = max(after - before, 1e-12)
        if f.levels[i] == 0:
            gain = max(gain, 1e-9)
        cand = (cost / gain, ("level", i, n), cost)
        if best is None or cand[0] < best[0]:
            best = cand
        if f.levels[i]:
            fc = f.fert_cost(i)
            fg = before * 2
            cand = (fc / max(fg, 1e-12), ("fert", i, 1), fc)
            if cand[0] < best[0]:
                best = cand
    return best


def spend_money(f):
    for _ in range(400):
        b = best_purchase(f)
        if b is None:
            return
        kind, i, n = b[1]
        if kind == "farmer":
            f.buy_farmer(i)
            continue
        if b[2] > f.money:
            return
        if kind == "level":
            f.buy(i, n)
        else:
            f.buy_fert(i)


def spend_leaves(f, policy):
    while True:
        opts = [(f.tree_cost(n), n) for n in f.nodes() if f.can_buy_tree(n)]
        if policy == "half":
            opts = [o for o in opts if f.leaves - o[0] >= f.leaves / 2]
        if not opts:
            return
        f.buy_tree(min(opts)[1])


FEED_BITES = 5          # политика feed: даём хищнику съесть столько рыбок, потом ловим
TANK_SHARE = 0.3        # на рыбок и место в аквариуме — не больше такой доли денег
_win_cache = {}


def win_rate(f):
    from farmgame.catch import bot_win_rate
    key = (round(f.catch_difficulty(), 3), f.catch_slow())
    if key not in _win_cache:
        _win_cache[key] = bot_win_rate(*key, games=60)
    return _win_cache[key]


def play_tank(f, mode, stats, left=1e9):
    """Ход бота в аквариуме (раз в секунду). left — сколько ещё, по прикидке, продлится забег (рыбки, которые
    не успеют вырасти до продажи фермы, не покупаются: аквариум с забегом обнуляется)."""
    if mode == "off" or not f.has_fishery():
        return
    # хищник: ловить сейчас или пусть ест
    if f.fy_pred and f.can_hook():
        if mode == "fast" or f.fy_pred_eaten >= FEED_BITES or len(f.fy_fish) <= 2:
            f.hook_predator()
            if random.random() < win_rate(f):
                amt, _p = f.catch_predator()
                stats["pred_money"] += amt
                stats["caught"] += 1
            else:
                f.lose_predator()
                stats["lost"] += 1
    # взрослых продаём, по паре самого дорогого вида оставляем на икру
    keep = {}
    for n in sorted(f.adults(), key=lambda n: -f.fy_fish[n][1]):
        k = f.fy_fish[n][0]
        if keep.get(k, 0) < 2 and k == max(x[0] for x in f.fy_fish):
            keep[k] = keep.get(k, 0) + 1
            continue
    sell = [n for n in f.adults() if not (f.fy_fish[n][0] in keep and keep[f.fy_fish[n][0]] > 0
                                           and keep.__setitem__(f.fy_fish[n][0], keep[f.fy_fish[n][0]] - 1) is None)]
    for n in sorted(sell, reverse=True):
        stats["fish_money"] += f.sell_fish(n) or 0
    budget = f.money * TANK_SHARE
    c = f.tank_cost()
    if c is not None and c <= budget:
        f.upgrade_tank()
        stats["tank_spent"] += c
        budget -= c
    kinds = [i for i in range(C.N_CROPS) if f.levels[i] > 0 and C.FISH_GROW[i] <= left]
    if kinds:
        best = max(kinds, key=f.fish_price)                # дорогая рыба выгоднее (x5 за место)
        while f.tank_used() < f.fy_cap and f.fish_price(best) <= budget and f.buy_fish(best):
            budget -= f.fish_price(best)
            stats["fish_spent"] += f.fish_price(best)


MILL_SHARE = 0.3        # на мельницу, пекарню и крестьян — не больше такой доли денег


def play_mill(f):
    """3.41: мельница и пекарня средневековья (бот без неё недооценивал главу). Строит здания и нанимает
    крестьян на долю денег, ставит их мельниками и пекарями, засыпает зерно до сбора, забирает хлеб."""
    if f.farm_def().get("barn") != "mill":
        return
    for b in (0, 1):
        if f.m_levels[b] < C.MILL_MAX_LVL and f.mill_can_build(b) and f.mill_building_cost(b) <= f.money * MILL_SHARE:
            f.buy_mill_building(b)
    while (f.m_workers[0] < f.m_levels[0] or f.m_workers[1] < f.m_levels[1]):
        if f.free_peasants() <= 0:
            if f.peasants >= C.PEASANT_MAX or f.peasant_cost() > f.money * MILL_SHARE or not f.hire_peasant():
                break
        b = 0 if f.m_workers[0] <= f.m_workers[1] and f.m_workers[0] < f.m_levels[0] else 1
        if f.m_workers[b] >= f.m_levels[b]:
            b = 1 - b
        if not f.set_mill_workers(b, 1):
            break
    if f.m_workers[0]:
        f.fill_hopper()
    f.collect_bread()
    if not f.m_workers[1]:
        f.sell_flour()


def play(farm_index=0, policy="spend", seed=1, max_hours=40, quiet=False, tank="off", mill=True):
    random.seed(seed)
    stats = dict(pred_money=0.0, fish_money=0.0, fish_spent=0.0, tank_spent=0.0, caught=0, lost=0)
    f = L.Farm()
    f.farm_index = farm_index
    f.reset_run()
    t = run_t = 0.0
    hist = []
    runs = []
    while t < max_hours * 3600:
        f.update(1.0)
        t += 1
        run_t += 1
        if mill:
            play_mill(f)
        for i in range(C.N_CROPS):
            f.collect(i)
        f.sun_click()
        f.start_rain()
        play_tank(f, tank, stats, (runs[-1][0] if runs else 1e9) - run_t)
        spend_money(f)
        if f.run_total() >= f.move_threshold():
            runs.append((run_t, 0, f.leaves, f.leaf_mult))
            break
        pot = f.potential_leaves()
        hist.append(pot)
        if run_t > 120 and pot >= C.TRUCK_MIN_LEAVES:
            marginal = (pot - hist[-61]) / 60 if len(hist) > 61 else 1e9
            if marginal < pot / run_t:
                got = f.sell_to_truck()
                spend_leaves(f, policy)
                runs.append((run_t, got, f.leaves, f.leaf_mult))
                run_t = 0.0
                hist = []
    spent = sum(f.nodes()[n]["costs"][k] for n in f.tree for k in range(f.tree[n]))
    levels = sum(f.tree.values())
    total = sum(len(n["costs"]) for n in f.nodes().values())
    if not quiet:
        print(f"ферма {farm_index}, политика {policy}, инфляция {getattr(C, 'TREE_INFLATION', 0)}: "
              f"глава {t / 3600:.1f} ч, забегов {len(runs)}, дерево {levels}/{total} ур. "
              f"(по базовым ценам {spent}), листьев на руках {f.leaves}, x{f.leaf_mult:.1f} от листьев")
        tail = runs[-8:]
        print("   последние забеги (мин / листьев за забег / на руках / множитель листьев):")
        print("   " + "; ".join(f"{r[0] / 60:.0f}м/{r[1]}/{r[2]}/x{r[3]:.1f}" for r in tail))
        if tank != "off":
            print(f"   аквариум ({tank}): хищников поймано {stats['caught']}, сорвалось {stats['lost']}; "
                  f"рыбки: потрачено {C.fmt(stats['fish_spent'])}, продано на {C.fmt(stats['fish_money'])}; "
                  f"хищники принесли {C.fmt(stats['pred_money'])}; места {C.fmt(stats['tank_spent'])}")
    f.bot_stats = stats
    return t, runs, f


if __name__ == "__main__":
    fi = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    pol = sys.argv[2] if len(sys.argv) > 2 else "spend"
    if len(sys.argv) > 3:
        C.TREE_INFLATION = float(sys.argv[3])
        L.TREE_INFLATION = C.TREE_INFLATION
    tk = sys.argv[4] if len(sys.argv) > 4 else "off"
    play(fi, pol, tank=tk)
