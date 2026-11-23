set_medieval(); A.tavern.unlocked = True
A.open_tavern(); A.tavern_refresh()
t = A.tavern
t.daily[0]["progress"] = t.daily[0]["target"]
t.daily[1]["progress"] = t.daily[1]["target"]; t.daily[1]["claimed"] = True
t.weekly["progress"] = t.weekly["target"]
A.open_board(); A.toasts.clear(); frames(20); snap("board_states")
t.weekly["claimed"] = True; frames(5); snap("board_weekly_done", crop=(630, 120, 900, 520))
