"""Tests de la lógica pura de alerts_monitor (parseo de feed + limpieza + dedup marca),
sin tocar la red."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "alerts_monitor", Path(__file__).resolve().parent.parent / "execution" / "alerts_monitor.py")
alerts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(alerts)


FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Alerta de Google - acme consultores</title>
  <entry>
    <id>tag:google.com,2013:1234</id>
    <title type="html">&lt;b&gt;Acme Consultores&lt;/b&gt; habla de IA para pymes</title>
    <link href="https://www.google.com/url?rct=j&amp;url=https://ejemplo.com/nota&amp;ct=ga"/>
    <published>2026-07-29T10:00:00Z</published>
    <content type="html">Un artículo sobre &lt;b&gt;automatización&lt;/b&gt; y negocios.</content>
  </entry>
  <entry>
    <id>tag:google.com,2013:5678</id>
    <title type="html">Noticia de nicho sin la marca</title>
    <link href="https://www.google.com/url?url=https://www.otrositio.org/x"/>
    <updated>2026-07-28T09:00:00Z</updated>
    <content type="html">Tendencias de marketing digital.</content>
  </entry>
</feed>"""


def test_clean_html():
    assert alerts.clean_html("<b>Hola</b> &amp; chau") == "Hola & chau"


def test_real_url_extrae_destino():
    href = "https://www.google.com/url?rct=j&url=https://ejemplo.com/nota&ct=ga"
    assert alerts.real_url(href) == "https://ejemplo.com/nota"


def test_real_url_vacio():
    assert alerts.real_url("") == ""


def test_source_domain_sin_www():
    assert alerts.source_domain("https://www.ejemplo.com/nota") == "ejemplo.com"


def test_is_brand_mention():
    names = ["acme consultores", "acme"]
    assert alerts.is_brand_mention("nota sobre Acme Consultores", names) is True
    assert alerts.is_brand_mention("nota genérica de seo", names) is False


def test_parse_atom_extrae_entradas():
    names = ["acme consultores"]
    out = alerts.parse_atom(FEED, names)
    assert len(out) == 2
    a = out[0]
    assert a["id"] == "tag:google.com,2013:1234"
    assert a["url"] == "https://ejemplo.com/nota"
    assert a["fuente"] == "ejemplo.com"
    assert a["marca"] is True
    assert "<" not in a["titulo"]
    assert out[1]["marca"] is False


def test_parse_atom_xml_roto_no_rompe():
    assert alerts.parse_atom("esto no es xml", []) == []
