"""seo-forge — monitor de menciones vía Google Alerts (Capa 3, feeds RSS/Atom).

Cierra el gap "Google Alerts" (herramienta 6). Google Alerts NO tiene API oficial, PERO
cada alerta puede entregarse como **feed RSS/Atom** (al crear la alerta: "Entregar a" ->
"Feed RSS"). Este script lee esos feeds, extrae las menciones, deduplica contra el historial
y marca las NUEVAS. Combustible para reputación + GEO + ideas de contenido.

⚠️ HONESTIDAD: es best-effort. Si un feed no responde, se salta sin romper. Gratis, sin key,
solo stdlib (urllib + xml.etree). Determinista: la misma entrada nunca se reporta 2 veces.

Entradas:
  - feeds: de --feed "url1,url2", o de config alerts.feeds (lista de URLs de feed).
  - marca: config brand.names -> marca cada entrada como mención de marca (True) o del nicho.

Salida:
  .tmp/alerts.json         -> {generado, feeds, total, nuevas, entradas:[...]}
  alerts-history.json      -> ids ya vistos (para no repetir; versionable, no secreto)

Uso:
    python execution/alerts_monitor.py
    python execution/alerts_monitor.py --feed "https://www.google.com/alerts/feeds/123/456"
"""
from __future__ import annotations

import html
import json
import re
import sys
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from _common import ROOT, cfg, now, save_json

HISTORY = ROOT / "alerts-history.json"
ATOM = "{http://www.w3.org/2005/Atom}"


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def clean_html(s: str) -> str:
    """Quita tags y desescapa entidades -> texto plano (los feeds traen title/content en HTML)."""
    text = re.sub(r"<[^>]+>", "", s or "")
    return html.unescape(text).strip()


def real_url(href: str) -> str:
    """Google Alerts envuelve el link en un redirect (google.com/url?url=REAL). Extrae el real."""
    if not href:
        return ""
    try:
        q = parse_qs(urlparse(href).query)
    except ValueError:
        return href
    return (q.get("url") or q.get("q") or [href])[0]


def source_domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def is_brand_mention(text: str, names: list[str]) -> bool:
    low = (text or "").lower()
    return any(n.lower() in low for n in names if n)


def parse_atom(xml_str: str, names: list[str] | None = None) -> list[dict]:
    """Parsea un feed Atom de Google Alerts -> lista de menciones. Stdlib, sin deps.
    Robusto: si el XML no parsea, devuelve [] (best-effort, no rompe)."""
    names = names or []
    # CN-003: los feeds de Alerts son chicos; cota de tamaño = defensa barata contra XML-bomb
    # (expansión de entidades) de un feed de tercero, sin sumar dependencia.
    if len(xml_str) > 5_000_000:
        return []
    try:
        root = ET.fromstring(xml_str)
    except (ET.ParseError, ValueError):
        return []
    out = []
    for e in root.iter(f"{ATOM}entry"):
        eid = (e.findtext(f"{ATOM}id") or "").strip()
        title = clean_html(e.findtext(f"{ATOM}title") or "")
        link_el = e.find(f"{ATOM}link")
        href = link_el.get("href") if link_el is not None else ""
        url = real_url(href)
        snippet = clean_html(e.findtext(f"{ATOM}content") or "")
        published = (e.findtext(f"{ATOM}published") or e.findtext(f"{ATOM}updated") or "").strip()
        if not (eid or url):
            continue
        out.append({
            "id": eid or url,
            "titulo": title,
            "url": url,
            "fuente": source_domain(url),
            "publicado": published,
            "snippet": snippet[:300],
            "marca": is_brand_mention(f"{title} {snippet}", names),
        })
    return out


def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (seo-forge alerts_monitor)"})
    with urlopen(req, timeout=30) as r:  # noqa: S310 - URL de feed la pone el usuario en config
        return r.read().decode("utf-8", errors="replace")


def load_history() -> set[str]:
    if HISTORY.exists():
        try:
            return set(json.loads(HISTORY.read_text(encoding="utf-8")).get("seen", []))
        except Exception:  # noqa: BLE001
            return set()
    return set()


def save_history(seen: set[str]) -> None:
    HISTORY.write_text(
        json.dumps({"actualizado": now(), "seen": sorted(seen)}, ensure_ascii=False, indent=2),
        encoding="utf-8")


def feeds() -> list[str]:
    f = arg("--feed")
    if f:
        return [u.strip() for u in f.split(",") if u.strip()]
    return [str(u) for u in cfg("alerts.feeds", []) if str(u).strip()]


def main():
    urls = feeds()
    if not urls:
        print("Alerts: no hay feeds. Crea alertas en google.com/alerts con entrega 'Feed RSS' "
              "y pon sus URLs en faro.config.json -> alerts.feeds (o pasa --feed). Se salta.")
        return

    names = [str(n) for n in cfg("brand.names", [])]
    seen = load_history()
    entradas, feeds_ok = [], 0

    for u in urls:
        try:
            xml_str = fetch(u)
        except Exception as e:  # noqa: BLE001 - feed no-oficial: degradar, no romper
            print(f"Alerts: no pude leer un feed ({type(e).__name__}). Se salta ese.")
            continue
        feeds_ok += 1
        for m in parse_atom(xml_str, names):
            m["nueva"] = m["id"] not in seen
            entradas.append(m)
            seen.add(m["id"])

    # dedup por id conservando orden (un mismo item puede venir en 2 feeds)
    vistos, dedup = set(), []
    for m in entradas:
        if m["id"] in vistos:
            continue
        vistos.add(m["id"])
        dedup.append(m)

    nuevas = [m for m in dedup if m["nueva"]]
    out = {
        "generado": now(),
        "feeds": feeds_ok,
        "total": len(dedup),
        "nuevas": len(nuevas),
        "entradas": dedup,
    }
    path = save_json("alerts.json", out)
    save_history(seen)

    print(f"Alerts: {len(dedup)} menciones ({feeds_ok} feeds) · {len(nuevas)} nuevas -> {path}")
    for m in nuevas[:10]:
        tag = "[MARCA]" if m["marca"] else "[nicho]"
        print(f"  {tag} {m['fuente']:<22} | {m['titulo'][:70]}")


if __name__ == "__main__":
    main()
