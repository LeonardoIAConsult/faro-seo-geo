#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
breadcrumb_inject.py — inyecta BreadcrumbList JSON-LD en los posts del blog.

BreadcrumbList es un rich-result de Google (muestra la ruta Inicio > Blog > Post en
los resultados) y ayuda a buscadores e IA a entender la jerarquia del sitio. GEO+SEO,
determinista, gratis.

Ruta: Inicio > Blog > <titulo del post>. Titulo y URL se toman del propio post
(<title> / <h1> y <link rel=canonical>). Idempotente (salta si ya tiene BreadcrumbList).

Uso:
  python execution/breadcrumb_inject.py --site "<dir>" [--apply]
"""
import argparse
import glob
import html as htmllib
import json
import os
import re
import sys

from _common import site_url

ORIGIN = site_url()  # de config/env (site.url); genérico si no hay config
HAS_BC = re.compile(r'"@type"\s*:\s*"BreadcrumbList"', re.I)
TITLE_RE = re.compile(r'<title>(.*?)</title>', re.I | re.S)
H1_RE = re.compile(r'<h1[^>]*>(.*?)</h1>', re.I | re.S)
CANON_RE = re.compile(r'<link\s+rel=["\']canonical["\']\s+href=["\'](.*?)["\']', re.I | re.S)
TAG_RE = re.compile(r'<[^>]+>')


def clean(s):
    return re.sub(r'\s+', ' ', htmllib.unescape(TAG_RE.sub('', s or ''))).strip()


def build(title, canonical):
    data = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": ORIGIN + "/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": ORIGIN + "/blog/"},
            {"@type": "ListItem", "position": 3, "name": title, "item": canonical},
        ],
    }
    return '    <script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + '</script>\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.site, "blog", "*.html")))
    files = [f for f in files if os.path.basename(f) != "index.html"]
    done = 0
    for f in files:
        h = open(f, encoding="utf-8").read()
        if HAS_BC.search(h):
            continue
        hm = H1_RE.search(h)
        tm = TITLE_RE.search(h)
        title = clean(hm.group(1)) if hm else (clean(tm.group(1)) if tm else "")
        cm = CANON_RE.search(h)
        canonical = cm.group(1).strip() if cm else (ORIGIN + "/blog/" + os.path.basename(f))
        if not title:
            continue
        block = build(title, canonical)
        new = h.replace("</head>", block + "</head>", 1)
        if new == h:
            continue
        done += 1
        if args.apply:
            open(f, "w", encoding="utf-8").write(new)
    mode = "APLICADO" if args.apply else "DRY-RUN (usa --apply)"
    print(f"{done} posts con BreadcrumbList a inyectar. Modo: {mode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
