"""Testi dei report PDF generati da regole sui numeri: niente modelli linguistici.

Ogni frase nasce da una metrica di `ReportMetrics` e la cita: nessun
commento generico, nessun aggettivo senza un numero dietro. Il tono è
descrittivo, non prescrittivo: il report descrive caratteristiche misurabili
del portafoglio e non raccomanda operazioni (TUF / MiFID II).

Le funzioni ricevono la lingua del documento (`lang`) invece di leggere quella
dell'interfaccia: lo stesso report si può generare in inglese o in italiano.
"""

from portfolio_intelligence.analytics.report_metrics import ReportMetrics, finite
from portfolio_intelligence.config import (
    BETA_HIGH,
    BETA_LOW,
    CORRELATION_ELEVATED,
    MONITOR_MAX_RISK_SHARE,
    RISK_LEVEL_BETA,
    RISK_LEVEL_DRAWDOWN,
    RISK_LEVEL_HHI,
    RISK_LEVEL_PE,
    RISK_LEVEL_SECTOR,
    RISK_LEVEL_USD,
    RISK_LEVEL_VOL,
    TRACKING_ERROR_HIGH,
)
from portfolio_intelligence.formatting import fmt_date, fmt_num, fmt_pct, fmt_pp, missing
from portfolio_intelligence.i18n import t_in

LEVELS = ("low", "moderate", "elevated", "high")
# sotto ~10 mesi di borsa i valori annualizzati vanno letti come indicativi
# (stessa soglia dell'avvertenza nelle note di metodologia)
SHORT_WINDOW_DAYS = 200
NOT_ASSESSED = "na"


def risk_level(value: float, bounds: tuple[float, float, float]) -> str:
    """Livello di rischio dai tre confini crescenti; NOT_ASSESSED se il valore manca."""
    if not finite(value):
        return NOT_ASSESSED
    for name, bound in zip(LEVELS, bounds, strict=False):
        if value < bound:
            return name
    return LEVELS[-1]


def _compare(value: float, bench: float, higher_is_better: bool, lang: str, key: str) -> str:
    """Assessment di confronto col benchmark: 'sopra/sotto di X pp' o 'in linea'."""
    if not (finite(value) and finite(bench)):
        return missing(lang)
    diff = value - bench
    if abs(diff) < 0.0005:
        return t_in(lang, f"rpt.{key}_inline")
    better = diff > 0 if higher_is_better else diff < 0
    return t_in(lang, f"rpt.{key}_{'better' if better else 'worse'}", pp=fmt_pp(diff, lang))


# ------------------------------------------------------------------ profilo del portafoglio


