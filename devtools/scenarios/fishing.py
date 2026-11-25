# 3.36: заготовка Рыбацкой деревни — пруд, рыбы, рыбаки, фестиваль, краб, чайка, повозка, дерево, садки, карта
f = A.farm
f.farm_index = 3
f.reset_run()
A.set_theme()
f.levels = [60, 40, 30, 25, 25, 25, 12, 0, 0]
f.farmers = [True] * 5 + [False] * 4
f.peasants = 6
f.money = 1e12
A.bg = A.build_background()
A.toasts.clear(); frames(40); snap("fi_field")
A.view = "barn"; frames(20); snap("fi_fishery")
A.view = "field"; A.open_modal("tree"); A.skip_anims(); frames(30); snap("fi_tree")
A.modal = None; f.rain_cd = 0; A.click_rain(); A.toasts.clear(); frames(90); snap("fi_fest")
A.modal = None; A.open_modal("shop"); A.shop_tab = "farm"; A.skip_anims(); frames(30); snap("fi_shop")
A.modal = None
