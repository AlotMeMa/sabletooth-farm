# -*- coding: utf-8 -*-
"""3.34: окно «Достижения» и проверка достижений. Открывается из «Настроек» (вкладка «Игра») и из таверны
(кнопка над «Призами»). Выполненное достижение — тост сразу; жетоны забираются кнопкой «Забрать»."""
import math

import pygame

from .ui_common import *  # noqa: F401,F403
from .tavern_ui import draw_token
from . import achievements as ach

MEDALS = ((205, 127, 50), (200, 205, 215), (245, 200, 60))     # бронза, серебро, золото — по награде


def draw_medal(s, x, y, tier, done=True, k=1.0):
    """Медаль на ленточке: tier 0..2; не выполнено — серая."""
    col = MEDALS[tier] if done else (185, 178, 170)
    for dx, rib in ((-6, (200, 70, 60)), (6, (70, 120, 200))):
        poly(s, rib if done else (165, 160, 155), [(x + dx * k - 5 * k, y - 22 * k), (x + dx * k + 5 * k, y - 22 * k),
                                                  (x + dx * k * 0.3 + 4 * k, y - 6 * k), (x + dx * k * 0.3 - 4 * k, y - 6 * k)], 2)
    pygame.draw.circle(s, OUT, (int(x), int(y + 4 * k)), int(14 * k) + 2)
    pygame.draw.circle(s, col, (int(x), int(y + 4 * k)), int(14 * k))
    pygame.draw.circle(s, tuple(max(0, c - 40) for c in col), (int(x), int(y + 4 * k)), int(9 * k), max(1, int(2 * k)))
    if done:
        poly(s, WHITE, [(x - 4 * k, y + 1 * k), (x - 1 * k, y + 6 * k), (x + 6 * k, y - 3 * k)], 0)


def medal_tier(a):
    return 2 if a["tokens"] >= 40 or a["prize"] else (1 if a["tokens"] >= 20 else 0)


