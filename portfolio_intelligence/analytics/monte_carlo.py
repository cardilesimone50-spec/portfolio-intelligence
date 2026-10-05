"""Simulazione Monte Carlo del valore del portafoglio a 1-5 anni.

Modulo puro e deterministico: stessa `random_state`, stesso risultato.

Due metodi, entrambi sui rendimenti giornalieri congiunti degli asset (in EUR
se il portafoglio è valutato in euro), con pesi costanti (ribilanciamento
giornaliero), senza costi, contributi o prelievi:

- "bootstrap" (non parametrico, a blocchi): ricampiona con reinserimento
  blocchi di giorni storici consecutivi. Ogni giorno simulato è un giorno
  realmente accaduto per tutti gli asset insieme, quindi restano le
  correlazioni effettive e le code grasse; i blocchi conservano anche un po'
  di persistenza della volatilità.
- "gbm" (parametrico, moto browniano geometrico): rendimenti logaritmici
  normali con media pari al rendimento geometrico storico del portafoglio e
  varianza w'Σw dalla matrice di covarianza degli asset.

Una proiezione probabilistica dalla serie storica, non una previsione: se il
periodo storico è stato eccezionale, lo saranno anche gli scenari.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from portfolio_intelligence.config import TRADING_DAYS

METHODS = ("bootstrap", "gbm")
PERCENTILES = (5, 10, 25, 50, 75, 90, 95)
STEPS_PER_MONTH = TRADING_DAYS // 12  # 21 giorni di borsa
MIN_OBSERVATIONS = 20  # meno di un mese di storico congiunto: troppo poco per stimare
DEFAULT_BLOCK = 5  # una settimana di borsa


@dataclass(frozen=True)
class MonteCarloResult:
    """Esito della simulazione.

    `paths` ha una riga per mese (indice in anni, 0 = oggi) e una colonna per
    percentile ("p5" … "p95"), in EUR. `final_values` sono i valori di tutte le
    simulazioni all'orizzonte.
    """

    method: str
    horizon_years: int
    n_simulations: int
    initial_value: float
    paths: pd.DataFrame
    final_values: np.ndarray = field(repr=False)

    def final(self, percentile: int) -> float:
        return float(self.paths[f"p{percentile}"].iloc[-1])

    @property
    def median_final(self) -> float:
        return self.final(50)

    @property
    def prob_loss(self) -> float:
        """Quota di scenari che finiscono sotto il valore iniziale."""
        return float(np.mean(self.final_values < self.initial_value))

    @property
    def prob_gain(self) -> float:
        return 1.0 - self.prob_loss

    @property
    def var_95(self) -> float:
        """Perdita in EUR superata solo nel 5% degli scenari (negativa = guadagno)."""
        return self.initial_value - self.final(5)

    @property
    def worst_case(self) -> dict[str, float]:
        return {"p5": self.final(5), "p10": self.final(10)}

    @property
    def best_case(self) -> dict[str, float]:
        return {"p90": self.final(90), "p95": self.final(95)}

    def value_at(self, years: float, percentile: int) -> float:
        """Valore del percentile all'anno indicato (al mese più vicino)."""
        row = self.paths.index.get_indexer([years], method="nearest")[0]
        return float(self.paths[f"p{percentile}"].iloc[row])

    def cagr(self, percentile: int, years: float | None = None) -> float:
        """Tasso composto annuo implicito nel percentile all'orizzonte (o all'anno dato)."""
        span = float(years if years is not None else self.horizon_years)
        value = self.value_at(span, percentile)
        return (value / self.initial_value) ** (1.0 / span) - 1.0

    @property
    def cagr_by_percentile(self) -> dict[str, float]:
        return {f"p{p}": self.cagr(p) for p in PERCENTILES}


def _weights(weights: Mapping[str, float] | np.ndarray, columns: pd.Index) -> pd.Series:
    """Pesi allineati alle colonne, normalizzati a somma 1; nessun peso negativo."""
    if isinstance(weights, Mapping):
        series = pd.Series({str(k): float(v) for k, v in weights.items()}, dtype=float)
        missing = sorted(set(series.index) - set(columns))
        if missing:
            raise ValueError(f"No historical returns for: {', '.join(missing)}")
        series = series.reindex(columns, fill_value=0.0)
    else:
        array = np.asarray(weights, dtype=float)
        if array.shape != (len(columns),):
            raise ValueError("weights must have one value per column of historical_returns")
        series = pd.Series(array, index=columns)
    if (series < 0).any():
        raise ValueError("Negative weights are not supported")
    total = float(series.sum())
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Weights must sum to a positive number")
    return series / total


