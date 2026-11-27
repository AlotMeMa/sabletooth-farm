# 3.46: карта глав из плиток пользователя
f = A.farm
f.farm_index = 3; f.reset_run(); A.set_theme(); A.bg = A.build_background()
A.toasts.clear(); A.open_modal("move"); frames(40); snap("map_here")
A.map_target = 0; A.map_x = 0; frames(20); snap("map_left")
A.map_select(4); frames(40); snap("map_secret")
