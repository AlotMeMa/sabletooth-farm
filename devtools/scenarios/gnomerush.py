# 3.26: «Гномье пришествие» — гномы выскакивают на грядках, шаманы выходят на лужайку, пляшут и уходят;
# плюс выход из полного экрана (F11) через новое окно
import pygame
f = A.farm
f.farm_index = 2
f.reset_run()
A.set_theme()
f.levels = [30, 20, 15, 10, 8, 6, 4, 0, 0]
f.farmers = [True, False, True, False, False, False, False, False, False]
f.peasants = 2
f.money = 1e9
A.bg = A.build_background()
A.toasts.clear(); frames(20); snap("r_before")
f.rain_cd = 0; A.click_rain(); A.toasts.clear()
frames(25); snap("r_coming")
frames(120); snap("r_dance")
frames(7); snap("r_dance2")
f.rain_left = 1.2; frames(30); snap("r_leaving")
frames(60); snap("r_after")
assert not f.helper_rush()
A._fs_toggled = 0; A.toggle_fullscreen(); assert A.fullscreen
A._fs_toggled = 0; A.toggle_fullscreen(); assert not A.fullscreen and A.wide is None
assert pygame.STATS.get("display_quit", 0) >= 1, pygame.STATS
frames(10); snap("r_window")
