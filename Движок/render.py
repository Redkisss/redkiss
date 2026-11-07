# -*- coding: utf-8 -*-
"""Генерация HTML-страниц из шаблонов."""
import html
import re
from urllib.parse import quote

from common import TEMPLATES, norm

ICONS = {
    "telegram": '<path d="M21.5 3.5 2.8 10.7c-.8.3-.8 1.4 0 1.7l4.6 1.5 1.8 5.6c.2.7 1.1.9 1.6.4l2.5-2.4 4.7 3.5c.6.4 1.4.1 1.6-.6L22.9 4.7c.2-.8-.6-1.5-1.4-1.2z"/><path d="m7.4 14 10.2-6.5-7.4 8.2-.4 3.9"/>',
    "vk": '<rect x="2.5" y="2.5" width="19" height="19" rx="5"/><path d="M6 8.5l2.3 7 2-5.2M12.5 8.5v7M17.5 8.5l-4 3.7 4 3.3"/>',
    "instagram": '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.2" cy="6.8" r=".6"/>',
    "pinterest": '<circle cx="12" cy="12" r="9.5"/><path d="M10.6 20.5 12 13.2M9 14.2c-1.5-3 .2-6.7 3.5-6.7 2.1 0 3.5 1.4 3.5 3.3 0 2.6-1.5 4.4-3.3 4.4-1 0-1.6-.7-1.4-1.6"/>',
    "tiktok": '<path d="M14 3.5v11a3.6 3.6 0 1 1-3.6-3.6"/><path d="M14 3.5c.3 2.4 1.9 4 4.6 4.2"/>',
    "youtube": '<rect x="2.5" y="5.5" width="19" height="13" rx="4"/><path d="M10 9.5v5l4.5-2.5z"/>',
    "whatsapp": '<path d="M3.5 20.5l1.3-4.3A8.5 8.5 0 1 1 8.2 19.3z"/><path d="M9 8.5c0 3.6 3 6.5 6.5 6.5l1-1.5-2-1-1 .8c-1-.4-2-1.4-2.4-2.4l.8-1-1-2z"/>',
    "avito": '<circle cx="7.5" cy="7.5" r="3"/><circle cx="16.5" cy="7.5" r="3"/><circle cx="7.5" cy="16.5" r="3"/><circle cx="16.5" cy="16.5" r="3"/>',
    "ozon": '<circle cx="12" cy="12" r="9.5"/><circle cx="12" cy="12" r="3.6"/>',
    "wb": '<rect x="2.5" y="2.5" width="19" height="19" rx="5"/><path d="M5.5 9l1.7 6 1.6-4 1.6 4 1.7-6M15 9v6h1.8a1.7 1.7 0 0 0 0-3.1A1.5 1.5 0 0 0 16.8 9z"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
}
ALIASES = {
    "telegram": ["telegram", "телеграм", "телега", "tg", "тг", "t.me"],
    "vk": ["vk", "вк", "вконтакте", "vkontakte"],
    "instagram": ["instagram", "инстаграм", "инста", "inst"],
    "pinterest": ["pinterest", "пинтерест"],
    "tiktok": ["tiktok", "тикток", "тик-ток", "tik tok"],
    "youtube": ["youtube", "ютуб", "ютьюб"],
    "whatsapp": ["whatsapp", "ватсап", "вотсап", "whats app", "вацап"],
    "avito": ["avito", "авито"],
    "ozon": ["ozon", "озон"],
    "wb": ["wb", "wildberries", "вайлдберриз", "вайлдберрис", "вб"],
}


def icon_for(name, url=""):
    n = norm(name)
    for key, words in ALIASES.items():
        if any(n == w or n.startswith(w) or (len(w) > 3 and w in n) for w in words):
            return key
    host = norm(url)
    for key, words in ALIASES.items():
        if key in host or any(w in host for w in words if len(w) > 3 and w.isascii()):
            return key
    return "link"


def svg_icon(key):
    return (f'<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" '
            f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[key]}</svg>')


def esc(s):
    return html.escape(str(s), quote=True)


def fill(tpl_name, ctx):
    tpl = (TEMPLATES / tpl_name).read_text(encoding="utf-8")

    def sub(m):
        k = m.group(1)
        if k not in ctx:
            raise KeyError(f"В шаблоне {tpl_name} используется {{{{{k}}}}}, но значения нет")
        return str(ctx[k])
    return re.sub(r"\{\{(\w+)\}\}", sub, tpl)


def contact_link(contact, item_title=None):
    """Для Telegram дописываем готовый текст сообщения о конкретном товаре."""
    if not contact:
        return ""
    if item_title and re.match(r"^https?://(t\.me|telegram\.me)/", contact) and "?" not in contact:
        return contact + "?text=" + quote(f"Здравствуйте! Интересует «{item_title}»")
    return contact


def header_html(base, settings, logo_size):
    socials = ""
    for s in settings["socials"]:
        key = icon_for(s["name"], s["url"])
        socials += (f'<a class="social" href="{esc(s["url"])}" target="_blank" rel="noopener" '
                    f'aria-label="{esc(s["name"])}" title="{esc(s["name"])}">{svg_icon(key)}</a>')
    contact = settings["contact"]
    cta = ""
    cta_mobile = ""
    if contact:
        cta = (f'<a class="btn btn-small" href="{esc(contact)}" target="_blank" rel="noopener">Написать</a>')
        cta_mobile = (f'<a class="btn btn-small cta-mobile" href="{esc(contact)}" target="_blank" '
                      f'rel="noopener">Написать</a>')
    w, h = logo_size
    return f'''<header class="site-header" id="siteHeader">
<div class="header-inner">
<nav class="socials" aria-label="Соцсети">{socials}{cta_mobile}</nav>
<a class="brand" href="{base}catalog/" aria-label="РЕДКИСС — все товары"><img src="{base}brand/logo-name.webp" alt="РЕДКИСС" width="{w}" height="{h}"></a>
<div class="header-cta">{cta}</div>
</div>
</header>'''


