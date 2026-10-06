"""Report Advisor: revisione di portafoglio per il consulente professionale.

Documento da comitato investimenti, non un cruscotto. Copertina con indice,
poi una sezione per pagina (la stessa numerazione dell'indice):

 1. Executive investment view   — dati principali e sintesi, frase per frase dai dati
 2. Portfolio profile           — Metric | Portfolio | Benchmark | Assessment
 3. Performance analysis        — base 100, anni solari, rendimento mobile a 12 mesi,
                                  mesi, episodi di drawdown, attribuzione
 4. Composition & concentration — posizioni, concentrazione, settori, valuta,
                                  fondamentali per titolo
 5. Risk analysis               — matrice dei rischi, rischio di coda, volatilità mobile,
                                  drawdown, correlazioni tra titoli, rischio per settore
 6. Stress testing              — scenari diretti e corretti, peggiori periodi storici
 7. Scenario analysis           — Monte Carlo con metodologia dichiarata, esiti storici
 8. Suitability context         — profilo dichiarato e controlli di monitoraggio
 9. Composite score & what-if   — punteggio proprietario, ricalcoli a pesi alternativi
10. Review considerations       — punti da approfondire e firma della revisione
11. Methodology & disclosures   — note, fonti, definizioni

Stessi numeri del report Investor (analytics/report_metrics.py); intestazione
col marchio e "Pagina n di N" su ogni pagina (visualization/pdf_common.py).
"""

from datetime import datetime

import pandas as pd
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

from portfolio_intelligence.analytics.report_metrics import (
    calendar_returns,
    finite,
    rebased,
    rolling_return,
    rolling_volatility,
    tail_risk,
    worst_windows,
)
from portfolio_intelligence.analytics.report_narrative import (
    investment_view,
    profile_rows,
    recovery_text,
    review_points,
)
from portfolio_intelligence.formatting import fmt_date, fmt_num, fmt_pp, missing
from portfolio_intelligence.ui.brand import mark_drawing
from portfolio_intelligence.visualization.pdf_common import (
    ACCENT,
    CONTENT_W,
    GREEN,
    INK,
    LINE,
    MUTED,
    RED,
    ReportInput,
    bar_list_chart,
    callout,
    clean,
    data_table,
    fan_chart,
    heatmap_table,
    kpi_grid,
    line_chart,
    render_pdf,
    report_reference,
    score_bars,
    score_color,
    section,
    side_by_side,
    styles,
    underwater_chart,
    weight_risk_chart,
)
from portfolio_intelligence.visualization.pdf_report import (
    _component,
    _risk_table,
    historical_block,
    holdings_table,
    notices_block,
    profile_check_box,
    projection_method,
    projection_table,
    stress_rows,
)

MAX_HOLDINGS_ROWS = 25
MAX_CORRELATION_HOLDINGS = 10


def _numbered(n: int, title: str) -> str:
    return f"{n}. {title}"


def _section_page(title: str, flowables: list) -> list:
    """Una sezione per pagina, come un documento da comitato."""
    return [PageBreak(), section(title), Spacer(1, 5), *flowables]


def _h3(text: str):
    return Paragraph(clean(text).upper(), styles()["h3"])


def _titled(title: str, *flowables) -> KeepTogether:
    """Sottotitolo unito al suo contenuto: mai un titolo solo a fondo pagina."""
    return KeepTogether([_h3(title), *flowables])


def _pct_axis(r: ReportInput):
    return lambda v: r.pct(v, 0)


# ------------------------------------------------------------------ copertina


