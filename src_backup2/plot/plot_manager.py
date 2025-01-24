from matplotlib.figure import Figure
import numpy as np
import matplotlib.pyplot as plt
import warnings
import matplotlib as mpl

class PlotManager:
    """圖表管理器"""
    def __init__(self, figure):
        """初始化圖表管理器"""
        # 關閉所有 matplotlib 的警告
        warnings.filterwarnings("ignore", category=UserWarning)
        
        # 設置全局字體配置
        mpl.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
        mpl.rcParams['axes.unicode_minus'] = False
        mpl.rcParams['font.family'] = 'sans-serif'
        
        self.figure = figure
        self.data_list = []
        self.axes = {}
        self.cached_plots = {
            'r_scale1': {'line': None, 'highlight_line': None, 'highlight_point': None},
            'r_scale2': {'line': None, 'highlight_line': None, 'highlight_point': None},
            'speed': {'line': None, 'highlight_line': None, 'highlight_point': None},
            'position': {'line': None, 'scatter': None, 'highlight_point': None}
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
        self.value_texts = []  # 儲存所有數值文字對象

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
            
            # 修改為3行1列的布局，只包含速度和R Scale圖表
            gs = self.figure.add_gridspec(3, 1, 
                                        height_ratios=[1, 1, 1], 
                                        hspace=0)  # 將整體間距設為0，後續手動調整
            
            # 調整圖表順序，將速度圖放在最上方
            self.axes = {
                'speed': self.figure.add_subplot(gs[0, 0]),     # 速度圖放在最上方
                'r_scale1': self.figure.add_subplot(gs[1, 0]),  # R Scale 1 放在中間
                'r_scale2': self.figure.add_subplot(gs[2, 0]),  # R Scale 2 放在最下方
            }
            
            # 繪製每個圖表
            for ax_name, ax in self.axes.items():
                if ax_name == 'speed':
                    self._plot_data(ax, 'G Speed', '')
                elif ax_name == 'r_scale1':
                    self._plot_data(ax, 'R Scale 1', '')
                elif ax_name == 'r_scale2':
                    self._plot_data(ax, 'R Scale 2', '')
            
            # 如果有高亮點，添加高亮顯示
            if highlight_index is not None and highlight_range is not None:
                if 0 <= highlight_range < len(self.data_list):
                    data = self.data_list[highlight_range]
                    if 0 <= highlight_index < len(data):
                        self._add_highlights(highlight_index, data)
            
            # 調整子圖之間的間距
            self.figure.tight_layout()
            
            # 手動調整各圖表的位置
            pos_r_scale1 = self.axes['r_scale1'].get_position()
            pos_r_scale2 = self.axes['r_scale2'].get_position()
            pos_speed = self.axes['speed'].get_position()
            
            # 調整上面三個圖表，使其緊密相連
            self.axes['r_scale2'].set_position([
                pos_r_scale2.x0,
                pos_r_scale2.y0 + 0.00,  # 稍微上移
                pos_r_scale2.width,
                pos_r_scale2.height
            ])
            
            self.axes['speed'].set_position([
                pos_speed.x0,
                pos_speed.y0,  # 稍微上移
                pos_speed.width,
                pos_speed.height
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
        """繪製數據到指定的軸"""
        try:
            for i, data in enumerate(self.data_list):
                if column_name in data.columns:
                    # 使用固定的列名作為標題，而不是從參數獲取
                    if column_name == 'G Speed':
                        plot_title = 'G Speed'
                    elif column_name == 'R Scale 1':
                        plot_title = 'R Scale 1'
                    elif column_name == 'R Scale 2':
                        plot_title = 'R Scale 2'
                    else:
                        plot_title = column_name
                    
                    ax.set_title(plot_title, fontsize=10, fontfamily='sans-serif')
                    ax.plot(data.index, data[column_name], 
                           color=self.colors[i % len(self.colors)],
                           label=f'數據集 {i+1}')
                    
                    # 設置軸標籤字體
                    ax.tick_params(axis='both', labelsize=8)
                    ax.grid(True, alpha=0.3)
                    
                    if len(self.data_list) > 1:
                        ax.legend(fontsize=8)
                    
        except Exception as e:
            print(f"繪製數據時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

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
        try:
            if 'position' not in self.axes:
                return
            
            ax = self.axes['position']
            ax.clear()
            
            data = self.data_list[0]  # 使用第一個數據集
            
            # 檢查數據中的列名
            if 'Longitude' in data.columns and 'Latitude' in data.columns:
                x_data = data['Longitude']
                y_data = data['Latitude']
                x_label = '經度'
                y_label = '緯度'
            else:
                print("錯誤：找不到位置數據列")
                return
            
            # 繪製軌跡線和散點
            line, = ax.plot(x_data, y_data, 'b-', linewidth=0.5)
            scatter = ax.scatter(x_data, y_data, c='blue', s=20)
            
            # 設置標題和標籤
            ax.set_title('位置軌跡圖', fontsize=10)
            ax.set_xlabel(x_label, fontsize=9)
            ax.set_ylabel(y_label, fontsize=9)
            ax.grid(True)
            
            # 設置適當的軸範圍
            x_min, x_max = x_data.min(), x_data.max()
            y_min, y_max = y_data.min(), y_data.max()
            
            # 計算邊距
            x_margin = (x_max - x_min) * 0.1
            y_margin = (y_max - y_min) * 0.1
            
            # 設置範圍
            ax.set_xlim(x_min - x_margin, x_max + x_margin)
            ax.set_ylim(y_min - y_margin, y_max + y_margin)
            
            # 初始化十字線列表
            self.position_crosshair_lines = []
            self.position_highlight_point = None
            
            # 保存繪圖對象
            self.cached_plots['position'] = {
                'line': line,
                'scatter': scatter,
                'highlight_point': None
            }
            
        except Exception as e:
            print(f"創建位置軌跡圖時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def _update_highlights(self, highlight_index):
        """更新高亮顯示"""
        # 移除舊的高亮
        self._remove_old_highlights()
        
        if highlight_index is not None:
            self._add_new_highlights(highlight_index)

    def _remove_old_highlights(self):
        """移除舊的高亮顯示"""
        try:
            for i in range(len(self.axes)):
                if i in self.cached_plots:
                    plot_cache = self.cached_plots[i]
                    # 清除高亮線
                    if 'highlight_line' in plot_cache and plot_cache['highlight_line']:
                        plot_cache['highlight_line'].remove()
                        plot_cache['highlight_line'] = None
                    
                    # 清除高亮點
                    if 'highlight_point' in plot_cache and plot_cache['highlight_point']:
                        if isinstance(plot_cache['highlight_point'], (list, tuple)):
                            for artist in plot_cache['highlight_point']:
                                artist.remove()
                        else:
                            plot_cache['highlight_point'].remove()
                        plot_cache['highlight_point'] = None
            
            # 強制更新畫布
            self.figure.canvas.draw_idle()
        
        except Exception as e:
            print(f"移除舊的高亮顯示時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def _add_new_highlights(self, index):
        """添加新的高亮顯示"""
        try:
            # 使用固定的列名列表
            columns_to_plot = ['G Speed', 'R Scale 1', 'R Scale 2']
            
            for i, (ax, col_name) in enumerate(zip(self.axes, columns_to_plot)):
                if col_name in self.data_list[0].columns:
                    # 添加垂直線
                    line = ax.axvline(x=index, color='r', linestyle='--', zorder=3)
                    # 添加高亮點
                    point = ax.plot(index, self.data_list[0][col_name].iloc[index], 
                                  'ro', markersize=6, zorder=4)[0]
                    
                    # 保存到緩存
                    if i not in self.cached_plots:
                        self.cached_plots[i] = {}
                    self.cached_plots[i]['highlight_line'] = line
                    self.cached_plots[i]['highlight_point'] = point
            
            # 更新畫布
            self.figure.canvas.draw_idle()
        
        except Exception as e:
            print(f"添加新的高亮顯示時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

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
        if event.inaxes is None or not self.data_list:
            return
        
        try:
            data = self.data_list[0]
            
            # 如果點擊的是軌跡圖
            if event.inaxes == self.axes.get('position'):
                # 找到最近的數據點
                if 'X' in data.columns and 'Y' in data.columns:
                    distances = ((data['X'] - event.xdata) ** 2 + 
                               (data['Y'] - event.ydata) ** 2) ** 0.5
                    nearest_idx = distances.argmin()
                    x, y = data['X'].iloc[nearest_idx], data['Y'].iloc[nearest_idx]
                elif 'Longitude' in data.columns and 'Latitude' in data.columns:
                    distances = ((data['Longitude'] - event.xdata) ** 2 + 
                               (data['Latitude'] - event.ydata) ** 2) ** 0.5
                    nearest_idx = distances.argmin()
                    x, y = data['Longitude'].iloc[nearest_idx], data['Latitude'].iloc[nearest_idx]
                else:
                    return
                
                print(f"點擊軌跡圖位置，索引: {nearest_idx}")
                
                # 清除所有舊的標記
                self._clear_all_highlights()
                
                # 更新軌跡圖的標記
                point = event.inaxes.scatter(x, y, color='red', s=100, zorder=5)
                self.crosshair_lines.append(point)
                
                # 更新主圖表
                for ax_name, ax in self.axes.items():
                    if ax_name != 'position':
                        # 獲取對應的數據列
                        column_mapping = {
                            'speed': 'G Speed',
                            'r_scale1': 'R Scale 1',
                            'r_scale2': 'R Scale 2'
                        }
                        
                        col_name = column_mapping.get(ax_name)
                        if col_name and col_name in data.columns:
                            value = data[col_name].iloc[nearest_idx]
                            
                            # 添加垂直線
                            v_line = ax.axvline(x=nearest_idx, color='red', linestyle='--', alpha=0.5)
                            self.crosshair_lines.append(v_line)
                            
                            # 添加高亮點
                            point = ax.scatter(nearest_idx, value, color='red', s=100, zorder=5)
                            self.crosshair_lines.append(point)
                            
                            # 添加數值標籤
                            text = ax.text(
                                nearest_idx, value,
                                f'{value:.2f}',
                                bbox=dict(facecolor='white', edgecolor='none', alpha=0.8),
                                verticalalignment='bottom',
                                horizontalalignment='right'
                            )
                            self.value_texts.append(text)
                            
                            # 添加索引標籤
                            index_text = ax.text(
                                0.02, 0.95,
                                f'索引: {nearest_idx}',
                                transform=ax.transAxes,
                                bbox=dict(facecolor='white', edgecolor='none', alpha=0.8),
                                verticalalignment='top',
                                horizontalalignment='left'
                            )
                            self.value_texts.append(index_text)
                
                # 更新圖表
                self.figure.canvas.draw_idle()
                
                # 觸發回調
                if self.click_callback:
                    self.click_callback(nearest_idx)
                
            else:
                # 點擊主圖表時的處理邏輯保持不變
                nearest_idx = int(round(event.xdata))
                if nearest_idx < 0 or nearest_idx >= len(data):
                    return
                
                print(f"點擊主圖表位置，索引: {nearest_idx}")
                self._update_all_plots(nearest_idx, data)
                
                # 觸發回調
                if self.click_callback:
                    self.click_callback(nearest_idx)
            
        except Exception as e:
            print(f"處理圖表點擊事件時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def _update_all_plots(self, index, data):
        """更新所有圖表的顯示"""
        try:
            # 清除所有舊的標記
            self._clear_all_highlights()
            
            # 更新主圖表
            for ax_name, ax in self.axes.items():
                if ax_name == 'position':
                    # 更新軌跡圖
                    if 'Longitude' in data.columns and 'Latitude' in data.columns:
                        x = data['Longitude'].iloc[index]
                        y = data['Latitude'].iloc[index]
                        point = ax.scatter(x, y, color='red', s=100, zorder=5)
                        self.crosshair_lines.append(point)
                        text = ax.text(
                            x, y,
                            f'經度: {x:.6f}\n緯度: {y:.6f}',
                            bbox=dict(facecolor='white', edgecolor='none', alpha=0.8),
                            verticalalignment='bottom',
                            horizontalalignment='right'
                        )
                        self.value_texts.append(text)
                    elif 'X' in data.columns and 'Y' in data.columns:
                        x = data['X'].iloc[index]
                        y = data['Y'].iloc[index]
                        point = ax.scatter(x, y, color='red', s=100, zorder=5)
                        self.crosshair_lines.append(point)
                        text = ax.text(
                            x, y,
                            f'X: {x:.2f}\nY: {y:.2f}',
                            bbox=dict(facecolor='white', edgecolor='none', alpha=0.8),
                            verticalalignment='bottom',
                            horizontalalignment='right'
                        )
                        self.value_texts.append(text)
                else:
                    # 更新其他圖表
                    column_mapping = {
                        'speed': 'G Speed',
                        'r_scale1': 'R Scale 1',
                        'r_scale2': 'R Scale 2'
                    }
                    
                    if ax_name in column_mapping:
                        col_name = column_mapping[ax_name]
                        if col_name in data.columns:
                            value = data[col_name].iloc[index]
                            
                            # 添加垂直線
                            v_line = ax.axvline(x=index, color='red', linestyle='--', alpha=0.5)
                            self.crosshair_lines.append(v_line)
                            
                            # 添加高亮點
                            point = ax.scatter(index, value, color='red', s=100, zorder=5)
                            self.crosshair_lines.append(point)
                            
                            # 添加數值標籤
                            text = ax.text(
                                index, value,
                                f'{value:.2f}',
                                bbox=dict(facecolor='white', edgecolor='none', alpha=0.8),
                                verticalalignment='bottom',
                                horizontalalignment='right'
                            )
                            self.value_texts.append(text)
            
            # 在每個圖表上添加索引標籤
            for ax_name, ax in self.axes.items():
                if ax_name != 'position':
                    index_text = ax.text(
                        0.02, 0.95,
                        f'索引: {index}',
                        transform=ax.transAxes,
                        bbox=dict(facecolor='white', edgecolor='none', alpha=0.8),
                        verticalalignment='top',
                        horizontalalignment='left'
                    )
                    self.value_texts.append(index_text)
            
            # 更新圖表
            self.figure.canvas.draw_idle()
            
        except Exception as e:
            print(f"更新圖表時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def _clear_all_highlights(self):
        """清除所有高亮標記"""
        try:
            # 清除資訊文字
            if self.info_text is not None:
                self.info_text.remove()
                self.info_text = None
            
            # 清除十字虛線和標記點
            for line in self.crosshair_lines:
                line.remove()
            self.crosshair_lines = []
            
            # 清除數值文字
            for text_obj in self.value_texts:
                text_obj.remove()
            self.value_texts = []
            
            # 清除軌跡圖上的標示點
            if hasattr(self, 'track_point') and self.track_point:
                self.track_point.remove()
                self.track_point = None
            
            # 清除位置軌跡圖的十字線和標記點
            if hasattr(self, 'position_crosshair_lines'):
                for line in self.position_crosshair_lines:
                    line.remove()
                self.position_crosshair_lines = []
            
            if hasattr(self, 'position_highlight_point') and self.position_highlight_point:
                self.position_highlight_point.remove()
                self.position_highlight_point = None
            
            # 強制更新圖表
            self.figure.canvas.draw_idle()
            
        except Exception as e:
            print(f"清除高亮標記時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def set_click_callback(self, callback):
        """設置點擊回調函數"""
        self.click_callback = callback

    def _add_highlights(self, index, data):
        """添加高亮顯示"""
        try:
            # 清除舊的高亮
            for plot_info in self.cached_plots.values():
                if plot_info['highlight_line']:
                    plot_info['highlight_line'].remove()
                    plot_info['highlight_line'] = None
                if plot_info['highlight_point']:
                    plot_info['highlight_point'].remove()
                    plot_info['highlight_point'] = None

            # 在每個子圖上添加垂直線和點
            for ax_name, ax in self.axes.items():
                if ax_name == 'speed' and 'G Speed' in data.columns:
                    y_value = data['G Speed'].iloc[index]
                    color = 'red'
                    # 添加垂直線
                    self.cached_plots['speed']['highlight_line'] = ax.axvline(
                        x=index, color=color, linestyle='--', alpha=0.5)
                    # 添加高亮點
                    self.cached_plots['speed']['highlight_point'] = ax.scatter(
                        index, y_value, color=color, s=100, zorder=5)
                    # 添加數值標籤
                    self._add_value_text(ax, index, y_value, color)

                elif ax_name == 'r_scale1' and 'R Scale 1' in data.columns:
                    y_value = data['R Scale 1'].iloc[index]
                    color = 'red'
                    self.cached_plots['r_scale1']['highlight_line'] = ax.axvline(
                        x=index, color=color, linestyle='--', alpha=0.5)
                    self.cached_plots['r_scale1']['highlight_point'] = ax.scatter(
                        index, y_value, color=color, s=100, zorder=5)
                    self._add_value_text(ax, index, y_value, color)

                elif ax_name == 'r_scale2' and 'R Scale 2' in data.columns:
                    y_value = data['R Scale 2'].iloc[index]
                    color = 'red'
                    self.cached_plots['r_scale2']['highlight_line'] = ax.axvline(
                        x=index, color=color, linestyle='--', alpha=0.5)
                    self.cached_plots['r_scale2']['highlight_point'] = ax.scatter(
                        index, y_value, color=color, s=100, zorder=5)
                    self._add_value_text(ax, index, y_value, color)

            # 更新圖表
            self.figure.canvas.draw_idle()

        except Exception as e:
            print(f"添加高亮顯示時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def _add_value_text(self, ax, x, y, color):
        """添加數值文字標籤"""
        try:
            # 獲取軸的範圍
            x_min, x_max = ax.get_xlim()
            y_min, y_max = ax.get_ylim()
            
            # 計算文字位置（稍微偏移以避免遮擋數據點）
            text_x = x + (x_max - x_min) * 0.02
            text_y = y + (y_max - y_min) * 0.02
            
            # 添加文字標籤
            text = ax.text(text_x, text_y, f'{y:.2f}', 
                          color=color,
                          fontsize=9,
                          bbox=dict(facecolor='white', 
                                   edgecolor='none',
                                   alpha=0.7))
            
            # 保存文字對象以便後續清除
            self.value_texts.append(text)
            
        except Exception as e:
            print(f"添加數值文字時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

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
            if hasattr(self, 'start_point_line') and self.start_point_line:
                for line in self.start_point_line:
                    line.remove()
                self.start_point_line = None

            # 儲存起點座標和相關資訊
            self.start_point = (x, y)
            self.has_start_point_set = True
            
            # 更新起點資訊
            self.start_point_data = {
                'x': x,
                'y': y
            }

            # 在所有子圖上添加垂直線
            self.start_point_line = []
            for ax_name, ax in self.axes.items():
                line = ax.axvline(x=x, color='green', linestyle='--', linewidth=2)
                self.start_point_line.append(line)

            # 更新圖表
            self.figure.canvas.draw_idle()
            print(f"起點已設定在: x={x:.6f}, y={y:.6f}")

        except Exception as e:
            print(f"設定起點時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def _draw_start_point_line(self):
        """重新繪製起點標記線"""
        if not self.has_start_point_set or self.start_point_data is None:
            return

        try:
            # 清除舊的起點線
            if hasattr(self, 'start_point_line') and self.start_point_line:
                for line in self.start_point_line:
                    line.remove()
                self.start_point_line = None

            # 在所有子圖上重新添加垂直線
            self.start_point_line = []
            x = self.start_point_data['x']
            for ax_name, ax in self.axes.items():
                line = ax.axvline(x=x, color='green', linestyle='--', linewidth=2)
                self.start_point_line.append(line)

            # 更新圖表
            self.figure.canvas.draw_idle()

        except Exception as e:
            print(f"重繪起點線時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def on_resize(self, event):
        """處理圖表大小改變事件"""
        if self.has_start_point_set:
            self._draw_start_point_line()

    def has_start_point(self):
        """檢查是否已設定起點"""
        return self.has_start_point_set

    def clear_start_point(self):
        """清除起點設定"""
        try:
            # 清除起點線
            if hasattr(self, 'start_point_line') and self.start_point_line:
                for line in self.start_point_line:
                    line.remove()
                self.start_point_line = None
            
            # 重置起點相關變數
            self.start_point = None
            self.has_start_point_set = False
            self.start_point_data = None
            self.is_setting_start_point = False
            
            # 更新圖表
            self.figure.canvas.draw_idle()
            print("起點設定已清除")
            
        except Exception as e:
            print(f"清除起點設定時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def _show_position_crosshair(self, x, y, index):
        """在位置軌跡圖上顯示十字線和標記"""
        try:
            ax = self.axes.get('position')
            if ax is None:
                return
            
            # 清除舊的十字線
            if hasattr(self, 'position_crosshair_lines'):
                for line in self.position_crosshair_lines:
                    line.remove()
            
            # 清除舊的標記點
            if hasattr(self, 'position_highlight_point'):
                if self.position_highlight_point:
                    self.position_highlight_point.remove()
            
            # 獲取軸的範圍
            x_min, x_max = ax.get_xlim()
            y_min, y_max = ax.get_ylim()
            
            # 創建十字線
            self.position_crosshair_lines = [
                ax.axvline(x=x, color='red', linestyle='--', alpha=0.5),
                ax.axhline(y=y, color='red', linestyle='--', alpha=0.5)
            ]
            
            # 添加標記點
            self.position_highlight_point = ax.scatter(
                [x], [y],
                color='red',
                s=100,
                zorder=5
            )
            
            # 添加座標文字
            text = ax.text(
                x, y,
                f'經度: {x:.6f}\n緯度: {y:.6f}',
                bbox=dict(facecolor='white', edgecolor='none', alpha=0.8),
                verticalalignment='bottom',
                horizontalalignment='right'
            )
            self.position_crosshair_lines.append(text)
            
            # 更新圖表
            self.figure.canvas.draw_idle()
            
        except Exception as e:
            print(f"顯示位置十字線時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def highlight_point(self, index):
        """高亮顯示指定索引的數據點"""
        try:
            # 清除所有舊的標記
            self._clear_all_highlights()
            
            # 遍歷每個子圖
            for ax_name, ax in self.axes.items():
                if ax_name in ['speed', 'r_scale1', 'r_scale2']:
                    # 獲取對應的數據列名
                    column_mapping = {
                        'speed': 'G Speed',
                        'r_scale1': 'R Scale 1',
                        'r_scale2': 'R Scale 2'
                    }
                    
                    col_name = column_mapping.get(ax_name)
                    if col_name and col_name in self.data_list[0].columns:
                        value = self.data_list[0][col_name].iloc[index]
                        
                        # 添加垂直線
                        v_line = ax.axvline(x=index, color='red', linestyle='--', alpha=0.5)
                        self.crosshair_lines.append(v_line)
                        
                        # 添加高亮點
                        point = ax.scatter(index, value, color='red', s=100, zorder=5)
                        self.crosshair_lines.append(point)
                        
                        # 添加數值標籤
                        text = ax.text(
                            index, value,
                            f'{value:.2f}',
                            bbox=dict(facecolor='white', edgecolor='none', alpha=0.8),
                            verticalalignment='bottom',
                            horizontalalignment='right'
                        )
                        self.value_texts.append(text)
                        
                        # 添加索引標籤
                        index_text = ax.text(
                            0.02, 0.95,
                            f'索引: {index}',
                            transform=ax.transAxes,
                            bbox=dict(facecolor='white', edgecolor='none', alpha=0.8),
                            verticalalignment='top',
                            horizontalalignment='left'
                        )
                        self.value_texts.append(index_text)
            
            # 更新圖表
            self.figure.canvas.draw()
            
        except Exception as e:
            print(f"高亮顯示數據點時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
