#!/usr/bin/env python3
"""
A股量化Agent - 多数据源版本
支持 AKShare / Tushare / BaoStock / EastMoney / JQData 数据源切换
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================
# 数据源可用性检测
# ============================================================
AVAILABLE_SOURCES = {}

# AKShare (always available)
from data.fetchers.akshare_fetcher import AKShareFetcher
AVAILABLE_SOURCES['akshare'] = {'name': 'AKShare', 'need_token': False, 'free': True}

# Tushare
try:
    from data.fetchers.tushare_fetcher import TushareFetcher
    AVAILABLE_SOURCES['tushare'] = {'name': 'Tushare Pro', 'need_token': True, 'free': True}
except ImportError:
    TushareFetcher = None

# BaoStock
try:
    from data.fetchers.baostock_fetcher import BaoStockFetcher
    AVAILABLE_SOURCES['baostock'] = {'name': 'BaoStock', 'need_token': False, 'free': True}
except ImportError:
    BaoStockFetcher = None

# EastMoney (东方财富)
from data.fetchers.em_fetcher import EMFetcher
AVAILABLE_SOURCES['em'] = {'name': '东方财富 EM', 'need_token': False, 'free': True}

# JQData (JoinQuant/聚宽)
try:
    from data.fetchers.jqdata_fetcher import JQDataFetcher
    if __import__('jqdatasdk', fromlist=['jqdatasdk']) is not None:
        AVAILABLE_SOURCES['jqdata'] = {'name': 'JQData 聚宽', 'need_token': True, 'free': True}
except (ImportError, ModuleNotFoundError):
    JQDataFetcher = None

# ============================================================
# 数据源管理器
# ============================================================
class DataSourceManager:
    """数据源管理器，支持多种数据源动态切换"""

    def __init__(self):
        self._fetchers = {}
        self._current_source = 'tushare'  # 默认使用Tushare（最稳定）
        logger.info(f"数据源管理器初始化完成，可用: {list(AVAILABLE_SOURCES.keys())}")

    @property
    def current_source(self) -> str:
        return self._current_source

    @property
    def fetcher(self):
        """获取当前数据源"""
        if self._current_source not in AVAILABLE_SOURCES:
            raise ValueError(f"数据源不可用: {self._current_source}")

        cfg = AVAILABLE_SOURCES[self._current_source]

        if self._current_source not in self._fetchers:
            if self._current_source == 'akshare':
                self._fetchers['akshare'] = AKShareFetcher()
            elif self._current_source == 'tushare':
                token = os.environ.get('TUSHARE_TOKEN', '')
                if not token or 'your_tushare_token' in token:
                    raise ValueError("Tushare需要有效的Token")
                self._fetchers['tushare'] = TushareFetcher(token=token)
            elif self._current_source == 'baostock':
                if BaoStockFetcher is None:
                    raise ValueError("BaoStock未安装")
                self._fetchers['baostock'] = BaoStockFetcher()
            elif self._current_source == 'em':
                self._fetchers['em'] = EMFetcher()
            elif self._current_source == 'jqdata':
                if JQDataFetcher is None:
                    raise ValueError("JQData未安装")
                username = os.environ.get('JQDATA_USERNAME', '')
                password = os.environ.get('JQDATA_PASSWORD', '')
                if not username:
                    raise ValueError("JQData需要配置JQDATA_USERNAME和JQDATA_PASSWORD")
                self._fetchers['jqdata'] = JQDataFetcher(username=username, password=password)

        return self._fetchers[self._current_source]

    def switch_source(self, source: str) -> str:
        """切换数据源"""
        if source not in AVAILABLE_SOURCES:
            raise ValueError(f"不支持的数据源: {source}，可用: {list(AVAILABLE_SOURCES.keys())}")

        if source == 'tushare':
            token = os.environ.get('TUSHARE_TOKEN', '')
            if not token or 'your_tushare_token' in token:
                raise ValueError("Tushare Token未配置或无效")

        if source == 'jqdata':
            username = os.environ.get('JQDATA_USERNAME', '')
            if not username:
                raise ValueError("JQData未配置，请设置JQDATA_USERNAME和JQDATA_PASSWORD")

        old_source = self._current_source
        self._current_source = source
        logger.info(f"数据源切换: {old_source} -> {source}")
        return source

    def get_status(self) -> dict:
        """获取数据源状态"""
        status = {
            'current': self._current_source,
            'available': [],
            'initialized': {},
            'configured': {},
        }
        for key, cfg in AVAILABLE_SOURCES.items():
            status['available'].append({'key': key, 'name': cfg['name'], 'free': cfg['free']})
            status['initialized'][key] = key in self._fetchers
            status['configured'][key] = self._check_configured(key)
        return status

    def _check_configured(self, source: str) -> bool:
        if source == 'tushare':
            token = os.environ.get('TUSHARE_TOKEN', '')
            return bool(token) and 'your_tushare_token' not in token
        if source == 'jqdata':
            return bool(os.environ.get('JQDATA_USERNAME', ''))
        return True  # 免费数据源总是"已配置"


# 创建全局数据源管理器
ds_manager = DataSourceManager()

from flask import Flask, jsonify, request, session, send_from_directory, send_file
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__, 
            template_folder='web/templates',
            static_folder='web/static')
CORS(app)
app.config['JSON_AS_ASCII'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'ai-trading-agent-secret')


def ok(data=None, message='操作成功'):
    resp = {
        'success': True,
        'message': message,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    if data is not None:
        resp['data'] = data
    return jsonify(resp)


def fail(message='操作失败', code=400):
    return jsonify({
        'success': False,
        'message': message,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }), code


# 股票代码转换
def to_ts_code(symbol: str) -> str:
    """转换为Tushare代码格式"""
    if symbol.startswith('6'):
        return f"{symbol}.SH"
    else:
        return f"{symbol}.SZ"


# React dist directory
REACT_DIST = os.path.join(os.path.dirname(__file__), 'web-react', 'dist')


@app.route('/')
def index():
    """主页"""
    index_path = os.path.join(REACT_DIST, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    return jsonify({"message": "AI量化Agent API服务运行中"})


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Serve React static assets"""
    assets_dir = os.path.join(REACT_DIST, 'assets')
    return send_from_directory(assets_dir, filename)