def simulate(
    initial_value: float,
    weights: Mapping[str, float] | np.ndarray,
    historical_returns: pd.DataFrame,
    horizon_years: int = 3,
    n_simulations: int = 1000,
    method: str = "bootstrap",
    random_state: int | None = 42,
    block_size: int = DEFAULT_BLOCK,
) -> MonteCarloResult:
    """Simula `n_simulations` traiettorie del valore del portafoglio.

    `historical_returns`: rendimenti semplici giornalieri, una colonna per
    asset. Si usano solo i giorni in cui tutti gli asset con peso hanno un
    dato (rendimenti congiunti).
    """
    if initial_value <= 0:
        raise ValueError("initial_value must be positive")
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    if not 1 <= horizon_years <= 5:
        raise ValueError("horizon_years must be between 1 and 5")
    if n_simulations < 10:
        raise ValueError("n_simulations must be at least 10")

    w = _weights(weights, historical_returns.columns)
    used = w[w > 0]
    joint = historical_returns[used.index].dropna()
    if len(joint) < MIN_OBSERVATIONS:
        raise ValueError(
            f"At least {MIN_OBSERVATIONS} days of joint history are needed, got {len(joint)}"
        )
    daily = joint.to_numpy() @ used.to_numpy()  # rendimento giornaliero del portafoglio
    rng = np.random.default_rng(random_state)
    n_steps = horizon_years * TRADING_DAYS

    if method == "bootstrap":
        block = max(1, min(block_size, len(daily)))
        n_blocks = -(-n_steps // block)  # arrotondamento per eccesso
        starts = rng.integers(0, len(daily) - block + 1, size=(n_simulations, n_blocks))
        idx = (starts[:, :, None] + np.arange(block)).reshape(n_simulations, -1)[:, :n_steps]
        log_steps = np.log1p(daily[idx])
    else:
        # crescita: media dei log-rendimenti del portafoglio (rendimento geometrico);
        # volatilità: sqrt(w' Σ w) dalla covarianza dei rendimenti degli asset
        mu = float(np.log1p(daily).mean())
        cov = np.atleast_2d(np.cov(joint.to_numpy(), rowvar=False, ddof=1))
        w_used = used.to_numpy()
        sigma = float(np.sqrt(w_used @ cov @ w_used))
        log_steps = rng.normal(mu, sigma, size=(n_simulations, n_steps))

    # valore a fine mese: si cumulano i log-rendimenti e si campiona ogni 21 giorni
    cumulative = np.cumsum(log_steps, axis=1)[:, STEPS_PER_MONTH - 1 :: STEPS_PER_MONTH]
    values = initial_value * np.exp(np.hstack([np.zeros((n_simulations, 1)), cumulative]))
    months = np.arange(values.shape[1])
    paths = pd.DataFrame(
        {f"p{p}": np.percentile(values, p, axis=0) for p in PERCENTILES},
        index=pd.Index(months / 12.0, name="years"),
    )
    paths.iloc[0] = initial_value  # t = 0: tutti i percentili coincidono, senza rumore numerico
    return MonteCarloResult(
        method=method,
        horizon_years=horizon_years,
        n_simulations=n_simulations,
        initial_value=float(initial_value),
        paths=paths,
        final_values=values[:, -1],
    )


def scenario_table(result: MonteCarloResult, years: tuple[int, ...] = (1, 3, 5)) -> list[dict]:
    """Scenari pessimistico (p10), mediano (p50) e ottimistico (p90) agli anni dati.

    Gli anni oltre l'orizzonte simulato vengono saltati.
    """
    return [
        {
            "years": y,
            "initial": result.initial_value,
            "p10": result.value_at(y, 10),
            "p50": result.value_at(y, 50),
            "p90": result.value_at(y, 90),
        }
        for y in years
        if y <= result.horizon_years
    ]
