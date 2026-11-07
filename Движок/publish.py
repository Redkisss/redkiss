# -*- coding: utf-8 -*-
"""Публикация: git add / commit / push. Все сообщения — по-русски и простыми словами."""
import datetime
import json
import shutil
import subprocess
from pathlib import Path

from common import CACHE_DIR, ROOT

BRANCH = "main"


def git(*args, check=False):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, timeout=600)


def publish(res, log=print):
    if not shutil.which("git"):
        log("\nНа компьютере не установлен Git — без него публикация невозможна.")
        log("Скачай и установи с https://git-scm.com/download/win (везде жми «Next»), потом запусти файл ещё раз.")
        return 1

    if not (ROOT / ".git").exists():
        log("\nСайт ещё не подключён к GitHub (это делается один раз).")
        log("Открой ИНСТРУКЦИЯ.txt, раздел «Первая публикация» — там по шагам.")
        return 1

    remote = git("remote", "get-url", "origin")
    if remote.returncode != 0 or not remote.stdout.strip():
        log("\nСайт ещё не подключён к GitHub (не указан адрес репозитория).")
        log("Открой ИНСТРУКЦИЯ.txt, раздел «Первая публикация» — там по шагам.")
        return 1

    if not res["ok"]:
        log("\nВ сборке были ошибки (см. выше) — публиковать не буду, чтобы не выложить сломанный сайт.")
        log("Исправь и запусти ещё раз.")
        return 1

    # пустой коммит без личных данных не нужен: задаём имя только если оно не настроено
    if not git("config", "user.name").stdout.strip():
        git("config", "user.name", "REDKISS")
    if not git("config", "user.email").stdout.strip():
        git("config", "user.email", "redkiss@users.noreply.github.com")

    cur = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if cur and cur != "HEAD" and cur != BRANCH:
        git("branch", "-M", BRANCH)

    log("\nГотовлю публикацию…")
    add = git("add", "-A")
    if add.returncode != 0:
        log("Не получилось подготовить файлы: " + add.stderr.strip())
        return 1
    status = git("status", "--porcelain")
    changes = [l for l in status.stdout.splitlines() if l.strip()]
    ahead = git("rev-list", "--count", "@{u}..HEAD")
    has_unpushed = ahead.returncode == 0 and ahead.stdout.strip() not in ("", "0")
    first_time = git("rev-parse", "HEAD").returncode != 0

    if not changes and not has_unpushed and not first_time:
        log("Ничего нового: сайт на GitHub уже такой же. Публиковать нечего.")
        return 0

    if changes:
        now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        parts = []
        try:
            s = json.loads((CACHE_DIR / "last_build.json").read_text(encoding="utf-8"))
            if s["new"]:
                parts.append("Новые: " + ", ".join(s["new"]))
            if s["changed"]:
                parts.append("Изменены: " + ", ".join(s["changed"]))
            if s["removed"]:
                parts.append("Убраны: " + ", ".join(s["removed"]))
        except Exception:
            pass
        subject = f"Обновление сайта {now}"
        body = "\n".join(parts) or f"Изменённых файлов: {len(changes)}"
        c = git("commit", "-m", subject, "-m", body)
        if c.returncode != 0:
            log("Не получилось сохранить изменения:\n" + (c.stdout + c.stderr).strip())
            return 1
        log(f"Сохранено: {subject}")
        for p in parts:
            log("  " + p)

    log("Отправляю на GitHub (в первый раз может открыться окно входа — войди в свой аккаунт)…")
    has_upstream = git("rev-parse", "--abbrev-ref", "@{u}").returncode == 0
    push = (git("push") if has_upstream else git("push", "-u", "origin", BRANCH))
    if push.returncode != 0:
        err = (push.stdout + push.stderr).strip()
        log("\nНе получилось отправить сайт на GitHub.")
        low = err.lower()
        if any(w in low for w in ("authentication", "403", "could not read username", "permission denied", "invalid credentials")):
            log("Похоже, не прошёл вход в GitHub. Запусти файл ещё раз и войди в аккаунт в открывшемся окне.")
        elif any(w in low for w in ("could not resolve host", "unable to access", "timed out", "failed to connect")):
            log("Похоже, нет интернета. Проверь соединение и запусти ещё раз.")
        elif any(w in low for w in ("rejected", "non-fast-forward", "fetch first")):
            log("На GitHub есть изменения, которых нет у тебя на компьютере (например, правка прямо на сайте GitHub).")
            log("Напиши мне — я аккуратно соединю, ничего не потеряв. Сам ничего не удаляй.")
        elif "repository not found" in low:
            log("GitHub не нашёл репозиторий. Проверь, что он создан и адрес указан верно (см. ИНСТРУКЦИЯ.txt).")
        log("\nТехнические подробности (можно прислать мне):\n" + err)
        return 1

    url = res.get("site_url") or ""
    log("\n" + "=" * 60)
    if url:
        log(f"Готово! Сайт обновится через 1–2 минуты: {url}")
    else:
        log("Готово! Сайт обновится через 1–2 минуты (ссылка вида логин.github.io/redkiss/).")
    log("=" * 60)
    return 0
