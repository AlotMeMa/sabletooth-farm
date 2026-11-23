"""Дымовой прогон игры на заглушке pygame: случайные клики по всем кнопкам, все окна и экраны, перемотка времени."""
import json, os, random, sys, traceback
# python devtools/monkey.py <seed> <шагов>   (EXTRA_VIEWS=casino — ещё и казино)
HERE = os.path.dirname(os.path.abspath(__file__))
GAME, FAKE = os.path.dirname(HERE), os.path.join(HERE, "fake_pygame")
SEED, STEPS = int(sys.argv[1]), int(sys.argv[2])
sys.path[:0] = [FAKE, GAME]
os.chdir(GAME)
import pygame
from farmgame import app as appmod, config as cfg, tavern as tv
import tempfile
cfg.SAVE_FILE = os.path.join(tempfile.gettempdir(), f"farm_monkey_{SEED}.json")
if os.path.exists(cfg.SAVE_FILE):
    os.remove(cfg.SAVE_FILE)

random.seed(SEED)
errors = []
seen_modals, seen_views, clicks = set(), set(), {}
EXTRA_VIEWS = [v for v in os.environ.get("EXTRA_VIEWS", "").split(",") if v]


def guard(what, fn, *a):
    try:
        return fn(*a)
    except SystemExit:
        return None
    except Exception:
        errors.append((what, traceback.format_exc()))
        if len(errors) > 5:
            finish()


def finish():
    for what, tb in errors[:6]:
        print("ОШИБКА при:", what); print(tb)
    print(f"seed {SEED}: шагов {STEPS}, окна {sorted(m for m in seen_modals if m)}, экраны {sorted(seen_views)}, "
          f"ферма {app.farm.farm_index}, деньги {cfg.fmt(app.farm.money)}, ошибок {len(errors)}")
    sys.exit(1 if errors else 0)


app = appmod.App()
app.quit_game = lambda: None
real_reset = app.reset_everything
app.reset_everything = lambda: None


def frame(dt=0.016):
    guard("update", app.update, dt * app.time_scale)
    app.t_real += dt
    guard("track_mouse", app.track_mouse)
    guard(f"draw view={app.view} modal={app.modal} mode={app.mode}", app.draw)
    guard("update_cursor", app.update_cursor)
    seen_modals.add(app.modal); seen_views.add(app.view)


def click_random_zone():
    if not app.zones:
        return
    rect, cb, btn = random.choice(app.zones)
    pos = rect.center
    pygame.STATE["mouse"] = pos
    guard(f"click {pos} view={app.view} modal={app.modal}", app.on_click, pos)


KEYS = [pygame.K_ESCAPE, pygame.K_b, pygame.K_t, pygame.K_u, pygame.K_s, pygame.K_m, pygame.K_F1, pygame.K_F11]
frame()
for step in range(STEPS):
    r = random.random()
    if r < 0.62:
        click_random_zone()
    elif r < 0.72:
        guard("key", app.on_key, random.choice(KEYS))
    elif r < 0.80:
        pos = (random.randint(150, 850), random.randint(200, 520))
        pygame.STATE["mouse"] = pos
        guard("drag-collect", app.try_collect, pos)
        guard("click-field", app.on_click, pos)
    elif r < 0.86:
        for _ in range(random.randint(1, 40)):
            guard("update big", app.update, random.choice((0.25, 1.0, 5.0, 15.0)))
    elif r < 0.90:
        app.modal = random.choice([None, "shop", "truck", "settings", "stats", "tree", "dev", "offline", "songs", "prizes"]
                                  + (["move"] if app.farm.has_next_farm() else []))
        if app.modal == "tree":
            app.tree_sel = random.choice(list(appmod.TREE_NODES))
    elif r < 0.93:
        f = app.farm
        f.money = max(f.money, 1e3) * random.choice((10, 1e3, 1e6))
    elif r < 0.95:
        t = app.tavern
        if t.unlocked:
            for q in t.daily + ([t.weekly] if t.weekly else []):
                if random.random() < 0.6:
                    q["progress"] = q["target"]
            if random.random() < 0.5:
                t.day = "" if random.random() < 0.7 else t.day
                t.week = "" if random.random() < 0.3 else t.week
            if random.random() < 0.3:
                t.tokens = getattr(t, "tokens", 0) + 100
    elif r < 0.97:
        guard("spawn", random.choice((app.spawn_squirrel, app.spawn_crow, app.spawn_bandit)))
        app.modal, app.view = None, "field"
    elif r < 0.985:
        guard("save", app.save)
        guard("load", app.load)
    else:
        if app.farm.has_next_farm() and random.random() < 0.5:
            app.farm.earn(app.farm.move_threshold())
            guard("move", app.do_move)
    frame()
for view in ["field", "barn", "tavern", "board"] + EXTRA_VIEWS:
    if view in ("tavern", "board"):
        app.tavern.unlocked = True
        guard("open_tavern", app.open_tavern)
        if view == "board":
            guard("open_board", app.open_board)
    elif view in EXTRA_VIEWS:
        guard("open " + view, getattr(app, "open_" + view))
    else:
        app.view = view
    for modal in [None, "shop", "truck", "settings", "stats", "tree", "dev", "offline", "songs", "prizes"] + (["move"] if app.farm.has_next_farm() else []):
        app.modal = modal
        for sel in (list(appmod.TREE_NODES) if modal == "tree" else [None]):
            app.tree_sel = sel
            for tab in (("fert", "farm") if modal == "shop" else (app.shop_tab,)):
                app.shop_tab = tab
                frame()
    app.modal = None
    for mode in ("upgrade", "normal"):
        app.mode = mode if view == "field" else "normal"
        frame()
guard("reset 1", real_reset); guard("reset 2", real_reset); frame()
guard("final save", app.save)
data = json.load(open(cfg.SAVE_FILE, encoding="utf-8"))
assert isinstance(data, dict) and "levels" in data
finish()
