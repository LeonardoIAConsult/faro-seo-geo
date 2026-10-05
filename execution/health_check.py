#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
health_check.py — verificación MAESTRA de salud SEO/GEO + alarma de regresión.

Las rutinas semanales (rank/backlink/geo/youtube) rastrean MOVIMIENTO, pero nada
vigilaba la SALUD ni AVISABA si algo se degrada. Este es el watchdog que faltaba
para que el SEO/GEO esté "siempre de punta": corre el chequeo maestro (report_build →
report_score actualiza report-history.json), compara vs la corrida anterior + umbrales
absolutos, y si algo se rompió o cayó → AVISA por Telegram (mismo bot del Brain).
Deja tablero versionado health-status.md.

"De punta" = no esperar a que un humano corra el motor para enterarse de una regresión.

La lógica de veredicto (evaluate/verdict/last_two) es PURA y testeable. El paso de red
(report_build + Telegram) no se testea.

Uso:
  python execution/health_check.py             # corre el chequeo maestro + alarma si degradado
  python execution/health_check.py --no-build   # evalúa el report-history existente (no re-audita)
  python execution/health_check.py --dry-run    # evalúa + tablero, NO envía Telegram (para probar)
  python execution/health_check.py --no-tokens  # no comprueba los accesos de Google (sin red)

Además de lo roto en el sitio, alarma ROJO si una fuente remota pasa de
health.max_data_age_days (9) o si un token de Google ya no refresca.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from _common import ROOT, TMP, cfg, site_dir

HEALTH_MD = ROOT / "health-status.md"
REPORT_HIST = ROOT / "report-history.json"
BACKLINK_HIST = ROOT / "backlink-history.json"
SECRETS = ROOT.parent / "flujo2-reunion" / ".secrets.env"  # mismo bot Telegram del Brain


def _load(path):
    p = Path(path)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def last_two(hist):
    """Pura (testeable). (cur, prev) = últimos 2 snapshots de {snapshots:[...]}."""
    snaps = (hist or {}).get("snapshots", [])
    cur = snaps[-1] if snaps else None
    prev = snaps[-2] if len(snaps) >= 2 else None
    return cur, prev


def evaluate(cur, prev, index=None, bl_cur=None, bl_prev=None, score_drop=3):
    """Pura (testeable). Lista de findings {sev, msg}.
    sev: 'ROJO' (algo roto AHORA) · 'REGRESION' (cayó vs anterior)."""
    out = []
    if not cur:
        return [{"sev": "ROJO", "msg": "Sin report-history: el chequeo maestro no produjo datos."}]
    m = cur.get("metricas", {})

    # --- ROJO absoluto: algo roto AHORA (independiente de la tendencia) ---
    if m.get("high", 0) > 0:
        out.append({"sev": "ROJO", "msg": f"{m['high']} hallazgo(s) HIGH técnicos"})
    if m.get("forms_rotos", 0) > 0:
        out.append({"sev": "ROJO", "msg": f"{m['forms_rotos']} formulario(s) roto(s) — la web no convierte"})
    if m.get("schema_invalido", 0) > 0:
        out.append({"sev": "ROJO", "msg": f"{m['schema_invalido']} schema(s) JSON-LD inválido(s)"})
    if m.get("enlaces_rotos", 0) > 0:
        out.append({"sev": "ROJO", "msg": f"{m['enlaces_rotos']} enlace(s) interno(s) roto(s)"})
    if index:
        conf = index.get("conflictos_canonical", [])
        if conf:
            out.append({"sev": "ROJO", "msg": f"{len(conf)} conflicto(s) de canónica (Google ignora tu canonical)"})

    # --- REGRESION vs anterior ---
    if prev:
        pm = prev.get("metricas", {})
        d = cur.get("score", 0) - prev.get("score", 0)
        if d <= -score_drop:
            out.append({"sev": "REGRESION", "msg": f"Salud SEO cayó {prev.get('score')}→{cur.get('score')} ({d})"})
        gc, pgc = m.get("geo_citado"), pm.get("geo_citado")
        if gc is not None and pgc is not None and gc < pgc:
            out.append({"sev": "REGRESION", "msg": f"Citación IA (GEO) bajó {pgc}→{gc}"})

    if bl_cur is not None and bl_prev is not None:
        c, p = bl_cur.get("total_backlinks", 0), bl_prev.get("total_backlinks", 0)
        if c < p:
            out.append({"sev": "REGRESION", "msg": f"Backlinks bajaron {p}→{c}"})
    return out


