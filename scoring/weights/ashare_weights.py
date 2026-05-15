"""
A股评分权重配置

根据文档第12章"A股进阶：政策理解优先"，A股评分权重与加密市场有显著差异：
- 政策/事件权重最高（35-40%）
- 资金流向重要（20-25%）
- 情绪权重较低（10%）
- 加入回测有效性评分（10%）
"""

from typing import Dict

# A股默认权重配置
ASHARE_DEFAULT_WEIGHTS: Dict[str, float] = {
    "event_policy": 0.35,    # 政策/事件评分（最重要）
    "sentiment": 0.10,       # 市场情绪（A股情绪噪音多，权重降低）
    "kline_structure": 0.15, # K线结构
    "technical": 0.10,       # 技术指标（A股技术有效性较低）
    "funding": 0.20,         # 资金流向（北向资金/主力资金）
    "backtest_validity": 0.10,  # 回测有效性（A股策略易失效）
}

# 政策驱动型配置（适合重大政策发布期）
ASHARE_POLICY_DRIVEN: Dict[str, float] = {
    "event_policy": 0.45,
    "sentiment": 0.05,
    "kline_structure": 0.10,
    "technical": 0.05,
    "funding": 0.25,
    "backtest_validity": 0.10,
}

# 价值投资型配置（适合基本面分析）
ASHARE_VALUE_INVESTING: Dict[str, float] = {
    "event_policy": 0.25,
    "sentiment": 0.10,
    "kline_structure": 0.15,
    "technical": 0.10,
    "funding": 0.25,
    "backtest_validity": 0.15,
}

# 短线交易型配置
ASHARE_SHORT_TERM: Dict[str, float] = {
    "event_policy": 0.30,
    "sentiment": 0.15,
    "kline_structure": 0.20,
    "technical": 0.15,
    "funding": 0.15,
    "backtest_validity": 0.05,
}
