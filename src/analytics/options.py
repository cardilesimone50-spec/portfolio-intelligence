"""Overlay di opzioni sul portafoglio: protezione dei guadagni e rendita.

Tre strategie da manuale, calcolate con Black-Scholes sulla volatilità
REALIZZATA del titolo (quella che già misuriamo):

- put protettiva: assicura un prezzo minimo di vendita → blocca il P&L
  non realizzato (al netto del premio pagato);
- covered call: vende upside oltre uno strike in cambio di un premio → rendita;
- collar a costo zero: la vendita della call finanzia la put → protezione
  (quasi) gratuita, rinunciando all'upside oltre lo strike della call.

ONESTÀ: sono stime teoriche (nessuna superficie di volatilità, dividendi
ignorati, esercizio europeo); i prezzi di mercato differiranno. Nessuna
strategia garantisce profitto: la put blocca un valore minimo SOLO al netto
del premio e fino alla scadenza. Non è consulenza né raccomandazione.
"""

from math import erf, exp, log, sqrt

import pandas as pd

TRADING_DAYS = 252


def _mid_series(table: pd.DataFrame) -> pd.Series:
    """Mid denaro/lettera per riga; fallback ultimo scambio; NaN se nulla."""
    bid = pd.to_numeric(table.get("bid"), errors="coerce").fillna(0.0)
    ask = pd.to_numeric(table.get("ask"), errors="coerce").fillna(0.0)
    last = pd.to_numeric(table.get("lastPrice"), errors="coerce").fillna(0.0)
    mid = (bid + ask) / 2
    mid = mid.where((bid > 0) & (ask > 0), last)
    return mid.where(mid > 0)


def protection_table(
    table: pd.DataFrame,
    spot: float,
    days: int,
    cost_basis: float | None = None,
    qty: float = 1.0,
    fx: float = 1.0,
    lo: float = 0.80,
    hi: float = 1.001,
) -> pd.DataFrame:
    """Confronto fattuale delle put reali tra lo `lo` e lo `hi` del prezzo.

    Nessuna raccomandazione: per ogni contratto quotato mostra costo, pavimento
    e — dato il carico — il P&L minimo bloccato. Colonne: strike, strike_pct,
    mid, cost_pct, cost_month_pct, floor, locked_pnl, iv, oi.
    """
    if table is None or table.empty or spot <= 0:
        return pd.DataFrame()
    rows = table.copy()
    rows["strike"] = pd.to_numeric(rows.get("strike"), errors="coerce")
    rows["mid"] = _mid_series(rows)
    rows = rows.dropna(subset=["strike", "mid"])
    rows = rows[(rows["strike"] >= spot * lo) & (rows["strike"] <= spot * hi)]
    if rows.empty:
        return pd.DataFrame()
    out = pd.DataFrame(index=rows.index)
    out["strike"] = rows["strike"]
    out["strike_pct"] = rows["strike"] / spot
    out["mid"] = rows["mid"]
    out["cost_pct"] = rows["mid"] / spot
    out["cost_month_pct"] = out["cost_pct"] / max(days / 30.0, 0.1)
    out["floor"] = rows["strike"] - rows["mid"]
    out["locked_pnl"] = (
        (out["floor"] - cost_basis) * qty * fx if cost_basis is not None else float("nan")
    )
    out["iv"] = pd.to_numeric(rows.get("impliedVolatility"), errors="coerce")
    out["oi"] = pd.to_numeric(rows.get("openInterest"), errors="coerce")
    return out.sort_values("strike", ascending=False).reset_index(drop=True)


