"""Motore multifattore (PI Score): momentum, bassa volatilità, trend.

Fattori price-based con letteratura decennale alle spalle:
- Momentum 12-1 (Jegadeesh & Titman 1993): rendimento degli ultimi ~12 mesi
  escludendo l'ultimo mese (che tende a invertire).
- Low volatility (Baker et al. 2011): i titoli meno volatili hanno
  storicamente reso più di quanto il CAPM preveda.
- Trend: distanza del prezzo dalla propria media mobile di lungo periodo.

Il punteggio composito è una media pesata dei percentili di ranking (0-100).
Nessuna garanzia: sono regolarità storiche, non leggi fisiche.
"""

import pandas as pd

SKIP_DAYS = 21  # ~1 mese di borsa escluso dal momentum
MIN_HISTORY = 60


def _relative_prices(returns: pd.DataFrame) -> pd.DataFrame:
    """Serie di prezzo relativa (base 1) ricostruita dai rendimenti."""
    return (1 + returns.fillna(0)).cumprod().where(returns.notna().cummax())


def momentum_12_1(returns: pd.DataFrame) -> pd.Series:
    """Rendimento cumulato della finestra, escluso l'ultimo mese."""
    prices = _relative_prices(returns)

    def column(series: pd.Series) -> float:
        valid = series.dropna()
        if len(valid) < MIN_HISTORY + SKIP_DAYS:
            return float("nan")
        return float(valid.iloc[-SKIP_DAYS - 1] / valid.iloc[0] - 1)

    return prices.apply(column)


def low_volatility(returns: pd.DataFrame) -> pd.Series:
    """Volatilità cambiata di segno: più alta = titolo più tranquillo."""
    counts = returns.notna().sum()
    vol = returns.std()
    return (-vol).where(counts >= MIN_HISTORY)


def trend_strength(returns: pd.DataFrame) -> pd.Series:
    """Distanza del prezzo dalla media mobile della finestra (max 200 giorni)."""
    prices = _relative_prices(returns)

    def column(series: pd.Series) -> float:
        valid = series.dropna()
        if len(valid) < MIN_HISTORY:
            return float("nan")
        moving_average = float(valid.tail(min(200, len(valid))).mean())
        return float(valid.iloc[-1] / moving_average - 1)

    return prices.apply(column)


def composite_scores(
    returns: pd.DataFrame,
    weights: tuple[float, float, float] = (0.5, 0.3, 0.2),
) -> pd.DataFrame:
    """PI Score per ogni titolo: percentili (0-100) dei tre fattori
    e composito pesato (default: 50% momentum, 30% low-vol, 20% trend)."""
    factors = pd.DataFrame(
        {
            "momentum": momentum_12_1(returns),
            "low_vol": low_volatility(returns),
            "trend": trend_strength(returns),
        }
    )
    ranked = factors.rank(pct=True) * 100
    w_mom, w_vol, w_trend = weights
    ranked["pi_score"] = (
        ranked["momentum"] * w_mom + ranked["low_vol"] * w_vol + ranked["trend"] * w_trend
    ) / (w_mom + w_vol + w_trend)
    return ranked.sort_values("pi_score", ascending=False)


def multifactor_weights(window_returns: pd.DataFrame, top_n: int = 10) -> pd.Series:
    """Strategia per il backtest: equipesato sui top_n per PI Score."""
    scores = composite_scores(window_returns)["pi_score"].dropna()
    if scores.empty:
        return pd.Series(dtype=float)
    top = scores.nlargest(min(top_n, len(scores))).index
    return pd.Series(1 / len(top), index=top)
