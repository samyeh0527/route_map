from PyQt5.QtCore import QThread, pyqtSignal
import pandas as pd

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