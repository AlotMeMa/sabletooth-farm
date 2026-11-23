# -*- coding: utf-8 -*-
"""Фоновая музыка.

Положи файл в assets/music/:
    summer.ogg / medieval.ogg / winter.ogg — своя музыка для каждой фермы;
    main.ogg — общая, играет там, где своей нет;
    tavern.ogg — музыка таверны (нет файла — в таверне играет музыка фермы).
Форматы: .ogg (лучше всего), .mp3, .wav. Трек играет по кругу, при переезде плавно меняется.
Громкость — в «Настройках», клавиша M — выключить/включить звук.
Звуки кнопок — assets/sfx/hover.ogg и click.ogg (без файлов играет встроенный мягкий щелчок).
"""
import os

import pygame

from .config import ASSET_DIR

AUDIO_EXTS = (".ogg", ".mp3", ".wav")
MUSIC_NAMES = ("summer", "medieval", "winter", "main", "tavern", "tavern_girl")   # tavern_girl — песня певицы Милы (3.16.1)
VOLUMES = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
FADE_MS = 1500


def music_dir():
    return os.path.join(ASSET_DIR, "music")


def find_music(farm_id, scene=None):
    """Файл музыки: для места (scene, например "tavern") — его трек, если он есть;
    для фермы — своя, иначе общая main. None — музыки нет."""
    folder = music_dir()
    if not os.path.isdir(folder):
        return None
    files = {}
    # 3.11.2: если лежат и summer.ogg, и summer.wav — берём .ogg (порядок AUDIO_EXTS), а не что вернёт папка
    for fn in sorted(os.listdir(folder), key=lambda f: AUDIO_EXTS.index(os.path.splitext(f)[1].lower())
                     if os.path.splitext(f)[1].lower() in AUDIO_EXTS else 99):
        stem, ext = os.path.splitext(fn)
        if ext.lower() in AUDIO_EXTS:
            files.setdefault(stem.lower(), os.path.join(folder, fn))
    if scene and scene in files:
        return files[scene]
    return files.get(farm_id) or files.get("main")


def has_scene_music(scene):
    """Лежит ли свой трек для места scene (например "tavern_girl")."""
    folder = music_dir()
    if not os.path.isdir(folder):
        return False
    return any(os.path.splitext(fn)[0].lower() == scene and os.path.splitext(fn)[1].lower() in AUDIO_EXTS
               for fn in os.listdir(folder))


class Music:
    def __init__(self, volume=0.4):
        self.ok = False          # есть ли вообще звук (на компьютере без колонок его может не быть)
        self.current = None      # путь к файлу, который играет сейчас
        self.volume = volume
        self.muted = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.ok = True
        except Exception as e:   # нет звуковой карты/драйвера — играем без звука
            print("Звук недоступен:", e)

    def effective_volume(self):
        return 0.0 if self.muted else self.volume

    def play_for(self, farm_id, scene=None):
        """Включает музыку фермы (или места scene). Если играет та же — ничего не трогает."""
        if not self.ok:
            return
        path = find_music(farm_id, scene)
        if path == self.current:
            return
        self.current = path
        try:
            pygame.mixer.music.stop()
            if path is None:
                return
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.effective_volume())
            pygame.mixer.music.play(-1, fade_ms=FADE_MS)
            print("Музыка:", os.path.relpath(path, ASSET_DIR))
        except Exception as e:   # битый файл или неподдерживаемый формат — без музыки, но не падаем
            print(f"Не удалось включить музыку {path}: {e}")
            self.current = None

    def position(self):
        """Сколько секунд играет текущая музыка (с момента включения, повторы не сбрасывают) или None.
        Таверна по этому времени держит бард в такт (3.5)."""
        if not self.ok or self.current is None:
            return None
        try:
            ms = pygame.mixer.music.get_pos()
        except Exception:
            return None
        return ms / 1000.0 if ms is not None and ms >= 0 else None

    def apply_volume(self):
        if self.ok:
            try:
                pygame.mixer.music.set_volume(self.effective_volume())
            except Exception:
                pass

    def next_volume(self):
        """0% -> 20% -> ... -> 100% -> 0% (кнопка в настройках)."""
        idx = min(range(len(VOLUMES)), key=lambda i: abs(VOLUMES[i] - self.volume))
        self.volume = VOLUMES[(idx + 1) % len(VOLUMES)]
        self.muted = False
        self.apply_volume()

    def toggle_mute(self):
        self.muted = not self.muted
        self.apply_volume()

    def label(self):
        if not self.ok:
            return "Звук недоступен"
        if self.current is None:
            return "Музыки нет"
        if self.muted or self.volume == 0:
            return "Музыка: выкл"
        return f"Музыка: {round(self.volume * 100)}%"


