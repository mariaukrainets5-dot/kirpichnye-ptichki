#!/usr/bin/env python3
"""Turns the Higgsfield originals in art-src/ into game images in art/:
cut-outs on transparency, animation sheets from the clips in art-src/video/ and resized story pictures."""
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

root = Path(__file__).parent
src, out = root / "art-src", root / "art"
out.mkdir(exist_ok=True)


def key(rgb):
    """Removes the green screen: returns RGBA with the green fringe cleaned off fur."""
    rgb = rgb.astype(float)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    spill = g - np.maximum(r, b)
    alpha = 1 - np.clip((spill - 25) / 80, 0, 1)
    rgb[..., 1] = np.where(spill > 0, np.maximum(r, b), g)
    a = Image.fromarray((alpha * 255).astype("uint8")).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1))
    img = Image.fromarray(rgb.astype("uint8")).convert("RGBA")
    img.putalpha(a)
    return img, a


def cutout(name, size=640):
    img, a = key(np.asarray(Image.open(src / f"{name}.png").convert("RGB")))
    img = img.crop(a.point(lambda v: 255 if v > 40 else 0).getbbox())
    img.thumbnail((size, size), Image.LANCZOS)
    img.save(out / f"{name}.webp", quality=86, method=6)


GRID, CELL = 6, 256
FF = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"


def sheet(name):
    """Turns a clip into a 6x6 sheet of cut-out frames for the game."""
    clip = src / "video" / f"{name}.mp4"
    info = subprocess.run([FF[:-6] + "ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(clip)], capture_output=True, text=True).stdout.strip().split(",")
    w, h = int(info[0]), int(info[1])
    raw = subprocess.run([FF, "-v", "error", "-i", str(clip), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    frames = np.frombuffer(raw, "uint8").reshape(-1, h, w, 3)
    picks = np.linspace(0, len(frames) - 1, GRID * GRID).astype(int)
    keyed = [key(frames[i]) for i in picks]
    box = None
    for _, a in keyed:
        b = a.point(lambda v: 255 if v > 60 else 0).getbbox()
        if b:
            box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    scale = CELL / max(box[2] - box[0], box[3] - box[1])
    cw, ch = round((box[2] - box[0]) * scale), round((box[3] - box[1]) * scale)
    canvas = Image.new("RGBA", (cw * GRID, ch * GRID), (0, 0, 0, 0))
    for i, (img, _) in enumerate(keyed):
        canvas.paste(img.crop(box).resize((cw, ch), Image.LANCZOS), ((i % GRID) * cw, (i // GRID) * ch))
    canvas.save(out / f"s-{name}.webp", quality=76, alpha_quality=88, method=6)
    print(name, (cw, ch), (out / f"s-{name}.webp").stat().st_size // 1024, "KB")


CHARACTERS = ("zayka", "medved", "slon", "zhiraf", "lisa", "snegir", "flamingo", "pavlin", "zhar", "edinorog", "drakon", "hero", "barmaley-full")
for name in CHARACTERS:
    cutout(name)
    sheet(name)
for name in ("flock", "barmaley", "kot", "hero-lego", "village", "bird", "tower"):
    img = Image.open(src / f"{name}.png").convert("RGB")
    img.thumbnail((1280, 1280), Image.LANCZOS)
    img.save(out / f"{name}.webp", quality=80, method=6)

for size in (180, 512):
    icon = Image.new("RGBA", (size, size), (255, 201, 40, 255))
    pic = Image.open(out / "zayka.webp").convert("RGBA")
    pic.thumbnail((int(size * .84), int(size * .84)), Image.LANCZOS)
    icon.alpha_composite(pic, ((size - pic.width) // 2, (size - pic.height) // 2))
    icon.convert("RGB").save(root / "docs" / f"icon-{size}.png")
