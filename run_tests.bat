@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem тесты логики: pygame им не нужен
set PY=python
where python >nul 2>nul
if errorlevel 1 set PY=py
%PY% -m unittest discover -s tests -t .
echo.
pause
