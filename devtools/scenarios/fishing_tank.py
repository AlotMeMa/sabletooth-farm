# 3.38: аквариум Рыбацкой деревни — пустой, с рыбой и икрой, лавка, хищник ест, тлеющий отсчёт, вылов
import random
random.seed(4)
f = A.farm
f.farm_index = 3
f.reset_run()
A.set_theme()
f.levels = [60, 40, 30, 25, 25, 25, 12, 10, 0]
f.money = 1e15
A.view = "barn"; A.toasts.clear(); frames(10); snap("tank_empty")
A.fy_shop = True; frames(10); snap("tank_shop")
A.fy_shop = False
for i in (0, 0, 2, 2, 4, 5, 7, 7, 3, 6):
    A.fy_buy(i)
for _ in range(200):
    f.update(1.0)
A.toasts.clear(); A.floaters.clear(); frames(20); snap("tank_fish")
for _ in range(400):
    f.update(1.0)
    if f.fy_pred:
        break
A.fishery_tick(0.1); A.toasts.clear(); frames(20); snap("tank_pred")
while f.fy_fish:
    f.update(1.0)
f.update(2.0)
A.fishery_tick(0.1); A.toasts.clear(); A.floaters.clear(); frames(8); snap("tank_grace")
A.fy_catch(); A.toasts.clear(); frames(10); snap("tank_caught")
