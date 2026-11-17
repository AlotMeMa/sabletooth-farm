from farmgame import hd as H_
set_medieval(); A.toasts.clear()
frames(3)
A.toggle_fullscreen()
print("wide", A.wide and (A.wide["size"], A.wide["offset"]), "fullscreen", A.fullscreen)
frames(3); A.t_real += 1; A.present_wide()
img = A.wide["display"].img; img.convert("RGB").save(OUT + "/wide.png"); print("кадр wide", img.size)
# мышь: реальная точка на окне -> координаты игры
ox, oy = A.wide["offset"]; k = A.hd_k
pygame.STATE["mouse"] = (int(ox + 500*k), int(oy + 320*k))
print("mouse ->", pygame.mouse.get_pos(), "lpos", A.lpos(pygame.STATE["mouse"]))
A.toggle_fullscreen(); print("back", A.wide, A.fullscreen, A.screen.get_size(), "mouse", pygame.mouse.get_pos())
A.edge_fill=False; A.toggle_fullscreen(); print("bars mode wide=", A.wide, A.fullscreen); A.toggle_fullscreen()
