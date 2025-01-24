import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from ui.map_viewer import MapViewer

def main():
    app = QApplication(sys.argv)
    # 設置全局字體，支持中文顯示
    font = QFont("Microsoft YaHei", 9)  # 使用微軟雅黑字體，大小為9
    app.setFont(font)
    viewer = MapViewer()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()