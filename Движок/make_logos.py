# -*- coding: utf-8 -*-
"""Одноразовый скрипт: делает логотипы с прозрачным фоном из ref-*.png.
Запускать нужно только если вы заменили файлы ref-*.png в папке Brand.
Результат: Brand/logo-name.png, logo-circle.png, logo-lips.png, favicon-*.png, favicon.ico
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

BRAND = Path(__file__).resolve().parent / "Brand"


def cut_white(img, max_w):
    """Убирает белый фон снаружи плашки. Края получают плавную прозрачность."""
    img = img.convert("RGB")
    arr = np.asarray(img).astype(np.float32)
    g = arr[:, :, 1]

    # "фон" = светлые пиксели (зелёный канал высокий), связанные с углами
    light = g >= 25
    labels, _ = ndimage.label(light)
    corner_labels = {labels[0, 0], labels[0, -1], labels[-1, 0], labels[-1, -1]} - {0}
    outside = np.isin(labels, list(corner_labels))

    # прозрачность пограничных пикселей: чем ближе к белому, тем прозрачнее
    rim_g = 5.0
    alpha = np.ones_like(g)
    alpha_out = np.clip((255.0 - g) / (255.0 - rim_g), 0, 1)
    alpha[outside] = alpha_out[outside]
    # слабые «хвосты» (почти белые) — полностью прозрачные
    alpha[outside & (alpha < 0.04)] = 0

    out = arr.copy()
    band = outside & (alpha > 0) & (alpha < 1)
    a3 = alpha[..., None]
    # un-premultiply относительно белого фона: убираем розовое гало
    unp = (arr - 255.0 * (1 - a3)) / np.maximum(a3, 1e-3)
    out[band] = np.clip(unp[band], 0, 255)

    rgba = np.dstack([out, alpha * 255.0]).astype(np.uint8)
    res = Image.fromarray(rgba, "RGBA")
    bbox = res.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    res = res.crop(bbox)
    if res.width > max_w:
        res = res.resize((max_w, round(res.height * max_w / res.width)), Image.LANCZOS)
    return res


def make_favicon(lips_rgba):
    """Губы из рамки на тёмном квадрате со скруглением."""
    w, h = lips_rgba.size
    # внутренняя часть рамки (отрезаем красный бордюр ~4%)
    pad = int(h * 0.06)
    inner = lips_rgba.crop((pad, pad, w - pad, h - pad))
    size = max(inner.size)
    sq = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    sq.paste(inner, ((size - inner.width) // 2, (size - inner.height) // 2), inner)
    # скругление
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=size // 6, fill=255)
    sq.putalpha(mask)
    return sq


def main():
    for name, out, max_w in [
        ("ref-Logo_Name.png", "logo-name.png", 1400),
        ("ref-Logo_Circle.png", "logo-circle.png", 1000),
        ("ref-Logo_Square.png", "logo-lips.png", 1400),
    ]:
        src = BRAND / name
        if not src.exists():
            print("Нет файла", src)
            continue
        res = cut_white(Image.open(src), max_w)
        res.save(BRAND / out, optimize=True)
        print("OK", out, res.size)

    lips = Image.open(BRAND / "logo-lips.png")
    fav = make_favicon(lips)
    for s in (32, 180, 512):
        fav.resize((s, s), Image.LANCZOS).save(BRAND / f"favicon-{s}.png", optimize=True)
    fav.resize((256, 256), Image.LANCZOS).save(
        BRAND / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    print("OK favicon")


if __name__ == "__main__":
    sys.exit(main())
