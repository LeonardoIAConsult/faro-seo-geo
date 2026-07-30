#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
report_score.py — "Salud SEO": un número compuesto (0-100) + diff vs la corrida anterior.

Lo que un dueño mira en 5 segundos: "Salud SEO 82/100, +4 vs la semana pasada, HIGH 0→0,
Citación IA 1/10→2/10". Convierte los intermedios (técnico/funcional/schema/GEO/contenido)
en un score ponderado y guarda historial versionado para ver la tendencia.

Determinista y sin red. Se usa desde report_build.py. Historial: report-history.json (raíz).
"""
from __future__ import annotations

import json
from datetime import date

from _common import ROOT

HIST = ROOT / "report-history.json"

# Pesos por componente. Se renormalizan sobre los componentes PRESENTES (si no hay GEO
# ni funcional, no penaliza: reparte el peso entre lo que sí se midió).
WEIGHTS = {"tecnica": 0.30, "funcional": 0.25, "schema": 0.15, "geo": 0.15, "contenido": 0.15}


def _clamp(x):
    return max(0, min(100, round(x)))


def _forms_ko(func):
    return sum(1 for x in func.get("forms", []) if x.get("ok") is False)


def compute(onpage, tech=None, func=None, schema=None, geo=None):
    """Devuelve {score, componentes{...}, metricas{...}}. Los componentes ausentes
    (None) se omiten del promedio ponderado (no penalizan)."""
    comp, metrics = {}, {}

    if tech:
        s = tech.get("summary", {})
        h, m, low = s.get("HIGH", 0), s.get("MED", 0), s.get("LOW", 0)
        comp["tecnica"] = _clamp(100 - (h * 15 + m * 3 + low * 0.5))
        metrics.update(high=h, med=m, low=low)

    if func:
        r = func.get("resumen", {})
        fko = _forms_ko(func)
        comp["funcional"] = _clamp(100 - (fko * 40 + r.get("enlaces_rotos", 0) * 5
                                          + r.get("assets_faltantes", 0) * 5
                                          + r.get("ctas_vacios", 0) * 3))
        metrics.update(forms_rotos=fko, enlaces_rotos=r.get("enlaces_rotos", 0),
                       assets_faltantes=r.get("assets_faltantes", 0))

    if schema:
        inv, miss = schema.get("json_invalido", 0), len(schema.get("issues", []))
        comp["schema"] = _clamp(100 - (inv * 20 + miss * 5))
        metrics.update(schema_invalido=inv, schema_faltantes=miss)

    if geo:
        q = geo.get("queries", 0) or 0
        comp["geo"] = _clamp((geo.get("tasa_citacion", 0) or 0) * 100)
        metrics.update(geo_citado=geo.get("citado", 0), geo_queries=q)

    # solo páginas públicas: las noindex (plantillas/legales) no son contenido a rankear
    pages = [p for p in onpage.get("pages", [])
             if "noindex" not in (p.get("meta_robots") or "").lower()]
    n = len(pages) or 1
    thin = sum(1 for p in pages if p["word_count"] < 300 and p["url"] != "/")
    noschema = sum(1 for p in pages if not p["jsonld_types"])
    noalt = sum(1 for p in pages if p["images_no_alt"] > 0)
    comp["contenido"] = _clamp(100 - ((thin + noschema + noalt) / (n * 3)) * 100)
    metrics.update(paginas=n, thin=thin, sin_schema=noschema, con_img_sin_alt=noalt)

    total_w = sum(WEIGHTS[k] for k in comp)
    score = _clamp(sum(comp[k] * WEIGHTS[k] for k in comp) / total_w) if total_w else 0
    return {"score": score, "componentes": comp, "metricas": metrics}


def update_history(result):
    """Guarda el snapshot de hoy (reemplaza si ya hay uno hoy) y devuelve (cur, prev)."""
    today = date.today().isoformat()
    snap = {"date": today, **result}
    hist = {"snapshots": []}
    if HIST.exists():
        try:
            hist = json.loads(HIST.read_text(encoding="utf-8"))
        except Exception:
            pass
    prev = next((s for s in reversed(hist["snapshots"]) if s["date"] != today), None)
    hist["snapshots"] = [s for s in hist["snapshots"] if s["date"] != today] + [snap]
    HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    return snap, prev


def _arrow(cur, prev, higher_better=True):
    if prev is None:
        return ""
    d = cur - prev
    if d == 0:
        return " (=)"
    up = d > 0
    good = up if higher_better else not up
    sign = "+" if up else ""
    return f" ({'↑' if good else '↓'}{sign}{d})"


def render(cur, prev):
    """Markdown de la sección 'Salud SEO' con el score, componentes y diff de métricas."""
    sc = cur["score"]
    head = f"## Salud SEO: {sc}/100"
    if prev:
        head += _arrow(sc, prev["score"]) + f" vs {prev['date']}"
    L = [head, ""]
    comp = cur["componentes"]
    L.append("| Componente | Score |\n|---|---|")
    labels = {"tecnica": "Técnica", "funcional": "Funcional/conversión", "schema": "Datos estructurados",
              "geo": "Citación IA (GEO)", "contenido": "Contenido"}
    pc = (prev or {}).get("componentes", {})
    for k, v in comp.items():
        L.append(f"| {labels.get(k, k)} | {v}/100{_arrow(v, pc.get(k) if k in pc else None)} |")
    # métricas clave (menos = mejor salvo citación, que usa higher=True en show())
    m, pm = cur["metricas"], (prev or {}).get("metricas", {})
    parts = []
    def show(key, label, higher=False):
        if key in m:
            parts.append(f"{label} {m[key]}{_arrow(m[key], pm.get(key) if key in pm else None, higher)}")
    show("high", "HIGH")
    show("forms_rotos", "Forms rotos")
    show("schema_invalido", "Schema inválido")
    show("geo_citado", "Citación IA", higher=True)
    show("thin", "Contenido delgado")
    if parts:
        L.append("\n**Métricas clave:** " + " · ".join(parts))
    return "\n".join(L)


def section(onpage, tech=None, func=None, schema=None, geo=None):
    """Atajo: computa, guarda historial y devuelve el markdown listo para el informe."""
    result = compute(onpage, tech, func, schema, geo)
    cur, prev = update_history(result)
    return render(cur, prev)
