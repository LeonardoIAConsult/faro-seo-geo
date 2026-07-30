#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
functional_audit.py — audita que la web FUNCIONE (no solo que se vea en SEO).

El hueco que costó un form roto: seo-forge auditaba descubrimiento (SEO/GEO) pero no
funcionalidad/conversión. Este script verifica lo que de verdad rompe el negocio:
  1. FORMULARIOS: cada <form action> externo (Apps Script, etc.) responde y NO da
     Access Denied / 404 (un form roto pierde el 100% de los leads).
  2. ENLACES INTERNOS rotos: cada <a href> interno apunta a un archivo que existe.
  3. ASSETS faltantes: cada <script src> / <link href> / <img src> local existe.
  4. CTAs vacíos: enlaces de CTA sin destino real (href="#", vacío).

Usa html_files + bs4 de _common (misma política de archivos que el resto de auditores;
antes tenía glob+regex propios y auditaba proyectos/ que el resto excluye -> falsos positivos).
Los endpoints de forms se chequean por red (best-effort). Salida: .tmp/functional_audit.json.

Uso:
  python execution/functional_audit.py --site "<dir>" [--no-net]
"""
from __future__ import annotations

import os
import sys

from _common import html_files, parse, save_json, site_dir


def is_external(u):
    return u.startswith(("http://", "https://", "//"))


def skip(u):
    if (not u) or u.startswith(("mailto:", "tel:", "javascript:", "data:", "#")):
        return True
    if "{{" in u or "}}" in u:        # merge tags de plantillas (se rellenan al enviar)
        return True
    if u.startswith("/_vercel/"):      # assets inyectados por Vercel en runtime
        return True
    return False


def resolve_local(site, html_path, url):
    """Mapea un href/src relativo a un archivo local. Devuelve la ruta o None si no aplica."""
    u = url.split("#")[0].split("?")[0].strip()
    if not u:
        return None
    base = os.path.dirname(str(html_path))
    if u.startswith("/"):
        target = os.path.join(str(site), u.lstrip("/"))
    else:
        target = os.path.normpath(os.path.join(base, u))
    if u.endswith("/") or os.path.isdir(target):
        target = os.path.join(target, "index.html")
    return target


def check_endpoint(url):
    """GET best-effort a un endpoint de form. Devuelve (ok, detalle)."""
    try:
        import requests
        r = requests.get(url, timeout=20, allow_redirects=True)
        body = (r.text or "")[:2000].lower()
        if "you need access" in body or "access denied" in body or "request access" in body:
            return False, f"Access Denied (deployment no público) [{r.status_code}]"
        if r.status_code >= 400 and r.status_code != 405:
            return False, f"HTTP {r.status_code}"
        return True, f"OK [{r.status_code}]"
    except Exception as e:
        return None, f"no verificable por red: {e}"


def main():
    no_net = "--no-net" in sys.argv
    site = site_dir()
    findings = []
    broken_links, missing_assets, empty_ctas = set(), set(), set()
    form_endpoints = {}

    for f in html_files(site):
        soup = parse(f)
        rel = os.path.relpath(str(f), str(site)).replace("\\", "/")
        # enlaces internos
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if skip(href) or is_external(href):
                continue
            tgt = resolve_local(site, f, href)
            if tgt and not os.path.isfile(tgt):
                broken_links.add((rel, href))
        # assets locales (script/link/img)
        for tag in soup.find_all(["script", "link", "img"]):
            src = tag.get("src") or tag.get("href")
            if not src or skip(src) or is_external(src):
                continue
            tgt = resolve_local(site, f, src)
            if tgt and not os.path.isfile(tgt):
                missing_assets.add((rel, src))
        # CTAs vacíos (clase que contiene "cta")
        for a in soup.find_all("a"):
            classes = " ".join(a.get("class") or [])
            if "cta" in classes.lower():
                href = (a.get("href") or "").strip()
                if href in ("", "#"):
                    empty_ctas.add((rel, "CTA sin destino"))
        # forms
        for form in soup.find_all("form", action=True):
            form_endpoints.setdefault(form["action"], []).append(rel)

    # chequeo de endpoints de forms (red)
    form_results = []
    for ep, pages in form_endpoints.items():
        if is_external(ep) and not no_net:
            ok, detail = check_endpoint(ep)
        else:
            ok, detail = (None, "endpoint local/relativo (revisar backend)")
        form_results.append({"endpoint": ep, "pages": pages, "ok": ok, "detail": detail})
        if ok is False:
            findings.append({"sev": "HIGH", "tipo": "form roto",
                             "detalle": f"{ep} — {detail} (en {', '.join(pages)})"})

    for rel, href in sorted(broken_links):
        findings.append({"sev": "HIGH", "tipo": "enlace interno roto", "detalle": f"{rel} -> {href}"})
    for rel, src in sorted(missing_assets):
        findings.append({"sev": "HIGH", "tipo": "asset faltante", "detalle": f"{rel} -> {src}"})
    for rel, _ in sorted(empty_ctas):
        findings.append({"sev": "MED", "tipo": "CTA sin destino", "detalle": rel})

    out = save_json("functional_audit.json", {
        "forms": form_results, "findings": findings,
        "resumen": {"forms": len(form_endpoints), "enlaces_rotos": len(broken_links),
                    "assets_faltantes": len(missing_assets), "ctas_vacios": len(empty_ctas)}})

    print(f"functional_audit: forms={len(form_endpoints)} enlaces_rotos={len(broken_links)} "
          f"assets_faltantes={len(missing_assets)} ctas_vacios={len(empty_ctas)} -> {out}")
    print("=== FORMS ===")
    for fr in form_results:
        flag = {True: "OK", False: "ROTO", None: "?"}[fr["ok"]]
        print(f"  [{flag}] {fr['endpoint'][:60]} — {fr['detail']}")
    for cat, items in [("ENLACES ROTOS", broken_links), ("ASSETS FALTANTES", missing_assets)]:
        if items:
            print(f"=== {cat} ({len(items)}) ===")
            for rel, u in sorted(items)[:15]:
                print(f"  {rel} -> {u}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
