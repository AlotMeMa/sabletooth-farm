set_medieval(); A.tavern.unlocked = True; A.tavern.tokens = 3000
for pid in ("horseshoe", "cup", "statue", "crystal", "bard_girl"):
    A.tavern.buy_prize(A.farm, pid)
A.open_tavern(); A.tv_bubble = None; A.toasts.clear(); frames(40); snap("g_tavern")
A.poke_bard(); frames(20); snap("g_girl", crop=(330, 200, 640, 500))
snap("g_trophies", crop=(90, 260, 340, 380), scale=2)
A.open_songs(); A.skip_anims(); frames(40); snap("g_songs")
A.modal = None; A.open_casino(); frames(5); A.open_modal("prizes"); A.prize_tab = "cosmetic"; A.skip_anims(); frames(40); snap("g_prizes")
