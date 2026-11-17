import os
from farmgame.tutorial import Tutorial
A.tut = Tutorial(); A.toasts.clear(); A.modal=None
f=A.farm
frames(10); snap("tut_hello")
A.tut_next(); frames(5); A.tut_click_box(); frames(2); snap("tut_collect_wait")
f.stash[0]=f.cycle_income(0); f.ready[0]=True; frames(2); A.tut_click_box(); frames(2); snap("tut_collect_ripe")
A.try_collect(A.coin_pos(0)); A.on_click(A.coin_pos(0)); frames(3)
print("step after collect", A.tut.current["id"])
A.tut_click_box(); frames(2); snap("tut_plant_poor")
f.money=1e4; frames(2); snap("tut_plant_rich")
A.do_buy(f.levels.index(0),1); frames(3); A.tut_click_box(); frames(2); snap("tut_upgrade1")
A.mode="upgrade"; frames(2); snap("tut_upgrade2")
A.do_buy(0,1); A.mode="normal"; frames(3); A.tut_click_box(); frames(2); snap("tut_shop")
A.open_modal("shop"); frames(3); A.modal=None; A.closing=None; frames(3); A.tut_click_box(); frames(2); snap("tut_bye")
A.tut_next(); print("done", A.tut.done)
