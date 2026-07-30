"""seo-forge — coherencia sitemap.xml <-> archivos reales <-> robots.txt (Capa 3).

Detecta: URLs en sitemap que no existen en disco (404 potencial), páginas publicables
que faltan en el sitemap (huérfanas para el crawler), robots.txt sin Sitemap:, lastmod
ausente. Determinista, local.
Salida: .tmp/sitemap_robots.json
Uso:  python execution/sitemap_robots_check.py --site "<ruta>"
"""
from __future__ import annotations

import re
from pathlib import Path

from _common import html_files, parse, rel_url, save_json, site_dir, site_url


def is_noindex(f: Path) -> bool:
    m = parse(f).find("meta", attrs={"name": "robots"})
    return bool(m and "noindex" in (m.get("content") or "").lower())


def main():
    root = site_dir()
    su = site_url()
    findings = []

    # URLs publicables reales (en disco). Las noindex NO deben estar en el sitemap:
    # se excluyen del chequeo de "huérfanas" (su ausencia del sitemap es correcta).
    files = html_files(root)
    real = {rel_url(root, f) for f in files}
    noindex = {rel_url(root, f) for f in files if is_noindex(f)}

    # sitemap
    sm = root / "sitemap.xml"
    sitemap_urls = set()
    if not sm.exists():
        findings.append({"severity": "HIGH", "issue": "No existe sitemap.xml", "fix": "Genera uno con todas las URLs canónicas."})
    else:
        locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", sm.read_text(encoding="utf-8"))
        for loc in locs:
            path = loc.replace(su, "") or "/"
            if not path.startswith("/"):
                path = "/" + path
            sitemap_urls.add(path)
        if "<lastmod>" not in sm.read_text(encoding="utf-8"):
            findings.append({"severity": "LOW", "issue": "sitemap sin <lastmod>", "fix": "Agrega lastmod para señalar frescura."})

    # robots
    rb = root / "robots.txt"
    if not rb.exists():
        findings.append({"severity": "MED", "issue": "No existe robots.txt", "fix": "Crea uno con la línea Sitemap:."})
    else:
        txt = rb.read_text(encoding="utf-8")
        if "sitemap" not in txt.lower():
            findings.append({"severity": "MED", "issue": "robots.txt sin línea Sitemap:", "fix": f"Agrega: Sitemap: {su}/sitemap.xml"})
        if re.search(r"(?im)^\s*Disallow:\s*/\s*$", txt):
            findings.append({"severity": "HIGH", "issue": "robots.txt bloquea todo (Disallow: /)", "fix": "Revisa — impide indexación completa."})

    # cruces
    in_sitemap_not_real = sorted(sitemap_urls - real)
    real_not_in_sitemap = sorted((real - sitemap_urls) - noindex)  # noindex fuera del sitemap = correcto
    for u in in_sitemap_not_real:
        findings.append({"severity": "HIGH", "url": u, "issue": "URL en sitemap sin archivo en disco (404 potencial)", "fix": "Elimínala del sitemap o crea la página."})
    for u in real_not_in_sitemap:
        findings.append({"severity": "MED", "url": u, "issue": "Página publicable ausente del sitemap", "fix": "Agrégala al sitemap para que Google la descubra."})

    out = save_json("sitemap_robots.json", {
        "real_pages": len(real),
        "sitemap_urls": len(sitemap_urls),
        "in_sitemap_not_real": in_sitemap_not_real,
        "real_not_in_sitemap": real_not_in_sitemap,
        "findings": findings,
    })
    print(f"sitemap_robots: disco={len(real)} sitemap={len(sitemap_urls)} | huérfanas={len(real_not_in_sitemap)} fantasma={len(in_sitemap_not_real)} -> {out}")


if __name__ == "__main__":
    main()
