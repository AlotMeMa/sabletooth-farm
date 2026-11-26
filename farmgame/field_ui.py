# -*- coding: utf-8 -*-
"""Поле: грядки, сбор и покупки, солнце, дождь, праздник, грузовик, режим прокачки.

Примесь к App (3.15: вынесено из app.py без изменений). Общие импорты и константы — ui_common.
"""
from .ui_common import *  # noqa: F401,F403
from .config import _rain_time


class FieldUI:
    # ------------------------------------------------------------ монетки и плашка денег
    MONEY_ICON = (34, 32)             # где на экране монетка плашки денег
    FESTIVAL_RECT = (875, 116, 60, 60)    # кнопка праздника — на траве справа от замка
    SHAMAN_RECT = (825, 82, 60, 60)       # 3.26: кнопка «Гномье пришествие» — там, где летом тучка

    def truck_tier(self):
        p = self.farm.potential_leaves()
        tier = 0
        for k, (_, _, need) in enumerate(TRUCK_TIERS):
            if p >= need:
                tier = k
        return tier

    def coin_pos(self, k):
        cx, cy = crop_center(k)
        if THEME.get("pond"):                 # 3.39.3: в пруду монетка сбоку, у правого края — рыбу не закрывает
            return cx + 30, cy - 26 + math.sin(self.t * 4 + k) * 3
        return cx, cy - 6 + math.sin(self.t * 4 + k) * 3

    def hit_tile(self, pos):
        dx = (pos[0] - OX) / (TW / 2)
        dy = (pos[1] + 18 - grid_oy()) / (TH / 2)
        fi, fj = (dx + dy) / 2, (dy - dx) / 2
        i, j = math.floor(fi + 0.5), math.floor(fj + 0.5)
        if (i, j) in SLOT:
            return SLOT.index((i, j))
        return None

    # ------------------------------------------------------------ actions
    def do_buy(self, k, n=None):
        f = self.farm
        if n is None:
            n = f.buy_amount(k, self.buy_mode)
        before = f.speed_steps(k)
        was_locked = f.levels[k] == 0
        if f.buy(k, n):
            self.quest("buy_levels", n)
            self.tut_event("plant" if was_locked else "buy_level")
            if f.speed_steps(k) > before:
                self.quest("milestone", f.speed_steps(k) - before)
            cx, cy = crop_center(k)
            self.floater(cx, cy - 70, f"+{n} ур.", (140, 240, 120))
            self.buy_effect(k, "plant" if was_locked else "milestone" if f.speed_steps(k) > before else "level")
            if was_locked:
                self.toast(f"Посажено: {CROPS[k]['name']}!")
                self.sfx.play("buy")
            elif f.speed_steps(k) > before:
                self.toast(f"{CROPS[k]['name']}: веха {prev_milestone(f.levels[k])}! Растёт быстрее x2")
                self.sfx.play("levelup")
            else:
                self.sfx.play("buy")
        else:
            self.toast(f"Не хватает денег: нужно ${fmt(f.cost(k, n))} за +{n} ур., у тебя ${fmt(f.money)}", 2.5)

    def buy_effect(self, k, kind):
        """Искорки над грядкой: посадка — зелёные листочки, уровень — немного искр, веха — золотое кольцо."""
        cx, cy = crop_center(k)
        fx = self.fx
        if kind == "plant":
            fx.sparks(cx, cy - 4, n=10, colors=((120, 200, 90), (170, 225, 110), (150, 110, 70)), speed=(30, 90),
                      life=(0.35, 0.6), size=(2, 4), gravity=160, up=60)
            fx.ring(cx, cy + 4, r0=10, r1=70, life=0.5, color=(160, 120, 80), width=3)
        elif kind == "milestone":
            fx.ring(cx, cy + 4, r0=12, r1=92, life=0.7, color=(255, 220, 100), width=4)
            fx.sparks(cx, cy - 20, n=14, colors=((255, 225, 110), (255, 250, 210), (255, 190, 70)), speed=(40, 120),
                      life=(0.5, 0.85), size=(2, 4), gravity=70, up=90)
        else:
            fx.sparks(cx, cy - 20, n=5, colors=((190, 240, 140), (255, 240, 160)), speed=(25, 70),
                      life=(0.3, 0.5), size=(2, 3), gravity=90, up=60)

    def try_collect(self, pos):
        f = self.farm
        for k in range(N_CROPS):
            if f.stash[k] > 0:
                x, y = self.coin_pos(k)
                if math.hypot(pos[0] - x, pos[1] - y) < 24:
                    self._collect(k)
                    return True
        k = self.hit_tile(pos)
        if k is not None and f.stash[k] > 0:
            self._collect(k)
            return True
        return False

    def _collect(self, k):
        amt = self.farm.collect(k)
        if amt:
            self.quest("collect")
            x, y = self.coin_pos(k)
            self.sfx.play("coin_big" if self.farm.last_lucky else "coin")
            if self.farm.last_lucky:
                self.floater(x, y - 10, "x10! +$" + fmt(amt), (255, 140, 220))
                self.toast(f"Гигантский урожай: {CROPS[k]['name']} x10!", 2.5)
            elif getattr(self.farm, "last_double", False):          # 3.41: «Золотой крючок»
                self.floater(x, y - 10, "x2! +$" + fmt(amt), (255, 215, 90))
            else:
                self.floater(x, y - 10, "+$" + fmt(amt))
            self.coins_to_counter(x, y, amt, 7 if self.farm.last_lucky else 3)

    def coins_to_counter(self, x, y, amt, n=3):
        """Монетки летят дугой из (x, y) в плашку денег; деньги на плашке прибавляются, когда они долетают."""
        if amt <= 0 or self.view in ("board", "fireside"):
            return
        share = amt / n
        self.money_pending += amt

        def arrive(share=share):
            self.money_pending = max(0.0, self.money_pending - share)
            self.money_bump = 1.0

        def coin(surf, cx, cy, sc):
            draw_coin(surf, cx, cy, 11 * sc)
        for i in range(n):
            self.fx.fly((x + random.uniform(-8, 8), y + random.uniform(-6, 6)), self.MONEY_ICON, coin,
                        dur=random.uniform(0.55, 0.75), delay=i * 0.06, arrive=arrive)

    def click_rain(self):
        f = self.farm
        if f.start_rain():
            self.quest("weather")
            if self.farm_info().get("rush_helpers"):
                kind = self.farm_info().get("helpers")          # 3.39.2: у каждой главы свои помощники
                extra = {"gnomes": ", шаманы пляшут", "fishermen": ", а с уловом пляшут"}.get(kind, "")
                self.toast(f"{self.farm_info()['weather']}! {self.helpers()['title']} работают на всех грядках{extra}")
            else:
                self.toast(f"{self.farm_info()['weather']}! Всё растёт быстрее")
            self.sfx.play({"Праздник урожая": "fanfare", GNOME_RUSH: "tambourine"}.get(self.farm_info()["weather"], "rain"))
        elif f.rain_left <= 0 and f.rain_cd > 0:
            self.toast(f"Ещё рано: {self.farm_info()['weather'].lower()} через {fmt_time(f.rain_cd)}", 1.5)

    def click_sun(self):
        amt = self.farm.sun_click()
        if amt:
            self.quest("sun")
            self.sfx.play("sun")
            self.floater(560, 120, "+$" + fmt(amt))
            self.toast("Солнечный бонус: +$" + fmt(amt))

    # ------------------------------------------------------------ draw
    def build_background(self):
        return build_field_background()

    def tile_corners(self, k, shrink=0.92):
        cx, cy = crop_center(k)
        hw, hh = TW / 2 * shrink, TH / 2 * shrink
        return (cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)

    def draw_soil(self, k):
        cx, cy = crop_center(k)
        draw_soil_tile(self.screen, cx, cy, self.farm.levels[k] == 0)

    def draw_plants(self, k):
        f = self.farm
        if f.levels[k] == 0:
            return
        cx, cy = crop_center(k)
        t = f.cycle_time(k)
        real_cycle = t / max(1e-6, f.growth_speed())         # сколько секунд на самом деле длится цикл
        bob = 0.0
        if f.working(k) and real_cycle < FAST_GROW_CYCLE:
            # быстрая грядка: растения всегда взрослые (иначе стадии мелькают), на каждом сборе мягко «кивают».
            # 3.26.1: и в «Гномье пришествие» на грядке без своего гнома (там тоже работает гном)
            grow = 1.0
            if real_cycle >= 1.2:
                bob = max(0.0, 1 - (f.progress[k] / t) / 0.15)
        else:
            grow = min(1.0, f.progress[k] / t)
        scale = 1.6 * (0.5 + 0.5 * grow) * (1 + 0.06 * math.sin(math.pi * bob))
        if f.stash[k] > 0:
            scale *= 1 + 0.04 * math.sin(self.t * 8)
        born = self.coin_born[k]
        if born is not None and self.t_real - born < 0.35:     # созрело: растения коротко подпрыгивают
            scale *= 1 + 0.1 * math.sin(math.pi * (self.t_real - born) / 0.35)
        tr = self.t_real
        amp = 3.4 if f.rain_left > 0 else 2.2                  # ветер: в дождь посильнее
        spots = PLANT_SPOTS
        if THEME.get("pond"):                       # 3.38.1: на участке пруда одна рыба — крупнее и без мельтешения
            key = f"crops/{FARM_ID[0]}/{CROP_KEYS[k]}"
            if has_sprite(key + "_1") or has_sprite(key):    # 3.39: картинка (с брызгами снизу) — чуть меньше, ниже
                spots, scale = [(0, 16)], scale * 0.8
            else:
                spots, scale = [(0, 2)], scale * 1.3
        for i, (ox, oy) in enumerate(spots):
            ph = k * 1.3 + i * 2.1
            sway = amp * (0.7 * math.sin(tr * 1.5 + ph) + 0.3 * math.sin(tr * 2.7 + ph * 1.9))
            draw_crop(self.screen, k, cx + ox, cy + oy, scale, grow, sway)

    def draw_front_fence(self):
        draw_front_fence_layer(self.screen)

    def draw_tile_overlay(self, k):
        s, f = self.screen, self.farm
        cx, cy = crop_center(k)
        if f.levels[k] == 0:
            if k != f.levels.index(0):
                draw_text(s, "?", 22, (cx, cy - 4), (215, 190, 160))
                return
            price = f.cost(k, 1)
            ok = f.money >= price
            plank = pygame.Rect(P(cx - 56), P(cy - 34), 112, 56)
            img = skin.stretched("sign", plank.w, plank.h)       # 3.16: своя табличка ui/sign
            if img is not None:
                s.blit(img, plank.topleft)
            else:
                rounded(s, (200, 150, 100), plank, 8, 3)
            draw_text_fit(s, CROPS[k]["name"], 14, (cx, cy - 22), 104)
            b = pygame.Rect(P(cx - 48), P(cy - 10), 96, 24)
            rounded(s, BTN_GREEN if ok else BTN_GREY, b, 8, 2)
            draw_text(s, "$" + fmt(price), 14, b.center)
            self.zone_btn(b, lambda k=k: self.do_buy(k, 1), 8)   # табличка всегда сажает 1 уровень
            return
        t = f.cycle_time(k)
        if f.stash[k] > 0:   # сколько лежит на грядке
            label = draw_text(s, "$" + fmt(f.stash[k]), 15, (cx, cy + 22), (255, 235, 120))
        else:                # сколько даст один цикл
            label = draw_text(s, "+$" + fmt(f.cycle_income(k)), 13, (cx, cy + 22))
        shift = 8 if self.farm_info()["peasants"] else 0                    # место под значок крестьянина
        bar = pygame.Rect(P(cx - BAR_W / 2 + shift), label.bottom + 1, BAR_W, 9)   # одинаковая для всех грядок
        if f.blocked[k] or f.frozen[k] > 0:     # ворона или лёд: грядка стоит
            draw_bar(s, bar, f.progress[k] / t, (150, 150, 160))
        elif f.working(k) and t <= 0.5:
            draw_bar(s, bar, 1.0, (120, 220, 90))
        else:
            draw_bar(s, bar, f.progress[k] / t, (120, 220, 90) if f.working(k) else GOLD)
        if self.farm_info()["peasants"]:   # средневековье: значок крестьянина на левом конце полоски
            # Значок «сидит» на самой полоске прогресса (как аватар), поэтому не закрывает овощи.
            ax, ay = bar.x - 2, bar.centery
            if f.farmers[k]:
                pygame.draw.circle(s, OUT, (ax, ay), 13)
                pygame.draw.circle(s, (245, 175, 50), (ax, ay), 11)                 # занят — оранжевый
                draw_helper_head(s, ax, ay + 2, 0.85)
            elif f.helper_rush():          # 3.26: на время пришествия тут работает гном из леса — фиолетовый
                pygame.draw.circle(s, OUT, (ax, ay), 13)
                pygame.draw.circle(s, (175, 130, 230), (ax, ay), 11)
                draw_helper_head(s, ax, ay + 2, 0.85)
            else:
                free = f.free_peasants() > 0
                pygame.draw.circle(s, OUT, (ax, ay), 12)
                pygame.draw.circle(s, BTN_BLUE if free else BTN_GREY, (ax, ay), 10)  # свободно — синий «+»
                pygame.draw.line(s, WHITE, (ax - 5, ay), (ax + 5, ay), 3)
                pygame.draw.line(s, WHITE, (ax, ay - 5), (ax, ay + 5), 3)
            if self.modal is None:   # кликается и значок, и сама полоска
                self.zone((ax - 14, ay - 14, bar.right - ax + 16, 28), lambda k=k: self.do_toggle_peasant(k))
        if f.stash[k] > 0:
            x, y = self.coin_pos(k)
            if self.coin_born[k] is None:                      # монетка только что появилась — выпрыгивает
                self.coin_born[k] = self.t_real
                self.fx.sparks(x, y, n=4, colors=((255, 235, 140), (255, 255, 225)), speed=(30, 70),
                               life=(0.25, 0.4), size=(2, 3), gravity=40)
            pop = anim.ease_out_back((self.t_real - self.coin_born[k]) / 0.3, 2.2)
            big = f.farmers[k] and f.stash[k] > f.cycle_income(k) * 1.5
            r = (18 if big else 15) * (0.85 if THEME.get("pond") else 1.0)
            draw_coin(s, x, y + (1 - min(1.0, pop)) * 10, r * max(0.05, pop))
        else:
            self.coin_born[k] = None

    def draw_upgrade_sign(self, k):
        s, f = self.screen, self.farm
        cx, cy = crop_center(k)
        lvl = f.levels[k]
        n = f.buy_amount(k, self.buy_mode)
        price = f.cost(k, n)
        ok = f.money >= price and n > 0
        board = pygame.Rect(P(cx - 44), P(cy - 55), 88, 68)
        pygame.draw.line(s, OUT, (P(cx), board.bottom), (P(cx), P(cy + 18)), 6)
        pygame.draw.line(s, (170, 120, 80), (P(cx), board.bottom), (P(cx), P(cy + 18)), 3)
        img = skin.stretched("sign", board.w, board.h)            # 3.16: своя табличка ui/sign
        if img is not None:
            s.blit(img, board.topleft)
        else:
            rounded(s, (235, 220, 205), board, 6, 3)
        draw_text_fit(s, CROPS[k]["name"], 12, (cx, board.y + 9), board.w - 8)
        bar = pygame.Rect(board.x + 5, board.y + 18, board.w - 10, 16)
        nm = next_milestone(lvl)
        if lvl == 0:
            draw_bar(s, bar, 0)
            draw_text(s, "не посажено", 10, bar.center)
        elif nm:
            pm = prev_milestone(lvl)
            draw_bar(s, bar, (lvl - pm) / (nm - pm), (120, 220, 90))
            draw_text(s, f"{lvl}/{nm}", 11, bar.center)
        else:
            draw_bar(s, bar, 1, (120, 220, 90))
            draw_text(s, f"{lvl} MAX", 11, bar.center)
        b = pygame.Rect(board.x + 5, board.y + 38, board.w - 10, 25)
        rounded(s, BTN_BLUE if ok else BTN_GREY, b, 6, 2)
        draw_text(s, "$" + fmt(price), 13, b.center)
        self.zone_btn(b, lambda k=k: self.do_buy(k), 6)
        # плашка "+N"
        tag = render_text(f"+{n}", 12, WHITE, OUT)
        tr = tag.get_rect(center=(P(cx), P(board.y - 9)))   # 3.17.1: выше — не закрывает название культуры
        rounded(s, (90, 70, 60), tr.inflate(10, 2), 6, 2)
        s.blit(tag, tr)

    def draw_sun(self):
        s, f = self.screen, self.farm
        x, y = 565, 72
        ready = f.sun_cd <= 0
        # мягкие лучи: бонус готов — ярче и «дышат»
        draw_sun_rays(s, x, y, self.t_real, 0.85 + 0.15 * math.sin(self.t_real * 3) if ready else 0.3)
        draw_sun_body(s, x, y, self.t)
        if ready:
            draw_text(s, "Бонус!", 14, (x, y + 52), (255, 245, 150))
            self.zone((x - 50, y - 50, 100, 115), self.click_sun)
        else:
            draw_text(s, fmt_time(f.sun_cd), 12, (x, y + 50))

    def draw_cloud(self):
        s, f = self.screen, self.farm
        x, y = 855, 108
        raining = f.rain_left > 0
        weather = self.farm_info()["weather"]
        if weather in WEATHER_BUTTON:          # праздник урожая и гномье пришествие — кнопкой
            self.draw_festival_button(WEATHER_BUTTON[weather])
            return
        draw_cloud_body(s, x, y, raining)
        if raining:
            drop = has_sprite("fx/raindrop")                     # 3.16: своя капля fx/raindrop
            for k in range(6):
                dy = (self.t * 120 + k * 17) % 50
                if drop:
                    blit_sprite(s, "fx/raindrop", x - 41 + k * 15, P(y + 38 + dy), 0.5, "center")
                else:
                    pygame.draw.line(s, (90, 160, 230), (x - 40 + k * 15, P(y + 34 + dy)), (x - 42 + k * 15, P(y + 42 + dy)), 3)
            draw_text(s, f"{self.farm_info()['weather']} x{f.growth_speed():g}  " + fmt_time(f.rain_left), 16, (x, y - 58), (180, 225, 255))
        elif f.rain_cd > 0:
            draw_text(s, fmt_time(f.rain_cd), 18, (x, y - 58))
        else:
            c = (255, 255, 255) if int(self.t * 2) % 2 else (190, 230, 255)
            draw_text(s, "Вызвать дождь!", 16, (x, y - 58), c)
            self.zone((x - 65, y - 45, 130, 90), self.click_rain)

    # ---------- 3.26: «Гномье пришествие» ----------
    RUSH_IN, RUSH_OUT = 2.2, 2.2      # сколько секунд шаманы идут на лужайку и уходят с неё

    def rush_clock(self):
        """(сколько идёт пришествие, сколько осталось) или None, если его нет."""
        f = self.farm
        if not f.helper_rush():
            return None
        total = max(f.rain_left, _rain_time(f.up("rain_len")))
        return total - f.rain_left, f.rain_left

    # ---------- 3.38.1: живой фон (окна, дым) и рыбаки из домов ----------
    RUSH_WALK = 2.6                   # сколько секунд рыбак идёт от дома до пруда

    def scene(self):
        """Точки живого фона фермы (THEME["scene"]) — только если лежит та самая картинка фона."""
        sc = THEME.get("scene")
        if not sc or sprite(sc["bg"]) is None:
            return None
        return sc

    def draw_scene_life(self):
        sc = self.scene()
        if sc is None:
            return
        s, t = self.screen, self.t_real
        for n, (x, y, size) in enumerate(sc.get("windows", ())):   # огонь в очаге: свет дрожит у каждого окна по-своему
            fl = 0.55 + 0.25 * math.sin(t * 3.1 + n * 1.7) + 0.2 * math.sin(t * 7.9 + n * 2.3) * math.sin(t * 1.3 + n)
            blit_light(s, x, y, size * (2.2 + 0.3 * fl), (255, 190, 90), 70 + 110 * fl)
            blit_light(s, x, y, size * 0.9, (255, 225, 150), 90 + 120 * fl)
        if self.view == "field" and not self.modal:
            last = getattr(self, "smoke_last", t)
            if t - last > 2.0:                       # вернулись на поле — не выпускаем весь накопленный дым разом
                last = t - 0.45
            self.smoke_last = last
            while t - self.smoke_last > 0.45:
                self.smoke_last += 0.45
                for x, y in sc.get("smoke", ()):
                    self.fx.dust(x, y, n=1, color=(214, 218, 224), size=(6, 10), spread=2, up=24, life=(2.6, 3.6),
                                 alpha=120, drift=9)

    def rush_walk(self, k, el, left, door, spot):
        """Где рыбак k на пути дом -> пруд -> дом: (x, y, идёт ли, смотрит вправо) или None (дома)."""
        delay = 0.2 + 0.22 * DRAW_ORDER.index(k)
        come = min(1.0, max(0.0, (el - delay) / self.RUSH_WALK))
        back = min(1.0, max(0.0, (self.RUSH_WALK + 0.2 - left) / self.RUSH_WALK))
        if come <= 0 or back >= 1:
            return None
        if back > 0:
            u, a, b = anim.ease_in_out(back), spot, door
        else:
            u, a, b = anim.ease_out_cubic(come), door, spot
        x, y = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
        walking = 0 < u < 1
        return x, y, walking, b[0] > a[0]

    def rush_spot(self, k):
        cx, cy = crop_center(k)
        right = k % 2 == 0
        return (cx + (64 if right else -64), cy + 14), right

    def rush_door(self, k, sc):
        spot, _r = self.rush_spot(k)
        return min(sc["doors"], key=lambda d: (d[0] - spot[0]) ** 2 + (d[1] - spot[1]) ** 2 + 400 * (k % 3))

    def draw_rush_walkers(self):
        """Рыбаки, которые сейчас идут (на месте их рисует draw_rush_worker): поверх прудов, чтобы не прятались."""
        sc = self.scene()
        clock = self.rush_clock()
        if sc is None or clock is None or not sc.get("doors"):
            return
        from .art_fishing import draw_fisher
        el, left = clock
        f = self.farm
        for k in DRAW_ORDER:
            if f.levels[k] == 0:
                continue
            spot, right = self.rush_spot(k)
            w = self.rush_walk(k, el, left, self.rush_door(k, sc), spot)
            if w is None or not w[2]:
                continue
            x, y, _walk, to_right = w
            hop = abs(math.sin((self.t_real + k) * 9)) * 3
            draw_fisher(self.screen, x, y - hop, 1.2, self.t_real + k * 0.7, flip=not to_right, n=k)

    def draw_rush_worker(self, k):
        """Гном из леса на грядке без своего гнома: выскакивает из сугроба, машет тяпкой, в конце исчезает."""
        clock = self.rush_clock()
        f = self.farm
        if clock is None or f.levels[k] == 0:           # 3.39.2: на празднике — у ВСЕХ открытых грядок, и со своим тоже
            self.rush_popped.discard(k)
            return
        el, left = clock
        delay = 0.25 + 0.18 * DRAW_ORDER.index(k)
        grow = min(1.0, max(0.0, (el - delay) / 0.35), max(0.0, left / 0.6))
        if grow <= 0.05:
            return
        cx, cy = crop_center(k)
        right = k % 2 == 0
        x, y = cx + (64 if right else -64), cy + 14
        fisher = self.farm_info().get("helpers") == "fishermen"     # 3.36: на фестивале — рыбаки с удочками
        sc = self.scene() if fisher else None
        if sc is not None and sc.get("doors"):                     # 3.38.1: пришёл из дома — без брызг
            w = self.rush_walk(k, el, left, self.rush_door(k, sc), ((x, y)))
            if w is None or w[2]:
                return                                              # дома или в пути (в пути — draw_rush_walkers)
            from .art_fishing import draw_fisher
            draw_fisher(self.screen, x, y, 1.25, self.t_real + k * 0.7, flip=right, n=k)
            return
        kind = self.farm_info().get("helpers")
        if k not in self.rush_popped:                 # выскочил — облачко снега (у рыбака — брызги, у крестьянина — пыль)
            self.rush_popped.add(k)
            dust = (200, 225, 240) if fisher else ROAD_DUST if kind == "peasants" else (245, 250, 255)
            self.fx.dust(x, y - 4, n=6, color=dust, size=(5, 9), spread=12,
                         up=20, drift=20, alpha=220, life=(0.35, 0.6))
        if fisher:
            from .art_fishing import draw_fisher
            draw_fisher(self.screen, x, y, 1.25 * (0.6 + 0.4 * grow), self.t_real + k * 0.7, flip=right, n=k)
            return
        if kind == "peasants":                        # 3.39.2: Праздник урожая — крестьяне у всех грядок
            draw_peasant_worker(self.screen, x, y, 1.25 * (0.6 + 0.4 * grow), self.t_real + k * 0.7, flip=right, n=k)
            return
        draw_gnome_worker(self.screen, x, y, 1.25 * (0.6 + 0.4 * grow), self.t_real + k * 0.7, flip=right, n=k)

    def draw_shamans(self):
        """Два гнома-шамана выходят справа на лужайку, пляшут с бубнами и уходят, когда пришествие кончается."""
        clock = self.rush_clock()
        if clock is None:
            self.rush_popped.clear()
            return
        if self.farm_info().get("helpers") == "peasants":   # 3.39.2: в средневековье плясунов нет (там конфетти)
            return
        el, left = clock
        sc = self.scene() if self.farm_info().get("helpers") == "fishermen" else None
        if sc is not None and sc.get("dance") and sc.get("doors"):   # 3.38.1: плясуны выходят из домов
            from .art_fishing import draw_fisher
            for n, spot in enumerate(sc["dance"]):
                door = min(sc["doors"], key=lambda d: (d[0] - spot[0]) ** 2 + (d[1] - spot[1]) ** 2)
                come = anim.ease_out_cubic(min(1.0, max(0.0, (el - 0.4 - 0.5 * n) / self.RUSH_WALK)))
                back = min(1.0, max(0.0, (self.RUSH_WALK + 0.2 - left) / self.RUSH_WALK))
                if come <= 0 or back >= 1:
                    continue
                a, b, u = (spot, door, back) if back > 0 else (door, spot, come)
                x, y = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
                t = self.t_real + n * 1.3
                if 0 < u < 1:
                    draw_fisher(self.screen, x, y - abs(math.sin(t * 9)) * 3, 1.5, t, flip=b[0] < a[0], n=n)
                else:
                    draw_fisher(self.screen, x, y, 1.6, t, flip=n == 1, cheer=True, n=n)
            return
        for n, (sx, sy) in enumerate(SHAMAN_SPOTS):
            come = anim.ease_out_cubic(min(1.0, max(0.0, (el - 0.3 * n) / self.RUSH_IN)))
            go = 1.0 - anim.ease_out_cubic(min(1.0, max(0.0, left / self.RUSH_OUT)))      # 0 → 1 в последние секунды
            off = (1.0 - come + go) * (W + 40 - sx)
            x, t = sx + off, self.t_real + n * 1.3
            if self.farm_info().get("helpers") == "fishermen":   # 3.36: на фестивале пляшут рыбаки с уловом
                from .art_fishing import draw_fisher
                draw_fisher(self.screen, x, sy, 1.6, t, flip=n == 1 if off <= 1.0 else go > 0, cheer=off <= 1.0, n=n)
                continue
            if off > 1.0:                                   # идёт: семенит, смотрит куда идёт
                hop = abs(math.sin(t * 9)) * 3
                draw_gnome_shaman_walk(self.screen, x, sy - hop, 1.6, t, flip=go > 0, n=n)
            else:
                draw_gnome_shaman(self.screen, x, sy, 1.6, t, flip=n == 1, n=n)
                if random.random() < 0.08:                  # искорки от бубна
                    self.fx.sparks(x + random.uniform(-18, 18), sy - 80, n=1,
                                   colors=((250, 215, 90), (215, 170, 255), (255, 255, 230)), speed=(20, 50),
                                   life=(0.4, 0.8), size=(2, 3), gravity=-20)

    def draw_festival_button(self, kind="festival"):
        """Кнопка погоды: «Праздник урожая» рядом с замком (средневековье) или «Гномье пришествие» (зима, 3.26)."""
        s, f = self.screen, self.farm
        gnomes = kind in ("shaman", "fishfest")       # 3.36: фестиваль — на месте кнопки пришествия
        fishfest = kind == "fishfest"
        rect = pygame.Rect(self.SHAMAN_RECT if gnomes else self.FESTIVAL_RECT)
        active = f.rain_left > 0
        ready = not active and f.rain_cd <= 0

        def sheaf(r):   # сноп пшеницы с красной лентой (если нет картинки ui/btn_festival)
            cx, cy = r.centerx, r.centery + 4
            for dx in (-9, -4, 0, 4, 9):
                pygame.draw.line(s, OUT, (cx + dx // 2, cy + 18), (cx + dx, cy - 12), 4)
                pygame.draw.line(s, (220, 180, 70), (cx + dx // 2, cy + 18), (cx + dx, cy - 12), 2)
                ellipse(s, (245, 205, 90), cx + dx * 1.2, cy - 16, 7, 14)
            rounded(s, (210, 60, 60), (cx - 11, cy + 2, 22, 7), 3, 2)

        def tambourine(r):   # бубен с лентами и колпак гнома (если нет картинки ui/btn_shaman)
            cx, cy = r.centerx + 3, r.centery + 4
            for n, c in enumerate(((230, 80, 70), (250, 200, 70), (90, 180, 110))):
                pygame.draw.line(s, c, (cx + 8, cy + 6), (cx + 12 + n * 4, cy + 20 - n * 2), 3)
            ellipse(s, (235, 215, 170), cx, cy, 30, 26, 2)
            pygame.draw.ellipse(s, (200, 70, 60), pygame.Rect(cx - 15, cy - 13, 30, 26), 3)
            for n in range(5):
                a = n * 2 * math.pi / 5 - 0.6
                pygame.draw.circle(s, (250, 215, 90), (P(cx + math.cos(a) * 15), P(cy + math.sin(a) * 13)), 3)
            hx, hy = r.centerx - 12, r.centery - 10
            poly(s, (110, 70, 150), [(hx - 8, hy + 4), (hx + 8, hy + 4), (hx + 2, hy - 14)], 2)
            pygame.draw.circle(s, WHITE, (hx + 2, hy - 15), 3)

        def fishbell(r):   # 3.36: рыба на верёвке с флажками (если нет картинки ui/btn_fishfest)
            from .art_fishing import draw_fish
            for n, c in enumerate(((230, 80, 70), (250, 200, 70), (90, 160, 220))):
                poly(s, c, [(r.x + 10 + n * 14, r.y + 12), (r.x + 22 + n * 14, r.y + 12), (r.x + 16 + n * 14, r.y + 22)], 1)
            draw_fish(s, r.centerx, r.centery + 20, 1.3, "salmon", 0.5)

        name = "fishfest" if fishfest else ("shaman" if gnomes else "festival")
        glow = (170, 215, 245) if fishfest else ((215, 190, 255) if gnomes else (255, 235, 150))
        if ready and not has_sprite(f"ui/btn_{name}"):
            pulse = 1 + 0.06 * math.sin(self.t * 5)
            pygame.draw.circle(s, glow, rect.center, P(40 * pulse))
        self.icon_button(rect, name, fishbell if fishfest else (tambourine if gnomes else sheaf), self.click_rain,
                         active=active or ready)
        below = rect.bottom + 14
        if active:
            word = "Фестиваль" if fishfest else ("Пришествие" if gnomes else "Праздник")
            draw_text(s, f"{word}! x{f.growth_speed():g}  " + fmt_time(f.rain_left), 15,
                      (rect.centerx, below), glow)
        elif f.rain_cd > 0:
            draw_text(s, fmt_time(f.rain_cd), 16, (rect.centerx, below))
        else:
            c = (255, 255, 255) if int(self.t * 2) % 2 else glow
            draw_text(s, "Рыбацкий фестиваль!" if fishfest else ("Призвать гномов!" if gnomes else "Праздник урожая!"),
                      15, (rect.centerx, below), c)

    def vehicle_dy(self):
        """3.39: лодка уходит не прямо влево (там берег и причал), а вниз-влево вдоль берега и за нижний край."""
        if self.farm_info()["vehicle"] != "boat" or self.truck_state != "leaving":
            return 0.0
        d = max(0.0, TRUCK_PARK_X - self.truck_x)
        return 0.35 * d + 0.002 * d * d

    def draw_vehicle(self, x, y, color, cargo=False, bob=0.0, tier=0, angle=0.0, sy=1.0):
        draw_vehicle_at(self.screen, self.farm_info()["vehicle"], tier, x, y, color, cargo, bob, angle, sy)

    def truck_pose(self):
        """Покачивание машины -> (подскок, наклон°, sy). Едет — трясётся на кочках; остановилась — клюёт носом
        и покачивается на рессорах; трогается — приседает на зад; стоит — еле заметно «дышит» мотором."""
        t, e = self.t, self.t - self.truck_t
        if self.farm_info()["vehicle"] == "boat":        # 3.38.1: лодка всегда покачивается на волнах
            k = min(1.0, self.truck_v / 150) if self.truck_state != "parked" else 0.0
            turn = 5.0 if self.truck_state == "leaving" else 0.0      # уходя вниз-влево, чуть клюёт носом
            return 2.0 * math.sin(t * 1.7) + 1.5 * k * math.sin(t * 5), 1.6 * math.sin(t * 1.2) + 1.2 * k + turn, 1.0
        cart = self.farm_info()["vehicle"] in ("cart", "sled", "fishcart")     # упряжка и повозка качаются, как телега
        if self.truck_state == "parked":
            spring = math.exp(-5 * e) * math.cos(10 * e) if e < 1.2 else 0.0
            idle = 0.004 * math.sin(t * (2.2 if cart else 3.1))
            return 0.0, 2.0 * spring, 1 - 0.03 * spring + idle
        k = min(1.0, self.truck_v / 150)
        bob = (abs(math.sin(t * 7)) * 2.5 if cart else abs(math.sin(t * 12)) * 2) * k
        ang = 0.8 * math.sin(t * (5 if cart else 8)) * k
        if self.truck_state == "leaving" and e < 1.0:
            ang -= 1.6 * math.exp(-4 * e)
        return bob, ang, 1.0

    def draw_truck_layer(self):
        if self.truck_state == "away":
            return
        s, f = self.screen, self.farm
        tier = self.leaving_tier if self.truck_state == "leaving" else self.truck_tier()
        name, color, _ = TRUCK_TIERS[tier]
        bob, ang, sy = self.truck_pose()
        shift = vehicle_shift(self.farm_info()["vehicle"], tier)
        if self.farm_info()["vehicle"] != "boat":         # 3.38.1: у лодки — вода, а не тень
            draw_shadow(s, self.truck_x - 10 - shift, TRUCK_GROUND + 3, 220 + 2 * shift, 18, 60)
        self.draw_vehicle(self.truck_x, TRUCK_GROUND + self.vehicle_dy(), color, cargo=self.truck_state == "leaving",
                          bob=bob, tier=tier, angle=ang, sy=sy)
        if self.truck_state == "parked" and self.modal is None:
            self.draw_truck_label(name, tier)

    def draw_truck_label(self, name, tier):
        """3.40.2: облачко «сколько дадут» над повозкой / упряжкой / лодкой. Ширина — по тексту, значок валюты и
        число стоят рядом и не наезжают друг на друга; облачко покачивается целиком, без масштаба (цифры не дрожат)."""
        s = self.screen
        p = self.farm.potential_leaves()
        brown, green = (90, 70, 60), (90, 200, 80)
        num, word = f"+{fmt(p)}", CUR["gen"]
        w_name = render_text(name, 13, brown, None).get_width()
        w_num = render_text(num, 17, green, OUT).get_width()
        w_word = render_text(word, 13, brown, None).get_width()
        icon_w, gap = 22, 5
        line = icon_w + gap + w_num + gap + w_word
        if line + 28 > 300:                                  # длинное название валюты — оставляем значок и число
            word, line = "", icon_w + gap + w_num
        bw, bh = max(150, w_name + 28, line + 28), 56
        lift = (0, 10, 50)[tier] if self.farm_info()["vehicle"] == "boat" else 0   # 3.38.1: над парусом
        bob = round(2 * math.sin(self.t * 3))
        cx = P(self.truck_x - 10)
        bx, by = P(cx - bw / 2), P(TRUCK_GROUND - 150 - lift - bh / 2) + bob
        rounded(s, WHITE, (bx, by, bw, bh), 14, 3)
        tail_x = P(self.truck_x - 15)
        poly(s, WHITE, [(tail_x - 10, by + bh - 2), (tail_x + 10, by + bh - 2), (tail_x - 5, by + bh + 14)], 0)
        draw_text(s, name, 13, (cx, by + 15), brown, outline=None)
        x0 = cx - line / 2
        draw_cur_icon(s, x0 + icon_w / 2, by + 37, 0.6)
        draw_text(s, num, 17, (x0 + icon_w + gap, by + 37), green, anchor="midleft")
        if word:
            draw_text(s, word, 13, (x0 + icon_w + gap + w_num + gap, by + 38), brown, anchor="midleft", outline=None)
        self.zone_btn((bx, by, bw, bh), lambda: self.open_modal("truck"), 14)
        self.zone((P(self.truck_x - 105), TRUCK_GROUND - 95, 190, 95), lambda: self.open_modal("truck"))

    def shop_has_affordable(self):
        f = self.farm
        peasants = self.farm_info()["peasants"]
        if peasants and f.peasants < PEASANT_MAX and f.money >= f.peasant_cost():
            return True
        for i in range(N_CROPS):
            if f.levels[i] == 0:
                continue
            if not peasants and not f.farmers[i] and f.money >= f.farmer_cost(i):
                return True
            if f.money >= f.fert_cost(i):
                return True
        return False

    def draw_upgrade_controls(self):
        s = self.screen
        plate = pygame.Rect(W // 2 - 150, 8, 300, 44)
        drawn = self.draw_banner(plate, "РЕЖИМ ПРОКАЧКИ", 20)      # 3.20: текст по полосе ленты
        xr = drawn.right + (4 if drawn.w > plate.w else 6)        # крестик — за концом ленты
        x = pygame.Rect(xr, plate.y + 4, 36, 36)
        rounded(s, BTN_BLUE, x, 8, 3)
        draw_text(s, "X", 18, x.center)
        self.zone_btn(x, lambda: setattr(self, "mode", "normal"), 8)
        opts = [(1, "1X"), (10, "10X"), ("next", "ВЕХА"), ("max", "MAX")]
        for idx, (val, label) in enumerate(opts):
            b = pygame.Rect(392 + idx * 80, 568, 72, 40)   # правее кнопки «Переезд»
            active = self.buy_mode == val
            rounded(s, (245, 175, 50) if active else BTN_BLUE, b, 8, 3)
            draw_text(s, label, 16, b.center)
            self.zone_btn(b, lambda v=val: setattr(self, "buy_mode", v), 8)
