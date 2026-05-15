# -*- coding: utf-8 -*-
"""
AI量化交易Agent系统 - Flask Web应用主文件
提供Dashboard界面和REST API接口，通过TradingAgent主控模块串联所有子系统
"""

import os
import sys
import json
import logging
import traceback
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# 加载环境变量（支持DeepSeek API等配置）
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# 将项目根目录添加到系统路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 导入主控Agent
from agent.trading_agent import TradingAgent

# 配置日志
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))
CORS(app)

# 应用配置
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ai-trading-agent-secret-key-2024')
app.config['JSON_AS_ASCII'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# ============================================================
# 全局Agent实例
# ============================================================
_agent: TradingAgent = None


def get_agent() -> TradingAgent:
    """获取全局Agent实例（懒加载）"""
    global _agent
    if _agent is None:
        config_path = os.path.join(PROJECT_ROOT, 'config', 'config.yaml')
        _agent = TradingAgent(config_path=config_path)
        logger.info("TradingAgent 初始化完成")
    return _agent


# ============================================================
# 辅助函数
# ============================================================

def handle_errors(f):
    """API错误处理装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"API异常 [{f.__name__}]: {e}\n{traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': f'服务器内部错误: {str(e)}'
            }), 500
    return decorated_function


def ok(data=None, message='操作成功'):
    """构建成功响应"""
    resp = {'success': True, 'message': message, 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    if data is not None:
        resp['data'] = data
    return jsonify(resp)


def fail(message='操作失败', code=400):
    """构建错误响应"""
    return jsonify({
        'success': False, 'message': message,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }), code


# ============================================================
# 页面路由
# ============================================================

@app.route('/')
def index():
    """主页Dashboard"""
    return render_template('index.html')


# ============================================================
# 市场数据API
# ============================================================

@app.route('/api/market', methods=['GET'])
@handle_errors
def api_market():
    """
    获取市场数据
    参数: symbol(btc/eth), period(daily/hourly), days(天数)
    """
    symbol = request.args.get('symbol', 'btc')
    period = request.args.get('period', 'daily')
    days = int(request.args.get('days', 90))

    agent = get_agent()

    # 获取K线数据
    fetch_result = agent.fetch_market_data(symbol=symbol, period=period, days=days)

    # 获取市场快照
    snapshot = agent.get_market_snapshot([symbol])

    # 获取恐惧贪婪指数
    fear_greed = agent.get_fear_greed()

    # 获取存储的K线数据用于前端展示
    klines = []
    df = agent._market_data.get(symbol)
    if df is not None and not df.empty:
        for _, row in df.tail(200).iterrows():
            klines.append({
                'timestamp': str(row.get('timestamp', '')),
                'open': float(row.get('open', 0)),
                'high': float(row.get('high', 0)),
                'low': float(row.get('low', 0)),
                'close': float(row.get('close', 0)),
                'volume': float(row.get('volume', 0)),
            })

    # 技术指标摘要
    indicators_summary = {}
    if df is not None and not df.empty:
        last = df.iloc[-1]
        indicators_summary = {
            'ma_5': float(last.get('ma_5', 0)) if 'ma_5' in df.columns else None,
            'ma_20': float(last.get('ma_20', 0)) if 'ma_20' in df.columns else None,
            'ma_60': float(last.get('ma_60', 0)) if 'ma_60' in df.columns else None,
            'rsi_14': float(last.get('rsi_14', 0)) if 'rsi_14' in df.columns else None,
            'macd': float(last.get('macd', 0)) if 'macd' in df.columns else None,
            'macd_signal': float(last.get('macd_signal', 0)) if 'macd_signal' in df.columns else None,
            'macd_hist': float(last.get('macd_hist', 0)) if 'macd_hist' in df.columns else None,
            'bollinger_upper': float(last.get('bollinger_upper', 0)) if 'bollinger_upper' in df.columns else None,
            'bollinger_middle': float(last.get('bollinger_middle', 0)) if 'bollinger_middle' in df.columns else None,
            'bollinger_lower': float(last.get('bollinger_lower', 0)) if 'bollinger_lower' in df.columns else None,
        }

    return ok({
        'fetch_result': fetch_result,
        'snapshot': snapshot,
        'fear_greed': fear_greed,
        'klines': klines,
        'indicators': indicators_summary,
        'symbol': symbol,
        'period': period,
    })


# ============================================================
# 回测系统API
# ============================================================

@app.route('/api/backtest', methods=['POST'])
@handle_errors
def api_backtest():
    """
    执行回测
    请求体: {strategy, symbol, period, days}
    """
    params = request.get_json(silent=True) or {}
    strategy_name = params.get('strategy', 'ma')
    symbol = params.get('symbol', 'btc')
    period = params.get('period', 'daily')
    days = int(params.get('days', 90))

    agent = get_agent()
    result = agent.run_backtest(
        symbol=symbol,
        strategy_name=strategy_name,
        period=period,
        days=days
    )

    if not result.get('success'):
        return fail(result.get('error', '回测失败'))

    return ok(result, message='回测执行完成')


@app.route('/api/backtest/result', methods=['GET'])
@handle_errors
def api_backtest_result():
    """获取最近回测结果"""
    agent = get_agent()
    if agent._backtest_result is None:
        return fail('暂无回测结果')
    return ok(agent._backtest_result.to_dict())


# ============================================================
# 新闻事件API
# ============================================================

@app.route('/api/news', methods=['POST'])
@handle_errors
def api_news():
    """
    提交新闻事件
    请求体: {title, content, source}
    """
    params = request.get_json(silent=True) or {}
    title = params.get('title', '').strip()
    content = params.get('content', '').strip()
    source = params.get('source', '手动输入')

    if not title:
        return fail('请输入新闻标题')

    agent = get_agent()
    result = agent.add_news_event(title=title, content=content, source=source)

    if not result.get('success'):
        return fail(result.get('error', '事件处理失败'))

    return ok(result, message='新闻事件已处理')


@app.route('/api/news', methods=['GET'])
@handle_errors
def api_news_list():
    """获取已处理的事件列表"""
    agent = get_agent()
    return ok({'events': agent._events})


# ============================================================
# 评分系统API
# ============================================================

@app.route('/api/score', methods=['GET'])
@handle_errors
def api_score():
    """
    获取评分
    参数: symbol(btc/eth)
    """
    symbol = request.args.get('symbol', 'btc')

    agent = get_agent()
    result = agent.calculate_score(symbol=symbol)

    if not result.get('success'):
        return fail(result.get('error', '评分失败'))

    return ok(result)


# ============================================================
# 决策系统API
# ============================================================

@app.route('/api/decision', methods=['GET'])
@handle_errors
def api_decision():
    """
    获取决策
    参数: symbol(btc/eth)
    """
    symbol = request.args.get('symbol', 'btc')

    agent = get_agent()
    result = agent.make_decision(symbol=symbol)

    if not result.get('success'):
        return fail(result.get('error', '决策生成失败'))

    return ok(result)


# ============================================================
# 模拟交易API
# ============================================================

@app.route('/api/portfolio', methods=['GET'])
@handle_errors
def api_portfolio():
    """获取模拟持仓"""
    agent = get_agent()
    return ok({
        'portfolio': agent.get_portfolio(),
        'trade_history': agent.get_trade_history()
    })


@app.route('/api/execute', methods=['POST'])
@handle_errors
def api_execute():
    """
    执行决策（模拟交易）
    请求体: {symbol}
    """
    params = request.get_json(silent=True) or {}
    symbol = params.get('symbol', 'btc')

    agent = get_agent()
    result = agent.execute_decision(symbol=symbol)

    if not result.get('success'):
        return fail(result.get('error', '执行失败'))

    return ok(result, message='模拟交易执行完成')


# ============================================================
# 报告系统API
# ============================================================

@app.route('/api/report', methods=['GET'])
@handle_errors
def api_report():
    """
    获取报告
    参数: type(daily/backtest), symbol
    """
    report_type = request.args.get('type', 'daily')
    symbol = request.args.get('symbol', 'btc')

    agent = get_agent()
    result = agent.generate_report(report_type=report_type, symbol=symbol)

    return ok(result)


# ============================================================
# 系统状态API
# ============================================================

_start_time = datetime.now()


@app.route('/api/status', methods=['GET'])
@handle_errors
def api_status():
    """系统状态"""
    agent = get_agent()
    status = agent.get_status()

    delta = datetime.now() - _start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)

    status['system'] = {
        'name': 'AI量化交易Agent',
        'version': '1.0.0',
        'uptime': f"{hours}小时{minutes}分{seconds}秒",
        'python_version': sys.version.split()[0]
    }

    return ok(status)


# ============================================================
# 应用工厂函数
# ============================================================

def create_app(config=None):
    """创建Flask应用实例"""
    if config:
        app.config.update(config)
    return app


# ============================================================
# 直接运行入口
# ============================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='AI量化交易Agent Web Dashboard')
    parser.add_argument('--host', type=str, default='0.0.0.0')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger.info(f"启动 AI量化交易Agent Web Dashboard")
    logger.info(f"地址: http://{args.host}:{args.port}")

    app.run(host=args.host, port=args.port, debug=args.debug)
