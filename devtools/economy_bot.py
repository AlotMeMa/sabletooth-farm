# -*- coding: utf-8 -*-
"""Бот-экономист: проходит главу «идеальной» игрой и печатает темп по забегам.

    python devtools/economy_bot.py [ферма 0|1|2] [политика spend|half] [инфляция дерева, напр. 0.1]

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


def play(farm_index=0, policy="spend", seed=1, max_hours=40, quiet=False):
    random.seed(seed)
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
        for i in range(C.N_CROPS):
            f.collect(i)
        f.sun_click()
        f.start_rain()
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
    return t, runs, f


if __name__ == "__main__":
    fi = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    pol = sys.argv[2] if len(sys.argv) > 2 else "spend"
    if len(sys.argv) > 3:
        C.TREE_INFLATION = float(sys.argv[3])
        L.TREE_INFLATION = C.TREE_INFLATION
    play(fi, pol)
