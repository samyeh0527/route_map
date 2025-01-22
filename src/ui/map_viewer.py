# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QHBoxLayout, QLabel, QSpinBox, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
from matplotlib import rcParams

from data.data_processor import DataProcessor
from plot.plot_manager import PlotManager
from ui.overlay_widget import OverlayWidget

class MapViewer(QMainWindow):
    """主窗口類"""
    def __init__(self):
        super().__init__()
        # 設置字體以支持中文顯示
        font = self.font()
        font.setFamily("Microsoft YaHei")  # 或其他支持中文的字體
        self.setFont(font)
        self.setWindowTitle("路線圖檢視器")
        self.setGeometry(100, 100, 1200, 800)
        # 初始化變量
        self.range_groups = []
        self.pending_highlight_index = None
        self.pending_range_index = None
        
        # 設置高亮定時器
        self.highlight_timer = QTimer()
        self.highlight_timer.setSingleShot(True)
        self.highlight_timer.timeout.connect(self._delayed_highlight)
        
        # 創建按鈕
        self.load_button = QPushButton("載入CSV")
        self.update_button = QPushButton("更新圖表")
        
        # 設置UI
        self._init_ui()
        
        # 連接按鈕信號
        self.load_button.clicked.connect(self.load_csv)
        self.update_button.clicked.connect(self.update_data_range)
        
        print("初始化完成：按鈕信號已連接")

    def _init_ui(self):
        """初始化UI"""
        # 創建中央部件和主布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 使用水平布局分割左右兩部分
        main_layout = QHBoxLayout(self.central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 左側控制面板（固定寬度）
        left_panel = QWidget()
        left_panel.setFixedWidth(350)  # 設置固定寬度
        self.left_layout = QVBoxLayout(left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(10)
        
        # 右側圖表區域
        right_panel = QWidget()
        self.right_layout = QVBoxLayout(right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)
        
        # 添加左右面板到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        # 設置左側控制面板
        self._setup_control_panel()
        
        # 設置右側圖表區域
        self._setup_plot_area()
        
    def _setup_control_panel(self):
        """設置控制面板"""
        # 創建控制面板容器
        control_panel = QWidget()
        control_panel.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """)
        
        # 創建主布局
        self.control_layout = QVBoxLayout(control_panel)
        self.control_layout.setContentsMargins(15, 15, 15, 15)
        self.control_layout.setSpacing(15)
        
        # 創建按鈕組
        button_group = QHBoxLayout()
        button_group.setSpacing(10)
        
        add_range_button = QPushButton("添加範圍")
        
        # 設置按鈕樣式
        for button in [self.load_button, add_range_button, self.update_button]:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #007bff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 5px 10px;
                    min-width: 80px;
                    height: 28px;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QPushButton:pressed {
                    background-color: #004085;
                }
            """)
        
        button_group.addWidget(self.load_button)
        button_group.addWidget(add_range_button)
        button_group.addWidget(self.update_button)
        button_group.addStretch()
        
        # 添加到控制面板布局
        self.control_layout.addLayout(button_group)
        
        # 添加第一個範圍組
        self.add_range_group()
        
        # 添加彈性空間
        self.control_layout.addStretch()
        
        # 添加到左側布局
        self.left_layout.addWidget(control_panel)
        
        # 連接添加範圍按鈕信號
        add_range_button.clicked.connect(self.add_range_group)
        
        print("控制面板設置完成：按鈕已添加到布局")

    def _setup_plot_area(self):
        """設置圖表區域"""
        # 創建圖表容器
        plot_container = QWidget()
        plot_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """)
        
        # 圖表布局
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(10, 10, 10, 10)
        
        # 創建圖表，設置更大的高度
        self.figure = Figure(figsize=(8, 12))  # 調整圖表的整體大小
        
        # 設置全局字體以支持中文
        rcParams['font.family'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
        rcParams['axes.unicode_minus'] = False  # 正確顯示負號
        rcParams['axes.titley'] = 1.0  # 移除標題的空間
        rcParams['axes.titlepad'] = -14  # 調整標題的間距
        
        self.canvas = FigureCanvas(self.figure)
        plot_layout.addWidget(self.canvas)
        
        # 創建圖表管理器並設置回調
        self.plot_manager = PlotManager(self.figure)
        self.plot_manager.set_click_callback(self._on_plot_clicked)
        
        # 添加到右側布局
        self.right_layout.addWidget(plot_container)

    def add_range_group(self):
        """添加新的範圍組"""
        group_id = len(self.range_groups)
        
        # 創建範圍組容器
        range_container = QWidget()
        range_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                margin: 2px;
            }
            QLabel[time="true"] {
                color: #0d6efd;
                padding: 4px 8px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-size: 12px;
            }
        """)
        
        # 創建垂直布局來包含標題和內容
        range_v_layout = QVBoxLayout(range_container)
        range_v_layout.setContentsMargins(10, 8, 10, 8)
        range_v_layout.setSpacing(8)
        
        # 創建標題行
        title_layout = QHBoxLayout()
        title_layout.setSpacing(5)
        
        # 範圍標題
        range_title = QLabel(f"範圍 {group_id + 1}")
        range_title.setStyleSheet("""
            QLabel {
                color: #495057;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        
        # 時間顯示標籤
        time_label = QLabel()
        time_label.setProperty("time", True)
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setText("時間: --:--:--")
        
        # 刪除按鈕（第一個範圍組除外）
        if group_id > 0:
            delete_button = QPushButton("✕")
            delete_button.setFixedSize(20, 20)
            delete_button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #dc3545;
                    border: none;
                    font-weight: bold;
                    padding: 0px;
                    min-width: 20px;
                }
                QPushButton:hover {
                    color: #c82333;
                }
            """)
            delete_button.clicked.connect(
                lambda: self.delete_range_group(range_container, group_id)
            )
            title_layout.addWidget(delete_button)
        
        title_layout.addWidget(range_title)
        title_layout.addStretch()
        title_layout.addWidget(time_label)
        
        # 添加所有元素到主布局
        range_v_layout.addLayout(title_layout)
        
        # 保存範圍組（使用隱藏的起始和結束位置）
        self.range_groups.append({
            'id': group_id,
            'container': range_container,
            'start': 0,  # 默認起始位置
            'end': 0,    # 默認結束位置
            'time_label': time_label
        })
        
        # 添加到控制面板
        self.control_layout.insertWidget(
            self.control_layout.count() - 1,  # 在彈性空間之前插入
            range_container
        )

    def delete_range_group(self, container, group_id):
        """刪除範圍組"""
        # 從界面移除
        container.deleteLater()
        
        # 從列表中移除
        self.range_groups = [g for g in self.range_groups if g['id'] != group_id]

    def update_data_range(self):
        """更新數據範圍"""
        try:
            print("\n=== 開始更新數據範圍 ===")
            if not hasattr(self, 'full_data'):
                print("錯誤：沒有載入數據")
                return
            
            # 獲取所有有效的數據範圍
            valid_ranges = []
            max_idx = len(self.full_data)
            
            # 為每個範圍組設置默認的起始和結束位置
            for i, group in enumerate(self.range_groups):
                if i == 0:  # 第一個範圍
                    start = 0
                    end = max_idx // len(self.range_groups)
                else:  # 其他範圍
                    prev_end = self.range_groups[i-1]['end']
                    start = prev_end
                    end = min(start + (max_idx // len(self.range_groups)), max_idx)
                
                group['start'] = start
                group['end'] = end
                
                print(f"\n範圍 {group['id'] + 1}:")
                print(f"起始位置: {start}")
                print(f"結束位置: {end}")
                
                if start >= end:
                    print(f"警告：範圍 {group['id'] + 1} 起始位置必須小於結束位置")
                    continue
                    
                if end > max_idx:
                    print(f"警告：範圍 {group['id'] + 1} 結束位置超出數據範圍")
                    continue
                
                if end - start > 0:
                    valid_ranges.append((start, end))
            
            if not valid_ranges:
                print("錯誤：沒有有效的數據範圍")
                QMessageBox.warning(self, "警告", "沒有有效的數據範圍")
                return
            
            try:
                # 處理所有有效範圍的數據
                all_data = []
                for i, (start, end) in enumerate(valid_ranges):
                    print(f"\n處理第 {i+1} 段數據...")
                    data = self.full_data.iloc[start:end].copy()
                    data.reset_index(drop=True, inplace=True)
                    all_data.append(data)
                    print(f"第 {i+1} 段數據大小: {len(data)} 行")
                
                # 更新圖表管理器的數據
                self.plot_manager.data_list = all_data
                
                # 更新圖表
                print("\n開始更新圖表...")
                self.plot_manager.create_plots()
                
                # 更新時間顯示
                self._calculate_time_difference()
                
                print("=== 數據更新完成 ===")
                
            except Exception as e:
                print(f"處理數據時出錯: {str(e)}")
                QMessageBox.critical(self, "錯誤", f"處理數據時出錯：{str(e)}")
            
        except Exception as e:
            print(f"更新數據範圍時出錯: {str(e)}")
            QMessageBox.critical(self, "錯誤", f"更新數據範圍時出錯：{str(e)}")

    def _on_update_complete(self, updated_data):
        """數據更新完成的回調"""
        try:
            print("數據更新完成，開始更新顯示...")
            self.data = updated_data
            self.plot_manager.data_list = [self.data]
            self.plot_manager.axes = None
            self.plot_manager.create_plots()
            
            print("顯示更新完成")
            
        except Exception as e:
            print(f"更新顯示時出錯: {str(e)}")
            self._on_update_error(str(e))
            
        finally:
            self._enable_controls()

    def _on_update_error(self, error_msg):
        """數據更新錯誤的回調"""
        print(f"發生錯誤: {error_msg}")
        QMessageBox.critical(self, "錯誤", f"更新數據時發生錯誤：{error_msg}")
        self._enable_controls()

    def _disable_controls(self):
        """禁用所有控件"""
        self.load_button.setEnabled(False)
        for group in self.range_groups:
            group['start_spin'].setEnabled(False)
            group['end_spin'].setEnabled(False)
        self.update_button.setEnabled(False)
        self.overlay.show()
        QApplication.processEvents()

    def _enable_controls(self):
        """啟用所有控件"""
        self.load_button.setEnabled(True)
        for group in self.range_groups:
            group['start_spin'].setEnabled(True)
            group['end_spin'].setEnabled(True)
        self.update_button.setEnabled(True)
        self.overlay.hide()
        QApplication.processEvents()

    def _calculate_time_difference(self):
        """計算每個範圍的時間差"""
        try:
            for group in self.range_groups:
                start = group['start']
                end = group['end']
                
                if end - start <= 0:
                    group['time_label'].setText("時間: 無效範圍")
                    continue
                    
                try:
                    # 獲取該範圍的數據
                    data = self.full_data.iloc[start:end]
                    
                    if 'Time' not in data.columns:
                        group['time_label'].setText("時間: 無時間數據")
                        continue
                        
                    # 計算時間差
                    start_time = pd.to_datetime(data['Time'].iloc[0])
                    end_time = pd.to_datetime(data['Time'].iloc[-1])
                    time_diff = end_time - start_time
                    
                    # 格式化時間差
                    hours = time_diff.total_seconds() // 3600
                    minutes = (time_diff.total_seconds() % 3600) // 60
                    seconds = time_diff.total_seconds() % 60
                    
                    time_str = f"時間: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
                    group['time_label'].setText(time_str)
                    
                except Exception as e:
                    print(f"計算範圍 {group['id'] + 1} 時間差時出錯: {str(e)}")
                    group['time_label'].setText("時間: 計算錯誤")
                
        except Exception as e:
            print(f"計算時間差時出錯: {str(e)}")
            return "時間計算錯誤"

    def load_csv(self):
        """載入 CSV 文件"""
        try:
            # 選擇文件
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "選擇 CSV 文件",
                "",
                "CSV 文件 (*.csv);;所有文件 (*.*)"
            )
            
            if not file_path:
                return
                
            print("\n=== 開始載入 CSV 文件 ===")
            print(f"文件路徑: {file_path}")
            
            # 讀取 CSV 文件
            self.full_data = pd.read_csv(file_path)
            max_value = len(self.full_data) - 1  # 最後一筆索引
            print(f"載入數據總長度: {len(self.full_data)} 筆")
            print(f"數據索引範圍: 0 到 {max_value}")
            
            # 設置所有範圍組的最大值和預設值
            for group in self.range_groups:
                group['start'] = 0
                group['end'] = max_value
            
            # 初始化圖表管理器的數據
            self.plot_manager.data_list = []
            
            # 更新圖表
            self.update_data_range()
            print("=== CSV 文件載入完成 ===\n")
            
        except Exception as e:
            print(f"載入 CSV 文件時出錯: {str(e)}")
            QMessageBox.critical(self, "錯誤", f"無法載入文件：{str(e)}")

    def resizeEvent(self, event):
        """窗口大小改變時調整遮罩層"""
        super().resizeEvent(event)
        if hasattr(self, 'overlay'):
            self.overlay.resize(self.central_widget.size())

    def _on_plot_clicked(self, range_idx, data_idx):
        """處理圖表點擊事件"""
        try:
            # 更新對應範圍的 SpinBox
            if 0 <= range_idx < len(self.range_groups):
                group = self.range_groups[range_idx]
                start = group['start']
                # 計算實際數據索引
                actual_idx = start + data_idx
                # 高亮顯示
                self.highlight_data_point(range_idx, actual_idx)
                
        except Exception as e:
            print(f"處理圖表點擊回調時出錯: {str(e)}")

    def highlight_data_point(self, range_idx, data_idx):
        """高亮顯示數據點
        
        Args:
            range_idx: 範圍索引
            data_idx: 數據點索引
        """
        if not self.range_groups or range_idx >= len(self.range_groups):
            print(f"無效的範圍索引: {range_idx}")
            return
            
        try:
            group = self.range_groups[range_idx]
            start = group['start']
            end = group['end']
            
            if start <= data_idx < end:
                self.pending_highlight_index = data_idx
                self.pending_range_index = range_idx
                self.highlight_timer.start(100)
            else:
                print(f"數據點索引 {data_idx} 超出範圍 {start}-{end}")
                
        except Exception as e:
            print(f"設置高亮點時出錯: {str(e)}")

    def _delayed_highlight(self):
        """延遲執行的高亮顯示"""
        if self.pending_highlight_index is not None and hasattr(self, 'pending_range_index'):
            index = self.pending_highlight_index
            range_idx = self.pending_range_index
            
            try:
                if 0 <= range_idx < len(self.range_groups):
                    self.plot_manager.create_plots(highlight_index=index, highlight_range=range_idx)
            except Exception as e:
                print(f"延遲高亮顯示時出錯: {str(e)}")
