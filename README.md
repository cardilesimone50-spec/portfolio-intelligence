# Portfolio Intelligence

Dashboard Python per l'analisi di portafogli azionari su dati Yahoo Finance:
rendimento/rischio in euro, correlazioni, fondamentali, classifiche Nasdaq-100
e ottimizzazione dei pesi (Markowitz long-only).

## Avvio

```bash
source venv/bin/activate
streamlit run app.py                              # dashboard web
python main.py -p AAPL:0.5 -p MSFT:0.5 --period 1y  # report CLI
python fundamentals_report.py AAPL MSFT NVDA      # fondamentali CLI
python download_nasdaq100.py                      # scarica/aggiorna il database prezzi
python -m pytest                                  # test
```

## Struttura

```
src/
├── data/            accesso rete (yahoo_client), cache CSV, validazione input
├── portfolio/       tipi base, rendimenti, rischio, ottimizzazione pesi
├── analytics/       metriche di performance (Sharpe, drawdown, statistiche annualizzate)
├── fundamentals/    bilanci e multipli di valutazione
├── visualization/   grafici Altair riusabili
├── cli.py           parsing argomenti CLI
└── report.py        report testuale di portafoglio
```
