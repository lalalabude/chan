"""
缠论K线可视化模块
提供K线图表、分型标记和笔的可视化功能
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Polygon
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Tuple, Optional
from kline_data import KLine, MergedKLine

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class Fractal:
    """分型数据结构"""
    def __init__(self, index: int, fractal_type: str, kline: MergedKLine):
        self.index = index
        self.type = fractal_type  # 'top' 或 'bottom'
        self.kline = kline
        self.price = kline.high if fractal_type == 'top' else kline.low
        self.time = kline.start_time


class Pen:
    """笔数据结构"""
    def __init__(self, start_fractal: Fractal, end_fractal: Fractal):
        self.start_fractal = start_fractal
        self.end_fractal = end_fractal
        self.start_time = start_fractal.time
        self.end_time = end_fractal.time
        self.start_price = start_fractal.price
        self.end_price = end_fractal.price
        self.direction = 'up' if end_fractal.price > start_fractal.price else 'down'


class KLineVisualizer:
    """K线可视化工具"""
    
    def __init__(self):
        self.fractals: List[Fractal] = []
        self.pens: List[Pen] = []
        self.debug = False
    
    def set_debug(self, debug: bool):
        """设置调试模式"""
        self.debug = debug
    
    def _log(self, message: str):
        """调试日志输出"""
        if self.debug:
            print(f"[Visualizer] {message}")
    
    def detect_fractals(self, merged_klines: List[MergedKLine]) -> List[Fractal]:
        """检测分型"""
        fractals = []
        
        for i in range(1, len(merged_klines) - 1):
            fractal_type = self._detect_fractal_type(merged_klines, i)
            if fractal_type:
                fractal = Fractal(i, fractal_type, merged_klines[i])
                fractals.append(fractal)
        
        self.fractals = fractals
        return fractals
    
    def _detect_fractal_type(self, klines: List[MergedKLine], index: int) -> Optional[str]:
        """检测分型类型"""
        if index == 0 or index >= len(klines) - 1:
            return None
        
        prev_k = klines[index - 1]
        curr_k = klines[index]
        next_k = klines[index + 1]
        
        # 顶分型判断
        if (curr_k.high > prev_k.high and curr_k.high > next_k.high and
            curr_k.low > prev_k.low and curr_k.low > next_k.low):
            return "top"
        
        # 底分型判断
        if (curr_k.high < prev_k.high and curr_k.high < next_k.high and
            curr_k.low < prev_k.low and curr_k.low < next_k.low):
            return "bottom"
        
        return None
    
    def calculate_pens(self, fractals: List[Fractal] = None) -> List[Pen]:
        """
        计算笔：连接有效的顶分型和底分型
        改进规则：
        1. 只有当顶、底分型中间至少有一根不属于这两个分型的独立K线时才形成有效的笔
        2. 每一笔必须是从一个有效的顶到下一个有效的底，或从底到顶，保持连贯性
        3. 笔必须是连续的，前一笔的终点就是下一笔的起点
        4. 如果出现多个相同类型的分型，取最后一个作为终点
        """
        if fractals is None:
            fractals = self.fractals
        
        if len(fractals) < 2:
            return []
        
        pens = []
        used_fractals = set()  # 记录已经被笔连接的分型
        
        # 寻找第一个有效的笔起点
        start_index = 0
        current_fractal = None
        
        # 找到第一个能形成有效笔的分型作为起点
        while start_index < len(fractals):
            candidate_start = fractals[start_index]
            target_type = 'top' if candidate_start.type == 'bottom' else 'bottom'
            
            self._log(f"尝试从分型{start_index}({candidate_start.type})开始...")
            valid_end_fractal = self._find_valid_pen_end(candidate_start, fractals, start_index, target_type)
            
            if valid_end_fractal is not None:
                # 找到了第一个有效的笔
                current_fractal = candidate_start
                break
            
            start_index += 1
        
        # 如果没有找到任何有效的笔起点，返回空列表
        if current_fractal is None:
            self._log("❌ 没有找到任何有效的笔起点")
            self.used_fractals = used_fractals
            self.pens = pens
            return pens
        
        # 从第一个有效起点开始，连续构建笔
        while current_fractal is not None:
            current_index = fractals.index(current_fractal)
            target_type = 'top' if current_fractal.type == 'bottom' else 'bottom'
            
            self._log(f"从分型{current_index}({current_fractal.type})寻找{target_type}分型...")
            valid_end_fractal = self._find_valid_pen_end(current_fractal, fractals, current_index, target_type)
            
            if valid_end_fractal is not None:
                # 创建有效的笔
                pen = Pen(current_fractal, valid_end_fractal)
                pens.append(pen)
                used_fractals.add(current_fractal)
                used_fractals.add(valid_end_fractal)
                
                self._log(f"✅ 创建有效笔: {current_fractal.type}({current_fractal.index}) -> {valid_end_fractal.type}({valid_end_fractal.index})")
                
                # 从终点分型继续寻找下一个笔，保持连贯性
                current_fractal = valid_end_fractal
            else:
                # 没有找到有效的笔终点，检查是否有剩余的未使用分型可以形成新的笔
                remaining_fractals = [f for f in fractals[current_index+1:] if f not in used_fractals]
                
                # 寻找下一个可以开始新笔的分型
                new_start_fractal = None
                for remaining_fractal in remaining_fractals:
                    # 寻找与当前分型不同类型的分型作为新起点
                    if remaining_fractal.type != current_fractal.type:
                        new_start_fractal = remaining_fractal
                        break
                
                if new_start_fractal:
                    self._log(f"🔄 从新的分型开始: {new_start_fractal.type}({new_start_fractal.index})")
                    current_fractal = new_start_fractal
                    continue
                else:
                    self._log(f"❌ 未找到有效笔终点，结束笔的构建")
                    break
        
        # 更新分型列表，只保留被笔连接的分型
        self.used_fractals = used_fractals
        self.pens = pens
        return pens
    
    def _find_valid_pen_end(self, start_fractal: Fractal, fractals: List[Fractal], 
                           start_index: int, target_type: str) -> Optional[Fractal]:
        """
        寻找有效的笔终点分型
        
        参数：
        - start_fractal: 起始分型
        - fractals: 所有分型列表
        - start_index: 起始分型在列表中的索引
        - target_type: 目标分型类型('top' 或 'bottom')
        
        返回：
        - 有效的终点分型，如果没有找到则返回None
        """
        last_valid_fractal = None
        
        for j in range(start_index + 1, len(fractals)):
            candidate_fractal = fractals[j]
            
            # 如果是目标类型的分型
            if candidate_fractal.type == target_type:
                # 检查是否满足独立K线条件
                has_independent = self._has_independent_klines_between(start_fractal, candidate_fractal)
                self._log(f"  检查分型{j}({candidate_fractal.type}): 独立K线={has_independent}")
                
                if has_independent:
                    # 这是一个有效的候选终点，记录它
                    # 如果已经有候选终点，则当前的是"最后一个"，应该替换之前的
                    last_valid_fractal = candidate_fractal
                    self._log(f"  ✅ 找到有效候选终点: 分型{j}")
                else:
                    self._log(f"  ❌ 分型{j}不满足独立K线条件")
                    
                # 继续寻找更后面的同类型分型，不要在这里break
                
            # 如果遇到了与起始分型相同类型的分型，且已经找到了有效终点
            elif candidate_fractal.type == start_fractal.type:
                # 如果已经找到了有效的终点，则停止寻找
                if last_valid_fractal is not None:
                    self._log(f"  遇到同类型分型{j}，停止寻找")
                    break
                # 如果还没有找到有效终点，则跳过这个同类型分型，继续寻找
                else:
                    self._log(f"  跳过同类型分型{j}，继续寻找")
                    continue
        
        return last_valid_fractal
    
    def _has_independent_klines_between(self, fractal1: Fractal, fractal2: Fractal) -> bool:
        """
        检查两个分型之间是否有独立的K线
        独立K线：不属于任何一个分型的K线
        严格规则：分型占用其前后各一根K线，即index-1, index, index+1三根K线
        """
        # 获取两个分型的索引
        start_index = min(fractal1.index, fractal2.index)
        end_index = max(fractal1.index, fractal2.index)
        
        self._log(f"    检查独立K线: 分型{start_index} -> 分型{end_index}")
        
        # 如果两个分型索引相差小于等于2，则没有独立K线
        if end_index - start_index <= 2:
            self._log(f"    分型间距离太近({end_index - start_index}), 无独立K线")
            return False
        
        # 分型占用的K线范围：前一根、当前、后一根
        fractal1_range = set(range(max(0, fractal1.index - 1), fractal1.index + 2))
        fractal2_range = set(range(max(0, fractal2.index - 1), fractal2.index + 2))
        
        self._log(f"    分型1占用K线: {fractal1_range}")
        self._log(f"    分型2占用K线: {fractal2_range}")
        
        # 检查两个分型之间的K线
        independent_klines = []
        for k_index in range(start_index + 1, end_index):
            # 如果这根K线不属于任何一个分型，则为独立K线
            if k_index not in fractal1_range and k_index not in fractal2_range:
                independent_klines.append(k_index)
        
        self._log(f"    独立K线: {independent_klines}")
        
        # 至少需要一根独立K线才能形成有效的笔
        has_independent = len(independent_klines) >= 1
        self._log(f"    独立K线数量: {len(independent_klines)}, 有效: {has_independent}")
        return has_independent
    
    def plot_klines(self, original_klines: List[KLine], merged_klines: List[MergedKLine], 
                   title: str = "缠论K线合并图", figsize: Tuple[int, int] = (15, 10),
                   save_path: str = None) -> plt.Figure:
        """
        绘制K线图，包含原始K线、合并K线、分型标记和笔
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, sharex=True)
        
        # 检测分型和计算笔
        fractals = self.detect_fractals(merged_klines)
        pens = self.calculate_pens(fractals)
        
        # 绘制原始K线（上图）
        self._plot_original_klines(ax1, original_klines, "原始K线数据")
        
        # 绘制合并后K线（下图）
        self._plot_merged_klines(ax2, merged_klines, "合并后K线数据")
        
        # 在合并K线图上添加分型标记
        self._plot_fractals(ax2, fractals)
        
        # 在合并K线图上添加笔
        self._plot_pens(ax2, pens)
        
        # 设置图表格式
        self._format_chart(ax1, ax2, title)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {save_path}")
        
        return fig
    
    def _plot_original_klines(self, ax, klines: List[KLine], title: str):
        """绘制原始K线（简化为高低点连线）"""
        if not klines:
            return
        
        times = [k.timestamp for k in klines]
        highs = [k.high for k in klines]
        lows = [k.low for k in klines]
        mids = [k.mid_price for k in klines]
        
        # 绘制高低点连线
        ax.plot(times, highs, 'g-', alpha=0.6, linewidth=1, label='最高价')
        ax.plot(times, lows, 'r-', alpha=0.6, linewidth=1, label='最低价')
        ax.plot(times, mids, 'b-', alpha=0.8, linewidth=2, label='中间价')
        
        # 填充高低点之间的区域
        ax.fill_between(times, highs, lows, alpha=0.2, color='gray')
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def _plot_merged_klines(self, ax, merged_klines: List[MergedKLine], title: str):
        """绘制合并后K线"""
        if not merged_klines:
            return
        
        times = [k.start_time for k in merged_klines]
        highs = [k.high for k in merged_klines]
        lows = [k.low for k in merged_klines]
        mids = [k.mid_price for k in merged_klines]
        
        # 绘制高低点连线，线条更粗
        ax.plot(times, highs, 'g-', linewidth=2, label='最高价')
        ax.plot(times, lows, 'r-', linewidth=2, label='最低价')
        ax.plot(times, mids, 'b-', linewidth=3, label='中间价')
        
        # 填充高低点之间的区域
        ax.fill_between(times, highs, lows, alpha=0.3, color='lightblue')
        
        # 标记合并的K线数量
        for i, k in enumerate(merged_klines):
            if k.original_count > 1:
                ax.annotate(f'{k.original_count}', 
                           xy=(k.start_time, k.mid_price), 
                           xytext=(5, 5), 
                           textcoords='offset points',
                           fontsize=8, 
                           color='purple',
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='yellow', alpha=0.7))
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def _plot_fractals(self, ax, fractals: List[Fractal]):
        """在图上标记分型（只显示被笔连接的分型）"""
        # 只显示被笔连接的分型
        used_fractals = getattr(self, 'used_fractals', set())
        
        for fractal in fractals:
            # 只显示被笔连接的分型
            if fractal in used_fractals:
                if fractal.type == 'top':
                    # 顶分型用红色向下三角
                    ax.scatter(fractal.time, fractal.price, 
                              marker='v', s=100, c='red', 
                              edgecolors='darkred', linewidth=2,
                              label='顶分型' if fractal == list(used_fractals)[0] or 
                                    not any(f.type == 'top' for f in used_fractals) else "")
                else:
                    # 底分型用绿色向上三角
                    ax.scatter(fractal.time, fractal.price, 
                              marker='^', s=100, c='green', 
                              edgecolors='darkgreen', linewidth=2,
                              label='底分型' if fractal == list(used_fractals)[0] or 
                                    not any(f.type == 'bottom' for f in used_fractals) else "")
    
    def _plot_pens(self, ax, pens: List[Pen]):
        """在图上绘制笔"""
        for i, pen in enumerate(pens):
            # 绘制笔的连线
            ax.plot([pen.start_time, pen.end_time], 
                   [pen.start_price, pen.end_price],
                   'k-', linewidth=2, alpha=0.8,
                   label='笔' if i == 0 else "")
            
            # 在笔的中点标记方向
            mid_time = pen.start_time + (pen.end_time - pen.start_time) / 2
            mid_price = (pen.start_price + pen.end_price) / 2
            
            direction_symbol = '↗' if pen.direction == 'up' else '↘'
            ax.annotate(direction_symbol, 
                       xy=(mid_time, mid_price), 
                       fontsize=12, 
                       ha='center', 
                       va='center',
                       color='black',
                       fontweight='bold')
    
    def _format_chart(self, ax1, ax2, title: str):
        """格式化图表"""
        # 设置主标题
        ax1.figure.suptitle(title, fontsize=16, fontweight='bold')
        
        # 设置x轴时间格式
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax2.xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        # 设置y轴标签
        ax1.set_ylabel('价格', fontsize=12)
        ax2.set_ylabel('价格', fontsize=12)
        ax2.set_xlabel('时间', fontsize=12)
        
        # 合并图例
        handles1, labels1 = ax1.get_legend_handles_labels()
        handles2, labels2 = ax2.get_legend_handles_labels()
        
        # 去重复的标签
        seen_labels = set()
        unique_handles = []
        unique_labels = []
        
        for handle, label in zip(handles1 + handles2, labels1 + labels2):
            if label not in seen_labels:
                unique_handles.append(handle)
                unique_labels.append(label)
                seen_labels.add(label)
        
        ax2.legend(unique_handles, unique_labels, loc='upper left', bbox_to_anchor=(1, 1))
    
    def get_fractal_summary(self) -> dict:
        """获取分型统计摘要"""
        if not self.fractals:
            return {}
        
        top_count = sum(1 for f in self.fractals if f.type == 'top')
        bottom_count = sum(1 for f in self.fractals if f.type == 'bottom')
        
        return {
            "总分型数": len(self.fractals),
            "顶分型数": top_count,
            "底分型数": bottom_count,
            "笔的数量": len(self.pens)
        }
    
    def print_fractal_details(self):
        """打印分型详细信息"""
        print(f"\n📊 分型分析结果:")
        print("=" * 50)
        
        summary = self.get_fractal_summary()
        for key, value in summary.items():
            print(f"{key}: {value}")
        
        if self.fractals:
            print(f"\n🔍 分型详情:")
            for i, fractal in enumerate(self.fractals):
                symbol = "🔺" if fractal.type == "top" else "🔻"
                print(f"{i+1}. {symbol} {fractal.type.upper()}分型 - "
                      f"时间: {fractal.time.strftime('%H:%M:%S')}, "
                      f"价格: {fractal.price:.2f}")
        
        if self.pens:
            print(f"\n📏 笔的详情:")
            for i, pen in enumerate(self.pens):
                direction_symbol = "📈" if pen.direction == "up" else "📉"
                print(f"{i+1}. {direction_symbol} {pen.direction.upper()}笔 - "
                      f"从 {pen.start_price:.2f} 到 {pen.end_price:.2f}, "
                      f"幅度: {abs(pen.end_price - pen.start_price):.2f}")