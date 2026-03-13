"""The Genie - Deploy 100% at lowest price day within each time window."""
import pandas as pd
import numpy as np
from typing import Dict, Set
from .base import BaseStrategy, SimulationResult
from ..engine.cash_bucket import CashBucket


class GenieStrategy(BaseStrategy):
    """
    Cash accumulates in liquid fund. Within each configurable time window,
    deploy 100% on the day with the lowest closing price.
    """
    
    def __init__(self, cash_bucket: CashBucket, window_trading_days: int):
        super().__init__(cash_bucket)
        self.window_trading_days = max(1, window_trading_days)
    
    def run(self, df: pd.DataFrame, initial_capital: float) -> SimulationResult:
        result = SimulationResult(
            total_invested=0,
            final_value=0,
            final_cash=0,
            cashflows=[],
            portfolio_values=[],
            dates=[],
            deployments=[],
        )
        
        cash = initial_capital
        units = 0.0
        total_invested = initial_capital
        portfolio_values = []
        dates = []
        cashflows = [(df.index[0], -initial_capital)] if initial_capital > 0 else []
        
        daily_rate = self.cash_bucket.daily_factor()
        monthly_contrib = self.cash_bucket.monthly_contribution
        seen_months = set()
        
        # Pre-compute: for each window, which day index has the lowest price?
        n = len(df)
        window_size = self.window_trading_days
        deploy_days: Set[pd.Timestamp] = set()
        
        i = 0
        while i < n:
            end_i = min(i + window_size, n)
            window_df = df.iloc[i:end_i]
            if len(window_df) == 0:
                break
            lowest_idx = window_df["Close"].idxmin()
            deploy_days.add(lowest_idx)
            i = end_i
        
        for idx, row in df.iterrows():
            price = float(row["Close"])
            year_month = (idx.year, idx.month)
            # Credit full monthly contribution at start of each month
            if year_month not in seen_months:
                seen_months.add(year_month)
                cash += monthly_contrib
            cash = cash * daily_rate
            
            if idx in deploy_days and cash > 0:
                deploy = cash
                units += deploy / price
                cash = 0
                total_invested += deploy
                cashflows.append((idx, -deploy))
                result.deployments.append({
                    "date": idx,
                    "amount_deployed": deploy,
                    "portfolio_value": units * price,
                })
            
            pv = units * price + cash
            portfolio_values.append(pv)
            dates.append(idx)
        
        if len(df) > 0:
            last_date = df.index[-1]
            final_value = units * float(df.iloc[-1]["Close"]) + cash
            cashflows.append((last_date, final_value))
        
        result.total_invested = total_invested
        result.final_value = units * float(df.iloc[-1]["Close"]) + cash
        result.final_cash = cash
        result.cashflows = cashflows
        result.portfolio_values = portfolio_values
        result.dates = dates
        return result
