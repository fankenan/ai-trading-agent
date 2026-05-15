"""
情绪评分模块

根据恐惧贪婪指数（Fear & Greed Index）评估市场情绪。
恐惧贪婪指数是衡量市场情绪的重要指标，范围通常为0-100。

评分逻辑：
  - 极度贪婪（80-100）：市场过热风险，适度看多但需警惕回调
  - 贪婪（60-80）：市场情绪积极，偏多
  - 中性（40-60）：市场情绪平稳，观望
  - 恐惧（20-40）：市场情绪悲观，可能存在抄底机会
  - 极度恐惧（0-20）：市场恐慌，可能存在较大机会但风险也高
"""

from typing import Dict, Any
from loguru import logger


class SentimentScorer:
    """情绪评分器

    基于恐惧贪婪指数对市场情绪进行评分。
    采用逆向思维：极度恐惧时往往蕴含机会，极度贪婪时则需警惕风险。

    Attributes:
        无
    """

    def score(self, fear_greed_index: Dict[str, Any]) -> Dict[str, Any]:
        """根据恐惧贪婪指数计算情绪评分

        将恐惧贪婪指数映射为0-100的综合评分。
        评分考虑了逆向投资思维：在恐惧中寻找机会，在贪婪中保持谨慎。

        Args:
            fear_greed_index: 恐惧贪婪指数数据，应包含以下字段：
                - value: 指数值（0-100）
                - classification: 分类标签（可选）
                - timestamp: 时间戳（可选）

        Returns:
            包含以下字段的字典：
            - score: 情绪评分（0-100）
            - details: 评分详情描述
            - market_sentiment: 市场情绪分类
            - action_bias: 操作偏向建议
        """
        if not fear_greed_index:
            logger.info("恐惧贪婪指数为空，返回中性评分50")
            return {
                "score": 50.0,
                "details": "无情绪数据，默认中性",
                "market_sentiment": "中性",
                "action_bias": "观望",
            }

        value: float = float(fear_greed_index.get("value", 50))
        classification: str = fear_greed_index.get("classification", "")

        # 根据恐惧贪婪指数计算评分
        # 核心思想：恐惧时给较高评分（逆向思维，恐惧中蕴含机会）
        #           贪婪时给较低评分（贪婪中蕴含风险）
        if value <= 10:
            # 极度恐惧 - 市场恐慌，可能有抄底机会但风险极高
            score = 75.0
            sentiment = "极度恐惧"
            action_bias = "谨慎抄底"
            details = "市场极度恐慌，历史数据显示此区间往往蕴含反弹机会，但需严格风控"
        elif value <= 25:
            # 恐惧 - 市场悲观，可能存在机会
            score = 70.0
            sentiment = "恐惧"
            action_bias = "偏多"
            details = "市场处于恐惧状态，逆向思维下可能存在较好的入场机会"
        elif value <= 40:
            # 偏恐惧 - 市场略悲观
            score = 60.0
            sentiment = "偏恐惧"
            action_bias = "轻度偏多"
            details = "市场情绪偏悲观，可适度关注机会"
        elif value <= 60:
            # 中性 - 市场平稳
            score = 50.0
            sentiment = "中性"
            action_bias = "观望"
            details = "市场情绪中性，建议观望等待明确信号"
        elif value <= 75:
            # 偏贪婪 - 市场偏乐观
            score = 40.0
            sentiment = "偏贪婪"
            action_bias = "轻度偏空"
            details = "市场情绪偏乐观，需警惕过热风险"
        elif value <= 90:
            # 贪婪 - 市场乐观
            score = 30.0
            sentiment = "贪婪"
            action_bias = "偏空"
            details = "市场处于贪婪状态，历史数据显示此区间回调概率增加"
        else:
            # 极度贪婪 - 市场过热
            score = 20.0
            sentiment = "极度贪婪"
            action_bias = "谨慎做空或减仓"
            details = "市场极度贪婪，泡沫风险较高，建议降低仓位"

        # 如果有外部分类标签，记录以供参考
        if classification:
            details += f"（官方分类: {classification}）"

        logger.info(f"情绪评分完成: 恐惧贪婪指数={value}, 评分={score}, 情绪={sentiment}")

        return {
            "score": score,
            "details": details,
            "market_sentiment": sentiment,
            "action_bias": action_bias,
            "fear_greed_value": value,
        }