def _cover(r: ReportInput, now: str, rid: str, toc: TableOfContents) -> list:
    s, T, m = styles(), r.T, r.metrics
    na = missing(r.lang)
    brand = Table(
        [
            [
                mark_drawing(11 * mm),
                Paragraph(
                    "SMARTEE<font color='#1E40AF'><b>FINANCE</b></font>",
                    ParagraphStyle(
                        "brand", parent=s["body"], fontSize=14, leading=16, textColor=INK
                    ),
                ),
            ]
        ],
        colWidths=[14 * mm, CONTENT_W - 14 * mm],
    )
    brand.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    meta = [
        (T("adr.f_client"), r.portfolio_name),
        *([(T("adr.f_recipient"), r.recipient)] if r.recipient else []),
        (T("adr.f_advisor"), r.advisor or na),
        (T("adr.f_profile"), r.profile_label or T("ov.no_profile")),
        (T("adr.f_valuation"), fmt_date(m.end)),
        (
            T("adr.f_window"),
            T(
                "adr.window_value",
                start=fmt_date(m.start),
                end=fmt_date(m.end),
                n=fmt_num(m.observations, r.lang, 0),
            ),
        ),
        (T("adr.f_benchmark"), r.benchmark),
        (T("adr.f_currency"), T("pdf.currency_eur") if r.in_eur else T("pdf.currency_orig")),
        (T("adr.f_source"), r.price_source or T("rep.source_unknown")),
        (T("adr.f_reference"), f"{rid} · {now}"),
    ]
    rows = [
        [Paragraph(clean(k), s["cell_muted"]), Paragraph(f"<b>{clean(v)}</b>", s["cell"])]
        for k, v in meta
    ]
    table = Table(rows, colWidths=[48 * mm, CONTENT_W - 48 * mm])
    table.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 2.6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    title = ParagraphStyle("cover_title", parent=s["h1"], fontSize=30, leading=34, spaceBefore=0)
    client = ParagraphStyle(
        "cover_client", parent=s["body"], fontSize=15, leading=19, textColor=ACCENT, spaceAfter=4
    )
    return [
        brand,
        Spacer(1, 26 * mm),
        Paragraph(T("adr.title"), title),
        Paragraph(clean(r.portfolio_name), client),
        Paragraph(T("adr.subtitle"), s["sub"]),
        Spacer(1, 8 * mm),
        table,
        Spacer(1, 9 * mm),
        _h3(T("adr.contents")),
        toc,
        Spacer(1, 8 * mm),
        callout([Paragraph(T("adr.confidential"), s["small"])], color=MUTED),
    ]


# ------------------------------------------------------------------ 1-2


def _key_figures(r: ReportInput) -> Table:
    T, m = r.T, r.metrics
    lang = r.lang
    pnl_known = r.pnl is not None and finite(r.pnl)
    cells = [
        (T("ov.kf_value"), r.eur(r.total), T("ov.kf_value_sub", n=len(r.positions))),
        (
            T("ov.kf_pnl"),
            r.eur(r.pnl, signed=True) if pnl_known else missing(lang),
            r.pct(r.pnl_pct, signed=True) if pnl_known else T("ov.kf_pnl_unknown"),
        ),
        (
            T("inv.k_total_return", period=r.period),
            r.pct(m.cum_return, signed=True),
            T("inv.k_bench", benchmark=r.benchmark, value=r.pct(m.bench_cum_return, signed=True)),
        ),
        (
            T("rpt.m_cagr"),
            r.pct(m.cagr, signed=True),
            T("inv.k_bench", benchmark=r.benchmark, value=r.pct(m.bench_cagr, signed=True)),
        ),
        (
            T("rpt.m_vol"),
            r.pct(m.vol),
            T("inv.k_bench", benchmark=r.benchmark, value=r.pct(m.bench_vol)),
        ),
        (
            T("rpt.m_maxdd"),
            r.pct(m.max_dd),
            T("inv.k_bench", benchmark=r.benchmark, value=r.pct(m.bench_max_dd)),
        ),
        (
            T("rpt.m_sharpe"),
            fmt_num(m.sharpe, lang),
            T("inv.k_bench", benchmark=r.benchmark, value=fmt_num(m.bench_sharpe, lang)),
        ),
        (
            T("rpt.m_beta", benchmark=r.benchmark),
            fmt_num(m.beta, lang),
            T("inv.k_corr", corr=fmt_num(m.correlation, lang)),
        ),
    ]

    def tone(value):
        return INK if value is None or not finite(value) else GREEN if value >= 0 else RED

    tones = {1: tone(r.pnl if pnl_known else None), 2: tone(m.cum_return), 3: tone(m.cagr)}
    return kpi_grid(cells, cols=4, colors_by_index=tones)


def _executive(r: ReportInput) -> list:
    s, T, m = styles(), r.T, r.metrics
    flow: list = [_h3(T("adr.kf_title")), _key_figures(r), Spacer(1, 6)]
    check = profile_check_box(r)
    if check is not None:
        flow += [check, Spacer(1, 4)]
    for heading, statements in investment_view(
        m, r.benchmark, r.profile_label, r.profile_band, r.lang
    ):
        block = [_h3(heading)]
        block += [Paragraph(f"–&nbsp;&nbsp;{clean(text)}", s["body"]) for text in statements]
        flow.append(KeepTogether(block))
    flow.append(Paragraph(T("adr.s1_caption"), s["caption"]))
    return [section(_numbered(1, T("adr.s1"))), Spacer(1, 5), *flow]


