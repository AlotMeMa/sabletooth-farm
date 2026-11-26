# 3.40.4: новые картинки пользователя — Якорь, улитки, лодки, хищники, кои, золотая рыбка, медали листа 6
A.tavern.unlocked = True; A.tavern.tokens = 300; A.tavern.sn_intro = True
f = A.farm
f.farm_index = 3; f.reset_run(); A.set_theme(); A.bg = A.build_background()
A.open_gameroom(); A.toasts.clear(); A.gr_open_game("snails")
for i, v in ((0, 10), (2, 25)):
    A.sn.select(i); A.sn.add_bet(A.tavern, v)
A.toasts.clear(); frames(10); snap("art_snails")
import random as _r; _r.seed(5)
A.sn_start(); frames(330); A.toasts.clear(); frames(2); snap("art_snails_race")
