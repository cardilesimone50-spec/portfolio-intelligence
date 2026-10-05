"""La lingua cambia i testi generati; l'inglese resta il default stabile."""

import pytest

from portfolio_intelligence.analytics.interpret import interpret_drawdown, interpret_sharpe
from portfolio_intelligence.i18n import get_language, set_language, t, t_in


@pytest.fixture(autouse=True)
def _restore_language():
    yield
    set_language("en")


def test_default_language_is_english():
    assert get_language() == "en"
    assert interpret_sharpe(0.7).startswith("In line with")


def test_italian_switches_generated_text():
    set_language("it")
    assert interpret_sharpe(0.7).startswith("In linea con")
    assert "correzione" in interpret_drawdown(-0.15)


def test_unknown_language_falls_back_to_english():
    set_language("de")
    assert get_language() == "en"


def test_missing_key_returns_key():
    assert t("no.such.key") == "no.such.key"


def test_t_in_formats_placeholders():
    assert t_in("it", "rep.page", n=2, total=4) == "Pagina 2 di 4"
    assert t_in("en", "rep.page", n=2, total=4) == "Page 2 of 4"


# ------------------------------------------------ copertura del catalogo


def _keys_used_in_code() -> set[str]:
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    files = [*root.glob("portfolio_intelligence/**/*.py"), *root.glob("app*.py")]
    # t("k"), T("k") e r.T("k") nei report, t_in(lang, "k") nei moduli puri
    pattern = re.compile(r"(?:\b[tT]\(|\bt_in\(\s*\w+\s*,)\s*[\"']([a-z_]+\.[a-z0-9_]+)[\"']")
    return {key for f in files for key in pattern.findall(f.read_text(encoding="utf-8"))}


def test_every_key_used_in_the_code_exists_in_both_languages():
    """Una chiave mancante mostrerebbe all'utente il nome tecnico della chiave."""
    from portfolio_intelligence.i18n import _CATALOG

    missing = sorted(key for key in _keys_used_in_code() if key not in _CATALOG)
    assert missing == []
    empty = sorted(key for key, (en, it) in _CATALOG.items() if not en.strip() or not it.strip())
    assert empty == []


def test_visible_texts_have_no_long_dashes():
    from portfolio_intelligence.i18n import _CATALOG

    assert [key for key, texts in _CATALOG.items() if any("—" in x for x in texts)] == []


def test_dynamic_period_and_strategy_labels_are_translated():
    from portfolio_intelligence.views.backtest import (
        CLIENT_STRATEGIES,
        HORIZON_DAYS,
        MARKET_STRATEGIES,
    )
    from portfolio_intelligence.views.common import PERIOD_DAYS

    keys = [f"mkt.p_{days}" for days in PERIOD_DAYS.values()]
    keys += [f"bt.s_{s}" for s in MARKET_STRATEGIES + CLIENT_STRATEGIES]
    keys += [f"bt.h_{h}" for h in HORIZON_DAYS]
    for key in keys:
        assert t_in("en", key) != key and t_in("it", key) != key, key


# ------------------------------------------------ numeri nella convenzione della lingua


def test_amounts_follow_the_interface_language():
    from portfolio_intelligence.ui.components import eur, num, pct, signed_eur

    assert eur(16076.4) == "€16,076"  # in inglese "16.076 €" si leggerebbe sedici euro
    assert eur(-487) == "-€487"
    assert signed_eur(9507) == "+€9,507"
    assert pct(0.3192) == "31.9%"
    assert pct(0.05, signed=True) == "+5.0%"
    assert num(1234.5, 1) == "1,234.5"
    set_language("it")
    assert eur(16076.4) == "16.076 €"
    assert eur(-487) == "-487 €"
    assert pct(0.3192) == "31,9%"
    assert num(1234.5, 1) == "1.234,5"
    assert pct(float("nan")) == "n/d"
