"""Report Advisor: documento di revisione del portafoglio per il consulente professionale.

Struttura da portfolio review / comitato investimenti, non un cruscotto:

 1. Executive investment view   — sintesi d'investimento, frase per frase dai dati
 2. Portfolio profile           — Metric | Portfolio | Benchmark | Assessment
 3. Performance analysis        — base 100, mesi, episodi di drawdown, attribuzione
 4. Composition & concentration — posizioni complete, concentrazione, settori, valuta
 5. Risk analysis               — matrice per categoria di rischio, drawdown
 6. Stress testing              — impatto diretto e corretto per le correlazioni
 7. Scenario analysis           — Monte Carlo con metodologia dichiarata, scenari storici
 8. Suitability context         — profilo dichiarato e controlli di monitoraggio
 9. Composite score & observations — punteggio proprietario, rilievi, analisi what-if
10. Review considerations       — punti da approfondire, descrittivi
11. Methodology & disclosures

Stessi numeri del report Investor (analytics/report_metrics.py). Documento a
scorrimento: il numero di pagine segue il contenuto, con "Pagina n di N".
"""

from datetime import datetime

import pandas as pd
from reportlab.lib.units import mm
from reportlab.platypus import (
    CondPageBreak,
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from portfolio_intelligence.analytics.report_metrics import finite, rebased
from portfolio_intelligence.analytics.report_narrative import (
    investment_view,
    profile_rows,
    recovery_text,
    review_points,
)
from portfolio_intelligence.formatting import fmt_date, fmt_num, fmt_pp, missing
from portfolio_intelligence.visualization.pdf_common import (
    ACCENT,
    CONTENT_W,
    GREEN,
    LINE,
    MUTED,
    RED,
    ReportInput,
    bar_list_chart,
    callout,
    clean,
    data_table,
    fan_chart,
    kpi_grid,
    line_chart,
    monthly_chart,
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
    holdings_table,
    notices_block,
    projection_method,
    projection_table,
    stress_rows,
)

MAX_HOLDINGS_ROWS = 25


def _numbered(n: int, title: str) -> str:
    return f"{n}. {title}"


def _block(title: str, flowables: list, min_space: float = 45 * mm) -> list:
    """Titolo di sezione mai orfano a fondo pagina."""
    return [CondPageBreak(min_space), section(title), Spacer(1, 4), *flowables, Spacer(1, 9)]


def _cover(r: ReportInput, now: str, rid: str) -> list:
    s, T, m = styles(), r.T, r.metrics
    na = missing(r.lang)
    meta = [
        (T("adr.f_client"), r.portfolio_name),
        *([(T("adr.f_recipient"), r.recipient)] if r.recipient else []),
        (T("adr.f_advisor"), r.advisor or na),
        (T("adr.f_profile"), r.profile_label or T("ov.no_profile")),
        (T("adr.f_valuation"), fmt_date(m.end)),
        (
            T("adr.f_window"),
            T("adr.window_value", start=fmt_date(m.start), end=fmt_date(m.end), n=m.observations),
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
    table = Table(rows, colWidths=[45 * mm, CONTENT_W - 45 * mm])
    table.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 2.4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story: list = [
        Paragraph("SMARTEEFINANCE · PORTFOLIO INTELLIGENCE", s["wordmark"]),
        HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=8),
        Paragraph(T("adr.title"), s["h1"]),
        Paragraph(T("adr.subtitle"), s["sub"]),
        Spacer(1, 2),
        table,
        Spacer(1, 4),
        Paragraph(T("adr.cover_note"), s["caption"]),
        Spacer(1, 8),
    ]
    view = investment_view(m, r.benchmark, r.profile_label, r.profile_band, r.lang)
    content: list = []
    for heading, statements in view:
        content.append(Paragraph(clean(heading).upper(), s["h3"]))
        for text in statements:
            content.append(Paragraph(f"–&nbsp;&nbsp;{clean(text)}", s["body"]))
    story += [section(_numbered(1, T("adr.s1"))), Spacer(1, 2), *content]
    story.append(Paragraph(T("adr.s1_caption"), s["caption"]))
    return story


def _profile(r: ReportInput) -> list:
    s, T = styles(), r.T
    rows: list[list] = [
        [T("pdf.h_metric"), T("pdf.h_portfolio"), r.benchmark, T("adr.h_assessment")]
    ]
    for metric, pf, bench, assessment in profile_rows(r.metrics, r.total, r.benchmark, r.lang):
        rows.append([metric, pf, bench, Paragraph(clean(assessment), s["cell_muted"])])
    table = data_table(
        rows,
        [46 * mm, 26 * mm, 22 * mm, 80 * mm],
        right_from=1,
        extra=[
            ("ALIGN", (3, 0), (3, -1), "LEFT"),
            ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (2, 1), (2, -1), MUTED),
            ("LEFTPADDING", (3, 0), (3, -1), 8),
        ],
    )
    return _block(
        _numbered(2, T("adr.s2")),
        [table, Paragraph(T("adr.s2_caption", benchmark=r.benchmark), s["caption"])],
    )


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
                str(e.days_to_trough),
                fmt_date(e.recovery) if e.recovery is not None else T("adr.not_recovered"),
                str(e.days_to_recover) if e.days_to_recover is not None else na,
            ]
        )
    return data_table(rows, [28 * mm, 28 * mm, 24 * mm, 30 * mm, 32 * mm, 32 * mm], right_from=2)


