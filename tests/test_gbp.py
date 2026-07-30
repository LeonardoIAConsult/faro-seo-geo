"""Tests de la lógica pura de gbp_pull (resumen de reseñas, completitud de perfil, totales de
métricas), sin tocar la red ni OAuth."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "gbp_pull", Path(__file__).resolve().parent.parent / "execution" / "gbp_pull.py")
gbp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gbp)


def test_review_summary_media_y_sin_responder():
    reviews = [
        {"starRating": "FIVE", "reviewReply": {"comment": "gracias"}},
        {"starRating": "FIVE"},
        {"starRating": "THREE"},
        {"starRating": "STAR_RATING_UNSPECIFIED"},  # no cuenta en la media
    ]
    s = gbp.review_summary(reviews)
    assert s["total"] == 4
    assert s["media"] == 4.33  # (5+5+3)/3
    assert s["sin_responder"] == 3
    assert s["distribucion"][5] == 2
    assert s["distribucion"][3] == 1


def test_review_summary_vacio():
    s = gbp.review_summary([])
    assert s["total"] == 0
    assert s["media"] == 0
    assert s["sin_responder"] == 0


def test_profile_completeness_completo():
    loc = {
        "title": "Your Brand",
        "categories": {"primaryCategory": {"displayName": "Consultor de marketing"}},
        "phoneNumbers": {"primaryPhone": "+57..."},
        "websiteUri": "https://www.example.com",
        "storefrontAddress": {"locality": "Bogotá"},
        "regularHours": {"periods": [{"openDay": "MONDAY"}]},
        "profile": {"description": "Consultoría de IA"},
    }
    c = gbp.profile_completeness(loc)
    assert c["score"] == 100
    assert c["faltan"] == []


def test_profile_completeness_incompleto():
    loc = {"title": "X", "websiteUri": "https://x.com"}
    c = gbp.profile_completeness(loc)
    assert c["score"] < 100
    assert "descripcion" in c["faltan"]
    assert "categoria_primaria" in c["faltan"]


def test_metric_totals_suma_series():
    resp = {"multiDailyMetricTimeSeries": [
        {"dailyMetricTimeSeries": [
            {"dailyMetric": "WEBSITE_CLICKS",
             "timeSeries": {"datedValues": [{"value": "3"}, {"value": "5"}, {"value": None}]}},
            {"dailyMetric": "CALL_CLICKS",
             "timeSeries": {"datedValues": [{"value": "2"}]}},
        ]}
    ]}
    t = gbp.metric_totals(resp)
    assert t["WEBSITE_CLICKS"] == 8
    assert t["CALL_CLICKS"] == 2
