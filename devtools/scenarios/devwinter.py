# 3.26: в режиме разработчика — кнопка «Зимнее поле (заготовка)»
A.open_modal("dev"); A.skip_anims(); frames(20); snap("dw_panel")
dict(A.dev_actions())["Зимнее поле (заготовка)"](); frames(40); snap("dw_field")
A.open_modal("dev"); A.skip_anims(); frames(5)
dict(A.dev_actions())["Назад на летнюю"](); frames(20); snap("dw_back")
