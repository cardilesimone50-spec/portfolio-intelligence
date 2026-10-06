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
    start: pd.Timestamp | None = None  # storico congiunto usato (tutti i titoli quotati)
    end: pd.Timestamp | None = None


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
    recent_vol: float  # ultimi 63 giorni di borsa (un trimestre), annualizzata
    # ---------------------------------------------------------------- benchmark
    bench_cum_return: float
    bench_cagr: float
    bench_vol: float
    bench_sharpe: float
    bench_sortino: float
    bench_max_dd: float
    bench_var95: float
    bench_es95: float
    bench_best_month: float
    bench_worst_month: float
    beta: float
    recent_beta: float  # ultimi 63 giorni di borsa
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
    sector_risk: pd.Series  # contributo al rischio aggregato per settore
    top_sector: str  # primo settore tra quelli classificati ("" se nessuno)
    top_sector_weight: float
    sector_coverage: float  # quota del capitale con un settore noto
    usd_weight: float
    weighted_pe: float
    pe_coverage: float  # quota del capitale con un P/E disponibile
    top_risk_ticker: str = ""  # primo contributore al rischio (non la prima posizione)
    top_risk_share: float = float("nan")
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
        start=pd.Timestamp(value.index[0]),
        end=pd.Timestamp(value.index[-1]),
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


RECENT_DAYS = 63  # un trimestre di borsa: il regime di rischio recente


def _value_from(daily: pd.Series) -> pd.Series:
    """Valore cumulato con il punto di partenza (1.0) il giorno prima del primo rendimento.

    Senza la base, un primo giorno in perdita non conterebbe nel drawdown.
    """
    if daily.empty:
        return daily
    base = pd.Series([1.0], index=[daily.index[0] - pd.Timedelta(days=1)])
    return pd.concat([base, (1 + daily).cumprod()])


