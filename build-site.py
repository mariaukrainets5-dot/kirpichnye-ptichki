#!/usr/bin/env python3
"""Wraps index.html (Artifact format, no document tags) into docs/index.html for GitHub Pages
and copies the game art next to it."""
import shutil
from pathlib import Path

HEAD = """<!doctype html>
<html lang="ru">
<head>
<meta name="description" content="Злой колдун Бармалей превратил зверят в кирпичики. Собери их, оживи и построй им домики.">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Зверята">
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


root = Path(__file__).parent
docs = root / "docs"
page = (root / "index.html").read_text(encoding="utf-8")
head, body = page.split('<canvas id="scene">', 1)
assert CDN in body
(docs / "index.html").write_text(
    HEAD + head + '</head>\n<body>\n<canvas id="scene">' + body.replace(CDN, "three.min.js") + SW + "</body>\n</html>\n",
    encoding="utf-8",
)
shutil.copytree(root / "art", docs / "art", dirs_exist_ok=True)
