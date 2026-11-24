# 3.20: трофеи над камином, жетоны слева, песня сверху, бармен целиком; реплики бармена
set_medieval(); A.tavern.unlocked = True; A.tavern.tokens = 5000
for pid in ("horseshoe", "cup", "statue", "crystal", "cat", "kettle", "flowers"):
    A.tavern.buy_prize(A.farm, pid)
A.farm.song, A.farm.song_left = 1, 300
A.open_tavern(); A.tv_bubble = None; A.toasts.clear(); frames(20); snap("t320_tavern")
snap("t320_mantel", crop=(120, 280, 300, 400), scale=2)
snap("t320_barman", crop=(640, 300, 820, 430), scale=2)
A.say_barman(); frames(5); snap("t320_line")
