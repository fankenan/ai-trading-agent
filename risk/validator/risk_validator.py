"""
风控验证器

整合所有风控规则，对交易决策进行全面的风险验证。
风控验证器具有一票否决权：当检测到critical级别的风险时，
可以直接否决交易决策，无论评分系统的评分多高。

风控验证流程：
  1. 仓位大小检查
  2. 日内亏损检查
  3. 最大回撤检查
  4. 流动性检查
  5. 黑天鹅事件检查
  6. 综合评估并生成最终验证结果
"""

from typing import Dict, Any, List, Optional
from loguru import logger

from risk.rules.risk_rules import RiskRules


class RiskValidator:
    """风控验证器

    对交易决策进行全面的风险验证，具有一票否决权。

    Attributes:
        config: 风控配置参数
        rules: 风控规则实例
    """

    # 风险等级优先级（用于确定综合风险等级）
    RISK_LEVEL_PRIORITY: Dict[str, int] = {
        "low": 0,
        "medium": 1,
        "high": 2,
        "critical": 3,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """初始化风控验证器

        Args:
            config: 风控配置参数，包含以下可选字段：
                - max_position_pct: 最大仓位比例（默认0.30）
                - max_daily_loss: 最大日内亏损比例（默认0.05）
                - max_drawdown: 最大回撤比例（默认0.15）
                - min_volume: 最低成交量要求（默认100000）
                - enable_veto: 是否启用一票否决权（默认True）
        """
        self.config: Dict[str, Any] = config or {}
        self.rules: RiskRules = RiskRules()

        # 从配置中读取参数，提供默认值
        self.max_position_pct: float = self.config.get("max_position_pct", 0.30)
        self.max_daily_loss: float = self.config.get("max_daily_loss", 0.05)
        self.max_drawdown: float = self.config.get("max_drawdown", 0.15)
        self.min_volume: float = self.config.get("min_volume", 100000.0)
        self.enable_veto: bool = self.config.get("enable_veto", True)

        logger.info(
            f"风控验证器初始化: 最大仓位={self.max_position_pct:.0%}, "
            f"最大日亏损={self.max_daily_loss:.0%}, "
            f"最大回撤={self.max_drawdown:.0%}, "
            f"一票否决={'启用' if self.enable_veto else '禁用'}"
        )

    def validate(
        self,
        decision: Dict[str, Any],
        portfolio: Dict[str, Any],
        events: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """验证交易决策

        对交易决策执行全面的风控检查，返回验证结果。

        Args:
            decision: 决策分析器的输出，包含 action, position_suggestion 等
            portfolio: 投资组合信息，包含：
                - total_value: 总资产价值
                - daily_pnl: 当日盈亏比例
                - current_drawdown: 当前回撤比例
                - position_pct: 当前仓位比例
                - available_balance: 可用余额
            events: 当前事件列表（用于黑天鹅检测）

        Returns:
            包含以下字段的字典：
            - approved: 是否通过风控验证
            - risk_level: 综合风险等级（"low"/"medium"/"high"/"critical"）
            - warnings: 警告信息列表（不阻止交易，但需注意）
            - vetoes: 否决信息列表（阻止交易）
            - check_results: 各项检查的详细结果
            - adjusted_decision: 风控调整后的决策建议
        """
        logger.info("开始风控验证...")

        events = events or []
        warnings: List[str] = []
        vetoes: List[str] = []
        check_results: Dict[str, Any] = {}

        action: str = decision.get("action", "hold")

        # 仅在需要交易时执行风控检查
        if action == "hold":
            logger.info("操作为hold，跳过风控检查")
            return {
                "approved": True,
                "risk_level": "low",
                "warnings": [],
                "vetoes": [],
                "check_results": {},
                "adjusted_decision": decision,
            }

        # 1. 仓位大小检查
        position_pct: float = portfolio.get("position_pct", 0)
        suggested_pct: float = decision.get("position_suggestion", {}).get("position_pct", 0)
        total_position = position_pct + suggested_pct

        position_check = self.rules.check_position_size(
            total_position, self.max_position_pct
        )
        check_results["position_size"] = position_check

        if not position_check["passed"]:
            vetoes.append(position_check["message"])
        elif position_check["risk_level"] == "medium":
            warnings.append(position_check["message"])

        # 2. 日内亏损检查
        daily_pnl: float = portfolio.get("daily_pnl", 0)
        daily_loss_check = self.rules.check_daily_loss(daily_pnl, self.max_daily_loss)
        check_results["daily_loss"] = daily_loss_check

        if not daily_loss_check["passed"]:
            vetoes.append(daily_loss_check["message"])
        elif daily_loss_check["risk_level"] == "medium":
            warnings.append(daily_loss_check["message"])

        # 3. 最大回撤检查
        drawdown: float = portfolio.get("current_drawdown", 0)
        drawdown_check = self.rules.check_drawdown(drawdown, self.max_drawdown)
        check_results["drawdown"] = drawdown_check

        if not drawdown_check["passed"]:
            vetoes.append(drawdown_check["message"])
        elif drawdown_check["risk_level"] in ("medium", "high"):
            warnings.append(drawdown_check["message"])

        # 4. 流动性检查
        volume: float = portfolio.get("volume", 0)
        liquidity_check = self.rules.check_liquidity(volume, self.min_volume)
        check_results["liquidity"] = liquidity_check

        if not liquidity_check["passed"]:
            vetoes.append(liquidity_check["message"])
        elif liquidity_check["risk_level"] == "medium":
            warnings.append(liquidity_check["message"])

        # 5. 黑天鹅事件检查
        black_swan_check = self.rules.check_black_swan(events)
        check_results["black_swan"] = black_swan_check

        if not black_swan_check["passed"]:
            if self.enable_veto:
                vetoes.append(black_swan_check["message"])
            else:
                warnings.append(black_swan_check["message"])

        # 6. 综合评估
        approved: bool = len(vetoes) == 0
        risk_level: str = self._calculate_risk_level(check_results)

        # 7. 生成调整后的决策
        adjusted_decision: Dict[str, Any] = self._adjust_decision(
            decision, approved, risk_level, warnings
        )

        result: Dict[str, Any] = {
            "approved": approved,
            "risk_level": risk_level,
            "warnings": warnings,
            "vetoes": vetoes,
            "check_results": check_results,
            "adjusted_decision": adjusted_decision,
        }

        if approved:
            logger.info(f"风控验证通过，风险等级: {risk_level}")
        else:
            logger.warning(f"风控验证未通过！否决原因: {vetoes}")

        return result

    def _calculate_risk_level(self, check_results: Dict[str, Any]) -> str:
        """计算综合风险等级

        取所有检查中最高风险等级作为综合风险等级。

        Args:
            check_results: 各项检查结果

        Returns:
            综合风险等级
        """
        max_priority: int = 0
        overall_level: str = "low"

        for check_name, result in check_results.items():
            level: str = result.get("risk_level", "low")
            priority: int = self.RISK_LEVEL_PRIORITY.get(level, 0)

            if priority > max_priority:
                max_priority = priority
                overall_level = level

        return overall_level

    def _adjust_decision(
        self,
        decision: Dict[str, Any],
        approved: bool,
        risk_level: str,
        warnings: List[str],
    ) -> Dict[str, Any]:
        """根据风控结果调整决策

        当风控未通过时，将决策调整为hold。
        当存在警告时，适当降低仓位建议。

        Args:
            decision: 原始决策
            approved: 是否通过风控
            risk_level: 风险等级
            warnings: 警告列表

        Returns:
            调整后的决策
        """
        adjusted = decision.copy()

        if not approved:
            # 风控否决，强制hold
            adjusted["action"] = "hold"
            adjusted["position_suggestion"] = {
                "action": "hold",
                "position_pct": 0.0,
                "quantity": 0.0,
                "reason": "风控否决，强制持有",
            }
            adjusted["vetoed"] = True
        elif risk_level == "high":
            # 高风险，减半仓位
            original_suggestion = decision.get("position_suggestion", {})
            adjusted["position_suggestion"] = {
                **original_suggestion,
                "position_pct": original_suggestion.get("position_pct", 0) * 0.5,
                "quantity": original_suggestion.get("quantity", 0) * 0.5,
                "reason": f"风控警告：高风险等级，仓位减半。原始建议: {original_suggestion.get('reason', '')}",
            }
            adjusted["risk_adjusted"] = True
        elif risk_level == "medium" and warnings:
            # 中等风险，减少30%仓位
            original_suggestion = decision.get("position_suggestion", {})
            adjusted["position_suggestion"] = {
                **original_suggestion,
                "position_pct": original_suggestion.get("position_pct", 0) * 0.7,
                "quantity": original_suggestion.get("quantity", 0) * 0.7,
                "reason": f"风控警告：中等风险等级，仓位减少30%。原始建议: {original_suggestion.get('reason', '')}",
            }
            adjusted["risk_adjusted"] = True

        return adjusted
