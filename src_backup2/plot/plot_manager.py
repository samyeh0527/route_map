from matplotlib.figure import Figure
import numpy as np
import matplotlib.pyplot as plt
import warnings
import matplotlib as mpl
import pandas as pd
from PyQt5.QtWidgets import QApplication, QProgressDialog, QMessageBox
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
        self.is_dragging = False  # 初始化拖曳狀態
        # 設定滑鼠事件 (點擊 & 拖曳)
        self.figure.canvas.mpl_connect('button_press_event', self._FastDragPlot)
        self.figure.canvas.mpl_connect('motion_notify_event', self._FastDragPlot)
        self.figure.canvas.mpl_connect('button_release_event', self._FastDragPlot)
        #透過函式參數傳入
        self.combo_selection = None
        self._just_set_start_point = False

    def create_plots(self, highlight_index=None, highlight_range=None):
        """創建圖表，支持高亮顯示"""
        try:
            print("\n=== 開始創建圖表 ===")
            if not self.data_list:
                print("錯誤: 沒有數據")
                return
            
            # 清除起點設定
            #self.clear_start_point()
            for ax in self.axes.values():
                ax.clear()
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
                try:
                    if line is not None:
                        line.remove()
                except (NotImplementedError, ValueError):
                    pass
            self.crosshair_lines = []
            
            # 找到 create_plots 內部的這段迴圈並加上 try-except 保護
            for text_obj in self.value_texts:
                try:
                    if text_obj is not None:
                        text_obj.remove()
                except (NotImplementedError, ValueError, AttributeError):
                    pass  # 捕捉並忽略 Matplotlib 找不到 Artist 的錯誤
            self.value_texts = []
            
            # 清除圖表但保持起點資訊
            self.figure.clear()
            
            # 修改為3行1列的布局，只包含速度和R Scale圖表
            gs = self.figure.add_gridspec(3, 1, 
                                        height_ratios=[1, 1, 1],  # 將整體間距設為0，後續手動調整
                                        hspace=0)
            
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
        """繪製數據到指定的軸（已優化：完美綁定多 CSV 原始檔案名稱至圖例）"""
        try:
            if not self.data_list or all(df.empty for df in self.data_list):
                print("沒有有效資料可繪圖")
                return
                
            # 💡 核心新增：透過 PyQt5 全域尋找主視窗以獲取加載的真實 CSV 檔名清單
            from PyQt5.QtWidgets import QApplication
            from ui.map_viewer import MapViewer
            main_win = None
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, MapViewer):
                    main_win = widget
                    break
            
            # 如果能找到主視窗且有加載多個檔案的紀錄，則提取檔名；否則使用預設格式
            file_names = []
            if main_win and hasattr(main_win, 'loaded_files') and main_win.loaded_files:
                import os
                file_names = [os.path.basename(path) for path, _ in main_win.loaded_files]

            for i, data in enumerate(self.data_list):
                if column_name in data.columns:
                    if column_name == 'G Speed':
                        plot_title = 'G Speed'
                    elif column_name == 'R Scale 1':
                        plot_title = 'R Scale 1'
                    elif column_name == 'R Scale 2':
                        plot_title = 'R Scale 2'
                    else:
                        plot_title = column_name
                    
                    ax.set_title(plot_title, 
                               fontsize=10, 
                               fontfamily='sans-serif',
                               loc='left',
                               pad=10,
                               bbox=dict(facecolor='black', edgecolor='none', pad=3.0, alpha=1.0),
                               color='white')
                    
                    # 🎯 【精確填入位置 1】在全域合併模式下，將動態獲取的真實 CSV 檔名傳給 label
                    line_label = file_names[i] if i < len(file_names) else f'數據集 {i+1}'
                    
                    ax.plot(data.index, data[column_name], 
                           color=self.colors[i % len(self.colors)],
                           label=line_label)  # 👈 這裡填入 line_label 綁定檔名
                    
                    ax.tick_params(axis='both', labelsize=8)
                    ax.grid(True, alpha=0.3)
            
            # 🎯 畫完所有線條後，強制開啟該座標軸的圖例顯示，讓檔名在右上角呈現
            ax.legend(fontsize=8, loc='upper right')
            
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
            ax.set_title('軌跡圖', fontsize=10)
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
                        #plot_cache['highlight_line'].remove()
                        #plot_cache['highlight_line'] = None
                        plot_cache['highlight_line'].set_visible(False)
                    
                    # 清除高亮點
                    if 'highlight_point' in plot_cache and plot_cache['highlight_point']:
                        if isinstance(plot_cache['highlight_point'], (list, tuple)):
                            for artist in plot_cache['highlight_point']:
                                artist.remove()
                                plot_cache['highlight_point'].set_visible(False)
                        else:
                            plot_cache['highlight_point'].remove()
                            plot_cache['highlight_point'].set_visible(False)
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
        ax.set_title('位置軌跡', fontsize=8)
        ax.set_xlabel('經度', fontsize=9)
        ax.set_ylabel('緯度', fontsize=9)
        ax.grid(True)
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        ax.xaxis.set_major_locator(plt.MaxNLocator(6))
        ax.yaxis.set_major_locator(plt.MaxNLocator(8))
        ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.4f'))
        ax.yaxis.set_major_formatter(plt.FormatStrFormatter('%.4f'))

    def _on_plot_click(self, event):
        """處理主圖表點擊回調（已優化：採用 QTimer 延時解鎖，徹底阻斷滑鼠放開時的殘留抖動）"""
        if event.inaxes is None or event.xdata is None:
            return
        
        # --- 🛡️【安全防線：防震鎖啟用期間，拒絕任何事件污染】---
        if getattr(self, '_just_set_start_point', False):
            return

        # --- 【核心攔截：在時序圖表上點擊設定起點】 ---
        if getattr(self, 'is_setting_start_point', False):
            try:
                nearest_idx = int(round(event.xdata))
                
                from PyQt5.QtWidgets import QApplication
                from ui.map_viewer import MapViewer
                from PyQt5.QtCore import QTimer  # 引入定時器
                
                main_win = None
                for widget in QApplication.topLevelWidgets():
                    if isinstance(widget, MapViewer):
                        main_win = widget
                        break
                
                if main_win:
                    print(f"\n[DEBUG][START POINT VIA PLOT] 成功在時序圖上選定起點位置，索引: {nearest_idx}")
                    
                    # 1. 強制啟動防震狀態鎖
                    self._just_set_start_point = True
                    
                    # 執行設定起點
                    self.set_start_point(nearest_idx, main_win.track_ax, main_win.track_canvas)
                    
                    # 2. 立即將任何潛在的拖曳旗標歸零
                    self.is_dragging = False
                    
                    # 3. 傳入當前 ax 釋放 Matplotlib 焦點鎖
                    try:
                        event.canvas.release_mouse(event.inaxes)
                        print("[DEBUG][DRAG FIX] 已成功對 Canvas 呼叫 release_mouse(ax) 解鎖。")
                    except Exception as e_release:
                        print(f"[DEBUG][DRAG FIX] 呼叫 release_mouse 失敗: {e_release}")
                    
                    # 4. UI 狀態重置
                    main_win.is_setting_start_point = False
                    main_win.set_start_button.setText("設定起點")
                    self.is_setting_start_point = False
                    
                    # 5. 刷新畫布
                    self.figure.canvas.draw_idle()
                    print("[DEBUG][DRAG FIX] --- 起點邏輯安全退出，QTimer 防震保護啟動 ---")
                    
                    # ====== ✨【核心優化點：半秒鐘後自動解鎖】======
                    # 讓防震鎖在後台維持 500 毫秒，這段期間內任何滑鼠移動、放開、抖動都會被完全過濾
                    QTimer.singleShot(500, self._unlock_anti_shake)
                    
                    return  # 完美精確攔截
                    
            except Exception as e:
                print(f"在趨勢圖上設定起點時出錯: {str(e)}")
                self._just_set_start_point = False
                return

        # --- 【常規點擊連動邏輯】 ---
        try:
            nearest_idx = int(round(event.xdata))
            print(f"[DEBUG][_on_plot_click] 觸發常規點擊更新，目前點擊索引: {nearest_idx}")
            
            # 清除舊的標記點並更新軌跡圖
            self.update_track_point(nearest_idx, event.inaxes, event.canvas)
            
            if hasattr(self, 'discovered_ranges') and self.discovered_ranges:
                for range_info in self.discovered_ranges:
                    s_idx = range_info.get('start_index', range_info.get('start', 0))
                    e_idx = range_info.get('end_index', range_info.get('end', 0))
                    if s_idx <= nearest_idx <= e_idx:
                        print(f"[DEBUG][_on_plot_click] 點擊落在範圍 {range_info.get('range_number')} 內")
                        
            print(f"已更新軌跡圖上的點 class name _on_plot_clicked")
            
        except Exception as e:
            print(f"處理主圖表點擊回調時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def _unlock_anti_shake(self):
        """定時器專用回調：安全解除防震鎖"""
        self._just_set_start_point = False
        print("[DEBUG][QTimer] 500ms 隔離期滿，防震鎖已安全解鎖，圖表恢復自由常態。\n")


    def _update_main_plots_with_reset_index(self, index):
        """使用重設後的索引更新主圖表"""
        try:
            if not hasattr(self, 'combined_track_data'):
                return
            
            data = self.combined_track_data
            #print(f"[_update_main_plots_with_reset_index] combined track data : \n{data}")
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
                        print(f"[_update_main_plots_with_reset_index] 更新數值標籤，value: {value}")
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
        """清除所有高亮標記（全面防禦防崩潰版本）"""
        try:
            # 1. 安全清除資訊文字
            if hasattr(self, 'info_text') and self.info_text is not None:
                try:
                    self.info_text.remove()
                except (NotImplementedError, ValueError, AttributeError):
                    pass
                self.info_text = None
            
            # 2. 安全清除十字虛線和標記點 (crosshair_lines)
            if hasattr(self, 'crosshair_lines') and self.crosshair_lines:
                for line in self.crosshair_lines:
                    try:
                        if line is not None:
                            line.remove()
                    except (NotImplementedError, ValueError, AttributeError):
                        pass  # 忽略已被 Matplotlib 釋放的物件
                self.crosshair_lines = []
            
            # 3. 安全清除數值文字標籤 (value_texts)
            if hasattr(self, 'value_texts') and self.value_texts:
                for text_obj in self.value_texts:
                    try:
                        if text_obj is not None:
                            text_obj.remove()
                    except (NotImplementedError, ValueError, AttributeError):
                        pass
                self.value_texts = []
                
            # 4. 安全清除位置軌跡圖上的點 (track_point)
            if hasattr(self, 'track_point') and self.track_point is not None:
                try:
                    # 判斷如果是 list/tuple 則遍歷移除
                    if isinstance(self.track_point, (list, tuple)):
                        for tp in self.track_point:
                            if tp is not None: tp.remove()
                    else:
                        self.track_point.remove()
                except (NotImplementedError, ValueError, AttributeError):
                    pass
                self.track_point = None

            # 5. 安全清除位置十字交叉線 (position_crosshair_lines)
            if hasattr(self, 'position_crosshair_lines') and self.position_crosshair_lines:
                for line in self.position_crosshair_lines:
                    try:
                        if line is not None:
                            line.remove()
                    except (NotImplementedError, ValueError, AttributeError):
                        pass
                self.position_crosshair_lines = []

        except Exception as e:
            # 即使外部有未預期的錯誤，也僅打印 debug 訊息，不中斷 PyQt 主線程點擊事件
            print(f"[DEBUG] _clear_all_highlights 執行防禦性跳過: {str(e)}")

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
            
            x_range = x_max - x_min
            y_range = y_max - y_min

            # 限制最小範圍，避免過度縮小
            min_x_range = 0.001
            min_y_range = 0.001
            if x_range * scale_factor < min_x_range:
                return
            if y_range * scale_factor < min_y_range:
                return

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
    def _FastDragPlot(self, event):
        """快速拖動圖表 (支援滑鼠點擊拖曳)（已優化：移除了會提早解鎖的舊代碼，改由 QTimer 控鎖）"""
        try:
            if event.inaxes is None:
                return

            ax = event.inaxes

            from PyQt5.QtWidgets import QApplication
            from ui.map_viewer import MapViewer
            
            main_win = None
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, MapViewer):
                    main_win = widget
                    break

            is_setting = main_win and getattr(main_win, 'is_setting_start_point', False)

            # --- 滑鼠按下 (開始拖曳) ---
            if event.name == 'button_press_event' and event.button == 1:
                if is_setting or getattr(self, '_just_set_start_point', False):
                    return
                self.is_dragging = True
                self.x0, self.y0 = event.xdata, event.ydata
                self.xlim0, self.ylim0 = ax.get_xlim(), ax.get_ylim()

            # --- 滑鼠移動 (執行拖曳) ---
            elif event.name == 'motion_notify_event' and getattr(self, "is_dragging", False):
                if is_setting or getattr(self, '_just_set_start_point', False):
                    self.is_dragging = False
                    return
                
                if event.xdata is None or event.ydata is None:
                    return
                
                dx = self.x0 - event.xdata
                dy = self.y0 - event.ydata

                ax.set_xlim(self.xlim0[0] + dx, self.xlim0[1] + dx)
                ax.set_ylim(self.ylim0[0] + dy, self.ylim0[1] + dy)
                self.figure.canvas.draw_idle()

            # --- 滑鼠釋放 (停止拖曳) ---
            elif event.name == 'button_release_event' and event.button == 1:
                self.is_dragging = False
                # 【優化】移除原本在這裡會提早將 _just_set_start_point 設為 False 的代碼
                # 完全交由上方 _on_plot_click 的 QTimer 延時解鎖，確保安全

        except Exception as e:
            print(f"拖拉圖表時出錯: {str(e)}") 
    
    
    def enable_start_point_selection(self):
        """啟用起點選擇模式"""
        self.is_setting_start_point = True
        print("請在位置軌跡圖上選擇起點")

    def set_start_point(self, index, track_ax=None, track_canvas=None):
        """
        設定新的單圈起點位置（已精簡：全域統一為多檔/列表架構，移除非必要 DataFrame 盲抓）
        """
        try:
            index = int(index)
            
            # 因為現在一定都是 list 結構，直接安全拿取第 1 筆檔案作為基準即可
            if hasattr(self, 'data_list') and isinstance(self.data_list, list) and len(self.data_list) > 0:
                data = self.data_list[0]
            else:
                print("[set_start_point] 錯誤：找不到任何已載入的數據列表，取消設定起點。")
                return

            if index < 0 or index >= len(data):
                print(f"[set_start_point] 錯誤：選定的索引 {index} 超出資料範圍 (0 - {len(data)-1})")
                return

            # 儲存起點資訊
            self.start_point = index
            self.has_start_point_set = True
            self.start_point_data = {'x': index}
            
            x_col = 'X' if 'X' in data.columns else 'Longitude'
            y_col = 'Y' if 'Y' in data.columns else 'Latitude'
            x = data[x_col].iloc[index]
            y = data[y_col].iloc[index]
            
            # 自動從主視窗補齊畫布元件參照
            from PyQt5.QtWidgets import QApplication
            from ui.map_viewer import MapViewer
            main_win = None
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, MapViewer):
                    main_win = widget
                    break
                    
            if track_ax is None and main_win is not None:
                track_ax = main_win.track_ax
            if track_canvas is None and main_win is not None:
                track_canvas = main_win.track_canvas

            if track_ax is not None and track_canvas is not None:
                self.update_track_point(index, track_ax, track_canvas)
            
            # 重新繪製起點線
            if hasattr(self, 'start_point_line') and self.start_point_line:
                for line in self.start_point_line:
                    try:
                        if line is not None: line.remove()
                    except (NotImplementedError, ValueError, AttributeError):
                        pass
            self.start_point_line = []
            
            if self.axes:
                for ax_name, ax_obj in self.axes.items():
                    if ax_obj is not None:
                        line = ax_obj.axvline(x=index, color='green', linestyle='--', linewidth=2)
                        self.start_point_line.append(line)
                self.figure.canvas.draw_idle()
            
            if track_ax is not None and track_canvas is not None:
                try:
                    y_range = track_ax.get_ylim()[1] - track_ax.get_ylim()[0]
                    fig_height_inches = track_ax.figure.get_size_inches()[1]
                    one_cm_data_units = (y_range / (fig_height_inches * 2.54))
                    track_line = track_ax.plot([x, x], [y - one_cm_data_units, y + one_cm_data_units], 
                                             color='green', linestyle='--', linewidth=2)[0]
                    self.start_point_line.append(track_line)
                    track_canvas.draw_idle()
                except Exception as e_track:
                    print(f"[set_start_point] 在軌跡圖上畫綠色標記線時跳過: {e_track}")
            
            # 呼叫並執行單圈探勘切割
            self.analyze_ranges(index, self.data_list)
            print(f"起點已成功設定在索引: {index}")
            
        except Exception as e:
            print(f"設定起點時出錯: {str(e)}")
    
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
                    try:
                        # 加上防禦：確保物件存在且未被提早清除
                        if line is not None:
                            line.remove()
                    except (NotImplementedError, ValueError):
                        pass  # 捕捉並忽略 Matplotlib 無法移除的底層錯誤
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
                    # 避免計算空的距離數組
            if data[x_col].isna().all() or data[y_col].isna().all():
                print("警告：所有座標數據為 NaN")
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
            #nearest_idx = distances.idxmin()
            nearest_idx = distances.idxmin() if not distances.empty else None
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
            if hasattr(self, 'combined_track_data') and self.combined_track_data is not None:
                data = self.combined_track_data
                if data.empty:
                    print("警告: combined_track_data 為空")
                    return
                print(f"使用 combined_track_data，數據長度: {len(data)} 筆")
                
                if not hasattr(self, 'current_checked_items') or not self.current_checked_items:
                    print("警告: 沒有選中的範圍數據")
                    return
                    
                # 獲取第一個範圍的長度
                first_range = self.current_checked_items[0]
                description = first_range['description']
                start_idx = int(description.split(',')[0].split(':')[1])
                end_idx = int(description.split(',')[1].split(':')[1])
                first_range_length = end_idx - start_idx + 1
                
                # 檢查索引是否超出第一個範圍
                if index >= first_range_length:
                    print(f"警告: 索引 {index} 超出第一個範圍長度 {first_range_length}")
                    return
                    
                print(f"使用第一個範圍的索引: {index}")
                
            elif self.data_list and self.data_list[0] is not None:
                data = self.data_list[0]
                if data.empty:
                    print("警告: data_list[0] 為空")
                    return
                print(f"使用原始數據，數據長度: {len(data)} 筆")
                print(f"使用原始索引: {index}")
            else:
                print("警告: 沒有可用的數據")
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
                if hasattr(self, 'combined_track_data') and self.combined_track_data is not None:
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

    def analyze_ranges(self, start_index, current_data=None):
        """分析數據範圍（已修正：正式加入 current_data 接口，解決 positional arguments 數量不符崩潰）"""
        try:
            # 創建進度對話框
            progress = QProgressDialog("多檔案單圈同步分析中...", None, 0, 0)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle("請稍候")
            progress.setCancelButton(None)
            progress.setMinimumDuration(0)
            progress.setWindowFlags(progress.windowFlags() & ~Qt.WindowCloseButtonHint)
            progress.show()
            QApplication.processEvents()
            
            # 1. 統一將數據源整理為一個 DataFrame 列表，以便使用統一的邏輯進行遍歷
            all_dfs = self.data_list if isinstance(self.data_list, list) else [self.data_list]
            
            # 2. 以點擊指定的 start_index，從第一個檔案中提取基準起點的經緯度坐標
            ref_data = all_dfs[0]
            x_col_ref = 'X' if 'X' in ref_data.columns else 'Longitude'
            y_col_ref = 'Y' if 'Y' in ref_data.columns else 'Latitude'
            start_x = ref_data[x_col_ref].iloc[start_index]
            start_y = ref_data[y_col_ref].iloc[start_index]
            
            tolerance = 0.00004  # 座標容差 (約 4-5 公尺)
            ranges = []
            global_run_counter = 1  # 全域 Run 編號計數器，讓所有檔案的 Run 序號自然排下去
            
            print(f"\n[DEBUG MULTI-FILE RANGE] 基準起點坐標設為: ({start_x}, {start_y})")
            
            # 3. 核心改變：逐一對加載的每一個 CSV 檔案執行單圈切分
            for file_idx, data in enumerate(all_dfs):
                print(f"[DEBUG MULTI-FILE RANGE] 開始分析第 {file_idx + 1} 筆 CSV 檔案...")
                
                # 確保時間欄位格式正確
                data['Time'] = pd.to_datetime(data['Time'])
                x_col = 'X' if 'X' in data.columns else 'Longitude'
                y_col = 'Y' if 'Y' in data.columns else 'Latitude'
                
                last_match_index = None
                in_range = False
                
                # 遍歷當前檔案的每一筆數據點
                for i in range(len(data)):
                    if i % 200 == 0:
                        progress.setLabelText(f"正在分析第 {file_idx + 1}/{len(all_dfs)} 筆檔案...\n已處理: {i}/{len(data)} 筆數據")
                        QApplication.processEvents()
                    
                    current_x = data[x_col].iloc[i]
                    current_y = data[y_col].iloc[i]
                    current_time = data['Time'].iloc[i]
                    
                    # 計算當前位置是否通過設定的起點範圍
                    x_match = abs(current_x - start_x) <= tolerance
                    y_match = abs(current_y - start_y) <= tolerance
                    
                    if x_match and y_match:
                        if not in_range:
                            if last_match_index is not None:
                                time_diff = (current_time - data['Time'].iloc[last_match_index]).total_seconds()
                                
                                # 時間鎖防禦：大於 5 秒才算完整的一圈，避免同一次通過起點時重複觸發
                                if time_diff >= 5:
                                    data_count = i - last_match_index + 1
                                    
                                    hours = int(time_diff // 3600)
                                    minutes = int((time_diff % 3600) // 60)
                                    seconds = int(time_diff % 60)
                                    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                                    
                                    print(f"-> 檔案 {file_idx + 1} 內找到 Run {global_run_counter}: 索引 {last_match_index} 到 {i} (筆數: {data_count}, 時間: {time_str})")
                                    
                                    # 將單圈結果封裝，帶有 global_run_counter 與所屬的 file_index 標記
                                    ranges.append({
                                        'range_number': global_run_counter,
                                        'start_index': last_match_index,
                                        'end_index': i,
                                        'start_time': data['Time'].iloc[last_match_index],
                                        'end_time': current_time,
                                        'duration': time_diff,
                                        'duration_str': time_str,
                                        'data_count': data_count,
                                        'file_index': file_idx  # 紀錄此 Run 是屬於哪一個檔案
                                    })
                                    global_run_counter += 1
                                    in_range = True
                        last_match_index = i
                    else:
                        if in_range:
                            in_range = False
            
            progress.close()
            
            # 將最終所有檔案合併算出的單圈列表，傳回主視窗刷新 QListWidget 清單
            if self.range_update_callback:
                self.range_update_callback(ranges)
                
            # 將探勘結果暫存於記憶體，供常規點擊高亮判定使用
            self.discovered_ranges = ranges
            return ranges
            
        except Exception as e:
            if 'progress' in locals():
                progress.close()
            print(f"分析多檔案範圍時出錯: {str(e)}")
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
        """在主圖表上高亮顯示指定Run（已修正：打勾瞬間自動精確反查多檔案檔名標籤，消滅無效警告）"""
        try:
            # 1. 獲取全域主視窗的檔案清單，用來提取 CSV 原始檔名
            from PyQt5.QtWidgets import QApplication
            from ui.map_viewer import MapViewer
            main_win = None
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, MapViewer):
                    main_win = widget
                    break
            
            file_names = []
            if main_win and hasattr(main_win, 'loaded_files') and main_win.loaded_files:
                import os
                file_names = [os.path.basename(path) for path, _ in main_win.loaded_files]

            # 2. 精確動態計算 label_name 標籤文字
            label_name = f'Run {range_id}'  # 預設基礎名稱
            
            # 優先級 1：如果記憶體映射表存在，直接反查出它屬於第幾個 CSV 檔案
            if hasattr(self, 'range_index_mapping') and range_id in self.range_index_mapping:
                file_idx = self.range_index_mapping[range_id].get('file_index', 0)
                if file_idx < len(file_names):
                    label_name = f'Run {range_id} ({file_names[file_idx]})'
                    
            # 優先級 2：如果映射表還沒建立（例如刚載入），嘗試從當前勾選清單中尋找
            elif hasattr(self, 'current_checked_items') and self.current_checked_items:
                item_data = next((item for item in self.current_checked_items if item['id'] == range_id), None)
                if item_data and 'label' in item_data:
                    label_name = item_data['label']
            
            print(f"[highlight_range] 成功為單圈高亮配置精確標籤: {label_name}")
            
            # 以下維持您原本的黃色區塊繪製邏輯
            highlights = []
            text_labels = []
            colors = ['#FFD700', '#98FB98', '#87CEFA', '#DDA0DD', '#F08080']
            color = colors[range_id % len(colors)]
            
            if not self.axes:
                return
            
            for i, (ax_name, ax) in enumerate(self.axes.items()):
                if ax is None:
                    continue
                    
                # 繪製黃色/彩色透明高亮背景
                highlight = ax.axvspan(start_index, end_index, alpha=0.2, color=color, zorder=1)
                highlights.append(highlight)
                
                # 配置文字標籤位置與黑框白底樣式
                x_pos = end_index
                y_pos = 0.85
                label_type = 'speed' if i == 0 else ('r_scale1' if i == 1 else 'r_scale2')

                text = ax.text(x_pos, y_pos, 
                             label_name,  # 👈 使用我們精確反查出的 line_label/label_name
                             horizontalalignment='right',
                             verticalalignment='top',
                             transform=ax.get_xaxis_transform(),
                             bbox=dict(facecolor='white', edgecolor=color, alpha=0.8, boxstyle='round,pad=0.5'),
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
            import traceback
            traceback.print_exc()


    def remove_range_highlight(self, range_id):
        """移除指定Run的高亮顯示"""
        try:
            if range_id in self.range_highlights:
                # 移除所有子圖中的高亮背景區塊
                for highlight in self.range_highlights[range_id]['highlights']:
                    try:
                        if highlight is not None:
                            highlight.remove()
                    except (NotImplementedError, ValueError):
                        pass
                # 移除所有文字標籤
                for label in self.range_highlights[range_id]['labels']:
                    try:
                        if label is not None:
                            label.remove()
                    except (NotImplementedError, ValueError):
                        pass
                del self.range_highlights[range_id]
                
        except Exception as e:
            print(f"移除Run高亮時出錯: {str(e)}")

    def plot_selected_ranges(self, checked_items, full_data, axes, canvas, track_ax, track_canvas):
        """繪製選中 Run 的圖表（已徹底修正：顏色由 range_id 絕對綁定，確保雙邊線條顏色永久統一）"""
        try:
            self.current_checked_items = checked_items
            print(f"[plot_selected_ranges] current_checked_items: {self.current_checked_items}")
            
            print("\n=== 重新編排索引後的 Run 詳細資料 ===")

            # 1. 呼叫 extract_range_data 獲取切片數據列表
            range_info_list = self.extract_range_data(checked_items, full_data)
            
            if not range_info_list:
                print("[plot_selected_ranges] 錯誤：提取的單圈範圍數據為空")
                return False

            self.figure.clear()
            gs = self.figure.add_gridspec(3, 1, height_ratios=[1, 1, 1], hspace=0)
            
            self.axes = {
                'speed': self.figure.add_subplot(gs[0, 0]),     
                'r_scale1': self.figure.add_subplot(gs[1, 0]),  
                'r_scale2': self.figure.add_subplot(gs[2, 0]),  
            }
            
            for ax in axes:
                ax.clear()
            
            plot_config = {
                'speed': ('G Speed', self.axes['speed'], 0),
                'r_scale1': ('R Scale 1', self.axes['r_scale1'], 1),
                'r_scale2': ('R Scale 2', self.axes['r_scale2'], 2)
            }
            
            # 獲取主視窗檔案清單以提取真實檔名
            from PyQt5.QtWidgets import QApplication
            from ui.map_viewer import MapViewer
            main_win = None
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, MapViewer):
                    main_win = widget
                    break
            
            file_names = []
            if main_win and hasattr(main_win, 'loaded_files') and main_win.loaded_files:
                import os
                file_names = [os.path.basename(path) for path, _ in main_win.loaded_files]
            
            # 3. 核心動態多軌繪製邏輯
            for ax_name, (col_name, ax, ax_idx) in plot_config.items():
                for index, range_df in enumerate(range_info_list):
                    if col_name in range_df.columns:
                        item_data = checked_items[index]
                        range_id = item_data['id']
                        
                        # 記憶體反查原始檔名
                        file_idx = 0
                        if hasattr(self, 'range_index_mapping') and range_id in self.range_index_mapping:
                            file_idx = self.range_index_mapping[range_id].get('file_index', 0)
                        
                        origin_file_name = file_names[file_idx] if file_idx < len(file_names) else f"檔案 {file_idx + 1}"
                        line_label = f"Run {range_id} ({origin_file_name})"
                        
                        # ✨【顏色統一修正點 1】線條顏色由 range_id 決定，不再受勾選項目先後順序影響
                        line_color = self.colors[(range_id - 1) % len(self.colors)]
                        
                        # 3a. 繪製主圖表線條
                        ax.plot(range_df.index, range_df[col_name], '-', linewidth=1, color=line_color, label=line_label)

                        # 3b. 同步更新輔助子圖表軸
                        if ax_idx < len(axes):
                            axes[ax_idx].plot(range_df.index, range_df[col_name], '-', linewidth=1, color=line_color, label=line_label)
                    else:
                        print(f"[plot_selected_ranges] 提示：Run {checked_items[index]['id']} 缺少 {col_name} 欄位，跳過線條繪製")

                # 圖表外觀美化
                ax.set_title(col_name, 
                           fontsize=10,
                           fontfamily='sans-serif',
                           loc='left',
                           pad=10,
                           bbox=dict(facecolor='black', edgecolor='none', pad=3.0, alpha=1.0),
                           color='white')
                ax.grid(True, alpha=0.3)
                ax.tick_params(axis='both', labelsize=8)
                ax.legend(fontsize=8, loc='upper left')
                
                # 設定選中範圍子圖表的外部屬性
                selected_ax = axes[ax_idx]
                selected_ax.set_title(col_name, fontsize=10, loc='left', pad=10)
                selected_ax.grid(True)
                selected_ax.set_xlabel('索引')
                selected_ax.set_ylabel(col_name)
                selected_ax.legend(loc='upper left', fontsize=8)
            
            self.figure.tight_layout()
            canvas.figure.tight_layout()
            self.figure.canvas.draw()
            canvas.draw()
            
            # 7. 呼叫多色重疊軌跡直繪方法
            self.plot_track_for_ranges_direct(range_info_list, checked_items, track_ax, track_canvas)
            
            print("\n=== 多檔案多單圈時序圖表與軌跡重疊渲染完成 ===")
            return True
            
        except Exception as e:
            print(f"繪製選中 Run 時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
    def plot_track_for_ranges_direct(self, range_info_list, checked_items, track_ax, track_canvas):
        """
        直接為選中的多個單圈範圍繪製重疊的位置軌跡圖。
        （已修正：顏色由 range_id 絕對綁定，確保與主時序圖顏色完美統一對齊）
        """
        try:
            if not track_ax or not track_canvas:
                print("[plot_track_for_ranges_direct] 警告：軌跡畫布元件不存在，跳過繪製")
                return
            
            # 1. 先清空原本的地圖/軌跡圖軸
            track_ax.clear()
            
            print("[plot_track_for_ranges_direct] 開始繪製多單圈重疊軌跡...")
            
            # 2. 迭代繪製每個單圈的經緯度軌跡
            for index, range_df in enumerate(range_info_list):
                if 'Longitude' in range_df.columns and 'Latitude' in range_df.columns:
                    item_data = checked_items[index]
                    range_id = item_data['id']
                    label_name = item_data.get('label', f'Run {range_id}')
                    
                    # ✨【顏色統一修正點 2】地圖軌跡線與起點圓點，完全使用與上方圖表相同的絕對 range_id 配色
                    track_color = self.colors[(range_id - 1) % len(self.colors)]
                    
                    # 繪製單圈軌跡線
                    track_ax.plot(
                        range_df['Longitude'], 
                        range_df['Latitude'], 
                        '-', 
                        linewidth=2, 
                        color=track_color,  # 👈 使用絕對綁定色
                        label=label_name
                    )
                    
                    # 標註該圈的起點（用圓點標示）
                    if len(range_df) > 0:
                        track_ax.scatter(
                            range_df['Longitude'].iloc[0], 
                            range_df['Latitude'].iloc[0], 
                            color=track_color,  # 👈 同步圓點顏色
                            marker='o', 
                            s=40, 
                            zorder=5
                        )
                else:
                    print(f"[plot_track_for_ranges_direct] 警告：第 {index+1} 組數據缺少 Longitude 或 Latitude 欄位")
            
            # 3. 圖表美化、比例尺對齊與標籤
            track_ax.set_title("選定單圈 - 重疊軌跡對比", fontsize=10, pad=10)
            track_ax.set_xlabel("經度 (Longitude)")
            track_ax.set_ylabel("緯度 (Latitude)")
            track_ax.grid(True, alpha=0.4)
            
            # 強制維持經緯度 1:1 地理比例，避免地圖變形
            track_ax.set_aspect('equal', adjustable='datalim')
            
            # 如果有多個 Run 則顯示圖例
            if len(range_info_list) > 1:
                track_ax.legend(loc='best', fontsize=9)
            
            # 4. 刷新畫布
            track_canvas.draw()
            print("[plot_track_for_ranges_direct] 重疊軌跡圖更新成功！")
            
        except Exception as e:
            print(f"[plot_track_for_ranges_direct] 繪製多圈軌跡時發生錯誤: {str(e)}")
            import traceback
            traceback.print_exc()
    def extract_range_data(self, checked_items, full_data):
        """從全域數據中提取選定的範圍數據，並完美保留多數據集結構"""
        try:
            print(f"[DEBUG] [extract_range_data] 開始提取數據，checked_items 數量: {len(checked_items)}")
            
            # 用於存儲切片後的所有單圈 DataFrame 串列
            extracted_dfs = []
            self.range_index_mapping = {}  # 紀錄對齊映射關係
            
            for index, item_data in enumerate(checked_items):
                description = item_data['description']
                range_id = item_data['id']
                
                # 解析起止索引
                indices = {}
                for pair in description.split(','):
                    key, value = pair.split(':')
                    indices[key] = int(value)
                
                start_idx = indices['start_index']
                end_idx = indices['end_index']
                
                # --- 【關鍵動態路由邏輯】 ---
                # 判定當前勾選的範圍應該從哪一個原始 DataFrame 中提取
                if isinstance(full_data, list):
                    # 在多檔案情況下，按 checked_items 的順序對應到對應的檔案 DataFrame
                    # 如果 checked_items 數量與 full_data 長度一致，則 index 就是對應檔案的 index
                    file_idx = index if index < len(full_data) else 0
                    source_df = full_data[file_idx]
                    print(f"[DEBUG] Run {range_id} 對應到多檔案列表中的第 {file_idx + 1} 筆檔案")
                else:
                    source_df = full_data
                
                # 安全切片提取
                range_df = source_df.iloc[start_idx:end_idx + 1].copy()
                range_df.reset_index(drop=True, inplace=True)
                
                # 保存原始索引映射關係，供後續點擊連動還原
                self.range_index_mapping[range_id] = {
                    'original_start': start_idx,
                    'original_end': end_idx,
                    'file_index': index if isinstance(full_data, list) else 0
                }
                
                extracted_dfs.append(range_df)
            
            print(f"[DEBUG] 成功提取 {len(extracted_dfs)} 組單圈數據集")
            return extracted_dfs
            
        except Exception as e:
            print(f"提取範圍數據時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            return []



    def plot_track_for_ranges(self, checked_items, full_data, track_ax, track_canvas):
        """繪製多單圈重疊軌跡圖（完美支援多數據集對比）"""
        try:
            track_ax.clear()
            
            # 首先提取所有選中 Run 的獨立 DataFrame 列表
            # 此時 range_data_list 的長度會與勾選的範圍數量完全一致！
            range_data_list = self.extract_range_data(checked_items, full_data)
            
            if not range_data_list:
                print("[plot_track_for_ranges] 警告：無有效切片數據可供繪製")
                return
                
            # 遍歷提取出來的每一組數據集並分層繪製（疊圖）
            for index, item_data in enumerate(checked_items):
                if index >= len(range_data_list):
                    break
                    
                range_id = item_data['id']
                range_df = range_data_list[index]
                
                # 自動偵測經緯度欄位名稱
                x_col = 'X' if 'X' in range_df.columns else 'Longitude'
                y_col = 'Y' if 'Y' in range_df.columns else 'Latitude'
                
                x_data = range_df[x_col]
                y_data = range_df[y_col]
                
                # 分層繪製各組數據，並貼上對應的標籤
                zorder = index + 1
                track_ax.plot(x_data, y_data, label=f'Run {range_id}', zorder=zorder)
                print(f"-> 已成功繪製數據集: Run {range_id}，總點數: {len(range_df)}")
            
            # 核心緩存：保存第一組被選中的 Run 作為點擊對齊的主參照物
            self.combined_track_data = range_data_list[0]
            
            # 重新配置圖表外觀與圖例
            track_ax.set_title('位置軌跡圖 (單圈重製對比)')
            track_ax.legend()
            track_ax.grid(True)
            track_ax.set_aspect('equal', adjustable='datalim')
            
            # 刷新畫布
            track_canvas.draw()
            print("=== 多數據集單圈重製圖表更新成功 ===")
            
        except Exception as e:
            print(f"繪製多單圈軌跡圖時出錯: {str(e)}")
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

    def apply_dsp_filter(self, filter_type="WMA", window_size=10):
        """
        全域統一 DSP 數位訊號處理路由控制中心
        支援多檔案 List[DataFrame] 架構，計算後自動同步刷新雙邊畫布
        
        參數:
            filter_type (str): 濾波器類型，支援 "WMA" (加權移動平均), "EMA" (指數移動平均)
            window_size (int): 濾波階數 / 滑動視窗大小
        """
        # 1. 基礎安全防禦
        if not self.data_list:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("警告")
            msg_box.setText("目前沒有已載入的數據，無法進行 DSP 濾波運算。")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
            return

        # 2. 還原原始數據防線：若視窗大小設為 0 或 1，視為不濾波，直接重新渲染原始圖表
        if window_size <= 1:
            print(f"[DSP] 偵測到參數 <= 1，主動恢復顯示原始未濾波數據。")
            self.create_plots()
            self._sync_main_win_track()
            return

        try:
            print(f"\n[DSP RUNNER] 啟動數位訊號處理核心 ─── 類型: {filter_type}, 階數: {window_size}")
            target_columns = ['R Scale 1', 'R Scale 2']  # 指定需要被低通平滑濾波的高頻噪訊欄位

            # 3. 自動遍歷目前記憶體中所有的 CSV 數據集 (List 結構)
            for file_idx, df in enumerate(self.data_list):
                if df is None or df.empty:
                    continue
                
                # 建立一個臨時儲存經濾波處理後的新 DataFrame 容器
                # 為了避免各欄位濾波長度縮減退化，在迴圈內動態對齊
                min_offset = 0
                temp_filtered_series = {}

                for scale in target_columns:
                    if scale in df.columns:
                        series = df[scale].to_numpy()
                        
                        # ========================================================
                        # 核心分流分組路由 1：加權移動平均 (WMA)
                        # ========================================================
                        if filter_type == "WMA":
                            weights = np.arange(1, window_size + 1)
                            weights_sum = weights.sum()
                            # 離散摺積運算
                            filtered_values = np.convolve(series, weights[::-1], mode='valid') / weights_sum
                            offset = len(df) - len(filtered_values)
                            min_offset = max(min_offset, offset)
                            temp_filtered_series[scale] = filtered_values

                        # ========================================================
                        # 核心分流分組路由 2：指數移動平均 (EMA) -> 反應速度快、無縫相容
                        # ========================================================
                        elif filter_type == "EMA":
                            # 利用 Pandas 內建高度優化的 ewm (Exponential Weighted Moving) 進行無損計算
                            # span=window_size 代表等效滑動視窗大小
                            filtered_values = df[scale].ewm(span=window_size, adjust=False).mean().to_numpy()
                            # EMA 特性為原長度輸出，因此不產生邊緣縮減對齊偏移 (offset=0)
                            temp_filtered_series[scale] = filtered_values
                            
                        # ========================================================
                        # (未來可擴充位置)：例如 Savitzky-Golay (SG) 濾波或卡爾曼濾波
                        # ========================================================
                        # elif filter_type == "SG":
                        #     from scipy.signal import savgol_filter
                        #     temp_filtered_series[scale] = savgol_filter(series, window_length=window_size, polyorder=2)

                # 4. 資料長度與時間軸硬性裁剪對齊 (防止多檔案長度退化導致繪圖崩潰)
                if temp_filtered_series:
                    # 根據計算得出的最大 offset 進行 iloc 裁切
                    aligned_df = df.iloc[min_offset:].copy()
                    
                    # 將各演算法算好的平滑陣列，精確寫入對齊後的 DataFrame 中
                    for scale, values in temp_filtered_series.items():
                        # 如果演算法有縮減長度（如 WMA），values 的長度理應完美等於 len(aligned_df)
                        # 如果演算法是原長度（如 EMA），我們需要對 values 進行對應切片以貼合 aligned_df
                        if len(values) == len(df):
                            aligned_df[scale] = values[min_offset:]
                        else:
                            aligned_df[scale] = values
                    
                    # 重設相對索引，確保點擊高亮、雙畫布絕對索引同步機制不脫節
                    aligned_df.reset_index(drop=True, inplace=True)
                    
                    # 覆蓋寫回全域資料列表
                    self.data_list[file_idx] = aligned_df
                    print(f"[DSP] 第 {file_idx + 1} 筆 CSV 檔案【{filter_type}】濾波與索引重對齊完成。")

            # 5. 數據清洗完畢，強制觸發畫布重新渲染
            self.figure.clear()
            self.create_plots()  # 重刷 3x1 主時序圖
            self._sync_main_win_track()  # 重刷底部位置地圖
            
            print(f"[DSP SUCCESS] 全模組數據已成功切換為 {filter_type} 平滑曲線並重新渲染畫布。\n")

        except Exception as e:
            print(f"[DSP ROUTER ERROR] 濾波執行分支失敗: {e}")
            import traceback
            traceback.print_exc()

    def _sync_main_win_track(self):
        """內部輔助方法：自動向外尋找主視窗並重繪地圖軌跡"""
        from PyQt5.QtWidgets import QApplication
        from ui.map_viewer import MapViewer
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, MapViewer):
                widget.plot_track_mulit()
                break
    def set_combo_selection(self, selection):
        self.combo_selection = selection
           
    def Debug_csv(self,data,name):
        df = pd.DataFrame(data)
        df.to_csv(f'{name}.csv', index=False, encoding='utf-8-sig')
    
    