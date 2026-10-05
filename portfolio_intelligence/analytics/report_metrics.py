"""Metriche dei report PDF (Investor e Advisor): un solo calcolo, due presentazioni.

Modulo puro, senza Streamlit né rete: riceve le serie già calcolate dalla
pipeline (rendimenti giornalieri del portafoglio e del benchmark, pesi,
contributi al rischio, fondamentali) e restituisce tutto ciò che i due report
mostrano. Le due versioni leggono gli stessi numeri: cambia solo quanto in
profondità li presentano.

Convenzioni: rendimenti semplici, frazioni (0.12 = 12%), annualizzazione su
252 giorni di borsa, CAGR geometrico. Le metriche relative al benchmark usano
solo i giorni in cui entrambe le serie hanno un dato.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from portfolio_intelligence.analytics.performance import (
    annualized_geometric_return,
    beta_alpha,
    expected_shortfall,
    max_drawdown,
    sharpe_from_daily,
    sortino_from_daily,
    value_at_risk,
)
from portfolio_intelligence.analytics.simulation import simulate_shock
from portfolio_intelligence.config import RISK_SHARE_OVER_WEIGHT, TRADING_DAYS
from portfolio_intelligence.portfolio import Portfolio

NAN = float("nan")
ROLLING_WINDOW = TRADING_DAYS  # finestre storiche di 12 mesi per gli scenari Investor
MIN_ROLLING_WINDOWS = 21  # almeno un mese di finestre distinte, altrimenti nessuno scenario
MIN_CAPTURE_MONTHS = 12  # capture ratio su base mensile solo con un anno di mesi


@dataclass(frozen=True)
class DrawdownEpisode:
    """Un episodio di drawdown: dal massimo al minimo e, se avvenuto, al recupero."""

    peak: pd.Timestamp
    trough: pd.Timestamp
    recovery: pd.Timestamp | None
    depth: float  # negativo, es. -0.18
    days_to_trough: int  # giorni di calendario
    days_to_recover: int | None  # dal minimo al recupero; None = non ancora recuperato


@dataclass(frozen=True)
class HistoricalScenarios:
    """Esiti storici a 12 mesi con i pesi attuali (non previsioni)."""

    bear: float  # 5° percentile dei rendimenti a 12 mesi
    base: float  # mediana
    bull: float  # 95° percentile
    worst: float
    best: float
    share_negative: float  # quota di finestre chiuse in perdita
    windows: int


@dataclass(frozen=True)
class ReportMetrics:
    # ---------------------------------------------------------------- finestra
    start: pd.Timestamp
    end: pd.Timestamp
    observations: int
    # ---------------------------------------------------------------- performance assoluta
    cum_return: float
    cagr: float
    vol: float
    sharpe: float
    sortino: float
    max_dd: float
    var95: float
    es95: float
    worst_day: float
    best_month: float
    worst_month: float
    # ---------------------------------------------------------------- benchmark
    bench_cum_return: float
    bench_cagr: float
    bench_vol: float
    bench_sharpe: float
    bench_sortino: float
    bench_max_dd: float
    bench_var95: float
    bench_es95: float
    beta: float
    alpha: float
    correlation: float
    tracking_error: float
    information_ratio: float
    up_capture: float
    down_capture: float
    capture_basis: str  # "monthly" | "daily"
    # ---------------------------------------------------------------- drawdown
    episodes: list[DrawdownEpisode]
    current_drawdown: float
    # ---------------------------------------------------------------- composizione
    weights: pd.Series
    risk: pd.Series
    hhi: float
    effective_n: float
    top_ticker: str
    top_weight: float
    top3_weight: float
    sector_weights: pd.Series
    top_sector: str
    top_sector_weight: float
    usd_weight: float
    weighted_pe: float
    pe_coverage: float  # quota del capitale con un P/E disponibile
    # ---------------------------------------------------------------- scenari storici
    scenarios: HistoricalScenarios | None = None
    risk_over_weight: list[str] = field(default_factory=list)

    @property
    def excess_return(self) -> float:
        return self.cum_return - self.bench_cum_return

    @property
    def excess_cagr(self) -> float:
        return self.cagr - self.bench_cagr

    @property
    def vol_diff(self) -> float:
        return self.vol - self.bench_vol


# ------------------------------------------------------------------ pezzi


def drawdown_episodes(value: pd.Series, top: int = 3) -> list[DrawdownEpisode]:
    """I `top` episodi di drawdown più profondi, dal più profondo.

    Un episodio inizia a un massimo, tocca il minimo e termina quando il
    valore torna al massimo precedente (recupero) o a fine serie (in corso).
    """
    series = value.dropna()
    if len(series) < 2:
        return []
    peak_value = series.cummax()
    under = series < peak_value
    episodes: list[DrawdownEpisode] = []
    start = None
    for i, (date, is_under) in enumerate(under.items()):
        if is_under and start is None:
            start = i - 1  # l'ultimo giorno al massimo
        if start is not None and (not is_under or i == len(series) - 1):
            end = i if not is_under else None
            stretch = series.iloc[start : (end if end is not None else i) + 1]
            trough_date = stretch.idxmin()
            peak_date = series.index[start]
            depth = float(stretch.min() / series.iloc[start] - 1)
            recovery = date if end is not None else None
            episodes.append(
                DrawdownEpisode(
                    peak=pd.Timestamp(peak_date),
                    trough=pd.Timestamp(trough_date),
                    recovery=pd.Timestamp(recovery) if recovery is not None else None,
                    depth=depth,
                    days_to_trough=(pd.Timestamp(trough_date) - pd.Timestamp(peak_date)).days,
                    days_to_recover=(
                        (pd.Timestamp(recovery) - pd.Timestamp(trough_date)).days
                        if recovery is not None
                        else None
                    ),
                )
            )
            start = None
    return sorted(episodes, key=lambda e: e.depth)[:top]


def historical_scenarios(daily: pd.Series) -> HistoricalScenarios | None:
    """Rendimenti di tutte le finestre di 12 mesi osservate (passo giornaliero).

    Con meno di un anno e un mese di storico non ci sono abbastanza finestre
    distinte: nessuno scenario, invece di numeri poco significativi.
    """
    value = (1 + daily.dropna()).cumprod()
    if len(value) < ROLLING_WINDOW + MIN_ROLLING_WINDOWS:
        return None
    rolling = (value.shift(-ROLLING_WINDOW) / value - 1).dropna()
    return HistoricalScenarios(
        bear=float(rolling.quantile(0.05)),
        base=float(rolling.median()),
        bull=float(rolling.quantile(0.95)),
        worst=float(rolling.min()),
        best=float(rolling.max()),
        share_negative=float((rolling < 0).mean()),
        windows=len(rolling),
    )


def capture_ratios(pf: pd.Series, bench: pd.Series) -> tuple[float, float, str]:
    """Up e down capture: quanto del rialzo (ribasso) del benchmark il portafoglio ha seguito.

    Su rendimenti mensili quando ci sono almeno 12 mesi, altrimenti giornalieri.
    Rapporto delle medie aritmetiche nei periodi di benchmark positivo (negativo).
    """
    aligned = pd.concat({"pf": pf, "bench": bench}, axis=1).dropna()
    basis = "daily"
    if len(aligned) >= 2:
        monthly = (1 + aligned).resample("ME").prod() - 1
        if len(monthly) >= MIN_CAPTURE_MONTHS:
            aligned, basis = monthly, "monthly"
    up = aligned[aligned["bench"] > 0]
    down = aligned[aligned["bench"] < 0]

    def ratio(part: pd.DataFrame) -> float:
        if len(part) == 0 or part["bench"].mean() == 0:
            return NAN
        return float(part["pf"].mean() / part["bench"].mean())

    return ratio(up), ratio(down), basis


def concentration(weights: pd.Series) -> tuple[float, float]:
    """Indice di Herfindahl e numero effettivo di posizioni (1/HHI)."""
    w = weights[weights > 0]
    if w.empty:
        return NAN, NAN
    w = w / w.sum()
    hhi = float((w**2).sum())
    return hhi, 1 / hhi


def weighted_multiple(weights: pd.Series, multiple: pd.Series) -> tuple[float, float]:
    """Multiplo medio ponderato (media armonica, come per gli indici) e copertura.

    La media armonica pondera gli utili, non i prezzi: un titolo con P/E molto
    alto non domina il dato. Solo multipli positivi.
    """
    m = pd.to_numeric(multiple.reindex(weights.index), errors="coerce")
    valid = m[(m > 0) & m.notna()]
    if valid.empty:
        return NAN, 0.0
    w = weights[valid.index]
    coverage = float(w.sum() / weights.sum()) if weights.sum() else 0.0
    return float(w.sum() / (w / valid).sum()), coverage


# ------------------------------------------------------------------ calcolo


def compute_report_metrics(
    pf_daily: pd.Series,
    bench_daily: pd.Series,
    weights: pd.Series,
    contributions: pd.Series,
    fund: pd.DataFrame,
    usd_weight: float,
    risk_free: float = 0.0,
    unclassified: str = "Not classified",
) -> ReportMetrics:
    """Tutte le metriche dei report a partire dalle serie della pipeline."""
    pf = pf_daily.dropna()
    bench = bench_daily.dropna()
    pf_value = (1 + pf).cumprod()
    bench_value = (1 + bench).cumprod()

    beta, alpha = beta_alpha(pf, bench)
    aligned = pd.concat({"pf": pf, "bench": bench}, axis=1).dropna()
    if len(aligned) >= 20:
        correlation = float(aligned["pf"].corr(aligned["bench"]))
        active = aligned["pf"] - aligned["bench"]
        tracking_error = float(active.std() * TRADING_DAYS**0.5)
    else:
        correlation = tracking_error = NAN
    cagr = annualized_geometric_return(pf)
    bench_cagr = annualized_geometric_return(bench)
    information_ratio = (
        (cagr - bench_cagr) / tracking_error
        if tracking_error and tracking_error == tracking_error
        else NAN
    )
    up_capture, down_capture, basis = capture_ratios(pf, bench)

    monthly = (1 + pf).resample("ME").prod() - 1 if len(pf) else pd.Series(dtype=float)

    w = weights[weights > 0].astype(float)
    w = w / w.sum() if w.sum() else w
    hhi, effective_n = concentration(w)
    ordered = w.sort_values(ascending=False)
    risk = contributions.reindex(w.index).astype(float)

    if "sector" in fund.columns:
        sectors = fund["sector"].reindex(w.index)
        sectors = sectors.where(sectors.notna() & (sectors.astype(str) != ""), unclassified)
    else:
        sectors = pd.Series(unclassified, index=w.index)
    sector_weights = w.groupby(sectors).sum().sort_values(ascending=False)

    pe = fund["pe"] if "pe" in fund.columns else pd.Series(dtype=float)
    weighted_pe, pe_coverage = weighted_multiple(w, pe)

    over = [
        str(ticker)
        for ticker in ordered.index
        if risk.get(ticker, NAN) == risk.get(ticker, NAN)
        and risk[ticker] > w[ticker] * RISK_SHARE_OVER_WEIGHT
        and len(w) >= 2
    ]

    return ReportMetrics(
        start=pd.Timestamp(pf.index[0]) if len(pf) else pd.NaT,
        end=pd.Timestamp(pf.index[-1]) if len(pf) else pd.NaT,
        observations=len(pf),
        cum_return=float(pf_value.iloc[-1] - 1) if len(pf) else NAN,
        cagr=cagr,
        vol=float(pf.std() * TRADING_DAYS**0.5) if len(pf) > 1 else NAN,
        sharpe=sharpe_from_daily(pf, risk_free_rate=risk_free),
        sortino=sortino_from_daily(pf, risk_free_rate=risk_free),
        max_dd=max_drawdown(pf_value) if len(pf) else NAN,
        var95=value_at_risk(pf),
        es95=expected_shortfall(pf),
        worst_day=float(pf.min()) if len(pf) else NAN,
        best_month=float(monthly.max()) if len(monthly) else NAN,
        worst_month=float(monthly.min()) if len(monthly) else NAN,
        bench_cum_return=float(bench_value.iloc[-1] - 1) if len(bench) else NAN,
        bench_cagr=bench_cagr,
        bench_vol=float(bench.std() * TRADING_DAYS**0.5) if len(bench) > 1 else NAN,
        bench_sharpe=sharpe_from_daily(bench, risk_free_rate=risk_free),
        bench_sortino=sortino_from_daily(bench, risk_free_rate=risk_free),
        bench_max_dd=max_drawdown(bench_value) if len(bench) else NAN,
        bench_var95=value_at_risk(bench),
        bench_es95=expected_shortfall(bench),
        beta=beta,
        alpha=alpha,
        correlation=correlation,
        tracking_error=tracking_error,
        information_ratio=information_ratio,
        up_capture=up_capture,
        down_capture=down_capture,
        capture_basis=basis,
        episodes=drawdown_episodes(pf_value),
        current_drawdown=float(pf_value.iloc[-1] / pf_value.max() - 1) if len(pf) else NAN,
        weights=ordered,
        risk=risk,
        hhi=hhi,
        effective_n=effective_n,
        top_ticker=str(ordered.index[0]) if len(ordered) else "",
        top_weight=float(ordered.iloc[0]) if len(ordered) else NAN,
        top3_weight=float(ordered.head(3).sum()) if len(ordered) else NAN,
        sector_weights=sector_weights,
        top_sector=str(sector_weights.index[0]) if len(sector_weights) else "",
        top_sector_weight=float(sector_weights.iloc[0]) if len(sector_weights) else NAN,
        usd_weight=float(usd_weight),
        weighted_pe=weighted_pe,
        pe_coverage=pe_coverage,
        scenarios=historical_scenarios(pf),
        risk_over_weight=over,
    )


def stress_tests(
    returns: pd.DataFrame,
    weights: pd.Series,
    metrics: ReportMetrics,
    include_fx: bool,
) -> list[dict]:
    """Scenari di stress: impatto diretto e, dove ha senso, corretto per le correlazioni.

    Ogni voce: {"key", "label_args", "direct", "total"} con impatti in frazione
    (None se non applicabile). Le etichette si traducono nel report.
    - top_position: la prima posizione perde il 20%; il contagio usa i beta
      storici degli altri titoli verso di essa (analytics/simulation.py);
    - market: il benchmark perde il 20%; impatto = beta × shock;
    - usd: il dollaro perde il 10% sull'euro; effetto di traduzione sulla quota USD;
    - worst_month: il peggior mese osservato, rigiocato con i pesi attuali.
    """
    tests: list[dict] = []
    if metrics.top_ticker and metrics.top_ticker in returns.columns:
        portfolio: Portfolio = [{"ticker": str(k), "weight": float(v)} for k, v in weights.items()]
        try:
            shock = simulate_shock(returns, portfolio, metrics.top_ticker, -0.20)
            tests.append(
                {
                    "key": "top_position",
                    "label_args": {"ticker": metrics.top_ticker, "weight": metrics.top_weight},
                    "direct": shock["direct"],
                    "total": shock["total"],
                }
            )
        except ValueError:
            pass
    if metrics.beta == metrics.beta:
        tests.append(
            {"key": "market", "label_args": {}, "direct": None, "total": metrics.beta * -0.20}
        )
    if include_fx and metrics.usd_weight > 0:
        tests.append(
            {
                "key": "usd",
                "label_args": {"share": metrics.usd_weight},
                "direct": -0.10 * metrics.usd_weight,
                "total": None,
            }
        )
    if metrics.worst_month == metrics.worst_month:
        tests.append(
            {"key": "worst_month", "label_args": {}, "direct": None, "total": metrics.worst_month}
        )
    return tests


def rebased(series: pd.Series) -> pd.Series:
    """Serie in base 100 dal primo valore valido."""
    valid = series.dropna()
    if valid.empty:
        return valid
    return valid / valid.iloc[0] * 100


def finite(value: float | None) -> bool:
    return value is not None and bool(np.isfinite(value))
