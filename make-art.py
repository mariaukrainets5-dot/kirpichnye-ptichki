#!/usr/bin/env python3
"""Turns the Higgsfield originals in art-src/ into game images in art/:
cut-outs on transparency (green screen removed) and resized story pictures."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

root = Path(__file__).parent
src, out = root / "art-src", root / "art"
out.mkdir(exist_ok=True)


def cutout(name, size=640):
    rgb = np.asarray(Image.open(src / f"{name}.png").convert("RGB")).astype(float)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    spill = g - np.maximum(r, b)
    alpha = 1 - np.clip((spill - 25) / 80, 0, 1)
    rgb[..., 1] = np.where(spill > 0, np.maximum(r, b), g)  # removes the green fringe on fur
    a = Image.fromarray((alpha * 255).astype("uint8")).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1))
    img = Image.fromarray(rgb.astype("uint8")).convert("RGBA")
    img.putalpha(a)
    img = img.crop(a.point(lambda v: 255 if v > 40 else 0).getbbox())
    img.thumbnail((size, size), Image.LANCZOS)
    img.save(out / f"{name}.webp", quality=86, method=6)
    return img.size


for name in ("zayka", "medved", "slon", "zhiraf", "lisa", "hero"):
    print(name, cutout(name))
for name in ("flock", "barmaley", "kot", "hero-lego", "village", "bird"):
    img = Image.open(src / f"{name}.png").convert("RGB")
    img.thumbnail((1280, 1280), Image.LANCZOS)
    img.save(out / f"{name}.webp", quality=80, method=6)

for size in (180, 512):
    icon = Image.new("RGBA", (size, size), (255, 201, 40, 255))
    pic = Image.open(out / "zayka.webp").convert("RGBA")
    pic.thumbnail((int(size * .84), int(size * .84)), Image.LANCZOS)
    icon.alpha_composite(pic, ((size - pic.width) // 2, (size - pic.height) // 2))
    icon.convert("RGB").save(root / "docs" / f"icon-{size}.png")
