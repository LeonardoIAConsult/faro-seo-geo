"""Tests de la lógica pura de gemini_keywords (dedup + strip_fences + prompt + parseo),
sin llamar a Gemini."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "gemini_keywords", Path(__file__).resolve().parent.parent / "execution" / "gemini_keywords.py")
kw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kw)


def test_dedup_case_insensitive_conserva_orden():
    assert kw.dedup(["IA", "ia", "  automatizar ", "IA "]) == ["IA", "automatizar"]


def test_strip_fences_json_block():
    text = 'texto\n```json\n{"a": 1}\n```\nmás texto'
    assert kw.strip_fences(text) == '{"a": 1}'


def test_strip_fences_sin_fences_recorta_llaves():
    text = 'blah {"a": 1} fin'
    assert kw.strip_fences(text) == '{"a": 1}'


def test_build_prompt_incluye_semillas_y_gsc():
    p = kw.build_prompt(["ia para pymes"], ["emprende digital"], ["Título existente"])
    assert "ia para pymes" in p
    assert "emprende digital" in p
    assert "Título existente" in p
    assert "JSON" in p


def test_parse_result_ok():
    text = '```json\n{"clusters":[{"pillar":"IA para pymes","intencion":"informacional"}],"notas":"x"}\n```'
    data = kw.parse_result(text)
    assert len(data["clusters"]) == 1
    assert data["clusters"][0]["pillar"] == "IA para pymes"
    assert not data.get("error_parse")


def test_parse_result_json_invalido_marca_error():
    data = kw.parse_result("no soy json")
    assert data["error_parse"] is True
    assert data["clusters"] == []


def test_parse_result_rellena_defaults():
    data = kw.parse_result('{"clusters":[]}')
    assert "notas" in data
