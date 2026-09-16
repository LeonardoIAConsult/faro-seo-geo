"""seo-forge — Índice real de Google vía URL Inspection API (Capa 3, OAuth).

El resto del motor audita TU HTML en disco. Este script pregunta a Google qué
hace REALMENTE con cada URL: ¿la indexó, la excluyó (y por qué), no la conoce?
¿respetó tu canonical o eligió otra? Cierra el punto ciego más grande: el estado
de indexación real (el reporte de cobertura de GSC no tiene endpoint de export;
la URL Inspection API sí, 1 URL a la vez).

Reusa el OAuth de gsc_pull (scope webmasters.readonly YA cubre urlInspection).
Límites Google: 2.000 inspecciones/día · 600/min por propiedad → un sitio chico
entra de sobra. Datos que cambian lento → el informe marca la antigüedad (fresh_note).

Requiere:
  - credentials.json + token.json (los mismos de gsc_pull)
  - GSC_SITE_URL en .env = propiedad verificada (ej. sc-domain:example.com)

Salida: .tmp/index_inspect.json

Uso:
    python execution/index_inspect.py                 # inspecciona las URLs del sitemap
    python execution/index_inspect.py --max 100 --delay 0.2
    python execution/index_inspect.py --url https://www.example.com/blog/x.html
"""
from __future__ import annotations

import os
import sys
import time
import xml.etree.ElementTree as ET

import gsc_pull
from _common import ROOT, save_json, site_dir


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def classify(coverage: str, verdict: str) -> tuple[str, str]:
    """Pura (testeable). Devuelve (bucket, motivo). bucket ∈ indexed|excluded|unknown.
    'indexed' = Google la tiene en el índice; 'excluded' = la conoce pero NO la indexa
    (con motivo accionable); 'unknown' = aún no la descubrió."""
    c = (coverage or "").lower()
    if "unknown to google" in c:
        return ("unknown", coverage or "URL desconocida para Google")
    if verdict == "PASS" or "submitted and indexed" in c or c.strip() == "indexed":
        return ("indexed", coverage or "Indexada")
    return ("excluded", coverage or "sin estado de cobertura")


def canonical_conflict(google_canonical: str, user_canonical: str) -> bool:
    """Pura (testeable). True si Google eligió una canónica DISTINTA a la que declaraste
    (fuga real: tu <link canonical> se ignora). Compara sin barra final."""
    g = (google_canonical or "").rstrip("/")
    u = (user_canonical or "").rstrip("/")
    return bool(g and u and g != u)


def sitemap_urls(root, limit: int) -> list[str]:
    """URLs del sitemap.xml del sitio (las páginas que QUEREMOS indexadas)."""
    sm = root / "sitemap.xml"
    if not sm.exists():
        return []
    try:
        tree = ET.parse(sm)
    except ET.ParseError:
        return []
    locs = []
    for el in tree.iter():
        if el.tag.endswith("loc") and el.text:
            locs.append(el.text.strip())
    return locs[:limit] if limit else locs


def inspect(svc, site, url):
    """Una inspección. Devuelve dict normalizado o {'error': ...} (quota/permiso)."""
    try:
        r = svc.urlInspection().index().inspect(
            body={"inspectionUrl": url, "siteUrl": site}).execute()
    except Exception as e:  # quota, permiso, 5xx → no rompe el lote
        return {"url": url, "error": str(e)[:160]}
    idx = r.get("inspectionResult", {}).get("indexStatusResult", {})
    verdict = idx.get("verdict", "")
    coverage = idx.get("coverageState", "")
    bucket, motivo = classify(coverage, verdict)
    return {
        "url": url,
        "bucket": bucket,
        "motivo": motivo,
        "verdict": verdict,
        "google_canonical": idx.get("googleCanonical"),
        "user_canonical": idx.get("userCanonical"),
        "canonical_conflict": canonical_conflict(
            idx.get("googleCanonical"), idx.get("userCanonical")),
        "last_crawl": idx.get("lastCrawlTime"),
        "robots": idx.get("robotsTxtState"),
        "fetch": idx.get("pageFetchState"),
    }


def summarize(rows: list[dict]) -> dict:
    ok = [r for r in rows if "error" not in r]
    err = [r for r in rows if "error" in r]
    buckets = {"indexed": 0, "excluded": 0, "unknown": 0}
    for r in ok:
        buckets[r["bucket"]] = buckets.get(r["bucket"], 0) + 1
    excluded = [r for r in ok if r["bucket"] == "excluded"]
    unknown = [r for r in ok if r["bucket"] == "unknown"]
    conflicts = [r for r in ok if r.get("canonical_conflict")]
    return {
        "total": len(rows),
        "buckets": buckets,
        "errores": len(err),
        "excluidas": excluded,
        "desconocidas": unknown,
        "conflictos_canonical": conflicts,
        "rows": rows,
    }


