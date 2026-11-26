# 3.40.2: надпись над повозкой/упряжкой/лодкой на всех фермах (цифры не наезжают на значок, не дрожат)
from farmgame.art_base import TRUCK_PARK_X
f = A.farm
for idx, tag in ((0, "summer"), (1, "medieval"), (2, "winter"), (3, "fishing")):
    f.farm_index = idx; f.reset_run(); A.set_theme(); A.bg = A.build_background()
    for n, val in ((0, 7), (1, 1234), (2, 9876543)):
        f.potential_leaves = lambda v=val: v
        A.truck_state = "parked"; A.truck_x = TRUCK_PARK_X; A.modal = None; A.toasts.clear()
        frames(7 + n); A.toasts.clear(); frames(1)
        snap(f"tl_{tag}_{n}")
