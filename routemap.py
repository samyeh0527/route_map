import pandas as pd
import os
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QPushButton, QFileDialog, QHBoxLayout, QTableWidget, 
                            QTableWidgetItem, QLabel, QSpinBox, QMessageBox, QFrame)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import matplotlib
from PyQt5.QtGui import QColor
import matplotlib.pyplot as plt
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtCore import Qt

# 設置中文字體
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False

class DataProcessor(QThread):
    """數據處理線程"""
    finished = pyqtSignal(pd.DataFrame)
    error = pyqtSignal(str)

    def __init__(self, full_data, start_idx, end_idx):
        super().__init__()
        self.full_data = full_data
        self.start_idx = start_idx
        self.end_idx = end_idx

    def run(self):
        """執行數據處理"""
        try:
            print(f"處理數據範圍: {self.start_idx} 到 {self.end_idx}")
            # 根據索引範圍選擇數據
            updated_data = self.full_data.iloc[self.start_idx:self.end_idx].copy()
            # 重置索引
            updated_data.reset_index(drop=True, inplace=True)
            print("數據處理完成")
            # 發送處理完成信號
            self.finished.emit(updated_data)
        except Exception as e:
            print(f"數據處理錯誤: {str(e)}")
            # 發送錯誤信號
            self.error.emit(str(e))

