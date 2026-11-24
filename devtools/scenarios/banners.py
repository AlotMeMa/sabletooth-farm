# 3.20: надписи на лентах (прокачка, сарай, мельница) и табличка «Рулетка»
set_summer(); A.toasts.clear(); A.mode = "upgrade"; frames(20); snap("bn_upgrade", crop=(250, 0, 750, 70), scale=2)
A.mode = "normal"; A.view = "barn"; frames(20); snap("bn_barn", crop=(450, 0, 900, 90), scale=2)
set_medieval(); A.toasts.clear(); A.view = "barn"; frames(20); snap("bn_mill", crop=(450, 0, 900, 90), scale=2)
A.tavern.unlocked = True; A.tavern.tokens = 500; A.open_tavern(); A.open_casino(); A.toasts.clear(); frames(30)
snap("bn_casino", crop=(0, 0, 600, 260), scale=2)