class AchievementsUI:
    ACH_PER_PAGE = 5

    def ach_tick(self, dt):
        """Проверка раз в секунду: новые достижения — тост и звук."""
        self.ach_t = getattr(self, "ach_t", 0.0) - dt
        if self.ach_t > 0:
            return
        self.ach_t = 1.0
        for a in ach.check(self.farm, self.tavern):
            self.sfx.play("fanfare" if a["prize"] else "levelup")
            extra = ""
            if a["prize"]:
                p = next((p for p in PRIZES if p["id"] == a["prize"]), None)
                extra = f" Трофей «{p['name']}» — на камине!" if p else ""
            self.toast(f"Достижение: «{a['title']}»!{extra} Жетоны — в «Достижениях»", 5)
            self.save()

    def open_achievements(self):
        self.open_modal("achievements")

    def draw_achievements(self):
        s, t = self.screen, self.tavern
        brown, soft = (90, 70, 60), (140, 110, 95)
        r = self.panel(720, 520, "ДОСТИЖЕНИЯ")
        done, total = len([a for a in t.ach_done if a in ach.BY_ID]), len(ach.ACHIEVEMENTS)
        draw_text(s, f"Получено: {done} из {total}   ·   жетонов: {t.tokens}", 15, (r.centerx, r.y + 56), brown,
                  outline=None)
        sec = getattr(self, "ach_sec", ach.SECTIONS[0][0])
        tw = (r.w - 60 - 8 * (len(ach.SECTIONS) - 1)) // len(ach.SECTIONS)
        for i, (key, title) in enumerate(ach.SECTIONS):
            ready = any(ach.BY_ID[aid]["sec"] == key for aid in ach.claimable(t))
            b = pygame.Rect(r.x + 30 + i * (tw + 8), r.y + 74, tw, 38)
            self.button(b, title, lambda k=key: self.ach_set_section(k), (245, 175, 50) if sec == key else BTN_BLUE,
                        True, 16)
            if ready:
                pygame.draw.circle(s, OUT, (b.right - 4, b.y + 4), 10)
                pygame.draw.circle(s, (240, 70, 70), (b.right - 4, b.y + 4), 8)
                draw_text(s, "!", 12, (b.right - 4, b.y + 4))
        items = [a for a in ach.ACHIEVEMENTS if a["sec"] == sec]
        # сначала — что можно забрать, потом невыполненные (ближе к цели — выше), в конце — забранные
        def order(a):
            if a["id"] in t.ach_done and a["id"] not in t.ach_claimed:
                return (0, 0)
            if a["id"] not in t.ach_done:
                return (1, -min(1.0, ach.value(a, self.farm, t) / a["target"]))
            return (2, 0)
        items.sort(key=order)
        per = self.ACH_PER_PAGE
        pages = max(1, (len(items) + per - 1) // per)
        page = min(getattr(self, "ach_page", 0), pages - 1)
        self.ach_page = page
        for n, a in enumerate(items[page * per:(page + 1) * per]):
            row = pygame.Rect(r.x + 30, r.y + 122 + n * 64, r.w - 60, 58)
            is_done, claimed = a["id"] in t.ach_done, a["id"] in t.ach_claimed
            rounded(s, (238, 222, 192) if is_done else (226, 214, 196), row, 10, 2, skin="card")
            draw_medal(s, row.x + 32, row.centery + 2, medal_tier(a), is_done, 0.95)
            draw_text_fit(s, a["title"], 17, (row.x + 62, row.y + 18), row.w - 280, brown, anchor="midleft", outline=None)
            draw_text_fit(s, a["text"], 13, (row.x + 62, row.y + 39), row.w - 280,
                          (60, 130, 50) if is_done else soft, anchor="midleft", outline=None)
            bt = pygame.Rect(row.right - 196, row.y + 10, 184, 38)
            if is_done and not claimed:
                self.button(bt, f"Забрать {a['tokens']}", lambda aid=a["id"]: self.ach_claim(aid), BTN_GREEN, True, 16)
                draw_token(s, bt.right - 22, bt.centery, 0.6)
            elif claimed:
                from .skin import draw_max
                draw_max(s, bt, 14, "Получено")
            else:
                v = ach.value(a, self.farm, t)
                bar = pygame.Rect(bt.x, bt.y + 6, bt.w, 16)
                draw_bar(s, bar, min(1.0, v / a["target"]), (120, 190, 90))
                shown = fmt(v) if a["stat"] == "earned" else (str(int(v)) if a["target"] > 1 else "")
                goal = ("$" + fmt(a["target"])) if a["stat"] == "earned" else fmt(a["target"])
                draw_text(s, f"{'$' if a['stat'] == 'earned' else ''}{shown} / {goal}" if a["target"] > 1 else "ещё нет",
                          11, bar.center)
                reward = f"{a['tokens']} жет." + (" + трофей" if a["prize"] else "")
                draw_text(s, reward, 12, (bt.centerx, bt.bottom + 2), soft, outline=None)
        if ach.claimable(t):
            self.button((r.x + 30, r.bottom - 66, 200, 40), "Забрать всё", self.ach_claim_all, BTN_GREEN, True, 17)
        if pages > 1:
            draw_text(s, f"{page + 1} / {pages}", 15, (r.centerx, r.bottom - 46), brown, outline=None)
            if page > 0:
                self.button((r.centerx - 92, r.bottom - 66, 40, 36), "<",
                            lambda: setattr(self, "ach_page", self.ach_page - 1), BTN_BLUE)
            if page < pages - 1:
                self.button((r.centerx + 52, r.bottom - 66, 40, 36), ">",
                            lambda: setattr(self, "ach_page", self.ach_page + 1), BTN_BLUE)

    def ach_set_section(self, key):
        self.ach_sec, self.ach_page = key, 0

    def ach_claim(self, aid):
        got = ach.claim(self.tavern, aid)
        if got:
            self.sfx.play("claim")
            self.toast(f"+{got} жетонов за «{ach.BY_ID[aid]['title']}»", 2.5)
            self.save()

    def ach_claim_all(self):
        got = ach.claim_all(self.tavern)
        if got:
            self.sfx.play("claim")
            self.toast(f"+{got} жетонов за достижения", 2.5)
            self.save()
