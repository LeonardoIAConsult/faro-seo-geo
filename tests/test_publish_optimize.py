"""Tests de publish_optimize: inlinks (string-surgery idempotente) + outlinks (bloque)."""
import publish_optimize as po
from related_posts import MARKER

# Un post hermano CON bloque de relacionados ya inyectado (formato de related_posts.build_block).
SIB_CON_BLOQUE = (
    "<html><body><article>\n"
    "  <p>cuerpo</p>\n"
    f"  {MARKER}\n"
    '  <nav class="related-posts" aria-label="Artículos relacionados">\n'
    "    <h2>Artículos relacionados</h2>\n"
    '    <ul>\n        <li><a href="otro.html">Otro</a></li>\n'
    "    </ul>\n"
    "  </nav>\n"
    "</article></body></html>\n"
)

SIB_SIN_BLOQUE = "<html><body><article><p>cuerpo</p></article></body></html>\n"

# Post VIEJO: tiene <nav class="related-posts"> pero SIN el comentario marcador
# (el caso que causaba el doble bloque). Debe detectarse como "ya tiene bloque".
SIB_NAV_VIEJO = (
    "<html><body><article>\n"
    "  <p>cuerpo</p>\n"
    '  <nav class="related-posts" aria-label="Art&iacute;culos relacionados">\n'
    "    <h2>Art&iacute;culos relacionados</h2>\n"
    '    <ul>\n        <li><a href="viejo.html">Viejo</a></li>\n'
    "    </ul>\n"
    "  </nav>\n"
    "</article></body></html>\n"
)


def test_nav_viejo_se_detecta_como_bloque_existente():
    # el fix: has_related_block True aunque NO tenga el marker (solo la clase)
    assert po.has_related_block(SIB_NAV_VIEJO) is True
    assert po.has_related_block(SIB_SIN_BLOQUE) is False


def test_add_inlink_funciona_en_nav_viejo_sin_marker():
    out = po.add_inlink(SIB_NAV_VIEJO, "nuevo.html", "Nuevo")
    assert out is not None
    assert 'href="nuevo.html"' in out
    assert out.index('href="nuevo.html"') < out.index("</ul>")


def test_ensure_outlinks_no_duplica_en_nav_viejo():
    # sin el fix, inyectaría un SEGUNDO bloque (doble). Debe devolver None.
    posts = {"nuevo.html": {"cats": {"ia"}, "title": "Nuevo"},
             "h1.html": {"cats": {"ia"}, "title": "H1"}}
    new_html, related = po.ensure_outlinks(SIB_NAV_VIEJO, "nuevo.html", posts, 4)
    assert new_html is None and related == []


def test_add_inlink_inserta_en_bloque_existente():
    out = po.add_inlink(SIB_CON_BLOQUE, "nuevo.html", "Mi Post Nuevo")
    assert out is not None
    assert 'href="nuevo.html"' in out
    assert "Mi Post Nuevo" in out
    # se insertó DENTRO del <ul> del bloque (antes del </ul>), no fuera
    assert out.index('href="nuevo.html"') < out.index("</ul>")


def test_add_inlink_idempotente_si_ya_enlaza():
    once = po.add_inlink(SIB_CON_BLOQUE, "nuevo.html", "Mi Post Nuevo")
    twice = po.add_inlink(once, "nuevo.html", "Mi Post Nuevo")
    assert twice is None  # ya lo enlaza → no duplica


def test_add_inlink_sin_bloque_devuelve_none():
    assert po.add_inlink(SIB_SIN_BLOQUE, "nuevo.html", "X") is None


def test_ensure_outlinks_no_duplica_si_ya_tiene_bloque():
    posts = {"nuevo.html": {"cats": {"ia"}, "title": "Nuevo"}}
    new_html, related = po.ensure_outlinks(SIB_CON_BLOQUE, "nuevo.html", posts, 4)
    assert new_html is None and related == []


def test_ensure_outlinks_anade_bloque_con_hermanos():
    # 3 posts del mismo cluster → el nuevo debe recibir un bloque con >=2 hermanos
    posts = {
        "nuevo.html": {"cats": {"ia"}, "title": "Nuevo"},
        "h1.html": {"cats": {"ia"}, "title": "Hermano 1"},
        "h2.html": {"cats": {"ia"}, "title": "Hermano 2"},
    }
    html = "<html><body><article><p>cuerpo</p></article></body></html>"
    new_html, related = po.ensure_outlinks(html, "nuevo.html", posts, 4)
    assert new_html is not None
    assert MARKER in new_html
    assert len(related) >= 2
