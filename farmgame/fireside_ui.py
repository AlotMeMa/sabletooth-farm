# -*- coding: utf-8 -*-
"""3.19: посиделки у камина. Навёл на камин в таверне — он светится; кликнул — садишься у огня.

Огонь живой (кодом), сверху — купленные украшения (кот, котелок, коврик, цветы). Музыка таверны тихо,
гул зала громче, сверху треск поленьев. Ферма работает как обычно — это место, где можно «оставить» игру
вместо паузы. Клик по огню — подбросить полено (вспыхнет). Примесь к App.
"""
import json
import os

from .tavern_art import *  # noqa: F401,F403
from .fireside_art import (FIRESIDE_LAYOUT, FIRESIDE_CUSTOM, Fire, draw_coals, draw_logs, draw_cat, draw_kettle,
                           draw_rug, build_fireside_background)

FIRESIDE_HINTS = ["Огонь потрескивает. Ферма работает сама — можно просто посидеть",
                  "Клик по огню — подбросить полено"]
CAT_LINES = ["Мрр…", "Мрр-мрр…", "*кот приоткрыл один глаз*", "*кот потянулся и снова уснул*"]
DOG_LINES = ["Гав!", "*пёс стучит хвостом по полу*", "*Буян лизнул тебе руку*", "Вуф… *и снова уснул*"]   # 3.33


def load_fireside_layout(custom):
    lay = json.loads(json.dumps(FIRESIDE_CUSTOM if custom else FIRESIDE_LAYOUT))
    path = os.path.join(ASSET_DIR, "backgrounds", "fireside.json")
    if custom and os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                lay.update(json.load(f))
        except (OSError, ValueError) as e:
            print("backgrounds/fireside.json не прочитан:", e)
    return lay


