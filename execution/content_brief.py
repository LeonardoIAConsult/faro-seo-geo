"""seo-forge — señales SEO para un content brief (Capa 3). NO redacta.

Decisión del dueño 2026-07-28: content_brief da SOLO datos duros; la redacción en la voz
la hacen los skills de contenido (marca-content-pipeline / Desinger_LAP). Aquí reunimos
señales objetivas para una keyword objetivo:
  - CANIBALIZACIÓN: ¿ya cubrimos esta keyword? (si sí → actualizar, no duplicar)
  - GSC real: posición/impresiones/clics de la keyword exacta + queries relacionadas
  - CLÚSTER: posts relacionados (por términos) con sus inlinks/enlaces contextuales (R7)
  - LONGITUD objetivo (media del sitio vs mínimo competitivo)
  - ENLAZAR-DESDE: qué posts del clúster deberían enlazar al nuevo/actualizado

Reusa .tmp/onpage.json + gsc_queries.json + internal_links.json (los corre si faltan).
Salida: .tmp/brief_<slug>.json (señales puras, sin TODOs).

Uso:  python execution/content_brief.py --keyword "marca personal para emprendedores"
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from _common import TMP, html_files, parse, rel_url, save_json, site_dir


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# stopwords ES: no aportan a la relevancia (evitan matchear "para/como/con..." en todo)
STOP = {"para", "como", "cómo", "con", "los", "las", "del", "una", "unos", "unas", "por",
        "que", "qué", "este", "esta", "esto", "sus", "más", "mas", "sin", "sobre", "entre",
        "desde", "hasta", "cuando", "donde", "porque", "pero", "tus", "muy"}


def keyterms(kw):
    return [t for t in re.split(r"\s+", kw.lower()) if len(t) > 3 and t not in STOP]


def _load(name, ensure=None, root=None):
    f = TMP / name
    if not f.exists() and ensure:
        subprocess.run([sys.executable, str(Path(__file__).with_name(ensure)),
                        "--site", str(root)], check=False)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def gsc_signals(kw, terms):
    """Keyword exacta + relacionadas (que contienen algún término) desde GSC."""
    d = _load("gsc_queries.json")
    if not d:
        return {"exacta": None, "relacionadas": [], "nota": "sin datos GSC (corre gsc_pull.py)"}
    rows = d.get("rows", [])
    kwl = kw.lower()
    exacta = next(({"position": r["position"], "impressions": r["impressions"],
                    "clicks": r["clicks"]} for r in rows if r["query"].lower() == kwl), None)
    rel = [{"query": r["query"], "position": r["position"], "impressions": r["impressions"]}
           for r in rows if r["query"].lower() != kwl
           and any(t in r["query"].lower() for t in terms)]
    rel.sort(key=lambda x: x["impressions"], reverse=True)
    return {"exacta": exacta, "relacionadas": rel[:8]}


def main():
    kw = arg("--keyword")
    if not kw:
        raise SystemExit('Uso: content_brief.py --keyword "..."')
    root = site_dir()
    terms = keyterms(kw)

    onpage = _load("onpage.json", ensure="onpage_analyze.py", root=root)
    ilinks = _load("internal_links.json", ensure="internal_links.py", root=root)
    il_by_url = {p["url"]: p for p in (ilinks["pages"] if ilinks else [])}

    # matching por contenido (re-parse: es 1 keyword, barato). Usa longitud de onpage (DRY).
    words_by_url = {p["url"]: p["word_count"] for p in onpage["pages"]} if onpage else {}
    related, exact = [], []
    for f in html_files(root):
        url = rel_url(root, f)
        soup = parse(f)
        title = (soup.title.string or "").strip() if soup.title else ""
        body = soup.find("body")
        text = body.get_text(" ", strip=True).lower() if body else ""
        score = sum(text.count(t) for t in terms)
        # canibalización = la keyword está en el TÍTULO (la página apunta a esa keyword).
        # Que aparezca en el cuerpo NO es canibalizar (eso es solo tema relacionado).
        if kw.lower() in title.lower():
            exact.append({"url": url, "title": title})
        if score > 0:
            il = il_by_url.get(url, {})
            related.append({"url": url, "title": title, "relevance": score,
                            "words": words_by_url.get(url, 0),
                            "inlinks": il.get("inlinks"), "ctx_outlinks": il.get("ctx_outlinks")})

    related.sort(key=lambda r: r["relevance"], reverse=True)
    lengths = list(words_by_url.values())
    avg = round(sum(lengths) / len(lengths)) if lengths else 0

    # enlazar-desde: top posts del clúster que deberían enlazar al target
    enlazar_desde = [r["url"] for r in related[:6]]

    brief = {
        "keyword": kw,
        "recomendacion": "actualizar la existente (no duplicar)" if exact else "crear nueva",
        "canibalizacion": exact,
        "gsc": gsc_signals(kw, terms),
        "cluster": {"posts_relacionados": related[:8]},
        "longitud": {"media_sitio": avg, "target_sugerido": max(avg, 900)},
        "enlazado": {"enlazar_desde": enlazar_desde,
                     "nota": "agrega un enlace contextual al nuevo post desde estos (cluster)"},
    }
    out = save_json(f"brief_{slug(kw)}.json", brief)
    canib = "YA CUBIERTA (actualizar)" if exact else "libre (crear nueva)"
    gx = brief["gsc"]["exacta"]
    gtxt = f"GSC pos {gx['position']} ({gx['impressions']} imp)" if gx else "sin datos GSC exactos"
    print(f"brief '{kw}': {canib} | {len(related)} relacionados | {gtxt} | "
          f"target ~{brief['longitud']['target_sugerido']} palabras -> {out}")


if __name__ == "__main__":
    main()
