"""Onboarding gate: landing → composizione del portafoglio → loading, poi la piattaforma.

Finché lo stage non è "app", la piattaforma è bloccata (sidebar nascosta).
"""

from collections.abc import Callable
from contextlib import suppress

import streamlit as st

from portfolio_intelligence.config import INVESTOR_HISTORY_PERIOD
from portfolio_intelligence.i18n import t
from portfolio_intelligence.ui.area_switch import area_switch
from portfolio_intelligence.ui.components import render_landing
from portfolio_intelligence.ui.legal import legal_footer
from portfolio_intelligence.views import portfolio_editor as pe
from portfolio_intelligence.views.common import (
    BENCHMARK,
    SAMPLE_PORTFOLIO,
    analysis_fundamentals,
    cached_eurusd,
    cached_prices,
    cached_risk_free,
    language_selector,
)

# orizzonte di default della sidebar (pf_period): il caricamento scalda le
# stesse chiavi di cache che la piattaforma userà alla prima apertura
_DEFAULT_PERIOD = INVESTOR_HISTORY_PERIOD

GATE_CSS = """
<style>
/* while gated, nothing but the screen itself is reachable */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] { display: none !important; }

/* ---- header: brand + stepper ---- */
.gate-bar {
    display: flex; flex-wrap: wrap; align-items: center; gap: var(--s-2) var(--s-6);
    min-height: 40px;
}
.gate-bar .brand { white-space: nowrap; }
.stepper { display: flex; align-items: center; gap: var(--s-3); }
.step {
    display: flex; align-items: center; gap: var(--s-2);
    font-size: 0.85rem; font-weight: 600; color: var(--muted);
}
.step-num {
    width: 22px; height: 22px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 700;
    border: 1px solid var(--line-strong); background: var(--panel); color: var(--muted);
}
.step.active { color: var(--ink); }
.step.active .step-num { background: var(--ink); border-color: var(--ink); color: #fff; }
.step-sep { width: var(--s-6); height: 1px; background: var(--line-strong); }

.gate-head {
    margin: var(--s-4) 0 var(--s-5); padding-bottom: var(--s-5);
    border-bottom: 1px solid var(--line);
}
.gate-title {
    font-family: var(--font-display) !important; font-weight: 600;
    font-size: 1.75rem; letter-spacing: -0.01em; color: var(--ink); margin: 0; padding: 0;
}
.gate-sub {
    color: var(--muted); font-size: 0.95rem; margin-top: var(--s-2); max-width: 720px;
}

/* ---- riepilogo ---- */
.sum-h {
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--muted); margin-bottom: var(--s-1);
}
.sum-row {
    display: flex; justify-content: space-between; align-items: baseline; gap: var(--s-3);
    padding: var(--s-2) 0; border-bottom: 1px solid var(--line); font-size: 0.9rem;
}
.sum-row .k { color: var(--muted); }
.sum-row .v { color: var(--ink); font-weight: 600; font-variant-numeric: tabular-nums; }
.sum-note { font-size: 0.8rem; color: var(--muted); line-height: 1.5; }

/* ---- caricamento: overlay a schermo intero, nessun widget vecchio sotto ---- */
.loading-wrap {
    position: fixed; inset: 0; z-index: 99999; background: var(--bg);
    display: flex; align-items: center; justify-content: center; padding: var(--s-5);
}
.loading-card {
    width: 100%; max-width: 440px; background: var(--panel);
    border: 1px solid var(--line); border-radius: var(--r-lg);
    padding: var(--s-6) var(--s-6) var(--s-5);
}
.loading-card .brand { font-size: 0.85rem; margin-bottom: var(--s-5); }
.loading-title {
    font-family: var(--font-display) !important; font-weight: 600; font-size: 1.3rem;
    color: var(--ink);
}
.loading-sub { font-size: 0.88rem; color: var(--muted); margin-top: 2px; }
.loading-bar {
    height: 4px; background: var(--subtle); border-radius: 2px; margin: var(--s-4) 0 var(--s-2);
}
.loading-bar div { height: 100%; background: var(--accent); border-radius: 2px; }
/* l'indicatore "Running/Stop" di Streamlit non deve affiorare sopra la scheda */
body:has(.loading-wrap) [data-testid="stStatusWidget"] { visibility: hidden; }
.lstep {
    display: flex; align-items: center; gap: var(--s-3); padding: var(--s-2) 0;
    font-size: 0.9rem; color: var(--muted); border-top: 1px solid var(--line);
}
.loading-bar + .lstep { border-top: none; }
.lstep.done, .lstep.active { color: var(--ink); }
.lstep-ic {
    flex: none; width: 18px; height: 18px; border-radius: 50%;
    border: 1.5px solid var(--line-strong); display: inline-flex;
    align-items: center; justify-content: center;
}
.lstep.done .lstep-ic {
    background: var(--gain); border-color: var(--gain); color: #fff; font-size: 0.66rem;
}
/* unica animazione: indica il passo in corso, non decora */
.lstep.active .lstep-ic {
    border-color: var(--accent-border); border-top-color: var(--accent);
    animation: lspin .8s linear infinite;
}
@keyframes lspin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .lstep.active .lstep-ic { animation: none; } }
</style>
"""


