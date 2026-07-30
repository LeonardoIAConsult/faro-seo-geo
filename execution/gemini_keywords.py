"""seo-forge — keyword research + topic clusters con Gemini (Capa 3, GRATIS).

Sube la herramienta 1 (Gemini) de 🟡 parcial a 🟢: la directiva #7 pedía "IA expande +
agrupa en clusters + mapea intención + detecta gaps", pero eso vivía SOLO en la cabeza de
la IA en sesión (no persistía). Este script lo convierte en motor: alimenta a Gemini con
las semillas + tus queries REALES de GSC + los temas que YA cubre el sitio, y devuelve un
mapa de clusters PERSISTENTE (pillar -> hijos + intención + gaps), reusable por el brief.

⚠️ ALCANCE HONESTO (regla dura del proyecto): Gemini NO da volumen de búsqueda de mercado
(eso es Keyword Planner = Ads API de pago, fuera de alcance). Da EXPANSIÓN + AGRUPACIÓN +
INTENCIÓN + GAPS. El campo "volumen" queda "no disponible": nunca se inventa una cifra.

Gated: sin GOOGLE_GENERATIVE_AI_API_KEY (la misma de geo/gbrain), se salta sin romper.

Entradas:
  - semillas: --seed "a,b,c" > config keywords.seeds > config geo.queries (fallback).
  - GSC real: .tmp/gsc_queries.json (si existe) -> keywords por las que YA apareces.
  - temas del sitio: .tmp/onpage.json (si existe) -> títulos ya cubiertos (para detectar gaps).

Salida:
  .tmp/keyword_clusters.json -> {generado, semillas, clusters:[{pillar,intencion,keywords,
                                 hijos,gaps,enlazar_desde}], notas}

Uso:
    python execution/gemini_keywords.py --seed "ia para pymes,automatizar negocio"
    python execution/gemini_keywords.py                 # usa config + GSC + onpage
"""
from __future__ import annotations

import json
import re
import sys

from _common import ROOT, cfg, now, save_json
from _geo_engines import gemini_generate


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def dedup(seq):
    """Dedup case-insensitive conservando orden."""
    seen, out = set(), []
    for x in seq:
        k = str(x).strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(str(x).strip())
    return out


def seeds() -> list[str]:
    s = arg("--seed")
    if s:
        return dedup(s.split(","))
    return dedup(cfg("keywords.seeds", []) or cfg("geo.queries", []))


def gsc_queries(limit=25) -> list[str]:
    f = ROOT / ".tmp" / "gsc_queries.json"
    if not f.exists():
        return []
    try:
        rows = json.loads(f.read_text(encoding="utf-8")).get("rows", [])
    except Exception:  # noqa: BLE001
        return []
    return dedup(r.get("query", "") for r in rows[:limit])


def site_topics(limit=80) -> list[str]:
    f = ROOT / ".tmp" / "onpage.json"
    if not f.exists():
        return []
    try:
        pages = json.loads(f.read_text(encoding="utf-8")).get("pages", [])
    except Exception:  # noqa: BLE001
        return []
    return dedup(p.get("title", "") for p in pages if p.get("title"))


def strip_fences(text: str) -> str:
    """Gemini suele envolver el JSON en ```json ... ```. Devuelve el bloque JSON pelado."""
    t = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(.+?)\s*```", t, re.S)
    if m:
        return m.group(1).strip()
    # sin fences: recorta al primer { ... último }
    i, j = t.find("{"), t.rfind("}")
    return t[i:j + 1] if i != -1 and j != -1 and j > i else t


def build_prompt(seed_list, gsc, topics) -> str:
    return f"""Eres estratega SEO. Idioma: español (Colombia/Latam). Nicho: consultoría de
IA y automatización accesible para pymes y emprendedores.

SEMILLAS: {", ".join(seed_list) or "(ninguna)"}
KEYWORDS REALES DE SEARCH CONSOLE (por las que el sitio YA aparece): {", ".join(gsc) or "(ninguna aún)"}
TEMAS QUE EL SITIO YA CUBRE (títulos existentes): {" | ".join(topics[:60]) or "(desconocido)"}

Tarea:
1. Expande las semillas + queries de GSC en keywords reales que buscaría el público objetivo.
2. Agrúpalas en clusters temáticos (modelo pillar + posts hijos).
3. Para cada cluster mapea la intención dominante: informacional | comercial | transaccional | navegacional.
4. Detecta GAPS: subtemas del cluster que el sitio NO cubre todavía (candidatos a crear).
5. Para cada gap, sugiere de qué temas existentes se debería enlazar (usa los títulos dados).

NO inventes cifras de volumen de búsqueda (no las tienes). Si mencionas volumen, pon "no disponible".

Responde SOLO con JSON válido, sin texto extra, con esta forma exacta:
{{"clusters":[{{"pillar":"...","intencion":"informacional","keywords":["..."],
"hijos":["título de post hijo sugerido"],"gaps":["subtema sin cubrir"],
"enlazar_desde":["título existente relacionado"]}}],
"notas":"observaciones de canibalización o prioridad"}}"""


def parse_result(text: str) -> dict:
    """Parsea la respuesta de Gemini a dict. Si falla, guarda el crudo para inspección."""
    raw = strip_fences(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"clusters": [], "notas": "", "error_parse": True, "crudo": text[:2000]}
    if not isinstance(data, dict):
        return {"clusters": [], "notas": "", "error_parse": True, "crudo": text[:2000]}
    data.setdefault("clusters", [])
    data.setdefault("notas", "")
    return data


def main():
    seed_list = seeds()
    gsc = gsc_queries()
    if not seed_list and not gsc:
        print("Keywords: no hay semillas ni GSC. Pon keywords.seeds/geo.queries en config o pasa "
              "--seed. Se salta.")
        return

    topics = site_topics()
    prompt = build_prompt(seed_list, gsc, topics)
    text = gemini_generate(prompt)
    if text is None:
        print("Keywords: sin GOOGLE_GENERATIVE_AI_API_KEY -> Gemini apagado. Se salta (no es error). "
              "Pon la key en .env (la misma de geo/gbrain).")
        return

    data = parse_result(text)
    out = {
        "generado": now(),
        "semillas": seed_list,
        "gsc_usadas": len(gsc),
        "temas_sitio": len(topics),
        "volumen": "no disponible (sin API de pago; regla del proyecto)",
        **data,
    }
    path = save_json("keyword_clusters.json", out)

    clusters = out.get("clusters", [])
    if out.get("error_parse"):
        print(f"Keywords: Gemini respondió pero el JSON no parseó (crudo guardado) -> {path}")
        return
    print(f"Keywords: {len(clusters)} clusters -> {path}")
    for c in clusters[:8]:
        gaps = c.get("gaps", [])
        g = f" · {len(gaps)} gaps" if gaps else ""
        print(f"  [{c.get('intencion', '?'):<14}] {c.get('pillar', '(sin pillar)')}{g}")


if __name__ == "__main__":
    main()
