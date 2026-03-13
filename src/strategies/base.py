from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Tuple, Any
import pandas as pd


@dataclass
class SimulationResult:
    """Result of running a strategy simulation."""
    total_invested: float
    final_value: float
    final_cash: float
    cashflows: List[Tuple[Any, float]]
    portfolio_values: List[float]
    dates: List[Any]
    xirr_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    deployments: List[dict] = field(default_factory=list)  # Genie/Staggered chart dots
    reversal_points: List[tuple] = field(default_factory=list)  # (date, price) for Staggered


class BaseStrategy(ABC):
    """Abstract base class for all investment strategies."""

    def __init__(self, cash_bucket):
        self.cash_bucket = cash_bucket

    @abstractmethod
    def run(self, df: pd.DataFrame, initial_capital: float) -> SimulationResult:
        """Run the strategy. df has DatetimeIndex and Close column."""
        pass
