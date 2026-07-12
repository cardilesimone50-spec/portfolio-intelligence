# Portfolio Intelligence

Dashboard Python per l'analisi di portafogli azionari su dati Yahoo Finance:
rendimento/rischio in euro (Sharpe, Sortino, max drawdown, VaR, beta/alpha vs
Nasdaq-100), correlazioni, fondamentali, ottimizzazione di Markowitz con
frontiera efficiente, backtest di strategie, alert automatici, report PDF,
import CSV/Excel dal broker e salvataggio portafogli/storico analisi in SQLite
con aggiornamento incrementale dei prezzi.

## Avvio

```bash
source venv/bin/activate
streamlit run app.py                              # dashboard web
python main.py -p AAPL:0.5 -p MSFT:0.5 --period 1y  # report CLI
python fundamentals_report.py AAPL MSFT NVDA      # fondamentali CLI
python download_nasdaq100.py                      # scarica/aggiorna il database prezzi
python -m pytest                                  # test
```

## Deploy

**Streamlit Community Cloud (gratuito):** vai su [share.streamlit.io](https://share.streamlit.io),
accedi con GitHub, "Create app" → repo `portfolio-intelligence`, branch `main`,
file `app.py`. Il database prezzi si scarica dal bottone in-app alla prima visita.

**Docker:**
```bash
docker build -t portfolio-intelligence .
docker run -p 8501:8501 portfolio-intelligence
```

## Struttura

```
src/
├── data/            accesso rete (yahoo_client), database SQLite (store), validazione
├── portfolio/       tipi base, rendimenti, rischio, ottimizzazione e frontiera efficiente
├── analytics/       performance: Sharpe, Sortino, drawdown, VaR, beta/alpha
├── fundamentals/    bilanci e multipli di valutazione
├── visualization/   grafici Altair riusabili
├── cli.py           parsing argomenti CLI
└── report.py        report testuale di portafoglio
```
