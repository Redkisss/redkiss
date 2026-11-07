@echo off
chcp 65001 >nul
cd /d "%~dp0"
title РЕДКИСС - просмотр сайта
set PYTHONIOENCODING=utf-8
set "PY="
python --version >nul 2>nul && set "PY=python"
if not defined PY (
  py -3 --version >nul 2>nul && set "PY=py -3"
)
if not defined PY (
  echo.
  echo Не найден Python - без него сайт не собрать.
  echo Скачай с https://www.python.org/downloads/ и при установке
  echo ОБЯЗАТЕЛЬНО поставь галочку "Add python.exe to PATH".
  echo Потом запусти этот файл ещё раз.
  echo.
  pause
  exit /b 1
)
echo.
%PY% "Движок\run.py" view
echo.
echo Нажми любую клавишу, чтобы закрыть окно...
pause >nul