def profile_rows(
    m: ReportMetrics, value_text: str, benchmark: str, lang: str, in_eur: bool = True
) -> list[tuple[str, str, str, str]]:
    """Tabella Metric | Portfolio | Benchmark | Assessment del report Advisor."""
    T = lambda key, **kw: t_in(lang, key, **kw)  # noqa: E731
    na = missing(lang)

    def ratio_cmp(value: float, bench: float, key: str) -> str:
        if not (finite(value) and finite(bench)):
            return na
        if value <= 0 and bench <= 0:
            return T("rpt.ratio_negative")  # rendimento sotto il tasso privo di rischio
        if abs(value - bench) < 0.05:
            return T(f"rpt.{key}_inline")
        return T(f"rpt.{key}_{'better' if value > bench else 'worse'}")

    if not finite(m.beta):
        beta_text = na
    elif m.beta > BETA_HIGH:
        beta_text = T("rpt.beta_amplifies", benchmark=benchmark)
    elif m.beta < BETA_LOW:
        beta_text = T("rpt.beta_dampens", benchmark=benchmark)
    else:
        beta_text = T("rpt.beta_inline", benchmark=benchmark)

    r2 = m.correlation**2 if finite(m.correlation) else float("nan")
    te_text = (
        na
        if not finite(m.tracking_error)
        else T("rpt.te_high" if m.tracking_error > TRACKING_ERROR_HIGH else "rpt.te_moderate")
    )
    capture_text = (
        T(
            "rpt.capture_text",
            up=fmt_pct(m.up_capture, lang, 0),
            down=fmt_pct(m.down_capture, lang, 0),
            basis=T(f"rpt.basis_{m.capture_basis}"),
        )
        if finite(m.up_capture) and finite(m.down_capture)
        else na
    )
    top_risk = m.risk.get(m.top_ticker, float("nan"))
    return [
        (T("rpt.m_value"), value_text, na, T("rpt.a_value")),
        (
            T("rpt.m_total_return"),
            fmt_pct(m.cum_return, lang, signed=True),
            fmt_pct(m.bench_cum_return, lang, signed=True),
            _compare(m.cum_return, m.bench_cum_return, True, lang, "ret"),
        ),
        (
            T("rpt.m_cagr"),
            fmt_pct(m.cagr, lang, signed=True),
            fmt_pct(m.bench_cagr, lang, signed=True),
            _compare(m.cagr, m.bench_cagr, True, lang, "ret"),
        ),
        (
            T("rpt.m_vol"),
            fmt_pct(m.vol, lang),
            fmt_pct(m.bench_vol, lang),
            _compare(m.vol, m.bench_vol, False, lang, "vol"),
        ),
        (
            T("rpt.m_sharpe"),
            fmt_num(m.sharpe, lang),
            fmt_num(m.bench_sharpe, lang),
            ratio_cmp(m.sharpe, m.bench_sharpe, "sharpe"),
        ),
        (
            T("rpt.m_sortino"),
            fmt_num(m.sortino, lang),
            fmt_num(m.bench_sortino, lang),
            ratio_cmp(m.sortino, m.bench_sortino, "sortino"),
        ),
        (
            T("rpt.m_maxdd"),
            fmt_pct(m.max_dd, lang),
            fmt_pct(m.bench_max_dd, lang),
            _compare(m.max_dd, m.bench_max_dd, True, lang, "dd"),
        ),
        (
            T("rpt.m_var"),
            fmt_pct(m.var95, lang),
            fmt_pct(m.bench_var95, lang),
            _compare(m.var95, m.bench_var95, True, lang, "tail"),
        ),
        (
            T("rpt.m_es"),
            fmt_pct(m.es95, lang),
            fmt_pct(m.bench_es95, lang),
            _compare(m.es95, m.bench_es95, True, lang, "tail"),
        ),
        (
            T("rpt.m_beta", benchmark=benchmark),
            fmt_num(m.beta, lang),
            "1,00" if lang == "it" else "1.00",
            beta_text,
        ),
        (
            T("rpt.m_alpha"),
            fmt_pct(m.alpha, lang, signed=True),
            na,
            T("rpt.a_alpha"),
        ),
        (
            T("rpt.m_corr"),
            fmt_num(m.correlation, lang),
            na,
            T("rpt.a_corr", r2=fmt_pct(r2, lang, 0)) if finite(r2) else na,
        ),
        (T("rpt.m_te"), fmt_pct(m.tracking_error, lang), na, te_text),
        (T("rpt.m_ir"), fmt_num(m.information_ratio, lang), na, T("rpt.a_ir")),
        (
            T("rpt.m_capture"),
            f"{fmt_pct(m.up_capture, lang, 0)} / {fmt_pct(m.down_capture, lang, 0)}",
            na,
            capture_text,
        ),
        (
            T("rpt.m_hhi"),
            fmt_num(m.hhi, lang),
            na,
            T("rpt.a_hhi", n=fmt_num(m.effective_n, lang, 1)) if finite(m.effective_n) else na,
        ),
        (
            T("rpt.m_top"),
            f"{m.top_ticker} {fmt_pct(m.top_weight, lang)}",
            na,
            T("rpt.a_top", risk=fmt_pct(top_risk, lang)) if finite(top_risk) else na,
        ),
        (
            T("rpt.m_usd"),
            fmt_pct(m.usd_weight, lang, 0),
            na,
            T("rpt.a_usd") if in_eur else T("rpt.r_fx_native"),
        ),
    ]


