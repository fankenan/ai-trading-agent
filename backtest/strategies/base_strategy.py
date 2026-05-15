"""
策略基类模块

定义所有交易策略的抽象基类，提供统一的接口规范。

所有自定义策略都应继承 BaseStrategy 并实现 generate_signals 方法。
"""

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd


class BaseStrategy(ABC):
    """交易策略抽象基类

    所有交易策略必须继承此类并实现 generate_signals 方法。

    Attributes:
        name: 策略名称
        description: 策略描述
    """

    def __init__(self, name: str = "", description: str = "") -> None:
        """初始化策略

        Args:
            name: 策略名称
            description: 策略描述
        """
        self.name: str = name
        self.description: str = description

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """生成交易信号

        根据行情数据生成交易信号序列。

        重要: 此方法必须确保不使用未来数据。
        在计算第i根K线的信号时，只能使用第0到第i根K线的数据。
        建议使用 df.iloc[:i+1] 进行逐K线计算，或使用 pandas 的
        rolling/shift 等方法确保不发生未来函数。

        Args:
            df: 行情数据 DataFrame，包含 open, high, low, close, volume 列

        Returns:
            pd.Series: 信号序列，与 df 等长。
                1 = 买入信号
                -1 = 卖出信号
                0 = 持有/无信号
        """
        ...

    def validate_params(self) -> bool:
        """验证策略参数是否合法

        Returns:
            True 表示参数合法，False 表示参数不合法
        """
        return True

    def __repr__(self) -> str:
        """策略的字符串表示"""
        param_str = ", ".join(
            f"{k}={v}" for k, v in self.__dict__.items() if k not in ("name", "description")
        )
        return f"{self.__class__.__name__}({param_str})"
