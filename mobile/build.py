"""3.17: сборка телефонных версий игры (запускается в GitHub Actions, см. .github/workflows/).

    python mobile/build.py stage web <папка> --baked <папка baked>        папка для pygbag (веб-версия)
    python mobile/build.py stage android <папка> --baked <...> --p4a <...>  папка для buildozer (APK)
    python mobile/build.py icons <папка> --baked <папка baked>             иконки и заставка (нужен pygame)
    python mobile/build.py webpatch <build/web>                           index.html: «как приложение» на iPhone

В сборку идут код (farmgame/), assets/ БЕЗ исходных картинок (музыка, звуки, шрифты, разметка .json)
и baked/ — картинки, заранее подогнанные под телефон (devtools/bake_sprites.py).
"""
import argparse
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
TITLE = "Весёлая ферма"
SHORT = "Ферма"
BG = "#9CDE76"

MAIN_WEB = '''# Веб-версия (pygbag). Собрано mobile/build.py — не править руками.
import asyncio
import os
import sys

import pygame  # noqa: F401  pygbag ставит pygame-ce только по import в самом main.py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from farmgame.app import main_async  # noqa: E402

asyncio.run(main_async())
'''

MAIN_ANDROID = '''# Android (buildozer). Собрано mobile/build.py — не править руками.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from farmgame.app import main  # noqa: E402

main()
'''


def game_version():
    with open(os.path.join(GAME, "farmgame", "config.py"), encoding="utf-8") as f:
        return re.search(r'GAME_VERSION = "([^"]+)"', f.read()).group(1)


def copy_tree(src, dst, skip_ext=()):
    n = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != "__pycache__" and not d.startswith(".")]
        for fn in files:
            if fn.lower().endswith(skip_ext) or fn.endswith((".pyc", ".tmp")):
                continue
            rel = os.path.relpath(os.path.join(root, fn), src)
            os.makedirs(os.path.dirname(os.path.join(dst, rel)), exist_ok=True)
            shutil.copy2(os.path.join(root, fn), os.path.join(dst, rel))
            n += 1
    return n


def stage(target, out, baked, p4a=None):
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    n = copy_tree(os.path.join(GAME, "farmgame"), os.path.join(out, "farmgame"))
    n += copy_tree(os.path.join(GAME, "assets"), os.path.join(out, "assets"), skip_ext=IMAGE_EXTS)
    if not os.path.isfile(os.path.join(baked, "manifest.json")):
        sys.exit(f"Нет {baked}/manifest.json — сначала devtools/bake_sprites.py")
    n += copy_tree(baked, os.path.join(out, "baked"))
    with open(os.path.join(out, "main.py"), "w", encoding="utf-8") as f:
        f.write(MAIN_WEB if target == "web" else MAIN_ANDROID)
    if target == "android":
        with open(os.path.join(HERE, "android", "buildozer.spec"), encoding="utf-8") as f:
            spec = f.read()
        spec = re.sub(r"(?m)^version = .*$", "version = " + game_version(), spec)
        if p4a:
            spec = re.sub(r"(?m)^p4a\.source_dir = .*$", "p4a.source_dir = " + os.path.abspath(p4a), spec)
        recipes = os.path.join(out, "recipes")
        shutil.copytree(os.path.join(HERE, "android", "recipes"), recipes)
        spec = re.sub(r"(?m)^p4a\.local_recipes = .*$", "p4a.local_recipes = " + os.path.abspath(recipes), spec)
        with open(os.path.join(out, "buildozer.spec"), "w", encoding="utf-8") as f:
            f.write(spec)
    size = sum(os.path.getsize(os.path.join(r, fn)) for r, _d, fs in os.walk(out) for fn in fs)
    print(f"{target}: {n} файлов, {size / 1e6:.1f} МБ -> {out} (версия {game_version()})")


