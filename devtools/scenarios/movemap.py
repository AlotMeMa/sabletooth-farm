# 3.23: карта глав в окне «Переезд»
set_summer(); A.toasts.clear(); A.open_modal("move"); A.skip_anims(); frames(40); snap("mm_summer")
A.move_info = True; frames(10); snap("mm_info"); A.move_info = False
A.map_select(2); frames(40); snap("mm_winter")
set_medieval(); A.toasts.clear(); A.modal = None; A.open_modal("move"); A.skip_anims(); frames(40); snap("mm_medieval")
A.map_select(0); frames(40); snap("mm_done")
# 3.35: зима открыта — со средневековья видно «Что будет при переезде», на зиме — финал
A.map_select(2); frames(40); snap("mm_med_to_winter")
A.move_info = True; frames(10); snap("mm_med_info"); A.move_info = False