# ======================================================================
#                     ЗВУКИ: кнопки, сбор, события
# ======================================================================
# Любой звук можно заменить своим файлом: assets/sfx/<имя>.ogg (или .wav/.mp3).
# Без файлов игра сама «синтезирует» короткие мягкие звуки — так звук есть сразу.
import array
import math
import random
import time

SFX_INFO = {   # имя -> когда играет
    "hover": "наведение на кнопку",
    "click": "нажатие кнопки",
    "coin": "сбор урожая с грядки",
    "coin_big": "гигантский урожай x10, пойманная белка",
    "buy": "покупка (уровень грядки, зверь, здание, крестьянин...)",
    "levelup": "веха грядки, улучшение в дереве",
    "product": "сбор продуктов сарая, хлеба, продажа муки",
    "feed": "покормить зверей / засыпать зерно",
    "squirrel": "белка выбежала на луг",
    "crow": "ворона села на грядку",
    "shoo": "прогнать ворону или разбойника",
    "bandit": "разбойник крадётся",
    "truck": "приехал грузовик скупщика",
    "fanfare": "приехал сборщик податей, переезд, праздник урожая",
    "rain": "дождь",
    "sun": "солнечный бонус",
    "sell": "продажа фермы скупщику",
    "quest": "задание таверны выполнено",
    "claim": "награда за задание получена",
    "crowd": "гул голосов в таверне (фон, играет по кругу)",
}
SFX_NAMES = tuple(SFX_INFO)
MIN_GAP = {"coin": 0.06, "hover": 0.03, "feed": 0.1}   # чтобы при сборе «пачкой» не трещало

# --- маленький синтезатор: события (начало, вид, параметры) смешиваются в один звук ---
NOTE = {"C5": 523.3, "E5": 659.3, "G5": 784.0, "A5": 880.0, "C6": 1046.5, "E6": 1318.5, "G6": 1568.0,
        "B6": 1975.5, "C7": 2093.0, "E7": 2637.0, "G7": 3136.0, "D6": 1174.7, "B5": 987.8}


def _tone(rate, f0, f1, dur, amp, wave="sine", vib=0.0):
    n = int(rate * dur)
    out = [0.0] * n
    ph = 0.0
    for i in range(n):
        t = i / n
        f = f0 + (f1 - f0) * t
        if vib:
            f *= 1 + 0.04 * math.sin(2 * math.pi * vib * i / rate)
        ph += 2 * math.pi * f / rate
        if wave == "bright":      # мягкий «колокольчик/медь»: основной тон + немного обертонов
            v = math.sin(ph) + 0.35 * math.sin(2 * ph) + 0.15 * math.sin(3 * ph)
        elif wave == "saw":
            v = 2 * ((ph / (2 * math.pi)) % 1.0) - 1
        else:
            v = math.sin(ph)
        env = min(1.0, i / (rate * 0.004)) * (1 - t) ** 2
        out[i] = v * env * amp
    return out


def _noise(rate, dur, amp, smooth0=0.6, smooth1=0.95):
    """Шум с плавающим «фильтром»: smooth ближе к 1 — глуше. Для «вжух», хруста."""
    n = int(rate * dur)
    out = [0.0] * n
    y = 0.0
    rnd = random.Random(7)
    for i in range(n):
        t = i / n
        k = smooth0 + (smooth1 - smooth0) * t
        y = k * y + (1 - k) * rnd.uniform(-1, 1)
        env = math.sin(math.pi * t)             # плавно нарастает и затихает
        out[i] = y * env * amp * 3
    return out


