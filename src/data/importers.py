"""Import di posizioni da file CSV/Excel esportati da broker."""

import io

import pandas as pd

_TICKER_COLUMNS = {"ticker", "symbol", "titolo", "simbolo", "stock", "azione", "strumento"}
_AMOUNT_COLUMNS = {
    "importo", "amount", "valore", "value", "controvalore", "eur", "euro",
    "importo (€)", "controvalore (€)", "valore di mercato",
}


def _to_number(value) -> float:
    """Converte importi anche in formato italiano ('1.234,56 €') in float."""
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("€", "").replace(" ", "").strip()
    if "," in text:
        # formato italiano: il punto è il separatore delle migliaia
        text = text.replace(".", "").replace(",", ".")
    return float(text)


def parse_positions(content: bytes, filename: str) -> dict[str, float]:
    """Estrae {ticker: importo} da un CSV o Excel.

    Riconosce le colonne per nome (case-insensitive): una tra ticker/symbol/
    titolo/... e una tra importo/amount/controvalore/... I duplicati vengono
    sommati; righe con importo non positivo o non numerico vengono scartate.
    """
    name = filename.lower()
    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(content))
    elif name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content), sep=None, engine="python")
    else:
        raise ValueError("Formato non supportato: usa un file .csv o .xlsx")

    columns = {str(c).strip().lower(): c for c in df.columns}
    ticker_col = next((columns[k] for k in columns if k in _TICKER_COLUMNS), None)
    amount_col = next((columns[k] for k in columns if k in _AMOUNT_COLUMNS), None)
    if ticker_col is None or amount_col is None:
        raise ValueError(
            f"Colonne non riconosciute: {list(df.columns)}. Servono una colonna "
            "ticker (es. 'ticker', 'titolo') e una importo (es. 'importo', "
            "'controvalore')."
        )

    positions: dict[str, float] = {}
    for _, row in df.iterrows():
        ticker = str(row[ticker_col]).strip().upper()
        if not ticker or ticker == "NAN":
            continue
        try:
            amount = _to_number(row[amount_col])
        except (ValueError, TypeError):
            continue
        if amount <= 0:
            continue
        positions[ticker] = positions.get(ticker, 0.0) + amount

    if not positions:
        raise ValueError("Nessuna posizione valida trovata nel file")
    return positions
