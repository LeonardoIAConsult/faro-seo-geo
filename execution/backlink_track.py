#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
backlink_track.py — snapshot de backlinks (Bing) + comparación con el anterior.

El cuello de botella SEO del sitio NO es técnico: es AUTORIDAD (0 backlinks, medido
2026-07-30). Este tracker es el instrumento que faltaba para la campaña de autoridad:
cada corrida guarda el total de enlaces entrantes y lo compara con el snapshot previo
-> ves subir de 0 a medida que el dueño crea perfiles, consigue guest posts, etc.

Gemelo de rank_track / youtube_track (patrón watchdog): snapshot + diff, historial
versionado en `backlink-history.json` (raíz). NO reescribe deliverables ni entra a
report_build (es medición longitudinal, como rank/youtube). Corre en la tarea semanal.

Fuente = Bing Webmaster GetLinkCounts (único backlink count GRATIS y automatizable;
GSC no expone backlinks por API). Gated por BING_API_KEY: sin key se salta, no rompe.

Uso:
  python execution/backlink_track.py
"""
import json
import os
import sys
from datetime import date

from _common import ROOT, cfg
from bing_pull import api_get, bing_site, normalize_links

HIST = ROOT / "backlink-history.json"


def total_backlinks(links: list[dict]) -> int:
    """Pura (testeable). Suma los enlaces entrantes de las páginas con url válida
    (mismo filtro que por_pagina → total y paginas_enlazadas nunca divergen)."""
    return sum(int(x.get("count") or 0) for x in links if x.get("url"))


def snapshot_from_links(links: list[dict], today: str) -> dict:
    """Pura (testeable). Arma el snapshot desde la lista normalizada de bing."""
    por_pagina = {x["url"]: int(x.get("count") or 0) for x in links if x.get("url")}
    return {
        "date": today,
        "total_backlinks": total_backlinks(links),
        "paginas_enlazadas": len([c for c in por_pagina.values() if c > 0]),
        "por_pagina": por_pagina,
    }


def find_prev(snapshots: list[dict], today: str) -> dict | None:
    """Pura (testeable). Último snapshot con fecha != hoy (para comparar)."""
    for s in reversed(snapshots):
        if s.get("date") != today:
            return s
    return None


def diff_snapshots(prev: dict, cur: dict) -> dict:
    """Pura (testeable). Compara dos snapshots: delta total, páginas nuevas/perdidas
    con enlaces, y cambios de conteo por página existente."""
    p_pag = prev.get("por_pagina", {})
    c_pag = cur.get("por_pagina", {})
    nuevas = sorted(u for u in c_pag if u not in p_pag and c_pag[u] > 0)
    perdidas = sorted(u for u in p_pag if u not in c_pag and p_pag[u] > 0)
    cambios = []
    for u in c_pag:
        if u in p_pag and c_pag[u] != p_pag[u]:
            cambios.append({"url": u, "antes": p_pag[u], "ahora": c_pag[u],
                            "delta": c_pag[u] - p_pag[u]})
    cambios.sort(key=lambda x: -abs(x["delta"]))
    return {
        "delta_total": cur.get("total_backlinks", 0) - prev.get("total_backlinks", 0),
        "paginas_nuevas": nuevas,
        "paginas_perdidas": perdidas,
        "cambios_conteo": cambios,
    }


def load_hist() -> dict:
    if HIST.exists():
        try:
            return json.loads(HIST.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"snapshots": []}


def main():
    key = os.environ.get("BING_API_KEY") or cfg("bing.api_key")
    if not key:
        print("backlink_track: sin BING_API_KEY (Bing WMT → Settings → API access). Se salta.")
        return 0

    site = bing_site()
    d = api_get("GetLinkCounts", key, siteUrl=site, page=0) or {}
    links = normalize_links(d)
    today = date.today().isoformat()
    snap = snapshot_from_links(links, today)

    hist = load_hist()
    prev = find_prev(hist["snapshots"], today)
    hist["snapshots"] = [s for s in hist["snapshots"] if s.get("date") != today]
    hist["snapshots"].append(snap)
    HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Snapshot {today}: {snap['total_backlinks']} backlinks · "
          f"{snap['paginas_enlazadas']} páginas enlazadas. "
          f"Historial: {len(hist['snapshots'])} snapshots.")
    if not prev:
        print("Primer snapshot (baseline). El próximo comparará movimiento.")
        return 0

    dd = diff_snapshots(prev, snap)
    arrow = "SUBE" if dd["delta_total"] > 0 else ("baja" if dd["delta_total"] < 0 else "igual")
    print(f"\n== vs {prev['date']} ==")
    print(f"  backlinks: {prev['total_backlinks']} -> {snap['total_backlinks']} "
          f"({arrow} {dd['delta_total']:+d})")
    if dd["paginas_nuevas"]:
        print(f"  páginas que empezaron a recibir enlaces: {len(dd['paginas_nuevas'])}")
        for u in dd["paginas_nuevas"][:8]:
            print(f"    + {u}")
    if dd["paginas_perdidas"]:
        print(f"  páginas que perdieron todos sus enlaces: {len(dd['paginas_perdidas'])}")
        for u in dd["paginas_perdidas"][:8]:
            print(f"    - {u}")
    for c in dd["cambios_conteo"][:8]:
        print(f"    ~ {c['delta']:+d}  {c['url']} ({c['antes']} -> {c['ahora']})")
    if dd["delta_total"] == 0 and not dd["paginas_nuevas"] and not dd["paginas_perdidas"]:
        print("  sin cambios. (Autoridad se mueve lento; los perfiles nuevos tardan en indexar.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
