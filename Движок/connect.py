# -*- coding: utf-8 -*-
"""Однократное подключение папки сайта к репозиторию на GitHub."""
import re
import shutil
import subprocess

from common import ROOT


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)


def connect(log=print):
    if not shutil.which("git"):
        log("Не установлен Git. Скачай с https://git-scm.com/download/win (везде жми «Next») и запусти файл ещё раз.")
        return None
    log("Подключаем сайт к GitHub. Нужен уже созданный на github.com пустой репозиторий (см. ИНСТРУКЦИЯ.txt).\n")
    current = git("remote", "get-url", "origin").stdout.strip()
    if current:
        log(f"Сейчас сайт подключён к: {current}")
        if input("Заменить на другой адрес? (д/н): ").strip().lower() not in ("д", "да", "y", "yes"):
            return current
    login = input("Твой логин на GitHub (латиницей): ").strip().lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", login):
        log("Логин выглядит странно (только латиница, цифры и дефис). Запусти файл ещё раз.")
        return None
    repo = input("Название репозитория [redkiss]: ").strip() or "redkiss"
    if not re.fullmatch(r"[A-Za-z0-9._-]+", repo):
        log("Название репозитория — только латиница, цифры, точка, дефис и подчёркивание.")
        return None
    url = f"https://github.com/{login}/{repo}.git"
    if not (ROOT / ".git").exists():
        r = git("init", "-b", "main")
        if r.returncode != 0:
            git("init")
            git("branch", "-M", "main")
    if current:
        git("remote", "set-url", "origin", url)
    else:
        git("remote", "add", "origin", url)
    log(f"\nГотово. Сайт подключён к {url}")
    log(f"После публикации он будет по адресу: https://{login.lower()}.github.io/{repo}/")
    return url