class FiresideUI:
    def init_fireside(self):
        self.fs_bg = None
        self.fs_lay = dict(FIRESIDE_LAYOUT)
        self.fs_embers = []            # [x, y, vx, vy, life, max_life, размер]
        self.fs_ember_t = 0.0
        self.fs_steam = []             # [x, y, t, life, фаза]
        self.fs_flare = 0.0            # подбросили полено: 1 → 0
        self.fs_fire = None            # 3.21: огонь из частиц (fireside_art.Fire)
        self.fs_twitch = 0.0           # кот дёрнул ухом
        self.fs_purr = 0.0             # кот мурчит (секунд осталось)
        self.fs_since = 0.0            # сколько сидим
        self.fs_money0 = 0.0
        self.fs_occ = []               # куски фона поверх огня (поленья)

    # ---------- вход и выход ----------
    def open_fireside(self):
        if self.tavern_bg is None:
            return
        if self.fs_bg is None:
            self.fs_bg, custom = build_fireside_background(self.tavern_bg, FIRESIDE_LAYOUT)
            self.fs_lay = load_fireside_layout(custom)
            self.fs_occ = build_occluders(self.fs_bg, self.fs_lay.get("front") or [])
        self.view, self.modal = "fireside", None
        self.fs_since = 0.0
        self.fs_money0 = self.farm.money
        self.fs_embers.clear()
        self.fs_steam.clear()
        self.fs_fire = None
        self.tv_bubble = None

    def leave_fireside(self):
        self.view = "tavern"

    # ---------- в таверне: камин светится под курсором ----------
    def draw_fireplace_zone(self, s):
        r = self.tl.get("fireside")
        if not r:
            return
        r = pygame.Rect(r)
        if self.modal is None and r.collidepoint(self.mouse):
            fx = self.tl["fx"].get("fire") or r.center
            blit_light(s, fx[0], fx[1] - 24, 200, (255, 196, 100), 160, 0.0)
        self.zone(r, self.open_fireside)
        self.tip(r, "Камин: посидеть у огня (ферма работает сама)")

    # ---------- кадр ----------
    def tick_fireside(self, rdt):
        L = self.fs_lay
        self.fs_since += rdt
        self.fs_flare = max(0.0, self.fs_flare - rdt * 0.35)
        if self.fs_fire is None:
            self.fs_fire = Fire(L["fire"][0], L["fire"][1], L["fire_w"], L["fire_h"])
            for _ in range(60):                       # сразу горит, а не разгорается с нуля
                self.fs_fire.update(1 / 60)
        self.fs_fire.update(rdt, 1.0 + 0.8 * self.fs_flare)
        self.fs_purr = max(0.0, self.fs_purr - rdt)
        self.fs_wag = max(0.0, getattr(self, "fs_wag", 0.0) - rdt)
        self.fs_twitch = max(0.0, self.fs_twitch - rdt * 4)
        if self.fs_twitch <= 0 and random.random() < rdt / 9:
            self.fs_twitch = 1.0
        fx, fy = L["fire"]
        w = L["fire_w"]
        self.fs_ember_t -= rdt
        while self.fs_ember_t <= 0:
            self.fs_ember_t += random.uniform(0.05, 0.14) / (1 + 2 * self.fs_flare)
            life = random.uniform(1.2, 2.6)
            self.fs_embers.append([fx + random.uniform(-0.35, 0.35) * w, fy - random.uniform(10, 60),
                                   random.uniform(-14, 14), random.uniform(-90, -45) * (1 + self.fs_flare),
                                   life, life, random.uniform(1.4, 2.6)])
        for e in self.fs_embers:
            e[2] += math.sin(self.t_real * 3 + e[5] * 7) * 30 * rdt
            e[0] += e[2] * rdt
            e[1] += e[3] * rdt
            e[3] *= 1 - 0.3 * rdt
            e[4] -= rdt
        self.fs_embers = [e for e in self.fs_embers if e[4] > 0][-140:]
        if self.tavern.prize_on("kettle") and random.random() < rdt * 3:
            kx, ky = L["kettle"]
            self.fs_steam.append([kx + random.uniform(-8, 8), ky - 60, 0.0, random.uniform(2.0, 3.2),
                                  random.uniform(0, 6.3)])
        for p in self.fs_steam:
            p[2] += rdt
        self.fs_steam = [p for p in self.fs_steam if p[2] < p[3]][-40:]

    def poke_fire(self):
        """Подбросить полено: огонь вспыхивает, летят искры, трещит."""
        self.fs_flare = 1.0
        self.quest("fire_poke")                      # 3.34: для достижений
        self.sfx.play("spark")
        fx, fy = self.fs_lay["fire"]
        for _ in range(30):
            life = random.uniform(0.6, 1.4)
            self.fs_embers.append([fx + random.uniform(-30, 30), fy - random.uniform(20, 80), random.uniform(-90, 90),
                                   random.uniform(-260, -120), life, life, random.uniform(1.5, 3.0)])

    def pet_cat(self):
        x, y = self.fs_lay["cat"]
        self.fs_purr = 4.0
        self.quest("pet_cat")
        self.fs_twitch = 1.0
        self.floater(x + 20, y - 50, random.choice(CAT_LINES), (255, 236, 200))

    def draw_fireside_extras(self, s, tt):
        from .decor_art import draw_wreath, draw_dog, draw_fireflies
        t, L = self.tavern, self.fs_lay
        if t.prize_on("wreath"):
            draw_wreath(s, *L.get("wreath", (940, 180)), 1.3, tt)
        if t.prize_on("dog"):
            x, y = L.get("dog", (835, 610))
            wag = max(0.0, getattr(self, "fs_wag", 0.0))
            draw_dog(s, x, y, 1.4, tt, min(1.0, wag), wag > 0)
            zone = pygame.Rect(int(x - 85), int(y - 70), 170, 72)
            self.zone(zone, self.pet_dog)
            self.tip(zone, "Погладить пса")
        if t.prize_on("fireflies"):
            draw_fireflies(s, tt, (120, 160, 880, 520), 14, 2)

    def pet_dog(self):
        x, y = self.fs_lay.get("dog", (835, 610))
        self.fs_wag = 3.0
        self.quest("pet_dog")
        self.floater(x - 30, y - 80, random.choice(DOG_LINES), (255, 236, 200))

    def draw_fireside_trophies(self, s):
        """3.21: купленные трофеи — на каминной полке у огня (в зале их больше нет)."""
        from .casino_ui import draw_prize_icon
        trophies = [p for p in PRIZES if p["kind"] == "trophy"]
        for p, spot in zip(trophies, self.fs_lay.get("trophies") or []):
            if not self.tavern.prizes.get(p["id"]):
                continue
            x, y, how = spot[0], spot[1], spot[2]
            k = spot[3] if len(spot) > 3 else 1.5
            if how == "hang":
                draw_prize_icon(s, p, x, y - 19 * k, k)
                pygame.draw.circle(s, OUT, (int(x), int(y - 31 * k)), 4)            # гвоздь
            else:
                blit_light(s, x, y - 19 * k, 50 * k, (255, 220, 150), 60, 0.0)
                draw_prize_icon(s, p, x, y - 20 * k, k)
            self.tip(pygame.Rect(int(x - 18 * k), int(y - 40 * k), int(36 * k), int(40 * k)), f"Трофей: {p['name']}")

    def draw_fireside_view(self):
        s, tt, L, t = self.screen, self.t_real, self.fs_lay, self.tavern
        s.blit(self.fs_bg, (0, 0))
        self.draw_fireside_trophies(s)
        fx, fy = L["fire"]
        w, h = L["fire_w"], L["fire_h"]
        fl = 0.5 * math.sin(tt * 7.3) + 0.3 * math.sin(tt * 12.1 + 1) + 0.2 * math.sin(tt * 3.1)
        # свет огня на всю комнату — пульсирует
        blit_light(s, fx, fy - h * 0.4, 760 + 60 * fl + 160 * self.fs_flare, (255, 150, 60), 70 + 14 * fl, 0.0)
        blit_light(s, fx, fy - h * 0.3, 300 + 30 * fl, (255, 190, 90), 120 + 30 * fl, 0.0)
        if t.prize_on("rug"):
            draw_rug(s, *L["rug"], L.get("rug_k", 1.0))
            blit_light(s, L["rug"][0], L["rug"][1] - 10, 380, (255, 170, 80), 40 + 10 * fl, 0.0)
        if not L.get("painted_logs"):             # на своём фоне угли и поленья уже нарисованы
            draw_coals(s, fx, fy, w, tt)
        if self.fs_fire is not None:
            self.fs_fire.draw(s, tt)
        if t.prize_on("kettle"):
            kx, ky = L["kettle"]
            draw_kettle(s, kx, ky, L.get("kettle_k", 1.25), tt, top=L.get("chain_top"))
        if not L.get("painted_logs"):
            draw_logs(s, fx, fy, w)
        for img, pos in self.fs_occ:              # поленья фона — перед огнём
            s.blit(img, pos)
        for x, y, _vx, _vy, life, life0, size in self.fs_embers:
            k = life / life0
            s.blit(soft_dot(size * 2.4, (255, 120, 40), 150 * k), (int(x - size * 2.4), int(y - size * 2.4)))
            pygame.draw.circle(s, (255, int(110 + 120 * k), int(40 + 60 * k)), (int(x), int(y)), max(1, int(size * k + 0.5)))
        for x, y, age, life, ph in self.fs_steam:
            k = age / life
            r = 5 + 14 * k
            s.blit(soft_dot(r, (250, 246, 240), 70 * math.sin(math.pi * k)),
                   (int(x + math.sin(ph + age * 1.6) * 8 * k - r), int(y - 70 * k - r)))
        self.draw_fireside_extras(s, tt)          # 3.33: венок, кресло-качалка, пёс, светлячки
        if t.prize_on("cat"):
            cx, cy = L["cat"]
            draw_cat(s, cx, cy, 1.6, tt, self.fs_twitch, self.fs_purr > 0)
            self.zone(pygame.Rect(int(cx - 45), int(cy - 50), 90, 56), self.pet_cat)
            self.tip(pygame.Rect(int(cx - 45), int(cy - 50), 90, 56), "Погладить кота")
        self.zone(pygame.Rect(int(fx - w * 0.6), int(fy - h * 0.9), int(w * 1.2), int(h * 0.9 + 20)), self.poke_fire)
        self.tip(pygame.Rect(int(fx - w * 0.6), int(fy - h * 0.9), int(w * 1.2), int(h * 0.9 + 20)),
                 "Подбросить полено")
        # подсказки сверху: появляются и тают
        hint = FIRESIDE_HINTS[0] if self.fs_since < 6 else (FIRESIDE_HINTS[1] if self.fs_since < 11 else None)
        if hint:
            age = self.fs_since % 6 if self.fs_since < 6 else self.fs_since - 6
            a = max(0.0, min(1.0, age / 0.8, (5 - age) / 0.8))
            if a > 0:
                img = render_text(hint, 17, (255, 236, 200), OUT).copy()     # копия: картинки текста в кэше
                hd.real(img).set_alpha(int(255 * a))
                s.blit(img, img.get_rect(center=(W // 2, 34)))
        # пока сидим — сколько заработала ферма
        got = max(0.0, self.farm.money - self.fs_money0)
        if self.fs_since > 3 and got > 0:
            mins = int(self.fs_since // 60)
            text = (f"У огня {mins} мин  ·  " if mins else "") + f"ферма заработала ${fmt(got)}"
            draw_text(s, text, 15, (W - 20, H - 22), (255, 230, 190), anchor="midright")
        self.draw_tavern_back("Встать", self.leave_fireside)
        for x, y, text, life, color in self.floaters:
            draw_text(s, text, 18, (x, y), color)
