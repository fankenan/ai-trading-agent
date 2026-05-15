"""
评分系统主类

整合各评分模块，通过加权计算生成综合评分。
评分结果将作为决策层的重要输入。

评分流程：
  1. 各模块独立评分（事件、情绪、技术指标、K线结构）
  2. 根据权重加权汇总
  3. 应用风险惩罚因子
  4. 生成最终评分和操作建议
"""

from typing import Dict, Any, List, Optional
import pandas as pd
from loguru import logger

from scoring.modules.event_scorer import EventScorer
from scoring.modules.sentiment_scorer import SentimentScorer
from scoring.modules.technical_scorer import TechnicalScorer
from scoring.modules.kline_scorer import KlineScorer
from scoring.weights.default_weights import DEFAULT_WEIGHTS


class ScoringSystem:
    """评分系统

    整合多个评分模块，通过加权计算生成综合评分。
    支持自定义权重配置，默认使用DEFAULT_WEIGHTS。

    Attributes:
        weights: 各模块权重配置
        event_scorer: 事件评分器
        sentiment_scorer: 情绪评分器
        technical_scorer: 技术指标评分器
        kline_scorer: K线结构评分器
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None) -> None:
        """初始化评分系统

        Args:
            weights: 自定义权重配置，格式为 {"event": 0.25, "sentiment": 0.15, ...}。
                     如果为None，则使用默认权重。
        """
        self.weights: Dict[str, float] = weights or DEFAULT_WEIGHTS.copy()

        # 归一化权重
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}
        else:
            logger.warning("权重总和为零，使用默认权重")
            self.weights = DEFAULT_WEIGHTS.copy()

        # 初始化各评分模块
        self.event_scorer: EventScorer = EventScorer()
        self.sentiment_scorer: SentimentScorer = SentimentScorer()
        self.technical_scorer: TechnicalScorer = TechnicalScorer()
        self.kline_scorer: KlineScorer = KlineScorer()

        logger.info(f"评分系统初始化完成，权重配置: {self.weights}")

    def calculate(
        self,
        df: Optional[pd.DataFrame] = None,
        events: Optional[List[Dict[str, Any]]] = None,
        fear_greed: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """计算综合评分

        整合各模块评分结果，加权计算综合评分，并应用风险惩罚因子。

        Args:
            df: 包含K线数据的DataFrame（用于技术指标和K线结构评分）
            events: 事件列表（用于事件评分）
            fear_greed: 恐惧贪婪指数数据（用于情绪评分）

        Returns:
            包含以下字段的字典：
            - total_score: 综合评分（0-100）
            - module_scores: 各模块独立评分详情
            - risk_penalty: 风险惩罚因子
            - recommendation: 操作建议
            - confidence: 评分置信度
        """
        logger.info("开始计算综合评分...")

        module_scores: Dict[str, Any] = {}

        # 1. 事件评分
        try:
            event_result = self.event_scorer.score(events or [])
            module_scores["event"] = event_result
        except Exception as e:
            logger.error(f"事件评分失败: {e}")
            module_scores["event"] = {"score": 0, "details": f"评分失败: {e}"}

        # 2. 情绪评分
        try:
            sentiment_result = self.sentiment_scorer.score(fear_greed or {})
            module_scores["sentiment"] = sentiment_result
        except Exception as e:
            logger.error(f"情绪评分失败: {e}")
            module_scores["sentiment"] = {"score": 50, "details": f"评分失败: {e}"}

        # 3. 技术指标评分
        try:
            if df is not None and not df.empty:
                technical_result = self.technical_scorer.score(df)
                module_scores["technical"] = technical_result
            else:
                module_scores["technical"] = {
                    "score": 50,
                    "details": "无K线数据",
                }
        except Exception as e:
            logger.error(f"技术指标评分失败: {e}")
            module_scores["technical"] = {"score": 50, "details": f"评分失败: {e}"}

        # 4. K线结构评分
        try:
            if df is not None and not df.empty:
                kline_result = self.kline_scorer.score(df)
                module_scores["kline"] = kline_result
            else:
                module_scores["kline"] = {
                    "score": 50,
                    "details": "无K线数据",
                }
        except Exception as e:
            logger.error(f"K线结构评分失败: {e}")
            module_scores["kline"] = {"score": 50, "details": f"评分失败: {e}"}

        # 5. 加权计算综合评分
        total_score: float = 0.0
        for module_name, module_result in module_scores.items():
            weight = self.weights.get(module_name, 0)
            score = module_result.get("score", 50)
            total_score += score * weight

        total_score = round(total_score, 1)

        # 6. 计算风险惩罚因子
        risk_penalty: float = self._calculate_risk_penalty(module_scores, events)

        # 应用风险惩罚
        final_score: float = round(total_score * (1 - risk_penalty), 1)
        final_score = min(max(final_score, 0), 100)

        # 7. 生成操作建议
        recommendation: str = self._generate_recommendation(final_score, module_scores)

        # 8. 计算置信度
        confidence: float = self._calculate_confidence(module_scores, df, events)

        result: Dict[str, Any] = {
            "total_score": final_score,
            "raw_score": total_score,
            "module_scores": module_scores,
            "risk_penalty": risk_penalty,
            "recommendation": recommendation,
            "confidence": confidence,
            "weights": self.weights,
        }

        logger.info(
            f"综合评分完成: 原始分={total_score}, "
            f"风险惩罚={risk_penalty:.2%}, "
            f"最终分={final_score}, "
            f"建议={recommendation}"
        )

        return result

    def _calculate_risk_penalty(
        self,
        module_scores: Dict[str, Any],
        events: Optional[List[Dict[str, Any]]] = None,
    ) -> float:
        """计算风险惩罚因子

        根据各模块评分的分歧程度和极端事件计算风险惩罚。
        分歧越大，惩罚越高；存在极端事件时额外惩罚。

        Args:
            module_scores: 各模块评分结果
            events: 事件列表

        Returns:
            风险惩罚因子（0.0 - 0.5）
        """
        scores = [
            m.get("score", 50)
            for m in module_scores.values()
            if isinstance(m.get("score"), (int, float))
        ]

        if len(scores) < 2:
            return 0.0

        # 计算评分标准差（分歧度）
        import numpy as np
        std_dev = float(np.std(scores))

        # 标准差越大，分歧越大，惩罚越高
        penalty = min(std_dev / 100, 0.2)

        # 检查是否存在S级事件（极端事件额外惩罚）
        if events:
            s_level_count = sum(
                1 for e in events if e.get("level", "").upper() == "S"
            )
            if s_level_count > 0:
                penalty += 0.1  # S级事件增加10%惩罚

        return min(penalty, 0.5)

    def _generate_recommendation(
        self,
        score: float,
        module_scores: Dict[str, Any],
    ) -> str:
        """根据综合评分生成操作建议

        Args:
            score: 综合评分
            module_scores: 各模块评分结果

        Returns:
            操作建议字符串
        """
        if score >= 80:
            return "强烈买入"
        elif score >= 65:
            return "建议买入"
        elif score >= 55:
            return "轻度看多"
        elif score >= 45:
            return "观望"
        elif score >= 35:
            return "轻度看空"
        elif score >= 20:
            return "建议卖出"
        else:
            return "强烈卖出"

    def _calculate_confidence(
        self,
        module_scores: Dict[str, Any],
        df: Optional[pd.DataFrame],
        events: Optional[List[Dict[str, Any]]] = None,
    ) -> float:
        """计算评分置信度

        置信度取决于数据完整性和模块间一致性。

        Args:
            module_scores: 各模块评分结果
            df: K线数据
            events: 事件列表

        Returns:
            置信度（0.0 - 1.0）
        """
        confidence = 0.5  # 基础置信度

        # 数据完整性加分
        if df is not None and not df.empty and len(df) >= 50:
            confidence += 0.15
        elif df is not None and not df.empty:
            confidence += 0.05

        if events and len(events) > 0:
            confidence += 0.1

        # 模块间一致性加分
        scores = [
            m.get("score", 50)
            for m in module_scores.values()
            if isinstance(m.get("score"), (int, float))
        ]
        if len(scores) >= 2:
            import numpy as np
            std_dev = float(np.std(scores))
            if std_dev < 10:
                confidence += 0.2  # 高一致性
            elif std_dev < 20:
                confidence += 0.1  # 中等一致性

        return min(confidence, 1.0)
