set_medieval(); A.tavern.unlocked = True; A.tavern.tokens = 23
A.open_tavern(); A.tv_bubble = None; A.toasts.clear()
frames(2)
A.open_songs(); A.skip_anims(); frames(20); snap("songs_menu")
A.do_order_song(2); A.toasts.clear(); frames(20); snap("song_playing")
A.open_songs(); frames(20); snap("songs_menu_busy")
A.modal=None; A.view="field"; A.farm.boost_left=600; frames(20); snap("song_pill_field", crop=(0,0,500,320))
