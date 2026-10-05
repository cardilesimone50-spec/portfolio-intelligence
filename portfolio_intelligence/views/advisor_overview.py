"""Panoramica cliente dell'area Advisor: una scheda di sintesi istituzionale.

Pensata per back office, boutique e consulenti professionali, non per il
risparmiatore: indicatori densi con il benchmark accanto, controlli di
monitoraggio con soglia e stato espliciti, performance in base 100, tabella
posizioni completa ed esportabile, rilievi numerati, reportistica in fondo.

Regole, testi e PDF sono gli stessi del Check-up Investor (views/checkup.py):
cambia la presentazione, non il calcolo.
"""

import html
import re

import pandas as pd
import streamlit as st

from portfolio_intelligence.analytics.insights import find_opportunities
from portfolio_intelligence.analytics.performance import (
    annualized_sharpe,
    max_drawdown,
)
from portfolio_intelligence.config import (
    HEALTH_SCORE_FAIR,
    MONITOR_MAX_CORRELATION,
    MONITOR_MAX_POSITION,
    MONITOR_MAX_RISK_SHARE,
    MONITOR_MAX_USD,
    MONITOR_MIN_DRAWDOWN,
)
from portfolio_intelligence.i18n import t
from portfolio_intelligence.portfolio.returns import per_ticker_cumulative_return
from portfolio_intelligence.ui.components import eur, num, pct, sec, signed_eur
from portfolio_intelligence.views import checkup
from portfolio_intelligence.views.common import BENCHMARK, PROFILE_VOL
from portfolio_intelligence.views.context import ViewContext
from portfolio_intelligence.visualization.charts import (
    GAIN_TEXT,
    LOSS,
    benchmark_overlay,
)
from portfolio_intelligence.visualization.pdf_advisor import build_advisor_report
from portfolio_intelligence.visualization.pdf_report import build_investor_report

OK, BREACH, NA = "ok", "breach", "na"

OVERVIEW_CSS = """
<style>
.fs-asof { font-size: 0.8rem; color: var(--muted); margin: 0 0 var(--s-3); }
.fs-asof b { color: var(--ink-2); font-weight: 600; }

/* griglia indicatori: 4 colonne, celle separate da filetti */
.fs-grid {
    display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
    background: var(--panel); border: 1px solid var(--line); border-radius: var(--r-lg);
    margin-bottom: var(--s-5);
}
.fs-cell { padding: var(--s-3) var(--s-4); border-left: 1px solid var(--line); }
.fs-cell:nth-child(4n + 1) { border-left: none; }
.fs-cell:nth-child(n + 5) { border-top: 1px solid var(--line); }
.fs-label {
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
    color: var(--muted);
}
.fs-value {
    font-size: 1.35rem; font-weight: 700; color: var(--ink); margin-top: var(--s-1);
    font-variant-numeric: tabular-nums; letter-spacing: -0.01em;
}
.fs-sub { font-size: 0.78rem; color: var(--muted); margin-top: 2px; font-variant-numeric: tabular-nums; }

/* controlli di monitoraggio */
.mon { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
.mon th {
    text-align: left; font-size: 0.68rem; font-weight: 600; letter-spacing: 0.06em;
    text-transform: uppercase; color: var(--muted); padding: 0 var(--s-2) var(--s-2) 0;
    border-bottom: 1px solid var(--line);
}
.mon th.num, .mon td.num { text-align: right; font-variant-numeric: tabular-nums; }
.mon td { padding: var(--s-2) var(--s-2) var(--s-2) 0; border-bottom: 1px solid var(--line);
          color: var(--ink-2); vertical-align: top; }
.mon td.check { color: var(--ink); font-weight: 600; }
.mon-pill {
    display: inline-block; font-size: 0.72rem; font-weight: 700; padding: 1px var(--s-2);
    border-radius: var(--r-sm); border: 1px solid currentColor; white-space: nowrap;
}
.fs-summary { font-size: 0.92rem; line-height: 1.6; color: var(--ink-2); }
.mon-summary { font-size: 0.86rem; color: var(--ink-2); margin-bottom: var(--s-2); }

/* rilievi numerati */
.obs { counter-reset: obs; margin: 0; padding: 0; list-style: none; }
.obs li {
    counter-increment: obs; position: relative; padding: var(--s-2) 0 var(--s-2) var(--s-6);
    border-bottom: 1px solid var(--line); font-size: 0.9rem; color: var(--ink-2); line-height: 1.5;
}
.obs li::before {
    content: counter(obs, decimal-leading-zero); position: absolute; left: 0; top: var(--s-2);
    font-weight: 700; color: var(--muted); font-variant-numeric: tabular-nums;
}

/* allocazione per settore */
.alloc-row { display: grid; grid-template-columns: 1.4fr 2fr 0.6fr; gap: var(--s-3);
             align-items: center; padding: 6px 0; font-size: 0.86rem; }
.alloc-row .name { color: var(--ink-2); }
.alloc-row .val { text-align: right; font-variant-numeric: tabular-nums; color: var(--ink); font-weight: 600; }
.alloc-track { height: 6px; background: var(--subtle); border-radius: 3px; }
.alloc-fill { height: 6px; background: var(--accent); border-radius: 3px; }

@media (max-width: 900px) {
    .fs-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .fs-cell:nth-child(4n + 1) { border-left: 1px solid var(--line); }
    .fs-cell:nth-child(2n + 1) { border-left: none; }
    .fs-cell:nth-child(n + 3) { border-top: 1px solid var(--line); }
}
</style>
"""


