#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
publish_optimize.py — al PUBLICAR un post nuevo: asegura enlazado interno (que lo
descubran y reciba autoridad) + prepara el aviso IndexNow. Sistema #4.

Problema real medido: ~13% de URLs quedan "descubiertas/rastreadas sin indexar". Un post
nuevo nace HUÉRFANO de enlaces contextuales — sus hermanos de cluster ya tienen su bloque
de relacionados congelado y no lo apuntan → Google lo descubre peor y le da poca autoridad.
Este orquestador, al publicar:
  (1) OUTLINKS: da al post su bloque de relacionados (reusa related_posts) → enlaza a hermanos.
  (2) INLINKS: hace que N hermanos del MISMO cluster lo enlacen de vuelta → discovery + autoridad.
  (3) reúne las URLs cambiadas para el ping IndexNow.

Reusa related_posts (mapa de clusters + selección de hermanos) e indexnow_ping (aviso).
Determinista sobre el HTML local. Idempotente. DRY-RUN por defecto.

⚠️ --apply MUTA el HTML local (con guardarraíl safe_write). El ping IndexNow y el deploy son
ACCIONES PÚBLICAS → este script NO las ejecuta: imprime el comando exacto para que el dueño
lo apruebe.

Uso:
  python execution/publish_optimize.py --site "<dir>" --slug nuevo-post.html           # dry-run (plan)
  python execution/publish_optimize.py --site "<dir>" --slug nuevo-post.html --apply    # inyecta enlaces local
  # luego, con OK del dueño (acción pública):
  #   python execution/indexnow_ping.py --urls "<las URLs que imprime este script>"
