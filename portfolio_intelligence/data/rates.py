"""Tasso risk-free: rendimento del T-bill USA a 13 settimane.

È la baseline onesta per Sharpe, Sortino e ottimizzazione: usare 0 gonfia
questi rapporti, perché ignora il rendimento privo di rischio disponibile a
mercato. Fonte primaria: il Tesoro USA (dato pubblico, riutilizzabile), colonna
"13 WEEKS BANK DISCOUNT", la stessa grandezza di ^IRX su Yahoo; in punti
percentuali annualizzati.
"""

import io
from datetime import date

import pandas as pd
import requests
import yfinance as yf

from portfolio_intelligence.logging_config import get_logger

log = get_logger(__name__)

TREASURY_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rates.csv/{year}/all"
)
TREASURY_COLUMN = "13 WEEKS BANK DISCOUNT"

IRX_TICKER = "^IRX"  # rendimento annualizzato del T-bill 3M USA, in punti percentuali
DEFAULT_RISK_FREE = 0.03  # fallback prudente se la serie non è disponibile


def fetch_tbill_treasury(today: date | None = None) -> float | None:
    """Ultimo rendimento del T-bill a 13 settimane dal Tesoro USA, in punti %.

    A inizio anno il file dell'anno corrente può essere vuoto: si prova anche
    quello precedente.
    """
    year = (today or date.today()).year
    for y in (year, year - 1):
        resp = requests.get(
            TREASURY_URL.format(year=y),
            params={
                "type": "daily_treasury_bill_rates",
                "field_tdr_date_value": str(y),
                "_format": "csv",
            },
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        resp.raise_for_status()
        if not resp.text.strip():
            continue
        frame = pd.read_csv(io.StringIO(resp.text))
        if TREASURY_COLUMN not in frame.columns:
            continue
        series = pd.Series(
            pd.to_numeric(frame[TREASURY_COLUMN], errors="coerce").to_numpy(),
            index=pd.to_datetime(frame["Date"], format="%m/%d/%Y"),
        ).dropna()
        if not series.empty:
            return float(series.sort_index().iloc[-1])
    return None


def fetch_risk_free_rate(default: float = DEFAULT_RISK_FREE) -> float:
    """Ultimo rendimento del T-bill USA a 3 mesi come decimale annuo.

    Le fonti lo danno in punti percentuali (5.25 = 5.25%): lo riportiamo a
    frazione (0.0525). Se la rete o i dati non rispondono — o il valore è fuori
    da un range plausibile — torna `default` senza rompere la UI: il risk-free
    resta comunque modificabile a mano.
    """
    latest: float | None = None

    # primario: Tesoro USA (fonte ufficiale)
    try:
        latest = fetch_tbill_treasury()
    except Exception as exc:  # noqa: BLE001 — si prova la riserva
        log.warning("US Treasury T-bill rate unavailable, falling back to Yahoo: %s", exc)
        latest = None

    # riserva: endpoint Yahoo chart via HTTP
    if latest is None:
        try:
            from portfolio_intelligence.data.providers import YahooChartProvider

            series = YahooChartProvider().fetch([IRX_TICKER], "5d")[IRX_TICKER].dropna()
            if not series.empty:
                latest = float(series.iloc[-1])
        except Exception:  # noqa: BLE001 — si prova l'ultima riserva
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
