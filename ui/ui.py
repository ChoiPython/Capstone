import tkinter as tk
from PIL import Image, ImageTk
from home import HomePage  # 메인 화면 프레임 임포트
from inventory import InventoryPage # 인벤토리 화면 프레임 임포트

class UI:
    def __init__(self, master):
        self.bg_color = "#fafaf8"
        self.master = master
        self.current_page = None  # 현재 중앙에 띄워진 페이지를 저장할 변수
        
        # 테스트 데이터 - 데이터에 D-day가 없어서 코드별로 추가하는데 이게 db단에서 처리해야함. 지금은 일단 코드에 추가했음.
        self.items = [
            {'id':1,'name': '돼지고기', 'category': '음식', 'quantity': 1, 'unit': '개', 'expiry_date': '2026-04-30', 'status': '만료', 'added_date': '2024-06-25'}, 
            {'id':2,'name': '소고기', 'category': '음식', 'quantity': 1, 'unit': '개', 'expiry_date': '2026-05-20', 'status': '만료', 'added_date': '2024-06-25'}, 
            {'id':3,'name': '당근', 'category': '채소', 'quantity': 1, 'unit': '개', 'expiry_date': '2026-05-22', 'status': '임박', 'added_date': '2024-06-25'}, 
            {'id':4,'name': '양상추', 'category': '채소', 'quantity': 1, 'unit': '개', 'expiry_date': '2026-05-22', 'status': '신선', 'added_date': '2024-06-25'}, 
            {'id':5,'name': '우유', 'category': '음료', 'quantity': 1, 'unit': '개', 'expiry_date': '2026-08-30', 'status': '신선', 'added_date': '2024-06-25'}, 
            {'id':6,'name': '우유', 'category': '음료', 'quantity': 1, 'unit': '개', 'expiry_date': '2026-08-30', 'status': '신선', 'added_date': '2024-06-25'}, 
            {'id':7,'name': '사과', 'category': '과일', 'quantity': 1, 'unit': '개', 'expiry_date': '2026-09-30', 'status': '신선', 'added_date': '2024-06-25'}, 
            {'id':8,'name': '바나나', 'category': '과일', 'quantity': 1, 'unit': '개', 'expiry_date': '2026-09-30', 'status': '신선', 'added_date': '2024-06-25'}, 
            {'id':9,'name': '오렌지', 'category': '과일', 'quantity': 1, 'unit': '개', 'expiry_date': '2026-09-30', 'status': '신선', 'added_date': '2024-06-25'}, 
            {'id':10,'name': '케찹', 'category': '기타', 'quantity': 1, 'unit': '개', 'expiry_date': '2026-09-30', 'status': '신선', 'added_date': '2024-06-25'}, 
            {'id':11,'name': '마요네즈', 'category': '기타', 'quantity': 1, 'unit': '개', 'expiry_date': '2026-09-30', 'status': '신선', 'added_date': '2024-06-25'}, 
            {'id':12,'name': '햄', 'category': '기타', 'quantity': 1, 'unit': '개', 'expiry_date': '2026-09-30', 'status': '신선', 'added_date': '2024-06-25'}, 
        ]

        # ㅡㅡㅡㅡㅡㅡ UI 해상도 설정 ㅡㅡㅡㅡㅡㅡ
        width  = self.master.winfo_screenwidth()
        height = self.master.winfo_screenheight()
        self.master.geometry(f"1280x800+{int(width/2-1280/2)}+{int(height/2-800/2)}")  
        self.master.resizable(False, False)

        # ㅡㅡㅡㅡㅡㅡ 레이아웃 프레임 설정 ㅡㅡㅡㅡㅡㅡ
        self.menu_frame()       
        self.add_v_line(self.menu_f, "right")  # 사이드바 구분선
        self.main_frame()                      # 화면이 갈아끼워질 도화지 프레임

        # ㅡㅡㅡㅡㅡㅡ 메뉴 버튼 설정 ㅡㅡㅡㅡㅡㅡ
        # command 인자에 클릭 시 실행할 화면 전환 함수를 지정합니다.
        self.menu_button_frame(img_path='../img/home.png', text="메인 화면", 
                               command=lambda: self.show_page("home"))

        # ㅡㅡㅡㅡㅡㅡ 인벤토리 버튼 설정 ㅡㅡㅡㅡㅡㅡ
        self.menu_button_frame(img_path='../img/inventory2.png', text="인벤토리", 
                               command=lambda: self.show_page("inventory"))


        # 처음 실행 시 메인 화면(home)을 기본으로 띄웁니다.
        self.show_page("home")  # 테스트용으로 인벤토리 페이지를 먼저 띄우도록 설정
        # self.show_page("home")  # 실제 배포 시에는 메인 화면이

    def menu_frame(self):
        self.menu_f = tk.Frame(self.master, width=260, height=800, bg=self.bg_color)
        self.menu_f.pack(side="left")
        self.menu_f.pack_propagate(0)

    def main_frame(self):
        self.main_f = tk.Frame(self.master, width=1020, height=800, bg='#f3f0e9')
        self.main_f.pack(side="right")
        self.main_f.pack_propagate(0)

    # [핵심] 화면 전환(스왑) 함수
    def show_page(self, page_name, category="전체"):
        # 기존 화면이 열려있다면 파괴(삭제)하여 메모리를 비웁니다.
        if self.current_page is not None:
            self.current_page.destroy()

        # 요청된 페이지 객체를 생성하여 컨테이너(self.main_f) 위에 얹습니다.``
        if page_name == "home":
            home_items= self.items[0:4]
            self.current_page = HomePage(self.main_f, self, items=home_items)
        
        elif page_name == "inventory":
            self.current_page = InventoryPage(self.main_f, self, items=self.items, category=category)
        
        if self.current_page:
            self.current_page.pack(fill="both", expand=True)

    def menu_button_frame(self, img_path='', text="default", command=None):
        menu_btn_f = tk.Frame(self.menu_f, width=260, height=50, bg=self.bg_color, bd=1, relief="solid")
        menu_btn_f.pack(pady=20, padx=10)
        menu_btn_f.pack_propagate(0)

        try: 
            img = Image.open(img_path)
            img = img.resize((30,30))
            photo = ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"이미지 로드 실패: {e}")
            return

        # 여러 메뉴 버튼이 생성될 때 덮어쓰기 방지를 위해 개별 위젯 변수로 선언
        icon_lbl = tk.Label(menu_btn_f, image=photo, bg=self.bg_color)
        icon_lbl.image = photo     
        icon_lbl.pack(side="left", padx=10)

        text_lbl = tk.Label(menu_btn_f, text=text, fg="#05a66b", bg=self.bg_color, font=("Arial", 20, "bold"))
        text_lbl.pack(side="left", fill='x')

        def on_hover(event):
            menu_btn_f.config(bg="#f3f0e9")
            icon_lbl.config(bg="#f3f0e9")
            text_lbl.config(bg="#f3f0e9")
        
        def off_hover(event):
            menu_btn_f.config(bg=self.bg_color)
            icon_lbl.config(bg=self.bg_color)
            text_lbl.config(bg=self.bg_color)

        for widget in (menu_btn_f, icon_lbl, text_lbl):
            widget.bind("<Enter>", on_hover)
            widget.bind("<Leave>", off_hover)
            if command:
                widget.bind("<Button-1>", lambda e: command())
    


    def add_v_line(self, parent, side, color="#cdcdcd", fill="y", height=0):
        line = tk.Frame(parent, width=1.5, bg=color, height=height)
        line.pack(side=side, fill=fill)
        return line