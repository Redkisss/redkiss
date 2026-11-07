# -*- coding: utf-8 -*-
"""Обработка картинок и видео + кэш (чтобы не пересчитывать то, что не менялось)."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageOps

from common import CACHE_DIR, DOCS, ROOT, VIDEO_MAX_MB, VIDEO_WARN_MB

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_OK = True
except Exception:  # библиотеки нет — HEIC пропустим с предупреждением
    HEIC_OK = False

PIPELINE_VERSION = "3"
SIZES = {"thumb": (200, 78), "card": (700, 82), "large": (1800, 85)}
FFMPEG = shutil.which("ffmpeg")


def src_key(path):
    """Ключ кэша: путь относительно рабочей папки (буква диска на разных ПК разная)."""
    try:
        return Path(path).relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _file_hash(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Cache:
    """Кэш лежит в служебной копии (не на Google Диске). Запись считается годной,
    только если исходник не менялся И готовые файлы в docs/ на месте и не изменились
    (git reset мог откатить их к старой версии)."""

    def __init__(self):
        self.path = CACHE_DIR / "manifest.json"
        self.data = {}
        self.existed = self.path.exists()
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self.data = {}
        self.new = {}

    @staticmethod
    def sig(path):
        st = path.stat()
        return f"{st.st_mtime_ns}:{st.st_size}:{PIPELINE_VERSION}"

    def get(self, key, sig):
        e = self.data.get(key)
        if not e or e.get("sig") != sig:
            return None
        hashes = e.get("hashes") or {}
        for f in e.get("files", []):
            p = DOCS / f
            try:
                if not p.exists() or hashes.get(f) != _file_hash(p):
                    return None
            except OSError:
                return None
        self.new[key] = e
        return e["out"]

    def put(self, key, sig, out, files):
        hashes = {}
        for f in files:
            try:
                hashes[f] = _file_hash(DOCS / f)
            except OSError:
                pass
        self.new[key] = {"sig": sig, "out": out, "files": list(files), "hashes": hashes}

    def save(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.new, ensure_ascii=False), encoding="utf-8")


def _save_webp(im, path, quality):
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "WEBP", quality=quality, method=4)


def _prepare(im):
    im = ImageOps.exif_transpose(im)
    if im.mode in ("P", "LA", "PA"):
        im = im.convert("RGBA")
    elif im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
    return im


def process_image(src, item_slug, stem, cache, rep, produced, cache_key=None):
    """Возвращает {'thumb': {src,w,h}, 'card': ..., 'large': ...} или None."""
    key = cache_key or f"img:{src_key(src)}"
    try:
        sig = Cache.sig(src)
    except OSError as e:
        rep.error(f"Не могу прочитать файл {src.name}: {e}")
        return None
    out = cache.get(key, sig)
    if out is None:
        try:
            with Image.open(src) as im0:
                im0.load()
                base = _prepare(im0)
        except Exception as e:
            ext = src.suffix.lower()
            if ext in (".heic", ".heif") and not HEIC_OK:
                rep.warn(f"Фото «{src.name}» (HEIC) не обработано: не установлена библиотека pillow-heif. "
                         f"Сохрани фото как JPG.")
            else:
                rep.warn(f"Не получилось открыть картинку «{src.name}» — пропущена ({type(e).__name__}). "
                         f"Возможно, файл повреждён.")
            return None
        out, files = {}, []
        for name, (width, q) in SIZES.items():
            if name == "large":
                im = base.copy()
                im.thumbnail((width, width), Image.LANCZOS)
            elif base.width > width:
                im = base.resize((width, round(base.height * width / base.width)), Image.LANCZOS)
            else:
                im = base
            rel = f"media/{item_slug}/{stem}-{name}.webp"
            _save_webp(im, DOCS / rel, q)
            out[name] = {"src": rel, "w": im.width, "h": im.height}
            files.append(rel)
        cache.put(key, sig, out, files)
    for v in out.values():
        produced.add(v["src"])
    return out


def make_og(main_large_rel, item_slug, cache, produced, src_sig, folder_name="media"):
    """1200x630 JPEG для превью в Telegram/VK (WebP они не любят)."""
    rel = f"{folder_name}/{item_slug}/og.jpg"
    key = f"og:{item_slug}"
    if cache.get(key, src_sig) is None:
        with Image.open(DOCS / main_large_rel) as im:
            im = im.convert("RGB")
            canvas = Image.new("RGB", (1200, 630), (10, 8, 9))
            h = 630
            w = round(im.width * h / im.height)
            if w > 1200:
                w, h = 1200, round(im.height * 1200 / im.width)
            im = im.resize((w, h), Image.LANCZOS)
            canvas.paste(im, ((1200 - w) // 2, (630 - h) // 2))
            (DOCS / rel).parent.mkdir(parents=True, exist_ok=True)
            canvas.save(DOCS / rel, "JPEG", quality=85)
        cache.put(key, src_sig, rel, [rel])
    produced.add(rel)
    return rel


def video_poster(src, item_slug, stem, cache, rep, produced):
    """Кадр из видео (нужен ffmpeg). None, если не вышло."""
    if not FFMPEG:
        return None
    key = f"poster:{src_key(src)}"
    try:
        sig = Cache.sig(src)
    except OSError:
        return None
    out = cache.get(key, sig)
    if out is None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_DIR / "_poster.jpg"
        ok = False
        for ss in ("0.5", "0"):
            try:
                tmp.unlink(missing_ok=True)
                subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", ss, "-i", str(src),
                                "-frames:v", "1", str(tmp)], timeout=120, check=True,
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                ok = tmp.exists() and tmp.stat().st_size > 0
            except Exception:
                ok = False
            if ok:
                break
        if not ok:
            rep.warn(f"Не получилось взять кадр из видео «{src.name}» — для обложки возьму главное фото.")
            return None
        # прогоняем кадр через обычную обработку
        res = process_image(tmp, item_slug, stem + "-poster", _NullCache(), rep, produced)
        tmp.unlink(missing_ok=True)
        if not res:
            return None
        files = [v["src"] for v in res.values()]
        cache.put(key, sig, res, files)
        out = res
    for v in out.values():
        produced.add(v["src"])
    return out


class _NullCache:
    def get(self, *a, **k):
        return None

    def put(self, *a, **k):
        pass


def copy_video(src, item_slug, filename, cache, rep, produced):
    """Копирует видео как есть. Возвращает путь относительно docs или None."""
    size_mb = src.stat().st_size / 1024 / 1024
    if size_mb > VIDEO_MAX_MB:
        rep.warn(f"Видео «{src.name}» весит {size_mb:.0f} МБ — GitHub не принимает файлы больше 100 МБ. "
                 f"Видео НЕ добавлено. Сожми его (например, через HandBrake) и положи заново.")
        return None
    if size_mb > VIDEO_WARN_MB:
        rep.warn(f"Видео «{src.name}» слишком тяжёлое ({size_mb:.0f} МБ) — сожми его, "
                 f"иначе сайт будет медленно открываться.")
    rel = f"media/{item_slug}/{filename}"
    dest = DOCS / rel
    key = f"video:{src_key(src)}"
    sig = Cache.sig(src)
    if cache.get(key, sig) is None or not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        cache.put(key, sig, rel, [rel])
    produced.add(rel)
    return rel
