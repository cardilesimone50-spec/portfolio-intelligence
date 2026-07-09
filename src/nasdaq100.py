"""Recupero della lista dei ticker che compongono l'indice Nasdaq-100."""

import io

import pandas as pd
import requests

_URL = "https://www.slickcharts.com/nasdaq100"
_HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio-intelligence research script)"}


def get_nasdaq100_tickers() -> list[str]:
    """Scarica la lista aggiornata dei ticker che compongono il Nasdaq-100."""
    try:
        response = requests.get(_URL, headers=_HEADERS, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise ValueError(
            f"Errore di rete durante il download della lista Nasdaq-100: {exc}"
        ) from exc

    tables = pd.read_html(io.StringIO(response.text))
    components = tables[0]
    return components["Symbol"].tolist()
