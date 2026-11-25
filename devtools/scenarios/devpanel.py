# 3.29: режим разработчика по местам — каждая кнопка каждой вкладки нажимается без ошибок
import traceback
A.quit_game = lambda: None
t = A.tavern
t.unlocked = True; t.tokens = 500; t.casino_open = True; t.casino_intro = True; t.bj_intro = True
errors = []
for view, opener in (("field", lambda: None), ("barn", lambda: setattr(A, "view", "barn")),
                     ("tavern", A.open_tavern), ("gameroom", A.open_gameroom)):
    A.modal = None; A.view = "field"; opener(); frames(2)
    A.modal, A.dev_tab, A.dev_page = "dev", None, 0
    A.skip_anims(); frames(3); snap("dev_" + view)
    assert A.dev_here() == {"field": "field", "barn": "barn", "tavern": "tavern", "gameroom": "games"}[view]
for tab in ("field", "barn", "tavern", "games", "all"):
    n = len(A.dev_groups()[tab])
    for i in range(n):
        label, cb = A.dev_groups()[tab][i]
        if "Переехать" in label or label.startswith("Полный экран"):
            continue
        try:
            cb(); frames(3)
        except Exception:
            errors.append((tab, label, traceback.format_exc().splitlines()[-1]))
    print(f"вкладка {tab}: кнопок {n}")
A.modal, A.dev_tab = "dev", "games"; A.skip_anims(); frames(3); snap("dev_games_tab")
# подкрутки игр работают
from farmgame import wheel as wh, blackjack as bjm
t.wheel_day = ""; wh.FORCE_NEXT = len(wh.SEGMENTS) - 1
got = wh.spin(t); assert got[0] == len(wh.SEGMENTS) - 1, got
bjm.FORCE_NEXT = [("A", "spades"), ("K", "hearts"), ("9", "clubs"), ("7", "diamonds")]
g = bjm.Blackjack(); t.tokens = 100; g.add_bet(t, 10); g.deal(t); assert g.result == "blackjack", g.result
print("ошибок:", len(errors))
for e in errors: print("  ", e)
