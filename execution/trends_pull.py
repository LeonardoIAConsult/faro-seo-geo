"""seo-forge — tendencias de búsqueda del nicho (Capa 3, Google Trends vía pytrends).

Cierra el gap "Trends": señal de estacionalidad + consultas que SUBEN, para alimentar el
content brief (escribir sobre lo que la gente empieza a buscar, no lo de siempre).

⚠️ HONESTIDAD: Google Trends NO tiene API oficial. pytrends hace scraping → puede fallar o
ser rate-limited (429). Es best-effort: si no responde, se salta sin romper. Gratis, sin key.

Entradas:
  - keywords: de --kw "a,b,c", o de config geo.queries, o (si no hay) top de gsc_queries.json
  - geo: config geo.trends_geo (ej. "CO" Colombia; "" = mundial) · hl: geo.trends_hl (def "es")

Salida:
  .tmp/trends.json  -> por keyword: interés reciente vs previo (dirección) + related "rising"

Uso:
    python execution/trends_pull.py --kw "ia para pymes,automatizar negocio" --timeframe "today 12-m"
"""
from __future__ import annotations

import json
import sys

from _common import ROOT, cfg, save_json


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def keywords():
    kw = arg("--kw")
    if kw:
        return [k.strip() for k in kw.split(",") if k.strip()]
    q = cfg("geo.queries", [])
    if q:
        return [str(x) for x in q][:15]
    # fallback: top keywords reales de GSC si existen
    f = ROOT / ".tmp" / "gsc_queries.json"
    gsc = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    return [r["query"] for r in gsc.get("rows", [])[:10]]


def direction(series):
    """Compara la 2a mitad vs la 1a mitad del interés -> sube/baja/estable + %."""
    if len(series) < 4:
        return "sin datos", 0
    mid = len(series) // 2
    a = sum(series[:mid]) / max(mid, 1)
    b = sum(series[mid:]) / max(len(series) - mid, 1)
    if a == 0:
        return ("sube" if b > 0 else "sin datos"), 0
    chg = round((b - a) / a * 100, 1)
    label = "sube" if chg >= 15 else "baja" if chg <= -15 else "estable"
    return label, chg


def main():
    kws = keywords()
    if not kws:
        print("Trends: no hay keywords (define geo.queries o pasa --kw). Se salta.")
        return
    try:
        from pytrends.request import TrendReq
    except ImportError:
        print("Trends: falta pytrends (pip install pytrends). Se salta — no es un error.")
        return

    geo = cfg("geo.trends_geo", "")
    hl = cfg("geo.trends_hl", "es")
    timeframe = arg("--timeframe", "today 12-m")
    out = {"geo": geo or "mundial", "timeframe": timeframe, "keywords": []}

    try:
        pt = TrendReq(hl=hl, tz=300)
        # pytrends: máximo 5 keywords por payload
        for i in range(0, len(kws), 5):
            batch = kws[i:i + 5]
            pt.build_payload(batch, timeframe=timeframe, geo=geo)
            iot = pt.interest_over_time()
            rq = pt.related_queries()
            for k in batch:
                entry = {"keyword": k, "tendencia": "sin datos", "cambio_pct": 0, "rising": []}
                if iot is not None and not iot.empty and k in iot.columns:
                    series = [int(x) for x in iot[k].tolist()]
                    lab, chg = direction(series)
                    entry["tendencia"] = lab
                    entry["cambio_pct"] = chg
                    entry["interes_reciente"] = series[-1] if series else 0
                rk = (rq.get(k) or {}).get("rising")
                if rk is not None and not rk.empty:
                    entry["rising"] = rk.head(5)["query"].tolist()
                out["keywords"].append(entry)
    except Exception as e:  # noqa: BLE001 - pytrends no-oficial: cualquier fallo = degradar, no romper
        print(f"Trends: no pude consultar (Google Trends no tiene API oficial; puede rate-limitar). {type(e).__name__}. Se salta.")
        if not out["keywords"]:
            return

    path = save_json("trends.json", out)
    print(f"Trends: {len(out['keywords'])} keywords (geo {out['geo']}) -> {path}")
    for e in out["keywords"][:10]:
        r = (" · rising: " + ", ".join(e["rising"][:3])) if e["rising"] else ""
        print(f"  {e['tendencia']:>7} ({e['cambio_pct']:+}%) | {e['keyword']}{r}")


if __name__ == "__main__":
    main()
