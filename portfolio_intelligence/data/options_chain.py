"""Option chain reali da Yahoo Finance: il mercato accanto alla teoria.

Il fetch è best-effort (l'endpoint opzioni di Yahoo è capriccioso): se fallisce
si restituisce None e la UI degrada alla sola stima teorica, dichiarandolo.
La logica di selezione (scadenza più vicina all'orizzonte, strike più vicino,
mid bid/ask) è pura e unit-testabile senza rete.
"""

import pandas as pd

_COLUMNS = ["strike", "bid", "ask", "lastPrice", "impliedVolatility", "volume", "openInterest"]


def nearest_expiry(expiries: list[str], target_days: int, today=None) -> str | None:
    """La scadenza quotata più vicina all'orizzonte richiesto (in giorni)."""
    if not expiries:
        return None
    today = pd.Timestamp(today) if today is not None else pd.Timestamp.now().normalize()
    scored = []
    for expiry in expiries:
        days = (pd.Timestamp(expiry) - today).days
        if days <= 0:
            continue
        scored.append((abs(days - target_days), expiry))
    if not scored:
        return None
    return min(scored)[1]


def days_to(expiry: str, today=None) -> int:
    today = pd.Timestamp(today) if today is not None else pd.Timestamp.now().normalize()
    return (pd.Timestamp(expiry) - today).days


def nearest_strike_row(table: pd.DataFrame, target_strike: float) -> pd.Series | None:
    """La riga della chain con lo strike più vicino a quello richiesto."""
    if table is None or table.empty or "strike" not in table.columns:
        return None
    valid = table.dropna(subset=["strike"])
    if valid.empty:
        return None
    idx = (valid["strike"] - target_strike).abs().idxmin()
    return valid.loc[idx]


def mid_price(row: pd.Series) -> float | None:
    """Mid bid/ask; se il book è vuoto, l'ultimo prezzo scambiato; altrimenti None."""
    bid = float(row.get("bid") or 0)
    ask = float(row.get("ask") or 0)
    if bid > 0 and ask > 0:
        return (bid + ask) / 2
    last = float(row.get("lastPrice") or 0)
    return last if last > 0 else None


def fetch_option_chain(ticker: str, kind: str, target_days: int) -> dict | None:
    """Chain reale (call o put) alla scadenza più vicina all'orizzonte.

    Restituisce {"expiry", "days", "table"} o None se Yahoo non risponde.
    """
    try:
        import yfinance as yf

        tk = yf.Ticker(ticker)
        expiries = list(tk.options or ())
        expiry = nearest_expiry(expiries, target_days)
        if expiry is None:
            return None
        chain = tk.option_chain(expiry)
        table = chain.calls if kind == "call" else chain.puts
        if table is None or table.empty:
            return None
        cols = [c for c in _COLUMNS if c in table.columns]
        return {
            "expiry": expiry,
            "days": days_to(expiry),
            "table": table[cols].reset_index(drop=True),
        }
    except Exception:
        return None