# ------------------------------------------------------------------ calcoli puri


def monitoring_checks(ctx: ViewContext) -> list[dict]:
    """Controlli di monitoraggio con misura, soglia e stato.

    Ogni voce: {"key", "label", "measured", "limit", "status"} con status in
    ok / breach / na. Soglie da config.py (MONITOR_*), le stesse usate da
    problemi e alert: Panoramica e PDF non si contraddicono.
    """
    assert ctx.computed is not None
    c = ctx.computed
    checks: list[dict] = []

    band = PROFILE_VOL.get(ctx.risk_profile)
    checks.append(
        {
            "key": "profile_vol",
            "label": t("ov.chk_profile_vol"),
            "measured": pct(c["annual_vol"]),
            "limit": f"≤ {pct(band, 0)}" if band is not None else t("ov.no_profile"),
            "status": NA if band is None else OK if c["annual_vol"] <= band else BREACH,
        }
    )

    weights = sorted(ctx.portfolio, key=lambda p: -p["weight"])
    if weights:
        top = weights[0]
        checks.append(
            {
                "key": "max_position",
                "label": t("ov.chk_max_position"),
                "measured": f"{top['ticker']} {pct(top['weight'], 0)}",
                "limit": f"≤ {pct(MONITOR_MAX_POSITION, 0)}",
                "status": OK if top["weight"] <= MONITOR_MAX_POSITION else BREACH,
            }
        )

    contributions = c["contributions"]
    if len(contributions) >= 2:
        share = float(contributions.iloc[0])
        checks.append(
            {
                "key": "risk_share",
                "label": t("ov.chk_risk_share"),
                "measured": f"{contributions.index[0]} {pct(share, 0)}",
                "limit": f"≤ {pct(MONITOR_MAX_RISK_SHARE, 0)}",
                "status": OK if share <= MONITOR_MAX_RISK_SHARE else BREACH,
            }
        )
        corr = c["avg_corr"]
        checks.append(
            {
                "key": "correlation",
                "label": t("ov.chk_correlation"),
                "measured": num(corr),
                "limit": f"≤ {num(MONITOR_MAX_CORRELATION)}",
                "status": NA
                if corr != corr
                else OK
                if corr <= MONITOR_MAX_CORRELATION
                else BREACH,
            }
        )

    checks.append(
        {
            "key": "usd",
            "label": t("ov.chk_usd"),
            "measured": pct(c["usd_weight"], 0),
            "limit": f"≤ {pct(MONITOR_MAX_USD, 0)}",
            "status": OK if c["usd_weight"] <= MONITOR_MAX_USD else BREACH,
        }
    )
    checks.append(
        {
            "key": "drawdown",
            "label": t("ov.chk_drawdown"),
            "measured": pct(c["drawdown"]),
            "limit": f"≥ {pct(MONITOR_MIN_DRAWDOWN, 0)}",
            "status": OK if c["drawdown"] >= MONITOR_MIN_DRAWDOWN else BREACH,
        }
    )
    checks.append(
        {
            "key": "health",
            "label": t("ov.chk_health"),
            "measured": f"{c['health']}/100",
            "limit": f"≥ {HEALTH_SCORE_FAIR}",
            "status": OK if c["health"] >= HEALTH_SCORE_FAIR else BREACH,
        }
    )
    return checks


