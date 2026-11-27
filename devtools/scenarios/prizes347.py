# 3.47: призы глав 3–5 — стойка (вкладка «Персонажи»), зал с новыми украшениями и группой на сцене
f, t = A.farm, A.tavern
f.farm_index = 2; f.reset_run(); A.set_theme(); A.bg = A.build_background()
t.unlocked = True; t.tokens = 5000
A.open_tavern(); A.toasts.clear(); frames(5)
A.open_modal("prizes"); A.prize_tab = "chars"; A.prize_page = 1; frames(30); snap("shop_chars")
A.prize_tab = "decor"; A.prize_page = 1; frames(5); snap("shop_decor")
A.modal = None
for pid in ("snow_globe", "antlers", "ice_chandelier", "ship_wheel", "goldfish_bowl", "nets", "dragon_egg",
            "dragon_shield", "brazier", "jellyfish", "frost_notes"):
    t.prizes[pid] = True
t.prizes["ice_idols"] = True; t._one_on_stage("ice_idols")
frames(60); snap("hall")
