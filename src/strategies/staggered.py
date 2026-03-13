"""Staggered Tactician - Tiered deployment based on daily drop %."""
import pandas as pd
from typing import Dict, List
from .base import BaseStrategy, SimulationResult
from ..engine.cash_bucket import CashBucket


class StaggeredStrategy(BaseStrategy):
    """
    Deploy a percentage of cash when market drops by X%.
    Rules: [{drop_pct: 2, deploy_pct: 10}, {drop_pct: 5, deploy_pct: 20}, ...]
    Highest matching rule applies per day.
    """
    
    def __init__(
        self,
        cash_bucket: CashBucket,
        rules: List[Dict[str, float]],
        drop_from: str = "ath",  # "ath" = all-time high, "last_purchase" = last deployment price
    ):
        super().__init__(cash_bucket)
        # Sort by drop_pct descending so we pick highest matching
        self.rules = sorted(
            [r for r in rules if "drop_pct" in r and "deploy_pct" in r],
            key=lambda x: x["drop_pct"],
            reverse=True
        )
        self.drop_from = drop_from if drop_from in ("ath", "last_purchase") else "ath"
    
    def _get_deploy_pct(self, drop_pct: float) -> float:
        """Return deployment % for given drop, or 0 if no rule matches."""
        for r in self.rules:
            if drop_pct >= r["drop_pct"]:
                return r["deploy_pct"] / 100
        return 0.0
    
    def run(self, df: pd.DataFrame, initial_capital: float) -> SimulationResult:
        result = SimulationResult(
            total_invested=0,
            final_value=0,
            final_cash=0,
            cashflows=[],
            portfolio_values=[],
            dates=[]
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
        reversal_price = None  # All-time high; drop % measured from this (or last purchase)
        reversal_points = []  # (date, price) for chart - new highs on price line
        last_purchase_price = None  # Price at last deployment; used when drop_from=="last_purchase"
        
        for idx, row in df.iterrows():
            price = float(row["Close"])
            year_month = (idx.year, idx.month)
            # Credit full monthly contribution at start of each month
            if year_month not in seen_months:
                seen_months.add(year_month)
                cash += monthly_contrib
            cash = cash * daily_rate
            
            # All-time high: track when price goes strictly above previous high
            if reversal_price is None:
                reversal_price = price
                reversal_points.append((idx, price))
            elif price > reversal_price:
                reversal_price = price  # New high
                reversal_points.append((idx, price))
            
            # Reference for drop %: ATH or last purchase (when drop_from=="last_purchase")
            if self.drop_from == "last_purchase":
                # Use last_purchase when price hasn't rallied above it; else use ATH (market made new high)
                if last_purchase_price is None:
                    ref_price = reversal_price  # First deployment uses ATH
                elif price <= last_purchase_price:
                    ref_price = last_purchase_price  # Still in dip or flat—avoid repeated deployment
                else:
                    ref_price = reversal_price  # Price rallied above last purchase—use ATH
            else:
                ref_price = reversal_price
            
            drop_pct = 0.0
            if ref_price > 0 and price < ref_price:
                drop_pct = (ref_price - price) / ref_price * 100
            
            deploy_pct = self._get_deploy_pct(drop_pct)  # as percentage
            if deploy_pct > 0 and cash > 0:
                total_before = cash
                deploy = cash * deploy_pct
                units += deploy / price
                cash -= deploy
                total_invested += deploy
                if self.drop_from == "last_purchase":
                    last_purchase_price = price  # Update reference for next deployment
                cashflows.append((idx, -deploy))
                pct_deployed = deploy_pct * 100
                pct_remaining = 100 - pct_deployed
                result.deployments.append({
                    "date": idx,
                    "amount_deployed": deploy,
                    "amount_remaining": cash,
                    "total_cash_before": total_before,
                    "deploy_pct": pct_deployed,
                    "remaining_pct": pct_remaining,
                    "portfolio_value": units * price + cash,
                    "drop_from_reversal_pct": round(drop_pct, 2),
                    "no_cash_left": total_before < 1,
                })
            elif deploy_pct > 0 and cash < 1:
                # Rules matched but no meaningful cash (0 or trivial) - show as red cross
                result.deployments.append({
                    "date": idx,
                    "amount_deployed": 0,
                    "amount_remaining": cash,
                    "total_cash_before": cash,
                    "deploy_pct": 0,
                    "remaining_pct": 100,
                    "portfolio_value": units * price + cash,
                    "drop_from_reversal_pct": round(drop_pct, 2),
                    "no_cash_left": True,
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
        result.reversal_points = reversal_points
        return result
