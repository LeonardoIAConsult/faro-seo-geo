"""Tests de social_audit: gating por token, señales de bio, hallazgos."""
import social_audit as sa


def test_networks_registry():
    assert set(sa.NETWORKS) == {"instagram", "facebook", "linkedin", "twitter"}


def test_all_gated_without_tokens(monkeypatch):
    for k in ("IG_ACCESS_TOKEN", "IG_USER_ID", "FB_PAGE_TOKEN", "LINKEDIN_TOKEN", "X_BEARER_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(sa, "cfg", lambda *a, **k: a[1] if len(a) > 1 else None)
    for fn in sa.NETWORKS.values():
        assert fn() is None   # sin token -> se salta


def test_bio_signals_keyword_and_link():
    s = sa._bio_signals("Consultor de IA y automatización para pymes", "https://x.com")
    assert s["bio_keyword"] is True
    assert s["bio_link"] is True
    assert s["bio_len"] > 30


def test_bio_signals_empty():
    s = sa._bio_signals("", "")
    assert s["bio_keyword"] is False
    assert s["bio_link"] is False


def test_audit_profile_flags():
    r = {"red": "instagram", "bio_len": 10, "bio_keyword": False,
         "bio_link": False, "dias_ultimo_post": 30}
    f = " ".join(sa.audit_profile(r))
    assert "bio muy corta" in f
    assert "no menciona el nicho" in f
    assert "sin link" in f
    assert "sin publicar" in f


def test_audit_profile_clean():
    r = {"red": "instagram", "bio_len": 80, "bio_keyword": True,
         "bio_link": True, "dias_ultimo_post": 2}
    assert sa.audit_profile(r) == []


def test_days_since():
    assert sa._days_since("bad") is None
