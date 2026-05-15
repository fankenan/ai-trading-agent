"""
默认权重配置

定义评分系统中各模块的默认权重配置。
权重总和应为1.0，系统会在初始化时自动归一化。

权重说明：
  - event: 事件评分权重（反映突发事件和新闻对市场的影响）
  - sentiment: 情绪评分权重（反映市场整体情绪状态）
  - technical: 技术指标评分权重（反映技术面分析结果）
  - kline: K线结构评分权重（反映价格行为和量价关系）
"""

from typing import Dict

# 默认模块权重配置
DEFAULT_WEIGHTS: Dict[str, float] = {
    "event": 0.25,      # 事件评分权重
    "sentiment": 0.15,   # 情绪评分权重
    "technical": 0.35,   # 技术指标评分权重
    "kline": 0.25,       # K线结构评分权重
}

# 保守型权重配置（更关注风控，降低事件权重）
CONSERVATIVE_WEIGHTS: Dict[str, float] = {
    "event": 0.15,
    "sentiment": 0.15,
    "technical": 0.40,
    "kline": 0.30,
}

# 激进型权重配置（更关注事件驱动机会）
AGGRESSIVE_WEIGHTS: Dict[str, float] = {
    "event": 0.35,
    "sentiment": 0.20,
    "technical": 0.25,
    "kline": 0.20,
}

# 新闻驱动型权重配置
NEWS_DRIVEN_WEIGHTS: Dict[str, float] = {
    "event": 0.40,
    "sentiment": 0.25,
    "technical": 0.20,
    "kline": 0.15,
}

# 技术分析型权重配置
TECHNICAL_WEIGHTS: Dict[str, float] = {
    "event": 0.10,
    "sentiment": 0.10,
    "technical": 0.50,
    "kline": 0.30,
}
