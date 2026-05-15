"""
A股数据获取器

基于AKShare获取A股行情、财务数据、公告信息等
适配A股特殊规则：T+1、涨跌停、停牌等
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger


class AShareFetcher:
    """A股数据获取器"""
    
    def __init__(self):
        self._cache = {}
        logger.info("A股数据获取器初始化完成")
    
    def get_stock_list(self) -> pd.DataFrame:
        """获取A股所有股票列表"""
        try:
            df = ak.stock_zh_a_spot_em()
            logger.info(f"获取A股列表: {len(df)} 只股票")
            return df
        except Exception as e:
            logger.error(f"获取A股列表失败: {e}")
            return pd.DataFrame()
    
    def get_klines(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq",
        days: Optional[int] = None  # 新增days参数
    ) -> pd.DataFrame:
        """
        获取A股K线数据
        
        Args:
            symbol: 股票代码，如 "000001" (平安银行)
            period: daily/weekly/monthly
            start_date: 开始日期，格式 "YYYYMMDD"
            end_date: 结束日期，格式 "YYYYMMDD"
            adjust: qfq(前复权)/hfq(后复权)/不复权
            days: 获取天数（会覆盖start_date）
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        if days is not None:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        elif start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        
        try:
            # AKShare获取历史行情
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            
            if df.empty:
                logger.warning(f"未获取到数据: {symbol}")
                return pd.DataFrame()
            
            # 统一列名
            df = df.rename(columns={
                "日期": "timestamp",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
                "振幅": "amplitude",
                "涨跌幅": "change_pct",
                "涨跌额": "change",
                "换手率": "turnover"
            })
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['datetime'] = df['timestamp']
            df['symbol'] = symbol
            
            # 添加A股特有字段
            df['is_limit_up'] = df['change_pct'] >= 9.9  # 涨停
            df['is_limit_down'] = df['change_pct'] <= -9.9  # 跌停
            
            logger.info(f"获取 {symbol} K线: {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} K线失败: {e}")
            return pd.DataFrame()
    
    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        """获取A股实时行情"""
        try:
            df = ak.stock_zh_a_spot_em()
            stock = df[df['代码'] == symbol]
            
            if stock.empty:
                return {"error": f"未找到股票: {symbol}"}
            
            row = stock.iloc[0]
            return {
                "symbol": symbol,
                "name": row.get('名称', ''),
                "price": float(row.get('最新价', 0)),
                "change_pct": float(row.get('涨跌幅', 0)),
                "change": float(row.get('涨跌额', 0)),
                "volume": float(row.get('成交量', 0)),
                "amount": float(row.get('成交额', 0)),
                "open": float(row.get('今开', 0)),
                "high": float(row.get('最高', 0)),
                "low": float(row.get('最低', 0)),
                "pre_close": float(row.get('昨收', 0)),
                "turnover": float(row.get('换手率', 0)),
                "pe": float(row.get('市盈率-动态', 0)) if pd.notna(row.get('市盈率-动态')) else None,
                "pb": float(row.get('市净率', 0)) if pd.notna(row.get('市净率')) else None,
                "market_cap": float(row.get('总市值', 0)) if pd.notna(row.get('总市值')) else None,
                "is_limit_up": row.get('涨跌幅', 0) >= 9.9,
                "is_limit_down": row.get('涨跌幅', 0) <= -9.9,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            return {"error": str(e)}
    
    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """获取股票基本信息"""
        try:
            # 个股信息
            info = ak.stock_individual_info_em(symbol=symbol)
            
            result = {}
            for _, row in info.iterrows():
                result[row['item']] = row['value']
            
            # 获取风险信息
            df_spot = ak.stock_zh_a_spot_em()
            stock_spot = df_spot[df_spot['代码'] == symbol]
            
            if not stock_spot.empty:
                row = stock_spot.iloc[0]
                result['is_st'] = 'ST' in str(row.get('名称', ''))
                result['is_limit_up'] = float(row.get('涨跌幅', 0)) >= 9.9
                result['is_limit_down'] = float(row.get('涨跌幅', 0)) <= -9.9
            
            return result
        except Exception as e:
            logger.error(f"获取股票信息失败: {e}")
            return {}
    
    def get_suspend_info(self, symbol: str) -> Dict[str, Any]:
        """获取停牌信息"""
        try:
            # 获取停牌股票列表
            suspend_df = ak.stock_tfp_em(date=datetime.now().strftime("%Y%m%d"))
            
            if suspend_df.empty:
                return {"is_suspended": False}
            
            stock_suspend = suspend_df[suspend_df['代码'] == symbol]
            
            if stock_suspend.empty:
                return {"is_suspended": False}
            
            row = stock_suspend.iloc[0]
            return {
                "is_suspended": True,
                "suspend_date": row.get('停牌日期', ''),
                "suspend_reason": row.get('停牌原因', ''),
                "resume_date": row.get('预计复牌日期', '')
            }
        except Exception as e:
            logger.error(f"获取停牌信息失败: {e}")
            return {"is_suspended": False, "error": str(e)}
    
    def get_policy_news(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取政策新闻（宏观经济/政策）"""
        try:
            # 财经新闻
            news_df = ak.stock_news_em()
            
            if news_df.empty:
                return []
            
            # 筛选政策相关新闻
            policy_keywords = ['政策', '监管', '央行', '证监会', '国务院', '财政部']
            
            results = []
            for _, row in news_df.head(50).iterrows():
                title = str(row.get('标题', ''))
                content = str(row.get('内容', ''))
                
                # 检查是否包含政策关键词
                is_policy = any(kw in title or kw in content for kw in policy_keywords)
                
                results.append({
                    "title": title,
                    "content": content[:500] + "..." if len(content) > 500 else content,
                    "time": row.get('发布时间', ''),
                    "source": row.get('来源', ''),
                    "is_policy_related": is_policy,
                    "url": row.get('链接', '')
                })
            
            # 优先返回政策相关新闻
            policy_news = [n for n in results if n['is_policy_related']]
            
            logger.info(f"获取政策新闻: {len(policy_news)} 条")
            return policy_news
            
        except Exception as e:
            logger.error(f"获取政策新闻失败: {e}")
            return []
    
    def get_announcement(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """获取个股公告"""
        try:
            # 个股公告
            ann_df = ak.stock_notice_report(symbol=symbol)
            
            if ann_df.empty:
                return []
            
            results = []
            for _, row in ann_df.head(20).iterrows():
                results.append({
                    "title": row.get('公告标题', ''),
                    "type": row.get('公告类型', ''),
                    "date": row.get('公告日期', ''),
                    "url": row.get('公告链接', '')
                })
            
            return results
        except Exception as e:
            logger.error(f"获取公告失败: {e}")
            return []
    
    def get_sector_flow(self) -> pd.DataFrame:
        """获取板块资金流向"""
        try:
            # 行业资金流向
            df = ak.stock_sector_fund_flow_rank()
            logger.info(f"获取板块资金流向: {len(df)} 个板块")
            return df
        except Exception as e:
            logger.error(f"获取板块资金流向失败: {e}")
            return pd.DataFrame()
    
    def get_north_south_flow(self) -> Dict[str, Any]:
        """获取北向资金流向"""
        try:
            # 北向资金
            df = ak.stock_hsgt_hist_em(symbol="北向资金")
            
            if df.empty:
                return {}
            
            latest = df.iloc[-1]
            return {
                "date": latest.get('日期', ''),
                "net_inflow": float(latest.get('净流入', 0)),
                "buy_amount": float(latest.get('买入成交额', 0)),
                "sell_amount": float(latest.get('卖出成交额', 0)),
                "cumulative": float(latest.get('历史累计净流入', 0))
            }
        except Exception as e:
            logger.error(f"获取北向资金失败: {e}")
            return {}
