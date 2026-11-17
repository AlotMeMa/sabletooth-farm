# экран мельницы: не построено / построена мельница / всё работает (мельники сами носят зерно)
from farmgame.config import GRAIN
set_medieval(); f = A.farm
A.view = "barn"; A.toasts.clear(); frames(3); snap("mill_none")
f.levels[GRAIN[0]] = 5; f.m_levels = [2, 0]; f.m_workers = [0, 0]; frames(3); snap("mill_one")
f.m_levels = [3, 2]; f.m_workers = [2, 1]; f.peasants = 9
for i in GRAIN: f.farmers[i] = True
f.rain_left, f.rain_cd = 0, 1e9
for _ in range(480): f.update(0.25)
print("hopper", round(f.hopper / f.hopper_cap(), 2), "sec", round(f.hopper_seconds()))
f.flour = A.mill_rate() * 100; f.bread = A.bread_batch() * 1.5
for i in range(60): frames(1, 1 / 30)
A.toasts.clear(); frames(1); snap("mill_full")
