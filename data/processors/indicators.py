# -*- coding: utf-8 -*-
"""
技术指标计算器

基于ta库提供常用的技术分析指标计算功能，包括移动均线、RSI、MACD、
布林带、ATR等。所有方法均接受标准K线DataFrame并返回添加了指标列的新DataFrame。
"""

from typing import List, Optional

import pandas as pd
import ta
from loguru import logger


class TechnicalIndicators:
    """技术指标计算器

    提供常用的技术分析指标计算方法，所有方法均基于收盘价和成交量计算。
    输入DataFrame需包含标准列: [timestamp, open, high, low, close, volume]。

    使用方式:
        ti = TechnicalIndicators()
        df = ti.add_all_indicators(df)
    """

    def add_ma(
        self,
        df: pd.DataFrame,
        periods: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """添加简单移动均线(SMA)

        计算指定周期的简单移动平均线，并将结果作为新列添加到DataFrame中。
        列名格式为: ma_{period}，如 ma_5, ma_10, ma_20, ma_60。

        Args:
            df: K线数据DataFrame，需包含 "close" 列
            periods: 移动均线周期列表，默认 [5, 10, 20, 60]

        Returns:
            添加了移动均线列的DataFrame
        """
        if periods is None:
            periods = [5, 10, 20, 60]

        if df is None or df.empty:
            logger.warning("添加MA跳过: DataFrame为空")
            return df

        logger.debug("计算移动均线: periods={}", periods)

        for period in periods:
            col_name: str = f"ma_{period}"
            df[col_name] = ta.trend.sma_indicator(
                df["close"], window=period
            )
            logger.debug("MA({}) 计算完成", period)

        return df

    def add_ema(
        self,
        df: pd.DataFrame,
        periods: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """添加指数移动均线(EMA)

        计算指定周期的指数移动平均线，并将结果作为新列添加到DataFrame中。
        列名格式为: ema_{period}，如 ema_12, ema_26。

        Args:
            df: K线数据DataFrame，需包含 "close" 列
            periods: EMA周期列表，默认 [12, 26]

        Returns:
            添加了EMA列的DataFrame
        """
        if periods is None:
            periods = [12, 26]

        if df is None or df.empty:
            logger.warning("添加EMA跳过: DataFrame为空")
            return df

        logger.debug("计算指数移动均线: periods={}", periods)

        for period in periods:
            col_name = f"ema_{period}"
            df[col_name] = ta.trend.ema_indicator(
                df["close"], window=period
            )
            logger.debug("EMA({}) 计算完成", period)

        return df

    def add_rsi(
        self,
        df: pd.DataFrame,
        period: int = 14,
    ) -> pd.DataFrame:
        """添加相对强弱指标(RSI)

        计算RSI指标，用于判断市场超买超卖状态。
        RSI > 70 通常视为超买，RSI < 30 通常视为超卖。

        Args:
            df: K线数据DataFrame，需包含 "close" 列
            period: RSI计算周期，默认14

        Returns:
            添加了 "rsi" 列的DataFrame
        """
        if df is None or df.empty:
            logger.warning("添加RSI跳过: DataFrame为空")
            return df

        logger.debug("计算RSI: period={}", period)

        df["rsi"] = ta.momentum.rsi(df["close"], window=period)
        return df

    def add_macd(
        self,
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> pd.DataFrame:
        """添加MACD指标

        计算MACD（移动平均收敛/发散）指标，包含：
        - macd: MACD线（快线EMA - 慢线EMA）
        - macd_signal: 信号线（MACD线的EMA）
        - macd_hist: MACD柱状图（MACD线 - 信号线）

        Args:
            df: K线数据DataFrame，需包含 "close" 列
            fast: 快线EMA周期，默认12
            slow: 慢线EMA周期，默认26
            signal: 信号线EMA周期，默认9

        Returns:
            添加了 macd, macd_signal, macd_hist 列的DataFrame
        """
        if df is None or df.empty:
            logger.warning("添加MACD跳过: DataFrame为空")
            return df

        logger.debug(
            "计算MACD: fast={}, slow={}, signal={}", fast, slow, signal
        )

        macd_obj = ta.trend.MACD(
            df["close"],
            window_fast=fast,
            window_slow=slow,
            window_sign=signal,
        )
        df["macd"] = macd_obj.macd()
        df["macd_signal"] = macd_obj.macd_signal()
        df["macd_hist"] = macd_obj.macd_diff()

        return df

    def add_bollinger(
        self,
        df: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> pd.DataFrame:
        """添加布林带指标

        计算布林带（Bollinger Bands），包含：
        - bb_upper: 布林带上轨（中轨 + std_dev * 标准差）
        - bb_middle: 布林带中轨（SMA）
        - bb_lower: 布林带下轨（中轨 - std_dev * 标准差）

        Args:
            df: K线数据DataFrame，需包含 "close" 列
            period: 布林带周期，默认20
            std_dev: 标准差倍数，默认2.0

        Returns:
            添加了 bb_upper, bb_middle, bb_lower 列的DataFrame
        """
        if df is None or df.empty:
            logger.warning("添加布林带跳过: DataFrame为空")
            return df

        logger.debug(
            "计算布林带: period={}, std_dev={}", period, std_dev
        )

        bb_obj = ta.volatility.BollingerBands(
            df["close"],
            window=period,
            window_dev=std_dev,
        )
        df["bb_upper"] = bb_obj.bollinger_hband()
        df["bb_middle"] = bb_obj.bollinger_mavg()
        df["bb_lower"] = bb_obj.bollinger_lband()

        return df

    def add_atr(
        self,
        df: pd.DataFrame,
        period: int = 14,
    ) -> pd.DataFrame:
        """添加真实波幅(ATR)

        计算ATR（Average True Range），用于衡量市场波动性。
        ATR值越大表示市场波动越剧烈。

        Args:
            df: K线数据DataFrame，需包含 "high", "low", "close" 列
            period: ATR计算周期，默认14

        Returns:
            添加了 "atr" 列的DataFrame
        """
        if df is None or df.empty:
            logger.warning("添加ATR跳过: DataFrame为空")
            return df

        logger.debug("计算ATR: period={}", period)

        df["atr"] = ta.volatility.average_true_range(
            df["high"],
            df["low"],
            df["close"],
            window=period,
        )
        return df

    def add_volume_ma(
        self,
        df: pd.DataFrame,
        periods: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """添加成交量移动均线

        计算指定周期的成交量简单移动平均线。
        列名格式为: vol_ma_{period}，如 vol_ma_5, vol_ma_20。

        Args:
            df: K线数据DataFrame，需包含 "volume" 列
            periods: 成交量均线周期列表，默认 [5, 20]

        Returns:
            添加了成交量均线列的DataFrame
        """
        if periods is None:
            periods = [5, 20]

        if df is None or df.empty:
            logger.warning("添加成交量均线跳过: DataFrame为空")
            return df

        logger.debug("计算成交量均线: periods={}", periods)

        for period in periods:
            col_name = f"vol_ma_{period}"
            df[col_name] = ta.trend.sma_indicator(
                df["volume"], window=period
            )
            logger.debug("成交量MA({}) 计算完成", period)

        return df

    def add_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """一次性添加所有技术指标

        依次调用所有指标计算方法，将全部技术指标添加到DataFrame中。
        包含: MA, EMA, RSI, MACD, 布林带, ATR, 成交量均线。

        Args:
            df: K线数据DataFrame，需包含标准列:
                [timestamp, open, high, low, close, volume]

        Returns:
            添加了所有技术指标列的DataFrame
        """
        if df is None or df.empty:
            logger.warning("添加所有指标跳过: DataFrame为空")
            return df

        required_columns = ["open", "high", "low", "close", "volume"]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValueError(
                f"DataFrame缺少必要的列: {missing}，"
                f"需要列: {required_columns}"
            )

        logger.info("开始计算所有技术指标, 数据记录数={}", len(df))

        # 移动均线
        df = self.add_ma(df, periods=[5, 10, 20, 60])

        # 指数移动均线
        df = self.add_ema(df, periods=[12, 26])

        # RSI
        df = self.add_rsi(df, period=14)

        # MACD
        df = self.add_macd(df, fast=12, slow=26, signal=9)

        # 布林带
        df = self.add_bollinger(df, period=20, std_dev=2.0)

        # ATR
        df = self.add_atr(df, period=14)

        # 成交量均线
        df = self.add_volume_ma(df, periods=[5, 20])

        # 统计新增的指标列
        indicator_columns = [
            col for col in df.columns if col not in required_columns + ["timestamp"]
        ]
        logger.info(
            "所有技术指标计算完成, 新增指标列数={}, 指标: {}",
            len(indicator_columns),
            indicator_columns,
        )

        return df
