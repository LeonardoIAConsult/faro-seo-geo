"""seo-forge — extrae datos reales de Google Search Console (Capa 3, OAuth).

El mejor combustible SEO: TUS keywords, posiciones, clics, impresiones, CTR reales.
Primera vez: abre navegador para autorizar (guarda token.json). Luego usa el token.

Requiere:
  - credentials.json  (OAuth client "Desktop app" de Google Cloud Console, API Search Console habilitada)
  - GSC_SITE_URL en .env  (ej. https://www.example.com/  — debe ser una propiedad verificada en GSC)

Salidas:
  --report queries   -> .tmp/gsc_queries.json   (top keywords: clics, impresiones, CTR, posición)
  --report pages     -> .tmp/gsc_pages.json     (rendimiento por página)
  --report opportunities -> .tmp/gsc_opportunities.json  (posición 5-20 = "frutos al alcance")

Uso:
    python execution/gsc_pull.py --report queries --days 90
    python execution/gsc_pull.py --report opportunities --days 90
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta

from _common import ROOT, save_json

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
_SERVICE = None  # cache del cliente (G7: evita re-autenticar en cada run())


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def service():
    global _SERVICE
    if _SERVICE is not None:
        return _SERVICE
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        raise SystemExit("Faltan libs: pip install google-api-python-client google-auth-oauthlib")

    cred_path = ROOT / os.environ.get("GSC_CREDENTIALS", "credentials.json")
    token_path = ROOT / os.environ.get("GSC_TOKEN", "token.json")
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not cred_path.exists():
                raise SystemExit(
                    f"No existe {cred_path}. Descarga credentials.json de Google Cloud Console "
                    "(OAuth Desktop app + API 'Google Search Console' habilitada). Ver directives/search_console.md")
            flow = InstalledAppFlow.from_client_secrets_file(str(cred_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    _SERVICE = build("searchconsole", "v1", credentials=creds)
    return _SERVICE


def run(dimensions, days, row_limit=1000):
    site = os.environ.get("GSC_SITE_URL")
    if not site:
        raise SystemExit("Define GSC_SITE_URL en .env (propiedad verificada en GSC).")
    end = date.today() - timedelta(days=2)  # GSC tiene ~2 días de lag
    start = end - timedelta(days=days)
    body = {"startDate": start.isoformat(), "endDate": end.isoformat(),
            "dimensions": dimensions, "rowLimit": row_limit}
    resp = service().searchanalytics().query(siteUrl=site, body=body).execute()
    rows = []
    for r in resp.get("rows", []):
        item = {dimensions[i]: r["keys"][i] for i in range(len(dimensions))}
        item.update({"clicks": r["clicks"], "impressions": r["impressions"],
                     "ctr": round(r["ctr"], 4), "position": round(r["position"], 1)})
        rows.append(item)
    return rows


def main():
    report = arg("--report", "queries")
    days = int(arg("--days", "90"))

    if report == "queries":
        rows = run(["query"], days)
        out = save_json("gsc_queries.json", {"days": days, "rows": rows})
        print(f"GSC queries: {len(rows)} keywords -> {out}")
    elif report == "pages":
        rows = run(["page"], days)
        out = save_json("gsc_pages.json", {"days": days, "rows": rows})
        print(f"GSC pages: {len(rows)} páginas -> {out}")
    elif report == "opportunities":
        rows = run(["query", "page"], days)
        opp = [r for r in rows if 5 <= r["position"] <= 20 and r["impressions"] >= 20]
        opp.sort(key=lambda r: r["impressions"], reverse=True)
        out = save_json("gsc_opportunities.json", {"days": days, "note": "posición 5-20, >=20 impresiones",
                                                    "rows": opp})
        print(f"GSC oportunidades (pos 5-20): {len(opp)} -> {out}")
        for r in opp[:10]:
            print(f"  pos {r['position']:>4} | imp {r['impressions']:>5} | {r['query']}")
    else:
        raise SystemExit("--report queries|pages|opportunities")


if __name__ == "__main__":
    main()