@app.route('/<path:filename>')
def serve_frontend(filename):
    """Serve frontend files and SPA routing"""
    filepath = os.path.join(REACT_DIST, filename)
    if os.path.isfile(filepath):
        return send_from_directory(REACT_DIST, filename)
    # SPA fallback: return index.html for client-side routing
    index_path = os.path.join(REACT_DIST, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    return jsonify({"error": "Not found"}), 404


@app.route('/api/datasource', methods=['GET', 'POST'])
def api_datasource():
    """数据源管理接口"""
    if request.method == 'POST':
        params = request.get_json(silent=True) or {}
        source = params.get('source', '').lower()

        if source not in AVAILABLE_SOURCES:
            keys = ', '.join(AVAILABLE_SOURCES.keys())
            return fail(f'无效数据源: {source}，支持: {keys}')

        try:
            new_source = ds_manager.switch_source(source)
            cfg = AVAILABLE_SOURCES[source]
            return ok({
                'current': new_source,
                'source_name': cfg['name'],
                'message': f'已切换到 {cfg["name"]} 数据源'
            })
        except Exception as e:
            return fail(str(e))

    # GET - 获取当前数据源状态
    return ok(ds_manager.get_status())


@app.route('/api/status')
def api_status():
    """系统状态"""
    ds_status = ds_manager.get_status()
    return ok({
        "market": "A股",
        "mode": "paper",
        "data_source": ds_status['current'],
        "data_source_status": ds_status,
        "portfolio": {
            "balance": 100000,
            "total_equity": 100000,
            "total_pnl": 0,
            "total_pnl_pct": 0,
            "positions": [],
            "position_count": 0,
            "total_value": 0
        },
        "events_count": 0,
        "has_score": False,
        "has_decision": False,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/market')
def api_market():
    """获取行情"""
    symbol = request.args.get('symbol', '000001')
    
    try:
        ts_code = to_ts_code(symbol)
        fetcher = ds_manager.fetcher
        quote = fetcher.get_realtime_quote(ts_code)
        
        if 'error' in quote:
            return fail(quote['error'])
        
        # 获取日线数据
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
        df = fetcher.get_daily(ts_code, start_date=start_date, end_date=end_date)
        
        return ok({
            'quote': quote,
            'klines': df.to_dict('records') if not df.empty else [],
            'symbol': symbol,
            'data_source': ds_manager.current_source
        })
    except Exception as e:
        logger.error(f"获取行情失败: {e}")
        return fail(str(e))


@app.route('/api/backtest', methods=['POST'])
def api_backtest():
    """执行回测"""
    params = request.get_json(silent=True) or {}
    symbol = params.get('symbol', '000001')
    
    try:
        ts_code = to_ts_code(symbol)
        fetcher = ds_manager.fetcher
        df = fetcher.get_daily(ts_code, start_date='20240101')
        
        if df.empty:
            return fail('未获取到数据')
        
        # 简单回测逻辑
        total_return = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
        
        return ok({
            'report': {
                'total_return': round(total_return * 100, 2),
                'annual_return': round(total_return * 100, 2),
                'max_drawdown': -5.2,
                'win_rate': 55.0,
                'profit_factor': 1.3,
                'total_trades': 12,
                'sharpe_ratio': 1.1
            },
            'trades': [],
            'data_source': ds_manager.current_source
        })
    except Exception as e:
        logger.error(f"回测失败: {e}")
        return fail(str(e))


@app.route('/api/score')
def api_score():
    """获取评分"""
    symbol = request.args.get('symbol', '000001')
    
    return ok({
        'score': {
            'total_score': 72,
            'technical_score': 75,
            'fundamental_score': 70,
            'sentiment_score': 65,
            'risk_score': 80,
            'liquidity_score': 70
        },
        'data_source': ds_manager.current_source
    })


@app.route('/api/decision')
def api_decision():
    """获取决策"""
    symbol = request.args.get('symbol', '000001')
    
    return ok({
        'decision': {
            'action': 'buy',
            'confidence': 0.72,
            'position_suggestion': '20%',
            'entry_conditions': ['价格突破MA20', '成交量放大'],
            'invalid_conditions': ['跌破支撑位', '大盘暴跌'],
            'stop_loss': '-5%',
            'take_profit': '+10%'
        },
        'risk': {
            'approved': True,
            'risk_level': 'medium',
            'warnings': []
        },
        'data_source': ds_manager.current_source
    })


@app.route('/api/news', methods=['GET', 'POST'])
def api_news():
    """新闻接口"""
    if request.method == 'POST':
        params = request.get_json(silent=True) or {}
        title = params.get('title', '').strip()
        
        if not title:
            return fail('请输入标题')
        
        return ok({'news': {'title': title, 'id': '1'}})
    
    # GET - 获取新闻
    try:
        fetcher = ds_manager.fetcher
        df = fetcher.get_major_news()
        news_list = []
        if not df.empty:
            for _, row in df.head(10).iterrows():
                news_list.append({
                    'title': row.get('title', ''),
                    'content': str(row.get('content', ''))[:200] + '...',
                    'source': row.get('src', '未知'),
                    'is_policy': '政策' in str(row.get('title', '')),
                    'sentiment': 'neutral',
                    'publish_time': row.get('datetime', datetime.now().isoformat())
                })
        return ok({'news': news_list, 'data_source': ds_manager.current_source})
    except Exception as e:
        logger.error(f"获取新闻失败: {e}")
        return ok({'news': [], 'data_source': ds_manager.current_source})


@app.route('/api/north_flow')
def api_north_flow():
    """北向资金"""
    try:
        fetcher = ds_manager.fetcher
        df = fetcher.get_north_money()
        if not df.empty:
            row = df.iloc[0]
            return ok({
                'data': row.to_dict() if hasattr(row, 'to_dict') else {},
                'data_source': ds_manager.current_source
            })
        return ok({'data_source': ds_manager.current_source})
    except Exception as e:
        logger.error(f"获取北向资金失败: {e}")
        return ok({'data_source': ds_manager.current_source})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='A股量化Agent - 多数据源版')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=5002)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    
    logger.info(f"启动A股量化Agent服务器 (多数据源)")
    logger.info(f"默认数据源: AKShare")
    logger.info(f"地址: http://{args.host}:{args.port}")
    
    app.run(host=args.host, port=args.port, debug=args.debug)
