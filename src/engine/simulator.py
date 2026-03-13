"""Main simulation loop - runs all strategies over price data."""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..data.loader import load_price_data
from .cash_bucket import CashBucket
from .metrics import compute_xirr, compute_max_drawdown
from ..strategies.base import SimulationResult
from ..strategies.sip import SIPStrategy
from ..strategies.genie import GenieStrategy
from ..strategies.staggered import StaggeredStrategy


@dataclass
class SimulatorConfig:
    """Configuration for the simulation."""
    initial_capital: float
    monthly_contribution: float
    liquid_fund_yield_pct: float
    genie_window_value: int
    genie_window_unit: str  # days, weeks, months, years
    staggered_rules: List[Dict[str, float]]  # [{"drop_pct": 2, "deploy_pct": 10}, ...]
    staggered_drop_from: str = "ath"  # "ath" = all-time high, "last_purchase" = last deployment price
    start_date: Optional[pd.Timestamp] = None
    end_date: Optional[pd.Timestamp] = None


def _window_to_trading_days(value: int, unit: str) -> int:
    """Convert window (value + unit) to approximate trading days."""
    trading_days_per_year = 252
    if unit == "days":
        return value
    if unit == "weeks":
        return value * 5
    if unit == "months":
        return int(value * (trading_days_per_year / 12))
    if unit == "years":
        return value * trading_days_per_year
    return value * 21  # default months


def run_simulation(
    df: pd.DataFrame,
    config: SimulatorConfig
) -> Dict[str, SimulationResult]:
    """
    Run all three strategies and return results.
    df must have DatetimeIndex and 'Close' column.
    """
    # Clip to date range
    if config.start_date is not None:
        df = df[df.index >= config.start_date]
    if config.end_date is not None:
        df = df[df.index <= config.end_date]
    
    if len(df) == 0:
        return {}
    
    cash_bucket = CashBucket(
        annual_rate=config.liquid_fund_yield_pct / 100,
        monthly_contribution=config.monthly_contribution
    )
    
    genie_window_days = _window_to_trading_days(
        config.genie_window_value,
        config.genie_window_unit
    )
    
    strategies = {
        "SIP": SIPStrategy(cash_bucket),
        "The Genie": GenieStrategy(cash_bucket, genie_window_days),
        "Staggered Tactician": StaggeredStrategy(
            cash_bucket,
            config.staggered_rules,
            drop_from=config.staggered_drop_from,
        ),
    }
    
    results: Dict[str, SimulationResult] = {}
    
    for name, strategy in strategies.items():
        result = strategy.run(df, config.initial_capital)
        # Compute XIRR and max drawdown
        result.xirr_pct = compute_xirr(result.cashflows)
        result.max_drawdown_pct = compute_max_drawdown(
            pd.Series(result.portfolio_values)
        ) * 100
        results[name] = result
    
    return results
