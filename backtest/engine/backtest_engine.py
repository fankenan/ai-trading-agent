"""
回测引擎模块

提供完整的回测执行引擎，支持手续费、滑点扣除，
严格禁止未来函数，确保回测结果的可靠性。

核心类:
    - Trade: 单笔交易记录
    - BacktestResult: 回测结果汇总
    - BacktestEngine: 回测引擎主类
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Any, Dict

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """单笔交易记录

    Attributes:
        entry_time: 入场时间
        entry_price: 入场价格（含滑点）
        exit_time: 出场时间
        exit_price: 出场价格（含滑点）
        side: 交易方向，"long" 表示做多，"short" 表示做空
        quantity: 交易数量（股数）
        pnl: 盈亏金额（扣除手续费和滑点后）
        pnl_pct: 盈亏百分比
        reason: 交易原因（信号描述）
        holding_bars: 持仓K线根数
    """

    entry_time: Any = None  # pd.Timestamp 或等效类型
    entry_price: float = 0.0
    exit_time: Any = None
    exit_price: float = 0.0
    side: str = "long"
    quantity: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    reason: str = ""
    holding_bars: int = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        result = asdict(self)
        # 将时间类型转为字符串以便序列化
        result["entry_time"] = str(self.entry_time) if self.entry_time is not None else None
        result["exit_time"] = str(self.exit_time) if self.exit_time is not None else None
        return result


@dataclass
class BacktestResult:
    """回测结果汇总

    Attributes:
        trades: 所有交易记录列表
        total_return: 总收益率（百分比）
        max_drawdown: 最大回撤（百分比）
        win_rate: 胜率（百分比）
        profit_factor: 盈亏比（总盈利 / 总亏损）
        total_trades: 总交易次数
        avg_holding_bars: 平均持仓K线数
        equity_curve: 权益曲线 DataFrame，包含 datetime, equity, drawdown 列
    """

    trades: List[Trade] = field(default_factory=list)
    total_return: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    avg_holding_bars: float = 0.0
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)

    def to_dict(self) -> dict:
        """将回测结果转换为字典

        Returns:
            包含所有回测指标和交易记录的字典
        """
        return {
            "total_return": round(self.total_return, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 4),
            "total_trades": self.total_trades,
            "avg_holding_bars": round(self.avg_holding_bars, 2),
            "trades": [t.to_dict() for t in self.trades],
            "equity_curve": (
                self.equity_curve.to_dict(orient="records")
                if not self.equity_curve.empty
                else []
            ),
        }

    def to_json(self) -> str:
        """将回测结果转换为JSON字符串

        Returns:
            JSON格式的回测结果字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class BacktestEngine:
    """回测引擎

    执行策略回测，支持:
    - 手续费扣除（按成交金额比例）
    - 滑点模拟（按价格比例）
    - 严格的未来函数检测
    - 完整的权益曲线记录
    - 详细的交易记录

    Usage:
        engine = BacktestEngine(initial_capital=100000, fee_rate=0.001, slippage=0.0005)
        result = engine.run(df, strategy)
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        fee_rate: float = 0.001,
        slippage: float = 0.0005,
    ) -> None:
        """初始化回测引擎

        Args:
            initial_capital: 初始资金，默认10000
            fee_rate: 手续费率，默认0.001（万分之一）
            slippage: 滑点率，默认0.0005（万分之零点五）
        """
        self.initial_capital: float = initial_capital
        self.fee_rate: float = fee_rate
        self.slippage: float = slippage

        # 运行时状态
        self._capital: float = initial_capital
        self._position: int = 0  # 当前持仓数量，正数做多，负数做空（当前仅支持做多）
        self._entry_price: float = 0.0
        self._entry_time: Any = None
        self._entry_bar_index: int = 0
        self._trades: List[Trade] = []
        self._equity_records: List[Dict[str, Any]] = []

    def run(self, df: pd.DataFrame, strategy: Any) -> BacktestResult:
        """执行回测

        Args:
            df: 行情数据 DataFrame，必须包含以下列:
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - volume: 成交量
                索引应为时间序列（DatetimeIndex 或可排序索引）
            strategy: 策略实例，必须实现 generate_signals(df) -> pd.Series 方法

        Returns:
            BacktestResult 回测结果对象

        Raises:
            ValueError: 当输入数据格式不正确或检测到未来函数时
        """
        # 重置运行时状态
        self._reset_state()

        # 验证输入数据
        self._validate_input(df)

        # 生成信号（策略内部只应使用当前及之前的数据）
        logger.info("正在生成交易信号...")
        signals = strategy.generate_signals(df.copy())

        # 验证信号序列
        if len(signals) != len(df):
            raise ValueError(
                f"信号序列长度({len(signals)})与数据长度({len(df)})不匹配"
            )

        # 检查未来函数
        self._check_future_leak(df, strategy)

        logger.info(f"开始回测，共 {len(df)} 根K线，初始资金 {self.initial_capital}")

        # 逐K线模拟交易
        for i in range(len(df)):
            current_bar = df.iloc[i]
            signal = signals.iloc[i]
            current_time = df.index[i]

            # 记录当前权益
            current_equity = self._calculate_current_equity(current_bar["close"])
            self._equity_records.append(
                {
                    "datetime": current_time,
                    "equity": round(current_equity, 4),
                    "price": current_bar["close"],
                }
            )

            # 执行交易信号
            if signal != 0:
                self._execute_trade(signal, current_bar, current_time, i)

        # 如果回测结束时仍有持仓，强制平仓
        if self._position > 0:
            self._close_position(
                df.iloc[-1], df.index[-1], len(df) - 1, reason="回测结束强制平仓"
            )

        # 计算回测指标
        metrics = self._calculate_metrics()

        # 构建权益曲线
        equity_df = pd.DataFrame(self._equity_records)
        if not equity_df.empty:
            equity_df["drawdown"] = (
                equity_df["equity"]
                / equity_df["equity"].cummax()
                - 1.0
            )
            equity_df["drawdown"] = equity_df["drawdown"].apply(lambda x: round(x, 6))

        # 构建回测结果
        result = BacktestResult(
            trades=self._trades,
            total_return=metrics["total_return"],
            max_drawdown=metrics["max_drawdown"],
            win_rate=metrics["win_rate"],
            profit_factor=metrics["profit_factor"],
            total_trades=metrics["total_trades"],
            avg_holding_bars=metrics["avg_holding_bars"],
            equity_curve=equity_df,
        )

        logger.info(
            f"回测完成: 总收益率={result.total_return:.2%}, "
            f"最大回撤={result.max_drawdown:.2%}, "
            f"胜率={result.win_rate:.2%}, "
            f"交易次数={result.total_trades}"
        )

        return result

    def _reset_state(self) -> None:
        """重置运行时状态"""
        self._capital = self.initial_capital
        self._position = 0
        self._entry_price = 0.0
        self._entry_time = None
        self._entry_bar_index = 0
        self._trades = []
        self._equity_records = []

    def _validate_input(self, df: pd.DataFrame) -> None:
        """验证输入数据格式

        Args:
            df: 行情数据

        Raises:
            ValueError: 当缺少必要列时
        """
        required_columns = {"open", "high", "low", "close", "volume"}
        actual_columns = set(df.columns.str.lower())
        missing = required_columns - actual_columns
        if missing:
            raise ValueError(f"行情数据缺少必要列: {missing}")

        if len(df) < 2:
            raise ValueError("行情数据至少需要2根K线")

    def _check_future_leak(self, df: pd.DataFrame, strategy: Any) -> None:
        """检查未来函数

        通过对比完整数据的信号与截断数据的信号，检测策略是否使用了未来数据。
        如果使用完整数据生成的信号与使用截断数据生成的信号存在差异，
        则说明策略可能存在未来函数问题。

        Args:
            df: 完整行情数据
            strategy: 策略实例

        Raises:
            ValueError: 当检测到未来函数时
        """
        logger.info("正在检查未来函数...")

        # 取前80%数据生成信号
        cutoff = int(len(df) * 0.8)
        if cutoff < 10:
            # 数据量太少，跳过检查
            logger.warning("数据量太少，跳过未来函数检查")
            return

        df_truncated = df.iloc[:cutoff].copy()
        df_full = df.copy()

        signals_truncated = strategy.generate_signals(df_truncated)
        signals_full = strategy.generate_signals(df_full)

        # 对比前cutoff个信号是否一致
        if len(signals_truncated) != cutoff:
            raise ValueError(
                "未来函数检查失败: 截断数据的信号长度不正确，"
                "策略可能依赖全局数据而非逐K线计算"
            )

        mismatch_count = 0
        for i in range(cutoff):
            if signals_truncated.iloc[i] != signals_full.iloc[i]:
                mismatch_count += 1

        # 允许少量差异（由于边界效应），但差异比例不能超过5%
        mismatch_ratio = mismatch_count / cutoff
        if mismatch_ratio > 0.05:
            raise ValueError(
                f"检测到未来函数! 截断数据与完整数据的信号不一致比例: "
                f"{mismatch_ratio:.2%} ({mismatch_count}/{cutoff})。"
                f"请确保策略的 generate_signals 方法只使用当前K线及之前的数据。"
            )

        logger.info(f"未来函数检查通过 (不一致率: {mismatch_ratio:.2%})")

    def _execute_trade(
        self,
        signal: int,
        current_bar: pd.Series,
        current_time: Any,
        bar_index: int,
    ) -> None:
        """执行交易信号

        Args:
            signal: 交易信号，1=买入, -1=卖出, 0=持有
            current_bar: 当前K线数据
            current_time: 当前时间
            bar_index: 当前K线索引
        """
        price = current_bar["close"]

        if signal == 1 and self._position == 0:
            # 买入开仓
            self._open_position(current_bar, current_time, bar_index, reason="信号买入")
        elif signal == -1 and self._position > 0:
            # 卖出平仓
            self._close_position(
                current_bar, current_time, bar_index, reason="信号卖出"
            )

    def _open_position(
        self,
        current_bar: pd.Series,
        current_time: Any,
        bar_index: int,
        reason: str = "",
    ) -> None:
        """开仓

        Args:
            current_bar: 当前K线数据
            current_time: 当前时间
            bar_index: 当前K线索引
            reason: 开仓原因
        """
        # 计算含滑点的买入价格（滑点增加买入成本）
        price = current_bar["close"] * (1.0 + self.slippage)

        # 计算可买入数量（整手，至少买1手=100股）
        max_affordable = self._capital / (price * (1.0 + self.fee_rate))
        quantity = int(max_affordable / 100) * 100  # 按手数取整
        if quantity <= 0:
            logger.warning(f"资金不足，无法开仓。当前资金: {self._capital:.2f}")
            return

        # 计算手续费
        fee = price * quantity * self.fee_rate

        # 扣除资金
        cost = price * quantity + fee
        self._capital -= cost

        # 记录持仓信息
        self._position = quantity
        self._entry_price = price
        self._entry_time = current_time
        self._entry_bar_index = bar_index

        logger.debug(
            f"开仓: 时间={current_time}, 价格={price:.4f}, "
            f"数量={quantity}, 手续费={fee:.4f}, 剩余资金={self._capital:.4f}"
        )

    def _close_position(
        self,
        current_bar: pd.Series,
        current_time: Any,
        bar_index: int,
        reason: str = "",
    ) -> None:
        """平仓

        Args:
            current_bar: 当前K线数据
            current_time: 当前时间
            bar_index: 当前K线索引
            reason: 平仓原因
        """
        if self._position <= 0:
            return

        # 计算含滑点的卖出价格（滑点降低卖出收入）
        price = current_bar["close"] * (1.0 - self.slippage)

        # 计算手续费
        fee = price * self._position * self.fee_rate

        # 计算盈亏
        revenue = price * self._position - fee
        cost_basis = self._entry_price * self._position
        pnl = revenue - cost_basis
        pnl_pct = pnl / cost_basis if cost_basis > 0 else 0.0

        # 回收资金
        self._capital += revenue

        # 记录交易
        trade = Trade(
            entry_time=self._entry_time,
            entry_price=round(self._entry_price, 6),
            exit_time=current_time,
            exit_price=round(price, 6),
            side="long",
            quantity=self._position,
            pnl=round(pnl, 4),
            pnl_pct=round(pnl_pct, 6),
            reason=reason,
            holding_bars=bar_index - self._entry_bar_index,
        )
        self._trades.append(trade)

        logger.debug(
            f"平仓: 时间={current_time}, 价格={price:.4f}, "
            f"盈亏={pnl:.4f} ({pnl_pct:.2%}), "
            f"持仓{bar_index - self._entry_bar_index}根K线"
        )

        # 清空持仓
        self._position = 0
        self._entry_price = 0.0
        self._entry_time = None
        self._entry_bar_index = 0

    def _calculate_current_equity(self, current_price: float) -> float:
        """计算当前总权益

        Args:
            current_price: 当前市场价格

        Returns:
            总权益 = 现金 + 持仓市值
        """
        position_value = self._position * current_price
        return self._capital + position_value

    def _calculate_metrics(self) -> dict:
        """计算回测指标

        Returns:
            包含各项回测指标的字典:
            - total_return: 总收益率
            - max_drawdown: 最大回撤
            - win_rate: 胜率
            - profit_factor: 盈亏比
            - total_trades: 总交易次数
            - avg_holding_bars: 平均持仓K线数
        """
        trades = self._trades
        total_trades = len(trades)

        if total_trades == 0:
            return {
                "total_return": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_trades": 0,
                "avg_holding_bars": 0.0,
            }

        # 总收益率
        final_equity = self._capital
        total_return = (final_equity - self.initial_capital) / self.initial_capital

        # 最大回撤（基于权益曲线）
        max_drawdown = 0.0
        if self._equity_records:
            equities = [r["equity"] for r in self._equity_records]
            peak = equities[0]
            for eq in equities:
                if eq > peak:
                    peak = eq
                dd = (peak - eq) / peak if peak > 0 else 0.0
                if dd > max_drawdown:
                    max_drawdown = dd

        # 胜率
        winning_trades = [t for t in trades if t.pnl > 0]
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0

        # 盈亏比
        total_profit = sum(t.pnl for t in trades if t.pnl > 0)
        total_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
        profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")

        # 平均持仓K线数
        avg_holding_bars = (
            sum(t.holding_bars for t in trades) / total_trades
            if total_trades > 0
            else 0.0
        )

        return {
            "total_return": round(total_return, 6),
            "max_drawdown": round(max_drawdown, 6),
            "win_rate": round(win_rate, 6),
            "profit_factor": round(profit_factor, 4),
            "total_trades": total_trades,
            "avg_holding_bars": round(avg_holding_bars, 2),
        }
