"""Design system dell'app: CSS iniettato una volta per run.

Estratto da app.py per tenere il router sottile; nessuna logica, solo stile.
"""

import streamlit as st

from src.visualization.charts import GAIN, LOSS

AMBER = "#d97706"  # status mid-band only (gauge/health)
ACCENT = "#1E40AF"  # brand primary (Stripe/Mercury blue)


def inject_theme() -> None:
    """Applica il design system (font, nav, card, sidebar, responsive)."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

        :root {{
            --panel: #ffffff;
            --panel-2: #ffffff;
            --line: #E2E8F0;
            --muted: #64748b;
            --ink: #0F172A;
            --accent: {ACCENT};
            --accent-soft: rgba(30, 64, 175, 0.08);
            --accent-border: rgba(30, 64, 175, 0.28);
            --gain: {GAIN};
            --loss: {LOSS};
            --font-ui: 'Inter', -apple-system, 'Segoe UI', sans-serif;
            --font-display: 'Space Grotesk', 'Inter', sans-serif;
        }}
        html, body, p, div, span, label, input, button, textarea, select, li {{
            font-family: var(--font-ui) !important;
        }}
        code, pre {{ font-family: ui-monospace, 'SF Mono', Menlo, monospace !important; }}
        [data-testid="stIconMaterial"], [class*="material-symbols"] {{
            font-family: 'Material Symbols Rounded' !important;
        }}
        .block-container {{ padding-top: 1.1rem; max-width: 1320px; }}
        h1, h2, h3 {{
            font-family: var(--font-display) !important; letter-spacing: -0.01em;
        }}

        /* ---- barra superiore ---- */
        .topbar {{
            display: flex; justify-content: space-between; align-items: baseline;
            padding: 2px 2px 10px;
        }}
        .brand {{
            font-family: var(--font-display) !important;
            font-size: 1.02rem; letter-spacing: 0.14em; color: var(--ink);
            text-transform: uppercase; font-weight: 500;
        }}
        .brand b {{ color: var(--accent); font-weight: 700; }}
        .brand-product {{
            font-family: var(--font-ui) !important; text-transform: none;
            font-size: 0.7rem; font-weight: 600; color: var(--muted);
            letter-spacing: 0.01em; margin-left: 10px; padding-left: 10px;
            border-left: 1px solid var(--line);
        }}
        .brand-tag {{ font-size: 0.72rem; color: var(--muted); letter-spacing: 0.04em; }}

        /* ---- menu di navigazione (segmented control) ---- */
        .st-key-navbar [data-testid="stSegmentedControl"] button,
        .st-key-navbar [role="radiogroup"] button {{
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            border-bottom: 2px solid transparent !important;
            padding: 6px 14px 10px !important;
        }}
        .st-key-navbar button p {{
            font-size: 0.78rem !important; font-weight: 600;
            letter-spacing: 0.07em; text-transform: uppercase;
            color: var(--muted) !important;
        }}
        .st-key-navbar button[aria-checked="true"],
        .st-key-navbar button[kind="segmented_controlActive"] {{
            border-bottom-color: var(--accent) !important;
        }}
        .st-key-navbar button[aria-checked="true"] p,
        .st-key-navbar button[kind="segmented_controlActive"] p {{
            color: var(--ink) !important;
        }}
        .st-key-navbar {{
            border-bottom: 1px solid var(--line);
            position: sticky; top: 0; z-index: 99;
            background: rgba(247, 248, 250, 0.85);
            backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
        }}
        /* sub-nav contestuale: chip discrete sotto la nav primaria */
        .st-key-subnav {{ margin: 4px 0 2px; }}
        .st-key-subnav [data-testid="stSegmentedControl"] button {{
            background: transparent !important; border: 1px solid var(--line) !important;
            border-radius: 8px !important; padding: 3px 14px !important;
            margin-right: 6px;
        }}
        .st-key-subnav button p {{
            font-size: 0.72rem !important; font-weight: 600; letter-spacing: 0.04em;
            text-transform: none; color: var(--muted) !important;
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

        /* ---- profondità e hover ---- */
        .panel, .hero-panel {{
            box-shadow: 0 1px 2px rgba(15,23,42,0.04), 0 4px 12px rgba(15,23,42,0.04);
            transition: transform 0.18s ease, border-color 0.18s ease;
        }}
        .panel:hover, .hero-panel:hover {{
            transform: translateY(-2px);
            border-color: rgba(30,64,175,0.28);
        }}
        .pos-row {{ transition: background 0.15s ease; border-radius: 8px; }}
        .pos-row:hover {{ background: rgba(20, 25, 35, 0.03); }}
        .stButton button, .stDownloadButton button {{
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }}
        .stButton button:hover, .stDownloadButton button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 14px rgba(30,64,175,0.14);
        }}

        /* ---- KPI card con icona ---- */
        .kpi-row {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 4px 0 6px; }}
        .kpi {{
            flex: 1; min-width: 210px;
            background: var(--panel); border: 1px solid var(--line);
            border-radius: 18px; padding: 20px 22px;
            box-shadow: 0 1px 2px rgba(15,23,42,0.04), 0 4px 12px rgba(15,23,42,0.04);
            transition: transform 0.18s ease, border-color 0.18s ease;
            animation: fadeUpSubtle 0.3s ease-out both;
        }}
        .kpi:hover {{ transform: translateY(-2px); border-color: rgba(30,64,175,0.3); }}
        .kpi-top {{ display: flex; justify-content: space-between; align-items: center; }}
        .kpi-icon {{
            width: 34px; height: 34px; border-radius: 9px; flex-shrink: 0;
            display: flex; align-items: center; justify-content: center;
        }}
        .kpi-label {{
            font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.1em;
            color: var(--muted); font-weight: 600; padding-right: 8px;
        }}
        .kpi-value {{
            font-size: 1.7rem; font-weight: 700; margin-top: 8px;
            font-variant-numeric: tabular-nums; letter-spacing: -0.02em;
        }}
        .kpi-sub {{ font-size: 0.75rem; color: var(--muted); margin-top: 4px;
                    line-height: 1.45; }}
        @keyframes fadeUpSubtle {{
            from {{ opacity: 0; transform: translateY(6px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* ---- empty state ---- */
        .empty {{
            text-align: center; padding: 54px 30px;
            border: 1.5px dashed rgba(20, 25, 35, 0.14);
            border-radius: 18px; margin: 20px 0;
        }}
        .empty-icon {{
            width: 46px; height: 46px; margin: 0 auto 14px; border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            background: rgba(30,64,175,0.1); color: var(--accent);
        }}
        .compliance {{
            margin: 42px auto 8px; max-width: 900px; text-align: center;
            font-size: 0.72rem; line-height: 1.5; color: #6b7280;
            border-top: 1px solid var(--line); padding-top: 16px;
        }}
        .empty-title {{ font-weight: 700; font-size: 1.05rem; }}
        .empty-hint {{
            color: var(--muted); font-size: 0.9rem; margin-top: 6px;
            max-width: 430px; margin-left: auto; margin-right: auto; line-height: 1.5;
        }}

        /* ---- spinner brandizzato ---- */
        [data-testid="stSpinner"] i {{
            border-top-color: var(--accent) !important;
            border-right-color: rgba(30,64,175,0.25) !important;
        }}

        .brand-product {{ white-space: nowrap; }}

        /* ---- responsive ---- */
        @media (max-width: 920px) {{
            .hero-panel {{ flex-direction: column; text-align: center; gap: 16px; }}
            .kpi {{ min-width: 100%; }}
            .landing-hero {{ padding: 44px 26px 40px !important; }}
            .landing-title {{ font-size: 2.1rem !important; }}
            .glass-row {{ flex-direction: column; }}
        }}
        @media (max-width: 640px) {{
            .block-container {{ padding-left: 0.6rem; padding-right: 0.6rem; }}
            .topbar {{ flex-direction: column; align-items: flex-start; gap: 2px; }}
            .brand {{ font-size: 0.92rem; letter-spacing: 0.08em; }}
            .brand-product {{
                display: block; margin: 3px 0 0; padding: 0; border-left: none;
            }}
            .brand-tag {{ font-size: 0.66rem; }}
            /* nav: horizontal scroll instead of wrapping onto 2 rows */
            .st-key-navbar [role="radiogroup"] {{
                flex-wrap: nowrap !important; overflow-x: auto; width: 100%;
                -webkit-overflow-scrolling: touch; scrollbar-width: none;
            }}
            .st-key-navbar [role="radiogroup"]::-webkit-scrollbar {{ display: none; }}
            .st-key-navbar button {{
                flex: 0 0 auto !important; padding: 6px 12px 10px !important;
            }}
            .st-key-navbar button p {{
                font-size: 0.72rem !important; letter-spacing: 0.04em;
                white-space: nowrap !important; overflow: visible !important;
                text-overflow: clip !important;
            }}
            .hero-panel {{ padding: 20px 18px; }}
            .hero-meta .big {{ font-size: 2.1rem; }}
            .gauge {{ width: 112px; height: 112px; }}
            .gauge-inner {{ width: 90px; height: 90px; }}
            .kpi-value {{ font-size: 1.5rem; }}
            [data-testid="stMetricValue"] {{ font-size: 1.4rem !important; }}
            .sec {{ margin: 20px 0 8px; }}
        }}

        /* ---- metriche flat: niente scatole, solo numeri e separatori ---- */
        .panel {{
            background: var(--panel); border: 1px solid var(--line);
            border-radius: 18px; padding: 22px 26px; height: 100%;
        }}
        [data-testid="stMetric"] {{
            background: transparent; border: none;
            border-left: 2px solid var(--line);
            border-radius: 0; padding: 2px 0 2px 14px;
        }}
        [data-testid="stMetricLabel"] p {{
            font-size: 0.68rem !important; text-transform: uppercase;
            letter-spacing: 0.1em; color: var(--muted) !important; font-weight: 600;
        }}
        [data-testid="stMetricValue"] {{
            font-family: var(--font-ui) !important; font-weight: 700;
            font-variant-numeric: tabular-nums; font-size: 1.65rem;
            letter-spacing: -0.02em;
        }}
        [data-testid="stMetricDelta"] {{
            font-variant-numeric: tabular-nums; font-size: 0.85rem; font-weight: 600;
        }}

        /* ---- etichette di sezione ---- */
        .sec {{
            display: flex; align-items: center; gap: 10px;
            font-size: 0.72rem; font-weight: 700; letter-spacing: 0.09em;
            text-transform: uppercase; color: var(--muted);
            margin: 26px 0 10px;
        }}
        .sec::before {{
            content: ""; display: block; width: 3px; height: 14px;
            background: var(--accent); border-radius: 2px;
        }}

        /* ---- hero con gauge ---- */
        .hero-panel {{
            display: flex; align-items: center; gap: 28px;
            background: var(--panel); border: 1px solid var(--line);
            border-radius: 12px; padding: 22px 28px;
        }}
        .gauge {{
            width: 128px; height: 128px; border-radius: 50%; flex-shrink: 0;
            background: conic-gradient(var(--gcol) calc(var(--val) * 3.6deg),
                                       rgba(20,25,35,0.08) 0);
            display: flex; align-items: center; justify-content: center;
        }}
        .gauge-inner {{
            width: 102px; height: 102px; border-radius: 50%; background: var(--panel);
            display: flex; flex-direction: column; align-items: center;
            justify-content: center;
        }}
        .gauge-num {{
            font-family: var(--font-display) !important;
            font-size: 2.2rem; font-weight: 700;
            line-height: 1; color: var(--gcol);
        }}
        .gauge-sub {{ font-size: 0.64rem; color: var(--muted); letter-spacing: 0.12em; }}
        .hero-meta .label {{
            font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.1em;
            color: var(--muted); font-weight: 600;
        }}
        .hero-meta .big {{
            font-family: var(--font-display) !important;
            font-size: 2.5rem; font-weight: 700; letter-spacing: -0.02em;
            font-variant-numeric: tabular-nums; margin: 2px 0;
        }}
        .chg {{
            font-size: 1rem; font-weight: 700; font-variant-numeric: tabular-nums;
        }}
        .up {{ color: var(--gain); }}
        .down {{ color: var(--loss); }}

        /* ---- DNA card ---- */
        .dna-title {{
            font-size: 0.72rem; letter-spacing: 0.16em; color: var(--muted);
            font-weight: 700; margin-bottom: 14px;
        }}
        .dna-row {{ display: flex; align-items: center; margin: 9px 0; gap: 10px; }}
        .dna-name {{ width: 72px; font-size: 0.86rem; color: #3a4150; }}
        .dna-track {{
            flex: 1; background: rgba(20,25,35,0.08); border-radius: 4px; height: 6px;
        }}
        .dna-fill {{ height: 100%; border-radius: 4px; background: #3987e5; }}
        .dna-fill.risk {{ background: var(--accent); }}
        .dna-value {{
            width: 36px; text-align: right; font-size: 0.88rem; font-weight: 700;
            font-variant-numeric: tabular-nums;
        }}
        .dna-status {{ margin-top: 14px; font-weight: 600; font-size: 0.98rem; }}

        .ai-card p {{ margin: 0 0 10px; line-height: 1.55; font-size: 0.95rem; }}

        /* ---- card posizioni (sidebar) ---- */
        .pos-row {{
            display: flex; align-items: center; gap: 11px;
            padding: 9px 2px;
            border-bottom: 1px solid rgba(20,25,35,0.06);
        }}
        .avatar {{
            width: 34px; height: 34px; border-radius: 10px; flex-shrink: 0;
            display: flex; align-items: center; justify-content: center;
            font-size: 0.7rem; font-weight: 800; color: #ffffff;
            letter-spacing: 0.02em;
        }}
        .pos-main {{ flex: 1; min-width: 0; }}
        .pos-ticker {{ font-weight: 700; font-size: 0.9rem; line-height: 1.2; }}
        .pos-name {{
            font-size: 0.7rem; color: var(--muted); max-width: 160px;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .pos-amt {{
            font-size: 0.78rem; color: var(--muted);
            font-variant-numeric: tabular-nums;
        }}
        .pos-weight-track {{
            margin-top: 4px; height: 3px; border-radius: 2px;
            background: rgba(20,25,35,0.08);
        }}
        .pos-weight-fill {{ height: 100%; border-radius: 2px; }}
        .pos-pct {{
            font-size: 0.82rem; font-weight: 700; color: #3a4150;
            font-variant-numeric: tabular-nums;
        }}

        /* ---- anteprima titolo (aggiungi) ---- */
        .ticker-preview {{
            display: flex; align-items: center; gap: 12px;
            background: var(--accent-soft);
            border: 1px solid var(--accent-border);
            border-radius: 14px; padding: 12px 14px; margin: 4px 0 10px;
            animation: fadeUpSubtle 0.25s ease-out both;
        }}
        .tp-main {{ flex: 1; min-width: 0; }}
        .tp-name {{
            font-weight: 700; font-size: 0.92rem; line-height: 1.2;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .tp-meta {{
            font-size: 0.7rem; color: var(--muted); text-transform: uppercase;
            letter-spacing: 0.04em; margin-top: 1px;
        }}
        .tp-price {{
            font-size: 0.9rem; font-weight: 700; margin-top: 4px;
            font-variant-numeric: tabular-nums;
        }}
        .tp-chg {{ font-size: 0.8rem; font-weight: 600; margin-left: 6px; }}
        .tp-chg.up {{ color: var(--gain); }}
        .tp-chg.down {{ color: var(--loss); }}

        /* ---- sidebar ---- */
        [data-testid="stSidebar"] {{
            background: var(--panel-2); border-right: 1px solid var(--line);
        }}
        [data-testid="stSidebar"] .sec {{ margin: 10px 0 6px; }}
        [data-testid="stSidebar"] hr {{ margin: 12px 0; }}

        /* ---- bottoni ed expander ---- */
        .stButton button, .stDownloadButton button {{
            border-radius: 8px; border: 1px solid rgba(20,25,35,0.12);
        }}
        [data-testid="stExpander"] {{
            border: 1px solid var(--line); border-radius: 10px; background: transparent;
        }}
        header[data-testid="stHeader"] {{ background: transparent; }}
        [data-testid="stMainMenu"] {{ display: none; }}
        [data-testid="stPopover"] > button {{
            border: none !important; background: transparent !important;
            color: var(--muted) !important; font-weight: 700;
        }}
        [data-testid="stPopover"] > button:hover {{ color: var(--ink) !important; }}
        </style>
        """,
        unsafe_allow_html=True,
    )