def _profile(r: ReportInput) -> list:
    s, T = styles(), r.T
    rows: list[list] = [
        [T("pdf.h_metric"), T("pdf.h_portfolio"), r.benchmark, T("adr.h_assessment")]
    ]
    for metric, pf, bench, assessment in profile_rows(
        r.metrics, r.eur(r.total), r.benchmark, r.lang, r.in_eur
    ):
        rows.append([metric, pf, bench, Paragraph(clean(assessment), s["cell_muted"])])
    table = data_table(
        rows,
        [46 * mm, 26 * mm, 22 * mm, 80 * mm],
        right_from=1,
        font_size=8.2,
        extra=[
            ("ALIGN", (3, 0), (3, -1), "LEFT"),
            ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (2, 1), (2, -1), MUTED),
            ("LEFTPADDING", (3, 0), (3, -1), 8),
            ("TOPPADDING", (0, 1), (-1, -1), 3.6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 3.6),
        ],
    )
    return _section_page(
        _numbered(2, T("adr.s2")),
        [table, Paragraph(T("adr.s2_caption", benchmark=r.benchmark), s["caption"])],
    )


# ------------------------------------------------------------------ 3. performance


def _calendar_table(r: ReportInput) -> Table | None:
    T = r.T
    if r.pf_daily is None:
        return None
    years = calendar_returns(r.pf_daily, r.bench_daily)
    if years.empty:
        return None
    rows: list[list] = [
        [T("adr.h_year"), T("pdf.h_portfolio"), r.benchmark, T("inv.h_difference")]
    ]
    extra: list = []
    for i, (year, row) in enumerate(years.iterrows(), start=1):
        label = f"{year} {T('adr.partial')}" if row["partial"] else str(year)
        diff = row["portfolio"] - row["benchmark"] if finite(row["benchmark"]) else float("nan")
        rows.append(
            [
                label,
                r.pct(row["portfolio"], signed=True),
                r.pct(row["benchmark"], signed=True),
                fmt_pp(diff, r.lang),
            ]
        )
        if finite(diff):
            extra.append(("TEXTCOLOR", (3, i), (3, i), GREEN if diff >= 0 else RED))
    return data_table(rows, [50 * mm, 40 * mm, 40 * mm, 44 * mm], extra=extra)


def _monthly_strip(r: ReportInput) -> Table | None:
    """Ultimi dodici mesi in orizzontale: portafoglio, benchmark e differenza."""
    T = r.T
    if r.monthly is None or len(r.monthly.dropna()) < 2:
        return None
    pf = r.monthly.dropna().tail(12)
    bench = r.bench_monthly
    na = missing(r.lang)
    header = [""] + [date.strftime("%m/%y") for date in pf.index]
    pf_row = [T("pdf.h_portfolio")] + [r.pct(v, signed=True) for v in pf]
    bench_row = [r.benchmark]
    diff_row = [T("inv.h_difference")]
    extra: list = []
    for col, (date, value) in enumerate(pf.items(), start=1):
        b = bench.get(date) if bench is not None else None
        bench_row.append(r.pct(b, signed=True) if b is not None else na)
        if b is not None and finite(b):
            diff = value - b
            diff_row.append(fmt_pp(diff, r.lang).replace(" pp", ""))
            extra.append(("TEXTCOLOR", (col, 3), (col, 3), GREEN if diff >= 0 else RED))
        else:
            diff_row.append(na)
    first = 22 * mm
    width = (CONTENT_W - first) / len(pf)
    return data_table(
        [header, pf_row, bench_row, diff_row],
        [first] + [width] * len(pf),
        font_size=6.8,
        zebra=False,
        extra=[
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 6.4),
            *extra,
        ],
    )


def _episodes_table(r: ReportInput) -> Table:
    T, m = r.T, r.metrics
    na = missing(r.lang)
    rows: list[list] = [
        [
            T("adr.h_peak"),
            T("adr.h_trough"),
            T("adr.h_depth"),
            T("adr.h_to_trough"),
            T("adr.h_recovery"),
            T("adr.h_to_recover"),
        ]
    ]
    for e in m.episodes:
        rows.append(
            [
                fmt_date(e.peak),
                fmt_date(e.trough),
                r.pct(e.depth),
                fmt_num(e.days_to_trough, r.lang, 0),
                fmt_date(e.recovery) if e.recovery is not None else T("adr.not_recovered"),
                fmt_num(e.days_to_recover, r.lang, 0) if e.days_to_recover is not None else na,
            ]
        )
    return data_table(rows, [28 * mm, 28 * mm, 24 * mm, 30 * mm, 32 * mm, 32 * mm], right_from=2)