def _attribution_rows(r: ReportInput) -> list[list]:
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
    if r.per_ticker_returns is None:
        return rows
    contrib = {
        ticker: (amount / r.total) * float(r.per_ticker_returns.get(ticker, float("nan")))
        for ticker, amount in r.positions.items()
        if r.total
    }
    ordered = sorted((kv for kv in contrib.items() if finite(kv[1])), key=lambda kv: -abs(kv[1]))[
        :8
    ]
    for ticker, value in ordered:
        rows.append(
            [
                ticker,
                r.pct(r.positions[ticker] / r.total),
                r.pct(r.per_ticker_returns.get(ticker), signed=True),
                fmt_pp(value, r.lang),
            ]
        )
    return rows


def _performance(r: ReportInput) -> list:
    s, T, m = styles(), r.T, r.metrics
    series = [(T("pdf.portfolio_legend"), rebased(r.pf_value), ACCENT, False)]
    if r.bench_value is not None:
        series.append((r.benchmark, rebased(r.bench_value), MUTED, True))
    flow: list = [
        line_chart(series, lambda v: fmt_num(v, r.lang, 0), height=58 * mm, reference=100.0),
        Paragraph(T("inv.growth_caption"), s["caption"]),
        Spacer(1, 6),
        Paragraph(clean(recovery_text(m, r.lang)), s["body"]),
        Spacer(1, 6),
    ]
    strip = _monthly_strip(r)
    if strip is not None:
        flow += [
            KeepTogether([Paragraph(T("adr.monthly_title").upper(), s["h3"]), strip]),
            Spacer(1, 6),
        ]
    flow += [
        KeepTogether([Paragraph(T("adr.episodes_title").upper(), s["h3"]), _episodes_table(r)]),
        Spacer(1, 6),
        KeepTogether(
            [
                Paragraph(T("adr.attribution_title").upper(), s["h3"]),
                data_table(_attribution_rows(r), [30 * mm, 40 * mm, 52 * mm, 52 * mm]),
                Paragraph(T("adr.attribution_caption"), s["caption"]),
            ]
        ),
    ]
    return _block(_numbered(3, T("adr.s3")), flow, min_space=90 * mm)


