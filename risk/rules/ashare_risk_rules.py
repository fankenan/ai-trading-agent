"""
A股风控规则

适配A股特殊风险：
- ST股票风险
- 涨跌停风险（买入涨停、卖出跌停）
- 停牌风险
- 减持/解禁风险
- 财报雷风险
"""

from typing import Dict, List, Any
from loguru import logger


class AShareRiskRules:
    """A股风控规则"""
    
    def __init__(self):
        # 基础风控参数
        self.max_position_pct = 0.20  # 最大单只持仓20%
        self.max_daily_loss = 0.05  # 单日最大亏损5%
        self.max_drawdown = 0.15  # 最大回撤15%
        self.max_single_loss = 0.07  # 单笔最大亏损7%
        
        # A股特有参数
        self.stock_blacklist = []  # 股票黑名单（如ST、退市风险）
        self.suspended_stocks = []  # 停牌股票列表
        self.recent_limit_up = []  # 近期涨停股票（追涨风险）
        
    def check_st_risk(self, stock_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查ST股票风险
        
        Returns:
            {pass: bool, reason: str, risk_level: str}
        """
        if stock_info.get('is_st', False):
            return {
                "pass": False,
                "reason": "ST股票风险过高，禁止交易",
                "risk_level": "critical",
                "rule": "st_risk"
            }
        return {"pass": True}
    
    def check_limit_up_risk(self, stock_info: Dict[str, Any], is_entry: bool = True) -> Dict[str, Any]:
        """
        检查涨跌停风险
        
        Args:
            stock_info: 股票信息
            is_entry: True=买入检查, False=卖出检查
        """
        if is_entry and stock_info.get('is_limit_up', False):
            return {
                "pass": False,
                "reason": "涨停买入风险极高，可能无法封板",
                "risk_level": "high",
                "rule": "limit_up_risk",
                "suggestion": "等待次日确认或排板"
            }
        
        if not is_entry and stock_info.get('is_limit_down', False):
            return {
                "pass": False,
                "reason": "跌停无法卖出，建议使用止损单预埋",
                "risk_level": "critical",
                "rule": "limit_down_risk"
            }
        
        return {"pass": True}
    
    def check_suspend_risk(self, suspend_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查停牌风险
        """
        if suspend_info.get('is_suspended', False):
            return {
                "pass": False,
                "reason": f"股票停牌: {suspend_info.get('suspend_reason', '未知原因')}",
                "risk_level": "critical",
                "rule": "suspend_risk",
                "resume_date": suspend_info.get('resume_date')
            }
        return {"pass": True}
    
    def check_position_size(self, position_pct: float) -> Dict[str, Any]:
        """检查仓位大小"""
        if position_pct > self.max_position_pct:
            return {
                "pass": False,
                "reason": f"仓位{position_pct:.1%}超过限制{self.max_position_pct:.1%}",
                "risk_level": "medium",
                "rule": "position_size"
            }
        return {"pass": True}
    
    def check_daily_loss(self, daily_pnl_pct: float) -> Dict[str, Any]:
        """检查日亏损"""
        if daily_pnl_pct < -self.max_daily_loss:
            return {
                "pass": False,
                "reason": f"日亏损{daily_pnl_pct:.1%}超过限制{self.max_daily_loss:.1%}",
                "risk_level": "critical",
                "rule": "daily_loss",
                "action": "暂停交易，等待次日确认"
            }
        return {"pass": True}
    
    def check_single_loss(self, trade_pnl_pct: float) -> Dict[str, Any]:
        """检查单笔亏损"""
        if trade_pnl_pct < -self.max_single_loss:
            return {
                "pass": False,
                "reason": f"单笔亏损{trade_pnl_pct:.1%}超过限制{self.max_single_loss:.1%}",
                "risk_level": "high",
                "rule": "single_loss"
            }
        return {"pass": True}
    
    def check_blacklist(self, symbol: str) -> Dict[str, Any]:
        """检查黑名单"""
        if symbol in self.stock_blacklist:
            return {
                "pass": False,
                "reason": f"{symbol}在黑名单中",
                "risk_level": "critical",
                "rule": "blacklist"
            }
        return {"pass": True}
    
    def check_policy_risk(self, events: List[Dict]) -> Dict[str, Any]:
        """
        检查政策风险（S级事件触发熔断）
        """
        s_level_events = [e for e in events if e.get('level', '').upper() == 'S']
        
        if s_level_events:
            return {
                "pass": False,
                "reason": f"检测到{len(s_level_events)}个S级政策事件，暂停自动交易",
                "risk_level": "critical",
                "rule": "policy_risk",
                "events": [e.get('title', '') for e in s_level_events],
                "action": "进入人工确认模式"
            }
        return {"pass": True}
    
    def check_market_risk(self, market_status: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查市场整体风险
        
        Args:
            market_status: 市场状态，{market_index_change: float, ...}
        """
        # 大盘暴跌检查
        market_change = market_status.get('market_index_change', 0)
        
        if market_change < -0.03:  # 大盘下跌超3%
            return {
                "pass": True,  # 不阻止，但给出警告
                "reason": f"大盘下跌{market_change:.1%}，建议降低仓位",
                "risk_level": "high",
                "rule": "market_risk",
                "action": "建议减仓50%"
            }
        
        if market_change < -0.05:  # 大盘下跌超5%
            return {
                "pass": False,
                "reason": f"大盘大幅下跌{market_change:.1%}，暂停开新仓",
                "risk_level": "critical",
                "rule": "market_risk",
                "action": "仅允许平仓，禁止开新仓"
            }
        
        return {"pass": True}
    
    def get_all_checks(self) -> List[str]:
        """获取所有风控规则列表"""
        return [
            "st_risk",        # ST股票检查
            "limit_up_risk",  # 涨跌停检查
            "suspend_risk",   # 停牌检查
            "position_size",  # 仓位检查
            "daily_loss",     # 日亏损检查
            "single_loss",    # 单笔亏损检查
            "blacklist",      # 黑名单检查
            "policy_risk",    # 政策风险检查
            "market_risk",    # 市场风险检查
        ]
