# 3.26.2: зимние картинки пользователя — упряжки трёх уровней на дороге и звери в сарае
f = A.farm
f.farm_index = 2
f.reset_run()
A.set_theme()
f.levels = [30, 20, 15, 10, 8, 6, 4, 2, 1]
f.farmers = [True] * 9
f.peasants = 9
f.a_levels = [3, 3, 3, 3]
f.a_keeper = [True] * 4
f.a_feed = [1e3] * 4
f.money = 1e12
A.bg = A.build_background()
A.toasts.clear()
for tier in range(3):
    A.truck_tier = lambda tier=tier: tier
    A.truck_state, A.truck_x = "parked", 830
    frames(20); snap(f"wa_sled{tier}")
A.truck_state = "away"
A.view = "barn"; frames(30); snap("wa_barn")
