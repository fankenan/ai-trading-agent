"""
技术指标评分模块

基于多种技术指标对市场进行综合评分。
使用的技术指标包括：
  - MA（移动平均线）：判断趋势方向
  - RSI（相对强弱指标）：判断超买超卖
  - MACD（指数平滑异同移动平均线）：判断趋势强度和转折
  - 布林带（Bollinger Bands）：判断波动率和价格位置

评分范围：0-100，50为中性。
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger


class TechnicalScorer:
    """技术指标评分器

    综合分析多种技术指标，生成0-100的综合技术评分。
    各指标独立评分后加权汇总。

    Attributes:
        ma_weight: MA指标权重
        rsi_weight: RSI指标权重
        macd_weight: MACD指标权重
        bollinger_weight: 布林带指标权重
    """

    def __init__(
        self,
        ma_weight: float = 0.30,
        rsi_weight: float = 0.25,
        macd_weight: float = 0.25,
        bollinger_weight: float = 0.20,
    ) -> None:
        """初始化技术指标评分器

        Args:
            ma_weight: MA指标权重（默认0.30）
            rsi_weight: RSI指标权重（默认0.25）
            macd_weight: MACD指标权重（默认0.25）
            bollinger_weight: 布林带指标权重（默认0.20）
        """
        total_weight = ma_weight + rsi_weight + macd_weight + bollinger_weight
        self.ma_weight = ma_weight / total_weight
        self.rsi_weight = rsi_weight / total_weight
        self.macd_weight = macd_weight / total_weight
        self.bollinger_weight = bollinger_weight / total_weight

    def score(self, df: pd.DataFrame) -> Dict[str, Any]:
        """根据技术指标综合评分

        分析DataFrame中的价格数据，计算各项技术指标并生成综合评分。

        Args:
            df: 包含价格数据的DataFrame，至少需要 'close' 列。
                建议包含 'open', 'high', 'low', 'volume' 列以获得更准确的评分。

        Returns:
            包含以下字段的字典：
            - score: 综合技术评分（0-100）
            - details: 评分详情描述
            - indicator_scores: 各指标独立评分
            - signals: 技术信号列表
        """
        if df is None or df.empty or len(df) < 20:
            logger.warning("数据不足，无法进行技术指标评分")
            return {
                "score": 50.0,
                "details": "数据不足（少于20根K线），无法可靠计算技术指标",
                "indicator_scores": {},
                "signals": ["数据不足"],
            }

        signals: list = []

        # 计算各指标评分
        ma_score, ma_detail = self._score_ma(df)
        rsi_score, rsi_detail = self._score_rsi(df)
        macd_score, macd_detail = self._score_macd(df)
        bollinger_score, bollinger_detail = self._score_bollinger(df)

        # 收集信号
        if ma_score > 65:
            signals.append("MA: 多头排列")
        elif ma_score < 35:
            signals.append("MA: 空头排列")

        if rsi_score > 70:
            signals.append("RSI: 超买区域")
        elif rsi_score < 30:
            signals.append("RSI: 超卖区域")

        if macd_score > 65:
            signals.append("MACD: 金叉/多头")
        elif macd_score < 35:
            signals.append("MACD: 死叉/空头")

        if bollinger_score > 65:
            signals.append("布林带: 价格触及上轨")
        elif bollinger_score < 35:
            signals.append("布林带: 价格触及下轨")

        # 加权综合评分
        total_score: float = (
            ma_score * self.ma_weight
            + rsi_score * self.rsi_weight
            + macd_score * self.macd_weight
            + bollinger_score * self.bollinger_weight
        )

        indicator_scores: Dict[str, float] = {
            "ma": round(ma_score, 1),
            "rsi": round(rsi_score, 1),
            "macd": round(macd_score, 1),
            "bollinger": round(bollinger_score, 1),
        }

        details: str = (
            f"MA评分{ma_score:.0f}({ma_detail}), "
            f"RSI评分{rsi_score:.0f}({rsi_detail}), "
            f"MACD评分{macd_score:.0f}({macd_detail}), "
            f"布林带评分{bollinger_score:.0f}({bollinger_detail})"
        )

        logger.info(f"技术指标评分完成: {total_score:.1f}分")
        logger.debug(f"各指标评分: {indicator_scores}")

        return {
            "score": round(total_score, 1),
            "details": details,
            "indicator_scores": indicator_scores,
            "signals": signals,
        }

    def _score_ma(self, df: pd.DataFrame) -> tuple:
        """MA（移动平均线）评分

        通过短期均线与长期均线的关系判断趋势方向。

        Args:
            df: 包含 'close' 列的DataFrame

        Returns:
            (评分, 描述) 元组
        """
        try:
            close = df["close"]
            ma5 = close.rolling(window=5).mean()
            ma10 = close.rolling(window=10).mean()
            ma20 = close.rolling(window=20).mean()
            ma60 = close.rolling(window=min(60, len(df))).mean()

            current_price = close.iloc[-1]
            current_ma5 = ma5.iloc[-1]
            current_ma10 = ma10.iloc[-1]
            current_ma20 = ma20.iloc[-1]
            current_ma60 = ma60.iloc[-1]

            score = 50.0  # 基准分

            # 价格在均线之上加分
            if current_price > current_ma5:
                score += 5
            if current_price > current_ma10:
                score += 10
            if current_price > current_ma20:
                score += 10
            if current_price > current_ma60:
                score += 10

            # 均线多头排列加分
            if current_ma5 > current_ma10 > current_ma20:
                score += 15
                detail = "多头排列"
            elif current_ma5 < current_ma10 < current_ma20:
                score -= 15
                detail = "空头排列"
            else:
                detail = "均线交织"

            return min(max(score, 0), 100), detail

        except Exception as e:
            logger.error(f"MA评分计算失败: {e}")
            return 50.0, "计算失败"

    def _score_rsi(self, df: pd.DataFrame) -> tuple:
        """RSI（相对强弱指标）评分

        RSI低于30为超卖（看多信号），高于70为超买（看空信号）。

        Args:
            df: 包含 'close' 列的DataFrame

        Returns:
            (评分, 描述) 元组
        """
        try:
            close = df["close"]
            delta = close.diff()

            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)

            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()

            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]

            if pd.isna(current_rsi):
                return 50.0, "数据不足"

            # RSI评分逻辑：超卖区域高分（逆向思维），超买区域低分
            if current_rsi <= 20:
                score = 85.0
                detail = "极度超卖"
            elif current_rsi <= 30:
                score = 75.0
                detail = "超卖"
            elif current_rsi <= 40:
                score = 60.0
                detail = "偏弱"
            elif current_rsi <= 60:
                score = 50.0
                detail = "中性"
            elif current_rsi <= 70:
                score = 40.0
                detail = "偏强"
            elif current_rsi <= 80:
                score = 25.0
                detail = "超买"
            else:
                score = 15.0
                detail = "极度超买"

            return score, detail

        except Exception as e:
            logger.error(f"RSI评分计算失败: {e}")
            return 50.0, "计算失败"

    def _score_macd(self, df: pd.DataFrame) -> tuple:
        """MACD（指数平滑异同移动平均线）评分

        通过MACD线、信号线和柱状图判断趋势强度和转折点。

        Args:
            df: 包含 'close' 列的DataFrame

        Returns:
            (评分, 描述) 元组
        """
        try:
            close = df["close"]
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            histogram = macd_line - signal_line

            current_macd = macd_line.iloc[-1]
            current_signal = signal_line.iloc[-1]
            current_hist = histogram.iloc[-1]
            prev_hist = histogram.iloc[-2] if len(histogram) >= 2 else 0

            score = 50.0

            # MACD线在信号线上方（金叉状态）
            if current_macd > current_signal:
                score += 15
                if current_hist > prev_hist:
                    score += 10  # 柱状图放大，趋势加强
                    detail = "金叉加强"
                else:
                    detail = "金叉减弱"
            else:
                score -= 15
                if current_hist < prev_hist:
                    score -= 10  # 柱状图放大，趋势加强
                    detail = "死叉加强"
                else:
                    detail = "死叉减弱"

            # MACD柱状图由负转正（金叉信号）
            if prev_hist < 0 and current_hist > 0:
                score += 15
                detail = "金叉形成"
            elif prev_hist > 0 and current_hist < 0:
                score -= 15
                detail = "死叉形成"

            # 零轴判断
            if current_macd > 0:
                score += 5
            else:
                score -= 5

            return min(max(score, 0), 100), detail

        except Exception as e:
            logger.error(f"MACD评分计算失败: {e}")
            return 50.0, "计算失败"

    def _score_bollinger(self, df: pd.DataFrame) -> tuple:
        """布林带（Bollinger Bands）评分

        通过价格在布林带中的位置判断超买超卖和波动率。

        Args:
            df: 包含 'close' 列的DataFrame

        Returns:
            (评分, 描述) 元组
        """
        try:
            close = df["close"]
            ma20 = close.rolling(window=20).mean()
            std20 = close.rolling(window=20).std()
            upper_band = ma20 + 2 * std20
            lower_band = ma20 - 2 * std20

            current_price = close.iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            current_ma = ma20.iloc[-1]

            if pd.isna(current_upper) or pd.isna(current_lower):
                return 50.0, "数据不足"

            # 计算价格在布林带中的位置百分比（0=下轨，100=上轨）
            band_width = current_upper - current_lower
            if band_width == 0:
                return 50.0, "布林带宽度为零"

            position = (current_price - current_lower) / band_width * 100

            # 逆向思维：触及下轨时高分（超卖），触及上轨时低分（超买）
            if position <= 5:
                score = 80.0
                detail = "触及下轨"
            elif position <= 20:
                score = 70.0
                detail = "接近下轨"
            elif position <= 40:
                score = 55.0
                detail = "偏下方"
            elif position <= 60:
                score = 50.0
                detail = "中轨附近"
            elif position <= 80:
                score = 40.0
                detail = "偏上方"
            elif position <= 95:
                score = 30.0
                detail = "接近上轨"
            else:
                score = 20.0
                detail = "触及上轨"

            return score, detail

        except Exception as e:
            logger.error(f"布林带评分计算失败: {e}")
            return 50.0, "计算失败"
