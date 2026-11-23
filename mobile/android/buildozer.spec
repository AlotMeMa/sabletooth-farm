# 3.17: сборка APK для Android (buildozer + python-for-android). Запускается в GitHub Actions (.github/workflows/android.yml):
# mobile/build.py складывает игру в build/android_src (main.py, farmgame/, assets/ без картинок, baked/) и кладёт рядом этот файл.

[app]
title = Весёлая ферма
package.name = vesyolayaferma
package.domain = io.github.alotmema
source.dir = .
source.include_exts = py,png,jpg,ogg,ttf,otf,json
source.exclude_dirs = .buildozer,bin,build
# версия: mobile/build.py подставляет версию игры (config.GAME_VERSION)
version = 0.0
requirements = python3,pygame
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png
android.presplash_color = #9CDE76
orientation = landscape
fullscreen = 1

# --- Android ---
android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True
# своего p4a: workflow скачивает его и чинит рецепт pygame (mobile/patch_p4a.py)
p4a.source_dir = ../p4a
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 0
