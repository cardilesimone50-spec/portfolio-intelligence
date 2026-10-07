"""Universi di riferimento (benchmark): un registro unico per dati, analisi e interfaccia.

Ogni benchmark ha un simbolo canonico in simbologia Yahoo — è anche il valore
salvato nel database per ogni cliente — e i simboli equivalenti per gli altri
provider della catena (`providers.py`). Un simbolo `None` vuol dire che quel
provider non copre la serie: viene saltato e la catena passa al successivo,
invece di interrogare un simbolo inventato.

Rendimento totale e indici di prezzo: i prezzi del portafoglio sono chiusure
rettificate (dividendi inclusi). QQQ, un ETF, è rettificato allo stesso modo;
^GSPC, FTSEMIB.MI e ^STOXX sono indici di PREZZO, senza dividendi, quindi il
rendimento relativo e l'alfa verso questi indici risultano sovrastimati di
circa il rendimento da dividendi dell'indice. `total_return` lo dichiara, e
interfaccia e report lo riportano accanto ai numeri.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Benchmark:
    ticker: str  # simbolo canonico (Yahoo): chiave nel DB e colonna dei prezzi
    label: str  # etichetta breve: grafici, tabelle, report
    name: str  # nome esteso: selettore dell'interfaccia
    currency: str  # valuta di quotazione: decide la conversione in EUR (fx.py)
    total_return: bool  # True: dividendi reinvestiti (prezzo rettificato)
    stooq: str | None = None  # simbolo Stooq; None = non coperto
    eodhd: str | None = None  # simbolo EODHD; None = non coperto


_REGISTRY = (
    # storico predefinito: l'ETF sul Nasdaq-100, a rendimento totale
    Benchmark("QQQ", "QQQ", "Nasdaq-100 (ETF QQQ)", "USD", True, stooq="qqq.us", eodhd="QQQ.US"),
    Benchmark("^GSPC", "S&P 500", "S&P 500", "USD", False, stooq="^spx", eodhd="GSPC.INDX"),
    Benchmark("FTSEMIB.MI", "FTSE MIB", "FTSE MIB", "EUR", False, eodhd="FTSEMIB.INDX"),
    # su EODHD lo STOXX Europe 600 è SXXP; STOXX.INDX è lo STOXX Europe 50
    Benchmark("^STOXX", "STOXX 600", "STOXX Europe 600", "EUR", False, eodhd="SXXP.INDX"),
)

BENCHMARKS: dict[str, Benchmark] = {b.ticker: b for b in _REGISTRY}
BENCHMARK_TICKERS = tuple(BENCHMARKS)
# il benchmark dei record senza scelta esplicita (clienti storici, area Investor)
DEFAULT_BENCHMARK = "QQQ"


def benchmark_or_default(ticker: str | None) -> str:
    """Benchmark salvato, o il predefinito per i record storici (NULL) e i valori sconosciuti."""
    return ticker if ticker in BENCHMARKS else DEFAULT_BENCHMARK


def benchmark_label(ticker: str) -> str:
    """Etichetta breve del benchmark; il ticker stesso se non è nel registro."""
    benchmark = BENCHMARKS.get(ticker)
    return benchmark.label if benchmark is not None else ticker


def is_price_index(ticker: str) -> bool:
    """True per gli indici di prezzo del registro (dividendi esclusi dalla serie)."""
    benchmark = BENCHMARKS.get(ticker)
    return benchmark is not None and not benchmark.total_return
