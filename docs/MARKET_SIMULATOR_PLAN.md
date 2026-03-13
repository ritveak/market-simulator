# Market Simulator - Architecture & Plan

## Overview

A financial simulation tool that compares three distinct investment philosophies using historical market data (local CSV files). Ensures a **Fair Comparison** by giving all strategies the same monthly cash inflow, with non-deployed cash earning a steady Liquid Fund interest rate.

---

## Data Format

- **Source**: Local CSV files in `resources/` folder (no API)
- **Columns**: Exactly 2 columns — `Date` and `Close`
- **Date format**: `DD/MM/YY` (e.g. 02/01/07 = 2 Jan 2007)
- **Close**: Closing price for that trading day

---

## Core Strategies

| Strategy | Logic |
|----------|-------|
| **SIP** | 100% of monthly inflow invested on the first trading day of every month |
| **The Genie** | Cash accumulates in Liquid Fund. 100% deployed at the **lowest price day** within each configurable time window (value + unit: days/weeks/months/years) |
| **Staggered Tactician** | Cash in Liquid Fund. Tranched deployment based on daily % drops from all-time high per rules table |

---

## User-Adjustable Inputs

| Variable | Widget | Info (hover) |
|----------|--------|--------------|
| Data File | Dropdown (scan `resources/**/*.csv`) | Select CSV from resources. Must have Date (DD/MM/YY) and Close columns |
| Initial Capital | number_input | Starting balance before contributions |
| Monthly Contribution | number_input | Amount added each month (same for all strategies) |
| Liquid Fund Yield (%) | number_input | Annual rate for non-deployed cash |
| Genie Window Value | number_input | Numeric value for window length |
| Genie Window Unit | selectbox (days/weeks/months/years) | Time unit for Genie deployment cycle |
| Simulation Start | date_input | Backtest start (within data range) |
| Simulation End | date_input | Backtest end (within data range) |
| Staggered Rules | data_editor | Map Market Drop % → Deployment % |

---

## Engine Logic

- **Cash Bucket**: `cash = (cash + daily_inflow) * (1 + annual_rate/252)` per trading day
- **Portfolio Value**: `units * price + remaining_cash`
- **Genie**: Find lowest-close day in each window → deploy 100% on that day

---

## Outputs

- Multi-line growth chart (Time vs Portfolio Value)
- Metrics table: Total Invested, Final Value, XIRR, Max Drawdown, Cash Balance

---

## File Structure

```
strategy/
├── app.py                 # Streamlit entry
├── requirements.txt
├── README.md
├── docs/MARKET_SIMULATOR_PLAN.md
├── resources/
│   └── nsedata/nifty/     # CSV data files
└── src/
    ├── data/loader.py     # CSV loader
    ├── engine/simulator.py, cash_bucket.py, metrics.py
    └── strategies/sip.py, genie.py, staggered.py
```
