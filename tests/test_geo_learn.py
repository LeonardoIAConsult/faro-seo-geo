"""Tests de geo_learn: clasificación de trayectorias + next-actions."""
import json

import geo_learn as gl


def test_status_val():
    assert gl._status_val("CITADO (fuente)") == 2
    assert gl._status_val("mencionado (texto)") == 1
    assert gl._status_val("ausente") == 0


def _hist(tmp_path):
    # 2 snapshots: A gana cita, B la pierde, C sigue ausente (hueco)
    snaps = {"snapshots": [
        {"date": "2026-07-20", "tasa_citacion": 0.33, "engines": ["gemini"], "queries": 3,
         "top_competidores": [{"dominio": "rival.com", "apariciones": 2}],
         "detalle": [
             {"query": "A", "status": "ausente", "competidores": ["rival.com"]},
             {"query": "B", "status": "CITADO (fuente)", "competidores": []},
             {"query": "C", "status": "ausente", "competidores": ["rival.com"]},
         ]},
        {"date": "2026-07-27", "tasa_citacion": 0.33, "engines": ["gemini"], "queries": 3,
         "top_competidores": [{"dominio": "rival.com", "apariciones": 2}],
         "detalle": [
             {"query": "A", "status": "CITADO (fuente)", "competidores": []},
             {"query": "B", "status": "ausente", "competidores": ["rival.com"]},
             {"query": "C", "status": "ausente", "competidores": ["rival.com"]},
         ]},
    ]}
    h = tmp_path / "hist.json"
    h.write_text(json.dumps(snaps), encoding="utf-8")
    return h


def test_classification_and_actions(tmp_path, monkeypatch):
    monkeypatch.setattr(gl, "HIST", _hist(tmp_path))
    monkeypatch.setattr(gl, "LEARN", tmp_path / "learn.md")
    monkeypatch.setattr(gl, "ACTIONS", tmp_path / "actions.json")
    rc = gl.main()
    assert rc == 0
    act = json.loads((tmp_path / "actions.json").read_text(encoding="utf-8"))
    tipos = {o["query"]: o["tipo"] for o in act["objetivos"]}
    assert tipos.get("C") == "hueco persistente"   # ausente en ambas
    assert tipos.get("B") == "cita perdida"         # perdió la cita
    assert "rival.com" in act["competidores_a_estudiar"]
    # el learnings se acumuló
    assert (tmp_path / "learn.md").exists()


def test_learnings_accumulates(tmp_path, monkeypatch):
    monkeypatch.setattr(gl, "HIST", _hist(tmp_path))
    monkeypatch.setattr(gl, "LEARN", tmp_path / "l.md")
    monkeypatch.setattr(gl, "ACTIONS", tmp_path / "a.json")
    gl.main()
    n1 = (tmp_path / "l.md").read_text(encoding="utf-8").count("corrida de aprendizaje")
    gl.main()
    n2 = (tmp_path / "l.md").read_text(encoding="utf-8").count("corrida de aprendizaje")
    assert n2 == n1 + 1   # cada corrida agrega una observación (se acumula)
