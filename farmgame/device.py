# -*- coding: utf-8 -*-
"""3.17: где запущена игра — компьютер, браузер (pygbag: iPhone, Android, ПК) или Android-приложение (APK).

Без pygame и без остальной игры (его импортируют config и savefile).

    WEB       — веб-версия (pygbag, WebAssembly): сохранение дублируется в localStorage браузера;
    ANDROID   — APK (python-for-android): сохранения в личной папке приложения (переживают обновление);
    HANDHELD  — «телефонная» сборка: экран целиком в пропорциях телефона, пальцы, без клавиатуры.
                На компьютере её можно примерить: python farm_idle.py --phone
"""
import os
import sys

WEB = sys.platform == "emscripten"
ANDROID = (not WEB) and ("ANDROID_ARGUMENT" in os.environ or "ANDROID_PRIVATE" in os.environ
                         or hasattr(sys, "getandroidapilevel"))
PHONE_PREVIEW = "--phone" in sys.argv          # примерка телефона на компьютере (мышь ведёт себя как палец)
HANDHELD = WEB or ANDROID or PHONE_PREVIEW
HANDHELD_K = 1.5        # чёткость телефонной сборки: картинки заранее подогнаны под неё (devtools/bake_sprites.py)
HANDHELD_FPS = 30       # idle-игре хватает, а батарея и нагрев — вдвое меньше
PREVIEW_SCREEN = (2532, 1170)   # примерка: экран iPhone 12–15, лёжа


def data_dir(base):
    """Куда писать сохранения, кэш картинок и crash.log. На Android — личная папка приложения: папку с кодом
    python-for-android перезаписывает при обновлении APK, а сохранения должны остаться."""
    if ANDROID:
        path = os.environ.get("ANDROID_PRIVATE")
        if path and os.path.isdir(path):
            return path
    return base


# ----------------------------------------------------------------------
#                      браузер (только для WEB)
# ----------------------------------------------------------------------
def _window():
    import platform as _platform          # в pygbag у модуля platform есть window — объект window из JavaScript
    return _platform.window


def viewport():
    """Размер страницы в браузере (CSS-пиксели) — (ширина, высота) или None (не браузер / не вышло)."""
    if not WEB:
        return None
    try:
        win = _window()
        w, h = int(win.innerWidth), int(win.innerHeight)
        return (w, h) if w > 0 and h > 0 else None
    except Exception:
        return None


class WebStore:
    """Хранилище браузера (localStorage): переживает перезагрузку страницы. Файлы в pygbag живут только в памяти,
    поэтому сохранение пишется и в файл (как на компьютере), и сюда — а при запуске файл восстанавливается отсюда."""
    PREFIX = "vesyolaya-ferma/"

    def __init__(self):
        self.ls = _window().localStorage

    def get(self, key):
        try:
            v = self.ls.getItem(self.PREFIX + key)
        except Exception as e:
            print("localStorage: не прочиталось", key, e)
            return None
        if v is None:
            return None
        v = str(v)
        return None if v in ("null", "undefined") else v

    def set(self, key, text):
        try:
            self.ls.setItem(self.PREFIX + key, text)
            return True
        except Exception as e:             # место кончилось или приватный режим Safari
            print("localStorage: не записалось", key, e)
            return False


def web_store():
    if not WEB:
        return None
    try:
        return WebStore()
    except Exception as e:
        print("localStorage недоступен:", e)
        return None
