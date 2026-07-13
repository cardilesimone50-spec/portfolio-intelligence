"""Interpretazione in linguaggio umano delle metriche ("so what?").

Regole di onestà: fasce basate su riferimenti dichiarati (norme storiche
dell'azionario, soglie convenzionali di correzione/bear market) e percentili
calcolati SOLO contro l'universo Nasdaq-100 che abbiamo davvero in database.
Nessun confronto con dataset che non possediamo.
"""

import pandas as pd


def universe_percentile(value: float, universe: pd.Series) -> float:
    """Frazione dell'universo con valore inferiore a `value` (0-1)."""
    valid = universe.dropna()
    if len(valid) == 0 or value != value:
        return float("nan")
    return float((valid < value).mean())


def interpret_volatility(annual_vol: float, universe_vols: pd.Series | None = None) -> str:
    if annual_vol != annual_vol:
        return ""
    if annual_vol < 0.12:
        text = "Oscillazioni da portafoglio prudente."
    elif annual_vol < 0.22:
        text = "Oscillazioni tipiche di un azionario diversificato."
    elif annual_vol < 0.35:
        text = "Oscillazioni elevate: preparati a variazioni ampie."
    else:
        text = "Oscillazioni da singolo titolo aggressivo, non da portafoglio."
    if universe_vols is not None:
        pct = universe_percentile(annual_vol, universe_vols)
        if pct == pct:
            text += (
                f" Oscilla meno del {1 - pct:.0%} dei singoli titoli del Nasdaq-100."
            )
    return text


def interpret_sharpe(sharpe: float) -> str:
    if sharpe != sharpe:
        return ""
    if sharpe < 0:
        return (
            "Nel periodo il rischio preso non è stato remunerato: "
            "hai reso meno del tasso privo di rischio."
        )
    if sharpe < 0.5:
        return (
            "Rendimento corretto per il rischio modesto: sotto la fascia "
            "0.5–1 tipica di un azionario diversificato di lungo periodo."
        )
    if sharpe < 1:
        return (
            "In linea con quanto un azionario diversificato ha storicamente "
            "offerto per unità di rischio (0.5–1)."
        )
    if sharpe < 2:
        return "Sopra la norma storica: ogni unità di rischio è stata ben pagata."
    return "Eccezionale nel periodo osservato: valori così raramente persistono."


def interpret_sortino(sortino: float, sharpe: float) -> str:
    if sortino != sortino or sharpe != sharpe or sharpe == 0:
        return ""
    if sortino > sharpe * 1.25:
        return (
            "La volatilità è sbilanciata verso l'alto: le discese pesano "
            "meno delle salite (buon segno)."
        )
    if sortino < sharpe * 0.9:
        return "La volatilità è concentrata nei ribassi: le discese fanno più male."
    return "Discese e salite hanno contribuito in modo simmetrico alla volatilità."


def interpret_drawdown(drawdown: float) -> str:
    if drawdown != drawdown:
        return ""
    if drawdown > -0.10:
        return "Entro una normale correzione di mercato (fino a -10%)."
    if drawdown > -0.20:
        return "Tra una correzione (-10%) e un bear market (-20%)."
    if drawdown > -0.35:
        return "Da bear market: discese così mettono alla prova la disciplina."
    return "Drawdown severo: pochi investitori reggono discese simili senza vendere."


def interpret_beta(beta: float, benchmark: str) -> str:
    if beta != beta:
        return ""
    if beta < 0.85:
        return f"Più difensivo del {benchmark}: attenui i movimenti del mercato."
    if beta <= 1.15:
        return f"Ti muovi sostanzialmente insieme al {benchmark}."
    return f"Amplifichi i movimenti del {benchmark}: salite e discese più ripide."


def interpret_correlation(avg_correlation: float) -> str:
    if avg_correlation != avg_correlation:
        return ""
    if avg_correlation > 0.75:
        return "I titoli si muovono quasi identici: la diversificazione è solo apparente."
    if avg_correlation > 0.6:
        return "I titoli si muovono molto insieme: il beneficio di diversificare è ridotto."
    if avg_correlation > 0.3:
        return "Diversificazione nella media per un portafoglio dello stesso mercato."
    return "I titoli si muovono in modo indipendente: buona diversificazione reale."
