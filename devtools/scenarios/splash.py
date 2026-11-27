# 3.45.4: бульк и шлейф пузырьков по щелчку в садках
f = A.farm
f.farm_index = 3; f.reset_run(); f.levels = [5] * 9; A.set_theme(); A.bg = A.build_background()
A.view = "barn"; A.toasts.clear(); frames(5)
for p in ((300, 300), (650, 420), (1000, 250)):
    A.on_click(p); frames(4)
assert len(A.fy_splashes) == 3, A.fy_splashes
frames(20); snap("splash")
