#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
alt_fill.py — rellena el atributo alt vacio (alt="") de las miniaturas de
articulos (portadas .webp) usando el titulo de la tarjeta que las acompana.

Determinista e idempotente:
  - Solo toca <img> con alt VACIO ('' o "   ") y src que termina en .webp.
  - El texto del alt = el primer <h1..h6> que aparece DESPUES del <img>
    dentro de una ventana corta (misma tarjeta). Si no hay heading cerca,
    NO toca la imagen (probablemente decorativa).
  - No modifica imagenes que ya tienen alt con contenido.

Uso:
  python execution/alt_fill.py --site "<dir>" [--files a.html b.html] [--apply]
  Sin --apply: dry-run (muestra que cambiaria, no escribe).
"""
import argparse
import html as htmllib
import os
import re
import sys

# imgs candidatas: alt vacio + src .webp
IMG_RE = re.compile(r'<img\b[^>]*?>', re.I | re.S)
ALT_ATTR_RE = re.compile(r'\balt\s*=\s*(["\'])(.*?)\1', re.I | re.S)
SRC_RE = re.compile(r'\bsrc\s*=\s*(["\'])(.*?)\1', re.I | re.S)
# heading despues del img (ventana corta)
HEADING_RE = re.compile(r'<h[1-6]\b[^>]*>(.*?)</h[1-6]>', re.I | re.S)
TAG_RE = re.compile(r'<[^>]+>')
WS_RE = re.compile(r'\s+')

WINDOW = 400  # chars a mirar despues del img para hallar el titulo


def clean_title(raw: str) -> str:
    txt = TAG_RE.sub('', raw)          # quita tags internos (span, etc.)
    txt = htmllib.unescape(txt)        # &amp; -> &
    txt = WS_RE.sub(' ', txt).strip()
    return txt


def alt_value_escape(txt: str) -> str:
    # el alt ira dentro de comillas dobles
    return txt.replace('"', '&quot;')


def process_html(text: str):
    """Devuelve (nuevo_texto, lista_de_cambios[(src, titulo)])."""
    changes = []
    out = []
    last = 0
    for m in IMG_RE.finditer(text):
        tag = m.group(0)
        alt_m = ALT_ATTR_RE.search(tag)
        src_m = SRC_RE.search(tag)
        src = src_m.group(2) if src_m else ''
        alt_empty = alt_m is not None and alt_m.group(2).strip() == ''
        if not (alt_empty and src.lower().endswith('.webp')):
            continue
        # busca titulo en la ventana siguiente
        win = text[m.end():m.end() + WINDOW]
        h = HEADING_RE.search(win)
        if not h:
            continue
        title = clean_title(h.group(1))
        if not title:
            continue
        new_alt = alt_value_escape(title)
        # reemplaza SOLO el valor del alt dentro de esta etiqueta
        q = alt_m.group(1)
        new_tag = tag[:alt_m.start()] + f'alt={q}{new_alt}{q}' + tag[alt_m.end():]
        out.append(text[last:m.start()])
        out.append(new_tag)
        last = m.end()
        changes.append((src, title))
    out.append(text[last:])
    return ''.join(out), changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', required=True)
    ap.add_argument('--files', nargs='*',
                    default=['index.html', 'blog/index.html'],
                    help='rutas relativas al --site')
    ap.add_argument('--apply', action='store_true',
                    help='escribe los cambios (por defecto solo muestra)')
    args = ap.parse_args()

    total = 0
    for rel in args.files:
        path = os.path.join(args.site, rel)
        if not os.path.isfile(path):
            print(f'[skip] no existe: {rel}')
            continue
        text = open(path, encoding='utf-8').read()
        new_text, changes = process_html(text)
        print(f'\n=== {rel}: {len(changes)} imgs con alt a rellenar ===')
        for src, title in changes[:8]:
            print(f'   {os.path.basename(src)}  ->  "{title[:70]}"')
        if len(changes) > 8:
            print(f'   ... (+{len(changes) - 8} mas)')
        total += len(changes)
        if args.apply and changes:
            open(path, 'w', encoding='utf-8').write(new_text)
            print(f'   [ESCRITO] {rel}')

    mode = 'APLICADO' if args.apply else 'DRY-RUN (usa --apply para escribir)'
    print(f'\nTotal: {total} imgs. Modo: {mode}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
