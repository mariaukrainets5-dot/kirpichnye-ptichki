#!/usr/bin/env python3
"""Wraps index.html (Artifact format, no document tags) into docs/index.html for GitHub Pages
and draws the home-screen icons from the bullfinch in the game's own data."""
import re
import struct
import zlib
from pathlib import Path

HEAD = """<!doctype html>
<html lang="ru">
<head>
<meta name="description" content="Собирай птичек из кирпичиков и прогоняй Кота Бандита, который всё разбрасывает.">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Птички">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#bfd9f2">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icon-180.png">
<style>
:root { padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px); box-sizing: border-box; }
img { max-width: 100%; }
</style>
"""
SW = """<script>if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');</script>
"""
CDN = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"


def png(path, size, pixels):
    raw = b"".join(b"\0" + bytes(c for x in range(size) for c in pixels(x, y)) for y in range(size))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def icons(page, docs):
    bird = page[page.index("id:'snegir'"):page.index("id:'tukan'")]
    pal = {k: bytes.fromhex(v) for k, v in re.findall(r"(\w):0x([0-9a-f]{6})", bird)}
    rows = re.findall(r'"([.A-Za-z]+)"', bird)
    slices = [rows[i:i + 11] for i in range(0, len(rows), 11)]
    top = {}
    for layer in slices:  # outer slices sit in front
        for r, row in enumerate(layer):
            for c, ch in enumerate(row):
                if ch != ".":
                    top[(c, r)] = pal[ch]
    for size in (180, 512):
        cell = size * 72 // 100 // 13
        ox, oy = (size - cell * 13) // 2, (size - cell * 11) // 2
        png(docs / f"icon-{size}.png", size,
            lambda x, y: top.get(((x - ox) // cell, (y - oy) // cell), b"\xff\xc9\x28"))


root = Path(__file__).parent
docs = root / "docs"
page = (root / "index.html").read_text(encoding="utf-8")
head, body = page.split('<canvas id="scene">', 1)
assert CDN in body
(docs / "index.html").write_text(
    HEAD + head + '</head>\n<body>\n<canvas id="scene">' + body.replace(CDN, "three.min.js") + SW + "</body>\n</html>\n",
    encoding="utf-8",
)
icons(page, docs)
