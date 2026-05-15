"""
突破策略

基于价格突破N日高点/低点，配合成交量确认的趋势突破策略。
当价格突破N日最高价且成交量放大时产生买入信号。

适用场景: 震荡后突破、箱体突破等行情
"""

import logging

import pandas as pd
import numpy as np

from backtest.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class BreakoutStrategy(BaseStrategy):
    """突破策略

    价格突破N日高点且成交量放大时买入:
    - 收盘价突破 lookback 日最高价
    - 当日成交量 > volume_multiple * lookback 日平均成交量
    - 价格跌破 lookback 日最低价时卖出

    Attributes:
        lookback: 回溯周期（突破窗口），默认20
        volume_multiple: 成交量放大倍数阈值，默认1.5
    """

    def __init__(
        self,
        lookback: int = 20,
        volume_multiple: float = 1.5,
    ) -> None:
        """初始化突破策略

        Args:
            lookback: 突破回溯周期
            volume_multiple: 成交量放大倍数
        """
        super().__init__(
            name="突破策略",
            description=f"{lookback}日价格突破，成交量{volume_multiple}倍确认",
        )
        self.lookback: int = lookback
        self.volume_multiple: float = volume_multiple

    def validate_params(self) -> bool:
        """验证参数合法性

        Returns:
            参数是否合法
        """
        if self.lookback <= 0:
            logger.error("回溯周期必须为正整数")
            return False
        if self.volume_multiple <= 0:
            logger.error("成交量放大倍数必须为正数")
            return False
        return True

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """生成突破信号

        使用 rolling 计算N日最高价、最低价和平均成交量，
        shift(1) 确保只使用历史数据（不含当日）。

        买入条件:
        1. 当日收盘价 > 前 lookback 日的最高价
        2. 当日成交量 > volume_multiple * 前 lookback 日的平均成交量

        卖出条件:
        1. 当日收盘价 < 前 lookback 日的最低价

        Args:
            df: 行情数据

        Returns:
            信号序列: 1=买入, -1=卖出, 0=持有
        """
        # 标准化列名
        df = df.copy()
        df.columns = df.columns.str.lower()

        # 使用 shift(1) 获取前一日及之前的数据，避免未来函数
        # N日最高价（不含当日）
        prev_high = df["high"].shift(1).rolling(window=self.lookback, min_periods=self.lookback).max()
        # N日最低价（不含当日）
        prev_low = df["low"].shift(1).rolling(window=self.lookback, min_periods=self.lookback).min()
        # N日平均成交量（不含当日）
        prev_avg_volume = df["volume"].shift(1).rolling(window=self.lookback, min_periods=self.lookback).mean()

        # 初始化信号序列
        signals = pd.Series(0, index=df.index, dtype=int)

        # 突破买入条件: 收盘价突破N日高点 且 成交量放大
        breakout_buy = (
            (df["close"] > prev_high)
            & (df["volume"] > prev_avg_volume * self.volume_multiple)
        )

        # 跌破卖出条件: 收盘价跌破N日低点
        breakout_sell = df["close"] < prev_low

        # 生成信号
        signals[breakout_buy] = 1    # 突破买入
        signals[breakout_sell] = -1  # 跌破卖出

        # 数据不足区域，信号保持为0
        signals[prev_high.isna()] = 0

        return signals