# ------------------------------------------------------------------ matrice dei rischi


def risk_matrix(m: ReportMetrics, in_eur: bool, benchmark: str, lang: str) -> list[dict]:
    """Categorie di rischio con misura, livello ed evidenza (stessa base per i due report).

    Il rischio di liquidità non è misurabile con i dati disponibili (niente
    volumi né spread): lo si dichiara invece di stimarlo.
    """
    T = lambda key, **kw: t_in(lang, key, **kw)  # noqa: E731
    top_risk = m.risk.get(m.top_ticker, float("nan"))
    rows = [
        {
            "key": "market",
            "measure": T("rpt.r_market_measure", beta=fmt_num(m.beta, lang), benchmark=benchmark),
            "level": risk_level(m.beta, RISK_LEVEL_BETA),
            "evidence": T(
                "rpt.r_market_evidence",
                corr=fmt_num(m.correlation, lang),
                drop=fmt_pct(m.beta * -0.20 if finite(m.beta) else float("nan"), lang),
            ),
        },
        {
            "key": "concentration",
            "measure": T(
                "rpt.r_conc_measure",
                hhi=fmt_num(m.hhi, lang),
                n=fmt_num(m.effective_n, lang, 1),
            ),
            "level": risk_level(m.hhi, RISK_LEVEL_HHI),
            "evidence": T(
                "rpt.r_conc_evidence",
                ticker=m.top_ticker,
                weight=fmt_pct(m.top_weight, lang),
                risk=fmt_pct(top_risk, lang),
                top3=fmt_pct(m.top3_weight, lang, 0),
            ),
        },
        {
            "key": "factor",
            "measure": (
                T(
                    "rpt.r_factor_measure",
                    sector=m.top_sector,
                    weight=fmt_pct(m.top_sector_weight, lang, 0),
                )
                if _sectors_known(m)
                else T("rpt.r_factor_missing")
            ),
            "level": (
                risk_level(m.top_sector_weight, RISK_LEVEL_SECTOR)
                if _sectors_known(m)
                else NOT_ASSESSED
            ),
            "evidence": T("rpt.r_factor_evidence", coverage=fmt_pct(m.sector_coverage, lang, 0)),
        },
        {
            "key": "currency",
            "measure": T("rpt.r_fx_measure", share=fmt_pct(m.usd_weight, lang, 0)),
            "level": risk_level(m.usd_weight, RISK_LEVEL_USD) if in_eur else NOT_ASSESSED,
            "evidence": (
                T("rpt.r_fx_evidence", impact=fmt_pct(-0.10 * m.usd_weight, lang))
                if in_eur
                else T("rpt.r_fx_native")
            ),
        },
        {
            "key": "volatility",
            "measure": T("rpt.r_vol_measure", vol=fmt_pct(m.vol, lang)),
            "level": risk_level(m.vol, RISK_LEVEL_VOL),
            "evidence": T(
                "rpt.r_vol_evidence",
                bench=fmt_pct(m.bench_vol, lang),
                benchmark=benchmark,
            ),
        },
        {
            "key": "drawdown",
            "measure": T("rpt.r_dd_measure", dd=fmt_pct(m.max_dd, lang)),
            "level": risk_level(
                abs(m.max_dd) if finite(m.max_dd) else m.max_dd, RISK_LEVEL_DRAWDOWN
            ),
            "evidence": _drawdown_evidence(m, lang),
        },
        {
            "key": "liquidity",
            "measure": T("rpt.r_liq_measure"),
            "level": NOT_ASSESSED,
            "evidence": T("rpt.r_liq_evidence"),
        },
        {
            "key": "valuation",
            "measure": (
                T("rpt.r_val_measure", pe=fmt_num(m.weighted_pe, lang, 1))
                if finite(m.weighted_pe)
                else T("rpt.r_val_missing")
            ),
            "level": risk_level(m.weighted_pe, RISK_LEVEL_PE)
            if m.pe_coverage >= 0.5
            else NOT_ASSESSED,
            "evidence": T("rpt.r_val_evidence", coverage=fmt_pct(m.pe_coverage, lang, 0)),
        },
    ]
    for row in rows:
        row["category"] = T(f"rpt.cat_{row['key']}")
        row["level_label"] = T(f"rpt.level_{row['level']}")
    return rows