def _attribution_table(r: ReportInput) -> Table:
    """Contributo approssimato al rendimento: peso attuale × rendimento del titolo nella finestra."""
    T = r.T
    rows: list[list] = [
        [
            T("pdf.h_ticker"),
            T("inv.h_weight"),
            T("pdf.h_return", period=r.period),
            T("adr.h_contribution"),
        ]
    ]
    if r.per_ticker_returns is not None and r.total:
        contrib = {
            ticker: (amount / r.total) * float(r.per_ticker_returns.get(ticker, float("nan")))
            for ticker, amount in r.positions.items()
        }
        ordered = sorted(
            (kv for kv in contrib.items() if finite(kv[1])), key=lambda kv: -abs(kv[1])
        )[:10]
        for ticker, value in ordered:
            rows.append(
                [
                    ticker,
                    r.pct(r.positions[ticker] / r.total),
                    r.pct(r.per_ticker_returns.get(ticker), signed=True),
                    fmt_pp(value, r.lang),
                ]
            )
    return data_table(rows, [30 * mm, 40 * mm, 52 * mm, 52 * mm])


def _performance(r: ReportInput) -> list:
    s, T, m = styles(), r.T, r.metrics
    series = [(T("pdf.portfolio_legend"), rebased(r.pf_value), ACCENT, False)]
    if r.bench_value is not None:
        series.append((r.benchmark, rebased(r.bench_value), MUTED, True))
    flow: list = [
        _titled(
            T("adr.growth_title", benchmark=r.benchmark),
            line_chart(series, lambda v: fmt_num(v, r.lang, 0), height=60 * mm, reference=100.0),
            Paragraph(T("inv.growth_caption"), s["caption"]),
        ),
        Spacer(1, 4),
        Paragraph(clean(recovery_text(m, r.lang)), s["body"]),
        Spacer(1, 6),
    ]
    calendar = _calendar_table(r)
    if calendar is not None:
        flow += [
            _titled(
                T("adr.calendar_title"),
                calendar,
                Paragraph(T("adr.calendar_caption"), s["caption"]),
            ),
            Spacer(1, 6),
        ]
    if r.pf_daily is not None:
        rolling_pf = rolling_return(r.pf_daily)
        if len(rolling_pf) >= 2:
            lines = [(T("pdf.portfolio_legend"), rolling_pf, ACCENT, False)]
            if r.bench_daily is not None:
                lines.append(
                    (
                        r.benchmark,
                        rolling_return(r.bench_daily).loc[rolling_pf.index[0] :],
                        MUTED,
                        True,
                    )
                )
            flow += [
                _titled(
                    T("adr.rolling_title"),
                    line_chart(lines, _pct_axis(r), height=48 * mm, reference=0.0),
                    Paragraph(T("adr.rolling_caption"), s["caption"]),
                ),
                Spacer(1, 6),
            ]
    strip = _monthly_strip(r)
    if strip is not None:
        flow += [_titled(T("adr.monthly_title"), strip), Spacer(1, 6)]
    flow += [
        _titled(T("adr.episodes_title"), _episodes_table(r)),
        Spacer(1, 6),
        _titled(
            T("adr.attribution_title"),
            _attribution_table(r),
            Paragraph(T("adr.attribution_caption"), s["caption"]),
        ),
    ]
    return _section_page(_numbered(3, T("adr.s3")), flow)


# ------------------------------------------------------------------ 4. composizione


def _fundamentals_table(r: ReportInput) -> Table | None:
    """Caratteristiche fondamentali per titolo (dove i dati esistono)."""
    T = r.T
    fund = r.fund
    if fund is None or fund.empty:
        return None
    columns = [
        ("pe", T("rpt.m_pe_short"), "num1"),
        ("ps", "P/S", "num1"),
        ("net_margin", T("fund.net_margin"), "pct"),
        ("revenue_growth", T("fund.rev_growth"), "pct_signed"),
        ("dividend_yield", T("fund.div_yield"), "pp"),
        ("debt_to_equity", T("fund.de"), "num1"),
    ]
    present = [c for c in columns if c[0] in fund.columns]
    ordered = sorted(r.positions, key=lambda k: -r.positions[k])[:MAX_HOLDINGS_ROWS]
    sub = fund.reindex(ordered)
    if sub[[c[0] for c in present]].isna().all().all():
        return None
    na = missing(r.lang)

    def cell(value, kind: str) -> str:
        v = pd.to_numeric(value, errors="coerce")
        if v != v:
            return na
        if kind == "pct":
            return r.pct(v)
        if kind == "pct_signed":
            return r.pct(v, signed=True)
        if kind == "pp":
            return fmt_num(v, r.lang, 2) + "%"
        return fmt_num(v, r.lang, 1)

    rows: list[list] = [[T("pdf.h_ticker"), *[label for _, label, _ in present]]]
    for ticker in ordered:
        rows.append([ticker, *[cell(sub.at[ticker, col], kind) for col, _, kind in present]])
    first = 22 * mm
    width = (CONTENT_W - first) / len(present)
    return data_table(rows, [first] + [width] * len(present), bold_first_col=True)


