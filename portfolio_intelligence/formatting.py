"""Numeri, importi e date nella convenzione di una lingua (modulo puro).

Usato dall'interfaccia (ui/components.py, con la lingua corrente) e dai
report PDF (con la lingua del documento): EN "€16,076" e "31.9%", IT
"16.076 €" e "31,9%". Valori mancanti o non finiti: "n/a" / "n/d".
"""

import math

import pandas as pd


def missing(lang: str) -> str:
    return "n/d" if lang == "it" else "n/a"


def _bad(value) -> bool:
    try:
        return value is None or not math.isfinite(float(value))
    except (TypeError, ValueError):
        return True


def _unsigned_zero(text: str) -> str:
    """'-0.0%' o '+0.00' → '0.0%' / '0.00': uno zero arrotondato non ha segno."""
    if text[:1] in "+-" and not any(ch in "123456789" for ch in text):
        return text[1:]
    return text


def _localize(text: str, lang: str) -> str:
    text = _unsigned_zero(text)
    if lang != "it":
        return text
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def fmt_eur(value, lang: str = "en", decimals: int = 0, signed: bool = False) -> str:
    if _bad(value):
        return missing(lang)
    value = float(value)
    digits = _localize(f"{abs(value):,.{decimals}f}", lang)
    zero = not any(ch in "123456789" for ch in digits)
    sign = "" if zero else "-" if value < 0 else ("+" if signed and value > 0 else "")
    return f"{sign}{digits} €" if lang == "it" else f"{sign}€{digits}"


def fmt_pct(value, lang: str = "en", decimals: int = 1, signed: bool = False) -> str:
    if _bad(value):
        return missing(lang)
    return _localize(f"{float(value):{'+' if signed else ''}.{decimals}%}", lang)


def fmt_num(value, lang: str = "en", decimals: int = 2, signed: bool = False) -> str:
    if _bad(value):
        return missing(lang)
    return _localize(f"{float(value):{'+' if signed else ''},.{decimals}f}", lang)


def fmt_pp(value, lang: str = "en", decimals: int = 1) -> str:
    """Differenza in punti percentuali, sempre con segno (0.034 → +3.4 pp)."""
    if _bad(value):
        return missing(lang)
    return _localize(f"{float(value) * 100:+.{decimals}f}", lang) + " pp"


def fmt_date(value, lang: str = "en") -> str:
    try:
        stamp = pd.Timestamp(value)
    except (TypeError, ValueError):
        return missing(lang)
    if pd.isna(stamp):
        return missing(lang)
    return stamp.strftime("%d/%m/%Y")


def ui_pct(value, decimals: int = 1, signed: bool = False) -> str:
    """fmt_pct nella lingua corrente dell'interfaccia (testi generati da regole)."""
    from portfolio_intelligence.i18n import get_language

    return fmt_pct(value, get_language(), decimals, signed)


def ui_num(value, decimals: int = 2) -> str:
    from portfolio_intelligence.i18n import get_language

    return fmt_num(value, get_language(), decimals)
