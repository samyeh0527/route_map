import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from ui.map_viewer import MapViewer
import matplotlib
import warnings

def setup_matplotlib():
    """設置 Matplotlib 的配置"""
    # 關閉字體相關警告
    warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
    
    # 設置中文字體
    matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
    matplotlib.rcParams['axes.unicode_minus'] = False
    
    # 設置 DPI 和後端
    matplotlib.use('Qt5Agg')
    matplotlib.rcParams['figure.dpi'] = 100

def main():
    # 在創建任何 matplotlib 圖表之前設置配置
    setup_matplotlib()
    
    app = QApplication(sys.argv)
    # 設置全局字體，支持中文顯示
    font = QFont("Microsoft YaHei", 9)  # 使用微軟雅黑字體，大小為9
    app.setFont(font)
    viewer = MapViewer()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()