def _holdings(r: ReportInput) -> list:
    s, T, m = styles(), r.T, r.metrics
    strip = [
        (T("pdf.c_holdings"), str(len(r.positions)), ""),
        (T("pdf.c_effective"), fmt_num(m.effective_n, r.lang, 1), T("inv.eff_note")),
        (T("pdf.c_hhi"), fmt_num(m.hhi, r.lang), ""),
        (T("inv.c_top3"), r.pct(m.top3_weight, 0), ""),
        (T("rpt.m_usd"), r.pct(m.usd_weight, 0), ""),
        (T("inv.c_sector"), r.pct(m.top_sector_weight, 0), m.top_sector),
    ]
    currency = (
        {T("adr.ccy_usd"): m.usd_weight, T("adr.ccy_other"): max(0.0, 1 - m.usd_weight)}
        if m.usd_weight == m.usd_weight
        else {}
    )
    left = [
        Paragraph(T("pdf.wr_title").upper(), s["h3"]),
        weight_risk_chart(
            m.weights, m.risk, r.lang, T("pdf.legend_weight"), T("pdf.legend_risk"), max_rows=8
        ),
    ]
    right = [
        Paragraph(T("pdf.sector_title").upper(), s["h3"]),
        bar_list_chart(m.sector_weights, r.lang, other_label=T("pdf.other_sectors")),
        Spacer(1, 4),
        Paragraph(T("adr.currency_title").upper(), s["h3"]),
        bar_list_chart(pd.Series(currency, dtype=float), r.lang),
    ]
    flagged = (
        T(
            "adr.flagged",
            tickers=", ".join(m.risk_over_weight),
        )
        if m.risk_over_weight
        else T("adr.flagged_none")
    )
    flow = [
        holdings_table(r, with_sector=True, max_rows=MAX_HOLDINGS_ROWS),
        Paragraph(T("inv.holdings_caption"), s["caption"]),
        Spacer(1, 6),
        kpi_grid(strip, cols=6),
        Spacer(1, 6),
        side_by_side(left, right),
        Spacer(1, 4),
        Paragraph(clean(flagged), s["body"]),
    ]
    return _block(_numbered(4, T("adr.s4")), flow, min_space=80 * mm)


def _risk(r: ReportInput) -> list:
    s, T, m = styles(), r.T, r.metrics
    left: list = [
        Paragraph(T("pdf.underwater_title").upper(), s["h3"]),
        underwater_chart(
            r.pf_value,
            note=T("pdf.trough", dd=r.pct(m.max_dd), date=fmt_date(m.episodes[0].trough))
            if m.episodes
            else "",
        ),
    ]
    right: list = [Paragraph(T("pdf.monthly_title").upper(), s["h3"])]
    if r.monthly is not None and len(r.monthly.dropna()) >= 2:
        right.append(monthly_chart(r.monthly.tail(12), r.lang))
    flow = [
        _risk_table(r),
        Paragraph(T("inv.risk_caption"), s["caption"]),
        Spacer(1, 6),
        side_by_side(left, right),
    ]
    return _block(_numbered(5, T("adr.s5")), flow, min_space=80 * mm)


def _stress(r: ReportInput) -> list:
    s, T = styles(), r.T
    if not r.stress:
        flow: list = [Paragraph(T("pdf.no_scenario"), s["small"])]
    else:
        flow = [
            data_table(stress_rows(r), [86 * mm, 28 * mm, 30 * mm, 30 * mm]),
            Paragraph(T("inv.stress_caption"), s["caption"]),
            Paragraph(T("adr.stress_note"), s["caption"]),
        ]
    return _block(_numbered(6, T("adr.s6")), flow)


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
                    start=fmt_date(m.start),
                    end=fmt_date(m.end),
                    n=m.observations,
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
        paths = p.get("paths")
        if paths is not None:
            flow.append(
                fan_chart(
                    paths,
                    lambda v: r.eur(v),
                    lambda y: T("adr.year_tick", n=y),
                )
            )
            flow.append(Paragraph(T("adr.fan_caption"), s["caption"]))
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
    sc = m.scenarios
    if sc is not None:
        rows2: list[list] = [
            [T("inv.h_scenario"), T("inv.h_12m_return"), T("inv.h_value_after")],
            [T("inv.sc_bear"), r.pct(sc.bear, signed=True), r.eur(r.total * (1 + sc.bear))],
            [T("inv.sc_base"), r.pct(sc.base, signed=True), r.eur(r.total * (1 + sc.base))],
            [T("inv.sc_bull"), r.pct(sc.bull, signed=True), r.eur(r.total * (1 + sc.bull))],
        ]
        flow += [
            Paragraph(T("adr.hist_title").upper(), s["h3"]),
            data_table(rows2, [86 * mm, 44 * mm, 44 * mm]),
            Paragraph(
                T(
                    "inv.sc_method",
                    windows=fmt_num(sc.windows, r.lang, 0),
                    start=fmt_date(m.start),
                    end=fmt_date(m.end),
                    negative=r.pct(sc.share_negative, 0),
                    worst=r.pct(sc.worst, signed=True),
                    best=r.pct(sc.best, signed=True),
                ),
                s["caption"],
            ),
        ]
    return _block(_numbered(7, T("adr.s7")), flow, min_space=90 * mm)


