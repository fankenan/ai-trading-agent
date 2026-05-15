"""
A股交易Agent - 主控制器

适配A股市场特点：
- 政策理解优先
- T+1交易制度
- 涨跌停限制
- 北向资金/主力资金监控
"""

import os
import yaml
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from loguru import logger

# 导入A股专用模块
from data.fetchers.ashare_fetcher import AShareFetcher
from data.storage.sqlite_storage import SQLiteStorage
from data.processors.indicators import TechnicalIndicators
from backtest.engine.ashare_backtest_engine import AShareBacktestEngine
from backtest.strategies.ma_strategy import MAStrategy
from backtest.strategies.breakout_strategy import BreakoutStrategy
from backtest.strategies.rsi_strategy import RSIStrategy
from backtest.reports.report_generator import BacktestReportGenerator
from scoring.scoring_system import ScoringSystem
from scoring.weights.ashare_weights import ASHARE_DEFAULT_WEIGHTS
from decision.analyzer.decision_analyzer import DecisionAnalyzer
from risk.rules.ashare_risk_rules import AShareRiskRules
from execution.paper.paper_trader import PaperTrader
from news.sources.news_fetcher import NewsFetcher
from news.classifiers.event_classifier import EventClassifier
from news.filters.dedup_filter import DedupFilter
from reports.report_generator import ReportGenerator
from ai.openai_client import AIClient


