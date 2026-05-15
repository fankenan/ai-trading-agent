"""
均线趋势策略

基于快慢均线交叉的趋势跟踪策略。
当快线上穿慢线时产生买入信号，快线下穿慢线时产生卖出信号。

适用场景: 趋势明显的市场环境
"""

import logging
from typing import Optional

import pandas as pd
import numpy as np

from backtest.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class MAStrategy(BaseStrategy):
    """均线趋势策略

    使用快慢均线交叉判断趋势方向:
    - 快线上穿慢线（金叉）-> 买入信号
    - 快线下穿慢线（死叉）-> 卖出信号

    Attributes:
        fast_period: 快线周期，默认5
        slow_period: 慢线周期，默认20
    """

    def __init__(
        self,
        fast_period: int = 5,
        slow_period: int = 20,
    ) -> None:
        """初始化均线策略

        Args:
            fast_period: 快速均线周期
            slow_period: 慢速均线周期
        """
        super().__init__(
            name="均线趋势策略",
            description=f"MA{fast_period}/{slow_period} 金叉买入，死叉卖出",
        )
        self.fast_period: int = fast_period
        self.slow_period: int = slow_period

    def validate_params(self) -> bool:
        """验证参数合法性

        Returns:
            参数是否合法
        """
        if self.fast_period <= 0 or self.slow_period <= 0:
            logger.error("均线周期必须为正整数")
            return False
        if self.fast_period >= self.slow_period:
            logger.error("快线周期必须小于慢线周期")
            return False
        return True

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """生成均线交叉信号

        使用 rolling 计算均线，shift(1) 确保不使用未来数据。
        金叉（快线从下方穿越慢线）产生买入信号，
        死叉（快线从上方穿越慢线）产生卖出信号。

        Args:
            df: 行情数据

        Returns:
            信号序列: 1=买入, -1=卖出, 0=持有
        """
        # 标准化列名
        df = df.copy()
        df.columns = df.columns.str.lower()

        # 计算均线（rolling 天然避免未来函数）
        fast_ma = df["close"].rolling(window=self.fast_period, min_periods=self.fast_period).mean()
        slow_ma = df["close"].rolling(window=self.slow_period, min_periods=self.slow_period).mean()

        # 使用 shift(1) 获取前一日的均线值，避免使用当日完整数据
        fast_ma_prev = fast_ma.shift(1)
        slow_ma_prev = slow_ma.shift(1)

        # 初始化信号序列
        signals = pd.Series(0, index=df.index, dtype=int)

        # 金叉条件: 昨日快线 <= 慢线，今日快线 > 慢线
        golden_cross = (fast_ma_prev <= slow_ma_prev) & (fast_ma > slow_ma)

        # 死叉条件: 昨日快线 >= 慢线，今日快线 < 慢线
        death_cross = (fast_ma_prev >= slow_ma_prev) & (fast_ma < slow_ma)

        # 生成信号
        signals[golden_cross] = 1   # 金叉买入
        signals[death_cross] = -1   # 死叉卖出

        # 慢线尚未计算完成的区域，信号保持为0
        signals[slow_ma.isna()] = 0

        return signals