def _holdings(r: ReportInput) -> list:
    s, T, m = styles(), r.T, r.metrics
    strip = [
        (T("pdf.c_holdings"), str(len(r.positions)), ""),
        (T("pdf.c_effective"), fmt_num(m.effective_n, r.lang, 1), T("inv.eff_note")),
        (T("pdf.c_hhi"), fmt_num(m.hhi, r.lang), ""),
        (T("inv.c_top3"), r.pct(m.top3_weight, 0), ""),
        (T("rpt.m_usd"), r.pct(m.usd_weight, 0), ""),
        (
            T("inv.c_sector"),
            r.pct(m.top_sector_weight, 0) if m.top_sector else missing(r.lang),
            m.top_sector,
        ),
    ]
    currency = (
        {T("adr.ccy_usd"): m.usd_weight, T("adr.ccy_other"): max(0.0, 1 - m.usd_weight)}
        if m.usd_weight == m.usd_weight
        else {}
    )
    left = [
        _h3(T("pdf.wr_title")),
        weight_risk_chart(
            m.weights, m.risk, r.lang, T("pdf.legend_weight"), T("pdf.legend_risk"), max_rows=8
        ),
    ]
    right = [
        _h3(T("pdf.sector_title")),
        bar_list_chart(m.sector_weights, r.lang, other_label=T("pdf.other_sectors")),
        Spacer(1, 4),
        _h3(T("adr.currency_title")),
        bar_list_chart(pd.Series(currency, dtype=float), r.lang),
    ]
    flagged = (
        T("adr.flagged", tickers=", ".join(m.risk_over_weight))
        if m.risk_over_weight
        else T("adr.flagged_none")
    )
    flow: list = [
        holdings_table(r, with_sector=True, max_rows=MAX_HOLDINGS_ROWS),
        Paragraph(T("inv.holdings_caption"), s["caption"]),
    ]
    if r.coverage_notes:
        flow.append(
            Paragraph(
                T("pdf.coverage") + " · ".join(clean(n) for n in r.coverage_notes), s["caption"]
            )
        )
    flow += [
        Spacer(1, 6),
        kpi_grid(strip, cols=6),
        Spacer(1, 6),
        side_by_side(left, right),
        Spacer(1, 4),
        Paragraph(clean(flagged), s["body"]),
        Spacer(1, 6),
    ]
    fundamentals = _fundamentals_table(r)
    if fundamentals is not None:
        flow.append(
            _titled(
                T("adr.fund_title"), fundamentals, Paragraph(T("adr.fund_caption"), s["caption"])
            )
        )
    return _section_page(_numbered(4, T("adr.s4")), flow)


# ------------------------------------------------------------------ 5. rischio


def _tail_table(r: ReportInput) -> Table | None:
    T = r.T
    if r.pf_daily is None:
        return None
    rows: list[list] = [
        [T("pdf.h_metric"), T("pdf.h_portfolio"), r.benchmark, T("inv.h_difference")]
    ]
    for key, pf, bench in tail_risk(r.pf_daily, r.bench_daily):
        diff = fmt_pp(pf - bench, r.lang) if finite(pf) and finite(bench) else missing(r.lang)
        rows.append([T(f"adr.tail_{key}"), r.pct(pf), r.pct(bench), diff])
    return data_table(rows, [74 * mm, 34 * mm, 34 * mm, 32 * mm])


def _sector_risk_table(r: ReportInput) -> Table | None:
    """Peso sul capitale e contributo al rischio aggregati per settore."""
    m, T = r.metrics, r.T
    if m.sector_weights.empty:
        return None
    rows: list[list] = [
        [T("adr.h_sector"), T("adr.h_sector_weight"), T("adr.h_sector_risk"), T("inv.h_ratio")]
    ]
    for sector, weight in m.sector_weights.items():
        risk = float(m.sector_risk.get(sector, float("nan")))
        ratio = risk / weight if finite(risk) and weight else float("nan")
        rows.append(
            [
                str(sector)[:40],
                r.pct(weight),
                r.pct(risk),
                f"{fmt_num(ratio, r.lang, 2)}×" if finite(ratio) else missing(r.lang),
            ]
        )
    return data_table(rows, [74 * mm, 34 * mm, 34 * mm, 32 * mm])


