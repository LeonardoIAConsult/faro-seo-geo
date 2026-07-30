#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
rank_track.py — snapshot de posiciones reales (GSC) + comparacion con el anterior.

Da el LOOP DE APRENDIZAJE de seo-forge: cada corrida guarda las posiciones actuales
de tus keywords y las compara con el snapshot previo -> ves que SUBE y que BAJA.
Con eso el auditor (y el dueño) dejan de trabajar a ciegas: aprenden de resultados reales.

Usa la auth de gsc_pull (token.json local). Historial persistente y versionado en
`rank-history.json` (raiz de seo-forge). Corre local (GSC OAuth vive local).

Uso:
  python execution/rank_track.py [--days 28]
"""
import json
import sys
from datetime import date

from _common import ROOT, site_dir  # noqa
from gsc_pull import run  # reutiliza auth + query de GSC

HIST = ROOT / "rank-history.json"


def write_opportunities(snap):
    """Cierra el loop: publica al repo del sitio las keywords en posicion 5-20
    (fruta al alcance: subir a top 5 = ganancia rapida). El auditor cloud lee este
    archivo y PRIORIZA los posts que apuntan a esas keywords. Sin datos GSC el
    archivo queda vacio pero el mecanismo queda montado."""
    try:
        site = site_dir()
    except Exception:
        return
    seo_dir = site / ".seo"
    seo_dir.mkdir(parents=True, exist_ok=True)
    opps = [
        {"keyword": q, "pos": v["pos"], "imp": v["imp"], "clk": v["clk"]}
        for q, v in snap["queries"].items()
        if 5.0 <= v["pos"] <= 20.0
    ]
    opps.sort(key=lambda x: x["imp"], reverse=True)
    (seo_dir / "opportunities.json").write_text(
        json.dumps({"generado": snap["date"], "ventana_dias": snap["days"],
                    "criterio": "keywords en posicion 5-20 (subir a top 5 = ganancia rapida)",
                    "oportunidades": opps}, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [f"# Oportunidades de ranking — {snap['date']}",
          "",
          "> Generado por seo-forge (rank_track). El auditor NOVA PRIORIZA los posts que",
          "> apuntan a estas keywords: están en posición 5-20, un empujón las mete al top 5.",
          ""]
    if opps:
        md.append("| Keyword | Posición | Impresiones | Clics |")
        md.append("|---|---|---|---|")
        for o in opps[:30]:
            md.append(f"| {o['keyword']} | {o['pos']} | {o['imp']} | {o['clk']} |")
    else:
        md.append("_Sin keywords en pos 5-20 todavía (contenido recién reindexado). "
                  "Cuando GSC acumule datos, aquí saldrán las de mayor palanca._")
    (seo_dir / "opportunities.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Oportunidades pos 5-20: {len(opps)} -> {seo_dir / 'opportunities.md'}")


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def load_hist():
    if HIST.exists():
        try:
            return json.loads(HIST.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"snapshots": []}


def main():
    days = int(arg("--days", "28"))
    rows = run(["query"], days)  # query, position, impressions, clicks, ctr
    today = date.today().isoformat()
    snap = {
        "date": today,
        "days": days,
        "keywords": len(rows),
        "queries": {
            r["query"]: {"pos": r["position"], "imp": r["impressions"], "clk": r["clicks"]}
            for r in rows
        },
    }
    hist = load_hist()
    prev = None
    for s in reversed(hist["snapshots"]):
        if s["date"] != today:
            prev = s
            break
    hist["snapshots"] = [s for s in hist["snapshots"] if s["date"] != today]
    hist["snapshots"].append(snap)
    HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    write_opportunities(snap)  # cierra el loop -> repo del sitio -> auditor cloud

    print(f"Snapshot {today} ({days}d): {len(rows)} keywords. Historial: {len(hist['snapshots'])} snapshots.")
    if not prev:
        print("Primer snapshot (baseline). El proximo comparara movimiento.")
        return 0

    movers = []
    for q, cur in snap["queries"].items():
        if q in prev["queries"]:
            delta = prev["queries"][q]["pos"] - cur["pos"]  # + = subio (mejor posicion)
            if abs(delta) >= 0.5:
                movers.append((delta, q, prev["queries"][q]["pos"], cur["pos"]))
    movers.sort(reverse=True)
    new_q = [q for q in snap["queries"] if q not in prev["queries"]]
    lost_q = [q for q in prev["queries"] if q not in snap["queries"]]

    print(f"\n== vs {prev['date']} ==")
    for delta, q, p0, p1 in movers[:10]:
        flag = "SUBE" if delta > 0 else "baja"
        print(f"  {flag} {abs(delta):>4.1f}  {q}  ({p0} -> {p1})")
    if not movers:
        print("  sin movimientos >=0.5 posiciones.")
    print(f"  keywords nuevas: {len(new_q)}  |  perdidas: {len(lost_q)}")
    if new_q:
        print("  nuevas:", ", ".join(new_q[:8]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
