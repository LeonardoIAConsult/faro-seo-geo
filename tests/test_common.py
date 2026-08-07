"""Tests de _common: config, política de archivos, guardarraíl."""
import _common as c


def test_cfg_reads_config():
    # valores reales de faro.config.json
    assert c.cfg("audit.thresholds.title_max") == 60
    assert isinstance(c.cfg("files.skip_dirs"), list)
    assert "proyectos" in c.cfg("files.skip_dirs")


def test_cfg_default_on_missing():
    assert c.cfg("no.existe.esta.ruta", "fallback") == "fallback"
    assert c.cfg("otra.ruta.inexistente") is None


def test_html_files_respects_skip(site):
    files = c.html_files(site)
    names = {f.name for f in files}
    assert "index.html" in names
    assert "good-post.html" in names
    # ningún archivo dentro de un skip_dir
    for f in files:
        assert not any(part in set(c.cfg("files.skip_dirs")) for part in f.parts)


def test_html_files_skips_underscore_prefix(tmp_path):
    # los partials/dev con prefijo _ (p.ej. _qacards.html) no son páginas públicas
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "_qacards.html").write_text("<html></html>", encoding="utf-8")
    names = {f.name for f in c.html_files(tmp_path)}
    assert "index.html" in names
    assert "_qacards.html" not in names


def test_html_intact_ok():
    good = "<html><head></head><body><article>x</article></body></html>"
    assert c.html_intact(good) is True


def test_html_intact_detects_unbalanced_head():
    bad = "<html><head><body></body></html>"  # head sin cerrar
    assert c.html_intact(bad) is False


def test_html_intact_detects_broken_jsonld():
    bad = '<head><script type="application/ld+json">{no valido}</script></head>'
    assert c.html_intact(bad) is False


def test_safe_write_reverts_on_broken(tmp_path):
    f = tmp_path / "x.html"
    f.write_text("<head></head>", encoding="utf-8")
    # intenta escribir HTML roto -> debe rechazar y devolver False
    ok = c.safe_write(f, "<head><body>")
    assert ok is False


def test_safe_write_ok(tmp_path):
    f = tmp_path / "x.html"
    ok = c.safe_write(f, "<html><head></head><body>ok</body></html>")
    assert ok is True
    assert "ok" in f.read_text(encoding="utf-8")