def compute_report_metrics(
    pf_daily: pd.Series,
    bench_daily: pd.Series,
    weights: pd.Series,
    contributions: pd.Series,
    fund: pd.DataFrame,
    usd_weight: float,
    risk_free: float = 0.0,
    unclassified: str = "Not classified",
    annual_vol: float | None = None,
    joint_daily: pd.Series | None = None,
) -> ReportMetrics:
    """Tutte le metriche dei report a partire dalle serie della pipeline.

    `annual_vol`: la volatilità del portafoglio usata dal resto dell'app
    (sqrt(w'Σw)); se data, è quella del report, così verifica del profilo,
    controlli di monitoraggio e rilievi usano lo stesso numero.
    `joint_daily`: rendimenti del portafoglio sui soli giorni in cui tutti i
    titoli hanno un prezzo; base degli scenari storici a 12 mesi.
    Il benchmark è ristretto alla finestra del portafoglio ("stessa finestra").
    """
    pf = pf_daily.dropna()
    bench = bench_daily.dropna()
    if len(pf):
        bench = bench.loc[pf.index[0] : pf.index[-1]]
    pf_value = _value_from(pf)
    bench_value = _value_from(bench)

    beta, alpha = beta_alpha(pf, bench)
    recent_beta, _ = beta_alpha(pf.tail(RECENT_DAYS), bench.tail(RECENT_DAYS))
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

    def monthly(daily: pd.Series) -> pd.Series:
        return (1 + daily).resample("ME").prod() - 1 if len(daily) else pd.Series(dtype=float)

    pf_monthly, bench_monthly = monthly(pf), monthly(bench)

    w = weights[weights > 0].astype(float)
    w = w / w.sum() if w.sum() else w
    hhi, effective_n = concentration(w)
    ordered = w.sort_values(ascending=False)
    risk = contributions.reindex(w.index).astype(float)
    risk_valid = risk.dropna()

    if "sector" in fund.columns:
        raw = fund["sector"].reindex(w.index)
        known = raw.notna() & (raw.astype(str).str.strip() != "")
    else:
        raw = pd.Series(index=w.index, dtype=object)
        known = pd.Series(False, index=w.index)
    sectors = raw.where(known, unclassified)
    sector_weights = w.groupby(sectors).sum().sort_values(ascending=False)
    sector_risk = risk.groupby(sectors).sum().reindex(sector_weights.index)
    classified = w[known].groupby(raw[known]).sum().sort_values(ascending=False)

    pe = fund["pe"] if "pe" in fund.columns else pd.Series(dtype=float)
    weighted_pe, pe_coverage = weighted_multiple(w, pe)

    over = [
        str(ticker)
        for ticker in ordered.index
        if risk.get(ticker, NAN) == risk.get(ticker, NAN)
        and risk[ticker] > w[ticker] * RISK_SHARE_OVER_WEIGHT
        and len(w) >= 2
    ]

    vol = (
        float(annual_vol)
        if annual_vol is not None and np.isfinite(annual_vol)
        else float(pf.std() * TRADING_DAYS**0.5)
        if len(pf) > 1
        else NAN
    )
    recent = pf.tail(RECENT_DAYS)
    return ReportMetrics(
        start=pd.Timestamp(pf.index[0]) if len(pf) else pd.NaT,
        end=pd.Timestamp(pf.index[-1]) if len(pf) else pd.NaT,
        observations=len(pf),
        cum_return=float(pf_value.iloc[-1] - 1) if len(pf) else NAN,
        cagr=cagr,
        vol=vol,
        sharpe=sharpe_from_daily(pf, risk_free_rate=risk_free),
        sortino=sortino_from_daily(pf, risk_free_rate=risk_free),
        max_dd=max_drawdown(pf_value) if len(pf) else NAN,
        var95=value_at_risk(pf),
        es95=expected_shortfall(pf),
        worst_day=float(pf.min()) if len(pf) else NAN,
        best_month=float(pf_monthly.max()) if len(pf_monthly) else NAN,
        worst_month=float(pf_monthly.min()) if len(pf_monthly) else NAN,
        recent_vol=float(recent.std() * TRADING_DAYS**0.5) if len(recent) >= 20 else NAN,
        bench_cum_return=float(bench_value.iloc[-1] - 1) if len(bench) else NAN,
        bench_cagr=bench_cagr,
        bench_vol=float(bench.std() * TRADING_DAYS**0.5) if len(bench) > 1 else NAN,
        bench_sharpe=sharpe_from_daily(bench, risk_free_rate=risk_free),
        bench_sortino=sortino_from_daily(bench, risk_free_rate=risk_free),
        bench_max_dd=max_drawdown(bench_value) if len(bench) else NAN,
        bench_var95=value_at_risk(bench),
        bench_es95=expected_shortfall(bench),
        bench_best_month=float(bench_monthly.max()) if len(bench_monthly) else NAN,
        bench_worst_month=float(bench_monthly.min()) if len(bench_monthly) else NAN,
        beta=beta,
        recent_beta=recent_beta,
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
        sector_risk=sector_risk,
        top_sector=str(classified.index[0]) if len(classified) else "",
        top_sector_weight=float(classified.iloc[0]) if len(classified) else NAN,
        sector_coverage=float(w[known].sum()) if len(w) else 0.0,
        usd_weight=float(usd_weight),
        weighted_pe=weighted_pe,
        pe_coverage=pe_coverage,
        top_risk_ticker=str(risk_valid.idxmax()) if len(risk_valid) else "",
        top_risk_share=float(risk_valid.max()) if len(risk_valid) else NAN,
        scenarios=historical_scenarios(joint_daily if joint_daily is not None else pf),
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


# ------------------------------------------------------------------ analisi di dettaglio (Advisor)


def calendar_returns(pf_daily: pd.Series, bench_daily: pd.Series | None) -> pd.DataFrame:
    """Rendimento per anno solare: colonne portfolio, benchmark, partial (anno incompleto)."""
    pf = pf_daily.dropna()
    if pf.empty:
        return pd.DataFrame(columns=["portfolio", "benchmark", "partial"])
    years = pf.groupby(pf.index.year).apply(lambda s: float((1 + s).prod() - 1))
    if bench_daily is not None:
        bench = bench_daily.dropna().loc[pf.index[0] : pf.index[-1]]
        bench_years = bench.groupby(bench.index.year).apply(lambda s: float((1 + s).prod() - 1))
    else:
        bench_years = pd.Series(dtype=float)
    first, last = pf.index[0], pf.index[-1]
    partial = {
        year: (year == first.year and (first.month, first.day) > (1, 7))
        or (year == last.year and (last.month, last.day) < (12, 24))
        for year in years.index
    }
    return pd.DataFrame(
        {
            "portfolio": years,
            "benchmark": bench_years.reindex(years.index),
            "partial": pd.Series(partial),
        }
    )


def rolling_return(daily: pd.Series, window: int = ROLLING_WINDOW) -> pd.Series:
    """Rendimento mobile su `window` giorni di borsa (per i grafici)."""
    value = (1 + daily.dropna()).cumprod()
    return (value / value.shift(window) - 1).dropna()


def rolling_volatility(daily: pd.Series, window: int = RECENT_DAYS) -> pd.Series:
    return (daily.dropna().rolling(window).std() * TRADING_DAYS**0.5).dropna()


def tail_risk(
    pf_daily: pd.Series, bench_daily: pd.Series | None
) -> list[tuple[str, float, float]]:
    """Rischio di coda storico: (chiave, portafoglio, benchmark) in frazioni.

    VaR ed Expected Shortfall al 95% e 99% su un giorno, peggior giorno e
    peggiori finestre di 5, 21 e 63 giorni di borsa (settimana, mese, trimestre).
    """
    pf = pf_daily.dropna()
    bench = (
        bench_daily.dropna().loc[pf.index[0] : pf.index[-1]]
        if bench_daily is not None and len(pf)
        else pd.Series(dtype=float)
    )

    def worst(daily: pd.Series, days: int) -> float:
        if len(daily) < days:
            return NAN
        value = (1 + daily).cumprod()
        return float((value / value.shift(days) - 1).min())

    rows = [
        ("var95", value_at_risk(pf, 0.95), value_at_risk(bench, 0.95)),
        ("es95", expected_shortfall(pf, 0.95), expected_shortfall(bench, 0.95)),
        ("var99", value_at_risk(pf, 0.99), value_at_risk(bench, 0.99)),
        ("es99", expected_shortfall(pf, 0.99), expected_shortfall(bench, 0.99)),
        (
            "worst_day",
            float(pf.min()) if len(pf) else NAN,
            float(bench.min()) if len(bench) else NAN,
        ),
        ("worst_week", worst(pf, 5), worst(bench, 5)),
        ("worst_month", worst(pf, 21), worst(bench, 21)),
        ("worst_quarter", worst(pf, 63), worst(bench, 63)),
    ]
    return rows


def worst_windows(
    pf_daily: pd.Series, bench_daily: pd.Series | None, days: int, count: int = 3
) -> list[dict]:
    """Le `count` peggiori finestre di `days` giorni (non sovrapposte), con il benchmark accanto."""
    pf = pf_daily.dropna()
    if len(pf) <= days:
        return []
    value = (1 + pf).cumprod()
    window = (value / value.shift(days) - 1).dropna().sort_values()
    bench = bench_daily.dropna() if bench_daily is not None else None
    chosen: list[dict] = []
    for end, ret in window.items():
        end_pos = value.index.get_loc(end)
        start = value.index[end_pos - days]
        if any(not (end < c["start"] or start > c["end"]) for c in chosen):
            continue
        bench_ret = NAN
        if bench is not None:
            span = bench.loc[start:end].iloc[1:]
            bench_ret = float((1 + span).prod() - 1) if len(span) else NAN
        chosen.append(
            {"start": start, "end": end, "portfolio": float(ret), "benchmark": bench_ret}
        )
        if len(chosen) == count:
            break
    return chosen
