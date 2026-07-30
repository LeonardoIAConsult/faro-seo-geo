"""seo-forge — extrae comportamiento real de Google Analytics 4 (Capa 3, OAuth).

Cierra el gap "GA4": el motor sabía qué buscas (GSC) pero no qué hace la gente al llegar.
Ahora trae páginas top, canales de tráfico y engagement REALES. Gratis (API oficial GA4 Data).

Requiere:
  - credentials.json  (mismo OAuth Desktop app; habilitar "Google Analytics Data API")
  - GA4_PROPERTY_ID en .env  (id NUMÉRICO de la propiedad GA4, ej. 123456789 — NO el "G-XXXX")
    Se saca en GA → Admin → Configuración de la propiedad → ID de la propiedad.

GATED: sin GA4_PROPERTY_ID, no rompe — avisa y sale limpio (como los motores de pago).

Salidas:
  --report overview -> .tmp/ga4_overview.json  (sesiones, usuarios, engagement, conversiones)
  --report pages    -> .tmp/ga4_pages.json     (páginas más vistas + engagement)
  --report channels -> .tmp/ga4_channels.json  (de dónde llega el tráfico)
  --report all      -> los tres

Uso:
    python execution/ga4_pull.py --report all --days 28
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta

from _common import ROOT, save_json

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
_SERVICE = None


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def property_id():
    pid = os.environ.get("GA4_PROPERTY_ID", "").strip()
    return pid


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
    token_path = ROOT / os.environ.get("GA4_TOKEN", "ga4_token.json")
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not cred_path.exists():
                raise SystemExit(
                    f"No existe {cred_path}. Descarga credentials.json (OAuth Desktop app + "
                    "'Google Analytics Data API' habilitada). Ver directives/analytics_ga4.md")
            flow = InstalledAppFlow.from_client_secrets_file(str(cred_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    _SERVICE = build("analyticsdata", "v1beta", credentials=creds)
    return _SERVICE


def run_report(dimensions, metrics, days, limit=25):
    """Llama runReport de la GA4 Data API y devuelve filas normalizadas."""
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days)
    body = {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "dimensions": [{"name": d} for d in dimensions],
        "metrics": [{"name": m} for m in metrics],
        "limit": limit,
    }
    resp = service().properties().runReport(
        property=f"properties/{property_id()}", body=body).execute()
    rows = []
    for r in resp.get("rows", []):
        item = {}
        for i, d in enumerate(dimensions):
            item[d] = r["dimensionValues"][i]["value"]
        for i, m in enumerate(metrics):
            v = r["metricValues"][i]["value"]
            try:
                item[m] = round(float(v), 3)
            except ValueError:
                item[m] = v
        rows.append(item)
    return rows


def main():
    if not property_id():
        print("GA4 no configurado (sin GA4_PROPERTY_ID en .env). Se salta — no es un error.")
        return
    report = arg("--report", "all")
    days = int(arg("--days", "28"))

    if report in ("overview", "all"):
        rows = run_report([], ["sessions", "activeUsers", "screenPageViews",
                               "engagementRate", "averageSessionDuration", "keyEvents"], days, limit=1)
        out = save_json("ga4_overview.json", {"days": days, "rows": rows})
        print(f"GA4 overview ({days}d) -> {out}")
    if report in ("pages", "all"):
        rows = run_report(["pagePath"], ["screenPageViews", "engagementRate"], days)
        out = save_json("ga4_pages.json", {"days": days, "rows": rows})
        print(f"GA4 páginas top: {len(rows)} -> {out}")
    if report in ("channels", "all"):
        rows = run_report(["sessionDefaultChannelGroup"], ["sessions", "engagementRate"], days)
        out = save_json("ga4_channels.json", {"days": days, "rows": rows})
        print(f"GA4 canales: {len(rows)} -> {out}")


if __name__ == "__main__":
    main()
