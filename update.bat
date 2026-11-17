@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py update.py %*) else (python update.py %*)
echo.
pause
