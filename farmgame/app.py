# -*- coding: utf-8 -*-
"""Приложение: окно, ввод, экраны и окна интерфейса."""
from .ui_common import *  # noqa: F401,F403
from .ui_common import _rain_time, _rain_cd, _rain_speed  # noqa: F401
from .tavern_ui import TavernUI
from .board_ui import BoardUI
from .songs_ui import SongsUI
from .tavern_life_ui import TavernLifeUI
from .fireside_ui import FiresideUI
from .move_ui import MoveUI, MAP_GAP
from .tavern_hud_ui import TavernHudUI
from .mill_ui import MillUI
from .tutorial_ui import TutorialUI
from .casino_ui import CasinoUI
from .gameroom_ui import GameRoomUI
from .blackjack_ui import BlackjackUI
from .snails_ui import SnailsUI
from .dice_ui import DiceUI
from .field_ui import FieldUI
from .creatures_ui import CreaturesUI
from .barn_ui import BarnUI
from .windows_ui import WindowsUI
from .hud_ui import HudUI
from .widgets_ui import WidgetsUI
from .screen_ui import ScreenUI
from .achievements_ui import AchievementsUI
from .fishery_ui import FisheryUI


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
class App(TavernUI, BoardUI, SongsUI, TavernLifeUI, FiresideUI, MoveUI, TavernHudUI, MillUI, TutorialUI, GameRoomUI, BlackjackUI, SnailsUI, DiceUI, CasinoUI, FieldUI, CreaturesUI, BarnUI, WindowsUI, HudUI, WidgetsUI,
          ScreenUI, AchievementsUI, FisheryUI):
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
        self.edge_fill = True         # 3.10: в полном экране по краям — размытый фон вместо чёрных полос
        self.wide = None              # окно в пропорциях экрана: dict(display, frame, offset, ...) — см. enter_wide
        self.was_minimized = False    # 3.16.4: полный экран свернули — при возврате пересоздаём его
        self.wide_refresh = False
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
        self.rush_popped = set()          # 3.26: на каких грядках гном из пришествия уже выскочил
        self.truck_state = "away"     # away | arriving | parked | leaving
        self.truck_x = VEHICLE_FAR
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
        self.init_move_map()           # 3.23: карта глав в окне «Переезд»
        self.init_mill()
        self.fishery_init()            # 3.37: рыборазводня (Рыбацкая деревня)
        self.init_tutorial()
        self.init_casino()
        self.init_gameroom()          # 3.27: Игровая — карта игр и колесо фортуны
        self.init_blackjack()         # 3.28: блэкджек с рыжим гномом Ворчуном (открывается зимой)
        self.init_snails()            # 3.40: скачки улиток со Старым Якорем (открываются в Рыбацкой деревне)
        self.init_dice()              # 3.43: кости с драконицей Искрой (откроются в главе 5)
        self.preload_sprites()        # картинки и синтез звуков — пока на экране заставка с крутящимся колесом
        self.load_cursors()
        self.bg = self.build_background()
        self.barn_bg = self.build_barn_background()
        self.mill_bg = self.build_mill_background()
        self.load()
        self.music.play_for(self.farm_info()["id"])
        self.report_assets()

    # ------------------------------------------------------------ загрузка картинок
    def preload_sprites(self):
        """Подгоняет все картинки из assets/ сразу при запуске, с заставкой и полоской.
        Иначе каждая картинка подгонялась бы при первом показе, и игра на миг замирала бы
        (например, когда белка выбегает в первый раз). Уже подогнанные берутся из .sprite_cache/ мгновенно.
        3.40.4: сначала берём всё, что уже в кэше; недостающее подгоняют несколько процессов сразу (warmup.py)."""
        from .templates import known_names
        from . import warmup
        self.load_t0 = time.time()
        self.draw_loading(0.0)                        # сразу что-то на экране, пока грузятся картинки заставки
        pygame.display.flip()
        early = LOADING_SPRITES + ("icons/peasant",)  # сама заставка (крестьянин — запасной талисман)
        for name in early:
            sprite(name)
        names = [n for n in sorted(known_names()) if n not in early]
        total = len(names) + 1                        # +1 — синтез звуков
        sounds = {"done": False}

        def synth():
            try:
                self.sfx.preload()
            except Exception as e:                    # noqa: BLE001
                print("Синтез звуков:", e)
            finally:
                sounds["done"] = True
        try:
            threading.Thread(target=synth, daemon=True).start()
        except Exception:                             # noqa: BLE001
            synth()

        def frame(frac):
            probe = spritefit.PROBE[0]
            spritefit.PROBE[0] = False                # сама заставка рисуется как обычно
            try:
                pygame.event.pump()                   # чтобы Windows не считала окно зависшим
                self.draw_loading(frac)
                pygame.display.flip()
            finally:
                spritefit.PROBE[0] = probe

        # 1) что уже подогнано — из кэша; чего нет — в список
        missing = []
        spritefit.PROBE[0] = True
        try:
            for n, name in enumerate(names):
                try:
                    sprite(name)
                except spritefit.NeedFit:
                    missing.append(name)
                if n % 25 == 0:
                    frame(0.5 * n / total if missing else n / total)
        finally:
            spritefit.PROBE[0] = False
        done0 = len(names) - len(missing)
        clock = pygame.time.Clock()
        # 2) недостающее — в нескольких процессах; окно крутит заставку
        if missing:
            print(f"Подгоняю {len(missing)} картинок в {warmup.workers()} процессах…")
            run = warmup.start(missing)
            if run is not None:
                ex, jobs = run
                try:
                    while not all(f.done() for f, _n in jobs):
                        got = sum(n for f, n in jobs if f.done())
                        frame((done0 + got) / total)
                        clock.tick(30)
                finally:
                    ex.shutdown(wait=True)
            # 3) забираем готовое из кэша (что процессы не смогли — подгоняется тут, в потоке, как раньше)
            state = {"done": 0, "finished": False}

            def work():
                try:
                    for name in missing:
                        sprite(name)
                        state["done"] += 1
                except Exception as e:                # не роняем игру: недогруженное загрузится при первом показе
                    print("Загрузка картинок:", e)
                finally:
                    state["finished"] = True
            try:
                worker = threading.Thread(target=work, daemon=True)
                worker.start()
            except Exception:                         # noqa: BLE001
                worker = None
                work()
            while worker is not None and not state["finished"]:
                frame((done0 + state["done"]) / total)
                clock.tick(60)
        while not sounds["done"]:
            frame((total - 1) / total)
            clock.tick(60)
        spritefit.save_index()
        print(f"Картинки готовы за {time.time() - self.load_t0:.1f} с")
        frame(1.0)

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
                           "show_fps": self.show_fps, "tips": self.show_tips, "edge_fill": self.edge_fill}
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
            self.edge_fill = bool(opts.get("edge_fill", True))
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

    def open_modal(self, name):
        self.modal = name
        self.confirm_reset = False
        if name == "shop":
            self.shop_page = 0
            self.tut_event("shop")
        if name == "move":
            self.open_move_map()

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
        if getattr(self, "fy_game", None) is not None and getattr(self, "fy_phase", "") == "intro":   # 3.39.5
            if key == pygame.K_ESCAPE:
                self.fy_catch_cancel()
                return
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                self.fy_catch_start()
                return
        if key == pygame.K_ESCAPE:
            if self.modal:
                self.modal = None
            elif self.mode == "upgrade":
                self.mode = "normal"
            elif self.view in ("barn", "tavern"):
                self.view = "field"
            elif self.view == "casino" and self.cs_spin is None:
                self.view = "gameroom"                 # 3.27: из рулетки — в Игровую
            elif self.view == "blackjack":
                self.bj_leave()
            elif self.view == "snails":
                self.sn_leave()
            elif self.view == "dice":
                self.dc_leave()
            elif self.view in ("board", "fireside", "gameroom"):
                self.view = "tavern"
        elif key == pygame.K_F11:
            self.toggle_fullscreen()
        elif key == pygame.K_m:
            self.toggle_music()
        elif self.view == "gameroom" and self.modal is None and key in (getattr(pygame, "K_UP", -1),
                                                                        getattr(pygame, "K_DOWN", -1)):
            self.gr_scroll_by(-280 if key == getattr(pygame, "K_UP", -1) else 280)
        elif self.modal == "move" and key in (getattr(pygame, "K_LEFT", -1), getattr(pygame, "K_RIGHT", -1)):
            self.map_scroll(-MAP_GAP if key == getattr(pygame, "K_LEFT", -1) else MAP_GAP)
        elif key == pygame.K_F1 and DEV:
            self.modal = None if self.modal == "dev" else "dev"
            self.dev_tab, self.dev_page = None, 0          # 3.29: открывается на вкладке текущего места
        elif self.modal is None:
            if key == pygame.K_b and self.view in ("field", "barn"):
                self.toggle_barn()
            elif key == pygame.K_t and self.tavern.unlocked:
                if self.view in ("tavern", "board", "fireside"):
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
        self.ach_tick(dt)                 # 3.34: достижения
        self.mill_tick(dt)
        self.fishery_tick(dt)             # 3.38: события аквариума (хищник приплыл, съел, уплыл)
        self.tut_tick(dt)
        self.casino_tick(dt)
        self.gameroom_tick(dt)
        self.blackjack_tick(dt)
        self.snails_tick(dt)
        self.dice_tick(dt)

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
            self.sfx.play("truck" if self.farm_info()["vehicle"] == "truck" else "fanfare")   # упряжка — фанфары
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
                self.truck_x = VEHICLE_FAR
        if self.truck_state in ("arriving", "leaving") and self.view == "field":     # пыль из-под задних колёс
            self.truck_dust += dt * min(1.0, self.truck_v / 120)
            if self.truck_dust >= 0.09:
                self.truck_dust = 0.0
                rear = 60 if self.farm_info()["vehicle"] == "truck" else 75
                if self.farm_info()["vehicle"] == "boat":      # 3.38.1: за лодкой — пена, а не пыль
                    self.fx.dust(self.truck_x + 110, TRUCK_GROUND - 6 + self.vehicle_dy(), n=2, color=(215, 235, 245), size=(5, 9), spread=8,
                                 up=6, drift=30, alpha=170, life=(0.4, 0.7))
                else:
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
        festival = self.farm_info()["weather"] in WEATHER_BUTTON   # праздник и пришествие: медленные «капли»
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

    def mouse_up(self):
        if self.volume_drag and self.volume_drag[1] == "sfx":
            self.sfx.play("click")        # услышать новую громкость звуков
        self.volume_drag = None
        self.map_drag_last = None
        self.gr_drag_last = None

    def quit_game(self):
        self.save()
        pygame.quit()
        sys.exit()

    # ------------------------------------------------------------ frame
    def draw(self):
        self.mouse = pygame.mouse.get_pos()
        self.animate()
        self.track_modal()
        self.tips = []
        self.draw_scene()
        if self.view == "field" and self.modal is None:
            tr = self.tavern.group_on("trail")     # 3.33: шлейф — один из группы (золото, звёзды, листья, пузыри)
            draw_trail(self.screen, self.trail, self.t_real,
                       color=(255, 212, 80) if tr == "gold_trail" else (255, 250, 225),
                       stars=tr == "star_trail",          # 3.27: джекпот колеса фортуны
                       style={"leaf_trail": "leaves", "bubble_trail": "bubbles"}.get(tr),
                       life=0.5 if tr in ("leaf_trail", "bubble_trail") else 0.28)
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
                "tree": self.draw_tree, "move": self.draw_move, "dev": self.draw_dev, "songs": self.draw_songs,
                "prizes": self.draw_prizes, "fortune": self.draw_fortune, "achievements": self.draw_achievements}

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
        if self.view in ("barn", "tavern", "board", "casino", "fireside", "gameroom", "blackjack", "snails", "dice"):
            {"barn": self.draw_barn_view, "tavern": self.draw_tavern_view, "board": self.draw_board_view,
             "casino": self.draw_casino_view, "fireside": self.draw_fireside_view,
             "gameroom": self.draw_gameroom_view, "blackjack": self.draw_blackjack_view,
             "snails": self.draw_snails_view, "dice": self.draw_dice_view}[self.view]()
            if self.view != "fireside":      # 3.19: у камина — без плашек, только огонь
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
        self.draw_scene_life()                # 3.38.1: окна мерцают, из трубы дым (если у фермы живой фон)
        self.draw_sun()
        self.draw_cloud()
        for k in DRAW_ORDER:
            self.draw_soil(k)
        for k in DRAW_ORDER:
            self.draw_plants(k)
            self.draw_ice(k)
            self.draw_rush_worker(k)          # 3.26: гном из «пришествия» на грядке
        self.draw_rush_walkers()              # 3.38.1: рыбаки идут из домов к прудам и обратно
        self.draw_front_fence()
        self.draw_shamans()                   # 3.26: шаманы пляшут на лужайке справа
        self.draw_truck_layer()
        if f.rain_left > 0:
            if self.farm_info()["weather"] == GNOME_RUSH:   # 3.26: тёплый свет, в воздухе — волшебные искорки шаманов
                s.blit(self.bless_tint, (0, 0))
                tr = self.t_real
                colors = ((250, 215, 90), (200, 160, 255), (150, 220, 255))
                for x, y, _ in self.drops:
                    sx = x + math.sin(tr * 1.6 + x * 0.1) * 6
                    r = 2.5 + 1.5 * (0.5 + 0.5 * math.sin(tr * 7 + x))     # мерцает
                    c = colors[int(x * 5) % len(colors)]
                    poly(s, c, [(sx, y - r * 1.6), (sx + r * 0.5, y - r * 0.5), (sx + r * 1.6, y), (sx + r * 0.5, y + r * 0.5),
                                (sx, y + r * 1.6), (sx - r * 0.5, y + r * 0.5), (sx - r * 1.6, y), (sx - r * 0.5, y - r * 0.5)], 0)
            elif self.farm_info()["weather"] == "Праздник урожая":   # конфетти и тёплый свет
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
                drop = has_sprite("fx/raindrop")              # 3.16: своя капля fx/raindrop
                for x, y, _ in self.drops:
                    if drop:
                        blit_sprite(s, "fx/raindrop", x - 1, y + 6, 0.55, "center")
                    else:
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
                elif e.type == pygame.MOUSEMOTION and e.buttons[0] and self.modal == "move":
                    self.map_drag(self.lpos(e.pos))          # 3.23: карту глав тянут мышью
                elif e.type == pygame.MOUSEMOTION and e.buttons[0] and self.view == "gameroom":
                    self.gr_drag(self.lpos(e.pos))           # 3.27: карту Игровой — тоже
                elif e.type == getattr(pygame, "MOUSEWHEEL", -1):
                    self.map_wheel(e)
                    self.gr_wheel(e)
                elif e.type == pygame.KEYDOWN:
                    self.on_key(e.key)
                else:
                    self.on_window_event(e)
            if self.wide_refresh:
                self.refresh_wide()
            self.update(dt)
            self.t_real = time.time() - self.t_start
            self.track_mouse()
            self.draw()
            self.update_cursor()
            try:
                self.present_wide()
                pygame.display.flip()
            except pygame.error as e:          # 3.16.8: окно поменялось посреди кадра (выход из полного экрана)
                print("Кадр не показан:", e)
                self.safe_window()


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
