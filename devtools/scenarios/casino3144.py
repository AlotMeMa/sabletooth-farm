set_medieval(); A.tavern.unlocked = True; A.tavern.tokens = 2400
A.open_casino(); A.toasts.clear(); frames(20); snap("t_intro")
for _ in range(4): A.poke_croupier()
frames(5); snap("t_intro5")
A.poke_croupier()
A.buy_prize("horseshoe"); A.buy_prize("statue"); A.toasts.clear()
A.cs_chip = 25
for key in (("red",), ("num", 17)):
    A.cs_place(key)
frames(20); snap("t_shelf")
A.open_modal("prizes"); A.skip_anims(); frames(40); snap("t_prizes")
A.modal = "dev"; A.skip_anims(); frames(30); snap("t_dev")
