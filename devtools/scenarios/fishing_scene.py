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