# Fuentes remotas que NO regenera report_build (las refresca run-rank-track.cmd, semanal).
# Sin esta vigilancia el tablero dijo SANO del 28-sep al 4-oct con Search Console congelado
# en el 16-sep: solo miraba lo que se lee del disco, y el disco siempre esta fresco.
SOURCES = {
    "Search Console": "gsc_opportunities.json",
    "Indice real de Google": "index_inspect.json",
    "Citacion IA (GEO)": "geo_citation.json",
    "YouTube": "youtube.json",
    "Google Analytics": "ga4_overview.json",
    "Bing": "bing_traffic.json",
    "Core Web Vitals": "cwv.json",
}
TOKENS = {"Search Console": "token.json", "Google Analytics": "ga4_token.json",
          "YouTube (OAuth)": "youtube_token.json"}
REAUTH = "re-autorizar: .venv/Scripts/python.exe reautorizar.py"


def stale_findings(ages, max_days):
    """Pura (testeable). ages = {fuente: dias | None}. None = sin archivo (fuente nunca corrida), se salta.
    Si se retira una llave, borrar su .tmp/*.json o quitarla de SOURCES: si no, queda ROJO fijo."""
    out = []
    for name, age in ages.items():
        if age is not None and age > max_days:
            out.append({"sev": "ROJO", "msg": f"{name}: datos de hace {int(age)} dias (max {max_days}). "
                                              "La rutina semanal no los esta refrescando"})
    return out


def data_ages(today=None):
    """Edad en dias de cada fuente (mtime) + fecha del ultimo snapshot de backlinks."""
    import time
    now = time.time()
    ages = {}
    for name, fname in SOURCES.items():
        f = TMP / fname
        ages[name] = (now - f.stat().st_mtime) / 86400 if f.exists() else None
    bl, _ = last_two(_load(BACKLINK_HIST))
    if bl and bl.get("date"):
        try:
            ages["Backlinks"] = ((today or date.today()) - date.fromisoformat(bl["date"])).days
        except ValueError:
            pass
    return ages


def _probe_token(path):
    """True = refresca · False = muerto (invalid_grant) · None = no se pudo comprobar (red)."""
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    try:
        creds = Credentials.from_authorized_user_file(str(path))
    except ValueError:
        return False  # sin refresh_token / malformado: no sirve para una rutina desatendida
    try:
        creds.refresh(Request())  # no se escribe a disco: solo se comprueba
        return True
    except RefreshError as e:
        # 5xx/429 de Google llegan como RefreshError(retryable=True): es Google, no el token.
        return None if getattr(e, "retryable", False) else False
    except Exception:  # noqa: BLE001 — sin red no es un token muerto
        return None


def token_findings(probe=_probe_token):
    """ROJO por cada token de Google que existe y ya no refresca."""
    out = []
    for name, fname in TOKENS.items():
        p = ROOT / fname
        if p.exists() and probe(p) is False:
            out.append({"sev": "ROJO", "msg": f"Acceso de Google vencido ({name}): {REAUTH}"})
    return out


def hollow_findings(geo, index):
    """Pura (testeable). Archivo fresco pero corrida vacia: la edad por mtime no lo ve.
    geo_citation escribe su json aunque no corra ningun motor; index_inspect, aunque fallen
    todas las inspecciones (cuota/permiso)."""
    out = []
    if geo is not None and not geo.get("engines"):
        out.append({"sev": "ROJO", "msg": "Citacion IA (GEO): la ultima corrida no midio con ningun motor"})
    if index:
        n, err = index.get("inspeccionadas_esta_corrida") or 0, index.get("errores") or 0
        if n and err >= n:
            out.append({"sev": "ROJO", "msg": f"Indice real de Google: fallaron las {n} inspecciones de la ultima corrida"})
    return out


def verdict(findings):
    """Pura (testeable). 'DEGRADADO' si hay ROJO/REGRESION; si no 'SANO'."""
    return "DEGRADADO" if any(f["sev"] in ("ROJO", "REGRESION") for f in findings) else "SANO"


