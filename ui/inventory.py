# 기존 임포트 아래에 추가
import cv2
from smart_fridge_ocr import process_frame_for_date  # 유통기한 추출 함수
from yolov8 import detect_food_category            # YOLO 음식 카테고리 인식 함수
from tkinter import messagebox
# import dtable  # 필요한 경우 d-day 계산이나 날짜 모듈 임포트

import tkinter as tk
from PIL import Image, ImageTk
from tkinter import ttk
from datetime import datetime
from detailed_item import DetailedItemPage
'''
정렬 부분을 구현해야하는데 뭐를 기준으로 정렬해야하는지가 의문.
각 부분마다 정렬하자는 민간인의 의견이 있었음
이를테면 이름, 수량, 등등 각 라벨별 옆에 업다운 버튼 둬서 그거별로 sorting되게 하면 좋겠다고 했음
이렇게 가도 되긴함
또 메인적으로는 어떤게 2이 되면 좋을지도 생각해야함. 6/1
'''

class InventoryPage(tk.Frame):
    def __init__(self, parent, main_ui, items=None,category=None):
        # 부모 컨테이너(self.main_f) 위에 얹어질 베이스 프레임으로 초기화
        self.main_ui = main_ui
        self.bg_color = main_ui.bg_color
        
        super().__init__(parent, bg=self.bg_color)
        self.category = category  # 나중에 카테고리 버튼 눌렀을 때 해당 카테고리로 필터링된 데이터만 보여주도록 구현해야할듯
        
        self.items=items

        self.curr_sort_col = "등록일"
        self.curr_sort_type = "desc"  # "asc(오름)" 또는 "desc(내림)"

        #ㅡㅡㅡㅡㅡㅡㅡㅡㅡ인벤토리 화면 프레임 설정 ㅡㅡㅡㅡㅡㅡㅡㅡㅡ
        self.inventory_title_frame()     # 인벤토리 타이틀 프레임
        self.category_btns_frame()   # 카테고리 버튼 프레임
        self.inventory_list_frame()     # 인벤토리 리스트 프레임
        self.camera_btn_frame()        # 카메라 버튼 프레임
        self.camera_btn()              # 카메라 버튼
        self.items_grid(self.items)            # 인벤토리 리스트 안에 표 생성
        
        #ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ


    def inventory_title_frame(self):
        self.inventory_title_f = tk.Frame(self, width=1000, height=90, bg=self.bg_color, bd=1, relief="solid")
        self.inventory_title_f.pack(fill="x")
        self.inventory_title_f.pack_propagate(0)

        inventory_title_l = tk.Label(self.inventory_title_f, text="인벤토리", bg=self.bg_color, fg="black", font=("Arial", 24, "bold"))
        inventory_title_l.pack(side="left", padx=20, pady=20)

        # filter 버튼이 필요한가? 흠
        # self.filter_btn = tk.Button(self.inventory_title_f, text="필터", font=("Arial", 16), bg="#05A66B", fg="white")
        # self.filter_btn.pack(side="right", padx=10, pady=20)
        # 정렬 버튼 - 글자 기준? 날짜 기준? 그걸 필터로 정하는건가? 흠 - 나중에 실제 데이터 들어오면 구현!
        # self.sort_btn = tk.Button(self.inventory_title_f, text="정렬", font=("Arial", 16), bg=self.bg_color, fg="black", bd=1, relief="solid")
        # self.sort_btn.pack(side="right", padx=10, pady=20)
        # self.sort_btn.config(command=self.sort_btn_event)
        ''' 
        정렬버튼을 없애고 의견 달아놓은거처럼 
        제품명, 수량, 유통기한, D-DAY, 상태, 추가한날의 
        각 라벨을 기준으로 sort하자
        디폴트는 그냥 추가한 날 기준으로 하는게 야르일듯
        '''
        # search 버튼
        self.search_bar = tk.Button(self.inventory_title_f, text="검색", font=("Arial", 16), bg=self.bg_color, fg="black", bd=1, relief="solid")
        self.search_bar.pack(side="right", padx=10, pady=20)
        self.search_bar.config(command=lambda: self.search_btn_event(self.search_bar.get()))

        # search 바
        self.search_bar = tk.Entry(self.inventory_title_f, width=20, font=("Arial", 20))
        self.search_bar.pack(side="right", padx=20, pady=20)
        self.search_bar.bind("<Return>", lambda event: self.search_btn_event(self.search_bar.get()))  # 엔터 키로 검색 실행
        
    
    # 지금은 제품명 기준으로만 검색하는데 필터 버튼이 생기면 다양하게 변신 가능..
    def search_btn_event(self, search_term):
        print(f"검색 버튼 클릭됨: {search_term}")
        items = [item for item in self.items if search_term in item['name']]
        self.destroy_frames_and_create()                # 기존 프레임 제거
        self.items_grid(items)          # 인벤토리 리스트 안에 표 생성 


    def sort_btn_event(self):
        print("정렬 버튼 클릭됨")

    def category_btns_frame(self):
        self.category_btns_f = tk.Frame(self, width=1000, height=50, bg=self.bg_color, bd=1, relief="solid")
        self.category_btns_f.pack(fill="x")
        self.category_btns_f.pack_propagate(0)

        # db에 저장되어 있는 카테고리로 표시
        self.items_categorys = set(item['category'] for item in self.items)  # items 리스트에서 카테고리 추출
        categorys = ["전체"] + list(self.items_categorys)

        for cate in categorys:
            btn = tk.Button(self.category_btns_f, text=cate, font=("Arial", 12), bg=self.bg_color, fg="black", bd=1, relief="solid")
            btn.pack(side="left", padx=10, pady=10)
            btn.config(command= lambda c=cate: category_btn_event(c))

        # 지금은 코드로 필터링하지만 나중에는 db에서 필터링하는게 빠르지 않나?.. 흠..
        def category_btn_event(cate):
            if cate == "전체":
                print("전체 카테고리 선택됨")
                # 지금 이렇게 하면 db가 없는 상태에선 변경된 데이터가 초기화 됨.
                self.main_ui.show_page("inventory", "전체")  # 전체보기 버튼 클릭 시 전체 인벤토리 페이지로 이동 - 전체화면을 보여주는 더 좋은 코드가 있지 않을까 생각함..

            elif cate == "음식":
                print("음식 카테고리 선택됨")
                items = [item for item in self.items if item['category'] == cate]
                self.destroy_frames_and_create()                # 기존 프레임 제거
                self.items_grid(items)          # 인벤토리 리스트 안에 표 생성
                
            elif cate == "음료":
                print("음료 카테고리 선택됨")
                items = [item for item in self.items if item['category'] == cate]
                self.destroy_frames_and_create()                # 기존 프레임 제거
                self.items_grid(items)          # 인벤토리 리스트 안에 표 생성 

            elif cate == "과일":
                print("과일 카테고리 선택됨")
                items = [item for item in self.items if item['category'] == cate]
                self.destroy_frames_and_create()                # 기존 프레임 제거
                self.items_grid(items)          # 인벤토리 리스트 안에 표 생성 

            elif cate == "채소":
                print("채소 카테고리 선택됨")
                items = [item for item in self.items if item['category'] == cate]
                self.destroy_frames_and_create()                # 기존 프레임 제거
                self.items_grid(items)          # 인벤토리 리스트 안에 표 생성  

            elif cate == "기타":
                print("기타 카테고리 선택됨")
                items = [item for item in self.items if item['category'] == cate]
                self.destroy_frames_and_create()                # 기존 프레임 제거
                self.items_grid(items)          # 인벤토리 리스트 안에 표 생성  

            
    def destroy_frames_and_create(self):
        self.inventory_list_f.destroy()  # 기존 인벤토리 리스트 프레임 제거
        self.canvas.destroy()  # 기존 캔버스 제거
        self.scrollbar.destroy()  # 기존 스크롤바 제거
        self.grid_f.destroy()  # 기존 그리드 프레임 제거
        self.camera_btn_f.destroy()  # 기존 카메라 버튼 프레임 제거
        self.inventory_list_frame()  # 새로운 인벤토리 리스트 프레임 생성
        self.camera_btn_frame()  # 새로운 카메라 버튼 프레임 생성
        self.camera_btn()  # 새로운 카메라 버튼 생성

    def inventory_list_frame(self):
        self.inventory_list_f = tk.Frame(self, width=1000, height=550, bg=self.bg_color, bd=1, relief="solid")
        self.inventory_list_f.pack(fill="both", expand=True)
        self.inventory_list_f.pack_propagate(0)

        # 스크롤바를 지원해 줄 canvas
        self.canvas = tk.Canvas(self.inventory_list_f, bg=self.bg_color, highlightthickness=0)
        
        self.scrollbar = tk.Scrollbar(self.inventory_list_f, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.grid_f = tk.Frame(self.canvas, bg=self.bg_color)  # 실제 데이터가 들어갈 프레임

        # 5. 데이터가 늘어나서 프레임 크기가 바뀌면 Canvas의 스크롤 범위를 자동 갱신해주는 바인딩
        self.grid_f.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # 6. Canvas 창 안에 실제 데이터 프레임을 윈도우 객체로 박아넣기
        self.canvas.create_window((0, 0), window=self.grid_f, anchor="nw")
        
        # 7. 레이아웃 배치
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 마우스 커서가 캔버스 영역에 들어오면 휠 스크롤 이벤트 연결 - 리눅스에서 Mousewheel 대신에 button-5, 4 사용
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", on_mousewheel))
        # 벗어나면다시 해제
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")



    def items_grid(self, items=[]):
        print(items)
        font = ("Arial", 12)
        heads = ['이미지', '제품명', '카테고리', '수량', '단위', '유통기한', 'D-DAY', '상태', '추가한 날']
        sort_heads = ['제품명', '수량', '유통기한', 'D-DAY', '상태', '추가한 날']
        heads_width = [10, 18, 12, 6, 6, 14, 8, 10, 14]

        for col, head in enumerate(heads):
            title = head
            sort_title = title in sort_heads

            # 정렬된 열이라면 화살표 아이콘 붙이기 - 이게 라즈베리파이에서 안깨지는지 몰겠네..ㅠㅠ ▲▼
            if sort_title and title == self.curr_sort_col:
                icon = " ▲" if self.curr_sort_type == "asc" else " ▼"
                title += icon
                font = ("Arial", 12, "bold")
                fg_color = "#05A66B"
            else:
                font = ("Arial", 12)
                fg_color = "black"

            header = tk.Label(self.grid_f, width=heads_width[col], text=head, bg=self.bg_color, fg="#05A66B", font=("Arial", 12, "bold"), borderwidth=1, relief="solid")
            header.grid(row=0, column=col, sticky="nsew")  # 헤더는 그리드로 배치
            if sort_title:
                header.bind("<Button-1>", lambda e, i=head: head_click_event(i))  # 클릭 이벤트 바인딩


            def head_click_event(col_title):
                print(f"{col_title} 헤더 클릭됨")
        
                # 1. 동일한 열을 연달아 클릭하면 차순을 반대로 뒤집음
                if self.curr_sort_col == col_title:
                    self.curr_sort_type = "desc" if self.curr_sort_type == "asc" else "asc"
                else:
                    # 새로운 열을 클릭하면 오름차순을 기본값으로 세팅
                    self.curr_sort_col = col_title
                    self.curr_sort_type = "asc"

                # # 2. 실제로 items 리스트를 정렬
                # # 와 타임 이거 어캐 정렬하누~
                if col_title == '제품명':
                    items.sort(key=lambda x: x['name'], reverse=self.curr_sort_type == "desc")
                elif col_title == '수량':
                    items.sort(key=lambda x: x['quantity'], reverse=self.curr_sort_type == "desc")
                elif col_title == '유통기한':
                    items.sort(key=lambda x: datetime.strptime(x['expiry_date'], '%Y-%m-%d'), reverse=self.curr_sort_type == "desc")
                elif col_title == 'D-DAY':
                    # D-DAY는 이미 계산된 d_day 값을 기준으로 정렬
                    items.sort(key=lambda x: int(x['d_day'][2:]) if x['d_day'].startswith("D-") else -int(x['d_day'][2:]), reverse=self.curr_sort_type == "desc")
                elif col_title == '상태':
                    # 상태는 '임박' > '만료' > '양호' 순으로 정렬
                    status_order = {'임박': 0, '만료': 1, '양호': 2}
                    items.sort(key=lambda x: status_order.get(x['status'], 3), reverse=self.curr_sort_type == "desc")


                # # 3. 기존 그리드 프레임을 싹 지우고 다시 그리기
                for widget in self.grid_f.winfo_children():
                    widget.destroy()

                self.items_grid(self.items) # 리스트를 다시 그리는 함수 재호출




        # D-DAY 계산하여 items 리스트에 추가하기    - 나중에 db안에 d_day 데이터가 있으면 이건 필요없긴한데.. 봐야할듯 찍을 때 계산하긴 하니깐..
        for i in range(len(items)):
            expiry_date = items[i]['expiry_date']
            # D-DAY 계산 로직
            d_day = datetime.strptime(expiry_date, '%Y-%m-%d') - datetime.now()
            # print(d_day.days)
            if d_day.days < 0:
                items[i]['d_day'] = f"D+{abs(d_day.days)}"  # 이미 만료된 경우 D+으로 표시
            else:
                items[i]['d_day'] = f"D-{d_day.days}"  # D-DAY 값을 items 딕셔너리에 추가

        
        for row, item in enumerate(items, start=1):
            # 이미지 셀
            try:
                img = Image.open('img/milk.png')
                photo = ImageTk.PhotoImage(img.resize((100, 100)))
                img_label = tk.Label(self.grid_f, image=photo, bg=self.bg_color)
                img_label.image = photo  # 참조 저장
                img_label.grid(row=row, column=0)
            except Exception as e:
                print(f"이미지 로드 실패: {e}")
                img_label = tk.Label(self.grid_f, text="이미지 없음", bg=self.bg_color, borderwidth=1, relief="solid")
                img_label.grid(row=row, column=0)
            
            def item_bind_all(widget, row, col):     # 나중에는 namge말고 고유 id값으로 불러야함               
                widget.bind("<Button-1>", lambda e, i=item: item_click_event(i))  # 클릭 이벤트 바인딩
                widget.grid(row=row, column=col, sticky="nsew")  # 이미지 셀에도 그리드 배치
                return widget
        
            # 텍스트 셀
            name=tk.Label(self.grid_f, text=item['name'], bg=self.bg_color, font=font)
            name = item_bind_all(name, row, 1)

            category = tk.Label(self.grid_f, text=item['category'], bg=self.bg_color, font=font)
            category = item_bind_all(category, row, 2)
            
            quantity = tk.Label(self.grid_f, text=item['quantity'], bg=self.bg_color, font=font)
            quantity = item_bind_all(quantity, row, 3)
            
            unit = tk.Label(self.grid_f, text=item['unit'], bg=self.bg_color, font=font)
            unit = item_bind_all(unit, row, 4)
            
            expiry_date = tk.Label(self.grid_f, text=item['expiry_date'], bg=self.bg_color, font=font)
            expiry_date = item_bind_all(expiry_date, row, 5)
            
            d_day = tk.Label(self.grid_f, text=item['d_day'], bg=self.bg_color, font=font)
            d_day = item_bind_all(d_day, row, 6)

            # 상태는 나중에 디자인 손 볼게요..ㅠㅠ 일단 이렇게
            if item['status'] == '임박':
                status = tk.Label(self.grid_f, text=item['status'], bg='orange', font=font)
                status.config(bd=1, relief="solid")
                
                status = item_bind_all(status, row, 7)
            elif item['status'] == '만료':
                status = tk.Label(self.grid_f, text=item['status'], bg='red', font=font)
                status.config(bd=1, relief="solid")

                status = item_bind_all(status, row, 7)
            else:
                status = tk.Label(self.grid_f, text=item['status'], bg='green', font=font)
                status.config(bd=1, relief="solid")

                status = item_bind_all(status, row, 7)

            added_date = tk.Label(self.grid_f, text=item['added_date'], bg=self.bg_color, font=font)
            added_date = item_bind_all(added_date, row, 8)

            def item_click_event(item):
                item_name = item['name']    
                print(f"{item_name} 아이템 클릭됨")

                # 콜백 함수 정의: 수정 창에서 데이터가 바뀌면 이 함수가 실행됩니다.
                def on_item_updated(updated_item, deleted=False):
                    print(updated_item)  # 수정된 아이템 데이터 확인용
                    # 삭제
                    if deleted:
                        # 1. 기존 리스트(self.items)에서 해당 아이템을 찾아 삭제합니다.
                        for i, original_item in enumerate(self.items):
                            if original_item['id'] == item['id']: # ID로 매칭 (추후 ID가 있으면 ID로)
                                del self.items[i]  # 해당 아이템 삭제
                                break

                        
                        # 2. 화면의 기존 그리드를 싹 지우고 다시 그립니다.
                        for widget in self.grid_f.winfo_children():
                            widget.destroy()
                        self.items_grid(self.items) # 리스트를 다시 그리는 함수 재호출
                        
                    else:
                        # 1. 기존 리스트(self.items)에서 해당 아이템을 찾아 데이터를 업데이트합니다.
                        for i, original_item in enumerate(self.items):
                            if original_item['id'] == item['id']: # ID로 매칭 (추후 ID가 있으면 ID로)
                                self.items[i] = updated_item
                                break
                        
                        # 2. 화면의 기존 그리드를 싹 지우고 다시 그립니다.
                        for widget in self.grid_f.winfo_children():
                            widget.destroy()
                        self.items_grid(self.items) # 리스트를 다시 그리는 함수 재호출

                # DetailedItemPage를 생성할 때 새로 만든 콜백 함수를 인자로 넘겨줍니다.
                self.detailed_page = DetailedItemPage(self.winfo_toplevel(), item, on_update=on_item_updated)  
                
                detailed_win = self.detailed_page.window
                detailed_win.transient(self.winfo_toplevel())  
                detailed_win.grab_set()
                

    def camera_btn_frame(self):
        self.camera_btn_f = tk.Frame(self, width=1000, height=130, bg=self.bg_color, bd=1, relief="solid")
        self.camera_btn_f.pack(fill="x")
        self.camera_btn_f.pack_propagate(0)

    def camera_btn(self):
        self.scan_btn = tk.Button(self.camera_btn_f, text="유통기한 스캔하기!", bg="#05A66B", fg="white", font=("Arial", 16, "bold"), width=60, height=2, command=self.camera_btn_event)
        self.scan_btn.pack(pady=20)

    def camera_btn(self):
        # 💡 버튼 생성 및 이벤트 바인딩
        self.scan_btn = tk.Button(
            self.camera_btn_f, 
            text="유통기한 스캔하기", 
            bg="#05a66b", 
            fg="white", 
            font=("Arial", 14, "bold"),
            command=self.scan_event # 🔥 스캔 이벤트 함수 연결
        )
        self.scan_btn.pack(pady=40)

    def scan_event(self):
        # 1. OpenCV를 통해 라즈베리파이 카메라(또는 웹캠) 열기
        # 만약 Pi 5 공식 라이브러리(Picamera2) 기반의 live 뷰가 smart_fridge_ocr에 내장되어 있으므로
        # 여기서는 cv2.VideoCapture(0) 또는 ocr 파일의 메인 루프 스타일을 제어합니다.
        # 일반적인 cv2 기반 카메라 열기 예시입니다.
        
        cap = cv2.box = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("카메라 오류", "카메라를 열 수 없습니다.")
            return

        messagebox.showinfo("스캔 시작", "카메라 창이 열리면 유통기한을 초록색 사각형에 맞추고 'C' 키를 누르세요.")

        found_date = None
        detected_category = "Unknown"
        captured_frame = None

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            h, w, _ = frame.shape
            # 가이드 박스 크기 및 위치 정의 (smart_fridge_ocr.py 스펙과 동일하게 설정)
            box_width, box_height = 300, 100
            x1 = (w - box_width) // 2
            y1 = (h - box_height) // 2
            x2 = x1 + box_width
            y2 = y1 + box_height

            # 화면 표시용 복사본에 가이드라인 그리기
            display_frame = frame.copy()
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(display_frame, "Align Date & Press 'C'", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.imshow('Smart Fridge - Scanning', display_frame)

            key = cv2.waitKey(1) & 0xFF
            
            # 'c' 키를 누르면 해당 시점의 프레임을 고정하고 캡처 분석 진행
            if key == ord('c'):
                captured_frame = frame
                roi = frame[y1:y2, x1:x2] # 유통기한 영역 (ROI)
                
                # 💡 [핵심 연동 1] OCR 파일을 이용한 유통기한 추출
                found_date = process_frame_for_date(roi)
                
                # 💡 [핵심 연동 2] YOLOv8 파일을 이용한 전체 프레임 기반 카테고리 분석
                detected_category = detect_food_category(frame, model_path="best.pt")
                break
                
            elif key == 27: # ESC 누르면 취소 종료
                break

        cap.release()
        cv2.destroyAllWindows()

        # 3. 캡처가 정상적으로 완료되었고 데이터가 추출되었을 때 처리
        if found_date and captured_frame is not None:
            # D-DAY 및 상태 판별을 위한 간단한 날짜 계산 (기존 규칙 응용)
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

            # 💡 [핵심 연동 3] 새로 스캔된 아이템 딕셔너리 생성
            # 기존 shared_items의 구조와 매칭되도록 딕셔너리를 구성합니다.
            new_id = max([item['id'] for item in self.items]) + 1 if self.items else 1
            
            new_item = {
                'id': new_id,
                'name': f"스캔된 {detected_category}_{new_id}", # 우선 인식된 카테고리로 이름 부여 (추후 수정 가능)
                'category': detected_category,                # YOLO가 찾은 카테고리
                'quantity': 1,
                'unit': '개',
                'expiry_date': found_date,                    # OCR이 찾은 유통기한
                'status': status,
                'added_date': today.strftime("%Y-%m-%d"),
                'd_day': f"D-{days_left}" if days_left >= 0 else f"D+{abs(days_left)}"
            }

            # 💡 [핵심 연동 4] ui.py에서 공유 중인 원본 shared_items 리스트에 삽입
            self.items.append(new_item)

            # 💡 [핵심 연동 5] 인벤토리 화면의 그리드를 싹 지우고 재렌더링 (새로고침)
            for widget in self.grid_f.winfo_children():
                widget.destroy()
            self.items_grid(self.items)

            messagebox.showinfo("성공", f"새로운 물품이 등록되었습니다!\n카테고리: {detected_category}\n유통기한: {found_date}")
        else:
            if key != 27:
                messagebox.showwarning("인식 실패", "유통기한 문자열을 인식하지 못했습니다. 다시 시도해주세요.")
