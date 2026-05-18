"""
JQData (JoinQuant) 数据获取器

聚宽数据，免费注册每天100万条数据额度
因子数据、财务数据、行业分类丰富
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from loguru import logger

try:
    import jqdatasdk as jq
    JQDATA_AVAILABLE = True
except ImportError:
    JQDATA_AVAILABLE = False


class JQDataFetcher:
    """JQData数据获取器"""

    def __init__(self, username: str = None, password: str = None):
        if not JQDATA_AVAILABLE:
            raise ImportError("jqdatasdk未安装，请运行: pip install jqdatasdk")

        self._username = username
        self._password = password
        self._logged_in = False

        if username and password:
            self._login()

        logger.info("JQData数据获取器初始化完成" + ("" if self._logged_in else " (未登录)"))

    def _login(self):
        try:
            jq.auth(self._username, self._password)
            if jq.is_auth():
                self._logged_in = True
                logger.info("JQData登录成功")
            else:
                logger.warning("JQData登录失败，请检查账号密码")
        except Exception as e:
            logger.warning(f"JQData登录异常: {e}")

    def _ensure_login(self):
        if not self._logged_in:
            raise RuntimeError("JQData未登录，请配置JQDATA_USERNAME和JQDATA_PASSWORD")

    def _to_jq_code(self, ts_code: str) -> str:
        """000001.SZ → 000001.XSHE"""
        parts = ts_code.split('.')
        suffix = 'XSHG' if parts[1] == 'SH' else 'XSHE'
        return f"{parts[0]}.{suffix}"

    def _from_jq_code(self, jq_code: str) -> str:
        """000001.XSHE → 000001.SZ"""
        parts = jq_code.split('.')
        suffix = 'SH' if parts[1] == 'XSHG' else 'SZ'
        return f"{parts[0]}.{suffix}"

    def get_daily(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取日线数据"""
        self._ensure_login()
        jq_code = self._to_jq_code(ts_code)

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        try:
            df = jq.get_price(
                jq_code, start_date=start_date, end_date=end_date,
                frequency='daily',
                fields=['open', 'close', 'high', 'low', 'volume', 'money', 'paused', 'high_limit', 'low_limit'],
                skip_paused=True, fq='pre'
            )

            if df is None or df.empty:
                logger.warning(f"JQData未获取到 {ts_code} 数据")
                return pd.DataFrame()

            df = df.reset_index()
            df = df.rename(columns={
                'index': 'timestamp',
                'money': 'amount',
            })
            df['pre_close'] = df['close'].shift(1)
            df['change'] = df['close'] - df['pre_close']
            df['change_pct'] = (df['change'] / df['pre_close'] * 100).round(4)
            df['is_limit_up'] = df['close'] >= df['high_limit']
            df['is_limit_down'] = df['close'] <= df['low_limit']
            df['datetime'] = df['timestamp']

            logger.info(f"JQData获取 {ts_code} 日线数据: {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"JQData获取 {ts_code} 数据失败: {e}")
            return pd.DataFrame()

    def get_realtime_quote(self, ts_code: str) -> Dict[str, Any]:
        """获取最新行情（用最新日线近似）"""
        self._ensure_login()

        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
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
                "change": float(row.get('change', 0)),
                "volume": float(row.get('volume', 0)),
                "amount": float(row.get('amount', 0)),
                "open": float(row.get('open', 0)),
                "high": float(row.get('high', 0)),
                "low": float(row.get('low', 0)),
                "pre_close": float(row.get('pre_close', 0)),
                "is_limit_up": bool(row.get('is_limit_up', False)),
                "is_limit_down": bool(row.get('is_limit_down', False)),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"JQData获取实时行情失败: {e}")
            return {"error": str(e)}

    def get_major_news(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """JQData不支持直接获取新闻"""
        return pd.DataFrame()

    def get_north_money(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取北向资金"""
        self._ensure_login()

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        try:
            df = jq.get_money_flow(
                '000001.XSHG',  # 上证指数
                start_date=start_date, end_date=end_date,
                fields=['date', 'net_amount_main']
            )
            if df is not None and not df.empty:
                df = df.reset_index()
                df = df.rename(columns={'net_amount_main': 'net_flow'})
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"JQData获取北向资金失败: {e}")
            return pd.DataFrame()

    def get_stock_basic(self, ts_code: str = None) -> pd.DataFrame:
        """获取股票基本信息"""
        self._ensure_login()
        try:
            df = jq.get_all_securities(['stock'], date=datetime.now().strftime("%Y-%m-%d"))
            df = df.reset_index()
            if ts_code:
                jq_code = self._to_jq_code(ts_code)
                df = df[df['index'] == jq_code]
            return df
        except Exception as e:
            logger.error(f"JQData获取股票基本信息失败: {e}")
            return pd.DataFrame()

    def get_limit_list(self, trade_date: str = None) -> pd.DataFrame:
        """获取龙虎榜"""
        self._ensure_login()
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y-%m-%d")

        try:
            df = jq.get_billboard_list(start_date=trade_date, end_date=trade_date)
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.error(f"JQData获取龙虎榜失败: {e}")
            return pd.DataFrame()
