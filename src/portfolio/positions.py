"""Posizioni con prezzo di carico: dal "quanto vale oggi" al "quanto ho guadagnato".

Una posizione è {"qty": float, "price": float} — quantità e prezzo medio di
carico nella valuta di quotazione del titolo. Il formato legacy {ticker: importo}
resta caricabile: il carico è dichiarato NON noto e il P&L non viene inventato.

Convenzione FX: carico e valore vengono convertiti al cambio ODIERNO, quindi il
P&L riflette il solo movimento di prezzo del titolo (l'effetto cambio sul
capitale resta visibile nelle metriche di rischio, non nel P&L per posizione).
"""

import pandas as pd


def normalize_position(raw) -> dict:
    """Porta un valore di posizione (nuovo o legacy) alla forma canonica.

    Nuovo: {"qty": q, "price": p} → invariato.
    Legacy: importo numerico → {"amount": importo} (carico non noto).
    """
    if isinstance(raw, dict):
        if raw.get("qty") is not None and raw.get("price") is not None:
            return {"qty": float(raw["qty"]), "price": float(raw["price"])}
        if raw.get("amount") is not None:
            return {"amount": float(raw["amount"])}
        raise ValueError(f"Unrecognized position shape: {raw}")
    return {"amount": float(raw)}


def normalize_portfolio(raw: dict) -> dict[str, dict]:
    """Normalizza un intero dict {ticker: posizione} (nuovo, legacy o misto)."""
    return {str(t).upper(): normalize_position(v) for t, v in raw.items()}


def merge_lot(existing: dict | None, qty: float, price: float) -> dict:
    """Aggiunge un lotto a una posizione: quantità sommate, carico medio ponderato.

    Se la posizione esistente è legacy (solo importo, carico non noto), il
    nuovo lotto la sostituisce: meglio un carico parziale ma vero che nessuno.
    """
    if existing and "qty" in existing:
        total_qty = existing["qty"] + qty
        avg = (existing["qty"] * existing["price"] + qty * price) / total_qty
        return {"qty": total_qty, "price": avg}
    return {"qty": float(qty), "price": float(price)}


def cost_basis_native(position: dict) -> float | None:
    """Controvalore di carico nella valuta del titolo; None se non noto."""
    if "qty" in position:
        return position["qty"] * position["price"]
    return None


def position_table(
    positions: dict[str, dict],
    last_native: pd.Series,
    fx_factor: pd.Series | None = None,
) -> pd.DataFrame:
    """Tabella per-ticker di quantità, carico, valore attuale e P&L.

    `last_native` = ultimo prezzo nella valuta di quotazione per ticker;
    `fx_factor` = fattore di conversione alla valuta di visualizzazione
    (prezzo_visualizzato / prezzo_nativo all'ultima data), default 1.

    Colonne: qty, buy_price, current_price, cost, value, pnl, pnl_pct,
    cost_known. Per le posizioni legacy (solo importo) il valore attuale è
    l'importo stesso e il P&L è NaN: meglio nessun numero che un numero finto.
    """
    rows = {}
    for ticker, pos in positions.items():
        last = float(last_native.get(ticker, float("nan")))
        factor = float(fx_factor.get(ticker, 1.0)) if fx_factor is not None else 1.0
        if "qty" in pos:
            qty, buy = pos["qty"], pos["price"]
            value = qty * last * factor
            cost = qty * buy * factor
            pnl = value - cost
            rows[ticker] = {
                "qty": qty,
                "buy_price": buy,
                "current_price": last,
                "cost": cost,
                "value": value,
                "pnl": pnl,
                "pnl_pct": pnl / cost if cost else float("nan"),
                "cost_known": True,
            }
        else:
            amount = pos["amount"]
            rows[ticker] = {
                "qty": float("nan"),
                "buy_price": float("nan"),
                "current_price": last,
                "cost": amount,
                "value": amount,
                "pnl": float("nan"),
                "pnl_pct": float("nan"),
                "cost_known": False,
            }
    table = pd.DataFrame.from_dict(rows, orient="index")
    return table.sort_values("value", ascending=False)


def totals(table: pd.DataFrame) -> dict:
    """Totali di portafoglio: valore, carico, P&L (solo sulle posizioni con
    carico noto) e flag di copertura completa del carico."""
    if table.empty:
        return {"value": 0.0, "cost": 0.0, "pnl": float("nan"), "pnl_pct": float("nan"),
                "cost_known": False}
    known = table[table["cost_known"]]
    value = float(table["value"].sum())
    cost = float(table["cost"].sum())
    pnl = float(known["pnl"].sum()) if len(known) else float("nan")
    known_cost = float(known["cost"].sum()) if len(known) else 0.0
    return {
        "value": value,
        "cost": cost,
        "pnl": pnl,
        "pnl_pct": pnl / known_cost if known_cost else float("nan"),
        "cost_known": bool(table["cost_known"].all()),
    }
