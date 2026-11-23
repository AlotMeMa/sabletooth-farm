# -*- coding: utf-8 -*-
"""Общее для App и его примесей (3.15): импорты и константы интерфейса.
Каждый модуль-примесь делает `from .ui_common import *` — так в нём те же имена, что были в app.py."""
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
from .tutorial import Tutorial
from .particles import Particles, draw_shadow
from . import skin
from . import screenfit


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

