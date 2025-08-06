"""
缠论K线合并核心逻辑
根据图片内容实现完整的K线合并算法
"""
from typing import List, Optional, Tuple
from kline_data import KLine, MergedKLine
from datetime import datetime


class KLineMerger:
    """缠论K线合并工具类"""
    
    def __init__(self):
        self.debug = False
    
    def set_debug(self, debug: bool):
        """设置调试模式"""
        self.debug = debug
    
    def _log(self, message: str):
        """调试日志输出"""
        if self.debug:
            print(f"[DEBUG] {message}")
    
    def _has_inclusion_relationship(self, k1: MergedKLine, k2: MergedKLine) -> Tuple[bool, str]:
        """
        判断两根K线是否存在包含关系
        新规则：当第n根K线的最高点大于等于第n+1或n-1根K线的最高点，
        且最低点小于等于第n+1或n-1根K线的最低点时，定义n与n+1或n-1存在包含关系
        
        返回: (是否存在包含关系, 包含类型)
        包含类型: 'k1_contains_k2' 或 'k2_contains_k1' 或 'none'
        """
        # 按照新规则：k1包含k2的条件
        k1_contains_k2 = (k1.high >= k2.high and k1.low <= k2.low)
        # k2包含k1的条件
        k2_contains_k1 = (k2.high >= k1.high and k2.low <= k1.low)
        
        if k1_contains_k2:
            self._log(f"发现包含关系: K1({k1.high},{k1.low}) 包含 K2({k2.high},{k2.low})")
            return True, 'k1_contains_k2'
        elif k2_contains_k1:
            self._log(f"发现包含关系: K2({k2.high},{k2.low}) 包含 K1({k1.high},{k1.low})")
            return True, 'k2_contains_k1'
        else:
            return False, 'none'
    
    def _merge_inclusion_relationship(self, k1: MergedKLine, k2: MergedKLine, trend_direction: str) -> MergedKLine:
        """
        处理包含关系的合并
        trend_direction: 'up'(上升趋势) 或 'down'(下降趋势)
        
        上升趋势：选择两根K线最高点中的较高点作为合并后的MaxGi，
                选择两根K线最低点中的较高点作为合并后的MaxDi
        下降趋势：选择两根K线最高点中的较低点作为合并后的MaxGi，
                选择两根K线最低点中的较低点作为合并后的MaxDi
        """
        if trend_direction == 'up':
            # 上升趋势
            merged_high = max(k1.high, k2.high)
            merged_low = max(k1.low, k2.low)
            self._log(f"上升趋势合并: High=max({k1.high},{k2.high})={merged_high}, Low=max({k1.low},{k2.low})={merged_low}")
        else:
            # 下降趋势
            merged_high = min(k1.high, k2.high)
            merged_low = min(k1.low, k2.low)
            self._log(f"下降趋势合并: High=min({k1.high},{k2.high})={merged_high}, Low=min({k1.low},{k2.low})={merged_low}")
        
        return MergedKLine(
            start_time=k1.start_time,
            end_time=k2.end_time,
            high=merged_high,
            low=merged_low,
            original_count=k1.original_count + k2.original_count
        )
    
    def _determine_trend_direction(self, current_k: MergedKLine, next_k: MergedKLine, merged_klines: List[MergedKLine]) -> str:
        """
        确定当前的趋势方向
        新规则：当第n根K线与n+1根K线存在包含关系，
        如果n的最高点大于等于n-1的最高点，称n-1、n、n+1根K线向上；
        相反如果n的最低点小于等于n-1的最低点，称n-1、n、n+1根K线向下
        """
        if len(merged_klines) == 0:
            return 'up'  # 默认上升趋势
        
        # 获取前一根K线（n-1）
        prev_k = merged_klines[-1] if merged_klines else None
        
        if prev_k is None:
            return 'up'  # 默认上升趋势
        
        # 按照新规则判断趋势方向
        if current_k.high >= prev_k.high:
            self._log(f"趋势向上: 当前K线最高点({current_k.high}) >= 前一根K线最高点({prev_k.high})")
            return 'up'
        elif current_k.low <= prev_k.low:
            self._log(f"趋势向下: 当前K线最低点({current_k.low}) <= 前一根K线最低点({prev_k.low})")
            return 'down'
        else:
            # 如果既不满足向上也不满足向下的条件，则按照最高点比较
            if current_k.high > prev_k.high:
                return 'up'
            else:
                return 'down'
    
    def _kline_to_merged(self, kline: KLine) -> MergedKLine:
        """将单根K线转换为MergedKLine"""
        return MergedKLine(
            start_time=kline.timestamp,
            end_time=kline.timestamp,
            high=kline.high,
            low=kline.low,
            original_count=1
        )
    
    def _detect_fractal_type(self, klines: List[MergedKLine], index: int) -> Optional[str]:
        """
        检测分型类型
        顶分型：当前K线的最高点和最低点的大于前后一根K线的最高点和最低点，即MaxGi>MaxGi±1，且MaxDi>MaxDi±1
        底分型：当前K线的最高点和最低点的小于前后一根K线的最高点和最低点，即MaxGi<MaxGi±1，且MaxDi<MaxDi±1
        """
        if index == 0 or index >= len(klines) - 1:
            return None
        
        prev_k = klines[index - 1]
        curr_k = klines[index]
        next_k = klines[index + 1]
        
        # 顶分型判断
        if (curr_k.high > prev_k.high and curr_k.high > next_k.high and
            curr_k.low > prev_k.low and curr_k.low > next_k.low):
            self._log(f"检测到顶分型 at index {index}: {curr_k}")
            return "top"
        
        # 底分型判断
        if (curr_k.high < prev_k.high and curr_k.high < next_k.high and
            curr_k.low < prev_k.low and curr_k.low < next_k.low):
            self._log(f"检测到底分型 at index {index}: {curr_k}")
            return "bottom"
        
        return None
    
    def merge_klines(self, klines: List[KLine]) -> List[MergedKLine]:
        """
        主要的K线合并方法
        按照缠论逻辑进行K线合并
        """
        if not klines:
            return []
        
        if len(klines) == 1:
            return [self._kline_to_merged(klines[0])]
        
        self._log(f"开始合并 {len(klines)} 根K线")
        
        # 初始化结果列表
        merged_result = []
        
        # 第一根K线直接添加
        current_merged = self._kline_to_merged(klines[0])
        
        for i in range(1, len(klines)):
            next_kline = self._kline_to_merged(klines[i])
            
            self._log(f"\n处理第 {i+1} 根K线: {next_kline}")
            
            # 检查是否存在包含关系
            has_inclusion, inclusion_type = self._has_inclusion_relationship(current_merged, next_kline)
            
            if has_inclusion:
                # 按照新规则：只处理从左至右的包含关系
                # 即当第n根K线包含第n+1根K线时才进行合并
                if inclusion_type == 'k1_contains_k2':
                    # 确定趋势方向
                    trend_direction = self._determine_trend_direction(current_merged, next_kline, merged_result)
                    self._log(f"当前趋势方向: {trend_direction}")
                    
                    # 合并K线
                    current_merged = self._merge_inclusion_relationship(current_merged, next_kline, trend_direction)
                    self._log(f"合并后: {current_merged}")
                else:
                    # 第n+1根K线包含第n根K线的情况不做处理，保留原K线
                    self._log(f"K2包含K1的情况不做处理，保留原K线")
                    merged_result.append(current_merged)
                    current_merged = next_kline
            else:
                # 没有包含关系，将当前合并的K线添加到结果中
                merged_result.append(current_merged)
                current_merged = next_kline
                self._log(f"无包含关系，添加到结果: {merged_result[-1]}")
        
        # 添加最后一根合并的K线
        merged_result.append(current_merged)
        
        self._log(f"\n合并完成，共得到 {len(merged_result)} 根合并K线")
        
        # 检测分型
        self._detect_fractals(merged_result)
        
        return merged_result
    
    def _detect_fractals(self, merged_klines: List[MergedKLine]):
        """检测所有分型"""
        self._log("\n开始检测分型...")
        fractals = []
        
        for i in range(1, len(merged_klines) - 1):
            fractal_type = self._detect_fractal_type(merged_klines, i)
            if fractal_type:
                fractals.append((i, fractal_type, merged_klines[i]))
        
        self._log(f"共检测到 {len(fractals)} 个分型")
        for index, ftype, kline in fractals:
            self._log(f"分型 {index}: {ftype} - {kline}")
        
        return fractals
    
    def get_merge_statistics(self, original_klines: List[KLine], merged_klines: List[MergedKLine]) -> dict:
        """获取合并统计信息"""
        total_merged_count = sum(k.original_count for k in merged_klines)
        compression_ratio = len(merged_klines) / len(original_klines) if original_klines else 0
        
        return {
            "原始K线数量": len(original_klines),
            "合并后K线数量": len(merged_klines),
            "总合并K线数": total_merged_count,
            "压缩比": f"{compression_ratio:.2%}",
            "平均合并数": total_merged_count / len(merged_klines) if merged_klines else 0
        }