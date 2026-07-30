"""Tests de onpage_analyze: extracción correcta de señales por página."""


def test_good_home(page_by_name):
    p = page_by_name("index.html")
    assert 30 <= p["title_len"] <= 70
    assert p["h1_count"] == 1
    assert p["lang"] == "es"
    assert p["canonical"]
    assert "Person" in p["jsonld_types"]
    assert p["images_no_alt"] == 0
    assert p["word_count"] > 150   # home con contenido real (no delgado)


def test_bad_post(page_by_name):
    p = page_by_name("bad-post.html")
    assert p["title_len"] == 0          # sin <title>
    assert p["h1_count"] == 0           # sin H1
    assert p["lang"] == ""              # sin lang
    assert not p["canonical"]           # sin canonical
    assert "INVALID_JSON" in p["jsonld_types"]  # JSON-LD roto detectado
    assert p["images_no_alt"] >= 1      # img sin alt


def test_good_post_schema_types(page_by_name):
    p = page_by_name("good-post.html")
    assert "Article" in p["jsonld_types"]
    assert "FAQPage" in p["jsonld_types"]
    assert p["internal_links"] >= 1     # enlaza a ../index.html


def test_decorative_alt_not_counted(page_by_name):
    # el post bueno usa alt no vacío; no debe contar como "sin alt"
    p = page_by_name("good-post.html")
    assert p["images_no_alt"] == 0


def test_word_count_excludes_nav_footer(tmp_path):
    # G6: word_count cuenta <article>, no el nav/footer que lo rodea
    import onpage_analyze as op
    nav = "<nav>" + " ".join(["menu"] * 200) + "</nav>"
    footer = "<footer>" + " ".join(["pie"] * 200) + "</footer>"
    html = f"<html><body>{nav}<article>uno dos tres cuatro cinco</article>{footer}</body></html>"
    f = tmp_path / "x.html"
    f.write_text(html, encoding="utf-8")
    p = op.analyze_page(tmp_path, f)
    assert p["word_count"] == 5   # solo el <article>, no los 400 de nav+footer


def test_word_count_multi_article_uses_main(tmp_path):
    # G6 regresión: una página con <main> envolviendo VARIOS <article> no debe
    # contar solo el primero (antes subcontaba: 30 en vez de 673 en el informe real)
    import onpage_analyze as op
    a1 = "<article>" + " ".join(["uno"] * 10) + "</article>"
    a2 = "<article>" + " ".join(["dos"] * 20) + "</article>"
    html = f"<html><body><nav>menu menu</nav><main>{a1}{a2}</main><footer>pie</footer></body></html>"
    f = tmp_path / "m.html"
    f.write_text(html, encoding="utf-8")
    p = op.analyze_page(tmp_path, f)
    assert p["word_count"] == 30   # 10 + 20 (todo el <main>), no solo el 1er article
