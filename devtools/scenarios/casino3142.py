set_medieval(); A.tavern.unlocked = True; A.tavern.tokens = 340
A.open_casino(); A.toasts.clear(); frames(30); snap("k_intro")
for _ in range(2): A.poke_croupier()
frames(5); snap("k_intro3")
for _ in range(3): A.poke_croupier()
A.cs_chip = 10
for key in (("red",), ("num", 17), ("dozen", 2), ("num", 0)):
    A.cs_place(key)
frames(3); snap("k_bets")
A.roulette.rng.seed(5); A.cs_start()
for i in range(int(2.5*30)): A.update(1/30)
frames(1); snap("k_spin")
for i in range(int(3.5*30)): A.update(1/30)
A.toasts.clear(); frames(2); snap("k_result")
