"""
创建GUI工具测试用的示例数据
"""
import pandas as pd
from datetime import datetime, timedelta
import random

def create_sample_excel():
    """创建示例Excel文件用于GUI工具测试"""
    
    # 生成测试数据
    data = []
    base_price = 100.0
    start_time = datetime(2024, 1, 1, 9, 0)
    
    # 生成50根K线数据，包含一些明显的包含关系
    for i in range(50):
        current_time = start_time + timedelta(minutes=i*5)
        
        # 模拟价格波动
        price_change = random.uniform(-1.5, 1.5)
        base_price += price_change
        
        # 生成高低价，确保有一些包含关系
        if i % 8 == 0:  # 每8根K线制造一个包含关系
            # 创建被包含的小K线
            price_range = random.uniform(0.3, 0.8)
        else:
            # 正常K线
            price_range = random.uniform(0.8, 2.0)
        
        high_price = base_price + price_range / 2
        low_price = base_price - price_range / 2
        
        data.append({
            'timestamp': current_time,
            'high': round(high_price, 2),
            'low': round(low_price, 2)
        })
        
        # 轻微调整基准价格
        base_price += random.uniform(-0.3, 0.3)
    
    # 创建DataFrame并保存
    df = pd.DataFrame(data)
    filename = "GUI测试数据.xlsx"
    df.to_excel(filename, index=False)
    
    print(f"✅ 已创建示例数据文件: {filename}")
    print(f"📊 包含 {len(data)} 根K线数据")
    print(f"🕐 时间范围: {data[0]['timestamp']} 到 {data[-1]['timestamp']}")
    print(f"💰 价格范围: {min(d['low'] for d in data):.2f} 到 {max(d['high'] for d in data):.2f}")
    
    return filename

if __name__ == "__main__":
    create_sample_excel()