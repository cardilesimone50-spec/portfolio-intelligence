"""Documenti legali: segnaposto riempiti dai dati societari, mai dati inventati."""

import re

import pytest

from portfolio_intelligence.ui import legal


@pytest.mark.parametrize("doc_key", list(legal.DOCS))
def test_every_placeholder_in_legal_docs_is_a_known_business_field(doc_key):
    _title, filename = legal.DOCS[doc_key]
    text = (legal.LEGAL_DIR / filename).read_text(encoding="utf-8")
    placeholders = set(re.findall(r"\{\{(\w+)\}\}", text))
    assert placeholders <= set(legal.BUSINESS_FIELDS), placeholders - set(legal.BUSINESS_FIELDS)


def test_missing_details_required_stay_visible_optional_disappear(monkeypatch):
    """Un privato senza attività commerciale non ha P.IVA/REA/PEC: quelle righe
    spariscono. Nome e contatto restano obbligatori (art. 13 GDPR)."""
    for key in legal.BUSINESS_FIELDS:
        monkeypatch.delenv(f"LEGAL_{key.upper()}", raising=False)

    text = legal.render_legal_doc("imprint")

    assert "{{" not in text
    assert "[da completare: email di contatto" in text
    assert "Partita IVA" not in text and "REA" not in text and "PEC" not in text


def test_configured_business_details_fill_the_documents(monkeypatch):
    monkeypatch.setenv("LEGAL_NAME", "Esempio S.r.l.")
    monkeypatch.setenv("LEGAL_VAT", "01234567890")

    text = legal.render_legal_doc("privacy")

    assert "Esempio S.r.l." in text
    assert "**Partita IVA**: 01234567890" in text


def test_avatar_text_meets_wcag_aa_on_every_palette_color():
    from portfolio_intelligence.ui.components import _luminance, on_color
    from portfolio_intelligence.visualization.charts import PALETTE

    def contrast(a, b):
        hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
        return (hi + 0.05) / (lo + 0.05)

    assert all(contrast(on_color(color), color) >= 4.5 for color in PALETTE)
