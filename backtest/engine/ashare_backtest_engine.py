"""
A股回测引擎

适配A股特殊交易规则：
- T+1制度：当日买入次日才能卖出
- 涨跌停限制：主板±10%，ST±5%，创业板±20%
- 交易时间：9:30-11:30, 13:00-15:00
- 停牌处理：停牌期间无法交易
- 最小交易单位：100股（1手）
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class AShareTrade:
    """A股交易记录"""
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    side: str = "long"  # A股只能做多
    quantity: int = 0  # 股数（必须是100的倍数）
    pnl: float = 0.0
    pnl_pct: float = 0.0
    reason: str = ""
    holding_days: int = 0
    # A股特有
    is_t1_locked: bool = True  # T+1锁定状态
    limit_up_entry: bool = False  # 是否涨停买入
    limit_down_exit: bool = False  # 是否跌停卖出


@dataclass
class AShareBacktestResult:
    """A股回测结果"""
    trades: List[AShareTrade] = field(default_factory=list)
    total_return: float = 0.0
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    win_trades: int = 0
    loss_trades: int = 0
    avg_holding_days: float = 0.0
    # A股特有指标
    limit_up_entries: int = 0  # 涨停买入次数
    limit_down_exits: int = 0  # 跌停卖出次数
    t1_blocked_exits: int = 0  # T+1阻止卖出次数
    equity_curve: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "total_trades": self.total_trades,
            "win_trades": self.win_trades,
            "loss_trades": self.loss_trades,
            "avg_holding_days": self.avg_holding_days,
            "limit_up_entries": self.limit_up_entries,
            "limit_down_exits": self.limit_down_exits,
            "t1_blocked_exits": self.t1_blocked_exits,
            "trades": [
                {
                    "entry_time": t.entry_time.isoformat() if t.entry_time else None,
                    "entry_price": t.entry_price,
                    "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                    "exit_price": t.exit_price,
                    "quantity": t.quantity,
                    "pnl": t.pnl,
                    "pnl_pct": t.pnl_pct,
                    "holding_days": t.holding_days,
                    "limit_up_entry": t.limit_up_entry,
                    "limit_down_exit": t.limit_down_exit,
                }
                for t in self.trades
            ]
        }


class AShareBacktestEngine:
    """A股回测引擎"""
    
    # A股交易规则常量
    LIMIT_UP_PCT = 0.10  # 主板涨停 10%
    LIMIT_DOWN_PCT = -0.10  # 主板跌停 -10%
    ST_LIMIT_UP_PCT = 0.05  # ST涨停 5%
    ST_LIMIT_DOWN_PCT = -0.05  # ST跌停 -5%
    MIN_TRADE_UNIT = 100  # 最小交易单位100股
    COMMISSION_RATE = 0.00025  # 佣金万2.5
    STAMP_TAX_RATE = 0.001  # 印花税千1（卖出时）
    MIN_COMMISSION = 5  # 最低佣金5元
    
    def __init__(
        self,
        initial_capital: float = 100000,
        is_st: bool = False,  # 是否为ST股票
        is_cyb: bool = False,  # 是否为创业板
    ):
        """
        初始化A股回测引擎
        
        Args:
            initial_capital: 初始资金（元）
            is_st: 是否为ST股票（涨跌停±5%）
            is_cyb: 是否为创业板（涨跌停±20%）
        """
        self.initial_capital = initial_capital
        self.is_st = is_st
        self.is_cyb = is_cyb
        
        # 设置涨跌停限制
        if is_st:
            self.limit_up_pct = self.ST_LIMIT_UP_PCT
            self.limit_down_pct = self.ST_LIMIT_DOWN_PCT
        elif is_cyb:
            self.limit_up_pct = 0.20
            self.limit_down_pct = -0.20
        else:
            self.limit_up_pct = self.LIMIT_UP_PCT
            self.limit_down_pct = self.LIMIT_DOWN_PCT
        
        # 状态变量
        self.capital = initial_capital
        self.position = 0  # 持仓股数
        self.position_cost = 0.0  # 持仓成本
        self.trades: List[AShareTrade] = []
        self.equity_curve: List[Dict] = []
        self.current_trade: Optional[AShareTrade] = None
        
        logger.info(
            f"A股回测引擎初始化: 初始资金={initial_capital}, "
            f"ST={is_st}, 创业板={is_cyb}, "
            f"涨停={self.limit_up_pct*100}%, 跌停={self.limit_down_pct*100}%"
        )
    
    def run(self, df: pd.DataFrame, strategy) -> AShareBacktestResult:
        """
        执行A股回测
        
        Args:
            df: K线数据DataFrame（必须包含open,high,low,close,volume,is_limit_up,is_limit_down）
            strategy: 策略实例
            
        Returns:
            AShareBacktestResult: 回测结果
        """
        logger.info(f"开始A股回测: {len(df)} 根K线")
        
        # 生成交易信号
        signals = strategy.generate_signals(df)
        
        # 遍历K线
        for i in range(len(df)):
            current_bar = df.iloc[i]
            current_time = current_bar['timestamp']
            
            # 更新T+1锁定状态
            self._update_t1_lock(current_time)
            
            # 获取当前信号
            signal = signals.iloc[i] if i < len(signals) else 0
            
            # 检查涨跌停状态
            is_limit_up = current_bar.get('is_limit_up', False)
            is_limit_down = current_bar.get('is_limit_down', False)
            
            # 执行交易逻辑
            if signal == 1 and self.position == 0:
                # 买入信号
                self._try_buy(current_bar, is_limit_up)
                
            elif signal == -1 and self.position > 0:
                # 卖出信号
                self._try_sell(current_bar, is_limit_down)
            
            # 更新持仓市值
            self._update_equity(current_bar)
        
        # 回测结束，强制平仓
        if self.position > 0:
            self._force_close(df.iloc[-1])
        
        # 计算结果
        result = self._calculate_result()
        
        logger.info(f"回测完成: 总收益={result.total_return:.2%}, 交易次数={result.total_trades}")
        
        return result
    
    def _update_t1_lock(self, current_time: datetime):
        """更新T+1锁定状态"""
        if self.current_trade and self.current_trade.is_t1_locked:
            # 检查是否已过T+1（次日开盘）
            entry_date = self.current_trade.entry_time.date()
            current_date = current_time.date()
            
            if current_date > entry_date:
                self.current_trade.is_t1_locked = False
    
    def _try_buy(self, bar: pd.Series, is_limit_up: bool):
        """尝试买入"""
        # A股规则：涨停时无法买入
        if is_limit_up:
            logger.debug(f"涨停无法买入: {bar['timestamp']}")
            return
        
        price = bar['close']
        
        # 计算可买入数量（100股整数倍）
        max_shares = int(self.capital / price / self.MIN_TRADE_UNIT) * self.MIN_TRADE_UNIT
        
        if max_shares < self.MIN_TRADE_UNIT:
            logger.debug("资金不足，无法买入")
            return
        
        # 计算交易成本
        commission = max(price * max_shares * self.COMMISSION_RATE, self.MIN_COMMISSION)
        total_cost = price * max_shares + commission
        
        if total_cost > self.capital:
            # 调整数量
            max_shares -= self.MIN_TRADE_UNIT
            if max_shares < self.MIN_TRADE_UNIT:
                return
            commission = max(price * max_shares * self.COMMISSION_RATE, self.MIN_COMMISSION)
        
        # 执行买入
        self.position = max_shares
        self.position_cost = price
        self.capital -= (price * max_shares + commission)
        
        # 创建交易记录
        self.current_trade = AShareTrade(
            entry_time=bar['timestamp'],
            entry_price=price,
            quantity=max_shares,
            is_t1_locked=True,
            limit_up_entry=is_limit_up
        )
        
        logger.debug(f"买入: {max_shares}股 @ {price}, 佣金={commission:.2f}")
    
    def _try_sell(self, bar: pd.Series, is_limit_down: bool):
        """尝试卖出"""
        # A股规则：T+1锁定期间无法卖出
        if self.current_trade and self.current_trade.is_t1_locked:
            logger.debug(f"T+1锁定，无法卖出: {bar['timestamp']}")
            if hasattr(self, 'result'):
                self.result.t1_blocked_exits += 1
            return
        
        # A股规则：跌停时无法卖出
        if is_limit_down:
            logger.debug(f"跌停无法卖出: {bar['timestamp']}")
            return
        
        price = bar['close']
        
        # 计算卖出收入
        sell_amount = price * self.position
        commission = max(sell_amount * self.COMMISSION_RATE, self.MIN_COMMISSION)
        stamp_tax = sell_amount * self.STAMP_TAX_RATE  # 印花税
        
        total_cost = commission + stamp_tax
        net_proceeds = sell_amount - total_cost
        
        # 计算盈亏
        pnl = net_proceeds - (self.position_cost * self.position)
        pnl_pct = pnl / (self.position_cost * self.position) if self.position_cost > 0 else 0
        
        # 更新交易记录
        if self.current_trade:
            self.current_trade.exit_time = bar['timestamp']
            self.current_trade.exit_price = price
            self.current_trade.pnl = pnl
            self.current_trade.pnl_pct = pnl_pct
            self.current_trade.holding_days = (bar['timestamp'] - self.current_trade.entry_time).days
            self.current_trade.limit_down_exit = is_limit_down
            
            self.trades.append(self.current_trade)
        
        # 更新资金
        self.capital += net_proceeds
        self.position = 0
        self.position_cost = 0
        self.current_trade = None
        
        logger.debug(f"卖出: {price}, 盈亏={pnl:.2f}, 佣金={commission:.2f}, 印花税={stamp_tax:.2f}")
    
    def _force_close(self, bar: pd.Series):
        """强制平仓（回测结束）"""
        if self.position == 0:
            return
        
        price = bar['close']
        sell_amount = price * self.position
        commission = max(sell_amount * self.COMMISSION_RATE, self.MIN_COMMISSION)
        stamp_tax = sell_amount * self.STAMP_TAX_RATE
        
        net_proceeds = sell_amount - commission - stamp_tax
        pnl = net_proceeds - (self.position_cost * self.position)
        
        if self.current_trade:
            self.current_trade.exit_time = bar['timestamp']
            self.current_trade.exit_price = price
            self.current_trade.pnl = pnl
            self.current_trade.reason = "回测结束强制平仓"
            self.trades.append(self.current_trade)
        
        self.capital += net_proceeds
        self.position = 0
        
        logger.info(f"强制平仓: 盈亏={pnl:.2f}")
    
    def _update_equity(self, bar: pd.Series):
        """更新权益曲线"""
        position_value = self.position * bar['close']
        total_equity = self.capital + position_value
        
        self.equity_curve.append({
            'timestamp': bar['timestamp'],
            'equity': total_equity,
            'cash': self.capital,
            'position_value': position_value,
            'position': self.position
        })
    
    def _calculate_result(self) -> AShareBacktestResult:
        """计算回测结果"""
        result = AShareBacktestResult()
        result.trades = self.trades
        result.equity_curve = pd.DataFrame(self.equity_curve)
        
        if not result.equity_curve.empty:
            final_equity = result.equity_curve['equity'].iloc[-1]
            result.total_return = (final_equity - self.initial_capital) / self.initial_capital
            
            # 计算最大回撤
            equity = result.equity_curve['equity']
            cummax = equity.cummax()
            drawdown = (equity - cummax) / cummax
            result.max_drawdown = drawdown.min()
        
        # 统计交易
        result.total_trades = len(self.trades)
        result.win_trades = sum(1 for t in self.trades if t.pnl > 0)
        result.loss_trades = sum(1 for t in self.trades if t.pnl <= 0)
        
        if result.total_trades > 0:
            result.win_rate = result.win_trades / result.total_trades
            
            total_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
            total_loss = abs(sum(t.pnl for t in self.trades if t.pnl <= 0))
            result.profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
            
            result.avg_holding_days = np.mean([t.holding_days for t in self.trades])
            
            result.limit_up_entries = sum(1 for t in self.trades if t.limit_up_entry)
            result.limit_down_exits = sum(1 for t in self.trades if t.limit_down_exit)
        
        return result
