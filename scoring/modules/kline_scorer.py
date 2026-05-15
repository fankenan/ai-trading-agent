"""
K线结构评分模块

基于K线形态、趋势方向、成交量和突破情况进行综合评分。
主要分析维度：
  - 趋势判断：通过近期高低点判断上升/下降/震荡趋势
  - 成交量分析：量价关系，放量/缩量判断
  - 突破识别：关键位突破情况
  - K线形态：阳线/阴线比例，实体大小

评分范围：0-100，50为中性。
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np
from loguru import logger


class KlineScorer:
    """K线结构评分器

    通过分析K线的结构特征，包括趋势、成交量、突破情况等，
    生成0-100的综合K线评分。

    Attributes:
        trend_weight: 趋势评分权重
        volume_weight: 成交量评分权重
        breakout_weight: 突破评分权重
        pattern_weight: K线形态权重
    """

    def __init__(
        self,
        trend_weight: float = 0.35,
        volume_weight: float = 0.25,
        breakout_weight: float = 0.25,
        pattern_weight: float = 0.15,
    ) -> None:
        """初始化K线结构评分器

        Args:
            trend_weight: 趋势权重（默认0.35）
            volume_weight: 成交量权重（默认0.25）
            breakout_weight: 突破权重（默认0.25）
            pattern_weight: K线形态权重（默认0.15）
        """
        total_weight = trend_weight + volume_weight + breakout_weight + pattern_weight
        self.trend_weight = trend_weight / total_weight
        self.volume_weight = volume_weight / total_weight
        self.breakout_weight = breakout_weight / total_weight
        self.pattern_weight = pattern_weight / total_weight

    def score(self, df: pd.DataFrame) -> Dict[str, Any]:
        """根据K线结构综合评分

        分析K线数据的趋势、成交量、突破情况和形态，生成综合评分。

        Args:
            df: 包含K线数据的DataFrame，需要 'open', 'high', 'low', 'close' 列，
                建议包含 'volume' 列。

        Returns:
            包含以下字段的字典：
            - score: 综合K线评分（0-100）
            - details: 评分详情描述
            - dimension_scores: 各维度独立评分
            - signals: K线信号列表
        """
        if df is None or df.empty or len(df) < 10:
            logger.warning("数据不足，无法进行K线结构评分")
            return {
                "score": 50.0,
                "details": "数据不足（少于10根K线），无法可靠分析K线结构",
                "dimension_scores": {},
                "signals": ["数据不足"],
            }

        signals: List[str] = []

        # 计算各维度评分
        trend_score, trend_detail = self._score_trend(df)
        volume_score, volume_detail = self._score_volume(df)
        breakout_score, breakout_detail = self._score_breakout(df)
        pattern_score, pattern_detail = self._score_pattern(df)

        # 收集信号
        if trend_score > 65:
            signals.append("趋势: 上升趋势")
        elif trend_score < 35:
            signals.append("趋势: 下降趋势")

        if volume_score > 65:
            signals.append("成交量: 放量")
        elif volume_score < 35:
            signals.append("成交量: 缩量")

        if breakout_score > 70:
            signals.append("突破: 向上突破")
        elif breakout_score < 30:
            signals.append("突破: 向下突破")

        if pattern_score > 65:
            signals.append("形态: 看多形态")
        elif pattern_score < 35:
            signals.append("形态: 看空形态")

        # 加权综合评分
        total_score: float = (
            trend_score * self.trend_weight
            + volume_score * self.volume_weight
            + breakout_score * self.breakout_weight
            + pattern_score * self.pattern_weight
        )

        dimension_scores: Dict[str, float] = {
            "trend": round(trend_score, 1),
            "volume": round(volume_score, 1),
            "breakout": round(breakout_score, 1),
            "pattern": round(pattern_score, 1),
        }

        details: str = (
            f"趋势{trend_score:.0f}({trend_detail}), "
            f"成交量{volume_score:.0f}({volume_detail}), "
            f"突破{breakout_score:.0f}({breakout_detail}), "
            f"形态{pattern_score:.0f}({pattern_detail})"
        )

        logger.info(f"K线结构评分完成: {total_score:.1f}分")

        return {
            "score": round(total_score, 1),
            "details": details,
            "dimension_scores": dimension_scores,
            "signals": signals,
        }

    def _score_trend(self, df: pd.DataFrame) -> tuple:
        """趋势评分

        通过近期高低点序列和价格变化判断趋势方向和强度。

        Args:
            df: 包含 'high', 'low', 'close' 列的DataFrame

        Returns:
            (评分, 描述) 元组
        """
        try:
            lookback = min(20, len(df))
            recent_df = df.tail(lookback)

            # 计算价格变化率
            price_change = (recent_df["close"].iloc[-1] - recent_df["close"].iloc[0]) / recent_df["close"].iloc[0] * 100

            # 计算高低点序列判断趋势
            highs = recent_df["high"].values
            lows = recent_df["low"].values

            higher_highs = 0
            higher_lows = 0
            for i in range(1, len(highs)):
                if highs[i] > highs[i - 1]:
                    higher_highs += 1
                if lows[i] > lows[i - 1]:
                    higher_lows += 1

            trend_ratio = (higher_highs + higher_lows) / (2 * (len(highs) - 1))

            score = 50.0

            # 趋势方向评分
            score += trend_ratio * 30  # 趋势比率贡献最多30分
            score += price_change * 2  # 价格变化贡献（每1%贡献2分，最多限制）

            # 限制分数范围
            score = min(max(score, 0), 100)

            if score >= 70:
                detail = "明显上升"
            elif score >= 55:
                detail = "偏上升"
            elif score >= 45:
                detail = "震荡"
            elif score >= 30:
                detail = "偏下降"
            else:
                detail = "明显下降"

            return score, detail

        except Exception as e:
            logger.error(f"趋势评分计算失败: {e}")
            return 50.0, "计算失败"

    def _score_volume(self, df: pd.DataFrame) -> tuple:
        """成交量评分

        分析量价关系，判断放量/缩量状态。

        Args:
            df: 包含 'close', 'volume' 列的DataFrame

        Returns:
            (评分, 描述) 元组
        """
        try:
            if "volume" not in df.columns:
                logger.warning("数据中缺少volume列，返回中性评分")
                return 50.0, "无成交量数据"

            lookback = min(20, len(df))
            recent_df = df.tail(lookback)

            avg_volume = recent_df["volume"].mean()
            current_volume = recent_df["volume"].iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

            # 判断价格方向
            price_change = recent_df["close"].iloc[-1] - recent_df["close"].iloc[-2]
            is_up = price_change > 0

            score = 50.0

            if is_up:
                # 上涨放量是积极的
                if volume_ratio > 2.0:
                    score += 30
                    detail = "大幅放量上涨"
                elif volume_ratio > 1.5:
                    score += 20
                    detail = "放量上涨"
                elif volume_ratio > 1.0:
                    score += 10
                    detail = "温和放量上涨"
                else:
                    score -= 5
                    detail = "缩量上涨"
            else:
                # 下跌放量是消极的
                if volume_ratio > 2.0:
                    score -= 30
                    detail = "大幅放量下跌"
                elif volume_ratio > 1.5:
                    score -= 20
                    detail = "放量下跌"
                elif volume_ratio > 1.0:
                    score -= 10
                    detail = "温和放量下跌"
                else:
                    score += 5
                    detail = "缩量下跌"

            return min(max(score, 0), 100), detail

        except Exception as e:
            logger.error(f"成交量评分计算失败: {e}")
            return 50.0, "计算失败"

    def _score_breakout(self, df: pd.DataFrame) -> tuple:
        """突破评分

        判断价格是否突破近期关键位（前高/前低）。

        Args:
            df: 包含 'high', 'low', 'close' 列的DataFrame

        Returns:
            (评分, 描述) 元组
        """
        try:
            lookback = min(20, len(df))
            recent_df = df.tail(lookback)

            # 计算近期高低点（排除最近3根K线）
            if len(recent_df) > 5:
                range_df = recent_df.iloc[:-3]
                resistance = range_df["high"].max()  # 阻力位
                support = range_df["low"].min()  # 支撑位
            else:
                resistance = recent_df["high"].max()
                support = recent_df["low"].min()

            current_close = recent_df["close"].iloc[-1]
            current_high = recent_df["high"].iloc[-1]
            current_low = recent_df["low"].iloc[-1]

            score = 50.0
            detail = "无突破"

            # 向上突破阻力位
            if current_close > resistance:
                breakout_strength = (current_close - resistance) / resistance * 100
                score = min(50 + breakout_strength * 10, 95)
                detail = f"向上突破阻力位({breakout_strength:.1f}%)"
            # 向下突破支撑位
            elif current_close < support:
                breakdown_strength = (support - current_close) / support * 100
                score = max(50 - breakdown_strength * 10, 5)
                detail = f"向下突破支撑位({breakdown_strength:.1f}%)"
            # 接近阻力位
            elif current_close > resistance * 0.98:
                score = 60.0
                detail = "接近阻力位"
            # 接近支撑位
            elif current_close < support * 1.02:
                score = 40.0
                detail = "接近支撑位"

            return score, detail

        except Exception as e:
            logger.error(f"突破评分计算失败: {e}")
            return 50.0, "计算失败"

    def _score_pattern(self, df: pd.DataFrame) -> tuple:
        """K线形态评分

        分析近期K线的阴阳比例、实体大小等形态特征。

        Args:
            df: 包含 'open', 'close' 列的DataFrame

        Returns:
            (评分, 描述) 元组
        """
        try:
            lookback = min(10, len(df))
            recent_df = df.tail(lookback)

            # 计算阳线/阴线比例
            bullish_count = 0
            bearish_count = 0
            total_body = 0.0

            for _, row in recent_df.iterrows():
                body = abs(row["close"] - row["open"])
                total_body += body

                if row["close"] > row["open"]:
                    bullish_count += 1
                elif row["close"] < row["open"]:
                    bearish_count += 1

            total = bullish_count + bearish_count
            if total == 0:
                return 50.0, "十字星密集"

            bullish_ratio = bullish_count / total
            avg_body = total_body / len(recent_df)

            # 使用平均实体大小判断K线力度
            avg_price = recent_df["close"].mean()
            body_ratio = avg_body / avg_price if avg_price > 0 else 0

            score = 50.0

            # 阳线比例贡献
            score += (bullish_ratio - 0.5) * 40  # 阳线比例偏离50%越多，影响越大

            # 实体大小贡献（大实体K线代表更强的趋势信号）
            if body_ratio > 0.03:
                score += (bullish_ratio - 0.5) * 20  # 大实体时加强方向性评分

            score = min(max(score, 0), 100)

            if score >= 70:
                detail = "强势阳线形态"
            elif score >= 55:
                detail = "偏多形态"
            elif score >= 45:
                detail = "阴阳均衡"
            elif score >= 30:
                detail = "偏空形态"
            else:
                detail = "强势阴线形态"

            return score, detail

        except Exception as e:
            logger.error(f"K线形态评分计算失败: {e}")
            return 50.0, "计算失败"
