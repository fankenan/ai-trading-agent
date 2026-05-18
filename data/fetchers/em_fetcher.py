"""
东方财富 (East Money) 数据获取器

直接调用东方财富 HTTP API，免费无需Token
数据丰富：实时行情、K线、资金流向、龙虎榜、新闻等
"""

import requests
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from loguru import logger


class EMFetcher:
    """东方财富数据获取器"""

    # EM 市场代码映射
    MARKET_MAP = {
        'sh': 1,  # 上海
        'sz': 0,  # 深圳
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://quote.eastmoney.com/',
        })
        logger.info("东方财富数据获取器初始化完成")

    def _to_em_code(self, ts_code: str) -> str:
        """000001.SZ → 0.000001  or  600519.SH → 1.600519"""
        parts = ts_code.split('.')
        market = '0' if parts[1] == 'SZ' else '1'
        return f"{market}.{parts[0]}"

    def _em_market_code(self, ts_code: str) -> str:
        parts = ts_code.split('.')
        return '1' if parts[1] == 'SH' else '0'

    def get_daily(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取日线数据
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

        em_code = self._to_em_code(ts_code)
        market = self._em_market_code(ts_code)
        # 计算需要的K线数量
        days = (datetime.strptime(end_date, "%Y%m%d") - datetime.strptime(start_date, "%Y%m%d")).days

        try:
            url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                'secid': em_code,
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                'klt': '101',  # 日线
                'fqt': '1',    # 前复权
                'beg': start_date,
                'end': end_date,
                'lmt': max(days + 50, 100),
            }

            resp = self.session.get(url, params=params, timeout=15)
            data = resp.json()

            if not data.get('data') or not data['data'].get('klines'):
                logger.warning(f"EM未获取到 {ts_code} K线数据")
                return pd.DataFrame()

            klines = data['data']['klines']
            rows = [line.split(',') for line in klines]

            df = pd.DataFrame(rows, columns=[
                'timestamp', 'open', 'close', 'high', 'low', 'volume',
                'amount', 'amplitude', 'change_pct', 'change', 'turnover'
            ])

            for col in ['open', 'close', 'high', 'low', 'volume', 'amount', 'change_pct', 'change', 'turnover']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            df = df.rename(columns={'amplitude': 'amplitude'})
            df['pre_close'] = df['close'] - df['change']
            df['is_limit_up'] = df['change_pct'] >= 9.9
            df['is_limit_down'] = df['change_pct'] <= -9.9
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['datetime'] = df['timestamp']

            logger.info(f"EM获取 {ts_code} 日线数据: {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"EM获取 {ts_code} 数据失败: {e}")
            return pd.DataFrame()

    def get_realtime_quote(self, ts_code: str) -> Dict[str, Any]:
        """获取实时行情"""
        em_code = self._to_em_code(ts_code)
        symbol = ts_code.split('.')[0]

        try:
            url = "https://push2.eastmoney.com/api/qt/stock/get"
            params = {
                'secid': em_code,
                'fields': 'f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f55,f57,f58,f60,f116,f117,f162,f167,f168,f169,f170,f171',
            }

            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()

            if not data.get('data'):
                return {"error": "未找到股票"}

            d = data['data']

            return {
                "symbol": symbol,
                "name": str(d.get('f58', '')),
                "price": float(d.get('f43', 0) / 100 if d.get('f43') else 0),
                "change_pct": float(d.get('f170', 0) / 100 if d.get('f170') else 0),
                "change": float(d.get('f169', 0) / 100 if d.get('f169') else 0),
                "volume": int(d.get('f47', 0)),
                "amount": float(d.get('f48', 0)),
                "open": float(d.get('f46', 0) / 100 if d.get('f46') else 0),
                "high": float(d.get('f44', 0) / 100 if d.get('f44') else 0),
                "low": float(d.get('f45', 0) / 100 if d.get('f45') else 0),
                "pre_close": float(d.get('f60', 0) / 100 if d.get('f60') else 0),
                "is_limit_up": float(d.get('f170', 0) / 100 if d.get('f170') else 0) >= 9.9,
                "is_limit_down": float(d.get('f170', 0) / 100 if d.get('f170') else 0) <= -9.9,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"EM获取实时行情失败: {e}")
            return {"error": str(e)}

    def get_major_news(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取财经新闻"""
        try:
            url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
            params = {'page_size': 20, 'page_index': 1, 'ann_type': 'A'}
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            if data.get('data', {}).get('list'):
                rows = []
                for item in data['data']['list']:
                    rows.append({
                        'title': item.get('title', ''),
                        'datetime': item.get('notice_date', ''),
                        'src': '东方财富',
                        'content': item.get('summary', ''),
                    })
                return pd.DataFrame(rows)
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"EM获取新闻失败: {e}")
            return pd.DataFrame()

    def get_north_money(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取北向资金流向"""
        try:
            url = "https://push2his.eastmoney.com/api/qt/kamt.kline/get"
            params = {
                'fields1': 'f1,f3,f5',
                'fields2': 'f51,f52,f53,f54',
                'klt': '101',
                'lmt': 30,
            }

            # 沪股通
            params_h = {**params, 'secid': '1.000001'}
            resp_h = self.session.get(url, params=params_h, timeout=10)
            data_h = resp_h.json()

            if data_h.get('data') and data_h['data'].get('klines'):
                klines = data_h['data']['klines']
                rows = []
                for line in klines:
                    parts = line.split(',')
                    rows.append({
                        'date': parts[0],
                        'net_flow': float(parts[1]) / 10000 if len(parts) > 1 else 0,
                    })
                return pd.DataFrame(rows)

            return pd.DataFrame()
        except Exception as e:
            logger.error(f"EM获取北向资金失败: {e}")
            return pd.DataFrame()

    def get_limit_list(self, trade_date: str = None) -> pd.DataFrame:
        """获取涨跌停列表"""
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y%m%d")

        try:
            url = "https://push2ex.eastmoney.com/getTopicZTPool"
            params = {
                'ut': '7eea3edcaed734bea9cbfce24459ed85',
                'PageIndex': 1,
                'PageSize': 50,
                'Date': trade_date,
            }
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            if data.get('data'):
                return pd.DataFrame(data['data'])
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"EM获取涨跌停列表失败: {e}")
            return pd.DataFrame()
