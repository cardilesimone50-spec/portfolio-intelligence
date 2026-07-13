"""Import di posizioni da file CSV/Excel esportati da broker."""

import io

import pandas as pd

_TICKER_COLUMNS = {
    "ticker",
    "symbol",
    "titolo",
    "simbolo",
    "stock",
    "azione",
    "strumento",
    "simbolo ticker",
    "codice",
}
_AMOUNT_COLUMNS = {
    "importo",
    "amount",
    "valore",
    "value",
    "controvalore",
    "eur",
    "euro",
    "importo (€)",
    "controvalore (€)",
    "valore di mercato",
    "valore in eur",
    "market value",
    "position value",
    "total",
}
_QUANTITY_COLUMNS = {"quantità", "quantity", "shares", "no. of shares", "qta", "pezzi"}
_PRICE_COLUMNS = {"prezzo", "price", "chiusura", "close", "prezzo medio", "price / share"}


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
        reader = lambda skip: pd.read_excel(io.BytesIO(content), skiprows=skip)  # noqa: E731
    elif name.endswith(".csv"):
        reader = lambda skip: pd.read_csv(  # noqa: E731
            io.BytesIO(content), sep=None, engine="python", skiprows=skip
        )
    else:
        raise ValueError("Formato non supportato: usa un file .csv o .xlsx")

    # gli export dei broker spesso hanno righe di intestazione prima della tabella:
    # prova a saltarne fino a 10 finché non compaiono colonne riconoscibili
    last_columns: list = []
    for skip in range(10):
        try:
            df = reader(skip)
        except Exception:
            continue
        columns = {str(c).strip().lower(): c for c in df.columns}
        ticker_col = next((columns[k] for k in columns if k in _TICKER_COLUMNS), None)
        amount_col = next((columns[k] for k in columns if k in _AMOUNT_COLUMNS), None)
        quantity_col = next((columns[k] for k in columns if k in _QUANTITY_COLUMNS), None)
        price_col = next((columns[k] for k in columns if k in _PRICE_COLUMNS), None)
        last_columns = list(df.columns)
        if ticker_col and (amount_col or (quantity_col and price_col)):
            break
    else:
        raise ValueError(
            f"Colonne non riconosciute: {last_columns}. Servono una colonna "
            "ticker (es. 'ticker', 'titolo') e una importo (es. 'importo', "
            "'controvalore') oppure quantità + prezzo."
        )

    positions: dict[str, float] = {}
    for _, row in df.iterrows():
        ticker = str(row[ticker_col]).strip().upper()
        if not ticker or ticker == "NAN":
            continue
        try:
            if amount_col is not None:
                amount = _to_number(row[amount_col])
            else:
                amount = _to_number(row[quantity_col]) * _to_number(row[price_col])
        except (ValueError, TypeError):
            continue
        if amount <= 0:
            continue
        positions[ticker] = positions.get(ticker, 0.0) + amount

    if not positions:
        raise ValueError("Nessuna posizione valida trovata nel file")
    return positions
