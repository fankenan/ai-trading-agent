"""
评分系统模块

提供多维度评分能力，包括事件评分、情绪评分、技术指标评分和K线结构评分。
通过加权综合计算得出最终评分，为决策层提供量化依据。
"""

from scoring.scoring_system import ScoringSystem

__all__ = ["ScoringSystem"]
