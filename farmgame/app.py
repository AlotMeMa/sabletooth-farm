# -*- coding: utf-8 -*-
"""Приложение: окно, ввод, экраны и окна интерфейса."""
import json
import math
import os
import random
import sys
import threading
import time

import pygame

from . import anim
from . import config as cfg
from . import hd
from . import savefile
from . import spritefit
from .config import *  # noqa: F401,F403
from .config import _rain_time, _rain_cd, _rain_speed  # noqa: F401
from .logic import Farm
from .audio import Music, Sfx
from .art import *  # noqa: F401,F403
from .tavern import Tavern
from .tavern_ui import TavernUI
from .mill_ui import MillUI
from .tutorial import Tutorial
from .tutorial_ui import TutorialUI
from .particles import Particles, draw_shadow
from . import skin


LOADING_SPRITES = ("backgrounds/loading", "ui/logo", "ui/loading_ring", "ui/loading_center")
HD_MODES = ("auto", "off")      # чёткость: HD под размер экрана / обычная 1000x640
FPS_LIMITS = (30, 60, 144)      # ограничение кадров в секунду («Настройки» → «Экран»)
MODAL_OPEN_TIME = 0.24          # окно выезжает с лёгкой пружинкой
MODAL_CLOSE_TIME = 0.14
TIP_DELAY = 0.45                # подсказка появляется, если задержать курсор на кнопке
SQUIRREL_HOP = {"run": (0.34, 16.0), "flee": (0.27, 13.0)}   # 3.3: белка скачет дугами — (период прыжка, высота)
DUST = (214, 196, 150)          # пыль на лугу
DIRT = (176, 128, 86)           # земля грядки
ROAD_DUST = (178, 150, 108)     # пыль на песчаной дороге (светлая на ней не видна)
COIN_SMALL = 0.7                # монетки-частицы (разбойник) — чуть меньше монеток урожая
FAST_GROW_CYCLE = 6.0           # грядка с работником растёт быстрее — показываем её всегда взрослой (без мелькания)


def hd_from_args():
    """Чёткость из командной строки (--hd=off, --hd=auto, --hd=1.5) или переменной FARM_HD. None — не задано."""
    val = os.environ.get("FARM_HD")
    for a in sys.argv[1:]:
        if a.startswith("--hd="):
            val = a[5:]
        elif a == "--no-hd":
            val = "off"
    if val is None:
        return None
    val = val.strip().lower()
    if val in HD_MODES:
        return val
    try:
        return max(1.0, min(3.0, float(val.replace(",", "."))))
    except ValueError:
        return None


def saved_hd_mode():
    """Настройка чёткости из сохранения: её надо знать ДО создания окна, поэтому читаем файл заранее."""
    for path in (cfg.SAVE_FILE, savefile.bak_path(cfg.SAVE_FILE)):
        data = savefile.load_json(path)
        if data is not None:
            opts = data.get("options")
            mode = opts.get("hd") if isinstance(opts, dict) else None
            return mode if mode in HD_MODES else "auto"
    return "auto"


