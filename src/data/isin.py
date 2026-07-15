"""Risoluzione ISIN → ticker prezzabile tramite OpenFIGI (Bloomberg).

Gli estratti conto bancari identificano i titoli per ISIN (es. US0378331005),
non per ticker: senza questa risoluzione il layer prezzi non sa cosa scaricare.

OpenFIGI è gratuito e ufficiale: senza API key concede ~25 richieste/minuto e
fino a 10 job per chiamata. Con una chiave gratuita (header X-OPENFIGI-APIKEY)
i limiti salgono, ma qui non è obbligatoria.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests

_OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
_MAX_JOBS_ANON = 10  # job per richiesta senza chiave
_MAX_JOBS_KEYED = 100
_TIMEOUT = 15

# a parità di ISIN OpenFIGI restituisce più listing (borse diverse): preferiamo
# le piazze con prezzo facilmente reperibile, USA in testa.
_EXCHANGE_PREFERENCE = ["US", "MM", "MI", "GR", "PA", "LN"]


class IsinError(Exception):
    """La risoluzione ISIN non è andata a buon fine."""


@dataclass(frozen=True)
class SecurityRef:
    """Titolo risolto a partire da un ISIN."""

    isin: str
    ticker: str
    exchange: str
    name: str
    market_sector: str = "Equity"

    @property
    def is_priceable_equity(self) -> bool:
        """True per azioni/ETF (marketSector 'Equity'); False per bond/fondi.

        Il motore prezzi è azionario: obbligazioni (Govt/Corp) e simili hanno un
        ISIN risolvibile ma nessun ticker prezzabile su un feed azionario.
        """
        return self.market_sector == "Equity"


def _api_key() -> str | None:
    return os.getenv("OPENFIGI_API_KEY")


def _pick_best(candidates: list[dict]) -> dict | None:
    """Sceglie il listing migliore tra i candidati di OpenFIGI per un ISIN."""
    usable = [c for c in candidates if c.get("ticker")]
    if not usable:
        return None

    def rank(candidate: dict) -> tuple[int, int]:
        exch = candidate.get("exchCode") or ""
        try:
            exch_rank = _EXCHANGE_PREFERENCE.index(exch)
        except ValueError:
            exch_rank = len(_EXCHANGE_PREFERENCE)
        # a parità, preferiamo le azioni ordinarie ai derivati/altro
        type_rank = 0 if candidate.get("securityType") == "Common Stock" else 1
        return exch_rank, type_rank

    return min(usable, key=rank)


def resolve_isins(
    isins: list[str], *, post=requests.post
) -> dict[str, SecurityRef]:
    """Mappa ISIN → SecurityRef per gli ISIN risolti (gli altri sono omessi).

    `post` è iniettabile per i test (nessuna chiamata di rete reale).
    """
    unique = [i.strip().upper() for i in isins if i and i.strip()]
    if not unique:
        return {}

    headers = {"Content-Type": "application/json"}
    key = _api_key()
    if key:
        headers["X-OPENFIGI-APIKEY"] = key
    chunk_size = _MAX_JOBS_KEYED if key else _MAX_JOBS_ANON

    resolved: dict[str, SecurityRef] = {}
    for start in range(0, len(unique), chunk_size):
        chunk = unique[start : start + chunk_size]
        jobs = [{"idType": "ID_ISIN", "idValue": isin} for isin in chunk]
        try:
            resp = post(_OPENFIGI_URL, json=jobs, headers=headers, timeout=_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
        except (requests.RequestException, ValueError) as exc:
            raise IsinError(f"OpenFIGI request failed: {exc}") from exc

        for isin, result in zip(chunk, payload, strict=False):
            best = _pick_best(result.get("data") or [])
            if best is None:
                continue
            resolved[isin] = SecurityRef(
                isin=isin,
                ticker=str(best["ticker"]),
                exchange=str(best.get("exchCode") or ""),
                name=str(best.get("name") or ""),
                market_sector=str(best.get("marketSector") or ""),
            )
    return resolved


def resolve_isin(isin: str, *, post=requests.post) -> SecurityRef | None:
    """Risolve un singolo ISIN; None se non trovato."""
    return resolve_isins([isin], post=post).get(isin.strip().upper())