class PlotManager:
    """圖表管理器"""
    def __init__(self, figure):
        self.figure = figure
        self.data_list = []
        self.axes = {}
        self.cached_plots = {
            'r_scale1': {'line': None, 'highlight_line': None, 'highlight_point': None},
            'r_scale2': {'line': None, 'highlight_line': None, 'highlight_point': None},
            'speed': {'line': None, 'highlight_line': None, 'highlight_point': None},
            'position': {'line': None, 'highlight_lines': None, 'highlight_point': None}
        }
        self.colors = ['b', 'g', 'r', 'm', 'c', 'y', 'k']
        
        # 添加點擊事件處理
        self.figure.canvas.mpl_connect('button_press_event', self._on_plot_click)
        self.click_callback = None  # 用於存儲回調函數

    def create_plots(self, highlight_index=None, highlight_range=None):
        """創建圖表，支持高亮顯示"""
        try:
            print("\n=== 開始創建圖表 ===")
            if not self.data_list:
                print("錯誤: 沒有數據")
                return
            
            self.figure.clear()
            
            # 修改為4行1列的布局，並設置不同區域的間距
            gs = self.figure.add_gridspec(4, 1, 
                                        height_ratios=[1, 1, 1, 2], 
                                        hspace=0)  # 將整體間距設為0，後續手動調整
            
            # 調整圖表順序，將高度圖1放在最上方
            self.axes = {
                'r_scale1': self.figure.add_subplot(gs[0, 0]),  # 高度圖1放在最上方
                'r_scale2': self.figure.add_subplot(gs[1, 0]),
                'speed': self.figure.add_subplot(gs[2, 0]),
                'position': self.figure.add_subplot(gs[3, 0])
            }
            
            # 繪製每個圖表
            for ax_name, ax in self.axes.items():
                if ax_name == 'r_scale1':
                    self._plot_data(ax, 'R Scale 1', '高度變化 1')
                elif ax_name == 'r_scale2':
                    self._plot_data(ax, 'R Scale 2', '高度變化 2')
                elif ax_name == 'speed':
                    self._plot_data(ax, 'G Speed', '速度變化')
                elif ax_name == 'position':
                    self._plot_position(ax)
            
            # 如果有高亮點，添加高亮顯示
            if highlight_index is not None and highlight_range is not None:
                if 0 <= highlight_range < len(self.data_list):
                    data = self.data_list[highlight_range]
                    if 0 <= highlight_index < len(data):
                        self._add_highlights(highlight_index, data)
            
            # 調整子圖之間的間距
            self.figure.tight_layout()
            
            # 手動調整各圖表的位置
            # 獲取當前位置
            pos_r_scale1 = self.axes['r_scale1'].get_position()
            pos_r_scale2 = self.axes['r_scale2'].get_position()
            pos_speed = self.axes['speed'].get_position()
            pos_position = self.axes['position'].get_position()
            
            # 調整上面三個圖表，使其緊密相連
            self.axes['r_scale2'].set_position([
                pos_r_scale2.x0,
                pos_r_scale2.y0 + 0.02,  # 稍微上移
                pos_r_scale2.width,
                pos_r_scale2.height
            ])
            
            self.axes['speed'].set_position([
                pos_speed.x0,
                pos_speed.y0 + 0.02,  # 稍微上移
                pos_speed.width,
                pos_speed.height
            ])
            
            # 調整位置軌跡圖，增加與速度圖的間距
            self.axes['position'].set_position([
                pos_position.x0,
                pos_position.y0 - 0.1,  # 增加與速度圖的間距
                pos_position.width,
                pos_position.height
            ])
            
            self.figure.canvas.draw()
            print("\n=== 圖表創建完成 ===")
            
        except Exception as e:
            print(f"\n!!! 創建圖表時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def _plot_data(self, ax, column_name, title):
        """繪製數據到指定軸"""
        if not self.data_list:
            return
            
        for i, data in enumerate(self.data_list):
            if column_name in data.columns:
                color = self.colors[i % len(self.colors)]
                ax.plot(data.index, data[column_name], 
                       color=color, 
                       label=f'第{i+1}段',
                       linewidth=1.5)
        
        ax.set_title(title, fontsize=10)
        
        # 只在速度圖表顯示X軸標籤
        if column_name == 'G Speed':
            ax.set_xlabel('數據點', fontsize=9)
        else:
            # 隱藏X軸標籤和刻度
            ax.set_xticklabels([])
            ax.tick_params(axis='x', length=0)
        
        ax.set_ylabel(column_name, fontsize=9)
        ax.grid(True)
        if ax.get_lines():  # 只在有數據時顯示圖例
            ax.legend()

    def _plot_position(self, ax):
        """繪製位置軌跡"""
        if not self.data_list:
            return
            
        for i, data in enumerate(self.data_list):
            if 'Longitude' in data.columns and 'Latitude' in data.columns:
                color = self.colors[i % len(self.colors)]
                ax.plot(data['Longitude'], data['Latitude'], 
                       color=color, 
                       label=f'第{i+1}段',
                       linewidth=1.5)
        
        ax.set_title('位置軌跡', fontsize=10)
        ax.set_xlabel('經度', fontsize=9)
        ax.set_ylabel('緯度', fontsize=9)
        ax.grid(True)
        if ax.get_lines():  # 只在有數據時顯示圖例
            ax.legend()

    def _create_initial_plots(self):
        """創建初始圖表"""
        self._create_r_scales()
        self._create_speed_plot()
        self._create_position_plot()

    def _create_r_scales(self):
        """創建R Scale圖表"""
        for scale, ax_key in [('R Scale 1', 'r_scale1'), ('R Scale 2', 'r_scale2')]:
            if scale in self.data_list[0].columns:
                ax = self.axes[ax_key]
                ax.clear()  # 清除舊圖表
                
                line, = ax.plot(self.data_list[0].index, self.data_list[0][scale], 'b-')
                self.cached_plots[ax_key]['line'] = line
                
                ax.set_title(f'{scale} 變化', fontsize=10)
                ax.set_xlabel('數據點', fontsize=9)
                ax.set_ylabel(scale, fontsize=9)
                ax.grid(True)
                
                # 設置適當的Y軸範圍
                y_min = self.data_list[0][scale].min()
                y_max = self.data_list[0][scale].max()
                margin = (y_max - y_min) * 0.1
                ax.set_ylim(y_min - margin, y_max + margin)
                
                # 設置X軸範圍
                ax.set_xlim(self.data_list[0].index[0], self.data_list[0].index[-1])

    def _create_speed_plot(self):
        """創建速度圖表"""
        if 'G Speed' in self.data_list[0].columns:
            ax = self.axes['speed']
            ax.clear()  # 清除舊圖表
            
            line, = ax.plot(self.data_list[0].index, self.data_list[0]['G Speed'], 'g-')
            self.cached_plots['speed']['line'] = line
            
            ax.set_title('速度變化', fontsize=10)
            ax.set_xlabel('數據點', fontsize=9)
            ax.set_ylabel('速度 (km/h)', fontsize=9)
            ax.grid(True)
            
            # 設置適當的Y軸範圍
            y_min = self.data_list[0]['G Speed'].min()
            y_max = self.data_list[0]['G Speed'].max()
            margin = (y_max - y_min) * 0.1
            ax.set_ylim(y_min - margin, y_max + margin)
            
            # 設置X軸範圍
            ax.set_xlim(self.data_list[0].index[0], self.data_list[0].index[-1])

    def _create_position_plot(self):
        """創建位置軌跡圖"""
        ax = self.axes['position']
        ax.clear()  # 清除舊圖表
        
        line, = ax.plot(self.data_list[0]['Longitude'], self.data_list[0]['Latitude'], 
                       'b-', linewidth=0.5)
        scatter = ax.scatter(self.data_list[0]['Longitude'], self.data_list[0]['Latitude'], 
                           c='blue', s=20, picker=True)
        
        self.cached_plots['position']['line'] = line
        self.cached_plots['position']['scatter'] = scatter
        
        self._setup_position_axes(ax)
        
        # 設置適當的軸範圍
        lon_min, lon_max = self.data_list[0]['Longitude'].min(), self.data_list[0]['Longitude'].max()
        lat_min, lat_max = self.data_list[0]['Latitude'].min(), self.data_list[0]['Latitude'].max()
        
        # 計算邊距
        lon_margin = (lon_max - lon_min) * 0.1
        lat_margin = (lat_max - lat_min) * 0.1
        
        # 設置範圍
        ax.set_xlim(lon_min - lon_margin, lon_max + lon_margin)
        ax.set_ylim(lat_min - lat_margin, lat_max + lat_margin)

    def _update_highlights(self, highlight_index):
        """更新高亮顯示"""
        # 移除舊的高亮
        self._remove_old_highlights()
        
        if highlight_index is not None:
            self._add_new_highlights(highlight_index)

    def _remove_old_highlights(self):
        """移除舊的高亮顯示"""
        for plot_cache in self.cached_plots.values():
            # 清除高亮線
            if plot_cache.get('highlight_line'):
                plot_cache['highlight_line'].remove()
                plot_cache['highlight_line'] = None
            
            # 清除高亮點
            if plot_cache.get('highlight_point'):
                if isinstance(plot_cache['highlight_point'], (list, tuple)):
                    for artist in plot_cache['highlight_point']:
                        artist.remove()
                else:
                    plot_cache['highlight_point'].remove()
                plot_cache['highlight_point'] = None
            
            # 特別處理位置軌跡圖的十字線
            if plot_cache.get('highlight_lines'):
                for line in plot_cache['highlight_lines']:
                    if line:  # 確保線條對象存在
                        line.remove()
                plot_cache['highlight_lines'] = None

        # 強制更新畫布
        self.figure.canvas.draw_idle()

    def _add_new_highlights(self, index):
        """添加新的高亮顯示"""
        for scale, ax_key in [('R Scale 1', 'r_scale1'), 
                            ('R Scale 2', 'r_scale2'), 
                            ('Speed', 'speed')]:
            if scale == 'Speed':
                if 'G Speed' in self.data_list[0].columns:
                    self._add_highlight_to_plot(ax_key, index, scale)
            elif scale in self.data_list[0].columns:
                self._add_highlight_to_plot(ax_key, index, scale)

        self._add_position_highlight(index)

    def _add_highlight_to_plot(self, ax_key, index, data_key):
        """為單個圖表添加高亮"""
        ax = self.axes[ax_key]
        cache = self.cached_plots[ax_key]
        
        # 處理速度圖表的特殊情況
        if data_key == 'Speed':
            data_key = 'G Speed'  # 使用 'G Speed' 而不是 'Speed'
        
        # 添加垂直線
        line = ax.axvline(x=index, color='r', linestyle='--', zorder=3)
        point = ax.plot(index, self.data_list[0][data_key].iloc[index], 
                       'ro', markersize=6, zorder=4)[0]
        
        cache['highlight_line'] = line
        cache['highlight_point'] = point

    def _add_position_highlight(self, index):
        """為位置軌跡圖添加高亮"""
        ax = self.axes['position']
        cache = self.cached_plots['position']
        
        # 確保先清除舊的高亮
        if cache.get('highlight_lines'):
            for line in cache['highlight_lines']:
                if line:
                    line.remove()
        if cache.get('highlight_point'):
            cache['highlight_point'].remove()
        
        current_lon = self.data_list[0]['Longitude'].iloc[index]
        current_lat = self.data_list[0]['Latitude'].iloc[index]
        
        # 添加新的十字線
        vline = ax.axvline(x=current_lon, color='r', linestyle='--', alpha=0.5, zorder=3)
        hline = ax.axhline(y=current_lat, color='r', linestyle='--', alpha=0.5, zorder=3)
        point = ax.scatter([current_lon], [current_lat], 
                         c='red', s=50, zorder=4)
        
        # 保存新的高亮對象
        cache['highlight_lines'] = [vline, hline]
        cache['highlight_point'] = point

    def _setup_subplots(self, gs):
        """設置子圖"""
        return {
            'r_scale1': self.figure.add_subplot(gs[0, 0]),
            'r_scale2': self.figure.add_subplot(gs[1, 0]),
            'speed': self.figure.add_subplot(gs[2, 0]),
            'position': self.figure.add_subplot(gs[3, 0])
        }

    def _adjust_layout(self):
        """調整布局"""
        # 自動調整子圖之間的間距
        self.figure.tight_layout()
        
        # 為X軸標籤預留足夠空間
        self.figure.subplots_adjust(bottom=0.15, right=0.95, top=0.95)

    def _setup_position_axes(self, ax):
        """設置位置軌跡圖的軸"""
        ax.set_title('位置軌跡', fontsize=10)
        ax.set_xlabel('經度', fontsize=9)
        ax.set_ylabel('緯度', fontsize=9)
        ax.grid(True)
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        ax.xaxis.set_major_locator(plt.MaxNLocator(6))
        ax.yaxis.set_major_locator(plt.MaxNLocator(8))
        ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.4f'))
        ax.yaxis.set_major_formatter(plt.FormatStrFormatter('%.4f'))

    def _on_plot_click(self, event):
        """處理圖表點擊事件"""
        if event.inaxes is None or self.click_callback is None or not self.data_list:
            return
            
        try:
            print("\n=== 處理圖表點擊 ===")
            print(f"點擊座標: x={event.xdata}, y={event.ydata}")
            
            # 獲取點擊的軸對象
            clicked_ax = event.inaxes
            
            # 對於位置圖的特殊處理
            if clicked_ax == self.axes['position']:
                # 找到最近的點
                min_distance = float('inf')
                nearest_range = 0
                nearest_idx = 0
                
                for range_idx, data in enumerate(self.data_list):
                    if len(data) == 0 or 'Longitude' not in data.columns or 'Latitude' not in data.columns:
                        continue
                        
                    distances = np.sqrt(
                        (data['Longitude'] - event.xdata) ** 2 + 
                        (data['Latitude'] - event.ydata) ** 2
                    )
                    
                    current_min_idx = distances.argmin()
                    current_min_distance = distances[current_min_idx]
                    
                    if current_min_distance < min_distance:
                        min_distance = current_min_distance
                        nearest_range = range_idx
                        nearest_idx = current_min_idx
                
                print(f"位置圖最近點: 範圍={nearest_range}, 索引={nearest_idx}")
                self.click_callback(nearest_range, nearest_idx)
                
            # 對於其他圖表的處理
            else:
                # 找到點擊的是哪個圖表
                for ax_name, ax in self.axes.items():
                    if ax == clicked_ax:
                        print(f"點擊的圖表: {ax_name}")
                        # 找到最近的數據點
                        clicked_x = event.xdata
                        min_distance = float('inf')
                        nearest_range = 0
                        nearest_idx = 0
                        
                        for range_idx, data in enumerate(self.data_list):
                            if len(data) == 0:
                                continue
                                
                            # 使用數據索引作為 x 座標
                            distances = np.abs(np.arange(len(data)) - clicked_x)
                            current_min_idx = distances.argmin()
                            current_min_distance = distances[current_min_idx]
                            
                            if current_min_distance < min_distance:
                                min_distance = current_min_distance
                                nearest_range = range_idx
                                nearest_idx = current_min_idx
                        
                        print(f"找到最近點: 範圍={nearest_range}, 索引={nearest_idx}")
                        self.click_callback(nearest_range, nearest_idx)
                        break
                
        except Exception as e:
            print(f"處理圖表點擊時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def set_click_callback(self, callback):
        """設置點擊回調函數"""
        self.click_callback = callback

    def _add_highlights(self, index, data):
        """添加高亮顯示"""
        try:
            # 為每個圖表添加高亮
            if 'R Scale 1' in data.columns:
                self._add_highlight_to_plot('r_scale1', index, data['R Scale 1'].iloc[index])
            if 'R Scale 2' in data.columns:
                self._add_highlight_to_plot('r_scale2', index, data['R Scale 2'].iloc[index])
            if 'G Speed' in data.columns:
                self._add_highlight_to_plot('speed', index, data['G Speed'].iloc[index])
            if all(col in data.columns for col in ['Longitude', 'Latitude']):
                self._add_position_highlight(index, data)
                
        except Exception as e:
            print(f"添加高亮顯示時出錯: {str(e)}")

    def _add_highlight_to_plot(self, ax_name, index, value):
        """為單個圖表添加高亮"""
        ax = self.axes[ax_name]
        # 添加垂直線和點
        ax.axvline(x=index, color='r', linestyle='--', alpha=0.5)
        ax.plot(index, value, 'ro', markersize=8)

    def _add_position_highlight(self, index, data):
        """為位置軌跡圖添加高亮"""
        ax = self.axes['position']
        lon = data['Longitude'].iloc[index]
        lat = data['Latitude'].iloc[index]
        
        # 清除之前的高亮
        if self.cached_plots['position'].get('highlight_lines'):
            for line in self.cached_plots['position']['highlight_lines']:
                if line:
                    line.remove()
        if self.cached_plots['position'].get('highlight_point'):
            self.cached_plots['position']['highlight_point'].remove()
        if self.cached_plots['position'].get('annotation'):
            self.cached_plots['position']['annotation'].remove()
        
        # 添加十字線
        vline = ax.axvline(x=lon, color='r', linestyle='--', alpha=0.5)
        hline = ax.axhline(y=lat, color='r', linestyle='--', alpha=0.5)
        
        # 添加高亮點
        point = ax.scatter([lon], [lat], c='red', s=100, zorder=5)
        
        # 添加數據標註
        annotation_text = f'經度: {lon:.6f}\n緯度: {lat:.6f}'
        if 'G Speed' in data.columns:
            annotation_text += f'\n速度: {data["G Speed"].iloc[index]:.1f} km/h'
        if 'Time' in data.columns:
            time_str = str(data['Time'].iloc[index])
            annotation_text += f'\n時間: {time_str}'
        
        annotation = ax.annotate(
            annotation_text,
            xy=(lon, lat),
            xytext=(10, 10),
            textcoords='offset points',
            bbox=dict(
                boxstyle='round,pad=0.5',
                fc='yellow',
                alpha=0.7,
                ec='r'
            ),
            zorder=6
        )
        
        # 保存高亮對象以便後續清除
        self.cached_plots['position']['highlight_lines'] = [vline, hline]
        self.cached_plots['position']['highlight_point'] = point
        self.cached_plots['position']['annotation'] = annotation
        
        # 更新畫布
        self.figure.canvas.draw_idle()

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

class MapViewer(QMainWindow):
    """主窗口類"""
    def __init__(self):
        super().__init__()
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
        
        # 創建輸入區域
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)
        
        # 起始值
        start_container = QWidget()
        start_layout = QVBoxLayout(start_container)
        start_layout.setContentsMargins(0, 0, 0, 0)
        start_layout.setSpacing(2)
        
        start_label = QLabel("起始位置")
        start_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        
        start_spin = QSpinBox()
        start_spin.setButtonSymbols(QSpinBox.NoButtons)
        start_spin.setRange(0, 99999)
        start_spin.setStyleSheet("""
            QSpinBox {
                background-color: #f8f9fa;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 100px;
            }
            QSpinBox:focus {
                border-color: #80bdff;
                background-color: white;
            }
        """)
        
        start_layout.addWidget(start_label)
        start_layout.addWidget(start_spin)
        
        # 結束值
        end_container = QWidget()
        end_layout = QVBoxLayout(end_container)
        end_layout.setContentsMargins(0, 0, 0, 0)
        end_layout.setSpacing(2)
        
        end_label = QLabel("結束位置")
        end_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        
        end_spin = QSpinBox()
        end_spin.setButtonSymbols(QSpinBox.NoButtons)
        end_spin.setRange(0, 99999)
        end_spin.setStyleSheet("""
            QSpinBox {
                background-color: #f8f9fa;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 100px;
            }
            QSpinBox:focus {
                border-color: #80bdff;
                background-color: white;
            }
        """)
        
        end_layout.addWidget(end_label)
        end_layout.addWidget(end_spin)
        
        # 設置最大值和預設值（如果已有數據）
        if hasattr(self, 'full_data'):
            max_value = len(self.full_data) - 1  # 最後一筆索引
            start_spin.setMaximum(max_value)
            end_spin.setMaximum(max_value)
            
            # 獲取前一個範圍組的結束值作為預設值
            if group_id > 0 and self.range_groups:
                prev_end_value = self.range_groups[-1]['end_spin'].value()
                end_spin.setValue(prev_end_value)
            else:
                end_spin.setValue(max_value)  # 第一個範圍組預設為最後一筆
        
        # 添加到輸入布局
        input_layout.addWidget(start_container)
        input_layout.addWidget(end_container)
        input_layout.addStretch()
        
        # 添加所有元素到主布局
        range_v_layout.addLayout(title_layout)
        range_v_layout.addLayout(input_layout)
        
        # 保存範圍組
        self.range_groups.append({
            'id': group_id,
            'container': range_container,
            'start_spin': start_spin,
            'end_spin': end_spin,
            'time_label': time_label  # 添加時間標籤到範圍組數據中
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
            
            for group in self.range_groups:
                start = group['start_spin'].value()
                end = group['end_spin'].value()
                
                print(f"範圍 {group['id'] + 1}: {start} 到 {end}")
                
                # 驗證範圍
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
                start = group['start_spin'].value()
                end = group['end_spin'].value()
                
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
                group['start_spin'].setMaximum(max_value)
                group['end_spin'].setMaximum(max_value)
                group['end_spin'].setValue(max_value)  # 所有範圍組的結束位置都預設為最後一筆
            
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
                start = group['start_spin'].value()
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
            start = group['start_spin'].value()
            end = group['end_spin'].value()
            
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

def main():
    app = QApplication(sys.argv)
    viewer = MapViewer()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
