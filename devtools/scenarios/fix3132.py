# 3.13.2: стена, плашки бонусов, доска заданий под курсором, «Макс. уровень», крупный крестьянин
set_medieval(); f = A.farm
f.boost_left = 600; f.song, f.song_left = 3, 237
A.toasts.clear(); frames(3); snap("field", crop=(100, 150, 900, 640))
f.m_levels = [5, 5]; f.m_workers = [1, 1]; f.peasants = 15
A.view = "barn"; A.toasts.clear(); frames(3); snap("mill")
A.tavern.unlocked = True; A.open_tavern(); A.tv_bubble = None
r = A.tl["board_sign"]; pygame.STATE["mouse"] = (int(r.centerx * A.hd_k), int(r.centery * A.hd_k))
for i in range(12): frames(1)
snap("board_hover", crop=(0, 180, 300, 420))
A.view = "field"; A.open_modal("shop"); A.shop_tab = "farm"; A.skip_anims()
for i in range(40): frames(1)
snap("shop")
