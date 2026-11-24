# 3.21: огонь камина — несколько кадров подряд
set_medieval(); A.tavern.unlocked = True; A.tavern.tokens = 5000
for pid in ("horseshoe", "cup", "statue", "crystal", "cat", "kettle", "flowers", "rug"):
    A.tavern.buy_prize(A.farm, pid)
A.open_tavern(); A.toasts.clear(); frames(5); A.open_fireside(); frames(60)
for i in range(4):
    frames(7); snap(f"fire_{i}", crop=(330, 120, 690, 500))
A.toasts.clear(); frames(5); snap("fire_full")
