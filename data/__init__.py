# -*- coding: utf-8 -*-
"""
数据层模块

提供数据获取、存储和技术指标计算功能。
使用AKShare作为数据源，SQLite作为本地存储，ta库计算技术指标。

注意：使用延迟导入避免循环依赖
"""

def __getattr__(name):
    """延迟导入，避免启动时加载所有依赖"""
    if name == "AKShareFetcher":
        from data.fetchers.akshare_fetcher import AKShareFetcher
        return AKShareFetcher
    elif name == "AShareFetcher":
        from data.fetchers.ashare_fetcher import AShareFetcher
        return AShareFetcher
    elif name == "SQLiteStorage":
        from data.storage.sqlite_storage import SQLiteStorage
        return SQLiteStorage
    elif name == "TechnicalIndicators":
        from data.processors.indicators import TechnicalIndicators
        return TechnicalIndicators
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "AKShareFetcher",
    "AShareFetcher", 
    "SQLiteStorage",
    "TechnicalIndicators",
]
