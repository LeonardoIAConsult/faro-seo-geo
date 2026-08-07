#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
outreach_tracker.py — CRM ligero del PIPELINE de outreach de backlinks/PR.

El cuello de botella SEO del sitio NO es técnico: es AUTORIDAD (0 backlinks, medido
2026-07-30). `backlink_track.py` mide los backlinks que YA aterrizaron; este script
rastrea el PIPELINE que los produce: los pitches a medios, podcasts, perfiles y
comunidades que hoy nadie rastrea. Sin esto, la campaña de autoridad trabaja a ciegas
(no se sabe a quién se contactó, quién respondió, qué se ganó).

Gemelo conceptual de backlink_track (embudo → resultado): cuando un target llega a
`ganado` con su `url_conseguida`, esa URL es la que debería aparecer en el snapshot de
`backlink_track` → el `--report` lista esas URLs para cruzarlas.

Estado persistente en `outreach-tracker.json` (RAÍZ del repo, dato versionado — NO en
.tmp/ que es efímero). Determinista, sin red. Lógica pura (advance/funnel) separada de
la I/O y testeable; la fecha de hoy se pasa como parámetro (no datetime.now() dentro).

Uso:
  python execution/outreach_tracker.py --add "Contxto" --tipo medio --nota "pitch dato 125 diagnosticos"
  python execution/outreach_tracker.py --set 1 --estado enviado
  python execution/outreach_tracker.py --set 1 --estado ganado --url https://contxto.com/...
  python execution/outreach_tracker.py --list [--estado enviado]
  python execution/outreach_tracker.py --report      (sin args == --report)
