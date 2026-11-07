@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
title РЕДКИСС - подготовка компьютера
set PYTHONIOENCODING=utf-8
set PYTHONDONTWRITEBYTECODE=1
set "DATA=%LOCALAPPDATA%\redkiss"
set "VENV=%DATA%\venv"
set "VPY=%VENV%\Scripts\python.exe"
set "PIP_CACHE_DIR=%DATA%\pip-cache"
set "REQ=%~dp0_движок\requirements.txt"
set "RUNPY=%~dp0_движок\run.py"

for /d /r "%~dp0" %%D in (__pycache__) do if exist "%%D" rd /s /q "%%D"

echo.
echo ============================================================
echo   РЕДКИСС: подготовка компьютера
echo   Запускается один раз на каждом ПК. Повторный запуск безопасен.
echo ============================================================
echo.
if not exist "%REQ%" goto :noreq

rem ================= 1. Python =================
echo [1/4] Проверяю Python...
call :findpy
if defined PYEXE goto :py_ok
call :findwinget
if not defined WINGET goto :py_manual
echo     Python не найден. Ставлю через winget. Если Windows спросит разрешение - нажми «Да».
"%WINGET%" install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
call :findpy
if defined PYEXE goto :py_ok
goto :py_manual
:py_ok
echo     Python найден: %PYEXE%

rem ================= 2. Git =================
echo.
echo [2/4] Проверяю Git...
call :findgit
if defined GITEXE goto :git_ok
call :findwinget
if not defined WINGET goto :git_manual
echo     Git не найден. Ставлю через winget. Если Windows спросит разрешение - нажми «Да».
"%WINGET%" install -e --id Git.Git --silent --accept-package-agreements --accept-source-agreements
call :findgit
if defined GITEXE goto :git_ok
goto :git_manual
:git_ok
echo     Git найден: %GITEXE%

rem ================= 3. Библиотеки Python (venv вне папки проекта) =================
echo.
echo [3/4] Готовлю библиотеки Python (папка %VENV%)...
if not exist "%DATA%" mkdir "%DATA%"
if not exist "%VPY%" if exist "%VENV%" rd /s /q "%VENV%"
if not exist "%VPY%" goto :mkvenv
"%VPY%" -c "import sys" >nul 2>nul
if not errorlevel 1 goto :venv_ok
echo     Прежняя среда не работает (возможно, Python был удалён или обновлён) - создаю заново...
rd /s /q "%VENV%"
:mkvenv
"%PYEXE%" -m venv "%VENV%"
if errorlevel 1 goto :venv_fail
if not exist "%VPY%" goto :venv_fail
:venv_ok
echo     Ставлю библиотеки (в первый раз это занимает 1-2 минуты, нужен интернет)...
"%VPY%" -m pip install --disable-pip-version-check --no-warn-script-location -q -r "%REQ%"
if errorlevel 1 goto :pip_fail
"%VPY%" -c "import openpyxl, PIL, pillow_heif" >nul 2>nul
if errorlevel 1 goto :pip_fail
echo     Библиотеки готовы.

rem ================= 4. Вход в GitHub =================
echo.
echo [4/4] Настраиваю вход в GitHub и проверяю доступ к сайту...
echo     Если откроется окно браузера «Sign in to GitHub» - войди в аккаунт и нажми «Authorize».
"%VPY%" "%RUNPY%" access
if errorlevel 1 goto :gh_fail

echo.
echo ============================================================
echo   ГОТОВО! Компьютер подготовлен.
echo   Дальше работай как обычно:
echo     1_ПОСМОТРЕТЬ_САЙТ.bat - посмотреть сайт у себя
echo     2_ОПУБЛИКОВАТЬ.bat    - выложить сайт в интернет
echo ============================================================
set "CODE=0"
goto :end

rem ---------------------------------------------------------------- ошибки
:noreq
echo Не найден файл _движок\requirements.txt.
echo Похоже, папка _движок скопировалась не целиком (Google Диск ещё не докачал файлы?).
echo Подожди, пока Google Диск закончит синхронизацию, и запусти этот файл ещё раз.
set "CODE=1"
goto :end

:py_manual
echo.
echo Не получилось поставить Python автоматически. Поставь его вручную, это просто:
echo   1. Сейчас откроется страница python.org. Нажми жёлтую кнопку «Download Python».
echo   2. Запусти скачанный файл.
echo   3. В ПЕРВОМ окне установки внизу поставь галочку «Add python.exe to PATH».
echo   4. Нажми «Install Now» и дождись надписи «Setup was successful», потом «Close».
echo   5. Закрой это окно и запусти Подготовка.bat ещё раз.
start "" "https://www.python.org/downloads/windows/"
set "CODE=1"
goto :end

