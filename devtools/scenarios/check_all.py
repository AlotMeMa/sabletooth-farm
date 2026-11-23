# Обход всех экранов: проверка целостности после обновления картинок
set_summer(); A.toasts.clear(); frames(30); snap("all_field_summer")
A.view = "barn"; frames(30); snap("all_barn")
A.view = "field"
for m in ("shop", "tree", "settings", "truck"):
    A.modal = m; A.skip_anims(); frames(40); snap("all_" + m)
A.modal = None
set_medieval(); A.farm.m_levels = [3, 2]; A.farm.peasants = 8; A.farm.m_workers = [2, 1]
A.farm.hopper = 5e4; A.farm.flour = 2e4; A.farm.bread = 1e4
A.toasts.clear(); frames(30); snap("all_field_med")
A.view = "barn"; frames(40); snap("all_mill")
A.view = "field"; A.tavern.unlocked = True; A.tavern.tokens = 120
A.open_tavern(); A.tv_bubble = None; A.toasts.clear(); frames(40); snap("all_tavern")
A.open_board(); frames(20); snap("all_board")
A.open_casino(); frames(30); snap("all_casino")
