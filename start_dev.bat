@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem ищем Python, у которого стоит pygame: сначала python, потом py
set PY=python
python -c "import pygame" >nul 2>nul
if errorlevel 1 set PY=py
echo Режим разработчика: F1 - панель, отдельное сохранение farm_save_dev.json
%PY% farm_idle.py --dev
if errorlevel 1 (
  echo.
  echo Игра закрылась с ошибкой. Если пишет, что нет pygame:  %PY% -m pip install pygame
  pause
)
