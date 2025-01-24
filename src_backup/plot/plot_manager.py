from matplotlib.figure import Figure
import numpy as np
import matplotlib.pyplot as plt

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
        # 添加縮放事件處理
        self.figure.canvas.mpl_connect('scroll_event', self._on_scroll)
        self.click_callback = None
        self.is_setting_start_point = False
        self.start_point_line = None
        self.start_point = None
        self.has_start_point_set = False
        self.start_point_data = None
        # 設定標記線的長度（1cm）
        self.marker_size_cm = 1.0
        self.info_text = None
        self.crosshair_lines = []  # 儲存十字虛線
        self.value_texts = []  # 新增：儲存所有數值文字對象

    def create_plots(self, highlight_index=None, highlight_range=None):
        """創建圖表，支持高亮顯示"""
        try:
            print("\n=== 開始創建圖表 ===")
            if not self.data_list:
                print("錯誤: 沒有數據")
                return
            
            # 暫存起點資訊
            temp_start_point_data = self.start_point_data if self.has_start_point_set else None
            
            # 清除所有標記
            if self.info_text is not None:
                self.info_text.remove()
                self.info_text = None
            
            for line in self.crosshair_lines:
                line.remove()
            self.crosshair_lines = []
            
            for text_obj in self.value_texts:
                text_obj.remove()
            self.value_texts = []
            
            # 清除圖表但保持起點資訊
            self.figure.clear()
            
            # 設置中文字體
            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 修改為4行1列的布局，並設置不同區域的間距
            gs = self.figure.add_gridspec(4, 1, 
                                        height_ratios=[1, 1, 1, 2], 
                                        hspace=0)  # 將整體間距設為0，後續手動調整
            
            # 調整圖表順序，將速度圖放在最上方
            self.axes = {
                'speed': self.figure.add_subplot(gs[0, 0]),     # 速度圖放在最上方
                'r_scale1': self.figure.add_subplot(gs[1, 0]),  # R Scale 1 放在第二
                'r_scale2': self.figure.add_subplot(gs[2, 0]),  # R Scale 2 放在第三
                'position': self.figure.add_subplot(gs[3, 0])   # 位置圖放在最下方
            }
            
            # 繪製每個圖表
            for ax_name, ax in self.axes.items():
                if ax_name == 'speed':
                    self._plot_data(ax, 'G Speed', '')
                elif ax_name == 'r_scale1':
                    self._plot_data(ax, 'R Scale 1', '')
                elif ax_name == 'r_scale2':
                    self._plot_data(ax, 'R Scale 2', '')
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
                pos_r_scale2.y0 + 0.00,  # 稍微上移
                pos_r_scale2.width,
                pos_r_scale2.height
            ])
            
            self.axes['speed'].set_position([
                pos_speed.x0,
                pos_speed.y0 ,  # 稍微上移
                pos_speed.width,
                pos_speed.height
            ])
            
            # 調整位置軌跡圖，增加與速度圖的間距
            self.axes['position'].set_position([
                pos_position.x0,
                pos_position.y0 -0.04,  # 增加與速度圖的間距
                pos_position.width,
                pos_position.height
            ])
            
            # 如果有起點資訊，重新繪製起點線
            if temp_start_point_data is not None:
                self.start_point_data = temp_start_point_data
                self.has_start_point_set = True
                self._draw_start_point_line()
            
            self.figure.canvas.draw()
            print("\n=== 圖表創建完成 ===")
            
        except Exception as e:
            print(f"創建圖表時出錯: {str(e)}")
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
        if column_name == 'R Scale 2':
            ax.set_xlabel('數據點', fontsize=9)
        else:
            # 隱藏X軸標籤和刻度
            ax.set_xticklabels([])
            ax.tick_params(axis='x', length=0)
        
        ax.set_ylabel(column_name, fontsize=9)
        ax.grid(True)
        if ax.get_lines():  # 只在有數據時顯示圖例
            ax.legend(loc='upper right')  # 將圖例設置在右上角

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
            ax.legend(loc='upper right')  # 將圖例設置在右上角

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
        if event.inaxes is None:
            return

        # 處理起點設定
        if self.is_setting_start_point and event.inaxes == self.axes['position']:
            self._set_start_point(event.xdata, event.ydata)
            self.is_setting_start_point = False
            return
        
        # 處理一般的點擊事件
        try:
            if event.inaxes == self.axes['position']:
                # 找到最近的數據點
                nearest_point = None
                min_distance = float('inf')
                nearest_data = None
                
                for data in self.data_list:
                    if 'Longitude' in data.columns and 'Latitude' in data.columns:
                        distances = ((data['Longitude'] - event.xdata) ** 2 + 
                                   (data['Latitude'] - event.ydata) ** 2) ** 0.5
                        idx = distances.argmin()
                        distance = distances.iloc[idx]
                        
                        if distance < min_distance:
                            min_distance = distance
                            nearest_point = {
                                'longitude': data['Longitude'].iloc[idx],
                                'latitude': data['Latitude'].iloc[idx],
                                'index': idx
                            }
                            if 'G Speed' in data.columns:
                                nearest_point['speed'] = data['G Speed'].iloc[idx]
                            if 'R Scale 1' in data.columns:
                                nearest_point['r_scale1'] = data['R Scale 1'].iloc[idx]
                            if 'R Scale 2' in data.columns:
                                nearest_point['r_scale2'] = data['R Scale 2'].iloc[idx]
                            nearest_data = data
                
                if nearest_point:
                    # 顯示資訊和十字虛線
                    info_text = f"位置: ({nearest_point['longitude']:.6f}, {nearest_point['latitude']:.6f})\n"
                    if 'speed' in nearest_point:
                        info_text += f"速度: {nearest_point['speed']:.2f}\n"
                    if 'r_scale1' in nearest_point:
                        info_text += f"R Scale 1: {nearest_point['r_scale1']:.2f}\n"
                    if 'r_scale2' in nearest_point:
                        info_text += f"R Scale 2: {nearest_point['r_scale2']:.2f}"
                    
                    self._show_info_and_crosshair(
                        nearest_point['longitude'], 
                        nearest_point['latitude'], 
                        info_text,
                        nearest_point['index'],
                        nearest_data
                    )
        
        except Exception as e:
            print(f"處理點擊事件時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def _show_info_and_crosshair(self, x, y, text, index, data):
        """在圖表上顯示資訊和十字虛線"""
        try:
            # 清除舊的資訊文字和十字虛線
            if self.info_text is not None:
                self.info_text.remove()
                self.info_text = None
            
            for line in self.crosshair_lines:
                line.remove()
            self.crosshair_lines = []
            
            # 清除舊的數值文字
            for text_obj in self.value_texts:
                text_obj.remove()
            self.value_texts = []
            
            # 在位置圖上顯示資訊和十字虛線
            ax = self.axes['position']
            self.info_text = ax.text(
                x, y, text,
                bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'),
                verticalalignment='bottom',
                horizontalalignment='right'
            )
            
            # 添加紅色十字虛線到位置圖
            h_line = ax.axhline(y=y, color='red', linestyle='--', alpha=0.5)
            v_line = ax.axvline(x=x, color='red', linestyle='--', alpha=0.5)
            self.crosshair_lines.extend([h_line, v_line])
            
            # 在其他圖表上添加垂直線和數值文字
            for ax_name, ax in self.axes.items():
                if ax_name != 'position':
                    v_line = ax.axvline(x=index, color='red', linestyle='--', alpha=0.5)
                    self.crosshair_lines.append(v_line)
                    
                    # 獲取當前值和圖表標題
                    value = None
                    title = ""
                    if ax_name == 'speed' and 'G Speed' in data.columns:
                        value = data['G Speed'].iloc[index]
                        title = "G Speed"
                    elif ax_name == 'r_scale1' and 'R Scale 1' in data.columns:
                        value = data['R Scale 1'].iloc[index]
                        title = "R Scale 1"
                    elif ax_name == 'r_scale2' and 'R Scale 2' in data.columns:
                        value = data['R Scale 2'].iloc[index]
                        title = "R Scale 2"
                    
                    if value is not None:
                        # 在左上角顯示數值，確保在圖表內部
                        ylim = ax.get_ylim()
                        y_pos = ylim[1] - (ylim[1] - ylim[0]) * 0.05  # 距離頂部5%
                        
                        text_obj = ax.text(
                            0.02, 0.95,  # 使用相對座標（左上角）
                            f'{title}: {value:.2f}',
                            transform=ax.transAxes,  # 使用軸的相對座標系統
                            bbox=dict(
                                facecolor='white',
                                edgecolor='none',
                                alpha=0.8,
                                pad=3
                            ),
                            verticalalignment='top',
                            horizontalalignment='left',
                            zorder=1000  # 確保文字在最上層
                        )
                        self.value_texts.append(text_obj)
            
            # 更新圖表
            self.figure.canvas.draw_idle()
            
        except Exception as e:
            print(f"顯示資訊和十字虛線時出錯: {str(e)}")
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

    def _on_scroll(self, event):
        """處理滾輪縮放事件"""
        try:
            # 確保滾動發生在圖表區域內
            if event.inaxes is None:
                return

            # 獲取當前軸的範圍
            ax = event.inaxes
            x_min, x_max = ax.get_xlim()
            y_min, y_max = ax.get_ylim()
            
            # 設置縮放係數
            base_scale = 1.1
            
            # 根據滾輪方向確定是放大還是縮小
            if event.button == 'up':  # 放大
                scale_factor = 1/base_scale
            else:  # 縮小
                scale_factor = base_scale
            
            # 計算以滑鼠位置為中心的新範圍
            x_center = event.xdata
            y_center = event.ydata
            
            # 計算新的範圍
            new_x_min = x_center - (x_center - x_min) * scale_factor
            new_x_max = x_center + (x_max - x_center) * scale_factor
            new_y_min = y_center - (y_center - y_min) * scale_factor
            new_y_max = y_center + (y_max - y_center) * scale_factor
            
            # 更新軸的範圍
            ax.set_xlim(new_x_min, new_x_max)
            ax.set_ylim(new_y_min, new_y_max)
            
            # 重繪圖表
            self.figure.canvas.draw_idle()
            
        except Exception as e:
            print(f"縮放處理時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def enable_start_point_selection(self):
        """啟用起點選擇模式"""
        self.is_setting_start_point = True
        print("請在位置軌跡圖上選擇起點")

    def _set_start_point(self, x, y):
        """設定起點並繪製垂直標記線"""
        try:
            # 清除舊的起點線（如果存在）
            if self.start_point_line is not None:
                for line in self.start_point_line:
                    line.remove()
                self.start_point_line = None

            # 儲存起點座標和相關資訊
            self.start_point = (x, y)
            self.has_start_point_set = True
            
            # 儲存當前的軸範圍
            ax = self.axes['position']
            self.start_point_data = {
                'x': x,
                'y': y,
                'y_range': abs(ax.get_ylim()[1] - ax.get_ylim()[0]),
                'bbox': ax.get_window_extent().transformed(self.figure.dpi_scale_trans.inverted())
            }

            # 繪製起點線
            self._draw_start_point_line()

            print(f"起點已設定在: 經度={x:.6f}, 緯度={y:.6f}")

        except Exception as e:
            print(f"設定起點時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def _draw_start_point_line(self):
        """繪製起點標記線"""
        if self.start_point_data is None:
            return

        try:
            ax = self.axes['position']
            x, y = self.start_point_data['x'], self.start_point_data['y']
            
            # 計算1cm在數據單位中的長度
            y_range = abs(ax.get_ylim()[1] - ax.get_ylim()[0])
            bbox = ax.get_window_extent().transformed(self.figure.dpi_scale_trans.inverted())
            cm_to_inch = 0.393701
            y_data_per_cm = (y_range / bbox.height) * cm_to_inch

            # 繪製1cm長的垂直綠色標記線
            if self.start_point_line is not None:
                for line in self.start_point_line:
                    line.remove()
            
            self.start_point_line = []
            line = ax.plot([x, x], [y, y + y_data_per_cm], 
                         color='green', linewidth=2, zorder=5)[0]
            self.start_point_line.append(line)

            # 更新圖表
            self.figure.canvas.draw_idle()

        except Exception as e:
            print(f"繪製起點線時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def on_resize(self, event):
        """處理圖表大小改變事件"""
        if self.has_start_point_set:
            self._draw_start_point_line()

    def has_start_point(self):
        """檢查是否已設定起點"""
        return self.has_start_point_set