# ======================================================================
#                              ПРИЛОЖЕНИЕ
# ======================================================================
class App(TavernUI, MillUI, TutorialUI):
    def __init__(self):
        # Растягивание 1000x640 на экран — со сглаживанием (linear), а не «лесенкой» (nearest).
        # Подсказка SDL должна стоять ДО создания окна. Уже заданную снаружи не трогаем.
        os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "1")
        forced = hd_from_args()
        self.hd_mode = forced if forced in HD_MODES else saved_hd_mode()
        if forced != "off" and (forced is not None or self.hd_mode != "off"):
            hd.make_dpi_aware()       # Windows 125%/150%: иначе система сама растянет окно — мыльно
        pygame.init()
        self.open_window(forced)
        self.fullscreen = False
        pygame.display.set_caption(f"Весёлая ферма {GAME_VERSION}")
        self.clock = pygame.time.Clock()
        self.farm = Farm()
        self.t = 0.0
        self.mode = "normal"          # normal | upgrade
        self.view = "field"           # field | barn | tavern | board
        self.buy_mode = 1             # 1 | 10 | "next" | "max"
        self.modal = None             # None | "shop" | "truck" | "settings" | "offline"
        self.offline_info = (0.0, 0.0)
        self.shop_tab = "fert"
        self.shop_page = 0
        self.zones = []
        self.floaters = []            # [x, y, text, life, color]
        self.toasts = []              # [text, life]
        self.drops = []
        self.truck_state = "away"     # away | arriving | parked | leaving
        self.truck_x = W + 230.0
        self.truck_v = 0.0            # 3.3: скорость (тормозит, подъезжая, и разгоняется, уезжая)
        self.truck_t = -99.0          # когда остановился / тронулся (для «покачивания на рессорах»)
        self.truck_dust = 0.0
        self.leaving_tier = 0
        self.squirrel = None          # dict(x, y, d, phase, timer, stop)
        self.squirrel_timer = self.squirrel_delay()
        self.crow = None              # dict(k, x, y, tx, ty, phase, timer, d)
        self.crow_timer = self.crow_delay()
        self.frost_timer = random.uniform(FROST_MIN, FROST_MAX)
        self.bandit = None            # dict(k, x, y, tx, ty, phase, timer, d, sack)
        self.bandit_timer = self.bandit_delay()
        self.move_notified = False
        self.time_scale = 1
        self.tree_sel = None
        self.confirm_reset = False
        self.autosave = 0.0
        self.rain_tint = hd.Surface((W, H), pygame.SRCALPHA)
        self.rain_tint.fill((60, 100, 160, 35))
        self.bless_tint = hd.Surface((W, H), pygame.SRCALPHA)
        self.bless_tint.fill((255, 220, 120, 30))
        self.shade = hd.Surface((W, H), pygame.SRCALPHA)
        self.shade.fill((20, 20, 40, 140))
        self.music = Music()
        self.sfx = Sfx(self.music)
        self.mouse = (0, 0)
        self.hover_key = None         # кнопка под курсором (чтобы щёлкнуть звуком один раз при наведении)
        self.trail = []               # шлейф за курсором: [(x, y, время)]
        self.t_start = time.time()
        self.t_real = 0.0             # настоящее время (шлейф не ускоряется в режиме разработчика)
        self.click_pos = (0, 0)
        self.volume_drag = None       # Rect ползунка громкости, пока его тянут мышкой
        # 3.1: плавность и эффекты (время — настоящее, не ускоряется в режиме разработчика)
        self.fx = Particles()
        self.money_shown = None       # деньги на плашке: догоняют настоящие плавно, монетки «долетают»
        self.money_pending = 0.0      # сколько денег ещё летит монетками в счётчик
        self.money_bump = 0.0         # монетка на плашке подпрыгивает, когда в неё что-то прилетело
        self.anim_t = None            # время прошлого кадра анимаций
        self.frame_dt = 0.0
        self._modal_seen = None       # какое окно было открыто в прошлом кадре (чтобы заметить открытие/закрытие)
        self.modal_t0 = -99.0
        self.modal_from_none = True
        self.closing = None           # (окно, время начала) — окно уезжает
        self._in_modal = False
        self.btn_hover = {}           # кнопка -> 0..1, насколько она «приподнята» под курсором
        self.press_key, self.press_t = None, -99.0
        self.tips, self.tip_key, self.tip_t0 = [], None, 0.0
        self.settings_tab = "sound"
        self.coin_born = [None] * N_CROPS   # 3.2: когда над грядкой появилась монетка (для «выпрыгивания»)
        self.fps_limit = FPS
        self.show_fps = False
        self.show_tips = True
        self.init_tavern()
        self.init_mill()
        self.init_tutorial()
        self.preload_sprites()        # картинки и синтез звуков — пока на экране заставка с крутящимся колесом
        self.load_cursors()
        self.bg = self.build_background()
        self.barn_bg = self.build_barn_background()
        self.mill_bg = self.build_mill_background()
        self.load()
        self.music.play_for(self.farm_info()["id"])
        self.report_assets()

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
        """Координаты мыши из события — в координаты игры (1000x640)."""
        return hd.to_logical_pos(pos) if self.hd_k != 1 else pos

    # ------------------------------------------------------------ загрузка картинок
    def preload_sprites(self):
        """Подгоняет все картинки из assets/ сразу при запуске, с заставкой и полоской.
        Иначе каждая картинка подгонялась бы при первом показе, и игра на миг замирала бы
        (например, когда белка выбегает в первый раз). Уже подогнанные берутся из .sprite_cache/ мгновенно."""
        from .templates import known_names
        self.load_t0 = time.time()
        self.draw_loading(0.0)                        # сразу что-то на экране, пока грузятся картинки заставки
        pygame.display.flip()
        early = LOADING_SPRITES + ("icons/peasant",)  # сама заставка (крестьянин — запасной талисман)
        for name in early:                            # грузим до потока: заставка и поток не трогают одно и то же
            sprite(name)
        names = [n for n in sorted(known_names()) if n not in early]
        total = len(names) + 1                        # +1 — синтез звуков
        state = {"done": 0, "finished": False}

        def work():
            try:
                for name in names:
                    sprite(name)                      # подгонка картинки (первый раз — долго, потом из кэша)
                    state["done"] += 1
                self.sfx.preload()                    # синтез звуков
            except Exception as e:                    # не роняем игру: недогруженное загрузится при первом показе
                print("Загрузка картинок/звуков:", e)
            finally:
                state["done"] = total
                state["finished"] = True

        # Картинки подгоняются в фоне, а экран перерисовывается 60 раз в секунду: колесо крутится плавно,
        # даже когда одна большая картинка подгоняется несколько секунд. Не вышло с потоком — грузим по очереди.
        try:
            worker = threading.Thread(target=work, daemon=True)
            worker.start()
        except Exception:
            worker = None
            work()
        clock = pygame.time.Clock()
        while worker is not None and not state["finished"]:
            pygame.event.pump()                       # чтобы Windows не считала окно зависшим
            self.draw_loading(state["done"] / total)
            pygame.display.flip()
            clock.tick(60)
        if worker is not None:
            worker.join(timeout=5)
        self.draw_loading(1.0)
        pygame.display.flip()

    def draw_loading(self, frac):
        draw_loading_screen(self.screen, frac, time.time() - getattr(self, "load_t0", time.time()),
                            "Весёлая ферма", "первый запуск после новых картинок дольше — потом мгновенно")

    # ------------------------------------------------------------ save
    def save(self):
        data = self.farm.to_dict()
        data["saved_at"] = time.time()
        data["version"] = SAVE_VERSION
        data["options"] = {"fullscreen": self.fullscreen, "music_volume": self.music.volume, "music_muted": self.music.muted,
                           "sfx_volume": self.sfx.volume, "hd": self.hd_mode, "fps_limit": self.fps_limit,
                           "show_fps": self.show_fps, "tips": self.show_tips}
        data["tavern"] = self.tavern.to_dict()
        data["tutorial"] = self.tut.to_dict()
        savefile.write(cfg.SAVE_FILE, data)     # через временный файл + запасная копия раз в 5 минут

    def apply_save(self, data):
        """Переносит прочитанное сохранение в игру. False — не получилось (игра остаётся «с чистого листа»)."""
        self.farm, self.tavern = Farm(), Tavern()
        try:
            self.farm.from_dict(data)
            self.tavern.from_dict(data.get("tavern"))
            self.tut = Tutorial.from_save(data.get("tutorial"))     # 3.9: старые сохранения — без обучения
            opts = data.get("options")
            opts = opts if isinstance(opts, dict) else {}

            def vol(key, cur):
                v = opts.get(key, cur)
                return max(0.0, min(1.0, float(v))) if isinstance(v, (int, float)) and v == v else cur
            if opts.get("fullscreen") and not self.fullscreen:
                self.toggle_fullscreen()
            self.music.volume = vol("music_volume", self.music.volume)
            self.music.muted = bool(opts.get("music_muted", False))
            self.sfx.volume = vol("sfx_volume", self.sfx.volume)
            self.fps_limit = opts.get("fps_limit") if opts.get("fps_limit") in FPS_LIMITS else FPS
            self.show_fps = bool(opts.get("show_fps", False))
            self.show_tips = bool(opts.get("tips", True))
            self.music.apply_volume()
            version = data.get("version", 1)
            if isinstance(version, (int, float)) and version < 2 and self.farm.farm_index >= 1:
                # старая версия: 2-я ферма была зимней. Теперь 2-я глава — средневековье, переезд «с нуля».
                f = self.farm
                f.farm_index, f.leaves, f.home_leaves, f.tree = 1, 0, 0, {}
                f.reset_run()
            return True
        except Exception as e:       # любое повреждение сохранения не должно ронять игру при запуске
            print("Сохранение не применилось:", repr(e))
            self.farm, self.tavern = Farm(), Tavern()
            return False

    def load(self):
        """Читает сохранение. Повреждённый файл не затирается: он откладывается рядом (farm_save.broken_...json),
        а игра берёт запасную копию farm_save.bak.json. Только если и её нет — начинает заново."""
        path = cfg.SAVE_FILE
        data, note, kept = savefile.read(path)
        if data is not None and not self.apply_save(data):
            kept = kept or savefile.keep_broken(path)
            bak = savefile.load_json(savefile.bak_path(path)) if note is None else None
            if bak is not None and self.apply_save(bak):
                data, note = bak, "restored"
            else:
                data, note = None, "lost"
        where = f" Старый файл отложен: {kept}" if kept else ""
        if note == "restored":
            self.toast("Сохранение было повреждено — взяла запасную копию." + where, 10)
        elif note == "lost":
            self.toast("Сохранение повреждено, запасной копии нет — начинаем заново." + where, 12)
        if data is None:
            return
        version = data.get("version", 1)
        if isinstance(version, (int, float)) and version > SAVE_VERSION:
            copy = savefile.keep_broken(path, "newer")
            self.toast("Это сохранение от более новой версии игры — лучше обнови игру." + (f" Копия: {copy}" if copy else ""), 10)
        self.set_theme()
        now = time.time()
        saved_at = data.get("saved_at", now)
        away = now - saved_at if isinstance(saved_at, (int, float)) and saved_at == saved_at else 0.0
        amt = self.farm.offline_earn(max(0.0, away))
        if amt > 0 and away >= 60:      # после быстрого перезапуска окно «С возвращением» не показываем
            self.offline_info = (min(away, self.farm.offline_cap()), amt)
            self.modal = "offline"
        if self.farm.truck_ready():
            self.truck_state = "parked"
            self.truck_x = TRUCK_PARK_X

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

    def truck_tier(self):
        p = self.farm.potential_leaves()
        tier = 0
        for k, (_, _, need) in enumerate(TRUCK_TIERS):
            if p >= need:
                tier = k
        return tier

    def coin_pos(self, k):
        cx, cy = crop_center(k)
        return cx, cy - 6 + math.sin(self.t * 4 + k) * 3

    def hit_tile(self, pos):
        dx = (pos[0] - OX) / (TW / 2)
        dy = (pos[1] + 18 - OY) / (TH / 2)
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
            else:
                self.floater(x, y - 10, "+$" + fmt(amt))
            self.coins_to_counter(x, y, amt, 7 if self.farm.last_lucky else 3)

    # ------------------------------------------------------------ монетки и плашка денег
    MONEY_ICON = (34, 32)             # где на экране монетка плашки денег

    def coins_to_counter(self, x, y, amt, n=3):
        """Монетки летят дугой из (x, y) в плашку денег; деньги на плашке прибавляются, когда они долетают."""
        if amt <= 0 or self.view == "board":
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

    def animate(self):
        """Всё, что движется по настоящему времени: частицы, деньги на плашке, «пружинки» кнопок."""
        now = self.t_real
        dt = 0.0 if self.anim_t is None else max(0.0, min(0.1, now - self.anim_t))
        self.anim_t = now
        self.frame_dt = dt
        self.fx.update(dt)
        if not any(p["kind"] == "fly" for p in self.fx.items):
            self.money_pending = 0.0          # на всякий случай: ничего не летит — ничего и не ждём
        target = max(0.0, self.farm.money - self.money_pending)
        if (self.money_shown is None or target < self.money_shown
                or target - self.money_shown <= max(0.005, target * 0.005)):
            self.money_shown = target         # траты — сразу (иначе кажется, что денег больше, чем есть)
        else:
            self.money_shown = anim.approach(self.money_shown, target, 9.0, dt)
        self.money_bump = max(0.0, self.money_bump - dt * 4)

    def skip_anims(self):
        """Мгновенно закончить анимации окон (для тестов и скриншотов)."""
        self.modal_t0 = -99.0
        self.closing = None
        self.fx.clear()
        self.money_pending = 0.0
        self.money_shown = None
        self.coin_born = [None if b is None else -99.0 for b in self.coin_born]

    def click_rain(self):
        f = self.farm
        if f.start_rain():
            self.quest("weather")
            self.toast(f"{self.farm_info()['weather']}! Всё растёт быстрее")
            self.sfx.play("fanfare" if self.farm_info()["weather"] == "Праздник урожая" else "rain")
        elif f.rain_left <= 0 and f.rain_cd > 0:
            self.toast(f"Ещё рано: {self.farm_info()['weather'].lower()} через {fmt_time(f.rain_cd)}", 1.5)

    # ------------------------------------------------------------ белка
    def squirrel_delay(self):
        return random.uniform(SQUIRREL_MIN, SQUIRREL_MAX) * 0.9 ** self.farm.up("sq_often") / self.farm.song_effect("squirrel")

    def crow_delay(self):
        return random.uniform(CROW_MIN, CROW_MAX) * 1.5 ** self.farm.up("scarecrow")

    def spawn_squirrel(self, golden=None):
        d = random.choice((1, -1))
        if golden is None:
            golden = random.random() < (GOLDEN_CHANCE + 0.04 * self.farm.up("golden")) * self.farm.song_effect("golden")
        self.squirrel = dict(x=-60.0 if d == 1 else W + 60.0, y=random.uniform(478, 506), d=d, golden=golden,
                             phase="run", timer=0.0, stop=random.uniform(260, 740), vy=0.0, life=0.0, hop_i=0)
        self.sfx.play("squirrel")
        if golden:
            self.toast("Ого! ЗОЛОТАЯ белка! Лови скорее!", 3)
        else:
            self.toast("Шур-шур... на лугу белка! Лови!", 2.5)

    def update_squirrel(self, dt):
        if self.squirrel is None:
            self.squirrel_timer -= dt
            if self.squirrel_timer <= 0:
                self.spawn_squirrel()
            return
        q = self.squirrel
        q["timer"] += dt
        q["life"] += dt
        golden = q["golden"]
        if golden and q["phase"] != "caught" and random.random() < 6 * dt:      # золотая белка поблёскивает
            self.fx.twinkle(q["x"] + random.uniform(-26, 26), q["y"] - random.uniform(12, 52) - self.squirrel_pose(q)[0],
                            r=random.uniform(3, 5.5))
        if q["phase"] == "caught":
            q["vy"] += 900 * dt
            q["y"] += q["vy"] * dt
            if q["timer"] > 0.9:
                self.end_squirrel()
        elif q["phase"] == "sit":
            if q["timer"] >= (GOLDEN_SIT if golden else SQUIRREL_SIT) + self.farm.up("sq_sit"):
                q["phase"], q["timer"], q["hop_i"] = "flee", 0.0, 0
        else:
            speed = SQUIRREL_SPEED * (1.4 if q["phase"] == "flee" else 1.0) * (GOLDEN_SPEED if golden else 1.0)
            q["x"] += q["d"] * speed * dt
            period = SQUIRREL_HOP[q["phase"]][0] / (GOLDEN_SPEED if golden else 1.0)
            i = int(q["timer"] / period)
            if i != q["hop_i"]:                                   # приземлилась — пыль из-под лап
                q["hop_i"] = i
                self.fx.dust(q["x"] - q["d"] * 8, q["y"], n=2, size=(3, 6), drift=-q["d"] * 25, alpha=130)
            if q["phase"] == "run" and (q["x"] - q["stop"]) * q["d"] >= 0:
                q["phase"], q["timer"] = "sit", 0.0
                self.fx.dust(q["x"], q["y"], n=3, size=(3, 6), alpha=120)
            if q["x"] < -80 or q["x"] > W + 80:
                self.end_squirrel()
                self.toast("Золотая белка убежала... эх!" if golden else "Белка убежала...", 1.5)

    def end_squirrel(self):
        self.squirrel = None
        self.squirrel_timer = self.squirrel_delay()

    def catch_squirrel(self):
        q = self.squirrel
        if not q or q["phase"] == "caught":
            return
        amt = self.farm.catch_squirrel(GOLDEN_MULT if q["golden"] else 1)
        self.sfx.play("coin_big")
        hop = self.squirrel_pose(q)[0]
        q["y"] -= hop                                   # кувырок начинается оттуда, где её поймали (хоть и в прыжке)
        q["phase"], q["timer"], q["vy"] = "caught", 0.0, -420.0
        self.floater(q["x"], q["y"] - 70, "+$" + fmt(amt))
        gold = ((255, 225, 110), (255, 250, 210), (255, 190, 70))
        self.fx.sparks(q["x"], q["y"] - 28, n=12 if q["golden"] else 7, colors=gold, speed=(50, 130), life=(0.35, 0.6),
                       size=(2, 4), gravity=120, up=70)
        self.fx.ring(q["x"], q["y"], r0=8, r1=46, life=0.45, color=(255, 235, 150), width=3)
        self.coins_to_counter(q["x"], q["y"] - 30, amt, 9 if q["golden"] else 5)
        self.quest("squirrel")
        if q["golden"]:
            self.quest("golden")
            self.toast(f"ЗОЛОТАЯ белка поймана! x{GOLDEN_MULT}: +$" + fmt(amt), 4)
        else:
            self.toast("Поймал белку! +$" + fmt(amt), 3)

    def squirrel_pose(self, q):
        """Как выглядит белка сейчас -> (подскок, sx, sy, наклон°, прозрачность, точка опоры).
        Бежит дугами: на земле сжимается перед прыжком, в воздухе вытягивается и клюёт носом к приземлению.
        Сидит — дышит и грызёт орешек. Поймали — кувыркается и тает."""
        d, t, ph = q["d"], q["timer"], q["phase"]
        if ph in ("run", "flee"):
            period, height = SQUIRREL_HOP[ph]
            period /= GOLDEN_SPEED if q["golden"] else 1.0
            u = (t / period) % 1.0
            if u < 0.16:                                   # лапы на земле: сжалась, толкается
                c = math.sin(math.pi * u / 0.16)
                return 0.0, 1 + 0.12 * c, 1 - 0.14 * c, 0.0, None, "midbottom"
            v = (u - 0.16) / 0.84                          # в воздухе
            s = math.sin(math.pi * v)
            return 4 * height * v * (1 - v), 1 - 0.04 * s, 1 + 0.07 * s, d * 9 * (1 - 2 * v), None, "midbottom"
        if ph == "sit":
            land = max(0.0, 1 - t / 0.16)                  # только что приземлилась
            breath = 0.022 * math.sin(t * 6)
            nibble = 3.0 * math.sin(t * 13) if (t % 1.4) < 0.5 else 0.0
            return 0.0, 1 + 0.1 * land, 1 - 0.12 * land + breath, nibble, None, "midbottom"
        k = min(1.0, t / 0.7)                              # поймали: кувырок через спину
        spin = d * 360 * anim.ease_out_cubic(k)
        fade = 255 * (1 - max(0.0, (t - 0.5) / 0.4))
        grow = 1 + 0.15 * math.sin(math.pi * min(1.0, t / 0.9))
        return 0.0, grow, grow, spin, max(0, fade), "center"

    def draw_squirrel_layer(self):
        q = self.squirrel
        if q is None:
            return
        hop, sx, sy, ang, alpha, pivot = self.squirrel_pose(q)
        if q["phase"] != "caught":                         # тень на траве: в прыжке меньше и бледнее
            lift = min(1.0, hop / 45)
            draw_shadow(self.screen, q["x"], q["y"] + 1, 46 * (1 - 0.35 * lift), 10 * (1 - 0.3 * lift), 70 * (1 - 0.5 * lift))
        if pivot == "center":
            draw_squirrel(self.screen, q["x"], q["y"] - 28, q["d"], 0, q["golden"], q["life"], sx, sy, ang, alpha, "center")
        else:
            draw_squirrel(self.screen, q["x"], q["y"], q["d"], hop, q["golden"], q["life"], sx, sy, ang)
        if q["phase"] != "caught" and self.modal is None:
            self.zone((P(q["x"] - 38), P(q["y"] - 66 - hop), 76, 70 + hop), self.catch_squirrel)

    # ------------------------------------------------------------ ворона
    def spawn_crow(self):
        f = self.farm
        if not self.farm_info()["crow"]:
            self.crow_timer = self.crow_delay()
            return
        free = [k for k in range(N_CROPS) if f.levels[k] > 0]
        if not free:
            self.crow_timer = self.crow_delay()
            return
        k = random.choice(free)
        cx, cy = crop_center(k)
        d = random.choice((1, -1))
        sx = W + 60 if d == -1 else -60
        self.crow = dict(k=k, x=float(sx), y=-40.0, sx=float(sx), sy=-40.0, tx=cx + 26 * -d, ty=cy - 34,
                         phase="fly_in", timer=0.0, d=d)

    def update_crow(self, dt):
        if self.crow is None:
            self.crow_timer -= dt
            if self.crow_timer <= 0:
                self.spawn_crow()
            return
        c = self.crow
        c["timer"] += dt
        if c["phase"] == "fly_in":
            u = min(1.0, c["timer"] / 2.2)
            e = 1 - (1 - u) ** 2
            c["x"] = c["sx"] + (c["tx"] - c["sx"]) * e
            c["y"] = c["sy"] + (c["ty"] - c["sy"]) * e - math.sin(u * math.pi) * 60
            if u >= 1:
                c["phase"], c["timer"] = "sit", 0.0
                self.fx.dust(c["x"], c["y"], n=3, color=DIRT, size=(3, 6), spread=12, alpha=140)
                self.farm.blocked[c["k"]] = True
                self.sfx.play("crow")
                self.toast(f"Кар! Ворона села на грядку «{CROPS[c['k']]['name']}» — она не растёт. Прогони!", 4)
        elif c["phase"] == "away":
            c["x"] -= c["d"] * 380 * dt
            c["y"] -= 260 * dt
            if c["y"] < -60:
                self.end_crow()

    def shoo_crow(self):
        c = self.crow
        if not c or c["phase"] != "sit":
            return
        self.farm.blocked[c["k"]] = False
        self.sfx.play("shoo")
        self.quest("crow")
        self.fx.feathers(c["x"], c["y"] - 26, n=6)            # перья летят и медленно кружат вниз
        self.fx.dust(c["x"], c["y"], n=3, color=DIRT, size=(3, 6), spread=12, alpha=140)
        c["phase"], c["timer"] = "away", 0.0
        c["d"] = -c["d"]
        self.floater(c["x"], c["y"] - 40, "Кыш!", (230, 240, 255))

    def end_crow(self):
        if self.crow:
            self.farm.blocked[self.crow["k"]] = False
        self.crow = None
        self.crow_timer = self.crow_delay()

    def crow_pose(self, c):
        """Как выглядит ворона -> (смотрит, подскок, крылья вверх, sx, sy, наклон°, каркает).
        Летит — машет крыльями (картинки crow_fly и crow по очереди), перед посадкой планирует.
        Сидит — цикл 3 с: клюёт грядку, каркает (откидывается назад), оглядывается."""
        t, d = c["timer"], c["d"]
        if c["phase"] == "fly_in":
            u = min(1.0, t / 2.2)
            if u > 0.82:                                   # планирует, крылья раскрыты, задрала нос
                return d, 0.0, True, 1.0, 1.0, d * 8, False
            ph = (t * 4.5) % 1.0
            return d, -3 * math.sin(2 * math.pi * ph), ph < 0.5, 1.0, 1.0, -d * 5, False
        if c["phase"] == "away":
            ph = (t * 7) % 1.0
            return -d, -3 * math.sin(2 * math.pi * ph), ph < 0.5, 1.0, 1.0, -d * 14, False
        land = max(0.0, 1 - t / 0.18)
        sx, sy = 1 + 0.1 * land, 1 - 0.12 * land + 0.015 * math.sin(t * 5)
        cyc = t % 3.0
        if cyc < 1.6:                                      # клюёт: наклоняется вперёд короткими ударами
            peck = max(0.0, math.sin(cyc * 7.5)) ** 2
            return d, 0.0, False, sx, sy - 0.03 * peck, -d * 22 * peck, False
        if cyc < 2.3:                                      # «Кар!»: откидывается назад и вытягивается
            k = math.sin(math.pi * (cyc - 1.6) / 0.7)
            return d, 0.0, False, sx - 0.03 * k, sy + 0.06 * k, d * 8 * k, True
        hop = 4 * max(0.0, math.sin(math.pi * (cyc - 2.3) / 0.25)) if cyc < 2.55 else 0.0
        return -d, hop, False, sx, sy, 0.0, False          # подпрыгнула и оглядывается

    def draw_crow_layer(self):
        c = self.crow
        if c is None:
            return
        face, hop, wings, sx, sy, ang, caw = self.crow_pose(c)
        if c["phase"] == "sit":
            draw_shadow(self.screen, c["x"], c["y"] + 1, 40, 9, 70)
            draw_crow(self.screen, c["x"], c["y"] - hop, face, c["timer"], False, 0.0, sx=sx, sy=sy, angle=ang)
            if caw:
                draw_text(self.screen, "Кар!", 16, (c["x"] + 14 * c["d"], c["y"] - 68), WHITE)
            if self.modal is None:
                self.zone((P(c["x"] - 44), P(c["y"] - 64), 88, 70), self.shoo_crow)
        else:
            draw_crow(self.screen, c["x"], c["y"] + hop, face, c["timer"], True, wings_up=wings, sx=sx, sy=sy, angle=ang)

    def click_sun(self):
        amt = self.farm.sun_click()
        if amt:
            self.quest("sun")
            self.sfx.play("sun")
            self.floater(560, 120, "+$" + fmt(amt))
            self.toast("Солнечный бонус: +$" + fmt(amt))

    def sell_farm(self):
        self.leaving_tier = self.truck_tier()
        gained = self.farm.sell_to_truck()
        self.sfx.play("sell")
        if gained > 0:
            self.quest("truck")
        self.modal = None
        self.mode = "normal"
        self.truck_state = "leaving"
        self.floaters.clear()
        if self.crow:
            self.shoo_crow() if self.crow["phase"] == "sit" else self.end_crow()
        self.toast(f"{self.farm_info()['buyer_cap']} забрал урожай! +{gained} {CUR['gen']}. Начинаем заново с бонусом!", 4)
        self.save()

    def reset_everything(self):
        if not self.confirm_reset:
            self.confirm_reset = True
            return
        self.farm = Farm()
        self.tavern = Tavern()
        self.view = "field"
        self.set_theme()
        self.bandit = None
        self.crow = None
        self.crow_timer = self.crow_delay()
        self.truck_state, self.truck_x = "away", W + 230.0
        self.confirm_reset = False
        self.modal = None
        self.tut.restart()
        self.save()
        self.toast("Прогресс сброшен")

    def report_assets(self):
        """Пишет в консоль, какие картинки из assets/ подхватились, и предупреждает о неузнанных."""
        from .templates import check_assets
        try:
            found, unknown = check_assets()
        except Exception as e:   # проверка не должна мешать игре
            print("Проверка assets не удалась:", e)
            return
        copies = [n for n in found if (lambda p: p is not None and is_template_copy(n, p))(find_asset_file(n))]
        found = [n for n in found if n not in copies]
        print(f"assets: подхвачено файлов — {len(found)}")
        if copies:
            print(f"   копий шаблонов (игра их пропускает, можно удалить): {len(copies)}")
        for name in sorted(found):
            note = ""
            parts = name.split("/")
            ids = {fm["id"]: fm["name"] for fm in FARMS}
            if len(parts) >= 2 and (parts[1] in ids or (parts[0] == "backgrounds" and parts[1] in ids)):
                fid = parts[1]
                if fid != self.farm_info()["id"]:
                    note = f"  (будет видно на ферме «{ids[fid]}», сейчас ты на другой)"
            print("   +", name + note)
        for rel, hint in unknown:
            print("   ? не узнаю", "assets/" + rel, ("— " + hint) if hint else "")
        if unknown:
            rel, hint = unknown[0]
            more = f" (и ещё {len(unknown) - 1})" if len(unknown) > 1 else ""
            self.toast(f"Картинка не узнана: assets/{rel}{more}" + (f" — {hint}" if hint else ""), 8)

    # ------------------------------------------------------------ фермы
    def farm_info(self):
        return FARMS[min(self.farm.farm_index, len(FARMS) - 1)]

    def set_theme(self):
        apply_farm(self.farm.farm_index)
        self.bg = self.build_background()
        self.music.play_for(self.farm_info()["id"])

    def do_move(self):
        f = self.farm
        old = self.farm_info()
        if not f.move_farm():
            return
        self.sfx.play("fanfare")
        self.set_theme()
        self.tavern.replace_impossible(self.farm_info(), blocked=self.quest_blocked())
        self.modal = None
        self.view, self.mode = "field", "normal"
        self.truck_state, self.truck_x = "away", W + 230.0
        self.crow = None
        self.squirrel = None
        self.bandit = None
        self.floaters.clear()
        self.move_notified = False
        self.toast(f"Добро пожаловать: {self.farm_info()['name']}! Всё заново, но доход x{FARM_BONUS ** f.farm_index}", 5)
        self.toast(f"Трофей «{old['trophy']['name']}»: {old['trophy']['text']}", 5)
        self.save()

    # ------------------------------------------------------------ мороз
    def update_frost(self, dt):
        if not self.farm_info()["frost"]:
            return
        self.frost_timer -= dt
        if self.frost_timer > 0:
            return
        self.frost_timer = random.uniform(FROST_MIN, FROST_MAX)
        f = self.farm
        free = [k for k in range(N_CROPS) if f.levels[k] > 0 and f.frozen[k] == 0 and not f.blocked[k]]
        if not free:
            return
        hit = random.sample(free, min(len(free), random.choice((1, 1, 2))))
        for k in hit:
            f.frozen[k] = FROST_HITS
        names = ", ".join(CROPS[k]["name"] for k in hit)
        self.toast(f"Мороз! Замёрзло: {names}. Разбей лёд кликами!", 4)

    def hit_ice(self, k):
        f = self.farm
        if f.frozen[k] <= 0:
            return
        f.frozen[k] -= 1
        cx, cy = crop_center(k)
        if f.frozen[k] == 0:
            self.floater(cx, cy - 60, "Лёд разбит!", (200, 235, 255))
        else:
            self.floater(cx + random.uniform(-20, 20), cy - 50, "Тресь!", (220, 240, 255))

    def draw_ice(self, k):
        f = self.farm
        hits = f.frozen[k]
        if hits <= 0:
            return
        cx, cy = crop_center(k)
        hw, hh, up = TW / 2 * 0.86, TH / 2 * 0.86, 46
        ice = hd.Surface((P(hw * 2 + 8), P(hh * 2 + up + 8)), pygame.SRCALPHA)
        ox, oy = hw + 4, hh + up + 4      # центр клетки внутри поверхности
        def L(x, y):
            return (P(ox + x), P(oy + y))
        body = [L(-hw, 0), L(-hw, -up), L(0, -hh - up), L(hw, -up), L(hw, 0), L(0, hh)]
        pygame.draw.polygon(ice, (190, 230, 255, 150), body)
        pygame.draw.polygon(ice, (225, 245, 255, 190), [L(-hw, -up), L(0, -hh - up), L(hw, -up), L(0, hh - up)])
        pygame.draw.polygon(ice, (255, 255, 255, 235), body, 3)
        pygame.draw.line(ice, (255, 255, 255, 235), L(-hw, -up), L(0, hh - up), 2)
        pygame.draw.line(ice, (255, 255, 255, 235), L(hw, -up), L(0, hh - up), 2)
        pygame.draw.line(ice, (255, 255, 255, 235), L(0, hh - up), L(0, hh), 2)
        pygame.draw.line(ice, (255, 255, 255, 200), L(-hw * 0.6, -up * 0.8), L(-hw * 0.3, -up * 0.2), 3)
        cracks = FROST_HITS - hits
        crack_lines = [[L(-20, -40), L(-5, -25), L(-15, -8), L(2, 5)], [L(25, -50), L(12, -30), L(28, -16)],
                       [L(-40, -10), L(-25, -18), L(-30, -32)]]
        for c in crack_lines[:cracks]:
            pygame.draw.lines(ice, (70, 120, 170, 230), False, c, 2)
        self.screen.blit(ice, (P(cx - ox), P(cy - oy)))
        draw_text(self.screen, f"x{hits}", 14, (cx + hw - 14, cy - up - 4), (220, 240, 255))
        if self.modal is None and self.mode == "normal":
            self.zone((P(cx - 60), P(cy - 70), 120, 100), lambda k=k: self.hit_ice(k))

    def open_modal(self, name):
        self.modal = name
        self.confirm_reset = False
        if name == "shop":
            self.shop_page = 0
            self.tut_event("shop")

    # ------------------------------------------------------------ input
    def on_click(self, pos):
        self.click_pos = pos
        self.tip_key, self.tip_t0 = None, self.t_real     # щёлкнул — подсказку убираем
        for rect, cb, btn in reversed(self.zones):
            if rect.collidepoint(pos):
                if btn:
                    self.sfx.play("click")
                    self.press_key, self.press_t = tuple(rect), self.t_real
                cb()
                return
        if self.modal is None and self.mode == "normal" and self.view == "field":
            self.try_collect(pos)

    def on_key(self, key):
        if key == pygame.K_ESCAPE:
            if self.modal:
                self.modal = None
            elif self.mode == "upgrade":
                self.mode = "normal"
            elif self.view in ("barn", "tavern"):
                self.view = "field"
            elif self.view == "board":
                self.view = "tavern"
        elif key == pygame.K_F11:
            self.toggle_fullscreen()
        elif key == pygame.K_m:
            self.toggle_music()
        elif key == pygame.K_F1 and DEV:
            self.modal = None if self.modal == "dev" else "dev"
        elif self.modal is None:
            if key == pygame.K_b and self.view in ("field", "barn"):
                self.toggle_barn()
            elif key == pygame.K_t and self.tavern.unlocked:
                if self.view in ("tavern", "board"):
                    self.leave_tavern()
                else:
                    self.open_tavern()
            elif key == pygame.K_u and self.view == "field":
                self.mode = "normal" if self.mode == "upgrade" else "upgrade"
            elif key == pygame.K_s:
                self.open_modal("shop")

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.t += dt
        f = self.farm
        f.update(dt)
        self.tavern_tick(dt)
        self.mill_tick(dt)
        self.tut_tick(dt)

        for fl in self.floaters:
            fl[1] -= 35 * dt
            fl[3] -= dt
        self.floaters = [fl for fl in self.floaters if fl[3] > 0]
        for tt in self.toasts:
            tt[1] -= dt
        self.toasts = [tt for tt in self.toasts if tt[1] > 0]

        # грузовик
        if self.truck_state == "away" and f.truck_ready():
            self.truck_state = "arriving"
            self.toast(self.farm_info()["arrive"], 4)
            self.sfx.play("truck" if self.farm_info()["vehicle"] == "truck" else "fanfare")
        elif self.truck_state == "arriving":            # 3.3: подъезжает и плавно тормозит
            self.truck_v = max(60.0, min(280.0, (self.truck_x - TRUCK_PARK_X) * 2.4))
            self.truck_x -= self.truck_v * dt
            if self.truck_x <= TRUCK_PARK_X:
                self.truck_x, self.truck_v = TRUCK_PARK_X, 0.0
                self.truck_state, self.truck_t = "parked", self.t
        elif self.truck_state == "leaving":             # трогается и разгоняется
            if self.truck_v == 0.0:
                self.truck_t = self.t
            self.truck_v = min(320.0, max(1.0, self.truck_v + 380 * dt))
            self.truck_x -= self.truck_v * dt
            if self.truck_x < -260:
                self.truck_state, self.truck_v = "away", 0.0
                self.truck_x = W + 230.0
        if self.truck_state in ("arriving", "leaving") and self.view == "field":     # пыль из-под задних колёс
            self.truck_dust += dt * min(1.0, self.truck_v / 120)
            if self.truck_dust >= 0.09:
                self.truck_dust = 0.0
                rear = 60 if self.farm_info()["vehicle"] == "truck" else 75
                self.fx.dust(self.truck_x + rear, TRUCK_GROUND + 2, n=2, color=ROAD_DUST, size=(5, 9), spread=6, up=10,
                             drift=50, alpha=150, life=(0.4, 0.7))

        if self.modal is None and self.view == "field":
            self.update_squirrel(dt)
            self.update_crow(dt)
            self.update_frost(dt)
            self.update_bandit(dt)
            if self.farm.can_move() and not self.move_notified:
                self.move_notified = True
                self.toast(f"Заработано ${fmt(self.farm.move_threshold())}! Можно переехать: {FARMS[self.farm.farm_index + 1]['name']}", 5)

        # дождь (капли падают быстро и брызгают об землю) или конфетти праздника (падает медленно, кувыркаясь)
        festival = self.farm_info()["weather"] == "Праздник урожая"
        if f.rain_left > 0:
            if festival:
                if random.random() < min(1.0, 70 * dt):
                    self.drops.append([random.uniform(150, 860), random.uniform(90, 140), random.uniform(260, 540)])
            else:
                for _ in range(4):
                    self.drops.append([random.uniform(180, 830), random.uniform(120, 160), random.uniform(220, 470)])
        speed = 150 if festival else 520
        landed = []
        for d in self.drops:
            d[1] += speed * dt
            if d[1] >= d[2]:
                landed.append(d)
        if landed:
            self.drops = [d for d in self.drops if d[1] < d[2]]
            if not festival and self.view == "field":
                for d in landed[:3]:
                    if random.random() < 0.5:
                        self.fx.splash(d[0], d[2])

        self.autosave += dt
        if self.autosave >= 15:
            self.autosave = 0
            self.save()

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
        if f.farmers[k] and real_cycle < FAST_GROW_CYCLE:
            # быстрая грядка: растения всегда взрослые (иначе стадии мелькают), на каждом сборе мягко «кивают»
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
        for i, (ox, oy) in enumerate(PLANT_SPOTS):
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
            rounded(s, (200, 150, 100), (P(cx - 56), P(cy - 34), 112, 56), 8, 3)
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
        elif f.farmers[k] and t <= 0.5:
            draw_bar(s, bar, 1.0, (120, 220, 90))
        else:
            draw_bar(s, bar, f.progress[k] / t, (120, 220, 90) if f.farmers[k] else GOLD)
        if self.farm_info()["peasants"]:   # средневековье: значок крестьянина на левом конце полоски
            # Значок «сидит» на самой полоске прогресса (как аватар), поэтому не закрывает овощи.
            ax, ay = bar.x - 2, bar.centery
            if f.farmers[k]:
                pygame.draw.circle(s, OUT, (ax, ay), 13)
                pygame.draw.circle(s, (245, 175, 50), (ax, ay), 11)                 # занят — оранжевый
                draw_peasant_head(s, ax, ay + 2, 0.85)
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
            draw_coin(s, x, y + (1 - min(1.0, pop)) * 10, (18 if big else 15) * max(0.05, pop))
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
        tr = tag.get_rect(center=(P(cx), P(board.y - 6)))
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
        if weather == "Праздник урожая":
            self.draw_festival_button()
            return
        draw_cloud_body(s, x, y, raining)
        if raining:
            for k in range(6):
                dy = (self.t * 120 + k * 17) % 50
                pygame.draw.line(s, (90, 160, 230), (x - 40 + k * 15, P(y + 34 + dy)), (x - 42 + k * 15, P(y + 42 + dy)), 3)
            draw_text(s, f"{self.farm_info()['weather']} x{f.growth_speed():g}  " + fmt_time(f.rain_left), 16, (x, y - 58), (180, 225, 255))
        elif f.rain_cd > 0:
            draw_text(s, fmt_time(f.rain_cd), 18, (x, y - 58))
        else:
            c = (255, 255, 255) if int(self.t * 2) % 2 else (190, 230, 255)
            draw_text(s, "Вызвать дождь!" if self.farm_info()["weather"] == "Дождь" else "Вызвать оттепель!", 16, (x, y - 58), c)
            self.zone((x - 65, y - 45, 130, 90), self.click_rain)

    FESTIVAL_RECT = (875, 116, 60, 60)    # кнопка праздника — на траве справа от замка

    def draw_festival_button(self):
        """Средневековье: кнопка «Праздник урожая» рядом с замком (вместо часовни)."""
        s, f = self.screen, self.farm
        rect = pygame.Rect(self.FESTIVAL_RECT)
        active = f.rain_left > 0
        ready = not active and f.rain_cd <= 0

        def sheaf(r):   # сноп пшеницы с красной лентой (если нет картинки ui/btn_festival)
            cx, cy = r.centerx, r.centery + 4
            for dx in (-9, -4, 0, 4, 9):
                pygame.draw.line(s, OUT, (cx + dx // 2, cy + 18), (cx + dx, cy - 12), 4)
                pygame.draw.line(s, (220, 180, 70), (cx + dx // 2, cy + 18), (cx + dx, cy - 12), 2)
                ellipse(s, (245, 205, 90), cx + dx * 1.2, cy - 16, 7, 14)
            rounded(s, (210, 60, 60), (cx - 11, cy + 2, 22, 7), 3, 2)

        if ready and not has_sprite("ui/btn_festival"):
            pulse = 1 + 0.06 * math.sin(self.t * 5)
            pygame.draw.circle(s, (255, 235, 150), rect.center, P(40 * pulse))
        self.icon_button(rect, "festival", sheaf, self.click_rain, active=active or ready)
        below = rect.bottom + 14
        if active:
            draw_text(s, f"Праздник! x{f.growth_speed():g}  " + fmt_time(f.rain_left), 15, (rect.centerx, below), (255, 235, 150))
        elif f.rain_cd > 0:
            draw_text(s, fmt_time(f.rain_cd), 16, (rect.centerx, below))
        else:
            c = (255, 255, 255) if int(self.t * 2) % 2 else (255, 235, 150)
            draw_text(s, "Праздник урожая!", 15, (rect.centerx, below), c)

    def draw_vehicle(self, x, y, color, cargo=False, bob=0.0, tier=0, angle=0.0, sy=1.0):
        draw_vehicle_at(self.screen, self.farm_info()["vehicle"], tier, x, y, color, cargo, bob, angle, sy)

    def truck_pose(self):
        """Покачивание машины -> (подскок, наклон°, sy). Едет — трясётся на кочках; остановилась — клюёт носом
        и покачивается на рессорах; трогается — приседает на зад; стоит — еле заметно «дышит» мотором."""
        t, e = self.t, self.t - self.truck_t
        cart = self.farm_info()["vehicle"] == "cart"
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
        draw_shadow(s, self.truck_x - 10, TRUCK_GROUND + 3, 220, 18, 60)
        self.draw_vehicle(self.truck_x, TRUCK_GROUND, color, cargo=self.truck_state == "leaving", bob=bob, tier=tier,
                          angle=ang, sy=sy)
        if self.truck_state == "parked" and self.modal is None:
            p = f.potential_leaves()
            pulse = 1 + 0.05 * math.sin(self.t * 5)
            bw, bh = P(190 * pulse), P(54 * pulse)
            bx, by = P(self.truck_x - 10 - bw / 2), P(TRUCK_GROUND - 150 - bh / 2)
            rounded(s, WHITE, (bx, by, bw, bh), 14, 3)
            poly(s, WHITE, [(self.truck_x - 25, by + bh - 2), (self.truck_x - 5, by + bh - 2), (self.truck_x - 20, by + bh + 14)], 0)
            draw_text(s, name, 13, (bx + bw / 2, by + 14), (90, 70, 60), outline=None)
            draw_cur_icon(s, bx + 30, by + 36, 0.6)
            draw_text(s, f"+{p} {CUR['gen']}", 16, (bx + bw / 2 + 10, by + 36), (90, 200, 80))
            self.zone_btn((bx, by, bw, bh), lambda: self.open_modal("truck"), 14)
            self.zone((P(self.truck_x - 105), TRUCK_GROUND - 95, 190, 95), lambda: self.open_modal("truck"))

    def draw_hud(self):
        s, f = self.screen, self.farm
        board = self.view == "board"     # на доске заданий плашки денег закрыли бы записки
        # плашки подстраиваются под длину текста
        def pill(y, h, text, size, icon):
            img = render_text(text, size, WHITE, OUT)
            w = max(h + 30, 58 + img.get_width() + 14)
            rounded(s, PILL, (14, y, w, h), h // 2, 3)
            icon(34, y + h / 2)
            s.blit(img, img.get_rect(midleft=(58, y + h // 2)))
            return pygame.Rect(14, y, w, h)

        if board:
            pill = lambda *a: pygame.Rect(0, 0, 0, 0)
            self.draw_tokens_pill(14, 12)
        shown = f.money if self.money_shown is None else self.money_shown
        bump = math.sin(min(1.0, 1 - self.money_bump) * math.pi) * 0.22 if self.money_bump > 0 else 0.0
        money_rect = pill(12, 40, "$" + fmt(shown), 20, lambda x, y: draw_coin(s, x, y, 17 * (1 + bump)))
        self.tip(money_rect, "Деньги. Урожай собирай с грядок — монетки прилетят сюда")
        inc_rect = pill(58, 36, "$" + fmt(f.total_income()) + " /с", 17, lambda x, y: draw_coin(s, x, y, 15, (200, 215, 240)))
        self.tip(inc_rect, "Доход в секунду со всех грядок")
        leaf_rect = pill(100, 36, f"{f.leaves}  {fmt_mult(f.home_leaves)}", 17, lambda x, y: draw_cur_icon(s, x, y, 0.95))
        if not board:
            self.zone_btn(leaf_rect, lambda: self.open_modal("tree"), 18)
            self.tip(leaf_rect, f"{CUR['title']}: множитель дохода. Щёлкни — дерево улучшений")
        if self.farm_info()["peasants"] and not board:
            pr = pill(142, 32, f"свободно {f.free_peasants()} из {f.peasants}", 15,
                      lambda x, y: draw_peasant_head(s, x, y + 1, 1.1))
            self.zone_btn(pr, lambda: (self.open_modal("shop"), setattr(self, "shop_tab", "farm")), 16)
            self.tip(pr, "Свободные крестьяне. Щёлкни — нанять ещё")
        if not board:
            y = 180 if self.farm_info()["peasants"] else 142
            self.draw_boost_pill(y)
            if self.farm.boost_left > 0:
                y += 38
            self.draw_song_pill(y)

        # шестерёнка
        g = pygame.Rect(W - 62, 12, 50, 50)

        def gear(r):
            for k in range(8):
                a = k * math.pi / 4
                pygame.draw.circle(s, OUT, (P(r.centerx + math.cos(a) * 14), P(r.centery + math.sin(a) * 14)), 6)
            pygame.draw.circle(s, OUT, r.center, 14)
            pygame.draw.circle(s, BTN_BLUE, r.center, 6)
        self.icon_button(g, "settings", gear, lambda: self.open_modal("settings"), tip="Настройки: звук, экран, игра")
        if self.view == "tavern":
            self.draw_tokens_pill(W - 72, 16, right=True)
            self.draw_tavern_back("На поле", self.leave_tavern)
            return
        if board:
            self.draw_tavern_back("В таверну", lambda: setattr(self, "view", "tavern"), 170)
            return

        if DEV:
            tag = draw_text(s, f"DEV  F1   скорость x{self.time_scale}", 14, (W // 2, 628), (255, 120, 120))
        # нижние кнопки (картинки — assets/ui/btn_*.png или лист assets/ui/buttons.png)
        if self.view == "barn":
            if has_sprite("ui/btn_field"):
                self.icon_button(pygame.Rect(16, 560, 62, 56), "field", None, self.toggle_barn, "На поле")
            else:
                back = pygame.Rect(16, 560, 134, 56)
                rounded(s, BTN_GREEN, back, 10, 3)
                draw_text(s, "<  На поле", 18, back.center)
                self.zone_btn(back, self.toggle_barn)
            return

        def cart(r):
            x, y = r.x - 16, r.y - 560
            pygame.draw.lines(s, OUT, False, [(x + 26, y + 573), (x + 34, y + 573), (x + 40, y + 598), (x + 64, y + 598),
                                              (x + 68, y + 581), (x + 37, y + 581)], 4)
            pygame.draw.circle(s, OUT, (x + 43, y + 606), 4)
            pygame.draw.circle(s, OUT, (x + 61, y + 606), 4)

        def shovel(r):
            x, y = r.x - 88, r.y - 560
            pygame.draw.line(s, OUT, (x + 102, y + 572), (x + 122, y + 594), 5)
            poly(s, (120, 120, 130), [(x + 118, y + 590), (x + 132, y + 578), (x + 142, y + 600), (x + 130, y + 606)])

        def barn_icon(r):
            x = r.x - 232
            if self.farm_info()["barn"] == "mill":
                poly(s, (210, 195, 170), [(x + 253, 610), (x + 273, 610), (x + 269, 586), (x + 257, 586)], 2)
                draw_mill_blades(s, x + 263, 584, self.t * 0.8, 20)
            else:
                poly(s, (225, 75, 70), [(x + 244, 590), (x + 263, 576), (x + 282, 590), (x + 282, 607), (x + 244, 607)])
                rounded(s, (240, 235, 230), (x + 256, 594, 14, 13), 1, 2)

        def move_icon(r):
            c = r.center
            if FARMS[f.farm_index + 1]["peasants"]:   # башенка — следующая глава средневековая
                poly(s, (200, 195, 188), [(c[0] - 12, c[1] + 18), (c[0] + 12, c[1] + 18), (c[0] + 12, c[1] - 10), (c[0] - 12, c[1] - 10)], 2)
                for dx in (-12, -2, 8):
                    poly(s, (200, 195, 188), [(c[0] + dx, c[1] - 10), (c[0] + dx + 5, c[1] - 10), (c[0] + dx + 5, c[1] - 16), (c[0] + dx, c[1] - 16)], 2)
                pygame.draw.line(s, OUT, (c[0], c[1] - 16), (c[0], c[1] - 26), 2)
                poly(s, (220, 60, 60), [(c[0], c[1] - 26), (c[0] + 10, c[1] - 22), (c[0], c[1] - 18)], 1)
                rounded(s, (110, 75, 50), (c[0] - 4, c[1] + 6, 8, 12), 3, 1)
            else:
                for k in range(3):   # снежинка — следующая ферма зимняя
                    ang = k * math.pi / 3
                    dx, dy = math.cos(ang) * 17, math.sin(ang) * 17
                    pygame.draw.line(s, OUT, (P(c[0] - dx), P(c[1] - dy)), (P(c[0] + dx), P(c[1] + dy)), 6)
                    pygame.draw.line(s, WHITE, (P(c[0] - dx), P(c[1] - dy)), (P(c[0] + dx), P(c[1] + dy)), 3)

        upgrade_on = self.mode == "upgrade"
        self.draw_tavern_button()
        self.icon_button(pygame.Rect(16, 560, 62, 56), "shop", cart, lambda: self.open_modal("shop"), "Магазин",
                         badge=self.shop_has_affordable(),
                         tip="Магазин: удобрения (прибыль x3) и " + ("крестьяне" if self.farm_info()["peasants"] else "фермеры") + "   (S)")
        self.icon_button(pygame.Rect(88, 560, 62, 56), "upgrade", shovel,
                         lambda: setattr(self, "mode", "normal" if self.mode == "upgrade" else "upgrade"), "Прокачка",
                         active=upgrade_on, tip="Прокачка грядок: по 1, по 10, до вехи или на все деньги   (U)")
        self.icon_button(pygame.Rect(160, 560, 62, 56), "tree", lambda r: draw_cur_icon(s, r.centerx, r.centery, 1.2),
                         lambda: self.open_modal("tree"), CUR["title"], badge=f.any_tree_affordable(),
                         tip=f"Дерево улучшений: постоянные бонусы за {CUR['title'].lower()}")
        mill = self.farm_info()["barn"] == "mill"
        self.icon_button(pygame.Rect(232, 560, 62, 56), "mill" if mill else "barn", barn_icon, self.toggle_barn,
                         "Мельница" if mill else "Сарай", badge=self.barn_attention(),
                         tip=("Мельница и пекарня: зерно — мука — хлеб" if mill
                              else "Сарай: звери едят урожай и дают продукты дороже") + "   (B)")
        if f.has_next_farm():
            self.icon_button(pygame.Rect(304, 560, 62, 56), "move", move_icon, lambda: self.open_modal("move"), "Переезд",
                             badge=f.can_move(), active=f.can_move(),
                             tip="Переезд на новую ферму: всё с нуля, но доход x2 и трофей")

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
        rounded(s, PANEL, plate, 8, 3)
        draw_text(s, "РЕЖИМ ПРОКАЧКИ", 20, plate.center, (90, 70, 60), outline=None)
        x = pygame.Rect(plate.right + 6, plate.y + 4, 36, 36)
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

    def draw_toasts(self):
        # на поле — над дорогой; в сарае и мельнице — над карточками, чтобы не закрывать кнопки
        in_barn = self.view == "barn"
        toasts = list(reversed(self.toasts))[:2 if self.view != "field" else 3]
        for n, (text, life) in enumerate(toasts):
            img = render_text(text, 16, WHITE, OUT)
            if self.view in ("tavern", "board"):   # внизу: не мешают балкону, облачкам и запискам
                y = 602 - n * 38
            elif in_barn:
                y = 126 - n * 38
            elif self.tut_visible():               # 3.9: над окошком бармена (в прокачке — наверху: внизу таблички)
                y = 100 + n * 40 if self.mode == "upgrade" else self.tut_box().y - 28 - n * 40
            else:
                y = 512 - n * 40
            r = img.get_rect(center=(W // 2 - (60 if in_barn else 0), y))
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

    def draw_shop(self):
        s, f = self.screen, self.farm
        r = self.panel(580, 470, "МАГАЗИН УЛУЧШЕНИЙ")
        peasants = self.farm_info()["peasants"]
        tabs = (("fert", "Удобрения  x3"), ("farm", "Крестьяне" if peasants else "Фермеры (копят урожай)"))
        for idx, (tab, label) in enumerate(tabs):
            b = pygame.Rect(r.x + 20 + idx * 275, r.y + 66, 265, 38)
            active = self.shop_tab == tab
            rounded(s, (245, 175, 50) if active else BTN_BLUE, b, 10, 3)
            draw_text(s, label, 16, b.center)
            self.zone_btn(b, lambda t=tab: (setattr(self, "shop_tab", t), setattr(self, "shop_page", 0)))

        if self.shop_tab == "farm" and peasants:
            self.draw_peasant_shop(r)
            return
        items = []
        for i in range(N_CROPS):
            if self.shop_tab == "fert":
                if f.levels[i] > 0:
                    items.append((f.fert_cost(i), i, f"Прибыль x3  (куплено: {f.fert[i]})",
                                  lambda i=i: self.buy_shop(f.buy_fert, i), True))
            else:
                if not f.farmers[i]:
                    planted = f.levels[i] > 0
                    items.append((f.farmer_cost(i), i, "Растёт без остановки, урожай копится" if planted else "Сначала посади культуру",
                                  lambda i=i: self.buy_shop(f.buy_farmer, i), planted))
        items.sort(key=lambda it: it[0])
        per = 4
        pages = max(1, math.ceil(len(items) / per))
        self.shop_page = min(self.shop_page, pages - 1)
        if not items:
            draw_text(s, "Все фермеры наняты!" if self.shop_tab == "farm" else "Пока нечего удобрять", 20,
                      (r.centerx, r.centery), (90, 70, 60), outline=None)
        for n, (price, i, sub, cb, enabled) in enumerate(items[self.shop_page * per:(self.shop_page + 1) * per]):
            row = pygame.Rect(r.x + 20, r.y + 118 + n * 70, r.w - 40, 62)
            rounded(s, (255, 245, 190), row, 10, 3)
            icon = pygame.Rect(row.x + 6, row.y + 5, 52, 52)
            rounded(s, (170, 225, 245), icon, 8, 2)
            draw_crop(s, i, icon.centerx, icon.bottom - 10, 1.0)
            draw_text(s, CROPS[i]["name"], 18, (row.x + 70, row.y + 20), (90, 70, 60), anchor="midleft", outline=None)
            draw_text(s, sub, 13, (row.x + 70, row.y + 44), (140, 110, 95), anchor="midleft", outline=None)
            ok = enabled and f.money >= price
            b = pygame.Rect(row.right - 150, row.y + 11, 140, 40)
            rounded(s, BTN_GREEN if ok else BTN_GREY, b, 8, 3)
            draw_text(s, "$" + fmt(price), 17, b.center)
            if enabled:
                self.zone_btn(b, cb, 8)
        if pages > 1:
            draw_text(s, f"{self.shop_page + 1} / {pages}", 16, (r.centerx, r.bottom - 36), (90, 70, 60), outline=None)
            if self.shop_page > 0:
                self.button((r.centerx - 90, r.bottom - 54, 40, 36), "<", lambda: setattr(self, "shop_page", self.shop_page - 1), BTN_BLUE)
            if self.shop_page < pages - 1:
                self.button((r.centerx + 50, r.bottom - 54, 40, 36), ">", lambda: setattr(self, "shop_page", self.shop_page + 1), BTN_BLUE)

    # ------------------------------------------------------------ сарай
    def toggle_barn(self):
        if self.view not in ("field", "barn"):
            return
        self.view = "field" if self.view == "barn" else "barn"
        self.mode = "normal"

    def barn_attention(self):
        f = self.farm
        if self.farm_info()["barn"] == "mill":
            return f.bread > 0 or any(f.m_levels[b] == 0 and f.mill_can_build(b) and f.money >= f.mill_building_cost(b)
                                      for b in (0, 1))
        if f.any_product_ready():
            return True
        return any(f.a_levels[a] == 0 and f.animal_crop_ready(a) and f.money >= f.animal_cost(a)
                   for a in range(N_ANIMALS))

    def do_buy_animal(self, a):
        f = self.farm
        was = f.a_levels[a]
        if f.buy_animal(a):
            self.sfx.play("levelup" if was else "buy")
            self.toast(f"{ANIMALS[a]['name']}: " + ("теперь живёт в сарае!" if was == 0 else f"уровень {f.a_levels[a]}!"), 2)
        else:
            self.toast(f"Не хватает денег: нужно ${fmt(f.animal_cost(a))}, у тебя ${fmt(f.money)}", 2.5)

    def do_buy_keeper(self, a):
        f = self.farm
        if f.buy_keeper(a):
            self.sfx.play("buy")
            self.toast(f"Скотник нанят: сам кормит, {ANIMALS[a]['name'].lower()} не голодает", 2.5)
        else:
            self.toast(f"Не хватает денег: нужно ${fmt(f.keeper_cost(a))}", 2)

    def do_feed(self, a):
        f = self.farm
        crop = ANIMALS[a]["crop"]
        took = f.feed_animal(a)
        if took > 0:
            self.quest("feed")
            self.sfx.play("feed")
            self.floater(self.pen_rect(a).centerx, self.pen_rect(a).y + 205, "корм +$" + fmt(took), (190, 240, 140))
        elif f.stash[crop] <= 0:
            self.toast(f"На грядке «{CROPS[crop]['name']}» пусто — подожди урожай", 2)
        else:
            self.toast("Кормушка полная!", 1.5)

    def do_collect_product(self, a):
        amt = self.farm.collect_product(a)
        if amt:
            self.quest("product")
            self.sfx.play("product")
            r = self.pen_rect(a)
            self.floater(r.centerx, r.y + 60, "+$" + fmt(amt))
            self.toast(f"{ANIMALS[a]['product']}: +$" + fmt(amt), 2)

    def pen_rect(self, a):
        w, gap = 228, 12
        x0 = (W - (N_ANIMALS * w + (N_ANIMALS - 1) * gap)) // 2
        return pygame.Rect(x0 + a * (w + gap), 160, w, 386)

    def build_barn_background(self):
        bg = hd.Surface((W, H))
        if blit_sprite(bg, "backgrounds/barn_inside", 0, 0, 1, "topleft"):
            return bg
        bg.fill((178, 84, 66))
        for x in range(0, W, 44):
            pygame.draw.line(bg, (150, 66, 52), (x, 0), (x, H), 3)
            for y in (60, 230, 400):
                pygame.draw.circle(bg, (130, 60, 48), (x + 22, y + (x // 44) % 3 * 7), 2)
        pygame.draw.rect(bg, (115, 70, 45), (0, 132, W, 18))
        pygame.draw.rect(bg, OUT, (0, 132, W, 18), 3)
        floor = [(0, 470), (W, 470), (W, H), (0, H)]
        poly(bg, (205, 160, 105), floor, 0)
        for y in range(478, H, 22):
            pygame.draw.line(bg, (180, 135, 85), (0, y), (W, y), 2)
        # окно и сено
        rounded(bg, (170, 220, 245), (W // 2 - 50, 20, 100, 80), 4, 4)
        pygame.draw.line(bg, OUT, (W // 2, 20), (W // 2, 100), 3)
        pygame.draw.line(bg, OUT, (W // 2 - 50, 60), (W // 2 + 50, 60), 3)
        for hx, hy in ((W - 230, 70), (W - 175, 95)):
            rounded(bg, (240, 205, 100), (hx, hy, 70, 40), 6, 3)
            for yy in (hy + 13, hy + 26):
                pygame.draw.line(bg, (205, 165, 70), (hx + 6, yy), (hx + 64, yy), 2)
        return bg

    def draw_pen_caption(self, r, text, active):
        """Подпись «Ест: ... -> ...» поверх картинки зверя, на плашке — чтобы её не закрывал крупный спрайт."""
        img = render_text(text, 12, (140, 110, 95), None)
        box = img.get_rect(center=(r.centerx, r.y + 46)).inflate(12, 4)
        plate = hd.Surface(box.size, pygame.SRCALPHA)
        plate.fill((238, 220, 186, 215) if active else (205, 190, 170, 215))
        self.screen.blit(plate, box)
        self.screen.blit(img, img.get_rect(center=box.center))

    def draw_pen(self, a):
        s, f = self.screen, self.farm
        an = ANIMALS[a]
        r = self.pen_rect(a)
        lvl = f.a_levels[a]
        crop = an["crop"]
        brown, soft = (90, 70, 60), (140, 110, 95)
        rounded(s, (238, 220, 186) if lvl else (205, 190, 170), r, 12, 3)
        head = pygame.Rect(r.x, r.y, r.w, 34)
        pygame.draw.rect(s, (150, 98, 62), head, border_top_left_radius=12, border_top_right_radius=12)
        pygame.draw.rect(s, OUT, head, 3, border_top_left_radius=12, border_top_right_radius=12)
        draw_text(s, an["name"] + (f"  ур. {lvl}" if lvl else ""), 17, head.center)

        # стойло и животное
        ellipse(s, (240, 210, 110), r.centerx, r.y + 150, 170, 34, ow=0)
        hungry = lvl > 0 and f.a_feed[a] <= 0
        if lvl:
            ANIMAL_DRAW[a](s, r.centerx - (10 if a in (1, 2) else 0), r.y + 156, 1.15, self.t + a, not hungry, THEME["snow"])
        else:
            ANIMAL_DRAW[a](s, r.centerx - (10 if a in (1, 2) else 0), r.y + 156, 1.15, 0, False, THEME["snow"])
            shade = hd.Surface((r.w - 20, 110), pygame.SRCALPHA)
            shade.fill((205, 190, 170, 170))
            s.blit(shade, (r.x + 10, r.y + 56))
        self.draw_pen_caption(r, f"Ест: {CROPS[crop]['name']}  ->  {an['product']} x{f.product_ratio(a, max(1, lvl)):.1f}", lvl > 0)
        # забор стойла
        for xx in range(r.x + 14, r.right - 10, 26):
            pygame.draw.rect(s, OUT, (xx - 1, r.y + 150, 8, 26))
            pygame.draw.rect(s, (225, 200, 160), (xx + 1, r.y + 152, 4, 22))
        pygame.draw.line(s, OUT, (r.x + 10, r.y + 160), (r.right - 10, r.y + 160), 5)
        pygame.draw.line(s, (225, 200, 160), (r.x + 10, r.y + 160), (r.right - 10, r.y + 160), 2)

        if lvl == 0:
            if not f.animal_crop_ready(a):
                draw_text(s, f"Сначала посади: {CROPS[crop]['name']}", 14, (r.centerx, r.y + 220), (190, 80, 70), outline=None)
            else:
                draw_text(s, f"Будет есть: {CROPS[crop]['name']}", 14, (r.centerx, r.y + 210), brown, outline=None)
                draw_text_fit(s, f"продукт в {an['ratio']:g} раза дороже корма", 12, (r.centerx, r.y + 232), r.w - 20,
                              soft, outline=None)
                draw_text_fit(s, "с уровнем ест меньше, а продукт дороже", 11, (r.centerx, r.y + 252), r.w - 20,
                              soft, outline=None)
            b = pygame.Rect(r.x + 16, r.bottom - 64, r.w - 32, 46)
            ok = f.animal_crop_ready(a) and f.money >= f.animal_cost(a)
            rounded(s, BTN_GREEN if ok else BTN_GREY, b, 10, 3)
            draw_text(s, "Купить $" + fmt(f.animal_cost(a)), 18, b.center)
            if f.animal_crop_ready(a):
                self.zone_btn(b, lambda a=a: self.do_buy_animal(a))
            return

        # готовые продукты
        if f.a_store[a] > 0:
            px, py = r.right - 36, r.y + 76 + math.sin(self.t * 4 + a) * 3
            pygame.draw.circle(s, OUT, (P(px), P(py)), 22)
            pygame.draw.circle(s, (255, 245, 200), (P(px), P(py)), 20)
            draw_product(s, a, px, py, 1.2)
            draw_text(s, "$" + fmt(f.a_store[a]), 15, (px, py + 30), (255, 235, 120))
        if hungry:
            draw_text(s, "Голодн" + ("ы" if a == 3 else "а") + "!", 15, (r.centerx - 50, r.y + 76), (255, 200, 190))
        self.zone((r.x + 8, r.y + 56, r.w - 16, 120), lambda a=a: self.do_collect_product(a) if self.farm.a_store[a] > 0 else self.do_feed(a))

        # полоски: производство и кормушка
        bar_w = r.w - 40
        t = an["time"]
        draw_bar(s, (r.x + 20, r.y + 184, bar_w, 12), f.a_prog[a] / t if f.a_feed[a] > 0 else 0, GOLD)
        cap = f.feeder_cap(a)
        draw_text(s, f"Корм: ${fmt(f.a_feed[a])} / ${fmt(cap)}", 12, (r.centerx, r.y + 209), brown, outline=None)
        draw_bar(s, (r.x + 20, r.y + 219, bar_w, 12), f.a_feed[a] / cap if cap > 0 else 0, (150, 210, 90))
        draw_text_fit(s, f"Ест ${fmt(f.eat_rate(a))}/с, даёт ${fmt(f.animal_income(a))}/с · на грядке ${fmt(f.stash[crop])}",
                      11, (r.centerx, r.y + 244), r.w - 16, soft, outline=None)

        # кнопки
        b1 = pygame.Rect(r.x + 14, r.y + 258, r.w - 28, 36)
        if f.a_keeper[a]:
            rounded(s, (200, 230, 180), b1, 9, 2)
            left = max(0.0, KEEPER_INTERVAL - f.a_keeper_t[a])
            draw_text(s, f"Скотник придёт через {math.ceil(left)} с", 14, b1.center, (60, 120, 50), outline=None)
        else:
            ok = f.stash[crop] > 0 and f.a_feed[a] < cap
            rounded(s, BTN_GREEN if ok else BTN_GREY, b1, 9, 3)
            draw_text(s, "Покормить", 16, b1.center)
            self.zone_btn(b1, lambda a=a: self.do_feed(a), 9)
        b2 = pygame.Rect(r.x + 14, r.y + 300, r.w - 28, 36)
        if lvl >= ANIMAL_MAX_LVL:
            rounded(s, (250, 212, 90), b2, 9, 2)
            draw_text(s, "Макс. уровень", 15, b2.center, brown, outline=None)
        else:
            price = f.animal_cost(a)
            rounded(s, BTN_BLUE if f.money >= price else BTN_GREY, b2, 9, 3)
            # следующий уровень: еды −10%, продукт дороже
            draw_text_fit(s, f"Ур. {lvl + 1}: x{f.product_ratio(a, lvl + 1):.1f}, еды -10%  ${fmt(price)}", 14, b2.center, b2.w - 12)
            self.zone_btn(b2, lambda a=a: self.do_buy_animal(a), 9)
        if not f.a_keeper[a]:
            b3 = pygame.Rect(r.x + 14, r.y + 342, r.w - 28, 36)
            price = f.keeper_cost(a)
            rounded(s, (235, 170, 70) if f.money >= price else BTN_GREY, b3, 9, 3)
            draw_text(s, f"Скотник: ${fmt(price)}", 15, b3.center)
            self.zone_btn(b3, lambda a=a: self.do_buy_keeper(a), 9)

    # ------------------------------------------------------------ мельница и пекарня
    def build_mill_background(self):
        bg = hd.Surface((W, H))
        if blit_sprite(bg, "backgrounds/mill_inside", 0, 0, 1, "topleft"):
            return bg
        bg.fill((150, 140, 128))
        for row, y in enumerate(range(0, 470, 34)):
            for x in range(-40 if row % 2 else 0, W, 80):
                shade = 160 + (x * 7 + y * 3) % 25
                rounded(bg, (shade, shade - 8, shade - 18), (x + 2, y + 2, 76, 30), 4, 2, (110, 100, 90))
        pygame.draw.rect(bg, (115, 75, 45), (0, 132, W, 18))
        pygame.draw.rect(bg, OUT, (0, 132, W, 18), 3)
        poly(bg, (190, 145, 95), [(0, 470), (W, 470), (W, H), (0, H)], 0)
        for y in range(478, H, 22):
            pygame.draw.line(bg, (165, 120, 75), (0, y), (W, y), 2)
        for sx in (W - 240, W - 180):   # мешки с мукой
            blob(bg, (240, 232, 215), [(sx, 100, 26), (sx + 4, 74, 18)], 3)
            draw_text(bg, "МУКА", 11, (sx, 102), (150, 120, 90), outline=None)
        rounded(bg, (170, 220, 245), (W // 2 - 50, 20, 100, 80), 4, 4)
        pygame.draw.line(bg, OUT, (W // 2, 20), (W // 2, 100), 3)
        return bg

    # ------------------------------------------------------------ разбойники
    def bandit_delay(self):
        return random.uniform(BANDIT_MIN, BANDIT_MAX) * 1.5 ** self.farm.up("guards")

    def spawn_bandit(self):
        f = self.farm
        if not self.farm_info()["bandits"]:
            self.bandit_timer = self.bandit_delay()
            return
        plots = [k for k in range(N_CROPS) if f.levels[k] > 0]
        if not plots:
            self.bandit_timer = self.bandit_delay()
            return
        plots.sort(key=lambda k: f.stash[k], reverse=True)
        k = random.choice(plots[:3])
        cx, cy = crop_center(k)
        d = 1 if cx < W / 2 else -1
        sx = -50.0 if d == 1 else W + 50.0
        self.bandit = dict(k=k, x=sx, y=random.uniform(470, 500), tx=cx - 40 * d, ty=cy + 18, d=d,
                           phase="walk", timer=0.0, sack=0.0, step_i=0, coin_t=0.0)
        self.toast(f"Разбойник крадётся к грядке «{CROPS[k]['name']}»! Прогони его!", 3.5)
        self.sfx.play("bandit")

    def update_bandit(self, dt):
        if self.bandit is None:
            if not self.farm_info()["bandits"]:
                return
            self.bandit_timer -= dt
            if self.bandit_timer <= 0:
                self.spawn_bandit()
            return
        b, f = self.bandit, self.farm
        b["timer"] += dt
        b.setdefault("step_i", 0)
        b.setdefault("coin_t", 0.0)
        period = self.BANDIT_STEP.get(b["phase"])
        if period:                                            # шаг — облачко пыли из-под ног
            i = int(b["timer"] / period)
            if i != b["step_i"]:
                b["step_i"] = i
                self.fx.dust(b["x"] - b["d"] * 6, b["y"], n=1 if b["phase"] == "walk" else 2, size=(3, 6),
                             drift=-b["d"] * 20, alpha=110)
        coin = lambda surf, x, y, sc: draw_coin(surf, x, y, 11 * sc)
        if b["phase"] == "steal" and f.stash[b["k"]] > 0:     # монетки с грядки летят в мешок
            b["coin_t"] += dt
            if b["coin_t"] >= 0.45:
                b["coin_t"] = 0.0
                cx, cy = crop_center(b["k"])
                self.fx.fly((cx + random.uniform(-25, 25), cy - 10), (b["x"] - b["d"] * 12, b["y"] - 38), coin,
                            dur=0.45, lift=45, spread=12, size=COIN_SMALL, shrink=0.75)
        elif b["phase"] == "escape" and b["sack"] > 0:        # убегает — монетки сыплются из мешка
            b["coin_t"] += dt
            if b["coin_t"] >= 0.5:
                b["coin_t"] = 0.0
                self.fx.drop(b["x"] - b["d"] * 16, b["y"] - 30, coin, ground=b["y"] + random.uniform(-2, 4),
                             vx=-b["d"] * random.uniform(20, 60), vy=-random.uniform(120, 180), life=1.1, size=COIN_SMALL)
        if b["phase"] == "walk":
            dx, dy = b["tx"] - b["x"], b["ty"] - b["y"]
            dist = math.hypot(dx, dy)
            step = 170 * dt
            if dist <= step:
                b["x"], b["y"] = b["tx"], b["ty"]
                b["phase"], b["timer"] = "steal", 0.0
            else:
                b["x"] += dx / dist * step
                b["y"] += dy / dist * step
        elif b["phase"] == "steal":
            k = b["k"]
            take = min(f.stash[k], f.stash[k] * BANDIT_STEAL * 0.7 ** f.up("traps") * dt)
            f.stash[k] -= take
            b["sack"] += take
            if b["timer"] >= BANDIT_TIME:
                b["phase"], b["timer"] = "escape", 0.0
                if b["sack"] > 0:
                    self.toast(f"Разбойник унёс ${fmt(b['sack'])}!", 3)
        else:   # escape / flee — бежит к краю экрана
            speed = 330 if b["phase"] == "flee" else 220
            ex = -80 if b["x"] < W / 2 else W + 80
            b["d"] = -1 if ex < 0 else 1
            b["x"] += b["d"] * speed * dt
            b["y"] += (500 - b["y"]) * min(1.0, dt * 2)
            if b["x"] < -70 or b["x"] > W + 70:
                self.bandit = None
                self.bandit_timer = self.bandit_delay()

    def shoo_bandit(self):
        b = self.bandit
        if not b or b["phase"] not in ("walk", "steal"):
            return
        self.sfx.play("shoo")
        self.quest("bandit")
        self.fx.dust(b["x"], b["y"], n=4, size=(4, 8), spread=14, alpha=140)
        if b["sack"] > 0:                                     # монетки летят из мешка обратно на грядку
            cx, cy = crop_center(b["k"])
            coin = lambda surf, x, y, sc: draw_coin(surf, x, y, 11 * sc)
            for i in range(6):
                self.fx.fly((b["x"] - b["d"] * 12, b["y"] - 38), (cx + random.uniform(-20, 20), cy - 8), coin,
                            dur=0.5, delay=i * 0.05, lift=55, spread=18, size=COIN_SMALL, shrink=1.0)
            self.farm.stash[b["k"]] += b["sack"]
            self.floater(b["x"], b["y"] - 70, "Вернул $" + fmt(b["sack"]), (200, 240, 160))
        else:
            self.floater(b["x"], b["y"] - 70, "Пошёл вон!", (230, 240, 255))
        b["sack"] = 0.0
        b["phase"], b["timer"] = "flee", 0.0

    BANDIT_STEP = {"walk": 0.5, "escape": 0.3, "flee": 0.26}   # длина шага, с

    def bandit_pose(self, b, d):
        """Разбойник -> (подскок, sx, sy, наклон°). Крадётся пригнувшись на цыпочках; у грядки присел и шарит;
        с добычей бежит вприпрыжку (мешок раскачивает его из стороны в сторону); прогнали — удирает."""
        t, ph = b["timer"], b["phase"]
        if ph == "steal":
            return 0.0, 1.0, 0.93 + 0.02 * math.sin(t * 12), -d * 9 + 3 * math.sin(t * 9)
        period = self.BANDIT_STEP.get(ph, 0.3)
        u = (t / period) % 1.0
        s = math.sin(math.pi * u)
        if ph == "walk":
            return 3 * s, 1.0, 0.94 + 0.03 * s, -d * 8 + 2 * math.sin(2 * math.pi * u)
        lean = 12 if ph == "flee" else 6
        rock = 5 * math.sin(2 * math.pi * u) if b["sack"] > 0 else 2 * math.sin(2 * math.pi * u)
        land = max(0.0, 1 - u / 0.15)
        return (6 if ph == "flee" else 5) * s, 1 + 0.06 * land, 1 - 0.07 * land, -d * lean + rock

    def draw_bandit_layer(self):
        b = self.bandit
        if b is None:
            return
        running = b["phase"] != "steal"
        d = b["d"] if b["phase"] != "steal" else (1 if crop_center(b["k"])[0] > b["x"] else -1)
        pose = self.bandit_pose(b, d)
        draw_shadow(self.screen, b["x"], b["y"] + 1, 50 * (1 - pose[0] / 30), 11, 70)
        draw_bandit(self.screen, b["x"], b["y"], d, b["timer"], b["sack"], running, pose)
        if b["phase"] == "steal":
            left = max(0.0, BANDIT_TIME - b["timer"])
            draw_bar(self.screen, (P(b["x"] - 22), P(b["y"] - 76), 44, 8), left / BANDIT_TIME, (230, 90, 80))
        if b["phase"] in ("walk", "steal") and self.modal is None:
            self.zone((P(b["x"] - 30), P(b["y"] - 70), 60, 74), self.shoo_bandit)

    def draw_barn_view(self):
        if self.farm_info()["barn"] == "mill":
            self.draw_mill_view()
            return
        s = self.screen
        s.blit(self.barn_bg, (0, 0))
        plate = pygame.Rect(W // 2 + 70, 26, 200, 44)
        rounded(s, PANEL, plate, 8, 3)
        draw_text(s, "САРАЙ", 22, plate.center, (90, 70, 60), outline=None)
        for a in range(N_ANIMALS):
            self.draw_pen(a)
        for x, y, text, life, color in self.floaters:
            draw_text(s, text, 18, (x, y), color)

    def draw_tree(self):
        s, f = self.screen, self.farm
        r = self.panel(820, 560, CUR["tree"])
        brown, soft = (90, 70, 60), (150, 115, 100)
        draw_cur_icon(s, r.x + 40, r.y + 80, 0.9)
        draw_text(s, f"{f.leaves} {CUR['gen']}   доход {fmt_mult(f.home_leaves)}", 18, (r.x + 64, r.y + 80), brown,
                  anchor="midleft", outline=None)
        draw_text(s, f"Каждая непотраченная {CUR['one']} даёт +2% к доходу" if CUR["icon"] == "seal" else "Каждый непотраченный лист даёт +2% к доходу", 13, (r.right - 24, r.y + 80), soft,
                  anchor="midright", outline=None)
        col_w = (r.w - 40) // len(TREE)
        for bi, (bname, nodes) in enumerate(TREE):
            cx = r.x + 20 + bi * col_w + col_w // 2
            draw_text(s, bname, 17, (cx, r.y + 114), brown, outline=None)
            prev = None
            for ni, node in enumerate(nodes):
                nid = node["id"]
                nr = pygame.Rect(0, 0, col_w - 18, 58)
                nr.center = (cx, r.y + 160 + ni * 74)
                if prev is not None:
                    done = f.up(nodes[ni - 1]["id"]) > 0
                    pygame.draw.line(s, OUT, (cx, prev.bottom), (cx, nr.top), 7)
                    pygame.draw.line(s, (120, 210, 100) if done else (190, 180, 175), (cx, prev.bottom), (cx, nr.top), 3)
                lvl, mx, cost = f.up(nid), len(node["costs"]), f.tree_cost(nid)
                if cost is None:
                    color = (250, 212, 90)
                elif not f.tree_available(nid):
                    color = (205, 200, 196)
                elif f.leaves >= cost:
                    color = (150, 222, 120)
                else:
                    color = (175, 215, 240)
                selected = self.tree_sel == nid
                rounded(s, color, nr, 10, 4 if selected else 2, (230, 90, 60) if selected else OUT)
                draw_text(s, node["name"], 13, (nr.centerx, nr.y + 15), brown, outline=None)
                for k in range(mx):  # точки уровней
                    px = nr.x + 12 + k * min(12, (nr.w - 80) // max(1, mx))
                    pygame.draw.circle(s, OUT, (px, nr.bottom - 15), 5)
                    pygame.draw.circle(s, (90, 190, 80) if k < lvl else WHITE, (px, nr.bottom - 15), 4)
                if cost is None:
                    draw_text(s, "МАКС", 13, (nr.right - 10, nr.bottom - 15), (170, 120, 20), anchor="midright", outline=None)
                elif not f.tree_available(nid):
                    draw_text(s, "закрыто", 12, (nr.right - 10, nr.bottom - 15), soft, anchor="midright", outline=None)
                else:
                    draw_text(s, str(cost), 14, (nr.right - 26, nr.bottom - 15), brown, anchor="midright", outline=None)
                    draw_cur_icon(s, nr.right - 15, nr.bottom - 15, 0.45)
                self.zone_btn(nr, lambda n=nid: setattr(self, "tree_sel", n))
                prev = nr

        info = pygame.Rect(r.x + 20, r.bottom - 112, r.w - 40, 96)
        rounded(s, (255, 245, 210), info, 10, 2)
        if self.tree_sel not in TREE_NODES:     # выбранное улучшение осталось от дерева прошлой фермы (после переезда)
            self.tree_sel = None
        if self.tree_sel is None:
            draw_text(s, "Нажми на улучшение, чтобы узнать, что оно даёт", 16, info.center, soft, outline=None)
            return
        node = TREE_NODES[self.tree_sel]
        nid = node["id"]
        lvl, cost = f.up(nid), f.tree_cost(nid)
        draw_text(s, f"{node['name']}  (ур. {lvl}/{len(node['costs'])})", 18, (info.x + 16, info.y + 20), brown,
                  anchor="midleft", outline=None)
        draw_text(s, "Сейчас: " + node["eff"](lvl), 14, (info.x + 16, info.y + 48), brown, anchor="midleft", outline=None)
        if cost is None:
            draw_text(s, "Максимальный уровень!", 14, (info.x + 16, info.y + 72), (170, 120, 20), anchor="midleft", outline=None)
            return
        draw_text(s, "Дальше: " + node["eff"](lvl + 1), 14, (info.x + 16, info.y + 72), (60, 140, 50),
                  anchor="midleft", outline=None)
        b = pygame.Rect(info.right - 210, info.y + 24, 194, 48)
        if not f.tree_available(nid):
            need = TREE_NODES[node["prev"]]["name"]
            # две строки, прижаты к правому краю, чтобы длинное название не вылезало за рамку
            draw_text(s, "Сначала возьми", 14, (info.right - 16, info.y + 36), (190, 80, 70), anchor="midright", outline=None)
            draw_text(s, f"«{need}»", 14, (info.right - 16, info.y + 58), (190, 80, 70), anchor="midright", outline=None)
            return
        ok = f.leaves >= cost
        rounded(s, BTN_GREEN if ok else BTN_GREY, b, 10, 3)
        draw_text(s, f"Купить: {cost}", 18, (b.centerx - 12, b.centery))
        draw_cur_icon(s, b.right - 26, b.centery, 0.55)
        spent = max(0, cost - (f.leaves - f.home_leaves))     # столько «домашних» листьев перестанут давать +2%
        if ok and spent:
            draw_text_fit(s, f"доход от {CUR['gen']}: {fmt_mult(f.home_leaves)} -> {fmt_mult(f.home_leaves - spent)}",
                          12, (b.centerx, info.bottom - 11), b.w + 12, soft, outline=None)
        if ok:
            self.zone_btn(b, lambda: self.buy_tree(nid))

    def buy_tree(self, nid):
        if self.farm.buy_tree(nid):
            self.quest("tree")
            self.sfx.play("levelup")
            self.toast(f"Улучшено: {TREE_NODES[nid]['name']}!", 2)
            if nid in ("sq_often",):
                self.squirrel_timer = min(self.squirrel_timer, self.squirrel_delay())
            if nid in ("scarecrow",):
                self.crow_timer = max(self.crow_timer, self.crow_delay())

    def draw_peasant_shop(self, r):
        s, f = self.screen, self.farm
        brown, soft = (90, 70, 60), (140, 110, 95)
        row = pygame.Rect(r.x + 20, r.y + 124, r.w - 40, 90)
        rounded(s, (255, 245, 190), row, 10, 3)
        icon = pygame.Rect(row.x + 10, row.y + 15, 60, 60)
        rounded(s, (200, 230, 170), icon, 8, 2)
        draw_peasant_head(s, icon.centerx, icon.centery + 2, 2.2)
        draw_text(s, "Нанять крестьянина", 19, (row.x + 86, row.y + 26), brown, anchor="midleft", outline=None)
        draw_text(s, f"Всего {f.peasants} из {PEASANT_MAX}, свободно {f.free_peasants()}", 14, (row.x + 86, row.y + 54),
                  soft, anchor="midleft", outline=None)
        b = pygame.Rect(row.right - 160, row.y + 22, 146, 46)
        if f.peasants >= PEASANT_MAX:
            rounded(s, (250, 212, 90), b, 8, 2)
            draw_text(s, "Все наняты", 15, b.center, brown, outline=None)
        else:
            ok = f.money >= f.peasant_cost()
            rounded(s, BTN_GREEN if ok else BTN_GREY, b, 8, 3)
            draw_text(s, "$" + fmt(f.peasant_cost()), 17, b.center)
            self.zone_btn(b, self.do_hire_peasant, 8)
        tips = [
            "Крестьянин на грядке — она растёт без остановки и копит урожай (кнопка у грядки).",
            "Крестьяне на мельнице мелют зерно, в пекарне пекут хлеб.",
            "Их можно в любой момент переставить: снять с грядки и отправить на мельницу.",
        ]
        for n, t in enumerate(tips):
            draw_text_fit(s, t, 13, (r.centerx, r.y + 250 + n * 26), r.w - 50, soft, outline=None)

    def do_hire_peasant(self):
        f = self.farm
        price = f.peasant_cost()
        if f.hire_peasant():
            self.quest("peasant")
            self.sfx.play("buy")
            self.toast(f"Нанят крестьянин! Свободно: {f.free_peasants()}", 2)
        else:
            self.toast(f"Не хватает денег: нужно ${fmt(price)}", 2)

    def do_toggle_peasant(self, k):
        f = self.farm
        was = f.farmers[k]
        if f.toggle_peasant(k):
            cx, cy = crop_center(k)
            self.floater(cx + 50, cy + 10, "снят" if was else "за работу!", (220, 240, 200))
        else:
            self.toast("Нет свободных крестьян: найми в магазине или сними с другой грядки", 2.5)

    def buy_shop(self, fn, i):
        price = self.farm.fert_cost(i) if fn == self.farm.buy_fert else self.farm.farmer_cost(i)
        if fn(i):
            self.sfx.play("buy")
            self.toast(f"Куплено для: {CROPS[i]['name']}")
        else:
            self.toast(f"Не хватает денег: нужно ${fmt(price)}, у тебя ${fmt(self.farm.money)}", 2.5)

    def draw_truck_modal(self):
        s, f = self.screen, self.farm
        tier = self.truck_tier()
        name, color, _ = TRUCK_TIERS[tier]
        r = self.panel(600, 440, name.upper())
        self.draw_vehicle(r.centerx + 30, r.y + 160, color, tier=tier)
        p = f.potential_leaves()
        brown = (90, 70, 60)
        y = r.y + 182
        draw_text(s, f"{self.farm_info()['buyer_cap']} заберёт урожай и деньги в обмен на {CUR['title'].lower()}!", 15, (r.centerx, y), brown, outline=None)
        draw_text(s, f"Заработано за забег (с урожаем на грядках): ${fmt(f.run_total())}", 17, (r.centerx, y + 28), brown, outline=None)
        draw_cur_icon(s, r.centerx - 95, y + 66, 0.9)
        draw_text(s, f"+{p} {CUR['gen']}", 28, (r.centerx + 15, y + 66), (110, 220, 90))
        after = f.home_leaves + p
        draw_text(s, f"Множитель дохода: {fmt_mult(f.home_leaves)}  ->  {fmt_mult(after)}   (+2% за каждую)",
                  17, (r.centerx, y + 104), brown, outline=None)
        draw_text_fit(s, f"Ещё ${fmt(f.money_for_next_leaf())} — и будет ещё +1. Чем дольше копишь, тем больше!",
                      13, (r.centerx, y + 130), r.w - 50, (140, 110, 95), outline=None)
        draw_text_fit(s, f"Грядки, здания и работники обнулятся. {CUR['title']} и дерево остаются (до переезда).",
                      13, (r.centerx, y + 150), r.w - 50, (190, 80, 70), outline=None)
        self.button((r.centerx - 230, r.bottom - 76, 250, 50), "Продать ферму!", self.sell_farm, BTN_GREEN, p > 0, 20)
        self.button((r.centerx + 40, r.bottom - 76, 190, 50), "Ещё покоплю", self.close_modal, BTN_BLUE, True, 18)

    def toggle_music(self):
        self.music.toggle_mute()
        self.toast("Музыка выключена (M — включить)" if self.music.muted else "Музыка включена", 1.5)

    def set_volume_from_x(self, drag, x):
        """Ползунок громкости: позиция мыши по ширине полоски -> 0..100% (шаг 5%). drag = (полоска, "music"/"sfx")."""
        rect, which = drag
        frac = max(0.0, min(1.0, (x - rect.x) / max(1, rect.w)))
        vol = round(frac * 20) / 20
        self.music.muted = False
        if which == "music":
            self.music.volume = vol
        else:
            self.sfx.volume = vol
        self.music.apply_volume()

    def start_volume_drag(self, rect, which="music"):
        self.volume_drag = (rect, which)
        self.set_volume_from_x(self.volume_drag, self.click_pos[0])

    def mouse_up(self):
        if self.volume_drag and self.volume_drag[1] == "sfx":
            self.sfx.play("click")        # услышать новую громкость звуков
        self.volume_drag = None

    def quit_game(self):
        self.save()
        pygame.quit()
        sys.exit()

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
        try:
            pygame.display.toggle_fullscreen()
            self.fullscreen = not self.fullscreen
        except pygame.error as e:
            self.toast(f"Не получилось переключить экран: {e}", 3)

    SETTINGS_TABS = (("sound", "Звук"), ("screen", "Экран"), ("game", "Игра"))

    def draw_settings(self):
        s, m = self.screen, self.music
        r = self.panel(540, 470, "НАСТРОЙКИ")
        soft = (150, 125, 110)
        x, w = r.x + 30, r.w - 60
        # вкладки
        tw = (w - 2 * 10) // 3
        for i, (key, title) in enumerate(self.SETTINGS_TABS):
            on = self.settings_tab == key
            self.button((x + i * (tw + 10), r.y + 72, tw, 42), title, lambda k=key: setattr(self, "settings_tab", k),
                        (245, 175, 50) if on else BTN_BLUE, True, 18)
        y = r.y + 136
        tab = self.settings_tab
        if tab == "sound":
            if m.ok and m.current is None:
                draw_text(s, "нет файла в assets/music/", 12, (x + w, y + 20), soft, anchor="midright", outline=None)
            self.volume_slider("Музыка", m.volume, "music", x, y + 20, w)
            self.volume_slider("Звуки", self.sfx.volume, "sfx", x, y + 82, w)
            self.button((x, y + 138, w, 46), ("Включить звук" if m.muted else "Выключить звук") + "   (M)",
                        self.toggle_music, BTN_GREEN if m.muted else (230, 110, 100), m.ok, 18)
        elif tab == "screen":
            self.button((x, y, w, 46), f"Экран: {'во весь экран' if self.fullscreen else 'в окне'}   (F11)",
                        self.toggle_fullscreen, (150, 120, 220), True, 18)
            active = "auto" if self.hd_k != 1 else "off"
            label = "Чёткость: HD" if self.hd_mode == "auto" else "Чёткость: обычная"
            self.button((x, y + 56, w, 46), label + ("*" if self.hd_mode != active else ""), self.toggle_hd,
                        (120, 160, 220), True, 18)
            if self.hd_mode != active:
                info = "* чёткость поменяется после перезапуска игры"
            else:
                info = f"картинка {self.canvas[0]}×{self.canvas[1]}" + (f"  (HD x{self.hd_k:g})" if self.hd_k != 1 else "")
            draw_text(s, info, 13, (r.centerx, y + 116), soft, outline=None)
            draw_text(s, "Кадров в секунду:", 17, (x, y + 160), (90, 70, 60), anchor="midleft", outline=None)
            bw = 70
            for i, fps in enumerate(FPS_LIMITS):
                on = self.fps_limit == fps
                self.button((x + w - (3 - i) * (bw + 8) + 8, y + 140, bw, 40), str(fps),
                            lambda v=fps: self.set_option("fps_limit", v), (245, 175, 50) if on else BTN_BLUE, True, 18)
            self.button((x, y + 196, w, 46), "Счётчик кадров: " + ("показан" if self.show_fps else "скрыт"),
                        lambda: self.set_option("show_fps", not self.show_fps),
                        BTN_GREEN if self.show_fps else BTN_GREY, True, 18)
        else:
            self.button((x, y, w, 46), "Статистика фермы", lambda: self.open_modal("stats"), (235, 170, 70), True, 18)
            self.button((x, y + 56, w, 46), "Подсказки у кнопок: " + ("включены" if self.show_tips else "выключены"),
                        lambda: self.set_option("show_tips", not self.show_tips),
                        BTN_GREEN if self.show_tips else BTN_GREY, True, 18)
            draw_text(s, "подсказка появится, если задержать курсор на кнопке", 13, (r.centerx, y + 116), soft,
                      outline=None)
            self.button((x, y + 196, w, 46), "Обучение заново (бармен)", self.tut_restart, (150, 120, 220), True, 17)
            half = (w - 12) // 2
            self.button((x, y + 140, half, 46), "Сохранить", lambda: (self.save(), self.toast("Сохранено!")), BTN_BLUE)
            label = "Точно? Ещё раз!" if self.confirm_reset else "Сбросить всё"
            self.button((x + w - half, y + 140, half, 46), label, self.reset_everything, (230, 90, 80), True, 17)
        self.button((r.centerx - 165, r.bottom - 72, 160, 46), "Закрыть", self.close_modal, BTN_GREEN)
        self.button((r.centerx + 15, r.bottom - 72, 180, 46), "Выйти из игры", self.quit_game, (150, 110, 100), True, 17)
        draw_text(s, f"версия {GAME_VERSION}", 12, (r.x + 26, r.y + 56), soft, anchor="midleft", outline=None)

    def set_option(self, name, value):
        setattr(self, name, value)
        self.save()

    def volume_slider(self, title, vol, which, x, y, w):
        s, m = self.screen, self.music
        brown = (90, 70, 60)
        if not m.ok:
            note = "звук недоступен"
        elif m.muted:
            note = "выкл"
        else:
            note = f"{round(vol * 100)}%"
        draw_text(s, f"{title}: {note}", 17, (x, y), brown, anchor="midleft", outline=None)
        bar = pygame.Rect(x + 12, y + 18, w - 24, 22)
        frac = 0.0 if m.muted else vol
        draw_bar(s, bar, frac, BTN_GREY if m.muted else (120, 196, 96))
        skin.draw_knob(s, bar.x + bar.w * frac, bar.centery, m.muted)
        if m.ok:
            self.zone(bar.inflate(28, 24), lambda b=bar: self.start_volume_drag(b, which))

    def draw_stats(self):
        s, f = self.screen, self.farm
        r = self.panel(560, 440, "СТАТИСТИКА")
        brown = (90, 70, 60)
        lines = [
            f"Ферма: {self.farm_info()['name']} ({f.farm_index + 1}/{len(FARMS)}), бонус ферм x{FARM_BONUS ** f.farm_index}",
            f"Всего заработано: ${fmt(f.total_earned)}",
            f"За этот забег: ${fmt(f.run_earned)}  (+${fmt(f.total_stash())} на грядках)",
            f"Ферм продано: {f.prestiges}",
            f"{CUR['title']}: {f.leaves}  (доход {fmt_mult(f.home_leaves)})",
            f"{CUR['title']} за продажу сейчас: {f.potential_leaves()}",
        ]
        if f.farm_index > 0:
            lines.append("Трофеи: " + ", ".join(FARMS[i]["trophy"]["name"] for i in range(f.farm_index)))
        if f.has_next_farm():
            lines.append(f"До переезда: ${fmt(max(0.0, f.move_threshold() - f.run_total()))}")
        for n, line in enumerate(lines):
            draw_text_fit(s, line, 17, (r.x + 34, r.y + 84 + n * 32), r.w - 68, brown, anchor="midleft", outline=None)
        self.button((r.centerx - 100, r.bottom - 72, 200, 46), "<  Назад", lambda: self.open_modal("settings"), BTN_BLUE)

    def draw_move(self):
        s, f = self.screen, self.farm
        nxt = FARMS[f.farm_index + 1]
        trophy = self.farm_info()["trophy"]
        r = self.panel(640, 440, "ПЕРЕЕЗД")
        brown, soft = (90, 70, 60), (140, 110, 95)
        draw_text(s, f"{self.farm_info()['name']}  ->  {nxt['name']}", 22, (r.centerx, r.y + 86), (70, 120, 190))
        lines = [
            ("Новая глава: всё начинается с нуля — деньги, грядки, здания,", (190, 80, 70)),
            (f"{CUR['title'].lower()} и дерево улучшений.", (190, 80, 70)),
            (f"С собой: доход x{FARM_BONUS} навсегда за каждую пройденную ферму", brown),
            (f"и трофей «{trophy['name']}»: {trophy['text']}.", brown),
        ]
        if nxt["peasants"]:
            lines.append(("Там: крестьяне, мельница с пекарней, разбойники, печати и привилегии короля.", soft))
        elif nxt["frost"]:
            lines.append(("Там: вместо дождя оттепель, вместо вороны мороз — лёд разбивай кликами.", soft))
        for n, (line, col) in enumerate(lines):
            draw_text_fit(s, line, 15, (r.centerx, r.y + 128 + n * 26), r.w - 56, col, outline=None)
        need = f.move_threshold()
        have = f.run_total()
        draw_text(s, f"Нужно заработать за забег: ${fmt(need)}", 16, (r.centerx, r.y + 270), brown, outline=None)
        draw_bar(s, (r.x + 60, r.y + 288, r.w - 120, 18), have / need, (120, 200, 255))
        draw_text(s, f"${fmt(have)}", 13, (r.centerx, r.y + 297))
        self.button((r.centerx - 230, r.bottom - 76, 250, 50), "Переехать!", self.do_move, (245, 175, 50), f.can_move(), 20)
        self.button((r.centerx + 40, r.bottom - 76, 190, 50), "Позже", self.close_modal, BTN_BLUE, True, 18)

    # ------------------------------------------------------------ режим разработчика
    def dev_actions(self):
        f = self.farm
        pm = f.price_mult

        def money():
            f.money = max(f.money, 1000 * pm) * 1000
        def leaves():
            f.leaves += 1000
            f.home_leaves += 1000
        def to_truck():
            need = (TRUCK_MIN_LEAVES / f.truck_mult() / LEAF_FACTOR) ** 2 * LEAF_UNIT * pm
            f.earn(max(0.0, need - f.run_total()) + 1)
        def to_move():
            f.earn(max(0.0, f.move_threshold() - f.run_total()) + 1)
        def move_now():
            if not f.has_next_farm():
                self.toast("Следующей фермы пока нет", 2)
                return
            to_move()
            self.do_move()
        def back_summer():
            f.farm_index = 0
            f.home_leaves = f.leaves
            f.reset_run()
            self.set_theme()
            self.modal = None
            self.toast("Вернулись на летнюю ферму (для тестов)", 2)
        def all_crops():
            for i in range(N_CROPS):
                f.levels[i] += 50
        def barn():
            for a in range(N_ANIMALS):
                f.a_levels[a] = max(f.a_levels[a], 5)
                f.a_keeper[a] = True
        def tree_max():
            for n, node in TREE_NODES.items():
                f.tree[n] = len(node["costs"])
        def squirrel(g):
            self.modal = None
            self.view = "field"
            self.spawn_squirrel(golden=g)
        def crow():
            self.modal, self.view = None, "field"
            if self.farm_info()["crow"]:
                self.spawn_crow()
            else:
                self.toast("На этой ферме ворон нет", 2)
        def frost():
            self.modal, self.view = None, "field"
            if self.farm_info()["frost"]:
                self.frost_timer = 0
            else:
                self.toast("На этой ферме мороза нет", 2)
        def speed():
            self.time_scale = {1: 10, 10: 60, 60: 1}[self.time_scale]
        def bandit():
            self.modal, self.view = None, "field"
            if self.farm_info()["bandits"]:
                self.spawn_bandit()
            else:
                self.toast("На этой ферме разбойников нет", 2)
        def mill():
            f.m_levels = [3, 3]
            f.peasants = max(f.peasants, 8)
        def quests_done():
            t = self.tavern
            t.unlocked = True
            self.tavern_refresh()
            for q in t.daily + [t.weekly]:
                q["progress"] = q["target"]
            self.modal = None
            self.open_tavern()
            self.open_board()
        def tavern_debug():
            self.tavern_debug = not self.tavern_debug
            if self.tavern.unlocked:
                self.modal = None
                self.open_tavern()
        def new_day():
            t = self.tavern
            t.unlocked = True
            t.day = t.week = ""
            self.tavern_refresh()
            self.toast("Таверна: новые задания дня и недели", 2)
        return [
            ("Деньги x1000", money), (f"+1000 {CUR['gen']}", leaves),
            ("Заработать до грузовика", to_truck), ("Заработать до переезда", to_move),
            ("Переехать сейчас", move_now), ("Назад на летнюю", back_summer),
            ("Все грядки +50 ур.", all_crops), ("Сарай: всё ур.5 + скотники", barn),
            ("Дерево на максимум", tree_max), (f"Скорость времени: x{self.time_scale}", speed),
            ("Белка", lambda: squirrel(False)), ("Золотая белка", lambda: squirrel(True)),
            ("Ворона", crow), ("Мороз", frost),
            ("Разбойник", bandit), ("Мельница и пекарня ур.3", mill),
            ("Таверна: все задания готовы", quests_done), ("Таверна: новый день и неделя", new_day),
            ("Таверна: показать разметку" + (" (вкл)" if self.tavern_debug else ""), tavern_debug),
        ]

    def draw_dev(self):
        r = self.panel(640, 590, "РЕЖИМ РАЗРАБОТЧИКА")
        draw_text(self.screen, f"Сохранение: {os.path.basename(cfg.SAVE_FILE)}   •   {self.clock.get_fps():.0f} кадр/с, "
                  f"картинка {self.canvas[0]}×{self.canvas[1]}   •   F1 — закрыть", 13,
                  (r.centerx, r.y + 70), (140, 110, 95), outline=None)
        for n, (label, cb) in enumerate(self.dev_actions()):
            col, row = n % 2, n // 2
            self.button((r.x + 30 + col * 300, r.y + 86 + row * 48, 280, 42), label, cb, (230, 110, 110), True, 15)

    def draw_offline(self):
        s = self.screen
        secs, amt = self.offline_info
        r = self.panel(460, 280, "С ВОЗВРАЩЕНИЕМ!")
        brown = (90, 70, 60)
        h, m = int(secs // 3600), int(secs % 3600 // 60)
        draw_text(s, f"Тебя не было {h} ч {m} мин.", 18, (r.centerx, r.y + 86), brown, outline=None)
        draw_text(s, "На ферме накопилось:", 18, (r.centerx, r.y + 116), brown, outline=None)
        draw_text(s, "+$" + fmt(amt), 30, (r.centerx, r.y + 154), GOLD)
        draw_text(s, "Не забудь собрать!", 14, (r.centerx, r.y + 182), (140, 110, 95), outline=None)
        self.button((r.centerx - 80, r.bottom - 72, 160, 46), "Ура!", self.close_modal)

    # ------------------------------------------------------------ frame
    def draw(self):
        self.mouse = pygame.mouse.get_pos()
        self.animate()
        self.track_modal()
        self.tips = []
        self.draw_scene()
        if self.view == "field" and self.modal is None:
            draw_trail(self.screen, self.trail, self.t_real)
        self.draw_hover()
        self.draw_tip()
        if self.show_fps:
            draw_text(self.screen, f"{self.clock.get_fps():.0f} кадр/с", 13, (W - 8, H - 4), WHITE,
                      anchor="bottomright")

    # ------------------------------------------------------------ окна: появление и исчезновение
    def track_modal(self):
        """Заметить, что окно открылось или закрылось (а это делают из многих мест), и запустить анимацию."""
        if self.modal == self._modal_seen:
            return
        prev, self._modal_seen = self._modal_seen, self.modal
        if self.modal is not None:
            self.modal_t0 = self.t_real
            self.modal_from_none = prev is None
            self.closing = None
        elif prev is not None:
            self.closing = (prev, self.t_real)

    def modal_drawers(self):
        return {"shop": self.draw_shop, "truck": self.draw_truck_modal,
                "settings": self.draw_settings, "stats": self.draw_stats, "offline": self.draw_offline,
                "tree": self.draw_tree, "move": self.draw_move, "dev": self.draw_dev, "songs": self.draw_songs}

    def draw_modal_layer(self, name, prog, opening):
        """Окно рисуется в отдельный слой и показывается чуть уменьшенным и прозрачным — так оно
        мягко выезжает (prog 0 -> 1) или уезжает. Возвращает False, если нарисовать не вышло."""
        layer = hd.Surface((W, H), pygame.SRCALPHA)
        layer.fill((0, 0, 0, 0))
        screen, self.screen = self.screen, layer
        self.panel_rect = None
        try:
            self.modal_drawers()[name]()
        except Exception as e:          # окно не нарисовалось (например, состояние уже другое) — без анимации
            print("Анимация окна:", e)
            return False
        finally:
            self.screen = screen
        box = (self.panel_rect or pygame.Rect(0, 0, W, H)).inflate(60, 60).clip(pygame.Rect(0, 0, W, H))
        piece = hd.Surface(box.size, pygame.SRCALPHA)
        piece.fill((0, 0, 0, 0))
        piece.blit(layer, (-box.x, -box.y))
        if opening:
            sc = 0.94 + 0.06 * anim.ease_out_back(prog, 1.4)
            alpha = anim.ease_out_cubic(min(1.0, prog / 0.6))
        else:
            sc = 1.0 - 0.04 * anim.ease_out_cubic(prog)
            alpha = 1.0 - anim.ease_out_cubic(prog)
        w, h = max(1, int(round(box.w * sc))), max(1, int(round(box.h * sc)))
        if (w, h) != box.size:
            piece = pygame.transform.smoothscale(piece, (w, h))
        hd.real(piece).set_alpha(int(255 * alpha))
        self.screen.blit(piece, piece.get_rect(center=box.center))
        return True

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

    def draw_closing(self):
        """Закрытое окно ещё мгновение уезжает (кнопки в нём уже не нажимаются)."""
        if not self.closing:
            return
        name, t0 = self.closing
        prog = (self.t_real - t0) / MODAL_CLOSE_TIME
        if prog >= 1 or name not in self.modal_drawers():
            self.closing = None
            return
        n_zones, n_tips = len(self.zones), len(self.tips)
        self.draw_shade(1 - anim.ease_out_cubic(prog))
        self._in_modal = True
        if not self.draw_modal_layer(name, prog, False):
            self.closing = None
        self._in_modal = False
        del self.zones[n_zones:]
        del self.tips[n_tips:]

    def track_mouse(self):
        """Точки шлейфа: только на поле и без открытых окон."""
        now = self.t_real
        if self.view == "field" and self.modal is None:
            pos = pygame.mouse.get_pos()
            if not self.trail or (abs(pos[0] - self.trail[-1][0]) + abs(pos[1] - self.trail[-1][1])) > 1:
                self.trail.append((pos[0], pos[1], now))
        self.trail = [p for p in self.trail if now - p[2] < 0.3][-40:]

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

    def draw_modal(self):
        self.zones = []
        self.tips = []
        prog = (self.t_real - self.modal_t0) / MODAL_OPEN_TIME
        self._in_modal = True
        try:
            if prog >= 1:
                self.screen.blit(self.shade, (0, 0))
                self.modal_drawers()[self.modal]()
                return
            self.draw_shade(anim.ease_out_cubic(prog) if self.modal_from_none else 1.0)
            if not self.draw_modal_layer(self.modal, prog, True):
                self.modal_t0 = -99.0
                self.modal_drawers()[self.modal]()
        finally:
            self._in_modal = False

    def draw_scene(self):
        self.zones = []
        s, f = self.screen, self.farm
        if self.view in ("barn", "tavern", "board"):
            {"barn": self.draw_barn_view, "tavern": self.draw_tavern_view, "board": self.draw_board_view}[self.view]()
            self.draw_hud()
            self.draw_toasts()
            self.fx.draw(s)
            if self.modal:
                self.draw_modal()
            else:
                self.draw_closing()
            return
        s.blit(self.bg, (0, 0))
        if THEME.get("building") == "mill":
            working = f.m_workers[0] > 0 and f.hopper > 0
            draw_mill_blades(s, MILL_HUB[0], MILL_HUB[1], self.t * (1.6 if working else 0.35))
        self.zone((120, 30, 250, 195), self.toggle_barn)   # клик по амбару / мельнице
        self.draw_sun()
        self.draw_cloud()
        for k in DRAW_ORDER:
            self.draw_soil(k)
        for k in DRAW_ORDER:
            self.draw_plants(k)
            self.draw_ice(k)
        self.draw_front_fence()
        self.draw_truck_layer()
        if f.rain_left > 0:
            if self.farm_info()["weather"] == "Праздник урожая":   # конфетти и тёплый свет
                s.blit(self.bless_tint, (0, 0))
                colors = ((255, 215, 90), (235, 90, 80), (110, 190, 110), (110, 160, 235), (245, 245, 235))
                tr = self.t_real
                for x, y, _ in self.drops:
                    k = int(x * 7) % len(colors)                     # цвет у бумажки свой и не мигает
                    w = 3 + (int(x * 3) % 3)
                    ww = w * abs(math.cos(tr * 6 + x)) + 0.8          # кувыркается: то широкая, то ребром
                    sx = x + math.sin(tr * 2.2 + x * 0.13) * 8        # покачивается из стороны в сторону
                    tilt = math.sin(tr * 4 + x) * w
                    poly(s, colors[k], [(sx - ww, y - tilt), (sx + ww, y + tilt), (sx + ww, y + tilt + 3),
                                        (sx - ww, y - tilt + 3)], 0)
            else:
                s.blit(self.rain_tint, (0, 0))
                for x, y, _ in self.drops:
                    pygame.draw.line(s, (100, 170, 235), (P(x), P(y)), (P(x - 2), P(y + 11)), 2)
        for k in DRAW_ORDER:
            if self.mode == "upgrade":
                self.draw_upgrade_sign(k)
            else:
                self.draw_tile_overlay(k)
        if self.mode == "upgrade":
            self.draw_upgrade_controls()
        if self.mode == "normal":
            for x, y, text, life, color in self.floaters:
                pop = max(0.0, 1 - (1.2 - life) / 0.2)            # появляется чуть крупнее и «садится»
                draw_text(s, text, 18 + int(round(5 * pop)), (x, y), color)
        self.draw_hud()
        self.draw_toasts()
        self.draw_squirrel_layer()
        self.draw_crow_layer()
        self.draw_bandit_layer()
        self.fx.draw(s)
        self.draw_tutorial()
        if self.modal:
            self.draw_modal()
        else:
            self.draw_closing()

    def run(self):
        while True:
            dt = min(self.clock.tick(self.fps_limit) / 1000.0, 0.25) * self.time_scale
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.quit_game()
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    self.on_click(self.lpos(e.pos))
                elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                    self.mouse_up()
                elif e.type == pygame.MOUSEMOTION and self.volume_drag is not None:
                    if e.buttons[0] and self.modal == "settings":
                        self.set_volume_from_x(self.volume_drag, self.lpos(e.pos)[0])
                    else:
                        self.volume_drag = None
                elif (e.type == pygame.MOUSEMOTION and e.buttons[0] and self.modal is None
                      and self.mode == "normal" and self.view == "field"):
                    self.try_collect(self.lpos(e.pos))
                elif e.type == pygame.KEYDOWN:
                    self.on_key(e.key)
            self.update(dt)
            self.t_real = time.time() - self.t_start
            self.track_mouse()
            self.draw()
            self.update_cursor()
            pygame.display.flip()


def main():
    if "--export-templates" in sys.argv:
        pygame.init()
        from .templates import export_templates
        out, n = export_templates()
        print(f"Готово: {n} шаблонов в папке {out}")
        return
    try:
        App().run()
    except Exception:
        # ошибка в игре: записываем её в crash.log рядом с игрой, чтобы было что прислать
        import traceback
        try:
            with open(os.path.join(cfg.BASE_DIR, "crash.log"), "a", encoding="utf-8") as f:
                f.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')}  версия {GAME_VERSION} ===\n")
                traceback.print_exc(file=f)
            print("Игра закрылась из-за ошибки. Подробности записаны в crash.log (рядом с игрой) — пришли этот файл.")
        except OSError:
            pass
        raise
