#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
og_fill.py — inyecta Open Graph + Twitter Card en páginas que no los tienen.

Para cada HTML SIN og:title, construye el bloque OG/Twitter a partir de datos
que la página YA tiene (deterministas): <title>, meta description, canonical y,
si existe, la portada blog/img/<slug>.webp. Mejora el share en redes (SEO social)
y refuerza señales para GEO/IA.

Idempotente: si ya hay og:title, no toca la página.
Inserta el bloque justo antes de </head>.

Uso:
  python execution/og_fill.py --site "<dir>" [--files a.html ...] [--apply]
  Sin --apply: dry-run.
Por defecto procesa todos los blog/*.html (menos index) del sitio.
"""
import argparse
import glob
import html as htmllib
import os
import re
import sys

from _common import site_url

TITLE_RE = re.compile(r'<title[^>]*>(.*?)</title>', re.I | re.S)
DESC_RE = re.compile(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', re.I | re.S)
CANON_RE = re.compile(r'<link\s+rel=["\']canonical["\']\s+href=["\'](.*?)["\']', re.I | re.S)
HAS_OGTITLE_RE = re.compile(r'property=["\']og:title["\']', re.I)


def esc_attr(s):
    return (htmllib.unescape(s)
            .replace('&', '&amp;').replace('"', '&quot;')
            .replace('<', '&lt;').replace('>', '&gt;').strip())


def origin_of(url):
    m = re.match(r'(https?://[^/]+)', url or '')
    return m.group(1) if m else ''


def build_block(title, desc, canonical, image):
    L = ['    <!-- Open Graph / Twitter (generado por seo-forge/og_fill) -->']
    L.append('    <meta property="og:type" content="article">')
    L.append(f'    <meta property="og:title" content="{title}">')
    if desc:
        L.append(f'    <meta property="og:description" content="{desc}">')
    if canonical:
        L.append(f'    <meta property="og:url" content="{canonical}">')
    if image:
        L.append(f'    <meta property="og:image" content="{image}">')
    L.append('    <meta property="og:site_name" content="Your Name">')
    L.append('    <meta property="og:locale" content="es_ES">')
    L.append('    <meta name="twitter:card" content="summary_large_image">')
    L.append(f'    <meta name="twitter:title" content="{title}">')
    if desc:
        L.append(f'    <meta name="twitter:description" content="{desc}">')
    if image:
        L.append(f'    <meta name="twitter:image" content="{image}">')
    return '\n'.join(L) + '\n'


def process(site, path):
    html = open(path, encoding='utf-8').read()
    if HAS_OGTITLE_RE.search(html):
        return None  # ya tiene OG
    tm = TITLE_RE.search(html)
    if not tm:
        return None
    title = esc_attr(tm.group(1))
    dm = DESC_RE.search(html)
    desc = esc_attr(dm.group(1)) if dm else ''
    cm = CANON_RE.search(html)
    canonical = cm.group(1).strip() if cm else ''
    # portada: blog/img/<slug>.webp
    slug = os.path.splitext(os.path.basename(path))[0]
    image = ''
    cover_rel = os.path.join('blog', 'img', slug + '.webp')
    if os.path.isfile(os.path.join(site, cover_rel)):
        origin = origin_of(canonical) or site_url()
        image = f'{origin}/blog/img/{slug}.webp'
    block = build_block(title, desc, canonical, image)
    new = html.replace('</head>', block + '</head>', 1)
    if new == html:
        return None  # no </head>
    return new, title, bool(image)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', required=True)
    ap.add_argument('--files', nargs='*')
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    if args.files:
        files = [os.path.join(args.site, f) for f in args.files]
    else:
        files = sorted(glob.glob(os.path.join(args.site, 'blog', '*.html')))
        files = [f for f in files if os.path.basename(f) != 'index.html']

    done = 0
    for path in files:
        if not os.path.isfile(path):
            continue
        r = process(args.site, path)
        if not r:
            continue
        new, title, has_img = r
        done += 1
        flag = 'img' if has_img else 'sin-img'
        print(f'  [{flag}] {os.path.basename(path)}  -> "{title[:60]}"')
        if args.apply:
            open(path, 'w', encoding='utf-8').write(new)

    mode = 'APLICADO' if args.apply else 'DRY-RUN (usa --apply)'
    print(f'\n{done} páginas con OG a inyectar. Modo: {mode}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
