# 3.17: сборка APK для Android (buildozer + python-for-android). Запускается в GitHub Actions (.github/workflows/android.yml):
# mobile/build.py складывает игру в build/android_src (main.py, farmgame/, assets/ без картинок, baked/) и кладёт рядом этот файл.

[app]
title = Весёлая ферма
package.name = vesyolayaferma
package.domain = io.github.alotmema
source.dir = .
source.include_exts = py,png,jpg,ogg,ttf,otf,json
source.exclude_dirs = .buildozer,bin,build,recipes
# версия: mobile/build.py подставляет версию игры (config.GAME_VERSION)
version = 0.0
# Python 3.12: сгенерированный Cython-код pygame 2.6.1 не собирается на 3.14 (по умолчанию в p4a)
requirements = python3==3.12.12,hostpython3==3.12.12,pygame
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png
android.presplash_color = #9CDE76
orientation = landscape
fullscreen = 1

# --- Android ---
android.api = 34
# Python 3.12 на Android собирается с API 26+ (setgrent и др.) — это Android 8.0 и новее
android.minapi = 26
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True
# p4a скачивает workflow (проверенная версия); рецепт pygame — свой (mobile/android/recipes/pygame)
p4a.source_dir = ../p4a
p4a.local_recipes = ./recipes
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 0