def _correlation(r: ReportInput):
    if r.returns is None or len(r.positions) < 2:
        return None
    top = [t for t in sorted(r.positions, key=lambda k: -r.positions[k]) if t in r.returns.columns]
    top = top[:MAX_CORRELATION_HOLDINGS]
    if len(top) < 2:
        return None
    corr = r.returns[top].corr(min_periods=20)
    return heatmap_table(corr, r.lang)


def _risk(r: ReportInput) -> list:
    s, T, m = styles(), r.T, r.metrics
    flow: list = [_risk_table(r), Paragraph(T("inv.risk_caption"), s["caption"]), Spacer(1, 6)]
    tail = _tail_table(r)
    if tail is not None:
        flow += [
            _titled(T("adr.tail_title"), tail, Paragraph(T("adr.tail_caption"), s["caption"])),
            Spacer(1, 6),
        ]
    if r.pf_daily is not None:
        vol_pf = rolling_volatility(r.pf_daily)
        if len(vol_pf) >= 2:
            lines = [(T("pdf.portfolio_legend"), vol_pf, ACCENT, False)]
            if r.bench_daily is not None:
                lines.append(
                    (
                        r.benchmark,
                        rolling_volatility(r.bench_daily).loc[vol_pf.index[0] :],
                        MUTED,
                        True,
                    )
                )
            flow += [
                _titled(
                    T("adr.rollvol_title"),
                    line_chart(lines, _pct_axis(r), height=46 * mm),
                    Paragraph(T("adr.rollvol_caption"), s["caption"]),
                ),
                Spacer(1, 6),
            ]
    flow += [
        _titled(
            T("pdf.underwater_title"),
            underwater_chart(
                r.pf_value,
                width=CONTENT_W,
                height=42 * mm,
                note=T("pdf.trough", dd=r.pct(m.max_dd), date=fmt_date(m.episodes[0].trough))
                if m.episodes
                else "",
            ),
        ),
        Spacer(1, 6),
    ]
    corr = _correlation(r)
    if corr is not None:
        flow += [
            _titled(T("adr.corr_title"), corr, Paragraph(T("adr.corr_caption"), s["caption"])),
            Spacer(1, 6),
        ]
    sector_table = _sector_risk_table(r)
    if sector_table is not None:
        flow.append(_titled(T("adr.sector_risk_title"), sector_table))
    return _section_page(_numbered(5, T("adr.s5")), flow)


# ------------------------------------------------------------------ 6-7


def _worst_table(r: ReportInput, days: int) -> Table | None:
    T = r.T
    if r.pf_daily is None:
        return None
    windows = worst_windows(r.pf_daily, r.bench_daily, days)
    if not windows:
        return None
    rows: list[list] = [
        [
            T("adr.h_window"),
            T("pdf.h_portfolio"),
            r.benchmark,
            T("inv.h_difference"),
            T("inv.h_amount"),
        ]
    ]
    for w in windows:
        diff = (
            fmt_pp(w["portfolio"] - w["benchmark"], r.lang)
            if finite(w["benchmark"])
            else missing(r.lang)
        )
        rows.append(
            [
                f"{fmt_date(w['start'])} – {fmt_date(w['end'])}".replace("–", "-"),
                r.pct(w["portfolio"]),
                r.pct(w["benchmark"]),
                diff,
                r.eur(r.total * w["portfolio"], signed=True),
            ]
        )
    return data_table(rows, [54 * mm, 28 * mm, 28 * mm, 30 * mm, 34 * mm])


def _stress(r: ReportInput) -> list:
    s, T = styles(), r.T
    flow: list = []
    if r.stress:
        flow += [
            data_table(stress_rows(r), [86 * mm, 28 * mm, 30 * mm, 30 * mm]),
            Paragraph(T("inv.stress_caption"), s["caption"]),
            Paragraph(T("adr.stress_note"), s["caption"]),
            Spacer(1, 8),
        ]
    else:
        flow.append(Paragraph(T("pdf.no_scenario"), s["small"]))
    for days in (21, 63):
        table = _worst_table(r, days)
        if table is not None:
            flow += [_titled(T(f"adr.worst_{days}"), table), Spacer(1, 6)]
    flow.append(Paragraph(T("adr.worst_caption"), s["caption"]))
    return _section_page(_numbered(6, T("adr.s6")), flow)


