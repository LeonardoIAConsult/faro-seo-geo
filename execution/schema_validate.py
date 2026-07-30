#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
schema_validate.py — valida el JSON-LD de cada página contra los campos que Google
exige por tipo. Un schema con campos faltantes NO genera rich result (Google lo ignora).

Chequea @type y sus requeridos:
  Article/BlogPosting -> headline, author
  FAQPage             -> mainEntity[] con name + acceptedAnswer.text
  BreadcrumbList      -> itemListElement[] con position + name + item
  VideoObject         -> name, thumbnailUrl, uploadDate
  Person/Organization/Blog -> name
Reporta JSON inválido y campos faltantes. Salida: .tmp/schema_validate.json.

Usa bs4 + html_files de _common (misma política de archivos que el resto de auditores;
evita el drift que había con el parser regex propio).

Uso:
  python execution/schema_validate.py --site "<dir>"
"""
from __future__ import annotations

import json

from _common import html_files, parse, rel_url, save_json, site_dir

# Campos que Google EXIGE (sin ellos no hay rich result → issue duro)
REQUIRED = {
    "Article": ["headline", "author"],
    "BlogPosting": ["headline", "author"],
    "Person": ["name"],
    "Organization": ["name"],
    "Blog": ["name"],
    "VideoObject": ["name", "thumbnailUrl", "uploadDate"],
}

# Campos RECOMENDADOS (mejoran el rich result; su ausencia no lo rompe → aviso suave)
RECOMMENDED = {
    "Article": ["image", "datePublished"],
    "BlogPosting": ["image", "datePublished"],
    "Organization": ["logo", "sameAs"],
    "VideoObject": ["description", "duration"],
}


def check_node(node, issues, recs, where):
    t = node.get("@type")
    if isinstance(t, list):
        t = t[0] if t else None
    if not t:
        return
    for req in REQUIRED.get(t, []):
        if not node.get(req):
            issues.append(f"{where}: {t} sin '{req}'")
    for rec in RECOMMENDED.get(t, []):
        if not node.get(rec):
            recs.append(f"{where}: {t} podría añadir '{rec}' (mejora el rich result)")
    if t == "ImageObject" and not (node.get("url") or node.get("contentUrl")):
        issues.append(f"{where}: ImageObject sin 'url'/'contentUrl'")
    if t == "WebPage" and not node.get("name"):
        recs.append(f"{where}: WebPage podría añadir 'name'")
    if t == "FAQPage":
        me = node.get("mainEntity") or []
        if not me:
            issues.append(f"{where}: FAQPage sin mainEntity")
        for q in (me if isinstance(me, list) else [me]):
            if not q.get("name") or not (q.get("acceptedAnswer") or {}).get("text"):
                issues.append(f"{where}: FAQPage con Q/A incompleta")
                break
    if t == "BreadcrumbList":
        items = node.get("itemListElement") or []
        if not items:
            issues.append(f"{where}: BreadcrumbList sin itemListElement")
        for it in (items if isinstance(items, list) else [items]):
            if not it.get("name") or not it.get("item") or "position" not in it:
                issues.append(f"{where}: BreadcrumbList con item incompleto")
                break


def main():
    root = site_dir()
    issues, recs, invalid, pages_ok = [], [], 0, 0
    for f in html_files(root):
        rel = rel_url(root, f)
        soup = parse(f)
        page_has = False
        for s in soup.find_all("script", type="application/ld+json"):
            page_has = True
            try:
                data = json.loads(s.string or "{}")
            except Exception:
                invalid += 1
                issues.append(f"{rel}: JSON-LD INVALIDO (Google lo ignora)")
                continue
            for node in (data if isinstance(data, list) else [data]):
                if not isinstance(node, dict):
                    continue
                graph = node.get("@graph")
                for sn in (graph if isinstance(graph, list) else [node]):
                    if isinstance(sn, dict):
                        check_node(sn, issues, recs, rel)
        if page_has:
            pages_ok += 1

    out = save_json("schema_validate.json", {
        "paginas_con_schema": pages_ok, "json_invalido": invalid,
        "issues": issues, "recomendaciones": recs})
    print(f"schema_validate: {pages_ok} páginas con schema · JSON inválido: {invalid} · "
          f"campos faltantes: {len(issues)} · recomendaciones: {len(recs)} -> {out}")
    for i in issues[:15]:
        print("  " + i)
    if not issues:
        print("  Schema válido (requeridos OK) en todas las páginas.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
