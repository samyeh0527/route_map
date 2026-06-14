根據您所提供修正後的最新原始碼（包含為了解決 Matplotlib 事件錯位、`is_dragging` 狀態沾黏、多檔案數據集分流、以及採用 PyQt5 `QTimer` 延時防震盾等核心 Bug 的最終演進版本），為您整理並撰寫出一份完整且結構嚴謹的系統功能與技術規格書（`spec.md`）。

---

# 系統規格書 (spec.md) - 路線圖檢視與遙測分析系統

本文件詳述「路線圖檢視器」系統的軟體架構、自訂自適應 UI 元件、多檔案路由管理、雙向數據連動機制以及 Matplotlib 狀態機防顫處理之技術規格。

---

## 1. 系統架構與基本資訊

本系統是一款基於 **PyQt5** 與 **Matplotlib** 建構的專業車輛遙測（Telemetry）數據可視化軟體。支援單一或多個跨視聯（CSV）軌跡數據導入，提供即時的時序圖形交互、動態單圈切割與 WMA（加權移動平均）濾波分析。

### 檔案模組分工

| 檔案名稱 | 系統定位 | 核心職責 |
| --- | --- | --- |
| **`main.py`** | 應用程式進入點 | 初始化全域環境、強制中文字體對齊、指定 `Qt5Agg` 繪圖後端並啟動主視窗。 |
| **`overlay_widget.py`** | 異步狀態提示元件 | 提供異步或耗時運算（如 WMA 濾波、單圈分析）時的半透明遮罩層。 |
| **`map_viewer.py`** | 主視窗控制總管 | 管理 PyQt5 元件佈局、多檔案管理彈窗生命週期、以及滑鼠點擊事件的實體分流。 |
| **`plot_manager.py`** | 圖表與後端繪圖引擎 | 負責 $3 \times 1$ 無縫時序圖與 2D 地圖的繪製、起點探勘、多路路由切片、與非同步事件解鎖。 |
| **`data_processor.py`** | 背景執行緒處理器 | 繼承自 `QThread`，預留用於執行海量數據的非同步切片與索引重設。 |

---

## 2. 介面佈局與自訂 UI 元件

### 2.1 主視窗佈局 (`map_viewer.py`)

視窗預設尺寸為 $1200 \times 800$ 像素，採用垂直（`QVBoxLayout`）與水平（`QHBoxLayout`）佈局嵌套管理，主要分為三大區域：

1. **頂部控制列**：整合「載入CSV」、「載入多個CSV」、「設定起點」、「更新圖表」、「繪製單圈與重製單圈」與「WMA濾波」等功能按鈕。
2. **中部主圖表區**：嵌入 Matplotlib 畫布（`FigureCanvas`），呈現三行一列（$3 \times 1$）緊湊排置的數據時間序列圖（包含 `G Speed`、`R Scale 1` 與 `R Scale 2`）。
3. **底部交互區（權重 1:2）**：左側為單圈 Run 的可選取複選清單（`QListWidget`），右側為 2D 空間幾何的位置軌跡圖畫布（`track_canvas`）。

### 2.2 異步狀態提示小部件 (`overlay_widget.py`)

* **滑鼠事件穿透**：啟用 `Qt.WA_TransparentForMouseEvents` 屬性，確保遮罩層顯示時，不意外阻斷用戶在底層畫布上的觀看。
* **視覺樣式**：底色採用極輕量半透明遮罩（`rgba(0,0,0,30)`），中央提示方塊採用深色半透明（`rgba(0,0,0,80)`）搭配白色文字，並具備 5px 圓角與置中對齊。
* **自適應縮放**：覆寫 `resizeEvent`，當主視窗改變大小時，自動呼叫 `self.setGeometry(self.parent().rect())` 保持完美貼合。

---

## 3. 多檔案管理與動態路由機制

系統支援同時載入多個 CSV 文件進行合併與比對分析。

```
[載入多檔 CSV] ──► 彈出管理視窗 (file_manage_window) ──► 篩選/刪除特定檔案
                                                              │
                                                              ▼
[ 建立動態路由映射 ] ◄── [ 擷取單圈 extract_range_data ] ◄── [ 確認合併並繪製 ]
        │
        ├──► 檔案 1 (DataFrame 1) ──► 擷取 Run 1 切片
        └──► 檔案 2 (DataFrame 2) ──► 擷取 Run 2 切片

```

### 3.1 安全編碼讀取

* 實作 `@staticmethod read_csv_safe`，優先以 `utf-8` 解碼，若發生 `UnicodeDecodeError` 則自動切換為 `gbk` 編碼進行容錯。

### 3.2 動態數據源路由 (`extract_range_data`)

為了防止在多檔案模式下切片退化為單一數據集，`PlotManager` 內建動態路由判定：