def _scenarios(r: ReportInput) -> list:
    s, T, m = styles(), r.T, r.metrics
    flow: list = []
    p = r.projection
    if p:
        method_lines = [
            (T("adr.mc_f_method"), T(f"rep.mc_method_{p.get('method', 'bootstrap')}")),
            (T("adr.mc_f_sims"), fmt_num(p.get("n", 0), r.lang, 0)),
            (
                T("adr.mc_f_history"),
                T(
                    "adr.window_value",
                    start=fmt_date(p.get("hist_start", m.start)),
                    end=fmt_date(p.get("hist_end", m.end)),
                    n=fmt_num(p.get("hist_days", m.observations), r.lang, 0),
                ),
            ),
            (T("adr.mc_f_weights"), T("adr.mc_v_weights")),
            (T("adr.mc_f_costs"), T("adr.mc_v_costs")),
            (T("adr.mc_f_nature"), T("adr.mc_v_nature")),
        ]
        rows = [
            [Paragraph(clean(k), s["cell_muted"]), Paragraph(clean(v), s["cell"])]
            for k, v in method_lines
        ]
        method_table = Table(rows, colWidths=[40 * mm, CONTENT_W - 48 * mm])
        method_table.setStyle(
            TableStyle(
                [
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        flow += [callout([method_table]), Spacer(1, 6)]
        if p.get("hist_days", m.observations) < 2 * 252:
            flow += [Paragraph(T("adr.mc_short"), s["small"]), Spacer(1, 4)]
        paths = p.get("paths")
        if paths is not None:
            flow.append(
                _titled(
                    T("adr.fan_title"),
                    fan_chart(
                        paths,
                        lambda v: r.eur(v),
                        lambda y: T("adr.year_tick", n=y),
                        height=60 * mm,
                    ),
                    Paragraph(T("adr.fan_caption"), s["caption"]),
                )
            )
            flow.append(Spacer(1, 4))
        flow.append(projection_table(r))
        cagr_rows = p.get("cagr", {})
        if cagr_rows:
            flow.append(
                Paragraph(
                    T(
                        "adr.mc_cagr",
                        horizon=p.get("horizon", 5),
                        p10=r.pct(cagr_rows.get("p10"), signed=True),
                        p50=r.pct(cagr_rows.get("p50"), signed=True),
                        p90=r.pct(cagr_rows.get("p90"), signed=True),
                    ),
                    s["caption"],
                )
            )
        flow.append(Paragraph(projection_method(r), s["caption"]))
        flow.append(Spacer(1, 6))
    else:
        flow.append(Paragraph(T("adr.mc_unavailable"), s["small"]))
    flow.append(KeepTogether([_h3(T("adr.hist_title")), *historical_block(r)]))
    return _section_page(_numbered(7, T("adr.s7")), flow)


# ------------------------------------------------------------------ 8-11


def _suitability(r: ReportInput) -> list:
    s, T = styles(), r.T
    flow: list = []
    check = profile_check_box(r)
    if check is not None:
        flow += [check, Spacer(1, 6)]
    else:
        flow += [
            callout([Paragraph(T("rpt.rp_no_profile"), s["body"])], color=MUTED),
            Spacer(1, 6),
        ]
    # il punteggio composito non è un criterio di adeguatezza: resta nella sezione 9
    checks = [chk for chk in (r.monitoring or []) if chk.get("key") != "health"]
    if checks:
        rows: list[list] = [
            [T("ov.col_check"), T("ov.col_measured"), T("ov.col_limit"), T("ov.col_status")]
        ]
        extra: list = []
        for i, chk in enumerate(checks, start=1):
            color = {"ok": GREEN, "breach": RED}.get(chk["status"], MUTED)
            label = {"ok": T("ov.status_ok"), "breach": T("ov.status_breach")}.get(
                chk["status"], T("ov.status_na")
            )
            rows.append([chk["label"], chk["measured"], chk["limit"], label])
            extra += [
                ("TEXTCOLOR", (3, i), (3, i), color),
                ("FONTNAME", (3, i), (3, i), "Helvetica-Bold"),
            ]
        flow.append(
            data_table(
                rows,
                [64 * mm, 40 * mm, 40 * mm, 30 * mm],
                right_from=1,
                extra=[("ALIGN", (3, 0), (3, -1), "LEFT"), *extra],
            )
        )
    flow.append(Paragraph(T("adr.s8_caption"), s["caption"]))
    return _section_page(_numbered(8, T("adr.s8")), flow)


def _observations(r: ReportInput) -> list:
    s, T = styles(), r.T
    comp = {_component(r.lang, k): v for k, v in r.breakdown.items()}
    score = Paragraph(
        T("inv.score_line", score=r.health)
        + f" <font size=7 color='#5b6472'>{T('inv.score_caption')}</font>",
        s["body"],
    )
    flow: list = [
        callout([score], color=score_color(r.health)),
        Spacer(1, 4),
        side_by_side(
            [score_bars(comp)],
            [Paragraph(T("inv.score_components_text", score=r.health), s["small"])],
        ),
    ]
    if r.what_if:
        flow += [Spacer(1, 8), _h3(T("adr.whatif_title"))]
        for item in r.what_if[:4]:
            flow.append(Paragraph(f"–&nbsp;&nbsp;{clean(item)}", s["body"]))
        flow.append(Paragraph(T("adr.whatif_caption"), s["caption"]))
    return _section_page(_numbered(9, T("adr.s9")), flow)


def _signoff(r: ReportInput) -> Table:
    """Riquadro firme della revisione (compilazione a mano o digitale)."""
    s, T = styles(), r.T
    rows = [
        [
            Paragraph(T("adr.so_prepared"), s["cell_muted"]),
            Paragraph(clean(r.advisor or ""), s["cell"]),
            Paragraph(T("adr.so_date"), s["cell_muted"]),
            "",
        ],
        [
            Paragraph(T("adr.so_reviewed"), s["cell_muted"]),
            "",
            Paragraph(T("adr.so_date"), s["cell_muted"]),
            "",
        ],
        [
            Paragraph(T("adr.so_client"), s["cell_muted"]),
            "",
            Paragraph(T("adr.so_date"), s["cell_muted"]),
            "",
        ],
    ]
    table = Table(rows, colWidths=[38 * mm, 74 * mm, 18 * mm, 44 * mm], rowHeights=[12 * mm] * 3)
    table.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (1, 0), (1, -1), 0.5, MUTED),
                ("LINEBELOW", (3, 0), (3, -1), 0.5, MUTED),
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def _review(r: ReportInput) -> list:
    s, T = styles(), r.T
    points = review_points(r.metrics, r.profile_label, r.profile_band, r.in_eur, r.lang)
    flow: list = []
    for i, point in enumerate(points, start=1):
        flow.append(Paragraph(f"<b>{i:02d}</b>&nbsp;&nbsp;{clean(point)}", s["body"]))
        flow.append(Spacer(1, 3))
    flow.append(Paragraph(T("adr.s10_caption"), s["caption"]))
    flow += [
        Spacer(1, 12),
        KeepTogether(
            [
                _h3(T("adr.signoff_title")),
                Spacer(1, 2),
                _signoff(r),
                Paragraph(T("adr.signoff_caption"), s["caption"]),
            ]
        ),
    ]
    return _section_page(_numbered(10, T("adr.s10")), flow)


def _methodology(r: ReportInput) -> list:
    s, T = styles(), r.T
    definitions = [
        T(f"adr.def_{key}")
        for key in (
            "te",
            "ir",
            "capture",
            "hhi",
            "risk",
            "episodes",
            "scenarios",
            "tail",
            "rolling",
        )
    ]
    flow: list = [notices_block(r), Spacer(1, 6), _h3(T("adr.defs_title"))]
    flow += [Paragraph(clean(text), s["fine"]) for text in definitions]
    return _section_page(_numbered(11, T("adr.s11")), flow)


def build_advisor_report(r: ReportInput) -> bytes:
    """La revisione di portafoglio Advisor come bytes PDF."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    rid = report_reference(r, now, "advisor")
    s = styles()
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            "toc0", parent=s["body"], fontSize=8.6, leading=13, leftIndent=0, firstLineIndent=0
        )
    ]
    toc.dotsMinLevel = 0
    story: list = [*_cover(r, now, rid, toc), PageBreak()]
    story += _executive(r)
    story += _profile(r)
    story += _performance(r)
    story += _holdings(r)
    story += _risk(r)
    story += _stress(r)
    story += _scenarios(r)
    story += _suitability(r)
    story += _observations(r)
    story += _review(r)
    story += _methodology(r)
    return render_pdf(
        story,
        r,
        r.T("adr.doc_title"),
        rid,
        header_right=f"{r.T('adr.title')} · {r.portfolio_name} · {fmt_date(r.metrics.end)}",
        cover=True,
        toc=toc,
    )
