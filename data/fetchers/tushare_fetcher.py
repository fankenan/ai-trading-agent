"""
Tushare数据获取器

使用Tushare Pro接口获取A股真实数据
"""

import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger


class TushareFetcher:
    """Tushare数据获取器"""
    
    def __init__(self, token: str = None):
        """
        初始化Tushare获取器
        
        Args:
            token: Tushare Pro的API Token
        """
        if token:
            ts.set_token(token)
        self.pro = ts.pro_api()
        logger.info("Tushare数据获取器初始化完成")
    
    def get_daily(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取日线数据
        
        Args:
            ts_code: 股票代码，如 "000001.SZ"
            start_date: 开始日期，格式 "YYYYMMDD"
            end_date: 结束日期，格式 "YYYYMMDD"
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        
        try:
            df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                logger.warning(f"未获取到数据: {ts_code}")
                return pd.DataFrame()
            
            # 转换列名
            df = df.rename(columns={
                "trade_date": "timestamp",
                "open": "open",
                "high": "high", 
                "low": "low",
                "close": "close",
                "vol": "volume",
                "amount": "amount",
                "pct_chg": "change_pct",
                "change": "change"
            })
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['datetime'] = df['timestamp']
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # 添加涨跌停标记
            df['is_limit_up'] = df['change_pct'] >= 9.9
            df['is_limit_down'] = df['change_pct'] <= -9.9
            
            logger.info(f"获取 {ts_code} 日线数据: {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取 {ts_code} 数据失败: {e}")
            return pd.DataFrame()
    
    def get_realtime_quote(self, ts_code: str) -> Dict[str, Any]:
        """获取实时行情"""
        try:
            # 使用日线接口获取最新数据（获取最近5天，取最新一条）
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
            df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                return {"error": "未找到股票"}
            
            # 取最新的一条数据
            df = df.sort_values('trade_date', ascending=False)
            row = df.iloc[0]
            
            # 从ts_code提取股票名称（避免额外API调用）
            name = ts_code.split('.')[0]
            
            return {
                "symbol": ts_code.split('.')[0],
                "name": name,
                "price": float(row['close']),
                "change_pct": float(row['pct_chg']),
                "change": float(row['change']),
                "volume": float(row['vol']) * 100,  # 手转股
                "amount": float(row['amount']) * 1000,
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "pre_close": float(row['pre_close']),
                "is_limit_up": float(row['pct_chg']) >= 9.9,
                "is_limit_down": float(row['pct_chg']) <= -9.9,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            return {"error": str(e)}
    
    def get_stock_basic(self, ts_code: str = None) -> pd.DataFrame:
        """获取股票基本信息"""
        try:
            if ts_code:
                df = self.pro.stock_basic(ts_code=ts_code)
            else:
                df = self.pro.stock_basic(exchange='', list_status='L')
            return df
        except Exception as e:
            logger.error(f"获取股票基本信息失败: {e}")
            return pd.DataFrame()
    
    def get_money_flow(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取个股资金流向"""
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        
        try:
            df = self.pro.moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
            return df
        except Exception as e:
            logger.error(f"获取资金流向失败: {e}")
            return pd.DataFrame()
    
    def get_north_money(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取北向资金流向"""
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        
        try:
            df = self.pro.moneyflow_hsgt(start_date=start_date, end_date=end_date)
            return df
        except Exception as e:
            logger.error(f"获取北向资金失败: {e}")
            return pd.DataFrame()
    
    def get_major_news(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取重大新闻"""
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
        
        try:
            df = self.pro.major_news(start_date=start_date, end_date=end_date)
            return df
        except Exception as e:
            logger.error(f"获取新闻失败: {e}")
            return pd.DataFrame()
    
    def get_limit_list(self, trade_date: str = None) -> pd.DataFrame:
        """获取每日涨跌停股票"""
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y%m%d")
        
        try:
            df = self.pro.limit_list(trade_date=trade_date)
            return df
        except Exception as e:
            logger.error(f"获取涨跌停列表失败: {e}")
            return pd.DataFrame()
