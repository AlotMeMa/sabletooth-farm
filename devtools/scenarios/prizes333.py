# 3.33: призовая стойка по вкладкам, новые украшения в зале и у камина, рубашка карт, шлейфы
from farmgame.config import PRIZES, PRIZE_TABS
set_medieval(); A.tavern.unlocked = True; A.tavern.tokens = 20000
for p in PRIZES:
    if not (p.get("jackpot") or p.get("achievement")):
        A.tavern.buy_prize(A.farm, p["id"])
A.tavern.prizes["golden_squirrel"] = A.tavern.prizes["golden_pitchfork"] = True
for tab, _t in PRIZE_TABS:
    A.modal = None; A.prize_tab = tab; A.open_modal("prizes"); A.skip_anims(); frames(20); snap("pz_" + tab)
A.modal = None
A.open_tavern(); A.tv_bubble = None; A.toasts.clear(); frames(30); snap("pz_hall")
A.poke_owl(); frames(10); snap("pz_owl")
A.open_fireside(); A.toasts.clear(); frames(60); snap("pz_fireside")
A.pet_dog(); frames(15); snap("pz_dog")
