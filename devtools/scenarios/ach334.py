# 3.34: достижения (окно, кнопка в таверне, тост) и разговор с барменом
set_medieval(); A.tavern.unlocked = True; A.tavern.tokens = 300
A.tavern.on("squirrel", 120); A.tavern.on("collect", 900); A.tavern.on("pet_cat", 20)
A.farm.total_earned = 5e12
A.ach_t = 0; frames(3)
A.open_achievements(); A.skip_anims(); frames(20); snap("ach_field")
A.ach_claim("squirrel_3"); A.ach_set_section("farm"); frames(10); snap("ach_farm")
A.modal = None; A.toasts.clear()
A.open_tavern(); A.tv_bubble = None; frames(20)
A.poke_barman(); frames(10); snap("talk_menu")
A.barman_topic("story"); frames(10); snap("talk_story")
A.barman_topic("news"); frames(10); snap("talk_news")
A.open_modal("settings"); A.settings_tab = "game"; A.skip_anims(); frames(10); snap("settings_game")
