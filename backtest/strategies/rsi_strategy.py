"""
RSI 策略

基于相对强弱指标（RSI）的超买超卖反转策略。
当 RSI 低于超卖阈值时买入，高于超买阈值时卖出。

适用场景: 震荡市、均值回归行情
"""

import logging

import pandas as pd
import numpy as np

from backtest.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class RSIStrategy(BaseStrategy):
    """RSI 策略

    基于 RSI 指标的超买超卖策略:
    - RSI 低于 oversold（超卖区）-> 买入信号
    - RSI 高于 overbought（超买区）-> 卖出信号

    Attributes:
        period: RSI 计算周期，默认14
        oversold: 超卖阈值，默认30
        overbought: 超买阈值，默认70
    """

    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
    ) -> None:
        """初始化 RSI 策略

        Args:
            period: RSI 计算周期
            oversold: 超卖阈值（低于此值产生买入信号）
            overbought: 超买阈值（高于此值产生卖出信号）
        """
        super().__init__(
            name="RSI策略",
            description=f"RSI({period}) 超卖({oversold})买入，超买({overbought})卖出",
        )
        self.period: int = period
        self.oversold: float = oversold
        self.overbought: float = overbought

    def validate_params(self) -> bool:
        """验证参数合法性

        Returns:
            参数是否合法
        """
        if self.period <= 0:
            logger.error("RSI周期必须为正整数")
            return False
        if self.oversold >= self.overbought:
            logger.error("超卖阈值必须小于超买阈值")
            return False
        if not (0 < self.oversold < 100) or not (0 < self.overbought < 100):
            logger.error("超买超卖阈值必须在 (0, 100) 范围内")
            return False
        return True

    def _calculate_rsi(self, series: pd.Series) -> pd.Series:
        """计算 RSI 指标

        使用 EWM（指数加权移动平均）方式计算 RSI，
        与常见行情软件的计算方式一致。

        Args:
            series: 收盘价序列

        Returns:
            RSI 值序列（0-100）
        """
        # 计算价格变动
        delta = series.diff()

        # 分离涨跌
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        # 使用 EWM 计算平均涨跌幅
        avg_gain = gain.ewm(alpha=1.0 / self.period, min_periods=self.period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / self.period, min_periods=self.period, adjust=False).mean()

        # 计算 RS 和 RSI
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))

        return rsi

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """生成 RSI 信号

        计算 RSI 指标后:
        - RSI 从上方穿越超卖阈值（进入超卖区）-> 买入信号
        - RSI 从下方穿越超买阈值（进入超买区）-> 卖出信号

        使用 shift(1) 确保不使用未来数据。

        Args:
            df: 行情数据

        Returns:
            信号序列: 1=买入, -1=卖出, 0=持有
        """
        # 标准化列名
        df = df.copy()
        df.columns = df.columns.str.lower()

        # 计算 RSI
        rsi = self._calculate_rsi(df["close"])

        # 使用 shift(1) 获取前一日 RSI，避免未来函数
        rsi_prev = rsi.shift(1)

        # 初始化信号序列
        signals = pd.Series(0, index=df.index, dtype=int)

        # 买入条件: 前一日 RSI >= oversold，当日 RSI < oversold（进入超卖区）
        oversold_enter = (rsi_prev >= self.oversold) & (rsi < self.oversold)

        # 卖出条件: 前一日 RSI <= overbought，当日 RSI > overbought（进入超买区）
        overbought_enter = (rsi_prev <= self.overbought) & (rsi > self.overbought)

        # 生成信号
        signals[oversold_enter] = 1    # 超卖买入
        signals[overbought_enter] = -1  # 超买卖出

        # RSI 尚未计算完成的区域，信号保持为0
        signals[rsi.isna()] = 0

        return signals