* 當 `full_data` 為 `list` 結構時，程式會根據選取單圈（Run）的迭代順序，將其精確對應至對應的原始檔案 DataFrame 中：

$$\text{file\_idx} = \text{index if index < len(full\_data) else 0}$$


* 切片完成後執行 `.reset_index(drop=True)` 將索引歸零，並將原始絕對起止索引與對應檔案序號封裝進 `self.range_index_mapping` 緩存中。

---

## 4. 核心業務邏輯與雙向事件連動

### 4.1 空間起點定位與自動化單圈探勘 (`analyze_ranges`)

當用戶觸發起點設定模式並點擊圖表時，系統會記錄下基準起點座標 $(start\_x, start\_y)$。隨後啟動空間容差演算法遍歷整筆數據：

* **地理空間容差限制**：

$$\Delta x = |current\_x - start\_x| \le 0.00004$$


$$\Delta y = |current\_y - start\_y| \le 0.00004$$


* **分段時間鎖防禦**：為了避免在通過起點時連續相鄰的數據點重複計數，內建時間差檢查：

$$\Delta t = (current\_time - last\_match\_time) \ge 5 \text{ 秒}$$



只有滿足 $\Delta t \ge 5$ 時，才會結算當前單圈，並計算該 Run 區間內的總資料筆數與 `HH:MM:SS` 格式化時長，隨後透過 `range_update_callback` 刷新主 UI 的勾選清單。

### 4.2 加權移動平均濾波（WMA）

針對高頻噪訊，系統提供了離散摺積平滑化演算法。對於指定長度為 $N$ 的滑動視窗（由 UI 彈窗自訂 $0 \sim 100$ 階）：

* **數學權重分配**：

$$W = [1, 2, 3, \dots, N]$$


* **摺積運算與對齊**：
利用 NumPy 的 `convolve` 進行 `valid` 模式運算：

$$\text{WMA}_t = \frac{\sum_{i=1}^{N} W_i \cdot S_{t - N + i}}{\sum_{i=1}^{N} W_i}$$



運算後自動執行 `pending_data.iloc[len(pending_data) - len(wma):].copy()` 進行長度修正與時間軸嚴格對齊，確保物理一致性。

---

## 5. Matplotlib 事件狀態機與防顫防沾黏設計

本系統在「趨勢圖設定起點」與「滑鼠拖曳（Pan）」高頻同步互動時，實作了深度的事件解鎖機制，徹底解決了 Matplotlib 與作業系統滑鼠放開時產生的二次沾黏。

### 5.1 滑鼠拖曳攔截鎖 (`_FastDragPlot`)

* 自訂一體化拖曳管理函式，綁定畫布的按下、移動與釋放事件。
* **起點模式防沾黏**：當 `event.name == 'button_press_event'` 觸發時，優先尋找全域主視窗狀態。若偵測到 `is_setting_start_point` 為 `True`，則拖曳機制立即執行 `return` 進行硬性阻斷，絕不允許將 `self.is_dragging` 啟動為 `True`。

### 5.2 虛擬焦點釋放與 QTimer 延時防震盾

在 `_on_plot_click` 攔截到時序圖表上的起點設定時，為了防止滑鼠放開時的物理微小抖動被誤判為「常規高亮點擊更新」，系統採用了雙重隔離防線：

1. **傳參式焦點解鎖**：精確傳入當前座標軸物件 `ax` 執行 `event.canvas.release_mouse(event.inaxes)`，釋放 Matplotlib 內部的滑鼠捕獲鎖。
2. **QTimer 非同步隔離防震盾**：
* 點擊瞬間將防震鎖旗標設為 `True`：`self._just_set_start_point = True`。
* 此時任何隨後發生的 `motion_notify_event`（滑鼠移動）或殘留的放開事件，都會在 `_on_plot_click` 最頂端被無情地直接 `return` 攔截。
* 啟動 PyQt5 後台計時器：`QTimer.singleShot(500, self._unlock_anti_shake)`。在 500 毫秒（半秒鐘）黃金隔離期滿後，才自動呼叫回調函式將鎖解開（`_just_set_start_point = False`），從而實現一擊脫離，無須二次點擊。



### 5.3 畫布圖層清理異常捕獲

* 在更新圖表及清除高亮標記時，為了解決 Matplotlib 畫布經 `ax.clear()` 重刷後舊有 Artist 物件失去依附關係而拋出 `NotImplementedError: cannot remove artist` 的問題，全元清理區塊皆封裝了輕量化防禦：
```python
try:
    if line is not None: line.remove()
except (NotImplementedError, ValueError, AttributeError):
    pass

```


這確保了在多檔案併行刷新時，底層垃圾回收機制不會干擾上層 PyQt 主執行緒的流暢運行。