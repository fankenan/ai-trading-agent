# -*- coding: utf-8 -*-
"""
AI量化交易Agent系统 - 项目启动入口
启动Flask Web服务器，加载配置，初始化日志
"""

import os
import sys
import argparse
import logging
from datetime import datetime


def setup_logging(debug=False):
    """
    初始化日志系统
    
    参数:
      debug: 是否开启调试模式，开启后日志级别为DEBUG，否则为INFO
    """
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = '%(asctime)s [%(levelname)s] %(name)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # 配置根日志记录器
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # 控制台输出
            logging.StreamHandler(sys.stdout)
        ]
    )

    # 设置第三方库日志级别（避免过多输出）
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    logger = logging.getLogger('main')
    logger.info("日志系统初始化完成 (级别: %s)", 'DEBUG' if debug else 'INFO')
    return logger


def load_config():
    """
    加载应用配置
    
    优先级: 环境变量 > 默认值
    """
    config = {
        'host': os.environ.get('FLASK_HOST', '0.0.0.0'),
        'port': int(os.environ.get('FLASK_PORT', '5000')),
        'debug': os.environ.get('FLASK_DEBUG', '0') == '1',
        'secret_key': os.environ.get('SECRET_KEY', 'ai-trading-agent-secret-key-2024'),
        'db_path': os.environ.get('DB_PATH', None),
        'log_level': os.environ.get('LOG_LEVEL', 'INFO')
    }

    return config


def main():
    """主函数 - 解析命令行参数并启动Web服务器"""
    parser = argparse.ArgumentParser(
        description='AI量化交易Agent系统 - Web Dashboard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py                    # 默认启动 (0.0.0.0:5000)
  python run.py --port 8080        # 指定端口
  python run.py --host 127.0.0.1   # 指定监听地址
  python run.py --debug            # 开启调试模式
  python run.py --port 8080 --debug  # 组合使用
        """
    )

    parser.add_argument(
        '--host',
        type=str,
        default=None,
        help='监听地址 (默认: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='监听端口 (默认: 5000)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        default=None,
        help='开启调试模式 (默认: 关闭)'
    )

    args = parser.parse_args()

    # 加载配置
    config = load_config()

    # 命令行参数覆盖配置
    host = args.host if args.host is not None else config['host']
    port = args.port if args.port is not None else config['port']
    debug = args.debug if args.debug is not None else config['debug']

    # 初始化日志
    logger = setup_logging(debug=debug)

    # 打印启动信息
    logger.info("=" * 60)
    logger.info("  AI量化交易Agent系统 - Web Dashboard")
    logger.info("=" * 60)
    logger.info(f"  启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  监听地址: {host}:{port}")
    logger.info(f"  调试模式: {'开启' if debug else '关闭'}")
    logger.info(f"  Python版本: {sys.version.split()[0]}")
    logger.info(f"  工作目录: {os.getcwd()}")
    logger.info("=" * 60)

    # 确保项目根目录在系统路径中
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        logger.debug(f"已添加项目路径: {project_root}")

    # 导入并创建Flask应用
    try:
        from web.app import create_app
    except ImportError as e:
        logger.error(f"无法导入Web模块: {e}")
        logger.error("请确保已安装Flask: pip install flask")
        sys.exit(1)

    # 创建应用实例
    flask_config = {
        'SECRET_KEY': config['secret_key'],
        'DEBUG': debug
    }
    app = create_app(config=flask_config)

    # 启动Web服务器
    logger.info(f"Web Dashboard启动成功!")
    logger.info(f"访问地址: http://{host}:{port}")
    logger.info("按 Ctrl+C 停止服务器")

    try:
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug  # 调试模式下启用热重载
        )
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭服务器...")
    except OSError as e:
        logger.error(f"端口 {port} 可能已被占用: {e}")
        logger.error(f"请尝试使用其他端口: python run.py --port {port + 1}")
        sys.exit(1)
    finally:
        logger.info("服务器已关闭")


if __name__ == '__main__':
    main()