:git_manual
echo.
echo Не получилось поставить Git автоматически. Поставь его вручную, это просто:
echo   1. Сейчас откроется страница git-scm.com. Нажми «Click here to download» (64-bit).
echo   2. Запусти скачанный файл.
echo   3. Во всех окнах установки ничего не меняй - просто нажимай «Next», в конце «Install» и «Finish».
echo   4. Закрой это окно и запусти Подготовка.bat ещё раз.
start "" "https://git-scm.com/download/win"
set "CODE=1"
goto :end

:venv_fail
echo.
echo Не получилось создать папку с библиотеками: %VENV%
echo Закрой это окно и запусти Подготовка.bat ещё раз. Если повторится - пришли мне скриншот.
set "CODE=1"
goto :end

:pip_fail
echo.
echo Не получилось скачать библиотеки Python. Скорее всего, нет интернета или он нестабилен.
echo Проверь соединение и запусти Подготовка.bat ещё раз - докачается то, чего не хватает.
set "CODE=1"
goto :end

:gh_fail
echo.
echo Не получилось подтвердить доступ к GitHub (причина написана выше).
echo Смотреть сайт (1_ПОСМОТРЕТЬ_САЙТ.bat) уже можно, а чтобы публиковать - запусти Подготовка.bat ещё раз
echo и войди в аккаунт GitHub в окне браузера.
set "CODE=1"
goto :end

:end
echo.
echo Нажми любую клавишу, чтобы закрыть окно...
pause >nul
exit /b %CODE%

rem ================================================================ подпрограммы
rem Ищет Python. Не опирается на PATH: сначала py-launcher (в т.ч. по полному пути),
rem потом обычные папки установки. Результат - в переменной PYEXE (пусто, если не найден).
:findpy
set "PYEXE="
set "PYL="
for /f "usebackq delims=" %%P in (`where py 2^>nul`) do if not defined PYL set "PYL=%%~dpP"
if not defined PYL if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" set "PYL=%LOCALAPPDATA%\Programs\Python\Launcher\"
if not defined PYL if exist "%windir%\py.exe" set "PYL=%windir%\"
if not defined PYL if exist "%ProgramFiles%\Python Launcher\py.exe" set "PYL=%ProgramFiles%\Python Launcher\"
if defined PYL set "PATH=%PYL%;%PATH%"
if defined PYL for %%V in (3.12 3.13 3.11 3.14 3.10 3.15 3) do if not defined PYEXE call :trypy %%V
for %%N in (312 313 311 314 310 315) do if not defined PYEXE call :trydir %%N
exit /b 0

rem Python из Microsoft Store не годится: он подменяет папку %LOCALAPPDATA% и ломает venv. Такой пропускаем.
:trypy
set "CAND="
for /f "usebackq delims=" %%P in (`py -%1 -c "import sys;print(sys.executable)" 2^>nul`) do if not defined CAND set "CAND=%%P"
if not defined CAND exit /b 0
echo "%CAND%" | find /i "\WindowsApps\" >nul
if errorlevel 1 set "PYEXE=%CAND%"
exit /b 0

:trydir
if exist "%LOCALAPPDATA%\Programs\Python\Python%1\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python%1\python.exe"
if not defined PYEXE if exist "%ProgramFiles%\Python%1\python.exe" set "PYEXE=%ProgramFiles%\Python%1\python.exe"
exit /b 0

rem Ищет Git (результат - GITEXE).
:findgit
set "GITEXE="
for /f "usebackq delims=" %%G in (`where git 2^>nul`) do if not defined GITEXE set "GITEXE=%%G"
if not defined GITEXE if exist "%ProgramFiles%\Git\cmd\git.exe" set "GITEXE=%ProgramFiles%\Git\cmd\git.exe"
if not defined GITEXE if exist "%ProgramW6432%\Git\cmd\git.exe" set "GITEXE=%ProgramW6432%\Git\cmd\git.exe"
if not defined GITEXE if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" set "GITEXE=%LOCALAPPDATA%\Programs\Git\cmd\git.exe"
exit /b 0

rem Ищет winget (результат - WINGET).
:findwinget
set "WINGET="
for /f "usebackq delims=" %%W in (`where winget 2^>nul`) do if not defined WINGET set "WINGET=%%W"
if not defined WINGET if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe" set "WINGET=%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe"
exit /b 0
