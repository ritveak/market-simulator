---
title: Ritveak's market simulator
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# Market Simulator

A financial simulation tool that compares three investment philosophies using historical market data. All strategies share the same monthly cash inflow for a fair comparison, with non-deployed cash earning a steady Liquid Fund interest rate.

## Strategies

| Strategy | Description |
|----------|-------------|
| **SIP** | 100% of monthly inflow is invested on the first trading day of every month, regardless of price. |
| **The Genie** | Cash accumulates in Liquid Fund. Within each time window (configurable: days/weeks/months/years), 100% is deployed on the day with the lowest closing price. |
| **Staggered Tactician** | Cash accumulates in Liquid Fund. Deployment happens in tranches based on daily drops from all-time high (e.g., 2% drop → deploy 10% of cash). |

## Data Format

Place CSV files in the `resources/` folder. Each file must have **exactly two columns**:

- **Date**: `DD/MM/YY` format (e.g., `02/01/07` for 2 January 2007)
- **Close**: Closing price for that trading day

Alternatively, you can upload your csv from browser as well!

## Quick Start

```bash
# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip3 install -r requirements.txt

# Run the app
streamlit run app.py
```

The app opens in your browser at `http://localhost:8501`.

## Project Structure

```
strategy/
├── app.py                 # Streamlit entry point
├── requirements.txt
├── README.md
├── docs/
│   └── MARKET_SIMULATOR_PLAN.md   # Full architecture and design
├── resources/             # Put your CSV files here
│   └── nsedata/
│       └── nifty/
│           └── nifty2007-2026.csv
└── src/
    ├── data/
    │   └── loader.py      # CSV discovery and loading
    ├── engine/
    │   ├── cash_bucket.py  # Daily compounding logic
    │   ├── metrics.py     # XIRR, max drawdown
    │   └── simulator.py   # Runs all strategies
    └── strategies/
        ├── sip.py         # SIP
        ├── genie.py       # The Genie (lowest-point deployment)
        └── staggered.py   # Staggered Tactician
```

## Input Parameters

| Parameter | Description |
|-----------|-------------|
| **Data File** | Select from dropdown – files in `resources/` |
| **Initial Capital** | Starting balance (₹) |
| **Monthly Contribution** | Amount added each month (₹) |
| **Liquid Fund Yield** | Annual % earned on non-deployed cash |
| **Genie Window** | Value + Unit (days/weeks/months/years) – deployment cycle length |
| **Simulation Dates** | Start and end for backtesting |
| **Staggered Rules** | Table: Market Drop % → Deployment % |

Each input has an info icon (?) – hover to see a short explanation.

## Outputs

- **Comparative Growth Chart**: Multi-line graph (Date vs Portfolio Value) for all three strategies
- **Performance Metrics Table**: Total Invested, Final Value, XIRR (%), Max Drawdown (%), Cash Balance

## License

MIT