def _sectors_known(m: ReportMetrics) -> bool:
    """Il settore conta solo se è noto per almeno metà del capitale."""
    return bool(m.top_sector) and m.sector_coverage >= 0.5


def _drawdown_evidence(m: ReportMetrics, lang: str) -> str:
    if not m.episodes:
        return missing(lang)
    worst = m.episodes[0]
    if worst.recovery is None:
        return t_in(
            lang,
            "rpt.dd_open",
            peak=fmt_date(worst.peak),
            trough=fmt_date(worst.trough),
            current=fmt_pct(m.current_drawdown, lang),
        )
    return t_in(
        lang,
        "rpt.dd_recovered",
        peak=fmt_date(worst.peak),
        trough=fmt_date(worst.trough),
        days=worst.days_to_recover,
    )


# ------------------------------------------------------------------ vista d'investimento


def investment_view(
    m: ReportMetrics,
    benchmark: str,
    profile_label: str | None,
    profile_band: float | None,
    lang: str,
) -> list[tuple[str, list[str]]]:
    """La sintesi d'investimento del report Advisor: (titolo, frasi) per sezione.

    Ogni frase cita il dato da cui nasce. Punti di forza e vulnerabilità
    compaiono solo se superano una soglia esplicita; se nessuna regola scatta,
    la sezione lo dice invece di inventare.
    """
    T = lambda key, **kw: t_in(lang, key, **kw)  # noqa: E731
    top_risk = m.risk.get(m.top_ticker, float("nan"))
    drivers = m.risk.dropna().sort_values(ascending=False).head(2)

    positioning = [
        T(
            "rpt.v_positioning",
            n=len(m.weights),
            eff=fmt_num(m.effective_n, lang, 1),
            sector=m.top_sector,
            sector_w=fmt_pct(m.top_sector_weight, lang, 0),
            usd=fmt_pct(m.usd_weight, lang, 0),
        )
    ]
    vol_level = t_in(lang, f"rpt.level_{risk_level(m.vol, RISK_LEVEL_VOL)}").lower()
    regime = [
        T(
            "rpt.v_regime",
            vol=fmt_pct(m.vol, lang),
            level=vol_level,
            bench_vol=fmt_pct(m.bench_vol, lang),
            benchmark=benchmark,
            beta=fmt_num(m.beta, lang),
            dd=fmt_pct(m.max_dd, lang),
        )
    ]
    if finite(m.recent_vol) and finite(m.vol) and m.vol > 0:
        change = m.recent_vol / m.vol - 1
        key = (
            "rpt.v_regime_up"
            if change > 0.15
            else "rpt.v_regime_down"
            if change < -0.15
            else "rpt.v_regime_stable"
        )
        regime.append(
            T(
                key,
                recent=fmt_pct(m.recent_vol, lang),
                full=fmt_pct(m.vol, lang),
                beta=fmt_num(m.recent_beta, lang),
            )
        )
    performance = [
        T(
            "rpt.v_performance",
            start=fmt_date(m.start),
            end=fmt_date(m.end),
            ret=fmt_pct(m.cum_return, lang, signed=True),
            bench=fmt_pct(m.bench_cum_return, lang, signed=True),
            benchmark=benchmark,
            excess=fmt_pp(m.excess_return, lang),
            cagr=fmt_pct(m.cagr, lang, signed=True),
            bench_cagr=fmt_pct(m.bench_cagr, lang, signed=True),
            sharpe=fmt_num(m.sharpe, lang),
            bench_sharpe=fmt_num(m.bench_sharpe, lang),
        )
    ]
    concentration = [
        T(
            "rpt.v_concentration",
            ticker=m.top_ticker,
            weight=fmt_pct(m.top_weight, lang),
            risk=fmt_pct(top_risk, lang),
            top3=fmt_pct(m.top3_weight, lang, 0),
        )
    ]
    sources = [
        T("rpt.v_source_position", ticker=str(ticker), share=fmt_pct(share, lang, 0))
        for ticker, share in drivers.items()
    ]
    if finite(m.correlation):
        sources.append(
            T(
                "rpt.v_source_market",
                benchmark=benchmark,
                r2=fmt_pct(m.correlation**2, lang, 0),
            )
        )

    vulnerabilities: list[str] = []
    for ticker in m.risk_over_weight[:2]:
        vulnerabilities.append(
            T(
                "rpt.v_vuln_risk_weight",
                ticker=ticker,
                risk=fmt_pct(m.risk.get(ticker), lang),
                weight=fmt_pct(m.weights.get(ticker), lang),
            )
        )
    if profile_band is not None and finite(m.vol) and m.vol > profile_band:
        vulnerabilities.append(
            T(
                "rpt.v_vuln_profile",
                vol=fmt_pct(m.vol, lang),
                band=fmt_pct(profile_band, lang, 0),
                profile=(profile_label or "").lower(),
            )
        )
    if finite(m.down_capture) and m.down_capture > 1:
        vulnerabilities.append(T("rpt.v_vuln_down_capture", down=fmt_pct(m.down_capture, lang, 0)))
    if _sectors_known(m) and m.top_sector_weight >= RISK_LEVEL_SECTOR[1]:
        vulnerabilities.append(
            T(
                "rpt.v_vuln_sector",
                sector=m.top_sector,
                weight=fmt_pct(m.top_sector_weight, lang, 0),
            )
        )
    if (
        m.episodes
        and m.episodes[0].recovery is None
        and finite(m.current_drawdown)
        and m.current_drawdown < -0.05
    ):
        vulnerabilities.append(T("rpt.v_vuln_open_dd", current=fmt_pct(m.current_drawdown, lang)))
    if m.pe_coverage >= 0.5 and finite(m.weighted_pe) and m.weighted_pe >= RISK_LEVEL_PE[2]:
        vulnerabilities.append(T("rpt.v_vuln_valuation", pe=fmt_num(m.weighted_pe, lang, 1)))
    if not vulnerabilities:
        vulnerabilities.append(T("rpt.v_none"))

    strengths: list[str] = []
    if (
        finite(m.sharpe)
        and finite(m.bench_sharpe)
        and m.sharpe > 0
        and m.sharpe > m.bench_sharpe + 0.05
    ):
        strengths.append(
            T(
                "rpt.v_str_sharpe",
                sharpe=fmt_num(m.sharpe, lang),
                bench=fmt_num(m.bench_sharpe, lang),
            )
        )
    if finite(m.max_dd) and finite(m.bench_max_dd) and m.max_dd > m.bench_max_dd + 0.01:
        strengths.append(
            T("rpt.v_str_dd", dd=fmt_pct(m.max_dd, lang), bench=fmt_pct(m.bench_max_dd, lang))
        )
    if finite(m.down_capture) and m.down_capture < 0.9:
        strengths.append(T("rpt.v_str_down_capture", down=fmt_pct(m.down_capture, lang, 0)))
    if finite(m.effective_n) and m.effective_n >= 10:
        strengths.append(T("rpt.v_str_diversified", n=fmt_num(m.effective_n, lang, 1)))
    if finite(m.correlation) and m.correlation < CORRELATION_ELEVATED and len(m.weights) >= 2:
        strengths.append(
            T("rpt.v_str_low_corr", corr=fmt_num(m.correlation, lang), benchmark=benchmark)
        )
    if not strengths:
        strengths.append(T("rpt.v_none"))

    implications: list[str] = []
    if m.top_risk_ticker and finite(m.top_risk_share):
        key = (
            "rpt.v_impl_driver"
            if m.top_risk_share >= MONITOR_MAX_RISK_SHARE
            else "rpt.v_impl_driver_soft"
        )
        implications.append(
            T(key, ticker=m.top_risk_ticker, risk=fmt_pct(m.top_risk_share, lang, 0))
        )
    if finite(m.beta):
        implications.append(
            T(
                "rpt.v_impl_market",
                benchmark=benchmark,
                impact=fmt_pct(m.beta * -0.20, lang),
            )
        )
    if profile_band is not None and finite(m.vol):
        key = "rpt.v_impl_profile_out" if m.vol > profile_band else "rpt.v_impl_profile_in"
        implications.append(
            T(key, profile=(profile_label or "").lower(), band=fmt_pct(profile_band, lang, 0))
        )

    return [
        (T("rpt.vh_positioning"), positioning),
        (T("rpt.vh_regime"), regime),
        (T("rpt.vh_performance"), performance),
        (T("rpt.vh_concentration"), concentration),
        (T("rpt.vh_sources"), sources),
        (T("rpt.vh_vulnerabilities"), vulnerabilities),
        (T("rpt.vh_strengths"), strengths),
        (T("rpt.vh_implications"), implications),
    ]


