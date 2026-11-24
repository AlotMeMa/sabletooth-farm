# -*- coding: utf-8 -*-
"""Живой зал таверны: такт музыки, ноты, огонь, пар, пылинки, трофеи, гирлянда.

Примесь к App (3.17: вынесено из tavern_ui.py без изменений). Разметка и рисунки — tavern_art.
"""
from .tavern_art import *  # noqa: F401,F403


class TavernLifeUI:
    # ---------- живой зал (3.5) ----------
    def tv_beat(self):
        """Сколько долей музыки таверны прошло (дробное число): по времени самой музыки, а если звука нет —
        по часам игры. Целая часть — номер доли, дробная — где мы внутри доли."""
        m = self.tl["music"]
        if self.audio_scene == "tavern_girl":
            m = self.tl.get("music_girl", m)
        pos = self.music.position() if self.audio_scene in ("tavern", "tavern_girl") else None
        if pos is None:
            pos = self.t_real
        elif m.get("loop", 0) > 0:
            pos %= m["loop"]
        return (pos - m.get("offset", 0.0)) * m["bpm"] / 60.0

    def tick_tavern_life(self, rdt):
        """Ноты в такт, искры камина, пар, блик на кружке бармена."""
        d = self.tl["bard"]
        self.tv_solo = max(0.0, self.tv_solo - rdt)
        if self.farm.song_left > 0 and self.farm.song:
            self.tv_solo = max(self.tv_solo, 0.5)        # 3.8: заказанная песня — бард играет с огоньком
        half = math.floor(self.tv_beat() * 2)
        if self.tv_half is None or abs(half - self.tv_half) > 8:
            self.tv_half = half            # первый кадр или повтор трека — без залпа нот
        elif half != self.tv_half:
            self.tv_half = half
            if self.tv_solo > 0 or half % 2 == 0:
                # ноты вылетают у грифа лютни (справа от головы барда) и плывут вверх-вправо
                self.tv_notes.append([d["x"] + 34 * d["k"] + random.uniform(-6, 6), d["y"] - 72 * d["k"],
                                      2.2, random.uniform(5, 35), NOTE_COLORS[half % len(NOTE_COLORS)]])
        fx = self.tl["fx"]
        if fx.get("fire"):
            fx0, fy0 = fx["fire"]
            self.tv_ember_t -= rdt
            while self.tv_ember_t <= 0:
                self.tv_ember_t += random.uniform(0.07, 0.2)
                life = random.uniform(0.7, 1.4)
                self.tv_embers.append([fx0 + random.uniform(-12, 12), fy0 - 6, random.uniform(-7, 7),
                                       random.uniform(-50, -26), life, life])
        for e in self.tv_embers:
            e[0] += e[2] * rdt + math.sin(self.t_real * 7 + e[5] * 9) * 0.35
            e[1] += e[3] * rdt
            e[4] -= rdt
        self.tv_embers = [e for e in self.tv_embers if e[4] > 0][-60:]
        self.tv_steam_t -= rdt
        if self.tv_steam_t <= 0 and fx.get("steam"):
            self.tv_steam_t = random.uniform(0.25, 0.45)
            n = random.randrange(len(fx["steam"]))
            sx, sy = fx["steam"][n]
            self.tv_steam.append([sx + random.uniform(-5, 5), sy, 0.0, random.uniform(2.2, 3.2),
                                  random.uniform(0, 6.3), 1.0 if n == 0 else 0.7])
        for p in self.tv_steam:
            p[2] += rdt
        self.tv_steam = [p for p in self.tv_steam if p[2] < p[3]][-40:]
        self.tv_twinkle_t -= rdt
        if self.tv_twinkle_t <= 0:
            self.tv_twinkle_t = random.uniform(3.5, 7.0)
            if fx.get("barman_mug"):
                mx, my = fx["barman_mug"]
                self.fx.twinkle(mx + random.uniform(-4, 4), my + random.uniform(-3, 3), 7, life=0.55)

    def draw_tavern_life(self, s, tt):
        """Свет и воздух зала (под персонажами): пылинки в свете окон, огонь камина, свечи, пар."""
        fx = self.tl["fx"]
        if self.tavern.prize_on("garland"):
            self.draw_garland(s, tt)
        if fx.get("motes"):
            x0, y0, x1, y1 = fx["motes"]
            if self.tv_motes is None:
                rnd = random.Random(7)
                self.tv_motes = [(rnd.uniform(x0, x1), rnd.uniform(y0, y1), rnd.uniform(0, 6.3)) for _ in range(18)]
            for mx, my, ph in self.tv_motes:
                x = mx + 10 * math.sin(tt * 0.13 + ph)
                y = my + 7 * math.sin(tt * 0.17 + ph * 1.7)
                a = 30 + 70 * (0.5 + 0.5 * math.sin(tt * 0.9 + ph * 3))
                img = soft_dot(1.6, (255, 246, 215), a)
                s.blit(img, (int(x) - 2, int(y) - 2))
        if fx.get("fire"):
            fx0, fy0 = fx["fire"]
            fl = 0.5 * math.sin(tt * 7.3) + 0.3 * math.sin(tt * 12.1 + 1) + 0.2 * math.sin(tt * 3.1)
            blit_light(s, fx0, fy0 - 16, 130 + 16 * fl, (255, 160, 60), 64 + 22 * fl, 0.0)
            for x, y, _vx, _vy, life, life0 in self.tv_embers:
                k = life / life0
                col = (255, int(90 + 90 * k), int(20 + 40 * k))
                s.blit(soft_dot(3.5, (255, 110, 30), 170 * k), (int(x) - 5, int(y) - 5))
                pygame.draw.circle(s, col, (int(x), int(y)), 2 if k > 0.5 else 1)
        for n, (cx, cy) in enumerate(fx.get("candles") or []):
            fl = 0.6 * math.sin(tt * 8.7 + n * 2.1) + 0.4 * math.sin(tt * 13.3 + n)
            blit_light(s, cx, cy, 40 + 6 * fl, (255, 205, 120), 92 + 26 * fl, 0.0)
        for x, y, t, life, ph, power in self.tv_steam:
            k = t / life
            r = 2.5 + 5.5 * k
            a = 60 * power * math.sin(math.pi * k)
            img = soft_dot(r, (250, 248, 240), a)
            px = x + math.sin(ph + t * 1.7) * 4 * k
            s.blit(img, (int(px - r) - 1, int(y - 30 * k - r) - 1))

    # ---------- HUD ----------
    def draw_tavern_trophies(self, s, front=False):
        """Купленные в казино трофеи в таверне. Места — "trophies" в разметке: [x, y, как, слой]
        (x, y — низ по центру; как: "hang" — висит на гвозде, "stand" — стоит, "shelf" — на своей полочке;
        слой "front" — рисуется после бармена, перед стойкой: вещь лежит на стойке перед ним)."""
        from .casino_ui import draw_prize_icon
        spots = self.tl.get("trophies") or []
        trophies = [p for p in PRIZES if p["kind"] == "trophy"]
        for p, spot in zip(trophies, spots):
            x, y = spot[0], spot[1]
            how = spot[2] if len(spot) > 2 else "stand"
            if (len(spot) > 3 and spot[3] == "front") != front or not self.tavern.prizes.get(p["id"]):
                continue
            if how == "hang":                                    # висит на гвозде
                draw_prize_icon(s, p, x, y - 18, 0.9)
                pygame.draw.circle(s, OUT, (int(x), int(y) - 30), 3)              # гвоздь между рожками
                pygame.draw.circle(s, (170, 170, 175), (int(x), int(y) - 30), 1)
            else:
                if how == "shelf":                               # маленькая полочка на стене
                    rounded(s, (140, 92, 54), (int(x) - 20, int(y), 40, 7), 2, 2, skin=None)
                blit_light(s, x, y - 18, 50, (255, 236, 170), 70, 0.0)
                draw_prize_icon(s, p, x, y - 19, 0.95)
            self.tip(pygame.Rect(int(x) - 18, int(y) - 38, 36, 40), f"Трофей из казино: {p['name']}")

    def draw_tavern_decor(self, s, tt):
        """3.19: купленные украшения в зале: котелок над огнём, кот у камина, цветы на столах.
        Места — "decor" в разметке (поправить можно в tavern.json)."""
        from .fireside_art import draw_cat, draw_kettle, draw_flowers
        t, d = self.tavern, self.tl.get("decor") or {}
        if t.prize_on("kettle") and d.get("kettle"):
            draw_kettle(s, d["kettle"][0], d["kettle"][1], 0.36, tt, top=d.get("kettle_top"))
        if t.prize_on("cat") and d.get("cat"):
            draw_cat(s, d["cat"][0], d["cat"][1], 0.62, tt, 1.0 if math.sin(tt * 0.7) > 0.97 else 0.0)
        if t.prize_on("flowers"):
            for x, y in d.get("flowers") or []:
                draw_flowers(s, x, y, 0.55, tt)

    def draw_garland(self, s, tt):
        """3.14, приз казино: гирлянда огоньков провисает под балконом, лампочки мигают по очереди."""
        y0 = self.tl.get("garland_y", 212)
        xs = [160, 400, 650, 900]
        cols = [(255, 90, 80), (255, 210, 80), (110, 220, 120), (110, 170, 255)]
        bulbs = ["fx/bulb_red", "fx/bulb_yellow", "fx/bulb_green", "fx/bulb_blue"]   # 3.16: свои лампочки
        n = 0
        for a, b in zip(xs, xs[1:]):
            pts = []
            for i in range(13):
                u = i / 12
                pts.append((a + (b - a) * u, y0 + 22 * 4 * u * (1 - u)))
            pygame.draw.lines(s, (60, 45, 35), False, [(int(x), int(y)) for x, y in pts], 2)
            for x, y in pts[1:-1:2]:
                col = cols[n % len(cols)]
                on = 0.55 + 0.45 * math.sin(tt * 2.4 - n * 0.9)
                blit_light(s, x, y + 6, 30, col, 90 + 120 * on, 0.0)
                if not blit_tf(s, bulbs[n % len(bulbs)], x, y + 7, 0.6, pivot="center", alpha=150 + 105 * on):
                    pygame.draw.circle(s, OUT, (int(x), int(y + 6)), 5)
                    pygame.draw.circle(s, tuple(int(c * (0.6 + 0.4 * on)) for c in col), (int(x), int(y + 6)), 4)
                n += 1
