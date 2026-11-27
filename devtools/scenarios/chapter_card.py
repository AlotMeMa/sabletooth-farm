# 3.45.4: заставка главы после переезда
f = A.farm
f.farm_index = 2; f.reset_run(); A.set_theme(); A.bg = A.build_background()
f.run_earned = f.money = f.move_threshold() * 10
A.do_move(); frames(70); snap("card")
A.on_click((500, 300)); frames(40)
assert A.chapter_card is None, "заставка не пропустилась щелчком"
snap("after")