def performance_blocks(
    m: ReportMetrics, benchmark: str, lang: str
) -> list[tuple[str, list[tuple]]]:
    """Le tre letture della performance: assoluta, relativa al benchmark, corretta per il rischio.

    Righe (metrica, portafoglio, benchmark, differenza) per il report Investor.
    """
    T = lambda key, **kw: t_in(lang, key, **kw)  # noqa: E731
    na = missing(lang)

    def diff_num(a: float, b: float) -> str:
        return fmt_num(a - b, lang, signed=True) if finite(a) and finite(b) else na

    absolute = [
        (
            T("rpt.m_total_return"),
            fmt_pct(m.cum_return, lang, signed=True),
            fmt_pct(m.bench_cum_return, lang, signed=True),
            fmt_pp(m.excess_return, lang),
        ),
        (
            T("rpt.m_cagr"),
            fmt_pct(m.cagr, lang, signed=True),
            fmt_pct(m.bench_cagr, lang, signed=True),
            fmt_pp(m.excess_cagr, lang),
        ),
        (
            T("rpt.m_best_month"),
            fmt_pct(m.best_month, lang, signed=True),
            fmt_pct(m.bench_best_month, lang, signed=True),
            fmt_pp(m.best_month - m.bench_best_month, lang)
            if finite(m.best_month) and finite(m.bench_best_month)
            else na,
        ),
        (
            T("rpt.m_worst_month"),
            fmt_pct(m.worst_month, lang, signed=True),
            fmt_pct(m.bench_worst_month, lang, signed=True),
            fmt_pp(m.worst_month - m.bench_worst_month, lang)
            if finite(m.worst_month) and finite(m.bench_worst_month)
            else na,
        ),
    ]
    relative = [
        (
            T("rpt.m_beta", benchmark=benchmark),
            fmt_num(m.beta, lang),
            "1,00" if lang == "it" else "1.00",
            diff_num(m.beta, 1.0),
        ),
        (T("rpt.m_alpha"), fmt_pct(m.alpha, lang, signed=True), na, na),
        (T("rpt.m_corr"), fmt_num(m.correlation, lang), na, na),
        (
            T("rpt.m_vol_diff"),
            fmt_pct(m.vol, lang),
            fmt_pct(m.bench_vol, lang),
            fmt_pp(m.vol_diff, lang),
        ),
        (T("rpt.m_te"), fmt_pct(m.tracking_error, lang), na, na),
    ]
    risk_adjusted = [
        (
            T("rpt.m_sharpe"),
            fmt_num(m.sharpe, lang),
            fmt_num(m.bench_sharpe, lang),
            diff_num(m.sharpe, m.bench_sharpe),
        ),
        (
            T("rpt.m_sortino"),
            fmt_num(m.sortino, lang),
            fmt_num(m.bench_sortino, lang),
            diff_num(m.sortino, m.bench_sortino),
        ),
        (
            T("rpt.m_maxdd"),
            fmt_pct(m.max_dd, lang),
            fmt_pct(m.bench_max_dd, lang),
            fmt_pp(m.max_dd - m.bench_max_dd, lang)
            if finite(m.max_dd) and finite(m.bench_max_dd)
            else na,
        ),
        (T("rpt.m_ir"), fmt_num(m.information_ratio, lang), na, na),
    ]
    return [
        (T("rpt.pb_absolute"), absolute),
        (T("rpt.pb_relative"), relative),
        (T("rpt.pb_risk_adjusted"), risk_adjusted),
    ]


