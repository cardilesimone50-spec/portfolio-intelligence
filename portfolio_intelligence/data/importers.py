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
_PRICE_COLUMNS = {"prezzo", "price", "chiusura", "close", "price / share"}
# prezzo di CARICO (costo medio): con la quantità permette il P&L reale
_COST_PRICE_COLUMNS = {
    "prezzo medio",
    "prezzo medio di carico",
    "prezzo di carico",
    "prezzo carico",
    "pmc",
    "avg price",
    "average price",
    "average cost",
    "avg cost",
    "cost basis",
    "book cost",
    "purchase price",
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


def parse_positions(content: bytes, filename: str) -> dict:
    """Estrae le posizioni da un CSV o Excel.

    Riconosce le colonne per nome (case-insensitive). Se il file ha quantità e
    prezzo di CARICO (es. Fineco "Prezzo medio di carico"), restituisce
    {ticker: {"qty": q, "price": p}} — da cui l'app calcola il P&L reale.
    Altrimenti ripiega su {ticker: importo} (controvalore, o quantità × prezzo
    corrente). I duplicati vengono aggregati; righe non numeriche scartate.
    """
    name = filename.lower()
    if name.endswith((".xlsx", ".xls")):
        reader = lambda skip: pd.read_excel(io.BytesIO(content), skiprows=skip)  # noqa: E731
    elif name.endswith(".csv"):
        reader = lambda skip: pd.read_csv(  # noqa: E731
            io.BytesIO(content), sep=None, engine="python", skiprows=skip
        )
    else:
        raise ValueError("Unsupported format: use a .csv or .xlsx file")

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
        cost_col = next((columns[k] for k in columns if k in _COST_PRICE_COLUMNS), None)
        last_columns = list(df.columns)
        if ticker_col and (amount_col or (quantity_col and (price_col or cost_col))):
            break
    else:
        raise ValueError(
            f"Unrecognized columns: {last_columns}. A ticker column is required "
            "(e.g. 'ticker', 'symbol') and an amount column (e.g. 'amount', "
            "'value') or quantity + price."
        )

    with_cost = quantity_col is not None and cost_col is not None
    positions: dict = {}
    for _, row in df.iterrows():
        ticker = str(row[ticker_col]).strip().upper()
        if not ticker or ticker == "NAN":
            continue
        try:
            if with_cost:
                qty = _to_number(row[quantity_col])
                cost = _to_number(row[cost_col])
                if qty <= 0 or cost <= 0:
                    continue
                # duplicati: quantità sommate, prezzo di carico medio ponderato
                prev = positions.get(ticker)
                if prev is not None:
                    total_qty = prev["qty"] + qty
                    cost = (prev["qty"] * prev["price"] + qty * cost) / total_qty
                    qty = total_qty
                positions[ticker] = {"qty": qty, "price": cost}
                continue
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
        raise ValueError("No valid position found in the file")
    return positions
