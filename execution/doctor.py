"""seo-forge — doctor: diagnóstico de conexiones (Capa 3, onboarding GAP2).

Responde UNA pregunta: ¿qué fuentes de datos están conectadas y qué falta para conectar
las que no? Es la base del onboarding — un usuario nuevo corre esto y ve, por fuente,
🟢 conectado / 🟡 parcial / 🔴 falta, con el siguiente paso concreto (y su directiva).

Determinista y HONESTO: por defecto solo mira presencia local (archivos de credenciales,
tokens, keys en .env, IDs en config) — NO llama a la red. Con `--probe` hace la llamada
real mínima a cada API para confirmar que el token sirve de verdad (no solo que existe).

Fuentes cubiertas:
  - gsc            Google Search Console (propiedad web/dominio)  — OAuth
  - gsc_platform   Platform properties sociales (IG/TikTok/X/YT en Search+Discover) — jul-2026
  - ga4            Google Analytics 4                              — OAuth
  - youtube        YouTube Data API                                — API key
  - gbp            Google Business Profile (SEO local)             — OAuth + aprobación Google
  - bing           Bing Webmaster (2º buscador + GEO)              — API key
  - pagespeed      PageSpeed Insights / Core Web Vitals            — API key (opcional)

Uso:
    python execution/doctor.py                # chequeo offline (rápido, sin red)
    python execution/doctor.py --probe        # además valida los tokens contra la API
    python execution/doctor.py --json         # salida máquina (para el wizard / report)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from _common import ROOT, cfg, save_json

# ── Especificación declarativa de cada fuente ────────────────────────────────
# requires: lista de (tipo, nombre, pista). tipo ∈ {file, env, cfg}
#   file → nombre es una env var que apunta a un archivo (con default); se chequea que exista
#   env  → nombre es una env var que debe tener valor no vacío
#   cfg  → nombre es una ruta de faro.config.json que debe existir
# Un item puede ser opcional (opt=True) → su ausencia baja a 🟡, no a 🔴.
SOURCES = [
    {
        "key": "gsc", "label": "Google Search Console (web)", "directive": "search_console.md",
        "fix_cmd": "python execution/gsc_pull.py --report queries   # abre el navegador para autorizar",
        "requires": [
            ("file", "GSC_CREDENTIALS", "credentials.json", "Descarga OAuth Desktop de Google Cloud Console (API Search Console habilitada)."),
            ("file", "GSC_TOKEN", "token.json", "Se genera al correr gsc_pull la 1ª vez (autoriza en el navegador)."),
            ("env", "GSC_SITE_URL", "", "URL de la propiedad verificada, ej. sc-domain:tudominio.com"),
        ],
    },
    {
        "key": "gsc_platform", "label": "Platform properties (social→Search)", "directive": "search_console.md",
        "fix_cmd": "Activa cada red en https://search.google.com/search-console/welcome, luego: python execution/doctor.py --probe",
        "requires": [
            ("file", "GSC_CREDENTIALS", "credentials.json", "Mismo OAuth que GSC."),
            ("file", "GSC_TOKEN", "token.json", "Comparte token con GSC (mismo scope webmasters.readonly)."),
        ],
        "note": "Activa cada red en search.google.com/search-console/welcome (IG/TikTok/X/YT). "
                "El acceso por API aún no está documentado — usa --probe para confirmar si responde.",
    },
    {
        "key": "ga4", "label": "Google Analytics 4", "directive": "analytics_ga4.md",
        "fix_cmd": "Pon GA4_PROPERTY_ID (numérico) en .env, luego: python execution/ga4_pull.py --report overview",
        "requires": [
            ("file", "GSC_CREDENTIALS", "credentials.json", "Mismo OAuth Desktop (habilitar Google Analytics Data API)."),
            ("file", "GA4_TOKEN", "ga4_token.json", "Se genera al correr ga4_pull la 1ª vez."),
            ("env", "GA4_PROPERTY_ID", "", "ID NUMÉRICO de la propiedad (GA → Admin → Config), NO el G-XXXX."),
        ],
    },
    {
        "key": "youtube", "label": "YouTube Data API", "directive": "youtube_audit.md",
        "fix_cmd": "Pon YT_API_KEY en .env (Cloud Console → YouTube Data API v3) + youtube.channel_id en config.",
        "requires": [
            ("env", "YT_API_KEY", "", "API key de Google Cloud (YouTube Data API v3 habilitada)."),
            ("cfg", "youtube.channel_id", "", "Canal a auditar (config youtube.channel_id o env YT_CHANNEL_ID)."),
        ],
    },
    {
        "key": "gbp", "label": "Google Business Profile (SEO local)", "directive": "local_seo.md",
        "fix_cmd": "python execution/gbp_pull.py --report accounts   # descubre IDs (requiere aprobación de Google)",
        "requires": [
            ("file", "GSC_CREDENTIALS", "credentials.json", "Mismo OAuth (scope business.manage)."),
            ("file", "GBP_TOKEN", "gbp_token.json", "Se genera al correr gbp_pull --report accounts."),
            ("env", "GBP_LOCATION_ID", "", "ID de la ficha (descúbrelo con gbp_pull --report accounts).", True),
        ],
        "note": "Además del OAuth, Google debe APROBAR el acceso a las Business Profile APIs (403 hasta aprobar).",
    },
    {
        "key": "bing", "label": "Bing Webmaster (2º buscador + GEO)", "directive": "bing_webmaster.md",
        "fix_cmd": "Pon BING_API_KEY en .env (Bing Webmaster Tools → Settings → API access).",
        "requires": [
            ("env", "BING_API_KEY", "", "Bing Webmaster Tools → Settings → API access (importa el sitio 1-clic desde GSC)."),
        ],
    },
    {
        "key": "pagespeed", "label": "PageSpeed / Core Web Vitals", "directive": "core_web_vitals.md",
        "requires": [
            ("env", "PAGESPEED_API_KEY", "", "Opcional: sin key funciona pero con rate limit más bajo.", True),
        ],
    },
]


# ── Núcleo puro (testeable, sin red) ─────────────────────────────────────────
def _file_ok(env_name: str, default_name: str, root: Path, env: dict) -> bool:
    """El archivo apuntado por env var (o su default) existe en root."""
    name = (env.get(env_name) or default_name) or default_name
    if not name:
        return False
    p = Path(name)
    if not p.is_absolute():
        p = root / p
    return p.exists()


def _present(item, env: dict, root: Path) -> bool:
    typ, name, default = item[0], item[1], item[2]
    if typ == "file":
        return _file_ok(name, default, root, env)
    if typ == "env":
        # YT_CHANNEL_ID también puede venir por env; para cfg lo maneja el caller
        return bool((env.get(name) or "").strip())
    if typ == "cfg":
        val = cfg(name)
        if val:
            return True
        # fallback env para casos con doble fuente (youtube.channel_id ↔ YT_CHANNEL_ID)
        alt = "YT_CHANNEL_ID" if name == "youtube.channel_id" else None
        return bool(alt and (env.get(alt) or "").strip())
    return False


def evaluate_source(spec: dict, env: dict, root: Path) -> dict:
    """Devuelve el estado de UNA fuente: status + qué falta. Puro (sin red)."""
    missing_req, missing_opt = [], []
    for item in spec["requires"]:
        opt = len(item) > 4 and item[4] is True
        if not _present(item, env, root):
            (missing_opt if opt else missing_req).append({
                "name": item[1], "hint": item[3] if len(item) > 3 else "",
            })
    if not missing_req and not missing_opt:
        status = "green"
    elif missing_req and len(missing_req) == len([i for i in spec["requires"] if not (len(i) > 4 and i[4] is True)]):
        status = "red"  # falta TODO lo requerido
    else:
        status = "yellow"  # parcial (falta algo requerido u opcional)
    return {
        "key": spec["key"], "label": spec["label"], "status": status,
        "directive": spec["directive"], "note": spec.get("note", ""),
        "missing": missing_req + missing_opt,
    }


def summarize(results: list[dict]) -> dict:
    counts = {"green": 0, "yellow": 0, "red": 0}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return counts


def next_action(results: list[dict], specs: list[dict]) -> dict | None:
    """La UNA cosa a hacer ahora: primera fuente NO conectada, por prioridad (orden de specs).
    Devuelve None si todo está 🟢. Guía activa del onboarding (modo --next)."""
    fix_by_key = {s["key"]: s.get("fix_cmd", "") for s in specs}
    order = {s["key"]: i for i, s in enumerate(specs)}
    pend = [r for r in results if r["status"] != "green"]
    if not pend:
        return None
    # rojo antes que amarillo; dentro del mismo estado, por prioridad de spec
    pend.sort(key=lambda r: (0 if r["status"] == "red" else 1, order.get(r["key"], 99)))
    top = pend[0]
    return {
        "label": top["label"], "status": top["status"],
        "missing": top["missing"], "fix_cmd": fix_by_key.get(top["key"], ""),
        "directive": top["directive"],
    }


# ── Probe opcional (SÍ toca red; best-effort, nunca rompe el diagnóstico) ─────
def probe_gsc(root: Path) -> dict:
    """Lista las propiedades verificadas y las clasifica web/dominio/plataforma."""
    try:
        sys.path.insert(0, str(root / "execution"))
        import gsc_pull  # reusa el OAuth cacheado
        svc = gsc_pull.service()
        sites = svc.sites().list().execute().get("siteEntry", [])
        classified = {"web": [], "domain": [], "platform": []}
        for s in sites:
            url = s.get("siteUrl", "")
            classified[classify_property(url)].append(url)
        return {"ok": True, "properties": classified, "count": len(sites)}
    except Exception as e:  # noqa: BLE001 — probe nunca debe romper el doctor
        return {"ok": False, "error": type(e).__name__ + ": " + str(e)[:200]}


def classify_property(site_url: str) -> str:
    """web | domain | platform. Las platform properties NO usan el esquema http/sc-domain."""
    u = (site_url or "").lower()
    if u.startswith("sc-domain:"):
        return "domain"
    if u.startswith("http://") or u.startswith("https://"):
        return "web"
    return "platform"


# ── Presentación ─────────────────────────────────────────────────────────────
ICON = {"green": "🟢", "yellow": "🟡", "red": "🔴"}


def render(results: list[dict], probe: dict | None) -> str:
    out = ["# seo-forge doctor — estado de conexiones\n"]
    counts = summarize(results)
    out.append(f"**{counts['green']} conectadas · {counts['yellow']} parciales · {counts['red']} sin conectar**\n")
    for r in results:
        out.append(f"## {ICON[r['status']]} {r['label']}")
        if r["status"] == "green":
            out.append("Conectada.")
        else:
            for m in r["missing"]:
                out.append(f"- Falta **{m['name']}** — {m['hint']}")
        if r["note"]:
            out.append(f"> {r['note']}")
        out.append(f"_Directiva: `directives/{r['directive']}`_\n")
    if probe is not None:
        out.append("## 🔎 Probe (API en vivo)")
        p = probe.get("gsc", {})
        if p.get("ok"):
            c = p["properties"]
            out.append(f"Propiedades verificadas en GSC: {p['count']} "
                       f"(web {len(c['web'])} · dominio {len(c['domain'])} · plataforma {len(c['platform'])}).")
            if c["platform"]:
                out.append("Platform properties detectadas por API: " + ", ".join(c["platform"]))
            else:
                out.append("⚠️ La API v1 clásica NO listó platform properties "
                           "(activadas en la UI pero sin exposición por API confirmada — ver Fase 2).")
        else:
            out.append(f"⚠️ No se pudo consultar GSC: {p.get('error', 'desconocido')}")
    return "\n".join(out)


def main():
    argv = sys.argv[1:]
    root = ROOT
    results = [evaluate_source(s, os.environ, root) for s in SOURCES]
    probe = None
    if "--probe" in argv:
        probe = {"gsc": probe_gsc(root)}
    if "--next" in argv:
        nxt = next_action(results, SOURCES)
        if nxt is None:
            print("🟢 Todo conectado. Nada pendiente.")
        else:
            print(f"➡️  Siguiente: conectar **{nxt['label']}** ({ICON[nxt['status']]})")
            for m in nxt["missing"]:
                print(f"   • Falta {m['name']} — {m['hint']}")
            if nxt["fix_cmd"]:
                print(f"   Comando: {nxt['fix_cmd']}")
            print(f"   Directiva: directives/{nxt['directive']}")
        return
    if "--json" in argv:
        payload = {"sources": results, "summary": summarize(results), "probe": probe}
        out = save_json("doctor.json", payload)
        print(f"doctor -> {out}")
    else:
        print(render(results, probe))


if __name__ == "__main__":
    main()
