"""seo-forge — Core Web Vitals vía PageSpeed Insights API (Capa 3, requiere red).

Consulta la API gratis de Google (datos de campo CrUX + lab Lighthouse) para LCP, INP,
CLS + score de performance. Sin API key funciona con límite bajo; con PAGESPEED_API_KEY
sube a 25.000/día.
Salida: .tmp/cwv.json
Uso:
    python execution/core_web_vitals.py                 # usa SEO_SITE_URL (home)
    python execution/core_web_vitals.py --url https://... --strategy mobile
"""
from __future__ import annotations

import os
import sys

import requests
from _common import save_json, site_url

API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def query(url: str, strategy: str):
    params = {"url": url, "strategy": strategy, "category": "performance"}
    key = os.environ.get("PAGESPEED_API_KEY")
    if key:
        params["key"] = key
    r = requests.get(API, params=params, timeout=60)
    r.raise_for_status()
    j = r.json()

    lh = j.get("lighthouseResult", {})
    score = (lh.get("categories", {}).get("performance", {}) or {}).get("score")
    audits = lh.get("audits", {})

    def lab(metric):
        return (audits.get(metric, {}) or {}).get("displayValue")

    field = j.get("loadingExperience", {}).get("metrics", {})

    def crux(metric):
        m = field.get(metric, {})
        return {"p75": m.get("percentile"), "category": m.get("category")}

    return {
        "url": url, "strategy": strategy,
        "performance_score": round(score * 100) if score is not None else None,
        "lab": {
            "LCP": lab("largest-contentful-paint"),
            "CLS": lab("cumulative-layout-shift"),
            "TBT": lab("total-blocking-time"),
            "FCP": lab("first-contentful-paint"),
            "SI": lab("speed-index"),
        },
        "field_crux": {
            "LCP": crux("LARGEST_CONTENTFUL_PAINT_MS"),
            "INP": crux("INTERACTION_TO_NEXT_PAINT"),
            "CLS": crux("CUMULATIVE_LAYOUT_SHIFT_SCORE"),
        },
    }


def main():
    url = arg("--url", site_url() + "/")
    strategy = arg("--strategy", "mobile")
    try:
        res = query(url, strategy)
    except requests.HTTPError as e:
        raise SystemExit(f"PageSpeed HTTP {e.response.status_code}: {e.response.text[:200]}")
    except requests.exceptions.SSLError:
        raise SystemExit("SSL error: Norton intercepta TLS. Asegura pip-system-certs instalado en el venv.")
    out = save_json("cwv.json", res)
    print(f"CWV {strategy} {url}: score={res['performance_score']} "
          f"LCP={res['lab']['LCP']} CLS={res['lab']['CLS']} INP(campo)={res['field_crux']['INP']} -> {out}")


if __name__ == "__main__":
    main()
