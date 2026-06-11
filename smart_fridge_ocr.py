import cv2
import pytesseract
import re
import time
from datetime import datetime  # 💡 [추가] 현재 년도를 가져오기 위해 필요합니다!
from picamera2 import Picamera2 
from libcamera import controls 
from yolov8 import detect_food_category
import numpy as np

# [1] 💡 대폭 강화된 유통기한 정규식 추출 함수 
def extract_expiry_date(ocr_text):
    # 알파벳 오인식 방지 전처리
    clean_text = ocr_text.replace('O', '0').replace('o', '0').replace('I', '1').replace('i', '1')
    
    # 시스템의 현재 년도를 가져옴 (예: "2024", "2026" 등)
    current_year = str(datetime.now().year)
    
    # 검색할 패턴 목록 (우선순위가 높은 긴 날짜부터 순서대로 찾음)
    patterns = [
        # 1순위: YYYY.MM.DD (예: 2026.06.20, 2026-06-20, 20260620 등)
        (r'20\d{2}[.\s\-\/]*[01]\d[.\s\-\/]*[0-3]\d', 8),
        
        # 2순위: YY.MM.DD (예: 26.06.20, 26 06 20, 260620 등)
        (r'[23]\d[.\s\-\/]*[01]\d[.\s\-\/]*[0-3]\d', 6),
        
        # 3순위: MM.DD (예: 06.20, 06/20, 06-20 등)
        # ※ 오작동 방지를 위해 월(01~12)과 일(01~31) 사이에 반드시 구분자(.)가 있도록 설정
        (r'([01]\d)[.\s\-\/]+([0-3]\d)', 4)
    ]
    
    for p, expected_len in patterns:
        match = re.search(p, clean_text)
        if match:
            # 3순위(MM.DD)가 발견되었을 때의 처리
            if expected_len == 4:
                month = match.group(1)
                day = match.group(2)
                # 월(1~12)과 일(1~31)이 상식적인 날짜 범위인지 1차 검증
                if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                    # 💡 현재 년도를 강제로 앞에 붙여줌!
                    return f"{current_year}-{month}-{day}"
            
            # 1순위, 2순위(YYYY.MM.DD / YY.MM.DD)가 발견되었을 때의 처리
            else:
                raw_date = match.group()
                nums = re.sub(r'[^0-9]', '', raw_date) # 숫자만 깔끔하게 추출
                
                # 8자리인 경우 (YYYYMMDD)
                if len(nums) == 8:
                    return f"{nums[:4]}-{nums[4:6]}-{nums[6:8]}"
                # 6자리인 경우 (YYMMDD)
                elif len(nums) == 6:
                    return f"20{nums[:2]}-{nums[2:4]}-{nums[4:6]}" 
                    
    return None

