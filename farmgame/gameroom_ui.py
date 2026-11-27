# -*- coding: utf-8 -*-
"""3.27: Игровая (бывшее казино) — вертикальная карта игр, как карта глав, только сверху вниз.

Сверху — ежедневное колесо фортуны (wheel.py), ниже по дорожке — рулетка, блэкджек (скоро), дальше — тайна.
Карту листают колесом мыши, перетаскиванием и стрелками ↑/↓. Всё рисуется кодом; свои картинки (необязательно):
ui/gameroom_map (вертикальная полоса 540×1460: бархат/ковёр с дорожкой, места игр — GAME_NODES),
props/fortune_wheel (колесо фортуны без надписей, квадрат), icons/game_<id> (значки игр в кружках).
Игровая, жетоны, призы и колесо — общие для всех ферм: переезжают вместе с таверной.
"""
import math
import random

import pygame

from .ui_common import *  # noqa: F401,F403
from .tavern_ui import draw_token
from .tavern_art import wrap
from .move_ui import draw_lock
from . import wheel as wh
from . import blackjack as bjl
from . import snails as snl
from .blackjack_ui import draw_suit

GR_VIEW = pygame.Rect(230, 64, 540, 566)        # окно карты на экране
GR_H = 1460                                     # высота всей карты (3.43: + кости)
GAME_NODES = [   # id, имя, (x, y) на карте, описание
    dict(id="wheel", name="Колесо фортуны", pos=(270, 150),
         text="Раз в день — бесплатно. Пусто, жетоны или джекпот недели."),
    dict(id="roulette", name="Рулетка", pos=(160, 440),
         text="Европейская рулетка с крупье. Ставки от 5 жетонов."),
    dict(id="blackjack", name="Блэкджек", pos=(380, 720), unlock="winter",
         text="Набери 21 и обыграй рыжего гнома Ворчуна. Открывается зимой."),
    dict(id="snails", name="Скачки улиток", pos=(220, 1000), unlock="fishing",      # 3.40: вместо «???»
         text="Ставь жетоны на улитку и болей! Ведёт моряк Старый Якорь. В Рыбацкой деревне."),
    dict(id="dice", name="Кости", pos=(370, 1290), unlock="dragons",                  # 3.43
         text="Больше, меньше или ровно 7? Кидает драконида Искра. В горах драконов."),
]
GR_NODE_R = 62
ICON_FILL = (GR_NODE_R * 2 + 8) / 100      # значок игры (холст 100) — во весь кружок, со своим ободком поверх нашего
# 3.45.2: своя карта пользователя — один экран (540×566, без прокрутки), игры — на её 5 круглых площадках
PAINTED_POS = [(270, 100), (168, 195), (372, 282), (168, 370), (372, 455)]
PAINTED_R = 44
CODE_LAYOUT = dict(h=GR_H, r=GR_NODE_R, pos=[n["pos"] for n in GAME_NODES])


def apply_layout(painted):
    """Карта своей картинкой — компактно, на площадках; кодом — длинная полоса с прокруткой, как раньше."""
    global GR_H, GR_NODE_R, ICON_FILL
    if painted:
        GR_H, GR_NODE_R = GR_VIEW.h, PAINTED_R
        pos = PAINTED_POS
    else:
        GR_H, GR_NODE_R, pos = CODE_LAYOUT["h"], CODE_LAYOUT["r"], CODE_LAYOUT["pos"]
    for node, p in zip(GAME_NODES, pos):
        node["pos"] = p
    ICON_FILL = (GR_NODE_R * 2 + 8) / 100
# цвета секторов по смыслу: «пусто» — приглушённые, жетоны — яркие, джекпот — чёрный с золотом
WHEEL_COLORS = ((120, 75, 85), (245, 205, 90), (80, 95, 120), (110, 190, 90),
                (90, 160, 230), (115, 105, 95), (205, 95, 200), (40, 34, 36))
WHEEL_SPIN = 4.6                                # сколько крутится колесо фортуны, с


