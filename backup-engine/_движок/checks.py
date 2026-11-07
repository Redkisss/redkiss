# -*- coding: utf-8 -*-
"""Проверка на «дубли» — копии файлов вида «товары (1).xlsx» или «01 (1).jpg».
Они появляются, когда Google Диск не смог аккуратно слить правки с двух компьютеров."""
import re

from common import PRODUCTS, ROOT

_DUP = re.compile(r"\s\(\d+\)$")


def _is_dup(path):
    stem = path.name if path.is_dir() else path.stem
    return bool(_DUP.search(stem))


def find_duplicates():
    found = []
    # рабочая папка (не заходя внутрь служебных и товарных папок)
    try:
        for p in ROOT.iterdir():
            if p.name.startswith(("_", ".", "~$")) or p == PRODUCTS:
                continue
            if _is_dup(p):
                found.append(p)
    except OSError:
        pass
    # всё внутри ТОВАРЫ
    if PRODUCTS.exists():
        for p in PRODUCTS.rglob("*"):
            if p.name.startswith(("~$", ".")) or p.name.lower() in ("desktop.ini", "thumbs.db"):
                continue
            if _is_dup(p):
                found.append(p)
    return found


def report_duplicates(log=print):
    """True, если дублей нет. Иначе пишет по-русски, что делать, и возвращает False."""
    dups = find_duplicates()
    if not dups:
        return True
    log("")
    log("=" * 60)
    log("СТОП. Нашлись копии файлов с «(1)», «(2)» в названии:")
    for p in dups:
        try:
            shown = p.relative_to(ROOT)
        except ValueError:
            shown = p
        log("   • " + str(shown))
    log("")
    log("Обычно так бывает, когда два компьютера одновременно правили один файл,")
    log("и Google Диск сохранил обе версии.")
    log("Что делать: открой эти файлы, оставь нужную версию, а лишнюю удали")
    log("(у нужной убери «(1)» из названия). Если это не копия, а просто такое название —")
    log("переименуй без скобок с цифрой. Потом запусти файл ещё раз.")
    log("Сайт не собирался и не публиковался — ничего не испорчено.")
    log("=" * 60)
    return False
