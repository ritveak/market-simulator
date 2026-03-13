"""SIP - Standard: deploy 100% of monthly contribution on first trading day of each month."""
import pandas as pd
from typing import Dict
from .base import BaseStrategy, SimulationResult
from ..engine.cash_bucket import CashBucket


class SIPStrategy(BaseStrategy):
    """Deploy exactly monthly_contribution on first trading day of each month (constant, independent of liquid fund yield)."""
    
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
        
        # Group by year-month to find first trading day of each month
        df_reset = df.reset_index()
        df_reset["ym"] = df_reset["Date"].dt.to_period("M")
        first_days = df_reset.groupby("ym").first().index
        
        first_days_set = set(
            df_reset[df_reset["ym"].isin(first_days)]["Date"].tolist()
        )
        # Build set of dates that are first trading day of month
        first_day_dates = set()
        for idx in df.index:
            # Check if this is first occurrence in its month
            year_month = (idx.year, idx.month)
            if year_month not in getattr(self, "_seen_months", {}):
                if not hasattr(self, "_seen_months"):
                    self._seen_months = {}
                self._seen_months[year_month] = idx
                first_day_dates.add(idx)
        
        # Actually we need to track per-month
        seen_months = set()
        monthly_contrib = self.cash_bucket.monthly_contribution

        for i, (idx, row) in enumerate(df.iterrows()):
            price = float(row["Close"])
            year_month = (idx.year, idx.month)

            # First trading day of month? Deploy exactly monthly_contribution (constant, independent of liquid fund yield)
            is_first = year_month not in seen_months
            if is_first:
                seen_months.add(year_month)
                deploy = monthly_contrib
                if i == 0 and initial_capital > 0:
                    deploy += initial_capital
                if deploy > 0:
                    units += deploy / price
                    cash = 0
                    total_invested += deploy
                    cashflows.append((idx, -deploy))
                    result.deployments.append({
                        "date": idx,
                        "amount_deployed": deploy,
                        "portfolio_value": units * price + cash,
                    })
            
            pv = units * price + cash
            portfolio_values.append(pv)
            dates.append(idx)
        
        # Final cashflow
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
