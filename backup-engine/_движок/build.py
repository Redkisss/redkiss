# -*- coding: utf-8 -*-
"""Сборщик сайта РЕДКИСС: ТОВАРЫ/ + товары.xlsx  ->  docs/ (в служебной копии вне Google Диска)"""
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image

import images
import render
from common import (BRAND, CACHE_DIR, DOCS, IMAGE_EXT, PRODUCTS, ROOT, STATIC, VIDEO_EXT, XLSX, Report,
                    fmt_price, is_hidden_name, natural_key, norm, repo_url, slugify, split_order_prefix, unique_slug)
from xlsx_io import XlsxBook

UNSUPPORTED_EXT = {".gif", ".bmp", ".tif", ".tiff", ".avi", ".mkv", ".wmv", ".jfif", ".flv", ".m4v"}
SITE_TITLE = "РЕДКИСС — авторские фигурки из смолы"


# ----------------------------------------------------------------- сканирование папок
def scan_products(rep):
    cats = []
    if not PRODUCTS.exists():
        PRODUCTS.mkdir()
        rep.warn("Папки «ТОВАРЫ» не было — я создал пустую. Положи в неё папки категорий.")
        return cats
    for entry in sorted(PRODUCTS.iterdir(), key=lambda p: natural_key(p.name)):
        if is_hidden_name(entry.name):
            continue
        if entry.is_file():
            if entry.suffix.lower() in IMAGE_EXT | VIDEO_EXT:
                rep.warn(f"Файл «{entry.name}» лежит прямо в «ТОВАРЫ». Нужна папка категории, а в ней папка товара.")
            continue
        order, name = split_order_prefix(entry.name)
        cat = {"folder": entry.name, "name": name, "order": order, "items": []}
        for sub in sorted(entry.iterdir(), key=lambda p: natural_key(p.name)):
            if is_hidden_name(sub.name):
                continue
            if sub.is_file():
                if sub.suffix.lower() in IMAGE_EXT | VIDEO_EXT:
                    rep.warn(f"Файл «{sub.name}» лежит прямо в категории «{name}». "
                             f"Создай внутри папку товара и положи файл туда.")
                continue
            it_order, it_name = split_order_prefix(sub.name)
            files, mtime = [], sub.stat().st_mtime
            for f in sorted(sub.iterdir(), key=lambda p: natural_key(p.name)):
                if is_hidden_name(f.name):
                    continue
                if f.is_dir():
                    rep.warn(f"В папке товара «{it_name}» есть вложенная папка «{f.name}» — она не читается. "
                             f"Фото и видео должны лежать прямо в папке товара.")
                    continue
                ext = f.suffix.lower()
                if ext in IMAGE_EXT | VIDEO_EXT:
                    files.append(f)
                    try:
                        mtime = max(mtime, f.stat().st_mtime)
                    except OSError:
                        pass
                elif ext in UNSUPPORTED_EXT:
                    rep.warn(f"Файл «{f.name}» (товар «{it_name}») — формат {ext} не поддерживается. "
                             f"Подойдут: jpg, png, webp, heic, mp4, mov, webm.")
            cat["items"].append({"folder": sub.name, "clean": it_name, "order": it_order,
                                 "mtime": mtime, "files": files, "path": sub})
        cats.append(cat)
    cats.sort(key=lambda c: (c["order"] is None, c["order"] or 0, norm(c["name"])))
    return cats


# ----------------------------------------------------------------- адрес сайта
def detect_site_url(settings_url):
    url = (settings_url or "").strip()
    if not url:
        out = repo_url()
        m = re.search(r"github\.com[:/]+([^/]+)/([^/]+?)(?:\.git)?/?$", out)
        if m:
            user, repo = m.group(1), m.group(2)
            url = f"https://{user.lower()}.github.io/" + ("" if repo.lower() == f"{user.lower()}.github.io" else repo + "/")
    if not url:
        return ""
    if not re.match(r"^https?://", url):
        url = "https://" + url
    return url.rstrip("/") + "/"


# ----------------------------------------------------------------- вспомогательное
class Out:
    """Запись файлов в docs/ с учётом того, что создано в этой сборке."""
    def __init__(self):
        self.produced = set()

    def write(self, rel, data):
        p = DOCS / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            data = data.encode("utf-8")
        if not p.exists() or p.read_bytes() != data:
            p.write_bytes(data)
        self.produced.add(rel)

    def copy(self, src, rel):
        self.write(rel, Path(src).read_bytes())


def digest(paths):
    h = hashlib.md5()
    for p in sorted(paths):
        h.update(Path(p).read_bytes())
    return h.hexdigest()[:8]


