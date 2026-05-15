"""
新闻获取器

提供新闻数据的获取和解析功能。
支持手动输入新闻文本，并将其解析为标准化的事件格式。

事件格式：
{
    "id": str,           # 事件唯一标识
    "title": str,        # 事件标题
    "text": str,         # 事件正文
    "source": str,       # 来源
    "timestamp": str,    # 时间戳
    "type": str,         # 事件类型
    "sentiment": str,    # 情绪方向
    "level": str,        # 事件等级（待分类器填充）
}
"""

from typing import Dict, Any, Optional
from datetime import datetime
import hashlib
import uuid
from loguru import logger


class NewsFetcher:
    """新闻获取器

    负责获取新闻数据并将其解析为标准化的事件格式。
    当前支持手动输入模式，后续可扩展API自动获取。

    Attributes:
        source: 新闻来源标识
    """

    def __init__(self, source: str = "manual") -> None:
        """初始化新闻获取器

        Args:
            source: 新闻来源标识（默认"manual"表示手动输入）
        """
        self.source: str = source
        logger.info(f"新闻获取器初始化，来源: {source}")

    def fetch_manual(self, news_text: str) -> Dict[str, Any]:
        """手动输入新闻

        将手动输入的新闻文本解析为标准化事件格式。

        Args:
            news_text: 新闻文本内容

        Returns:
            标准化的事件字典，包含：
            - id: 事件唯一标识（基于内容哈希生成）
            - title: 事件标题（取文本前50个字符）
            - text: 事件正文
            - source: 来源
            - timestamp: 时间戳
            - type: 事件类型（待分类器填充）
            - sentiment: 情绪方向（待分类器填充）
        """
        if not news_text or not news_text.strip():
            logger.warning("新闻文本为空")
            return {}

        # 生成唯一ID（基于内容哈希）
        content_hash: str = hashlib.md5(
            news_text.strip().encode("utf-8")
        ).hexdigest()[:12]

        # 提取标题（取前50个字符，遇到换行截断）
        title: str = news_text.strip().split("\n")[0][:50]
        if len(news_text.strip().split("\n")[0]) > 50:
            title += "..."

        event: Dict[str, Any] = {
            "id": f"evt_{content_hash}",
            "title": title,
            "text": news_text.strip(),
            "source": self.source,
            "timestamp": datetime.now().isoformat(),
            "type": "",        # 待分类器填充
            "sentiment": "",   # 待分类器填充
            "level": "",       # 待分类器填充
        }

        logger.info(f"手动新闻已解析: id={event['id']}, title={title}")
        return event

    def parse_event(self, title: str, content: str = "", source: str = "") -> Dict[str, Any]:
        """解析事件文本

        将标题和内容解析为结构化的事件数据。
        支持两种调用方式：
        - parse_event(text)           单参数模式，text作为完整文本
        - parse_event(title, content, source)  三参数模式，分别传入标题、内容和来源

        Args:
            title: 事件标题，或完整事件文本（当content为空时）
            content: 事件正文（可选）
            source: 来源标识（可选）

        Returns:
            解析后的事件字典
        """
        # 兼容单参数调用：如果content为空，将title作为完整文本处理
        if not content:
            text = title
        else:
            # 三参数模式：将标题和内容合并为完整文本
            text = f"标题: {title}\n来源: {source}\n{content}"

        if not text or not text.strip():
            logger.warning("事件文本为空")
            return {}

        # 尝试解析结构化文本（key: value 格式）
        structured: Dict[str, str] = {}
        lines: list = text.strip().split("\n")

        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                if key and value:
                    structured[key] = value

        # 如果成功解析出结构化字段，使用它们
        if structured:
            title = structured.get("title", structured.get("标题", text[:50]))
            event_type = structured.get("type", structured.get("类型", ""))
            sentiment = structured.get("sentiment", structured.get("情绪", ""))
            source = structured.get("source", structured.get("来源", self.source))

            event: Dict[str, Any] = {
                "id": f"evt_{hashlib.md5(text.strip().encode('utf-8')).hexdigest()[:12]}",
                "title": title[:50] + ("..." if len(title) > 50 else ""),
                "text": text.strip(),
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "type": event_type,
                "sentiment": sentiment,
                "level": "",  # 待分类器填充
            }

            logger.info(f"结构化事件已解析: id={event['id']}, type={event_type}")
            return event

        # 非结构化文本，使用 fetch_manual 处理
        return self.fetch_manual(text)
