#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
geo_citation.py — mide la CITACION GEO real: ¿la IA cita a la marca? (multi-motor)

Optimizar para ser citado por IA no sirve si nadie mide si de hecho te citan. Este
orquestador le hace a CADA motor disponible (ver _geo_engines.py) las preguntas que un
cliente del nicho haría + las keywords reales de GSC, y detecta por pregunta:
  - si la marca aparece como FUENTE citada (grounding) o solo mencionada en el texto
  - QUE competidores dominan la respuesta (inteligencia GEO)
  - una tasa de citación por motor y global, con historial (loop de aprendizaje)

Honestidad (G4): reporta SOLO los motores que de verdad corrieron. Gemini es gratis y
siempre corre si hay key; OpenAI/Perplexity solo si pones su key (si no, se saltan).

Requiere GOOGLE_GENERATIVE_AI_API_KEY (Gemini, gratis). Opcional OPENAI_API_KEY /
PERPLEXITY_API_KEY para sumar esos motores. Historial: geo-citation-history.json.

Uso:
  python execution/geo_citation.py [--model gemini-2.5-flash] [--no-gsc]
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date

from _common import ROOT, TMP, cfg
from _geo_engines import ENGINES

HIST = ROOT / "geo-citation-history.json"

BRAND_DOMAIN = cfg("brand.domain", "example.com")
BRAND_NAMES = cfg("brand.names", ["your brand", "yourbrand",
                                  "your brand", "your brand"])
QUERIES = cfg("geo.queries", [])
GSC_TOP = cfg("geo.gsc_queries_top", 5)


def evaluate(text, sources):
    """Clasifica una respuesta: CITADO (fuente) > mencionado (texto) > ausente."""
    t = (text or "").lower()
    src = " ".join(sources)
    cited = BRAND_DOMAIN in src or any(n in src for n in BRAND_NAMES)
    mentioned = any(n in t for n in BRAND_NAMES) or BRAND_DOMAIN in t
    if cited:
        status = "CITADO (fuente)"
    elif mentioned:
        status = "mencionado (texto)"
    else:
        status = "ausente"
    competitors = [s for s in sources if BRAND_DOMAIN not in s
                   and not any(n in s for n in BRAND_NAMES)]
    return status, competitors


_RANK = {"CITADO (fuente)": 2, "mencionado (texto)": 1, "ausente": 0}


def best(statuses):
    """Estado a nivel pregunta = el mejor entre los motores (¿te cita ALGUNA IA?)."""
    return max(statuses, key=lambda s: _RANK.get(s, -1)) if statuses else "ausente"


def gsc_queries(top):
    """Top keywords reales de GSC (por impresiones) como preguntas adicionales."""
    f = TMP / "gsc_queries.json"
    if not f.exists():
        return []
    try:
        rows = json.loads(f.read_text(encoding="utf-8")).get("rows", [])
    except Exception:
        return []
    rows.sort(key=lambda r: r.get("impressions", 0), reverse=True)
    return [r["query"] for r in rows[:top] if r.get("query")]


def main():
    model = None
    for i, a in enumerate(sys.argv):
        if a == "--model" and i + 1 < len(sys.argv):
            model = sys.argv[i + 1]
    use_gsc = "--no-gsc" not in sys.argv

    queries = list(QUERIES)
    if use_gsc:
        for q in gsc_queries(GSC_TOP):
            if q not in queries:
                queries.append(q)
    if not queries:
        print("ERROR: no hay preguntas GEO. Define geo.queries en seo-forge.config.json.")
        return 1

    # ¿qué motores están disponibles? (los que no tienen key devuelven None y se saltan)
    detalle, comp_counter = [], {}
    engines_run = set()
    per_engine = {name: {"citado": 0, "mencionado": 0, "queries": 0} for name in ENGINES}

    for q in queries:
        per_eng_status, sources_all, comps_all = {}, [], []
        for name, eng in ENGINES.items():
            try:
                res = eng(q, model) if name == "gemini" else eng(q)
            except Exception as e:
                res = None
                per_eng_status[name] = f"error: {str(e)[:50]}"
            if not res:
                continue
            engines_run.add(name)
            status, comps = evaluate(res["answer"], res["sources"])
            per_eng_status[name] = status
            per_engine[name]["queries"] += 1
            if status.startswith("CITADO"):
                per_engine[name]["citado"] += 1
            elif "mencionado" in status:
                per_engine[name]["mencionado"] += 1
            sources_all += res["sources"]
            comps_all += comps
        real_statuses = [s for s in per_eng_status.values() if s in _RANK]
        qstatus = best(real_statuses)
        for c in set(comps_all):
            comp_counter[c] = comp_counter.get(c, 0) + 1
        detalle.append({"query": q, "status": qstatus, "por_motor": per_eng_status,
                        "fuentes": sorted(set(sources_all)), "competidores": sorted(set(comps_all))})
        print(f"  [{qstatus:>17}] {q[:55]}  ({'+'.join(sorted(engines_run)) or 'sin motor'})")
        time.sleep(1)

    engines_run = sorted(engines_run)
    n = len(queries)
    citado = sum(1 for r in detalle if r["status"].startswith("CITADO"))
    mencionado = sum(1 for r in detalle if "mencionado" in r["status"])
    top_comp = sorted(comp_counter.items(), key=lambda x: x[1], reverse=True)[:12]
    por_motor = {name: {**v, "tasa": round(v["citado"] / v["queries"], 2) if v["queries"] else 0}
                 for name, v in per_engine.items() if name in engines_run}

    today = date.today().isoformat()
    snap = {"date": today, "engines": engines_run,
            "model": (model or cfg("geo.model", "gemini-2.5-flash")),  # compat informe
            "queries": n, "citado": citado, "mencionado": mencionado,
            "tasa_citacion": round(citado / n, 2) if n else 0,
            "por_motor": por_motor,
            "top_competidores": [{"dominio": d, "apariciones": c} for d, c in top_comp],
            "detalle": detalle}

    hist = {"snapshots": []}
    if HIST.exists():
        try:
            hist = json.loads(HIST.read_text(encoding="utf-8"))
        except Exception:
            pass
    hist["snapshots"] = [s for s in hist["snapshots"] if s["date"] != today] + [snap]
    HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    (TMP / "geo_citation.json").write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")

    if not engines_run:
        print("\nERROR: ningún motor GEO disponible. Pon GOOGLE_GENERATIVE_AI_API_KEY "
              "(Gemini, gratis) — y opcional OPENAI_API_KEY / PERPLEXITY_API_KEY.")
        return 1
    print(f"\n== GEO citación {today} · motores: {', '.join(engines_run)} ==")
    print(f"  Citado (alguna IA): {citado}/{n}  |  Mencionado: {mencionado}/{n}  "
          f"|  Tasa: {snap['tasa_citacion']}")
    for name, v in por_motor.items():
        print(f"    · {name}: citado {v['citado']}/{v['queries']} (tasa {v['tasa']})")
    print("  Dominios que DOMINAN tu nicho en la IA:")
    for d, c in top_comp[:8]:
        print(f"    {c}x  {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
