"""
决策分析器

核心决策引擎，基于评分系统的综合评分、当前价格和持仓信息，
生成具体的交易决策。

决策逻辑：
  - 综合评分 >= 65：考虑买入
  - 综合评分 <= 35：考虑卖出
  - 35 < 综合评分 < 65：持有观望
  - 结合持仓状态调整决策（已有持仓时降低买入倾向）
  - 识别冲突信号并提供警告
"""

from typing import Dict, Any, List, Optional
from loguru import logger


class DecisionAnalyzer:
    """决策分析器

    接收评分系统的输出结果，结合当前市场价格和持仓状态，
    经过分析后生成具体的交易决策。

    Attributes:
        buy_threshold: 买入阈值（默认65）
        sell_threshold: 卖出阈值（默认35）
        max_position_pct: 最大持仓比例（默认0.3，即30%）
    """

    def __init__(
        self,
        buy_threshold: float = 65.0,
        sell_threshold: float = 35.0,
        max_position_pct: float = 0.30,
    ) -> None:
        """初始化决策分析器

        Args:
            buy_threshold: 买入评分阈值（默认65）
            sell_threshold: 卖出评分阈值（默认35）
            max_position_pct: 单次最大建仓比例（默认0.30）
        """
        self.buy_threshold: float = buy_threshold
        self.sell_threshold: float = sell_threshold
        self.max_position_pct: float = max_position_pct

        logger.info(
            f"决策分析器初始化: 买入阈值={buy_threshold}, "
            f"卖出阈值={sell_threshold}, 最大持仓={max_position_pct:.0%}"
        )

    def analyze(
        self,
        score_result: Dict[str, Any],
        current_price: float,
        position: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """分析评分结果并生成交易决策

        综合考虑评分、价格和持仓状态，生成具体的交易决策。

        Args:
            score_result: 评分系统的输出结果，包含 total_score, module_scores 等
            current_price: 当前市场价格
            position: 当前持仓信息，格式为：
                {
                    "symbol": str,          # 交易对
                    "quantity": float,      # 持有数量
                    "avg_cost": float,      # 平均成本
                    "current_value": float, # 当前市值
                    "pnl_pct": float,       # 盈亏百分比
                }
                如果为None，表示当前无持仓。

        Returns:
            包含以下字段的字典：
            - action: 操作建议（"buy"/"sell"/"hold"）
            - entry_condition: 入场条件描述
            - invalid_condition: 失效条件描述
            - position_suggestion: 仓位建议
            - conflict_signals: 冲突信号列表
            - confidence: 决策置信度（0.0-1.0）
            - reasoning: 决策推理过程
            - score_snapshot: 评分快照
        """
        position = position or {}
        total_score: float = score_result.get("total_score", 50)
        module_scores: Dict[str, Any] = score_result.get("module_scores", {})
        confidence: float = score_result.get("confidence", 0.5)

        logger.info(
            f"开始决策分析: 综合评分={total_score}, "
            f"当前价格={current_price}, "
            f"持仓={'有' if position else '无'}"
        )

        # 1. 识别冲突信号
        conflict_signals: List[str] = self._detect_conflicts(module_scores)

        # 2. 确定基础操作方向
        action: str = self._determine_action(total_score, position)

        # 3. 生成入场和失效条件
        entry_condition: str = self._generate_entry_condition(action, total_score, current_price)
        invalid_condition: str = self._generate_invalid_condition(action, total_score, current_price)

        # 4. 计算仓位建议
        position_suggestion: Dict[str, Any] = self._calculate_position_suggestion(
            action, total_score, position, current_price
        )

        # 5. 调整置信度
        adjusted_confidence: float = self._adjust_confidence(
            confidence, conflict_signals, action, total_score
        )

        # 6. 生成推理过程
        reasoning: str = self._generate_reasoning(
            total_score, module_scores, action, position, conflict_signals
        )

        result: Dict[str, Any] = {
            "action": action,
            "entry_condition": entry_condition,
            "invalid_condition": invalid_condition,
            "position_suggestion": position_suggestion,
            "conflict_signals": conflict_signals,
            "confidence": adjusted_confidence,
            "reasoning": reasoning,
            "score_snapshot": {
                "total_score": total_score,
                "raw_score": score_result.get("raw_score", total_score),
                "recommendation": score_result.get("recommendation", ""),
            },
        }

        logger.info(
            f"决策完成: 操作={action}, 置信度={adjusted_confidence:.2%}, "
            f"冲突信号={len(conflict_signals)}个"
        )

        return result

    def _determine_action(
        self,
        total_score: float,
        position: Dict[str, Any],
    ) -> str:
        """确定基础操作方向

        根据综合评分和当前持仓状态确定操作方向。

        Args:
            total_score: 综合评分
            position: 当前持仓信息

        Returns:
            操作方向（"buy"/"sell"/"hold"）
        """
        has_position: bool = bool(position and position.get("quantity", 0) > 0)

        if total_score >= self.buy_threshold:
            if has_position:
                # 已有持仓，评分高但不再加仓
                return "hold"
            return "buy"
        elif total_score <= self.sell_threshold:
            if has_position:
                return "sell"
            return "hold"  # 无持仓时不能卖出
        else:
            return "hold"

    def _detect_conflicts(self, module_scores: Dict[str, Any]) -> List[str]:
        """检测模块间的冲突信号

        当不同评分模块给出矛盾信号时，记录冲突。

        Args:
            module_scores: 各模块评分结果

        Returns:
            冲突信号列表
        """
        conflicts: List[str] = []

        scores: Dict[str, float] = {}
        for name, result in module_scores.items():
            if isinstance(result, dict) and "score" in result:
                scores[name] = result["score"]

        if len(scores) < 2:
            return conflicts

        # 检查事件评分与技术评分是否冲突
        event_score = scores.get("event", 50)
        tech_score = scores.get("technical", 50)

        if event_score >= 70 and tech_score <= 30:
            conflicts.append("事件利好但技术面看空")
        elif event_score <= 30 and tech_score >= 70:
            conflicts.append("事件利空但技术面看多")

        # 检查情绪评分与K线评分是否冲突
        sentiment_score = scores.get("sentiment", 50)
        kline_score = scores.get("kline", 50)

        if sentiment_score >= 70 and kline_score <= 30:
            conflicts.append("情绪积极但K线结构偏空")
        elif sentiment_score <= 30 and kline_score >= 70:
            conflicts.append("情绪消极但K线结构偏多")

        # 检查是否有模块评分极端偏离
        for name, score in scores.items():
            if score >= 90:
                conflicts.append(f"{name}模块评分极高({score})，可能存在异常")
            elif score <= 10:
                conflicts.append(f"{name}模块评分极低({score})，可能存在异常")

        return conflicts

    def _generate_entry_condition(
        self,
        action: str,
        score: float,
        price: float,
    ) -> str:
        """生成入场条件

        Args:
            action: 操作方向
            score: 综合评分
            price: 当前价格

        Returns:
            入场条件描述
        """
        if action == "buy":
            return (
                f"综合评分{score}分，超过买入阈值{self.buy_threshold}分。"
                f"建议在当前价格{price}附近入场，"
                f"分批建仓以控制风险。"
            )
        elif action == "sell":
            return (
                f"综合评分{score}分，低于卖出阈值{self.sell_threshold}分。"
                f"建议在当前价格{price}附近减仓或清仓。"
            )
        else:
            return (
                f"综合评分{score}分，处于观望区间"
                f"({self.sell_threshold}-{self.buy_threshold})。"
                f"暂不建议操作。"
            )

    def _generate_invalid_condition(
        self,
        action: str,
        score: float,
        price: float,
    ) -> str:
        """生成失效条件

        Args:
            action: 操作方向
            score: 综合评分
            price: 当前价格

        Returns:
            失效条件描述
        """
        if action == "buy":
            return (
                f"若综合评分跌破{self.buy_threshold}分，"
                f"或价格跌破当前价格{-3:.0%}（即{price * 0.97:.2f}），"
                f"则买入建议失效。"
            )
        elif action == "sell":
            return (
                f"若综合评分回升至{self.sell_threshold}分以上，"
                f"或价格反弹超过当前价格{3:.0%}（即{price * 1.03:.2f}），"
                f"则卖出建议失效。"
            )
        else:
            return (
                f"若综合评分突破{self.buy_threshold}分（看多）或"
                f"跌破{self.sell_threshold}分（看空），"
                f"则观望建议更新为对应操作。"
            )

    def _calculate_position_suggestion(
        self,
        action: str,
        score: float,
        position: Dict[str, Any],
        current_price: float,
    ) -> Dict[str, Any]:
        """计算仓位建议

        根据操作方向和评分强度计算建议仓位。

        Args:
            action: 操作方向
            score: 综合评分
            position: 当前持仓
            current_price: 当前价格

        Returns:
            仓位建议字典
        """
        suggestion: Dict[str, Any] = {
            "action": action,
            "position_pct": 0.0,
            "quantity": 0.0,
            "reason": "",
        }

        if action == "buy":
            # 根据评分强度计算仓位比例
            if score >= 80:
                pct = self.max_position_pct
            elif score >= 70:
                pct = self.max_position_pct * 0.7
            else:
                pct = self.max_position_pct * 0.5

            suggestion["position_pct"] = round(pct, 4)
            suggestion["reason"] = f"评分{score}分，建议建仓{pct:.0%}"
        elif action == "sell":
            current_qty: float = position.get("quantity", 0)
            if score <= 20:
                # 极低评分，建议全部清仓
                suggestion["quantity"] = current_qty
                suggestion["reason"] = f"评分{score}分，建议全部清仓"
            elif score <= 30:
                # 低评分，建议减仓50%
                suggestion["quantity"] = round(current_qty * 0.5, 8)
                suggestion["reason"] = f"评分{score}分，建议减仓50%"
            else:
                suggestion["quantity"] = round(current_qty * 0.3, 8)
                suggestion["reason"] = f"评分{score}分，建议减仓30%"
        else:
            suggestion["reason"] = "观望，不建议调整仓位"

        return suggestion

    def _adjust_confidence(
        self,
        base_confidence: float,
        conflicts: List[str],
        action: str,
        score: float,
    ) -> float:
        """调整决策置信度

        根据冲突信号数量和操作方向调整置信度。

        Args:
            base_confidence: 基础置信度
            conflicts: 冲突信号列表
            action: 操作方向
            score: 综合评分

        Returns:
            调整后的置信度
        """
        adjusted = base_confidence

        # 冲突信号降低置信度
        adjusted -= len(conflicts) * 0.1

        # 评分越极端，置信度越高（方向明确）
        if score >= 80 or score <= 20:
            adjusted += 0.1
        elif 40 <= score <= 60:
            adjusted -= 0.05  # 中间区间降低置信度

        return min(max(adjusted, 0.0), 1.0)

    def _generate_reasoning(
        self,
        total_score: float,
        module_scores: Dict[str, Any],
        action: str,
        position: Dict[str, Any],
        conflicts: List[str],
    ) -> str:
        """生成决策推理过程

        以自然语言描述决策的推理过程。

        Args:
            total_score: 综合评分
            module_scores: 各模块评分
            action: 操作方向
            position: 持仓信息
            conflicts: 冲突信号

        Returns:
            推理过程描述
        """
        reasoning_parts: List[str] = []

        # 评分概述
        reasoning_parts.append(f"综合评分为{total_score}分，")

        # 各模块评分概述
        module_descriptions: List[str] = []
        for name, result in module_scores.items():
            if isinstance(result, dict) and "score" in result:
                module_descriptions.append(
                    f"{name}模块{result['score']}分"
                )
        reasoning_parts.append(
            f"其中{'、'.join(module_descriptions)}。"
        )

        # 持仓状态
        if position and position.get("quantity", 0) > 0:
            pnl_pct = position.get("pnl_pct", 0)
            reasoning_parts.append(
                f"当前持仓{position.get('quantity', 0)}个单位，"
                f"盈亏{pnl_pct:.2%}。"
            )
        else:
            reasoning_parts.append("当前无持仓。")

        # 决策依据
        if action == "buy":
            reasoning_parts.append(
                f"综合评分超过买入阈值{self.buy_threshold}分，建议买入建仓。"
            )
        elif action == "sell":
            reasoning_parts.append(
                f"综合评分低于卖出阈值{self.sell_threshold}分，建议卖出减仓。"
            )
        else:
            reasoning_parts.append(
                f"综合评分处于观望区间，建议持有观望。"
            )

        # 冲突信号
        if conflicts:
            reasoning_parts.append(
                f"注意：存在{len(conflicts)}个冲突信号：{'；'.join(conflicts)}。"
            )

        return "".join(reasoning_parts)
