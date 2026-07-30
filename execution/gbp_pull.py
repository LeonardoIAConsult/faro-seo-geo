"""seo-forge — Google Business Profile: perfil, reseñas y rendimiento (Capa 3, OAuth).

Cierra la herramienta 7 (Business Profile / Maps) para el SEO LOCAL. Trae datos REALES de la
ficha de Google: categoría, completitud del perfil, reseñas (media, sin responder) y métricas
de rendimiento (impresiones en Búsqueda/Maps, clics a la web, llamadas, cómo-llegar). Gratis
(APIs oficiales de Business Profile), gated como GSC/GA4.

⚠️ GATE DE ACCESO (importante, decir al dueño): las Business Profile APIs NO se activan solas.
Requieren, además del OAuth:
  1. Proyecto en Google Cloud con estas APIs habilitadas:
     - My Business Account Management API   (cuentas/ubicaciones)
     - My Business Business Information API  (perfil, categorías, horario)
     - Business Profile Performance API      (métricas)
     - (reseñas usan el endpoint legacy mybusiness v4, cubierto por el mismo scope)
  2. **Solicitud de acceso aprobada por Google** (formulario "Business Profile APIs"). Hasta que
     la aprueben, las llamadas devuelven 403 PERMISSION_DENIED. El script lo detecta y avisa
     claro (no rompe, no inventa).

Requiere:
  - credentials.json (mismo OAuth Desktop app; scope business.manage). token -> gbp_token.json.
  - GBP_ACCOUNT_ID + GBP_LOCATION_ID (en .env o config local.account_id/location_id).
    ¿No los sabes? Corre primero `--report accounts` (solo necesita OAuth) para descubrirlos.

Salidas:
  --report accounts     -> .tmp/gbp_accounts.json     (cuentas + ubicaciones = para sacar los IDs)
  --report profile      -> .tmp/gbp_profile.json      (categorías + completitud del perfil)
  --report reviews      -> .tmp/gbp_reviews.json      (media, distribución, sin responder)
  --report performance  -> .tmp/gbp_performance.json  (impresiones/clics/llamadas/direcciones)
  --report all          -> profile + reviews + performance

Uso:
    python execution/gbp_pull.py --report accounts
    python execution/gbp_pull.py --report all --days 30
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta

from _common import ROOT, cfg, save_json

SCOPES = ["https://www.googleapis.com/auth/business.manage"]
ACCT_API = "https://mybusinessaccountmanagement.googleapis.com/v1"
INFO_API = "https://mybusinessbusinessinformation.googleapis.com/v1"
REVIEW_API = "https://mybusiness.googleapis.com/v4"  # reseñas: solo en el legacy v4
PERF_API = "https://businessprofileperformance.googleapis.com/v1"

STAR = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
_CREDS = None


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def creds():
    """OAuth (reusa credentials.json; token propio gbp_token.json). Mismo patrón que gsc/ga4."""
    global _CREDS
    if _CREDS is not None:
        return _CREDS
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        raise SystemExit("Faltan libs: pip install google-api-python-client google-auth-oauthlib")

    cred_path = ROOT / os.environ.get("GSC_CREDENTIALS", "credentials.json")
    token_path = ROOT / os.environ.get("GBP_TOKEN", "gbp_token.json")
    c = None
    if token_path.exists():
        c = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not c or not c.valid:
        if c and c.expired and c.refresh_token:
            c.refresh(Request())
        else:
            if not cred_path.exists():
                raise SystemExit(
                    f"No existe {cred_path}. Descarga credentials.json (OAuth Desktop app) y "
                    "habilita las Business Profile APIs. Ver directives/local_seo.md")
            flow = InstalledAppFlow.from_client_secrets_file(str(cred_path), SCOPES)
            c = flow.run_local_server(port=0)
        token_path.write_text(c.to_json(), encoding="utf-8")
    _CREDS = c
    return c


def api_get(url, params=None):
    """GET con bearer. Traduce el gate de acceso (403) a un mensaje honesto en vez de stack."""
    import requests
    from google.auth.transport.requests import Request as GARequest
    c = creds()
    if not c.valid and c.refresh_token:
        c.refresh(GARequest())
    r = requests.get(url, params=params or {},
                     headers={"Authorization": f"Bearer {c.token}"}, timeout=60)
    if r.status_code == 403:
        raise SystemExit(
            "GBP: 403 PERMISSION_DENIED. Falta aprobación de acceso a las Business Profile APIs "
            "(formulario de Google) o la API no está habilitada en el proyecto. Ver el GATE DE "
            "ACCESO en directives/local_seo.md. No es un bug del código.")
    r.raise_for_status()
    return r.json()


def account_id() -> str | None:
    return os.environ.get("GBP_ACCOUNT_ID") or cfg("local.account_id")


def location_id() -> str | None:
    return os.environ.get("GBP_LOCATION_ID") or cfg("local.location_id")


# ---------------- lógica pura (testeable) ----------------
def review_summary(reviews: list[dict]) -> dict:
    """Resume reseñas: media, distribución 1-5, cuántas sin responder."""
    stars, unanswered, dist = [], 0, {i: 0 for i in range(1, 6)}
    for rv in reviews:
        n = STAR.get(rv.get("starRating", ""), 0)
        if n:
            stars.append(n)
            dist[n] += 1
        if not rv.get("reviewReply"):
            unanswered += 1
    avg = round(sum(stars) / len(stars), 2) if stars else 0
    return {"total": len(reviews), "media": avg, "sin_responder": unanswered, "distribucion": dist}


def profile_completeness(loc: dict) -> dict:
    """Checklist de completitud del perfil (más completo = mejor ranking local)."""
    checks = {
        "titulo": bool(loc.get("title")),
        "categoria_primaria": bool((loc.get("categories") or {}).get("primaryCategory")),
        "telefono": bool((loc.get("phoneNumbers") or {}).get("primaryPhone")),
        "web": bool(loc.get("websiteUri")),
        "direccion": bool(loc.get("storefrontAddress")),
        "horario": bool((loc.get("regularHours") or {}).get("periods")),
        "descripcion": bool((loc.get("profile") or {}).get("description")),
    }
    faltan = [k for k, v in checks.items() if not v]
    score = round(sum(checks.values()) / len(checks) * 100)
    return {"score": score, "checks": checks, "faltan": faltan}


def metric_totals(resp: dict) -> dict:
    """Suma cada serie diaria de fetchMultiDailyMetricsTimeSeries -> total por métrica."""
    out = {}
    for series in resp.get("multiDailyMetricTimeSeries", []):
        for m in series.get("dailyMetricTimeSeries", []):
            metric = m.get("dailyMetric", "?")
            vals = m.get("timeSeries", {}).get("datedValues", [])
            out[metric] = sum(int(v.get("value", 0) or 0) for v in vals)
    return out


# ---------------- reports ----------------
def report_accounts():
    accts = api_get(f"{ACCT_API}/accounts").get("accounts", [])
    data = {"accounts": []}
    for a in accts:
        name = a.get("name", "")  # "accounts/123"
        locs = api_get(f"{INFO_API}/{name}/locations",
                       {"readMask": "name,title,storefrontAddress"}).get("locations", [])
        data["accounts"].append({
            "account_id": name.split("/")[-1],
            "nombre": a.get("accountName", ""),
            "tipo": a.get("type", ""),
            "ubicaciones": [{"location_id": (loc.get("name") or "").split("/")[-1],
                             "titulo": loc.get("title", "")} for loc in locs],
        })
    path = save_json("gbp_accounts.json", data)
    print(f"GBP accounts -> {path}")
    for a in data["accounts"]:
        print(f"  account {a['account_id']} ({a['nombre']})")
        for loc in a["ubicaciones"]:
            print(f"    location {loc['location_id']} | {loc['titulo']}")
    print("Pon GBP_ACCOUNT_ID + GBP_LOCATION_ID en .env (o local.account_id/location_id en config).")


def report_profile():
    lid = location_id()
    loc = api_get(f"{INFO_API}/locations/{lid}", {
        "readMask": "name,title,categories,phoneNumbers,websiteUri,storefrontAddress,regularHours,profile"})
    comp = profile_completeness(loc)
    prim = (loc.get("categories") or {}).get("primaryCategory", {}).get("displayName", "?")
    out = {"location_id": lid, "titulo": loc.get("title"), "categoria": prim, **comp}
    path = save_json("gbp_profile.json", out)
    print(f"GBP profile: completitud {comp['score']}/100 · categoría '{prim}' -> {path}")
    if comp["faltan"]:
        print(f"  faltan: {', '.join(comp['faltan'])}")


def report_reviews():
    aid, lid = account_id(), location_id()
    reviews, page_token = [], None
    while True:
        params = {"pageSize": 50}
        if page_token:
            params["pageToken"] = page_token
        resp = api_get(f"{REVIEW_API}/accounts/{aid}/locations/{lid}/reviews", params)
        reviews.extend(resp.get("reviews", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    summ = review_summary(reviews)
    path = save_json("gbp_reviews.json", summ)
    print(f"GBP reviews: {summ['total']} · media {summ['media']} · {summ['sin_responder']} sin responder -> {path}")


def report_performance(days):
    lid = location_id()
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days)
    metrics = ["BUSINESS_IMPRESSIONS_DESKTOP_SEARCH", "BUSINESS_IMPRESSIONS_MOBILE_SEARCH",
               "BUSINESS_IMPRESSIONS_DESKTOP_MAPS", "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
               "WEBSITE_CLICKS", "CALL_CLICKS", "BUSINESS_DIRECTION_REQUESTS"]
    params = [("dailyMetrics", m) for m in metrics] + [
        ("dailyRange.start_date.year", start.year), ("dailyRange.start_date.month", start.month),
        ("dailyRange.start_date.day", start.day), ("dailyRange.end_date.year", end.year),
        ("dailyRange.end_date.month", end.month), ("dailyRange.end_date.day", end.day)]
    resp = api_get(f"{PERF_API}/locations/{lid}:fetchMultiDailyMetricsTimeSeries", params)
    totals = metric_totals(resp)
    out = {"dias": days, "totales": totals}
    path = save_json("gbp_performance.json", out)
    print(f"GBP performance ({days}d) -> {path}")
    for k, v in totals.items():
        print(f"  {v:>7} | {k}")


def main():
    report = arg("--report", "profile")
    days = int(arg("--days", "30"))

    if report == "accounts":
        report_accounts()
        return

    if not (account_id() and location_id()):
        print("GBP: faltan GBP_ACCOUNT_ID/GBP_LOCATION_ID (o local.account_id/location_id en config). "
              "Corre primero `--report accounts` para descubrirlos. Se salta.")
        return

    if report == "profile":
        report_profile()
    elif report == "reviews":
        report_reviews()
    elif report == "performance":
        report_performance(days)
    elif report == "all":
        report_profile()
        report_reviews()
        report_performance(days)
    else:
        raise SystemExit("--report accounts|profile|reviews|performance|all")


if __name__ == "__main__":
    main()
