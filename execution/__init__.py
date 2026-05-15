"""
执行层模块

提供交易执行功能，包括模拟交易（Paper Trading）。
模拟交易器用于回测和策略验证，不涉及真实资金。
"""

from execution.paper.paper_trader import PaperTrader

__all__ = ["PaperTrader"]
