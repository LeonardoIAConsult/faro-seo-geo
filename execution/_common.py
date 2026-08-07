"""seo-forge — helpers compartidos (Capa 3).

Determinista, sin efectos de red salvo donde se indica. Lee el sitio ESTÁTICO
desde disco (rápido, gratis, sin rate limit) y escribe intermedios a .tmp/.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from bs4 import BeautifulSoup

# Consola Windows (cp1252) no codifica los emoji de los reportes -> UnicodeEncodeError.
# Forzamos UTF-8 en stdout/stderr una sola vez; todos los scripts importan _common.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):  # pragma: no cover
        pass

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / ".tmp"
TMP.mkdir(exist_ok=True)

if load_dotenv:
    load_dotenv(ROOT / ".env")


def _load_config() -> dict:
    """Config única del sitio (faro.config.json). Todo lo específico del sitio
    vive ahí, NO en el código → reusable en cualquier sitio (los secretos siguen en .env).
    Override por CONFIG en env var SEO_FORGE_CONFIG. Si falta, {} (los defaults por
    campo viven en cfg())."""
    path = Path(os.environ.get("SEO_FORGE_CONFIG", ROOT / "faro.config.json"))
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"WARN: faro.config.json no parsea ({e}); uso defaults.", file=sys.stderr)
    return {}


CONFIG = _load_config()


def cfg(path: str, default=None):
    """Lee un valor de la config por ruta con puntos: cfg('audit.thresholds.title_max', 60)."""
    node = CONFIG
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return default
    return node


def site_dir() -> Path:
    """Carpeta del sitio estático. Prioridad: --site (CLI) > SEO_SITE_DIR (env) > config."""
    for i, a in enumerate(sys.argv):
        if a == "--site" and i + 1 < len(sys.argv):
            return Path(sys.argv[i + 1])
    env = os.environ.get("SEO_SITE_DIR") or cfg("site.dir")
    if env:
        return Path(env)
    raise SystemExit("ERROR: pasa --site <ruta>, define SEO_SITE_DIR en .env, o site.dir en faro.config.json")


def site_url() -> str:
    """URL pública. Prioridad: SEO_SITE_URL (env) > config > default."""
    url = os.environ.get("SEO_SITE_URL") or cfg("site.url", "https://www.example.com")
    return url.rstrip("/")


def html_files(root: Path) -> list[Path]:
    """Todos los .html publicables. Política de exclusión ÚNICA (config files.skip_*),
    para que todos los auditores vean el MISMO 'sitio' (evita drift/falsos positivos)."""
    skip = set(cfg("files.skip_dirs",
                   ["_archivo", "node_modules", ".git", ".claude", ".github", ".vscode", "proyectos"]))
    skip_names = set(cfg("files.skip_files", ["hero-preview.html", "fondos-preview.html"]))
    prefixes = tuple(cfg("files.skip_name_prefixes", ["_"]))  # partials/dev: _qacards.html, etc.
    out = []
    for p in root.rglob("*.html"):
        if any(part in skip for part in p.parts):
            continue
        if p.name in skip_names or (prefixes and p.name.startswith(prefixes)):
            continue
        out.append(p)
    return sorted(out)


def rel_url(root: Path, f: Path) -> str:
    """Mapea archivo local -> URL pública (index.html -> /)."""
    rel = f.relative_to(root).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def parse(f: Path) -> BeautifulSoup:
    return BeautifulSoup(f.read_text(encoding="utf-8", errors="replace"), "lxml")


def parse_str(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def html_intact(html: str) -> bool:
    """Guardarraíl compartido: True si el HTML no quedó roto tras una edición.
    Chequea: <head>/<article> balanceados y que TODO JSON-LD parsea. Cualquier
    mutador debe llamar esto (o safe_write) antes de escribir — así el motor no
    publica un archivo roto. Generaliza el head_check de video_object.py."""
    import re as _re
    if html.count("<head") != html.count("</head>"):
        return False
    if html.count("<article") != html.count("</article>"):
        return False
    for m in _re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, _re.S | _re.I):
        try:
            json.loads(m.group(1))
        except Exception:
            return False
    return True


def safe_write(path: Path, new_html: str) -> bool:
    """Escribe new_html en path SOLO si pasa html_intact. Devuelve True si escribió,
    False si lo rechazó (deja el archivo intacto). Guardarraíl determinista para mutadores."""
    if not html_intact(new_html):
        return False
    Path(path).write_text(new_html, encoding="utf-8")
    return True


def save_json(name: str, data) -> Path:
    out = TMP / name
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def text_len(s: str | None) -> int:
    return len((s or "").strip())
