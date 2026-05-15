"""
事件评分模块

根据事件等级（S/A/B/C）对事件列表进行评分。
事件等级越高，对市场的影响越大，评分也越高。

评分规则：
  - S级事件：100分（重大利好/利空，如美联储决议、黑天鹅事件）
  - A级事件：80分（重要事件，如重要经济数据发布、大型交易所事件）
  - B级事件：60分（一般事件，如常规经济指标、行业新闻）
  - C级事件：30分（轻微事件，如常规公告、噪音信息）
"""

from typing import List, Dict, Any
from loguru import logger


class EventScorer:
    """事件评分器

    根据事件列表中各事件的等级计算综合评分。
    当存在多个事件时，取最高等级事件的分数作为基准，
    并根据事件数量给予适当的叠加加成。

    Attributes:
        level_scores: 事件等级与分数的映射关系
    """

    # 事件等级对应的基础分数
    LEVEL_SCORES: Dict[str, int] = {
        "S": 100,  # 重大事件
        "A": 80,   # 重要事件
        "B": 60,   # 一般事件
        "C": 30,   # 轻微事件
    }

    def score(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """对事件列表进行综合评分

        遍历事件列表，根据每个事件的等级计算分数。
        多个事件会产生叠加效应，但上限为100分。

        Args:
            events: 事件列表，每个事件应包含 'level' 字段（S/A/B/C），
                    可选包含 'sentiment' 字段（positive/negative/neutral）

        Returns:
            包含以下字段的字典：
            - score: 综合评分（0-100）
            - details: 评分详情描述
            - event_count: 事件总数
            - level_distribution: 各等级事件数量分布
        """
        if not events:
            logger.info("事件列表为空，返回默认评分0")
            return {
                "score": 0,
                "details": "无事件数据",
                "event_count": 0,
                "level_distribution": {},
            }

        level_distribution: Dict[str, int] = {"S": 0, "A": 0, "B": 0, "C": 0}
        max_score: int = 0
        total_score: float = 0.0
        sentiment_counts: Dict[str, int] = {"positive": 0, "negative": 0, "neutral": 0}

        for event in events:
            level: str = event.get("level", "C").upper()
            if level not in self.LEVEL_SCORES:
                logger.warning(f"未知事件等级: {level}，默认按C级处理")
                level = "C"

            event_score: int = self.LEVEL_SCORES[level]
            level_distribution[level] = level_distribution.get(level, 0) + 1
            total_score += event_score

            if event_score > max_score:
                max_score = event_score

            # 统计情绪分布
            sentiment: str = event.get("sentiment", "neutral")
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1

        # 综合评分逻辑：以最高分事件为基准，加上其他事件的叠加加成
        # 叠加加成随事件数量递减，避免过度放大
        if len(events) > 1:
            additional_score: float = (total_score - max_score) * 0.1
            final_score: float = min(max_score + additional_score, 100.0)
        else:
            final_score = float(max_score)

        # 根据情绪方向微调分数
        if sentiment_counts["negative"] > sentiment_counts["positive"]:
            final_score = max(final_score * 0.85, 0)  # 利空事件适当降低评分
            sentiment_detail = "偏利空"
        elif sentiment_counts["positive"] > sentiment_counts["negative"]:
            final_score = min(final_score * 1.05, 100)  # 利好事件适当提高评分
            sentiment_detail = "偏利好"
        else:
            sentiment_detail = "中性"

        details: str = (
            f"共{len(events)}个事件，"
            f"S级{level_distribution['S']}个、"
            f"A级{level_distribution['A']}个、"
            f"B级{level_distribution['B']}个、"
            f"C级{level_distribution['C']}个，"
            f"情绪倾向: {sentiment_detail}"
        )

        logger.info(f"事件评分完成: {final_score:.1f}分, {details}")

        return {
            "score": round(final_score, 1),
            "details": details,
            "event_count": len(events),
            "level_distribution": level_distribution,
        }