# [2] 전처리 및 OCR 함수 
def process_frame_for_date(frame):
    img = cv2.resize(frame, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 💡 [핵심 개선] 샤프닝(Sharpening) 필터 적용 
    # 글자의 윤곽선을 날카롭게 강조하여 6과 8, 3과 8의 구분을 명확하게 합니다.
    sharpen_kernel = np.array([[0, -1, 0], 
                               [-1, 5,-1], 
                               [0, -1, 0]])
    gray = cv2.filter2D(gray, -1, sharpen_kernel)
    
    # Tesseract 옵션: 숫자 인식률을 높이는 --oem 3 (기본 엔진) 추가
    tess_config = '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789.-/ '

    stages = [
        {'name': 'Adaptive Threshold', 'type': 'adaptive', 'blur': (3, 3)},
        {'name': 'Otsu Binary Inv', 'type': 'otsu_inv', 'blur': (3, 3)},
        {'name': 'Otsu Binary', 'type': 'otsu', 'blur': (3, 3)},
        {'name': 'High Contrast Otsu', 'type': 'contrast_otsu', 'blur': (5, 5)},
    ]

    for stage in stages:
        processed = gray.copy()
        
        # 블러를 너무 강하게 주면 글자가 뭉개지므로 가볍게만 처리
        if stage['blur']:
            processed = cv2.GaussianBlur(processed, stage['blur'], 0)
            
        if stage['type'] == 'adaptive':
            final_img = cv2.adaptiveThreshold(
                processed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
        elif stage['type'] == 'otsu_inv':
            _, final_img = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        elif stage['type'] == 'otsu':
            _, final_img = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif stage['type'] == 'contrast_otsu':
            processed = cv2.equalizeHist(processed)
            _, final_img = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        result = pytesseract.image_to_string(final_img, config=tess_config)
        
        date_match = extract_expiry_date(result)
        if date_match:
            print(f"✅ [{stage['name']}] 인식 성공!: {date_match}")
            return date_match
            
    return None

# [3] 🔥 실시간 자동 스캔 + 오류 해결 카메라 함수
def run_camera_scan():
    print("Raspberry Pi 5 Picamera2 module initializing...")
    window_name = 'Smart Fridge - Live OCR'
    
    try:
        picam2 = Picamera2()
        config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "BGR888"})
        picam2.configure(config)
        picam2.start()
        
        try:
            picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        except Exception as e:
            pass 
            
    except Exception as e:
        print(f"camera initialization failed: {e}")
        return None

    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    # 💡 [새로 추가할 코드] 모니터(LCD) 해상도를 구해 창을 정중앙으로 이동시킵니다.
    try:
        import tkinter as tk
        # 이미 home.py에서 실행 중인 tkinter 루트 창을 가져옵니다.
        root = tk._default_root 
        if root is not None:
            screen_w = root.winfo_screenwidth()
            screen_h = root.winfo_screenheight()
        else:
            # 혹시 단독 실행 시를 위한 예외 처리
            temp_root = tk.Tk()
            temp_root.withdraw()
            screen_w = temp_root.winfo_screenwidth()
            screen_h = temp_root.winfo_screenheight()
            temp_root.destroy()

        # 카메라 설정 해상도 (640x480)
        cam_w, cam_h = 640, 480
        
        # 정중앙 X, Y 좌표 계산
        center_x = int((screen_w - cam_w) / 2)
        center_y = int((screen_h - cam_h) / 2)
        
        # 창 이동
        cv2.moveWindow(window_name, center_x, center_y)
    except Exception as e:
        print(f"창 중앙 정렬 실패 (무시됨): {e}")
    touch_action = None

    def mouse_click(event, x, y, flags, param):
        nonlocal touch_action
        if event == cv2.EVENT_LBUTTONDOWN:
            # '닫기' 버튼 좌표 영역 터치 시
            if 520 <= x <= 640 and 0 <= y <= 60:
                touch_action = "CLOSE"

    cv2.setMouseCallback(window_name, mouse_click)

    # 💡 [추가] 너무 잦은 OCR 연산으로 인한 화면 버벅임(Lag)을 방지하기 위한 타이머
    last_ocr_time = time.time()

    try:
        while True:
            frame = picam2.capture_array()
            h, w, _ = frame.shape
            
            box_width, box_height = 300, 100
            x1 = (w - box_width) // 2
            y1 = (h - box_height) // 2
            x2 = x1 + box_width
            y2 = y1 + box_height

            display_frame = frame.copy()
            
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(display_frame, "Align Date inside the box", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # [닫기] 버튼 그리기 (빨간색, 우측 상단)
            cv2.rectangle(display_frame, (520, 0), (640, 60), (0, 0, 255), -1)
            cv2.putText(display_frame, "CLOSE", (535, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            cv2.imshow(window_name, display_frame)

            # 1. 닫기 버튼 터치 감지
            if touch_action == "CLOSE":
                print("process closed by user.")
                return None

            # 💡 2. [핵심] 실시간 연속 스캔 (1초에 한 번씩 검사)
            current_time = time.time()
            if current_time - last_ocr_time > 1.0:
                roi = frame[y1:y2, x1:x2]
                
                found_date = process_frame_for_date(roi)
                
                if found_date:
                    print(f"ocr success: {found_date}")
                    # 성공 시 화면에 피드백을 보여주고 0.5초 대기
                    cv2.putText(display_frame, "Success!", (250, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
                    cv2.imshow(window_name, display_frame)
                    cv2.waitKey(500)
                    
                    # YOLO 음식 카테고리 분석 후 리턴
                    detected_category = detect_food_category(frame)
                    return found_date, detected_category
                
                # 검사 후 타이머 초기화
                last_ocr_time = current_time

            # 키보드 q 눌러서 종료 기능도 유지
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                return None
                    
    finally:
        # 💡 [핵심] 다시 실행했을 때 카메라 오류가 나지 않도록 완전 초기화
        try:
            picam2.stop()
            picam2.close()  # 카메라 자원을 OS에 완전히 반납!
        except:
            pass
        cv2.destroyAllWindows()
        cv2.waitKey(1) # 라즈베리파이 Wayland/X11 GUI 버퍼 비우기 (좀비 창 방지)