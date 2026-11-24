# 3.19: украшения в зале, посиделки у камина, окно призов (вкладка украшений)
set_medieval(); A.tavern.unlocked = True; A.tavern.tokens = 2000
A.open_tavern(); A.tv_bubble = None; A.toasts.clear(); frames(20); snap("fs_tavern_plain")
for pid in ("flowers", "rug", "kettle", "cat"):
    A.tavern.buy_prize(A.farm, pid)
pygame.STATE["mouse"] = (int(225 * A.hd_k), int(420 * A.hd_k)); frames(30); snap("fs_tavern_decor")
pygame.STATE["mouse"] = (0, 0)
A.open_modal("prizes"); A.prize_tab = "cosmetic"; A.skip_anims(); frames(30); snap("fs_modal")
A.modal = None; A.prize_page = 1; A.open_modal("prizes"); A.skip_anims(); frames(10); snap("fs_modal2")
A.modal = None
A.open_fireside(); frames(90); snap("fs_view")
A.poke_fire(); frames(12); snap("fs_poke")
A.fs_since = 200; frames(5); snap("fs_later")
A.tavern.prize_off = ["cat", "rug", "kettle", "flowers"]
A.leave_fireside(); A.open_fireside(); frames(40); snap("fs_bare")
