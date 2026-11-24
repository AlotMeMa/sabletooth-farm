# -*- coding: utf-8 -*-
"""3.23: окно «Переезд» — карта глав, как выбор уровней: листается влево-вправо, «ты здесь» на текущей ферме,
дальше — закрытые главы. Внизу — выбранная глава: что там, сколько осталось до переезда, кнопка «Переехать!»
и «i» — что именно произойдёт при переезде. Примесь к App.

Своя картинка карты (необязательно): assets/ui/move_map.png — длинная полоса 1240×278 (места глав — MAP_NODES).
"""
from .ui_common import *  # noqa: F401,F403
from .chapters import chapters
from .tavern_art import wrap

MAP_GAP = 300                       # между главами на карте, px
MAP_FIRST = 170                     # первая глава от левого края карты
MAP_Y = [160, 132, 162, 134]        # высота каждой главы на карте (дорожка петляет; сверху место для флажка)
NODE_R = 58                         # радиус кружка главы
MAP_H = 278
TINTS = {"summer": (150, 200, 110), "medieval": (205, 170, 110), "winter": (190, 215, 240), "secret": (170, 160, 175)}
_thumbs = {}
# какой квадрат фона фермы взять в кружок (x, y, сторона): там, где амбар / мельница и край поля
THUMB_BOX = {"summer": (80, 10, 500), "medieval": (50, 0, 520), "winter": (80, 10, 500)}


def map_width(n):
    return MAP_FIRST * 2 + MAP_GAP * (n - 1)


def node_pos(i):
    return MAP_FIRST + i * MAP_GAP, MAP_Y[i % len(MAP_Y)]


def build_map_background(n, ids):
    """Карта-пергамент: своя картинка ui/move_map или кодом — пергамент, пятна-края глав, следы потёртостей."""
    w = map_width(n)
    bg = hd.Surface((w, MAP_H))
    if blit_sprite(bg, "ui/move_map", 0, 0, 1, "topleft"):
        return bg
    bg.fill((232, 214, 176))
    rnd = random.Random(3)
    for i, cid in enumerate(ids):                     # у каждой главы — свой цвет земли вокруг
        x, y = node_pos(i)
        col = TINTS.get(cid, (200, 190, 170))
        for _ in range(10):
            bx, by = x + rnd.uniform(-130, 130), y + rnd.uniform(-70, 90)
            r = rnd.uniform(50, 95)
            bg.blit(soft_dot_img(r, col, 70), (int(bx - r), int(by - r)))
    for _ in range(40):                               # потёртости пергамента
        x, y, r = rnd.uniform(0, w), rnd.uniform(0, MAP_H), rnd.uniform(10, 40)
        bg.blit(soft_dot_img(r, (190, 160, 120), 26), (int(x - r), int(y - r)))
    pygame.draw.rect(bg, (150, 110, 75), (0, 0, w, MAP_H), 4)
    return bg


def soft_dot_img(r, color, alpha):
    from .particles import soft_dot
    return soft_dot(r, color, alpha)


def chapter_thumb(cid, dark):
    """Круглая картинка главы: середина её фона (поле), в кружке. dark — притемнить (закрыта)."""
    key = (cid, dark, hd.scale())
    if key in _thumbs:
        return _thumbs[key]
    d = NODE_R * 2
    out = None
    src = sprite(f"backgrounds/{cid}")
    if src is not None:
        from .spritefit import Pix
        k = hd.scale()
        real_src = hd.real(src)
        bx, by, bs = THUMB_BOX.get(cid, (240, 90, 520))
        box = pygame.Rect(int(bx * k), int(by * k), int(bs * k), int(bs * k)).clip(real_src.get_rect())
        part = hd._orig.get("smoothscale", pygame.transform.smoothscale)(real_src.subsurface(box).copy(),
                                                                          (int(d * k), int(d * k)))
        part = part.convert_alpha() if hasattr(part, "convert_alpha") else part
        if dark:
            part.fill((105, 100, 115, 255), None, pygame.BLEND_RGBA_MULT)
        px = Pix(part)
        size = int(d * k)
        c = size / 2
        for yy in range(size):                         # круглая маска с мягким краем
            for xx in range(size):
                dist = ((xx + 0.5 - c) ** 2 + (yy + 0.5 - c) ** 2) ** 0.5
                a = max(0.0, min(1.0, c - dist))
                px.buf[(yy * size + xx) * 4 + 3] = int(px.buf[(yy * size + xx) * 4 + 3] * a)
        out = hd.wrap(px.surface())
    _thumbs[key] = out
    return out


