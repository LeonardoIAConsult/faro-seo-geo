"""seo-forge — genera marcado JSON-LD (Datos estructurados) para una página (Capa 3).

Determinista: lee el HTML local, extrae señales (title, description, H1, fecha, autor,
imagen) y emite un bloque <script type="application/ld+json"> listo para pegar.
NO edita el HTML automáticamente (eso lo decide el orquestador tras revisión).

Tipos soportados: Article (blog), Person (home/perfil), BreadcrumbList, FAQPage
(si detecta patrón pregunta/respuesta), Organization, LocalBusiness (plantilla).

Uso:
    python execution/schema_generate.py --file "<ruta html>" --type Article
    python execution/schema_generate.py --file "<ruta html>" --type Person
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from _common import ROOT, cfg, site_url  # noqa
from bs4 import BeautifulSoup

# Identidad de marca — toda en faro.config.json (reusable en otro sitio).
AUTHOR = cfg("brand.author", "Your Name")
JOB_TITLE = cfg("brand.job_title", "Consultor (tu cargo)")
ORG_NAME = cfg("brand.org_name", "Your Brand")
LOGO_PATH = cfg("brand.logo_path", "/logo.svg")
PHONE = cfg("brand.phone", "")
EMAIL = cfg("brand.email", "")
AREA = cfg("brand.area_served", "Colombia")
SAMEAS = cfg("brand.sameas", [])


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def build(soup: BeautifulSoup, url_path: str, kind: str):
    su = site_url()
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    d = soup.find("meta", attrs={"name": "description"})
    desc = (d.get("content") or "").strip() if d else ""
    og = soup.find("meta", attrs={"property": "og:image"})
    img = (og.get("content") or "").strip() if og else ""
    full = su + url_path

    if kind == "Person":
        return {
            "@context": "https://schema.org", "@type": "Person", "name": AUTHOR,
            "url": su + "/", "image": img, "description": desc,
            "jobTitle": JOB_TITLE,
            "sameAs": SAMEAS,
        }
    if kind == "Organization":
        return {
            "@context": "https://schema.org", "@type": "Organization",
            "name": ORG_NAME, "url": su + "/", "logo": su + LOGO_PATH,
            "founder": {"@type": "Person", "name": AUTHOR},
        }
    if kind == "LocalBusiness":
        # Marca personal de servicios (sin dirección física pública). Usamos ProfessionalService
        # con areaServed en vez de PostalAddress. El local pack de Google se nutre del GBP, no del schema.
        return {
            "@context": "https://schema.org", "@type": "ProfessionalService",
            "name": f"{AUTHOR} — Marketing Digital e IA", "url": su + "/",
            "image": img or su + "/og-image.png", "description": desc,
            "telephone": PHONE, "email": EMAIL,
            "areaServed": {"@type": "Country", "name": AREA},
            "founder": {"@type": "Person", "name": AUTHOR}, "priceRange": "$$",
        }
    if kind == "FAQPage":
        qs = []
        for h in soup.find_all(["h2", "h3"]):
            q = h.get_text(" ", strip=True)
            if q.endswith("?") or q.lower().startswith(("qué", "cómo", "por qué", "cuándo", "cuál")):
                nxt = h.find_next(["p"])
                a = nxt.get_text(" ", strip=True) if nxt else ""
                if a:
                    qs.append({"@type": "Question", "name": q,
                               "acceptedAnswer": {"@type": "Answer", "text": a[:500]}})
        return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": qs}

    if kind == "Blog":
        # Página índice del blog: Blog + lista de posts (parseada de las tarjetas).
        posts = []
        for a in soup.select("a.blog-card"):
            href = (a.get("href") or "").strip()
            if not href:
                continue
            h = a.find(["h2", "h3", "h4"])
            name = h.get_text(" ", strip=True) if h else ""
            im = a.find("img")
            isrc = (im.get("src") or "").strip() if im else ""
            purl = href if href.startswith("http") else su + "/blog/" + href.lstrip("/")
            pimg = ""
            if isrc:
                pimg = isrc if isrc.startswith("http") else su + "/blog/" + isrc.lstrip("./")
            item = {"@type": "BlogPosting", "headline": name[:110], "url": purl}
            if pimg:
                item["image"] = pimg
            posts.append(item)
        return {
            "@context": "https://schema.org", "@type": "Blog",
            "url": su + "/blog/", "name": title[:110], "description": desc, "inLanguage": "es",
            "publisher": {"@type": "Organization", "name": ORG_NAME,
                          "logo": {"@type": "ImageObject", "url": su + LOGO_PATH}},
            "blogPost": posts,
        }

    # Article (default para blog)
    return {
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": title[:110], "description": desc, "image": img,
        "url": full, "mainEntityOfPage": full,
        "author": {"@type": "Person", "name": AUTHOR, "url": su + "/"},
        "publisher": {"@type": "Organization", "name": ORG_NAME,
                      "logo": {"@type": "ImageObject", "url": su + LOGO_PATH}},
        "inLanguage": "es",
    }


def main():
    f = arg("--file")
    kind = arg("--type", "Article")
    if not f:
        raise SystemExit("Uso: schema_generate.py --file <html> --type Article|Person|Organization|LocalBusiness|FAQPage|Blog")
    p = Path(f)
    soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "lxml")
    site = Path(os.environ.get("SEO_SITE_DIR", p.parent))
    try:
        url_path = "/" + p.relative_to(site).as_posix()
    except ValueError:
        url_path = "/" + p.name
    data = build(soup, url_path, kind)
    block = '<script type="application/ld+json">\n' + json.dumps(data, ensure_ascii=False, indent=2) + "\n</script>"
    print(block)


if __name__ == "__main__":
    main()