ESTADO = "index-coverage-state.json"


def cargar_estado() -> dict:
    """Ultimo veredicto conocido de Google POR URL, de corridas anteriores.

    Existe porque la inspeccion se hace por lotes: en una corrida solo se preguntan unas
    pocas URLs, pero el informe y la alarma necesitan la foto del SITIO ENTERO. Sin esto,
    un lote de 35 URLs se leia como si el sitio tuviera 35 URLs, y la alarma comparaba un
    trozo contra otro trozo distinto: puro ruido.
    """
    import json
    try:
        with open(ROOT / ESTADO, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, ValueError):
        return {}


def guardar_estado(estado: dict) -> None:
    import json
    with open(ROOT / ESTADO, "w", encoding="utf-8") as fh:
        json.dump(estado, fh, ensure_ascii=False, indent=2)


def main():
    import datetime

    site = os.environ.get("GSC_SITE_URL")
    if not site:
        raise SystemExit("Define GSC_SITE_URL en .env (propiedad verificada en GSC).")
    svc = gsc_pull.service()

    one = arg("--url")
    delay = float(arg("--delay", "0.2"))
    marcador = None
    todas = []
    if one:
        urls = [one]
    else:
        limit = int(arg("--max", "300"))
        todas = sitemap_urls(site_dir(), limit)
        urls = todas
        if not todas:
            raise SystemExit(f"No hay sitemap.xml en {site_dir()} (o vacío). Pasa --url o genera el sitemap.")

        # LOTE ROTATIVO (2026-09-16). Este paso inspecciona las URLs UNA A UNA contra la URL
        # Inspection API, que va lenta por cuota: 108 URLs tardan mas de diez minutos. Esa ventana
        # tan larga es la que se lleva por delante cualquier suspension del portatil, y por eso la
        # rutina semanal moria SIEMPRE aqui —en el paso 2 de 9— dejando los cinco siguientes con
        # datos de semanas atras. El arreglo de libro (S4U, para que la tarea no cuelgue de la
        # sesion) exige ser administrador y esta cuenta no lo es.
        # Con --lote N se inspecciona solo un trozo por corrida y se va rotando: el sitio entero
        # queda cubierto en varias pasadas, y cada pasada cabe de sobra en la ventana. Lo que NO
        # se inspecciono esta corrida no desaparece: sale del estado persistente (cargar_estado).
        lote = int(arg("--lote", "0"))
        if lote > 0 and len(todas) > lote:
            marcador = ROOT / ".tmp" / "index_inspect_offset.txt"
            try:
                desde = int(marcador.read_text(encoding="utf-8").strip())
            except Exception:
                desde = 0
            desde = desde % len(todas)
            urls = (todas + todas)[desde:desde + lote]   # se da la vuelta al llegar al final
            print(f"lote rotativo: URLs {desde + 1}-{desde + lote} de {len(todas)} "
                  f"(la proxima corrida sigue donde esta lo dejo)")

    rows = []
    for i, u in enumerate(urls, 1):
        rows.append(inspect(svc, site, u))
        if i < len(urls):
            time.sleep(delay)

    # El marcador avanza AQUI, no antes: si la corrida muere a mitad del lote, la siguiente
    # repite este mismo trozo en vez de saltarselo hasta la vuelta completa.
    if marcador is not None:
        marcador.parent.mkdir(parents=True, exist_ok=True)
        marcador.write_text(str((desde + lote) % len(todas)), encoding="utf-8")

    errores_corrida = sum(1 for r in rows if "error" in r)

    if one:
        # Consulta puntual: no toca el estado del sitio ni la alarma, y se guarda APARTE.
        # Antes escribia index_inspect.json, el mismo archivo que lee el informe: un chequeo
        # de una sola URL dejaba el tablero diciendo "de 1 URL del sitemap, 1 indexada".
        data = summarize(rows)
    else:
        hoy = datetime.date.today().isoformat()
        estado = cargar_estado()
        for r in rows:
            if "error" in r:          # un fallo de cuota no borra un veredicto bueno anterior
                continue
            estado[r["url"]] = dict(r, inspeccionada=hoy)
        estado = {u: estado[u] for u in todas if u in estado}   # fuera lo que ya no esta en el sitemap
        guardar_estado(estado)

        filas_sitio = [estado[u] for u in todas if u in estado]
        data = summarize(filas_sitio)
        data["errores"] = errores_corrida
        data["inspeccionadas_esta_corrida"] = len(urls)
        data["sin_inspeccionar_nunca"] = [u for u in todas if u not in estado]
        fechas = [f.get("inspeccionada") for f in filas_sitio if f.get("inspeccionada")]
        data["dato_mas_antiguo"] = min(fechas) if fechas else None
        data["cobertura_parcial"] = len(urls) < len(todas)

    out = save_json("index_inspect_url.json" if one else "index_inspect.json", data)
    b = data["buckets"]
    print(f"index_inspect: {data['total']} URLs | indexadas={b['indexed']} "
          f"excluidas={b['excluded']} desconocidas={b['unknown']} "
          f"conflictos_canonical={len(data['conflictos_canonical'])} errores={data['errores']} -> {out}")
    if data.get("cobertura_parcial"):
        print(f"  (foto del sitio entero: {data['inspeccionadas_esta_corrida']} URLs frescas de hoy, "
              f"el resto del estado guardado; dato mas antiguo {data.get('dato_mas_antiguo')})")
    for r in data["excluidas"][:10]:
        print(f"  ✗ {r['url']} — {r['motivo']}")
    for r in data["conflictos_canonical"][:6]:
        print(f"  ⚠ canonical: {r['url']} → Google usa {r['google_canonical']}")

    if "--alert" in sys.argv and not one:
        _coverage_alert(data)