def income_table(
    table: pd.DataFrame,
    spot: float,
    days: int,
    qty: float = 1.0,
    fx: float = 1.0,
    lo: float = 0.999,
    hi: float = 1.20,
) -> pd.DataFrame:
    """Confronto fattuale delle call reali per la covered call (rendita).

    Colonne: strike, strike_pct, mid, yield_pct (periodo), yield_ann,
    income (premio × quantità in valuta di visualizzazione), iv, oi.
    """
    if table is None or table.empty or spot <= 0:
        return pd.DataFrame()
    rows = table.copy()
    rows["strike"] = pd.to_numeric(rows.get("strike"), errors="coerce")
    rows["mid"] = _mid_series(rows)
    rows = rows.dropna(subset=["strike", "mid"])
    rows = rows[(rows["strike"] >= spot * lo) & (rows["strike"] <= spot * hi)]
    if rows.empty:
        return pd.DataFrame()
    out = pd.DataFrame(index=rows.index)
    out["strike"] = rows["strike"]
    out["strike_pct"] = rows["strike"] / spot
    out["mid"] = rows["mid"]
    out["yield_pct"] = rows["mid"] / spot
    out["yield_ann"] = out["yield_pct"] * 365.0 / max(days, 1)
    out["income"] = rows["mid"] * qty * fx
    out["iv"] = pd.to_numeric(rows.get("impliedVolatility"), errors="coerce")
    out["oi"] = pd.to_numeric(rows.get("openInterest"), errors="coerce")
    return out.sort_values("strike", ascending=True).reset_index(drop=True)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def bs_price(kind: str, spot: float, strike: float, years: float, sigma: float,
             rate: float = 0.0) -> float:
    """Prezzo Black-Scholes (europeo, senza dividendi) di call o put."""
    if years <= 0 or sigma <= 0 or spot <= 0 or strike <= 0:
        raise ValueError("spot, strike, years and sigma must be positive")
    d1 = (log(spot / strike) + (rate + sigma**2 / 2) * years) / (sigma * sqrt(years))
    d2 = d1 - sigma * sqrt(years)
    if kind == "call":
        return spot * _norm_cdf(d1) - strike * exp(-rate * years) * _norm_cdf(d2)
    if kind == "put":
        return strike * exp(-rate * years) * _norm_cdf(-d2) - spot * _norm_cdf(-d1)
    raise ValueError(f"Unknown option kind: {kind}")


def protective_put(
    spot: float,
    sigma: float,
    rate: float = 0.0,
    strike_pct: float = 0.95,
    days: int = 90,
    cost_basis: float | None = None,
) -> dict:
    """Put protettiva: quanto costa assicurare un prezzo minimo di vendita.

    `floor_exit` = strike − premio: il ricavo minimo per azione se si esercita
    alla scadenza. Con `cost_basis` (carico per azione) si calcola anche il
    P&L minimo bloccato per azione.
    """
    years = days / 365.0
    strike = spot * strike_pct
    premium = bs_price("put", spot, strike, years, sigma, rate)
    floor_exit = strike - premium
    return {
        "strike": strike,
        "premium": premium,
        "premium_pct": premium / spot,
        "floor_exit": floor_exit,
        "locked_pnl": (floor_exit - cost_basis) if cost_basis is not None else None,
        "days": days,
    }


def covered_call(
    spot: float,
    sigma: float,
    rate: float = 0.0,
    strike_pct: float = 1.05,
    days: int = 90,
) -> dict:
    """Covered call: premio incassato vendendo upside oltre lo strike.

    `yield_pct` = premio/spot sul periodo; `cap` = strike: oltre quel prezzo
    le azioni vengono consegnate (upside rinunciato).
    """
    years = days / 365.0
    strike = spot * strike_pct
    premium = bs_price("call", spot, strike, years, sigma, rate)
    return {
        "strike": strike,
        "premium": premium,
        "yield_pct": premium / spot,
        "cap": strike,
        "days": days,
    }


def zero_cost_collar(
    spot: float,
    sigma: float,
    rate: float = 0.0,
    put_strike_pct: float = 0.95,
    days: int = 90,
    cost_basis: float | None = None,
) -> dict:
    """Collar a costo zero: lo strike della call che finanzia la put protettiva.

    Bisezione sullo strike della call in [spot, 3×spot] finché il premio della
    call eguaglia quello della put. Risultato: prezzo minimo garantito (strike
    put) e massimo (strike call) a premio netto ~zero.
    """
    years = days / 365.0
    put_strike = spot * put_strike_pct
    put_premium = bs_price("put", spot, put_strike, years, sigma, rate)

    lo, hi = spot, spot * 3.0
    if bs_price("call", spot, hi, years, sigma, rate) > put_premium:
        hi = spot * 10.0  # volatilità estreme: allarga la ricerca
    for _ in range(80):
        mid = (lo + hi) / 2
        if bs_price("call", spot, mid, years, sigma, rate) > put_premium:
            lo = mid
        else:
            hi = mid
    call_strike = (lo + hi) / 2
    return {
        "put_strike": put_strike,
        "call_strike": call_strike,
        "premium_net": bs_price("call", spot, call_strike, years, sigma, rate) - put_premium,
        "floor": put_strike,
        "cap": call_strike,
        "locked_pnl": (put_strike - cost_basis) if cost_basis is not None else None,
        "days": days,
    }
