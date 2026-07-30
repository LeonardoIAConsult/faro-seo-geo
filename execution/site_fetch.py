"""seo-forge — crawler que baja un sitio a disco (Capa 3, red). Escribe archivos.

Cierra el límite "auditar cuenta nueva en frío": las auditorías on-page/técnica/schema/enlaces
leen el HTML DESDE DISCO (rápido, gratis, sin rate limit). Para un prospecto cuyo repo no tienes,
este crawler descarga sus páginas mismo-dominio a una carpeta, y luego apuntas ahí `SEO_SITE_DIR`.

Guarda cada URL como archivo espejo compatible con `_common.rel_url`:
  /            -> index.html
  /blog/       -> blog/index.html         (URL con barra final)
  /pagina.html -> pagina.html             (URL con extensión)
  /servicios   -> servicios/index.html    (URL sin extensión = estilo directorio)

**Educado por defecto:** mismo dominio, respeta robots.txt, delay entre requests, límite de
páginas, User-Agent identificable. Es un GET (lectura). Úsalo en TU sitio o con permiso del dueño.

Salidas:
  <out>/...        árbol de HTML descargado (out por defecto: .tmp/site-fetch/<dominio>/)
  .tmp/site_fetch.json  -> resumen (paginas, saltadas, errores) + la ruta para SEO_SITE_DIR

Uso:
    python execution/site_fetch.py --url https://www.cliente.com --max-pages 200
    python execution/site_fetch.py --url https://www.cliente.com --out "C:/tmp/cliente" --delay 0.5
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
from urllib.robotparser import RobotFileParser

from _common import TMP, save_json, site_url


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def has_flag(name):
    return name in sys.argv


def host_of(url: str) -> str:
    h = urlparse(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def same_site(url: str, root_host: str) -> bool:
    """Mismo dominio registrable (sin www). Subdominios (cdn., shop.) = fuera, por seguridad."""
    if not url.startswith(("http://", "https://")):
        return False
    return host_of(url) == root_host


def url_to_path(base_dir: Path, url: str) -> Path:
    """Mapea URL -> archivo local espejo (compatible con _common.rel_url)."""
    path = unquote(urlparse(url).path)
    if path in ("", "/"):
        rel = "index.html"
    elif path.endswith("/"):
        rel = path.lstrip("/") + "index.html"
    elif path.endswith((".html", ".htm")):
        rel = path.lstrip("/")
    else:
        rel = path.lstrip("/") + "/index.html"
    return base_dir / rel


def is_within(base: Path, target: Path) -> bool:
    """True si `target` queda DENTRO de `base` tras resolver (bloquea traversal ../, %2e%2e)."""
    base_r = base.resolve()
    try:
        target.resolve().relative_to(base_r)
        return True
    except ValueError:
        return False


def normalize(url: str, keep_query: bool) -> str:
    """Canonicaliza: netloc en minúsculas sin www (colapsa www/no-www → misma página, evita
    doble-crawl), quita fragmento (#...) y, por defecto, el query (?...) para no crawlear infinito."""
    p = urlparse(url)
    netloc = p.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    q = ("?" + p.query) if (keep_query and p.query) else ""
    return f"{p.scheme}://{netloc}{p.path}{q}"


def clean_links(html: str, base_url: str, root_host: str, keep_query: bool):
    """Extrae enlaces mismo-sitio absolutos y normalizados de un HTML."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute = normalize(urljoin(base_url, href), keep_query)
        if same_site(absolute, root_host) and absolute not in seen:
            seen.add(absolute)
            out.append(absolute)
    return out


def is_html(content_type: str) -> bool:
    return "text/html" in (content_type or "").lower()


UA = "seo-forge site_fetch (+https://github.com/LeonardoIAConsult/faro-seo-geo)"


def robots_for(start: str, ignore: bool):
    if ignore:
        return None
    p = urlparse(start)
    rp = RobotFileParser()
    rp.set_url(f"{p.scheme}://{p.netloc}/robots.txt")
    try:
        rp.read()
    except Exception:  # noqa: BLE001 - sin robots legible = no bloquear
        return None
    return rp


def main():
    start = arg("--url") or site_url()
    if not start:
        raise SystemExit("Pasa --url https://... (o define SEO_SITE_URL).")
    start = normalize(start if start.startswith("http") else "https://" + start, False)
    root_host = host_of(start)
    max_pages = int(arg("--max-pages", "200"))
    delay = float(arg("--delay", "0.5"))
    keep_query = has_flag("--keep-query")
    out = Path(arg("--out") or (TMP / "site-fetch" / root_host))
    out.mkdir(parents=True, exist_ok=True)

    import requests
    rp = robots_for(start, has_flag("--ignore-robots"))
    sess = requests.Session()
    sess.headers["User-Agent"] = UA

    queue, seen = [start], {start}
    saved, skipped, errors = 0, 0, []

    while queue and saved < max_pages:
        url = queue.pop(0)
        if rp is not None and not rp.can_fetch(UA, url):
            skipped += 1
            continue
        try:
            r = sess.get(url, timeout=30, allow_redirects=True)
        except Exception as e:  # noqa: BLE001 - una URL caída no debe abortar el crawl
            errors.append({"url": url, "error": type(e).__name__})
            continue
        if r.status_code != 200 or not is_html(r.headers.get("Content-Type", "")):
            skipped += 1
            continue
        # CN-002: no procesar contenido si un redirect salió del dominio objetivo (SSRF/off-site).
        if not same_site(r.url, root_host):
            skipped += 1
            continue
        dest = url_to_path(out, normalize(r.url, keep_query))
        # CN-001: nunca escribir fuera del directorio de salida (path traversal vía ../ o %2e%2e).
        if not is_within(out, dest):
            skipped += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(r.text, encoding="utf-8", errors="replace")
        saved += 1
        for link in clean_links(r.text, r.url, root_host, keep_query):
            if link not in seen:
                seen.add(link)
                queue.append(link)
        if delay:
            time.sleep(delay)

    res = {
        "start": start, "dominio": root_host, "out": str(out),
        "paginas": saved, "saltadas": skipped, "errores": len(errors),
        "detalle_errores": errors[:20], "limite_alcanzado": saved >= max_pages,
    }
    save_json("site_fetch.json", res)
    print(f"site_fetch: {saved} páginas -> {out}")
    if skipped or errors:
        print(f"  saltadas {skipped} (no-HTML/robots/no-200) · errores {len(errors)}")
    if res["limite_alcanzado"]:
        print(f"  ⚠️ tope de {max_pages} páginas alcanzado (sube --max-pages si el sitio es más grande)")
    print(f"Ahora audita: define SEO_SITE_DIR=\"{out}\" (o pasa --site \"{out}\" a los scripts).")


if __name__ == "__main__":
    main()
