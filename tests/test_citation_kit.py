"""Tests de la lógica pura de citation_kit (build_snippets + render_md/html +
guardarraíles anti-invención), sin escribir a disco ni red."""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "citation_kit", Path(__file__).resolve().parent.parent / "execution" / "citation_kit.py")
ck = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ck)


# Dict de ejemplo (mismo shape que citation-kit-data.json), local al test.
DATA = {
    "fuente": "Informe Diagnóstico E&E 2026 — 125 emprendedores",
    "url_canonica": "https://aceleracionestrategica-eye.web.app/diagnostico",
    "atribucion": "Casa Sobre la Roca · E&E 2026",
    "encuadre": "De 250+ personas mentoreadas, 12 lanzaron negocio estructurado.",
    "stats": [
        {"id": "semilla",    "cifra": "85.6%", "texto": "está en etapa Semilla"},
        {"id": "excel_wa",   "cifra": "85%",   "texto": "usa solo Excel y WhatsApp"},
        {"id": "sin_herr",   "cifra": "22%",   "texto": "no usa herramienta digital"},
        {"id": "solo_ciudad","cifra": "69.6%", "texto": "vende solo en su ciudad"},
    ],
}


def test_build_snippets_genera_4():
    snippets = ck.build_snippets(DATA)
    assert len(snippets) == 4
    assert {s["id"] for s in snippets} == {"semilla", "excel_wa", "sin_herr", "solo_ciudad"}


def test_cada_snippet_md_lleva_cifra_url_y_atribucion():
    for s in ck.build_snippets(DATA):
        assert s["cifra"] in s["md"]
        assert DATA["url_canonica"] in s["md"]
        assert DATA["atribucion"] in s["md"]


def test_cada_snippet_html_lleva_cifra_url_y_atribucion():
    import html as htmllib
    for s in ck.build_snippets(DATA):
        assert s["cifra"] in s["html"]
        assert DATA["url_canonica"] in s["html"]
        # la atribución va escapada (& → &amp;) por ser HTML válido
        assert htmllib.escape(DATA["atribucion"]) in s["html"]
        assert "<strong>" in s["html"]


def test_stat_sin_cifra_no_se_emite():
    data = dict(DATA)
    data["stats"] = [
        {"id": "sin_cifra", "cifra": "", "texto": "algo"},
        {"id": "ok", "cifra": "50%", "texto": "válido"},
    ]
    snippets = ck.build_snippets(data)
    assert len(snippets) == 1
    assert snippets[0]["id"] == "ok"


def test_sin_url_canonica_lanza_error():
    data = dict(DATA)
    data["url_canonica"] = ""
    with pytest.raises(SystemExit):
        ck.build_snippets(data)


def test_load_data_falta_archivo_lanza_error(tmp_path):
    with pytest.raises(SystemExit):
        ck.load_data(tmp_path / "no-existe.json")