def key_figures(ctx: ViewContext) -> list[tuple[str, str, str, str]]:
    """Le otto celle della griglia: (etichetta, valore, nota, colore del valore o '')."""
    assert ctx.computed is not None
    c = ctx.computed
    totals = ctx.pnl_totals or {}
    bench_value = (1 + c["bench_daily"]).cumprod()
    bench_cum = float(bench_value.iloc[-1] - 1)
    sharpe = annualized_sharpe(c["returns"], ctx.portfolio, risk_free_rate=ctx.risk_free)
    band = PROFILE_VOL.get(ctx.risk_profile)

    def tone(value: float | None) -> str:
        if value is None or value != value:
            return ""
        return GAIN_TEXT if value >= 0 else LOSS

    raw_pnl = totals.get("pnl")
    pnl = float(raw_pnl) if raw_pnl is not None else float("nan")
    pnl_known = pnl == pnl
    cost = totals.get("cost")
    return [
        (
            t("ov.kf_value"),
            eur(ctx.total),
            t("ov.kf_value_sub", n=len(ctx.amounts)),
            "",
        ),
        (
            t("ov.kf_pnl"),
            signed_eur(pnl) if pnl_known else "n/a",
            t("ov.kf_pnl_sub", pct=pct(totals.get("pnl_pct"), signed=True), cost=eur(cost))
            if pnl_known and cost
            else t("ov.kf_pnl_unknown"),
            tone(pnl),
        ),
        (
            t("ov.kf_irr"),
            pct(ctx.irr, signed=True) if ctx.irr is not None else "n/a",
            t("ov.kf_irr_sub"),
            tone(ctx.irr),
        ),
        (
            t("ov.kf_return", period=ctx.period),
            pct(c["cum_return"], signed=True),
            t("ov.kf_bench", benchmark=BENCHMARK, value=pct(bench_cum, signed=True)),
            tone(c["cum_return"]),
        ),
        (
            t("ov.kf_vol"),
            pct(c["annual_vol"]),
            t("ov.kf_vol_sub", band=pct(band, 0)) if band is not None else t("ov.no_profile"),
            "",
        ),
        (
            t("ov.kf_dd"),
            pct(c["drawdown"]),
            t(
                "ov.kf_bench",
                benchmark=BENCHMARK,
                value=pct(max_drawdown(bench_value)),
            ),
            "",
        ),
        (
            t("ov.kf_var"),
            eur(ctx.total * c["var_95"]),
            t("ov.kf_var_sub", pct=pct(c["var_95"])),
            "",
        ),
        (
            t("ov.kf_sharpe"),
            num(sharpe),
            t("ov.kf_sharpe_sub", beta=num(c["beta"]), benchmark=BENCHMARK),
            "",
        ),
    ]


def holdings_frame(ctx: ViewContext) -> pd.DataFrame:
    """Tabella posizioni completa: anagrafica, carico, mercato, P&L, rischio."""
    assert ctx.computed is not None
    c = ctx.computed
    fund = c["fund"]
    pos = ctx.pos if ctx.pos is not None else pd.DataFrame()
    cum = per_ticker_cumulative_return(c["prices"])
    rows = []
    for ticker in sorted(ctx.amounts, key=lambda k: -ctx.amounts[k]):

        def field(col: str, frame: pd.DataFrame = pos, key: str = ticker) -> float | None:
            if col not in frame.columns or key not in frame.index:
                return None
            value = frame.at[key, col]
            return None if pd.isna(value) else value

        rows.append(
            {
                "ticker": ticker,
                "name": ctx.names.get(ticker) or field("name", fund) or "",
                "sector": field("sector", fund) or "",
                "qty": field("qty"),
                "avg_cost": field("buy_price"),
                "last": field("current_price"),
                "value": ctx.amounts[ticker],
                "weight": ctx.amounts[ticker] / ctx.total if ctx.total else None,
                "pnl": field("pnl"),
                "pnl_pct": field("pnl_pct"),
                "risk": float(c["contributions"].get(ticker, float("nan"))),
                "period_return": cum.get(ticker),
            }
        )
    return pd.DataFrame(rows)


def sector_weights(ctx: ViewContext) -> pd.Series:
    assert ctx.computed is not None
    fund = ctx.computed["fund"]
    sectors = (
        fund["sector"].reindex(list(ctx.amounts))
        if "sector" in fund.columns
        else pd.Series(index=list(ctx.amounts), dtype=object)
    )
    sectors = sectors.fillna(t("pdf.not_classified")).replace("", t("pdf.not_classified"))
    weights = pd.Series(ctx.amounts, dtype=float) / ctx.total
    return weights.groupby(sectors).sum().sort_values(ascending=False)


# ------------------------------------------------------------------ disegno


