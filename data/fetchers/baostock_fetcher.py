"""
BaoStock数据获取器

完全免费，无需注册，历史数据全面（1990年至今）
支持日线/周线/月线、分钟线、财报、指数成分股等
"""

import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from loguru import logger


class BaoStockFetcher:
    """BaoStock数据获取器"""

    def __init__(self):
        self._logged_in = False
        self._login()
        logger.info("BaoStock数据获取器初始化完成")

    def _login(self):
        try:
            lg = bs.login()
            if lg.error_code == '0':
                self._logged_in = True
            else:
                logger.warning(f"BaoStock登录警告: {lg.error_msg}")
        except Exception as e:
            logger.warning(f"BaoStock登录失败: {e}")

    def _ensure_login(self):
        if not self._logged_in:
            self._login()

    def _to_baostock_code(self, ts_code: str) -> str:
        """000001.SZ → sz.000001"""
        parts = ts_code.split('.')
        return f"{parts[1].lower()}.{parts[0]}"

    def _from_baostock_code(self, bs_code: str) -> str:
        """sz.000001 → 000001.SZ"""
        parts = bs_code.split('.')
        return f"{parts[1]}.{parts[0].upper()}"

    def get_daily(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取日线数据（复权）
        """
        self._ensure_login()
        bs_code = self._to_baostock_code(ts_code)

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        try:
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,preclose,volume,amount,pctChg,isST,turn,peTTM,pbMRQ",
                start_date=start_date, end_date=end_date,
                frequency="d", adjustflag="2"  # 前复权
            )
            if rs.error_code != '0':
                logger.error(f"BaoStock查询失败: {rs.error_msg}")
                return pd.DataFrame()

            rows = []
            while (rs.error_code == '0') & rs.next():
                rows.append(rs.get_row_data())

            if not rows:
                return pd.DataFrame()

            df = pd.DataFrame(rows, columns=rs.fields)

            df = df.rename(columns={
                "date": "timestamp",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "preclose": "pre_close",
                "volume": "volume",
                "amount": "amount",
                "pctChg": "change_pct",
            })

            for col in ['open', 'high', 'low', 'close', 'pre_close', 'volume', 'amount', 'change_pct']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            df['is_limit_up'] = pd.to_numeric(df['change_pct'], errors='coerce') >= 9.9
            df['is_limit_down'] = pd.to_numeric(df['change_pct'], errors='coerce') <= -9.9
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['datetime'] = df['timestamp']
            df = df.sort_values('timestamp').reset_index(drop=True)

            logger.info(f"BaoStock获取 {ts_code} 日线数据: {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"BaoStock获取 {ts_code} 数据失败: {e}")
            return pd.DataFrame()

    def get_realtime_quote(self, ts_code: str) -> Dict[str, Any]:
        """获取最新行情"""
        self._ensure_login()

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

        try:
            df = self.get_daily(ts_code, start_date, end_date)
            if df.empty:
                return {"error": "未找到股票数据"}

            row = df.iloc[-1]
            symbol = ts_code.split('.')[0]

            return {
                "symbol": symbol,
                "name": symbol,
                "price": float(row.get('close', 0)),
                "change_pct": float(row.get('change_pct', 0)),
                "change": float(row.get('close', 0)) - float(row.get('pre_close', 0)),
                "volume": float(row.get('volume', 0)),
                "amount": float(row.get('amount', 0)),
                "open": float(row.get('open', 0)),
                "high": float(row.get('high', 0)),
                "low": float(row.get('low', 0)),
                "pre_close": float(row.get('pre_close', 0)),
                "is_limit_up": float(row.get('change_pct', 0)) >= 9.9,
                "is_limit_down": float(row.get('change_pct', 0)) <= -9.9,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"BaoStock获取实时行情失败: {e}")
            return {"error": str(e)}

    def get_major_news(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """BaoStock不支持新闻，返回空DataFrame"""
        return pd.DataFrame()

    def get_north_money(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """BaoStock不支持北向资金"""
        return pd.DataFrame()

    def get_stock_basic(self, ts_code: str = None) -> pd.DataFrame:
        """获取股票基本信息"""
        self._ensure_login()
        try:
            rs = bs.query_stock_basic()
            if rs.error_code != '0':
                return pd.DataFrame()

            rows = []
            while (rs.error_code == '0') & rs.next():
                rows.append(rs.get_row_data())

            if not rows:
                return pd.DataFrame()

            df = pd.DataFrame(rows, columns=rs.fields)
            if ts_code:
                symbol = ts_code.split('.')[0]
                df = df[df['code'] == symbol]
            return df
        except Exception as e:
            logger.error(f"BaoStock获取股票基本信息失败: {e}")
            return pd.DataFrame()

    def get_limit_list(self, trade_date: str = None) -> pd.DataFrame:
        """BaoStock不支持涨跌停列表"""
        return pd.DataFrame()

    def __del__(self):
        try:
            bs.logout()
        except:
            pass