def _spec(name):
    """Из чего «собран» звук: список (время начала, функция-генератор)."""
    T = lambda f0, f1, d, a, w="sine", vib=0.0: (lambda r: _tone(r, f0, f1, d, a, w, vib))
    N = NOTE
    if name == "hover":
        return [(0, T(1500, 1900, 0.045, 0.16))]
    if name == "click":
        return [(0, T(700, 380, 0.07, 0.30))]
    if name == "coin":
        return [(0, T(N["E6"], N["E6"], 0.05, 0.22, "bright")), (0.045, T(N["B6"], N["B6"], 0.16, 0.22, "bright"))]
    if name == "coin_big":
        return [(i * 0.06, T(f, f, 0.18, 0.2, "bright")) for i, f in enumerate((N["C6"], N["E6"], N["G6"], N["C7"]))]
    if name == "buy":
        return [(0, T(520, 980, 0.08, 0.26))]
    if name == "levelup":
        return [(0, T(N["G5"], N["G5"], 0.09, 0.22, "bright")), (0.08, T(N["B5"], N["B5"], 0.09, 0.22, "bright")),
                (0.16, T(N["D6"], N["D6"], 0.25, 0.22, "bright"))]
    if name == "product":
        return [(0, T(300, 820, 0.06, 0.28)), (0.06, T(N["E6"], N["E6"], 0.05, 0.18, "bright")),
                (0.10, T(N["B6"], N["B6"], 0.14, 0.18, "bright"))]
    if name == "feed":
        return [(0, lambda r: _noise(r, 0.07, 0.25, 0.85, 0.9)), (0.1, lambda r: _noise(r, 0.07, 0.22, 0.85, 0.9))]
    if name == "squirrel":
        return [(i * 0.07, T(2600, 3600, 0.045, 0.14)) for i in range(3)]
    if name == "crow":
        caw = lambda r: [a * 0.6 + b for a, b in zip(_tone(r, 640, 470, 0.22, 0.20, "saw", vib=28),
                                                     _noise(r, 0.22, 0.08, 0.3, 0.4))]
        return [(0, caw), (0.32, caw)]
    if name == "shoo":
        return [(0, lambda r: _noise(r, 0.28, 0.12, 0.5, 0.97))]
    if name == "bandit":
        return [(0, T(196, 196, 0.22, 0.30, "bright")), (0.24, T(185, 185, 0.35, 0.30, "bright"))]
    if name == "truck":
        honk = lambda r: [a + b for a, b in zip(_tone(r, 392, 392, 0.14, 0.18, "bright"), _tone(r, 494, 494, 0.14, 0.14, "bright"))]
        return [(0, honk), (0.2, honk)]
    if name == "fanfare":
        notes = (N["C5"], N["E5"], N["G5"], N["C6"])
        return [(i * 0.11, T(f, f, 0.12 if i < 3 else 0.4, 0.22, "bright")) for i, f in enumerate(notes)]
    if name == "rain":
        return [(i * 0.12, T(f, f, 0.45, 0.14)) for i, f in enumerate((N["G6"], N["E6"], N["C6"]))]
    if name == "sun":
        return [(i * 0.06, T(f, f, 0.2, 0.13, "bright")) for i, f in enumerate((N["C7"], N["E7"], N["G7"], N["E7"]))]
    if name == "quest":
        return [(i * 0.09, T(f, f, 0.12 if i < 2 else 0.35, 0.2, "bright"))
                for i, f in enumerate((N["G5"], N["C6"], N["E6"]))]
    if name == "claim":
        return [(i * 0.05, T(f, f, 0.16, 0.18, "bright")) for i, f in enumerate((N["C6"], N["E6"], N["G6"], N["C7"], N["E7"]))]
    if name == "crowd":
        return [(0, _crowd)]
    if name == "sell":
        return [(i * 0.05, T(f, f, 0.14, 0.17, "bright"))
                for i, f in enumerate((N["E6"], N["G6"], N["B6"], N["E6"], N["G6"], N["B6"], N["C7"]))]
    return []


def _crowd(rate, dur=8.0):
    """Гул таверны: тихие «бормочущие» голоса, смешки, звон кружек. Петля без шва —
    всё, что вылезает за конец, переносится в начало. Считается на половинной частоте (голосам хватает)."""
    r2 = rate // 2
    n = int(r2 * dur)
    mix = [0.0] * n
    rnd = random.Random(11)
    # 1) ровный низкий шум зала
    y = 0.0
    for i in range(n):
        y = 0.985 * y + 0.015 * rnd.uniform(-1, 1)
        mix[i] += y * 0.55

    def add(start, samples):
        for j, v in enumerate(samples):
            mix[(start + j) % n] += v

    # 2) голоса: «пилка» с плавающим тоном, слоги 3–6 в секунду, мягко сглажено
    for _ in range(26):
        d = rnd.uniform(0.6, 1.6)
        m = int(r2 * d)
        f0 = rnd.uniform(95, 240)
        syl = rnd.uniform(3, 6)
        amp = rnd.uniform(0.018, 0.04)
        ph, lp, out = 0.0, 0.0, []
        for j in range(m):
            t = j / m
            f = f0 * (1 + 0.08 * math.sin(2 * math.pi * 0.7 * j / r2) + 0.05 * math.sin(2 * math.pi * syl * 0.37 * j / r2))
            ph += f / r2
            v = 2 * (ph % 1.0) - 1
            lp = 0.82 * lp + 0.18 * v
            env = abs(math.sin(math.pi * syl * j / r2)) ** 1.5 * math.sin(math.pi * t)
            out.append(lp * env * amp)
        add(rnd.randrange(n), out)
    # 3) смешки: «ха-ха-ха» с понижением тона
    for _ in range(4):
        start = rnd.randrange(n)
        f0 = rnd.uniform(260, 380)
        for k in range(rnd.randint(3, 5)):
            m = int(r2 * 0.11)
            ph, out = 0.0, []
            for j in range(m):
                ph += f0 * (1 - 0.06 * k) / r2
                v = 2 * (ph % 1.0) - 1
                out.append(v * math.sin(math.pi * j / m) * 0.02)
            add(start + int(k * 0.16 * r2), out)
    # 4) звон кружек
    for _ in range(5):
        f = rnd.uniform(1800, 2600)
        m = int(r2 * 0.25)
        out = [math.sin(2 * math.pi * f * j / r2) * (1 - j / m) ** 3 * 0.05 for j in range(m)]
        add(rnd.randrange(n), out)
    peak = max(1e-6, max(abs(v) for v in mix))
    mix = [v * 0.35 / peak for v in mix]
    full = []
    for v in mix:               # обратно на полную частоту
        full.append(v)
        full.append(v)
    return full


