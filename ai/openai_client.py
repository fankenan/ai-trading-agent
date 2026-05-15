"""
OpenAI客户端

封装OpenAI API调用，提供以下功能：
  - analyze_news: 分析新闻事件，提取关键信息
  - generate_decision_context: 生成决策上下文摘要
  - summarize_report: 总结交易报告

使用前需要设置OPENAI_API_KEY环境变量或传入api_key参数。
"""

from typing import Dict, Any, Optional
import json
from loguru import logger


class AIClient:
    """OpenAI API客户端

    封装OpenAI API调用，提供AI辅助分析功能。

    Attributes:
        api_key: OpenAI API密钥
        model: 使用的模型名称
        client: OpenAI客户端实例
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        """初始化OpenAI客户端

        Args:
            api_key: OpenAI API密钥。如果为None，则从环境变量OPENAI_API_KEY获取。
            model: 使用的模型名称（默认从环境变量OPENAI_MODEL获取，否则"gpt-4o-mini"）
            base_url: API基础URL（默认从环境变量OPENAI_BASE_URL获取）
        """
        import os

        self.api_key: str = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model: str = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url: str = base_url or os.environ.get("OPENAI_BASE_URL", "")
        self.client: Optional[Any] = None

        if not self.api_key:
            logger.warning(
                "未设置OpenAI API密钥。AI分析功能将不可用。"
                "请设置OPENAI_API_KEY环境变量或传入api_key参数。"
            )
        else:
            try:
                from openai import OpenAI
                client_kwargs = {"api_key": self.api_key}
                if self.base_url:
                    client_kwargs["base_url"] = self.base_url
                self.client = OpenAI(**client_kwargs)
                logger.info(f"OpenAI客户端初始化成功，模型: {self.model}, base_url: {self.base_url or '默认'}")
            except ImportError:
                logger.error(
                    "openai包未安装。请执行 pip install openai 安装。"
                )
            except Exception as e:
                logger.error(f"OpenAI客户端初始化失败: {e}")

    def analyze_news(self, text: str) -> Dict[str, Any]:
        """分析新闻事件

        使用OpenAI分析新闻文本，提取事件等级、情绪方向、
        影响范围和交易建议。

        Args:
            text: 新闻文本内容

        Returns:
            包含以下字段的字典：
            - level: 事件等级（S/A/B/C）
            - sentiment: 情绪方向（positive/negative/neutral）
            - impact: 影响评估
            - key_points: 关键要点列表
            - trading_implication: 交易影响分析
            - confidence: 分析置信度
            - raw_response: 原始API响应
        """
        if not self.client:
            logger.warning("OpenAI客户端未初始化，返回默认分析结果")
            return self._get_default_analysis(text)

        system_prompt: str = """你是一位专业的加密货币市场分析师。请分析以下新闻事件，并以JSON格式返回分析结果。

请严格按照以下JSON格式返回（不要包含其他文字）：
{
    "level": "S/A/B/C",
    "sentiment": "positive/negative/neutral",
    "impact": "对市场的潜在影响描述",
    "key_points": ["要点1", "要点2", "要点3"],
    "trading_implication": "对交易的潜在影响和建议",
    "confidence": 0.0-1.0
}

