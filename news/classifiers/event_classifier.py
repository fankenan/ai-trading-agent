"""
事件分类器

对新闻事件进行分类，确定事件等级（S/A/B/C）和情绪方向。
分类结果将直接影响评分系统中事件评分模块的输出。

事件等级定义：
  - S级：重大事件，对市场产生深远影响（如美联储决议、黑天鹅事件）
  - A级：重要事件，对市场产生显著影响（如重要经济数据、大型交易所事件）
  - B级：一般事件，对市场产生一定影响（如常规经济指标、行业新闻）
  - C级：轻微事件，对市场影响较小（如常规公告、噪音信息）

分类基于关键词匹配和规则引擎，后续可扩展为AI模型分类。
"""

from typing import Dict, Any, List, Optional
from loguru import logger


class EventClassifier:
    """事件分类器

    基于关键词匹配和规则引擎对事件进行分类。
    确定事件等级、情绪方向和是否可交易。

    Attributes:
        s_keywords: S级事件关键词
        a_keywords: A级事件关键词
        b_keywords: B级事件关键词
        positive_keywords: 利好关键词
        negative_keywords: 利空关键词
    """

    def __init__(self) -> None:
        """初始化事件分类器"""
        # S级事件关键词（重大事件）
        self.s_keywords: List[str] = [
            "美联储", "Fed", "利率决议", "加息", "降息", "量化宽松", "QT",
            "黑天鹅", "崩盘", "熔断", "战争", "制裁",
            "黑客攻击", "交易所跑路", "监管禁止", "重大政策",
            "ETF通过", "ETF批准", "比特币减半", "以太坊升级",
        ]

        # A级事件关键词（重要事件）
        self.a_keywords: List[str] = [
            "CPI", "非农", "GDP", "失业率", "通胀",
            "SEC", "监管", "合规", "法案",
            "交易所上线", "交易所下架", "合约爆仓",
            "鲸鱼", "巨鲸", "大量转账",
            "重要合作", "战略投资", "融资",
        ]

        # B级事件关键词（一般事件）
        self.b_keywords: List[str] = [
            "经济数据", "PMI", "PPI", "零售",
            "行业报告", "分析报告", "研报",
            "技术升级", "版本更新", "产品发布",
            "高管变动", "人事变动",
            "市场情绪", "恐惧贪婪",
        ]

        # 利好关键词
        self.positive_keywords: List[str] = [
            "上涨", "涨", "突破", "新高", "利好", "看多", "牛市",
            "批准", "通过", "合作", "投资", "增长", "盈利",
            "升级", "创新高", "反弹", "复苏", "乐观",
            "buy", "bullish", "surge", "rally", "breakout", "ATH",
        ]

        # 利空关键词
        self.negative_keywords: List[str] = [
            "下跌", "跌", "暴跌", "崩盘", "利空", "看空", "熊市",
            "禁止", "拒绝", "制裁", "黑客", "跑路", "爆雷",
            "亏损", "下滑", "衰退", "恐慌", "悲观", "风险",
            "sell", "bearish", "crash", "dump", "hack", "ban",
        ]

        logger.info("事件分类器初始化完成")

    def classify(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """对事件进行分类

        根据事件内容确定等级、情绪方向和是否可交易。

        Args:
            event: 事件字典，至少包含 'text' 字段

        Returns:
            包含以下字段的字典：
            - level: 事件等级（"S"/"A"/"B"/"C"）
            - confidence: 分类置信度（0.0-1.0）
            - reasoning: 分类推理过程
            - tradable: 是否可交易
            - sentiment: 情绪方向（"positive"/"negative"/"neutral"）
            - event_type: 事件类型
        """
        if not event or not event.get("text"):
            logger.warning("事件为空或缺少text字段")
            return {
                "level": "C",
                "confidence": 0.0,
                "reasoning": "事件为空，默认C级",
                "tradable": False,
                "sentiment": "neutral",
                "event_type": "unknown",
            }

        text: str = (event.get("title", "") + " " + event.get("text", "")).lower()

        # 1. 确定事件等级
        level, level_confidence, level_reasoning = self._classify_level(text)

        # 2. 确定情绪方向
        sentiment, sentiment_reasoning = self._classify_sentiment(text)

        # 3. 确定事件类型
        event_type: str = self._classify_type(text)

        # 4. 判断是否可交易
        tradable: bool = self._is_tradable(level, sentiment)

        result: Dict[str, Any] = {
            "level": level,
            "confidence": level_confidence,
            "reasoning": f"{level_reasoning}；{sentiment_reasoning}",
            "tradable": tradable,
            "sentiment": sentiment,
            "event_type": event_type,
        }

        logger.info(
            f"事件分类完成: level={level}, sentiment={sentiment}, "
            f"tradable={tradable}, confidence={level_confidence:.2%}"
        )

        return result

    def _classify_level(self, text: str) -> tuple:
        """确定事件等级

        Args:
            text: 事件文本（小写）

        Returns:
            (等级, 置信度, 推理) 元组
        """
        s_count = sum(1 for kw in self.s_keywords if kw.lower() in text)
        a_count = sum(1 for kw in self.a_keywords if kw.lower() in text)
        b_count = sum(1 for kw in self.b_keywords if kw.lower() in text)

        if s_count > 0:
            confidence = min(0.7 + s_count * 0.1, 0.95)
            return "S", confidence, f"匹配到{s_count}个S级关键词"
        elif a_count > 0:
            confidence = min(0.6 + a_count * 0.1, 0.90)
            return "A", confidence, f"匹配到{a_count}个A级关键词"
        elif b_count > 0:
            confidence = min(0.5 + b_count * 0.1, 0.80)
            return "B", confidence, f"匹配到{b_count}个B级关键词"
        else:
            return "C", 0.5, "未匹配到高级别关键词，默认C级"

    def _classify_sentiment(self, text: str) -> tuple:
        """确定情绪方向

        Args:
            text: 事件文本（小写）

        Returns:
            (情绪方向, 推理) 元组
        """
        positive_count = sum(1 for kw in self.positive_keywords if kw.lower() in text)
        negative_count = sum(1 for kw in self.negative_keywords if kw.lower() in text)

        if positive_count > negative_count:
            return "positive", f"利好信号{positive_count}个 > 利空信号{negative_count}个"
        elif negative_count > positive_count:
            return "negative", f"利空信号{negative_count}个 > 利好信号{positive_count}个"
        else:
            return "neutral", f"利好信号{positive_count}个 = 利空信号{negative_count}个"

    def _classify_type(self, text: str) -> str:
        """确定事件类型

        Args:
            text: 事件文本（小写）

        Returns:
            事件类型字符串
        """
        type_keywords: Dict[str, List[str]] = {
            "monetary_policy": ["利率", "美联储", "Fed", "加息", "降息", "货币政策"],
            "regulation": ["监管", "SEC", "合规", "法案", "禁止", "批准"],
            "market_data": ["CPI", "非农", "GDP", "经济数据", "PMI", "通胀"],
            "security": ["黑客", "攻击", "跑路", "漏洞", "安全"],
            "technology": ["升级", "更新", "技术", "分叉", "硬分叉"],
            "institutional": ["ETF", "机构", "鲸鱼", "巨鲸", "融资", "投资"],
            "market_event": ["暴跌", "崩盘", "熔断", "反弹", "突破"],
        }

        best_type: str = "other"
        best_count: int = 0

        for event_type, keywords in type_keywords.items():
            count = sum(1 for kw in keywords if kw.lower() in text)
            if count > best_count:
                best_count = count
                best_type = event_type

        return best_type

    def _is_tradable(self, level: str, sentiment: str) -> bool:
        """判断事件是否可交易

        S级和A级事件可交易，B级事件在情绪明确时可交易，
        C级事件不建议交易。

        Args:
            level: 事件等级
            sentiment: 情绪方向

        Returns:
            是否可交易
        """
        if level in ("S", "A"):
            return True
        if level == "B" and sentiment in ("positive", "negative"):
            return True
        return False
