# экран мельницы: не построено / построена мельница / всё работает
from farmgame.config import GRAIN
set_medieval(); f = A.farm
A.view = "barn"; A.toasts.clear(); frames(3); snap("mill_none")
f.levels[GRAIN[0]] = 5; f.m_levels = [2, 0]; f.m_workers = [0, 0]; frames(3); snap("mill_one")
f.m_levels = [3, 2]; f.m_workers = [2, 1]; f.peasants = 6
f.hopper = f.hopper_cap() * 0.6; f.flour = A.mill_rate() * 100; f.bread = A.bread_batch() * 1.5; f.oven_load = 1e8; f.oven_prog = 8
for i in range(60): frames(1, 1 / 30)
A.toasts.clear(); frames(1); snap("mill_full")