def recovery_text(m: ReportMetrics, lang: str) -> str:
    """Caratteristiche di recupero del drawdown più profondo, in una frase."""
    if not m.episodes:
        return missing(lang)
    worst = m.episodes[0]
    if worst.recovery is None:
        return t_in(
            lang,
            "rpt.recovery_open",
            dd=fmt_pct(worst.depth, lang),
            peak=fmt_date(worst.peak),
            trough=fmt_date(worst.trough),
            days=worst.days_to_trough,
            current=fmt_pct(m.current_drawdown, lang),
        )
    return t_in(
        lang,
        "rpt.recovery_done",
        dd=fmt_pct(worst.depth, lang),
        peak=fmt_date(worst.peak),
        trough=fmt_date(worst.trough),
        days=worst.days_to_trough,
        recovery=fmt_date(worst.recovery),
        rdays=worst.days_to_recover,
    )


def review_points(
    m: ReportMetrics,
    profile_label: str | None,
    profile_band: float | None,
    in_eur: bool,
    lang: str,
) -> list[str]:
    """Punti da approfondire nella revisione con il cliente: descrittivi, mai operativi."""
    T = lambda key, **kw: t_in(lang, key, **kw)  # noqa: E731
    points: list[str] = []
    if profile_band is not None and finite(m.vol) and m.vol > profile_band:
        points.append(
            T(
                "rpt.rp_profile",
                profile=(profile_label or "").lower(),
                vol=fmt_pct(m.vol, lang),
                band=fmt_pct(profile_band, lang, 0),
            )
        )
    elif profile_band is None:
        points.append(T("rpt.rp_no_profile"))
    if finite(m.top_weight) and m.top_weight > 0.25:
        points.append(
            T("rpt.rp_concentration", ticker=m.top_ticker, weight=fmt_pct(m.top_weight, lang, 0))
        )
    for ticker in m.risk_over_weight[:2]:
        points.append(
            T(
                "rpt.rp_risk_weight",
                ticker=ticker,
                risk=fmt_pct(m.risk.get(ticker), lang, 0),
                weight=fmt_pct(m.weights.get(ticker), lang, 0),
            )
        )
    if in_eur and m.usd_weight >= RISK_LEVEL_USD[1]:
        points.append(T("rpt.rp_currency", share=fmt_pct(m.usd_weight, lang, 0)))
    if _sectors_known(m) and m.top_sector_weight >= RISK_LEVEL_SECTOR[1]:
        points.append(
            T("rpt.rp_sector", sector=m.top_sector, weight=fmt_pct(m.top_sector_weight, lang, 0))
        )
    if m.observations < SHORT_WINDOW_DAYS:
        points.append(T("rpt.rp_short_window"))
    if not points:
        points.append(T("rpt.rp_none"))
    return points


def investor_summary(
    m: ReportMetrics,
    benchmark: str,
    profile_label: str | None,
    profile_band: float | None,
    lang: str,
) -> tuple[list[str], list[str]]:
    """Sintesi e punti di attenzione del report Investor: le stesse regole della vista Advisor.

    Restituisce (frasi di sintesi, punti di attenzione). Nessun testo del motore
    di regole dell'app: solo frasi che citano ReportMetrics, nella lingua del PDF.
    """
    view = dict(investment_view(m, benchmark, profile_label, profile_band, lang))
    T = lambda key, **kw: t_in(lang, key, **kw)  # noqa: E731
    summary = [
        *view[T("rpt.vh_performance")],
        *view[T("rpt.vh_regime")][:1],
        *view[T("rpt.vh_concentration")],
        *view[T("rpt.vh_implications")][:2],
    ]
    attention = [text for text in view[T("rpt.vh_vulnerabilities")] if text != T("rpt.v_none")]
    return summary, attention
