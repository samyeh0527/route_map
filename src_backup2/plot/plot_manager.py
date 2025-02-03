from matplotlib.figure import Figure
import numpy as np
import matplotlib.pyplot as plt
import warnings
import matplotlib as mpl
import pandas as pd
from PyQt5.QtWidgets import QApplication, QProgressDialog
from PyQt5.QtCore import Qt

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
        self.track_point = None
        self.range_update_callback = None  # 添加新的回調屬性
        self.range_highlights = {}  # 存儲範圍高亮對象

    def create_plots(self, highlight_index=None, highlight_range=None):
        """創建圖表，支持高亮顯示"""
        try:
            print("\n=== 開始創建圖表 ===")
            if not self.data_list:
                print("錯誤: 沒有數據")
                return
            
            # 清除起點設定
            self.clear_start_point()
            
            # 清除分段範圍相關設定
            if hasattr(self, 'current_checked_items'):
                self.current_checked_items = None
            if hasattr(self, 'combined_track_data'):
                self.combined_track_data = None
            
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
            # 如果沒有數據,清除標題plot_selected_ranges
            if not self.data_list:
                ax.set_title("")
                return
                
            for i, data in enumerate(self.data_list):
                if column_name in data.columns:
                    # 使用固定的列名作為標題
                    if column_name == 'G Speed':
                        plot_title = 'G Speed'
                    elif column_name == 'R Scale 1':
                        plot_title = 'R Scale 1'
                    elif column_name == 'R Scale 2':
                        plot_title = 'R Scale 2'
                    else:
                        plot_title = column_name
                    
                    # 設置黑底白字的標題
                    ax.set_title(plot_title, 
                               fontsize=10, 
                               fontfamily='sans-serif',
                               loc='left',
                               pad=10,
                               bbox=dict(
                                   facecolor='black',
                                   edgecolor='none',
                                   pad=3.0,
                                   alpha=1.0
                               ),
                               color='white')
                    
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
        
        # if highlight_index is not None:
        #     self._add_new_highlights(highlight_index)

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
            
            # for i, (ax, col_name) in enumerate(zip(self.axes, columns_to_plot)):
            #     if col_name in self.data_list[0].columns:
            #         # 添加垂直線
            #         line = ax.axvline(x=index, color='r', linestyle='--', zorder=3)
            #         # 添加高亮點
            #         point = ax.plot(index, self.data_list[0][col_name].iloc[index], 
            #                       'ro', markersize=6, zorder=4)[0]
                    
            #         # 保存到緩存
            #         if i not in self.cached_plots:
            #             self.cached_plots[i] = {}
            #         self.cached_plots[i]['highlight_line'] = line
            #         self.cached_plots[i]['highlight_point'] = point
            
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
        if event.inaxes is None:
            return
        
        try:
            if not self.data_list:
                print("警告：沒有可用的數據")
                return
            
            if hasattr(self, 'current_checked_items') and self.current_checked_items:
                nearest_idx = int(round(event.xdata))
                
                # 找出點擊位置所屬的Run
                clicked_run_info = None
                for range_id, range_info in self.range_index_mapping.items():
                    if range_info['start'] <= nearest_idx <= range_info['end']:
                        clicked_run_info = {
                            'run_id': range_id,
                            'relative_idx': nearest_idx - range_info['start']
                        }
                        break
                
                if clicked_run_info is not None:
                    relative_idx = clicked_run_info['relative_idx']
                    
                    # 正確的方式清除舊的數值標籤
                    for ax in self.axes.values():
                        # 找出需要移除的文字對象
                        texts_to_remove = [text for text in ax.texts if hasattr(text, 'is_value_label')]
                        # 逐個移除文字對象
                        for text in texts_to_remove:
                            text.remove()
                    
                    # 其餘代碼保持不變
                    run_count = len(self.range_highlights)
                    vertical_spacing = 0.15
                    
                    updates = []
                    for i, (range_id, range_obj) in enumerate(self.range_highlights.items()):
                        vertical_position = 0.95 - (i * vertical_spacing)
                        range_info = self.range_index_mapping[range_id]
                        original_idx = range_info['original_start'] + relative_idx
                        
                        if original_idx <= range_info['original_end']:
                            for text in range_obj['labels']:
                                # 找到對應的 item_data 以獲取自定義標籤
                                item_data = next((item for item in self.current_checked_items 
                                                if item['id'] == range_id), None)
                                label_name = item_data.get('label', f'Run {range_id}') if item_data else f'Run {range_id}'
                                
                                if text.label_type == 'speed':
                                    value = self.data_list[0]['G Speed'].iloc[original_idx]
                                    text.set_text(f'{label_name}\n{value:.1f} km/h')
                                    print(f"[_on_plot_click] 更新速度標籤，value: {value}")
                                    updates.append((self.axes['speed'], range_id, value, vertical_position))
                                elif text.label_type == 'r_scale1':
                                    value = self.data_list[0]['R Scale 1'].iloc[original_idx]
                                    text.set_text(f'{label_name}\n{value:.2f}')
                                    print(f"[_on_plot_click] 更新R Scale 1標籤，value: {value}")
                                    updates.append((self.axes['r_scale1'], range_id, value, vertical_position))
                                elif text.label_type == 'r_scale2':
                                    value = self.data_list[0]['R Scale 2'].iloc[original_idx]
                                    text.set_text(f'{label_name}\n{value:.2f}')
                                    print(f"[_on_plot_click] 更新R Scale 2標籤，value: {value}")
                                    updates.append((self.axes['r_scale2'], range_id, value, vertical_position))
                                text.set_y(0.85)
                    
                    # 批量添加新的數值標籤
                    for ax, range_id, value, vertical_position in updates:
                        if isinstance(ax, str):
                            ax = self.axes[ax]
                        # 修改字體大小為7，並調整文字框的padding和間距
                        value_text = ax.text(0, vertical_position,
                                           f'Run {range_id}: {value:.2f}',
                                           transform=ax.transAxes,
                                           horizontalalignment='left',
                                           verticalalignment='top',
                                           fontsize=7,  # 縮小字體
                                           zorder=float('inf'),
                                           bbox=dict(facecolor='white',
                                                   edgecolor='black',
                                                   alpha=0.8,
                                                   pad=0.2,  # 減小padding
                                                   boxstyle='round,pad=0.3'))  # 減小文字框邊距
                        value_text.is_value_label = True
                        
                        # 調整垂直間距，避免重疊
                        vertical_spacing = 0.08  # 減小垂直間距
                    
                    # 一次性更新所有圖表
                    self._update_all_plots_with_reset_index(nearest_idx)
                    
                    # 觸發回調
                    if self.click_callback:
                        self.click_callback(nearest_idx)
                    
                    # 最後才重繪圖表
                    self.figure.canvas.draw()
                
            else:
                # 使用原始數據的處理邏輯（保持不變）
                nearest_idx = int(round(event.xdata))
                if 0 <= nearest_idx < len(self.data_list[0]):
                    self._update_highlights(nearest_idx)
                    
                    for range_id, range_obj in self.range_highlights.items():
                        for text in range_obj['labels']:
                            if text.label_type == 'speed':
                                value = self.data_list[0]['G Speed'].iloc[nearest_idx]
                                text.set_text(f'Run {text.range_id}\n{value:.1f} km/h')
                            elif text.label_type == 'r_scale1':
                                value = self.data_list[0]['R Scale 1'].iloc[nearest_idx]
                                text.set_text(f'Run {text.range_id}\n{value:.2f}')
                            elif text.label_type == 'r_scale2':
                                value = self.data_list[0]['R Scale 2'].iloc[nearest_idx]
                                text.set_text(f'Run {text.range_id}\n{value:.2f}')
                            text.set_y(0.85)
                    
                    if self.click_callback:
                        self.click_callback(nearest_idx)
                    
                    self.figure.canvas.draw()
            
        except Exception as e:
            print(f"處理主圖表點擊回調時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def _update_main_plots_with_reset_index(self, index):
        """使用重設後的索引更新主圖表"""
        try:
            if not hasattr(self, 'combined_track_data'):
                return
            
            data = self.combined_track_data
            
            # 檢查索引是否在有效範圍內
            if index >= len(data):
                print(f"警告：索引 {index} 超出範圍 (最大值: {len(data)-1})")
                return
            
            # 清除舊的標記
            self._clear_all_highlights()
            
            # 更新主圖表上的標記
            for ax_name, ax in self.axes.items():
                if ax_name != 'position':
                    column_mapping = {
                        'speed': 'G Speed',
                        'r_scale1': 'R Scale 1',
                        'r_scale2': 'R Scale 2'
                    }
                    
                    col_name = column_mapping.get(ax_name)
                    if col_name and col_name in data.columns:
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
                            f'',
                            bbox=dict(facecolor='white', edgecolor='none', alpha=0.8),
                            verticalalignment='bottom',
                            horizontalalignment='right'
                        )
                        self.value_texts.append(text)
                        
                        # 添加索引標籤
                        index_text = ax.text(
                            0.02, 0.95,
                            f'',
                            transform=ax.transAxes,
                            bbox=dict(facecolor='white', edgecolor='none', alpha=0.8),
                            verticalalignment='top',
                            horizontalalignment='left'
                        )
                        self.value_texts.append(index_text)
            
            # 更新圖表
            self.figure.canvas.draw_idle()
            
        except Exception as e:
            print(f"更新主圖表時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def _update_all_plots_with_reset_index(self, index):
        """使用重設後的索引更新所有圖表"""
        try:
            # 清除所有舊的標記
            self._clear_all_highlights()
            
            if hasattr(self, 'combined_track_data'):
                data = self.combined_track_data
                
                # 更新主圖表
                self._update_main_plots_with_reset_index(index)
                
                # 更新軌跡圖
                if 'position' in self.axes:
                    x_col = 'X' if 'X' in data.columns else 'Longitude'
                    y_col = 'Y' if 'Y' in data.columns else 'Latitude'
                    
                    x = data[x_col].iloc[index]
                    y = data[y_col].iloc[index]
                    
                    point = self.axes['position'].scatter(x, y, color='red', s=100, zorder=5)
                    self.crosshair_lines.append(point)
                    
                    # 添加座標文字標籤
                    text = self.axes['position'].text(
                        x, y,
                        f'經度: {x:.6f}\n緯度: {y:.6f}',
                        bbox=dict(facecolor='white', edgecolor='none', alpha=0.8),
                        verticalalignment='bottom',
                        horizontalalignment='right'
                    )
                    self.value_texts.append(text)
            
            # 更新圖表
            self.figure.canvas.draw_idle()
            
        except Exception as e:
            print(f"更新所有圖表時出錯: {str(e)}")
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

    def set_start_point(self, index, track_ax, track_canvas):
        """設定起點"""
        try:
            # 確保 index 是整數類型
            index = int(index)
            
            # 儲存起點資訊
            self.start_point = index
            self.has_start_point_set = True
            self.start_point_data = {'x': index}  # 確保存儲的也是整數
            
            # 獲取選中點的座標，處理不同的列名情況
            data = self.data_list[0]  # 假設使用第一個數據集
            x_col = 'X' if 'X' in data.columns else 'Longitude'
            y_col = 'Y' if 'Y' in data.columns else 'Latitude'
            
            x = data[x_col].iloc[index]
            y = data[y_col].iloc[index]
            
            # 更新軌跡圖上的點
            self.update_track_point(index, track_ax, track_canvas)
            print(f"已更新軌跡圖上的點 clsaa name {self.update_track_point.__name__}")
            # 清除舊的標記線
            if hasattr(self, 'start_point_line') and self.start_point_line:
                for line in self.start_point_line:
                    line.remove()
            
            self.start_point_line = []
            
            # 為主圖表添加垂直線並更新顯示
            for ax_name, ax in self.axes.items():
                line = ax.axvline(x=index, color='green', linestyle='--', linewidth=2)
                self.start_point_line.append(line)
                ax.figure.canvas.draw()  # 更新每個主圖表
            
            # 計算1公分的數據單位長度
            y_range = track_ax.get_ylim()[1] - track_ax.get_ylim()[0]
            fig_height_inches = track_ax.figure.get_size_inches()[1]
            one_cm_data_units = (y_range / (fig_height_inches * 2.54))  # 轉換1公分到數據單位
            
            # 在軌跡圖上添加垂直線（向上下各延伸1公分）
            track_line = track_ax.plot([x, x], 
                                     [y - one_cm_data_units, y + one_cm_data_units],  # 從選取點向上下各延伸1公分
                                     color='green',
                                     linestyle='--',
                                     linewidth=2)[0]
            self.start_point_line.append(track_line)
            
            # 更新軌跡圖顯示
            track_canvas.draw()
            
            # 呼叫 analyze_ranges 進行分析
            analyze =self.analyze_ranges(index)
            #print(analyze,"\n",type(analyze),"\n",len(analyze))  
            print(f"起點已設定在索引: {index}")
            
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

    def find_nearest_point(self, x_click, y_click):
        """找到最接近點擊位置的數據點索引"""
        try:
            # 檢查是否有範圍數據
            if hasattr(self, 'combined_track_data') and hasattr(self, 'current_checked_items') and self.current_checked_items:
                data = self.combined_track_data
                
                # 檢查數據是否為空
                if data.empty:
                    print("警告：選定範圍內沒有數據")
                    return None
                
            elif self.data_list:
                data = self.data_list[0]
                # 檢查數據是否為空
                if data.empty:
                    print("警告：數據列表為空")
                    return None
            else:
                print("警告：沒有可用的數據")
                return None
            
            x_col = 'X' if 'X' in data.columns else 'Longitude'
            y_col = 'Y' if 'Y' in data.columns else 'Latitude'
            
            # 確保所需的列存在
            if x_col not in data.columns or y_col not in data.columns:
                print(f"警告：找不到必要的列 {x_col} 或 {y_col}")
                return None
            
            # 檢查座標值是否有效
            if pd.isna(x_click) or pd.isna(y_click):
                print("警告：無效的點擊座標")
                return None
            
            # 計算點擊位置到所有點的距離
            distances = np.sqrt(
                (data[x_col] - x_click) ** 2 + 
                (data[y_col] - y_click) ** 2
            )
            
            # 檢查距離序列是否為空
            if distances.empty:
                print("警告：距離計算結果為空")
                return None
            
            # 找到最小距離的索引
            nearest_idx = distances.idxmin()
            
            # 如果使用的是重設索引的數據，直接返回索引
            return nearest_idx
            
        except Exception as e:
            print(f"查找最近點時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
        
    def update_track_point(self, index, track_ax, track_canvas):
        """更新軌跡圖上的點"""
        try:
            # 檢查是否有範圍數據
            if hasattr(self, 'combined_track_data'):
                data = self.combined_track_data
                print(f"數據長度: {len(data)} 筆")
                #print(f"current_checked_items: {self.current_checked_items}")
                # 獲取第一個範圍的長度
                first_range = self.current_checked_items[0]
                description = first_range['description']
                start_idx = int(description.split(',')[0].split(':')[1])
                end_idx = int(description.split(',')[1].split(':')[1])
                first_range_length = end_idx - start_idx + 1
                
                # 檢查索引是否超出第一個範圍
                if index >= first_range_length:
                    print(f"索引 {index} 超出第一個範圍長度 {first_range_length}")
                    return
                    
                print(f"使用第一個範圍的索引: {index}")
            elif self.data_list:
                data = self.data_list[0]
                print(f"使用原始索引: {index}")
            else:
                return
                
            # 安全地移除舊的 track_point
            if hasattr(self, 'track_point') and self.track_point is not None:
                try:
                    self.track_point.remove()
                except ValueError:
                    pass  # 忽略移除失敗的情況
            self.track_point = None
            
            x_col = 'X' if 'X' in data.columns else 'Longitude'
            y_col = 'Y' if 'Y' in data.columns else 'Latitude'
            
            # 確保索引在有效範圍內
            if 0 <= index < len(data):
                self.track_point = track_ax.scatter(
                    data[x_col].iloc[index],
                    data[y_col].iloc[index],
                    color='red',
                    s=100,
                    zorder=5
                )
                track_canvas.draw()
                
                # 更新主圖表高亮
                if hasattr(self, 'combined_track_data'):
                    self._clear_all_highlights()
                    self._update_main_plots_with_reset_index(index)
                else:
                    self.highlight_point(index)
                
        except Exception as e:
            print(f"更新軌跡點時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
    def set_range_update_callback(self, callback):
        """設置範圍更新回調函數"""
        self.range_update_callback = callback

    def analyze_ranges(self, start_index):
        """分析數據範圍"""
        try:
            # 創建進度對話框
            progress = QProgressDialog("分析數據範圍中...", None, 0, 0)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle("請稍候")
            progress.setCancelButton(None)
            progress.setMinimumDuration(0)
            progress.setWindowFlags(
                progress.windowFlags() & ~Qt.WindowCloseButtonHint
            )
            progress.show()
            
            QApplication.processEvents()
            
            data = self.data_list[0]
            data['Time'] = pd.to_datetime(data['Time'])
            
            x_col = 'X' if 'X' in data.columns else 'Longitude'
            y_col = 'Y' if 'Y' in data.columns else 'Latitude'
            start_x = data[x_col].iloc[start_index]
            start_y = data[y_col].iloc[start_index]
            
            tolerance = 0.00015
            
            ranges = []
            current_range = 1
            last_match_index = start_index
            in_range = False
            
            for i in range(start_index + 1, len(data)):
                if i % 100 == 0:
                    progress.setLabelText(f"分析數據範圍中...\n已處理: {i}/{len(data)} 筆數據")
                    QApplication.processEvents()
                
                current_x = data[x_col].iloc[i]
                current_y = data[y_col].iloc[i]
                current_time = data['Time'].iloc[i]
                
                x_match = abs(current_x - start_x) <= tolerance
                y_match = abs(current_y - start_y) <= tolerance
                
                if x_match and y_match:
                    if not in_range:
                        time_diff = (current_time - data['Time'].iloc[last_match_index]).total_seconds()
                        
                        if time_diff >= 5:
                            # 計算該範圍內的資料筆數
                            data_count = i - last_match_index + 1
                            
                            print(f"\n找到範圍 {current_range}:")
                            print(f"起點: 索引 {last_match_index}")
                            print(f"  座標: ({data[x_col].iloc[last_match_index]}, {data[y_col].iloc[last_match_index]})")
                            print(f"  時間: {data['Time'].iloc[last_match_index]}")
                            print(f"終點: 索引 {i}")
                            print(f"  座標: ({current_x}, {current_y})")
                            print(f"  時間: {current_time}")
                            print(f"資料筆數: {data_count}")
                            
                            hours = int(time_diff // 3600)
                            minutes = int((time_diff % 3600) // 60)
                            seconds = int(time_diff % 60)
                            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                            print(f"時間差: {time_str}")
                            print("---")
                            
                            ranges.append({
                                'range_number': current_range,
                                'start_index': last_match_index,
                                'end_index': i,
                                'start_time': data['Time'].iloc[last_match_index],
                                'end_time': current_time,
                                'duration': time_diff,
                                'duration_str': time_str,
                                'data_count': data_count  # 新增資料筆數
                            })
                            
                            current_range += 1
                            last_match_index = i
                            in_range = True
                else:
                    if in_range:
                        in_range = False
            
            progress.close()
            
            if self.range_update_callback:
                self.range_update_callback(ranges)
            
            return ranges
            
        except Exception as e:
            if 'progress' in locals():
                progress.close()
            print(f"分析範圍時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def clear_all_markers(self):
        """清除所有標記點"""
        try:
            # 清除起點標記
            self.clear_start_point()
            
            # 清除高亮點
            if hasattr(self, 'highlight_point'):
                for ax in self.axes:
                    if hasattr(ax, 'highlight_point') and ax.highlight_point:
                        ax.highlight_point.remove()
                        ax.highlight_point = None
            
            # 清除其他可能的標記
            if hasattr(self, 'track_highlight_point') and self.track_highlight_point:
                self.track_highlight_point.remove()
                self.track_highlight_point = None
            
            # 清除所有範圍高亮
            range_ids = list(self.range_highlights.keys())  # 創建鍵的列表以避免在迭代時修改字典
            for range_id in range_ids:
                self.remove_range_highlight(range_id)
            
            # 更新圖表
            self.figure.canvas.draw_idle()
            
        except Exception as e:
            print(f"清除所有標記時出錯: {str(e)}")

    def highlight_range(self, start_index, end_index, range_id):
        """在主圖表上高亮顯示指定Run"""
        try:
            # 檢查是否有 current_checked_items
            if hasattr(self, 'current_checked_items'):
                item_data = next((item for item in self.current_checked_items 
                                if item['id'] == range_id), None)
                label_name = item_data.get('label', '') if item_data else ''
                print(f"[highlight_range] 找到對應的 item_data: {item_data}")
                print(f"[highlight_range] label_name: {label_name}")
            else:
                label_name = ''
                print(f"[highlight_range] 警告：找不到 current_checked_items")
                print(f"[highlight_range] 使用空白 label_name: {label_name}")
            
            # 原有的代碼...
            highlights = []
            text_labels = []
            colors = ['#FFD700', '#98FB98', '#87CEFA', '#DDA0DD', '#F08080']
            color = colors[range_id % len(colors)]
            
            axes = self.figure.get_axes()
            
            for i, ax in enumerate(axes):
                highlight = ax.axvspan(start_index, end_index, 
                                     alpha=0.2, 
                                     color=color,
                                     zorder=1)
                highlights.append(highlight)
                
                x_pos = end_index
                y_pos = 0.85
                
                if i == 0:
                    label_type = 'speed'
                else:
                    label_type = 'r_scale1' if i == 1 else 'r_scale2'

                print(f"[highlight_range] 添加標籤，軸 {i}，使用 label_name: {label_name}")
                text = ax.text(x_pos, y_pos, 
                              label_name,  # 直接使用 label_name
                              horizontalalignment='right',
                              verticalalignment='top',
                              transform=ax.get_xaxis_transform(),
                              bbox=dict(facecolor='white',
                                      edgecolor=color,
                                      alpha=0.8,
                                      boxstyle='round,pad=0.5'),
                              fontsize=9,
                              zorder=5)
                
                text.range_id = range_id
                text.label_type = label_type
                text_labels.append(text)
            
            self.range_highlights[range_id] = {
                'highlights': highlights,
                'labels': text_labels
            }
            
        except Exception as e:
            print(f"添加Run高亮時出錯: {str(e)}")
    
    def remove_range_highlight(self, range_id):
        """移除指定Run的高亮顯示"""
        try:
            if range_id in self.range_highlights:
                # 移除所有子圖中的高亮
                for highlight in self.range_highlights[range_id]['highlights']:
                    highlight.remove()
                # 移除所有文字標籤
                for label in self.range_highlights[range_id]['labels']:
                    label.remove()
                del self.range_highlights[range_id]
                
        except Exception as e:
            print(f"移除Run高亮時出錯: {str(e)}")

    def plot_selected_ranges(self, checked_items, full_data, axes, canvas, track_ax, track_canvas):
        """繪製選中Run的圖表"""
        try:
            self.current_checked_items = checked_items
            print(f"[plot_selected_ranges] current_checked_items: {self.current_checked_items}")
            
            print("\n=== 重新編排索引後的Run詳細資料 ===")
            
            # 創建一個字典來存儲每個Run的索引映射
            self.range_index_mapping = {}
            current_index = 0
            
            # 為每個Run創建索引映射
            for item_data in checked_items:
                description = item_data['description']
                range_id = item_data['id']
                start_idx = int(description.split(',')[0].split(':')[1])
                end_idx = int(description.split(',')[1].split(':')[1])
                range_length = end_idx - start_idx + 1
                
                # 存儲該Run的索引範圍
                self.range_index_mapping[range_id] = {
                    'start': current_index,
                    'end': current_index + range_length - 1,
                    'original_start': start_idx,
                    'original_end': end_idx
                }
                
                print(f"\nRun {range_id}:")
                print(f"原始索引範圍: {start_idx} 到 {end_idx}")
                print(f"重設後索引範圍: {current_index} 到 {current_index + range_length - 1}")
                print(f"資料筆數: {range_length}")
                
                current_index += range_length

            # 創建組合數據
            self.combined_track_data = pd.DataFrame()
            for item_data in checked_items:
                range_id = item_data['id']
                start_idx = int(item_data['description'].split(',')[0].split(':')[1])
                end_idx = int(item_data['description'].split(',')[1].split(':')[1])
                range_data = full_data.iloc[start_idx:end_idx+1].copy()
                self.combined_track_data = pd.concat([self.combined_track_data, range_data], ignore_index=True)

            # 原有的圖表繪製代碼保持不變
            self.figure.clear()
            
            gs = self.figure.add_gridspec(3, 1, 
                                        height_ratios=[1, 1, 1], 
                                        hspace=0)
            
            self.axes = {
                'speed': self.figure.add_subplot(gs[0, 0]),
                'r_scale1': self.figure.add_subplot(gs[1, 0]),
                'r_scale2': self.figure.add_subplot(gs[2, 0]),
            }
            
            # 清除選中範圍的圖表
            for i, ax in enumerate(axes):
                ax.clear()
            
            # 定義要繪製的列和對應的軸
            plot_config = {
                'speed': ('G Speed', self.axes['speed']),
                'r_scale1': ('R Scale 1', self.axes['r_scale1']),
                'r_scale2': ('R Scale 2', self.axes['r_scale2'])
            }
            
            # 為每個勾選的範圍繪製對應的圖表
            for ax_name, (col_name, ax) in plot_config.items():
                if col_name in full_data.columns:
                    for item_data in checked_items:
                        label_name = item_data.get('label', '')
                        print(f"[plot_selected_ranges] 處理項目，label_name: {label_name}")
                        description = item_data['description']
                        range_id = item_data['id']
                        # 獲取標籤名稱，如果沒有則使用預設的 Run {range_id}
                        label_name = item_data.get('label', f'Run {range_id}')
                        
                        start_idx = int(description.split(',')[0].split(':')[1])
                        end_idx = int(description.split(',')[1].split(':')[1])
                        
                        # 獲取該範圍的數據並重設索引
                        range_data = full_data.iloc[start_idx:end_idx+1].copy()
                        range_data.reset_index(drop=True, inplace=True)
                        
                        # 在主圖表上繪製（使用重設後的索引和自定義標籤）
                        ax.plot(range_data.index, 
                               range_data[col_name], 
                               '-', 
                               linewidth=1, 
                               label=label_name)
                        
                        # 在選中範圍的圖表上繪製（使用相同的重設索引和自定義標籤）
                        selected_ax = axes[list(plot_config.keys()).index(ax_name)]
                        line = selected_ax.plot(
                            range_data.index,
                            range_data[col_name],
                            '-',
                            linewidth=1,
                            label=label_name
                        )[0]
                        print(f"[plot_selected_ranges] 添加選中範圍的線，label_name: {label_name}")
                    # 設置主圖表屬性
                    ax.set_title(col_name, 
                               fontsize=10,
                               fontfamily='sans-serif',
                               loc='left',
                               pad=10,
                               bbox=dict(
                                   facecolor='black',
                                   edgecolor='none',
                                   pad=3.0,
                                   alpha=1.0
                               ),
                               color='white')
                    ax.grid(True, alpha=0.3)
                    ax.tick_params(axis='both', labelsize=8)
                    if len(checked_items) > 1:
                        ax.legend(fontsize=8)
                    
                    # 設置選中範圍圖表的屬性
                    selected_ax = axes[list(plot_config.keys()).index(ax_name)]
                    selected_ax.set_title(col_name, fontsize=10)
                    selected_ax.grid(True)
                    selected_ax.set_xlabel('索引')
                    selected_ax.set_ylabel(col_name)
                    if len(checked_items) > 1:
                        selected_ax.legend()
            
            # 調整布局並更新圖表
            self.figure.tight_layout()
            canvas.figure.tight_layout()
            self.figure.canvas.draw()
            canvas.draw()
            
            # 繪製軌跡圖
            self.plot_track_for_ranges(checked_items, full_data, track_ax, track_canvas)
            
            print("\n=== Run資料輸出完成 ===")
            return True
            
        except Exception as e:
            print(f"繪製選中Run時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def plot_track_for_ranges(self, checked_items, full_data, track_ax, track_canvas):
        """繪製軌跡圖"""
        try:
            track_ax.clear()
            
            # 確定座標列名
            x_col = 'X' if 'X' in full_data.columns else 'Longitude'
            y_col = 'Y' if 'Y' in full_data.columns else 'Latitude'
            
            # 創建一個新的 DataFrame 來存儲第一個選中Run的數據
            combined_data = pd.DataFrame()
            
            # 反轉列表順序，使第一個選中的Run顯示在最上層
            reversed_items = list(reversed(checked_items))
            
            # 繪製每個選中Run的軌跡
            for index, item_data in enumerate(reversed_items):
                description = item_data['description']
                range_id = item_data['id']
                indices = {}
                for pair in description.split(','):
                    key, value = pair.split(':')
                    indices[key] = int(value)
                
                start_idx = indices['start_index']
                end_idx = indices['end_index']
                
                # 獲取該Run的數據並重設索引
                range_data = full_data.iloc[start_idx:end_idx+1].copy()
                range_data.reset_index(drop=True, inplace=True)
                
                # 只保存第一個選中Run的數據用於索引
                if index == len(reversed_items) - 1:  # 第一個選中的Run
                    combined_data = range_data
                
                # 使用重設後的索引繪製軌跡
                x_data = range_data[x_col]
                y_data = range_data[y_col]
                # 設置zorder，確保第一個選中的Run在最上層
                zorder = index + 1
                track_ax.plot(x_data, y_data, label=f'Run {range_id}', zorder=zorder)
            
            # 存儲第一個選中Run的數據供後續使用
            self.combined_track_data = combined_data
            
            # 設置軌跡圖屬性
            track_ax.set_title('位置軌跡圖')
            track_ax.legend()
            track_ax.grid(True)
            track_ax.set_aspect('equal', adjustable='datalim')
            
            # 更新軌跡圖
            track_canvas.draw()
            
        except Exception as e:
            print(f"繪製軌跡圖時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def _update_right_plot_value(self, plot_type, index, value, range_id):
        """更新主圖表上的Run標籤數值"""
        try:
            ax_mapping = {
                'speed': 'speed',
                'r_scale1': 'r_scale1',
                'r_scale2': 'r_scale2'
            }
            ax_name = ax_mapping.get(plot_type)
            if ax_name not in self.axes:
                print(f"警告：找不到圖表軸 {ax_name}")
                return
                
            ax = self.axes[ax_name]
            
            # 尋找對應的 item_data 以獲取自定義標籤
            if hasattr(self, 'current_checked_items'):
                item_data = next((item for item in self.current_checked_items 
                                if item['id'] == range_id), None)
                label_name = item_data.get('label', '') if item_data else ''
                print(f"[_update_right_plot_value] 找到對應的 item_data: {item_data}")
                print(f"[_update_right_plot_value] label_name: {label_name}")
            else:
                label_name = ''
                print(f"[_update_right_plot_value] 警告：找不到 current_checked_items")
                print(f"[_update_right_plot_value] 使用空白 label_name: {label_name}")
            
            # 尋找並更新Run標籤
            for text in ax.texts:
                if hasattr(text, 'range_id') and text.range_id == range_id:
                    # 根據數據類型設置不同的格式
                    if plot_type == 'speed':
                        print(f"[_update_right_plot_value] 更新速度標籤，使用 label_name: {label_name}")
                        text.set_text(f'{label_name}\n{value:.1f} km/h')
                    else:
                        print(f"[_update_right_plot_value] 更新其他標籤，使用 label_name: {label_name}")
                        text.set_text(f'{label_name}\n{value:.2f}')
                    break
            
            # 重繪圖表
            self.figure.canvas.draw_idle()
            
        except Exception as e:
            print(f"更新圖表數值時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
