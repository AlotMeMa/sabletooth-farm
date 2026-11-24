# -*- coding: utf-8 -*-
"""Таверна на экране: переходы, задания и награды, жители, звук, зал и его разметка (режим разработчика).

Части экрана таверны (3.17): board_ui — доска заданий, songs_ui — песни барда и плашки бафов,
tavern_life_ui — живой зал (такт, огонь, пар, трофеи, гирлянда), tavern_hud_ui — кнопки и жетоны.
Разметка зала, рисунки людей и фоны — tavern_art (всё оттуда доступно и через tavern_ui, как раньше).
"""
from .tavern_art import *  # noqa: F401,F403
from .tavern_art import _layout_procedural  # noqa: F401


class TavernUI:
    def init_tavern(self):
        self.tavern = tv.Tavern()
        self.tavern_check = 0.0
        self.audio_scene = None
        self.tv_bubble = None          # [x, y, text, life]
        self.tv_talk = None            # [индекс гостя на балконе, текст, life]
        self.tv_talk_timer = 2.0
        self.tv_notes = []             # ноты от барда: [x, y, life, vx, цвет]
        self.tv_note_timer = 0.0
        self.barman_line = 0
        self.tavern_greeted = False
        self.tavern_bg = self.tavern_fg = None
        self.tavern_custom = False
        self.tl = load_layout(False)
        self.tavern_occ = []
        self.tavern_debug = False      # режим разработчика: показать разметку зала
        self.tavern_check_seen = False
        self.board_bg = None
        # 3.5: живой зал
        self.tv_solo = 0.0             # бард играет соло (секунд осталось)
        self.tv_half = None            # номер последней полудоли, на которой бард пускал ноту
        self.tv_embers = []            # искры камина: [x, y, vx, vy, life, max_life]
        self.tv_ember_t = 0.0
        self.tv_steam = []             # пар: [x, y, t, life, фаза, сила]
        self.tv_steam_t = 0.0
        self.tv_twinkle_t = 3.0
        self.tv_motes = None

    def quest_blocked(self):
        """Задания, которые сейчас не выполнить: их не выдаём."""
        f, out = self.farm, set()
        if PEASANT_MAX - f.peasants < 2:
            out.add("peasant")
        if sum(MILL_MAX_LVL - lvl for lvl in f.m_levels) < 3:
            out.add("build")
        left = sum(len(node["costs"]) - f.up(nid) for nid, node in f.nodes().items())
        if left < 4:
            out.add("tree")
        return out

    def tavern_refresh(self):
        changed = self.tavern.refresh(self.farm_info(), blocked=self.quest_blocked())
        self.pay_owed()
        return changed

    # ---------- переходы ----------
    def open_tavern(self):
        if not self.tavern.unlocked:
            return
        self.tavern_refresh()
        self.view, self.mode = "tavern", "normal"
        self.modal = None
        if self.tavern_bg is None:
            self.tavern_bg, self.tavern_fg, self.tavern_custom = build_tavern_scene()
            self.tl = load_layout(self.tavern_custom)
            self.tavern_occ = build_occluders(self.tavern_bg, self.tl["occluders"])
        if not self.tavern_greeted:
            self.tavern_greeted = True
            hint = (" Тебя уже ждёт награда!" if self.tavern.claimable() else "")
            self.say_barman("Заходи, путник! Задания — на доске, слева." + hint)

    def open_board(self):
        if self.board_bg is None:
            self.board_bg = build_board_background()
        self.view = "board"

    def leave_tavern(self):
        self.view = "field"

    def sync_scene_audio(self):
        """Музыка и гул таверны включаются/выключаются сами по тому, где мы сейчас."""
        want = "tavern" if self.view in ("tavern", "board", "casino") else None
        if want and self.tavern.prize_on("bard_girl") and has_scene_music("tavern_girl"):
            want = "tavern_girl"            # 3.15.2: певица поёт свою песню
        if want != self.audio_scene:
            self.audio_scene = want
            self.music.play_for(self.farm_info()["id"], want)
            self.sfx.ambient("crowd" if want else None)
        self.sfx.update_ambient()

    # ---------- задания ----------
    def quest(self, event, n=1):
        if event == "collect":
            self.tut_event("collect")
        for q in self.tavern.on(event, n):
            self.sfx.play("quest")
            big = q is self.tavern.weekly
            self.toast(("Задание НЕДЕЛИ выполнено" if big else "Задание выполнено") + f": «{q['title']}»! Награда — в таверне", 4)

    def quest_money(self, minutes):
        """Деньги за задание = столько минут дохода грядок (без дождя и буста), но не меньше небольшой суммы."""
        f = self.farm
        inc = sum(f.income_per_sec(i, False) for i in range(N_CROPS))
        if f.boost_left > 0:
            inc /= 2
        return max(inc * 60 * minutes, 20 * f.price_mult * minutes)

    def grant_reward(self, minutes, prestige, boost):
        """Выдаёт ферме награду задания (жетоны начисляет сама таверна). Возвращает, сколько денег дали."""
        f = self.farm
        money = self.quest_money(minutes)
        f.earn(money)
        if prestige:
            f.leaves += prestige
            f.home_leaves += prestige
            f.leaves_earned += prestige
        if boost:
            f.boost_left += boost * 60
        return money

    def pay_owed(self):
        """Награды за задания, которые сменились незабранными (полночь, понедельник), выдаём автоматически."""
        owed = self.tavern.take_owed()
        if not owed:
            return
        money = sum(self.grant_reward(o["minutes"], o["prestige"], o["boost"]) for o in owed)
        tokens, prestige, boost = (sum(o[k] for o in owed) for k in ("tokens", "prestige", "boost"))
        parts = ["+$" + fmt(money), f"+{tokens} жетонов"]
        if prestige:
            parts.append(f"+{prestige} {CUR['gen']}")
        if boost:
            parts.append(f"доход x2 на {boost} мин")
        self.sfx.play("claim")
        self.toast("Незабранные награды таверны выданы сами: " + ", ".join(parts), 7)
        self.save()

    def claim_quest(self, q, pos):
        reward = self.tavern.claim(q)
        if not reward:
            return
        minutes, tokens, prestige, boost = reward
        money = self.grant_reward(minutes, prestige, boost)
        parts = ["+$" + fmt(money), f"+{tokens} жетонов"]
        if prestige:
            parts.append(f"+{prestige} {CUR['gen']}")
        if boost:
            parts.append(f"доход x2 на {boost} мин")
        self.sfx.play("claim")
        self.floater(pos[0], pos[1] - 20, "+$" + fmt(money))
        self.toast("Награда: " + ", ".join(parts), 4)
        for d in self.tavern.just_done:
            self.sfx.play("quest")
            self.toast(f"Задание НЕДЕЛИ выполнено: «{d['title']}»!", 4)
        self.save()

    # ---------- жители ----------
    def say_barman(self, text=None):
        if text is None:
            text = tv.BARMAN_LINES[self.barman_line % len(tv.BARMAN_LINES)]
            self.barman_line += 1
        b = self.tl["barman"]
        self.tv_bubble = [b["x"], b["waist"] - 112 * b["k"], text, 4.5]

    def poke_bard(self):
        """Клик по барду — соло: 8 долей ноты летят на каждую полудолю, бард качается сильнее."""
        d = self.tl["bard"]
        lines = tv.GIRL_LINES if self.tavern.prize_on("bard_girl") else tv.BARD_LINES
        self.tv_bubble = [d["x"], d["y"] - 135 * d["k"], random.choice(lines), 3.5]
        self.tv_solo = 8 * 60.0 / self.tl["music"]["bpm"]
        for _ in range(3):
            self.tv_notes.append([d["x"] + 34 * d["k"] + random.uniform(-10, 10), d["y"] - 72 * d["k"] + random.uniform(-8, 8),
                                  2.0, random.uniform(0, 45), random.choice(NOTE_COLORS)])
        for _ in range(3):
            self.fx.twinkle(d["x"] + random.uniform(-45, 45), d["y"] - random.uniform(40, 120) * d["k"], 7, life=0.6)

    def poke_casino(self):
        t = self.tavern
        if DEV or t.casino_open:        # 3.14: открыто, когда жетонов впервые набралось CASINO_UNLOCK_TOKENS
            self.open_casino()
            return
        self.toast(f"Игорный зал откроется, когда накопишь {CASINO_UNLOCK_TOKENS} жетонов (у тебя {t.tokens})", 3)
        self.say_barman(f"Туда пускают с {CASINO_UNLOCK_TOKENS} жетонами в кармане. Выполняй задания с доски!")

    def tavern_tick(self, dt):
        t = self.tavern
        if not t.unlocked and self.farm.farm_index >= tv.TAVERN_FROM_FARM:
            t.unlocked = True
            self.tavern_refresh()
            self.toast("Открылась таверна «Хмельной колос»! Кнопка — над «Магазином»", 5)
            self.sfx.play("fanfare")
        if t.unlocked and t.check_casino():
            self.toast(f"Открылся игорный зал! Дверь «Казино» — справа в таверне", 5)
            self.sfx.play("fanfare")
            self.save()
        self.tavern_check -= dt
        if t.unlocked and self.tavern_check <= 0:
            self.tavern_check = 5.0
            if self.tavern_refresh() and self.tavern_check_seen:
                self.toast("На доске в таверне — новые задания!", 4)
            self.tavern_check_seen = True
        self.sync_scene_audio()
        if self.view != "tavern":
            return
        rdt = min(dt, 0.25)
        if self.tv_bubble:
            self.tv_bubble[3] -= rdt
            if self.tv_bubble[3] <= 0:
                self.tv_bubble = None
        if self.tv_talk:
            self.tv_talk[2] -= rdt
            if self.tv_talk[2] <= 0:
                self.tv_talk = None
        self.tv_talk_timer -= rdt
        if self.tv_talk_timer <= 0 and self.tl["talkers"]:
            self.tv_talk_timer = random.uniform(2.5, 5.0)
            self.tv_talk = [random.randrange(len(self.tl["talkers"])), random.choice(BALCONY_LINES), 2.2]
        self.tick_tavern_life(rdt)
        for n in self.tv_notes:
            n[0] += n[3] * rdt + math.sin(self.t_real * 3 + n[2]) * 0.4
            n[1] -= 40 * rdt
            n[2] -= rdt
        self.tv_notes = [n for n in self.tv_notes if n[2] > 0][-30:]

    # ---------- экран: зал ----------
    def draw_tavern_view(self):
        s, tt = self.screen, self.t_real
        s.blit(self.tavern_bg, (0, 0))
        self.draw_tavern_life(s, tt)
        self.draw_tavern_trophies(s)
        if not self.tavern_custom:
            # огонь в камине
            for i in range(5):
                fx = 228 + i * 14
                h = 26 + 12 * math.sin(tt * 7 + i * 1.7) + 6 * math.sin(tt * 13 + i)
                poly(s, (250, 150, 50), [(fx - 9, 430), (fx + 9, 430), (fx + 2, 430 - h), (fx - 1, 430 - h * 1.1)], 0)
                poly(s, (255, 225, 110), [(fx - 4, 430), (fx + 4, 430), (fx + 1, 430 - h * 0.6)], 0)
            # гости на балконе (за перилами)
            for n, (x, look, face) in enumerate(BALCONY_PEOPLE):
                talking = self.tv_talk is not None and self.tv_talk[0] == n
                bob = math.sin(tt * 2 + n * 1.3) * 1.5
                lift = -0.9 if look.get("mug") and math.sin(tt * 0.8 + n) > 0.85 else 0.35
                hands = draw_person(s, x, BALCONY_FLOOR + bob, 0.85, look, tt, talking, arms=(0.3, lift), face=face)
                if look.get("mug"):
                    draw_mug(s, hands[1][0] + 4, hands[1][1] - 4, 0.6)
        # бармен по пояс (протирает кружку); за стойкой — стойка рисуется поверх него
        L = self.tl
        b = L["barman"]
        wipe = math.sin(tt * 3)
        # 3.5: протирает кружку — чуть поворачивается и ходит из стороны в сторону (низ закрыт стойкой)
        # низ продлён на 30 px: локти и фартук уходят за стойку без щели (её наклон открывал фон под локтем)
        down = extended_down("characters/barman", 30 / max(0.1, b["sprite_scale"]))
        if not down or not blit_tf(s, down, b["x"] + 1.3 * math.sin(tt * 3.2), b["waist"] + 32 + math.sin(tt * 1.5),
                                   b["sprite_scale"], angle=1.5 * math.sin(tt * 3.2 + 0.6)):
            look = dict(top=(200, 210, 225), apron=True, hair=(70, 50, 40), style="bald", mustache=True)
            talking = self.tv_bubble is not None and self.tv_bubble[0] == b["x"]
            hands = draw_person(s, b["x"], b["waist"], b["k"], look, tt, talking, upper=True,
                                arms=(0.9 + 0.25 * wipe, 0.9 - 0.25 * wipe))
            draw_mug(s, hands[0][0] + 4, hands[0][1] - 6, 0.7 * b["k"])
            rounded(s, (245, 245, 240), (P(hands[1][0] - 7 * b["k"]), P(hands[1][1] - 5 * b["k"]), P(14 * b["k"]), P(10 * b["k"])), 3, 2)
        if not self.tavern_custom:
            for n, (x, look, face) in enumerate(PATRONS):
                cheers = math.sin(tt * 0.9 + n * 2) > 0.8
                hands = draw_person(s, x, 520, 1.05, look, tt, cheers, arms=(0.3, -1.0 if cheers else 0.5), face=face)
                draw_mug(s, hands[1][0] + 2, hands[1][1] - 5, 0.75)
            s.blit(self.tavern_fg, (0, 0))
        self.draw_tavern_trophies(s, front=True)  # то, что лежит на стойке перед барменом
        for img, pos in self.tavern_occ:          # стойка и всё, что стоит перед персонажами
            s.blit(img, pos)
        # бард на сцене
        d = L["bard"]
        beat = self.tv_beat()
        hit = max(0.0, 1.0 - (beat % 1.0) * 3.5)         # 1 — ровно на доле, быстро спадает
        solo = self.tv_solo > 0
        strum = hit
        bob = 2.5 * hit * (1.6 if solo else 1.0)
        bx, by, k = d["x"], d["y"], d["k"]
        sway = math.sin(beat * math.pi) * (5.0 if solo else 2.5)   # туда-сюда за две доли
        girl = self.tavern.prize_on("bard_girl")
        if not blit_tf(s, "characters/bard_girl" if girl else "characters/bard", bx, by, d["sprite_scale"],
                       sx=1 + 0.02 * hit, sy=1 - 0.035 * hit * (1.5 if solo else 1.0), angle=sway):
            look = (dict(top=(230, 225, 205), dress=(190, 90, 80), hair=(200, 140, 70), style="long", girl=True)
                    if girl else dict(top=(60, 140, 90), legs=(150, 60, 60), hair=(170, 110, 60), style="bard"))
            talking = self.tv_bubble is not None and self.tv_bubble[0] == bx
            draw_person(s, bx, by - bob, k, look, tt, talking, arms=(1.35, 0.55 + 0.35 * strum))
            draw_lute(s, bx + 3.5 * k, by - bob - 40 * k, k, strum)
        notes = [f"icons/note_{i}" for i in range(1, 5) if has_sprite(f"icons/note_{i}")]
        fancy = self.tavern.prize_on("gold_notes")     # 3.14: приз «Нарядные ноты»
        for x, y, life, _vx, col in self.tv_notes:
            if fancy:
                col = (255, 214, 90)
                if int(life * 10) % 7 == 0:
                    blit_light(s, x + 5, y - 6, 26, (255, 236, 150), 160, 0.0)
            if notes:   # свои ноты из assets/icons/note_1..4: появляются, покачиваются и тают
                n = NOTE_COLORS.index(col) if col in NOTE_COLORS else 0
                age = 2.2 - life
                grow = min(1.0, 0.55 + age * 2.5)
                blit_tf(s, notes[n % len(notes)], x, y, grow, angle=12 * math.sin(life * 4 + n),
                        pivot="center", alpha=255 * min(1.0, life / 0.6))
            else:
                draw_note(s, x, y, color=col)
        self.zone(L["barman_zone"], self.say_barman)
        self.zone(L["bard_zone"], self.open_songs)
        self.tip(L["bard_zone"], "Бард: заказать песню за жетоны")
        # стрелка к доске заданий
        r = L["board_sign"]
        arrow = [(r.x, r.centery), (r.x + 34, r.y + 10), (r.x + 34, r.y + 26), (r.right, r.y + 26),
                 (r.right, r.bottom - 26), (r.x + 34, r.bottom - 26), (r.x + 34, r.bottom - 10)]
        hover = self.modal is None and r.collidepoint(self.mouse)
        grow = self.btn_anim(r)
        if hover or grow:      # 3.13.2: подсветка по форме стрелки (раньше — квадратная рамка вокруг)
            cx, cy = r.centerx + 8, r.centery
            k = 1.0 + 0.04 * grow
            arrow = [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in arrow]
        from . import skin
        k = 1.0 + 0.04 * grow
        pic = pygame.Rect(0, 0, int(r.w * k), int(r.h * k))
        pic.center = r.center
        if skin.has("sign_board"):                     # 3.18: свой указатель ui/sign_board (стрелка влево)
            if hover:
                blit_light(s, r.centerx + 8, r.centery, r.w * 1.7, (255, 232, 140), 150)
            skin.plate(s, "sign_board", pic)
        else:
            if hover:
                blit_light(s, r.centerx + 8, r.centery, r.w * 1.7, (255, 232, 140), 150)
                halo = [(cx + (x - cx) * 1.08, cy + (y - cy) * 1.14) for x, y in arrow]
                poly(s, (255, 236, 160), halo, 0)
            poly(s, (190, 132, 78) if hover else (176, 120, 70), arrow, 3)
        draw_text(s, "Доска", 18, (r.x + 82, r.centery - 11))
        draw_text(s, "заданий", 16, (r.x + 82, r.centery + 10))
        self.zone_btn(r, self.open_board, 12, glow="sprite")
        if self.tavern.claimable():
            pygame.draw.circle(s, OUT, (r.right - 4, r.y + 24), 12)
            pygame.draw.circle(s, (240, 70, 70), (r.right - 4, r.y + 24), 10)
            draw_text(s, "!", 15, (r.right - 4, r.y + 24))
        # вывеска казино
        c, door = L["casino_sign"], L["casino_door"]
        if skin.plate(s, "sign_casino", pygame.Rect(c).inflate(10, 8)):   # 3.18: своя вывеска ui/sign_casino
            draw_text(s, "Казино", 17, (c.centerx - 6, c.centery))
        else:
            rounded(s, (176, 120, 70), c, 6, 3)
            draw_text(s, "Казино  >", 17, c.center)
        if self.tavern.casino_open or DEV:
            draw_text(s, "открыто", 13, (door.centerx, door.y + 70), (190, 255, 170))
        else:
            draw_text(s, f"от {CASINO_UNLOCK_TOKENS}", 13, (door.centerx, door.y + 62), (255, 230, 160))
            draw_token(s, door.centerx, door.y + 86, 0.6)
        self.zone_btn(door.union(c), self.poke_casino, 10)
        # разговоры
        if self.tv_talk and self.tv_talk[0] < len(L["talkers"]):
            n, text, _ = self.tv_talk
            tx, ty = L["talkers"][n]
            draw_bubble(s, tx, ty, text, 13, 140)
        if self.tv_bubble:
            x, y, text, _ = self.tv_bubble
            draw_bubble(s, x, y, text)
        for x, y, text, life, color in self.floaters:
            draw_text(s, text, 18, (x, y), color)
        if self.tavern_debug:
            self.draw_tavern_debug()

    def draw_tavern_debug(self):
        """Разметка зала поверх картинки (режим разработчика): что закрывает персонажей, где они стоят."""
        s, L = self.screen, self.tl
        for pts in L["occluders"]:
            pygame.draw.polygon(s, (255, 40, 40), [(int(x), int(y)) for x, y in pts], 2)
        for key, col in (("barman_zone", (60, 160, 255)), ("bard_zone", (60, 160, 255)), ("board_sign", (60, 220, 90)),
                         ("casino_door", (60, 220, 90)), ("casino_sign", (60, 220, 90))):
            pygame.draw.rect(s, col, L[key], 2)
        for tx, ty in L["talkers"]:
            pygame.draw.circle(s, (255, 230, 0), (int(tx), int(ty)), 5)
        for key in ("barman", "bard"):
            p = L[key]
            y = p["waist"] if key == "barman" else p["y"]
            pygame.draw.line(s, (255, 0, 255), (p["x"] - 12, int(y)), (p["x"] + 12, int(y)), 2)
        fx = L["fx"]
        if fx.get("fire"):
            pygame.draw.circle(s, (255, 140, 0), [int(v) for v in fx["fire"]], 7, 2)
        for pt in fx.get("candles") or []:
            pygame.draw.circle(s, (255, 200, 0), [int(v) for v in pt], 5, 2)
        for pt in fx.get("steam") or []:
            pygame.draw.circle(s, WHITE, [int(v) for v in pt], 5, 2)
        if fx.get("barman_mug"):
            pygame.draw.circle(s, (120, 255, 255), [int(v) for v in fx["barman_mug"]], 5, 2)
        if fx.get("motes"):
            x0, y0, x1, y1 = fx["motes"]
            pygame.draw.rect(s, (255, 246, 215), (x0, y0, x1 - x0, y1 - y0), 1)
        # метроном: кружок вспыхивает на каждой доле — сверь с музыкой и поправь bpm/offset в tavern.json
        m, beat = L["music"], self.tv_beat()
        flash = max(0.0, 1.0 - (beat % 1.0) * 4)
        pygame.draw.circle(s, OUT, (W // 2, 26), 16)
        pygame.draw.circle(s, (255, int(120 + 120 * flash), 60) if flash > 0 else (90, 70, 60), (W // 2, 26), 13)
        draw_text(s, f"{m['bpm']:g} BPM, сдвиг {m.get('offset', 0):g} с, доля {int(beat) % 100}", 13, (W // 2, 54),
                  (255, 230, 120))
        draw_text_fit(s, "красное — перед персонажами, жёлтое — облачка, малиновое — пояс бармена / ноги барда; "
                         "оранжевое — огонь, свечи, белое — пар", 12, (W // 2 + 40, 628), W - 140, (255, 230, 120))












