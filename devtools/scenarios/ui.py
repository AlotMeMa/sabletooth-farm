from farmgame.tutorial import Tutorial
set_summer(); A.toasts.clear()
A.open_modal("shop"); A.skip_anims(); frames(40); snap("ui_shop")
A.modal=None; A.closing=None
A.open_modal("settings"); A.settings_tab="game"; frames(40); snap("ui_settings")
A.modal=None; A.closing=None; A.tut=Tutorial(); A.tut_next(); frames(30); A.tut_click_box(); frames(2); snap("ui_tut")
set_medieval(); f=A.farm; f.m_levels=[3,2]; f.m_workers=[1,1]; f.peasants=5; f.hopper=f.hopper_cap()*0.5; f.flour=1e6; f.bread=1e6
A.view="barn"; A.toasts.clear(); frames(10); snap("ui_mill")
A.tavern.unlocked=True; A.tavern.tokens=30; A.open_tavern(); A.open_songs(); frames(40); A.toasts.clear(); frames(2); snap("ui_songs")
