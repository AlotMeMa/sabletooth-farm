# 3.28: блэкджек — только зимой, дилер Ворчун, упрощённые правила
import random as _r
t = A.tavern
t.unlocked = True; t.tokens = 300; t.casino_open = True; t.casino_intro = True
A.toasts.clear()
A.open_gameroom(); A.gr_scroll_by(500); frames(60); snap("bj_map_summer")
A.gr_open_game("blackjack"); frames(5)
assert A.view == "gameroom", "летом блэкджек закрыт"
f = A.farm
f.farm_index = 2; f.reset_run(); A.set_theme(); A.bg = A.build_background()
A.toasts.clear(); A.gr_open_game("blackjack"); frames(20); snap("bj_intro")
assert A.view == "blackjack"
for _ in range(3):
    A.bj_poke(); frames(2)
A.bj_chip = 10; A.bj_place(); A.bj_place(); frames(10); snap("bj_bet")
_r.seed(5)
A.bj_deal(); frames(4); snap("bj_dealing")
frames(60); snap("bj_dealt")
g = A.bj
if g.state == "player":
    from farmgame import blackjack as bjm
    while g.state == "player" and bjm.hand_value(g.player) < 15:
        A.bj_hit(); frames(40)
    snap("bj_hit")
    if g.state == "player":
        A.bj_stand()
frames(150); snap("bj_done")
print("итог:", g.result, "игрок", g.player, "дилер", g.dealer, "жетонов", t.tokens)
A.bj_again(); frames(10); snap("bj_again")
A.on_key(__import__("pygame").K_ESCAPE); frames(5)
assert A.view == "gameroom"
print("ставка вернулась, жетонов", t.tokens)
