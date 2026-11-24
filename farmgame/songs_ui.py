# -*- coding: utf-8 -*-
"""Заказ песни у барда и плашки бафов (песня, доход x2).

Примесь к App (3.17: вынесено из tavern_ui.py без изменений). Разметка и рисунки — tavern_art.
"""
from .tavern_art import *  # noqa: F401,F403
from . import skin


class SongsUI:
    # ---------- заказ песни (3.8) ----------
    def open_songs(self):
        self.modal = "songs"

    def song_def(self, sid=None):
        sid = self.farm.song if sid is None else sid
        return next((sg for sg in SONGS if sg["id"] == sid), None)

    def do_order_song(self, sid):
        ok, why = tv.order_song(self.tavern, self.farm, sid)
        if not ok:
            self.toast(why, 2.5)
            return
        sg = self.song_def(sid)
        self.modal = None
        self.sfx.play("fanfare")
        self.toast(f"Бард играет «{sg['name']}»: {sg['effect']} на {sg['minutes']} мин", 4)
        if self.view == "tavern":
            self.poke_bard()
            d = self.tl["bard"]
            self.tv_bubble = [d["x"], d["y"] - 135 * d["k"], sg["line"], 4.0]

    def listen_bard(self):
        self.modal = None
        self.poke_bard()

    def draw_songs(self):
        """Окно заказа песни: три песни с эффектом и ценой в жетонах."""
        s, f, t = self.screen, self.farm, self.tavern
        r = self.panel(600, 430, "ЗАКАЗАТЬ ПЕСНЮ")
        playing = self.song_def() if f.song_left > 0 else None
        if playing:
            m, sec = int(f.song_left // 60), int(f.song_left % 60)
            draw_text_fit(s, f"Сейчас играет «{playing['name']}» — ещё {m}:{sec:02d}", 16, (r.centerx, r.y + 58),
                          r.w - 60, (60, 130, 50), outline=None)
        else:
            draw_text(s, f"У тебя жетонов: {t.tokens}. Песня действует, пока играет", 15, (r.centerx, r.y + 58), SOFT,
                      outline=None)
        for n, sg in enumerate(SONGS):
            card = pygame.Rect(r.x + 34, r.y + 84 + n * 86, r.w - 68, 76)
            rounded(s, (238, 222, 192), card, 10, 2, skin="card")
            for i in range(2):                     # ноты слева
                draw_note_icon(s, card.x + 20 + i * 14, card.centery + 8 - i * 10, (n + i) % len(NOTE_COLORS))
            draw_text_fit(s, sg["name"], 17, (card.x + 62, card.y + 22), card.w - 240, BROWN, anchor="midleft", outline=None)
            draw_text_fit(s, f"{sg['effect']}, {sg['minutes']} мин", 13, (card.x + 62, card.y + 50), card.w - 240,
                          (60, 130, 50), anchor="midleft", outline=None)
            bt = pygame.Rect(card.right - 160, card.y + 16, 146, 44)
            can = playing is None and t.tokens >= sg["cost"]
            self.button(bt, f"{sg['cost']}", lambda sid=sg["id"]: self.do_order_song(sid), BTN_GREEN, can, 18)
            draw_token(s, bt.x + 36, bt.centery, 0.75)
            if playing is not None and playing["id"] == sg["id"]:
                draw_text(s, "играет", 13, (bt.centerx, bt.bottom + 8), (60, 130, 50), outline=None)
            elif not can:
                self.tip(bt, "Бард ещё играет прошлый заказ" if playing else f"Нужно жетонов: {sg['cost']}")
        self.button((r.centerx - 120, r.bottom - 66, 240, 42), "Просто послушать", self.listen_bard, BTN_BLUE, True, 16)

    def draw_song_pill(self, y, right=None, center=None):
        """Плашка «♪ песня  12:34», пока играет заказанная песня. right — правый край (плашка справа)."""
        f, s = self.farm, self.screen
        sg = self.song_def() if f.song_left > 0 else None
        if sg is None:
            return 0
        m, sec = int(f.song_left // 60), int(f.song_left % 60)
        img = render_text(f"{sg['name']}   {m}:{sec:02d}", 14, WHITE, OUT)
        r = pygame.Rect(14, y, 50 + img.get_width() + 14, 30)
        if right is not None:
            r.right = right
        if center is not None:
            r.centerx = center
        if not skin.plate(s, "pill", r):                          # 3.18: своя плашка ui/pill
            rounded(s, (170, 140, 220), r, 15, 3)
        draw_note_icon(s, r.x + 22, r.centery + 6, 0, 0.7)
        s.blit(img, img.get_rect(midleft=(r.x + 46, r.centery)))
        self.tip(r, f"Песня барда: {sg['effect']}")
        return 36

    def draw_boost_pill(self, y, right=None, center=None):
        f, s = self.farm, self.screen
        if f.boost_left <= 0:
            return 0
        m, sec = int(f.boost_left // 60), int(f.boost_left % 60)
        img = render_text(f"доход x2   {m}:{sec:02d}", 15, WHITE, OUT)
        r = pygame.Rect(14, y, 58 + img.get_width() + 14, 32)
        if right is not None:
            r.right = right
        if center is not None:
            r.centerx = center
        if not skin.plate(s, "pill", r):                          # 3.18: своя плашка ui/pill
            rounded(s, (250, 200, 90), r, 16, 3)
        draw_text(s, "x2", 15, (r.x + 30, r.centery), WHITE)
        s.blit(img, img.get_rect(midleft=(r.x + 54, r.centery)))
        return 38
