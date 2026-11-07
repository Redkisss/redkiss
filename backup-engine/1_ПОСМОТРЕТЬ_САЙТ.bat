@echo off
chcp 65001 >nul
cd /d "%~dp0"
title РЕДКИСС - просмотр сайта
set PYTHONIOENCODING=utf-8
set PYTHONDONTWRITEBYTECODE=1
set "PY=%~dp0_движок\python\python.exe"
if not exist "%PY%" (
  echo.
  echo Не найден встроенный Python: _движок\python\python.exe
  echo Возможно, Google Диск ещё не докачал файлы. Подожди, пока он закончит синхронизацию,
  echo и запусти этот файл ещё раз.
  echo.
  pause
  exit /b 1
)
echo.
"%PY%" "%~dp0_движок\run.py" view
echo.
echo Нажми любую клавишу, чтобы закрыть окно...
pause >nul
