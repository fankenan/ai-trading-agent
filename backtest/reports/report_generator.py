"""
回测报告生成器模块

将回测结果转化为结构化的报告，支持 Markdown 和 JSON 格式输出。

报告内容包括:
- 策略名称与回测期间
- 核心绩效指标（总收益、最大回撤、胜率、盈亏比等）
- 交易统计
- 样本充足性判断
"""

import json
import logging
from typing import Any, Dict, List

import pandas as pd

from backtest.engine.backtest_engine import BacktestResult, Trade

logger = logging.getLogger(__name__)


class BacktestReportGenerator:
    """回测报告生成器

    将 BacktestResult 转换为可读的报告格式。

    Usage:
        generator = BacktestReportGenerator()
        report = generator.generate(result, strategy_name="均线策略")
        md_text = generator.to_markdown(report)
        json_text = generator.to_json(report)
    """

    # 样本充足性判断的最小交易次数阈值
    MIN_TRADES_FOR_RELIABILITY: int = 30

    def generate(self, result: BacktestResult, strategy_name: str = "") -> Dict[str, Any]:
        """生成回测报告

        Args:
            result: 回测结果对象
            strategy_name: 策略名称

        Returns:
            包含完整报告内容的字典
        """
        # 确定回测期间
        backtest_period = self._get_backtest_period(result)

        # 计算附加统计指标
        trade_stats = self._calculate_trade_stats(result.trades)

        # 样本充足性判断
        sufficiency = self._judge_sample_sufficiency(result.total_trades)

        # 综合评级
        rating = self._calculate_rating(result, sufficiency)

        report: Dict[str, Any] = {
            "strategy_name": strategy_name,
            "backtest_period": backtest_period,
            "performance": {
                "total_return": f"{result.total_return:.2%}",
                "max_drawdown": f"{result.max_drawdown:.2%}",
                "win_rate": f"{result.win_rate:.2%}",
                "profit_factor": (
                    f"{result.profit_factor:.2f}"
                    if result.profit_factor != float("inf")
                    else "无穷大（无亏损交易）"
                ),
                "total_trades": result.total_trades,
                "avg_holding_bars": f"{result.avg_holding_bars:.1f}",
            },
            "trade_statistics": trade_stats,
            "sample_sufficiency": sufficiency,
            "overall_rating": rating,
        }

        return report

    def to_markdown(self, report: Dict[str, Any]) -> str:
        """将报告转换为 Markdown 格式

        Args:
            report: 报告字典

        Returns:
            Markdown 格式的报告字符串
        """
        lines: List[str] = []

        # 标题
        lines.append(f"# 回测报告: {report['strategy_name']}")
        lines.append("")

        # 回测期间
        period = report["backtest_period"]
        lines.append(f"**回测期间**: {period['start']} ~ {period['end']}（共 {period['trading_days']} 个交易日）")
        lines.append("")

        # 核心绩效指标
        lines.append("## 核心绩效指标")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        perf = report["performance"]
        lines.append(f"| 总收益率 | {perf['total_return']} |")
        lines.append(f"| 最大回撤 | {perf['max_drawdown']} |")
        lines.append(f"| 胜率 | {perf['win_rate']} |")
        lines.append(f"| 盈亏比 | {perf['profit_factor']} |")
        lines.append(f"| 总交易次数 | {perf['total_trades']} |")
        lines.append(f"| 平均持仓K线数 | {perf['avg_holding_bars']} |")
        lines.append("")

        # 交易统计
        lines.append("## 交易统计")
        lines.append("")
        stats = report["trade_statistics"]
        lines.append("| 统计项 | 数值 |")
        lines.append("|--------|------|")
        lines.append(f"| 盈利交易次数 | {stats['winning_trades']} |")
        lines.append(f"| 亏损交易次数 | {stats['losing_trades']} |")
        lines.append(f"| 平均盈利 | {stats['avg_win']} |")
        lines.append(f"| 平均亏损 | {stats['avg_loss']} |")
        lines.append(f"| 最大单笔盈利 | {stats['max_win']} |")
        lines.append(f"| 最大单笔亏损 | {stats['max_loss']} |")
        lines.append(f"| 盈利交易平均持仓 | {stats['avg_win_holding_bars']} 根K线 |")
        lines.append(f"| 亏损交易平均持仓 | {stats['avg_loss_holding_bars']} 根K线 |")
        lines.append("")

        # 样本充足性
        lines.append("## 样本充足性")
        lines.append("")
        sufficiency = report["sample_sufficiency"]
        lines.append(f"**判断结果**: {sufficiency['judgment']}")
        lines.append(f"**说明**: {sufficiency['description']}")
        lines.append("")

        # 综合评级
        lines.append("## 综合评级")
        lines.append("")
        rating = report["overall_rating"]
        lines.append(f"**评级**: {rating['grade']}")
        lines.append(f"**评语**: {rating['comment']}")
        lines.append("")

        return "\n".join(lines)

    def to_json(self, report: Dict[str, Any]) -> str:
        """将报告转换为 JSON 格式

        Args:
            report: 报告字典

        Returns:
            JSON 格式的报告字符串
        """
        return json.dumps(report, ensure_ascii=False, indent=2)

    def _get_backtest_period(self, result: BacktestResult) -> Dict[str, Any]:
        """获取回测期间信息

        Args:
            result: 回测结果

        Returns:
            包含开始时间、结束时间、交易天数的字典
        """
        if result.equity_curve.empty:
            return {
                "start": "N/A",
                "end": "N/A",
                "trading_days": 0,
            }

        start_time = result.equity_curve["datetime"].iloc[0]
        end_time = result.equity_curve["datetime"].iloc[-1]
        trading_days = len(result.equity_curve)

        return {
            "start": str(start_time),
            "end": str(end_time),
            "trading_days": trading_days,
        }

    def _calculate_trade_stats(self, trades: List[Trade]) -> Dict[str, Any]:
        """计算交易统计指标

        Args:
            trades: 交易记录列表

        Returns:
            交易统计字典
        """
        if not trades:
            return {
                "winning_trades": 0,
                "losing_trades": 0,
                "avg_win": "N/A",
                "avg_loss": "N/A",
                "max_win": "N/A",
                "max_loss": "N/A",
                "avg_win_holding_bars": "N/A",
                "avg_loss_holding_bars": "N/A",
            }

        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]

        # 平均盈亏
        avg_win = (
            sum(t.pnl for t in winning_trades) / len(winning_trades)
            if winning_trades
            else 0.0
        )
        avg_loss = (
            sum(t.pnl for t in losing_trades) / len(losing_trades)
            if losing_trades
            else 0.0
        )

        # 最大单笔盈亏
        max_win = max((t.pnl for t in trades), default=0.0)
        max_loss = min((t.pnl for t in trades), default=0.0)

        # 盈利/亏损交易的平均持仓K线数
        avg_win_holding = (
            sum(t.holding_bars for t in winning_trades) / len(winning_trades)
            if winning_trades
            else 0.0
        )
        avg_loss_holding = (
            sum(t.holding_bars for t in losing_trades) / len(losing_trades)
            if losing_trades
            else 0.0
        )

        return {
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "avg_win": f"{avg_win:.2f}",
            "avg_loss": f"{avg_loss:.2f}",
            "max_win": f"{max_win:.2f}",
            "max_loss": f"{max_loss:.2f}",
            "avg_win_holding_bars": f"{avg_win_holding:.1f}",
            "avg_loss_holding_bars": f"{avg_loss_holding:.1f}",
        }

    def _judge_sample_sufficiency(self, total_trades: int) -> Dict[str, str]:
        """判断样本充足性

        根据交易次数判断回测结果的统计可靠性。

        Args:
            total_trades: 总交易次数

        Returns:
            包含判断结果和说明的字典
        """
        if total_trades >= self.MIN_TRADES_FOR_RELIABILITY:
            return {
                "judgment": "充足",
                "description": (
                    f"交易次数({total_trades}) >= {self.MIN_TRADES_FOR_RELIABILITY}，"
                    "样本量充足，回测结果具有统计意义。"
                ),
            }
        elif total_trades >= self.MIN_TRADES_FOR_RELIABILITY // 2:
            return {
                "judgment": "勉强",
                "description": (
                    f"交易次数({total_trades})介于 "
                    f"{self.MIN_TRADES_FOR_RELIABILITY // 2}~{self.MIN_TRADES_FOR_RELIABILITY} 之间，"
                    "样本量偏少，回测结果仅供参考。"
                ),
            }
        else:
            return {
                "judgment": "不足",
                "description": (
                    f"交易次数({total_trades}) < {self.MIN_TRADES_FOR_RELIABILITY // 2}，"
                    "样本量严重不足，回测结果不可靠，建议扩大回测时间范围。"
                ),
            }

    def _calculate_rating(
        self, result: BacktestResult, sufficiency: Dict[str, str]
    ) -> Dict[str, str]:
        """综合评级

        根据回测指标和样本充足性给出综合评级。

        评级标准:
        - A+: 总收益 > 50%, 最大回撤 < 10%, 胜率 > 60%, 样本充足
        - A:  总收益 > 30%, 最大回撤 < 15%, 胜率 > 55%, 样本充足
        - B:  总收益 > 15%, 最大回撤 < 25%, 胜率 > 45%
        - C:  总收益 > 0%, 其他条件不满足
        - D:  总收益 <= 0%

        Args:
            result: 回测结果
            sufficiency: 样本充足性判断

        Returns:
            包含评级和评语的字典
        """
        total_return = result.total_return
        max_drawdown = result.max_drawdown
        win_rate = result.win_rate
        is_sufficient = sufficiency["judgment"] == "充足"

        if (
            total_return > 0.50
            and max_drawdown < 0.10
            and win_rate > 0.60
            and is_sufficient
        ):
            return {
                "grade": "A+",
                "comment": "策略表现优异，高收益低回撤，样本充足，结果可信度高。",
            }
        elif (
            total_return > 0.30
            and max_drawdown < 0.15
            and win_rate > 0.55
            and is_sufficient
        ):
            return {
                "grade": "A",
                "comment": "策略表现良好，收益可观且风险可控，样本充足。",
            }
        elif total_return > 0.15 and max_drawdown < 0.25 and win_rate > 0.45:
            return {
                "grade": "B",
                "comment": "策略表现一般，有一定盈利能力但需关注风险控制。",
            }
        elif total_return > 0:
            return {
                "grade": "C",
                "comment": "策略微利，表现较弱，建议优化参数或更换策略逻辑。",
            }
        else:
            return {
                "grade": "D",
                "comment": "策略亏损，不建议实盘使用，需要重新审视策略逻辑。",
            }
