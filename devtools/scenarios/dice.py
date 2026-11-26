# 3.43: кости с драконицей Искрой — карта, правила, ставки, полёт костей, итог
from farmgame import dice as dcl
t = A.tavern
t.unlocked = True; t.tokens = 300; t.casino_open = True; t.casino_intro = True
A.toasts.clear()
A.open_gameroom(); A.gr_scroll_by(2000); A.gr_sel = "dice"; frames(40); snap("dc_map")
A.open_dice(force=True); frames(20); snap("dc_intro")
assert A.view == "dice"
for _ in range(3):
    A.dc_poke(); frames(2)
A.dc_chip = 10; A.dc_area_click("under"); A.dc_area_click("under")
A.dc_chip = 25; A.dc_area_click("seven")
A.toasts.clear(); frames(10); snap("dc_bet")
assert A.dc.bets == {"under": 20, "seven": 25, "over": 0}, A.dc.bets
dcl.FORCE_NEXT = (3, 4)
A.dc_roll(); frames(30); snap("dc_flight")
frames(120); A.toasts.clear(); frames(2); snap("dc_win")
A.dc_again(); dcl.FORCE_NEXT = (6, 5); A.dc_roll(); frames(150); A.toasts.clear(); frames(2); snap("dc_lose")
