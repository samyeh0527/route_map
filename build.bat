@echo off
cd /d D:\route_map_git

:: 取得當前日期與時間 (格式: YYYYMMDD_HHMMSS)
for /f "tokens=2 delims==" %%I in ('wmic OS Get localdatetime /value ^| find "="') do set datetime=%%I
set datetime=%datetime:~0,8%_%datetime:~8,6%

:: 設定輸出檔案名稱
set output_name=route_map_%datetime%.exe

:: 執行 pyinstaller 並指定輸出名稱
pyinstaller --onefile --noconsole --add-data "src;src" --windowed --icon=src/002.ico --name "%output_name%" src/main.py

pause
