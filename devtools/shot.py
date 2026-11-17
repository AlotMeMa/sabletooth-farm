"""Кадры игры без окна, на заглушке pygame (PIL): python devtools/shot.py <сценарий> [--hd=off|1.5]
Сценарий — devtools/scenarios/<имя>.py. Кадры — в devtools/shots/<метка>_*.png (метка — переменная TAG)."""
import os, sys, time, random
HERE = os.path.dirname(os.path.abspath(__file__))
GAME, SCEN = os.path.dirname(HERE), sys.argv[1]
TAG = os.environ.get("TAG", "x")
sys.argv = [sys.argv[0]] + [a for a in sys.argv[2:]]
sys.path[:0] = [os.path.join(HERE, "fake_pygame"), GAME]
os.chdir(GAME)
import pygame
from farmgame import app as appmod, config as cfg
import tempfile
cfg.SAVE_FILE = os.path.join(tempfile.gettempdir(), "farm_shot_save.json")
if os.path.exists(cfg.SAVE_FILE):
    os.remove(cfg.SAVE_FILE)
random.seed(3)
t0 = time.time()
A = appmod.App()
print(f"App за {time.time()-t0:.1f} с, k={A.hd_k}")
A.skip_anims()
OUT = os.path.join(HERE, "shots")
os.makedirs(OUT, exist_ok=True)


def frames(n=1, dt=1 / 60):
    for _ in range(n):
        A.update(dt * A.time_scale)
        A.t_real += dt
        A.track_mouse()
        A.animate() if hasattr(A, "animate") else None
        A.draw()


def snap(name, crop=None, scale=1):
    img = pygame.STATE["screen"].img
    if crop:
        k = A.hd_k
        img = img.crop(tuple(int(v * k) for v in crop))
    if scale != 1:
        img = img.resize((int(img.width * scale), int(img.height * scale)))
    p = f"{OUT}/{TAG}_{name}.png"
    img.convert("RGB").save(p)
    print("кадр", p)


def set_summer():
    f = A.farm
    f.levels = [60, 40, 30, 25, 25, 25, 12, 10, 5]
    f.farmers = [True] * 9
    f.a_levels = [5, 4, 3, 2]
    f.a_keeper = [True] * 4
    f.a_feed = [1e3] * 4
    f.money = 1e12
    A.coin_born = [None] * cfg.N_CROPS


def set_medieval():
    f = A.farm
    f.farm_index = 1
    f.reset_run()
    A.set_theme()
    f.levels = [60, 40, 30, 25, 25, 25, 12, 10, 5]
    f.money = 1e12
    A.bg = A.build_background()


exec(open(os.path.join(HERE, "scenarios", SCEN + ".py"), encoding="utf-8").read())
