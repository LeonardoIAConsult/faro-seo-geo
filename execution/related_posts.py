#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
related_posts.py — enlazado interno por clusters (autoridad temática, gratis).

Inserta al final de cada post un bloque "Artículos relacionados" con 3-4 enlaces
a hermanos del MISMO cluster (categoría), usando el título real como anchor
(descriptivo = bueno para SEO). Es la palanca de enlazado interno #1 y 100% gratis.

Fuente del mapa de clusters: las tarjetas de blog/index.html (`data-cats` por post).
Determinista e idempotente (marca `<!-- related-posts -->`; no duplica).
Se inyecta justo antes de `</article>`.

Uso:
  python execution/related_posts.py --site "<dir>" [--n 4] [--apply]
  Sin --apply: dry-run.
"""
import argparse
import hashlib
import os
import re
import sys

from bs4 import BeautifulSoup

MARKER = "<!-- related-posts -->"
EMOJI_RE = re.compile(
    r'[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF'
    r'\U00002190-\U000021FF\U00002B00-\U00002BFF️‍]+'
)


def clean_title(t):
    t = EMOJI_RE.sub('', t or '')
    return re.sub(r'\s+', ' ', t).strip(' -–—:·')


def load_map(site):
    """slug -> {cats:set, title:str} desde el índice del blog."""
    idx = os.path.join(site, "blog", "index.html")
    soup = BeautifulSoup(open(idx, encoding="utf-8").read(), "lxml")
    posts = {}
    for a in soup.select("a.blog-card"):
        href = (a.get("href") or "").strip()
        if not href or not href.endswith(".html"):
            continue
        h = a.find(["h2", "h3", "h4"])
        title = clean_title(h.get_text(" ", strip=True)) if h else href
        cats = set((a.get("data-cats") or "").split())
        posts[href] = {"cats": cats, "title": title}
    return posts


def pick_related(slug, posts, n):
    me = posts[slug]
    cands = []
    for other, meta in posts.items():
        if other == slug:
            continue
        shared = len(me["cats"] & meta["cats"])
        if shared == 0:
            continue
        # orden estable pseudo-aleatorio por par (diversifica sin azar real)
        tie = hashlib.md5((slug + "|" + other).encode()).hexdigest()
        cands.append((-shared, tie, other, meta["title"]))
    cands.sort()
    return [(o, t) for _, _, o, t in cands[:n]]


def build_block(related):
    lis = "".join(
        f'\n        <li><a href="{o}">{t}</a></li>' for o, t in related
    )
    return (
        f'{MARKER}\n'
        f'    <nav class="related-posts" aria-label="Artículos relacionados">\n'
        f'      <h2>Artículos relacionados</h2>\n'
        f'      <ul>{lis}\n'
        f'      </ul>\n'
        f'    </nav>\n'
    )


def process(site, slug, posts, n):
    path = os.path.join(site, "blog", slug)
    if not os.path.isfile(path):
        return None
    html = open(path, encoding="utf-8").read()
    if MARKER in html:
        return None  # ya tiene bloque
    related = pick_related(slug, posts, n)
    if len(related) < 2:
        return None  # sin suficientes hermanos, no forzar
    block = build_block(related)
    new = html.replace("</article>", block + "</article>", 1)
    if new == html:
        return None  # sin </article>
    return new, related


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    posts = load_map(args.site)
    done = 0
    for slug in posts:
        r = process(args.site, slug, posts, args.n)
        if not r:
            continue
        new, related = r
        done += 1
        if done <= 6:
            print(f'  {slug} -> ' + ", ".join(t[:30] for _, t in related))
        if args.apply:
            open(os.path.join(args.site, "blog", slug), "w", encoding="utf-8").write(new)

    mode = "APLICADO" if args.apply else "DRY-RUN (usa --apply)"
    print(f'\n{done} posts con bloque de relacionados. Modo: {mode}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
