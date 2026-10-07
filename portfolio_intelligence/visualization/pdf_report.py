"""Report Investor: quattro pagine di qualità istituzionale, leggibili da un investitore informato.

Pagina 1 — Panoramica: cruscotto di indicatori, punteggio composito
           proprietario, verifica del profilo, sintesi, performance in base 100.
Pagina 2 — Performance e benchmark: assoluta, relativa, corretta per il
           rischio; caratteristiche di recupero; drawdown e mesi.
Pagina 3 — Composizione e rischio: posizioni con peso sul capitale e
           contributo al rischio, concentrazione, settori, matrice dei rischi.
Pagina 4 — Stress test, scenari storici (e proiezione Monte Carlo solo nella
           copia predisposta dal consulente), punti di attenzione, metodologia.

Gli stessi numeri del report Advisor (visualization/pdf_advisor.py), da
analytics/report_metrics.py: cambia solo la profondità della presentazione.
Ogni pagina è racchiusa in un KeepInFrame: se il contenuto eccede si
restringe, così il documento resta sempre di quattro pagine.
"""

from datetime import datetime

from reportlab.lib.units import mm
from reportlab.platypus import KeepInFrame, PageBreak, Paragraph, Spacer

from portfolio_intelligence.analytics.report_metrics import finite, rebased
from portfolio_intelligence.analytics.report_narrative import (
    SHORT_WINDOW_DAYS,
    investor_summary,
    performance_blocks,
    recovery_text,
    risk_matrix,
)
from portfolio_intelligence.formatting import fmt_date, fmt_num, fmt_pp, missing
from portfolio_intelligence.i18n import t_in
from portfolio_intelligence.visualization.pdf_common import (
    ACCENT,
    CONTENT_W,
    FRAME_H,
    GREEN,
    HALF_W,
    INK,
    LEVEL_COLORS,
    MUTED,
    RED,
    ReportInput,
    bar_list_chart,
    callout,
    clean,
    data_table,
    kpi_grid,
    line_chart,
    monthly_chart,
    page_header,
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

PAGES = 4
MAX_HOLDINGS_ROWS = 12


def _tone(value: float | None):
    if value is None or not finite(value):
        return INK
    return GREEN if value >= 0 else RED


def dashboard_cells(r: ReportInput) -> tuple[list[tuple[str, str, str]], dict[int, object]]:
    """Le sedici celle della panoramica e i colori dei valori con segno."""
    m, T, lang = r.metrics, r.T, r.lang
    na = missing(lang)
    has_cost = (
        r.invested is not None and finite(r.invested) and r.pnl is not None and finite(r.pnl)
    )
    cells = [
        (T("inv.k_value"), r.eur(r.total), T("inv.k_value_note", n=len(r.positions))),
        (
            T("inv.k_invested"),
            r.eur(r.invested) if has_cost else na,
            (T("inv.k_invested_note") if r.cost_known else T("inv.k_invested_partial"))
            if has_cost
            else T("inv.k_cost_unknown"),
        ),
        (
            T("inv.k_pnl"),
            r.eur(r.pnl, signed=True) if has_cost else na,
            r.pct(r.pnl_pct, signed=True) if has_cost else T("inv.k_cost_unknown"),
        ),
        (
            T("inv.k_total_return", period=r.period_label),
            r.pct(m.cum_return, signed=True),
            T("inv.k_window", start=fmt_date(m.start), end=fmt_date(m.end)),
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
            T("rpt.m_sortino"),
            fmt_num(m.sortino, lang),
            T("inv.k_bench", benchmark=r.benchmark, value=fmt_num(m.bench_sortino, lang)),
        ),
        (
            T("rpt.m_beta", benchmark=r.benchmark),
            fmt_num(m.beta, lang),
            T("inv.k_corr", corr=fmt_num(m.correlation, lang)),
        ),
        (T("rpt.m_alpha"), r.pct(m.alpha, signed=True), T("inv.k_alpha_note")),
        (T("rpt.m_var"), r.pct(m.var95), r.eur(r.total * m.var95) if finite(m.var95) else na),
        (T("rpt.m_es"), r.pct(m.es95), r.eur(r.total * m.es95) if finite(m.es95) else na),
        (
            T("inv.k_concentration"),
            T("inv.k_hhi", hhi=fmt_num(m.hhi, lang)),
            T(
                "inv.k_concentration_note",
                n=fmt_num(m.effective_n, lang, 1),
                ticker=m.top_ticker,
                weight=r.pct(m.top_weight, 0),
            ),
        ),
        (
            T("inv.k_bench_return"),
            r.pct(m.bench_cum_return, signed=True),
            T("inv.k_bench_note", benchmark=r.benchmark),
        ),
        (
            T("inv.k_relative"),
            fmt_pp(m.excess_return, lang),
            T("inv.k_relative_note", benchmark=r.benchmark),
        ),
    ]
    colors_by_index = {
        2: _tone(r.pnl if has_cost else None),
        3: _tone(m.cum_return),
        4: _tone(m.cagr),
        10: _tone(m.alpha),
        14: _tone(m.bench_cum_return),
        15: _tone(m.excess_return),
    }
    return cells, colors_by_index


def _page1(r: ReportInput, now: str, rid: str) -> list:
    s, T = styles(), r.T
    m = r.metrics
    meta = [r.portfolio_name]
    if r.advisor:
        meta.append(T("pdf.prepared_by", advisor=r.advisor))
    if r.profile_label:
        meta.append(T("pdf.profile", profile=r.profile_label.lower()))
    meta += [
        T("pdf.window", start=fmt_date(m.start), end=fmt_date(m.end)),
        T("pdf.generated", now=now),
        T("rep.ref", rid=rid),
        T("pdf.currency_eur") if r.in_eur else T("pdf.currency_orig"),
    ]
    story: list = [
        Paragraph(T("inv.title"), s["h1"]),
    ]
    if r.recipient:
        story.append(Paragraph(clean(T("pdf.prepared_for", recipient=r.recipient)), s["sub"]))
    story += [Paragraph(clean(" · ".join(meta)), s["sub"]), Spacer(1, 2)]

    story += [section(T("inv.s_overview")), Spacer(1, 4)]
    cells, tones = dashboard_cells(r)
    story += [kpi_grid(cells, cols=4, colors_by_index=tones), Spacer(1, 6)]

    score = Paragraph(
        T("inv.score_line", score=r.health)
        + f" <font size=7 color='#5b6472'>{T('inv.score_caption')}</font>",
        s["body"],
    )
    story += [callout([score], color=score_color(r.health)), Spacer(1, 5)]

    check = profile_check_box(r)
    if check is not None:
        story += [check, Spacer(1, 5)]

    # sintesi dalle stesse regole della revisione Advisor, nella lingua del documento
    summary, _ = investor_summary(m, r.benchmark, r.profile_label, r.profile_band, r.lang)
    story += [section(T("inv.s_summary")), Spacer(1, 4)]
    for sentence in summary or [T("pdf.no_summary")]:
        story.append(Paragraph(f"–&nbsp;&nbsp;{clean(sentence)}", s["body"]))
    story.append(Spacer(1, 7))

    story += [section(T("inv.s_growth", benchmark=r.benchmark)), Spacer(1, 4)]
    series = [(T("pdf.portfolio_legend"), rebased(r.pf_value), ACCENT, False)]
    if r.bench_value is not None:
        series.append((r.benchmark, rebased(r.bench_value), MUTED, True))
    story.append(
        line_chart(series, lambda v: fmt_num(v, r.lang, 0), height=54 * mm, reference=100.0)
    )
    story.append(Paragraph(T("inv.growth_caption"), s["caption"]))
    if r.coverage_notes:
        story.append(
            Paragraph(
                T("pdf.coverage") + " · ".join(clean(note) for note in r.coverage_notes),
                s["caption"],
            )
        )
    return story


def _page2(r: ReportInput, now: str) -> list:
    s, T, m, lang = styles(), r.T, r.metrics, r.lang
    story = page_header(r, T("inv.p2_title", benchmark=r.benchmark), now)
    header = [T("pdf.h_metric"), T("pdf.h_portfolio"), r.benchmark, T("inv.h_difference")]
    widths = [70 * mm, 34 * mm, 34 * mm, 36 * mm]
    for title, rows in performance_blocks(m, r.benchmark, lang):
        story += [section(title), Spacer(1, 3)]
        story += [data_table([header, *[list(row) for row in rows]], widths), Spacer(1, 6)]
    story.append(Paragraph(T("inv.alpha_caveat"), s["caption"]))
    story.append(Spacer(1, 6))

    story += [section(T("inv.s_recovery")), Spacer(1, 4)]
    story.append(Paragraph(clean(recovery_text(m, lang)), s["body"]))
    story.append(Spacer(1, 6))

    left: list = [Paragraph(T("pdf.underwater_title").upper(), s["h3"])]
    left.append(
        underwater_chart(
            r.pf_value,
            note=T("pdf.trough", dd=r.pct(m.max_dd), date=fmt_date(m.episodes[0].trough))
            if m.episodes
            else "",
        )
    )
    right: list = [Paragraph(T("pdf.monthly_title").upper(), s["h3"])]
    if r.monthly is not None and len(r.monthly.dropna()) >= 2:
        right.append(monthly_chart(r.monthly.tail(12), lang))
    else:
        right.append(Paragraph(T("pdf.no_history"), s["small"]))
    story += [side_by_side(left, right), Spacer(1, 8)]

    story += [section(T("inv.s_score")), Spacer(1, 4)]
    comp = {_component(lang, k): v for k, v in r.breakdown.items()}
    story.append(
        side_by_side(
            [score_bars(comp)],
            [Paragraph(T("inv.score_components_text", score=r.health), s["small"])],
        )
    )
    return story


def _component(lang: str, name: str) -> str:
    translated = t_in(lang, f"comp.{name}")
    return name if translated.startswith("comp.") else translated


def holdings_table(r: ReportInput, with_sector: bool = False, max_rows: int = MAX_HOLDINGS_ROWS):
    """Posizioni con peso sul capitale accanto al contributo al rischio.

    I rapporti rischio/peso oltre la soglia sono in rosso grassetto; le celle
    restano testo semplice, così righe e colonne numeriche restano allineate.
    """
    T, m = r.T, r.metrics
    na = missing(r.lang)
    header = [T("pdf.h_ticker"), T("pdf.h_company")]
    if with_sector:
        header.append(T("adr.h_sector"))
    header += [
        T("inv.h_value"),
        T("inv.h_weight"),
        T("inv.h_risk"),
        T("inv.h_ratio"),
        T("pdf.h_return", period=r.period_label),
        T("pdf.h_pnl"),
    ]
    first_num = 3 if with_sector else 2
    ratio_col = first_num + 3
    rows: list[list] = [header]
    extra: list = []
    ordered = sorted(r.positions.items(), key=lambda kv: -kv[1])
    shown, rest = ordered[:max_rows], ordered[max_rows:]
    for ticker, amount in shown:
        weight = amount / r.total if r.total else float("nan")
        risk = float(m.risk.get(ticker, float("nan")))
        ratio = risk / weight if finite(risk) and weight else float("nan")
        ret = r.per_ticker_returns.get(ticker) if r.per_ticker_returns is not None else None
        pnl = r.per_ticker_pnl.get(ticker) if r.per_ticker_pnl is not None else None
        row = [ticker, r.names.get(ticker, "")[: 24 if with_sector else 30]]
        if with_sector:
            row.append(str(r.sector_of.get(ticker, ""))[:18])
        row += [
            r.eur(amount),
            r.pct(weight),
            r.pct(risk),
            f"{fmt_num(ratio, r.lang, 2)}×" if finite(ratio) else na,
            r.pct(ret, signed=True) if ret is not None else na,
            r.eur(pnl, signed=True) if pnl is not None and finite(pnl) else na,
        ]
        rows.append(row)
        if ticker in m.risk_over_weight:
            n = len(rows) - 1
            extra += [
                ("TEXTCOLOR", (ratio_col, n), (ratio_col, n), RED),
                ("FONTNAME", (ratio_col, n), (ratio_col, n), "Helvetica-Bold"),
            ]
    if rest:
        rest_total = sum(amount for _, amount in rest)
        filler = [""] * (len(header) - first_num - 2)
        rows.append(
            [f"+{len(rest)}", T("pdf.other_holdings")]
            + ([""] if with_sector else [])
            + [r.eur(rest_total), r.pct(rest_total / r.total), *filler]
        )
    names_muted = [
        ("TEXTCOLOR", (1, 1), (first_num - 1, -1), MUTED),
        ("FONTSIZE", (1, 1), (first_num - 1, -1), 7.2),
    ]
    if with_sector:
        widths = [13 * mm, 27 * mm, 20 * mm, 19 * mm, 15 * mm, 18 * mm, 18 * mm, 22 * mm, 22 * mm]
    else:
        widths = [15 * mm, 41 * mm, 23 * mm, 17 * mm, 17 * mm, 17 * mm, 22 * mm, 22 * mm]
    return data_table(
        rows,
        widths,
        right_from=first_num,
        bold_first_col=True,
        font_size=7.4 if with_sector else 7.8,
        extra=names_muted + extra,
    )


def _page3(r: ReportInput, now: str) -> list:
    s, T, m, lang = styles(), r.T, r.metrics, r.lang
    story = page_header(r, T("inv.p3_title"), now)
    story += [section(T("inv.s_holdings")), Spacer(1, 3)]
    story.append(holdings_table(r))
    story.append(Paragraph(T("inv.holdings_caption"), s["caption"]))
    story.append(flagged_note(r))
    story.append(Spacer(1, 6))

    strip = [
        (T("pdf.c_holdings"), str(len(r.positions)), ""),
        (T("pdf.c_effective"), fmt_num(m.effective_n, lang, 1), T("inv.eff_note")),
        (T("pdf.c_hhi"), fmt_num(m.hhi, lang), ""),
        (T("inv.c_top3"), r.pct(m.top3_weight, 0), ""),
        (T("rpt.m_usd"), r.pct(m.usd_weight, 0), ""),
        (T("inv.c_sector"), r.pct(m.top_sector_weight, 0), m.top_sector),
    ]
    story += [kpi_grid(strip, cols=6), Spacer(1, 6)]

    left = [
        Paragraph(T("pdf.wr_title").upper(), s["h3"]),
        weight_risk_chart(
            m.weights,
            m.risk,
            lang,
            T("pdf.legend_weight"),
            T("pdf.legend_risk"),
            width=HALF_W,
            max_rows=6,
        ),
    ]
    right = [
        Paragraph(T("pdf.sector_title").upper(), s["h3"]),
        bar_list_chart(m.sector_weights, lang, other_label=T("pdf.other_sectors")),
        Paragraph(T("inv.sector_caption"), s["caption"]),
    ]
    story += [side_by_side(left, right), Spacer(1, 6)]

    story += [section(T("inv.s_risk")), Spacer(1, 3)]
    story.append(_risk_table(r))
    story.append(Paragraph(T("inv.risk_caption"), s["caption"]))
    return story


def _risk_table(r: ReportInput):
    s, T = styles(), r.T
    rows: list[list] = [
        [T("inv.h_category"), T("inv.h_measure"), T("inv.h_level"), T("inv.h_evidence")]
    ]
    for row in risk_matrix(r.metrics, r.in_eur, r.benchmark, r.lang):
        color = LEVEL_COLORS.get(row["level"], INK).hexval()[2:]
        rows.append(
            [
                Paragraph(f"<b>{clean(row['category'])}</b>", s["cell"]),
                Paragraph(clean(row["measure"]), s["cell"]),
                Paragraph(
                    f"<b><font color='#{color}'>{clean(row['level_label'])}</font></b>", s["cell"]
                ),
                Paragraph(clean(row["evidence"]), s["cell_muted"]),
            ]
        )
    return data_table(rows, [34 * mm, 42 * mm, 20 * mm, 78 * mm], right_from=None)


def stress_rows(r: ReportInput) -> list[list]:
    """Tabella degli stress test: impatto diretto e corretto per le correlazioni, in % e importo."""
    s, T = styles(), r.T
    na = missing(r.lang)
    rows: list[list] = [
        [T("inv.h_scenario"), T("inv.h_direct"), T("inv.h_total"), T("inv.h_amount")]
    ]
    for test in r.stress:
        args = dict(test.get("label_args", {}))
        if "weight" in args:
            args["weight"] = r.pct(args["weight"], 0)
        if "share" in args:
            args["share"] = r.pct(args["share"], 0)
        label = T(f"stress.{test['key']}", benchmark=r.benchmark, **args)
        impact = test["total"] if test["total"] is not None else test["direct"]
        rows.append(
            [
                Paragraph(clean(label), s["cell"]),
                r.pct(test["direct"], signed=True) if test["direct"] is not None else na,
                r.pct(test["total"], signed=True) if test["total"] is not None else na,
                r.eur(r.total * impact, signed=True) if impact is not None else na,
            ]
        )
    return rows


def _page4(r: ReportInput, now: str) -> list:
    s, T, m, lang = styles(), r.T, r.metrics, r.lang
    story = page_header(r, T("inv.p4_title"), now)

    story += [section(T("inv.s_stress")), Spacer(1, 3)]
    if r.stress:
        story.append(data_table(stress_rows(r), [86 * mm, 28 * mm, 30 * mm, 30 * mm]))
        story.append(Paragraph(T("inv.stress_caption"), s["caption"]))
    else:
        story.append(Paragraph(T("pdf.no_scenario"), s["small"]))
    story.append(Spacer(1, 7))

    story += [section(T("inv.s_scenarios")), Spacer(1, 3)]
    story += historical_block(r)
    story.append(Spacer(1, 7))

    if r.projection:
        story += [section(T("inv.s_projection")), Spacer(1, 3)]
        story.append(projection_table(r))
        story.append(Paragraph(projection_method(r), s["caption"]))
        story.append(Spacer(1, 7))

    _, attention = investor_summary(m, r.benchmark, r.profile_label, r.profile_band, lang)
    story += [section(T("pdf.attention_title")), Spacer(1, 3)]
    if attention:
        for item in attention[:4]:
            story.append(Paragraph(f"–&nbsp;&nbsp;{clean(item)}", s["body"]))
            story.append(Spacer(1, 2))
    else:
        story.append(Paragraph(T("pdf.none_flagged"), s["small"]))
    story.append(Paragraph(T("inv.obs_caption"), s["caption"]))
    story.append(Spacer(1, 7))

    story += [section(T("pdf.notices_title")), Spacer(1, 3)]
    story.append(notices_block(r))
    return story


def profile_check_box(r: ReportInput):
    """Verifica di coerenza con il profilo dichiarato (solo volatilità), o None senza profilo."""
    if r.profile_band is None or not r.profile_label:
        return None
    s, T, m = styles(), r.T, r.metrics
    ok = finite(m.vol) and m.vol <= r.profile_band
    check = Paragraph(
        T(
            "inv.profile_check",
            status=T("rep.within") if ok else T("rep.outside"),
            vol=r.pct(m.vol),
            band=r.pct(r.profile_band, 0),
            profile=r.profile_label.lower(),
        )
        + f" <font size=7 color='#5b6472'>{T('pdf.check_caveat')}</font>",
        s["body"],
    )
    return callout([check], color=GREEN if ok else RED)


def historical_block(r: ReportInput) -> list:
    """Esiti storici a 12 mesi in percentuale: nessun importo futuro, nessuna previsione."""
    s, T, m = styles(), r.T, r.metrics
    sc = m.scenarios
    if sc is None:
        return [Paragraph(T("inv.sc_short"), s["small"])]
    rows = [
        [T("inv.h_scenario"), T("inv.h_12m_return")],
        [T("inv.sc_bear"), r.pct(sc.bear, signed=True)],
        [T("inv.sc_base"), r.pct(sc.base, signed=True)],
        [T("inv.sc_bull"), r.pct(sc.bull, signed=True)],
    ]
    caption = T(
        "inv.sc_method",
        windows=fmt_num(sc.windows, r.lang, 0),
        start=fmt_date(sc.start if sc.start is not None else m.start),
        end=fmt_date(sc.end if sc.end is not None else m.end),
        negative=r.pct(sc.share_negative, 0),
        worst=r.pct(sc.worst, signed=True),
        best=r.pct(sc.best, signed=True),
    )
    return [data_table(rows, [110 * mm, 64 * mm]), Paragraph(caption, s["caption"])]


def flagged_note(r: ReportInput):
    """Posizioni con contributo al rischio molto oltre il peso, anche se fuori tabella."""
    s, T, m = styles(), r.T, r.metrics
    text = (
        T("adr.flagged", tickers=", ".join(m.risk_over_weight))
        if m.risk_over_weight
        else T("adr.flagged_none")
    )
    return Paragraph(clean(text), s["small"])


def projection_table(r: ReportInput):
    """Scenari Monte Carlo: ribassista (p10), centrale (p50), rialzista (p90) per orizzonte."""
    T = r.T
    rows_in = (r.projection or {}).get("rows", [])
    header = [T("inv.h_scenario")] + [
        T("pdf.mc_year1") if row["years"] == 1 else T("pdf.mc_years", n=row["years"])
        for row in rows_in
    ]
    rows: list[list] = [header]
    for key in ("p10", "p50", "p90"):
        rows.append(
            [T(f"rep.mc_{key}")]
            + [
                f"{r.eur(row[key])} ({r.pct(row[key] / row['initial'] - 1, 0, signed=True)})"
                for row in rows_in
            ]
        )
    first = CONTENT_W * 0.3
    rest = (CONTENT_W - first) / max(1, len(rows_in))
    return data_table(rows, [first] + [rest] * len(rows_in))


def projection_method(r: ReportInput) -> str:
    """Metodologia della proiezione, con il periodo storico effettivamente ricampionato."""
    p = r.projection or {}
    m = r.metrics
    return r.T(
        "rep.mc_method",
        method=r.T(f"rep.mc_method_{p.get('method', 'bootstrap')}"),
        n=fmt_num(p.get("n", 0), r.lang, 0),
        start=fmt_date(p.get("hist_start", m.start)),
        end=fmt_date(p.get("hist_end", m.end)),
        loss=r.pct(p.get("prob_loss"), 0),
        horizon=p.get("horizon", 5),
    )


def notices_block(r: ReportInput):
    """Metodologia e avvertenze in due colonne di testo piccolo."""
    from reportlab.platypus import Table, TableStyle

    s, T = styles(), r.T
    rf = T("pdf.notice_rf2", rate=r.pct(r.risk_free, 2)) if r.risk_free is not None else ""
    bits = [
        T("rep.n_data", period=r.period_label, source=r.price_source or T("rep.source_unknown")),
        T("rep.n_fundamentals"),
        *([T("pdf.notice_pnl")] if r.pnl is not None and finite(r.pnl) else []),
        T("pdf.notice_costs"),
        T("rep.n_returns", rf=rf),
        T("rep.n_risk", benchmark=r.benchmark),
        *([T("bench.price_index_note", benchmark=r.benchmark)] if r.benchmark_price_index else []),
        T("rep.n_weights"),
        T("rep.n_scenarios"),
        T("rep.n_score"),
        T("pdf.notice_no_advice"),
        T("pdf.notice_profile"),
        T("pdf.notice_confidential") if r.advisor_issued else T("rep.n_personal_use"),
    ]
    if r.metrics.observations < SHORT_WINDOW_DAYS:
        bits.insert(0, T("pdf.notice_caution"))
    half = (len(bits) + 1) // 2
    table = Table(
        [
            [
                [Paragraph(clean(bit), s["fine"]) for bit in bits[:half]],
                [Paragraph(clean(bit), s["fine"]) for bit in bits[half:]],
            ]
        ],
        colWidths=[CONTENT_W / 2] * 2,
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("LEFTPADDING", (1, 0), (1, 0), 4),
                ("RIGHTPADDING", (0, 0), (0, 0), 4),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ]
        )
    )
    return table


def build_investor_report(r: ReportInput) -> bytes:
    """Il report Investor di quattro pagine come bytes PDF."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    rid = report_reference(r, now, "investor")
    pages = [_page1(r, now, rid), _page2(r, now), _page3(r, now), _page4(r, now)]
    story: list = []
    for i, page in enumerate(pages):
        if i:
            story.append(PageBreak())
        story.append(KeepInFrame(CONTENT_W, FRAME_H, page, mode="shrink"))
    return render_pdf(
        story,
        r,
        r.T("inv.doc_title"),
        rid,
        header_right=f"{r.T('inv.title')} · {r.portfolio_name}",
    )
