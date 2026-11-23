# 3.17: примерка телефона (запускать с --phone): кадры всего экрана телефона, нажатия пальцем
def tap(pos, hold=0.0):
    A.touch_down(pos)
    frames(max(1, int(hold * 60)))
    A.touch_up(pos)
    frames(2)


def shot(name):
    A.present_wide()
    snap(name)


print("экран", A.wide["size"], "картинка", A.canvas, "сдвиг", A.wide["offset"])
A.tut.active = False if hasattr(A.tut, "active") else None
set_summer(); A.toasts.clear(); frames(30); shot("phone_field")

# 1) тап чуть мимо кнопки — срабатывает (кнопки — по отпусканию пальца)
A.modal = "settings"; A.settings_tab = "screen"; A.skip_anims(); frames(20)
btn = [z for z in A.zones if z[2] is not None][1]          # [0] — крестик окна, [1] — вкладка «Звук»
tap((btn[0].centerx, btn[0].top - 9))      # над вкладкой, в 9 точках от неё
print("тап рядом с вкладкой «Звук»:", A.settings_tab, "(ждём sound)")
frames(10); shot("phone_settings")

# 2) нажал и увёл палец с кнопки — не срабатывает
A.settings_tab = "screen"; frames(3)
A.touch_down(btn[0].center); frames(2); A.touch_move((btn[0].centerx, btn[0].bottom + 120)); A.touch_up((btn[0].centerx, btn[0].bottom + 120)); frames(2)
print("увёл палец:", A.settings_tab, "(ждём screen)")
A.modal = None; A.skip_anims(); frames(10)

# 3) долгое нажатие на кнопку с подсказкой — подсказка, без нажатия
tip_rect = None
for r, text in A.tips:
    z = A.zone_at(r.center)
    if z is not None and z[2] is not None:
        tip_rect, tip_text = r, text
        break
if tip_rect:
    state = (A.modal, A.mode, A.view)
    A.touch_down(tip_rect.center); frames(50); shot("phone_tip"); A.touch_up(tip_rect.center); frames(3)
    print("долгое нажатие на", repr(tip_text[:30]), "->", (A.modal, A.mode, A.view) == state, "(ждём True)")

# 4) свайп по монеткам
f = A.farm
f.stash = [100.0] * len(f.stash)
A.touch_down(A.coin_pos(0))
for k in range(1, len(f.stash)):
    A.touch_move(A.coin_pos(k))
A.touch_up(A.coin_pos(len(f.stash) - 1))
print("свайп: осталось несобранных грядок", sum(1 for v in f.stash if v > 0), "(ждём 0)")

# 5) догон времени после «телефона в кармане»
m0 = A.farm.farm_value(); A.catch_up(600); print("догон 10 мин: окно", A.modal, "прибавка", A.farm.farm_value() > m0)
A.modal = None; A.skip_anims()
A.portrait = True; frames(3); shot("phone_portrait"); A.portrait = False
