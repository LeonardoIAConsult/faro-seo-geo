#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
geo_learn.py — motor de AUTO-APRENDIZAJE GEO. Cierra el loop para llevar al dueño
a la punta en citación por IA: mide → aprende qué mueve la aguja → prioriza → alimenta
el contenido de NOVA → re-mide.

Lee `geo-citation-history.json` (snapshots de geo_citation a lo largo del tiempo) y:
  - traza la TRAYECTORIA de cada pregunta (ausente → mencionado → citado, por fecha).
  - clasifica: GANADAS (mejoró a citado), PERDIDAS (perdió cita), HUECOS persistentes
    (ausente en todas las corridas = a atacar), ESTABLES.
  - mide la TENDENCIA de la tasa de citación (¿sube corrida a corrida?).
  - detecta los COMPETIDORES que dominan de forma persistente (a quién estudiar/ganar).
  - **aprende**: cada corrida deja una observación fechada en `geo-learnings.md` (log que
    se acumula) y una lista priorizada de acciones en `geo-next-actions.json` que el
    siguiente ciclo de contenido (NOVA) usa como objetivos. Así el sistema se afina solo.

Determinista, sin red (usa lo que geo_citation ya midió). Correr tras geo_citation.py.
Uso:  python execution/geo_learn.py
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date

from _common import ROOT

HIST = ROOT / "geo-citation-history.json"
LEARN = ROOT / "geo-learnings.md"
ACTIONS = ROOT / "geo-next-actions.json"

RANK = {"CITADO (fuente)": 2, "mencionado (texto)": 1, "ausente": 0}


def _status_val(s):
    for k, v in RANK.items():
        if s.startswith(k[:6]):
            return v
    return 0


def main():
    if not HIST.exists():
        print("Sin geo-citation-history.json — corre geo_citation.py primero.")
        return 1
    snaps = sorted(json.loads(HIST.read_text(encoding="utf-8"))["snapshots"], key=lambda s: s["date"])
    if not snaps:
        print("Historial vacío.")
        return 1
    last = snaps[-1]
    dates = [s["date"] for s in snaps]

    # trayectoria por pregunta
    traj = {}
    for s in snaps:
        for r in s.get("detalle", []):
            traj.setdefault(r["query"], {})[s["date"]] = r["status"]
    ganadas, perdidas, huecos, estables = [], [], [], []
    for q, byd in traj.items():
        seq = [byd.get(d) for d in dates if d in byd]
        vals = [_status_val(x) for x in seq if x]
        if not vals:
            continue
        cur = vals[-1]
        if cur >= 2 and (len(vals) == 1 or vals[0] < 2):
            ganadas.append(q)
        elif cur < 2 and any(v >= 2 for v in vals[:-1]):
            perdidas.append(q)
        elif all(v == 0 for v in vals) and len(vals) >= 2:
            huecos.append(q)
        elif cur >= 2:
            estables.append(q)

    # tendencia de tasa
    tasas = [(s["date"], s.get("tasa_citacion", 0)) for s in snaps]
    delta = round(tasas[-1][1] - tasas[-2][1], 2) if len(tasas) >= 2 else 0

    # competidores persistentes (dominan varias corridas)
    comp = Counter()
    for s in snaps:
        for c in s.get("top_competidores", []):
            comp[c["dominio"]] += c.get("apariciones", 1)
    top_comp = comp.most_common(10)

    # huecos actuales (ausente en la última corrida) con su competidor a estudiar
    ausentes = []
    for r in last.get("detalle", []):
        if r["status"] == "ausente":
            rival = r["competidores"][0] if r.get("competidores") else None
            ausentes.append({"query": r["query"], "rival": rival})

    # ACCIONES priorizadas: huecos persistentes primero, luego perdidas, luego ausentes nuevas
    priority = [{"query": q, "tipo": "hueco persistente", "prioridad": "alta"} for q in huecos]
    priority += [{"query": q, "tipo": "cita perdida", "prioridad": "alta"} for q in perdidas]
    seen = {p["query"] for p in priority}
    priority += [{"query": a["query"], "tipo": "ausente", "prioridad": "media", "rival": a["rival"]}
                 for a in ausentes if a["query"] not in seen]
    ACTIONS.write_text(json.dumps({
        "generado": date.today().isoformat(),
        "tasa_actual": tasas[-1][1], "tendencia": delta,
        "objetivos": priority[:12],
        "competidores_a_estudiar": [d for d, _ in top_comp[:5]],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # LEARNINGS: observación fechada que se ACUMULA (auto-aprendizaje)
    obs = [f"## {date.today().isoformat()} — corrida de aprendizaje GEO",
           f"- Tasa citación: **{tasas[-1][1]}** ({'+' if delta >= 0 else ''}{delta} vs {tasas[-2][0] if len(tasas) >= 2 else 'baseline'}) · "
           f"motores: {', '.join(last.get('engines', []))} · {last.get('queries', 0)} preguntas",
           f"- 🟢 Ganadas: {len(ganadas)}" + (f" ({'; '.join(ganadas[:3])})" if ganadas else ""),
           f"- 🔴 Perdidas: {len(perdidas)}" + (f" ({'; '.join(perdidas[:3])})" if perdidas else ""),
           f"- 🟡 Huecos persistentes (atacar): {len(huecos)}" + (f" ({'; '.join(huecos[:3])})" if huecos else ""),
           f"- Competidores que dominan: {', '.join(d for d, _ in top_comp[:5])}",
           "- **Regla aprendida (a refinar por sesión LLM):** ver `geo-next-actions.json` → los objetivos"
           " alimentan el próximo lote de contenido de NOVA (posts answer-first para esas preguntas).\n"]
    block = "\n".join(obs)
    header = ("# GEO — aprendizajes (auto-acumulado por geo_learn.py)\n\n"
              "> Cada corrida agrega una observación. El objetivo: llevar la tasa de citación por IA "
              "hacia la punta. Los `geo-next-actions.json` son los objetivos del próximo contenido.\n\n"
              "<!-- nuevas observaciones se agregan debajo -->\n\n")
    prev = LEARN.read_text(encoding="utf-8") if LEARN.exists() else header
    LEARN.write_text(prev + block + "\n", encoding="utf-8")

    print(f"geo_learn: tasa {tasas[-1][1]} ({'+' if delta >= 0 else ''}{delta}) · "
          f"ganadas {len(ganadas)} · perdidas {len(perdidas)} · huecos {len(huecos)}")
    print(f"  objetivos priorizados: {len(priority)} -> {ACTIONS.name}")
    print(f"  competidores a estudiar: {', '.join(d for d, _ in top_comp[:5])}")
    print(f"  aprendizaje acumulado -> {LEARN.name}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
