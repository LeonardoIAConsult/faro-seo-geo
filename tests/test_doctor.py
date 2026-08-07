"""Tests de doctor: lógica pura de diagnóstico (evaluate_source, classify_property,
summarize). Sin red — el probe (que sí toca la API) no se testea aquí."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "execution"))

import doctor  # noqa: E402


def _spec(*requires):
    return {"key": "k", "label": "L", "directive": "d.md", "requires": list(requires)}


def test_classify_property():
    assert doctor.classify_property("sc-domain:ejemplo.com") == "domain"
    assert doctor.classify_property("https://www.ejemplo.com/") == "web"
    assert doctor.classify_property("http://ejemplo.com") == "web"
    # las platform properties no usan http/sc-domain
    assert doctor.classify_property("@yourbrandpinzon") == "platform"
    assert doctor.classify_property("") == "platform"


def test_summarize_cuenta_por_estado():
    res = [{"status": "green"}, {"status": "green"}, {"status": "yellow"}, {"status": "red"}]
    assert doctor.summarize(res) == {"green": 2, "yellow": 1, "red": 1}


def test_env_present_y_ausente():
    spec = _spec(("env", "MI_KEY", "", "pista"))
    green = doctor.evaluate_source(spec, {"MI_KEY": "valor"}, Path("."))
    assert green["status"] == "green" and green["missing"] == []
    red = doctor.evaluate_source(spec, {"MI_KEY": ""}, Path("."))
    assert red["status"] == "red" and red["missing"][0]["name"] == "MI_KEY"


def test_env_solo_espacios_cuenta_ausente():
    spec = _spec(("env", "K", "", "h"))
    r = doctor.evaluate_source(spec, {"K": "   "}, Path("."))
    assert r["status"] == "red"


def test_file_present_por_default(tmp_path):
    (tmp_path / "token.json").write_text("{}", encoding="utf-8")
    spec = _spec(("file", "TOKEN_ENV", "token.json", "h"))
    r = doctor.evaluate_source(spec, {}, tmp_path)
    assert r["status"] == "green"


def test_file_override_por_env(tmp_path):
    (tmp_path / "custom.json").write_text("{}", encoding="utf-8")
    spec = _spec(("file", "TOKEN_ENV", "token.json", "h"))
    # el default token.json NO existe; el override sí
    r = doctor.evaluate_source(spec, {"TOKEN_ENV": "custom.json"}, tmp_path)
    assert r["status"] == "green"


def test_file_ausente_es_red(tmp_path):
    spec = _spec(("file", "TOKEN_ENV", "no-existe.json", "h"))
    r = doctor.evaluate_source(spec, {}, tmp_path)
    assert r["status"] == "red"


def test_parcial_es_yellow(tmp_path):
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    spec = _spec(
        ("file", "A", "a.json", "h"),          # presente
        ("env", "B", "", "h"),                 # ausente (requerido)
    )
    r = doctor.evaluate_source(spec, {}, tmp_path)
    assert r["status"] == "yellow"
    assert [m["name"] for m in r["missing"]] == ["B"]


def test_opcional_ausente_no_es_red(tmp_path):
    # único item es opcional → su ausencia NO baja a rojo, sino a amarillo
    spec = _spec(("env", "OPC", "", "h", True))
    r = doctor.evaluate_source(spec, {}, tmp_path)
    assert r["status"] == "yellow"


def test_todo_presente_incluyendo_opcional(tmp_path):
    spec = _spec(("env", "REQ", "", "h"), ("env", "OPC", "", "h", True))
    r = doctor.evaluate_source(spec, {"REQ": "x", "OPC": "y"}, tmp_path)
    assert r["status"] == "green"


def test_next_action_todo_verde_es_none():
    specs = [{"key": "a"}, {"key": "b"}]
    res = [{"key": "a", "status": "green"}, {"key": "b", "status": "green"}]
    assert doctor.next_action(res, specs) == None  # noqa: E711


def test_next_action_prioriza_rojo_sobre_amarillo():
    specs = [{"key": "a", "fix_cmd": "cmd-a"}, {"key": "b", "fix_cmd": "cmd-b"}]
    res = [
        {"key": "a", "status": "yellow", "label": "A", "missing": [], "directive": "a.md"},
        {"key": "b", "status": "red", "label": "B", "missing": [], "directive": "b.md"},
    ]
    nxt = doctor.next_action(res, specs)
    assert nxt["label"] == "B" and nxt["fix_cmd"] == "cmd-b"


def test_next_action_respeta_orden_de_specs_en_mismo_estado():
    specs = [{"key": "a", "fix_cmd": "cmd-a"}, {"key": "b", "fix_cmd": "cmd-b"}]
    res = [
        {"key": "b", "status": "red", "label": "B", "missing": [], "directive": "b.md"},
        {"key": "a", "status": "red", "label": "A", "missing": [], "directive": "a.md"},
    ]
    # ambos rojos → gana el que va primero en specs (a)
    assert doctor.next_action(res, specs)["label"] == "A"