def _suitability(r: ReportInput) -> list:
    s, T, m = styles(), r.T, r.metrics
    flow: list = []
    if r.profile_band is not None and r.profile_label:
        ok = finite(m.vol) and m.vol <= r.profile_band
        text = T(
            "inv.profile_check",
            status=T("pdf.within") if ok else T("pdf.outside"),
            vol=r.pct(m.vol),
            band=r.pct(r.profile_band, 0),
            profile=r.profile_label.lower(),
        )
        flow += [callout([Paragraph(text, s["body"])], color=GREEN if ok else RED), Spacer(1, 6)]
    else:
        flow += [
            callout([Paragraph(T("rpt.rp_no_profile"), s["body"])], color=MUTED),
            Spacer(1, 6),
        ]
    if r.monitoring:
        rows: list[list] = [
            [T("ov.col_check"), T("ov.col_measured"), T("ov.col_limit"), T("ov.col_status")]
        ]
        for chk in r.monitoring:
            color = {"ok": GREEN, "breach": RED}.get(chk["status"], MUTED).hexval()[2:]
            label = {"ok": T("ov.status_ok"), "breach": T("ov.status_breach")}.get(
                chk["status"], T("ov.status_na")
            )
            rows.append(
                [
                    Paragraph(clean(chk["label"]), s["cell"]),
                    chk["measured"],
                    chk["limit"],
                    Paragraph(f"<b><font color='#{color}'>{clean(label)}</font></b>", s["cell"]),
                ]
            )
        flow.append(data_table(rows, [64 * mm, 40 * mm, 40 * mm, 30 * mm], right_from=1))
        flow[-1].setStyle(TableStyle([("ALIGN", (3, 0), (3, -1), "LEFT")]))
    flow.append(Paragraph(T("adr.s8_caption"), s["caption"]))
    return _block(_numbered(8, T("adr.s8")), flow)


def _observations(r: ReportInput) -> list:
    s, T = styles(), r.T
    comp = {_component(r.lang, k): v for k, v in r.breakdown.items()}
    score = Paragraph(
        T("inv.score_line", score=r.health)
        + f" <font size=7 color='#5b6472'>{T('inv.score_caption')}</font>",
        s["body"],
    )
    obs: list = [Paragraph(T("adr.obs_title").upper(), s["h3"])]
    for item in r.observations[:6] or [T("pdf.none_flagged")]:
        obs.append(Paragraph(f"–&nbsp;&nbsp;{clean(item)}", s["body"]))
    flow: list = [
        callout([score], color=score_color(r.health)),
        Spacer(1, 4),
        side_by_side([score_bars(comp)], obs),
    ]
    if r.what_if:
        flow += [Spacer(1, 6), Paragraph(T("adr.whatif_title").upper(), s["h3"])]
        for item in r.what_if[:3]:
            flow.append(Paragraph(f"–&nbsp;&nbsp;{clean(item)}", s["body"]))
        flow.append(Paragraph(T("adr.whatif_caption"), s["caption"]))
    return _block(_numbered(9, T("adr.s9")), flow, min_space=70 * mm)


def _review(r: ReportInput) -> list:
    s, T = styles(), r.T
    points = review_points(r.metrics, r.profile_label, r.profile_band, r.in_eur, r.lang)
    flow: list = []
    for i, point in enumerate(points, start=1):
        flow.append(Paragraph(f"<b>{i:02d}</b>&nbsp;&nbsp;{clean(point)}", s["body"]))
        flow.append(Spacer(1, 2))
    flow.append(Paragraph(T("adr.s10_caption"), s["caption"]))
    return _block(_numbered(10, T("adr.s10")), flow)


def _methodology(r: ReportInput) -> list:
    s, T = styles(), r.T
    definitions = [
        T(f"adr.def_{key}")
        for key in ("te", "ir", "capture", "hhi", "risk", "episodes", "scenarios")
    ]
    flow: list = [
        notices_block(r),
        Spacer(1, 4),
        Paragraph(T("adr.defs_title").upper(), s["h3"]),
    ]
    flow += [Paragraph(clean(text), s["fine"]) for text in definitions]
    return [CondPageBreak(80 * mm), section(_numbered(11, T("adr.s11"))), Spacer(1, 4), *flow]


def build_advisor_report(r: ReportInput) -> bytes:
    """Il report Advisor come bytes PDF."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    rid = report_reference(r, now)
    story: list = [*_cover(r, now, rid), PageBreak()]
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
    return render_pdf(story, r, r.T("adr.doc_title"), rid)
