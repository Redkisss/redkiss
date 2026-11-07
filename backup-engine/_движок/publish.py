# -*- coding: utf-8 -*-
"""Публикация через скрытую служебную копию репозитория (%USERPROFILE%\\.redkiss-publish),
которая лежит ВНЕ Google Диска. Все сообщения — по-русски и простыми словами."""
import datetime
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from common import BACKUP_DIR_NAME, CACHE_DIR, ENGINE, GIT_PORTABLE, ROOT, SERVICE, repo_url

BRANCH = "main"
ALLOWED_TOP = {".git", ".gitignore", "docs", "_cache", BACKUP_DIR_NAME}
GITIGNORE = "# Служебное: кэш сжатых картинок живёт только на компьютере\n_cache/\n"
NET_WORDS = ("could not resolve host", "unable to access", "timed out", "failed to connect", "empty reply",
             "connection was reset", "connection reset", "early eof", "rpc failed", "ssl")
AUTH_WORDS = ("authentication", "403", "could not read username", "permission denied", "invalid credentials",
              "terminal prompts disabled", "401")


# ----------------------------------------------------------------- git
def find_git():
    exe = GIT_PORTABLE / "cmd" / "git.exe"
    if exe.exists():
        return str(exe)
    return shutil.which("git")


def _env():
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"       # git сам вопросов не задаёт; вход — через окно браузера (GCM)
    if GIT_PORTABLE.exists():
        extra = [str(GIT_PORTABLE / p) for p in ("ucrt64/bin", "usr/bin", "cmd")]
        env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    return env


def git(*args, cwd=None, timeout=900):
    exe = find_git()
    return subprocess.run([exe, "-C", str(cwd or SERVICE), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                          timeout=timeout, env=_env())


def git_retry(*args, tries=3, **kw):
    """Сетевые команды иногда падают с «Empty reply» — пробуем ещё раз."""
    r = None
    for _ in range(tries):
        r = git(*args, **kw)
        if r.returncode == 0:
            return r
        low = (r.stdout + r.stderr).lower()
        if not any(w in low for w in NET_WORDS) or any(w in low for w in AUTH_WORDS):
            return r
        time.sleep(3)
    return r


def explain_git_error(err, log):
    low = err.lower()
    if any(w in low for w in AUTH_WORDS):
        log("Похоже, не прошёл вход в GitHub. Запусти файл ещё раз и войди в аккаунт в открывшемся окне браузера.")
    elif any(w in low for w in NET_WORDS):
        log("Похоже, нет интернета или GitHub сейчас не отвечает. Проверь соединение и запусти ещё раз.")
    elif any(w in low for w in ("rejected", "non-fast-forward", "fetch first")):
        log("На GitHub появились изменения прямо в момент публикации. Просто запусти файл ещё раз.")
    elif "repository not found" in low or "not found" in low:
        log("GitHub не нашёл репозиторий. Проверь адрес в файле _движок\\repo.txt.")
    log("\nТехнические подробности (можно прислать мне):\n" + err)


def hide_dir(path):
    try:
        import ctypes
        ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x2 | 0x10)   # скрытая папка
    except Exception:
        pass


def ensure_service_dir():
    SERVICE.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if SERVICE.name.startswith("."):
        hide_dir(SERVICE)


# ----------------------------------------------------------------- шаг 1: подготовить служебную копию
def prepare_repo(log=print):
    """Если копии нет — создаёт; затем fetch + reset --hard origin/main.
    Сайт всё равно пересобирается целиком, поэтому локальные правки в копии не нужны."""
    if not find_git():
        log("\nНе найден Git (он должен лежать в папке _движок\\git). Верни папку _движок целиком "
            "(из Google Диска или из его корзины) и запусти ещё раз.")
        return False
    url = repo_url()
    if not url:
        log("\nНе указан адрес репозитория. Впиши его в файл _движок\\repo.txt "
            "(например: https://github.com/логин/redkiss.git).")
        return False
    ensure_service_dir()
    if not (SERVICE / ".git").exists():
        log("\nНа этом компьютере ещё нет служебной копии сайта — создаю (нужен интернет).")
        r = git("init", "-b", BRANCH)
        if r.returncode != 0:
            log("Не получилось создать служебную копию:\n" + (r.stdout + r.stderr).strip())
            return False
        git("remote", "add", "origin", url)
    else:
        git("remote", "set-url", "origin", url)
    git("config", "core.autocrlf", "false")
    git("config", "core.longpaths", "true")
    git("config", "core.quotepath", "false")

    log("\nСверяюсь с GitHub…")
    r = git_retry("fetch", "origin")
    if r.returncode != 0:
        log("Не получилось связаться с GitHub — публиковать не буду.")
        explain_git_error((r.stdout + r.stderr).strip(), log)
        return False
    if git("rev-parse", "--verify", "-q", f"origin/{BRANCH}").returncode == 0:
        r = git("checkout", "-f", "-B", BRANCH, f"origin/{BRANCH}")
        if r.returncode != 0:
            log("Не получилось обновить служебную копию:\n" + (r.stdout + r.stderr).strip())
            return False
        git("branch", f"--set-upstream-to=origin/{BRANCH}", BRANCH)
    return True


