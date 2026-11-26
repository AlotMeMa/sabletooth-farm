# -*- coding: utf-8 -*-
"""Окна: магазин, дерево, крестьяне, скупщик, настройки, статистика, переезд, офлайн, разработчик.

Примесь к App (3.15: вынесено из app.py без изменений). Общие импорты и константы — ui_common.
"""
from .ui_common import *  # noqa: F401,F403


class WindowsUI:
    SETTINGS_TABS = (("sound", "Звук"), ("screen", "Экран"), ("game", "Игра"))

    def sell_farm(self):
        self.leaving_tier = self.truck_tier()
        gained = self.farm.sell_to_truck()
        self.sfx.play("sell")
        if gained > 0:
            self.quest("truck")
        self.modal = None
        self.mode = "normal"
        self.truck_state = "leaving"
        self.floaters.clear()
        if self.crow:
            self.shoo_crow() if self.crow["phase"] == "sit" else self.end_crow()
        self.toast(f"{self.farm_info()['buyer_cap']} забрал урожай! +{gained} {CUR['gen']}. Начинаем заново с бонусом!", 4)
        self.save()

    def reset_everything(self):
        if not self.confirm_reset:
            self.confirm_reset = True
            return
        self.farm = Farm()
        self.tavern = Tavern()
        self.view = "field"
        self.set_theme()
        self.bandit = None
        self.crow = None
        self.crow_timer = self.crow_delay()
        self.truck_state, self.truck_x = "away", VEHICLE_FAR
        self.confirm_reset = False
        self.modal = None
        self.tut.restart()
        self.save()
        self.toast("Прогресс сброшен")

    def do_move(self):
        f = self.farm
        old = self.farm_info()
        if not f.move_farm():
            return
        self.sfx.play("fanfare")
        self.set_theme()
        self.tavern.replace_impossible(self.farm_info(), blocked=self.quest_blocked())
        self.modal = None
        self.view, self.mode = "field", "normal"
        self.truck_state, self.truck_x = "away", VEHICLE_FAR
        self.crow = None
        self.squirrel = None
        self.bandit = None
        self.floaters.clear()
        self.move_notified = False
        self.toast(f"Добро пожаловать: {self.farm_info()['name']}! Всё заново, но доход x{FARM_BONUS ** f.farm_index}", 5)
        self.toast(f"Трофей «{old['trophy']['name']}»: {old['trophy']['text']}", 5)
        self.save()

    def draw_shop(self):
        s, f = self.screen, self.farm
        r = self.panel(580, 470, "МАГАЗИН УЛУЧШЕНИЙ")
        peasants = self.farm_info()["peasants"]
        tabs = (("fert", "Удобрения  x3"), ("farm", self.helpers()["title"] if peasants else "Фермеры (копят урожай)"))
        for idx, (tab, label) in enumerate(tabs):
            b = pygame.Rect(r.x + 20 + idx * 275, r.y + 66, 265, 38)
            active = self.shop_tab == tab
            rounded(s, (245, 175, 50) if active else BTN_BLUE, b, 10, 3)
            draw_text(s, label, 16, b.center)
            self.zone_btn(b, lambda t=tab: (setattr(self, "shop_tab", t), setattr(self, "shop_page", 0)))

        if self.shop_tab == "farm" and peasants:
            self.draw_peasant_shop(r)
            return
        items = []
        for i in range(N_CROPS):
            if self.shop_tab == "fert":
                if f.levels[i] > 0:
                    items.append((f.fert_cost(i), i, f"Прибыль x3  (куплено: {f.fert[i]})",
                                  lambda i=i: self.buy_shop(f.buy_fert, i), True))
            else:
                if not f.farmers[i]:
                    planted = f.levels[i] > 0
                    items.append((f.farmer_cost(i), i, "Растёт без остановки, урожай копится" if planted else "Сначала посади культуру",
                                  lambda i=i: self.buy_shop(f.buy_farmer, i), planted))
        items.sort(key=lambda it: it[0])
        per = 4
        pages = max(1, math.ceil(len(items) / per))
        self.shop_page = min(self.shop_page, pages - 1)
        if not items:
            draw_text(s, "Все фермеры наняты!" if self.shop_tab == "farm" else "Пока нечего удобрять", 20,
                      (r.centerx, r.centery), (90, 70, 60), outline=None)
        for n, (price, i, sub, cb, enabled) in enumerate(items[self.shop_page * per:(self.shop_page + 1) * per]):
            row = pygame.Rect(r.x + 20, r.y + 118 + n * 70, r.w - 40, 62)
            rounded(s, (255, 245, 190), row, 10, 3)
            icon = pygame.Rect(row.x + 6, row.y + 5, 52, 52)
            rounded(s, (170, 225, 245), icon, 8, 2)
            draw_crop(s, i, icon.centerx, icon.bottom - 10, 1.0)
            draw_text(s, CROPS[i]["name"], 18, (row.x + 70, row.y + 20), (90, 70, 60), anchor="midleft", outline=None)
            draw_text(s, sub, 13, (row.x + 70, row.y + 44), (140, 110, 95), anchor="midleft", outline=None)
            ok = enabled and f.money >= price
            b = pygame.Rect(row.right - 150, row.y + 11, 140, 40)
            rounded(s, BTN_GREEN if ok else BTN_GREY, b, 8, 3)
            draw_text(s, "$" + fmt(price), 17, b.center)
            if enabled:
                self.zone_btn(b, cb, 8)
        if pages > 1:
            draw_text(s, f"{self.shop_page + 1} / {pages}", 16, (r.centerx, r.bottom - 36), (90, 70, 60), outline=None)
            if self.shop_page > 0:
                self.button((r.centerx - 90, r.bottom - 54, 40, 36), "<", lambda: setattr(self, "shop_page", self.shop_page - 1), BTN_BLUE)
            if self.shop_page < pages - 1:
                self.button((r.centerx + 50, r.bottom - 54, 40, 36), ">", lambda: setattr(self, "shop_page", self.shop_page + 1), BTN_BLUE)

    def draw_tree(self):
        s, f = self.screen, self.farm
        r = self.panel(820, 560, CUR["tree"])
        brown, soft = (90, 70, 60), (150, 115, 100)
        draw_cur_icon(s, r.x + 40, r.y + 80, 0.9)
        draw_text(s, f"{f.leaves} {CUR['gen']}   доход {fmt_mult(f.home_leaves)}", 18, (r.x + 64, r.y + 80), brown,
                  anchor="midleft", outline=None)
        note = {"seal": f"Каждая непотраченная {CUR['one']} даёт +2% к доходу",
                "frostleaf": "Каждый непотраченный листочек даёт +2% к доходу"}.get(CUR["icon"],
                                                                              "Каждый непотраченный лист даёт +2% к доходу")
        draw_text_fit(s, note, 13, (r.right - 24, r.y + 80), r.w * 0.42, soft, anchor="midright", outline=None)
        col_w = (r.w - 40) // len(TREE)
        for bi, (bname, nodes) in enumerate(TREE):
            cx = r.x + 20 + bi * col_w + col_w // 2
            draw_text(s, bname, 17, (cx, r.y + 114), brown, outline=None)
            prev = None
            for ni, node in enumerate(nodes):
                nid = node["id"]
                nr = pygame.Rect(0, 0, col_w - 18, 58)
                nr.center = (cx, r.y + 160 + ni * 74)
                if prev is not None:
                    done = f.up(nodes[ni - 1]["id"]) > 0
                    pygame.draw.line(s, OUT, (cx, prev.bottom), (cx, nr.top), 7)
                    pygame.draw.line(s, (120, 210, 100) if done else (190, 180, 175), (cx, prev.bottom), (cx, nr.top), 3)
                lvl, mx, cost = f.up(nid), len(node["costs"]), f.tree_cost(nid)
                if cost is None:
                    color, look = (250, 212, 90), "tree_node_max"
                elif not f.tree_available(nid):
                    color, look = (205, 200, 196), "tree_node_locked"
                elif f.leaves >= cost:
                    color, look = (150, 222, 120), "tree_node_ready"
                else:
                    color, look = (175, 215, 240), "tree_node_open"
                selected = self.tree_sel == nid
                if skin.plate(s, look, nr):          # 3.20: своя карточка (assets/ui/tree_sheet или ui/tree_node_*)
                    if selected:
                        pygame.draw.rect(s, (230, 90, 60), nr.inflate(6, 6), 3, border_radius=12)
                    # 3.23: в левом верхнем углу картинки — листик/замок: название правее и не шире рамки
                    draw_text_fit(s, node["name"], 13, (nr.centerx + 6, nr.y + 16), nr.w - 40, brown, outline=None)
                else:
                    rounded(s, color, nr, 10, 4 if selected else 2, (230, 90, 60) if selected else OUT)
                    draw_text(s, node["name"], 13, (nr.centerx, nr.y + 15), brown, outline=None)
                for k in range(mx):  # точки уровней
                    px = nr.x + 12 + k * min(12, (nr.w - 80) // max(1, mx))
                    if not blit_sprite(s, "ui/tree_pip_on" if k < lvl else "ui/tree_pip_off", px, nr.bottom - 15, 0.34,
                                       "center"):
                        pygame.draw.circle(s, OUT, (px, nr.bottom - 15), 5)
                        pygame.draw.circle(s, (90, 190, 80) if k < lvl else WHITE, (px, nr.bottom - 15), 4)
                if cost is None:
                    draw_text(s, "МАКС", 13, (nr.right - 10, nr.bottom - 15), (170, 120, 20), anchor="midright", outline=None)
                elif not f.tree_available(nid):
                    draw_text(s, "закрыто", 12, (nr.right - 10, nr.bottom - 15), soft, anchor="midright", outline=None)
                else:
                    draw_text(s, str(cost), 14, (nr.right - 26, nr.bottom - 15), brown, anchor="midright", outline=None)
                    draw_cur_icon(s, nr.right - 15, nr.bottom - 15, 0.45)
                self.zone_btn(nr, lambda n=nid: setattr(self, "tree_sel", n))
                prev = nr

        info = pygame.Rect(r.x + 20, r.bottom - 112, r.w - 40, 96)
        rounded(s, (255, 245, 210), info, 10, 2)
        if self.tree_sel not in TREE_NODES:     # выбранное улучшение осталось от дерева прошлой фермы (после переезда)
            self.tree_sel = None
        if self.tree_sel is None:
            draw_text(s, "Нажми на улучшение, чтобы узнать, что оно даёт", 16, (info.centerx, info.centery - 12), soft,
                      outline=None)
            draw_text_fit(s, f"Каждая покупка поднимает цену всех других улучшений на {round(TREE_INFLATION * 100)}% — "
                             "выбирай, что брать первым", 14, (info.centerx, info.centery + 16), info.w - 30, brown,
                          outline=None)
            return
        node = TREE_NODES[self.tree_sel]
        nid = node["id"]
        lvl, cost = f.up(nid), f.tree_cost(nid)
        draw_text(s, f"{node['name']}  (ур. {lvl}/{len(node['costs'])})", 18, (info.x + 16, info.y + 20), brown,
                  anchor="midleft", outline=None)
        draw_text(s, "Сейчас: " + node["eff"](lvl), 14, (info.x + 16, info.y + 48), brown, anchor="midleft", outline=None)
        if cost is None:
            draw_text(s, "Максимальный уровень!", 14, (info.x + 16, info.y + 72), (170, 120, 20), anchor="midleft", outline=None)
            return
        draw_text(s, "Дальше: " + node["eff"](lvl + 1), 14, (info.x + 16, info.y + 72), (60, 140, 50),
                  anchor="midleft", outline=None)
        b = pygame.Rect(info.right - 210, info.y + 24, 194, 48)
        if not f.tree_available(nid):
            need = TREE_NODES[node["prev"]]["name"]
            # две строки, прижаты к правому краю, чтобы длинное название не вылезало за рамку
            draw_text(s, "Сначала возьми", 14, (info.right - 16, info.y + 36), (190, 80, 70), anchor="midright", outline=None)
            draw_text(s, f"«{need}»", 14, (info.right - 16, info.y + 58), (190, 80, 70), anchor="midright", outline=None)
            return
        ok = f.leaves >= cost
        infl = f.tree_inflation(nid)
        if infl > 1.005:   # 3.31: видно, насколько подорожало из-за других покупок
            draw_text_fit(s, f"дороже в x{infl:.2f} из-за других улучшений", 12, (b.centerx, info.y + 12), b.w + 12,
                          (190, 80, 70), outline=None)
        rounded(s, BTN_GREEN if ok else BTN_GREY, b, 10, 3)
        draw_text(s, f"Купить: {cost}", 18, (b.centerx - 12, b.centery))
        draw_cur_icon(s, b.right - 26, b.centery, 0.55)
        spent = max(0, cost - (f.leaves - f.home_leaves))     # столько «домашних» листьев перестанут давать +2%
        if ok and spent:
            draw_text_fit(s, f"доход от {CUR['gen']}: {fmt_mult(f.home_leaves)} -> {fmt_mult(f.home_leaves - spent)}",
                          12, (b.centerx, info.bottom - 11), b.w + 12, soft, outline=None)
        if ok:
            self.zone_btn(b, lambda: self.buy_tree(nid))

    def buy_tree(self, nid):
        if self.farm.buy_tree(nid):
            self.quest("tree")
            self.sfx.play("levelup")
            self.toast(f"Улучшено: {TREE_NODES[nid]['name']}! Остальное подорожало на {round(TREE_INFLATION * 100)}%", 2.5)
            if nid in ("sq_often",):
                self.squirrel_timer = min(self.squirrel_timer, self.squirrel_delay())
            if nid in ("scarecrow",):
                self.crow_timer = max(self.crow_timer, self.crow_delay())

    def draw_peasant_shop(self, r):
        s, f = self.screen, self.farm
        brown, soft = (90, 70, 60), (140, 110, 95)
        row = pygame.Rect(r.x + 20, r.y + 124, r.w - 40, 90)
        rounded(s, (255, 245, 190), row, 10, 3)
        icon = pygame.Rect(row.x + 10, row.y + 15, 60, 60)
        rounded(s, (200, 230, 170), icon, 8, 2)
        draw_helper_head(s, icon.centerx, icon.centery + 2, 2.2)
        hp = self.helpers()
        draw_text(s, f"Нанять {hp['acc']}", 19, (row.x + 86, row.y + 26), brown, anchor="midleft", outline=None)
        draw_text(s, f"Всего {f.peasants} из {PEASANT_MAX}, свободно {f.free_peasants()}", 14, (row.x + 86, row.y + 54),
                  soft, anchor="midleft", outline=None)
        b = pygame.Rect(row.right - 160, row.y + 22, 146, 46)
        if f.peasants >= PEASANT_MAX:
            skin.draw_max(s, b, 14, "Все наняты")
        else:
            ok = f.money >= f.peasant_cost()
            rounded(s, BTN_GREEN if ok else BTN_GREY, b, 8, 3)
            draw_text(s, "$" + fmt(f.peasant_cost()), 17, b.center)
            self.zone_btn(b, self.do_hire_peasant, 8)
        if self.farm_info()["barn"] == "mill":
            tips = [
                "Крестьянин на грядке — она растёт без остановки и копит урожай (кнопка у грядки).",
                "Крестьяне на мельнице мелют зерно, в пекарне пекут хлеб.",
                "Их можно в любой момент переставить: снять с грядки и отправить на мельницу.",
            ]
        else:                                                   # 3.25: гномы зимой — только грядки
            tips = [
                f"{hp['one'].capitalize()} на грядке — она растёт без остановки и копит урожай (кнопка у грядки).",
                f"Их можно в любой момент переставить: снять с одной грядки и поставить на другую.",
            ]
        for n, t in enumerate(tips):
            draw_text_fit(s, t, 13, (r.centerx, r.y + 250 + n * 26), r.w - 50, soft, outline=None)

    def helpers(self):
        """3.25: как зовут помощников-артель на этой ферме (крестьяне, гномы)."""
        return HELPERS.get(self.farm_info().get("helpers", "peasants"), HELPERS["peasants"])

    def do_hire_peasant(self):
        f = self.farm
        price = f.peasant_cost()
        if f.hire_peasant():
            self.quest("peasant")
            self.sfx.play("buy")
            self.toast(f"Нанят {self.helpers()['one']}! Свободно: {f.free_peasants()}", 2)
        else:
            self.toast(f"Не хватает денег: нужно ${fmt(price)}", 2)

    def do_toggle_peasant(self, k):
        f = self.farm
        was = f.farmers[k]
        if f.toggle_peasant(k):
            cx, cy = crop_center(k)
            self.floater(cx + 50, cy + 10, "снят" if was else "за работу!", (220, 240, 200))
        else:
            self.toast(f"Нет свободных {self.helpers()['gen']}: найми в магазине или сними с другой грядки", 2.5)

    def buy_shop(self, fn, i):
        price = self.farm.fert_cost(i) if fn == self.farm.buy_fert else self.farm.farmer_cost(i)
        if fn(i):
            self.sfx.play("buy")
            self.toast(f"Куплено для: {CROPS[i]['name']}")
        else:
            self.toast(f"Не хватает денег: нужно ${fmt(price)}, у тебя ${fmt(self.farm.money)}", 2.5)

    def draw_truck_modal(self):
        s, f = self.screen, self.farm
        tier = self.truck_tier()
        name, color, _ = TRUCK_TIERS[tier]
        r = self.panel(600, 440, name.upper())
        self.draw_vehicle(r.centerx + 30, r.y + 160, color, tier=tier)
        p = f.potential_leaves()
        brown = (90, 70, 60)
        y = r.y + 182
        draw_text(s, f"{self.farm_info()['buyer_cap']} заберёт урожай и деньги в обмен на {CUR['title'].lower()}!", 15, (r.centerx, y), brown, outline=None)
        aq = f.aquarium_value() if f.has_fishery() else 0.0
        if aq > 0:          # 3.42: рыботорговец выкупает и рыбок из аквариума (по нынешней цене)
            draw_text_fit(s, f"Заработано за забег: ${fmt(f.run_total())} — с уловом и рыбками аквариума (${fmt(aq)})",
                          16, (r.centerx, y + 28), r.w - 40, brown, outline=None)
        else:
            draw_text(s, f"Заработано за забег (с урожаем на грядках): ${fmt(f.run_total())}", 17, (r.centerx, y + 28), brown, outline=None)
        draw_cur_icon(s, r.centerx - 95, y + 66, 0.9)
        draw_text(s, f"+{p} {CUR['gen']}", 28, (r.centerx + 15, y + 66), (110, 220, 90))
        after = f.home_leaves + p
        draw_text(s, f"Множитель дохода: {fmt_mult(f.home_leaves)}  ->  {fmt_mult(after)}   (+2% за каждую)",
                  17, (r.centerx, y + 104), brown, outline=None)
        draw_text_fit(s, f"Ещё ${fmt(f.money_for_next_leaf())} — и будет ещё +1. Чем дольше копишь, тем больше!",
                      13, (r.centerx, y + 130), r.w - 50, (140, 110, 95), outline=None)
        draw_text_fit(s, f"Грядки, здания и работники обнулятся. {CUR['title']} и дерево остаются (до переезда).",
                      13, (r.centerx, y + 150), r.w - 50, (190, 80, 70), outline=None)
        self.button((r.centerx - 230, r.bottom - 76, 250, 50), "Продать ферму!", self.sell_farm, BTN_GREEN, p > 0, 20)
        self.button((r.centerx + 40, r.bottom - 76, 190, 50), "Ещё покоплю", self.close_modal, BTN_BLUE, True, 18)

    def toggle_music(self):
        self.music.toggle_mute()
        self.toast("Музыка выключена (M — включить)" if self.music.muted else "Музыка включена", 1.5)

    def set_volume_from_x(self, drag, x):
        """Ползунок громкости: позиция мыши по ширине полоски -> 0..100% (шаг 5%). drag = (полоска, "music"/"sfx")."""
        rect, which = drag
        frac = max(0.0, min(1.0, (x - rect.x) / max(1, rect.w)))
        vol = round(frac * 20) / 20
        self.music.muted = False
        if which == "music":
            self.music.volume = vol
        else:
            self.sfx.volume = vol
        self.music.apply_volume()

    def start_volume_drag(self, rect, which="music"):
        self.volume_drag = (rect, which)
        self.set_volume_from_x(self.volume_drag, self.click_pos[0])

    def draw_settings(self):
        s, m = self.screen, self.music
        r = self.panel(540, 470, "НАСТРОЙКИ")
        soft = (150, 125, 110)
        x, w = r.x + 30, r.w - 60
        # вкладки
        tw = (w - 2 * 10) // 3
        for i, (key, title) in enumerate(self.SETTINGS_TABS):
            on = self.settings_tab == key
            self.button((x + i * (tw + 10), r.y + 72, tw, 42), title, lambda k=key: setattr(self, "settings_tab", k),
                        (245, 175, 50) if on else BTN_BLUE, True, 18)
        y = r.y + 136
        tab = self.settings_tab
        if tab == "sound":
            if m.ok and m.current is None:
                draw_text(s, "нет файла в assets/music/", 12, (x + w, y + 20), soft, anchor="midright", outline=None)
            self.volume_slider("Музыка", m.volume, "music", x, y + 20, w)
            self.volume_slider("Звуки", self.sfx.volume, "sfx", x, y + 82, w)
            self.button((x, y + 138, w, 46), ("Включить звук" if m.muted else "Выключить звук") + "   (M)",
                        self.toggle_music, BTN_GREEN if m.muted else (230, 110, 100), m.ok, 18)
        elif tab == "screen":
            half = (w - 10) // 2
            self.button((x, y, half, 46), f"{'Во весь экран' if self.fullscreen else 'В окне'}  (F11)",
                        self.toggle_fullscreen, (150, 120, 220), True, 17)
            self.button((x + w - half, y, half, 46), "Края: " + ("размытый фон" if self.edge_fill else "полосы"),
                        lambda: self.set_edge_fill(not self.edge_fill), (150, 120, 220), True, 15)
            self.tip(pygame.Rect(x + w - half, y, half, 46), "Полный экран: по бокам размытое продолжение картинки или чёрные полосы")
            active = "auto" if self.hd_k != 1 else "off"
            label = "Чёткость: HD" if self.hd_mode == "auto" else "Чёткость: обычная"
            self.button((x, y + 56, w, 46), label + ("*" if self.hd_mode != active else ""), self.toggle_hd,
                        (120, 160, 220), True, 18)
            if self.hd_mode != active:
                info = "* чёткость поменяется после перезапуска игры"
            else:
                info = f"картинка {self.canvas[0]}×{self.canvas[1]}" + (f"  (HD x{self.hd_k:g})" if self.hd_k != 1 else "")
            draw_text(s, info, 13, (r.centerx, y + 116), soft, outline=None)
            draw_text(s, "Кадров в секунду:", 17, (x, y + 160), (90, 70, 60), anchor="midleft", outline=None)
            bw = 70
            for i, fps in enumerate(FPS_LIMITS):
                on = self.fps_limit == fps
                self.button((x + w - (3 - i) * (bw + 8) + 8, y + 140, bw, 40), str(fps),
                            lambda v=fps: self.set_option("fps_limit", v), (245, 175, 50) if on else BTN_BLUE, True, 18)
            self.button((x, y + 196, w, 46), "Счётчик кадров: " + ("показан" if self.show_fps else "скрыт"),
                        lambda: self.set_option("show_fps", not self.show_fps),
                        BTN_GREEN if self.show_fps else BTN_GREY, True, 18)
        else:
            half0 = (w - 12) // 2       # 3.34: рядом со статистикой — достижения
            self.button((x, y, half0, 46), "Статистика", lambda: self.open_modal("stats"), (235, 170, 70), True, 18)
            from . import achievements as _ach
            self.button((x + w - half0, y, half0, 46), "Достижения" + (" (!)" if _ach.claimable(self.tavern) else ""),
                        self.open_achievements, (235, 170, 70), True, 18)
            self.button((x, y + 56, w, 46), "Подсказки у кнопок: " + ("включены" if self.show_tips else "выключены"),
                        lambda: self.set_option("show_tips", not self.show_tips),
                        BTN_GREEN if self.show_tips else BTN_GREY, True, 18)
            draw_text(s, "подсказка появится, если задержать курсор на кнопке", 13, (r.centerx, y + 116), soft,
                      outline=None)
            self.button((x, y + 196, w, 46), "Обучение заново (бармен)", self.tut_restart, (150, 120, 220), True, 17)
            half = (w - 12) // 2
            self.button((x, y + 140, half, 46), "Сохранить", lambda: (self.save(), self.toast("Сохранено!")), BTN_BLUE)
            label = "Точно? Ещё раз!" if self.confirm_reset else "Сбросить всё"
            self.button((x + w - half, y + 140, half, 46), label, self.reset_everything, (230, 90, 80), True, 17)
        self.button((r.centerx - 165, r.bottom - 72, 160, 46), "Закрыть", self.close_modal, BTN_GREEN)
        self.button((r.centerx + 15, r.bottom - 72, 180, 46), "Выйти из игры", self.quit_game, (150, 110, 100), True, 17)
        draw_text(s, f"версия {GAME_VERSION}", 12, (r.x + 26, r.y + 56), soft, anchor="midleft", outline=None)

    def set_option(self, name, value):
        setattr(self, name, value)
        self.save()

    def volume_slider(self, title, vol, which, x, y, w):
        s, m = self.screen, self.music
        brown = (90, 70, 60)
        if not m.ok:
            note = "звук недоступен"
        elif m.muted:
            note = "выкл"
        else:
            note = f"{round(vol * 100)}%"
        draw_text(s, f"{title}: {note}", 17, (x, y), brown, anchor="midleft", outline=None)
        bar = pygame.Rect(x + 12, y + 18, w - 24, 22)
        frac = 0.0 if m.muted else vol
        draw_bar(s, bar, frac, BTN_GREY if m.muted else (120, 196, 96))
        skin.draw_knob(s, bar.x + bar.w * frac, bar.centery, m.muted)
        if m.ok:
            self.zone(bar.inflate(28, 24), lambda b=bar: self.start_volume_drag(b, which))

    def draw_stats(self):
        s, f = self.screen, self.farm
        r = self.panel(560, 440, "СТАТИСТИКА")
        brown = (90, 70, 60)
        lines = [
            f"Ферма: {self.farm_info()['name']} ({f.farm_index + 1}/{len(FARMS)}), бонус ферм x{FARM_BONUS ** f.farm_index}",
            f"Всего заработано: ${fmt(f.total_earned)}",
            f"За этот забег: ${fmt(f.run_earned)}  (+${fmt(f.total_stash())} на грядках)",
            f"Ферм продано: {f.prestiges}",
            f"{CUR['title']}: {f.leaves}  (доход {fmt_mult(f.home_leaves)})",
            f"{CUR['title']} за продажу сейчас: {f.potential_leaves()}",
        ]
        if f.farm_index > 0:
            lines.append("Трофеи: " + ", ".join(FARMS[i]["trophy"]["name"] for i in range(f.farm_index)))
        if f.has_next_farm():
            lines.append(f"До переезда: ${fmt(max(0.0, f.move_threshold() - f.run_total()))}")
        for n, line in enumerate(lines):
            draw_text_fit(s, line, 17, (r.x + 34, r.y + 84 + n * 32), r.w - 68, brown, anchor="midleft", outline=None)
        self.button((r.centerx - 100, r.bottom - 72, 200, 46), "<  Назад", lambda: self.open_modal("settings"), BTN_BLUE)

    # ------------------------------------------------------------ режим разработчика
    # ------------------------------------------------------------ режим разработчика (F1)
    # 3.29 (просьба пользователя): кнопки разложены по местам — у каждой локации свой набор, по максимуму;
    # окно открывается на вкладке того места, где ты сейчас. Общие вещи — во вкладке «Общее».
    DEV_TABS = (("field", "Поле"), ("barn", "Сарай"), ("tavern", "Таверна"), ("games", "Игровая"), ("all", "Общее"))
    DEV_VIEW_TAB = {"field": "field", "barn": "barn", "tavern": "tavern", "board": "tavern", "fireside": "tavern",
                    "gameroom": "games", "casino": "games", "blackjack": "games",
                    "snails": "games", "dice": "games"}

    def dev_fishery_tab(self, money, go):
        """3.39.1: режим разработчика для аквариума Рыбацкой деревни."""
        f = self.farm

        def best():
            opened = [i for i in range(N_CROPS) if f.levels[i] > 0] or [0]
            if not any(f.levels):
                f.levels[0] = 1
            return max(opened, key=lambda i: f.fish_price(i))

        def fill(adult):
            def act():
                i = best()
                while f.tank_used() < f.fy_cap:
                    f.fy_fish.append([i + 1, f.fish_price(i) or 1.0, 1.0 if adult else 0.0, f._new_seed()])
                f.fy_grace = 0.0
            return act

        def grow_all():
            for fish in f.fy_fish:
                fish[2] = 1.0

        def roe():
            i = best()
            if f.tank_used() < f.fy_cap:
                f.fy_eggs.append([i + 1, random.uniform(0.2, 0.8), random.uniform(0.3, 0.8), 3.0])

        def pred(rank):
            def act():
                f._pred_gone()
                f.spawn_predator(rank)
                go("barn")
            return act

        def soon():
            if f.fy_pred:
                f._pred_gone()
            f.fy_timer = 5.0
            if not f.fy_fish:
                fill(False)()

        def ate_all():
            if not f.fy_pred:
                f.spawn_predator(1)
            for fish in f.fy_fish:
                f.fy_pred_val += f.fish_worth(fish) * f.predator()["ratio"]
            f.fy_pred_eaten += len(f.fy_fish)
            f.fy_fish = []
            go("barn")

        def fat():
            if not f.fy_pred:
                f.spawn_predator(3)
            f.fy_pred_eaten = max(f.fy_pred_eaten, 15)
            f.fy_pred_val += f.total_income() * 60

        def autowin():
            self.fy_autowin = not getattr(self, "fy_autowin", False)
            self.toast("Вылов: всегда удаётся" if self.fy_autowin else "Вылов: по-честному", 2)

        def unspook():
            f.fy_spook = 0.0

        def runs():
            f.fy_runs += 1
            self.toast(f"Забегов в деревне: {f.fy_runs} — первый хищник сильнее", 2)

        def tank_max():
            f.fy_cap = FISH_TANK_MAX

        def reset():
            f.fy_fish, f.fy_eggs = [], []
            f._pred_gone()
            f.fy_cap, f.fy_rank, f.fy_up = FISH_TANK_START, 0, FISH_UP_START

        win = "вкл" if getattr(self, "fy_autowin", False) else "выкл"
        return [("Заполнить мальками", fill(False)), ("Заполнить взрослыми", fill(True)),
                ("Все рыбы — взрослые", grow_all), ("Икра (малёк через 3 с)", roe),
                ("Хищник через 5 с", soon), ("Аквариум: 25 мест", tank_max)] + \
               [(f"Хищник ранга {r}: {PRED_RANK_NAMES[r].lower()}", pred(r)) for r in range(1, 6)] + \
               [("Хищник съел всех (тлеет)", ate_all), ("Хищник съел 15 (толстый)", fat),
                (f"Вылов всегда удаётся: {win}", autowin), ("Снять «насторожился»", unspook),
                (f"Забегов в деревне +1 (сейчас {f.fy_runs})", runs), ("Аквариум с нуля", reset),
                ("Деньги x1000", money), ("В садки", lambda: go("barn"))]

    def dev_here(self):
        return self.DEV_VIEW_TAB.get(self.view, "field")

    def dev_groups(self):
        """{вкладка: [(подпись, действие)]}"""
        from . import wheel as wh
        from . import blackjack as bjl
        f, t = self.farm, self.tavern
        pm = f.price_mult
        info = self.farm_info()

        def go(view):
            self.modal, self.view = None, view

        # ---------- поле ----------
        def money():
            f.money = max(f.money, 1000 * pm) * 1000
        def leaves():
            f.leaves += 1000
            f.home_leaves += 1000
        def to_truck():
            need = (TRUCK_MIN_LEAVES / f.truck_mult() / LEAF_FACTOR) ** 2 * LEAF_UNIT * pm
            f.earn(max(0.0, need - f.run_total()) + 1)
        def to_move():
            f.earn(max(0.0, f.move_threshold() - f.run_total()) + 1)
        def move_now():
            if not f.has_next_farm():
                self.toast("Следующей фермы пока нет", 2)
                return
            to_move()
            self.do_move()
        def to_farm(fid):
            def act():
                f.farm_index = next(n for n, fm in enumerate(FARMS) if fm["id"] == fid)
                f.home_leaves = f.leaves
                f.reset_run()
                self.set_theme()
                go("field")
                self.toast(f"{self.farm_info()['name']} (для тестов, всё с нуля)", 3)
            return act
        def all_crops():
            for i in range(N_CROPS):
                f.levels[i] += 50
        def open_all():
            for i in range(N_CROPS):
                f.levels[i] = max(f.levels[i], 1)
        def helpers_all():
            if info["peasants"]:
                f.peasants = max(f.peasants, PEASANT_MAX)
            for i in range(N_CROPS):
                if f.levels[i]:
                    f.farmers[i] = True
        def collect_all():
            got = sum(f.collect(i) or 0 for i in range(N_CROPS))
            self.toast(f"Собрано ${fmt(got)}", 2)
        def tree_max():
            for n, node in TREE_NODES.items():
                f.tree[n] = len(node["costs"])
        def tree_reset():
            f.tree = {}
            self.toast("Дерево сброшено", 2)
        def weather():
            f.rain_left, f.rain_cd = 0.0, 0.0
            go("field")
            self.click_rain()
        def sun():
            f.sun_cd = 0.0
        def squirrel(g):
            go("field")
            self.spawn_squirrel(golden=g)
        def pest(kind):
            go("field")
            if kind == "crow":
                self.spawn_crow() if info["crow"] else self.toast("На этой ферме ворон нет", 2)
            elif kind == "frost":
                if info["frost"]:
                    self.frost_timer = 0
                else:
                    self.toast("На этой ферме мороза нет", 2)
            elif info["bandits"]:
                self.spawn_bandit()
            else:
                self.toast("На этой ферме разбойников нет", 2)
        def offline():
            amt = f.offline_earn(3600)
            self.offline_info = (3600.0, amt)
            self.modal = "offline"
        field = [("Деньги x1000", money), (f"+1000 {CUR['gen']}", leaves),
                 ("Все грядки +50 ур.", all_crops), ("Открыть все грядки", open_all),
                 (f"{self.helpers()['title'] if info['peasants'] else 'Помощники'} на все грядки", helpers_all),
                 ("Собрать весь урожай", collect_all),
                 (f"{info['weather']} сейчас", weather), ("Солнце: бонус готов", sun),
                 ("Белка", lambda: squirrel(False)), ("Золотая белка", lambda: squirrel(True))]
        if info["crow"]:
            field.append(("Ворона", lambda: pest("crow")))
        if info["frost"]:
            field.append(("Мороз на грядку", lambda: pest("frost")))
        if info["bandits"]:
            field.append(("Разбойник", lambda: pest("bandit")))
        field += [(f"Позвать: {info['buyer']}", to_truck), ("Заработать до переезда", to_move),
                  ("Переехать сейчас", move_now), ("Дерево на максимум", tree_max), ("Дерево сбросить", tree_reset),
                  ("Офлайн: «тебя не было 1 ч»", offline)]
        field += [(f"Ферма: {fm['name']}", to_farm(fm["id"])) for fm in FARMS if fm["id"] != info["id"]]

        # ---------- сарай / мельница ----------
        def barn():
            for a in range(N_ANIMALS):
                f.a_levels[a] = max(f.a_levels[a], 5)
                f.a_keeper[a] = True
        def feed():
            for a in range(N_ANIMALS):
                if f.a_levels[a]:
                    f.a_feed[a] = f.feeder_cap(a)
        def products():
            base = max(1.0, f.total_income()) * 60
            for a in range(N_ANIMALS):
                if f.a_levels[a]:
                    f.a_store[a] += base
        def barn_reset():
            f.a_levels = [0] * N_ANIMALS
            f.a_keeper = [False] * N_ANIMALS
            f.a_feed = [0.0] * N_ANIMALS
            f.a_store = [0.0] * N_ANIMALS
        def mill():
            f.m_levels = [3, 3]
            f.peasants = max(f.peasants, 8)
        def hopper():
            f.hopper = f.hopper_cap()
        barn_tab = [("Все звери ур.5 + скотники", barn), ("Накормить всех доверху", feed),
                    ("Продукты готовы (+минута дохода)", products), ("Сарай с нуля", barn_reset),
                    ("Деньги x1000", money)]
        if info.get("barn") == "fishery":           # 3.39.1: аквариум — воспроизводить ситуации быстро
            barn_tab = self.dev_fishery_tab(money, go)
        if info.get("barn") == "mill":
            barn_tab += [("Мельница и пекарня ур.3", mill), ("Засыпать зерно доверху", hopper)]
        if info.get("barn") != "fishery":
            barn_tab += [("В сарай", lambda: go("barn"))]

        # ---------- таверна ----------
        def tokens(n):
            def act():
                t.unlocked = True
                t.tokens = max(0, t.tokens + n)
                self.toast(f"Жетонов: {t.tokens}", 2)
            return act
        def quests_done():
            t.unlocked = True
            self.tavern_refresh()
            for q in t.daily + [t.weekly]:
                q["progress"] = q["target"]
            self.modal = None
            self.open_tavern()
            self.open_board()
        def new_day():
            t.unlocked = True
            t.day = t.week = ""
            self.tavern_refresh()
            self.toast("Таверна: новые задания дня и недели", 2)
        def tavern_debug():
            self.tavern_debug = not self.tavern_debug
            if t.unlocked:
                self.modal = None
                self.open_tavern()
        def prizes_all():
            for p in PRIZES:
                t.prizes[p["id"]] = True
            t.prize_off = []
            self.toast("Все призы получены (артист на сцене — первый)", 2)
        def prizes_none():
            t.prizes, t.prize_off = {}, []
        def artist(pid):
            def act():
                t.prizes[pid] = True
                if pid in t.prize_off:
                    t.prize_off.remove(pid)
                t._one_on_stage(pid)
                self.modal = None
                self.open_tavern()
            return act
        def fireside():
            t.unlocked = True
            self.modal = None
            self.open_tavern()
            self.open_fireside()
        tavern_tab = [("Жетоны +500", tokens(500)), ("Жетоны в ноль", tokens(-10 ** 9)),
                      ("Все задания готовы", quests_done), ("Новый день и неделя", new_day),
                      ("Все призы", prizes_all), ("Призы с нуля", prizes_none)]
        tavern_tab += [(f"На сцену: {p['name']}", artist(p["id"])) for p in PRIZES if p.get("stage")]
        tavern_tab += [("Посиделки у камина", fireside), ("Показать разметку" + (" (вкл)" if self.tavern_debug else ""),
                                                            tavern_debug)]

        # ---------- Игровая ----------
        def open_games():
            t.unlocked = t.casino_open = True
            self.modal = None
            self.open_gameroom()
        def wheel_again():
            t.wheel_day = ""
            self.toast("Колесо можно крутить снова", 2)
        def wheel_jackpot():
            t.wheel_day = ""
            wh.FORCE_NEXT = len(wh.SEGMENTS) - 1
            self.toast("Следующий спин — ДЖЕКПОТ", 2)
        def wheel_week():
            wh.WEEK_SHIFT += 1
            self.toast(f"Джекпот недели: {wh.jackpot_for()['name']}", 2)
        def roulette_rules():
            t.casino_intro = False
            open_games()
            self.open_casino()
        def blackjack():
            if not bjl.unlocked(f.farm_index):
                to_farm("winter")()
            open_games()
            self.open_blackjack()
        def bj_force(kind):
            def act():
                bjl.FORCE_NEXT = {"natural": [("A", "spades"), ("K", "hearts"), ("9", "clubs"), ("7", "diamonds")],
                                  "dealer21": [("9", "spades"), ("7", "hearts"), ("A", "clubs"), ("K", "diamonds")],
                                  "bust": [("10", "spades"), ("6", "hearts"), ("10", "clubs"), ("7", "diamonds"),
                                           ("K", "hearts")]}[kind]
                self.toast("Следующая раздача подготовлена", 2)
            return act
        games_tab = [("Открыть Игровую", open_games), ("Жетоны +500", tokens(500)), ("Жетоны в ноль", tokens(-10 ** 9)),
                     ("Колесо: крутить снова", wheel_again), ("Колесо: следующий — джекпот", wheel_jackpot),
                     ("Колесо: джекпот следующей недели", wheel_week),
                     ("Рулетка: правила снова", roulette_rules), ("Блэкджек: открыть (зимой)", blackjack),
                     ("Блэкджек: правила снова", lambda: setattr(t, "bj_intro", False)),
                     ("Блэкджек: следующая — очко", bj_force("natural")),
                     ("Блэкджек: у дилера очко", bj_force("dealer21")),
                     ("Блэкджек: «Взять» — перебор", bj_force("bust")), ("Призовая стойка", lambda: self.open_modal("prizes"))]

        # 3.40: скачки улиток
        def snails_open():
            from . import snails as snl
            if not snl.unlocked(f.farm_index):
                to_farm("fishing")()
            t.unlocked = True
            self.open_snails()

        def sn_force(win):
            def act():
                from . import snails as snl
                snl.FORCE_NEXT = win
                self.toast("Следующий забег: " + ("твоя улитка первая" if win else "твоя улитка проиграет"), 2)
            return act
        games_tab += [("Улитки: открыть (деревня)", snails_open),
                      ("Улитки: правила снова", lambda: setattr(t, "sn_intro", False)),
                      ("Улитки: следующий — победа", sn_force(True)),
                      ("Улитки: следующий — проигрыш", sn_force(False))]

        # 3.43: кости (глава 5 ещё не готова — открываются отсюда)
        def dice_force(pair):
            def act():
                from . import dice as dcl
                dcl.FORCE_NEXT = pair
                self.toast(f"Следующий бросок: {pair[0]} и {pair[1]}", 2)
            return act
        games_tab += [("Кости: открыть (глава 5)", lambda: (setattr(t, "unlocked", True), self.open_dice(force=True))),
                      ("Кости: правила снова", lambda: setattr(t, "dc_intro", False)),
                      ("Кости: следующий — 3 и 4 (семь)", dice_force((3, 4))),
                      ("Кости: следующий — 6 и 6", dice_force((6, 6))),
                      ("Кости: следующий — 1 и 2", dice_force((1, 2)))]

        # ---------- общее ----------
        def speed():
            self.time_scale = {1: 10, 10: 60, 60: 1}[self.time_scale]
        def fps():
            self.show_fps = not self.show_fps
        def save_now():
            self.save()
            self.toast("Сохранено", 1.5)
        def tutorial():
            from .tutorial import Tutorial
            self.tut = Tutorial()
            self.toast("Обучение начнётся заново", 2)
        all_tab = [(f"Скорость времени: x{self.time_scale}", speed), ("Показать кадры/с" + (" (вкл)" if self.show_fps else ""), fps),
                   ("Сохранить сейчас", save_now), ("Обучение заново", tutorial),
                   ("Полный экран (F11)", self.toggle_fullscreen), ("Перезагрузить картинки", self.dev_reload_art),
                   ("На поле", lambda: go("field")), ("В таверну", lambda: (setattr(t, "unlocked", True), self.open_tavern(),
                                                                         setattr(self, "modal", None)))]
        return {"field": field, "barn": barn_tab, "tavern": tavern_tab, "games": games_tab, "all": all_tab}

    def dev_actions(self):
        """Все действия разработчика одним списком (для сценариев и старых тестов)."""
        out, seen = [], set()
        for acts in self.dev_groups().values():
            for label, cb in acts:
                if label not in seen:
                    seen.add(label)
                    out.append((label, cb))
        # старые имена кнопок (сценарии 3.25–3.28)
        groups = dict(out)
        out.append(("Зимнее поле", groups.get("Ферма: Зимнее поле", lambda: None)))
        out.append(("Назад на летнюю", groups.get("Ферма: Летняя ферма", lambda: None)))
        return out

    def dev_reload_art(self):
        """Забыть подогнанные картинки в памяти — новые файлы из assets/ подхватятся без перезапуска."""
        from . import art_sprites
        art_sprites._sprite_cache.clear()
        art_sprites._sprite_scaled.clear()
        self.bg = self.build_background()
        self.cs_bg = None
        self.gr_bg = None
        self.toast("Картинки перечитаны", 2)

    def draw_dev(self):
        r = self.panel(660, 600, "РЕЖИМ РАЗРАБОТЧИКА")
        s = self.screen
        draw_text(s, f"Сохранение: {os.path.basename(cfg.SAVE_FILE)}   •   {self.clock.get_fps():.0f} кадр/с, "
                  f"картинка {self.canvas[0]}×{self.canvas[1]}   •   F1 — закрыть", 13,
                  (r.centerx, r.y + 66), (140, 110, 95), outline=None)
        here = self.dev_here()
        tab = getattr(self, "dev_tab", None) or here
        groups = self.dev_groups()
        tw = (r.w - 60 - 4 * 6) // 5
        for i, (key, title) in enumerate(self.DEV_TABS):
            label = title + (" •" if key == here else "")
            self.button((r.x + 30 + i * (tw + 6), r.y + 82, tw, 34), label, lambda k=key: setattr(self, "dev_tab", k),
                        (245, 175, 50) if key == tab else BTN_BLUE, True, 14)
        acts = groups.get(tab, [])
        per = 22
        page = min(getattr(self, "dev_page", 0), max(0, (len(acts) - 1) // per))
        for n, (label, cb) in enumerate(acts[page * per:(page + 1) * per]):
            col, row = n % 2, n // 2
            self.button((r.x + 30 + col * 305, r.y + 126 + row * 38, 295, 32), label, cb, (230, 110, 110), True, 14)
        if len(acts) > per:
            self.button((r.right - 90, r.bottom - 44, 60, 30), f"{page + 1}/{(len(acts) - 1) // per + 1}",
                        lambda: setattr(self, "dev_page", (page + 1) % ((len(acts) - 1) // per + 1)), BTN_BLUE, True, 14)
        draw_text(s, "• — вкладка места, где ты сейчас", 12, (r.x + 30, r.bottom - 26), (140, 110, 95),
                  anchor="midleft", outline=None)

    def draw_offline(self):
        s = self.screen
        secs, amt = self.offline_info
        r = self.panel(460, 280, "С ВОЗВРАЩЕНИЕМ!")
        brown = (90, 70, 60)
        h, m = int(secs // 3600), int(secs % 3600 // 60)
        draw_text(s, f"Тебя не было {h} ч {m} мин.", 18, (r.centerx, r.y + 86), brown, outline=None)
        draw_text(s, "На ферме накопилось:", 18, (r.centerx, r.y + 116), brown, outline=None)
        draw_text(s, "+$" + fmt(amt), 30, (r.centerx, r.y + 154), GOLD)
        draw_text(s, "Не забудь собрать!", 14, (r.centerx, r.y + 182), (140, 110, 95), outline=None)
        self.button((r.centerx - 80, r.bottom - 72, 160, 46), "Ура!", self.close_modal)
