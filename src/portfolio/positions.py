"""Posizioni per lotti: quantità, prezzo E data di carico → P&L e IRR reali.

Forma canonica di una posizione: {"lots": [{"qty", "price", "date"?}, ...]} —
ogni lotto ha quantità, prezzo medio di carico nella valuta di quotazione e,
se nota, la data di acquisto (ISO "YYYY-MM-DD"). Restano caricabili i formati
precedenti: {"qty","price"} (un lotto senza data) e il legacy {ticker: importo}
(carico non noto: il P&L non viene inventato).

Convenzione FX: carico e valore vengono convertiti al cambio ODIERNO, quindi il
P&L riflette il solo movimento di prezzo del titolo. Con le date dei lotti si
calcolano holding period, rendimento annualizzato per posizione e IRR
money-weighted del portafoglio (i flussi veri dell'investitore).
"""

from datetime import date as _date
from datetime import datetime

import pandas as pd


def _clean_date(value) -> str | None:
    """Data del lotto come ISO "YYYY-MM-DD" (serializzabile in JSON), o None."""
    if value in (None, ""):
        return None
    if isinstance(value, str):
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    if isinstance(value, (_date, datetime, pd.Timestamp)):
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    raise ValueError(f"Unrecognized lot date: {value!r}")


def normalize_position(raw) -> dict:
    """Porta un valore di posizione (lotti, singolo o legacy) alla forma canonica."""
    if isinstance(raw, dict):
        if raw.get("lots"):
            lots = [
                {
                    "qty": float(lot["qty"]),
                    "price": float(lot["price"]),
                    "date": _clean_date(lot.get("date")),
                }
                for lot in raw["lots"]
            ]
            return {"lots": lots}
        if raw.get("qty") is not None and raw.get("price") is not None:
            return {
                "lots": [
                    {
                        "qty": float(raw["qty"]),
                        "price": float(raw["price"]),
                        "date": _clean_date(raw.get("date")),
                    }
                ]
            }
        if raw.get("amount") is not None:
            return {"amount": float(raw["amount"])}
        raise ValueError(f"Unrecognized position shape: {raw}")
    return {"amount": float(raw)}


def normalize_portfolio(raw: dict) -> dict[str, dict]:
    """Normalizza un intero dict {ticker: posizione} (nuovo, legacy o misto)."""
    return {str(t).upper(): normalize_position(v) for t, v in raw.items()}


def add_lot(existing: dict | None, qty: float, price: float, date=None) -> dict:
    """Aggiunge un lotto a una posizione, preservando la storia dei lotti.

    Se la posizione esistente è legacy (solo importo, carico non noto), il
    nuovo lotto la sostituisce: meglio un carico parziale ma vero che nessuno.
    """
    lot = {"qty": float(qty), "price": float(price), "date": _clean_date(date)}
    if existing and existing.get("lots"):
        return {"lots": [*existing["lots"], lot]}
    return {"lots": [lot]}


# retrocompatibilità col nome precedente (stessa semantica, senza data)
def merge_lot(existing: dict | None, qty: float, price: float) -> dict:
    return add_lot(existing, qty, price)


def aggregate(position: dict) -> dict | None:
    """Quantità totale, carico medio e prima data dei lotti; None se legacy."""
    lots = position.get("lots")
    if not lots:
        return None
    qty = sum(lot["qty"] for lot in lots)
    cost = sum(lot["qty"] * lot["price"] for lot in lots)
    dates = [lot["date"] for lot in lots if lot.get("date")]
    return {
        "qty": qty,
        "price": cost / qty if qty else float("nan"),
        "first_date": min(dates) if dates else None,
        "all_dated": len(dates) == len(lots),
    }


def cost_basis_native(position: dict) -> float | None:
    """Controvalore di carico nella valuta del titolo; None se non noto."""
    agg = aggregate(position)
    if agg is None:
        return None
    return agg["qty"] * agg["price"]


