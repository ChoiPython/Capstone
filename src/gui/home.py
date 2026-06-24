import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime
from item_reg import ItemRegPage

import cv2  
from tkinter import messagebox  

import os
import sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from smart_fridge_ocr import run_camera_scan

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

    def total_item_label(self):
        # [변경] 하드코딩된 "0" 대신, 실제 전체 아이템 리스트(self.items)의 개수를 구합니다.
        total_count = len(self.items)
        
        # (기존 프레임이나 배치는 유지하고 text 부분만 수정합니다)
        self.total_lbl = tk.Label(
            self.item_count_f, 
            text=f"전체\n\n{total_count}개",  # 💡 0개 -> 실제 개수로 변경
            bg=self.bg_color, 
            fg='black', 
            font=("Arial", 16, "bold"), 
            bd=1, 
            relief="solid", 
            width=10, 
            height=5
        )
        self.total_lbl.pack(side="left", padx=30, pady=20)

    def exp_item_label(self):
        # [변경] 상태(status)가 '임박' 또는 '주의'인 아이템의 개수를 필터링하여 구합니다.
        exp_count = len([i for i in self.items if i.get('status') in ['임박', '주의']])
        
        self.exp_lbl = tk.Label(
            self.item_count_f, 
            text=f"임박\n\n{exp_count}개",  # 💡 0개 -> 실제 개수로 변경
            bg=self.bg_color, 
            fg='orange', 
            font=("Arial", 16, "bold"), 
            bd=1, 
            relief="solid", 
            width=10, 
            height=5
        )
        self.exp_lbl.pack(side="left", padx=30, pady=20)

    def expired_item_label(self):
        # [변경] 상태(status)가 '만료'인 아이템의 개수를 필터링하여 구합니다.
        expired_count = len([i for i in self.items if i.get('status') == '만료'])
        
        self.expired_lbl = tk.Label(
            self.item_count_f, 
            text=f"만료\n\n{expired_count}개",  # 💡 0개 -> 실제 개수로 변경
            bg=self.bg_color, 
            fg='red', 
            font=("Arial", 16, "bold"), 
            bd=1, 
            relief="solid", 
            width=10, 
            height=5
        )
        self.expired_lbl.pack(side="left", padx=30, pady=20)

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
        self.scan_btn = tk.Button(self.camera_btn_f, text="유통기한 스캔하기!", bg="#05A66B", fg="white", font=("Arial", 16, "bold"), width=100, height=4, command=self.camera_btn)
        self.scan_btn.pack(pady=20)

    def camera_btn_frame(self):
        # 1. 부모 프레임의 높이(height)를 기존 130에서 200 정도로 넉넉하게 키웁니다.
        self.camera_btn_f = tk.Frame(self, width=1000, height=200, bg=self.bg_color, bd=1, relief="solid")
        self.camera_btn_f.pack(fill="x", pady=10) # 여백도 약간 줍니다.
        self.camera_btn_f.pack_propagate(0)

    def camera_btn(self):
        # 2. 버튼의 width, height 뿐만 아니라 글씨 크기(font)도 키워야 버튼이 자연스럽게 커집니다.
        # Tkinter 버튼에서 width, height는 '픽셀'이 아니라 '글자 수' 기준입니다.
        self.scan_btn = tk.Button(
            self.camera_btn_f, 
            text="유통기한 스캔하기", 
            command=self.scan_event,
            font=("Arial", 18, "bold"),       # 💡 글씨를 큼직하게 변경
            bg="#05a66b", 
            fg="white",
            width=25,                        # 💡 글자 수 기준 너비 (여유있게 25자 크기)
            height=2                         # 💡 글자 줄 수 기준 높이 (2줄 높이)
        )
        
        # 3. pack할 때 프레임 정중앙에 꽉 차거나 여유롭게 배치되도록 패딩(pady)을 줍니다.
        self.scan_btn.pack(expand=True, pady=20)

    # 스캔 이벤트 함수
    def scan_event(self):
        # 💡 [핵심 1] 중복 실행 방지 (더블 클릭 차단)
        # 이미 스캔이 진행 중이라면 버튼을 또 눌러도 무시합니다.
        if getattr(self, 'is_scanning', False):
            print("이미 스캔이 진행 중입니다.")
            return
            
        self.is_scanning = True # 스캔 시작 상태로 잠금

        try:
            messagebox.showinfo("스캔 시작", "카메라 창이 열리면 유통기한을 맞추고 기다려주세요.\n취소하려면 CLOSE버튼을 눌러주세요.")

            # 💡 [핵심 2] 변경된 리턴 값 3개(날짜, 카테고리, 이미지경로)를 받음
            result = run_camera_scan()

            # 취소(CLOSE 버튼이나 q키) 처리 로직 수정
            # result가 (None, None, None)으로 반환되므로 조건문을 수정해야 합니다.
            if result == (None, None, None) or result[0] is None:
                messagebox.showwarning("스캔 취소", "유통기한 스캔이 취소되었습니다.")
                return

            # 정상적으로 데이터를 가지고 돌아온 경우 언패킹
            found_date, detected_category, saved_img_path = result

            # --- 아래는 기존 데이터 추가 및 UI 새로고침 로직 ---
            try:
                today = datetime.now().date()
                exp_date = datetime.strptime(found_date, "%Y-%m-%d").date()
                days_left = (exp_date - today).days
                status = "만료" if days_left < 0 else "임박" if days_left <= 3 else "신선"
            except:
                days_left = 0
                status = "신선"

            new_item = {
                'name': " ",
                'category': detected_category,
                'quantity': 1,
                'unit': '개',
                'expiry_date': found_date,
                'status': status,
                'reg_date': today.strftime("%Y-%m-%d"),
                'Dday': f"D-{days_left}" if days_left >= 0 else f"D+{abs(days_left)}",
                'image_path': saved_img_path  # 💡 [추가] 기왕 저장한 사진 경로도 DB에 함께 기록해둡니다!
            }
            


            # 홈 화면 새로고침 UI 갱신
            self.total_count = len(self.items)
            self.warning_count = len([i for i in self.items if i['status'] in ['주의', '임박']])
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
    
            # 등록햇습니다 말고 저장화면불렁기
            messagebox.showinfo("성공", f"새로운 물품이 등록되었습니다!\n\n카테고리: {detected_category}\n유통기한: {found_date}")
            
            # item_reg 페이지로 이동하면서 새로 등록된 아이템의 ID를 전달하여 상세 정보 페이지로 바로 이동할 수 있도록 합니다.
            self.item_reg = ItemRegPage(self.winfo_toplevel(), new_item)
                
            itemreg_win = self.item_reg.window
            itemreg_win.transient(self.winfo_toplevel())  
            itemreg_win.wait_visibility()
            itemreg_win.grab_set()


        finally:
            # 💡 [핵심 1] 스캔이 완전히 끝나거나 취소되면 다시 버튼을 누를 수 있도록 잠금 해제
            self.is_scanning = False