"""
AI量化交易Agent - 主控制器
串联数据层、回测层、新闻监控层、评分系统、决策层、风控层、执行层
"""
import yaml
import json
from datetime import datetime
from pathlib import Path
from loguru import logger

# 导入所有模块
from data.fetchers.akshare_fetcher import AKShareFetcher
from data.storage.sqlite_storage import SQLiteStorage
from data.processors.indicators import TechnicalIndicators
from backtest.engine.backtest_engine import BacktestEngine
from backtest.strategies.ma_strategy import MAStrategy
from backtest.strategies.breakout_strategy import BreakoutStrategy
from backtest.strategies.rsi_strategy import RSIStrategy
from backtest.reports.report_generator import BacktestReportGenerator
from scoring.scoring_system import ScoringSystem
from scoring.weights.default_weights import DEFAULT_WEIGHTS
from decision.analyzer.decision_analyzer import DecisionAnalyzer
from risk.validator.risk_validator import RiskValidator
from execution.paper.paper_trader import PaperTrader
from news.sources.news_fetcher import NewsFetcher
from news.classifiers.event_classifier import EventClassifier
from news.filters.dedup_filter import DedupFilter
from reports.report_generator import ReportGenerator
from ai.openai_client import AIClient


class TradingAgent:
    """AI量化交易Agent主控制器"""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初始化Agent，加载配置并初始化所有模块

        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        self.config = self._load_config(config_path)
        self.mode = self.config.get('mode', 'paper')

        # 初始化各层模块
        self.fetcher = AKShareFetcher()
        self.storage = SQLiteStorage(self.config['data']['storage']['path'])
        self.indicators = TechnicalIndicators()
        self.scoring_system = ScoringSystem(DEFAULT_WEIGHTS)
        self.decision_analyzer = DecisionAnalyzer()
        self.risk_validator = RiskValidator(self.config.get('risk', {}))
        self.paper_trader = PaperTrader(
            self.config['backtest']['initial_capital']
        )
        self.news_fetcher = NewsFetcher()
        self.event_classifier = EventClassifier()
        self.dedup_filter = DedupFilter()
        self.report_generator = ReportGenerator()
        
        # 初始化AI客户端（从环境变量读取DeepSeek配置）
        self.ai_client = AIClient()

        # 状态存储
        self._market_data: dict = {}
        self._events: list = []
        self._score_result: dict | None = None
        self._decision: dict | None = None
        self._risk_result: dict | None = None
        self._backtest_result = None

        logger.info(f"AI量化Agent初始化完成，模式: {self.mode}")

    def _load_config(self, config_path: str) -> dict:
        """加载YAML配置文件"""
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
            return self._default_config()
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _default_config(self) -> dict:
        """默认配置"""
        return {
            'mode': 'paper',
            'market': {'symbols': ['BTC/USDT', 'ETH/USDT']},
            'data': {'storage': {'path': 'data/storage/market_data.db'}},
            'backtest': {'initial_capital': 10000, 'fee_rate': 0.001, 'slippage': 0.0005},
            'risk': {'max_position_size': 0.20, 'max_daily_loss': 0.05, 'max_drawdown': 0.15}
        }

    # === 数据层方法 ===

    def fetch_market_data(self, symbol: str = "btc", period: str = "daily", days: int = 90) -> dict:
        """
        获取市场数据

        Args:
            symbol: 币种符号
            period: 周期 daily/hourly
            days: 天数
        """
        logger.info(f"获取 {symbol} {period} 市场数据...")
        try:
            df = self.fetcher.get_klines(symbol=symbol, period=period, days=days)
            if df is not None and not df.empty:
                # 添加技术指标
                df = self.indicators.add_all_indicators(df)
                # 存储到数据库
                self.storage.save_klines(df, symbol, period)
                self._market_data[symbol] = df
                logger.info(f"获取成功: {len(df)} 条数据")
                return {"success": True, "count": len(df), "symbol": symbol}
            return {"success": False, "error": "未获取到数据"}
        except Exception as e:
            logger.error(f"获取市场数据失败: {e}")
            return {"success": False, "error": str(e)}

    def get_market_snapshot(self, symbols: list = None) -> dict:
        """获取市场快照"""
        if symbols is None:
            symbols = ["btc", "eth"]
        return self.fetcher.get_market_snapshot(symbols)

    def get_fear_greed(self) -> dict:
        """获取恐惧贪婪指数"""
        try:
            return self.fetcher.get_fear_greed_index()
        except Exception as e:
            logger.error(f"获取恐惧贪婪指数失败: {e}")
            return {"value": 50, "classification": "中性"}

    # === 回测层方法 ===

    def run_backtest(self, symbol: str = "btc", strategy_name: str = "ma", period: str = "daily", days: int = 90) -> dict:
        """
        执行回测

        Args:
            symbol: 币种
            strategy_name: 策略名称 ma/breakout/rsi
            period: 周期
            days: 天数
        """
        logger.info(f"执行回测: {symbol} {strategy_name}策略")

        # 获取数据
        data_result = self.fetch_market_data(symbol, period, days)
        if not data_result['success']:
            return {"success": False, "error": "数据获取失败"}

        df = self._market_data[symbol]

        # 选择策略
        strategies = {
            'ma': MAStrategy(),
            'breakout': BreakoutStrategy(),
            'rsi': RSIStrategy()
        }
        strategy = strategies.get(strategy_name, MAStrategy())

        # 执行回测
        engine = BacktestEngine(
            initial_capital=self.config['backtest']['initial_capital'],
            fee_rate=self.config['backtest']['fee_rate'],
            slippage=self.config['backtest']['slippage']
        )

        result = engine.run(df, strategy)
        self._backtest_result = result

        # 生成报告
        report_gen = BacktestReportGenerator()
        report = report_gen.generate(result, strategy.name)

        return {"success": True, "report": report, "result": result.to_dict()}

    # === 新闻监控方法 ===

    def add_news_event(self, title: str, content: str = "", source: str = "manual") -> dict:
        """
        添加新闻事件

        Args:
            title: 新闻标题
            content: 新闻内容
            source: 来源
        """
        try:
            # 解析事件
            event = self.news_fetcher.parse_event(title, content, source)
            # 分类
            classified = self.event_classifier.classify(event)
            # 去重
            self._events = self.dedup_filter.filter(self._events + [classified])

            logger.info(f"事件已添加: {title}, 等级: {classified.get('level', 'N/A')}")
            return {"success": True, "event": classified}
        except Exception as e:
            logger.error(f"添加事件失败: {e}")
            return {"success": False, "error": str(e)}

    # === 评分方法 ===

    def calculate_score(self, symbol: str = "btc") -> dict:
        """
        计算综合评分

        Args:
            symbol: 币种
        """
        df = self._market_data.get(symbol)
        if df is None or df.empty:
            return {"success": False, "error": "无市场数据，请先获取数据"}

        fear_greed = self.get_fear_greed()

        self._score_result = self.scoring_system.calculate(
            df=df,
            events=self._events,
            fear_greed=fear_greed
        )

        return {"success": True, "score": self._score_result}

    # === 决策方法 ===

    def make_decision(self, symbol: str = "btc") -> dict:
        """
        生成交易决策

        Args:
            symbol: 币种
        """
        # 先计算评分
        score_result = self.calculate_score(symbol)
        if not score_result['success']:
            return score_result

        # 获取当前价格
        snapshot = self.get_market_snapshot([symbol])
        symbol_data = snapshot.get(symbol, {})
        current_price = symbol_data.get('price', 0) if symbol_data else 0

        # 获取当前持仓
        portfolio = self.paper_trader.get_portfolio()

        # 生成决策
        self._decision = self.decision_analyzer.analyze(
            score_result=self._score_result,
            current_price=current_price,
            position=portfolio
        )

        # 风控验证
        self._risk_result = self.risk_validator.validate(
            decision=self._decision,
            portfolio=portfolio,
            events=self._events
        )

        return {
            "success": True,
            "decision": self._decision,
            "risk": self._risk_result
        }

    # === 执行方法 ===

    def execute_decision(self, symbol: str = "btc") -> dict:
        """
        执行决策（模拟交易）

        Args:
            symbol: 币种
        """
        if self._decision is None:
            return {"success": False, "error": "请先生成决策"}

        if not self._risk_result.get('approved', False):
            return {"success": False, "error": "风控未通过", "risk": self._risk_result}

        if self.mode != 'paper':
            return {"success": False, "error": "当前仅支持模拟交易模式"}

        snapshot = self.get_market_snapshot([symbol])
        symbol_data = snapshot.get(symbol, {})
        current_price = symbol_data.get('price', 0) if symbol_data else 0

        result = self.paper_trader.execute(self._decision, current_price)
        return {"success": True, "execution": result}

    # === 报告方法 ===

    def generate_report(self, report_type: str = "daily", symbol: str = "btc") -> dict:
        """
        生成报告

        Args:
            report_type: daily/backtest
            symbol: 币种
        """
        if report_type == "backtest" and self._backtest_result:
            gen = BacktestReportGenerator()
            report = gen.generate(self._backtest_result, "backtest")
            return {"success": True, "report": report}

        # 日报
        report = self.report_generator.generate_daily(
            market_data=self._market_data,
            score=self._score_result,
            decision=self._decision,
            risk=self._risk_result,
            portfolio=self.paper_trader.get_portfolio()
        )
        return {"success": True, "report": report}

    # === 状态方法 ===

    def get_status(self) -> dict:
        """获取系统状态"""
        return {
            "mode": self.mode,
            "symbols": list(self._market_data.keys()),
            "events_count": len(self._events),
            "has_score": self._score_result is not None,
            "has_decision": self._decision is not None,
            "portfolio": self.paper_trader.get_portfolio(),
            "timestamp": datetime.now().isoformat()
        }

    def get_portfolio(self) -> dict:
        """获取模拟交易持仓"""
        return self.paper_trader.get_portfolio()

    def get_trade_history(self) -> list:
        """获取交易历史"""
        return self.paper_trader.get_trade_history()
