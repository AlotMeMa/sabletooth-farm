# -*- coding: utf-8 -*-
"""Общее для тестов: путь к игре и готовые фермы. Тестам не нужен pygame — они проверяют только логику."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from farmgame.logic import Farm  # noqa: E402


def summer_farm():
    """Летняя ферма середины игры: 8 грядок с фермерами, звери со скотниками."""
    f = Farm()
    f.levels = [200, 100, 100, 50, 50, 50, 25, 10, 0]
    f.fert = [2, 2, 2, 1, 1, 1, 0, 0, 0]
    f.farmers = [True] * 8 + [False]
    f.a_levels = [10, 10, 5, 0]
    f.a_keeper = [True, True, True, False]
    return f


def medieval_farm():
    """Средневековое поле: крестьяне на грядках, мельница и пекарня работают."""
    f = Farm()
    f.farm_index = 1
    f.reset_run()
    f.levels = [60, 50, 50, 50, 50, 50, 50, 50, 50]
    f.peasants = 8
    f.farmers = [False, False, True, False, True, False, False, True, False]   # зерновые: рожь, ячмень, полба
    f.m_levels = [2, 1]
    f.m_workers = [2, 1]
    return f