事件等级说明：
- S级：重大事件，对市场产生深远影响（如美联储决议、黑天鹅事件）
- A级：重要事件，对市场产生显著影响
- B级：一般事件，对市场产生一定影响
- C级：轻微事件，对市场影响较小"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请分析以下新闻：\n\n{text}"},
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            content: str = response.choices[0].message.content.strip()

            # 尝试解析JSON响应
            # 处理可能的markdown代码块包裹
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                content = content.rsplit("```", 1)[0] if "```" in content else content

            result: Dict[str, Any] = json.loads(content)

            # 确保必要字段存在
            result.setdefault("level", "C")
            result.setdefault("sentiment", "neutral")
            result.setdefault("impact", "")
            result.setdefault("key_points", [])
            result.setdefault("trading_implication", "")
            result.setdefault("confidence", 0.5)
            result["raw_response"] = content

            logger.info(
                f"新闻分析完成: level={result['level']}, "
                f"sentiment={result['sentiment']}, "
                f"confidence={result['confidence']}"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 原始响应: {content}")
            return self._get_default_analysis(text)
        except Exception as e:
            logger.error(f"新闻分析失败: {e}")
            return self._get_default_analysis(text)

    def generate_decision_context(self, data: Dict[str, Any]) -> str:
        """生成决策上下文

        将评分、决策和风控数据整合为结构化的决策上下文文本，
        供AI进一步分析或人工审阅。

        Args:
            data: 包含评分、决策和风控数据的字典

        Returns:
            结构化的决策上下文文本
        """
        context_parts: list = []

        # 评分信息
        score: Dict[str, Any] = data.get("score", {})
        if score:
            context_parts.append(
                f"【评分信息】综合评分: {score.get('total_score', 'N/A')}分，"
                f"建议: {score.get('recommendation', 'N/A')}，"
                f"置信度: {score.get('confidence', 0):.0%}"
            )

            module_scores = score.get("module_scores", {})
            for name, ms in module_scores.items():
                if isinstance(ms, dict):
                    context_parts.append(
                        f"  - {name}: {ms.get('score', 'N/A')}分 "
                        f"({ms.get('details', '')})"
                    )

        # 决策信息
        decision: Dict[str, Any] = data.get("decision", {})
        if decision:
            context_parts.append(
                f"\n【决策信息】操作: {decision.get('action', 'N/A')}，"
                f"置信度: {decision.get('confidence', 0):.0%}"
            )
            context_parts.append(f"  推理: {decision.get('reasoning', 'N/A')}")

            conflict_signals = decision.get("conflict_signals", [])
            if conflict_signals:
                context_parts.append(f"  冲突信号: {'；'.join(conflict_signals)}")

        # 风控信息
        risk: Dict[str, Any] = data.get("risk", {})
        if risk:
            context_parts.append(
                f"\n【风控信息】验证: {'通过' if risk.get('approved', True) else '未通过'}，"
                f"风险等级: {risk.get('risk_level', 'N/A')}"
            )

            warnings = risk.get("warnings", [])
            if warnings:
                context_parts.append(f"  警告: {'；'.join(warnings)}")

            vetoes = risk.get("vetoes", [])
            if vetoes:
                context_parts.append(f"  否决: {'；'.join(vetoes)}")

        # 市场信息
        market: Dict[str, Any] = data.get("market", {})
        if market:
            context_parts.append(
                f"\n【市场信息】当前价格: {market.get('current_price', 'N/A')}，"
                f"24h涨跌: {market.get('price_change_24h', 'N/A')}，"
                f"24h成交量: {market.get('volume_24h', 'N/A')}"
            )

        context: str = "\n".join(context_parts)
        logger.info("决策上下文已生成")
        return context

    def summarize_report(self, report: Dict[str, Any]) -> str:
        """总结交易报告

        使用OpenAI对交易报告进行智能总结，生成简洁的摘要。

        Args:
            report: 交易报告字典

        Returns:
            报告摘要文本
        """
        if not self.client:
            logger.warning("OpenAI客户端未初始化，返回简单摘要")
            return report.get("summary", "无法生成摘要")

        system_prompt: str = """你是一位专业的量化交易分析师。请对以下交易报告进行简洁的总结。

总结要求：
1. 控制在200字以内
2. 突出关键数据和结论
3. 使用简洁专业的语言
4. 如果有风险提示，请重点说明"""

        try:
            report_text: str = json.dumps(report, ensure_ascii=False, indent=2)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请总结以下交易报告：\n\n{report_text}"},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            summary: str = response.choices[0].message.content.strip()
            logger.info("报告总结已生成")
            return summary

        except Exception as e:
            logger.error(f"报告总结失败: {e}")
            return report.get("summary", "总结生成失败")

    def _get_default_analysis(self, text: str) -> Dict[str, Any]:
        """获取默认分析结果（当API不可用时使用）

        Args:
            text: 新闻文本

        Returns:
            默认分析结果字典
        """
        return {
            "level": "C",
            "sentiment": "neutral",
            "impact": "AI分析不可用，无法评估影响",
            "key_points": ["AI分析服务不可用"],
            "trading_implication": "建议人工审核此新闻事件",
            "confidence": 0.0,
            "raw_response": "",
        }