def render_board(cur, prev, findings, v):
    """Markdown del tablero health-status.md."""
    L = [f"# Salud seo-forge — {date.today().isoformat()}", "",
         f"**Veredicto: {'🟢 SANO' if v == 'SANO' else '🔴 DEGRADADO'}**", ""]
    if cur:
        sc = cur.get("score", "?")
        line = f"- Salud SEO: **{sc}/100**"
        if prev:
            dd = cur.get("score", 0) - prev.get("score", 0)
            line += f" ({'+' if dd >= 0 else ''}{dd} vs {prev.get('date')})"
        L.append(line)
        m = cur.get("metricas", {})
        L.append(f"- HIGH {m.get('high', 0)} · forms rotos {m.get('forms_rotos', 0)} · "
                 f"schema inválido {m.get('schema_invalido', 0)} · enlaces rotos {m.get('enlaces_rotos', 0)} · "
                 f"citación IA {m.get('geo_citado', '?')}")
    # Desglose por componente. Sin esto el tablero podia decir "SANO / de punta" con la salud
    # tecnica en 44 y la citacion por IA en 0, porque el veredicto solo mira ROJO/REGRESION
    # (correcto como gate de release: MED y LOW no deben bloquear). Pero un verde que esconde
    # donde duele entrena a no mirar el tablero. El veredicto no cambia; deja de callar.
    if cur and cur.get("componentes"):
        comp = cur["componentes"]
        peor = sorted(comp.items(), key=lambda kv: kv[1])[:2]
        L.append("- Por componente: " + " · ".join(f"{k} {v}" for k, v in sorted(comp.items())))
        flojos = [f"**{k} {v}/100**" for k, v in peor if v < 70]
        if flojos:
            L.append(f"- ⚠️ Lo que tira la nota abajo: {', '.join(flojos)}")
    if cur:
        m = cur.get("metricas", {})
        pend = m.get("med", 0) + m.get("low", 0)
        if pend:
            L.append(f"- Pendientes que NO bloquean el veredicto: {m.get('med', 0)} medias · "
                     f"{m.get('low', 0)} bajas")

    L.append("")
    if findings:
        L.append("## Hallazgos")
        for f in findings:
            icon = "🔴" if f["sev"] == "ROJO" else ("📉" if f["sev"] == "REGRESION" else "•")
            L.append(f"- {icon} **{f['sev']}** — {f['msg']}")
    elif cur and (cur.get("score", 100) < 80
                  or any(v < 70 for v in (cur.get("componentes") or {}).values())):
        L.append("_Nada ROJO, que es lo que mira el gate. Pero la nota o algun componente estan"
                 " bajos: hay trabajo pendiente, no es \"de punta\"._")
    else:
        L.append("_Sin hallazgos: SEO/GEO de punta._")
    L.append("\n_Generado por health_check.py (tarea seo-forge-health)._")
    return "\n".join(L)


def _telegram_creds():
    """Token/chat: env (TELEGRAM_*) o el .secrets.env del Brain (mismo bot del watchdog)."""
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if tok and chat:
        return tok, chat
    if SECRETS.exists():
        for line in SECRETS.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                tok = tok or line.split("=", 1)[1].strip()
            elif line.startswith("TELEGRAM_CHAT_ID="):
                chat = chat or line.split("=", 1)[1].strip()
    return tok, chat


def send_telegram(text):
    """Envía la alarma. Gated: sin credenciales o --dry-run → no rompe (solo tablero)."""
    if "--dry-run" in sys.argv:
        print("health_check: --dry-run, alarma NO enviada (habría alarmado).")
        return False
    tok, chat = _telegram_creds()
    if not (tok and chat):
        print("health_check: sin TELEGRAM_BOT_TOKEN/CHAT_ID (.secrets.env o .env). Alarma NO enviada (solo tablero).")
        return False
    import requests
    try:
        r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                          data={"chat_id": chat, "text": text}, timeout=30)
        ok = r.status_code == 200 and r.json().get("ok")
        print("health_check: alarma Telegram enviada" if ok else "health_check: Telegram respondió no-OK (revisar chat_id)")
        return bool(ok)
    except Exception as e:
        # NUNCA imprimir la respuesta/URL cruda: la URL lleva el token (secreto).
        print(f"health_check: fallo el envío Telegram ({type(e).__name__})")
        return False


def main():
    score_drop = int(cfg("health.score_drop_alarm", 3))

    if "--no-build" not in sys.argv:
        try:
            subprocess.run([sys.executable, str(Path(__file__).with_name("report_build.py")),
                            "--site", str(site_dir())], check=True, timeout=600)
        except Exception as e:
            # que el chequeo maestro NO pueda correr es en sí una alarma
            msg = f"[seo-forge] ⚠️ health_check no pudo correr el chequeo maestro: {type(e).__name__}"
            send_telegram(msg)
            print(msg)
            return 2

    cur, prev = last_two(_load(REPORT_HIST))
    index = _load(TMP / "index_inspect.json")
    bl_cur, bl_prev = last_two(_load(BACKLINK_HIST))
    findings = evaluate(cur, prev, index, bl_cur, bl_prev, score_drop)
    findings += stale_findings(data_ages(), int(cfg("health.max_data_age_days", 9)))
    findings += hollow_findings(_load(TMP / "geo_citation.json"), index)
    if "--no-tokens" not in sys.argv:
        findings += token_findings()
    v = verdict(findings)

    HEALTH_MD.write_text(render_board(cur, prev, findings, v), encoding="utf-8")
    print(f"health_check: {v} · {len(findings)} hallazgo(s) -> {HEALTH_MD}")

    if v == "DEGRADADO":
        sc = cur.get("score", "?") if cur else "?"
        lines = "\n".join(f"- {f['sev']}: {f['msg']}" for f in findings)
        send_telegram(f"[seo-forge] 🔴 SEO/GEO DEGRADADO (Salud {sc}/100)\n\n{lines}\n\nTablero: health-status.md")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
