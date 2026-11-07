# -*- coding: utf-8 -*-
"""Общие мелочи: пути, транслит, отчёт об ошибках."""
import os
import re
import unicodedata
from pathlib import Path

ENGINE = Path(__file__).resolve().parent     # _движок/ (лежит на Google Диске)
ROOT = ENGINE.parent                          # рабочая папка на Google Диске
PRODUCTS = ROOT / "ТОВАРЫ"
XLSX = ROOT / "товары.xlsx"

# Служебная копия репозитория — ВНЕ Google Диска, у каждого ПК своя.
# Тут собирается сайт (docs/), лежит кэш картинок и делается git commit/push.
SERVICE = Path(os.environ.get("REDKISS_SERVICE") or (Path.home() / ".redkiss-publish"))
DOCS = SERVICE / "docs"
CACHE_DIR = SERVICE / "_cache"
BACKUP_DIR_NAME = "backup-engine"             # куда в репозиторий кладётся копия движка

BRAND = ENGINE / "Brand"
STATIC = ENGINE / "static"
TEMPLATES = ENGINE / "templates"
PY_PORTABLE = ENGINE / "python"
GIT_PORTABLE = ENGINE / "git"
ERROR_LOG = ROOT / "ОШИБКА.txt"


def repo_url():
    """Адрес репозитория на GitHub — в файле _движок/repo.txt."""
    try:
        for line in (ENGINE / "repo.txt").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
    except OSError:
        pass
    return ""


IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
VIDEO_EXT = {".mp4", ".mov", ".webm"}
VIDEO_WARN_MB = 40
VIDEO_MAX_MB = 95  # у GitHub жёсткий лимит 100 МБ на файл

_TR = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}


def slugify(text):
    """'Лесная дева' -> 'lesnaya-deva'. Только латиница, цифры и дефисы."""
    out = []
    for ch in str(text).lower():
        if ch in _TR:
            out.append(_TR[ch])
        else:
            n = unicodedata.normalize("NFKD", ch)
            out.append("".join(c for c in n if ord(c) < 128))
    s = re.sub(r"[^a-z0-9]+", "-", "".join(out)).strip("-")
    return s or "item"


def unique_slug(base, used):
    s, n = base, 2
    while s in used:
        s = f"{base}-{n}"
        n += 1
    used.add(s)
    return s


def norm(text):
    """Для сравнения имён: без регистра, без лишних пробелов, ё = е."""
    return re.sub(r"\s+", " ", str(text or "").replace(" ", " ")).strip().casefold().replace("ё", "е")


def natural_key(text):
    return [int(t) if t.isdigit() else t.casefold() for t in re.split(r"(\d+)", str(text))]


_PREFIX = re.compile(r"^\s*(\d+)[\s._)\-]+(\S.*)$")


def split_order_prefix(name):
    """'2 Бюсты' -> (2, 'Бюсты'); 'Бюсты' -> (None, 'Бюсты')."""
    m = _PREFIX.match(name)
    if m:
        return int(m.group(1)), m.group(2).strip()
    return None, name.strip()


def is_hidden_name(name):
    return name.startswith("_") or name.startswith(".") or name.startswith("~$")


def fmt_price(v):
    """5000 -> '5 000 ₽', '5000' -> '5 000 ₽', '5000 руб' -> '5000 руб'."""
    if v is None or v == "":
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, (int, float)):
        return f"{v:,}".replace(",", " ") + " ₽"
    s = str(v).strip()
    if re.fullmatch(r"\d+([.,]\d+)?", s):
        n = float(s.replace(",", "."))
        if n.is_integer():
            return f"{int(n):,}".replace(",", " ") + " ₽"
    return s


class Report:
    def __init__(self):
        self.warnings = []
        self.errors = []

    def warn(self, msg):
        self.warnings.append(msg)

    def error(self, msg):
        self.errors.append(msg)
