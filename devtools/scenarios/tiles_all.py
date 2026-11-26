# 3.39.6: плитки поля одной ширины на всех фермах — по кадру с каждой
for idx, tag in ((0, "sum"), (1, "med"), (2, "win"), (3, "fish")):
    f = A.farm
    f.farm_index = idx
    f.reset_run()
    A.set_theme()
    f.levels = [5, 5, 5, 5, 5, 0, 5, 0, 0]
    f.money = 1e9
    A.view = "field"; A.modal = None; A.toasts.clear(); frames(20); A.toasts.clear(); frames(1); snap(f"tiles_{tag}")
