# -*- coding: utf-8 -*-
"""
Agent模块

包含主控制器：
- TradingAgent: 加密市场交易Agent
- AShareAgent: A股交易Agent
"""

def __getattr__(name):
    """延迟导入"""
    if name == "TradingAgent":
        from agent.trading_agent import TradingAgent
        return TradingAgent
    elif name == "AShareAgent":
        from agent.ashare_agent import AShareAgent
        return AShareAgent
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["TradingAgent", "AShareAgent"]