"""
import argparse
import json
import sys
from datetime import date

from _common import ROOT

STORE = ROOT / "outreach-tracker.json"

# Estados válidos del embudo (constante, orden = avance típico del pipeline).
ESTADOS = ["idea", "borrador", "enviado", "respondio", "ganado", "descartado"]
# Tipos de target válidos.
TIPOS = ["medio", "podcast", "perfil", "comunidad", "guest_post"]


def new_id(targets: list[dict]) -> int:
    """Pura. Id autoincremental = max(id existentes) + 1, empezando en 1."""
    return max((int(t.get("id", 0)) for t in targets), default=0) + 1


def add_target(targets: list[dict], objetivo: str, tipo: str, today: str,
               nota: str = "") -> list[dict]:
    """Pura (testeable). Crea un target en estado `idea` con id nuevo y fecha hoy.
    Devuelve la lista actualizada (no muta la de entrada). Valida el tipo."""
    if tipo not in TIPOS:
        raise ValueError(f"tipo inválido: {tipo!r}. Válidos: {', '.join(TIPOS)}")
    if not (objetivo or "").strip():
        raise ValueError("el objetivo no puede estar vacío")
    nuevos = list(targets)
    nuevos.append({
        "id": new_id(targets),
        "objetivo": objetivo.strip(),
        "tipo": tipo,
        "estado": "idea",
        "fecha_actualizado": today,
        "url_conseguida": "",
        "nota": (nota or "").strip(),
    })
    return nuevos


def advance(targets: list[dict], target_id, estado: str, today: str,
            url: str = "", nota: str | None = None) -> list[dict]:
    """Pura (testeable). Avanza el estado de un target y actualiza su fecha.
    - Valida que `estado` esté en ESTADOS.
    - Si el nuevo estado es `ganado`, exige `url` (el backlink conseguido).
    - `nota` solo se sobrescribe si se pasa (None = se conserva la anterior).
    Devuelve la lista actualizada (no muta la de entrada)."""
    if estado not in ESTADOS:
        raise ValueError(f"estado inválido: {estado!r}. Válidos: {', '.join(ESTADOS)}")
    if estado == "ganado" and not (url or "").strip():
        raise ValueError("estado 'ganado' exige --url (la URL del backlink conseguido)")

    tid = str(target_id)
    encontrado = False
    nuevos = []
    for t in targets:
        if str(t.get("id")) == tid:
            encontrado = True
            t = dict(t)  # copia: no mutar el original
            t["estado"] = estado
            t["fecha_actualizado"] = today
            if estado == "ganado":
                t["url_conseguida"] = url.strip()
            if nota is not None:
                t["nota"] = nota.strip()
        nuevos.append(t)
    if not encontrado:
        raise ValueError(f"no existe target con id {target_id!r}")
    return nuevos


def funnel(targets: list[dict]) -> dict:
    """Pura (testeable). Embudo: conteo por estado + tasa de conversión + URLs ganadas.
    Conversión = ganado / (enviado + respondio + ganado); 0.0 si el denominador es 0
    (aún nadie ha llegado a la etapa de contacto real)."""
    conteo = {e: 0 for e in ESTADOS}
    for t in targets:
        est = t.get("estado")
        if est in conteo:
            conteo[est] += 1
    contactados = conteo["enviado"] + conteo["respondio"] + conteo["ganado"]
    conversion = (conteo["ganado"] / contactados) if contactados else 0.0
    urls_ganadas = sorted(
        (t.get("url_conseguida") or "").strip()
        for t in targets
        if t.get("estado") == "ganado" and (t.get("url_conseguida") or "").strip()
    )
    return {
        "conteo": conteo,
        "total": len(targets),
        "contactados": contactados,
        "conversion": conversion,
        "urls_ganadas": urls_ganadas,
    }


def load_store() -> dict:
    """I/O. Carga outreach-tracker.json (o vacío si no existe/parsea)."""
    if STORE.exists():
        try:
            data = json.loads(STORE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("targets"), list):
                return data
        except Exception:
            pass
    return {"targets": []}


def save_store(data: dict) -> None:
    """I/O. Persiste el estado en la raíz del repo (dato versionado)."""
    STORE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _print_list(targets: list[dict], estado: str | None = None) -> None:
    """I/O. Tabla: id · objetivo · tipo · estado · url/nota."""
    filas = [t for t in targets if not estado or t.get("estado") == estado]
    if not filas:
        print("(sin targets)" if not estado else f"(sin targets en estado '{estado}')")
        return
    print(f"{'id':<4} {'objetivo':<24} {'tipo':<11} {'estado':<11} url/nota")
    print("-" * 78)
    for t in filas:
        extra = (t.get("url_conseguida") or "").strip() or (t.get("nota") or "").strip()
        print(f"{str(t.get('id')):<4} {str(t.get('objetivo'))[:24]:<24} "
              f"{str(t.get('tipo')):<11} {str(t.get('estado')):<11} {extra}")


def _print_report(targets: list[dict]) -> None:
    """I/O. Embudo: conteo por estado + conversión + URLs ganadas (cruce con backlink_track)."""
    f = funnel(targets)
    print(f"== Embudo de outreach ({f['total']} targets) ==")
    for e in ESTADOS:
        print(f"  {e:<11} {f['conteo'][e]}")
    print(f"\nContactados (enviado+respondio+ganado): {f['contactados']}")
    print(f"Tasa de conversión (ganado/contactados): {f['conversion']:.0%}")
    if f["urls_ganadas"]:
        print("\nBacklinks ganados (cruzar con backlink_track.py):")
        for u in f["urls_ganadas"]:
            print(f"  + {u}")
    else:
        print("\nAún sin backlinks ganados. (Autoridad se construye pitch a pitch.)")


def main():
    ap = argparse.ArgumentParser(description="CRM ligero del pipeline de outreach de backlinks.")
    ap.add_argument("--add", metavar="OBJETIVO", help="crea un target nuevo (estado idea)")
    ap.add_argument("--tipo", choices=TIPOS, help="tipo del target (para --add)")
    ap.add_argument("--set", metavar="ID", help="id del target a avanzar")
    ap.add_argument("--estado", choices=ESTADOS, help="nuevo estado (para --set / filtro de --list)")
    ap.add_argument("--url", default="", help="URL conseguida (obligatoria si --estado ganado)")
    ap.add_argument("--nota", default=None, help="nota libre")
    ap.add_argument("--list", action="store_true", help="lista los targets (filtra con --estado)")
    ap.add_argument("--report", action="store_true", help="embudo + conversión + URLs ganadas")
    args = ap.parse_args()

    store = load_store()
    targets = store["targets"]

    if args.add:
        if not args.tipo:
            print("ERROR: --add requiere --tipo", file=sys.stderr)
            return 2
        today = date.today().isoformat()
        try:
            targets = add_target(targets, args.add, args.tipo, today, args.nota or "")
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        store["targets"] = targets
        save_store(store)
        nuevo = targets[-1]
        print(f"Añadido target #{nuevo['id']}: {nuevo['objetivo']} ({nuevo['tipo']}) → idea.")
        return 0

    if args.set is not None:
        if not args.estado:
            print("ERROR: --set requiere --estado", file=sys.stderr)
            return 2
        today = date.today().isoformat()
        try:
            targets = advance(targets, args.set, args.estado, today, args.url, args.nota)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        store["targets"] = targets
        save_store(store)
        print(f"Target #{args.set} → {args.estado} (actualizado {today}).")
        return 0

    if args.list:
        _print_list(targets, args.estado)
        return 0

    # Sin args (o --report) → reporte de embudo.
    _print_report(targets)
    return 0


if __name__ == "__main__":
    sys.exit(main())
