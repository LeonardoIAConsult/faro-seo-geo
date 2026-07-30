"""Tests de la lógica pura de site_fetch (mapeo URL→archivo, mismo-sitio, links, normalización),
sin tocar la red."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "site_fetch", Path(__file__).resolve().parent.parent / "execution" / "site_fetch.py")
sf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sf)

BASE = Path("/out")


def test_url_to_path_home():
    assert sf.url_to_path(BASE, "https://x.com/") == BASE / "index.html"
    assert sf.url_to_path(BASE, "https://x.com") == BASE / "index.html"


def test_url_to_path_dir_trailing_slash():
    assert sf.url_to_path(BASE, "https://x.com/blog/") == BASE / "blog" / "index.html"


def test_url_to_path_html_file():
    assert sf.url_to_path(BASE, "https://x.com/pagina.html") == BASE / "pagina.html"


def test_url_to_path_sin_extension_es_directorio():
    # URL sin extensión → estilo directorio (compatible con rel_url: /servicios/)
    assert sf.url_to_path(BASE, "https://x.com/servicios") == BASE / "servicios" / "index.html"


def test_host_of_quita_www():
    assert sf.host_of("https://www.Ejemplo.com/x") == "ejemplo.com"


def test_same_site():
    assert sf.same_site("https://ejemplo.com/a", "ejemplo.com") is True
    assert sf.same_site("https://www.ejemplo.com/a", "ejemplo.com") is True
    assert sf.same_site("https://cdn.ejemplo.com/a", "ejemplo.com") is False  # subdominio fuera
    assert sf.same_site("https://otro.com/a", "ejemplo.com") is False
    assert sf.same_site("mailto:a@b.com", "ejemplo.com") is False


def test_normalize_quita_fragmento_y_query():
    assert sf.normalize("https://x.com/a?b=1#frag", keep_query=False) == "https://x.com/a"
    assert sf.normalize("https://x.com/a?b=1#frag", keep_query=True) == "https://x.com/a?b=1"


def test_clean_links_filtra_externos_y_esquemas():
    html = """
    <a href="/interna">i</a>
    <a href="https://www.ejemplo.com/otra">o</a>
    <a href="https://externa.com/x">e</a>
    <a href="mailto:a@b.com">m</a>
    <a href="#seccion">s</a>
    """
    links = sf.clean_links(html, "https://ejemplo.com/base", "ejemplo.com", keep_query=False)
    assert "https://ejemplo.com/interna" in links
    assert "https://ejemplo.com/otra" in links  # www normalizado a mismo sitio
    assert all("externa.com" not in u for u in links)
    assert all("mailto" not in u for u in links)


def test_is_html():
    assert sf.is_html("text/html; charset=utf-8") is True
    assert sf.is_html("application/pdf") is False
    assert sf.is_html("") is False


def test_is_within_bloquea_traversal(tmp_path):
    out = tmp_path / "site"
    out.mkdir()
    # dentro: OK
    assert sf.is_within(out, sf.url_to_path(out, "https://x.com/blog/post")) is True
    # traversal con ../ y con %2e%2e: bloqueado (CN-001)
    assert sf.is_within(out, sf.url_to_path(out, "https://x.com/../../evil.html")) is False
    assert sf.is_within(out, sf.url_to_path(out, "https://x.com/%2e%2e/%2e%2e/evil")) is False
