"""
K线数据结构定义
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class KLine:
    """简化的K线数据结构 - 只包含时间、最高价、最低价"""
    timestamp: datetime  # 时间戳
    high: float         # 最高价
    low: float          # 最低价
    
    def __post_init__(self):
        """初始化后验证数据"""
        if self.high < self.low:
            raise ValueError(f"最高价({self.high})不能小于最低价({self.low})")
    
    @property
    def mid_price(self) -> float:
        """中间价格（最高价和最低价的平均值）"""
        return (self.high + self.low) / 2
    
    def __str__(self):
        return f"KLine({self.timestamp}, H:{self.high}, L:{self.low}, Mid:{self.mid_price:.2f})"


@dataclass
class MergedKLine:
    """合并后的K线数据结构"""
    start_time: datetime    # 开始时间
    end_time: datetime      # 结束时间
    high: float            # 最高价
    low: float             # 最低价
    original_count: int = 1 # 原始K线数量
    
    @property
    def mid_price(self) -> float:
        """中间价格（最高价和最低价的平均值）"""
        return (self.high + self.low) / 2
    
    def __str__(self):
        return f"MergedKLine({self.start_time}-{self.end_time}, H:{self.high}, L:{self.low}, Mid:{self.mid_price:.2f}, Count:{self.original_count})"