def xirr(flows: list[tuple], guess_hi: float = 10.0) -> float | None:
    """Tasso interno di rendimento (annuo, act/365) dei flussi (data, importo).

    Convenzione: esborsi negativi, incassi positivi. Bisezione sull'NPV in
    (-99%, +1000%); None se i flussi non hanno una radice (es. tutti positivi)
    o coprono meno di 7 giorni (annualizzare avrebbe poco senso).
    """
    if len(flows) < 2:
        return None
    dated = sorted((pd.Timestamp(d), float(v)) for d, v in flows)
    t0 = dated[0][0]
    span_days = (dated[-1][0] - t0).days
    if span_days < 7:
        return None
    years = [(d - t0).days / 365.0 for d, _ in dated]
    values = [v for _, v in dated]
    if not (any(v < 0 for v in values) and any(v > 0 for v in values)):
        return None

    def npv(rate: float) -> float:
        return sum(v / (1 + rate) ** t for v, t in zip(values, years, strict=True))

    lo, hi = -0.99, guess_hi
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        return None
    for _ in range(100):
        mid = (lo + hi) / 2
        f_mid = npv(mid)
        if abs(f_mid) < 1e-9:
            break
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return float((lo + hi) / 2)


def portfolio_xirr(
    positions: dict[str, dict],
    last_native: pd.Series,
    fx_factor: pd.Series | None = None,
    today=None,
) -> float | None:
    """IRR money-weighted del portafoglio dai flussi dei lotti datati.

    Richiede che TUTTI i lotti abbiano data e carico: con dati parziali si
    restituisce None invece di un numero mezzo inventato.
    """
    today = pd.Timestamp(today) if today is not None else pd.Timestamp.now().normalize()
    flows: list[tuple] = []
    final_value = 0.0
    for ticker, pos in positions.items():
        lots = pos.get("lots")
        if not lots or any(not lot.get("date") for lot in lots):
            return None
        last = float(last_native.get(ticker, float("nan")))
        factor = float(fx_factor.get(ticker, 1.0)) if fx_factor is not None else 1.0
        if last != last:
            return None
        for lot in lots:
            flows.append((lot["date"], -lot["qty"] * lot["price"] * factor))
        final_value += sum(lot["qty"] for lot in lots) * last * factor
    flows.append((today, final_value))
    return xirr(flows)


def position_table(
    positions: dict[str, dict],
    last_native: pd.Series,
    fx_factor: pd.Series | None = None,
    today=None,
) -> pd.DataFrame:
    """Tabella per-ticker: quantità, carico, data, valore attuale, P&L e IRR.

    `last_native` = ultimo prezzo nella valuta di quotazione per ticker;
    `fx_factor` = fattore di conversione alla valuta di visualizzazione
    (prezzo_visualizzato / prezzo_nativo all'ultima data), default 1.

    Colonne: qty, buy_price, buy_date, days_held, current_price, cost, value,
    pnl, pnl_pct, ann_pct (IRR annuo della posizione, solo se i lotti sono
    datati), cost_known. Per le posizioni legacy il valore attuale è l'importo
    stesso e il P&L è NaN: meglio nessun numero che un numero finto.
    """
    today = pd.Timestamp(today) if today is not None else pd.Timestamp.now().normalize()
    rows = {}
    for ticker, pos in positions.items():
        last = float(last_native.get(ticker, float("nan")))
        factor = float(fx_factor.get(ticker, 1.0)) if fx_factor is not None else 1.0
        agg = aggregate(pos)
        if agg is not None:
            qty, buy = agg["qty"], agg["price"]
            value = qty * last * factor
            cost = qty * buy * factor
            pnl = value - cost
            first = pd.Timestamp(agg["first_date"]) if agg["first_date"] else pd.NaT
            days = (today - first).days if first is not pd.NaT else float("nan")
            ann = float("nan")
            if agg["all_dated"] and last == last:
                flows = [
                    (lot["date"], -lot["qty"] * lot["price"] * factor)
                    for lot in pos["lots"]
                ]
                flows.append((today, value))
                ann_val = xirr(flows)
                ann = ann_val if ann_val is not None else float("nan")
            rows[ticker] = {
                "qty": qty,
                "buy_price": buy,
                "buy_date": first,
                "days_held": days,
                "current_price": last,
                "cost": cost,
                "value": value,
                "pnl": pnl,
                "pnl_pct": pnl / cost if cost else float("nan"),
                "ann_pct": ann,
                "cost_known": True,
            }
        else:
            amount = pos["amount"]
            rows[ticker] = {
                "qty": float("nan"),
                "buy_price": float("nan"),
                "buy_date": pd.NaT,
                "days_held": float("nan"),
                "current_price": last,
                "cost": amount,
                "value": amount,
                "pnl": float("nan"),
                "pnl_pct": float("nan"),
                "ann_pct": float("nan"),
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
