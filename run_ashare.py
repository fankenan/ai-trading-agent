#!/usr/bin/env python3
"""
A股量化Agent启动脚本
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 导入A股Agent
from agent.ashare_agent import AShareAgent

# 创建全局Agent实例
_agent = None

def get_agent():
    """获取A股Agent实例"""
    global _agent
    if _agent is None:
        config_path = Path(__file__).parent / 'config' / 'ashare_config.yaml'
        _agent = AShareAgent(str(config_path))
        logger.info("A股Agent初始化完成")
    return _agent


from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__, 
            template_folder='web/templates',
            static_folder='web/static')
CORS(app)
app.config['JSON_AS_ASCII'] = False


def ok(data=None, message='操作成功'):
    """成功响应"""
    resp = {
        'success': True,
        'message': message,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    if data is not None:
        resp['data'] = data
    return jsonify(resp)


def fail(message='操作失败', code=400):
    """失败响应"""
    return jsonify({
        'success': False,
        'message': message,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }), code


@app.route('/')
def index():
    """主页"""
    index_path = os.path.join(os.path.dirname(__file__), 'web', 'templates', 'index.html')
    from flask import send_file
    return send_file(index_path)


@app.route('/api/status')
def api_status():
    """系统状态"""
    agent = get_agent()
    return ok(agent.get_status())


@app.route('/api/market')
def api_market():
    """获取行情"""
    symbol = request.args.get('symbol', '000001')
    days = int(request.args.get('days', 365))
    
    agent = get_agent()
    result = agent.fetch_market_data(symbol, days)
    
    if not result['success']:
        return fail(result.get('error', '获取失败'))
    
    # 获取实时行情
    quote = agent.get_realtime_quote(symbol)
    
    return ok({
        'fetch_result': result,
        'quote': quote,
        'symbol': symbol
    })


@app.route('/api/backtest', methods=['POST'])
def api_backtest():
    """执行回测"""
    params = request.get_json(silent=True) or {}
    symbol = params.get('symbol', '000001')
    strategy = params.get('strategy', 'ma')
    days = int(params.get('days', 365))
    
    agent = get_agent()
    result = agent.run_backtest(symbol, strategy, days)
    
    if not result['success']:
        return fail(result.get('error', '回测失败'))
    
    return ok(result, message='回测完成')


@app.route('/api/score')
def api_score():
    """获取评分"""
    symbol = request.args.get('symbol', '000001')
    
    agent = get_agent()
    result = agent.calculate_score(symbol)
    
    if not result['success']:
        return fail(result.get('error', '评分失败'))
    
    return ok(result)


@app.route('/api/decision')
def api_decision():
    """获取决策"""
    symbol = request.args.get('symbol', '000001')
    
    agent = get_agent()
    result = agent.make_decision(symbol)
    
    if not result['success']:
        return fail(result.get('error', '决策失败'))
    
    return ok(result)


@app.route('/api/news', methods=['GET', 'POST'])
def api_news():
    """新闻接口"""
    agent = get_agent()
    
    if request.method == 'POST':
        params = request.get_json(silent=True) or {}
        title = params.get('title', '').strip()
        content = params.get('content', '').strip()
        source = params.get('source', 'manual')
        
        if not title:
            return fail('请输入标题')
        
        result = agent.add_news_event(title, content, source)
        if not result['success']:
            return fail(result.get('error', '添加失败'))
        return ok(result, message='新闻已添加')
    
    # GET - 获取政策新闻
    news = agent.get_policy_news()
    return ok({'news': news})


@app.route('/api/north_flow')
def api_north_flow():
    """北向资金"""
    agent = get_agent()
    flow = agent.get_north_flow()
    return ok(flow)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='A股量化Agent')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=5001, help='监听端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    args = parser.parse_args()
    
    logger.info(f"启动A股量化Agent服务器")
    logger.info(f"地址: http://{args.host}:{args.port}")
    
    app.run(host=args.host, port=args.port, debug=args.debug)
