# 3.26.1: быстрая грядка (цикл короче кадра) и пришествие — ничего не должно мельтешить:
# стадии растений не прыгают, монетка не выпрыгивает заново каждый цикл, полоска не дёргается
from farmgame import field_ui as fu, art as artmod
f = A.farm
f.farm_index = 2
f.reset_run()
A.set_theme()
f.levels = [400, 60, 25, 10, 5, 0, 0, 0, 0]
f.farmers = [True, False, False, False, False, False, False, False, False]
f.peasants = 1
f.money = 1e9
A.bg = A.build_background()
log = []
orig = fu.draw_crop
def spy(s, k, x, y, scale, grow, sway):
    log.append((k, round(grow, 3), round(scale, 3)))
    return orig(s, k, x, y, scale, grow, sway)
fu.draw_crop = spy
pops = []
def measure(tag, n=120):
    log.clear()
    born0 = list(A.coin_born)
    resets = 0
    for _ in range(n):
        prev = list(A.coin_born)
        frames(1)
        resets += sum(1 for a, b in zip(prev, A.coin_born) if b is not None and a != b)
    jumps = {}
    by = {}
    for k, g, sc in log:
        by.setdefault(k, []).append((g, sc))
    for k, seq in by.items():
        gs = [g for g, _ in seq[::3]]
        jumps[k] = sum(1 for a, b in zip(gs, gs[1:]) if abs(a - b) > 0.25)
    assert not any(jumps.values()), (tag, jumps)
    print(f"{tag}: циклы {[round(f.cycle_time(k)/f.growth_speed(),2) for k in range(5)]} "
          f"прыжков стадий {jumps}, монетка выпрыгнула {resets} раз за {n} кадров")
A.toasts.clear(); frames(10)
measure("обычно")
snap("fb_normal")
f.rain_cd = 0; A.click_rain(); A.toasts.clear()
frames(60)
measure("пришествие")
snap("fb_rush")
A.view = "barn"; frames(30); snap("fb_barn")