def _coverage_alert(data):
    """Auto-vigilancia: compara la indexacion con la corrida anterior; alarma Telegram si empeora.

    Compara PROPORCION (no-indexadas / total medido), no la cifra bruta. Motivo: con lotes
    rotativos el numero de URLs con veredicto crece corrida a corrida mientras se completa la
    primera vuelta, asi que la cifra bruta sube sola aunque el sitio este mejor que nunca.
    La proporcion no tiene ese sesgo. Se exige ademas que suba en absoluto, para no alarmar
    por un redondeo cuando el denominador se mueve.

    Historial en index-coverage-history.json (versionable, no secreto). Reusa el
    send_telegram de health_check (mismo bot del watchdog). Solo-lectura respecto a
    Google (no pide indexación: eso es acción de UI, sin API pública).
    """
    import datetime
    import json

    import health_check
    from _common import ROOT

    hist_path = ROOT / "index-coverage-history.json"
    b = data["buckets"]
    not_indexed = b.get("excluded", 0) + b.get("unknown", 0)
    total = data["total"] or 1
    snap = {
        "date": datetime.date.today().isoformat(),
        "total": data["total"],
        "indexed": b.get("indexed", 0),
        "excluded": b.get("excluded", 0),
        "unknown": b.get("unknown", 0),
        "not_indexed": not_indexed,
        "tasa_no_indexadas": round(not_indexed / total, 4),
        "frescas_esta_corrida": data.get("inspeccionadas_esta_corrida", data["total"]),
    }
    try:
        hist = json.load(open(hist_path, encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        hist = []
    prev = hist[-1] if hist else None
    hist.append(snap)
    with open(hist_path, "w", encoding="utf-8") as fh:
        json.dump(hist, fh, ensure_ascii=False, indent=2)

    if not prev:
        print(f"index_inspect: primera medicion ({not_indexed}/{data['total']} no indexadas)")
        return

    # Historial viejo (anterior a los lotes) no trae la tasa: se calcula de sus propias cifras.
    tasa_prev = prev.get("tasa_no_indexadas")
    if tasa_prev is None:
        tasa_prev = prev["not_indexed"] / (prev.get("total") or 1)

    empeoro = snap["tasa_no_indexadas"] > tasa_prev and not_indexed > prev["not_indexed"]
    if empeoro:
        subida = not_indexed - prev["not_indexed"]
        urls = [r["url"] for r in (data["excluidas"] + data["desconocidas"])][:8]
        msg = (
            f"[seo-forge] Indexacion EMPEORO: no-indexadas {prev['not_indexed']}/{prev.get('total', '?')}"
            f" -> {not_indexed}/{snap['total']} (+{subida}). Indexadas {snap['indexed']}/{snap['total']}."
            "\nEjemplos:\n" + "\n".join(f"- {u}" for u in urls)
        )
        health_check.send_telegram(msg)
        print(f"index_inspect: ALARMA enviada (no-indexadas +{subida})")
    elif snap["tasa_no_indexadas"] < tasa_prev:
        print(f"index_inspect: mejora {tasa_prev:.1%} -> {snap['tasa_no_indexadas']:.1%} no indexadas (sin alarma)")
    else:
        print(f"index_inspect: sin empeoramiento ({not_indexed}/{snap['total']} no indexadas)")


if __name__ == "__main__":
    main()
