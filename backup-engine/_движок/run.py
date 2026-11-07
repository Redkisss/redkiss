# -*- coding: utf-8 -*-
"""Точка входа для .bat-файлов (запускается Python из venv: %LOCALAPPDATA%\\redkiss\\venv).
   run.py view      — собрать и открыть сайт у себя
   run.py publish   — собрать и выложить в интернет
   run.py build     — только собрать
   run.py access    — проверить вход в GitHub (для Подготовка.bat)"""
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True          # не мусорим файлами __pycache__ в рабочей папке
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def check_libs():
    try:
        import openpyxl  # noqa: F401
        import PIL  # noqa: F401
        return True
    except Exception:
        print("\nНе найдены нужные библиотеки Python.")
        print("Запусти файл Подготовка.bat — он их установит (достаточно один раз на каждом компьютере).")
        return False


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "access":
        import publish
        return 0 if publish.check_access() else 1
    if not check_libs():
        return 1

    import checks
    if not checks.report_duplicates():       # дубли «(1)» — остановиться до всего остального
        return 1

    import publish
    from common import CACHE_DIR
    if cmd == "publish":
        if not publish.prepare_repo():
            return 1
    else:
        publish.ensure_service_dir()

    if not (CACHE_DIR / "manifest.json").exists():
        print("\nНа этом компьютере ещё нет кэша сжатых картинок (так бывает при первом запуске на новом ПК).")
        print("Поэтому первая сборка может занять несколько минут — это нормально, просто подожди.")
        print("Дальше будет быстро: сжимаются только новые и изменённые фото.")

    import build as B
    res = B.build()
    B.print_report(res)
    if res.get("fatal"):
        return 1
    if cmd == "view":
        import serve
        return serve.serve()
    if cmd == "publish":
        return publish.publish(res)
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    try:
        code = main()
    except KeyboardInterrupt:
        code = 0
    except Exception:
        from common import ERROR_LOG
        try:
            ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
            ERROR_LOG.write_text(traceback.format_exc(), encoding="utf-8")
            where = str(ERROR_LOG)
        except Exception:
            where = "(не удалось сохранить)"
        print("\n" + "!" * 60)
        print("Что-то пошло не так внутри программы (это не твоя ошибка).")
        print("Подробности сохранены в файле: " + where)
        print("Пришли этот файл мне — я разберусь.")
        print("Последняя строка ошибки:  " + traceback.format_exc().strip().splitlines()[-1])
        print("!" * 60)
        code = 1
    sys.exit(code)