def _go_input() -> None:
    st.session_state.stage = "input"


def _go_loading() -> None:
    st.session_state.stage = "loading"


def _load_sample() -> None:
    st.session_state.positions = {t_: dict(p) for t_, p in SAMPLE_PORTFOLIO.items()}


def render_gate() -> None:
    """Il flusso a tre stadi prima della piattaforma. Chiama st.stop() se attivo."""
    if "stage" not in st.session_state:
        st.session_state.stage = "landing"
    if st.session_state.stage == "app":
        return

    st.markdown(GATE_CSS, unsafe_allow_html=True)

    # ---- stage 1: landing ------------------------------------------------
    if st.session_state.stage == "landing":
        _topbar(step=None)
        render_landing(on_start=_go_input)
        legal_footer()

    # ---- stage 2: portfolio composition ----------------------------------
    elif st.session_state.stage == "input":
        _topbar(step=1)
        _render_input()
        legal_footer()

    # ---- stage 3: real data fetch with progress, then the platform -------
    elif st.session_state.stage == "loading":
        _render_loading()

    st.stop()


def _topbar(step: int | None) -> None:
    """Marchio, avanzamento (solo nei passi del flusso) e lingua."""
    stepper = ""
    if step is not None:
        steps = [
            f'<div class="step{" active" if n == step else ""}">'
            f'<span class="step-num">{n}</span>{t(f"gate.step{n}")}</div>'
            for n in (1, 2)
        ]
        stepper = f'<div class="stepper">{steps[0]}<div class="step-sep"></div>{steps[1]}</div>'
    bar, area_col, lang_col = st.columns([4.6, 1.4, 1], vertical_alignment="center")
    with area_col:
        area_switch("investor", "area_sw_gate")
    with bar:
        st.markdown(
            f'<div class="gate-bar"><div class="brand">◆ SMARTEE<b>FINANCE</b></div>{stepper}</div>',
            unsafe_allow_html=True,
        )
    with lang_col:
        language_selector("lang_gate")


# ----------------------------------------------------------------- stage 2


