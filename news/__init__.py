"""
新闻监控层模块

提供新闻获取、事件分类和去重过滤功能。
新闻监控是事件驱动策略的重要数据来源。
"""

from news.sources.news_fetcher import NewsFetcher
from news.classifiers.event_classifier import EventClassifier
from news.filters.dedup_filter import DedupFilter

__all__ = ["NewsFetcher", "EventClassifier", "DedupFilter"]
