# 3.14: казино для игроков — дверь, крупье с правилами, призовая стойка, гирлянда
set_medieval(); A.tavern.unlocked = True; A.tavern.tokens = 60
A.open_tavern(); A.tv_bubble = None; A.toasts.clear(); frames(30); snap("c_door_closed", crop=(860, 200, 1000, 560))
A.tavern.tokens = 340; frames(10); A.toasts.clear(); frames(2); snap("c_door_open", crop=(860, 200, 1000, 560))
A.poke_casino(); frames(40); snap("c_intro")
for _ in range(5):
    A.poke_croupier()
frames(10)
for key in (("red",), ("num", 17)):
    A.cs_place(key)
frames(5); snap("c_bets")
A.open_modal("prizes"); A.skip_anims(); frames(40); snap("c_prizes_trophy")
A.buy_prize("horseshoe"); A.buy_prize("lucky_coin"); A.buy_prize("garland"); A.buy_prize("gold_notes")
A.prize_tab = "buff"; frames(20); snap("c_prizes_buff")
A.prize_tab = "cosmetic"; frames(20); snap("c_prizes_cosm")
A.modal = None; A.view = "tavern"; A.toasts.clear(); frames(40); snap("c_tavern_garland")
A.view = "field"; frames(20); snap("c_field_pills")
