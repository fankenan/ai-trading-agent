"""
风控规则模块

定义和检查各类风控规则，包括：
  - 仓位大小检查：防止单次交易仓位过大
  - 日内亏损检查：防止单日亏损超过限额
  - 最大回撤检查：防止整体回撤超过限额
  - 流动性检查：确保交易对有足够的流动性
  - 黑天鹅事件检查：检测极端市场事件

每条规则返回检查结果，包含是否通过、风险等级和描述信息。
"""

from typing import Dict, Any, List, Optional
from loguru import logger


class RiskRules:
    """风控规则集

    提供多种风控规则的检查方法。
    每个检查方法独立运行，返回标准化的检查结果。

    Attributes:
        无
    """

    def check_position_size(
        self,
        position_pct: float,
        max_pct: float = 0.30,
    ) -> Dict[str, Any]:
        """检查仓位大小

        验证当前交易仓位是否超过最大允许比例。

        Args:
            position_pct: 当前仓位比例（0.0 - 1.0）
            max_pct: 最大允许仓位比例（默认0.30，即30%）

        Returns:
            包含以下字段的字典：
            - passed: 是否通过检查
            - risk_level: 风险等级（"low"/"medium"/"high"）
            - message: 检查结果描述
            - current_value: 当前仓位比例
            - limit_value: 限制值
        """
        if position_pct < 0:
            logger.warning(f"仓位比例为负值: {position_pct}，自动修正为0")
            position_pct = 0

        passed: bool = position_pct <= max_pct

        if position_pct <= max_pct * 0.5:
            risk_level = "low"
            message = f"仓位比例{position_pct:.2%}处于安全范围内（限制{max_pct:.0%}）"
        elif position_pct <= max_pct * 0.8:
            risk_level = "low"
            message = f"仓位比例{position_pct:.2%}适中（限制{max_pct:.0%}）"
        elif position_pct <= max_pct:
            risk_level = "medium"
            message = f"仓位比例{position_pct:.2%}接近上限（限制{max_pct:.0%}），请注意控制"
        else:
            risk_level = "high"
            message = f"仓位比例{position_pct:.2%}超过上限{max_pct:.0%}！建议减仓"

        result: Dict[str, Any] = {
            "passed": passed,
            "risk_level": risk_level,
            "message": message,
            "current_value": position_pct,
            "limit_value": max_pct,
        }

        logger.debug(f"仓位检查: {message}")
        return result

    def check_daily_loss(
        self,
        daily_pnl: float,
        max_loss: float = 0.05,
    ) -> Dict[str, Any]:
        """检查日内亏损

        验证当日盈亏是否超过最大允许亏损额。

        Args:
            daily_pnl: 当日盈亏比例（负值表示亏损，如-0.03表示亏损3%）
            max_loss: 最大允许亏损比例（默认0.05，即5%）

        Returns:
            包含以下字段的字典：
            - passed: 是否通过检查
            - risk_level: 风险等级
            - message: 检查结果描述
            - current_value: 当前盈亏比例
            - limit_value: 限制值
        """
        passed: bool = daily_pnl >= -max_loss

        if daily_pnl >= 0:
            risk_level = "low"
            message = f"当日盈利{daily_pnl:.2%}"
        elif daily_pnl >= -max_loss * 0.5:
            risk_level = "low"
            message = f"当日亏损{daily_pnl:.2%}，在安全范围内（限制-{max_loss:.0%}）"
        elif daily_pnl >= -max_loss * 0.8:
            risk_level = "medium"
            message = f"当日亏损{daily_pnl:.2%}，接近限制（限制-{max_loss:.0%}），请谨慎操作"
        elif daily_pnl >= -max_loss:
            risk_level = "high"
            message = f"当日亏损{daily_pnl:.2%}，接近止损线（限制-{max_loss:.0%}）！"
        else:
            risk_level = "critical"
            message = f"当日亏损{daily_pnl:.2%}已超过止损线（限制-{max_loss:.0%}）！建议停止交易！"

        result: Dict[str, Any] = {
            "passed": passed,
            "risk_level": risk_level,
            "message": message,
            "current_value": daily_pnl,
            "limit_value": -max_loss,
        }

        logger.debug(f"日内亏损检查: {message}")
        return result

    def check_drawdown(
        self,
        current_drawdown: float,
        max_drawdown: float = 0.15,
    ) -> Dict[str, Any]:
        """检查最大回撤

        验证当前回撤是否超过最大允许回撤。

        Args:
            current_drawdown: 当前回撤比例（正值，如0.10表示回撤10%）
            max_drawdown: 最大允许回撤比例（默认0.15，即15%）

        Returns:
            包含以下字段的字典：
            - passed: 是否通过检查
            - risk_level: 风险等级
            - message: 检查结果描述
            - current_value: 当前回撤
            - limit_value: 限制值
        """
        if current_drawdown < 0:
            logger.warning(f"回撤值为负: {current_drawdown}，自动修正为0")
            current_drawdown = 0

        passed: bool = current_drawdown <= max_drawdown

        if current_drawdown <= max_drawdown * 0.3:
            risk_level = "low"
            message = f"当前回撤{current_drawdown:.2%}，处于正常范围（限制{max_drawdown:.0%}）"
        elif current_drawdown <= max_drawdown * 0.6:
            risk_level = "medium"
            message = f"当前回撤{current_drawdown:.2%}，需关注（限制{max_drawdown:.0%}）"
        elif current_drawdown <= max_drawdown * 0.8:
            risk_level = "high"
            message = f"当前回撤{current_drawdown:.2%}，接近限制（限制{max_drawdown:.0%}）！"
        else:
            risk_level = "critical"
            message = f"当前回撤{current_drawdown:.2%}已超过限制{max_drawdown:.0%}！建议立即减仓！"

        result: Dict[str, Any] = {
            "passed": passed,
            "risk_level": risk_level,
            "message": message,
            "current_value": current_drawdown,
            "limit_value": max_drawdown,
        }

        logger.debug(f"回撤检查: {message}")
        return result

    def check_liquidity(
        self,
        volume: float,
        min_volume: float = 100000.0,
    ) -> Dict[str, Any]:
        """检查流动性

        验证交易对的成交量是否满足最低流动性要求。

        Args:
            volume: 当前成交量（通常为24小时成交量）
            min_volume: 最低成交量要求（默认100000）

        Returns:
            包含以下字段的字典：
            - passed: 是否通过检查
            - risk_level: 风险等级
            - message: 检查结果描述
            - current_value: 当前成交量
            - limit_value: 限制值
        """
        passed: bool = volume >= min_volume

        if volume >= min_volume * 3:
            risk_level = "low"
            message = f"成交量{volume:,.0f}充足（最低要求{min_volume:,.0f}）"
        elif volume >= min_volume * 1.5:
            risk_level = "low"
            message = f"成交量{volume:,.0f}良好（最低要求{min_volume:,.0f}）"
        elif volume >= min_volume:
            risk_level = "medium"
            message = f"成交量{volume:,.0f}刚好达标（最低要求{min_volume:,.0f}），滑点可能较大"
        elif volume >= min_volume * 0.5:
            risk_level = "high"
            message = f"成交量{volume:,.0f}不足（最低要求{min_volume:,.0f}），流动性风险较高"
        else:
            risk_level = "critical"
            message = f"成交量{volume:,.0f}严重不足（最低要求{min_volume:,.0f}），不建议交易！"

        result: Dict[str, Any] = {
            "passed": passed,
            "risk_level": risk_level,
            "message": message,
            "current_value": volume,
            "limit_value": min_volume,
        }

        logger.debug(f"流动性检查: {message}")
        return result

    def check_black_swan(
        self,
        events: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """检查黑天鹅事件

        检测事件列表中是否存在黑天鹅级别的极端事件。
        黑天鹅事件特征：S级事件且具有高度不确定性。

        Args:
            events: 事件列表，每个事件应包含 'level' 和 'type' 字段

        Returns:
            包含以下字段的字典：
            - passed: 是否通过检查（无黑天鹅事件为通过）
            - risk_level: 风险等级
            - message: 检查结果描述
            - black_swan_events: 检测到的黑天鹅事件列表
        """
        events = events or []
        black_swan_events: List[Dict[str, Any]] = []

        # 黑天鹅事件关键词
        black_swan_keywords: List[str] = [
            "黑天鹅", "崩盘", "暴跌", "暴涨", "熔断",
            "黑客攻击", "交易所跑路", "监管禁止", "战争",
            "制裁", "违约", "破产",
        ]

        for event in events:
            level: str = event.get("level", "").upper()
            event_text: str = event.get("text", "").lower() + event.get("title", "").lower()

            # S级事件自动标记为潜在黑天鹅
            if level == "S":
                black_swan_events.append(event)
                continue

            # 检查是否包含黑天鹅关键词
            for keyword in black_swan_keywords:
                if keyword in event_text:
                    black_swan_events.append(event)
                    break

        passed: bool = len(black_swan_events) == 0

        if passed:
            risk_level = "low"
            message = "未检测到黑天鹅事件"
        elif len(black_swan_events) == 1:
            risk_level = "high"
            message = f"检测到1个潜在黑天鹅事件，建议暂停交易或大幅降低仓位"
        else:
            risk_level = "critical"
            message = f"检测到{len(black_swan_events)}个潜在黑天鹅事件！强烈建议停止所有交易！"

        result: Dict[str, Any] = {
            "passed": passed,
            "risk_level": risk_level,
            "message": message,
            "black_swan_events": black_swan_events,
        }

        logger.debug(f"黑天鹅检查: {message}")
        return result
