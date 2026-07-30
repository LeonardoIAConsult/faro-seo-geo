"""Tests de schema_validate: requeridos por tipo + recomendados (R5)."""
import schema_validate as sv


def _check(node):
    issues, recs = [], []
    sv.check_node(node, issues, recs, "p")
    return issues, recs


def test_videoobject_missing_thumbnail_flagged():
    issues, _ = _check({"@type": "VideoObject", "name": "x", "uploadDate": "2026-01-01"})
    assert any("thumbnailUrl" in i for i in issues)


def test_videoobject_complete_ok():
    issues, _ = _check({"@type": "VideoObject", "name": "x", "thumbnailUrl": "u",
                        "uploadDate": "2026-01-01", "description": "d", "duration": "PT1M"})
    assert issues == []


def test_article_requires_author():
    issues, _ = _check({"@type": "Article", "headline": "h"})
    assert any("author" in i for i in issues)


def test_article_recommends_image_and_date():
    _, recs = _check({"@type": "Article", "headline": "h", "author": {"name": "x"}})
    joined = " ".join(recs)
    assert "image" in joined and "datePublished" in joined


def test_imageobject_requires_url():
    issues, _ = _check({"@type": "ImageObject"})
    assert any("ImageObject" in i for i in issues)
    issues2, _ = _check({"@type": "ImageObject", "contentUrl": "u"})
    assert issues2 == []


def test_organization_recommends_logo_sameas():
    _, recs = _check({"@type": "Organization", "name": "Org"})
    joined = " ".join(recs)
    assert "logo" in joined and "sameAs" in joined


def test_faqpage_incomplete_flagged():
    issues, _ = _check({"@type": "FAQPage", "mainEntity": [{"name": "q"}]})
    assert any("FAQPage" in i for i in issues)


def test_breadcrumb_complete_ok():
    issues, _ = _check({"@type": "BreadcrumbList",
                        "itemListElement": [{"position": 1, "name": "a", "item": "u"}]})
    assert issues == []


def test_videoobject_in_required():
    assert "VideoObject" in sv.REQUIRED
