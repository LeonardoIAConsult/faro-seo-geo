"""Tests de la lógica pura de trends_pull (la dirección de tendencia, sin tocar pytrends)."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "trends_pull", Path(__file__).resolve().parent.parent / "execution" / "trends_pull.py")
trends = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(trends)


def test_direction_sube():
    lab, chg = trends.direction([1, 1, 2, 6, 8, 10])
    assert lab == "sube"
    assert chg > 0


def test_direction_baja():
    lab, chg = trends.direction([10, 9, 8, 2, 1, 1])
    assert lab == "baja"
    assert chg < 0


def test_direction_estable():
    lab, chg = trends.direction([5, 5, 5, 5, 5, 5])
    assert lab == "estable"
    assert chg == 0


def test_direction_sin_datos():
    lab, _ = trends.direction([1, 2])
    assert lab == "sin datos"


def test_direction_desde_cero():
    # arranca en 0 y aparece interés -> sube (sin división por cero)
    lab, chg = trends.direction([0, 0, 3, 5])
    assert lab == "sube"
    assert chg == 0