def flat(text, n=180):
    t = re.sub(r"\s+", " ", text).strip()
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def build_brand(out, cache, produced_media):
    """Логотипы для сайта (WebP) + иконки + картинка для превью ссылки."""
    sizes = {}
    for src, dest, w in [("logo-name.png", "brand/logo-name.webp", 700), ("logo-circle.png", "brand/logo-circle.webp", 700)]:
        s = BRAND / src
        if not s.exists():
            raise FileNotFoundError(f"Нет логотипа {s}. Запусти make_logos.py или положи файл.")
        d = DOCS / dest
        if not d.exists() or d.stat().st_mtime < s.stat().st_mtime:
            with Image.open(s) as im:
                im = im.convert("RGBA")
                im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
                d.parent.mkdir(parents=True, exist_ok=True)
                im.save(d, "WEBP", quality=90, method=4)
        with Image.open(d) as im:
            sizes[src] = im.size
        out.produced.add(dest)
    for f in ("favicon.ico", "favicon-32.png", "favicon-180.png"):
        if (BRAND / f).exists():
            out.copy(BRAND / f, f"brand/{f}")
    og = DOCS / "brand/og.jpg"
    if not og.exists() or og.stat().st_mtime < (BRAND / "logo-circle.png").stat().st_mtime:
        with Image.open(BRAND / "logo-circle.png") as im:
            im = im.convert("RGBA")
            im.thumbnail((560, 560), Image.LANCZOS)
            canvas = Image.new("RGB", (1200, 630), (10, 8, 9))
            canvas.paste(im, ((1200 - im.width) // 2, (630 - im.height) // 2), im)
            og.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(og, "JPEG", quality=88)
    out.produced.add("brand/og.jpg")
    return sizes


# ----------------------------------------------------------------- основная сборка
def build(log=print):
    rep = Report()
    started = datetime.datetime.now()
    DOCS.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out = Out()

    # прошлая сборка — чтобы сказать, что нового
    old_items, old = {}, {}
    try:
        old = json.loads((DOCS / "data.json").read_text(encoding="utf-8"))
        old_items = {i["slug"]: json.dumps(i, sort_keys=True, ensure_ascii=False) for i in old.get("items", [])}
    except Exception:
        pass

    log("Читаю папку «ТОВАРЫ»…")
    cats = scan_products(rep)

    log("Читаю товары.xlsx…")
    xl = XlsxBook(XLSX, rep)
    if xl.unreadable_locked:
        rep.error("Файл товары.xlsx сейчас занят (открыт в Excel). Закрой товары.xlsx и запусти ещё раз.")
        return {"ok": False, "report": rep, "fatal": True}
    rows = xl.rows
    row_by_key = {norm(r.folder): r for r in rows}

    # --- связываем папки и строки Excel
    folder_keys = set()
    folders_info = []
    for cat in cats:
        for it in cat["items"]:
            it["row"] = row_by_key.get(norm(it["folder"])) or row_by_key.get(norm(it["clean"]))
            folder_keys |= {norm(it["folder"]), norm(it["clean"])}
            folders_info.append((it["folder"], it["clean"], cat["name"]))
    seen_clean = {}
    for cat in cats:
        for it in cat["items"]:
            k = norm(it["clean"])
            if k in seen_clean and it["row"] is not None:
                rep.warn(f"Две папки с одинаковым названием «{it['clean']}» ({seen_clean[k]} и {cat['name']}) — "
                         f"в Excel они делят одну строку. Переименуй одну из папок.")
            seen_clean.setdefault(k, cat["name"])
    missing = [r for r in rows if norm(r.folder) not in folder_keys]
    for r in missing:
        rep.warn(f"В Excel есть товар «{r.folder}» (строка {r.num}), но папки с таким названием нет — "
                 f"строка подсвечена красным.")

    # --- адрес сайта
    cfg_url = xl.settings["site_url"]
    git_url = detect_site_url("")
    if git_url and (not cfg_url or urlparse(detect_site_url(cfg_url)).netloc.endswith("github.io")):
        site_url = git_url      # адрес github.io всегда берём из актуального подключения Git
    else:
        site_url = detect_site_url(cfg_url)   # свой домен из настроек не трогаем
    if site_url and site_url != cfg_url and (not cfg_url or urlparse(detect_site_url(cfg_url)).netloc.endswith("github.io")):
        xl.set_site_url(site_url)

    # --- запись Excel (дописать новые папки)
    new_rows = sum(1 for cat in cats for it in cat["items"] if it["row"] is None)
    xl.sync(folders_info, missing)
    saved = xl.save()
    if saved == "locked":
        rep.warn("Файл товары.xlsx открыт в Excel, поэтому я не смог дописать в него новые папки и подсветить "
                 "ошибки. Закрой товары.xlsx и запусти ещё раз.")
    elif saved and new_rows:
        log(f"В товары.xlsx дописано новых строк: {new_rows}")

    # --- картинки / видео
    cache = images.Cache()
    log("Обрабатываю фото и видео (новые и изменённые)…")
    if not images.FFMPEG:
        log("  (ffmpeg не найден — обложкой видео будет главное фото)")
    brand_sizes = build_brand(out, cache, None)

    used_slugs, cat_slugs_used = set(), set()
    items, categories = [], []
    hidden = 0
    for ci, cat in enumerate(cats):
        cslug = unique_slug(slugify(cat["name"]), cat_slugs_used)
        cat["slug"] = cslug
        for it in cat["items"]:
            row = it["row"]
            if row and row.hide:
                hidden += 1
                continue
            title = (row.title if row and row.title else it["clean"])
            if not it["files"]:
                rep.warn(f"В папке товара «{it['clean']}» ({cat['name']}) нет фото и видео — пока не показываю.")
                continue
            slug = unique_slug(slugify(it["clean"]), used_slugs)
            produced = out.produced
            stems = set()

            def stem_for(f):
                return unique_slug(slugify(f.stem), stems)

            entries = []   # в порядке файлов
            for f in it["files"]:
                ext = f.suffix.lower()
                st = stem_for(f)
                if ext in IMAGE_EXT:
                    res = images.process_image(f, slug, st, cache, rep, produced)
                    if res:
                        entries.append({"file": f, "type": "image", **res})
                else:
                    entries.append({"file": f, "type": "video", "_stem": st})
            imgs = [e for e in entries if e["type"] == "image"]
            cover_entry = None
            for e in imgs:
                if "главная" in e["file"].stem.casefold():
                    cover_entry = e
                    break
            if cover_entry is None and imgs:
                cover_entry = imgs[0]
            fallback_poster = {k: cover_entry[k] for k in ("thumb", "card", "large")} if cover_entry else None
            final = []
            for e in entries:
                if e["type"] == "video":
                    f = e["file"]
                    rel = images.copy_video(f, slug, f"{e['_stem']}{f.suffix.lower()}", cache, rep, produced)
                    if not rel:
                        continue
                    poster = images.video_poster(f, slug, e["_stem"], cache, rep, produced) or fallback_poster
                    if not poster:
                        rep.warn(f"Товар «{title}»: есть только видео, а для кадра нужен ffmpeg или хотя бы одно фото — "
                                 f"добавь фото.")
                        continue
                    final.append({"type": "video", "src": rel, "poster": poster, "_file": e["file"]})
                else:
                    final.append({"type": "image", **{k: e[k] for k in ("thumb", "card", "large")}, "_file": e["file"]})
            if not final:
                rep.warn(f"Товар «{title}»: не удалось обработать ни одного файла — пропущен.")
                continue
            if cover_entry:
                ci_idx = next(i for i, m in enumerate(final) if m["type"] == "image" and m["_file"] == cover_entry["file"])
                final.insert(0, final.pop(ci_idx))
            cover = (final[0] if final[0]["type"] == "image" else {"thumb": final[0]["poster"]["thumb"],
                                                                    "card": final[0]["poster"]["card"],
                                                                    "large": final[0]["poster"]["large"]})
            cover = {k: cover[k] for k in ("thumb", "card", "large")}
            second = next((m for m in final[1:] if m["type"] == "image"), None)
            second = {k: second[k] for k in ("thumb", "card", "large")} if second else None
            og = images.make_og(cover["large"]["src"], slug, cache, produced,
                                images.Cache.sig(final[0]["_file"]))
            for m in final:
                m.pop("_file", None)
            order = row.order if (row and row.order is not None) else it["order"]
            items.append({
                "slug": slug, "title": title, "category": cslug, "categoryName": cat["name"],
                "description": row.desc if row else "", "size": row.size if row else "",
                "material": row.material if row else "", "status": row.status if row else "",
                "price": fmt_price(row.price) if row and row.price is not None else "",
                "isNew": bool(row and row.is_new), "hasVideo": any(m["type"] == "video" for m in final),
                "cover": cover, "cover2": second, "media": final, "og": og,
                "_order": order, "_mtime": it["mtime"], "_cat": ci,
            })
        categories.append({"slug": cslug, "name": cat["name"], "_count": 0})
    cache.save()

    # защита: если товаров вдруг 0, а раньше были — не стираем сайт
    if not items and old_items:
        rep.error(f"Не нашёл ни одного товара, а на сайте их было {len(old_items)}. Похоже, папка «ТОВАРЫ» пуста, "
                  f"переименована или не там лежит. Сайт НЕ тронут. Верни папки на место и запусти ещё раз.")
        return {"ok": False, "report": rep, "fatal": True}

    # --- порядок
    def sort_key(i):
        if i["_order"] is not None:
            return (0, i["_order"], i["_cat"], norm(i["title"]))
        return (1, -i["_mtime"], i["_cat"], norm(i["title"]))
    items.sort(key=sort_key)
    for i in items:
        for c in categories:
            if c["slug"] == i["category"]:
                c["_count"] += 1
    for i in items:
        for k in ("_order", "_mtime", "_cat"):
            i.pop(k)
    categories = [{"slug": c["slug"], "name": c["name"], "count": c["_count"]} for c in categories if c["_count"] > 0]
    cat_name = {c["slug"]: c["name"] for c in categories}

    # --- данные для сайта
    settings = xl.settings
    desc_site = settings["description"] or "Авторские фигурки из смолы ручной работы."
    socials = [{"name": s["name"], "url": s["url"], "icon": render.icon_for(s["name"], s["url"])}
               for s in settings["socials"]]
    data = {"generated": started.isoformat(timespec="seconds"),
            "site": {"title": "РЕДКИСС", "description": desc_site, "url": site_url,
                     "contact": settings["contact"], "socials": socials},
            "categories": categories, "items": items}
    # время сборки меняем, только если реально изменилось содержимое (иначе каждая публикация «что-то меняла»)
    if old.get("generated") and {k: v for k, v in old.items() if k != "generated"} ==             json.loads(json.dumps({k: v for k, v in data.items() if k != "generated"})):
        data["generated"] = old["generated"]
    out.write("data.json", json.dumps(data, ensure_ascii=False, indent=1))
    data_js = "window.REDKISS_DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";"
    out.write("data.js", data_js)

    # --- статика (css/js)
    static_files = [p for p in STATIC.rglob("*") if p.is_file()]
    for p in static_files:
        out.copy(p, "assets/" + p.relative_to(STATIC).as_posix())
    v_css = digest([p for p in static_files if p.suffix == ".css"])
    v_js = digest([p for p in static_files if p.suffix == ".js"])
    v_data = hashlib.md5(data_js.encode("utf-8")).hexdigest()[:8]

    def abs_url(rel):
        return (site_url + rel) if site_url else rel

    logo_w, logo_h = brand_sizes["logo-name.png"]
    cw, ch = brand_sizes["logo-circle.png"]
    common = {"v_css": v_css, "v_js": v_js, "v_data": v_data, "robots": ""}

    # --- заставка
    out.write("index.html", render.fill("splash.html", {
        **common, "description": render.esc(desc_site), "logo_w": cw, "logo_h": ch,
        "og": render.og_tags(SITE_TITLE, desc_site, abs_url("brand/og.jpg") if site_url else "brand/og.jpg", site_url)}))

    def page(depth_base, **kw):
        base = depth_base
        return render.fill("layout.html", {
            **common, "base": base, "head_pre": "", "header": render.header_html(base, settings, (logo_w, logo_h)),
            "footer": render.footer_html(), **kw})

    # --- каталог
    out.write("catalog/index.html", page(
        "../", title=SITE_TITLE, description=render.esc(desc_site), body_class="page-catalog", page="catalog",
        cats=render.cats_html("../", categories, "all"), content=render.fill("catalog_content.html", {}),
        og=render.og_tags(SITE_TITLE, desc_site, abs_url("brand/og.jpg") if site_url else "../brand/og.jpg",
                          site_url + "catalog/" if site_url else "")))

    # --- страницы товаров
    for it in items:
        base = "../../"
        d = flat(it["description"]) if it["description"] else desc_site
        title = f"{it['title']} — РЕДКИСС"
        og_img = abs_url(it["og"]) if site_url else base + it["og"]
        out.write(f"item/{it['slug']}/index.html", page(
            base, title=render.esc(title), description=render.esc(d), body_class="page-item", page="item",
            cats=render.cats_html(base, categories, it["category"]),
            content=render.item_content(base, it, settings, it["categoryName"]),
            og=render.og_tags(title, d, og_img, site_url + f"item/{it['slug']}/" if site_url else "")))

    # --- 404
    site_path = urlparse(site_url).path if site_url else "/"
    head_pre = ('<script>(function(){var r="' + site_path + '",p=location.pathname,'
                'b=p.indexOf(r)===0?r:"/";document.write(\'<base href="\'+b+\'">\');})();</script>')
    out.write("404.html", page(
        "", title="Страница не найдена — РЕДКИСС", description="Такой страницы нет.", body_class="page-404",
        page="notfound", head_pre=head_pre, cats=render.cats_html("", categories, ""),
        content=render.fill("notfound_content.html", {}),
        og=render.og_tags("Страница не найдена — РЕДКИСС", "Такой страницы нет.", "", "")).replace(
        '<meta name="theme-color"', '<meta name="robots" content="noindex">\n<meta name="theme-color"', 1))

    # --- sitemap / robots / служебные файлы
    robots = "User-agent: *\nAllow: /\n"
    if site_url:
        urls = [site_url, site_url + "catalog/"] + [site_url + f"item/{i['slug']}/" for i in items]
        today = started.date().isoformat()
        sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        sm += "".join(f"<url><loc>{render.esc(u)}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
        sm += "</urlset>\n"
        out.write("sitemap.xml", sm)
        robots += f"Sitemap: {site_url}sitemap.xml\n"
    out.write("robots.txt", robots)
    out.write(".nojekyll", "")
    # свой домен: если в настройках не github.io — нужен файл CNAME
    host = urlparse(site_url).netloc if site_url else ""
    cname = DOCS / "CNAME"
    if host and not host.endswith("github.io"):
        out.write("CNAME", host + "\n")
    elif cname.exists():
        out.produced.add("CNAME")  # его создал сам GitHub — не трогаем

    # --- уборка лишнего в docs/
    for p in sorted(DOCS.rglob("*"), reverse=True):
        rel = p.relative_to(DOCS).as_posix()
        if p.is_file() and rel not in out.produced:
            try:
                p.unlink()
            except OSError:
                pass
        elif p.is_dir():
            try:
                p.rmdir()
            except OSError:
                pass

    # --- итоги
    total_mb = sum(p.stat().st_size for p in DOCS.rglob("*") if p.is_file()) / 1024 / 1024
    if total_mb > 700:
        rep.warn(f"Сайт уже весит {total_mb:.0f} МБ, а у GitHub Pages лимит 1 ГБ. Скоро придётся чистить видео.")
    new_slugs = [i for i in items if i["slug"] not in old_items]
    removed = [s for s in old_items if s not in {i["slug"] for i in items}]
    changed = [i for i in items if i["slug"] in old_items
               and json.dumps(i, sort_keys=True, ensure_ascii=False) != old_items[i["slug"]]]
    no_desc = [i["title"] for i in items if not i["description"]]
    summary = {"new": [i["title"] for i in new_slugs], "removed": removed,
               "changed": [i["title"] for i in changed], "site_url": site_url}
    (CACHE_DIR / "last_build.json").write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    return {"ok": not rep.errors, "report": rep, "categories": len(categories), "items": len(items),
            "new": [i["title"] for i in new_slugs], "removed": removed, "changed": [i["title"] for i in changed],
            "no_desc": no_desc, "hidden": hidden, "site_url": site_url, "seconds": (datetime.datetime.now() - started).total_seconds(),
            "total_mb": total_mb}


def print_report(res, log=print):
    rep = res["report"]
    log("")
    log("=" * 60)
    if res.get("fatal"):
        for e in rep.errors:
            log("ОШИБКА: " + e)
        log("=" * 60)
        return
    line = f"Категорий: {res['categories']}, товаров: {res['items']}, новых: {len(res['new'])}."
    if res["new"]:
        line += " Новые: " + ", ".join(res["new"]) + "."
    log(line)
    if res["hidden"]:
        log(f"Скрыто через Excel: {res['hidden']}.")
    if res["no_desc"]:
        log("Без описания: " + ", ".join(res["no_desc"]) + ".")
    if res["removed"]:
        log("Убраны с сайта: " + ", ".join(res["removed"]) + ".")
    for w in rep.warnings:
        log("  ! " + w)
    for e in rep.errors:
        log("  ОШИБКА: " + e)
    if not rep.errors:
        log("Ошибок нет." + ("" if not rep.warnings else f" Предупреждений: {len(rep.warnings)}."))
    log(f"Готово за {res['seconds']:.1f} с. Размер сайта: {res['total_mb']:.0f} МБ.")
    log("=" * 60)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    r = build()
    print_report(r)
    sys.exit(0 if r["ok"] else 1)
