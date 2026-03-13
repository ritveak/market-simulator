"""Performance metrics: XIRR, Max Drawdown, etc."""
import pandas as pd
import numpy as np
from typing import List, Tuple
from datetime import datetime


def compute_xirr(cashflows: List[Tuple[datetime, float]]) -> float:
    """Compute XIRR from list of (date, amount) - negative for outflows, positive for inflows."""
    if len(cashflows) < 2:
        return 0.0
    try:
        from numpy_financial import irr
        dates = np.array([d.timestamp() for d, _ in cashflows])
        amounts = np.array([a for _, a in cashflows])
        # Normalize to daily scale for numerical stability
        base = dates.min()
        days = (dates - base) / (24 * 3600)
        # irr expects periodic cashflows; use Newton for irregular
        def npv(r):
            return sum(a / (1 + r) ** (d / 365) for d, a in zip(days, amounts))
        # Binary search for rate
        low, high = -0.99, 10.0
        for _ in range(100):
            mid = (low + high) / 2
            val = npv(mid)
            if abs(val) < 1e-6:
                return mid * 100  # as percentage
            if val > 0:
                low = mid
            else:
                high = mid
        return ((low + high) / 2) * 100
    except Exception:
        return 0.0


def compute_max_drawdown(portfolio_values: pd.Series) -> float:
    """Max drawdown as (peak - trough) / peak."""
    if len(portfolio_values) < 2:
        return 0.0
    cummax = portfolio_values.cummax()
    drawdown = (cummax - portfolio_values) / cummax.replace(0, np.nan)
    return float(drawdown.max()) if not drawdown.isna().all() else 0.0
