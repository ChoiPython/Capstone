import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime

import cv2  
from tkinter import messagebox  
from smart_fridge_ocr import process_frame_for_date  
from yolov8 import detect_food_category            
from picamera2 import Picamera2
from libcamera import controls

# [추가] 상위 폴더의 AI 스크립트 접근을 위한 경로 설정
import os
import sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 이제 상위 폴더에 있는 모듈을 정상적으로 import 할 수 있습니다.
from smart_fridge_ocr import process_frame_for_date  
from yolov8 import detect_food_category

class HomePage(tk.Frame):
    def __init__(self, parent, main_ui, items):
        # 부모 컨테이너(self.main_f) 위에 얹어질 베이스 프레임으로 초기화
        super().__init__(parent, bg='#f3f0e9')
        self.main_ui = main_ui
        self.bg_color = main_ui.bg_color

        # 여기도 데이터로 적용해야함
        self.items = items

        # ㅡㅡㅡㅡㅡㅡ 메인 유닛 안내문 설정 ㅡㅡㅡㅡㅡㅡ
        self.item_count_frame()     # 현재 재고 현황 프레임
        self.warning_status_img()   # 1. 주의 현황 아이콘
        self.warning_status_label() # 1. 주의 현황 라벨
        self.total_item_label()     # 2. 총 재고 수 라벨
        self.exp_item_label()       # 3. 유통기한 임박 제품 수 라벨
        self.expired_item_label()   # 4. 유통기한 지난 제품 수 라벨

        # ㅡㅡㅡㅡㅡㅡ 인벤토리 리스트 요약 설정 ㅡㅡㅡㅡㅡㅡ
        self.inventory_list_frame()     # 인벤토리 리스트 프레임
        self.inventory_item_frame()     # 인벤토리 아이템 프레임
        for item in self.items:              # 나중에 실제 데이터 들어오면 상위 4개만
            self.inventory_items(item)

        # ㅡㅡㅡㅡㅡㅡ 카메라 버튼 설정 ㅡㅡㅡㅡㅡㅡ
        self.camera_btn_frame()     # 카메라 버튼 프레임
        self.camera_btn()           # 카메라 버튼

    # 모든 자식 위젯 프레임들의 첫 번째 인자를 self(HomePage 자체)로 변경했습니다.
    def item_count_frame(self):
        self.item_count_f = tk.Frame(self, width=1000, height=160, bg="#05A66B")
        self.item_count_f.pack(pady=20, padx=20)
        self.item_count_f.pack_propagate(0)

    def warning_status_img(self):
        try: 
            img = Image.open('../img/warning3.png')
            img = img.resize((100,100))
            photo = ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"이미지 로드 실패: {e}")
            return

        self.warning_status_icon = tk.Label(self.item_count_f, image=photo, bg="#05A66B")
        self.warning_status_icon.image = photo
        self.warning_status_icon.pack(side="left", padx=15)

    def warning_status_label(self, item_count=0):
        warning_status_l = tk.Label(self.item_count_f, text="유통기한 만료 아이템 확인 요망", bg="#05A66B", fg="white", font=("Arial", 16, "bold"))
        warning_status_l.pack(side='left', pady=10, padx=10, anchor="w")
        self.main_ui.add_v_line(self.item_count_f, "left", color="#cdcdcd", fill=None, height=100)

    def total_item_label(self, total_count=0):
        total_item_l = tk.Label(self.item_count_f, text=f"총 재고\n{total_count}", bg="#05A66B", fg="white", font=("Arial", 16, "bold"))
        total_item_l.pack(side='left', pady=10, padx=20, anchor="w")
        self.main_ui.add_v_line(self.item_count_f, "left", color="#cdcdcd", fill=None, height=100)

    def exp_item_label(self, exp_count=0):
        exp_item_l = tk.Label(self.item_count_f, text=f"유통기한 임박 제품\n{exp_count}", bg="#05A66B", fg="white", font=("Arial", 16, "bold"))
        exp_item_l.pack(side='left', pady=10, padx=20, anchor="w")
        self.main_ui.add_v_line(self.item_count_f, "left", color="#cdcdcd", fill=None, height=100)

    def expired_item_label(self, expired_count=0):
        expired_item_l = tk.Label(self.item_count_f, text=f"만료된 제품\n{expired_count}", bg="#05A66B", fg="white", font=("Arial", 16, "bold"))
        expired_item_l.pack(side='left', pady=10, padx=20, anchor="w")

    def inventory_list_frame(self):
        self.inventory_list_f = tk.Frame(self, width=1000, height=400, bg=self.bg_color)
        self.inventory_list_f.pack(pady=20, padx=20)
        self.inventory_list_f.pack_propagate(0)

        title_frame = tk.Frame(self.inventory_list_f, width=1000, height=50, bg=self.bg_color)
        title_frame.pack(side="top", fill="x")

        title_l = tk.Label(title_frame, text="인벤토리 리스트", bg=self.bg_color, fg="#05A66B", font=("Arial", 18, "bold"))
        title_l.pack(side="left", pady=20, anchor="w")

        view_all_btn = tk.Button(title_frame, text="전체보기", bg="#05A66B", fg="white", font=("Arial", 12, "bold"), command=self.view_all_btn_event)
        view_all_btn.pack(side="right", pady=5, padx=10, anchor="e")

    def inventory_item_frame(self):
        self.item_f = tk.Frame(self.inventory_list_f, width=1000, height=330, bg=self.bg_color, bd=1, relief="solid")
        self.item_f.pack(pady=10, padx=20)
        self.item_f.pack_propagate(0)

    def inventory_items(self, item):
        each_item_f = tk.Frame(self.item_f, width=215, height=280, bg=self.bg_color, bd=1, relief="solid")
        each_item_f.pack(side='left', pady=5, padx=10)
        each_item_f.pack_propagate(0)
        # 이미지는 일단 우유 이미지로 고정, 나중에 데이터에 맞는 이미지로 변경해야할듯
        try: 
            img = Image.open('../img/milk.png')
            img = img.resize((200,150))
            photo = ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"이미지 로드 실패: {e}")
            return
        
        self.item_img = tk.Label(each_item_f, image=photo, bg=self.bg_color)    #, bd=1, relief="solid"
        self.item_img.image = photo
        self.item_img.pack(side="top", padx=10)

        self.item_name = tk.Label(each_item_f, text=item['name'], bg=self.bg_color, fg='black', font=("Arial", 12, "bold"))
        self.item_name.pack(side="top", pady=5)

        self.item_exp_date = tk.Label(each_item_f, text=f"유통기한: {item['expiry_date']}", bg=self.bg_color, fg='black', font=("Arial", 10))
        self.item_exp_date.pack(side="top", pady=5)

        # D-day 계산
        expiry_date = item['expiry_date']
        # D-DAY 계산 로직
        d_day = datetime.strptime(expiry_date, '%Y-%m-%d') - datetime.now()
        # print(d_day.days)
        if d_day.days < 0:
            item['d_day'] = f"D+{abs(d_day.days)}"  # 이미 만료된 경우 D+으로 표시
        else:
            item['d_day'] = f"D-{d_day.days}"  # D-DAY 값을 items 딕셔너리에 추가
        self.item_left_days = tk.Label(each_item_f, text=f"{item['d_day']}", bg='red', fg='white', font=("Arial", 20), width=10)
        self.item_left_days.pack(side="top", pady=5)

    # 인벤토리 화면으로 전환
    def view_all_btn_event(self):
        self.main_ui.show_page("inventory", "전체")  # 전체보기 버튼 클릭 시 전체 인벤토리 페이지로 이동

    def camera_btn_frame(self):
        self.camera_btn_f = tk.Frame(self, width=1000, height=130, bg=self.bg_color)
        self.camera_btn_f.pack(pady=20, padx=20)
        self.camera_btn_f.pack_propagate(0)

    def camera_btn(self):
        self.scan_btn = tk.Button(self.camera_btn_f, text="유통기한 스캔하기!", bg="#05A66B", fg="white", font=("Arial", 16, "bold"), width=60, height=2, command=self.camera_btn_event)
        self.scan_btn.pack(pady=20)

    def camera_btn_frame(self):
        self.camera_btn_f = tk.Frame(self, width=1000, height=130, bg=self.bg_color, bd=1, relief="solid")
        self.camera_btn_f.pack(fill="x")
        self.camera_btn_f.pack_propagate(0)

    def camera_btn(self):
        # 💡 [수정] 버튼 생성 및 스캔 이벤트 연결
        self.scan_btn = tk.Button(
            self.camera_btn_f, 
            text="유통기한 스캔하기", 
            bg="#05a66b", 
            fg="white", 
            font=("Arial", 14, "bold"),
            command=self.scan_event  # 🔥 이벤트 함수 연결
        )
        self.scan_btn.pack(pady=40)

    # 🔥 [새로 추가] 홈 화면용 카메라 스캔 및 AI 연동 마스터 함수
    def scan_event(self):
        # 1. 라즈베리파이 5 전용 Picamera2 열기
        try:
            picam2 = Picamera2()
            config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "BGR888"})
            picam2.configure(config)
            picam2.start()
            
            # 자동 초점 모드 켜기
            try:
                picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
            except:
                pass
        except Exception as e:
            messagebox.showerror("카메라 오류", f"카메라를 열 수 없습니다:\n{e}")
            return

        messagebox.showinfo("스캔 시작", "카메라 창이 열리면 유통기한을 초록색 사각형에 맞추고 'C' 키를 누르세요.")

        found_date = None
        detected_category = "Unknown"
        captured_frame = None
        key = 0 # key 변수 초기화

        try:
            while True:
                # 2. cv2.VideoCapture 대신 picam2에서 프레임 가져오기
                frame = picam2.capture_array()

                h, w, _ = frame.shape
                # 가이드 박스 크기 및 위치 정의
                box_width, box_height = 300, 100
                x1 = (w - box_width) // 2
                y1 = (h - box_height) // 2
                x2 = x1 + box_width
                y2 = y1 + box_height

                # 사용자 안내용 화면 가이드라인 그리기
                display_frame = frame.copy()
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(display_frame, "Align Date & Press 'C'", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                cv2.imshow('Smart Fridge - Scanning', display_frame)

                key = cv2.waitKey(1) & 0xFF
                
                # 'c' 키를 누르면 고정 및 캡처 분석 시작
                if key == ord('c'):
                    captured_frame = frame
                    roi = frame[y1:y2, x1:x2] # 유통기한 글자 영역 추출
                    
                    # 💡 [모델 연동 1] OCR 분석
                    found_date = process_frame_for_date(roi)
                    
                    # 💡 [모델 연동 2] YOLOv8 분석
                    detected_category = detect_food_category(frame, model_path="best.pt")
                    break
                    
                elif key == 27: # ESC 누르면 스캔 취소
                    break

        finally:
            # 3. 루프가 끝나면 카메라 메모리 안전하게 해제
            picam2.stop()
            cv2.destroyAllWindows()

        # 4. 데이터 인식을 성공적으로 마치고 값이 들어왔을 때 처리 로직
        if found_date and captured_frame is not None:
            try:
                today = datetime.now().date()
                exp_date = datetime.strptime(found_date, "%Y-%m-%d").date()
                days_left = (exp_date - today).days
                
                if days_left < 0:
                    status = "만료"
                elif days_left <= 3:
                    status = "임박"
                else:
                    status = "신선"
            except:
                days_left = 0
                status = "신선"

            # 새 물품 ID 계산
            new_id = max([item['id'] for item in self.items]) + 1 if self.items else 1
            
            # 공유 데이터 명세에 맞춘 새 아이템 생성
            new_item = {
                'id': new_id,
                'name': f"스캔된 {detected_category}_{new_id}",
                'category': detected_category,
                'quantity': 1,
                'unit': '개',
                'expiry_date': found_date,
                'status': status,
                'added_date': today.strftime("%Y-%m-%d"),
                'd_day': f"D-{days_left}" if days_left >= 0 else f"D+{abs(days_left)}"
            }

            self.items.append(new_item)

            # --- 이 부분은 home.py와 inventory.py의 UI 갱신 로직에 맞게 그대로 둡니다 ---
            # (여기는 올려주신 기존 코드의 ui 새로고침 부분과 동일하게 유지하시면 됩니다)
            
            # [예시: home.py의 경우]
            if hasattr(self, 'total_count'): # 홈 화면인지 인벤토리 화면인지 구분
                self.total_count = len(self.items)
                self.warning_count = len([i for i in self.items if i['status'] == '주의' or i['status'] == '임박'])
                self.expired_count = len([i for i in self.items if i['status'] == '만료'])

                for widget in self.winfo_children():
                    widget.destroy()
                    
                self.item_count_frame()     
                self.warning_status_img()   
                self.warning_status_label() 
                self.total_item_label()     
                self.exp_item_label()       
                self.expired_item_label()   
                self.inventory_list_frame()     
                self.inventory_item_frame()     
                for item in self.items[:4]:
                    self.inventory_items(item)
                self.camera_btn_frame()
                self.camera_btn()
            else:
                # [예시: inventory.py의 경우]
                for widget in self.grid_f.winfo_children():
                    widget.destroy()
                self.items_grid(self.items)

            messagebox.showinfo("성공", f"새로운 물품이 등록되었습니다!\n카테고리: {detected_category}\n유통기한: {found_date}")
        else:
            if key != 27:
                messagebox.showwarning("인식 실패", "유통기한 날짜를 명확히 인식하지 못했습니다. 다시 시도해 주세요.")