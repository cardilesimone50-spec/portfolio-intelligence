"""Validazione delle strutture dati di ingresso — anche quelle che arrivano dal DB.

Una riga di `prices` corrotta (data non parsabile, prezzo non numerico o <= 0)
non deve far crashare l'intero pivot in `store.load_prices`; un JSON di
posizioni corrotto in `portfolios` non deve far crashare l'intero book
dell'advisor in `store.list_portfolios`. Qui si scarta la riga/voce singola,
si logga cosa e perché, e si continua con quello che resta di valido.
"""

import json
import re

import pandas as pd

from portfolio_intelligence.logging_config import get_logger
from portfolio_intelligence.portfolio import Portfolio

log = get_logger(__name__)

# ticker ammessi: lettere, cifre e i separatori dei simboli di borsa (BRK.B, ENI.MI,
# ^IRX, EURUSD=X, BF-B). Nessun carattere che possa diventare markup HTML.
TICKER_PATTERN = re.compile(r"^[A-Z0-9^][A-Z0-9.^=\-]{0,19}$")
# codici cliente: lettere (anche accentate), cifre, spazio e - _ . /
CLIENT_CODE_PATTERN = re.compile(r"^[\w][\w .\-/]{0,59}$")


def is_valid_ticker(ticker: str) -> bool:
    return bool(TICKER_PATTERN.match(str(ticker)))


def is_valid_client_code(code: str) -> bool:
    return bool(CLIENT_CODE_PATTERN.match(str(code).strip()))


def weights_sum_to_one(portfolio: Portfolio, tolerance: float = 1e-6) -> bool:
    total = sum(position["weight"] for position in portfolio)
    return abs(total - 1.0) <= tolerance


def validate_price_rows(long: pd.DataFrame) -> pd.DataFrame:
    """Pulisce il DataFrame long (date, ticker, close) letto da `prices`.

    Scarta righe con ticker vuoto, data non parsabile o prezzo non numerico/
    non positivo; logga un warning con il conteggio degli scarti (mai silenzioso).
    """
    if long.empty:
        return long
    n_before = len(long)
    clean = long.copy()
    clean["ticker"] = clean["ticker"].astype(str).str.strip()
    clean["close"] = pd.to_numeric(clean["close"], errors="coerce")
    clean["date"] = pd.to_datetime(clean["date"], errors="coerce")
    valid = (
        clean["ticker"].ne("")
        & clean["date"].notna()
        & clean["close"].notna()
        & (clean["close"] > 0)
    )
    dropped = n_before - int(valid.sum())
    if dropped:
        log.warning(
            "validate_price_rows: scartate %d/%d righe non valide da 'prices'", dropped, n_before
        )
    return clean.loc[valid]


def safe_load_positions(advisor: str, name: str, raw: str) -> dict | None:
    """`json.loads` tollerante: su JSON corrotto logga e restituisce None
    invece di far crashare l'intero book dell'advisor in `list_portfolios`."""
    try:
        return json.loads(raw)
    except (TypeError, ValueError) as exc:
        log.warning("portfolio corrotto, scartato: advisor=%s name=%s (%s)", advisor, name, exc)
        return None