def _status_pill(status: str) -> str:
    color, label = {
        OK: (GAIN_TEXT, t("ov.status_ok")),
        BREACH: (LOSS, t("ov.status_breach")),
    }.get(status, ("var(--muted)", t("ov.status_na")))
    return f'<span class="mon-pill" style="color:{color}">{label}</span>'


def _key_figures_html(cells: list[tuple[str, str, str, str]]) -> str:
    return (
        '<div class="fs-grid">'
        + "".join(
            f'<div class="fs-cell"><div class="fs-label">{label}</div>'
            f'<div class="fs-value"{f" style=color:{color}" if color else ""}>{value}</div>'
            f'<div class="fs-sub">{sub}</div></div>'
            for label, value, sub, color in cells
        )
        + "</div>"
    )


def _checks_html(checks: list[dict]) -> str:
    rows = "".join(
        f'<tr><td class="check">{chk["label"]}</td><td class="num">{chk["measured"]}</td>'
        f'<td class="num">{chk["limit"]}</td><td>{_status_pill(chk["status"])}</td></tr>'
        for chk in checks
    )
    return (
        '<table class="mon"><thead><tr>'
        f'<th>{t("ov.col_check")}</th><th class="num">{t("ov.col_measured")}</th>'
        f'<th class="num">{t("ov.col_limit")}</th><th>{t("ov.col_status")}</th>'
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


def _sector_html(weights: pd.Series) -> str:
    return "".join(
        f'<div class="alloc-row"><span class="name">{html.escape(str(name))}</span>'
        f'<div class="alloc-track"><div class="alloc-fill" style="width:{w:.0%}"></div></div>'
        f'<span class="val">{pct(w, 1)}</span></div>'
        for name, w in weights.items()
    )


def _holdings_table(ctx: ViewContext) -> None:
    frame = holdings_frame(ctx)
    ccy = "EUR" if ctx.in_eur else t("ov.native_ccy")

    def signed(value: float) -> str:
        return ("+" if value > 0 else "") + num(value, 0)

    def tone(value) -> str:
        if value is None or value != value:
            return ""
        return f"color: {GAIN_TEXT if value >= 0 else LOSS}"

    # numeri formattati con le convenzioni della lingua dell'interfaccia, come il
    # resto della pagina; lo Styler cambia solo la visualizzazione, l'ordinamento
    # delle colonne resta numerico
    styled = frame.style.format(
        {
            "qty": lambda v: num(v, 0) if float(v).is_integer() else num(v, 4),
            "avg_cost": lambda v: num(v, 2),
            "last": lambda v: num(v, 2),
            "value": lambda v: num(v, 0),
            "weight": lambda v: pct(v, 1),
            "pnl": signed,
            "pnl_pct": lambda v: pct(v, 1, signed=True),
            "risk": lambda v: pct(v, 1),
            "period_return": lambda v: pct(v, 1, signed=True),
        },
        na_rep="n/a",
    ).map(tone, subset=["pnl", "pnl_pct"])
    st.dataframe(
        styled,
        column_config={
            "ticker": st.column_config.TextColumn(t("chk.col_ticker")),
            "name": st.column_config.TextColumn(t("fund.name")),
            "sector": st.column_config.TextColumn(t("fund.sector")),
            "qty": st.column_config.NumberColumn(t("pos.qty")),
            "avg_cost": st.column_config.NumberColumn(t("ov.col_avg_cost")),
            "last": st.column_config.NumberColumn(t("ov.col_last")),
            "value": st.column_config.NumberColumn(t("ov.col_value", ccy=ccy)),
            "weight": st.column_config.NumberColumn(t("chk.col_weight")),
            "pnl": st.column_config.NumberColumn(t("ov.col_pnl", ccy=ccy)),
            "pnl_pct": st.column_config.NumberColumn(t("ov.col_pnl_pct")),
            "risk": st.column_config.NumberColumn(t("ov.col_risk")),
            "period_return": st.column_config.NumberColumn(t("chk.col_return", period=ctx.period)),
        },
        hide_index=True,
        width="stretch",
    )
    note_col, export_col = st.columns([3, 1], vertical_alignment="center")
    note_col.caption(t("ov.holdings_note"))
    export_col.download_button(
        t("ov.export_csv"),
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name=f"{ctx.portfolio_name}_holdings_{pd.Timestamp.now():%Y%m%d}.csv",
        mime="text/csv",
        width="stretch",
        key="ov_export_holdings",
    )


def render(ctx: ViewContext, recipient_field) -> None:
    """Disegna la Panoramica. `recipient_field()` disegna il campo intestazione PDF."""
    assert ctx.computed is not None
    c = ctx.computed
    st.markdown(OVERVIEW_CSS, unsafe_allow_html=True)

    price_date = pd.Timestamp(c["prices"].index[-1])
    st.markdown(
        '<div class="fs-asof">'
        + " · ".join(
            [
                t("ov.asof", date=f"<b>{price_date:%d/%m/%Y}</b>"),
                t("ov.ccy", ccy="<b>EUR</b>" if ctx.in_eur else f"<b>{t('ov.native_ccy')}</b>"),
                t("ov.window", period=f"<b>{ctx.period}</b>"),
                t("ov.benchmark", benchmark=f"<b>{BENCHMARK}</b>"),
            ]
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(_key_figures_html(key_figures(ctx)), unsafe_allow_html=True)

    checks = monitoring_checks(ctx)
    breaches = sum(chk["status"] == BREACH for chk in checks)
    perf_col, mon_col = st.columns([1.35, 1], gap="large")
    with perf_col:
        sec(t("ov.perf_title", benchmark=BENCHMARK))
        st.altair_chart(
            benchmark_overlay(c["pf_value"], (1 + c["bench_daily"]).cumprod(), BENCHMARK),
            width="stretch",
        )
        st.caption(t("ov.perf_note"))
    with mon_col:
        sec(t("ov.monitor_title"))
        summary_color = LOSS if breaches else GAIN_TEXT
        st.markdown(
            f'<div class="mon-summary" style="color:{summary_color}">'
            + (
                t("ov.monitor_breaches", n=breaches, total=len(checks))
                if breaches
                else t("ov.monitor_clear", total=len(checks))
            )
            + "</div>"
            + _checks_html(checks),
            unsafe_allow_html=True,
        )
        st.caption(t("ov.monitor_note"))

    sec(t("ov.holdings_title"))
    _holdings_table(ctx)
    if ctx.pnl_totals and not ctx.pnl_totals.get("cost_known", True):
        st.caption(t("pos.cost_unknown"))

    problems = checkup.top_problems(ctx)
    exec_text = checkup.executive_text(ctx)
    obs_col, alloc_col = st.columns([1.35, 1], gap="large")
    with obs_col:
        sec(t("ov.obs_title"))
        observations = problems + find_opportunities(ctx.portfolio, c["fund"])[:2]
        if observations:
            st.markdown(
                '<ol class="obs">'
                + "".join(
                    f"<li>{re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html.escape(text))}</li>"
                    for text in observations
                )
                + "</ol>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(t("chk.no_problems"))
        sec(t("ov.summary_title"))
        summary_html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(exec_text))
        st.markdown(f'<div class="fs-summary">{summary_html}</div>', unsafe_allow_html=True)
        st.caption(t("chk.exec_caption"))
    with alloc_col:
        sec(t("ov.sector_title"))
        st.markdown(_sector_html(sector_weights(ctx)), unsafe_allow_html=True)
        sec(t("ov.scenario_title"))
        simulations, discarded, has_candidates = checkup.scenario_results(ctx)
        for text in simulations:
            st.markdown(text)
        if not simulations:
            st.caption(t("chk.no_improve") if has_candidates else t("chk.no_scenario"))

    sec(t("ov.reporting_title"))
    with st.container(border=True):
        field_col, adv_col, client_col, save_col = st.columns(
            [1.5, 1.1, 1.1, 0.9], vertical_alignment="bottom"
        )
        with field_col:
            ctx.report_recipient = recipient_field()
        # dati preparati qui (sessione, lingua, Monte Carlo in cache); il PDF si
        # impagina solo al clic, in un thread separato
        report = checkup.report_input(ctx, exec_text, problems, simulations, monitoring=checks)
        stamp = f"{pd.Timestamp.now():%Y%m%d}"
        with adv_col:
            st.download_button(
                t("ov.pdf_advisor"),
                data=lambda: build_advisor_report(report),
                file_name=f"{ctx.portfolio_name}_review_{stamp}.pdf",
                mime="application/pdf",
                width="stretch",
                type="primary",
                key="ov_pdf_advisor",
            )
        with client_col:
            st.download_button(
                t("ov.pdf_client"),
                data=lambda: build_investor_report(report),
                file_name=f"{ctx.portfolio_name}_report_{stamp}.pdf",
                mime="application/pdf",
                width="stretch",
                key="ov_pdf_client",
            )
        with save_col:
            checkup.save_snapshot_button(ctx)
        st.caption(t("ov.reports_note"))
        checkup.history_panel(ctx)
