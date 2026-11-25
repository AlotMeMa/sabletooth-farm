# -*- coding: utf-8 -*-
"""Кнопки таверны: жетоны, «На поле» / «В таверну», «Таверна» на поле, «Призы».

Примесь к App (3.17: вынесено из tavern_ui.py без изменений). Разметка и рисунки — tavern_art.
"""
from .tavern_art import *  # noqa: F401,F403


class TavernHudUI:
    def draw_tokens_pill(self, x, y, right=False):
        """Жетоны таверны. 3.20: в зале — слева, под плашками денег (справа закрывала гостя на балконе)."""
        s = self.screen
        img = render_text(str(self.tavern.tokens), 18, WHITE, OUT)
        w = 58 + img.get_width() + 14
        r = pygame.Rect(x - w if right else x, y, w, 40)
        from . import skin
        if not skin.plate(s, "pill", r):                          # 3.18: своя плашка ui/pill
            rounded(s, (235, 190, 130), r, 20, 3)
        draw_token(s, r.x + 22, r.centery, 0.95)
        s.blit(img, img.get_rect(midleft=(r.x + 44, r.centery)))
        return r

    def draw_tavern_back(self, label, cb, width=134, pos=(16, 560), h=56):
        if label == "На поле" and has_sprite("ui/btn_field"):
            self.icon_button(pygame.Rect(16, 560, 62, 56), "field", None, cb, label)
            return
        back = pygame.Rect(pos[0], pos[1], width, h)
        rounded(self.screen, BTN_GREEN, back, 10, 3)
        draw_text(self.screen, "<  " + label, 18, back.center)
        self.zone_btn(back, cb)

    def draw_tavern_button(self):
        """Кнопка «Таверна» на поле: слева, над «Магазином»."""
        if not self.tavern.unlocked:
            return
        r = pygame.Rect(16, 478, 62, 56)
        if not has_sprite("ui/btn_tavern") and has_sprite("ui/btn_shop"):
            # своих кнопок-картинок уже много, а этой нет — рисуем деревянную плашку в тон им, а не синюю
            s = self.screen
            hov = self.modal is None and r.collidepoint(self.mouse)
            rounded(s, (255, 240, 190) if hov else (120, 72, 40), r.inflate(6, 6), 12, 0)
            rounded(s, (176, 112, 62), r, 10, 3)
            rounded(s, (214, 160, 100), r.inflate(-10, -10), 7, 2, (150, 95, 55))
            draw_mug(s, r.centerx - 3, r.centery + 4, 1.2)
            draw_text(s, "Таверна", 12, (r.centerx, r.bottom + 12))
            if self.tavern.claimable():
                pygame.draw.circle(s, OUT, (r.right - 2, r.y + 2), 11)
                pygame.draw.circle(s, (240, 70, 70), (r.right - 2, r.y + 2), 9)
                draw_text(s, "!", 14, (r.right - 2, r.y + 2))
            self.zone_btn(r, self.open_tavern, glow="sprite")
            self.tip(r, TAVERN_TIP)
            return
        self.icon_button(pygame.Rect(16, 478, 62, 56), "tavern", lambda r: draw_mug(self.screen, r.centerx - 3, r.centery + 4, 1.2),
                         self.open_tavern, "Таверна", badge=bool(self.tavern.claimable()), tip=TAVERN_TIP)

    def draw_achievements_button(self):
        """3.34: «Достижения» в таверне — над «Призами». Своя картинка — ui/btn_achievements."""
        from . import achievements as ach
        from .achievements_ui import draw_medal
        r = pygame.Rect(16, 392, 62, 56)
        ready = bool(ach.claimable(self.tavern))
        done = len(self.tavern.ach_done)
        self.icon_button(r, "achievements", lambda rr: draw_medal(self.screen, rr.centerx, rr.centery, 2, True, 0.9),
                         self.open_achievements, "Достижения", badge=ready,
                         tip=f"Достижения: {done} из {len(ach.ACHIEVEMENTS)}" + (" — есть награда!" if ready else ""))

    def draw_prizes_button(self):
        """3.16.7: «Призы» прямо в таверне — над «На поле» (как «Таверна» над «Магазином» на поле).
        Своя картинка — ui/btn_prizes; без неё деревянная плашка с жетоном, в тон остальным кнопкам."""
        from .config import PRIZES as _P
        r = pygame.Rect(16, 478, 62, 56)
        t = self.tavern
        shop = [p for p in _P if t.prize_state(p) == "can" and not (p.get("jackpot") or p.get("achievement"))]
        cheapest = min(p["cost"] for p in shop) if shop else None     # 3.34: джекпоты и трофеи за достижения не в счёт
        badge = cheapest is not None and t.tokens >= cheapest
        tip = f"Призы за жетоны: трофеи и украшения (у тебя {t.tokens})"
        if not has_sprite("ui/btn_prizes") and has_sprite("ui/btn_shop"):
            s = self.screen
            hov = self.modal is None and r.collidepoint(self.mouse)
            rounded(s, (255, 240, 190) if hov else (120, 72, 40), r.inflate(6, 6), 12, 0)
            rounded(s, (176, 112, 62), r, 10, 3)
            rounded(s, (214, 160, 100), r.inflate(-10, -10), 7, 2, (150, 95, 55))
            draw_token(s, r.centerx, r.centery, 1.15)
            draw_text(s, "Призы", 12, (r.centerx, r.bottom + 12))
            if badge:
                pygame.draw.circle(s, OUT, (r.right - 2, r.y + 2), 11)
                pygame.draw.circle(s, (240, 70, 70), (r.right - 2, r.y + 2), 9)
                draw_text(s, "!", 14, (r.right - 2, r.y + 2))
            self.zone_btn(r, lambda: self.open_modal("prizes"), glow="sprite")
            self.tip(r, tip)
            return
        self.icon_button(r, "prizes", lambda rr: draw_token(self.screen, rr.centerx, rr.centery, 1.15),
                         lambda: self.open_modal("prizes"), "Призы", badge=badge, tip=tip)
