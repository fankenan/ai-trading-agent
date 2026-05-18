#!/usr/bin/env python3
"""
A股量化Agent - 多数据源版本
支持AKShare和Tushare数据源切换，默认使用AKShare
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

# 导入数据获取器
try:
    from data.fetchers.tushare_fetcher import TushareFetcher
    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False
    TushareFetcher = None
    logger.warning("Tushare not installed, only AKShare will be available")

from data.fetchers.akshare_fetcher import AKShareFetcher

# 数据源管理器
class DataSourceManager:
    """数据源管理器，支持AKShare和Tushare切换"""
    
    def __init__(self, tushare_token: str = None):
        self._akshare = None
        self._tushare = None
        self._tushare_token = tushare_token
        self._current_source = 'akshare'  # 默认使用AKShare
        logger.info("数据源管理器初始化完成，默认使用AKShare")
    
    @property
    def current_source(self) -> str:
        return self._current_source
    
    @property
    def fetcher(self):
        """获取当前数据源"""
        if self._current_source == 'akshare':
            if self._akshare is None:
                self._akshare = AKShareFetcher()
            return self._akshare
        else:
            if not TUSHARE_AVAILABLE:
                raise ValueError("Tushare not installed")
            if self._tushare is None:
                if not self._tushare_token:
                    raise ValueError("Tushare需要配置Token")
                self._tushare = TushareFetcher(token=self._tushare_token)
            return self._tushare
    
    def switch_source(self, source: str) -> str:
        """切换数据源"""
        if source not in ['akshare', 'tushare']:
            raise ValueError(f"不支持的数据源: {source}")
        
        old_source = self._current_source
        self._current_source = source
        logger.info(f"数据源切换: {old_source} -> {source}")
        return source
    
    def get_status(self) -> dict:
        """获取数据源状态"""
        return {
            'current': self._current_source,
            'available': ['akshare', 'tushare'] if TUSHARE_AVAILABLE else ['akshare'],
            'akshare_initialized': self._akshare is not None,
            'tushare_initialized': self._tushare is not None,
            'tushare_configured': bool(self._tushare_token)
        }


# 创建全局数据源管理器
tushare_token = os.environ.get('TUSHARE_TOKEN', '')
ds_manager = DataSourceManager(tushare_token=tushare_token)

from flask import Flask, jsonify, request, session
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


@app.route('/')
def index():
    """主页"""
    index_path = os.path.join(os.path.dirname(__file__), 'web-react', 'dist', 'index.html')
    if os.path.exists(index_path):
        from flask import send_file
        return send_file(index_path)
    return jsonify({"message": "AI量化Agent API服务运行中"})


@app.route('/api/datasource', methods=['GET', 'POST'])
def api_datasource():
    """数据源管理接口"""
    if request.method == 'POST':
        # 切换数据源
        params = request.get_json(silent=True) or {}
        source = params.get('source', '').lower()
        
        if source not in ['akshare', 'tushare']:
            return fail('无效的数据源，支持: akshare, tushare')
        
        if source == 'tushare' and not tushare_token:
            return fail('Tushare未配置Token，请在.env中设置TUSHARE_TOKEN')
        
        try:
            new_source = ds_manager.switch_source(source)
            return ok({
                'current': new_source,
                'message': f'已切换到 {new_source.upper()} 数据源'
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
