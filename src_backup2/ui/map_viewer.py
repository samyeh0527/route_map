# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QHBoxLayout, QLabel, QSpinBox, QMessageBox, QApplication, QListWidget, QListWidgetItem, QToolBar
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
from matplotlib import rcParams
import numpy as np
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import sys
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
        if getattr(sys, 'frozen', False):
            icon_path = sys._MEIPASS + '\\src\\icon\\002.ico'  # 使用打包後的路徑
        else:
            icon_path = 'icon/002.ico'  # 開發時的路徑
        self.setWindowIcon(QIcon(icon_path))


        self.setGeometry(100, 100, 1200, 800)
        
        # 初始化變量
        self.range_groups = []
        self.pending_highlight_index = None
        self.pending_range_index = None
        self.x_range = (-1000, 1000)  # 設置默認X軸範圍
        self.y_range = (-1000, 1000)  # 設置默認Y軸範圍
        self.is_setting_start_point = False
        
        # 設置高亮定時器
        self.highlight_timer = QTimer()
        self.highlight_timer.setSingleShot(True)
        self.highlight_timer.timeout.connect(self._delayed_highlight)
        
        # 創建按鈕
        self.load_button = QPushButton("載入CSV")
        self.set_start_button = QPushButton("設定起點")  # 在這裡創建按鈕
        self.update_button = QPushButton("更新圖表")
        self.switch_lap_button = QPushButton("切換單圈")
        
        # 設置UI
        self._init_ui()
        
        # 連接按鈕信號
        self.load_button.clicked.connect(self.load_csv)
        self.set_start_button.clicked.connect(self.start_setting_start_point)
        self.update_button.clicked.connect(self.update_data_range)
        self.switch_lap_button.clicked.connect(self.switch_lap)
        
        print("初始化完成：按鈕信號已連接")

        # 創建圖表管理器並設置回調
        self.plot_manager = PlotManager(self.figure)
        self.plot_manager.set_click_callback(self._on_plot_clicked)
        self.plot_manager.set_range_update_callback(self.update_range_list)

        # 設置 check_list 的選取模式
        self.check_list.setSelectionMode(QListWidget.NoSelection)  # 禁用選取反白
        self.check_list.setFocusPolicy(Qt.NoFocus)  # 禁用焦點顯示
        
        # 設置樣式表，移除選取時的背景色
        self.check_list.setStyleSheet("""
            QListWidget::item {
                background: transparent;
            }
            QListWidget::item:selected {
                background: transparent;
                color: black;
            }
            QListWidget::item:hover {
                background: transparent;
            }
        """)

    def _init_ui(self):
        """初始化UI"""
        # 創建中央部件和主布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 使用垂直布局作為主布局
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 創建頂部按鈕區域
        top_button_layout = QHBoxLayout()
        
        # 設置按鈕樣式
        button_style = """
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
        """
        
        # 添加按鈕到頂部布局
        for button in [self.load_button, self.set_start_button, self.update_button, self.switch_lap_button]:
            button.setStyleSheet(button_style)
            top_button_layout.addWidget(button)
        top_button_layout.addStretch()
        
        main_layout.addLayout(top_button_layout)
        
        # 創建主圖表容器
        plot_container = QWidget()
        plot_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """)
        
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(10, 10, 10, 10)
        
        # 創建主圖表（只包含三個垂直子圖）
        self.figure = Figure(figsize=(10, 6))
        self.axes = self.figure.subplots(3, 1)  # 只創建三個垂直排列的子圖
        
        # 初始化時不設置標題,等待數據載入後再設置
        for ax in self.axes:
            ax.set_title("")
        
        # 設置字體
        rcParams['font.family'] = ['Microsoft JhengHei', 'Noto Sans TC', 'DFKai-SB', 'sans-serif']
        rcParams['axes.unicode_minus'] = False
        rcParams['axes.titley'] = 1.0
        rcParams['axes.titlepad'] = -14
        
        self.canvas = FigureCanvas(self.figure)
        plot_layout.addWidget(self.canvas)
        
        # 創建軌跡圖
        self.track_figure = Figure(figsize=(8, 4))
        self.track_ax = self.track_figure.add_subplot(111)
        self.track_canvas = FigureCanvas(self.track_figure)
        
        # 新增：啟用緊湊布局
        self.track_figure.tight_layout()
        
        # 保存初始視圖狀態
        self.track_ax.set_title(" ", fontsize=8)
        self.track_ax.grid(True)
        self.track_ax.set_aspect('equal', adjustable='datalim')  # 修改：使用 adjustable='datalim'
        self.track_home_limits = None  # 添加這行來存儲初始視圖範圍
        
        # 創建圖表管理器並設置回調
        self.plot_manager = PlotManager(self.figure)
        self.plot_manager.set_click_callback(self._on_plot_clicked)
        
        main_layout.addWidget(plot_container)
        
        # 創建底部區域
        bottom_layout = QHBoxLayout()
        
        # 創建左側列表（可勾選的list）
        self.check_list = QListWidget()
        self.check_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:hover {
                background-color: #f8f9fa;
            }
        """)
        # itemChanged 訊號
        self.check_list.itemChanged.connect(self.on_item_changed)

        # 在底部右側添加位置軌跡圖
        track_plot_container = QWidget()
        track_plot_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """)
        
        track_plot_layout = QVBoxLayout(track_plot_container)
        track_plot_layout.setContentsMargins(15, 15, 15, 15)
        track_plot_layout.setSpacing(8)
        
        # 創建水平布局來放置導航工具欄和軌跡圖
        track_content_layout = QHBoxLayout()
        
        # 創建導航工具欄（縮放和平移）
        self.track_toolbar = NavigationToolbar(self.track_canvas, self, coordinates=False)
        self.track_toolbar.setOrientation(Qt.Vertical)
        self.track_toolbar.setStyleSheet("QToolBar { border: none; }")
        self.track_toolbar.hide()  # 隱藏原始工具欄

        # 創建兩個垂直工具欄容器
        left_toolbar = QToolBar()
        right_toolbar = QToolBar()
        left_toolbar.setOrientation(Qt.Vertical)
        right_toolbar.setOrientation(Qt.Vertical)
        left_toolbar.setStyleSheet("QToolBar { border: none; }")
        right_toolbar.setStyleSheet("QToolBar { border: none; }")

        # 定義左右兩側的按鈕
        left_actions = ['Zoom', 'Back', 'Forward']
        right_actions = ['Home', 'Pan']

        # 將按鈕分配到左右工具欄，並移除原始工具欄中的按鈕
        for action in self.track_toolbar.actions():
            if action.text() in left_actions + right_actions:
                if action.text() in left_actions:
                    left_toolbar.addAction(action)
                else:
                    right_toolbar.addAction(action)
            
            # 從原始工具欄中移除所有按鈕
            self.track_toolbar.removeAction(action)

            # 特別處理 Home 按鈕的事件
            if action.text() == 'Home':
                action.triggered.disconnect()
                action.triggered.connect(self._track_home)

        # 修改 track_content_layout 的內容
        track_content_layout.addWidget(left_toolbar)
        track_content_layout.addWidget(self.track_canvas)
        track_content_layout.addWidget(right_toolbar)
        
        # 將水平布局添加到主布局
        track_plot_layout.addLayout(track_content_layout)
        
        # 設置軌跡圖的基本屬性
        self.track_ax.set_title(" ", fontsize=8)
        self.track_ax.grid(True)
        self.track_ax.set_aspect('equal', adjustable='datalim')  #
        
        # 修改：使用正確的事件連接方式
        self.track_canvas.mpl_connect('button_press_event', self._on_track_click)
        
        # 初始化追蹤點
        self.track_point = None
        
        # 設置底部區域的寬度比例（左側列表:右側軌跡圖 = 1:2）
        bottom_layout.addWidget(self.check_list, 1)
        bottom_layout.addWidget(track_plot_container, 2)
        
        # 設置底部區域的高度（整體高度的1/3）
        bottom_widget = QWidget()
        bottom_widget.setLayout(bottom_layout)
        
        main_layout.addWidget(bottom_widget)
        main_layout.setStretch(1, 2)  # 主圖表區域佔2
        main_layout.setStretch(2, 1)  # 底部區域佔1

    def on_item_changed(self, item):
        """處理列表項勾選狀態變化"""
        try:
            # 獲取項目數據
            item_data = item.data(Qt.UserRole)
            if not item_data:
                return
            
            # 解析起始和結束索引
            description = item_data['description']
            indices = {}
            for pair in description.split(','):
                key, value = pair.split(':')
                indices[key] = int(value)
            
            start_index = indices['start_index']
            end_index = indices['end_index']
            
            if item.checkState() == Qt.Checked:
                # 當項目被勾選時，在主圖表上標示範圍
                self.plot_manager.highlight_range(start_index, end_index, item_data['id'])
            else:
                # 當項目取消勾選時，移除對應的範圍標示
                self.plot_manager.remove_range_highlight(item_data['id'])
            
            # 重繪圖表
            self.canvas.draw()
            
        except Exception as e:
            print(f"處理列表項變化時出錯: {str(e)}")

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
        
        self.set_start_button = QPushButton("設定起點")
        
        # 設置按鈕樣式
        for button in [self.load_button, self.set_start_button, self.update_button]:
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
        button_group.addWidget(self.set_start_button)
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
        
        # 連接設定起點按鈕信號
        self.set_start_button.clicked.connect(self.start_setting_start_point)
        self.is_setting_start_point = False
        
        print("控制面板設置完成：按鈕已添加到布局")

    def _setup_plot_area(self):
        """設置圖表區域"""
        # 創建右側主布局
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        
        # 創建上方主圖表容器
        main_plot_container = QWidget()
        main_plot_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """)
        main_plot_layout = QVBoxLayout(main_plot_container)
        main_plot_layout.setContentsMargins(10, 10, 10, 10)
        
        # 創建主圖表
        self.figure = Figure(figsize=(8, 8))  # 調整主圖表大小
        self.canvas = FigureCanvas(self.figure)
        main_plot_layout.addWidget(self.canvas)
        
        # 創建底部位置軌跡圖容器
        track_plot_container = QWidget()
        track_plot_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """)
        track_plot_layout = QVBoxLayout(track_plot_container)
        track_plot_layout.setContentsMargins(10, 10, 10, 10)
        
        # 創建位置軌跡圖
        self.track_figure = Figure(figsize=(8, 4))  # 調整軌跡圖大小
        self.track_ax = self.track_figure.add_subplot(111)
        self.track_canvas = FigureCanvas(self.track_figure)
        track_plot_layout.addWidget(self.track_canvas)
        
        # 添加到右側布局
        right_layout.addWidget(main_plot_container, stretch=2)  # 主圖表佔2
        right_layout.addWidget(track_plot_container, stretch=1)  # 軌跡圖佔1
        
        # 添加到右側面板
        self.right_layout.addWidget(right_container)
        
        # 創建圖表管理器並設置回調
        self.plot_manager = PlotManager(self.figure)
        self.plot_manager.set_click_callback(self._on_plot_clicked)
        
        # 連接軌跡圖的點擊事件
        self.track_canvas.mpl_connect('button_press_event', self._on_track_click)

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
        
        # 在添加新範圍組後更新列表
        self.update_range_list()

    def delete_range_group(self, container, group_id):
        """刪除範圍組"""
        # 從界面移除
        container.deleteLater()
        
        # 從列表中移除
        self.range_groups = [g for g in self.range_groups if g['id'] != group_id]
        
        # 在刪除範圍組後更新列表
        self.update_range_list()

    def update_data_range(self):
        """更新數據範圍"""
        try:
            if not hasattr(self, 'full_data'):
                print("錯誤：沒有載入數據")
                QMessageBox.warning(self, "警告", "請先載入數據")
                return
            
            # 清除所有標示點
            if hasattr(self, 'track_point') and self.track_point:
                self.track_point.remove()
                self.track_point = None
            
            # 清除起點標記和高亮點
            self.plot_manager.clear_all_markers()  # 新增方法調用
            
            # 清除列表
            self.check_list.clear()
            
            # 更新圖表
            self.plot_manager.data_list = [self.full_data]  # 使用完整數據
            self.plot_manager.create_plots()
            
            # 確保重新繪製所有圖表
            self.canvas.draw()
            self.track_canvas.draw()
            self._update_track_ax()
            print("圖表更新完成")
            
        except Exception as e:
            print(f"更新圖表時出錯: {str(e)}")
            QMessageBox.critical(self, "錯誤", f"更新圖表時出錯：{str(e)}")

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
        """計算時間差"""
        try:
            if not hasattr(self, 'full_data') or 'Time' not in self.full_data.columns:
                return "時間: 無時間數據"
            
            # 計算時間差
            start_time = pd.to_datetime(self.full_data['Time'].iloc[0])
            end_time = pd.to_datetime(self.full_data['Time'].iloc[-1])
            time_diff = end_time - start_time
            
            # 格式化時間差
            hours = time_diff.total_seconds() // 3600
            minutes = (time_diff.total_seconds() % 3600) // 60
            seconds = time_diff.total_seconds() % 60
            
            return f"時間: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
            
        except Exception as e:
            print(f"計算時間差時出錯: {str(e)}")
            return "時間: 計算錯誤"

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
            print(f"載入數據總長度: {len(self.full_data)} 筆")
            
            # 更新主圖表（三個垂直子圖）
            self.plot_manager.data_list = [self.full_data]
            self.plot_manager.create_plots()
            self.canvas.draw()
            
            # 更新位置軌跡圖（底部右方）
            self.plot_track()
            
            # 保存初始視圖狀態
            self.track_home_limits = {
                'xlim': self.track_ax.get_xlim(),
                'ylim': self.track_ax.get_ylim(),
                'aspect': self.track_ax.get_aspect()
            }
            
            # 更新工具欄並重新綁定 home 按鈕事件
            for action in self.track_toolbar.actions():
                if action.text() == 'Home':
                    try:
                        action.triggered.disconnect()
                    except TypeError:
                        pass  # 如果沒有連接的信號，忽略錯誤
                    action.triggered.connect(self._track_home)
            
            self.track_canvas.draw()
            
            print("已設置初始視圖範圍：", self.track_home_limits)
            
            # 在載入數據後更新時間顯示
            self._calculate_time_difference()
            
            # 新增：更新布局
            self.track_figure.tight_layout()
            
            print("=== CSV 文件載入完成 ===\n")
            
        except Exception as e:
            print(f"載入 CSV 文件時出錯: {str(e)}")
            QMessageBox.critical(self, "錯誤", f"無法載入文件：{str(e)}")

    def resizeEvent(self, event):
        """窗口大小改變時調整遮罩層"""
        super().resizeEvent(event)
        if hasattr(self, 'overlay'):
            self.overlay.resize(self.central_widget.size())

    def _on_plot_clicked(self, index):
        """處理主圖表點擊回調"""
        try:
            # 清除舊的標記點並更新軌跡圖
            self.plot_manager.update_track_point(index, self.track_ax, self.track_canvas)
            print(f"已更新軌跡圖上的點 class name _on_plot_clicked")
        except Exception as e:
            print(f"處理主圖表點擊回調時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

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

    def start_setting_start_point(self):
        """開始設定起點模式"""
        if self.plot_manager.has_start_point():
            # UI 相關邏輯保留在 MapViewer
            reply = QMessageBox.warning(
                self,
                "警告",
                "確定要重新設定起點位置嗎？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
        
            # 清除軌跡圖上的起點標記
            self.plot_manager.clear_start_point()
            self.track_canvas.draw()  # 立即更新軌跡圖顯示
        
        # UI 狀態管理
        self.is_setting_start_point = True
        self.set_start_button.setText("請在位置軌跡圖上選擇起點")
        # 委託 PlotManager 處理數據相關操作
        self.plot_manager.enable_start_point_selection()

    def _on_track_click(self, event):
        """處理軌跡圖點擊事件"""
        if event.inaxes != self.track_ax or not hasattr(self, 'full_data'):
            return
        
        try:
            # 委託 PlotManager 處理數據相關操作
            nearest_idx = self.plot_manager.find_nearest_point(event.xdata, event.ydata)
            if nearest_idx is None:
                return
            
            # 獲取點擊位置的經緯度
            x_col = 'X' if 'X' in self.full_data.columns else 'Longitude'
            y_col = 'Y' if 'Y' in self.full_data.columns else 'Latitude'
            x = self.full_data[x_col].iloc[nearest_idx]
            y = self.full_data[y_col].iloc[nearest_idx]
            
            if self.is_setting_start_point:
                # 委託 PlotManager 處理數據相關操作
                self.plot_manager.set_start_point(nearest_idx, self.track_ax, self.track_canvas)
                # UI 狀態管理保留在 MapViewer
                self.is_setting_start_point = False
                self.set_start_button.setText("設定起點")
                print(f"已在軌跡圖上設定起點:")
                print(f"索引: {nearest_idx}")
                print(f"經度: {x:.6f}")
                print(f"緯度: {y:.6f}")
            else:
                # 委託 PlotManager 處理數據相關操作
                self.plot_manager.update_track_point(nearest_idx, self.track_ax, self.track_canvas)
                print(f"已更新軌跡圖上的點 def name : _on_track_click ")
                print(f"已更新顯示位置:")
                print(f"索引: {nearest_idx}")
                print(f"經度: {x:.6f}")
                print(f"緯度: {y:.6f}")

        except Exception as e:
            print(f"處理軌跡圖點擊時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def update_range_list(self, ranges):
        """更新範圍列表"""
        self.check_list.clear()
        for range_info in ranges:
            # 創建列表項，格式：範圍1, 時間 00:00:00
            item_text = f"Run{range_info['range_number']}, 時間 {range_info['duration_str']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, {"id": range_info['range_number'], "description": f"start_index:{range_info['start_index']},end_index:{range_info['end_index']}"})
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.check_list.addItem(item)
            
    def update_map(self):
        """更新地圖顯示"""
        try:
            print(f"[DEBUG] Function name: update_map")
            # 清除已設定的起點
            self.plot_manager.clear_start_point()
            
            # 獲取選擇的數據範圍
            selected_range = self.range_combo.currentText()
            if selected_range == "全部":
                start_idx = 0
                end_idx = len(self.full_data)
            else:
                # 解析選擇的範圍（格式如 "0-100"）
                start_str, end_str = selected_range.split('-')
                start_idx = int(start_str)
                end_idx = int(end_str)
            
            # 更新數據和圖表
            selected_data = self.full_data.iloc[start_idx:end_idx].copy()
            self.plot_manager.update_data([selected_data])
            self.plot_manager.create_plots()
            
            print(f"已更新地圖顯示，範圍: {start_idx} - {end_idx}")
            
        except Exception as e:
            print(f"更新地圖時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def set_start_point(self, event):
        """設定起點"""
        try:
            if not hasattr(self, 'full_data'):
                QMessageBox.warning(self, "警告", "請先載入數據")
                return
            
            # 清除所有現有標記
            self.plot_manager.clear_all_markers()
            
            # 獲取點擊位置的座標
            x, y = event.xdata, event.ydata
            if x is None or y is None:
                return
            
            # 設置新的起點
            self.plot_manager.set_start_point(x, y)
            self.canvas.draw()
            self.track_canvas.draw()
            
        except Exception as e:
            print(f"設定起點時出錯: {str(e)}")
            QMessageBox.critical(self, "錯誤", f"設定起點時出錯：{str(e)}")

    def update_data_list(self, new_data_list):
        """更新數據列表"""
        try:
            # 清除所有標記
            self.plot_manager.clear_all_markers()
            
            # 更新數據列表
            self.plot_manager.data_list = new_data_list
            self.plot_manager.create_plots()
            
            # 重繪圖表
            self.canvas.draw()
            self.track_canvas.draw()
            
        except Exception as e:
            print(f"更新數據列表時出錯: {str(e)}")
            QMessageBox.critical(self, "錯誤", f"更新數據列表時出錯：{str(e)}")

    def _track_home(self):
        """回到軌跡圖的初始視圖"""
        try:
            if self.track_home_limits:
                print("正在重置視圖到初始狀態...")
                self.track_ax.set_xlim(self.track_home_limits['xlim'])
                self.track_ax.set_ylim(self.track_home_limits['ylim'])
                self.track_ax.set_aspect(self.track_home_limits['aspect'])
                self.track_canvas.draw()
                print("視圖重置完成")
            else:
                print("沒有保存的初始視圖範圍")
        except Exception as e:
            print(f"重置視圖時出錯: {str(e)}")

    def switch_lap(self):
        """切換單圈功能"""
        try:
            checked_items = []
            checked_ids = []  # 新增: 儲存已勾選項目的ID
            
            # 收集已勾選的項目和ID
            for i in range(self.check_list.count()):
                item = self.check_list.item(i)
                if item.checkState() == Qt.Checked:
                    item_data = item.data(Qt.UserRole)
                    checked_items.append(item_data)
                    checked_ids.append(item_data['id'])  # 儲存項目ID
            
            if checked_items:
                # 更新軌跡圖標題
                print(f"debug checked_items:{checked_items}")
                if len(checked_ids) == 1:
                    self.track_ax.set_title(f"範圍 {checked_ids[0]} 軌跡圖", fontsize=12)
                else:
                    id_str = ', '.join(str(id) for id in checked_ids)
                    self.track_ax.set_title(f"範圍 {id_str} 軌跡圖", fontsize=12)
                
                # 使用 plot_manager 繪製圖表
                # 重新排序 checked_items,讓第一個選的範圍在最後繪製
                #checked_items.reverse()
                success = self.plot_manager.plot_selected_ranges(
                    checked_items,
                    self.full_data, 
                    self.axes,
                    self.canvas,
                    self.track_ax,
                    self.track_canvas
                )
                
                if success:
                    print("\n=== 已重繪範圍 ===")
                    for id in checked_ids:
                        print(f"範圍 {id}")
                else:
                    QMessageBox.warning(self, "警告", "繪製圖表時發生錯誤")
            else:
                print("沒有勾選任何範圍")
                QMessageBox.warning(self, "警告", "請先勾選要顯示的範圍")
            
        except Exception as e:
            print(f"切換單圈時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "錯誤", f"切換單圈時出錯：{str(e)}")

    def _update_track_ax(self):
        """更新軌跡圖"""
        self.plot_track()   

    def plot_track(self):
        """繪製位置軌跡圖"""
        self.track_ax.clear()
        
        if 'X' in self.full_data.columns and 'Y' in self.full_data.columns:
            print("繪製位置軌跡圖 (X-Y)")
            x_data, y_data = self.full_data['X'], self.full_data['Y']
            x_label, y_label = 'X', 'Y'
        elif 'Longitude' in self.full_data.columns and 'Latitude' in self.full_data.columns:
            print("繪製位置軌跡圖 (經緯度)")
            x_data, y_data = self.full_data['Longitude'], self.full_data['Latitude']
            x_label, y_label = '經度', '緯度'
        else:
            print("數據中無法找到合適的 X-Y 或 經緯度 列")
            return  # 若無合適數據則不繪製

        # 繪製軌跡圖
        self.track_ax.plot(x_data, y_data, 'b-', linewidth=1.5, zorder=1)
        self.track_ax.set_xlabel(x_label, fontsize=10)
        self.track_ax.set_ylabel(y_label, fontsize=10)
        self.track_ax.set_title("位置軌跡圖", fontsize=8)
        self.track_ax.grid(True)
        self.track_ax.set_aspect('equal', adjustable='datalim')

        # 設置適當的邊距
        x_min, x_max = x_data.min(), x_data.max()
        y_min, y_max = y_data.min(), y_data.max()
        margin_x = (x_max - x_min) * 0.1
        margin_y = (y_max - y_min) * 0.1

        # 設置軸範圍
        self.track_ax.set_xlim(x_min - margin_x, x_max + margin_x)
        self.track_ax.set_ylim(y_min - margin_y, y_max + margin_y)
        
        self.track_canvas.draw()
