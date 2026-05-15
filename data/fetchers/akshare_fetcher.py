"""
AKShare数据获取器

使用AKShare接口获取A股真实数据（免费，无需Token）
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from loguru import logger


class AKShareFetcher:
    """AKShare数据获取器"""
    
    def __init__(self):
        """初始化AKShare获取器"""
        logger.info("AKShare数据获取器初始化完成")
    
    def _convert_code(self, ts_code: str) -> str:
        """
        转换股票代码格式
        000001.SZ -> 000001
        600519.SH -> 600519
        """
        return ts_code.split('.')[0]
    
    def get_daily(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取日线数据
        
        Args:
            ts_code: 股票代码，如 "000001.SZ"
            start_date: 开始日期，格式 "YYYYMMDD"
            end_date: 结束日期，格式 "YYYYMMDD"
        """
        symbol = self._convert_code(ts_code)
        
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        
        try:
            # 使用akshare获取A股日线数据
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                    start_date=start_date, end_date=end_date, adjust="qfq")
            
            if df is None or df.empty:
                logger.warning(f"AKShare未获取到数据: {symbol}")
                return pd.DataFrame()
            
            # 转换列名
            df = df.rename(columns={
                "日期": "timestamp",
                "开盘": "open",
                "最高": "high", 
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
                "成交额": "amount",
                "涨跌幅": "change_pct",
                "涨跌额": "change",
                "昨收": "pre_close"
            })
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['datetime'] = df['timestamp']
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # 添加涨跌停标记
            df['is_limit_up'] = df['change_pct'] >= 9.9
            df['is_limit_down'] = df['change_pct'] <= -9.9
            
            logger.info(f"AKShare获取 {symbol} 日线数据: {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"AKShare获取 {symbol} 数据失败: {e}")
            return pd.DataFrame()
    
    def get_realtime_quote(self, ts_code: str) -> Dict[str, Any]:
        """获取实时行情"""
        symbol = self._convert_code(ts_code)
        
        try:
            # 获取实时行情
            df = ak.stock_zh_a_spot_em()
            
            # 查找对应股票
            row = df[df['代码'] == symbol]
            if row.empty:
                return {"error": "未找到股票"}
            
            row = row.iloc[0]
            
            return {
                "symbol": symbol,
                "name": str(row.get('名称', '')),
                "price": float(row.get('最新价', 0)),
                "change_pct": float(row.get('涨跌幅', 0)),
                "change": float(row.get('涨跌额', 0)),
                "volume": float(row.get('成交量', 0)),
                "amount": float(row.get('成交额', 0)),
                "open": float(row.get('今开', 0)),
                "high": float(row.get('最高', 0)),
                "low": float(row.get('最低', 0)),
                "pre_close": float(row.get('昨收', 0)),
                "is_limit_up": float(row.get('涨跌幅', 0)) >= 9.9,
                "is_limit_down": float(row.get('涨跌幅', 0)) <= -9.9,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"AKShare获取实时行情失败: {e}")
            return {"error": str(e)}
    
    def get_stock_basic(self, ts_code: str = None) -> pd.DataFrame:
        """获取股票基本信息"""
        try:
            df = ak.stock_info_a_code_name()
            if ts_code:
                symbol = self._convert_code(ts_code)
                df = df[df['code'] == symbol]
            return df
        except Exception as e:
            logger.error(f"AKShare获取股票基本信息失败: {e}")
            return pd.DataFrame()
    
    def get_money_flow(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取个股资金流向"""
        symbol = self._convert_code(ts_code)
        
        try:
            df = ak.stock_individual_fund_flow(stock=symbol, market="sh" if symbol.startswith('6') else "sz")
            return df
        except Exception as e:
            logger.error(f"AKShare获取资金流向失败: {e}")
            return pd.DataFrame()
    
    def get_north_money(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取北向资金流向"""
        try:
            df = ak.stock_hsgt_north_net_flow_in_em()
            return df
        except Exception as e:
            logger.error(f"AKShare获取北向资金失败: {e}")
            return pd.DataFrame()
    
    def get_major_news(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取财经新闻"""
        try:
            df = ak.stock_news_em(symbol="财经")
            # 转换格式
            if not df.empty:
                df = df.rename(columns={
                    '发布时间': 'datetime',
                    '新闻标题': 'title',
                    '新闻内容': 'content',
                    '来源': 'src'
                })
            return df.head(20)
        except Exception as e:
            logger.error(f"AKShare获取新闻失败: {e}")
            return pd.DataFrame()
    
    def get_limit_list(self, trade_date: str = None) -> pd.DataFrame:
        """获取每日涨跌停股票"""
        try:
            df = ak.stock_zt_pool_em(date=trade_date or datetime.now().strftime("%Y%m%d"))
            return df
        except Exception as e:
            logger.error(f"AKShare获取涨跌停列表失败: {e}")
            return pd.DataFrame()
