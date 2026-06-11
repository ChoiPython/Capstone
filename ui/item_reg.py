import tkinter as tk
import db_manager  # 💡 추가된 update_item 함수를 사용하기 위해 임포트 확인
from PIL import Image, ImageTk
from tkinter import messagebox
from tkcalendar import Calendar
from tkinter import ttk  

class ItemRegPage:
    def __init__(self, master, item, on_update=None):
        self.bg_color = '#fafaf8'
        self.item_data = item
        print(self.item_data)
        # 💡 DB 필드명과 맞춰서 세팅 (quentity, exp_date, Dday 등 유연하게 예외 처리)
        self.category = item.get('category')
        self.quantity = item.get('quantity') or item.get('quantity', 1) 
        self.unit = item.get('unit', '개')
        self.expiry_date = item.get('exp_date') or item.get('expiry_date', '2026-01-01')
        self.status = item.get('status', '신선')
        self.reg_date = item.get('reg_date')or item.get('reg_date', '')
        self.Dday = item.get('Dday')
        self.image_path = item.get('img_path', '../img/milk.png')
        
        # 1. 새 팝업 창 생성 (넘겨받은 진짜 윈도우 창 객체를 부모로 지정)
        self.window = tk.Toplevel(master)
        self.window.title("아이템 수정")
        self.window.configure(bg=self.bg_color)

        # ㅡㅡㅡㅡㅡㅡ UI 해상도 설정 ㅡㅡㅡㅡㅡㅡ
        width = self.window.winfo_screenwidth()
        height = self.window.winfo_screenheight()
        self.window.geometry(f"600x340+{int(width/2-600/2)}+{int(height/2-340/2)}")  
        self.window.resizable(False, False) 
        self.window.transient(master)  # 모달 윈도우 설정 (메인 잠금)
        self.window.grab_set()  # 모달 윈도우 설정 (메인 잠금)

        #ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ프레임 생성ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ
        self.control_bar_frame()  # 제어 바 프레임 생성
        self.item_info_frame()   # 아이템 정보 프레임 생성
        self.image_frame(img_path='../img/milk.png')  # 이미지 프레임 생성 (테스트용 이미지 경로)
        self.item_name_frame()   # 아이템 이름 프레임 생성
        self.info_left_frame()   # 정보 왼쪽 프레임 생성
        self.add_v_line(self.info_f, "left", color="#cdcdcd", fill=None, height=180)  # 정보 프레임 안에 수직선 추가
        self.info_right_frame()  # 정보 오른쪽 프레임 생성

    def control_bar_frame(self):
        self.control_bar_f = tk.Frame(self.window, width=600, height=70, bg=self.bg_color, bd=1, relief="solid")
        self.control_bar_f.pack(fill='x')
        self.control_bar_f.pack_propagate(0)
        
        close_btn = tk.Button(self.control_bar_f, text="취소", bg="white", font=("Arial", 12, "bold"), command=self.window.destroy)
        close_btn.pack(side="right", padx=10, pady=10)

        delete_btn = tk.Button(self.control_bar_f, text="저장", bg="white", font=("Arial", 12, "bold"), command=lambda: self.control_event("저장"))
        delete_btn.pack(side="right", padx=10, pady=10)

    def control_event(self, action):
        if action == "저장":
            try:
                # 수량이 숫자인지 확인 소수점도 포함해야함
                quantity_raw = self.quantity_entry.get()
                if len(quantity_raw.split(".")) == 1:    # 정수인경우
                    quantity = int(quantity_raw)
                else:
                    quantity = float(quantity_raw)
            except ValueError:
                messagebox.showerror("입력 오류", "수량은 숫자여야 합니다.")
                return

            name = self.item_name.get()
            # 영어로 돼 있는거 한글로 바구기
            category = ''
            if self.category == 'dairy_beverage': 
                category = '유제품 및 음료'
            elif self.category == 'processed_food': 
                category = '신선 가공식품'
            elif self.category == 'meat': 
                category = '냉장 육류'
            elif self.category == 'sauce': 
                category = '소스 및 조미료'
            elif self.category == 'vegetable': 
                category = '자연 신선식품'
            elif self.category == 'etc': 
                category = '기타'
                
            print('\n\ncategory:', category)
            # category = self.category_entry.get()
            
            db_success = db_manager.insert_item(
                name=name,
                category_name=category,
                exp_date=self.expiry_date,
                reg_date=self.reg_date,
                Dday=self.Dday,
                status = self.status,
                quantity = self.quantity,
                unit = self.unit,
                image_path=self.image_path,
                
            )
            
            if not db_success:
                messagebox.showerror("오류", "데이터베이스 저장에 실패했습니다.")
                return

            self.update_item_data = {
                'name': name,
                'category': category,
                'quantity': quantity,
                'unit': self.unit,
                'expiry_date': self.expiry_date,
                'status': self.status,
                'reg_date': self.reg_date,
                'Dday': self.Dday
            }
            
            if self.on_update:
                self.on_update(self.update_item_data)
                
            messagebox.showinfo("저장", '아이템 정보가 변경되었습니다.')
            self.window.destroy()  # 팝업 창 닫기

    def item_info_frame(self):
        self.info_f = tk.Frame(self.window, width=600, height=270, bg=self.bg_color)
        self.info_f.pack()
        self.info_f.pack_propagate(0)

    def image_frame(self, img_path=''):
        self.image_f = tk.Frame(self.info_f, width=250, height=230, bg=self.bg_color)
        self.image_f.pack(side="left", padx=10)
        self.image_f.pack_propagate(0)

        try: 
            img = Image.open(img_path)
            img = img.resize((250,230))
            photo = ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"이미지 로드 실패: {e}")
            return

        self.item_img = tk.Label(self.image_f, image=photo, bg='#f3f0e9')
        self.item_img.image = photo
        self.item_img.pack(side="top")

    def item_name_frame(self):            
        self.name_f = tk.Frame(self.info_f, width=350, height=50, bg=self.bg_color)
        self.name_f.pack(side="top", padx=10, pady=10)
        self.name_f.pack_propagate(0)
        
        self.item_name = tk.Entry(self.name_f, textvariable=tk.StringVar(value=self.item_data.get('name', '')), bg=self.bg_color, fg='black', font=("Arial", 20, "bold"))
        self.item_name.pack(side="left", padx=10)

    def info_left_frame(self):
        def label_img_load(img_path):
            try: 
                img = Image.open(img_path)
                img = img.resize((20,20))
                photo = ImageTk.PhotoImage(img)
                return photo
            except Exception as e:
                print(f"이미지 로드 실패: {e}")
                return None
            
        self.left_f = tk.Frame(self.info_f, width=160, height=180, bg=self.bg_color)
        self.left_f.pack(side="left")
        self.left_f.pack_propagate(0)
        
        # 수량 라벨
        self.quantity_frame = tk.Frame(self.left_f, bg=self.bg_color)
        self.quantity_frame.pack(side="top", fill='x', pady=15)

        quantity_photo = label_img_load("../img/quantity.png")
        self.quantity_icon = tk.Label(self.quantity_frame, image=quantity_photo, bg=self.bg_color)
        self.quantity_icon.image = quantity_photo
        self.quantity_icon.pack(side="left")

        quantity_l = tk.Label(self.quantity_frame, text=f"수량:", bg=self.bg_color, font=("Arial", 12))
        quantity_l.pack(side="left", padx=3)
        
        initial_q = self.item_data.get('quantity', 1)
        self.quantity_entry = tk.Entry(self.quantity_frame, textvariable=tk.StringVar(value=str(initial_q)), bg=self.bg_color, fg='black', font=("Arial", 12))
        self.quantity_entry.pack(side="left", padx=3)

        # 💡 [구조 수정] 카테고리 대형 프레임
        self.category_frame = tk.Frame(self.left_f, bg=self.bg_color)   
        self.category_frame.pack(side="top", fill='x', pady=5)
        
        # 1층: 아이콘 + "카테고리:" 글자 라인
        self.category_title_frame = tk.Frame(self.category_frame, bg=self.bg_color)
        self.category_title_frame.pack(side="top", anchor="w")

        category_photo = label_img_load("../img/category.png")            
        self.category_icon = tk.Label(self.category_title_frame, image=category_photo, bg=self.bg_color)
        self.category_icon.image = category_photo
        self.category_icon.pack(side="left")
        
        # 명칭을 '분류' -> '카테고리'로 변경 완료
        category_l = tk.Label(self.category_title_frame, text=f"카테고리:", bg=self.bg_color, font=("Arial", 12))
        category_l.pack(side="left", padx=3)

        # 2층: 드롭다운 리스트박스 (한 칸 밑으로 배치)
        category_list = ["유제품 및 음료", "신선 가공식품", "냉장 육류", "소스 및 조미료", "자연 신선식품", "기타"]
        self.category_var = tk.StringVar(value=self.category)
        
        self.category_entry = ttk.Combobox(
            self.category_frame, 
            textvariable=self.category, 
            values=category_list, 
            state="readonly", 
            font=("Arial", 11),
            width=14 # 밑으로 내려와 공간이 생겼으므로 가로 너비를 조금 더 넓힘(6 -> 10)
        )
        # side="top"으로 지정하여 1층 아래에 생성되게 하고, padx=25를 주어 아이콘 시작점 정렬을 맞췄습니다.
        self.category_entry.pack(side="top", anchor="w", padx=(25, 0), pady=(3, 0))

        # 단위
        self.unit_frame = tk.Frame(self.left_f, bg=self.bg_color)
        self.unit_frame.pack(side="top", fill='x', pady=15)

        unit_photo = label_img_load("../img/unit.png")
        self.unit_icon = tk.Label(self.unit_frame, image=unit_photo, bg=self.bg_color)
        self.unit_icon.image = unit_photo
        self.unit_icon.pack(side="left")
        
        unit_l = tk.Label(self.unit_frame, text=f"단위: {self.unit}", bg=self.bg_color, font=("Arial", 12))
        unit_l.pack(side="left", padx=3)

    def info_right_frame(self):
        def label_img_load(img_path):
            try: 
                img = Image.open(img_path)
                img = img.resize((20,20))
                photo = ImageTk.PhotoImage(img)
                return photo
            except Exception as e:
                print(f"이미지 로드 실패: {e}")
                return None
            
        self.right_f = tk.Frame(self.info_f, width=160, height=180, bg=self.bg_color)
        self.right_f.pack(side="left", fill='x', padx=5)
        self.right_f.pack_propagate(0)

        # 유통기한 라벨
        self.expiry_frame = tk.Frame(self.right_f, bg=self.bg_color)
        self.expiry_frame.pack(side="top", fill='x', pady=10)

        expiry_photo = label_img_load("../img/expiry.png")
        self.expiry_icon = tk.Label(self.expiry_frame, image=expiry_photo, bg=self.bg_color)
        self.expiry_icon.image = expiry_photo
        self.expiry_icon.pack(side="left")

        self.expiry_l = tk.Label(self.expiry_frame, text=f"유통기한\n {self.expiry_date}", bg=self.bg_color, font=("Arial", 10))
        self.expiry_l.pack(side="left", padx=3)

        def control_event(item_date_str):
            expiry_window = tk.Toplevel(self.window)
            expiry_window.title("유통기한 변경")
            
            width = self.window.winfo_screenwidth()
            height = self.window.winfo_screenheight()
            expiry_window.geometry(f"420x280+{int(width/2-600/2)}+{int(height/2-340/2)}")   
            expiry_window.resizable(False, False)
            
            expiry_window.transient(self.window)
            expiry_window.grab_set()
            
            try:
                year, month, day = item_date_str.split("-")
            except ValueError:
                year, month, day = 2026, 1, 1

            self.calendar = Calendar(
                expiry_window, 
                selectmode='day', 
                year=int(year), month=int(month), day=int(day), 
                showweeknumbers=False, 
                locale='ko_KR',
                font=("Arial", 11),
                date_pattern='yyyy-mm-dd'
            )
            self.calendar.pack(side="left", padx=5, pady=5, fill="both", expand=True)
            
            def on_confirm():
                selected_date = self.calendar.get_date()
                messagebox.showinfo("유통기한변경", f"유통기한이 {selected_date}로 변경되었습니다.")
                self.expiry_date = selected_date  # 💡 로컬 변수 업데이트

                self.expiry_l.config(text=f"유통기한\n {selected_date}")
                
                from datetime import datetime
                today = datetime.today()
                expiry_dt = datetime.strptime(selected_date, "%Y-%m-%d")
                Dday_diff = (expiry_dt - today).days
                
                if Dday_diff < 0:
                    self.Dday_l.config(text=f"D+{abs(Dday_diff)}")
                    self.Dday = f"D+{abs(Dday_diff)}"
                else:
                    self.Dday_l.config(text=f"D-{abs(Dday_diff)}")
                    self.Dday = f"D-{abs(Dday_diff)}"

                if Dday_diff < 0:
                    self.status_l.config(text=f"상태: 만료", fg='red')
                    expired_photo = label_img_load("../img/expired.png")
                    self.status_icon.config(image=expired_photo)
                    self.status_icon.image = expired_photo
                    self.status = "만료"
                elif Dday_diff <= 3:
                    self.status_l.config(text=f"상태: 임박", fg='orange')
                    warning_photo = label_img_load("../img/warning.png")
                    self.status_icon.config(image=warning_photo)
                    self.status_icon.image = warning_photo
                    self.status = "임박"
                else:
                    self.status_l.config(text=f"상태: 신선", fg='green')
                    fresh_photo = label_img_load("../img/fresh.png")
                    self.status_icon.config(image=fresh_photo)
                    self.status_icon.image = fresh_photo
                    self.status = "신선"
    
                expiry_window.destroy()
                
            confirm_btn = tk.Button(
                expiry_window, 
                text="확인", 
                font=("Arial", 12, "bold"),
                bg="#e1e1e1",
                command=on_confirm
            )
            confirm_btn.pack(side="right", fill='both', expand=True, padx=(0, 5), pady=5)

        self.expiry_change = tk.Button(self.expiry_frame, text="변경", bg="white", font=("Arial", 14), command=lambda: control_event(self.expiry_date))
        self.expiry_change.pack(side="left", padx=3)

        # D-Day 라벨
        self.Dday_frame = tk.Frame(self.right_f, bg=self.bg_color)
        self.Dday_frame.pack(side="top", fill='x', pady=10)

        Dday_photo = label_img_load("../img/d_day.png")
        self.Dday_icon = tk.Label(self.Dday_frame, image=Dday_photo, bg=self.bg_color)
        self.Dday_icon.image = Dday_photo
        self.Dday_icon.pack(side="left")

        self.Dday_l = tk.Label(self.Dday_frame, text=f"D-Day\n   {self.Dday}", bg=self.bg_color, font=("Arial", 10))
        self.Dday_l.pack(side="left")

        # 상태 라벨
        self.status_frame = tk.Frame(self.right_f, bg=self.bg_color)
        self.status_frame.pack(side="top", fill='x', pady=3)
        
        if self.status == "신선":
            status_photo = label_img_load("../img/fresh.png")
            fg_color = 'green'
        elif self.status == "임박":
            status_photo = label_img_load("../img/warning.png")
            fg_color = 'orange'
        else:
            status_photo = label_img_load("../img/expired.png")
            fg_color = 'red'

        self.status_icon = tk.Label(self.status_frame, image=status_photo, bg=self.bg_color)
        self.status_icon.image = status_photo
        self.status_icon.pack(side="left", pady=10)

        self.status_l = tk.Label(self.status_frame, text=f"상태: {self.status}", bg=self.bg_color, font=("Arial", 12), fg=fg_color)
        self.status_l.pack(side="left", padx=3)

    def add_v_line(self, parent, side, color="#cdcdcd", fill="y", height=0):
        line = tk.Frame(parent, width=1.5, bg=color, height=height)
        line.pack(side=side, fill=fill)
        return line

if __name__ == "__main__":
    # 테스트 구동 시 실제 DB의 1번 아이템을 가져와서 수정해보는 시나리오 예시
    root = tk.Tk()
    root.withdraw()
    
    # 임의의 테스트 데이터 (실제 프로젝트에서는 DB에서 꺼낸 딕셔너리를 전달하면 됩니다)
    test_item = {
        'id': 1,
        'name': '맛있는 우유',
        'category': '음료',
        'quantity': 2,
        'unit': '개',
        'exp_date': '2026-06-30',
        'status': '신선',
        'reg_date': '2026-06-01',
        'Dday': 'D-19'
    }
    
    # 메인 페이지 새로고침을 담당할 임시 콜백 함수
    def my_refresh_callback(updated_data):
        print("\n[메인 새로고침 콜백 수신]:")
        print(updated_data)

    adjustment_page = ItemAdjustmentPage(root, test_item, on_update=my_refresh_callback)
    adjustment_page.window.mainloop()