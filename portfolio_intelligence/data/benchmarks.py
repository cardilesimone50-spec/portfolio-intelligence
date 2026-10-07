"""Universi di riferimento (benchmark): un registro unico per dati, analisi e interfaccia.

Ogni benchmark ha un simbolo canonico in simbologia Yahoo — è anche il valore
salvato nel database per ogni cliente — e i simboli equivalenti per gli altri
provider della catena (`providers.py`). Un simbolo `None` vuol dire che quel
provider non copre la serie: viene saltato e la catena passa al successivo,
invece di interrogare un simbolo inventato.

Solo serie TOTAL RETURN: i prezzi del portafoglio sono chiusure rettificate
(dividendi inclusi), quindi anche il benchmark deve reinvestire i dividendi,
altrimenti rendimento relativo e alfa risultano gonfiati del rendimento da
dividendi dell'indice. Tutte le serie sono ETF a replica fisica con storico
giornaliero lungo su Yahoo e coperti dal feed con licenza (EODHD): prezzo
rettificato per i dividendi (QQQ, SPY, EXSA) o ETF ad accumulazione (CSMIB). Il
rendimento è al netto dei costi del fondo e delle ritenute che il fondo subisce
sui dividendi: i report lo dichiarano nella metodologia.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Benchmark:
    ticker: str  # simbolo canonico (Yahoo): chiave nel DB e colonna dei prezzi
    label: str  # etichetta breve: grafici, tabelle, report
    name: str  # nome esteso: selettore dell'interfaccia e metodologia dei report
    currency: str  # valuta di quotazione: decide la conversione in EUR (fx.py)
    stooq: str | None = None  # simbolo Stooq; None = non coperto
    eodhd: str | None = None  # simbolo EODHD; None = non coperto


_REGISTRY = (
    # storico predefinito: l'ETF sul Nasdaq-100, total return tramite il prezzo rettificato
    Benchmark("QQQ", "QQQ", "Nasdaq-100 (ETF QQQ)", "USD", stooq="qqq.us", eodhd="QQQ.US"),
    # come QQQ: ETF USA, total return tramite il prezzo rettificato, dal 1993. L'indice
    # ^SP500TR esiste solo su Yahoo: nessuna fonte con licenza né riserva
    Benchmark("SPY", "S&P 500 TR", "S&P 500 Total Return (ETF SPY)", "USD", eodhd="SPY.US"),
    # su Yahoo FTSEMIBN.MI ("Net Total Return") riporta i valori dell'indice di prezzo:
    # si usa l'ETF iShares ad accumulazione (IE00B53L4X51), che replica il FTSE MIB Net TR
    Benchmark(
        "CSMIB.MI",
        "FTSE MIB TR",
        "FTSE MIB Net Total Return (ETF iShares CSMIB)",
        "EUR",
        eodhd="CSMIB.MI",
    ),
    # lo STOXX Europe 600 NR su Yahoo (SXXR.Z) ha storico breve e valori incoerenti, e gli
    # ETF ad accumulazione (MEUD.PA, XSX6.DE) hanno storico giornaliero solo dal 2023-2024:
    # ETF iShares (DE0002635307, Xetra, dal 2004), total return tramite il prezzo rettificato
    Benchmark(
        "EXSA.DE",
        "STOXX 600 TR",
        "STOXX Europe 600 Total Return (ETF iShares EXSA)",
        "EUR",
        eodhd="EXSA.XETRA",
    ),
)

BENCHMARKS: dict[str, Benchmark] = {b.ticker: b for b in _REGISTRY}
BENCHMARK_TICKERS = tuple(BENCHMARKS)
# il benchmark dei record senza scelta esplicita (clienti storici, area Investor)
DEFAULT_BENCHMARK = "QQQ"
# indici di prezzo usati prima del passaggio al total return: un cliente salvato con
# uno di questi passa alla serie total return dello stesso indice, non al predefinito
LEGACY_BENCHMARKS = {"^GSPC": "SPY", "FTSEMIB.MI": "CSMIB.MI", "^STOXX": "EXSA.DE"}


def canonical_benchmark(ticker: str | None) -> str | None:
    """Il ticker del registro (anche da un ticker storico), o None se sconosciuto."""
    resolved = LEGACY_BENCHMARKS.get(ticker or "", ticker)
    return resolved if resolved in BENCHMARKS else None


def benchmark_or_default(ticker: str | None) -> str:
    """Benchmark salvato, o il predefinito per i record storici (NULL) e i valori sconosciuti."""
    return canonical_benchmark(ticker) or DEFAULT_BENCHMARK


def benchmark_label(ticker: str) -> str:
    """Etichetta breve del benchmark; il ticker stesso se non è nel registro."""
    benchmark = BENCHMARKS.get(ticker)
    return benchmark.label if benchmark is not None else ticker


def benchmark_name(ticker: str) -> str:
    """Nome esteso del benchmark (serie e, per gli ETF, il fondo); il ticker se sconosciuto."""
    benchmark = BENCHMARKS.get(ticker)
    return benchmark.name if benchmark is not None else ticker
