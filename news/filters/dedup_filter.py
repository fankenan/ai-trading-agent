"""
去重过滤器

对事件列表进行去重处理，避免相同或高度相似的事件重复影响评分。
去重策略：
  1. 基于事件ID精确去重
  2. 基于标题相似度模糊去重
  3. 基于内容哈希去重
"""

from typing import Dict, Any, List
import hashlib
from difflib import SequenceMatcher
from loguru import logger


class DedupFilter:
    """去重过滤器

    对事件列表进行多级去重，确保每个事件只被处理一次。

    Attributes:
        seen_ids: 已见事件ID集合
        seen_hashes: 已见内容哈希集合
        seen_titles: 已见标题列表（用于模糊匹配）
        similarity_threshold: 标题相似度阈值（默认0.8）
    """

    def __init__(self, similarity_threshold: float = 0.8) -> None:
        """初始化去重过滤器

        Args:
            similarity_threshold: 标题相似度阈值，超过此值视为重复（默认0.8）
        """
        self.seen_ids: set = set()
        self.seen_hashes: set = set()
        self.seen_titles: List[str] = []
        self.similarity_threshold: float = similarity_threshold

        logger.info(f"去重过滤器初始化，相似度阈值: {similarity_threshold}")

    def filter(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对事件列表进行去重

        依次通过ID去重、哈希去重和标题相似度去重，
        返回去重后的事件列表。

        Args:
            events: 待去重的事件列表

        Returns:
            去重后的事件列表
        """
        if not events:
            return []

        unique_events: List[Dict[str, Any]] = []
        duplicate_count: int = 0

        for event in events:
            if self._is_duplicate(event):
                duplicate_count += 1
                logger.debug(f"过滤重复事件: {event.get('id', 'unknown')}")
                continue

            unique_events.append(event)

            # 记录已见事件
            event_id: str = event.get("id", "")
            if event_id:
                self.seen_ids.add(event_id)

            event_text: str = event.get("text", "")
            if event_text:
                content_hash = hashlib.md5(
                    event_text.strip().encode("utf-8")
                ).hexdigest()
                self.seen_hashes.add(content_hash)

            event_title: str = event.get("title", "")
            if event_title:
                self.seen_titles.append(event_title)

        if duplicate_count > 0:
            logger.info(
                f"去重完成: 原始{len(events)}个事件，"
                f"过滤{duplicate_count}个重复，"
                f"保留{len(unique_events)}个唯一事件"
            )
        else:
            logger.info(f"去重完成: {len(events)}个事件均无重复")

        return unique_events

    def _is_duplicate(self, event: Dict[str, Any]) -> bool:
        """判断事件是否为重复事件

        依次检查：
        1. ID是否已存在
        2. 内容哈希是否已存在
        3. 标题是否与已有事件高度相似

        Args:
            event: 待检查的事件

        Returns:
            是否为重复事件
        """
        # 1. ID精确去重
        event_id: str = event.get("id", "")
        if event_id and event_id in self.seen_ids:
            return True

        # 2. 内容哈希去重
        event_text: str = event.get("text", "")
        if event_text:
            content_hash = hashlib.md5(
                event_text.strip().encode("utf-8")
            ).hexdigest()
            if content_hash in self.seen_hashes:
                return True

        # 3. 标题相似度去重
        event_title: str = event.get("title", "")
        if event_title and self.seen_titles:
            for seen_title in self.seen_titles:
                similarity = self._calculate_similarity(event_title, seen_title)
                if similarity >= self.similarity_threshold:
                    logger.debug(
                        f"标题相似度{similarity:.2f}超过阈值: "
                        f"'{event_title}' vs '{seen_title}'"
                    )
                    return True

        return False

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度

        使用SequenceMatcher计算文本相似度比率。

        Args:
            text1: 第一个文本
            text2: 第二个文本

        Returns:
            相似度比率（0.0 - 1.0）
        """
        if not text1 or not text2:
            return 0.0

        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def reset(self) -> None:
        """重置过滤器状态

        清空所有已见记录，使过滤器恢复到初始状态。
        """
        self.seen_ids.clear()
        self.seen_hashes.clear()
        self.seen_titles.clear()
        logger.info("去重过滤器已重置")