"""
from __future__ import annotations

import argparse
import os
import sys

from _common import cfg, safe_write, save_json, site_url
from related_posts import (
    MARKER,
    already_has_related,
    build_block,
    clean_title,
    load_map,
    pick_related,
)

MIN_CTX = cfg("audit.min_contextual_links", 3)


def has_related_block(html: str) -> bool:
    # detecta el marker NUEVO o el nav viejo por clase (idempotente contra el sitio real)
    return already_has_related(html)


def ensure_outlinks(html: str, slug: str, posts: dict, n: int):
    """Si el post nuevo no tiene bloque de relacionados, lo construye e inserta antes de
    </article>. Devuelve (nuevo_html, hermanos_enlazados) o (None, []) si no aplica."""
    if has_related_block(html):
        return None, []
    related = pick_related(slug, posts, n)
    if len(related) < 2:
        return None, []
    block = build_block(related)
    new = html.replace("</article>", block + "</article>", 1)
    if new == html:
        return None, []
    return new, related


def _related_anchor(html: str):
    """Índice donde empieza el bloque de relacionados: el marker NUEVO si está, si no la
    apertura del <nav class="related-posts"> (posts viejos). -1 si no hay bloque."""
    i = html.find(MARKER)
    if i != -1:
        return i
    return html.find('<nav class="related-posts"')


def add_inlink(html: str, slug: str, title: str):
    """Inserta un <li><a href="slug"> dentro del bloque de relacionados EXISTENTE del hermano,
    justo antes del </ul> del bloque. Sirve para el marker NUEVO y el nav viejo (por clase).
    String-surgery (no re-serializa el doc → no rompe formato). Idempotente: si ya lo enlaza
    o no tiene bloque, devuelve None."""
    i = _related_anchor(html)
    if i == -1:
        return None  # el hermano no tiene bloque de relacionados
    j = html.find("</ul>", i)
    if j == -1:
        return None
    block = html[i:j]
    if f'href="{slug}"' in block:
        return None  # ya lo enlaza (idempotente)
    li = f'\n        <li><a href="{slug}">{title}</a></li>'
    return html[:j] + li + html[j:]


def plan_inlinks(site, slug, posts, cap):
    """Elige hasta `cap` hermanos del cluster que deberían enlazar al post nuevo.
    Devuelve lista de dicts: {slug, tiene_bloque, ya_enlaza, path}."""
    siblings = pick_related(slug, posts, cap * 3)  # candidatos por cluster
    plan = []
    for sib_slug, _title in siblings:
        path = os.path.join(site, "blog", sib_slug)
        if not os.path.isfile(path):
            continue
        html = open(path, encoding="utf-8").read()
        tiene = already_has_related(html)
        ya = (f'href="{slug}"' in html)
        plan.append({"slug": sib_slug, "tiene_bloque": tiene, "ya_enlaza": ya, "path": path})
        if len([p for p in plan if p["tiene_bloque"] and not p["ya_enlaza"]]) >= cap:
            break
    return plan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--slug", required=True, help="nombre del archivo del post nuevo, ej: mi-post.html")
    ap.add_argument("--n", type=int, default=4, help="nº de relacionados en el bloque del post nuevo")
    ap.add_argument("--apply", action="store_true", help="muta el HTML local (default: dry-run)")
    args = ap.parse_args()

    site = args.site
    slug = args.slug
    posts = load_map(site)
    if slug not in posts:
        print(f"ERROR: '{slug}' no está en el índice del blog (blog/index.html). "
              f"¿Agregaste su tarjeta con data-cats? Sin cluster no hay enlazado.")
        return 1

    new_title = clean_title(posts[slug]["title"])
    post_path = os.path.join(site, "blog", slug)
    if not os.path.isfile(post_path):
        print(f"ERROR: no existe {post_path}")
        return 1

    changed = []          # slugs mutados (o a mutar)
    notas = []

    # (1) OUTLINKS — bloque de relacionados en el post nuevo
    post_html = open(post_path, encoding="utf-8").read()
    new_html, related = ensure_outlinks(post_html, slug, posts, args.n)
    if new_html:
        if args.apply:
            if safe_write(post_path, new_html):
                changed.append(slug)
                notas.append(f"[outlinks] bloque de relacionados AÑADIDO a {slug} "
                             f"({len(related)} enlaces)")
            else:
                notas.append(f"[outlinks] RECHAZADO por safe_write (HTML quedaría roto): {slug}")
        else:
            changed.append(slug)
            notas.append(f"[outlinks] falta bloque de relacionados en {slug} → "
                         f"añadiría {len(related)}: " + ", ".join(t[:30] for _, t in related))
    else:
        notas.append(f"[outlinks] {slug} ya tiene bloque de relacionados (o sin hermanos suficientes)")

    # (2) INLINKS — hermanos del cluster que enlazan al post nuevo
    plan = plan_inlinks(site, slug, posts, MIN_CTX)
    aplicables = [p for p in plan if p["tiene_bloque"] and not p["ya_enlaza"]]
    sin_bloque = [p for p in plan if not p["tiene_bloque"]]
    for p in aplicables:
        if args.apply:
            html = open(p["path"], encoding="utf-8").read()
            mutated = add_inlink(html, slug, new_title)
            if mutated and safe_write(p["path"], mutated):
                changed.append(p["slug"])
                notas.append(f"[inlinks] {p['slug']} ahora enlaza a {slug}")
            else:
                notas.append(f"[inlinks] no se pudo insertar en {p['slug']} (safe_write/estado)")
        else:
            changed.append(p["slug"])
            notas.append(f"[inlinks] {p['slug']} debería enlazar a {slug} (tiene bloque)")
    if sin_bloque:
        notas.append("[inlinks] hermanos SIN bloque de relacionados (corre related_posts --apply "
                     "primero): " + ", ".join(p["slug"] for p in sin_bloque))
    if not aplicables and not sin_bloque:
        notas.append("[inlinks] el post ya recibe enlaces de sus hermanos o no hay cluster")

    # (3) IndexNow — URLs cambiadas (acción pública: NO se dispara aquí)
    base = site_url() + "/blog/"
    urls = [base + s for s in dict.fromkeys(changed)]  # dedup preservando orden

    out = save_json("publish-optimize.json", {
        "slug": slug, "apply": args.apply, "min_contextual": MIN_CTX,
        "cambiados": list(dict.fromkeys(changed)), "urls_indexnow": urls, "notas": notas})

    mode = "APLICADO (HTML local mutado)" if args.apply else "DRY-RUN (usa --apply para inyectar)"
    print(f"publish_optimize: {slug} | modo: {mode} | archivos cambiados: {len(set(changed))} -> {out}")
    for nlin in notas:
        print("  " + nlin)
    if urls:
        print("\n  IndexNow (ACCIÓN PÚBLICA — requiere OK del dueño + deploy previo):")
        print('    python execution/indexnow_ping.py --urls "' + ",".join(urls) + '"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
