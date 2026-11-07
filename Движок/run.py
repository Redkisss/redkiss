# -*- coding: utf-8 -*-
"""Точка входа для .bat-файлов.
   python run.py view      — собрать и открыть сайт у себя
   python run.py publish   — собрать и выложить в интернет
   python run.py build     — только собрать
   python run.py connect   — один раз подключить к GitHub
Использует только стандартную библиотеку, пока не поставит нужные пакеты."""
import importlib
import os
import subprocess
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

NEED = [("openpyxl", "openpyxl"), ("PIL", "Pillow"), ("pillow_heif", "pillow-heif")]


def ensure_packages():
    missing = []
    for mod, pkg in NEED:
        try:
            importlib.import_module(mod)
        except Exception:
            missing.append(pkg)
    if not missing:
        return True
    print("Первый запуск: устанавливаю нужные программки для Python:", ", ".join(missing))
    print("(нужен интернет, это займёт около минуты)")
    r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check"] + missing)
    if r.returncode != 0:
        # pillow-heif необязателен: без него просто не откроются фото HEIC
        required = [p for p in missing if p != "pillow-heif"]
        if required:
            subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check"] + required)
    for mod, pkg in NEED[:2]:
        try:
            importlib.invalidate_caches()
            importlib.import_module(mod)
        except Exception:
            print("\nНе получилось установить «" + pkg + "». Проверь интернет и запусти ещё раз.")
            return False
    return True


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if not ensure_packages():
        return 1
    if cmd == "connect":
        import connect
        url = connect.connect()
        if not url:
            return 1
        ans = input("\nОпубликовать сайт прямо сейчас? (д/н): ").strip().lower()
        if ans not in ("д", "да", "y", "yes"):
            print("Хорошо. Когда захочешь выложить сайт — запусти 2_ОПУБЛИКОВАТЬ.bat")
            return 0
        cmd = "publish"
    import build as B
    res = B.build()
    B.print_report(res)
    if res.get("fatal"):
        return 1
    if cmd == "view":
        import serve
        return serve.serve()
    if cmd == "publish":
        import publish
        return publish.publish(res)
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    try:
        code = main()
    except KeyboardInterrupt:
        code = 0
    except Exception:
        log = HERE / "_cache" / "error.log"
        log.parent.mkdir(exist_ok=True)
        log.write_text(traceback.format_exc(), encoding="utf-8")
        print("\n" + "!" * 60)
        print("Что-то пошло не так внутри программы (это не твоя ошибка).")
        print("Подробности сохранены в файле: " + str(log))
        print("Пришли этот файл мне — я разберусь.")
        print("Последняя строка ошибки:  " + traceback.format_exc().strip().splitlines()[-1])
        print("!" * 60)
        code = 1
    sys.exit(code)