# ----------------------------------------------------------------- шаг 2: резервная копия движка
def sync_backup():
    """Копия _движка (без python и git — они тяжёлые), bat-файлов и инструкции — в отдельную папку репозитория."""
    dest = SERVICE / BACKUP_DIR_NAME
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)

    def ignore(d, names):
        skip = set()
        for n in names:
            if n in ("__pycache__", "_cache") or n.endswith(".pyc"):
                skip.add(n)
            elif Path(d) == ENGINE and n in ("python", "git"):
                skip.add(n)
        return skip

    shutil.copytree(ENGINE, dest / ENGINE.name, ignore=ignore)
    for p in ROOT.iterdir():
        if p.is_file() and (p.suffix.lower() == ".bat" or p.name == "ИНСТРУКЦИЯ.txt"):
            shutil.copy2(p, dest / p.name)
    (dest / "ЧИТАЙ_МЕНЯ.txt").write_text(
        "Резервная копия движка сайта РЕДКИСС (обновляется при каждой публикации).\n"
        "Здесь НЕТ тяжёлых портативных программ _движок\\python и _движок\\git, а также фото (ТОВАРЫ) и товары.xlsx.\n"
        "Чтобы восстановить: положи эти файлы в рабочую папку, а Python (embeddable 3.12, 64-bit, python.org)\n"
        "и MinGit (github.com/git-for-windows/git/releases) — в _движок\\python и _движок\\git.\n"
        "Подробности — в ИНСТРУКЦИЯ.txt рядом.\n", encoding="utf-8")


# ----------------------------------------------------------------- шаг 3: commit + push
def publish(res, log=print):
    if not res["ok"]:
        log("\nВ сборке были ошибки (см. выше) — публиковать не буду, чтобы не выложить сломанный сайт.")
        log("Исправь и запусти ещё раз.")
        return 1

    log("\nГотовлю публикацию…")
    (SERVICE / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    try:
        sync_backup()
    except OSError as e:
        log(f"Не получилось обновить резервную копию движка ({e}) — публикую без неё.")

    # убираем из репозитория всё старое, что лежало вне docs и резервной копии
    tracked = {n.split("/")[0] for n in git("ls-files", "-z").stdout.split("\0") if n}
    legacy = sorted(tracked - ALLOWED_TOP)
    if legacy:
        git("rm", "-r", "-f", "-q", "--", *legacy)
        for n in legacy:                       # то, что осталось на диске
            p = SERVICE / n
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.exists():
                p.unlink()

    add = git("add", "-A")
    if add.returncode != 0:
        log("Не получилось подготовить файлы: " + add.stderr.strip())
        return 1
    changes = [l for l in git("status", "--porcelain").stdout.splitlines() if l.strip()]
    ahead = git("rev-list", "--count", "@{u}..HEAD")
    has_unpushed = ahead.returncode == 0 and ahead.stdout.strip() not in ("", "0")
    first_time = git("rev-parse", "--verify", "-q", "HEAD").returncode != 0
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
        ident = []
        if not git("config", "user.name").stdout.strip():
            ident += ["-c", "user.name=REDKISS"]
        if not git("config", "user.email").stdout.strip():
            ident += ["-c", "user.email=redkiss@users.noreply.github.com"]
        c = git(*ident, "commit", "-q", "-m", subject, "-m", body)
        if c.returncode != 0:
            log("Не получилось сохранить изменения:\n" + (c.stdout + c.stderr).strip())
            return 1
        log(f"Сохранено: {subject}")
        for p in parts:
            log("  " + p)

    log("Отправляю на GitHub (в первый раз на этом компьютере откроется окно браузера — войди в аккаунт GitHub)…")
    push = git_retry("push", "-u", "origin", BRANCH)
    if push.returncode != 0:
        log("\nНе получилось отправить сайт на GitHub.")
        explain_git_error((push.stdout + push.stderr).strip(), log)
        return 1

    url = res.get("site_url") or ""
    log("\n" + "=" * 60)
    log(f"Готово! Сайт обновится через 1–2 минуты: {url}" if url else
        "Готово! Сайт обновится через 1–2 минуты (ссылка вида логин.github.io/redkiss/).")
    log("=" * 60)
    return 0
