#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
redirect_audit.py — audita los redirects del sitio (Vercel) por fugas SEO (R11).

Los redirects mal hechos filtran autoridad y confunden a Google:
  - falta el redirect canónico de host (apex -> www o viceversa) → contenido duplicado
  - redirects TEMPORALES (302) donde deberían ser permanentes (301) → no pasan autoridad
  - CADENAS (A→B→C) → cada salto pierde señal y velocidad
  - LOOPS (A→A) → página inaccesible

Lee {site}/vercel.json (determinista, sin red). Salida: .tmp/redirect_audit.json.

Uso:
  python execution/redirect_audit.py --site "<dir>"
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from _common import cfg, save_json, site_dir, site_url


def dest_path(destination):
    """Path del destino (sin host ni $1), para comparar con sources."""
    d = destination or ""
    if d.startswith("http"):
        d = urlparse(d).path or "/"
    return re.sub(r"\$\d+", "", d).rstrip("/") or "/"


def src_path(source):
    return re.sub(r"\(\.\*\)|\$\d+", "", source or "").rstrip("/") or "/"


def analyze(redirects, apex_host, www_url):
    findings = []
    www_host = urlparse(www_url).netloc
    # 1) redirect canónico de host (apex -> www, permanente)
    has_canonical = any(
        any(h.get("type") == "host" and h.get("value") == apex_host for h in r.get("has", []))
        and www_host in (r.get("destination") or "") and r.get("permanent")
        for r in redirects)
    if not has_canonical:
        findings.append({"sev": "HIGH", "tipo": "sin redirect canónico de host",
                         "detalle": f"falta 301 de {apex_host} → {www_host} (o no es permanent)"})
    # 2) temporales + 3) cadenas/loops
    src_paths = {src_path(r.get("source")) for r in redirects}
    for r in redirects:
        s, dest = r.get("source"), r.get("destination")
        dp = dest_path(dest)
        # ¿cambia de host? (redirect de host o destino absoluto a otro dominio) → NO es loop
        is_host_redirect = any(h.get("type") == "host" for h in r.get("has", [])) \
            or (dest or "").startswith("http")
        if not r.get("permanent"):
            findings.append({"sev": "MED", "tipo": "redirect temporal (302)",
                             "detalle": f"{s} → {dest} (usa permanent:true para pasar autoridad)"})
        if src_path(s) == dp and not is_host_redirect:
            findings.append({"sev": "HIGH", "tipo": "loop", "detalle": f"{s} → {dest}"})
        elif dp in src_paths and dp != "/" and not is_host_redirect:
            findings.append({"sev": "MED", "tipo": "cadena de redirects",
                             "detalle": f"{s} → {dp}, y {dp} también redirige (encadena)"})
    return findings, has_canonical


def main():
    site = site_dir()
    vpath = site / "vercel.json"
    if not vpath.exists():
        out = save_json("redirect_audit.json",
                        {"nota": "sin vercel.json (¿otro host? ajusta el auditor)", "findings": []})
        print(f"redirect_audit: no hay vercel.json en {site} -> {out}")
        return 0
    try:
        vjson = json.loads(vpath.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"redirect_audit: vercel.json no parsea: {e}")
        return 1
    redirects = vjson.get("redirects", [])
    apex_host = cfg("brand.domain", urlparse(site_url()).netloc.replace("www.", ""))
    findings, has_canonical = analyze(redirects, apex_host, site_url())

    out = save_json("redirect_audit.json", {
        "redirects": len(redirects), "canonico_host": has_canonical,
        "findings": findings})
    print(f"redirect_audit: {len(redirects)} redirects | canónico host: "
          f"{'✅' if has_canonical else '🔴 FALTA'} | hallazgos: {len(findings)} -> {out}")
    for f in findings:
        print(f"  {f['sev']} · {f['tipo']}: {f['detalle']}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
