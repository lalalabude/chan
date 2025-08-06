"""
缠论K线分析GUI应用程序
提供交互式的K线合并分析、分型标记和用户自定义标记功能
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.patches as patches
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Optional, Dict, Tuple
import os

from chan_kline_tool import ChanKLineTool
from kline_data import KLine, MergedKLine

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class DrawingTool:
    """绘图工具类，处理用户自定义标记"""
    def __init__(self, ax, canvas):
        self.ax = ax
        self.canvas = canvas
        self.drawing_mode = None  # 'line', 'rect', None
        self.start_point = None
        self.current_artist = None
        self.user_drawings = []  # 存储用户绘制的图形
        
    def set_drawing_mode(self, mode):
        """设置绘图模式"""
        self.drawing_mode = mode
        
    def on_press(self, event):
        """鼠标按下事件"""
        if event.inaxes != self.ax or self.drawing_mode is None:
            return
        
        self.start_point = (event.xdata, event.ydata)
        
    def on_motion(self, event):
        """鼠标移动事件"""
        if event.inaxes != self.ax or self.drawing_mode is None or self.start_point is None:
            return
            
        # 移除临时绘制的图形
        if self.current_artist:
            self.current_artist.remove()
            self.current_artist = None
            
        end_point = (event.xdata, event.ydata)
        
        if self.drawing_mode == 'line':
            # 绘制临时直线
            line = self.ax.plot([self.start_point[0], end_point[0]], 
                               [self.start_point[1], end_point[1]], 
                               'r--', alpha=0.7, linewidth=2)[0]
            self.current_artist = line
            
        elif self.drawing_mode == 'rect':
            # 绘制临时矩形
            width = end_point[0] - self.start_point[0]
            height = end_point[1] - self.start_point[1]
            rect = patches.Rectangle(self.start_point, width, height, 
                                   linewidth=2, edgecolor='r', 
                                   facecolor='yellow', alpha=0.3)
            self.ax.add_patch(rect)
            self.current_artist = rect
            
        self.canvas.draw_idle()
        
    def on_release(self, event):
        """鼠标释放事件"""
        if event.inaxes != self.ax or self.drawing_mode is None or self.start_point is None:
            return
            
        end_point = (event.xdata, event.ydata)
        
        # 移除临时图形
        if self.current_artist:
            self.current_artist.remove()
            self.current_artist = None
            
        # 添加永久图形
        if self.drawing_mode == 'line':
            line = self.ax.plot([self.start_point[0], end_point[0]], 
                               [self.start_point[1], end_point[1]], 
                               'red', linewidth=2, label='用户标记线')[0]
            self.user_drawings.append(line)
            
        elif self.drawing_mode == 'rect':
            width = end_point[0] - self.start_point[0]
            height = end_point[1] - self.start_point[1]
            rect = patches.Rectangle(self.start_point, width, height, 
                                   linewidth=2, edgecolor='red', 
                                   facecolor='yellow', alpha=0.3)
            self.ax.add_patch(rect)
            self.user_drawings.append(rect)
            
        self.start_point = None
        self.drawing_mode = None  # 绘制完成后退出绘图模式
        self.canvas.draw()
        
    def clear_drawings(self):
        """清除所有用户绘制的图形"""
        for artist in self.user_drawings:
            if hasattr(artist, 'remove'):
                artist.remove()
            else:
                artist.set_visible(False)
        self.user_drawings.clear()
        self.canvas.draw()


class ChanGUIApp:
    """缠论K线分析GUI主应用"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("缠论K线分析工具 v2.0")
        self.root.geometry("1400x900")
        
        # 数据
        self.chan_tool = ChanKLineTool()
        self.original_data = []
        self.merged_data = []
        self.current_view = "original"  # "original" 或 "merged"
        
        # GUI组件
        self.setup_gui()
        self.setup_matplotlib()
        self.setup_drawing_tool()
        
        # 状态
        self.data_loaded = False
        self.merged = False
        self.show_markers = True  # 标记显示状态
        self.selected_kline_info = None  # 选中的K线信息
        
    def setup_gui(self):
        """设置GUI界面"""
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 第一行按钮
        button_frame1 = ttk.Frame(control_frame)
        button_frame1.pack(fill=tk.X, pady=(0, 5))
        
        self.import_btn = ttk.Button(button_frame1, text="📁 导入数据", 
                                   command=self.import_data, width=15)
        self.import_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.view_original_btn = ttk.Button(button_frame1, text="📊 原始K线", 
                                          command=self.show_original, width=15)
        self.view_original_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.view_original_btn.config(state='disabled')
        
        self.view_merged_btn = ttk.Button(button_frame1, text="📈 合并K线", 
                                        command=self.show_merged, width=15)
        self.view_merged_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.view_merged_btn.config(state='disabled')
        
        # 第二行：绘图工具
        button_frame2 = ttk.Frame(control_frame)
        button_frame2.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(button_frame2, text="绘图工具:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.draw_line_btn = ttk.Button(button_frame2, text="📏 画线", 
                                      command=self.start_draw_line, width=12)
        self.draw_line_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.draw_rect_btn = ttk.Button(button_frame2, text="⬜ 画框", 
                                      command=self.start_draw_rect, width=12)
        self.draw_rect_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.clear_btn = ttk.Button(button_frame2, text="🗑️ 清除标记", 
                                  command=self.clear_drawings, width=12)
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.toggle_markers_btn = ttk.Button(button_frame2, text="👁️ 隐藏标记", 
                                           command=self.toggle_markers, width=12)
        self.toggle_markers_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 状态信息
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(fill=tk.X)
        
        self.status_label = ttk.Label(status_frame, text="请导入数据开始分析", 
                                    foreground="blue")
        self.status_label.pack(side=tk.LEFT)
        
        # K线坐标信息显示
        self.coordinate_label = ttk.Label(status_frame, text="", 
                                        foreground="green")
        self.coordinate_label.pack(side=tk.RIGHT)
        
        # 图表框架
        chart_frame = ttk.LabelFrame(main_frame, text="K线图表", padding=5)
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        self.chart_container = chart_frame
        
    def setup_matplotlib(self):
        """设置matplotlib图表"""
        self.fig = Figure(figsize=(12, 8), dpi=100)
        self.ax = self.fig.add_subplot(111)
        
        self.canvas = FigureCanvasTkAgg(self.fig, self.chart_container)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 添加增强的工具栏
        toolbar_frame = ttk.Frame(self.chart_container)
        toolbar_frame.pack(fill=tk.X)
        
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()
        
        # 添加自定义缩放按钮
        custom_toolbar = ttk.Frame(toolbar_frame)
        custom_toolbar.pack(side=tk.RIGHT, fill=tk.X)
        
        ttk.Button(custom_toolbar, text="重置视图", 
                  command=self.reset_view, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(custom_toolbar, text="适应窗口", 
                  command=self.fit_to_window, width=10).pack(side=tk.LEFT, padx=2)
        
        # 初始化空图表
        self.ax.set_title("缠论K线分析工具", fontsize=16, fontweight='bold')
        self.ax.text(0.5, 0.5, '请导入数据开始分析', 
                    transform=self.ax.transAxes, 
                    ha='center', va='center', 
                    fontsize=16, color='gray')
        self.canvas.draw()
        
    def setup_drawing_tool(self):
        """设置绘图工具"""
        self.drawing_tool = DrawingTool(self.ax, self.canvas)
        
        # 连接鼠标事件
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('motion_notify_event', self.drawing_tool.on_motion)
        self.canvas.mpl_connect('button_release_event', self.drawing_tool.on_release)
        
    def import_data(self):
        """导入数据"""
        file_path = filedialog.askopenfilename(
            title="选择K线数据文件",
            filetypes=[
                ("Excel files", "*.xlsx *.xls"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
            
        try:
            # 尝试加载数据
            success = self.chan_tool.load_from_excel(file_path)
            
            if success:
                self.original_data = self.chan_tool.original_klines
                self.data_loaded = True
                self.merged = False
                
                # 更新状态
                self.status_label.config(text=f"已导入 {len(self.original_data)} 根K线数据", 
                                       foreground="green")
                
                # 启用相关按钮
                self.view_original_btn.config(state='normal')
                self.view_merged_btn.config(state='normal')
                
                # 显示原始K线
                self.show_original()
                
            else:
                messagebox.showerror("错误", "数据导入失败，请检查文件格式")
                
        except Exception as e:
            messagebox.showerror("错误", f"导入数据时出错: {str(e)}")
            

    def draw_candlestick(self, ax, times, highs, lows, title, color_scheme='original'):
        """绘制K线柱状图（只显示最高价和最低价之间的柱状）"""
        ax.clear()
        
        # 绘制K线柱状
        for i, (time, high, low) in enumerate(zip(times, highs, lows)):
            if color_scheme == 'original':
                # 原始K线用蓝色
                color = 'lightblue'
                edge_color = 'blue'
            else:
                # 合并K线用绿色
                color = 'lightgreen'
                edge_color = 'darkgreen'
            
            # 绘制从最低价到最高价的柱状图
            bar_width = 0.6
            bar_height = high - low
            
            rect = patches.Rectangle((time - bar_width/2, low), bar_width, bar_height,
                                   linewidth=2, edgecolor=edge_color, 
                                   facecolor=color, alpha=0.8)
            ax.add_patch(rect)
            
            # 在柱状图中央显示序号
            mid_price = (high + low) / 2
            ax.text(time, mid_price, str(i+1), 
                   ha='center', va='center', fontsize=8, fontweight='bold', color='black')
        
        # 设置图表属性
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('时间序列', fontsize=12)
        ax.set_ylabel('价格', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # 设置x轴
        ax.set_xlim(-0.5, len(times) - 0.5)
        if len(times) > 0:
            ax.set_xticks(range(len(times)))
            ax.set_xticklabels([f'K{i+1}' for i in range(len(times))], rotation=45)
            
            # 设置y轴范围，确保所有数据可见
            y_min = min(lows) * 0.98
            y_max = max(highs) * 1.02
            ax.set_ylim(y_min, y_max)
        
        return ax
        
    def show_original(self):
        """显示原始K线"""
        if not self.data_loaded:
            return
            
        self.current_view = "original"
        
        # 准备数据
        times = list(range(len(self.original_data)))
        highs = [k.high for k in self.original_data]
        lows = [k.low for k in self.original_data]
        
        # 绘制图表
        self.draw_candlestick(self.ax, times, highs, lows, 
                            f"原始K线图 (共{len(self.original_data)}根)", 'original')
        
        # 清除之前的用户绘制
        self.drawing_tool.user_drawings.clear()
        
        # 强制刷新canvas
        self.canvas.draw_idle()
        self.canvas.flush_events()
        
    def show_merged(self):
        """显示合并后的K线"""
        if not self.data_loaded:
            messagebox.showwarning("警告", "请先导入数据")
            return
            
        # 如果还没有合并，自动执行合并
        if not self.merged:
            try:
                success = self.chan_tool.merge_klines()
                if success:
                    self.merged_data = self.chan_tool.merged_klines
                    self.merged = True
                    
                    # 更新状态
                    stats = self.chan_tool.get_statistics()
                    self.status_label.config(
                        text=f"合并完成: {stats['原始K线数量']} → {stats['合并后K线数量']} 根 (压缩比: {stats['压缩比']})", 
                        foreground="green"
                    )
                else:
                    messagebox.showerror("错误", "K线合并失败")
                    return
            except Exception as e:
                messagebox.showerror("错误", f"合并K线时出错: {str(e)}")
                return
            
        self.current_view = "merged"
        
        # 准备数据
        times = list(range(len(self.merged_data)))
        highs = [k.high for k in self.merged_data]
        lows = [k.low for k in self.merged_data]
        
        # 绘制图表
        self.draw_candlestick(self.ax, times, highs, lows, 
                            f"合并后K线图 (共{len(self.merged_data)}根)", 'merged')
        
        # 添加分型标记和笔的连线（如果启用了标记显示）
        if self.show_markers:
            self.add_fractal_markers()
            self.add_pen_lines()
        
        # 添加合并信息标记
        self.add_merge_info()
        
        self.canvas.draw()
        
    def add_fractal_markers(self):
        """添加分型标记"""
        fractals = self.chan_tool.visualizer.detect_fractals(self.merged_data)
        pens = self.chan_tool.visualizer.calculate_pens(fractals)
        
        # 获取被笔连接的分型
        used_fractals = getattr(self.chan_tool.visualizer, 'used_fractals', set())
        
        for fractal in fractals:
            # 只显示被笔连接的分型
            if fractal in used_fractals:
                time_index = fractal.index
                price = fractal.price
                
                if fractal.type == 'top':
                    # 顶分型用红色向下三角
                    self.ax.scatter(time_index, price, marker='v', s=200, c='red', 
                                  edgecolors='darkred', linewidth=2, zorder=5,
                                  label='顶分型' if fractal == list(used_fractals)[0] else "")
                else:
                    # 底分型用绿色向上三角
                    self.ax.scatter(time_index, price, marker='^', s=200, c='green', 
                                  edgecolors='darkgreen', linewidth=2, zorder=5,
                                  label='底分型' if fractal == list(used_fractals)[0] else "")
                              
    def add_pen_lines(self):
        """添加笔的连线"""
        pens = self.chan_tool.visualizer.calculate_pens()
        
        for i, pen in enumerate(pens):
            start_index = pen.start_fractal.index
            end_index = pen.end_fractal.index
            start_price = pen.start_price
            end_price = pen.end_price
            
            # 绘制笔的连线
            self.ax.plot([start_index, end_index], [start_price, end_price],
                        'k-', linewidth=3, alpha=0.8, zorder=4,
                        label='笔' if i == 0 else "")
            
            # 在笔的中点添加方向标记
            mid_index = (start_index + end_index) / 2
            mid_price = (start_price + end_price) / 2
            
            direction_symbol = '↗' if pen.direction == 'up' else '↘'
            self.ax.annotate(direction_symbol, xy=(mid_index, mid_price), 
                           fontsize=14, ha='center', va='center',
                           color='black', fontweight='bold', zorder=6)
                           
    def add_merge_info(self):
        """添加合并信息标记"""
        for i, k in enumerate(self.merged_data):
            if k.original_count > 1:
                # 在合并的K线上方显示合并数量
                self.ax.annotate(f'×{k.original_count}', 
                               xy=(i, k.high), 
                               xytext=(5, 10), 
                               textcoords='offset points',
                               fontsize=10, 
                               color='purple',
                               fontweight='bold',
                               bbox=dict(boxstyle='round,pad=0.3', 
                                       facecolor='yellow', alpha=0.8))
        
    def start_draw_line(self):
        """开始画线模式"""
        self.drawing_tool.set_drawing_mode('line')
        self.status_label.config(text="画线模式：点击并拖拽绘制直线", foreground="orange")
        
    def start_draw_rect(self):
        """开始画框模式"""
        self.drawing_tool.set_drawing_mode('rect')
        self.status_label.config(text="画框模式：点击并拖拽绘制矩形", foreground="orange")
        
    def clear_drawings(self):
        """清除用户绘制的标记"""
        self.drawing_tool.clear_drawings()
        self.status_label.config(text="已清除所有用户标记", foreground="blue")
    
    def toggle_markers(self):
        """切换标记显示/隐藏"""
        self.show_markers = not self.show_markers
        if self.show_markers:
            self.toggle_markers_btn.config(text="👁️ 隐藏标记")
            self.status_label.config(text="标记已显示", foreground="blue")
        else:
            self.toggle_markers_btn.config(text="👁️ 显示标记")
            self.status_label.config(text="标记已隐藏", foreground="blue")
        
        # 重新绘制当前视图
        if self.current_view == "merged":
            self.show_merged()
        elif self.current_view == "original":
            self.show_original()
    
    def on_click(self, event):
        """处理鼠标点击事件"""
        # 如果在绘图模式，传递给绘图工具
        if self.drawing_tool.drawing_mode is not None:
            self.drawing_tool.on_press(event)
            return
        
        if event.inaxes != self.ax or not self.data_loaded:
            return
        
        # 获取点击位置
        x_click = event.xdata
        y_click = event.ydata
        
        if x_click is None or y_click is None:
            return
        
        # 查找最近的K线
        self.find_nearest_kline(x_click, y_click)
    
    def find_nearest_kline(self, x_click, y_click):
        """查找最近的K线并显示坐标信息"""
        if self.current_view == "original" and self.original_data:
            klines = self.original_data
            times = list(range(len(klines)))
        elif self.current_view == "merged" and self.merged_data:
            klines = self.merged_data
            times = list(range(len(klines)))
        else:
            return
        
        # 找到最近的K线索引
        if len(times) == 0:
            return
        
        nearest_index = min(range(len(times)), key=lambda i: abs(times[i] - x_click))
        
        # 获取K线信息
        kline = klines[nearest_index]
        
        # 显示坐标信息
        if self.current_view == "original":
            info_text = f"K线 {nearest_index + 1}: 高={kline.high:.2f}, 低={kline.low:.2f}, 中间价={kline.mid_price:.2f}"
        else:
            info_text = f"K线 {nearest_index + 1}: 高={kline.high:.2f}, 低={kline.low:.2f}, 中间价={kline.mid_price:.2f}"
            if hasattr(kline, 'original_count'):
                info_text += f", 合并数={kline.original_count}"
        
        self.coordinate_label.config(text=info_text)
        
        # 在图上高亮显示选中的K线
        self.highlight_selected_kline(nearest_index)
    
    def highlight_selected_kline(self, index):
        """高亮显示选中的K线"""
        # 清除之前的高亮
        if hasattr(self, 'highlight_artist') and self.highlight_artist:
            try:
                self.highlight_artist.remove()
            except:
                # 如果无法移除，则隐藏
                self.highlight_artist.set_visible(False)
        
        # 获取当前数据
        if self.current_view == "original" and self.original_data:
            klines = self.original_data
        elif self.current_view == "merged" and self.merged_data:
            klines = self.merged_data
        else:
            return
        
        if index >= len(klines):
            return
        
        kline = klines[index]
        
        # 绘制高亮框
        bar_width = 0.8
        bar_height = kline.high - kline.low
        
        highlight_rect = patches.Rectangle((index - bar_width/2, kline.low), 
                                         bar_width, bar_height,
                                         linewidth=3, edgecolor='yellow', 
                                         facecolor='none', alpha=0.8)
        self.ax.add_patch(highlight_rect)
        self.highlight_artist = highlight_rect
        
        self.canvas.draw_idle()
    
    def reset_view(self):
        """重置视图到初始状态"""
        if not self.data_loaded:
            return
        
        # 重新绘制当前视图
        if self.current_view == "merged":
            self.show_merged()
        elif self.current_view == "original":
            self.show_original()
    
    def fit_to_window(self):
        """适应窗口大小"""
        if not self.data_loaded:
            return
        
        self.ax.relim()
        self.ax.autoscale()
        self.canvas.draw()


def main():
    """主函数"""
    # 创建主窗口
    root = tk.Tk()
    
    # 设置窗口图标（如果有的话）
    try:
        root.iconbitmap('icon.ico')
    except:
        pass
    
    # 创建应用实例
    app = ChanGUIApp(root)
    
    # 运行应用
    root.mainloop()


if __name__ == "__main__":
    main()