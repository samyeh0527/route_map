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
        self.click_callback = None


    def create_plots(self, highlight_index=None, highlight_range=None):
        """創建圖表，支持高亮顯示"""
        try:
            print("\n=== 開始創建圖表 ===")
            if not self.data_list:
                print("錯誤: 沒有數據")
                return
            
            self.figure.clear()
            
            # 設置中文字體
            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
            plt.rcParams['axes.unicode_minus'] = False
            
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
