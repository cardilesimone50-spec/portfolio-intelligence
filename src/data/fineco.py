"""Parsing dell'estratto conto Fineco: estrae la posizione titoli dal PDF.

La sezione «Strumenti finanziari» elenca un titolo per riga, nella forma
    <ISIN> <descrizione> <quantità...> <divisa> <prezzi/cambi...> <controvalore>
Il controvalore è già in euro (la loro somma è la riga «Totale in euro»).

Estraiamo ISIN, descrizione, divisa e controvalore EUR: il ticker prezzabile si
ottiene poi risolvendo l'ISIN (src.data.isin), perché gli estratti bancari non
riportano ticker. Questa funzione è pura e non fa rete: il parsing del testo è
separato dall'estrazione del PDF così da poter essere testato in modo
deterministico.
"""

from __future__ import annotations

import io
import re
from collections.abc import Callable
from dataclasses import dataclass

from src.data.isin import SecurityRef, resolve_isins

# ISIN: 2 lettere paese + 9 alfanumerici + 1 cifra di controllo
_ISIN_RE = re.compile(r"\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b")
# numero in formato italiano: 1.234,56 oppure 12,50 (con eventuale segno)
_NUMBER_RE = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d+|-?\d+,\d+")
_SECTION_START = "Strumenti finanziari"
_SECTION_END = re.compile(r"totale in euro", re.IGNORECASE)


@dataclass(frozen=True)
class FinecoHolding:
    """Una riga della posizione titoli Fineco."""

    isin: str
    name: str
    currency: str
    market_value_eur: float


def _to_number(token: str) -> float:
    """'6.375,80' -> 6375.80 (formato italiano)."""
    return float(token.replace(".", "").replace(",", "."))


def extract_holdings(text: str) -> list[FinecoHolding]:
    """Estrae le posizioni dalla sezione «Strumenti finanziari» del testo.

    Robusto rispetto alle intestazioni di pagina che si intromettono nella
    tabella (righe senza ISIN vengono ignorate). Si ferma alla riga «Totale in
    euro» che chiude la sezione.
    """
    holdings: list[FinecoHolding] = []
    in_section = False
    for line in text.splitlines():
        if _SECTION_START in line:
            in_section = True
            continue
        if not in_section:
            continue
        if _SECTION_END.search(line):
            break
        match = _ISIN_RE.search(line)
        if not match:
            continue
        isin = match.group(1)
        rest = line[match.end() :]
        numbers = _NUMBER_RE.findall(rest)
        if not numbers:
            continue
        market_value = _to_number(numbers[-1])  # ultimo numero = controvalore EUR
        if market_value <= 0:
            continue
        currency = "USD" if re.search(r"\bUSD\b", rest) else "EUR"
        # descrizione: dall'ISIN fino alla prima quantità (primo numero della riga)
        first_number = _NUMBER_RE.search(rest)
        name = rest[: first_number.start()].strip() if first_number else ""
        holdings.append(FinecoHolding(isin, name, currency, market_value))
    return holdings


def parse_fineco_pdf(content: bytes) -> list[FinecoHolding]:
    """Estrae la posizione titoli da un PDF Fineco (usa pdfplumber)."""
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    holdings = extract_holdings("\n".join(pages))
    if not holdings:
        raise ValueError(
            "No securities position found: is this a Fineco statement with a "
            "'Strumenti finanziari' section?"
        )
    return holdings


def resolve_to_positions(
    holdings: list[FinecoHolding],
    resolver: Callable[[list[str]], dict[str, SecurityRef]] = resolve_isins,
) -> tuple[dict[str, float], list[FinecoHolding]]:
    """Trasforma gli holding (per ISIN) in {ticker: controvalore EUR}.

    Usa `resolver` (ISIN → SecurityRef, di default OpenFIGI; iniettabile nei
    test) per ottenere un ticker prezzabile. Gli strumenti non risolvibili —
    tipicamente obbligazioni come i BTP, che il motore azionario non prezza —
    vengono restituiti a parte così da poterlo dire all'utente invece di
    ignorarli in silenzio.
    """
    refs = resolver([h.isin for h in holdings])
    positions: dict[str, float] = {}
    skipped: list[FinecoHolding] = []
    for holding in holdings:
        ref = refs.get(holding.isin)
        # non risolto, oppure risolto ma non azionario (bond/fondo): non prezzabile
        if ref is None or not ref.is_priceable_equity:
            skipped.append(holding)
            continue
        positions[ref.ticker] = positions.get(ref.ticker, 0.0) + holding.market_value_eur
    return positions, skipped
