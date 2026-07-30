#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
img_dimensions.py — añade width/height reales a los <img> que no los tienen (arregla CLS).

Imágenes sin width/height causan layout shift (CLS): el navegador no reserva su espacio
hasta que cargan. Este script lee las dimensiones intrínsecas (Pillow para raster,
viewBox para SVG) y añade los atributos width/height → el navegador reserva el hueco
correcto y el contenido deja de saltar. El CSS sigue controlando el tamaño de display.

Determinista e idempotente (salta imgs que ya tienen ambos atributos).

Uso:
  python execution/img_dimensions.py --site "<dir>" --files index.html [--apply]
"""
import argparse
import os
import re
import sys

IMG_RE = re.compile(r'<img\b[^>]*>', re.I | re.S)
HAS_W = re.compile(r'\bwidth\s*=', re.I)
HAS_H = re.compile(r'\bheight\s*=', re.I)
SRC_RE = re.compile(r'\bsrc\s*=\s*["\']([^"\']+)["\']', re.I)
VIEWBOX_RE = re.compile(r'viewBox\s*=\s*["\']([\d.\s-]+)["\']', re.I)


def dims(site, src):
    src = src.split("?")[0]  # quita ?v=...
    path = os.path.join(site, src.lstrip("/"))
    if not os.path.isfile(path):
        return None
    if src.lower().endswith(".svg"):
        try:
            vb = VIEWBOX_RE.search(open(path, encoding="utf-8", errors="ignore").read())
            if vb:
                p = vb.group(1).split()
                if len(p) == 4:
                    return int(round(float(p[2]))), int(round(float(p[3])))
        except Exception:
            return None
        return None
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.width, im.height
    except Exception:
        return None


def process(site, html):
    out, last, n = [], 0, 0
    for m in IMG_RE.finditer(html):
        tag = m.group(0)
        if HAS_W.search(tag) and HAS_H.search(tag):
            continue
        sm = SRC_RE.search(tag)
        if not sm:
            continue
        d = dims(site, sm.group(1))
        if not d:
            continue
        w, h = d
        new_tag = tag[:-1].rstrip() + f' width="{w}" height="{h}">' if tag.endswith(">") else tag
        # inserta antes de /> o >
        if tag.rstrip().endswith("/>"):
            new_tag = tag.rstrip()[:-2].rstrip() + f' width="{w}" height="{h}" />'
        else:
            new_tag = tag.rstrip()[:-1].rstrip() + f' width="{w}" height="{h}">'
        out.append(html[last:m.start()])
        out.append(new_tag)
        last = m.end()
        n += 1
    out.append(html[last:])
    return "".join(out), n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--files", nargs="*", default=["index.html"])
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    total = 0
    for rel in args.files:
        p = os.path.join(args.site, rel)
        if not os.path.isfile(p):
            print(f"[skip] {rel}")
            continue
        html = open(p, encoding="utf-8").read()
        new, n = process(args.site, html)
        total += n
        print(f"  {rel}: {n} imgs dimensionadas")
        if args.apply and n:
            open(p, "w", encoding="utf-8").write(new)
    print(f"\nTotal: {total}. Modo: {'APLICADO' if args.apply else 'DRY-RUN'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
