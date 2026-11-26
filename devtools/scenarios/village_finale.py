# 3.42: окно рыботорговца с рыбками аквариума, карта глав, бармен после «Морского волка»
f = A.farm
f.farm_index = 3; f.reset_run(); A.set_theme(); A.bg = A.build_background()
f.levels = [30] * 6 + [0] * 3; f.money = 1e14; f.earn(5e13)
for _ in range(8):
    f.buy_fish(5)
for x in f.fy_fish[:5]:
    x[2] = 1.0
A.toasts.clear(); A.open_modal("truck"); A.skip_anims(); frames(10); snap("vf_truck")
A.modal = None; A.open_modal("move"); A.skip_anims(); A.map_scroll(900); frames(30); snap("vf_map")
A.modal = None
A.tavern.unlocked = True; A.tavern.ach_done = list(A.tavern.ach_done) + ["final_1", "final_2"]
A.open_tavern(); A.tv_bubble = None; frames(10); A.poke_barman(); frames(5); A.barman_topic("news"); frames(10); snap("vf_barman")
