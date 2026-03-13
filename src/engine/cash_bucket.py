"""Cash bucket logic - daily compounding with monthly inflow."""
from dataclasses import dataclass
from datetime import datetime
import pandas as pd


@dataclass
class CashBucket:
    """Savings account that compounds daily at annual rate."""
    annual_rate: float  # e.g. 0.06 for 6%
    monthly_contribution: float
    
    # 252 trading days per year
    TRADING_DAYS_PER_YEAR = 252
    
    def daily_factor(self) -> float:
        return 1 + (self.annual_rate / self.TRADING_DAYS_PER_YEAR)
    
    def daily_inflow(self, trading_days_in_month: int) -> float:
        if trading_days_in_month <= 0:
            return 0
        return self.monthly_contribution / trading_days_in_month
