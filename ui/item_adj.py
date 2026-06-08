import tkinter as tk
from PIL import Image, ImageTk
from tkinter import messagebox
from tkcalendar import Calendar
'''
아이템 수정 페이지: 품명, 수량, 카테고리, 단위, 유통기한만 수정함
카테고리 수정 -> 관련된 라벨 수정
유통기한 수정 -> D-Dat, 상태 같이 수정

수정페이지는 entery로 수정할 수 있게 함.

'''
class ItemAdjustmentPage:
    def __init__(self, master, item, on_update=None): # 이해하기 쉽도록 parent 대신 master로 명칭 변경
        self.bg_color = '#fafaf8'
        self.item_data = item
        self.status = item['status']  # 상태는 유통기한 변경 시 업데이트되므로 초기값으로 설정
        self.d_day = item['d_day']  # D-Day도 유통기한 변경 시 업데이트되므로 초기값으로 설정

        self.on_update = on_update
        
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
        
        # pin_btn = tk.Button(self.control_bar_f, text="고정", bg="white", font=("Arial", 12, "bold"), command=lambda: self.control_event("고정"))
        # pin_btn.pack(side="left", padx=10, pady=10)

        close_btn = tk.Button(self.control_bar_f, text="취소", bg="white", font=("Arial", 12, "bold"), command=self.window.destroy)
        close_btn.pack(side="right", padx=10, pady=10)

        delete_btn = tk.Button(self.control_bar_f, text="저장", bg="white", font=("Arial", 12, "bold"), command=lambda: self.control_event("저장"))
        delete_btn.pack(side="right", padx=10, pady=10)

        # edit_btn = tk.Button(self.control_bar_f, text="수정", bg="white", font=("Arial", 12, "bold"), command=lambda: self.control_event("수정"))
        # edit_btn.pack(side="right", padx=10, pady=10)


    def control_event(self, action):
        if action == "저장":
            try:
                # 수량이 숫자인지 확인 소수점도 포함해야함
                quantity = self.quantity_entry.get()
                print(f"입력된 수량: {quantity}")
                print(f"수량 입력 타입: {type(quantity)}")

                if len(quantity.split(".")) == 1:    # 정수인경우
                    quantity = int(quantity)
                    print(f"수량이 정수로 입력됨: {quantity}")
                else:
                    quantity = float(quantity)
                    print(f"수량이 소수로 입력됨: {quantity}")


            except ValueError:
                messagebox.showerror("입력 오류", "수량은 숫자여야 합니다.")
                return
            
            self.update_item = {
                'id': self.item_data['id'],  # 아이디는 수정 불가
                'name': self.item_name.get(),
                'category': self.category_entry.get(),
                'quantity': quantity,
                'unit': self.item_data['unit'],  # 단위는 수정 불가
                'expiry_date': self.item_data['expiry_date'],  # 유통기한은 달력에서 변경하므로 여기서는 기존 데이터 유지
                'status': self.status,  # 상태는 유통기한 변경 시 자동으로 업데이트되므로 여기서는 기존 데이터 유지
                'added_date': self.item_data['added_date'],  # 추가 날짜는 수정 불가
                'd_day': self.d_day  # D-Day도 유통기한 변경 시 자동으로 업데이트되므로 기존 데이터 유지
            }
            if self.on_update:
                self.on_update(self.update_item)
                
            messagebox.showinfo("저장", '아이템 정보가 변경되었습니다.')
            self.window.destroy()  # 팝업 창 닫기


    def item_info_frame(self):
        self.info_f = tk.Frame(self.window, width=600, height=270, bg=self.bg_color)
        self.info_f.pack()
        self.info_f.pack_propagate(0)

    def image_frame(self, img_path='', ):
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

        self.item_img = tk.Label(self.image_f, image=photo, bg='#f3f0e9')    #,d bd=1, relief="solid"
        self.item_img.image = photo
        self.item_img.pack(side="top")

    def item_name_frame(self):            
        self.name_f = tk.Frame(self.info_f, width=350, height=50, bg=self.bg_color)     #, bd=1, relief="solid"
        self.name_f.pack(side="top", padx=10, pady=10)
        self.name_f.pack_propagate(0)
        
        self.item_name = tk.Entry(self.name_f, textvariable=tk.StringVar(value=self.item_data['name']), bg=self.bg_color, fg='black', font=("Arial", 20, "bold"))
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
        self.quantity_frame = tk.Frame(self.left_f, bg=self.bg_color)   # 프레임, bd=1, relief="solid"
        self.quantity_frame.pack(side="top", fill='x', pady=15)

        quantity_photo= label_img_load("../img/quantity.png")              # 이미지
        self.quantity_icon = tk.Label(self.quantity_frame, image=quantity_photo, bg=self.bg_color)
        self.quantity_icon.image = quantity_photo
        self.quantity_icon.pack(side="left")

        quantity_l = tk.Label(self.quantity_frame, text=f"수량:", bg=self.bg_color, font=("Arial", 12))    # 라벨
        quantity_l.pack(side="left", padx=3)
        # 수량 엔트리는 데이터 저장할 때 숫자인지 판단해야함.
        self.quantity_entry = tk.Entry(self.quantity_frame, textvariable=tk.StringVar(value=self.item_data['quantity']), bg=self.bg_color, fg='black', font=("Arial", 12))
        self.quantity_entry.pack(side="left", padx=3)

        # # 카테고리 라벨
        self.category_frame = tk.Frame(self.left_f, bg=self.bg_color)   # 프레임, bd=1, relief="solid"
        self.category_frame.pack(side="top", fill='x', pady=15)
        category_photo = label_img_load("../img/category.png")            # 이미지

        self.category_icon = tk.Label(self.category_frame, image=category_photo, bg=self.bg_color)
        self.category_icon.image = category_photo
        self.category_icon.pack(side="left")
        
        category_l = tk.Label(self.category_frame, text=f"카테고리:", bg=self.bg_color, font=("Arial", 12))
        category_l.pack(side="left", padx=3)
    
        self.category_entry = tk.Entry(self.category_frame, textvariable=tk.StringVar(value=self.item_data['category']), bg=self.bg_color, fg='black', font=("Arial", 12))
        self.category_entry.pack(side="left", padx=3)


        # # 단위 - L, ml, 개 등
        self.unit_frame = tk.Frame(self.left_f, bg=self.bg_color)   # 프레임, bd=1, relief="solid"
        self.unit_frame.pack(side="top", fill='x', pady=15)

        unit_photo = label_img_load("../img/unit.png")            # 이미지
        self.unit_icon = tk.Label(self.unit_frame, image=unit_photo, bg=self.bg_color)
        self.unit_icon.image = unit_photo
        self.unit_icon.pack(side="left")
        
        unit_l = tk.Label(self.unit_frame, text=f"단위: {self.item_data['unit']}", bg=self.bg_color, font=("Arial", 12))
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
        self.expiry_frame = tk.Frame(self.right_f, bg=self.bg_color)   # 프레임, bd=1, relief="solid"
        self.expiry_frame.pack(side="top", fill='x', pady=10)

        expiry_photo = label_img_load("../img/expiry.png")            # 이미지
        self.expiry_icon = tk.Label(self.expiry_frame, image=expiry_photo, bg=self.bg_color)
        self.expiry_icon.image = expiry_photo
        self.expiry_icon.pack(side="left")

        self.expiry_l = tk.Label(self.expiry_frame, text=f"유통기한\n {self.item_data['expiry_date']}", bg=self.bg_color, font=("Arial", 10))    # 라벨
        self.expiry_l.pack(side="left", padx=3)

        
        def control_event(item):
            # 새로운 창 띄우기
            expiry_window = tk.Toplevel(self.window)
            expiry_window.title("유통기한 변경")
            
            width = self.window.winfo_screenwidth()
            height = self.window.winfo_screenheight()
            # 달력이 커졌으므로 팝업 창 해상도도 넉넉하게 확장합니다.
            expiry_window.geometry(f"420x280+{int(width/2-600/2)}+{int(height/2-340/2)}")   
            expiry_window.resizable(False, False)
            
            # 안전망: 모달 윈도우 설정 (메인 잠금)
            expiry_window.transient(self.window)
            expiry_window.grab_set()
            
            print(type(item), item)
            
            # font 속성을 지정하여 달력 크기를 훨씬 큼직하게 키웠습니다.
            year=item.split("-")[0]
            month=item.split("-")[1]
            day=item.split("-")[2]
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
            # 달력창 띄우면 수정창 비활성화
            
            def on_confirm():
                selected_date = self.calendar.get_date()
                print(f"선택된 날짜: {selected_date}")
                # DB에 선택된 날짜로 유통기한 업데이트 로직 필요
                messagebox.showinfo("유통기한 변경", f"유통기한이 {selected_date}로 변경되었습니다.")   # 이 알람을 빼도 될듯..의견필요!
                self.item_data['expiry_date'] = selected_date  # 아이템 데이트 업데이트 (실제 DB 연동 시에도 업데이트 필요)

                '''
                유통기한 변경 시 D-Day와 상태 라벨도 같이 업데이트해야 함
                D-Day는 오늘 날짜와 유통기한의 차이로 계산
                '''
                # 1. 유통기한 라벨 바꾸기
                self.expiry_l.config(text=f"유통기한\n {selected_date}")
                # 2. D-Day 계산해서 라벨 바꾸기
                from datetime import datetime
                today = datetime.today()
                expiry_date = datetime.strptime(selected_date, "%Y-%m-%d")
                d_day_diff = (expiry_date - today).days
                if d_day_diff < 0:
                    self.d_day_l.config(text=f"D+{abs(d_day_diff)}")
                    self.d_day = f"D+{abs(d_day_diff)}"  # D-Day 업데이트
                else:
                    self.d_day_l.config(text=f"D-{d_day_diff}")
                    self.d_day = f"D-{d_day_diff}"  # D-Day 업데이트

                # 3. 상태 업데이트하기 (신선, 임박, 만료)
                if d_day_diff < 0:
                    self.status_l.config(text=f"상태: 만료", fg='red')
                    expired_photo = label_img_load("../img/expired.png")
                    self.status_icon.config(image=expired_photo)
                    self.status_icon.image = expired_photo
                    self.status = "만료"  # 상태 업데이트

                elif d_day_diff <= 3:  # 임박 기준은 3일 이내로 설정
                    self.status_l.config(text=f"상태: 임박", fg='orange')
                    warning_photo = label_img_load("../img/warning.png")
                    self.status_icon.config(image=warning_photo)
                    self.status_icon.image = warning_photo
                    self.status = "임박"  # 상태 업데이트

                else:
                    self.status_l.config(text=f"상태: 신선", fg='green')
                    fresh_photo = label_img_load("../img/fresh.png")
                    self.status_icon.config(image=fresh_photo)
                    self.status_icon.image = fresh_photo
                    self.status = "신선"  # 상태 업데이트
    

                expiry_window.destroy()  # 팝업 창 닫기
                
            # fill='both', expand=True 옵션을 주어 달력 오른쪽 남은 공간을 버튼이 꽉 채우도록 했습니다.
            confirm_btn = tk.Button(
                expiry_window, 
                text="확인", 
                font=("Arial", 12, "bold"),
                bg="#e1e1e1",
                command=on_confirm
            )
            confirm_btn.pack(side="right", fill='both', expand=True, padx=(0, 5), pady=5)

        self.expiry_change = tk.Button(self.expiry_frame, text="변경", bg="white", font=("Arial", 14), command=lambda: control_event(self.item_data['expiry_date']))
        self.expiry_change.pack(side="left", padx=3)


        self.d_day_frame = tk.Frame(self.right_f, bg=self.bg_color)   # 프레임, bd=1, relief="solid"
        self.d_day_frame.pack(side="top", fill='x', pady=10)

        d_day_photo = label_img_load("../img/d_day.png")            # 이미지
        self.d_day_icon = tk.Label(self.d_day_frame, image=d_day_photo, bg=self.bg_color)
        self.d_day_icon.image = d_day_photo
        self.d_day_icon.pack(side="left")

        self.d_day_l = tk.Label(self.d_day_frame, text=f"D-Day\n   {self.item_data['d_day']}", bg=self.bg_color, font=("Arial", 10))    # 라벨
        self.d_day_l.pack(side="left")

        
        self.status_frame = tk.Frame(self.right_f, bg=self.bg_color)   # 프레임, bd=1, relief="solid"
        self.status_frame.pack(side="top", fill='x', pady=3)
        if self.item_data['status'] == "신선":
            status_photo = label_img_load("../img/fresh.png")            # 이미지
            fg_color = 'green'
        elif self.item_data['status'] == "임박":
            status_photo = label_img_load("../img/warning.png")            # 이미지
            fg_color = 'orange'
        elif self.item_data['status'] == "만료":
            status_photo = label_img_load("../img/expired.png")            # 이미지
            fg_color = 'red'


        self.status_icon = tk.Label(self.status_frame, image=status_photo, bg=self.bg_color)
        self.status_icon.image = status_photo
        self.status_icon.pack(side="left", pady=10)

        self.status_l = tk.Label(self.status_frame, text=f"상태: {self.item_data['status']}", bg=self.bg_color, font=("Arial", 12), fg=fg_color)
        self.status_l.pack(side="left", padx=3)


    def add_v_line(self, parent, side, color="#cdcdcd", fill="y", height=0):
        line = tk.Frame(parent, width=1.5, bg=color, height=height)
        line.pack(side=side, fill=fill)
        return line


        

        



if __name__ == "__main__":
    # 테스트용 코드 - 실제로는 InventoryPage에서 DetailedItemPage를 호출할 때 사용
    root = tk.Tk()
    root.withdraw()  # 메인 윈도우 숨기기 (테스트용)
    
    # 테스트 아이템 데이터
    test_item = {
        'name': '우유',
        'category': '음료',
        'quantity': 1,
        'unit': '개',
        'expiry_date': '2026-04-30',
        'status': '임박',
        'added_date': '2024-06-25',
        'd_day': 'D+21'
    }
    
    adjustment_page = ItemAdjustmentPage(root, test_item)
    adjustment_page.window.mainloop()
