# -*- coding: utf-8 -*-
"""
数据获取器子模块
支持 AKShare / Tushare / BaoStock / EastMoney / JQData
"""

from data.fetchers.akshare_fetcher import AKShareFetcher
from data.fetchers.em_fetcher import EMFetcher

try:
    from data.fetchers.tushare_fetcher import TushareFetcher
except ImportError:
    TushareFetcher = None

try:
    from data.fetchers.baostock_fetcher import BaoStockFetcher
except ImportError:
    BaoStockFetcher = None

try:
    from data.fetchers.jqdata_fetcher import JQDataFetcher
except ImportError:
    JQDataFetcher = None

__all__ = [
    "AKShareFetcher",
    "TushareFetcher",
    "BaoStockFetcher",
    "EMFetcher",
    "JQDataFetcher",
]
