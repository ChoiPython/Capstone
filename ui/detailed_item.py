import tkinter as tk
from PIL import Image, ImageTk
from tkinter import messagebox
from item_adj import ItemAdjustmentPage  # 아이템 수정 페이지 임포트

class DetailedItemPage:
    def __init__(self, master, item, on_update=None): # 이해하기 쉽도록 parent 대신 master로 명칭 변경
        self.bg_color = '#fafaf8'
        self.item_data = item
        self.main_master = master  # 부모 창 객체 저장
        self.on_update = on_update  # 데이터 업데이트 콜백 함수
        print(item)
        
        # 1. 새 팝업 창 생성 (넘겨받은 진짜 윈도우 창 객체를 부모로 지정)
        self.window = tk.Toplevel(master)
        self.window.title("아이템 상세 정보")
        self.window.configure(bg=self.bg_color)

        # ㅡㅡㅡㅡㅡㅡ UI 해상도 설정 ㅡㅡㅡㅡㅡㅡ
        width = self.window.winfo_screenwidth()
        height = self.window.winfo_screenheight()
        self.window.geometry(f"600x340+{int(width/2-600/2)}+{int(height/2-340/2)}")  
        self.window.resizable(False, False) 

        #ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ프레임 생성ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ
        self.control_bar_frame()  # 제어 바 프레임 생성
        self.item_info_frame()   # 아이템 정보 프레임 생성
        self.image_frame(img_path='img/milk.png')  # 이미지 프레임 생성 (테스트용 이미지 경로)
        self.item_name_frame()   # 아이템 이름 프레임 생성
        self.info_left_frame()   # 정보 왼쪽 프레임 생성
        self.add_v_line(self.info_f, "left", color="#cdcdcd", fill=None, height=180)  # 정보 프레임 안에 수직선 추가
        self.info_right_frame()  # 정보 오른쪽 프레임 생성


        
    def control_bar_frame(self):
        self.control_bar_f = tk.Frame(self.window, width=600, height=70, bg=self.bg_color, bd=1, relief="solid")
        self.control_bar_f.pack(fill='x')
        self.control_bar_f.pack_propagate(0)
        
        pin_btn = tk.Button(self.control_bar_f, text="고정", bg="white", font=("Arial", 12, "bold"), command=lambda: self.control_event("고정"))
        pin_btn.pack(side="left", padx=10, pady=10)

        close_btn = tk.Button(self.control_bar_f, text="닫기", bg="white", font=("Arial", 12, "bold"), command=self.window.destroy)
        close_btn.pack(side="right", padx=10, pady=10)

        delete_btn = tk.Button(self.control_bar_f, text="삭제", bg="white", font=("Arial", 12, "bold"), command=lambda: self.control_event("삭제"))
        delete_btn.pack(side="right", padx=10, pady=10)

        edit_btn = tk.Button(self.control_bar_f, text="수정", bg="white", font=("Arial", 12, "bold"), command=lambda: self.control_event("수정"))
        edit_btn.pack(side="right", padx=10, pady=10)


    def control_event(self, action):
        print(f"{action} 버튼 클릭됨")
        # 여기에 고정, 수정, 삭제 기능 구현 - DB 연동 필요
        # 삭제 먼저 구현 간단하니깐 ㅎㅎ
        if action == "삭제":            
            # 삭제하시겠습니까 알림 띄우기
            if messagebox.askyesno("삭제", f"'{self.item_data['name']}'을(를) 삭제하시겠습니까?"):
                self.on_update(self.item_data['id'], deleted=True)  # 삭제 콜백 함수 호출 (인벤토리 화면에서 처리)

                messagebox.showinfo("삭제", f"'{self.item_data['name']}'이(가) 삭제되었습니다.")
                self.window.destroy()  # 팝업 창 닫기

        if action == "수정":
            ItemAdjustmentPage(self.main_master, self.item_data, on_update=self.on_update)  # 아이템 수정 페이지 열기
            self.window.destroy()  # 상세 정보 창 닫기 (수정 페이지로 이동)
            # 인벤토리 화면 업데이트 로직 필요
            pass

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
        
        self.item_name = tk.Label(self.name_f, text=self.item_data['name'], bg=self.bg_color, fg='black', font=("Arial", 20, "bold"))
        self.item_name.pack(side="left", padx=10)
        
        self.category = tk.Label(self.name_f, text=f"카테고리: {self.item_data['category']}", bg=self.bg_color, fg='gray', font=("Arial", 10))
        self.category.pack(side="left")


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

        quantity_photo= label_img_load("img/quantity.png")              # 이미지
        self.quantity_icon = tk.Label(self.quantity_frame, image=quantity_photo, bg=self.bg_color)
        self.quantity_icon.image = quantity_photo
        self.quantity_icon.pack(side="left")

        quantity_l = tk.Label(self.quantity_frame, text=f"수량: {self.item_data['quantity']}{self.item_data['unit']}", bg=self.bg_color, font=("Arial", 12))    # 라벨
        quantity_l.pack(side="left", padx=3)

        # # 카테고리 라벨
        self.category_frame = tk.Frame(self.left_f, bg=self.bg_color)   # 프레임, bd=1, relief="solid"
        self.category_frame.pack(side="top", fill='x', pady=15)
        category_photo = label_img_load("img/category.png")            # 이미지

        self.category_icon = tk.Label(self.category_frame, image=category_photo, bg=self.bg_color)
        self.category_icon.image = category_photo
        self.category_icon.pack(side="left")
        
        category_l = tk.Label(self.category_frame, text=f"카테고리: {self.item_data['category']}", bg=self.bg_color, font=("Arial", 12))
        category_l.pack(side="left", padx=3)


        # # 단위 - L, ml, 개 등
        self.unit_frame = tk.Frame(self.left_f, bg=self.bg_color)   # 프레임, bd=1, relief="solid"
        self.unit_frame.pack(side="top", fill='x', pady=15)

        unit_photo = label_img_load("img/unit.png")            # 이미지
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

        expiry_photo = label_img_load("img/expiry.png")            # 이미지
        self.expiry_icon = tk.Label(self.expiry_frame, image=expiry_photo, bg=self.bg_color)
        self.expiry_icon.image = expiry_photo
        self.expiry_icon.pack(side="left")

        expiry_l = tk.Label(self.expiry_frame, text=f"유통기한\n   {self.item_data['expiry_date']}", bg=self.bg_color, font=("Arial", 10))    # 라벨
        expiry_l.pack(side="left", padx=3)

        self.d_day_frame = tk.Frame(self.right_f, bg=self.bg_color)   # 프레임, bd=1, relief="solid"
        self.d_day_frame.pack(side="top", fill='x', pady=10)

        d_day_photo = label_img_load("img/d_day.png")            # 이미지
        self.d_day_icon = tk.Label(self.d_day_frame, image=d_day_photo, bg=self.bg_color)
        self.d_day_icon.image = d_day_photo
        self.d_day_icon.pack(side="left")

        d_day_l = tk.Label(self.d_day_frame, text=f"D-Day\n   {self.item_data['d_day']}", bg=self.bg_color, font=("Arial", 10))    # 라벨
        d_day_l.pack(side="left")

        
        self.status_frame = tk.Frame(self.right_f, bg=self.bg_color)   # 프레임, bd=1, relief="solid"
        self.status_frame.pack(side="top", fill='x', pady=3)
        if self.item_data['status'] == "신선":
            status_photo = label_img_load("img/fresh.png")            # 이미지
            fg_color = 'green'
        elif self.item_data['status'] == "임박":
            status_photo = label_img_load("img/warning.png")            # 이미지
            fg_color = 'orange'
        elif self.item_data['status'] == "만료":
            status_photo = label_img_load("img/expired.png")            # 이미지
            fg_color = 'red'


        self.status_icon = tk.Label(self.status_frame, image=status_photo, bg=self.bg_color)
        self.status_icon.image = status_photo
        self.status_icon.pack(side="left", pady=10)

        status_l = tk.Label(self.status_frame, text=f"상태: {self.item_data['status']}", bg=self.bg_color, font=("Arial", 12), fg=fg_color)
        status_l.pack(side="left", padx=3)


        
        


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
    
    detailed_page = DetailedItemPage(root, test_item)
    detailed_page.window.mainloop()
