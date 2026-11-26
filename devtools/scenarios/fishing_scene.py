# 3.38.1: живой фон Рыбацкой деревни — поле ниже, без забора, окна, дым, рыбаки из домов на фестивале
f = A.farm
f.farm_index = 3
f.reset_run()
A.set_theme()
f.levels = [60, 40, 30, 25, 25, 25, 12, 10, 0]
f.farmers = [True, False, False, False, False, False, False, False, False]
f.money = 1e12
A.view = "field"; A.toasts.clear(); frames(60); A.toasts.clear(); frames(2); snap("scene_field")
f.rain_cd = 0; A.modal = None; A.click_rain(); A.toasts.clear()
frames(45); A.toasts.clear(); frames(1); snap("scene_walk")
frames(150); A.toasts.clear(); frames(1); snap("scene_party")
f.rain_left = 1.5; frames(30); A.toasts.clear(); frames(1); snap("scene_home")
# 3.38.1: лодка рыботорговца (3 уровня) у причала и одна рыба на участке
f.rain_left = 0
for tier in range(3):
    A.truck_tier = lambda tier=tier: tier
    A.truck_state = "parked"; A.truck_x = 830; A.truck_t = A.t
    A.toasts.clear(); frames(20); A.toasts.clear(); frames(1); snap(f"scene_boat{tier}")
A.truck_state = "leaving"; A.leaving_tier = 2; A.truck_v = 120; frames(12); A.toasts.clear(); frames(1); snap("scene_boat_leave")
