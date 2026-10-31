#!/usr/bin/env python3
"""Turns the Higgsfield originals in art-src/ into game images in art/:
cut-outs on transparency, animation sheets from the clips in art-src/video/ and resized story pictures."""
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageFilter

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


GRID, CELL, PAD = 8, 224, 6  # PAD: пустая кромка вокруг кадра, чтобы кадры не просвечивали друг в друга
FF = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
FPS = 24


def main_only(img, a):
    """Keeps only the character itself: stray smoke and sparks around it are dropped."""
    small = np.asarray(a.resize((96, 96)).point(lambda v: 255 if v > 40 else 0).filter(ImageFilter.MaxFilter(3))) > 0
    seen = np.zeros(small.shape, bool)
    best = []
    for y, x in zip(*np.nonzero(small)):
        if seen[y, x]:
            continue
        stack, part = [(y, x)], []
        seen[y, x] = True
        while stack:
            cy, cx = stack.pop()
            part.append((cy, cx))
            for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                if 0 <= ny < 96 and 0 <= nx < 96 and small[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(part) > len(best):
            best = part
    mask = np.zeros(small.shape, "uint8")
    for y, x in best:
        mask[y, x] = 255
    grown = Image.fromarray(mask).resize(a.size, Image.NEAREST).filter(ImageFilter.MaxFilter(9))
    clean = ImageChops.multiply(a, grown)
    img = img.copy()
    img.putalpha(clean)
    return img, clean


def best_loop(frames):
    """Finds the longest stretch whose last frame looks like its first one, so the clip loops without a jump."""
    small = np.stack([np.asarray(Image.fromarray(f).resize((48, 48))) for f in frames[::2]]).astype(float)
    n = len(small)
    least, most = int(2.6 * FPS / 2), n - 1
    best, pair = 1e18, (0, n - 1)
    for a in range(0, n - least):
        for b in range(a + least, min(a + most, n - 1) + 1):
            score = ((small[a] - small[b]) ** 2).mean() - (b - a) * .06
            if score < best:
                best, pair = score, (a, b)
    return pair[0] * 2, pair[1] * 2


def sheet(name):
    """Turns a clip into a sheet of cut-out frames for the game."""
    clip = src / "video" / f"{name}.mp4"
    info = subprocess.run([FF[:-6] + "ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(clip)], capture_output=True, text=True).stdout.strip().split(",")
    w, h = int(info[0]) // 2 * 2 // 2, int(info[1]) // 2
    raw = subprocess.run([FF, "-v", "error", "-i", str(clip), "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    frames = np.frombuffer(raw, "uint8").reshape(-1, h, w, 3)
    a, b = best_loop(frames)
    picks = np.linspace(a, b, GRID * GRID, endpoint=False).astype(int)
    keyed = [main_only(*key(frames[i])) for i in picks]
    box = None
    for _, al in keyed:
        c = al.point(lambda v: 255 if v > 60 else 0).getbbox()
        if c:
            box = c if box is None else (min(box[0], c[0]), min(box[1], c[1]), max(box[2], c[2]), max(box[3], c[3]))
    scale = (CELL - PAD * 2) / max(box[2] - box[0], box[3] - box[1])
    cw, ch = round((box[2] - box[0]) * scale), round((box[3] - box[1]) * scale)
    fw, fh = cw + PAD * 2, ch + PAD * 2
    canvas = Image.new("RGBA", (fw * GRID, fh * GRID), (0, 0, 0, 0))
    for i, (img, _) in enumerate(keyed):
        canvas.paste(img.crop(box).resize((cw, ch), Image.LANCZOS), ((i % GRID) * fw + PAD, (i // GRID) * fh + PAD))
    canvas.save(out / f"s-{name}.webp", quality=72, alpha_quality=85, method=4)
    print(name, f"loop {a/FPS:.1f}-{b/FPS:.1f}s", (fw, fh), (out / f"s-{name}.webp").stat().st_size // 1024, "KB")


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
