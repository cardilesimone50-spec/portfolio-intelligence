"""Tasso risk-free: rendimento del T-bill USA a 13 settimane (^IRX).

È la baseline onesta per Sharpe, Sortino e ottimizzazione: usare 0 gonfia
questi rapporti, perché ignora il rendimento privo di rischio disponibile a
mercato. Yahoo espone ^IRX già annualizzato, in punti percentuali.
"""

import pandas as pd
import yfinance as yf

IRX_TICKER = "^IRX"  # rendimento annualizzato del T-bill 3M USA, in punti percentuali
DEFAULT_RISK_FREE = 0.03  # fallback prudente se la serie non è disponibile


def fetch_risk_free_rate(default: float = DEFAULT_RISK_FREE) -> float:
    """Ultimo rendimento del T-bill USA a 3 mesi (^IRX) come decimale annuo.

    Yahoo restituisce ^IRX in punti percentuali (5.25 = 5.25%): lo riportiamo a
    frazione (0.0525). Se la rete o i dati non rispondono — o il valore è fuori
    da un range plausibile — torna `default` senza rompere la UI: il risk-free
    resta comunque modificabile a mano.
    """
    latest: float | None = None

    # primario: endpoint Yahoo chart via HTTP (robusto sugli IP cloud)
    try:
        from src.data.providers import YahooChartProvider

        series = YahooChartProvider().fetch([IRX_TICKER], "5d")[IRX_TICKER].dropna()
        if not series.empty:
            latest = float(series.iloc[-1])
    except Exception:  # noqa: BLE001 — si prova il fallback
        latest = None

    # fallback: libreria yfinance
    if latest is None:
        try:
            data = yf.download(IRX_TICKER, period="5d", auto_adjust=False, progress=False)["Close"]
            if isinstance(data, pd.DataFrame):
                data = data.iloc[:, 0]
            data = data.dropna()
            if not data.empty:
                latest = float(data.iloc[-1])
        except Exception:  # noqa: BLE001
            latest = None

    if latest is None or not 0.0 <= latest <= 100.0:
        return default
    return latest / 100.0
