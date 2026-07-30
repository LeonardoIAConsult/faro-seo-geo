"""seo-forge — auditoría técnica SEO (Capa 3), determinista sobre HTML local.

Aplica reglas y emite hallazgos con severidad. Cubre: title/meta faltantes o de mal
largo, H1 múltiples/ausentes, canonical ausente, lang ausente, imgs sin alt, JSON-LD
inválido, robots noindex accidental, duplicados de title/description.
Salida: .tmp/technical_audit.json  + resumen por stdout.

Depende de .tmp/onpage.json (corre onpage_analyze.py antes, o lo llama).
Uso:  python execution/technical_audit.py --site "<ruta>"
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from _common import TMP, cfg, save_json, site_dir

# Umbrales estándar (Google/mejores prácticas 2026) — override en seo-forge.config.json
TITLE_MIN = cfg("audit.thresholds.title_min", 30)
TITLE_MAX = cfg("audit.thresholds.title_max", 60)
DESC_MIN = cfg("audit.thresholds.desc_min", 70)
DESC_MAX = cfg("audit.thresholds.desc_max", 160)
THIN_WORDS = cfg("audit.thresholds.thin_words", 300)
# Prefijos noindex intencionales (legales/plantillas) que NO son hallazgo
NOINDEX_OK = tuple(cfg("audit.noindex_allowlist", ["/legal/", "/diagnostico/plantillas/"]))


def load_onpage(root: Path):
    f = TMP / "onpage.json"
    if not f.exists():
        subprocess.run([sys.executable, str(Path(__file__).with_name("onpage_analyze.py")),
                        "--site", str(root)], check=True)
    return json.loads(f.read_text(encoding="utf-8"))["pages"]


def audit(pages):
    findings = []

    def add(sev, url, issue, fix):
        findings.append({"severity": sev, "url": url, "issue": issue, "fix": fix})

    titles, descs = Counter(), Counter()
    for p in pages:
        u = p["url"]
        # Página noindex = no se indexa → los checks orientados a indexación
        # (schema, contenido delgado, og, imgs) no aplican y solo generan ruido.
        noindex = "noindex" in (p["meta_robots"] or "").lower()
        if p["title_len"] == 0:
            add("HIGH", u, "Sin <title>", "Agrega un title único de 30-60 chars con la keyword principal.")
        elif p["title_len"] > TITLE_MAX:
            add("MED", u, f"Title largo ({p['title_len']} chars)", f"Recorta a <= {TITLE_MAX}.")
        elif p["title_len"] < TITLE_MIN:
            add("LOW", u, f"Title corto ({p['title_len']} chars)", f"Amplía a >= {TITLE_MIN}.")
        if p["title"]:
            titles[p["title"]] += 1

        if p["meta_desc_len"] == 0 and not noindex:
            add("MED", u, "Sin meta description", "Agrega una de 70-160 chars con gancho + keyword.")
        elif p["meta_desc_len"] > DESC_MAX:
            add("LOW", u, f"Meta description larga ({p['meta_desc_len']})", f"Recorta a <= {DESC_MAX}.")
        if p["meta_description"]:
            descs[p["meta_description"]] += 1

        if p["h1_count"] == 0:
            add("HIGH", u, "Sin H1", "Agrega un único H1 descriptivo.")
        elif p["h1_count"] > 1:
            add("MED", u, f"{p['h1_count']} H1 (debe ser 1)", "Deja un solo H1; baja el resto a H2.")

        if not p["canonical"] and not noindex:
            add("MED", u, "Sin canonical", "Agrega <link rel=canonical> absoluto y autoreferente.")
        if not p["lang"]:
            add("LOW", u, "Sin atributo lang en <html>", 'Agrega lang="es".')
        if noindex:
            # noindex intencional en legales y plantillas de utilidad no es hallazgo
            # (allowlist en config). Solo alerta si aparece en contenido público.
            if not u.startswith(NOINDEX_OK):
                add("HIGH", u, "robots=noindex", "Confirma si es intencional; si no, quítalo (bloquea indexación).")
        if p["images_no_alt"] > 0 and not noindex:
            add("LOW", u, f"{p['images_no_alt']} imgs sin alt", "Agrega alt descriptivo (accesibilidad + SEO imágenes).")
        if "INVALID_JSON" in p["jsonld_types"]:
            add("HIGH", u, "JSON-LD inválido", "Corrige el schema; Google lo ignora si no parsea.")
        if not p["jsonld_types"] and not noindex:
            add("LOW", u, "Sin datos estructurados", "Agrega schema (Article/Person/etc) — ver schema_generate.py.")
        if p["word_count"] < THIN_WORDS and p["url"] not in ("/",) and not noindex:
            add("LOW", u, f"Contenido delgado ({p['word_count']} palabras)", f"Amplía a >= {THIN_WORDS} si es página de contenido.")
        if not p["og_title"] and not noindex:
            add("LOW", u, "Sin og:title", "Agrega Open Graph para mejor share en redes.")

    for t, n in titles.items():
        if n > 1:
            add("HIGH", "(varias)", f"Title duplicado en {n} páginas: “{t[:60]}…”", "Haz cada title único.")
    for d, n in descs.items():
        if n > 1:
            add("MED", "(varias)", f"Meta description duplicada en {n} páginas", "Haz cada description única.")

    return findings


def main():
    root = site_dir()
    pages = load_onpage(root)
    findings = audit(pages)
    sev = Counter(f["severity"] for f in findings)
    out = save_json("technical_audit.json", {
        "pages_audited": len(pages),
        "summary": dict(sev),
        "findings": findings,
    })
    print(f"technical_audit: {len(pages)} páginas | HIGH={sev['HIGH']} MED={sev['MED']} LOW={sev['LOW']} -> {out}")
    for f in [x for x in findings if x["severity"] == "HIGH"][:15]:
        print(f"  HIGH {f['url']}: {f['issue']}")


if __name__ == "__main__":
    main()
