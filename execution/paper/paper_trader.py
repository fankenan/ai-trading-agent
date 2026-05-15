"""
模拟交易器

提供模拟交易功能，用于策略回测和验证。
不涉及真实资金，所有交易在本地模拟执行。

功能：
  - 模拟买入/卖出操作
  - 跟踪持仓状态和权益变化
  - 记录完整的交易历史
  - 生成权益曲线
  - 交易记录持久化（CSV格式）
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import csv
import os
from loguru import logger


class PaperTrader:
    """模拟交易器

    模拟真实交易环境，支持买入、卖出和持有操作。
    自动跟踪持仓、余额和权益变化。

    Attributes:
        initial_capital: 初始资金
        balance: 当前可用余额
        positions: 当前持仓列表
        trade_history: 交易历史记录
        equity_curve: 权益曲线记录
    """

    def __init__(self, initial_capital: float = 10000.0) -> None:
        """初始化模拟交易器

        Args:
            initial_capital: 初始资金（默认10000）
        """
        self.initial_capital: float = initial_capital
        self.balance: float = initial_capital
        self.positions: List[Dict[str, Any]] = []
        self.trade_history: List[Dict[str, Any]] = []
        self.equity_curve: List[Dict[str, Any]] = []

        # 记录初始权益
        self._record_equity(0.0)

        logger.info(f"模拟交易器初始化完成，初始资金: {initial_capital}")

    def execute(
        self,
        decision: Dict[str, Any],
        current_price: float,
    ) -> Dict[str, Any]:
        """执行模拟交易

        根据决策结果执行对应的交易操作。

        Args:
            decision: 交易决策，包含：
                - action: 操作类型（"buy"/"sell"/"hold"）
                - position_suggestion: 仓位建议
                - confidence: 决策置信度
            current_price: 当前市场价格

        Returns:
            包含以下字段的字典：
            - success: 是否执行成功
            - action: 实际执行的操作
            - quantity: 交易数量
            - price: 执行价格
            - total: 交易总额
            - fee: 手续费
            - balance: 执行后余额
            - message: 执行结果描述
        """
        action: str = decision.get("action", "hold")
        suggestion: Dict[str, Any] = decision.get("position_suggestion", {})

        logger.info(f"执行交易决策: action={action}, price={current_price}")

        if action == "hold":
            result: Dict[str, Any] = {
                "success": True,
                "action": "hold",
                "quantity": 0,
                "price": current_price,
                "total": 0,
                "fee": 0,
                "balance": self.balance,
                "message": "持有观望，未执行交易",
            }
            self._record_equity(current_price)
            return result

        if action == "buy":
            return self._execute_buy(suggestion, current_price)

        if action == "sell":
            return self._execute_sell(suggestion, current_price)

        # 未知操作类型
        logger.warning(f"未知操作类型: {action}，默认hold")
        self._record_equity(current_price)
        return {
            "success": False,
            "action": "hold",
            "quantity": 0,
            "price": current_price,
            "total": 0,
            "fee": 0,
            "balance": self.balance,
            "message": f"未知操作类型: {action}",
        }

    def get_portfolio(self) -> Dict[str, Any]:
        """获取当前持仓信息

        Returns:
            包含以下字段的字典：
            - balance: 可用余额
            - positions: 持仓列表
            - total_value: 持仓总市值
            - total_equity: 总权益（余额 + 市值）
            - total_pnl: 总盈亏金额
            - total_pnl_pct: 总盈亏百分比
            - position_count: 持仓数量
        """
        total_value: float = sum(
            pos.get("current_value", 0) for pos in self.positions
        )
        total_equity: float = self.balance + total_value
        total_pnl: float = total_equity - self.initial_capital
        total_pnl_pct: float = (
            total_pnl / self.initial_capital if self.initial_capital > 0 else 0
        )

        return {
            "balance": round(self.balance, 2),
            "positions": self.positions.copy(),
            "total_value": round(total_value, 2),
            "total_equity": round(total_equity, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 4),
            "position_count": len(self.positions),
        }

    def get_trade_history(self) -> List[Dict[str, Any]]:
        """获取交易历史

        Returns:
            交易历史记录列表，每条记录包含：
            - timestamp: 交易时间
            - action: 操作类型
            - quantity: 数量
            - price: 价格
            - total: 总额
            - fee: 手续费
        """
        return self.trade_history.copy()

    def get_equity_curve(self) -> List[Dict[str, Any]]:
        """获取权益曲线

        Returns:
            权益曲线数据列表，每条记录包含：
            - timestamp: 记录时间
            - equity: 总权益
            - balance: 余额
            - position_value: 持仓市值
        """
        return self.equity_curve.copy()

    def _execute_buy(
        self,
        suggestion: Dict[str, Any],
        price: float,
    ) -> Dict[str, Any]:
        """执行买入操作

        Args:
            suggestion: 仓位建议
            price: 当前价格

        Returns:
            交易执行结果
        """
        position_pct: float = suggestion.get("position_pct", 0)
        if position_pct <= 0:
            logger.info("买入仓位比例为0，跳过买入")
            self._record_equity(price)
            return {
                "success": True,
                "action": "hold",
                "quantity": 0,
                "price": price,
                "total": 0,
                "fee": 0,
                "balance": self.balance,
                "message": "买入仓位比例为0，未执行",
            }

        # 计算买入金额
        total_equity = self.balance + sum(
            pos.get("current_value", 0) for pos in self.positions
        )
        invest_amount: float = total_equity * position_pct

        # 检查余额是否充足
        if invest_amount > self.balance:
            invest_amount = self.balance
            logger.warning(f"余额不足，调整买入金额为: {invest_amount}")

        if invest_amount <= 0:
            logger.info("可用余额为0，无法买入")
            self._record_equity(price)
            return {
                "success": False,
                "action": "buy",
                "quantity": 0,
                "price": price,
                "total": 0,
                "fee": 0,
                "balance": self.balance,
                "message": "可用余额不足",
            }

        # 计算手续费（0.1%）
        fee: float = invest_amount * 0.001
        actual_invest: float = invest_amount - fee

        # 计算买入数量
        quantity: float = actual_invest / price

        # 更新余额
        self.balance -= invest_amount

        # 更新持仓
        self.positions.append({
            "quantity": quantity,
            "avg_cost": price,
            "current_price": price,
            "current_value": quantity * price,
            "invest_amount": actual_invest,
            "pnl": 0,
            "pnl_pct": 0,
            "buy_time": datetime.now().isoformat(),
        })

        # 记录交易
        trade: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "action": "buy",
            "quantity": round(quantity, 8),
            "price": price,
            "total": round(invest_amount, 2),
            "fee": round(fee, 2),
        }
        self.trade_history.append(trade)
        self._save_trade(trade)

        # 更新权益
        self._record_equity(price)

        logger.info(
            f"买入成功: 数量={quantity:.8f}, 价格={price}, "
            f"金额={invest_amount:.2f}, 手续费={fee:.2f}"
        )

        return {
            "success": True,
            "action": "buy",
            "quantity": round(quantity, 8),
            "price": price,
            "total": round(invest_amount, 2),
            "fee": round(fee, 2),
            "balance": round(self.balance, 2),
            "message": f"买入{quantity:.8f}个单位，价格{price}",
        }

    def _execute_sell(
        self,
        suggestion: Dict[str, Any],
        price: float,
    ) -> Dict[str, Any]:
        """执行卖出操作

        Args:
            suggestion: 仓位建议
            price: 当前价格

        Returns:
            交易执行结果
        """
        sell_quantity: float = suggestion.get("quantity", 0)

        if sell_quantity <= 0:
            # 未指定卖出数量，默认卖出全部持仓
            sell_quantity = sum(pos.get("quantity", 0) for pos in self.positions)

        if sell_quantity <= 0 or not self.positions:
            logger.info("无持仓可卖出")
            self._record_equity(price)
            return {
                "success": True,
                "action": "hold",
                "quantity": 0,
                "price": price,
                "total": 0,
                "fee": 0,
                "balance": self.balance,
                "message": "无持仓可卖出",
            }

        # 计算实际可卖出数量
        total_available: float = sum(pos.get("quantity", 0) for pos in self.positions)
        actual_sell: float = min(sell_quantity, total_available)

        if actual_sell <= 0:
            self._record_equity(price)
            return {
                "success": False,
                "action": "sell",
                "quantity": 0,
                "price": price,
                "total": 0,
                "fee": 0,
                "balance": self.balance,
                "message": "卖出数量为0",
            }

        # 按比例从各持仓中卖出
        sell_ratio: float = actual_sell / total_available
        total_sell_value: float = 0
        total_cost: float = 0

        remaining_positions: List[Dict[str, Any]] = []
        for pos in self.positions:
            pos_sell_qty: float = pos["quantity"] * sell_ratio
            sell_value: float = pos_sell_qty * price
            cost_value: float = pos_sell_qty * pos["avg_cost"]

            total_sell_value += sell_value
            total_cost += cost_value

            # 更新剩余持仓
            remaining_qty: float = pos["quantity"] - pos_sell_qty
            if remaining_qty > 1e-10:
                remaining_positions.append({
                    **pos,
                    "quantity": remaining_qty,
                    "current_price": price,
                    "current_value": remaining_qty * price,
                })

        self.positions = remaining_positions

        # 计算手续费（0.1%）
        fee: float = total_sell_value * 0.001
        net_proceeds: float = total_sell_value - fee

        # 更新余额
        self.balance += net_proceeds

        # 计算盈亏
        pnl: float = net_proceeds - total_cost
        pnl_pct: float = pnl / total_cost if total_cost > 0 else 0

        # 记录交易
        trade: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "action": "sell",
            "quantity": round(actual_sell, 8),
            "price": price,
            "total": round(total_sell_value, 2),
            "fee": round(fee, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 4),
        }
        self.trade_history.append(trade)
        self._save_trade(trade)

        # 更新权益
        self._record_equity(price)

        logger.info(
            f"卖出成功: 数量={actual_sell:.8f}, 价格={price}, "
            f"金额={total_sell_value:.2f}, 盈亏={pnl:.2f}({pnl_pct:.2%})"
        )

        return {
            "success": True,
            "action": "sell",
            "quantity": round(actual_sell, 8),
            "price": price,
            "total": round(total_sell_value, 2),
            "fee": round(fee, 2),
            "balance": round(self.balance, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 4),
            "message": f"卖出{actual_sell:.8f}个单位，价格{price}，盈亏{pnl:.2f}",
        }

    def _record_equity(self, current_price: float) -> None:
        """记录权益数据点

        Args:
            current_price: 当前价格
        """
        position_value: float = sum(
            pos.get("quantity", 0) * current_price for pos in self.positions
        )
        total_equity: float = self.balance + position_value

        self.equity_curve.append({
            "timestamp": datetime.now().isoformat(),
            "equity": round(total_equity, 2),
            "balance": round(self.balance, 2),
            "position_value": round(position_value, 2),
        })

    def _save_trade(self, trade: Dict[str, Any]) -> None:
        """保存交易记录到CSV文件

        将交易记录追加写入 trades.csv 文件。
        如果文件不存在则创建并写入表头。

        Args:
            trade: 交易记录字典
        """
        try:
            file_path: str = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "data",
                "trades.csv"
            )

            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            file_exists: bool = os.path.exists(file_path)

            with open(file_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=trade.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(trade)

            logger.debug(f"交易记录已保存: {file_path}")

        except Exception as e:
            logger.error(f"保存交易记录失败: {e}")