def draw_lock(s, x, y, k=1.0):
    """Замок (глава закрыта)."""
    pygame.draw.arc(s, OUT, pygame.Rect(int(x - 9 * k), int(y - 20 * k), int(18 * k), int(22 * k)), 0, math.pi,
                    max(3, int(5 * k)))
    pygame.draw.arc(s, (190, 190, 200), pygame.Rect(int(x - 9 * k), int(y - 20 * k), int(18 * k), int(22 * k)), 0,
                    math.pi, max(1, int(2 * k)))
    rounded(s, (225, 180, 70), (int(x - 13 * k), int(y - 9 * k), int(26 * k), int(22 * k)), 4, 3, skin=None)
    pygame.draw.circle(s, OUT, (int(x), int(y + 1 * k)), max(2, int(3 * k)))


class MoveUI:
    def init_move_map(self):
        self.map_x = 0.0
        self.map_target = 0.0
        self.map_sel = 0
        self.map_t = 0.0
        self.move_info = False
        self.map_drag_last = None
        self.map_bg = None

    def open_move_map(self):
        """Окно открылось: карта на текущей главе, выбрана следующая (если есть) — видно, куда ехать."""
        f = self.farm
        chs = chapters(f.farm_index)
        self.map_sel = min(f.farm_index + 1, len(chs) - 1) if f.has_next_farm() else f.farm_index
        self.move_info = False
        self.map_target = self.map_center_on(f.farm_index)
        self.map_x = self.map_target

    # ---------- прокрутка ----------
    def map_view(self):
        r = getattr(self, "panel_rect", None) or pygame.Rect(60, 46, 880, 548)
        return pygame.Rect(r.x + 66, r.y + 50, r.w - 132, MAP_H)      # по бокам — место для стрелок

    def map_max(self):
        return max(0, map_width(len(chapters(self.farm.farm_index))) - self.map_view().w)

    def map_center_on(self, i):
        x, _y = node_pos(i)
        return max(0.0, min(self.map_max(), x - self.map_view().w / 2 + MAP_GAP * 0.25))

    def map_scroll(self, dx):
        self.map_target = max(0.0, min(self.map_max(), self.map_target + dx))

    def map_wheel(self, e):
        if self.modal == "move":
            self.map_scroll(-(getattr(e, "y", 0) + getattr(e, "x", 0)) * 120)

    def map_drag(self, pos):
        """Тянем карту мышью (кнопка зажата)."""
        if self.modal != "move":
            return
        if self.map_drag_last is None:
            if self.map_view().collidepoint(pos):
                self.map_drag_last = pos
            return
        dx = pos[0] - self.map_drag_last[0]
        self.map_drag_last = pos
        self.map_target = max(0.0, min(self.map_max(), self.map_target - dx))
        self.map_x = self.map_target

    def map_select(self, i):
        self.map_sel = i
        self.map_target = self.map_center_on(i)

    # ---------- окно ----------
    def draw_move(self):
        s, f = self.screen, self.farm
        chs = chapters(f.farm_index)
        if self.map_bg is None or self.map_bg.get_width() != map_width(len(chs)):
            self.map_bg = build_map_background(len(chs), [c["id"] for c in chs])
        r = self.panel(880, 548, "КАРТА ГЛАВ")
        view = self.map_view()
        now = self.t_real
        dt = max(0.0, min(0.1, now - self.map_t))
        self.map_t = now
        self.map_x += (self.map_target - self.map_x) * min(1.0, dt * 9)
        active = not self.move_info
        # --- карта ---
        layer = hd.Surface((view.w, view.h))
        layer.blit(self.map_bg, (-int(self.map_x), 0))
        pts = [node_pos(i) for i in range(len(chs))]
        for i in range(len(pts) - 1):                    # дорожка между главами: пройденная — сплошная
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            done = chs[i + 1]["state"] in ("done", "here")
            steps = 26
            for k in range(steps):
                if not done and k % 2:
                    continue
                u0, u1 = k / steps, (k + 1) / steps
                a = (x0 + (x1 - x0) * u0 - self.map_x, y0 + (y1 - y0) * u0 + math.sin(u0 * math.pi) * 22)
                b = (x0 + (x1 - x0) * u1 - self.map_x, y0 + (y1 - y0) * u1 + math.sin(u1 * math.pi) * 22)
                pygame.draw.line(layer, (120, 85, 55) if done else (165, 140, 115), a, b, 6 if done else 4)
        for i, c in enumerate(chs):
            x, y = pts[i]
            x -= self.map_x
            if x < -NODE_R * 2 or x > view.w + NODE_R * 2:
                continue
            self.draw_map_node(layer, c, x, y, i == self.map_sel, now)
        s.blit(layer, view.topleft)
        pygame.draw.rect(s, OUT, view.inflate(4, 4), 3, border_radius=6)
        if active:
            for i, c in enumerate(chs):                  # клик по главе — выбрать
                x, y = pts[i]
                nr = pygame.Rect(0, 0, NODE_R * 2 + 10, NODE_R * 2 + 40)
                nr.center = (int(view.x + x - self.map_x), int(view.y + y + 12))
                if view.colliderect(nr):
                    self.zone_btn(nr.clip(view), lambda n=i: self.map_select(n), NODE_R)
            if self.map_target > 1:                       # стрелки — снаружи карты, по бокам
                self.button((view.x - 52, view.centery - 26, 42, 52), "<", lambda: self.map_scroll(-MAP_GAP), BTN_BLUE)
            if self.map_target < self.map_max() - 1:
                self.button((view.right + 10, view.centery - 26, 42, 52), ">", lambda: self.map_scroll(MAP_GAP),
                            BTN_BLUE)
        # --- выбранная глава ---
        info = pygame.Rect(r.x + 22, view.bottom + 12, r.w - 44, r.bottom - 24 - view.bottom - 12)
        self.draw_map_card(info, chs[self.map_sel], chs, active)
        if self.move_info:
            self.draw_move_info(r)

    def draw_map_node(self, s, c, x, y, selected, t):
        st = c["state"]
        ring = {"done": (110, 185, 90), "here": (250, 200, 70), "next": (120, 180, 240)}.get(st, (150, 140, 130))
        draw_shadow(s, x, y + NODE_R + 6, NODE_R * 1.7, 18, 60)
        if st == "here":
            blit_light(s, x, y, NODE_R * 3.2 * (1 + 0.04 * math.sin(t * 3)), (255, 220, 120), 150, 0.0)
        if selected:
            pygame.draw.circle(s, WHITE, (int(x), int(y)), NODE_R + 11)
        pygame.draw.circle(s, OUT, (int(x), int(y)), NODE_R + 7)
        pygame.draw.circle(s, ring, (int(x), int(y)), NODE_R + 5)
        dark = st in ("soon", "locked")
        img = chapter_thumb(c["id"], dark) if c["id"] != "secret" else None
        if img is not None:
            s.blit(img, (int(x - NODE_R), int(y - NODE_R)))
        else:
            pygame.draw.circle(s, (120, 110, 130) if c["id"] == "secret" else (200, 190, 170), (int(x), int(y)), NODE_R)
            if c["id"] == "secret":
                draw_text(s, "?", 46, (int(x), int(y) - 2), (235, 230, 240))
        if st in ("soon", "locked") and c["id"] != "secret":
            draw_lock(s, x, y + 6, 1.4)
        if st == "done":                                         # галочка: пройдено
            pygame.draw.circle(s, OUT, (int(x + NODE_R * 0.72), int(y - NODE_R * 0.72)), 15)
            pygame.draw.circle(s, (110, 185, 90), (int(x + NODE_R * 0.72), int(y - NODE_R * 0.72)), 13)
            cx, cy = x + NODE_R * 0.72, y - NODE_R * 0.72
            pygame.draw.lines(s, WHITE, False, [(cx - 6, cy), (cx - 1, cy + 5), (cx + 7, cy - 5)], 3)
        # подпись
        label = c["name"] if c["id"] != "secret" else "Тайна"
        img_t = render_text(label, 15, WHITE, OUT)
        plate = pygame.Rect(0, 0, img_t.get_width() + 34, 30)
        plate.midtop = (int(x), int(y + NODE_R + 4))
        if not skin.plate(s, "pill", plate):
            rounded(s, PILL, plate, 15, 3)
        s.blit(img_t, img_t.get_rect(center=plate.center))
        tag = {"soon": "скоро", "locked": "закрыто"}.get(st)
        if tag:
            draw_text(s, tag, 13, (int(x), plate.bottom + 8), (120, 95, 80), outline=None)
        if st == "here":                                         # флажок «ты здесь» прыгает над главой
            hop = abs(math.sin(t * 2.6)) * 7
            py = y - NODE_R - 22 - hop
            pygame.draw.line(s, OUT, (int(x), int(py)), (int(x), int(py + 22)), 4)
            poly(s, (230, 80, 70), [(x, py - 26), (x + 34, py - 18), (x, py - 8)], 2)
            draw_text(s, "Ты здесь", 14, (int(x + 2), int(py - 38)), (255, 240, 200))

    def draw_map_card(self, box, c, chs, active):
        s, f = self.screen, self.farm
        brown, soft = (90, 70, 60), (140, 110, 95)
        rounded(s, (238, 222, 192), box, 10, 2, skin="card")
        left = pygame.Rect(box.x + 22, box.y + 14, box.w * 0.55, box.h - 28)
        draw_text(s, f"Глава {c['n']}" if c["id"] != "secret" else "Дальше", 14, (left.x, left.y + 8), soft,
                  anchor="midleft", outline=None)
        draw_text_fit(s, c["name"] if c["id"] != "secret" else "Тайна", 22, (left.x, left.y + 34), left.w, brown,
                      anchor="midleft", outline=None)
        for n, line in enumerate(wrap(c["text"], 14, left.w, 4)):
            draw_text(s, line, 14, (left.x, left.y + 64 + n * 21), brown, anchor="midleft", outline=None)
        right = pygame.Rect(left.right + 16, box.y + 16, box.right - left.right - 38, box.h - 32)
        st = c["state"]
        nxt = next((ch for ch in chs if ch["state"] in ("next", "soon")), None)
        if st in ("here", "next") and nxt is not None and nxt["state"] == "next":
            need, have = f.move_threshold(), f.run_total()
            draw_text_fit(s, f"Переезд на «{nxt['name']}»", 16, (right.centerx, right.y + 10), right.w, brown,
                          outline=None)
            draw_text(s, f"нужно заработать за забег ${fmt(need)}", 13, (right.centerx, right.y + 33), soft,
                      outline=None)
            bar = pygame.Rect(right.x, right.y + 46, right.w, 20)
            draw_bar(s, bar, have / need, (120, 200, 255))
            draw_text(s, f"${fmt(have)}  ({min(100, int(have / need * 100))}%)", 13, bar.center)
            bt = pygame.Rect(right.x, right.bottom - 50, right.w - 58, 48)
            if active:
                self.button(bt, "Переехать!", self.do_move, (245, 175, 50), f.can_move(), 20)
                ib = pygame.Rect(bt.right + 10, bt.y + 2, 46, 44)
                self.button(ib, "i", lambda: setattr(self, "move_info", True), BTN_BLUE, True, 22)
                self.tip(ib, "Что будет при переезде")
            else:
                skin.draw(s, "button_grey", bt)
        elif st == "here":
            draw_text_fit(s, "Ты здесь", 18, (right.centerx, right.y + 16), right.w, brown, outline=None)
            for n, line in enumerate(wrap("Следующая глава готовится — она появится на карте с обновлением. "
                                          "А пока доход тут растёт и растёт!", 14, right.w, 4)):
                draw_text(s, line, 14, (right.centerx, right.y + 46 + n * 20), soft, outline=None)
        elif st == "done":
            draw_text(s, "Пройдено", 18, (right.centerx, right.y + 16), (80, 150, 70), outline=None)
            trophy = FARMS[c["n"] - 1]["trophy"]["name"]
            for n, line in enumerate(wrap(f"С тобой навсегда: доход x{FARM_BONUS} и трофей «{trophy}».", 14,
                                          right.w, 3)):
                draw_text(s, line, 14, (right.centerx, right.y + 46 + n * 20), soft, outline=None)
        else:
            prev = chs[c["n"] - 2]["name"] if c["n"] >= 2 else ""
            title = "Скоро" if st == "soon" else "Закрыто"
            text = ("Эта глава ещё готовится — она откроется в одном из обновлений." if st == "soon"
                    else f"Откроется после главы «{prev}».") if c["id"] != "secret" else \
                "Что там — пока секрет даже для бармена."
            draw_text(s, title, 18, (right.centerx, right.y + 16), brown, outline=None)
            for n, line in enumerate(wrap(text, 14, right.w, 4)):
                draw_text(s, line, 14, (right.centerx, right.y + 46 + n * 20), soft, outline=None)

    def draw_move_info(self, r):
        """«i»: что произойдёт при переезде (поверх карты)."""
        s, f = self.screen, self.farm
        fade = hd.Surface((r.w, r.h), pygame.SRCALPHA)
        fade.fill((30, 20, 10, 120))
        s.blit(fade, r.topleft)
        box = pygame.Rect(0, 0, 600, 330)
        box.center = r.center
        rounded(s, (245, 232, 205), box, 12, 3, skin="card")
        brown, soft = (90, 70, 60), (140, 110, 95)
        trophy = self.farm_info()["trophy"]
        nxt = FARMS[f.farm_index + 1] if f.farm_index + 1 < len(FARMS) else None
        draw_text(s, "Что будет при переезде", 20, (box.centerx, box.y + 30), brown, outline=None)
        parts = [
            (f"Новая глава: всё начинается с нуля — деньги, грядки, здания, {CUR['title'].lower()} и дерево улучшений.",
             (190, 80, 70)),
            (f"С собой: доход x{FARM_BONUS} навсегда за каждую пройденную ферму и трофей «{trophy['name']}»"
             + (f": {trophy['text']}." if trophy["text"] and not trophy["text"].startswith("(") else "."), brown),
            ("Таверна, жетоны и призы остаются с тобой.", brown),
        ]
        if nxt and nxt["peasants"]:
            parts.append(("Там: крестьяне, мельница с пекарней, разбойники, печати.", soft))
        elif nxt and nxt["frost"]:
            parts.append(("Там: вместо дождя оттепель, вместо вороны мороз.", soft))
        y = box.y + 66
        for text, col in parts:
            for line in wrap(text, 15, box.w - 60, 3):
                draw_text(s, line, 15, (box.centerx, y), col, outline=None)
                y += 24
            y += 8
        self.button((box.centerx - 90, box.bottom - 62, 180, 46), "Понятно", lambda: setattr(self, "move_info", False),
                    BTN_GREEN, True, 18)
