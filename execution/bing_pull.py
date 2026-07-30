"""seo-forge — datos de Bing Webmaster Tools (Capa 3, API key).

2º buscador + señal GEO: Bing alimenta ChatGPT Search y Copilot, así que aparecer
en Bing = presencia en esas IAs. Además da datos que GSC no expone: recuento de
enlaces entrantes (backlinks) por página, GRATIS.

Motor GRATIS con GATE: requiere `BING_API_KEY` (Bing Webmaster Tools → Settings →
API access → generar key) + el sitio verificado en Bing WMT (se puede importar 1-clic
desde GSC). Sin key → se salta (no rompe), como los motores de pago.

API JSON: https://ssl.bing.com/webmaster/api.svc/json/{METHOD}?apikey=KEY&siteUrl=URL
Respuesta envuelta en {"d": ...}; las fechas vienen como "/Date(ms)/".

Salidas:
  --report traffic  -> .tmp/bing_traffic.json   (impresiones/clics en Bing)
  --report queries  -> .tmp/bing_queries.json   (keywords reales en Bing + posición)
  --report links    -> .tmp/bing_links.json     (enlaces entrantes por página)
  --report sites    -> valida la key y lista sitios verificados (para descubrir el siteUrl)

Uso:
    python execution/bing_pull.py --report traffic
    python execution/bing_pull.py --report queries
"""
from __future__ import annotations

import os
import re
import sys

import requests
from _common import cfg, save_json, site_url

BASE = "https://ssl.bing.com/webmaster/api.svc/json"
_DATE = re.compile(r"/Date\((\d+)")


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def parse_ms_date(val) -> str | None:
    """Pura (testeable). '/Date(1690000000000)/' o '/Date(1690000000000-0700)/' -> 'YYYY-MM-DD'.
    Devuelve None si no matchea (no revienta ante formatos raros de Bing)."""
    if not isinstance(val, str):
        return None
    m = _DATE.search(val)
    if not m:
        return None
    from datetime import datetime, timezone
    return datetime.fromtimestamp(int(m.group(1)) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def summarize_traffic(rows: list[dict]) -> dict:
    """Pura (testeable). Suma impresiones/clics de GetRankAndTrafficStats."""
    imp = sum(int(r.get("Impressions", 0) or 0) for r in rows)
    clk = sum(int(r.get("Clicks", 0) or 0) for r in rows)
    ctr = round(clk / imp, 4) if imp else 0.0
    return {"dias": len(rows), "impresiones": imp, "clics": clk, "ctr": ctr}


def top_queries(rows: list[dict], n: int = 20) -> list[dict]:
    """Pura (testeable). Ordena queries por impresiones desc y normaliza campos."""
    out = []
    for r in rows:
        out.append({
            "query": r.get("Query"),
            "impresiones": int(r.get("Impressions", 0) or 0),
            "clics": int(r.get("Clicks", 0) or 0),
            "pos_impresion": r.get("AvgImpressionPosition"),
            "pos_clic": r.get("AvgClickPosition"),
        })
    out.sort(key=lambda x: -x["impresiones"])
    return out[:n]


def normalize_links(d) -> list[dict]:
    """Pura (testeable). GetLinkCounts devuelve {"Links":[{Url,Count},...]} (shape varía,
    best-effort). Normaliza a [{"url","count"}] ordenado por count desc."""
    links = d.get("Links", d) if isinstance(d, dict) else d
    norm = [{"url": x.get("Url"), "count": int(x.get("Count") or 0)}
            for x in links] if isinstance(links, list) else []
    norm.sort(key=lambda x: -(x["count"] or 0))
    return norm


def bing_site() -> str:
    """siteUrl verificado en Bing. Override BING_SITE_URL; si no, el del sitio."""
    return os.environ.get("BING_SITE_URL") or site_url()


def api_get(method: str, key: str, **params):
    """Una llamada JSON. Devuelve el payload de 'd' o lanza con mensaje claro."""
    params["apikey"] = key
    r = requests.get(f"{BASE}/{method}", params=params, timeout=60)
    if r.status_code != 200:
        raise SystemExit(f"Bing {method} HTTP {r.status_code}: {r.text[:200]}")
    try:
        return r.json().get("d")
    except ValueError:
        raise SystemExit(f"Bing {method}: respuesta no-JSON ({r.text[:120]})")


def main():
    key = os.environ.get("BING_API_KEY") or cfg("bing.api_key")
    if not key:
        print("bing_pull: sin BING_API_KEY (Bing WMT → Settings → API access). Se salta.")
        return
    report = arg("--report", "traffic")
    site = bing_site()

    if report == "sites":
        d = api_get("GetUserSites", key)
        sites = [s.get("Url") for s in (d or [])]
        print(f"bing_pull: sitios verificados = {sites}")
        save_json("bing_sites.json", {"sites": sites})
        return

    if report == "traffic":
        d = api_get("GetRankAndTrafficStats", key, siteUrl=site) or []
        rows = [{"fecha": parse_ms_date(r.get("Date")), "Impressions": r.get("Impressions"),
                 "Clicks": r.get("Clicks")} for r in d]
        data = {"site": site, "resumen": summarize_traffic(d), "rows": rows}
        out = save_json("bing_traffic.json", data)
        s = data["resumen"]
        print(f"bing_pull traffic: {s['dias']} días · impresiones={s['impresiones']} "
              f"clics={s['clics']} ctr={s['ctr']} -> {out}")
        return

    if report == "queries":
        d = api_get("GetQueryStats", key, siteUrl=site) or []
        top = top_queries(d)
        out = save_json("bing_queries.json", {"site": site, "queries": top})
        print(f"bing_pull queries: {len(top)} keywords (top por impresiones) -> {out}")
        for q in top[:8]:
            print(f"  {q['impresiones']:>5} imp · {q['clics']:>3} clk · pos {q['pos_impresion']} · {q['query']}")
        return

    if report == "links":
        d = api_get("GetLinkCounts", key, siteUrl=site, page=0) or {}
        norm = normalize_links(d)
        out = save_json("bing_links.json", {"site": site, "total_paginas": len(norm), "links": norm})
        print(f"bing_pull links: {len(norm)} páginas con enlaces entrantes -> {out}")
        return

    raise SystemExit(f"--report desconocido: {report} (traffic|queries|links|sites)")


if __name__ == "__main__":
    main()