# ---------------------------------------------------------------- иконки
def icons(out, baked):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    pygame.init()
    pygame.display.set_mode((64, 64))
    with open(os.path.join(baked, "manifest.json"), encoding="utf-8") as f:
        table = json.load(f)["sprites"]

    def baked_img(*names):
        for name in names:
            fn = table.get(name)
            if fn:
                return pygame.image.load(os.path.join(baked, fn)).convert_alpha()
        return None

    green = (156, 222, 118)          # BG
    mascot = baked_img("ui/loading_center", "icons/peasant@2x", "icons/peasant")
    os.makedirs(out, exist_ok=True)
    for size in (512, 192, 180, 64):
        icon = pygame.Surface((size, size))
        icon.fill(green)
        pygame.draw.circle(icon, (255, 236, 150), (size // 2, size // 2), int(size * 0.42))
        if mascot is not None:
            k = size * 0.78 / max(mascot.get_size())
            img = pygame.transform.smoothscale(mascot, (max(1, int(mascot.get_width() * k)),
                                                        max(1, int(mascot.get_height() * k))))
            icon.blit(img, img.get_rect(center=(size // 2, size // 2)))
        name = "icon.png" if size == 512 else f"icon-{size}.png"
        pygame.image.save(icon, os.path.join(out, name))
    pygame.image.save(pygame.image.load(os.path.join(out, "icon-64.png")), os.path.join(out, "favicon.png"))
    splash = pygame.Surface((960, 540))
    splash.fill(green)
    logo = baked_img("ui/logo")
    if logo is not None:
        k = 820 / logo.get_width()
        logo = pygame.transform.smoothscale(logo, (820, int(logo.get_height() * k)))
        splash.blit(logo, logo.get_rect(center=(480, 270)))
    pygame.image.save(splash, os.path.join(out, "presplash.png"))
    print("иконки и заставка ->", out)


# ---------------------------------------------------------------- веб: «как приложение»
HEAD = """
<!-- 3.17 vesyolaya-ferma: на iPhone/Android «На экран Домой» — открывается без адресной строки, лёжа -->
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="{short}">
<meta name="theme-color" content="#000000">
<link rel="apple-touch-icon" href="icon-180.png">
<link rel="manifest" href="manifest.webmanifest">
<style>
  html, body {{ background: #000 !important; overscroll-behavior: none; touch-action: none;
               -webkit-user-select: none; user-select: none; -webkit-touch-callout: none; }}
</style>
"""
VIEWPORT = ('<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, '
            'user-scalable=no, viewport-fit=cover">')


def webpatch(web):
    path = os.path.join(web, "index.html")
    with open(path, encoding="utf-8") as f:
        html = f.read()
    if "3.17 vesyolaya-ferma" not in html:
        html, n = re.subn(r'<meta[^>]*name=["\']viewport["\'][^>]*>', VIEWPORT, html, count=1, flags=re.I)
        head = HEAD.format(short=SHORT) + ("" if n else VIEWPORT + "\n")
        html = re.sub(r"</head>", head + "</head>", html, count=1, flags=re.I)
        html = re.sub(r"<title>.*?</title>", f"<title>{TITLE}</title>", html, count=1, flags=re.I | re.S)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    manifest = dict(name=TITLE, short_name=SHORT, start_url=".", scope=".", display="fullscreen",
                    orientation="landscape", background_color="#000000", theme_color="#000000",
                    icons=[dict(src="icon-192.png", sizes="192x192", type="image/png"),
                           dict(src="icon.png", sizes="512x512", type="image/png")])
    with open(os.path.join(web, "manifest.webmanifest"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    with open(os.path.join(web, ".nojekyll"), "w") as f:
        f.write("")
    print("index.html и manifest.webmanifest готовы:", web)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("stage", "icons", "webpatch"))
    ap.add_argument("args", nargs="+")
    ap.add_argument("--baked")
    ap.add_argument("--p4a")
    a = ap.parse_args()
    if a.cmd == "stage":
        stage(a.args[0], a.args[1], a.baked, a.p4a)
    elif a.cmd == "icons":
        icons(a.args[0], a.baked)
    else:
        webpatch(a.args[0])
