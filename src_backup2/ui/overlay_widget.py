from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class OverlayWidget(QWidget):
    """遮罩層小部件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 設置遮罩層樣式
        self.setStyleSheet("""
            background-color: rgba(0, 0, 0, 30);
        """)
        
        # 創建等待提示
        layout = QVBoxLayout(self)
        self.label = QLabel("處理中，請稍候...", self)
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 80);
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label, alignment=Qt.AlignCenter)

    def resizeEvent(self, event):
        """確保遮罩層大小與父窗口一致"""
        self.setGeometry(self.parent().rect()) 