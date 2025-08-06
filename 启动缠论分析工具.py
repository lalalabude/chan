"""
缠论K线分析工具启动脚本
双击此文件即可启动GUI应用程序
"""
import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from chan_gui_app import main
    print("🎯 启动缠论K线分析工具...")
    print("=" * 50)
    print("功能说明:")
    print("1. 📁 导入数据：支持Excel文件导入")
    print("2. ⚙️ 执行合并：按缠论理论合并K线")
    print("3. 📊 查看图表：原始K线和合并K线对比")
    print("4. 📏 绘图工具：支持画线、画框标记")
    print("5. 🔺 分型标记：自动标记顶分型和底分型")
    print("6. 📈 笔的连线：连接分型形成笔")
    print("=" * 50)
    
    # 启动GUI应用
    main()
    
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保已安装所需依赖包:")
    print("pip install -r requirements.txt")
    input("按回车键退出...")
    
except Exception as e:
    print(f"❌ 程序运行出错: {e}")
    input("按回车键退出...")