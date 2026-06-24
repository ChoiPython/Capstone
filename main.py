import tkinter as tk
import os
import sys

# [추가] 상위 폴더(smart_fridge_ver1)를 패스에 등록하여 
# 하위 파일들이 ocr, yolo 모듈을 부를 수 있도록 길을 열어줍니다.
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from ui import UI  # 같은 폴더 내 ui.py 임포트

if __name__ == "__main__":
    main_ui = tk.Tk()
    ui = UI(main_ui)
    main_ui.mainloop()