"""Design system dell'app: CSS iniettato una volta per run.

Estratto da app.py per tenere il router sottile; nessuna logica, solo stile.

Principi: superfici piatte con bordi sottili, nessun effetto decorativo
(gradienti, vetro, animazioni d'ingresso, card che si sollevano), una sola
scala di spaziature (--s-*) e di raggi (--r-*). Tipografia: Source Serif per
i titoli, Source Sans per interfaccia e numeri; entrambi serviti da Streamlit
(stessa origine, licenza OFL), nessuna richiesta a font di terze parti.
"""

import streamlit as st

from portfolio_intelligence.visualization.charts import GAIN_TEXT, LOSS

AMBER = "#d97706"  # status mid-band only (gauge/health)
ACCENT = "#1E40AF"  # brand primary
ACCENT_HOVER = "#1E3A8A"


def inject_theme() -> None:
    """Applica il design system (font, nav, card, widget, sidebar, responsive)."""
    st.markdown(
        f"""
        <style>

        :root {{
            --bg: #F8FAFC;
            --panel: #ffffff;
            --subtle: #F1F5F9;
            --line: #E2E8F0;
            --line-strong: #CBD5E1;
            --muted: #64748b;
            --ink-2: #334155;
            --ink: #0F172A;
            --accent: {ACCENT};
            --accent-hover: {ACCENT_HOVER};
            --accent-soft: rgba(30, 64, 175, 0.08);
            --accent-border: rgba(30, 64, 175, 0.28);
            --gain: {GAIN_TEXT};
            --loss: {LOSS};
            --font-ui: 'Source Sans', -apple-system, 'Segoe UI', sans-serif;
            --font-display: 'Source Serif', Georgia, 'Times New Roman', serif;
            /* scala unica: ogni margine/padding del CSS custom usa questi passi */
            --s-1: 4px; --s-2: 8px; --s-3: 12px; --s-4: 16px;
            --s-5: 24px; --s-6: 32px; --s-7: 48px;
            --r-sm: 6px; --r-md: 8px; --r-lg: 12px;
        }}
        html, body, p, div, span, label, input, button, textarea, select, li {{
            font-family: var(--font-ui) !important;
        }}
        code, pre {{ font-family: ui-monospace, 'SF Mono', Menlo, monospace !important; }}
        [data-testid="stIconMaterial"], [class*="material-symbols"] {{
            font-family: 'Material Symbols Rounded' !important;
        }}
        .block-container {{ padding-top: var(--s-4); max-width: 1320px; }}
        h1, h2, h3 {{
            font-family: var(--font-display) !important; font-weight: 600 !important;
            letter-spacing: -0.005em; color: var(--ink);
        }}
        /* Streamlit avvolge il testo dei titoli in uno span: eredita il serif */
        h1 *, h2 *, h3 * {{ font-family: inherit !important; }}
        /* titoli di pagina custom: niente icona-ancora né padding di Streamlit */
        .page-title {{ padding: 0 !important; margin: 0 !important; }}
        .page-title [data-testid="stHeaderActionElements"] {{ display: none; }}

        /* ---- barra superiore ---- */
        .topbar {{
            display: flex; justify-content: space-between; align-items: baseline;
            padding: 0 0 var(--s-3);
        }}
        .brand {{
            font-size: 1rem; letter-spacing: 0.14em; color: var(--ink);
            text-transform: uppercase; font-weight: 500;
        }}
        .brand b {{ color: var(--accent); font-weight: 700; }}
        .brand-product {{
            text-transform: none; white-space: nowrap;
            font-size: 0.75rem; font-weight: 600; color: var(--muted);
            letter-spacing: 0.01em; margin-left: var(--s-3); padding-left: var(--s-3);
            border-left: 1px solid var(--line);
        }}
        .brand-tag {{ font-size: 0.75rem; color: var(--muted); }}

        /* ---- navigazione primaria (segmented control) ---- */
        .st-key-navbar {{
            border-bottom: 1px solid var(--line);
            position: sticky; top: 0; z-index: 99; background: var(--bg);
        }}
        .st-key-navbar [data-testid="stSegmentedControl"] button,
        .st-key-navbar [role="radiogroup"] button {{
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            border-bottom: 2px solid transparent !important;
            padding: var(--s-2) var(--s-4) var(--s-3) !important;
        }}
        .st-key-navbar button p {{
            font-size: 0.8rem !important; font-weight: 600;
            letter-spacing: 0.06em; text-transform: uppercase;
            color: var(--muted) !important;
        }}
        .st-key-navbar button:hover p {{ color: var(--ink) !important; }}
        .st-key-navbar button[aria-checked="true"],
        .st-key-navbar button[kind="segmented_controlActive"] {{
            border-bottom-color: var(--accent) !important;
        }}
        .st-key-navbar button[aria-checked="true"] p,
        .st-key-navbar button[kind="segmented_controlActive"] p {{
            color: var(--ink) !important;
        }}
        /* sub-nav contestuale */
        .st-key-subnav {{ margin: var(--s-1) 0 var(--s-1); }}
        .st-key-subnav [data-testid="stSegmentedControl"] button {{
            background: transparent !important; border: 1px solid var(--line) !important;
            border-radius: var(--r-md) !important; padding: var(--s-1) var(--s-4) !important;
            margin-right: var(--s-2);
        }}
        .st-key-subnav button p {{
            font-size: 0.8rem !important; font-weight: 600;
            color: var(--muted) !important;
        }}
        .st-key-subnav button[aria-checked="true"],
        .st-key-subnav button[kind="segmented_controlActive"] {{
            background: var(--accent-soft) !important;
            border-color: var(--accent-border) !important;
        }}
        .st-key-subnav button[aria-checked="true"] p,
        .st-key-subnav button[kind="segmented_controlActive"] p {{
            color: var(--accent) !important;
        }}

        /* ---- widget di Streamlit, adattati al marchio ---- */
        .stButton button, .stDownloadButton button, [data-testid="stPopover"] > button {{
            border-radius: var(--r-md); font-weight: 600; box-shadow: none;
        }}
        [data-testid="stBaseButton-primary"] {{
            background: var(--accent); border: 1px solid var(--accent); color: #fff;
        }}
        [data-testid="stBaseButton-primary"]:hover {{
            background: var(--accent-hover); border-color: var(--accent-hover); color: #fff;
        }}
        [data-testid="stBaseButton-secondary"] {{
            background: var(--panel); border: 1px solid var(--line-strong); color: var(--ink);
        }}
        [data-testid="stBaseButton-secondary"]:hover {{
            background: var(--subtle); border-color: var(--ink-2); color: var(--ink);
        }}
        [data-testid="stBaseButton-tertiary"]:hover {{ color: var(--accent); }}
        [data-testid^="stBaseButton"]:disabled {{
            background: var(--subtle); border-color: var(--line); color: var(--muted);
        }}
        [data-testid^="stBaseButton"]:focus-visible,
        [data-testid="stPopover"] > button:focus-visible {{
            outline: 2px solid var(--accent); outline-offset: 2px;
        }}
        div[data-baseweb="input"], div[data-baseweb="select"] > div,
        div[data-baseweb="textarea"] {{
            border-radius: var(--r-md) !important;
        }}
        [data-baseweb="tab-list"] {{ gap: var(--s-5); border-bottom: 1px solid var(--line); }}
        [data-baseweb="tab"] p {{ font-weight: 600; font-size: 0.9rem; }}
        [data-testid="stExpander"] {{
            border: 1px solid var(--line); border-radius: var(--r-md); background: transparent;
        }}
        [data-testid="stExpander"] summary p {{ font-weight: 600; }}
        [data-testid="stAlert"] > div {{ border-radius: var(--r-md); }}
        header[data-testid="stHeader"] {{ background: transparent; }}
        [data-testid="stMainMenu"] {{ display: none; }}
        [data-testid="stPopover"] > button {{
            border: none !important; background: transparent !important;
            color: var(--muted) !important;
        }}
        [data-testid="stPopover"] > button:hover {{ color: var(--ink) !important; }}
        [data-testid="stSpinner"] i {{
            border-top-color: var(--accent) !important;
            border-right-color: var(--accent-border) !important;
        }}

        /* ---- avviso informativo neutro (al posto di st.info con icona) ---- */
        .notice {{
            background: var(--subtle); border: 1px solid var(--line);
            border-radius: var(--r-md); padding: var(--s-3) var(--s-4);
            font-size: 0.85rem; color: var(--ink-2); margin: var(--s-2) 0 var(--s-3);
        }}

        /* ---- pannelli ---- */
        .panel {{
            background: var(--panel); border: 1px solid var(--line);
            border-radius: var(--r-lg); padding: var(--s-5); height: 100%;
        }}

        /* ---- striscia KPI: un solo pannello, celle separate da filetti ---- */
        .kpi-row {{
            display: flex; flex-wrap: wrap; margin: var(--s-1) 0 var(--s-2);
            background: var(--panel); border: 1px solid var(--line);
            border-radius: var(--r-lg);
        }}
        .kpi {{
            flex: 1; min-width: 210px; padding: var(--s-4) var(--s-5);
            border-left: 1px solid var(--line);
        }}
        .kpi:first-child {{ border-left: none; }}
        .kpi-label {{
            font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em;
            color: var(--muted); font-weight: 600;
        }}
        .kpi-value {{
            font-size: 1.7rem; font-weight: 700; margin-top: var(--s-2); color: var(--ink);
            font-variant-numeric: tabular-nums; letter-spacing: -0.01em;
        }}
        .kpi-sub {{
            font-size: 0.8rem; color: var(--muted); margin-top: var(--s-1); line-height: 1.45;
        }}

        /* ---- libro clienti (Advisor) ---- */
        .client-list {{
            background: var(--panel); border: 1px solid var(--line); border-radius: var(--r-lg);
        }}
        .client-row {{
            display: flex; align-items: center; gap: var(--s-4); flex-wrap: wrap;
            padding: var(--s-3) var(--s-5); border-top: 1px solid var(--line);
        }}
        .client-row:first-child {{ border-top: none; }}
        .client-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
        .client-name {{ min-width: 150px; }}
        .client-value {{ min-width: 120px; }}
        .client-strong {{ font-weight: 700; font-variant-numeric: tabular-nums; }}
        .client-value .chg {{ font-size: 0.8rem; margin-left: var(--s-1); }}
        .client-problem {{ flex: 1; margin-top: 0; }}
        .client-health {{
            font-size: 1.5rem; font-weight: 700; font-variant-numeric: tabular-nums;
        }}
        .client-health span {{ font-size: 0.75rem; color: var(--muted); font-weight: 600; }}

        /* ---- stato vuoto ---- */
        .empty {{
            text-align: center; padding: var(--s-7) var(--s-6);
            border: 1px dashed var(--line-strong);
            border-radius: var(--r-lg); margin: var(--s-4) 0;
        }}
        .empty-title {{ font-weight: 700; font-size: 1.05rem; color: var(--ink); }}
        .empty-hint {{
            color: var(--muted); font-size: 0.9rem; margin: var(--s-2) auto 0;
            max-width: 430px; line-height: 1.5;
        }}
        .compliance {{
            margin: var(--s-7) auto var(--s-2); max-width: 900px; text-align: center;
            font-size: 0.75rem; line-height: 1.5; color: var(--muted);
            border-top: 1px solid var(--line); padding-top: var(--s-4);
        }}

        /* ---- footer legale ---- */
        .legal-footer {{
            margin: var(--s-6) 0 var(--s-2); padding-top: var(--s-4);
            border-top: 1px solid var(--line);
            font-size: 0.8rem; color: var(--muted); line-height: 1.7;
        }}
        .legal-footer a {{ color: var(--muted); text-decoration: underline; }}
        .legal-footer a:hover, .legal-footer a:focus-visible {{ color: var(--accent); }}

        /* ---- metriche native: niente scatole, solo numeri e filetti ---- */
        [data-testid="stMetric"] {{
            background: transparent; border: none;
            border-left: 1px solid var(--line);
            border-radius: 0; padding: var(--s-1) 0 var(--s-1) var(--s-4);
        }}
        [data-testid="stMetricLabel"] p {{
            font-size: 0.72rem !important; text-transform: uppercase;
            letter-spacing: 0.08em; color: var(--muted) !important; font-weight: 600;
        }}
        [data-testid="stMetricValue"] {{
            font-weight: 700; font-variant-numeric: tabular-nums; font-size: 1.65rem;
            letter-spacing: -0.01em;
        }}
        [data-testid="stMetricDelta"] {{
            font-variant-numeric: tabular-nums; font-size: 0.85rem; font-weight: 600;
        }}

        /* ---- etichette di sezione ---- */
        .sec {{
            font-size: 0.75rem; font-weight: 700; letter-spacing: 0.08em;
            text-transform: uppercase; color: var(--muted);
            margin: var(--s-5) 0 var(--s-3);
        }}

        /* ---- hero con indicatore circolare ---- */
        .hero-panel {{
            display: flex; align-items: center; gap: var(--s-6);
            background: var(--panel); border: 1px solid var(--line);
            border-radius: var(--r-lg); padding: var(--s-5) var(--s-6);
        }}
        .gauge {{
            width: 128px; height: 128px; border-radius: 50%; flex-shrink: 0;
            background: conic-gradient(var(--gcol) calc(var(--val) * 3.6deg), var(--line) 0);
            display: flex; align-items: center; justify-content: center;
        }}
        .gauge-inner {{
            width: 104px; height: 104px; border-radius: 50%; background: var(--panel);
            display: flex; flex-direction: column; align-items: center;
            justify-content: center;
        }}
        .gauge-num {{
            font-size: 2.2rem; font-weight: 700; font-variant-numeric: tabular-nums;
            line-height: 1; color: var(--ink);
        }}
        .gauge-sub {{
            font-size: 0.68rem; color: var(--muted); letter-spacing: 0.1em;
            margin-top: var(--s-1);
        }}
        .hero-meta .label {{
            font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em;
            color: var(--muted); font-weight: 600;
        }}
        .hero-meta .big {{
            font-size: 2.5rem; font-weight: 700; letter-spacing: -0.01em; color: var(--ink);
            font-variant-numeric: tabular-nums; margin: var(--s-1) 0;
        }}
        .chg {{ font-size: 1rem; font-weight: 700; font-variant-numeric: tabular-nums; }}
        .chg-line {{ font-size: 0.95rem; margin-top: 2px; }}
        .chg-line.small {{ font-size: 0.85rem; }}
        .up {{ color: var(--gain); }}
        .down {{ color: var(--loss); }}

        /* ---- profilo e scomposizione dello score ---- */
        .dna-title {{
            font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase;
            color: var(--muted); font-weight: 700; margin-bottom: var(--s-3);
        }}
        .dna-row {{ display: flex; align-items: center; margin: var(--s-2) 0; gap: var(--s-3); }}
        .dna-name {{ width: 76px; font-size: 0.88rem; color: var(--ink-2); }}
        .dna-track {{ flex: 1; background: var(--subtle); border-radius: 3px; height: 6px; }}
        .dna-fill {{ height: 100%; border-radius: 3px; background: var(--ink-2); }}
        .dna-fill.risk {{ background: var(--accent); }}
        .dna-value {{
            width: 36px; text-align: right; font-size: 0.88rem; font-weight: 700;
            font-variant-numeric: tabular-nums;
        }}
        .dna-status {{ margin-top: var(--s-3); font-weight: 600; font-size: 0.95rem; }}

        .ai-card p {{ margin: 0 0 var(--s-3); line-height: 1.55; font-size: 0.95rem; }}

        /* ---- posizioni (sidebar) ---- */
        .pos-row {{
            display: flex; align-items: center; gap: var(--s-3);
            padding: var(--s-2) 0; border-bottom: 1px solid var(--line);
        }}
        .avatar {{
            width: 34px; height: 34px; border-radius: var(--r-md); flex-shrink: 0;
            display: flex; align-items: center; justify-content: center;
            font-size: 0.7rem; font-weight: 700; color: #ffffff; letter-spacing: 0.02em;
        }}
        .pos-main {{ flex: 1; min-width: 0; }}
        .pos-ticker {{ font-weight: 700; font-size: 0.9rem; line-height: 1.2; }}
        .pos-name {{
            font-size: 0.75rem; color: var(--muted); max-width: 160px;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .pos-amt {{
            font-size: 0.8rem; color: var(--muted); font-variant-numeric: tabular-nums;
        }}
        .pos-weight-track {{
            margin-top: var(--s-1); height: 3px; border-radius: 2px; background: var(--subtle);
        }}
        .pos-weight-fill {{ height: 100%; border-radius: 2px; }}
        .pos-pct {{
            font-size: 0.85rem; font-weight: 700; color: var(--ink-2);
            font-variant-numeric: tabular-nums;
        }}

        /* ---- anteprima titolo (aggiungi) ---- */
        .ticker-preview {{
            display: flex; align-items: center; gap: var(--s-3);
            background: var(--panel); border: 1px solid var(--line);
            border-radius: var(--r-md); padding: var(--s-3);
            margin: var(--s-1) 0 var(--s-3);
        }}
        .tp-main {{ flex: 1; min-width: 0; }}
        .tp-name {{
            font-weight: 700; font-size: 0.92rem; line-height: 1.2;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .tp-meta {{ font-size: 0.75rem; color: var(--muted); margin-top: 2px; }}
        .tp-price {{
            font-size: 0.9rem; font-weight: 700; margin-top: var(--s-1);
            font-variant-numeric: tabular-nums;
        }}
        .tp-chg {{ font-size: 0.8rem; font-weight: 600; margin-left: var(--s-2); }}
        .tp-chg.up {{ color: var(--gain); }}
        .tp-chg.down {{ color: var(--loss); }}

        /* ---- sidebar ---- */
        [data-testid="stSidebar"] {{
            background: var(--panel); border-right: 1px solid var(--line);
        }}
        [data-testid="stSidebar"] .sec {{ margin: var(--s-3) 0 var(--s-2); }}
        [data-testid="stSidebar"] hr {{ margin: var(--s-3) 0; }}

        /* ---- context switcher Advisor (sidebar) ---- */
        .side-context-switch {{
            font-size: 0.75rem; color: var(--muted); margin: 2px 0 var(--s-3);
            padding-bottom: var(--s-3); border-bottom: 1px solid var(--line);
        }}
        .side-context-switch span {{ font-weight: 700; color: var(--ink-2); }}
        .side-context-switch a {{ color: var(--muted); text-decoration: underline; }}
        .side-context-switch a:hover {{ color: var(--accent); }}

        /* ---- responsive ---- */
        @media (max-width: 920px) {{
            .hero-panel {{ flex-direction: column; text-align: center; gap: var(--s-4); }}
            .kpi {{ min-width: 100%; border-left: none; border-top: 1px solid var(--line); }}
            .kpi:first-child {{ border-top: none; }}
        }}
        @media (max-width: 640px) {{
            .block-container {{ padding-left: var(--s-3); padding-right: var(--s-3); }}
            .topbar {{ flex-direction: column; align-items: flex-start; gap: 2px; }}
            .brand {{ font-size: 0.92rem; letter-spacing: 0.08em; }}
            .brand-product {{
                display: block; margin: var(--s-1) 0 0; padding: 0; border-left: none;
            }}
            /* nav: scorrimento orizzontale invece di andare a capo */
            .st-key-navbar [role="radiogroup"] {{
                flex-wrap: nowrap !important; overflow-x: auto; width: 100%;
                -webkit-overflow-scrolling: touch; scrollbar-width: none;
            }}
            .st-key-navbar [role="radiogroup"]::-webkit-scrollbar {{ display: none; }}
            .st-key-navbar button {{
                flex: 0 0 auto !important; padding: var(--s-2) var(--s-3) var(--s-3) !important;
            }}
            .st-key-navbar button p {{
                font-size: 0.75rem !important; letter-spacing: 0.04em;
                white-space: nowrap !important; overflow: visible !important;
                text-overflow: clip !important;
            }}
            .hero-panel {{ padding: var(--s-5) var(--s-4); }}
            .hero-meta .big {{ font-size: 2.1rem; }}
            .gauge {{ width: 112px; height: 112px; }}
            .gauge-inner {{ width: 90px; height: 90px; }}
            .kpi-value {{ font-size: 1.5rem; }}
            [data-testid="stMetricValue"] {{ font-size: 1.4rem !important; }}
            .sec {{ margin: var(--s-5) 0 var(--s-2); }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