class AShareAgent:
    """A股交易Agent主控制器"""
    
    def __init__(self, config_path: str = "config/ashare_config.yaml"):
        """
        初始化A股Agent
        
        Args:
            config_path: A股配置文件路径
        """
        # 加载配置
        self.config = self._load_config(config_path)
        self.mode = self.config.get('mode', 'paper')
        
        # 初始化A股专用数据获取器
        self.fetcher = AShareFetcher()
        self.storage = SQLiteStorage(self.config['data']['storage']['path'])
        self.indicators = TechnicalIndicators()
        
        # 评分系统（使用A股权重）
        self.scoring_system = ScoringSystem(ASHARE_DEFAULT_WEIGHTS)
        self.decision_analyzer = DecisionAnalyzer()
        
        # A股风控规则
        self.risk_rules = AShareRiskRules()
        
        # 模拟交易
        self.paper_trader = PaperTrader(
            self.config['backtest']['initial_capital']
        )
        
        # 新闻监控
        self.news_fetcher = NewsFetcher()
        self.event_classifier = EventClassifier()
        self.dedup_filter = DedupFilter()
        self.report_generator = ReportGenerator()
        
        # AI客户端
        self.ai_client = AIClient()
        
        # 状态存储
        self._market_data: Dict[str, pd.DataFrame] = {}
        self._events: List[Dict] = []
        self._score_result: Optional[Dict] = None
        self._decision: Optional[Dict] = None
        self._stock_info: Dict[str, Dict] = {}
        
        logger.info(f"A股Agent初始化完成，模式: {self.mode}")
    
    def _load_config(self, config_path: str) -> Dict:
        """加载YAML配置"""
        import pandas as pd
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
            return self._default_config()
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _default_config(self) -> Dict:
        """默认A股配置"""
        return {
            'mode': 'paper',
            'market': {'symbols': ['000001', '000002']},
            'data': {'storage': {'path': 'data/storage/ashare_data.db'}},
            'backtest': {
                'initial_capital': 100000,
                'commission_rate': 0.00025,
                'stamp_tax_rate': 0.001,
                'min_commission': 5,
                'min_trade_unit': 100
            }
        }
    
    # === 数据层方法 ===
    
    def fetch_market_data(self, symbol: str = "000001", days: int = 365) -> Dict:
        """
        获取A股行情数据
        
        Args:
            symbol: 股票代码，如 "000001"
            days: 获取天数
        """
        logger.info(f"获取A股 {symbol} 行情数据...")
        try:
            # 获取K线数据
            df = self.fetcher.get_klines(symbol=symbol, days=days)
            
            if df is not None and not df.empty:
                # 添加技术指标
                df = self.indicators.add_all_indicators(df)
                
                # 存储到数据库
                self.storage.save_klines(df, symbol, 'daily')
                self._market_data[symbol] = df
                
                # 获取股票基本信息
                self._stock_info[symbol] = self.fetcher.get_stock_info(symbol)
                
                logger.info(f"获取成功: {symbol}, {len(df)} 条数据")
                return {"success": True, "count": len(df), "symbol": symbol}
            
            return {"success": False, "error": "未获取到数据"}
            
        except Exception as e:
            logger.error(f"获取行情失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_realtime_quote(self, symbol: str) -> Dict:
        """获取A股实时行情"""
        return self.fetcher.get_realtime_quote(symbol)
    
    def get_policy_news(self) -> List[Dict]:
        """获取政策新闻"""
        return self.fetcher.get_policy_news()
    
    def get_north_flow(self) -> Dict:
        """获取北向资金流向"""
        return self.fetcher.get_north_south_flow()
    
    # === 回测层方法 ===
    
    def run_backtest(
        self,
        symbol: str = "000001",
        strategy_name: str = "ma",
        days: int = 365
    ) -> Dict:
        """
        执行A股回测
        
        Args:
            symbol: 股票代码
            strategy_name: 策略名称 ma/breakout/rsi
            days: 回测天数
        """
        logger.info(f"执行A股回测: {symbol} {strategy_name}策略")
        
        # 获取数据
        data_result = self.fetch_market_data(symbol, days)
        if not data_result['success']:
            return {"success": False, "error": "数据获取失败"}
        
        df = self._market_data[symbol]
        
        # 获取股票信息（判断ST/创业板）
        stock_info = self._stock_info.get(symbol, {})
        is_st = stock_info.get('is_st', False)
        is_cyb = symbol.startswith('300')  # 创业板代码以300开头
        
        # 选择策略
        strategies = {
            'ma': MAStrategy(),
            'breakout': BreakoutStrategy(),
            'rsi': RSIStrategy()
        }
        strategy = strategies.get(strategy_name, MAStrategy())
        
        # 执行A股回测
        engine = AShareBacktestEngine(
            initial_capital=self.config['backtest']['initial_capital'],
            is_st=is_st,
            is_cyb=is_cyb
        )
        
        result = engine.run(df, strategy)
        
        # 生成报告
        report_gen = BacktestReportGenerator()
        report = report_gen.generate(result, strategy.name)
        
        return {
            "success": True,
            "report": report,
            "result": result.to_dict(),
            "ashare_specific": {
                "limit_up_entries": result.limit_up_entries,
                "limit_down_exits": result.limit_down_exits,
                "t1_blocked_exits": result.t1_blocked_exits,
                "avg_holding_days": result.avg_holding_days
            }
        }
    
    # === 风控检查 ===
    
    def check_risk(self, symbol: str, action: str = "buy") -> Dict:
        """
        A股风控检查
        
        Args:
            symbol: 股票代码
            action: buy/sell
        """
        checks = []
        
        # 1. 检查ST风险
        stock_info = self._stock_info.get(symbol, {})
        checks.append(self.risk_rules.check_st_risk(stock_info))
        
        # 2. 检查停牌
        suspend_info = self.fetcher.get_suspend_info(symbol)
        checks.append(self.risk_rules.check_suspend_risk(suspend_info))
        
        # 3. 检查涨跌停
        is_entry = (action == "buy")
        checks.append(self.risk_rules.check_limit_up_risk(stock_info, is_entry))
        
        # 4. 检查政策风险
        checks.append(self.risk_rules.check_policy_risk(self._events))
        
        # 汇总结果
        failed_checks = [c for c in checks if not c.get('pass', True)]
        
        return {
            "approved": len(failed_checks) == 0,
            "risk_level": "critical" if any(c.get('risk_level') == 'critical' for c in failed_checks) else "high" if failed_checks else "low",
            "checks": checks,
            "warnings": [c['reason'] for c in failed_checks if c.get('risk_level') == 'high'],
            "vetoes": [c['reason'] for c in failed_checks if c.get('risk_level') == 'critical']
        }
    
    # === 新闻监控 ===
    
    def add_news_event(self, title: str, content: str = "", source: str = "manual") -> Dict:
        """添加新闻事件"""
        try:
            event = self.news_fetcher.parse_event(title, content, source)
            classified = self.event_classifier.classify(event)
            self._events = self.dedup_filter.filter(self._events + [classified])
            
            # 如果是政策相关，使用AI分析
            if classified.get('is_policy_related', False):
                ai_analysis = self.ai_client.analyze_news(f"{title}\n{content}")
                classified['ai_analysis'] = ai_analysis
            
            logger.info(f"事件已添加: {title}, 等级: {classified.get('level', 'N/A')}")
            return {"success": True, "event": classified}
        except Exception as e:
            logger.error(f"添加事件失败: {e}")
            return {"success": False, "error": str(e)}
    
    # === 评分与决策 ===
    
    def calculate_score(self, symbol: str = "000001") -> Dict:
        """计算综合评分"""
        df = self._market_data.get(symbol)
        if df is None or df.empty:
            return {"success": False, "error": "无市场数据"}
        
        # 获取北向资金作为情绪指标
        north_flow = self.get_north_flow()
        
        self._score_result = self.scoring_system.calculate(
            df=df,
            events=self._events,
            fear_greed=north_flow  # 用北向资金代替恐惧贪婪指数
        )
        
        return {"success": True, "score": self._score_result}
    
    def make_decision(self, symbol: str = "000001") -> Dict:
        """生成交易决策"""
        # 先计算评分
        score_result = self.calculate_score(symbol)
        if not score_result['success']:
            return score_result
        
        # 获取当前价格
        quote = self.get_realtime_quote(symbol)
        current_price = quote.get('price', 0)
        
        # 获取持仓
        portfolio = self.paper_trader.get_portfolio()
        
        # 生成决策
        self._decision = self.decision_analyzer.analyze(
            score_result=self._score_result,
            current_price=current_price,
            position=portfolio
        )
        
        # 风控检查
        action = self._decision.get('action', 'hold')
        risk_check = self.check_risk(symbol, action)
        
        return {
            "success": True,
            "decision": self._decision,
            "risk": risk_check
        }
    
    # === 状态查询 ===
    
    def get_status(self) -> Dict:
        """获取系统状态"""
        return {
            "mode": self.mode,
            "market": "A股",
            "symbols": list(self._market_data.keys()),
            "events_count": len(self._events),
            "has_score": self._score_result is not None,
            "has_decision": self._decision is not None,
            "portfolio": self.paper_trader.get_portfolio(),
            "timestamp": datetime.now().isoformat()
        }


# 兼容原有接口
if __name__ == "__main__":
    agent = AShareAgent()
    print(agent.get_status())
