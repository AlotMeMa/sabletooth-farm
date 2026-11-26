# -*- coding: utf-8 -*-
"""Существа на поле: белка, ворона, разбойник, мороз и лёд.

Примесь к App (3.15: вынесено из app.py без изменений). Общие импорты и константы — ui_common.
"""
from .ui_common import *  # noqa: F401,F403


class CreaturesUI:
    BANDIT_STEP = {"walk": 0.5, "escape": 0.3, "flee": 0.26}   # длина шага, с

    # ------------------------------------------------------------ белка
    def squirrel_delay(self):
        return random.uniform(SQUIRREL_MIN, SQUIRREL_MAX) * 0.9 ** self.farm.up("sq_often") / self.farm.song_effect("squirrel")

    def crow_delay(self):
        return random.uniform(CROW_MIN, CROW_MAX) * 1.5 ** self.farm.up("scarecrow")

    # 3.39: что пишет игра про зверька и вредителя — по-своему в каждой главе (краб и чайка в Рыбацкой деревне)
    CRITTER_TEXTS = {
        "squirrel": dict(in_="Шур-шур... на лугу белка! Лови!", golden_in="Ого! ЗОЛОТАЯ белка! Лови скорее!",
                         out="Белка убежала...", golden_out="Золотая белка убежала... эх!",
                         caught="Поймал белку! +$", golden_caught="ЗОЛОТАЯ белка поймана! x{m}: +$"),
        "crab": dict(in_="Щёлк-щёлк... по берегу бежит краб! Лови!", golden_in="Ого! ЗОЛОТОЙ краб! Лови скорее!",
                     out="Краб удрал в воду...", golden_out="Золотой краб удрал в воду... эх!",
                     caught="Поймал краба! +$", golden_caught="ЗОЛОТОЙ краб пойман! x{m}: +$"),
        "crow": dict(pest="Кар! Ворона села на грядку «{name}» — она не растёт. Прогони!", shoo="Кыш!"),
        "gull": dict(pest="Кья-кья! Чайка уселась на пруд «{name}» — улов стоит. Прогони!", shoo="Кыш!"),
    }

    def critter_text(self, what):
        kind = THEME.get("pest", "crow") if what in ("pest", "shoo") else THEME.get("critter", "squirrel")
        texts = self.CRITTER_TEXTS.get(kind) or self.CRITTER_TEXTS["crow" if what in ("pest", "shoo") else "squirrel"]
        return texts["in_" if what == "in" else what]

    def spawn_squirrel(self, golden=None):
        d = random.choice((1, -1))
        if golden is None:
            golden = random.random() < (GOLDEN_CHANCE + 0.04 * self.farm.up("golden")) * self.farm.song_effect("golden")
        self.squirrel = dict(x=-60.0 if d == 1 else W + 60.0, y=random.uniform(478, 506), d=d, golden=golden,
                             phase="run", timer=0.0, stop=random.uniform(260, 740), vy=0.0, life=0.0, hop_i=0)
        self.sfx.play("squirrel")
        self.toast(self.critter_text("golden_in" if golden else "in"), 3 if golden else 2.5)

    def update_squirrel(self, dt):
        if self.squirrel is None:
            self.squirrel_timer -= dt
            if self.squirrel_timer <= 0:
                self.spawn_squirrel()
            return
        q = self.squirrel
        q["timer"] += dt
        q["life"] += dt
        golden = q["golden"]
        if golden and q["phase"] != "caught" and random.random() < 6 * dt:      # золотая белка поблёскивает
            self.fx.twinkle(q["x"] + random.uniform(-26, 26), q["y"] - random.uniform(12, 52) - self.squirrel_pose(q)[0],
                            r=random.uniform(3, 5.5))
        if q["phase"] == "caught":
            q["vy"] += 900 * dt
            q["y"] += q["vy"] * dt
            if q["timer"] > 0.9:
                self.end_squirrel()
        elif q["phase"] == "sit":
            if q["timer"] >= (GOLDEN_SIT if golden else SQUIRREL_SIT) + self.farm.up("sq_sit"):
                q["phase"], q["timer"], q["hop_i"] = "flee", 0.0, 0
        else:
            speed = SQUIRREL_SPEED * (1.4 if q["phase"] == "flee" else 1.0) * (GOLDEN_SPEED if golden else 1.0)
            q["x"] += q["d"] * speed * dt
            period = SQUIRREL_HOP[q["phase"]][0] / (GOLDEN_SPEED if golden else 1.0)
            i = int(q["timer"] / period)
            if i != q["hop_i"]:                                   # приземлилась — пыль из-под лап
                q["hop_i"] = i
                self.fx.dust(q["x"] - q["d"] * 8, q["y"], n=2, size=(3, 6), drift=-q["d"] * 25, alpha=130)
            if q["phase"] == "run" and (q["x"] - q["stop"]) * q["d"] >= 0:
                q["phase"], q["timer"] = "sit", 0.0
                self.fx.dust(q["x"], q["y"], n=3, size=(3, 6), alpha=120)
            if q["x"] < -80 or q["x"] > W + 80:
                self.end_squirrel()
                self.toast(self.critter_text("golden_out" if golden else "out"), 1.5)

    def end_squirrel(self):
        self.squirrel = None
        self.squirrel_timer = self.squirrel_delay()

    def catch_squirrel(self):
        q = self.squirrel
        if not q or q["phase"] == "caught":
            return
        amt = self.farm.catch_squirrel(GOLDEN_MULT if q["golden"] else 1)
        self.sfx.play("coin_big")
        hop = self.squirrel_pose(q)[0]
        q["y"] -= hop                                   # кувырок начинается оттуда, где её поймали (хоть и в прыжке)
        q["phase"], q["timer"], q["vy"] = "caught", 0.0, -420.0
        self.floater(q["x"], q["y"] - 70, "+$" + fmt(amt))
        gold = ((255, 225, 110), (255, 250, 210), (255, 190, 70))
        self.fx.sparks(q["x"], q["y"] - 28, n=12 if q["golden"] else 7, colors=gold, speed=(50, 130), life=(0.35, 0.6),
                       size=(2, 4), gravity=120, up=70)
        self.fx.ring(q["x"], q["y"], r0=8, r1=46, life=0.45, color=(255, 235, 150), width=3)
        self.coins_to_counter(q["x"], q["y"] - 30, amt, 9 if q["golden"] else 5)
        self.quest("squirrel")
        if q["golden"]:
            self.quest("golden")
            self.toast(self.critter_text("golden_caught").format(m=GOLDEN_MULT) + fmt(amt), 4)
        else:
            self.toast(self.critter_text("caught") + fmt(amt), 3)

    def squirrel_pose(self, q):
        """Как выглядит белка сейчас -> (подскок, sx, sy, наклон°, прозрачность, точка опоры).
        Бежит дугами: на земле сжимается перед прыжком, в воздухе вытягивается и клюёт носом к приземлению.
        Сидит — дышит и грызёт орешек. Поймали — кувыркается и тает."""
        d, t, ph = q["d"], q["timer"], q["phase"]
        if ph in ("run", "flee"):
            period, height = SQUIRREL_HOP[ph]
            period /= GOLDEN_SPEED if q["golden"] else 1.0
            u = (t / period) % 1.0
            if u < 0.16:                                   # лапы на земле: сжалась, толкается
                c = math.sin(math.pi * u / 0.16)
                return 0.0, 1 + 0.12 * c, 1 - 0.14 * c, 0.0, None, "midbottom"
            v = (u - 0.16) / 0.84                          # в воздухе
            s = math.sin(math.pi * v)
            return 4 * height * v * (1 - v), 1 - 0.04 * s, 1 + 0.07 * s, d * 9 * (1 - 2 * v), None, "midbottom"
        if ph == "sit":
            land = max(0.0, 1 - t / 0.16)                  # только что приземлилась
            breath = 0.022 * math.sin(t * 6)
            nibble = 3.0 * math.sin(t * 13) if (t % 1.4) < 0.5 else 0.0
            return 0.0, 1 + 0.1 * land, 1 - 0.12 * land + breath, nibble, None, "midbottom"
        k = min(1.0, t / 0.7)                              # поймали: кувырок через спину
        spin = d * 360 * anim.ease_out_cubic(k)
        fade = 255 * (1 - max(0.0, (t - 0.5) / 0.4))
        grow = 1 + 0.15 * math.sin(math.pi * min(1.0, t / 0.9))
        return 0.0, grow, grow, spin, max(0, fade), "center"

    def draw_squirrel_layer(self):
        q = self.squirrel
        if q is None:
            return
        hop, sx, sy, ang, alpha, pivot = self.squirrel_pose(q)
        if q["phase"] != "caught":                         # тень на траве: в прыжке меньше и бледнее
            lift = min(1.0, hop / 45)
            draw_shadow(self.screen, q["x"], q["y"] + 1, 46 * (1 - 0.35 * lift), 10 * (1 - 0.3 * lift), 70 * (1 - 0.5 * lift))
        if pivot == "center":
            draw_squirrel(self.screen, q["x"], q["y"] - 28, q["d"], 0, q["golden"], q["life"], sx, sy, ang, alpha, "center")
        else:
            draw_squirrel(self.screen, q["x"], q["y"], q["d"], hop, q["golden"], q["life"], sx, sy, ang)
        if q["phase"] != "caught" and self.modal is None:
            self.zone((P(q["x"] - 38), P(q["y"] - 66 - hop), 76, 70 + hop), self.catch_squirrel)

    # ------------------------------------------------------------ ворона
    def spawn_crow(self):
        f = self.farm
        if not self.farm_info()["crow"]:
            self.crow_timer = self.crow_delay()
            return
        free = [k for k in range(N_CROPS) if f.levels[k] > 0]
        if not free:
            self.crow_timer = self.crow_delay()
            return
        k = random.choice(free)
        cx, cy = crop_center(k)
        d = random.choice((1, -1))
        sx = W + 60 if d == -1 else -60
        self.crow = dict(k=k, x=float(sx), y=-40.0, sx=float(sx), sy=-40.0, tx=cx + 26 * -d, ty=cy - 34,
                         phase="fly_in", timer=0.0, d=d)

    def update_crow(self, dt):
        if self.crow is None:
            self.crow_timer -= dt
            if self.crow_timer <= 0:
                self.spawn_crow()
            return
        c = self.crow
        c["timer"] += dt
        if c["phase"] == "fly_in":
            u = min(1.0, c["timer"] / 2.2)
            e = 1 - (1 - u) ** 2
            c["x"] = c["sx"] + (c["tx"] - c["sx"]) * e
            c["y"] = c["sy"] + (c["ty"] - c["sy"]) * e - math.sin(u * math.pi) * 60
            if u >= 1:
                c["phase"], c["timer"] = "sit", 0.0
                self.fx.dust(c["x"], c["y"], n=3, color=DIRT, size=(3, 6), spread=12, alpha=140)
                self.farm.blocked[c["k"]] = True
                self.sfx.play("crow")
                self.toast(self.critter_text("pest").format(name=CROPS[c['k']]['name']), 4)
        elif c["phase"] == "away":
            c["x"] -= c["d"] * 380 * dt
            c["y"] -= 260 * dt
            if c["y"] < -60:
                self.end_crow()

    def shoo_crow(self):
        c = self.crow
        if not c or c["phase"] != "sit":
            return
        self.farm.blocked[c["k"]] = False
        self.sfx.play("shoo")
        self.quest("crow")
        self.fx.feathers(c["x"], c["y"] - 26, n=6)            # перья летят и медленно кружат вниз
        self.fx.dust(c["x"], c["y"], n=3, color=DIRT, size=(3, 6), spread=12, alpha=140)
        c["phase"], c["timer"] = "away", 0.0
        c["d"] = -c["d"]
        self.floater(c["x"], c["y"] - 40, self.critter_text("shoo"), (230, 240, 255))

    def end_crow(self):
        if self.crow:
            self.farm.blocked[self.crow["k"]] = False
        self.crow = None
        self.crow_timer = self.crow_delay()

    def crow_pose(self, c):
        """Как выглядит ворона -> (смотрит, подскок, крылья вверх, sx, sy, наклон°, каркает).
        Летит — машет крыльями (картинки crow_fly и crow по очереди), перед посадкой планирует.
        Сидит — цикл 3 с: клюёт грядку, каркает (откидывается назад), оглядывается."""
        t, d = c["timer"], c["d"]
        if c["phase"] == "fly_in":
            u = min(1.0, t / 2.2)
            if u > 0.82:                                   # планирует, крылья раскрыты, задрала нос
                return d, 0.0, True, 1.0, 1.0, d * 8, False
            ph = (t * 4.5) % 1.0
            return d, -3 * math.sin(2 * math.pi * ph), ph < 0.5, 1.0, 1.0, -d * 5, False
        if c["phase"] == "away":
            ph = (t * 7) % 1.0
            return -d, -3 * math.sin(2 * math.pi * ph), ph < 0.5, 1.0, 1.0, -d * 14, False
        land = max(0.0, 1 - t / 0.18)
        sx, sy = 1 + 0.1 * land, 1 - 0.12 * land + 0.015 * math.sin(t * 5)
        cyc = t % 3.0
        if cyc < 1.6:                                      # клюёт: наклоняется вперёд короткими ударами
            peck = max(0.0, math.sin(cyc * 7.5)) ** 2
            return d, 0.0, False, sx, sy - 0.03 * peck, -d * 22 * peck, False
        if cyc < 2.3:                                      # «Кар!»: откидывается назад и вытягивается
            k = math.sin(math.pi * (cyc - 1.6) / 0.7)
            return d, 0.0, False, sx - 0.03 * k, sy + 0.06 * k, d * 8 * k, True
        hop = 4 * max(0.0, math.sin(math.pi * (cyc - 2.3) / 0.25)) if cyc < 2.55 else 0.0
        return -d, hop, False, sx, sy, 0.0, False          # подпрыгнула и оглядывается

    def draw_crow_layer(self):
        c = self.crow
        if c is None:
            return
        face, hop, wings, sx, sy, ang, caw = self.crow_pose(c)
        if c["phase"] == "sit":
            draw_shadow(self.screen, c["x"], c["y"] + 1, 40, 9, 70)
            draw_crow(self.screen, c["x"], c["y"] - hop, face, c["timer"], False, 0.0, sx=sx, sy=sy, angle=ang)
            if caw:
                draw_text(self.screen, "Кар!", 16, (c["x"] + 14 * c["d"], c["y"] - 68), WHITE)
            if self.modal is None:
                self.zone((P(c["x"] - 44), P(c["y"] - 64), 88, 70), self.shoo_crow)
        else:
            draw_crow(self.screen, c["x"], c["y"] + hop, face, c["timer"], True, wings_up=wings, sx=sx, sy=sy, angle=ang)

    # ------------------------------------------------------------ мороз
    def update_frost(self, dt):
        if not self.farm_info()["frost"]:
            return
        self.frost_timer -= dt
        if self.frost_timer > 0:
            return
        f = self.farm
        self.frost_timer = random.uniform(FROST_MIN, FROST_MAX) * 1.5 ** f.up("warmbeds")   # 3.29: «Тёплые грядки»
        free = [k for k in range(N_CROPS) if f.levels[k] > 0 and f.frozen[k] == 0 and not f.blocked[k]]
        if not free:
            return
        hit = random.sample(free, min(len(free), random.choice((1, 1, 2))))
        for k in hit:
            f.frozen[k] = max(1, FROST_HITS - f.up("icepick"))                             # 3.29: «Ледоруб»
        names = ", ".join(CROPS[k]["name"] for k in hit)
        self.toast(f"Мороз! Замёрзло: {names}. Разбей лёд кликами!", 4)

    def hit_ice(self, k):
        f = self.farm
        if f.frozen[k] <= 0:
            return
        f.frozen[k] -= 1
        cx, cy = crop_center(k)
        if f.frozen[k] == 0:
            self.floater(cx, cy - 60, "Лёд разбит!", (200, 235, 255))
        else:
            self.floater(cx + random.uniform(-20, 20), cy - 50, "Тресь!", (220, 240, 255))

    def draw_ice(self, k):
        f = self.farm
        hits = f.frozen[k]
        if hits <= 0:
            return
        cx, cy = crop_center(k)
        hw, hh, up = TW / 2 * 0.86, TH / 2 * 0.86, 46
        ice = hd.Surface((P(hw * 2 + 8), P(hh * 2 + up + 8)), pygame.SRCALPHA)
        ox, oy = hw + 4, hh + up + 4      # центр клетки внутри поверхности
        def L(x, y):
            return (P(ox + x), P(oy + y))
        body = [L(-hw, 0), L(-hw, -up), L(0, -hh - up), L(hw, -up), L(hw, 0), L(0, hh)]
        pygame.draw.polygon(ice, (190, 230, 255, 150), body)
        pygame.draw.polygon(ice, (225, 245, 255, 190), [L(-hw, -up), L(0, -hh - up), L(hw, -up), L(0, hh - up)])
        pygame.draw.polygon(ice, (255, 255, 255, 235), body, 3)
        pygame.draw.line(ice, (255, 255, 255, 235), L(-hw, -up), L(0, hh - up), 2)
        pygame.draw.line(ice, (255, 255, 255, 235), L(hw, -up), L(0, hh - up), 2)
        pygame.draw.line(ice, (255, 255, 255, 235), L(0, hh - up), L(0, hh), 2)
        pygame.draw.line(ice, (255, 255, 255, 200), L(-hw * 0.6, -up * 0.8), L(-hw * 0.3, -up * 0.2), 3)
        cracks = FROST_HITS - hits
        crack_lines = [[L(-20, -40), L(-5, -25), L(-15, -8), L(2, 5)], [L(25, -50), L(12, -30), L(28, -16)],
                       [L(-40, -10), L(-25, -18), L(-30, -32)]]
        for c in crack_lines[:cracks]:
            pygame.draw.lines(ice, (70, 120, 170, 230), False, c, 2)
        self.screen.blit(ice, (P(cx - ox), P(cy - oy)))
        draw_text(self.screen, f"x{hits}", 14, (cx + hw - 14, cy - up - 4), (220, 240, 255))
        if self.modal is None and self.mode == "normal":
            self.zone((P(cx - 60), P(cy - 70), 120, 100), lambda k=k: self.hit_ice(k))

    # ------------------------------------------------------------ разбойники
    def bandit_delay(self):
        return random.uniform(BANDIT_MIN, BANDIT_MAX) * 1.5 ** self.farm.up("guards")

    def spawn_bandit(self):
        f = self.farm
        if not self.farm_info()["bandits"]:
            self.bandit_timer = self.bandit_delay()
            return
        plots = [k for k in range(N_CROPS) if f.levels[k] > 0]
        if not plots:
            self.bandit_timer = self.bandit_delay()
            return
        plots.sort(key=lambda k: f.stash[k], reverse=True)
        k = random.choice(plots[:3])
        cx, cy = crop_center(k)
        d = 1 if cx < W / 2 else -1
        sx = -50.0 if d == 1 else W + 50.0
        self.bandit = dict(k=k, x=sx, y=random.uniform(470, 500), tx=cx - 40 * d, ty=cy + 18, d=d,
                           phase="walk", timer=0.0, sack=0.0, step_i=0, coin_t=0.0)
        self.toast(f"Разбойник крадётся к грядке «{CROPS[k]['name']}»! Прогони его!", 3.5)
        self.sfx.play("bandit")

    def update_bandit(self, dt):
        if self.bandit is None:
            if not self.farm_info()["bandits"]:
                return
            self.bandit_timer -= dt
            if self.bandit_timer <= 0:
                self.spawn_bandit()
            return
        b, f = self.bandit, self.farm
        b["timer"] += dt
        b.setdefault("step_i", 0)
        b.setdefault("coin_t", 0.0)
        period = self.BANDIT_STEP.get(b["phase"])
        if period:                                            # шаг — облачко пыли из-под ног
            i = int(b["timer"] / period)
            if i != b["step_i"]:
                b["step_i"] = i
                self.fx.dust(b["x"] - b["d"] * 6, b["y"], n=1 if b["phase"] == "walk" else 2, size=(3, 6),
                             drift=-b["d"] * 20, alpha=110)
        coin = lambda surf, x, y, sc: draw_coin(surf, x, y, 11 * sc)
        if b["phase"] == "steal" and f.stash[b["k"]] > 0:     # монетки с грядки летят в мешок
            b["coin_t"] += dt
            if b["coin_t"] >= 0.45:
                b["coin_t"] = 0.0
                cx, cy = crop_center(b["k"])
                self.fx.fly((cx + random.uniform(-25, 25), cy - 10), (b["x"] - b["d"] * 12, b["y"] - 38), coin,
                            dur=0.45, lift=45, spread=12, size=COIN_SMALL, shrink=0.75)
        elif b["phase"] == "escape" and b["sack"] > 0:        # убегает — монетки сыплются из мешка
            b["coin_t"] += dt
            if b["coin_t"] >= 0.5:
                b["coin_t"] = 0.0
                self.fx.drop(b["x"] - b["d"] * 16, b["y"] - 30, coin, ground=b["y"] + random.uniform(-2, 4),
                             vx=-b["d"] * random.uniform(20, 60), vy=-random.uniform(120, 180), life=1.1, size=COIN_SMALL)
        if b["phase"] == "walk":
            dx, dy = b["tx"] - b["x"], b["ty"] - b["y"]
            dist = math.hypot(dx, dy)
            step = 170 * dt
            if dist <= step:
                b["x"], b["y"] = b["tx"], b["ty"]
                b["phase"], b["timer"] = "steal", 0.0
            else:
                b["x"] += dx / dist * step
                b["y"] += dy / dist * step
        elif b["phase"] == "steal":
            k = b["k"]
            take = min(f.stash[k], f.stash[k] * BANDIT_STEAL * 0.7 ** f.up("traps") * dt)
            f.stash[k] -= take
            b["sack"] += take
            if b["timer"] >= BANDIT_TIME:
                b["phase"], b["timer"] = "escape", 0.0
                if b["sack"] > 0:
                    self.toast(f"Разбойник унёс ${fmt(b['sack'])}!", 3)
        else:   # escape / flee — бежит к краю экрана
            speed = 330 if b["phase"] == "flee" else 220
            ex = -80 if b["x"] < W / 2 else W + 80
            b["d"] = -1 if ex < 0 else 1
            b["x"] += b["d"] * speed * dt
            b["y"] += (500 - b["y"]) * min(1.0, dt * 2)
            if b["x"] < -70 or b["x"] > W + 70:
                self.bandit = None
                self.bandit_timer = self.bandit_delay()

    def shoo_bandit(self):
        b = self.bandit
        if not b or b["phase"] not in ("walk", "steal"):
            return
        self.sfx.play("shoo")
        self.quest("bandit")
        self.fx.dust(b["x"], b["y"], n=4, size=(4, 8), spread=14, alpha=140)
        if b["sack"] > 0:                                     # монетки летят из мешка обратно на грядку
            cx, cy = crop_center(b["k"])
            coin = lambda surf, x, y, sc: draw_coin(surf, x, y, 11 * sc)
            for i in range(6):
                self.fx.fly((b["x"] - b["d"] * 12, b["y"] - 38), (cx + random.uniform(-20, 20), cy - 8), coin,
                            dur=0.5, delay=i * 0.05, lift=55, spread=18, size=COIN_SMALL, shrink=1.0)
            self.farm.stash[b["k"]] += b["sack"]
            self.floater(b["x"], b["y"] - 70, "Вернул $" + fmt(b["sack"]), (200, 240, 160))
        else:
            self.floater(b["x"], b["y"] - 70, "Пошёл вон!", (230, 240, 255))
        b["sack"] = 0.0
        b["phase"], b["timer"] = "flee", 0.0

    def bandit_pose(self, b, d):
        """Разбойник -> (подскок, sx, sy, наклон°). Крадётся пригнувшись на цыпочках; у грядки присел и шарит;
        с добычей бежит вприпрыжку (мешок раскачивает его из стороны в сторону); прогнали — удирает."""
        t, ph = b["timer"], b["phase"]
        if ph == "steal":
            return 0.0, 1.0, 0.93 + 0.02 * math.sin(t * 12), -d * 9 + 3 * math.sin(t * 9)
        period = self.BANDIT_STEP.get(ph, 0.3)
        u = (t / period) % 1.0
        s = math.sin(math.pi * u)
        if ph == "walk":
            return 3 * s, 1.0, 0.94 + 0.03 * s, -d * 8 + 2 * math.sin(2 * math.pi * u)
        lean = 12 if ph == "flee" else 6
        rock = 5 * math.sin(2 * math.pi * u) if b["sack"] > 0 else 2 * math.sin(2 * math.pi * u)
        land = max(0.0, 1 - u / 0.15)
        return (6 if ph == "flee" else 5) * s, 1 + 0.06 * land, 1 - 0.07 * land, -d * lean + rock

    def draw_bandit_layer(self):
        b = self.bandit
        if b is None:
            return
        running = b["phase"] != "steal"
        d = b["d"] if b["phase"] != "steal" else (1 if crop_center(b["k"])[0] > b["x"] else -1)
        pose = self.bandit_pose(b, d)
        draw_shadow(self.screen, b["x"], b["y"] + 1, 50 * (1 - pose[0] / 30), 11, 70)
        draw_bandit(self.screen, b["x"], b["y"], d, b["timer"], b["sack"], running, pose)
        if b["phase"] == "steal":
            left = max(0.0, BANDIT_TIME - b["timer"])
            draw_bar(self.screen, (P(b["x"] - 22), P(b["y"] - 76), 44, 8), left / BANDIT_TIME, (230, 90, 80))
        if b["phase"] in ("walk", "steal") and self.modal is None:
            self.zone((P(b["x"] - 30), P(b["y"] - 70), 60, 74), self.shoo_bandit)
