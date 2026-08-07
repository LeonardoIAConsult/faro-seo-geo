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
    L.append("")
    if findings:
        L.append("## Hallazgos")
        for f in findings:
            icon = "🔴" if f["sev"] == "ROJO" else ("📉" if f["sev"] == "REGRESION" else "•")
            L.append(f"- {icon} **{f['sev']}** — {f['msg']}")
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
