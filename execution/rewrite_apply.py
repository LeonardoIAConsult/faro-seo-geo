#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
rewrite_apply.py — aplica reescrituras de posts (fin del boilerplate duplicado).

Separa CONTENIDO (lo escribe la IA, grounded + voz de marca) de APLICACIÓN
(determinista). Por cada post reemplaza el cuerpo boilerplate por el nuevo y
limpia head: title/meta/OG/Twitter/schema/H1/alt + inyecta FAQPage.

Entradas:
  --bodies <dir>: por cada post, `<slug>.html` con SOLO el HTML del cuerpo nuevo
                  (los <p>/<h2>/<ul>… que van dentro de <article>, sin el
                  bloque de related-posts).
  --meta <json>:  { "<slug>.html": {"title","meta","faq":[{"q","a"},...]}, ... }

El cuerpo se reemplaza en la región entre <article> y <!-- related-posts -->
(o </article> si no hay marcador), preservando related-posts, CTA y footer.

Uso:
  python execution/rewrite_apply.py --site "<dir>" --bodies .tmp/bodies --meta .tmp/rw.json [--apply]
"""
import argparse
import json
import os
import re
import sys

from _common import cfg, site_url

AUTHOR = cfg("brand.author", "Example Author")  # de config brand.author
BRAND = " | " + AUTHOR
TODAY = "2026-07-27"
ORIGIN = site_url()  # de config/env (site.url)


def esc_attr(s):
    return s.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;').strip()


def faq_block(faq):
    data = {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q["q"].strip(),
                            "acceptedAnswer": {"@type": "Answer", "text": q["a"].strip()}}
                           for q in faq if q.get("q") and q.get("a")]}
    return '    <script type="application/ld+json">\n' + json.dumps(data, ensure_ascii=False) + '\n    </script>\n'


def apply_one(site, slug, body, meta):
    path = os.path.join(site, "blog", slug)
    if not os.path.isfile(path):
        return f"[no existe] {slug}"
    h = open(path, encoding="utf-8").read()
    title = meta["title"].strip()
    desc = meta["meta"].strip()
    slugbase = os.path.splitext(slug)[0]
    img = f"{ORIGIN}/blog/img/{slugbase}.webp"
    canon = f"{ORIGIN}/blog/{slug}"

    # 1) cuerpo: región entre <article> y <!-- related-posts -->
    new_body = "\n" + body.strip() + "\n        "
    h2, n = re.subn(r'(<article>).*?(\s*<!-- related-posts -->)', lambda m: m.group(1) + new_body + m.group(2), h, count=1, flags=re.S)
    if n == 0:
        h2, n = re.subn(r'(<article>).*?(</article>)', lambda m: m.group(1) + new_body + m.group(2), h, count=1, flags=re.S)
    if n == 0:
        return f"[sin <article>] {slug}"
    h = h2

    # 2) title / meta description
    h = re.sub(r'<title>.*?</title>', f'<title>{esc_attr(title)}{BRAND}</title>', h, count=1, flags=re.S)
    h = re.sub(r'(<meta name="description" content=")[^"]*(">)', lambda m: m.group(1) + esc_attr(desc) + m.group(2), h, count=1)

    # 3) OG / Twitter title + desc
    h = re.sub(r'(<meta property="og:title" content=")[^"]*(">)', lambda m: m.group(1) + esc_attr(title) + BRAND + m.group(2), h, count=1)
    h = re.sub(r'(<meta property="og:description" content=")[^"]*(">)', lambda m: m.group(1) + esc_attr(desc) + m.group(2), h, count=1)
    h = re.sub(r'(<meta name="twitter:title" content=")[^"]*(">)', lambda m: m.group(1) + esc_attr(title) + BRAND + m.group(2), h, count=1)
    h = re.sub(r'(<meta name="twitter:description" content=")[^"]*(">)', lambda m: m.group(1) + esc_attr(desc) + m.group(2), h, count=1)

    # 4) Article schema: headline + description + image + fechas (regenera el 1er bloque Article)
    art = {"@context": "https://schema.org", "@type": "Article",
           "headline": title, "description": desc, "image": img, "inLanguage": "es",
           "datePublished": "2026-07-06", "dateModified": TODAY,
           "author": {"@type": "Person", "name": AUTHOR, "url": ORIGIN},
           "publisher": {"@type": "Person", "name": AUTHOR},
           "mainEntityOfPage": canon}
    h = re.sub(r'<script type="application/ld\+json">\{"@context":"https://schema.org","@type":"Article".*?</script>',
               '<script type="application/ld+json">' + json.dumps(art, ensure_ascii=False) + '</script>', h, count=1, flags=re.S)

    # 5) FAQPage (si hay >=2 y no existe ya)
    faq = [q for q in meta.get("faq", []) if q.get("q") and q.get("a")]
    if len(faq) >= 2 and '"@type":"FAQPage"' not in h.replace(' ', '') and '"@type": "FAQPage"' not in h:
        h = h.replace('</head>', faq_block(faq) + '</head>', 1)

    # 6) H1 + alt de portada
    h = re.sub(r'<h1>.*?</h1>', f'<h1>{esc_attr(title)}</h1>', h, count=1, flags=re.S)
    h = re.sub(r'(<div class="article-cover"><img src="[^"]+" alt=")[^"]*(")',
               lambda m: m.group(1) + esc_attr(title) + m.group(2), h, count=1)

    open(path, "w", encoding="utf-8").write(h)
    words = len(re.sub(r'<[^>]+>', ' ', body).split())
    return f"[OK {words}w, {len(faq)} FAQ] {slug}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--bodies", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    meta = json.load(open(args.meta, encoding="utf-8"))
    for slug, m in meta.items():
        bpath = os.path.join(args.bodies, slug)
        if not os.path.isfile(bpath):
            print(f"[falta body] {slug}")
            continue
        body = open(bpath, encoding="utf-8").read()
        if args.apply:
            print("  " + apply_one(args.site, slug, body, m))
        else:
            print(f"  [dry] {slug} ({len(body)} chars body, {len(m.get('faq', []))} FAQ)")
    print("APLICADO" if args.apply else "DRY-RUN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
