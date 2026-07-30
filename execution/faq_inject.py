#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
faq_inject.py — inyecta FAQPage JSON-LD en posts, desde un JSON de Q&A.

La generación de las Q&A (grounded en el texto real del post) la hace la IA
(directiva nova_content_audit). Este script SOLO inyecta de forma determinista,
para no inventar: consume `{ "<slug>.html": [{"q":"...","a":"..."}, ...], ... }`.

FAQPage es la palanca GEO #1: Google la muestra como rich result y los LLM
(ChatGPT/Perplexity) citan las respuestas directas.

Idempotente: si el post ya tiene FAQPage, lo salta. Requiere >=2 Q&A por post.
Se inyecta antes de </head>, junto al schema Article existente.

Uso:
  python execution/faq_inject.py --site "<dir>" --data faq.json [--apply]
"""
import argparse
import json
import os
import re
import sys

HAS_FAQ_RE = re.compile(r'"@type"\s*:\s*"FAQPage"', re.I)


def build_block(qas):
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": qa["q"].strip(),
                "acceptedAnswer": {"@type": "Answer", "text": qa["a"].strip()},
            }
            for qa in qas
            if qa.get("q") and qa.get("a")
        ],
    }
    js = json.dumps(data, ensure_ascii=False, indent=2)
    return '    <script type="application/ld+json">\n' + js + "\n    </script>\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--data", required=True, help="JSON {slug: [{q,a},...]}")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    faqs = json.load(open(args.data, encoding="utf-8"))
    done = 0
    skipped = 0
    for slug, qas in faqs.items():
        qas = [q for q in qas if q.get("q") and q.get("a")]
        if len(qas) < 2:
            print(f"  [skip <2 Q&A] {slug}")
            skipped += 1
            continue
        path = os.path.join(args.site, "blog", slug)
        if not os.path.isfile(path):
            print(f"  [no existe] {slug}")
            continue
        html = open(path, encoding="utf-8").read()
        if HAS_FAQ_RE.search(html):
            skipped += 1
            continue
        block = build_block(qas)
        new = html.replace("</head>", block + "</head>", 1)
        if new == html:
            print(f"  [sin </head>] {slug}")
            continue
        done += 1
        print(f"  [{len(qas)} Q&A] {slug}")
        if args.apply:
            open(path, "w", encoding="utf-8").write(new)

    mode = "APLICADO" if args.apply else "DRY-RUN (usa --apply)"
    print(f"\n{done} posts con FAQPage a inyectar ({skipped} saltados). Modo: {mode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
