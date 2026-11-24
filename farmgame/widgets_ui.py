# -*- coding: utf-8 -*-
"""Общие детали интерфейса: кнопки, окна-панели, подсказки, сообщения, зоны клика.

Примесь к App (3.15: вынесено из app.py без изменений). Общие импорты и константы — ui_common.
"""
from .ui_common import *  # noqa: F401,F403


class WidgetsUI:
    # ------------------------------------------------------------ helpers
    def toast(self, text, life=3.0):
        self.toasts.append([text, life])
        self.toasts = self.toasts[-3:]

    def floater(self, x, y, text, color=GOLD):
        self.floaters.append([x, y, text, 1.2, color])
        if len(self.floaters) > 40:
            self.floaters.pop(0)

    def zone(self, rect, cb):
        """Кликабельное место (растение, белка, здание...). Без подсветки."""
        self.zones.append((pygame.Rect(rect), cb, None))

    def zone_btn(self, rect, cb, radius=10, glow="ring"):
        """Кнопка интерфейса: при наведении подсвечивается и тихо щёлкает.
        glow="ring" — светлая рамка вокруг; "sprite" — ореол по силуэту рисует сама кнопка."""
        self.zones.append((pygame.Rect(rect), cb, (glow, radius)))

    def icon_button(self, rect, name, fallback, cb, label=None, badge=False, active=False, tip=None):
        """Кнопка с картинкой. Есть assets/ui/btn_<name>.png — рисуется она (со светом сзади при наведении),
        нет — синяя плашка и значок, нарисованный кодом (fallback(rect)).
        Под курсором кнопка чуть приподнимается, при нажатии — проседает."""
        s = self.screen
        rect = pygame.Rect(rect)
        sprite_name = f"ui/btn_{name}"
        grow = self.btn_anim(rect, self.modal is None or name == "close" or self._in_modal)
        if has_sprite(sprite_name):
            scale = (rect.h + 10) / spritefit.BTN_CANVAS * (1 + 0.07 * grow)
            hovered = (self.modal is None or name == "close") and rect.collidepoint(self.mouse)
            if hovered or active:      # 3.4.1: свет «из-за кнопки» вместо обводки (и без тормозов)
                pulse = 0.0 if hovered else 0.06 * math.sin(self.t_real * 3)
                blit_backlight(s, rect.centerx, rect.centery, rect.h * ((2.15 if hovered else 1.9) + 0.1 * grow + pulse),
                               (255, 232, 140) if hovered else (255, 196, 70))
            blit_sprite(s, sprite_name, rect.centerx, rect.centery, scale, "center")
            self.zone_btn(rect, cb, glow="sprite")
        else:
            d = int(round(4 * grow))
            look = rect.inflate(d, d)
            rounded(s, (240, 180, 60) if active else BTN_BLUE, look, 10, 3)
            if fallback:
                fallback(rect)
            self.zone_btn(rect, cb)
        if tip:
            self.tip(rect, tip)
        if label:
            draw_text(s, label, 12, (rect.centerx, rect.bottom + 12))
        if badge:
            pygame.draw.circle(s, OUT, (rect.right - 2, rect.y + 2), 11)
            pygame.draw.circle(s, (240, 70, 70), (rect.right - 2, rect.y + 2), 9)
            draw_text(s, "!", 14, (rect.right - 2, rect.y + 2))

    def draw_toasts(self):
        # на поле — над дорогой; в сарае и мельнице — над карточками, чтобы не закрывать кнопки
        in_barn = self.view == "barn"
        toasts = list(reversed(self.toasts))[:2 if self.view != "field" else 3]
        for n, (text, life) in enumerate(toasts):
            img = render_text(text, 16, WHITE, OUT)
            if self.view in ("tavern", "board", "casino"):   # внизу: не мешают балкону, облачкам и запискам
                y = 602 - n * 38
            elif self.view == "fireside":                  # 3.19: у камина внизу кот и коврик — сообщения сверху
                y = 84 + n * 38
            elif in_barn:
                y = 126 - n * 38
            elif self.tut_visible():               # 3.9: над окошком бармена (в прокачке — наверху: внизу таблички)
                y = 100 + n * 40 if self.mode == "upgrade" else self.tut_box().y - 46 - n * 40   # выше таблички «Бармен»
            else:
                y = 512 - n * 40
            r = img.get_rect(center=(W // 2 + (40 if in_barn else 0), y))
            if not skin.plate(self.screen, "toast", r.inflate(34, 12)):   # 3.18: своя плашка ui/toast
                rounded(self.screen, (90, 70, 60), r.inflate(26, 12), 12, 3)
            self.screen.blit(img, r)

    # ------------------------------------------------------------ modals
    def panel(self, w, h, title):
        s = self.screen
        r = pygame.Rect(0, 0, w, h)
        r.center = (W // 2, H // 2)
        self.panel_rect = r
        skin.draw(s, "panel", r)                       # 3.4: деревянная рамка + пергамент
        tw = render_text(title, 24, WHITE, OUT).get_width()
        head = pygame.Rect(0, 0, min(r.w - 110, max(230, tw + 96)), 50)
        head.midtop = (r.centerx, r.y - 10)           # табличка висит на верхней доске рамки
        skin.draw(s, "panel_header", head)
        draw_text(s, title, 24, (head.centerx, head.centery - 2))
        x = pygame.Rect(r.right - 30, r.y - 14, 44, 44)
        self.icon_button(x, "close", lambda rr: draw_text(s, "X", 20, rr.center), self.close_modal)
        return r

    def close_modal(self):
        self.modal = None
        self.confirm_reset = False

    def button(self, rect, label, cb, color=BTN_GREEN, enabled=True, size=18):
        rect = pygame.Rect(rect)
        grow = self.btn_anim(rect, enabled and (self.modal is None or self._in_modal)) if enabled else 0.0
        look = rect.inflate(int(round(6 * grow)), int(round(4 * grow)))
        skin.draw(self.screen, skin.button_skin(color) if enabled else "button_grey", look)
        draw_text(self.screen, label, size, (rect.centerx, rect.centery - 1 + (1 if grow < 0 else 0)))
        if enabled:
            self.zone_btn(rect, cb)

    def btn_anim(self, rect, allowed=True):
        """Насколько кнопка «приподнята» (0..1) под курсором; -1 — только что нажата (проседает)."""
        key = tuple(rect)
        if key == self.press_key and self.t_real - self.press_t < 0.12:
            return -1.0
        target = 1.0 if allowed and rect.collidepoint(self.mouse) else 0.0
        v = anim.approach(self.btn_hover.get(key, 0.0), target, 18.0, self.frame_dt)
        if v < 0.01 and target == 0.0:
            self.btn_hover.pop(key, None)
            return 0.0
        self.btn_hover[key] = v
        return v

    def tip(self, rect, text):
        """Подсказка: появится, если задержать курсор на rect (если подсказки включены в настройках)."""
        self.tips.append((pygame.Rect(rect), text))

    def draw_banner(self, plate, text, size=22, color=(90, 70, 60)):
        """3.20: заголовок на ленте ui/banner (лента шире plate: концы-«хвосты» по бокам). У картинки-ленты
        полоса под надпись — верхние две трети (хвосты свисают ниже), поэтому текст выше середины и не шире
        полосы. Без картинки — плашка кодом. Возвращает прямоугольник ленты (или плашки)."""
        s = self.screen
        plate = pygame.Rect(plate)
        ribbon = plate.inflate(60, 8)
        if skin.plate(s, "banner", ribbon):
            draw_text_fit(s, text, size, (ribbon.centerx, ribbon.y + ribbon.h * 0.36), ribbon.w * 0.66, color,
                          outline=None)
            return ribbon
        rounded(s, PANEL, plate, 8, 3)
        draw_text_fit(s, text, size, plate.center, plate.w - 16, color, outline=None)
        return plate

    def draw_shade(self, alpha):
        """Затемнение под окном. Во время анимации — отдельный слой своей прозрачности: само затемнение
        не трогаем (set_alpha(None) у полупрозрачной картинки в pygame делает её сплошной — был синий фон)."""
        if alpha >= 1:
            self.screen.blit(self.shade, (0, 0))
            return
        if alpha <= 0.01:
            return
        if getattr(self, "shade_fade", None) is None:
            self.shade_fade = hd.Surface((W, H), pygame.SRCALPHA)
        self.shade_fade.fill((20, 20, 40, int(140 * alpha)))
        self.screen.blit(self.shade_fade, (0, 0))

    def draw_hover(self):
        """Подсветка кнопки под курсором + тихий звук при наведении на новую кнопку."""
        hovered = None
        for rect, _cb, btn in reversed(self.zones):
            if rect.collidepoint(self.mouse):
                hovered = (rect, btn) if btn else None
                break
        key = tuple(hovered[0]) if hovered else None
        if key != self.hover_key:
            self.hover_key = key
            if key is not None:
                self.sfx.play("hover")
        if hovered and hovered[1][0] == "ring":
            draw_hover_ring(self.screen, hovered[0], hovered[1][1])

    def draw_tip(self):
        """Подсказка у кнопки под курсором: появляется через полсекунды, мягко проявляется."""
        tip = None
        if self.show_tips and self.modal is None:
            for rect, text in reversed(self.tips):
                if rect.collidepoint(self.mouse):
                    tip = (tuple(rect), text)
                    break
        if tip is None or tip[0] != self.tip_key:
            self.tip_key = tip[0] if tip else None
            self.tip_t0 = self.t_real
        if tip is None:
            return
        k = (self.t_real - self.tip_t0 - TIP_DELAY) / 0.18
        if k <= 0:
            return
        img = render_text(tip[1], 14, WHITE, None)
        box = img.get_rect().inflate(20, 12)
        mx, my = self.mouse
        box.midbottom = (mx, my - 14)
        if box.y < 4:                                   # у верхнего края — под курсором
            box.midtop = (mx, my + 26)
        box.x = max(6, min(W - 6 - box.w, box.x))
        plate = hd.Surface((box.w + 6, box.h + 6), pygame.SRCALPHA)
        plate.fill((0, 0, 0, 0))
        rounded(plate, (78, 60, 52), pygame.Rect(0, 0, box.w, box.h), 9, 2, (40, 30, 28))
        plate.blit(img, img.get_rect(center=(box.w // 2, box.h // 2)))
        hd.real(plate).set_alpha(int(240 * anim.ease_out_cubic(k)))
        self.screen.blit(plate, box.topleft)
