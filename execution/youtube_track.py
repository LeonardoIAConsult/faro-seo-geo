#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
youtube_track.py — watchdog semanal del canal: snapshot + diff vs la corrida anterior.

Gemelo de rank_track.py pero para YouTube. NO reescribe el deliverable (los títulos
optimizados son juicio/voz, no deterministas). Lo que hace es VIGILAR y avisar:
  - videos NUEVOS desde la última corrida (aún sin optimizar).
  - videos cuyo nº de issues BAJÓ (aplicaste un fix -> confirmar) o SUBIÓ (regresión).
  - crecimiento de vistas (qué video ganó tracción -> priorizar).

Lee `.tmp/youtube.json` (lo produce youtube_pull.py, córrelo antes). Historial persistente
en `youtube-history.json`. Escribe un tablero legible en `youtube-audit-status.md`.

Uso (tras youtube_pull.py):
  python execution/youtube_track.py
"""
import json
from datetime import date

from _common import ROOT, TMP

HIST = ROOT / "youtube-history.json"
STATUS = ROOT / "youtube-audit-status.md"
YT = TMP / "youtube.json"

# archivo del deliverable (para saber qué videos ya están cubiertos por optimización a mano)
DELIVERABLE = ROOT.parent.parent / "OUTPUTS" / "youtube" / "2026-07-27-optimizacion-videos-top.md"


def load_hist():
    if HIST.exists():
        try:
            return json.loads(HIST.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"snapshots": []}


def deliverable_ids():
    """IDs de video ya presentes en el deliverable (por el patron watch?v=ID)."""
    if not DELIVERABLE.exists():
        return set()
    import re
    txt = DELIVERABLE.read_text(encoding="utf-8")
    return set(re.findall(r"watch\?v=([\w-]{6,})", txt))


def main():
    if not YT.exists():
        raise SystemExit("Falta .tmp/youtube.json — corre youtube_pull.py antes.")
    yt = json.loads(YT.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    snap = {
        "date": today,
        "videos": {
            v["id"]: {
                "title": v["title"], "views": v["views"],
                "issues": len(v["issues"]), "is_short": v.get("is_short", False),
            }
            for v in yt["videos"]
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

    cov = deliverable_ids()
    cur = snap["videos"]
    con_issues = sum(1 for v in cur.values() if v["issues"])
    sin_optimizar = [(vid, v) for vid, v in cur.items() if v["issues"] and vid not in cov]

    lines = ["# YouTube — tablero de auditoría (watchdog semanal)",
             f"**Actualizado:** {today} · Canal: {yt['channel']} · {len(cur)} videos · "
             f"{con_issues} con issues · {len(cov)} cubiertos en el deliverable\n"]

    # comparacion vs anterior
    if prev:
        pv = prev["videos"]
        nuevos = [vid for vid in cur if vid not in pv]
        mejoraron = [(vid, pv[vid]["issues"], cur[vid]["issues"]) for vid in cur
                     if vid in pv and cur[vid]["issues"] < pv[vid]["issues"]]
        empeoraron = [(vid, pv[vid]["issues"], cur[vid]["issues"]) for vid in cur
                      if vid in pv and cur[vid]["issues"] > pv[vid]["issues"]]
        crecio = sorted(
            [(vid, cur[vid]["views"] - pv[vid]["views"], cur[vid]) for vid in cur
             if vid in pv and cur[vid]["views"] - pv[vid]["views"] > 0],
            key=lambda x: -x[1])
        lines.append(f"## Cambios vs {prev['date']}")
        lines.append(f"- Videos nuevos: **{len(nuevos)}** · issues resueltos en: "
                     f"**{len(mejoraron)}** · con regresión: **{len(empeoraron)}**")
        for vid in nuevos:
            v = cur[vid]
            lines.append(f"  - 🆕 NUEVO: [{v['title'][:60]}](https://youtu.be/{vid}) "
                         f"({v['issues']} issues){' [Short]' if v['is_short'] else ''}")
        for vid, a, b in mejoraron:
            lines.append(f"  - ✅ mejoró: [{cur[vid]['title'][:55]}](https://youtu.be/{vid}) "
                         f"({a}→{b} issues)")
        for vid, a, b in empeoraron:
            lines.append(f"  - ⚠️ regresión: [{cur[vid]['title'][:55]}](https://youtu.be/{vid}) "
                         f"({a}→{b} issues)")
        if crecio:
            top = crecio[0]
            lines.append(f"- Mayor crecimiento de vistas: [{top[2]['title'][:50]}]"
                         f"(https://youtu.be/{top[0]}) (+{top[1]} vistas)")
        lines.append("")
    else:
        lines.append("_Primer snapshot (baseline). La próxima corrida comparará._\n")

    # accion pendiente: videos con issues que NO estan en el deliverable
    lines.append("## Acción pendiente — videos con issues sin optimización a mano")
    if sin_optimizar:
        lines.append(f"{len(sin_optimizar)} video(s) con issues NO cubiertos en el deliverable "
                     f"(agrégalos con títulos/descr en la voz):\n")
        for vid, v in sorted(sin_optimizar, key=lambda x: -x[1]["views"]):
            lines.append(f"- [{v['title'][:60]}](https://youtu.be/{vid}) — "
                         f"{v['views']} vistas, {v['issues']} issues"
                         f"{' [Short]' if v['is_short'] else ''}")
    else:
        lines.append("_Todos los videos con issues ya están en el deliverable._")

    STATUS.write_text("\n".join(lines), encoding="utf-8")
    print(f"youtube_track: snapshot {today}. {len(cur)} videos, {con_issues} con issues. "
          f"Sin optimizar (no en deliverable): {len(sin_optimizar)}. -> {STATUS.name}")
    if prev:
        pv = prev["videos"]
        print(f"  vs {prev['date']}: nuevos={sum(1 for vid in cur if vid not in pv)} "
              f"mejoraron={sum(1 for vid in cur if vid in pv and cur[vid]['issues'] < pv[vid]['issues'])} "
              f"regresion={sum(1 for vid in cur if vid in pv and cur[vid]['issues'] > pv[vid]['issues'])}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
