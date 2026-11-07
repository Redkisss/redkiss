@echo off
chcp 65001 >nul
cd /d "%~dp0"
title РЕДКИСС - просмотр сайта
set PYTHONIOENCODING=utf-8
set PYTHONDONTWRITEBYTECODE=1
set "VPY=%LOCALAPPDATA%\redkiss\venv\Scripts\python.exe"
for /d /r "%~dp0" %%D in (__pycache__) do if exist "%%D" rd /s /q "%%D"
if not exist "%VPY%" goto :noprep
"%VPY%" -c "import sys" >nul 2>nul
if errorlevel 1 goto :noprep
echo.
"%VPY%" "%~dp0_движок\run.py" view
echo.
echo Нажми любую клавишу, чтобы закрыть окно...
pause >nul
exit /b 0

:noprep
echo.
echo Сначала запусти Подготовка.bat
echo (она нужна один раз на каждом компьютере - поставит всё необходимое).
echo Потом запусти этот файл ещё раз.
echo.
echo Нажми любую клавишу, чтобы закрыть окно...
pause >nul
exit /b 1