def _render_input() -> None:
    pe.inject_css()
    st.markdown(
        '<div class="gate-head">'
        f'<h1 class="page-title gate-title">{t("gate.title")}</h1>'
        f'<div class="gate-sub">{t("gate.sub")}</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    main, side = st.columns([2.4, 1], gap="large")
    with main:
        with st.container(border=True):
            tab_manual, tab_import, tab_sample = st.tabs(
                [t("gate.tab_manual"), t("gate.tab_import"), t("gate.tab_sample")]
            )
            with tab_manual:
                pe.manual_entry("gate")
            with tab_import:
                pe.file_import("gate")
            with tab_sample:
                st.markdown(
                    f'<div class="tab-desc">{t("gate.sample_desc")}</div>',
                    unsafe_allow_html=True,
                )
                st.button(t("gate.sample"), on_click=_load_sample)
        pe.positions_table("gate")
    with side:
        _summary_panel()


def _summary_panel() -> None:
    positions = st.session_state.positions
    rows = pe.cost_basis(positions)
    costs = sorted((cost for _, _, cost in rows.values()), reverse=True)
    total = sum(costs)
    if total:
        largest = max(rows, key=lambda k: rows[k][2])
        largest_txt = f"{largest} · {rows[largest][2] / total:.1%}"
        top3_txt = f"{sum(costs[:3]) / total:.1%}"
        total_txt = f"{total:,.2f}"
    else:
        largest_txt = top3_txt = total_txt = "—"

    summary = [
        (t("gate.sum_positions"), str(len(positions))),
        (t("gate.sum_invested"), total_txt),
        (t("gate.sum_largest"), largest_txt),
        (t("gate.sum_top3"), top3_txt),
    ]
    with st.container(border=True):
        st.markdown(
            f'<div class="sum-h">{t("gate.summary")}</div>'
            + "".join(
                f'<div class="sum-row"><span class="k">{k}</span><span class="v">{v}</span></div>'
                for k, v in summary
            ),
            unsafe_allow_html=True,
        )
        st.button(
            t("gate.analyze"),
            type="primary",
            width="stretch",
            on_click=_go_loading,
            disabled=not positions,
            help=None if positions else t("gate.analyze_disabled"),
        )
        st.markdown(
            f'<div class="sum-note">{t("gate.analyze_note")}</div>',
            unsafe_allow_html=True,
        )


# ----------------------------------------------------------------- stage 3


def _loading_html(labels: list[str], done: int, n_positions: int) -> str:
    rows = ""
    for i, label in enumerate(labels):
        state = "done" if i < done else "active" if i == done else ""
        icon = "✓" if i < done else ""
        rows += f'<div class="lstep {state}"><span class="lstep-ic">{icon}</span>{label}</div>'
    pct = done / len(labels) * 100
    return (
        '<div class="loading-wrap"><div class="loading-card">'
        '<div class="brand">◆ SMARTEE<b>FINANCE</b></div>'
        f'<div class="loading-title">{t("gate.loading_title")}</div>'
        f'<div class="loading-sub">{t("gate.loading_sub", n=n_positions)}</div>'
        f'<div class="loading-bar"><div style="width:{pct:.0f}%"></div></div>'
        f"{rows}</div></div>"
    )


def _render_loading() -> None:
    """Scarica davvero i dati dell'analisi, mostrando l'avanzamento passo per passo.

    Scalda le cache che la piattaforma interroga alla prima apertura, così la
    vista si apre già pronta invece di mostrare spinner in sequenza.
    """
    tickers = tuple(sorted(st.session_state.positions))
    tasks: list[tuple[str, Callable[[], object]]] = [
        (
            t("gate.load_prices"),
            lambda: (
                cached_prices(tickers, _DEFAULT_PERIOD),
                cached_prices((BENCHMARK,), _DEFAULT_PERIOD),
            ),
        ),
        (t("gate.load_fx"), lambda: cached_eurusd(_DEFAULT_PERIOD)),
        (t("gate.load_fundamentals"), lambda: analysis_fundamentals(tickers)),
        (t("gate.load_rates"), cached_risk_free),
    ]
    labels = [label for label, _ in tasks]
    placeholder = st.empty()
    for i, (_label, task) in enumerate(tasks):
        placeholder.markdown(_loading_html(labels, i, len(tickers)), unsafe_allow_html=True)
        # nessun blocco qui: la piattaforma rifà la chiamata e mostra
        # l'errore nel suo contesto, con il messaggio giusto
        with suppress(Exception):
            task()
    placeholder.markdown(_loading_html(labels, len(tasks), len(tickers)), unsafe_allow_html=True)
    st.session_state.stage = "app"
    st.rerun()
