"""seo-forge — Índice real de Google vía URL Inspection API (Capa 3, OAuth).

El resto del motor audita TU HTML en disco. Este script pregunta a Google qué
hace REALMENTE con cada URL: ¿la indexó, la excluyó (y por qué), no la conoce?
¿respetó tu canonical o eligió otra? Cierra el punto ciego más grande: el estado
de indexación real (el reporte de cobertura de GSC no tiene endpoint de export;
la URL Inspection API sí, 1 URL a la vez).

Reusa el OAuth de gsc_pull (scope webmasters.readonly YA cubre urlInspection).
Límites Google: 2.000 inspecciones/día · 600/min por propiedad → un sitio chico
entra de sobra. Datos que cambian lento → el informe marca la antigüedad (fresh_note).

Requiere:
  - credentials.json + token.json (los mismos de gsc_pull)
  - GSC_SITE_URL en .env = propiedad verificada (ej. sc-domain:example.com)

Salida: .tmp/index_inspect.json

Uso:
    python execution/index_inspect.py                 # inspecciona las URLs del sitemap
    python execution/index_inspect.py --max 100 --delay 0.2
    python execution/index_inspect.py --url https://www.example.com/blog/x.html
"""
from __future__ import annotations

import os
import sys
import time
import xml.etree.ElementTree as ET

import gsc_pull
from _common import save_json, site_dir


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def classify(coverage: str, verdict: str) -> tuple[str, str]:
    """Pura (testeable). Devuelve (bucket, motivo). bucket ∈ indexed|excluded|unknown.
    'indexed' = Google la tiene en el índice; 'excluded' = la conoce pero NO la indexa
    (con motivo accionable); 'unknown' = aún no la descubrió."""
    c = (coverage or "").lower()
    if "unknown to google" in c:
        return ("unknown", coverage or "URL desconocida para Google")
    if verdict == "PASS" or "submitted and indexed" in c or c.strip() == "indexed":
        return ("indexed", coverage or "Indexada")
    return ("excluded", coverage or "sin estado de cobertura")


def canonical_conflict(google_canonical: str, user_canonical: str) -> bool:
    """Pura (testeable). True si Google eligió una canónica DISTINTA a la que declaraste
    (fuga real: tu <link canonical> se ignora). Compara sin barra final."""
    g = (google_canonical or "").rstrip("/")
    u = (user_canonical or "").rstrip("/")
    return bool(g and u and g != u)


def sitemap_urls(root, limit: int) -> list[str]:
    """URLs del sitemap.xml del sitio (las páginas que QUEREMOS indexadas)."""
    sm = root / "sitemap.xml"
    if not sm.exists():
        return []
    try:
        tree = ET.parse(sm)
    except ET.ParseError:
        return []
    locs = []
    for el in tree.iter():
        if el.tag.endswith("loc") and el.text:
            locs.append(el.text.strip())
    return locs[:limit] if limit else locs


def inspect(svc, site, url):
    """Una inspección. Devuelve dict normalizado o {'error': ...} (quota/permiso)."""
    try:
        r = svc.urlInspection().index().inspect(
            body={"inspectionUrl": url, "siteUrl": site}).execute()
    except Exception as e:  # quota, permiso, 5xx → no rompe el lote
        return {"url": url, "error": str(e)[:160]}
    idx = r.get("inspectionResult", {}).get("indexStatusResult", {})
    verdict = idx.get("verdict", "")
    coverage = idx.get("coverageState", "")
    bucket, motivo = classify(coverage, verdict)
    return {
        "url": url,
        "bucket": bucket,
        "motivo": motivo,
        "verdict": verdict,
        "google_canonical": idx.get("googleCanonical"),
        "user_canonical": idx.get("userCanonical"),
        "canonical_conflict": canonical_conflict(
            idx.get("googleCanonical"), idx.get("userCanonical")),
        "last_crawl": idx.get("lastCrawlTime"),
        "robots": idx.get("robotsTxtState"),
        "fetch": idx.get("pageFetchState"),
    }


def summarize(rows: list[dict]) -> dict:
    ok = [r for r in rows if "error" not in r]
    err = [r for r in rows if "error" in r]
    buckets = {"indexed": 0, "excluded": 0, "unknown": 0}
    for r in ok:
        buckets[r["bucket"]] = buckets.get(r["bucket"], 0) + 1
    excluded = [r for r in ok if r["bucket"] == "excluded"]
    unknown = [r for r in ok if r["bucket"] == "unknown"]
    conflicts = [r for r in ok if r.get("canonical_conflict")]
    return {
        "total": len(rows),
        "buckets": buckets,
        "errores": len(err),
        "excluidas": excluded,
        "desconocidas": unknown,
        "conflictos_canonical": conflicts,
        "rows": rows,
    }


def main():
    site = os.environ.get("GSC_SITE_URL")
    if not site:
        raise SystemExit("Define GSC_SITE_URL en .env (propiedad verificada en GSC).")
    svc = gsc_pull.service()

    one = arg("--url")
    delay = float(arg("--delay", "0.2"))
    if one:
        urls = [one]
    else:
        limit = int(arg("--max", "300"))
        urls = sitemap_urls(site_dir(), limit)
        if not urls:
            raise SystemExit(f"No hay sitemap.xml en {site_dir()} (o vacío). Pasa --url o genera el sitemap.")

    rows = []
    for i, u in enumerate(urls, 1):
        rows.append(inspect(svc, site, u))
        if i < len(urls):
            time.sleep(delay)

    data = summarize(rows)
    out = save_json("index_inspect.json", data)
    b = data["buckets"]
    print(f"index_inspect: {data['total']} URLs | indexadas={b['indexed']} "
          f"excluidas={b['excluded']} desconocidas={b['unknown']} "
          f"conflictos_canonical={len(data['conflictos_canonical'])} errores={data['errores']} -> {out}")
    for r in data["excluidas"][:10]:
        print(f"  ✗ {r['url']} — {r['motivo']}")
    for r in data["conflictos_canonical"][:6]:
        print(f"  ⚠ canonical: {r['url']} → Google usa {r['google_canonical']}")


if __name__ == "__main__":
    main()
