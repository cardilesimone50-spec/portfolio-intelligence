"""La lingua cambia i testi generati; l'inglese resta il default stabile."""

import pytest

from src.analytics.interpret import interpret_drawdown, interpret_sharpe
from src.i18n import get_language, set_language, t, t_in


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
    assert t_in("it", "pdf.page", n=2) == "Pagina 2 di 3"
    assert t_in("en", "pdf.page", n=2) == "Page 2 of 3"
