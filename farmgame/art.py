# -*- coding: utf-8 -*-
"""Вся графика: текст, примитивы, процедурные рисунки и загрузка спрайтов из assets/.

С 3.17 разложено по частям (art_sprites → art_base → art_plants → art_world → art_field, каждая берёт всё из
предыдущей); здесь — всё вместе, как раньше: from .art import * / art.что-угодно (читать и менять на месте;
присваивание art.X = ... до частей не дойдёт).
"""
from .art_field import *  # noqa: F401,F403
# закрытые кэши и помощники — тоже доступны как art._имя (как было до 3.17)
from .art_sprites import _sprite_cache, _sprite_scaled, _load_sprite  # noqa: F401,E402
from .art_base import _fonts, _texts, _font_files, _font_ratio, _sys_font, _ratio  # noqa: F401,E402
from .art_world import _stone, _eye, _beanie, _scarf, _animal_sprite  # noqa: F401,E402
from .art_field import (_fence_layers, _seamless_crop, _wide_front, _fence_front_as_strip, _glows, _lights,  # noqa
                        _light_disc)