def _synth(name):
    init = pygame.mixer.get_init()
    rate, size, channels = init if isinstance(init, tuple) else (44100, -16, 2)
    if size != -16:   # синтез рассчитан на 16-битный звук; иначе лучше тишина, чем треск
        return None
    parts = [(int(t0 * rate), gen(rate)) for t0, gen in _spec(name)]
    if not parts:
        return None
    total = max(start + len(p) for start, p in parts)
    mix = [0.0] * total
    for start, p in parts:
        for i, v in enumerate(p):
            mix[start + i] += v
    buf = array.array("h")
    for v in mix:
        v = int(32767 * max(-1.0, min(1.0, v)))
        for _c in range(channels):
            buf.append(v)
    return pygame.mixer.Sound(buffer=buf.tobytes())


def find_sfx(name):
    folder = os.path.join(ASSET_DIR, "sfx")
    if not os.path.isdir(folder):
        return None
    for fn in os.listdir(folder):
        stem, ext = os.path.splitext(fn)
        if stem.lower() == name and ext.lower() in AUDIO_EXTS:
            return os.path.join(folder, fn)
    return None


class Sfx:
    def __init__(self, music, volume=0.6):
        self.music = music          # общий «выключить звук» живёт в Music.muted
        self.volume = volume
        self.sounds = {}            # загружаются при первом проигрывании
        self.last = {}

    def get(self, name):
        if name not in self.sounds:
            snd = None
            if self.music.ok:
                path = find_sfx(name)
                try:
                    snd = pygame.mixer.Sound(path) if path else _synth(name)
                except Exception as e:
                    print(f"Звук {name} не загрузился: {e}")
            self.sounds[name] = snd
        return self.sounds[name]

    def play(self, name):
        if self.music.muted or self.volume <= 0 or not self.music.ok:
            return
        now = time.time()
        if now - self.last.get(name, 0.0) < MIN_GAP.get(name, 0.0):
            return
        snd = self.get(name)
        if snd is None:
            return
        self.last[name] = now
        try:
            snd.set_volume(self.volume)
            snd.play()
        except Exception:
            pass

    # ---- фоновая петля (гул таверны) ----
    AMBIENT_K = 0.55            # петля тише обычных звуков

    def ambient(self, name):
        """Включает фоновую петлю name (None — выключить). Громкость = «Звуки» x AMBIENT_K."""
        cur = getattr(self, "amb", None)
        if cur and cur[0] == name:
            return
        if cur and cur[1] is not None:
            try:
                cur[1].fadeout(600)
            except Exception:
                pass
        self.amb = None
        if name is None or not self.music.ok:
            return
        snd = self.get(name)
        self.amb = (name, snd)
        if snd is None:
            return
        try:
            snd.set_volume(self.ambient_volume())
            snd.play(loops=-1, fade_ms=800)
        except Exception:
            pass

    def ambient_volume(self):
        return 0.0 if self.music.muted else self.volume * self.AMBIENT_K

    def update_ambient(self):
        """Каждый кадр: ползунок «Звуки» и «Выключить звук» сразу действуют и на петлю."""
        amb = getattr(self, "amb", None)
        if amb and amb[1] is not None:
            try:
                amb[1].set_volume(self.ambient_volume())
            except Exception:
                pass

    def preload(self):
        for name in SFX_NAMES:      # и гул таверны (~0.5 с) — пока видна заставка
            self.get(name)
