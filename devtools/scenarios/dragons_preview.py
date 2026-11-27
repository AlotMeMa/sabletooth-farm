# 3.48: превью главы 5 через режим разработчика (кнопка «Ферма: Горы драконов»)
from farmgame.config import FARMS
f = A.farm
f.farm_index = len(FARMS) - 1; f.reset_run(); f.levels = [5, 5, 5, 5, 5, 5, 5, 5, 5]; A.set_theme(); A.bg = A.build_background()
for i in range(9):
    f.progress[i] = (i % 3) / 2.5 if hasattr(f, "progress") else 0
frames(20); A.toasts.clear(); frames(3); snap("field")
A.open_modal("move"); frames(40); snap("map")
A.modal = None; A.open_modal("tree"); frames(30); snap("tree")
