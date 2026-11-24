# 3.24: заготовка зимней главы (пока закрыта) — поле, сарай, дерево, карта глав
f = A.farm
f.farm_index = 2
f.reset_run()
A.set_theme()
f.levels = [60, 40, 30, 25, 25, 25, 12, 10, 5]
f.farmers = [True] * 9
f.a_levels = [5, 4, 3, 2]
f.a_keeper = [True] * 4
f.a_feed = [1e3] * 4
f.money = 1e12
A.bg = A.build_background()
A.toasts.clear(); frames(30); snap("w_field")
A.view = "barn"; frames(30); snap("w_barn")
A.view = "field"; A.open_modal("tree"); A.skip_anims(); frames(30); snap("w_tree")
A.modal = None; A.open_modal("move"); A.skip_anims(); frames(30); snap("w_map")
