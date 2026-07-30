#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
internal_links.py — audita el ENLAZADO INTERNO (autoridad + descubrimiento).

La directiva NOVA exige ">=3 enlaces internos contextuales" por post y "sin huérfanas",
pero nada lo MEDÍA. Este script construye el grafo de enlaces internos del sitio y calcula:
  - inlinks (cuántas páginas enlazan A cada página) → 0 = huérfana de enlace (Google la
    descubre peor, recibe poca autoridad).
  - outlinks contextuales (enlaces en el CUERPO <article>/<main>, no en nav/footer) →
    la señal de autoridad real; la directiva pide >=3.
  - profundidad de clic desde la home (BFS) → páginas muy profundas se descubren peor.

Determinista, lee HTML local. Salida: .tmp/internal_links.json + resumen por stdout.
Misma política de archivos que el resto (html_files de _common).

Uso:
  python execution/internal_links.py --site "<dir>"
"""
from __future__ import annotations

import os
from collections import deque

from _common import cfg, html_files, parse, rel_url, save_json, site_dir

MIN_CTX = cfg("audit.min_contextual_links", 3)


def _skip_href(h):
    h = (h or "").strip()
    return (not h) or h.startswith(("mailto:", "tel:", "javascript:", "#", "http", "//"))


def _resolve_to_page(site, page_file, href, page_index):
    """Resuelve un href relativo/absoluto al rel_url de la página destino, o None."""
    u = href.split("#")[0].split("?")[0].strip()
    if not u:
        return None
    base = os.path.dirname(str(page_file))
    if u.startswith("/"):
        target = os.path.join(str(site), u.lstrip("/"))
    else:
        target = os.path.normpath(os.path.join(base, u))
    if u.endswith("/") or os.path.isdir(target):
        target = os.path.join(target, "index.html")
    return page_index.get(os.path.normcase(os.path.abspath(target)))


def main():
    site = site_dir()
    files = html_files(site)
    # índice ruta-absoluta -> rel_url (para resolver enlaces a páginas reales)
    page_index = {os.path.normcase(os.path.abspath(str(f))): rel_url(site, f) for f in files}

    inlinks = {rel_url(site, f): set() for f in files}     # url -> {urls que la enlazan}
    ctx_out = {rel_url(site, f): 0 for f in files}          # url -> nº enlaces contextuales
    edges_all = {rel_url(site, f): set() for f in files}    # url -> {urls destino} (todos)
    anchors = {}                                            # url destino -> set(anchor text)
    noindex = set()                                        # urls con robots=noindex (intencional)

    for f in files:
        src = rel_url(site, f)
        soup = parse(f)
        mr = soup.find("meta", attrs={"name": "robots"})
        if mr and "noindex" in (mr.get("content") or "").lower():
            noindex.add(src)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if _skip_href(href):
                continue
            dst = _resolve_to_page(site, f, href, page_index)
            if not dst or dst == src:
                continue
            edges_all[src].add(dst)
            inlinks[dst].add(src)
            anchors.setdefault(dst, set()).add(a.get_text(" ", strip=True)[:60])
            # contextual = dentro de <article> o <main> (no nav/footer)
            if a.find_parent(["article", "main"]):
                ctx_out[src] += 1

    # profundidad de clic desde la home ("/") por BFS sobre TODOS los enlaces
    depth = {u: None for u in inlinks}
    if "/" in depth:
        depth["/"] = 0
        q = deque(["/"])
        while q:
            u = q.popleft()
            for v in edges_all.get(u, ()):
                if depth.get(v) is None:
                    depth[v] = depth[u] + 1
                    q.append(v)

    pages = []
    for u in sorted(inlinks):
        pages.append({
            "url": u,
            "inlinks": len(inlinks[u]),
            "ctx_outlinks": ctx_out[u],
            "depth": depth.get(u),
            "anchor_variedad": len(anchors.get(u, set())),
        })

    # las páginas noindex (legales, plantillas de utilidad) NO son contenido público:
    # que sean huérfanas/profundas es correcto → se excluyen del reporte de problemas.
    def indexable(u):
        return u != "/" and u not in noindex
    orphans = [p["url"] for p in pages if p["inlinks"] == 0 and indexable(p["url"])]
    unreachable = [p["url"] for p in pages if p["depth"] is None and indexable(p["url"])]
    pobres_ctx = [p["url"] for p in pages if p["ctx_outlinks"] < MIN_CTX and indexable(p["url"])]
    deep = sorted([p for p in pages if p["depth"] and p["depth"] >= 3], key=lambda p: -p["depth"])

    out = save_json("internal_links.json", {
        "min_contextual": MIN_CTX,
        "resumen": {"paginas": len(pages), "huerfanas": len(orphans),
                    "inalcanzables": len(unreachable), "pobres_contextual": len(pobres_ctx)},
        "huerfanas": orphans, "inalcanzables": unreachable,
        "pobres_contextual": pobres_ctx,
        "mas_profundas": [{"url": p["url"], "depth": p["depth"]} for p in deep[:10]],
        "pages": pages})

    print(f"internal_links: {len(pages)} páginas | huérfanas={len(orphans)} "
          f"inalcanzables={len(unreachable)} pobres_ctx(<{MIN_CTX})={len(pobres_ctx)} -> {out}")
    for u in orphans[:10]:
        print(f"  huérfana (0 inlinks): {u}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
