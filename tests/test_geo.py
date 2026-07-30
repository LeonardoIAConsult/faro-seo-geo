"""Tests de GEO multi-motor: normalización de dominio, gating por key, evaluación."""
import _geo_engines as ge
import geo_citation as gc


def test_domain_of_url():
    assert ge.domain_of("https://www.example.com/blog/x") == "example.com"
    assert ge.domain_of("http://Ejemplo.COM/a") == "ejemplo.com"


def test_domain_of_title_like_domain():
    assert ge.domain_of("example.com") == "example.com"
    assert ge.domain_of("Sitio Sin Dominio") == ""


def test_engines_gated_without_keys(monkeypatch):
    # sin ninguna key, los tres motores devuelven None (se saltan)
    for k in ("GOOGLE_GENERATIVE_AI_API_KEY", "OPENAI_API_KEY", "PERPLEXITY_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert ge.gemini("q") is None
    assert ge.openai("q") is None
    assert ge.perplexity("q") is None


def test_engines_registry_has_three():
    assert set(ge.ENGINES) == {"gemini", "openai", "perplexity"}


def test_evaluate_cited_by_source():
    # acme-test.com = brand.domain de la config de test (conftest) -> CITADO como fuente
    status, comps = gc.evaluate("respuesta", ["acme-test.com", "competidor.com"])
    assert status.startswith("CITADO")
    assert "competidor.com" in comps


def test_evaluate_mentioned_only():
    # "acme corp" está en brand.names de la config de test (conftest) -> mencionado, no citado
    status, _ = gc.evaluate("según Acme Corp, la IA...", ["otro.com"])
    assert "mencionado" in status


def test_evaluate_absent():
    status, comps = gc.evaluate("respuesta genérica", ["a.com", "b.com"])
    assert status == "ausente"
    assert set(comps) == {"a.com", "b.com"}


def test_best_picks_highest():
    assert gc.best(["ausente", "CITADO (fuente)", "mencionado (texto)"]).startswith("CITADO")
    assert gc.best(["ausente", "mencionado (texto)"]) == "mencionado (texto)"
    assert gc.best([]) == "ausente"
