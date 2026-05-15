"""
综合报告生成器

生成交易系统的各类报告，包括：
  - 每日交易报告：汇总当日市场数据、评分、决策、风控和持仓情况
  - 回测报告：汇总策略回测结果，包含关键绩效指标

报告支持Markdown和JSON两种输出格式。
"""

from typing import Dict, Any, Optional
from datetime import datetime
import json
from loguru import logger


class ReportGenerator:
    """综合报告生成器

    整合各模块的输出数据，生成结构化的交易报告。

    Attributes:
        无
    """

    def generate_daily(
        self,
        market_data: Optional[Dict[str, Any]] = None,
        score: Optional[Dict[str, Any]] = None,
        decision: Optional[Dict[str, Any]] = None,
        risk: Optional[Dict[str, Any]] = None,
        portfolio: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """生成每日交易报告

        汇总当日所有模块的输出，生成完整的交易日报。

        Args:
            market_data: 市场数据，包含价格、成交量等
            score: 评分系统输出
            decision: 决策分析器输出
            risk: 风控验证器输出
            portfolio: 投资组合状态

        Returns:
            每日报告字典，包含：
            - report_type: 报告类型
            - timestamp: 生成时间
            - summary: 报告摘要
            - sections: 各模块详细数据
        """
        market_data = market_data or {}
        score = score or {}
        decision = decision or {}
        risk = risk or {}
        portfolio = portfolio or {}

        timestamp: str = datetime.now().isoformat()

        # 生成报告摘要
        total_score: float = score.get("total_score", 0)
        action: str = decision.get("action", "hold")
        risk_approved: bool = risk.get("approved", True)
        risk_level: str = risk.get("risk_level", "low")
        total_equity: float = portfolio.get("total_equity", 0)
        daily_pnl_pct: float = portfolio.get("daily_pnl_pct", 0)

        summary: str = (
            f"综合评分{total_score}分，建议操作{action}。"
            f"风控{'通过' if risk_approved else '未通过'}"
            f"（风险等级: {risk_level}）。"
            f"总权益{total_equity:.2f}，"
            f"当日盈亏{daily_pnl_pct:.2%}。"
        )

        report: Dict[str, Any] = {
            "report_type": "daily",
            "timestamp": timestamp,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "summary": summary,
            "sections": {
                "market": {
                    "current_price": market_data.get("current_price", 0),
                    "price_change_24h": market_data.get("price_change_24h", 0),
                    "volume_24h": market_data.get("volume_24h", 0),
                    "high_24h": market_data.get("high_24h", 0),
                    "low_24h": market_data.get("low_24h", 0),
                },
                "scoring": {
                    "total_score": total_score,
                    "raw_score": score.get("raw_score", total_score),
                    "recommendation": score.get("recommendation", ""),
                    "confidence": score.get("confidence", 0),
                    "module_scores": {
                        name: {
                            "score": data.get("score", 0),
                            "details": data.get("details", ""),
                        }
                        for name, data in score.get("module_scores", {}).items()
                    },
                    "risk_penalty": score.get("risk_penalty", 0),
                },
                "decision": {
                    "action": action,
                    "confidence": decision.get("confidence", 0),
                    "reasoning": decision.get("reasoning", ""),
                    "entry_condition": decision.get("entry_condition", ""),
                    "invalid_condition": decision.get("invalid_condition", ""),
                    "position_suggestion": decision.get("position_suggestion", {}),
                    "conflict_signals": decision.get("conflict_signals", []),
                },
                "risk_control": {
                    "approved": risk_approved,
                    "risk_level": risk_level,
                    "warnings": risk.get("warnings", []),
                    "vetoes": risk.get("vetoes", []),
                },
                "portfolio": {
                    "total_equity": total_equity,
                    "balance": portfolio.get("balance", 0),
                    "total_pnl": portfolio.get("total_pnl", 0),
                    "total_pnl_pct": portfolio.get("total_pnl_pct", 0),
                    "position_count": portfolio.get("position_count", 0),
                    "daily_pnl_pct": daily_pnl_pct,
                },
            },
        }

        logger.info(f"每日报告已生成: {summary}")
        return report

    def generate_backtest(
        self,
        backtest_result: Dict[str, Any],
        strategy_name: str = "默认策略",
    ) -> Dict[str, Any]:
        """生成回测报告

        汇总策略回测结果，生成包含关键绩效指标的回测报告。

        Args:
            backtest_result: 回测结果，包含：
                - total_return: 总收益率
                - annual_return: 年化收益率
                - max_drawdown: 最大回撤
                - sharpe_ratio: 夏普比率
                - win_rate: 胜率
                - total_trades: 总交易次数
                - profit_trades: 盈利交易次数
                - loss_trades: 亏损交易次数
                - avg_profit: 平均盈利
                - avg_loss: 平均亏损
                - profit_factor: 盈亏比
                - equity_curve: 权益曲线数据
            strategy_name: 策略名称

        Returns:
            回测报告字典
        """
        timestamp: str = datetime.now().isoformat()

        total_return: float = backtest_result.get("total_return", 0)
        max_drawdown: float = backtest_result.get("max_drawdown", 0)
        sharpe_ratio: float = backtest_result.get("sharpe_ratio", 0)
        win_rate: float = backtest_result.get("win_rate", 0)

        # 综合评价
        if total_return > 0.5 and max_drawdown < 0.2 and sharpe_ratio > 1.5:
            evaluation = "优秀"
        elif total_return > 0.2 and max_drawdown < 0.3 and sharpe_ratio > 1.0:
            evaluation = "良好"
        elif total_return > 0:
            evaluation = "一般"
        else:
            evaluation = "较差"

        summary: str = (
            f"策略'{strategy_name}'回测完成。"
            f"总收益率{total_return:.2%}，最大回撤{max_drawdown:.2%}，"
            f"夏普比率{sharpe_ratio:.2f}，胜率{win_rate:.2%}。"
            f"综合评价: {evaluation}。"
        )

        report: Dict[str, Any] = {
            "report_type": "backtest",
            "timestamp": timestamp,
            "strategy_name": strategy_name,
            "summary": summary,
            "evaluation": evaluation,
            "performance_metrics": {
                "total_return": total_return,
                "annual_return": backtest_result.get("annual_return", 0),
                "max_drawdown": max_drawdown,
                "sharpe_ratio": sharpe_ratio,
                "sortino_ratio": backtest_result.get("sortino_ratio", 0),
                "calmar_ratio": backtest_result.get("calmar_ratio", 0),
                "win_rate": win_rate,
                "total_trades": backtest_result.get("total_trades", 0),
                "profit_trades": backtest_result.get("profit_trades", 0),
                "loss_trades": backtest_result.get("loss_trades", 0),
                "avg_profit": backtest_result.get("avg_profit", 0),
                "avg_loss": backtest_result.get("avg_loss", 0),
                "profit_factor": backtest_result.get("profit_factor", 0),
                "max_consecutive_wins": backtest_result.get("max_consecutive_wins", 0),
                "max_consecutive_losses": backtest_result.get("max_consecutive_losses", 0),
            },
        }

        logger.info(f"回测报告已生成: {summary}")
        return report

    def to_markdown(self, report: Dict[str, Any]) -> str:
        """将报告转换为Markdown格式

        Args:
            report: 报告字典

        Returns:
            Markdown格式的报告字符串
        """
        report_type: str = report.get("report_type", "unknown")

        if report_type == "daily":
            return self._daily_to_markdown(report)
        elif report_type == "backtest":
            return self._backtest_to_markdown(report)
        else:
            return f"# 未知报告类型\n\n```json\n{json.dumps(report, ensure_ascii=False, indent=2)}\n```"

    def to_json(self, report: Dict[str, Any]) -> str:
        """将报告转换为JSON格式

        Args:
            report: 报告字典

        Returns:
            JSON格式的报告字符串
        """
        return json.dumps(report, ensure_ascii=False, indent=2, default=str)

    def _daily_to_markdown(self, report: Dict[str, Any]) -> str:
        """将每日报告转换为Markdown格式

        Args:
            report: 每日报告字典

        Returns:
            Markdown字符串
        """
        sections = report.get("sections", {})
        lines: list = []

        lines.append(f"# AI量化交易日报")
        lines.append(f"")
        lines.append(f"**日期**: {report.get('date', 'N/A')}")
        lines.append(f"**生成时间**: {report.get('timestamp', 'N/A')}")
        lines.append(f"")
        lines.append(f"## 摘要")
        lines.append(f"")
        lines.append(f"{report.get('summary', '无摘要')}")
        lines.append(f"")

        # 市场概况
        market = sections.get("market", {})
        lines.append(f"## 市场概况")
        lines.append(f"")
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 当前价格 | {market.get('current_price', 'N/A')} |")
        lines.append(f"| 24h涨跌幅 | {market.get('price_change_24h', 'N/A')} |")
        lines.append(f"| 24h成交量 | {market.get('volume_24h', 'N/A')} |")
        lines.append(f"| 24h最高 | {market.get('high_24h', 'N/A')} |")
        lines.append(f"| 24h最低 | {market.get('low_24h', 'N/A')} |")
        lines.append(f"")

        # 评分详情
        scoring = sections.get("scoring", {})
        lines.append(f"## 评分详情")
        lines.append(f"")
        lines.append(f"- **综合评分**: {scoring.get('total_score', 'N/A')}分")
        lines.append(f"- **原始评分**: {scoring.get('raw_score', 'N/A')}分")
        lines.append(f"- **操作建议**: {scoring.get('recommendation', 'N/A')}")
        lines.append(f"- **置信度**: {scoring.get('confidence', 0):.0%}")
        lines.append(f"- **风险惩罚**: {scoring.get('risk_penalty', 0):.2%}")
        lines.append(f"")

        module_scores = scoring.get("module_scores", {})
        if module_scores:
            lines.append(f"| 模块 | 评分 | 详情 |")
            lines.append(f"|------|------|------|")
            for name, data in module_scores.items():
                lines.append(f"| {name} | {data.get('score', 'N/A')} | {data.get('details', 'N/A')} |")
            lines.append(f"")

        # 决策分析
        decision = sections.get("decision", {})
        lines.append(f"## 决策分析")
        lines.append(f"")
        lines.append(f"- **操作建议**: {decision.get('action', 'N/A')}")
        lines.append(f"- **置信度**: {decision.get('confidence', 0):.0%}")
        lines.append(f"- **入场条件**: {decision.get('entry_condition', 'N/A')}")
        lines.append(f"- **失效条件**: {decision.get('invalid_condition', 'N/A')}")
        lines.append(f"")

        conflict_signals = decision.get("conflict_signals", [])
        if conflict_signals:
            lines.append(f"**冲突信号**:")
            for signal in conflict_signals:
                lines.append(f"- {signal}")
            lines.append(f"")

        # 风控状态
        risk_control = sections.get("risk_control", {})
        lines.append(f"## 风控状态")
        lines.append(f"")
        lines.append(f"- **验证结果**: {'通过' if risk_control.get('approved', True) else '未通过'}")
        lines.append(f"- **风险等级**: {risk_control.get('risk_level', 'N/A')}")
        lines.append(f"")

        warnings = risk_control.get("warnings", [])
        if warnings:
            lines.append(f"**警告**:")
            for w in warnings:
                lines.append(f"- {w}")
            lines.append(f"")

        vetoes = risk_control.get("vetoes", [])
        if vetoes:
            lines.append(f"**否决原因**:")
            for v in vetoes:
                lines.append(f"- {v}")
            lines.append(f"")

        # 持仓状态
        portfolio_section = sections.get("portfolio", {})
        lines.append(f"## 持仓状态")
        lines.append(f"")
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 总权益 | {portfolio_section.get('total_equity', 'N/A')} |")
        lines.append(f"| 可用余额 | {portfolio_section.get('balance', 'N/A')} |")
        lines.append(f"| 总盈亏 | {portfolio_section.get('total_pnl', 'N/A')} ({portfolio_section.get('total_pnl_pct', 0):.2%}) |")
        lines.append(f"| 当日盈亏 | {portfolio_section.get('daily_pnl_pct', 0):.2%} |")
        lines.append(f"| 持仓数量 | {portfolio_section.get('position_count', 0)} |")
        lines.append(f"")

        return "\n".join(lines)

    def _backtest_to_markdown(self, report: Dict[str, Any]) -> str:
        """将回测报告转换为Markdown格式

        Args:
            report: 回测报告字典

        Returns:
            Markdown字符串
        """
        metrics = report.get("performance_metrics", {})
        lines: list = []

        lines.append(f"# 策略回测报告")
        lines.append(f"")
        lines.append(f"**策略名称**: {report.get('strategy_name', 'N/A')}")
        lines.append(f"**生成时间**: {report.get('timestamp', 'N/A')}")
        lines.append(f"**综合评价**: {report.get('evaluation', 'N/A')}")
        lines.append(f"")
        lines.append(f"## 摘要")
        lines.append(f"")
        lines.append(f"{report.get('summary', '无摘要')}")
        lines.append(f"")

        lines.append(f"## 绩效指标")
        lines.append(f"")
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 总收益率 | {metrics.get('total_return', 0):.2%} |")
        lines.append(f"| 年化收益率 | {metrics.get('annual_return', 0):.2%} |")
        lines.append(f"| 最大回撤 | {metrics.get('max_drawdown', 0):.2%} |")
        lines.append(f"| 夏普比率 | {metrics.get('sharpe_ratio', 0):.2f} |")
        lines.append(f"| 索提诺比率 | {metrics.get('sortino_ratio', 0):.2f} |")
        lines.append(f"| 卡玛比率 | {metrics.get('calmar_ratio', 0):.2f} |")
        lines.append(f"| 胜率 | {metrics.get('win_rate', 0):.2%} |")
        lines.append(f"| 盈亏比 | {metrics.get('profit_factor', 0):.2f} |")
        lines.append(f"| 总交易次数 | {metrics.get('total_trades', 0)} |")
        lines.append(f"| 盈利次数 | {metrics.get('profit_trades', 0)} |")
        lines.append(f"| 亏损次数 | {metrics.get('loss_trades', 0)} |")
        lines.append(f"| 平均盈利 | {metrics.get('avg_profit', 0):.2f} |")
        lines.append(f"| 平均亏损 | {metrics.get('avg_loss', 0):.2f} |")
        lines.append(f"| 最大连胜 | {metrics.get('max_consecutive_wins', 0)} |")
        lines.append(f"| 最大连亏 | {metrics.get('max_consecutive_losses', 0)} |")
        lines.append(f"")

        return "\n".join(lines)
