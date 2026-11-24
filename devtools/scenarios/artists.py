# 3.23: артисты на сцене (пока без картинок — кодом)
set_medieval(); A.tavern.unlocked = True; A.tavern.tokens = 5000
A.open_tavern(); A.tv_bubble = None; A.toasts.clear()
for pid in ("fiddler", "bagpiper"):
    A.tavern.buy_prize(A.farm, pid); frames(20); A.poke_bard(); frames(3); snap("ar_" + pid, crop=(380, 220, 640, 440), scale=2)
A.open_modal("prizes"); A.prize_tab = "cosmetic"; A.prize_page = 2; A.skip_anims(); frames(30); snap("ar_modal")
