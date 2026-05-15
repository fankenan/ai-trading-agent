"""
回测层模块

提供完整的回测引擎、策略基类、内置策略和报告生成功能。
"""

from backtest.engine.backtest_engine import BacktestEngine, BacktestResult, Trade
from backtest.strategies.base_strategy import BaseStrategy
from backtest.strategies.ma_strategy import MAStrategy
from backtest.strategies.breakout_strategy import BreakoutStrategy
from backtest.strategies.rsi_strategy import RSIStrategy
from backtest.reports.report_generator import BacktestReportGenerator

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "Trade",
    "BaseStrategy",
    "MAStrategy",
    "BreakoutStrategy",
    "RSIStrategy",
    "BacktestReportGenerator",
]
