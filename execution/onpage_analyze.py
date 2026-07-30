"""seo-forge — análisis on-page determinista de todo el sitio (Capa 3).

Extrae por página: title, meta description, canonical, robots, H1..H3, OG/Twitter,
lang, hreflang, JSON-LD types, conteo de palabras, imgs sin alt, enlaces int/ext.
Salida: .tmp/onpage.json  (consumido por report_build.py, eeat, geo, briefs).

Uso:
    python execution/onpage_analyze.py --site "<ruta del sitio>"
"""
from __future__ import annotations

import json

from _common import html_files, parse, rel_url, save_json, site_dir, site_url, text_len


def analyze_page(root, f):
    soup = parse(f)
    url = rel_url(root, f)
    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    def meta(name=None, prop=None):
        if name:
            t = soup.find("meta", attrs={"name": name})
        else:
            t = soup.find("meta", attrs={"property": prop})
        return (t.get("content") or "").strip() if t else ""

    canonical = ""
    link_c = soup.find("link", rel="canonical")
    if link_c:
        canonical = (link_c.get("href") or "").strip()

    h1s = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    h2s = [h.get_text(" ", strip=True) for h in soup.find_all("h2")]

    jsonld_types = []
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "{}")
        except (json.JSONDecodeError, TypeError):
            jsonld_types.append("INVALID_JSON")
            continue
        for node in (data if isinstance(data, list) else [data]):
            if not isinstance(node, dict):
                continue
            # soporta @graph: varios nodos schema dentro de un mismo bloque
            graph = node.get("@graph")
            subnodes = graph if isinstance(graph, list) else [node]
            for sn in subnodes:
                if not isinstance(sn, dict):
                    continue
                t = sn.get("@type")
                if isinstance(t, list):
                    jsonld_types.extend(t)
                elif t:
                    jsonld_types.append(t)

    html_tag = soup.find("html")
    lang = (html_tag.get("lang") if html_tag else "") or ""
    hreflang = [ln.get("hreflang") for ln in soup.find_all("link", rel="alternate") if ln.get("hreflang")]

    imgs = soup.find_all("img")
    # alt="" (vacío) es válido para imágenes decorativas (lector de pantalla las salta);
    # solo es error cuando el atributo alt FALTA por completo.
    imgs_no_alt = [i.get("src", "?") for i in imgs if i.get("alt") is None]

    # G6: cuenta el contenido REAL, no el nav/footer global que infla el total.
    # Prefiere <main> (envuelve TODO el contenido; en páginas multi-<article> como el
    # informe, un solo <article> subcontaba), luego <article>, y si no hay, <body>.
    content = soup.find("main") or soup.find("article") or soup.find("body")
    words = len(content.get_text(" ", strip=True).split()) if content else 0

    su = site_url()
    links = soup.find_all("a", href=True)

    def _internal(h):
        # cuenta también enlaces RELATIVOS (otro-post.html, ../index.html),
        # no solo los absolutos "/..." o con el dominio. Excluye no-navegables.
        h = (h or "").strip()
        if not h or h.startswith(("mailto:", "tel:", "javascript:", "#")):
            return False
        if h.startswith("http"):
            return su in h
        return True  # relativo => interno

    internal = [a["href"] for a in links if _internal(a["href"])]
    external = [a["href"] for a in links if a["href"].startswith("http") and su not in a["href"]]

    return {
        "url": url,
        "file": str(f.name),
        "title": title,
        "title_len": text_len(title),
        "meta_description": meta(name="description"),
        "meta_desc_len": text_len(meta(name="description")),
        "meta_robots": meta(name="robots"),
        "canonical": canonical,
        "lang": lang,
        "hreflang": hreflang,
        "h1": h1s,
        "h1_count": len(h1s),
        "h2_count": len(h2s),
        "og_title": meta(prop="og:title"),
        "og_image": meta(prop="og:image"),
        "twitter_card": meta(name="twitter:card"),
        "jsonld_types": jsonld_types,
        "word_count": words,
        "images": len(imgs),
        "images_no_alt": len(imgs_no_alt),
        "images_no_alt_src": imgs_no_alt[:10],
        "internal_links": len(internal),
        "external_links": len(external),
    }


def main():
    root = site_dir()
    files = html_files(root)
    pages = [analyze_page(root, f) for f in files]
    out = save_json("onpage.json", {"site": str(root), "pages": pages, "count": len(pages)})
    print(f"onpage: {len(pages)} páginas analizadas -> {out}")


if __name__ == "__main__":
    main()