def build_gameroom_map():
    """Вертикальная карта: своя картинка ui/gameroom_map или кодом — бархат, ромбики, золотая рамка."""
    apply_layout(has_sprite("ui/gameroom_map"))
    bg = hd.Surface((GR_VIEW.w, GR_H))
    if blit_sprite(bg, "ui/gameroom_map", 0, 0, 1, "topleft"):
        return bg, True
    for y in range(0, GR_H, 4):                 # бархат: сверху светлее
        u = y / GR_H
        c = (int(120 - 50 * u), int(30 - 12 * u), int(40 - 14 * u))
        pygame.draw.rect(bg, c, (0, y, GR_VIEW.w, 4))
    rnd = random.Random(7)
    for y in range(20, GR_H, 60):               # ромбики узора
        for x in range((y // 60) % 2 * 30 + 15, GR_VIEW.w, 60):
            pygame.draw.polygon(bg, (150, 45, 55), [(x, y - 8), (x + 6, y), (x, y + 8), (x - 6, y)], 1)
    for _ in range(60):                         # золотая пыль
        pygame.draw.circle(bg, (200, 160, 80), (rnd.randrange(GR_VIEW.w), rnd.randrange(GR_H)), 1)
    return bg, False


def draw_fortune_wheel(s, cx, cy, r, angle, labels=True):
    """Колесо фортуны: 8 секторов (wheel.SEGMENTS), angle — поворот в радианах (сектор 0 — под стрелкой сверху)."""
    n = len(wh.SEGMENTS)
    step = 2 * math.pi / n
    pygame.draw.circle(s, OUT, (P(cx), P(cy)), P(r + 6))
    pygame.draw.circle(s, (120, 70, 40), (P(cx), P(cy)), P(r + 4))
    for i in range(n):                          # сектора — всегда кодом: награды точно под стрелкой
        a0 = -math.pi / 2 + angle + (i - 0.5) * step
        pts = [(cx, cy)] + [(cx + math.cos(a0 + step * t / 8) * r, cy + math.sin(a0 + step * t / 8) * r)
                            for t in range(9)]
        pygame.draw.polygon(s, WHEEL_COLORS[i % len(WHEEL_COLORS)], [(P(x), P(y)) for x, y in pts])
        pygame.draw.line(s, OUT, (P(cx), P(cy)), (P(pts[1][0]), P(pts[1][1])), 2)
    # обод: своя картинка props/fortune_wheel (кольцо, середина пустая) или гвоздики кодом
    if not blit_tf(s, "props/fortune_wheel", cx, cy, (2 * r + 40) / 300, angle=-math.degrees(angle), pivot="center"):
        for i in range(n * 2):                  # гвоздики по ободу
            a = -math.pi / 2 + angle + (i - 1) * step / 2
            pygame.draw.circle(s, (255, 225, 140), (P(cx + math.cos(a) * (r + 1)), P(cy + math.sin(a) * (r + 1))),
                               max(2, P(r * 0.035)))
    if labels:
        for i, (kind, amount, label) in enumerate(wh.SEGMENTS):
            a = -math.pi / 2 + angle + i * step
            tx, ty = cx + math.cos(a) * r * 0.66, cy + math.sin(a) * r * 0.66
            if kind == "tokens":
                draw_token(s, tx, ty - r * 0.06, r / 260)
                draw_text(s, label, max(10, int(r * 0.13)), (P(tx), P(ty + r * 0.1)), WHITE)
            elif kind == "jackpot":                 # звезда (символ ★ есть не во всех шрифтах) и «ДЖЕКПОТ»
                blit_light(s, tx, ty, r * 0.5, (255, 220, 120), 170, 0.0)
                sr = r * 0.1
                star = [(tx + math.cos(-math.pi / 2 + i * math.pi / 5) * (sr if i % 2 == 0 else sr * 0.45),
                         ty - r * 0.05 + math.sin(-math.pi / 2 + i * math.pi / 5) * (sr if i % 2 == 0 else sr * 0.45))
                        for i in range(10)]
                poly(s, (255, 215, 80), star, 2)
                draw_text(s, "ДЖЕКПОТ", max(8, int(r * 0.07)), (P(tx), P(ty + r * 0.1)), (255, 220, 90))
            else:
                draw_text(s, "—", max(10, int(r * 0.14)), (P(tx), P(ty)), (90, 70, 60), outline=None)
    pygame.draw.circle(s, OUT, (P(cx), P(cy)), P(r * 0.14) + 2)
    pygame.draw.circle(s, GOLD, (P(cx), P(cy)), P(r * 0.14))


def draw_game_icon(s, gid, x, y, k=1.0, t=0.0):
    """Значок игры в кружке карты: картинка icons/game_<id> или кодом."""
    if blit_sprite(s, f"icons/game_{gid}", x, y, k * ICON_FILL, "center"):   # своя картинка — на весь кружок
        return
    if gid == "wheel":
        draw_fortune_wheel(s, x, y, 46 * k, t * 0.4, labels=False)
        poly(s, (230, 60, 60), [(x - 8 * k, y - 54 * k), (x + 8 * k, y - 54 * k), (x, y - 40 * k)], 2)
    elif gid == "roulette":
        pygame.draw.circle(s, OUT, (P(x), P(y)), P(46 * k) + 2)
        pygame.draw.circle(s, (120, 70, 40), (P(x), P(y)), P(46 * k))
        for i in range(18):
            a = t * 0.3 + i * math.pi / 9
            col = (196, 52, 48) if i % 2 else (38, 34, 36)
            pygame.draw.circle(s, col, (P(x + math.cos(a) * 34 * k), P(y + math.sin(a) * 34 * k)), max(2, P(6 * k)))
        pygame.draw.circle(s, (40, 120, 70), (P(x), P(y)), P(24 * k))
        pygame.draw.circle(s, GOLD, (P(x), P(y)), P(7 * k))
        pygame.draw.circle(s, WHITE, (P(x + math.cos(-t) * 40 * k), P(y + math.sin(-t) * 40 * k)), max(2, P(4 * k)))
    elif gid == "blackjack":                      # две карты внахлёст: туз и король
        for i, (dx, dy, txt) in enumerate(((-12, -4, "A"), (12, 4, "K"))):
            card = pygame.Rect(0, 0, P(38 * k), P(52 * k))
            card.center = (P(x + dx * k), P(y + dy * k))
            rounded(s, (250, 245, 235), card, max(3, P(5 * k)), 2, skin=None)
            draw_text(s, txt, max(12, P(20 * k)), (card.centerx, card.centery - P(4 * k)),
                      (190, 40, 40) if i else OUT, outline=None)
            draw_suit(s, "hearts" if i else "spades", card.centerx, card.bottom - P(12 * k), 0.8 * k)
    elif gid == "snails":                         # 3.40: улитка на дорожке
        from .snails_ui import draw_snail
        pygame.draw.circle(s, (60, 124, 80), (P(x), P(y)), P(46 * k))
        pygame.draw.line(s, (240, 230, 200), (P(x + 30 * k), P(y - 30 * k)), (P(x + 30 * k), P(y + 30 * k)), max(2, P(3 * k)))
        draw_snail(s, x - 4 * k, y + 14 * k, 1.5 * k, 0, t)
    elif gid == "dice":                           # 3.43: две кости
        from .dice_ui import draw_die
        pygame.draw.circle(s, (150, 60, 55), (P(x), P(y)), P(46 * k))
        draw_die(s, x - 16 * k, y + 6 * k, 38 * k, 3, 0.0)
        draw_die(s, x + 16 * k, y - 8 * k, 38 * k, 4, 0.0)
    else:
        draw_text(s, "?", max(20, int(50 * k)), (P(x), P(y) - 2), (235, 220, 200))


UNLOCK_TAG = {"winter": "ЗИМОЙ", "fishing": "В ДЕРЕВНЕ", "dragons": "В ГОРАХ"}
UNLOCK_BUTTON = {"winter": "Зимой", "fishing": "В деревне", "dragons": "В горах"}


def game_locked(node, farm_index):
    """3.40: игра закрыта до своей главы (блэкджек — зима, улитки — Рыбацкая деревня)."""
    fid = node.get("unlock")
    if not fid:
        return False
    from .config import FARMS
    idx = next((n for n, fm in enumerate(FARMS) if fm["id"] == fid), len(FARMS))
    return farm_index < idx


class GameRoomUI:
    # ------------------------------------------------------------ состояние
    def init_gameroom(self):
        self.gr_scroll = 0.0           # прокрутка карты (y)
        self.gr_target = 0.0
        self.gr_drag_last = None
        self.gr_bg = None              # (картинка, своя ли)
        self.gr_sel = "wheel"          # выбранная игра (подпись справа)
        self.fw_angle = 0.0            # колесо фортуны: поворот
        self.fw_spin = None            # dict(t, a0, a1, idx, reward) — пока крутится
        self.fw_ticks = 0              # сколько секторов проехало (щелчок на каждом)
        self.fw_msg = None

    def open_gameroom(self):
        """Игровая — за дверью таверны (бывшее казино). Колесо фортуны доступно — выбрано и подсвечено."""
        self.tavern.unlocked = True
        self.open_tavern()
        self.view = "gameroom"
        self.modal = None
        self.gr_sel = "wheel" if wh.can_spin(self.tavern) else "roulette"
        self.gr_target = 0.0 if self.gr_sel == "wheel" else 220.0
        self.gr_scroll = self.gr_target

    def gr_max(self):
        return GR_H - GR_VIEW.h

    def gr_scroll_by(self, dy):
        self.gr_target = max(0.0, min(self.gr_max(), self.gr_target + dy))

    def gr_wheel(self, e):
        if self.view == "gameroom" and self.modal is None:
            self.gr_scroll_by(-getattr(e, "y", 0) * 110)

    def gr_drag(self, pos):
        if self.view != "gameroom" or self.modal is not None:
            return
        if self.gr_drag_last is None:
            if GR_VIEW.collidepoint(pos):
                self.gr_drag_last = pos
            return
        dy = pos[1] - self.gr_drag_last[1]
        self.gr_drag_last = pos
        self.gr_target = max(0.0, min(self.gr_max(), self.gr_target - dy))
        self.gr_scroll = self.gr_target

    def gameroom_tick(self, dt):
        m = max(0.0, self.gr_max())               # 3.45.4: карта могла смениться (своя — без прокрутки)
        self.gr_target = max(0.0, min(m, self.gr_target))
        self.gr_scroll = max(0.0, min(m, self.gr_scroll))
        self.gr_scroll += (self.gr_target - self.gr_scroll) * min(1.0, dt * 10)
        sp = self.fw_spin
        if sp is None:
            return
        u = min(1.0, (self.t_real - sp["t"]) / WHEEL_SPIN)
        e = 1 - (1 - u) ** 3                       # замедляется к концу
        self.fw_angle = sp["a0"] + (sp["a1"] - sp["a0"]) * e
        passed = int((self.fw_angle - sp["a0"]) / (2 * math.pi / len(wh.SEGMENTS)))
        if passed > self.fw_ticks:
            self.fw_ticks = passed
            self.sfx.play("hover")                 # щелчок о стрелку
        if u >= 1.0 or self.modal != "fortune":     # закрыли окно посреди вращения — сразу итог
            self.fw_finish()

    # ------------------------------------------------------------ игры
    def gr_open_game(self, gid):
        self.gr_sel = gid
        node = next(n for n in GAME_NODES if n["id"] == gid)
        if gid == "wheel":
            self.open_modal("fortune")
        elif gid == "roulette":
            self.open_casino()
        elif gid == "blackjack":
            self.open_blackjack()
        elif gid == "snails":
            self.open_snails()
        elif gid == "dice":
            self.open_dice()
        elif node.get("soon"):
            self.toast(f"{node['name']} откроется скоро. {node['text']}" if gid != "secret" else node["text"], 3)
            self.sfx.play("hover")

    def fw_start(self):
        if self.fw_spin is not None:
            return
        got = wh.spin(self.tavern)
        if got is None:
            self.toast(f"Колесо уже крутили сегодня. Снова — через {fmt_time(wh.seconds_to_next())}", 2.5)
            return
        idx, reward = got
        self.quest("wheel_spin")                     # 3.34: для достижений
        if reward.get("jackpot") or reward["kind"] == "prize":
            self.quest("wheel_jackpot")
        n = len(wh.SEGMENTS)
        step = 2 * math.pi / n
        # сектор idx встаёт под стрелку сверху, когда поворот колеса = -idx*step (по модулю оборота);
        # крутим по часовой: 5 полных оборотов + остаток до нужного сектора, чуть в сторону от середины сектора
        target = -idx * step + random.uniform(-0.32, 0.32) * step
        a0 = self.fw_angle
        a1 = a0 + 2 * math.pi * 5 + (target - a0) % (2 * math.pi)
        self.fw_spin = dict(t=self.t_real, a0=a0, a1=a1, idx=idx, reward=reward)
        self.fw_ticks = 0
        self.fw_msg = None
        self.save()                                # награда уже начислена — сохраняем сразу

    def fw_finish(self):
        sp, self.fw_spin = self.fw_spin, None
        if sp is None:
            return
        self.fw_angle = sp["a1"] % (2 * math.pi)
        r = sp["reward"]
        jack = r.get("jackpot") or r["kind"] == "prize"
        self.fw_msg = (r["text"], (255, 220, 90) if jack else (WHITE if r["amount"] else (220, 200, 190)))
        if r["kind"] == "prize":
            self.sfx.play("fanfare")
        elif r["amount"]:
            self.sfx.play("coin_big" if jack or r["amount"] >= 20 else "coin")
        if self.modal == "fortune":
            pr = self.panel_rect or pygame.Rect(W // 2 - 1, H // 2 - 1, 2, 2)
            if r["amount"] or r["kind"] == "prize":
                self.fx.sparks(pr.centerx, pr.y + 250, n=26 if jack else 12, up=90)
        if self.view != "gameroom" or self.modal != "fortune":
            self.toast(f"Колесо фортуны: {r['text']}", 3)

    # ------------------------------------------------------------ рисование
    def gr_node_xy(self, node):
        x, y = node["pos"]
        return GR_VIEW.x + x, GR_VIEW.y + y - self.gr_scroll

    def draw_gameroom_view(self):
        s = self.screen
        if self.cs_bg is None:
            self.cs_bg = self.build_casino_background()
        s.blit(self.cs_bg, (0, 0))
        shade = hd.Surface((W, H), pygame.SRCALPHA)
        shade.fill((20, 10, 12, 150))
        s.blit(shade, (0, 0))
        if self.gr_bg is None:
            self.gr_bg = build_gameroom_map()
        bg, painted = self.gr_bg
        rounded(s, (90, 55, 30), GR_VIEW.inflate(16, 16), 14, 3, skin=None)
        s.blit(bg, GR_VIEW.topleft, pygame.Rect(0, int(round(self.gr_scroll)), GR_VIEW.w, GR_VIEW.h))
        if not painted:
            self.gr_draw_path(s)
        t = self.t_real
        can = wh.can_spin(self.tavern)
        for node in GAME_NODES:
            x, y = self.gr_node_xy(node)
            if y < GR_VIEW.y - 120 or y > GR_VIEW.bottom + 120:
                continue
            self.gr_draw_node(s, node, x, y, t, can)
        # всё, что вылезло за край карты, закрываем полосами фона (обрезка по окну есть не везде)
        for band in (pygame.Rect(GR_VIEW.x - 8, 0, GR_VIEW.w + 16, GR_VIEW.y - 8),
                     pygame.Rect(GR_VIEW.x - 8, GR_VIEW.bottom + 8, GR_VIEW.w + 16, H - GR_VIEW.bottom - 8)):
            if band.h > 0:
                s.blit(self.cs_bg, band.topleft, band)
                s.blit(shade, band.topleft, pygame.Rect(0, 0, band.w, band.h))
        frame = GR_VIEW.inflate(16, 16)
        for edge in (pygame.Rect(frame.x, frame.y, frame.w, 8), pygame.Rect(frame.x, GR_VIEW.bottom, frame.w, 8)):
            rounded(s, (90, 55, 30), edge, 3, 0, skin=None)
        pygame.draw.rect(s, OUT, frame, 3, border_radius=14)
        for edge, down in ((GR_VIEW.y, True), (GR_VIEW.bottom - 30, False)):     # тень сверху/снизу
            fade = hd.Surface((GR_VIEW.w, 30), pygame.SRCALPHA)
            for i in range(30):
                a = int(140 * ((30 - i) / 30 if down else i / 30))
                pygame.draw.line(fade, (20, 8, 10, a), (0, i), (GR_VIEW.w, i))
            s.blit(fade, (GR_VIEW.x, edge))
        # стрелки листания
        if self.gr_target > 1:
            self.button((GR_VIEW.centerx - 24, GR_VIEW.y + 4, 48, 30), "^", lambda: self.gr_scroll_by(-280), BTN_BLUE,
                        True, 16)
        if self.gr_target < self.gr_max() - 1:
            self.button((GR_VIEW.centerx - 24, GR_VIEW.bottom - 34, 48, 30), "v", lambda: self.gr_scroll_by(280),
                        BTN_BLUE, True, 16)
        # заголовок
        if has_sprite("ui/banner"):
            self.draw_banner((GR_VIEW.centerx - 150, 8, 300, 52), "ИГРОВАЯ", 26)
        else:
            plate = pygame.Rect(GR_VIEW.centerx - 130, 10, 260, 46)
            rounded(s, (120, 70, 40), plate, 10, 3)
            draw_text(s, "ИГРОВАЯ", 26, plate.center, GOLD)
        self.gr_draw_side(s, can)

    def gr_draw_path(self, s):
        """Золотая дорожка от игры к игре (только на карте кодом — на своей картинке она нарисована)."""
        pts = [self.gr_node_xy(n) for n in GAME_NODES]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            for i in range(1, 24):
                u = i / 24
                mx = x0 + (x1 - x0) * u + math.sin(u * math.pi) * 60 * (1 if x1 < x0 else -1)
                my = y0 + (y1 - y0) * u
                if i % 2:
                    pygame.draw.circle(s, (120, 80, 30), (P(mx), P(my + 2)), 6)
                    pygame.draw.circle(s, (235, 190, 90), (P(mx), P(my)), 5)

    def gr_draw_node(self, s, node, x, y, t, can):
        gid = node["id"]
        locked = game_locked(node, self.farm.farm_index)
        soon = node.get("soon") or locked
        hover = math.hypot(self.mouse[0] - x, self.mouse[1] - y) < GR_NODE_R + 6 and GR_VIEW.collidepoint(self.mouse)
        draw_shadow(s, x, y + GR_NODE_R + 6, GR_NODE_R * 1.7, 18, 70)
        glow = gid == "wheel" and can
        if glow:
            blit_light(s, x, y, GR_NODE_R * 3.4 * (1 + 0.05 * math.sin(t * 3)), (255, 210, 110), 170, 0.0)
        if self.gr_sel == gid or hover:
            pygame.draw.circle(s, WHITE, (P(x), P(y)), GR_NODE_R + 11)
        ring = (150, 140, 130) if soon else ((250, 200, 70) if glow else (200, 160, 90))
        pygame.draw.circle(s, OUT, (P(x), P(y)), GR_NODE_R + 7)
        pygame.draw.circle(s, ring, (P(x), P(y)), GR_NODE_R + 5)
        pygame.draw.circle(s, (60, 30, 30) if not soon else (70, 60, 65), (P(x), P(y)), GR_NODE_R)
        k = GR_NODE_R / 62
        draw_game_icon(s, gid, x, y, k, t)
        if soon:
            dark = hd.Surface((GR_NODE_R * 2, GR_NODE_R * 2), pygame.SRCALPHA)
            dark.fill((0, 0, 0, 0))
            pygame.draw.circle(dark, (30, 25, 30, 130), (GR_NODE_R, GR_NODE_R), GR_NODE_R)
            s.blit(dark, (P(x - GR_NODE_R), P(y - GR_NODE_R)))
            if gid != "secret":
                draw_lock(s, x, y + 8 * k, 1.3 * k)
        img_t = render_text(node["name"], 16 if k > 0.9 else 13, WHITE, OUT)
        plate = pygame.Rect(0, 0, img_t.get_width() + (34 if k > 0.9 else 20), 32 if k > 0.9 else 24)
        plate.midtop = (P(x), P(y + GR_NODE_R + 6))
        if not skin.plate(s, "pill", plate):
            rounded(s, PILL, plate, 15, 3)
        s.blit(img_t, img_t.get_rect(center=plate.center))
        tag, col = None, None
        if gid == "wheel":
            tag, col = ("КРУТИ!", (90, 170, 80)) if can else ("ЗАВТРА", (140, 130, 125))
        elif locked:
            tag, col = UNLOCK_TAG.get(node["unlock"], "СКОРО"), (90, 150, 210)
        elif soon:
            tag, col = ("СКОРО", (235, 150, 60)) if gid != "secret" else (None, None)
        if tag:
            img_g = render_text(tag, 12, WHITE, OUT)
            badge = pygame.Rect(0, 0, img_g.get_width() + 18, 22)
            badge.center = (P(x), P(y - GR_NODE_R - 4))
            rounded(s, col, badge, 11, 2, skin=None)
            s.blit(img_g, img_g.get_rect(center=badge.center))
        hit = pygame.Rect(0, 0, GR_NODE_R * 2 + 10, GR_NODE_R * 2 + 44).move(P(x - GR_NODE_R - 5), P(y - GR_NODE_R - 5))
        if self.modal is None and hit.clip(GR_VIEW).w > 0:
            self.zone(hit.clip(GR_VIEW), lambda gid=gid: self.gr_open_game(gid))
            self.tip(hit.clip(GR_VIEW), node["text"])

    def gr_draw_side(self, s, can):
        """Справа: жетоны, выбранная игра, джекпот недели."""
        box = pygame.Rect(GR_VIEW.right + 22, 120, W - GR_VIEW.right - 36, 300)
        rounded(s, (238, 222, 192), box, 12, 3, skin="card")
        brown, soft = (90, 70, 60), (140, 110, 95)
        node = next(n for n in GAME_NODES if n["id"] == self.gr_sel)
        draw_text_fit(s, node["name"], 18, (box.centerx, box.y + 24), box.w - 20, brown, outline=None)
        for n, line in enumerate(wrap(node["text"], 13, box.w - 24, 4)):
            draw_text(s, line, 13, (box.centerx, box.y + 52 + n * 18), soft, outline=None)
        jp = wh.jackpot_for()
        y = box.y + 140
        draw_text(s, "Джекпот недели", 15, (box.centerx, y), (190, 120, 40), outline=None)
        for n, line in enumerate(wrap(jp["name"].capitalize(), 14, box.w - 24, 2)):
            draw_text(s, line, 14, (box.centerx, y + 24 + n * 18), brown, outline=None)
        y += 76
        if can:
            draw_text_fit(s, "Колесо можно крутить!", 14, (box.centerx, y), box.w - 16, (80, 150, 70), outline=None)
        else:
            draw_text(s, "Колесо — снова через", 13, (box.centerx, y), soft, outline=None)
            draw_text(s, fmt_time(wh.seconds_to_next()), 15, (box.centerx, y + 20), brown, outline=None)
        go = pygame.Rect(box.x + 14, box.bottom - 50, box.w - 28, 40)
        if game_locked(node, self.farm.farm_index):
            self.button(go, UNLOCK_BUTTON.get(node["unlock"], "Скоро"), lambda: None, BTN_GREY, False, 17)
        elif node.get("soon"):
            self.button(go, "Скоро", lambda: None, BTN_GREY, False, 17)
        else:
            self.button(go, "Играть!", lambda: self.gr_open_game(self.gr_sel), BTN_GREEN, True, 18)
        pb = pygame.Rect(14, 112, 170, 46)
        self.button(pb, "Призы", lambda: self.open_modal("prizes"), (245, 175, 50), True, 19)
        draw_token(s, pb.x + 28, pb.centery, 0.7)
        self.tip(pb, "Призовая стойка: трофеи и украшения за жетоны")

    def draw_fortune(self):
        """Окно колеса фортуны."""
        s = self.screen
        r = self.panel(560, 560, "КОЛЕСО ФОРТУНЫ")
        cx, cy, rad = r.centerx, r.y + 292, 148      # 3.28: ниже — стрелка не наезжает на строку джекпота
        blit_light(s, cx, cy, rad * 2.6, (255, 210, 120), 120, 0.0)
        draw_fortune_wheel(s, cx, cy, rad, self.fw_angle)
        # стрелка сверху: своя картинка props/fortune_pointer (остриём вниз) или кодом
        if not blit_sprite(s, "props/fortune_pointer", cx, cy - rad + 14, 1, "midbottom"):
            poly(s, (230, 60, 60), [(cx - 18, cy - rad - 26), (cx + 18, cy - rad - 26), (cx, cy - rad + 8)], 3)
            pygame.draw.circle(s, GOLD, (cx, cy - rad - 26), 6)
        jp = wh.jackpot_for()
        draw_text_fit(s, f"Джекпот этой недели: {jp['name']}", 15, (cx, r.y + 58), r.w - 60, (190, 120, 40),
                      outline=None)
        busy = self.fw_spin is not None
        can = wh.can_spin(self.tavern)
        bt = pygame.Rect(cx - 110, r.bottom - 70, 220, 50)
        if busy:
            self.button(bt, "Крутится...", lambda: None, BTN_GREY, False, 20)
        elif can:
            self.button(bt, "Крутить!", self.fw_start, BTN_GREEN, True, 22)
        else:
            self.button(bt, f"Завтра: {fmt_time(wh.seconds_to_next())}", lambda: None, BTN_GREY, False, 17)
        msg = self.fw_msg
        if msg is None and not busy and not can and self.tavern.wheel_last:
            msg = (f"Сегодня выпало: {self.tavern.wheel_last['text']}", (90, 70, 60))
        if msg and not busy:
            draw_text_fit(s, msg[0], 18, (cx, r.bottom - 88), r.w - 40, msg[1],
                          outline=OUT if msg[1] != (90, 70, 60) else None)
