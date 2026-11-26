# 3.39.1: свои помощники артели всегда у грядок (средневековье, зима, деревня), 3-й плясун, F1 «Сарай» в деревне
for idx, tag in ((1, "med"), (2, "win"), (3, "fish")):
    f = A.farm
    f.farm_index = idx
    f.reset_run()
    A.set_theme()
    f.levels = [30, 25, 20, 15, 12, 10, 8, 5, 0]
    f.farmers = [True, True, True, False, True, False, True, False, False]
    f.peasants = 12
    f.money = 1e12
    A.view = "field"; A.modal = None; A.toasts.clear(); frames(30); A.toasts.clear(); frames(1); snap(f"own_{tag}")
f.rain_cd = 0; A.click_rain(); frames(240); A.toasts.clear(); frames(1); snap("own_fish_fest")
A.view = "barn"; A.dev_tab = "barn"; A.open_modal("dev"); A.skip_anims(); frames(5); snap("dev_tank")