def cats_html(base, categories, active="all"):
    li = (f'<li><a href="{base}catalog/" data-cat="all"'
          f'{" class=is-active aria-current=page" if active == "all" else ""}>Все</a></li>')
    for c in categories:
        cur = c["slug"] == active
        li += (f'<li><a href="{base}catalog/?cat={esc(c["slug"])}" data-cat="{esc(c["slug"])}"'
               f'{" class=is-active aria-current=page" if cur else ""}>{esc(c["name"])}</a></li>')
    return f'<nav class="cats" aria-label="Категории"><ul>{li}</ul></nav>'


def footer_html():
    return '<footer class="site-footer"><span class="star">✦</span><p>РЕДКИСС · фигурки ручной работы</p></footer>'


def og_tags(title, desc, image_url, page_url):
    t = f'''<meta property="og:type" content="website">
<meta property="og:site_name" content="РЕДКИСС">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:locale" content="ru_RU">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">'''
    if image_url:
        t += (f'\n<meta property="og:image" content="{esc(image_url)}">'
              f'\n<meta property="og:image:width" content="1200">'
              f'\n<meta property="og:image:height" content="630">'
              f'\n<meta name="twitter:image" content="{esc(image_url)}">')
    if page_url:
        t += f'\n<meta property="og:url" content="{esc(page_url)}">'
        t += f'\n<link rel="canonical" href="{esc(page_url)}">'
    return t


def text_to_html(text):
    """Переносы строк из Excel: пустая строка = новый абзац, одиночный перенос = <br>."""
    paras = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return "".join("<p>" + esc(p.strip()).replace("\n", "<br>") + "</p>" for p in paras)


def back_phrase(cat_name):
    """'Бюсты' -> 'назад к бюстам'. Если склонить нельзя — 'назад: Название'."""
    n = cat_name.strip()
    low = n.lower()
    if " " not in n and re.fullmatch(r"[а-яё\-]+", low):
        if low.endswith(("ы", "и")):
            return "назад к " + low[:-1] + "ам"
        if low.endswith("я"):
            return "назад к " + low + "м"
    return "назад: " + n


def item_content(base, item, settings, cat_name):
    thumbs = ""
    for i, m in enumerate(item["media"]):
        src = m["thumb"]["src"] if m["type"] == "image" else (m["poster"]["thumb"]["src"] if m.get("poster") else "")
        play = '<span class="thumb-play" aria-hidden="true">▶</span>' if m["type"] == "video" else ""
        thumbs += (f'<button class="thumb{" is-active" if i == 0 else ""}" type="button" data-index="{i}" '
                   f'aria-label="Показать {"видео" if m["type"] == "video" else "фото"} {i + 1}">'
                   f'<img src="{base}{esc(src)}" alt="" loading="lazy" width="{m["thumb"]["w"] if m["type"] == "image" else m["poster"]["thumb"]["w"]}" '
                   f'height="{m["thumb"]["h"] if m["type"] == "image" else m["poster"]["thumb"]["h"]}">{play}</button>')
    first = item["media"][0]
    if first["type"] == "image":
        stage = (f'<img src="{base}{esc(first["large"]["src"])}" alt="{esc(item["title"])}" '
                 f'width="{first["large"]["w"]}" height="{first["large"]["h"]}">')
    else:
        stage = f'<img src="{base}{esc(first["poster"]["large"]["src"])}" alt="{esc(item["title"])}">'
    multi = len(item["media"]) > 1
    rows = ""
    for label, val in (("Размер", item["size"]), ("Материал", item["material"]),
                       ("Статус", item["status"]), ("Цена", item["price"])):
        if val:
            rows += f"<div><dt>{label}</dt><dd>{esc(val)}</dd></div>"
    desc = f'<div class="item-desc">{text_to_html(item["description"])}</div>' if item["description"] else ""
    contact = settings["contact"]
    cta = ""
    if contact:
        cta = (f'<a class="btn btn-solid" href="{esc(contact_link(contact, item["title"]))}" target="_blank" '
               f'rel="noopener" id="contactBtn">Написать мне</a>')
    back = (f'<a class="back" href="{base}catalog/?cat={esc(item["category"])}">← {esc(back_phrase(cat_name))}</a>')
    return f'''<main id="main" class="wrap item-page" data-slug="{esc(item["slug"])}">
<div class="item-layout{"" if multi else " single"}">
<div class="thumbs" id="thumbs" aria-label="Фото и видео"{"" if multi else " hidden"}>{thumbs}</div>
<div class="stage" id="stage">
<div class="stage-media" id="stageMedia">{stage}</div>
<button class="stage-nav prev" type="button" id="prevBtn" aria-label="Предыдущее"{"" if multi else " hidden"}>‹</button>
<button class="stage-nav next" type="button" id="nextBtn" aria-label="Следующее"{"" if multi else " hidden"}>›</button>
<div class="stage-count" id="stageCount"{"" if multi else " hidden"}>1 / {len(item["media"])}</div>
</div>
<aside class="info">
<h1 class="item-title">{esc(item["title"])}</h1>
<p class="item-cat">{esc(cat_name)}</p>
<hr class="red-line">
{desc}
<dl class="item-props">{rows}</dl>
{cta}
{back}
</aside>
</div>
<section class="related" id="related" hidden>
<h2><span class="star">✦</span> Ещё из этой категории</h2>
<div class="grid" id="relatedGrid"></div>
</section>
</main>'''
