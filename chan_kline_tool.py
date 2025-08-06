"""
缠论K线合并工具主类
提供完整的K线合并功能，支持Excel文件读取和导出
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Union
from datetime import datetime
import os
from kline_data import KLine, MergedKLine
from kline_merger import KLineMerger
from kline_visualizer import KLineVisualizer


class ChanKLineTool:
    """缠论K线合并主工具类"""
    
    def __init__(self):
        self.merger = KLineMerger()
        self.visualizer = KLineVisualizer()
        self.original_klines: List[KLine] = []
        self.merged_klines: List[MergedKLine] = []
        self.debug = False
    
    def set_debug(self, debug: bool):
        """设置调试模式"""
        self.debug = debug
        self.merger.set_debug(debug)
        self.visualizer.set_debug(debug)
    
    def _log(self, message: str):
        """调试日志输出"""
        if self.debug:
            print(f"[ChanTool] {message}")
    
    def load_from_excel(self, file_path: str, sheet_name: str = 0, 
                       time_column: str = 'timestamp', 
                       high_column: str = 'high', 
                       low_column: str = 'low') -> bool:
        """
        从Excel文件加载K线数据（简化版：只需要时间、最高价、最低价）
        
        参数：
        - file_path: Excel文件路径
        - sheet_name: 工作表名称或索引
        - time_column: 时间列名
        - high_column: 最高价列名
        - low_column: 最低价列名
        """
        try:
            self._log(f"正在加载Excel文件: {file_path}")
            
            # 读取Excel文件
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            self._log(f"Excel文件读取成功，共 {len(df)} 行数据")
            
            # 检查必要的列是否存在
            required_columns = [time_column, high_column, low_column]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                self._log(f"错误: 缺少必要的列: {missing_columns}")
                return False
            
            # 转换数据
            klines = []
            for index, row in df.iterrows():
                try:
                    # 处理时间列
                    if isinstance(row[time_column], str):
                        timestamp = pd.to_datetime(row[time_column])
                    else:
                        timestamp = row[time_column]
                    
                    kline = KLine(
                        timestamp=timestamp,
                        high=float(row[high_column]),
                        low=float(row[low_column])
                    )
                    klines.append(kline)
                    
                except Exception as e:
                    self._log(f"第 {index+1} 行数据转换失败: {e}")
                    continue
            
            self.original_klines = klines
            self._log(f"成功加载 {len(klines)} 根K线数据")
            return True
            
        except Exception as e:
            self._log(f"加载Excel文件失败: {e}")
            return False
    
    def load_from_data(self, data: List[Dict]) -> bool:
        """
        从字典列表加载K线数据
        
        参数：
        data: 包含K线数据的字典列表，每个字典应包含时间、开高低收等字段
        """
        try:
            klines = []
            for i, item in enumerate(data):
                try:
                    timestamp = item.get('timestamp') or item.get('time') or item.get('datetime')
                    if isinstance(timestamp, str):
                        timestamp = pd.to_datetime(timestamp)
                    
                    kline = KLine(
                        timestamp=timestamp,
                        high=float(item.get('high')),
                        low=float(item.get('low'))
                    )
                    klines.append(kline)
                except Exception as e:
                    self._log(f"第 {i+1} 条数据转换失败: {e}")
                    continue
            
            self.original_klines = klines
            self._log(f"成功加载 {len(klines)} 根K线数据")
            return True
            
        except Exception as e:
            self._log(f"加载数据失败: {e}")
            return False
    
    def merge_klines(self) -> bool:
        """执行K线合并"""
        if not self.original_klines:
            self._log("错误: 没有可合并的K线数据")
            return False
        
        try:
            self._log("开始执行K线合并...")
            self.merged_klines = self.merger.merge_klines(self.original_klines)
            self._log(f"K线合并完成，原始 {len(self.original_klines)} 根，合并后 {len(self.merged_klines)} 根")
            return True
        except Exception as e:
            self._log(f"K线合并失败: {e}")
            return False
    
    def export_to_excel(self, output_path: str, include_original: bool = True) -> bool:
        """
        导出结果到Excel文件
        
        参数：
        - output_path: 输出文件路径
        - include_original: 是否包含原始K线数据
        """
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                
                # 导出合并后的K线数据
                if self.merged_klines:
                    merged_data = []
                    for kline in self.merged_klines:
                                            merged_data.append({
                        '开始时间': kline.start_time,
                        '结束时间': kline.end_time,
                        '最高价': kline.high,
                        '最低价': kline.low,
                        '中间价': kline.mid_price,
                        '原始K线数量': kline.original_count
                    })
                    
                    merged_df = pd.DataFrame(merged_data)
                    merged_df.to_excel(writer, sheet_name='合并后K线', index=False)
                    self._log(f"合并后K线数据已导出，共 {len(merged_data)} 条")
                
                # 导出原始K线数据（可选）
                if include_original and self.original_klines:
                    original_data = []
                    for kline in self.original_klines:
                                            original_data.append({
                        '时间': kline.timestamp,
                        '最高价': kline.high,
                        '最低价': kline.low,
                        '中间价': kline.mid_price
                    })
                    
                    original_df = pd.DataFrame(original_data)
                    original_df.to_excel(writer, sheet_name='原始K线', index=False)
                    self._log(f"原始K线数据已导出，共 {len(original_data)} 条")
                
                # 导出统计信息
                if self.original_klines and self.merged_klines:
                    stats = self.merger.get_merge_statistics(self.original_klines, self.merged_klines)
                    stats_data = [{'统计项': k, '数值': v} for k, v in stats.items()]
                    stats_df = pd.DataFrame(stats_data)
                    stats_df.to_excel(writer, sheet_name='合并统计', index=False)
                    self._log("统计信息已导出")
            
            self._log(f"Excel文件导出成功: {output_path}")
            return True
            
        except Exception as e:
            self._log(f"导出Excel文件失败: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        """获取合并统计信息"""
        if not self.original_klines or not self.merged_klines:
            return {}
        
        return self.merger.get_merge_statistics(self.original_klines, self.merged_klines)
    
    def print_summary(self):
        """打印合并结果摘要"""
        if not self.original_klines:
            print("❌ 没有加载K线数据")
            return
        
        print(f"\n📊 缠论K线合并结果摘要")
        print("=" * 50)
        
        if self.merged_klines:
            stats = self.get_statistics()
            for key, value in stats.items():
                print(f"{key}: {value}")
            
            # 显示前几根合并后的K线
            print(f"\n前5根合并后的K线:")
            for i, kline in enumerate(self.merged_klines[:5]):
                print(f"{i+1}. {kline}")
            
            if len(self.merged_klines) > 5:
                print(f"... 还有 {len(self.merged_klines) - 5} 根")
                
            # 显示分型信息
            self.visualizer.print_fractal_details()
        else:
            print("❌ 尚未执行合并操作")
    
    def plot_chart(self, title: str = "缠论K线合并分析图", 
                   figsize: tuple = (15, 10), 
                   save_path: str = None):
        """
        绘制K线图表，包含分型标记和笔
        
        参数：
        - title: 图表标题
        - figsize: 图表大小
        - save_path: 保存路径（可选）
        """
        if not self.original_klines or not self.merged_klines:
            print("❌ 请先加载数据并执行合并操作")
            return None
        
        fig = self.visualizer.plot_klines(
            self.original_klines, 
            self.merged_klines, 
            title=title,
            figsize=figsize,
            save_path=save_path
        )
        
        return fig
    
    def validate_data(self) -> bool:
        """验证K线数据的有效性"""
        if not self.original_klines:
            self._log("错误: 没有K线数据需要验证")
            return False
        
        invalid_count = 0
        for i, kline in enumerate(self.original_klines):
            # 检查价格数据的合理性
            if kline.high < kline.low:
                self._log(f"第 {i+1} 根K线最高价小于最低价: {kline}")
                invalid_count += 1
        
        if invalid_count == 0:
            self._log("✅ K线数据验证通过")
            return True
        else:
            self._log(f"❌ 发现 {invalid_count} 处数据异常")
            return False