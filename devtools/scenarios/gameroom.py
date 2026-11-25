# 3.27: Игровая — карта игр сверху вниз, колесо фортуны (раз в день), рулетка из Игровой, джекпот-скины
import random as _r
t = A.tavern
t.unlocked = True
t.tokens = 500
t.casino_open = True
t.casino_intro = True
A.toasts.clear()
A.poke_casino(); A.skip_anims(); frames(30); snap("gr_top")
assert A.view == "gameroom", A.view
A.gr_scroll_by(400); frames(60); snap("gr_bottom")
A.gr_scroll_by(-1000); frames(60)
before = t.tokens
A.gr_open_game("wheel"); A.skip_anims(); frames(20); snap("fw_ready")
A.fw_start(); frames(90); snap("fw_spinning")
frames(260); snap("fw_done")
assert A.fw_spin is None and not __import__("farmgame.wheel", fromlist=["x"]).can_spin(t)
print("колесо:", t.wheel_last, "жетонов было", before, "стало", t.tokens)
A.modal = None; frames(10); snap("gr_after")
A.gr_open_game("roulette"); frames(10)
assert A.view == "casino"
import pygame as _pg
A.on_key(_pg.K_ESCAPE); frames(5)
assert A.view == "gameroom", A.view
A.gr_open_game("blackjack"); frames(5)
assert A.view == "gameroom"
t.prizes["rainbow_notes"] = True; t.prizes["star_trail"] = True
A.open_modal("prizes"); A.prize_tab = "cosmetic"; A.prize_page = 3; A.skip_anims(); frames(10); snap("gr_prizes")
A.modal = None; A.view = "tavern"; frames(200); snap("gr_tavern_notes")
