# 3.40: скачки улиток в Игровой — карта, правила Якоря, ставка, забег, итог
import random as _r
from farmgame import snails as sn
t = A.tavern
t.unlocked = True; t.tokens = 300; t.casino_open = True; t.casino_intro = True
A.toasts.clear()
A.open_gameroom(); A.gr_scroll_by(800); A.gr_sel = "snails"; frames(40); snap("sn_map_locked")
f = A.farm
f.farm_index = 3; f.reset_run(); A.set_theme(); A.bg = A.build_background()
A.open_gameroom(); A.gr_scroll_by(800); A.gr_sel = "snails"; A.toasts.clear(); frames(40); snap("sn_map")
A.gr_open_game("snails"); frames(20); snap("sn_intro")
assert A.view == "snails"
for _ in range(3):
    A.sn_poke(); frames(2)
A.sn_lane_click(1); A.sn_chip = 10; A.sn_lane_click(1); A.sn_lane_click(1)
A.sn_lane_click(3); A.sn_chip = 25; A.sn_lane_click(3)               # 3.40.1: вторая улитка, фишки первой на месте
A.sn_lane_click(0); A.sn_chip = 5; A.sn_lane_click(0)
A.toasts.clear(); frames(10); snap("sn_bet")
assert A.sn.bets == [5, 20, 0, 25, 0], A.sn.bets
_r.seed(3)
A.sn_start(); frames(40); snap("sn_countdown")
frames(300); snap("sn_race")
frames(500); A.toasts.clear(); frames(5); snap("sn_done")
sn.FORCE_NEXT = True
A.sn_again(); A.sn_start(); frames(900); A.toasts.clear(); frames(5); snap("sn_win")
# 3.40.3: ставки на четырёх улиток, как у пользователя — подсказки «придёт первой» и итог чистыми
A.sn_again(); A.sn_clear(); A.sn.clear_bet(A.tavern)
for i, v in ((0, 10), (1, 25), (2, 10), (3, 25)):
    A.sn.select(i); A.sn.add_bet(A.tavern, v)
A.toasts.clear(); frames(5); snap("sn_bet4")
sn.FORCE_NEXT = True
A.sn_start(); frames(900); A.toasts.clear(); frames(5); snap("sn_net4")
