# 3.45.3: щелчок мимо окна закрывает его; по окну — нет; колесо, пока крутится, — не закрывается
from farmgame.config import W, H
for name in ("settings", "shop", "tree", "move", "achievements", "stats"):
    A.open_modal(name); frames(30)
    r = A.panel_hit
    A.on_click(r.center); frames(2)
    assert A.modal == name, (name, "закрылось от щелчка по окну")
    A.on_click((r.x - 8 if r.x > 10 else 5, r.bottom + 5 if r.bottom < H - 6 else 5)); frames(2)
    assert A.modal is None, (name, "не закрылось щелчком мимо")
    print("ok", name)
A.open_modal("settings"); frames(30); snap("settings")
