# -*- coding: utf-8 -*-
"""Окно, HD, полный экран без полос, курсор мыши.

Примесь к App (3.15: вынесено из app.py без изменений). Общие импорты и константы — ui_common.
"""
from .ui_common import *  # noqa: F401,F403


class ScreenUI:
    # ------------------------------------------------------------ окно и HD
    def open_window(self, forced=None):
        """Окно игры. Игра «думает» в координатах 1000x640, а рисует в k раз крупнее (HD, см. hd.py):
        k подбирается так, чтобы окно целиком влезло на экран. SCALED: картинка растягивается под окно
        и под весь экран (F11) с сохранением пропорций. RESIZABLE: окно можно тянуть мышкой."""
        if isinstance(forced, float):
            k = forced
        elif (forced or self.hd_mode) == "off":
            k = 1.0
        else:
            k = hd.choose_scale(W, H)
        hd.install(k)
        spritefit.FIT_SCALE[0] = k
        self.hd_k = k
        self.canvas = (int(round(W * k)), int(round(H * k)))
        try:
            real = pygame.display.set_mode(self.canvas, pygame.SCALED | pygame.RESIZABLE)
        except pygame.error as e:              # не дали окно такого размера — обычная чёткость
            print("HD-окно не открылось:", e)
            hd.install(1.0)
            spritefit.FIT_SCALE[0] = 1.0
            self.hd_k, self.canvas = 1.0, (W, H)
            real = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        self.screen = hd.HiSurf(real, self.hd_k, (W, H)) if self.hd_k != 1 else real
        print(f"Картинка {self.canvas[0]}×{self.canvas[1]} (чёткость x{self.hd_k:g})")

    def toggle_hd(self):
        """Чёткость меняется со следующего запуска: все картинки подгоняются под новый размер."""
        self.hd_mode = "off" if self.hd_mode == "auto" else "auto"
        self.save()
        self.toast("Чёткость поменяется после перезапуска игры", 4)

    def lpos(self, pos):
        """Координаты мыши из события — в координаты игры (1000x640): с учётом HD и полей полного экрана."""
        return hd.to_logical_pos(pos) if (self.hd_k != 1 or self.wide) else pos

    # ------------------------------------------------------------ курсор
    def load_cursors(self):
        """Свой курсор из assets/ui/cursor.png (и cursor_hover.png — над кнопками).
        Кончик стрелки = левый верхний угол картинки. Нет файла — обычный курсор Windows."""
        self.cursors = {}
        self.cursor_state = None
        for name in ("cursor", "cursor_hover"):
            img = sprite(f"ui/{name}")
            if img is None:
                continue
            try:
                # курсор рисует система, поверх окна: размер — как раньше, только на экранах 125%/150% крупнее
                cur = hd.to_logical(img)
                d = hd.dpi_scale() if self.hd_k != 1 else 1.0
                if d > 1.05:
                    cur = hd._orig.get("smoothscale", pygame.transform.smoothscale)(
                        hd.real(img), (int(round(cur.get_width() * d)), int(round(cur.get_height() * d))))
                self.cursors[name] = pygame.cursors.Cursor((0, 0), cur)
            except Exception as e:   # очень старый pygame или драйвер без цветных курсоров
                print(f"Не получилось поставить курсор ui/{name}: {e}")

    def update_cursor(self):
        if not self.cursors:
            return
        want = "cursor"
        if "cursor_hover" in self.cursors:
            pos = pygame.mouse.get_pos()
            if any(rect.collidepoint(pos) for rect, _cb, _b in self.zones):
                want = "cursor_hover"
        if want not in self.cursors:
            want = None
        if want == self.cursor_state:
            return
        self.cursor_state = want
        try:
            if want is None:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            else:
                pygame.mouse.set_cursor(self.cursors[want])
        except Exception as e:
            print("Курсор:", e)
            self.cursors = {}

    def toggle_fullscreen(self):
        # 3.16.8: F11 быстро несколько раз подряд — окно пересоздавалось, не успев встать, и SDL падал.
        # Между переключениями — не меньше 0.7 с (лишние нажатия просто пропускаются).
        now = time.time()
        if now - getattr(self, "_fs_toggled", 0.0) < 0.7:
            return
        self._fs_toggled = now
        try:
            if self.fullscreen and self.wide:
                self.leave_wide()
            elif not self.fullscreen and self.edge_fill and self.enter_wide():
                pass
            elif self.fullscreen:                # обычный полный экран (с полосами) — выходим через новое окно
                self.restore_window(fresh=True)
            else:
                pygame.display.toggle_fullscreen()
            self.fullscreen = not self.fullscreen
        except Exception as e:                 # любая ошибка окна — не закрывать игру, а вернуться в окно
            print("Переключение экрана:", e)
            self.safe_window()
            if not any(t[0].startswith("Не получилось переключить экран") for t in self.toasts):
                self.toast("Не получилось переключить экран — игра осталась в окне", 3)

    # ---------- 3.10: полный экран без чёрных полос ----------
    def set_canvas(self, real):
        """Игра рисует в real (окно или картинка-кадр в полном экране)."""
        self.screen = hd.HiSurf(real, self.hd_k, (W, H)) if self.hd_k != 1 else real

    def enter_wide(self):
        """Полный экран в пропорциях монитора: игра посередине, по краям — её размытое продолжение.
        False — не вышло или не нужно (пропорции совпадают): тогда обычный полный экран с полосами."""
        try:
            sizes = pygame.display.get_desktop_sizes()
            geo = screenfit.wide_geometry(self.canvas, sizes[0]) if sizes else None
        except Exception:
            geo = None
        if geo is None:
            return False
        (ww, wh), (ox, oy) = geo
        try:
            display = pygame.display.set_mode((ww, wh), pygame.SCALED | pygame.FULLSCREEN)
            frame = pygame.Surface(self.canvas).convert()
        except pygame.error as e:
            print("Полный экран с полями не открылся:", e)
            self.restore_window()
            return False
        self.wide = dict(display=display, frame=frame, offset=(ox, oy), size=(ww, wh), edges=None, t=-1.0,
                         win=None, check=self.t_real)
        self.set_canvas(frame)
        hd.set_offset(ox, oy)
        self.shade_fade = None
        return True

    @staticmethod
    def window_size():
        try:
            return tuple(pygame.display.get_window_size())
        except Exception:
            return None

    def restore_window(self, fresh=False):
        """Обычное окно. fresh=True — окно создаётся заново с нуля (выход из полного экрана, 3.26)."""
        if fresh:
            self.fresh_display()
        real = pygame.display.set_mode(self.canvas, pygame.SCALED | pygame.RESIZABLE)
        self.set_canvas(real)
        hd.set_offset(0, 0)
        self.wide = None

    def fresh_display(self):
        """3.26: выход из полного экрана давал чёрное окно — SDL оставлял «рисовальщик» полноэкранного размера,
        и кадры игры уходили мимо окна. Теперь окно закрывается и открывается заново: видеосистема SDL
        перезапускается, а картинки, звук и сохранение не трогаются (они живут отдельно от окна)."""
        try:
            pygame.display.quit()
            pygame.display.init()
        except pygame.error as e:
            print("Окно не перезапустилось:", e)
        try:
            pygame.display.set_caption(f"Весёлая ферма {GAME_VERSION}")
        except pygame.error:
            pass
        self.cursor_state = None              # свой курсор поставится заново на первом кадре
        self.was_minimized = False

    def leave_wide(self):
        self.restore_window(fresh=True)

    def on_window_event(self, e):
        """3.16.5: свернули полный экран (кнопкой, Alt+Tab, Win), а Windows вернул его обычным окном — пересоздаём.
        Только по настоящему «свернули» → «развернули» и только если размер окна правда стал другим.
        (В 3.16.4 срабатывало и на потерю фокуса: каждое пересоздание окна снова теряло фокус — окно пересоздавалось
        по кругу, пока Windows не отказал: «failed to create renderer».)"""
        mini = getattr(pygame, "WINDOWMINIMIZED", None)
        back = getattr(pygame, "WINDOWRESTORED", None)
        if mini is not None and e.type == mini:
            if self.wide:
                self.was_minimized = True
        elif back is not None and e.type == back:
            if self.wide and self.was_minimized:
                self.was_minimized = False
                now, was = self.window_size(), self.wide.get("win")
                if was and now and now != was and getattr(self, "_wide_refreshes", 0) < 3:
                    self.wide_refresh = True

    def refresh_wide(self):
        """Пересоздать полный экран после сворачивания (не вышло — спокойно вернуться в окно)."""
        self.wide_refresh = False
        if not self.wide:
            return
        self._wide_refreshes = getattr(self, "_wide_refreshes", 0) + 1
        try:
            self.restore_window()
            if not self.enter_wide():
                self.fullscreen = False
        except pygame.error as e:
            print("Полный экран после сворачивания:", e)
            self.safe_window()

    def safe_window(self):
        """Что-то пошло не так с полным экраном — вернуться в обычное окно (без сообщений по кругу)."""
        self.wide = None
        self.fullscreen = False
        hd.set_offset(0, 0)
        try:
            self.restore_window(fresh=True)
        except pygame.error as e:
            print("Окно не пересоздалось:", e)

    def set_edge_fill(self, on):
        """Переключить края полного экрана (размытый фон / чёрные полосы); в полном экране — сразу."""
        was_full = self.fullscreen
        if was_full:
            self.toggle_fullscreen()
        self.edge_fill = on
        if was_full:
            self.toggle_fullscreen()
        self.save()

    def build_edges(self):
        """Поля по краям: зеркальный край картинки, сильно размытый и чуть затемнённый."""
        wd, frame = self.wide, self.wide["frame"]
        (ww, wh), (ox, oy) = wd["size"], wd["offset"]
        cw, ch = frame.get_size()
        edges = []
        if ox > 0:     # полосы берутся вдвое шире поля и сжимаются: мелкие детали (плашки, кнопки) растворяются
            sw = min(cw // 3, ox * 2)
            parts = (((0, 0, sw, ch), (0, oy)), ((cw - sw, 0, sw, ch), (ox + cw, oy)))
            size = (ox, ch)
        else:
            sh = min(ch // 3, oy * 2)
            parts = (((0, 0, cw, sh), (ox, 0)), ((0, ch - sh, cw, sh), (ox, oy + ch)))
            size = (cw, oy)
        for rect, pos in parts:
            strip = frame.subsurface(pygame.Rect(rect))
            small = pygame.transform.smoothscale(strip, (max(2, size[0] // 24), max(2, size[1] // 24)))
            big = pygame.transform.smoothscale(small, size)
            big = pygame.transform.flip(big, ox > 0, oy > 0)        # зеркально: у края игры — тот же цвет
            shade = pygame.Surface(size, pygame.SRCALPHA)
            shade.fill((25, 18, 12, 110))
            big.blit(shade, (0, 0))
            edges.append((big, pos))
        wd["edges"] = edges

    def present_wide(self):
        """Собрать кадр полного экрана: поля (обновляются 5 раз в секунду) + картинка игры посередине."""
        wd = self.wide
        if wd is None:
            return
        if wd["win"] is None and self.t_real - wd["check"] >= 1.0:    # размер полного экрана — когда окно встало
            wd["win"] = self.window_size()
        if wd["edges"] is None or self.t_real - wd["t"] >= 0.2 or self.t_real < wd["t"]:
            wd["t"] = self.t_real
            try:
                self.build_edges()
            except Exception as e:          # поля — украшение: не вышло — просто тёмные края
                print("Края экрана:", e)
                wd["edges"] = []
        disp = wd["display"]
        if not wd["edges"]:
            disp.fill((20, 16, 12))
        for img, pos in wd["edges"]:
            disp.blit(img, pos)
        disp.blit(wd["frame"], wd["offset"])
