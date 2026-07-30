#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
dup_check.py — detecta contenido (casi) duplicado entre posts del blog.

El boilerplate duplicado (62 posts con el mismo cuerpo) costó el ~0 tráfico orgánico
y se cazó a mano. Este script lo detecta AUTOMÁTICO: compara el cuerpo de cada post
por shingles (n-gramas de palabras) y reporta los pares con alta similitud (Jaccard).
Así el auditor y el informe avisan si NOVA (o una plantilla) reintroduce duplicados.

Salida: .tmp/dup_check.json + pares sospechosos por stdout.
Uso:
  python execution/dup_check.py --site "<dir>" [--threshold 0.30] [--n 4]
"""
import argparse
import glob
import os
import re
import sys

TAG_RE = re.compile(r'<[^>]+>')
WS_RE = re.compile(r'\s+')


def body_text(html):
    m = re.search(r'<article\b[^>]*>(.*?)</article>', html, re.S | re.I)
    chunk = m.group(1) if m else html
    txt = TAG_RE.sub(' ', chunk)
    txt = re.sub(r'[^0-9a-záéíóúñü ]', ' ', txt.lower())
    return WS_RE.sub(' ', txt).strip()


def shingles(text, n):
    w = text.split()
    return set(tuple(w[i:i + n]) for i in range(max(0, len(w) - n + 1)))


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--threshold", type=float, default=0.30)
    ap.add_argument("--n", type=int, default=4)
    args = ap.parse_args()

    posts = {}
    for f in sorted(glob.glob(os.path.join(args.site, "blog", "*.html"))):
        if os.path.basename(f) == "index.html":
            continue
        sh = shingles(body_text(open(f, encoding="utf-8", errors="replace").read()), args.n)
        if len(sh) >= 10:
            posts[os.path.basename(f)] = sh

    names = list(posts)
    pairs = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            s = jaccard(posts[names[i]], posts[names[j]])
            if s >= args.threshold:
                pairs.append((round(s, 2), names[i], names[j]))
    pairs.sort(reverse=True)

    import json
    tmp = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".tmp")
    os.makedirs(tmp, exist_ok=True)
    out = os.path.join(tmp, "dup_check.json")
    json.dump({"threshold": args.threshold, "n": args.n, "posts": len(posts),
               "pares_duplicados": [{"sim": s, "a": a, "b": b} for s, a, b in pairs]},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"dup_check: {len(posts)} posts comparados. Pares sospechosos (sim>={args.threshold}): {len(pairs)} -> {out}")
    for s, a, b in pairs[:15]:
        print(f"  {s:.2f}  {a}  <->  {b}")
    if not pairs:
        print("  Sin duplicados. Contenido único.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
