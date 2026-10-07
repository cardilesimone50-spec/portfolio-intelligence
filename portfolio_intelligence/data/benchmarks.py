"""Universi di riferimento (benchmark): un registro unico per dati, analisi e interfaccia.

Ogni benchmark ha un simbolo canonico in simbologia Yahoo — è anche il valore
salvato nel database per ogni cliente — e i simboli equivalenti per gli altri
provider della catena (`providers.py`). Un simbolo `None` vuol dire che quel
provider non copre la serie: viene saltato e la catena passa al successivo,
invece di interrogare un simbolo inventato.

Solo serie TOTAL RETURN: i prezzi del portafoglio sono chiusure rettificate
(dividendi inclusi), quindi anche il benchmark deve reinvestire i dividendi,
altrimenti rendimento relativo e alfa risultano gonfiati del rendimento da
dividendi dell'indice. Dove Yahoo non pubblica un indice total return
affidabile si usa un ETF ad accumulazione a replica fisica sullo stesso indice
(rendimento al netto dei costi del fondo): il nome esteso lo dichiara e i
report lo riportano nella metodologia.
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
    # indice total return ufficiale di S&P Dow Jones Indices (lordo, dividendi reinvestiti)
    Benchmark("^SP500TR", "S&P 500 TR", "S&P 500 Total Return", "USD"),
    # su Yahoo FTSEMIBN.MI ("Net Total Return") riporta i valori dell'indice di prezzo:
    # si usa l'ETF iShares ad accumulazione (IE00B53L4X51), che replica il FTSE MIB Net TR
    Benchmark(
        "CSMIB.MI",
        "FTSE MIB TR",
        "FTSE MIB Net Total Return (ETF iShares CSMIB)",
        "EUR",
        eodhd="CSMIB.MI",
    ),
    # lo STOXX Europe 600 NR su Yahoo (SXXR.Z) ha storico breve e valori incoerenti: ETF
    # Amundi Core ad accumulazione (LU0908500753), su Euronext Paris dal 2013, TER 0,07%
    Benchmark(
        "MEUD.PA",
        "STOXX 600 TR",
        "STOXX Europe 600 Net Total Return (ETF Amundi MEUD)",
        "EUR",
        eodhd="MEUD.PA",
    ),
)

BENCHMARKS: dict[str, Benchmark] = {b.ticker: b for b in _REGISTRY}
BENCHMARK_TICKERS = tuple(BENCHMARKS)
# il benchmark dei record senza scelta esplicita (clienti storici, area Investor)
DEFAULT_BENCHMARK = "QQQ"
# indici di prezzo usati prima del passaggio al total return: un cliente salvato con
# uno di questi passa alla serie total return dello stesso indice, non al predefinito
LEGACY_BENCHMARKS = {"^GSPC": "^SP500TR", "FTSEMIB.MI": "CSMIB.MI", "^STOXX": "MEUD.PA"}


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
