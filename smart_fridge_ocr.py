import cv2
import pytesseract
import re
import time
from picamera2 import Picamera2 
from libcamera import controls 
from yolov8 import detect_food_category

# [1] 유통기한 추출 함수 
def extract_expiry_date(ocr_text):
    clean_text = ocr_text.replace('O', '0').replace('o', '0').replace('I', '1').replace('i', '1')
    patterns = [r'20\d{6}', r'20\d{2}[.\s]+\d{2}[.\s]+\d{2}']
    for p in patterns:
        match = re.search(p, clean_text)
        if match:
            raw_date = match.group()
            only_nums = re.sub(r'[^0-9]', '', raw_date)
            if len(only_nums) >= 8:
                date_str = only_nums[:8]
                return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return None

# [2] 전처리 및 OCR 함수 
def process_frame_for_date(frame):
    img = cv2.resize(frame, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    stages = [
        {'name': 'Stage 1: Normal', 'kernel': None, 'iter': 0, 'invert': False},
        {'name': 'Stage 1: Inverted', 'kernel': None, 'iter': 0, 'invert': True},
        {'name': 'Stage 2: Light Blur', 'kernel': (3, 3), 'iter': 0, 'invert': True},
        {'name': 'Stage 3: Heavy Blur & Dilation', 'kernel': (5, 5), 'iter': 1, 'invert': True},
    ]

    for stage in stages:
        processed = gray.copy()
        if stage['kernel'] is not None:
            processed = cv2.GaussianBlur(processed, stage['kernel'], 0)
        _, thresh = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        if stage['iter'] > 0:
            k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            thresh = cv2.dilate(thresh, k, iterations=stage['iter'])
        
        final_for_ocr = cv2.bitwise_not(thresh) if stage['invert'] else thresh
        config = '--psm 11 -c preserve_interword_spaces=1'
        result = pytesseract.image_to_string(final_for_ocr, config=config)
        
        date_match = extract_expiry_date(result)
        if date_match:
            print(f"✅ [{stage['name']}] get date!: {date_match}")
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
                print("사용자가 화면의 'CLOSE' 버튼을 터치하여 종료합니다.")
                return None

            # 💡 2. [핵심] 실시간 연속 스캔 (1초에 한 번씩 검사)
            current_time = time.time()
            if current_time - last_ocr_time > 1.0:
                roi = frame[y1:y2, x1:x2]
                
                found_date = process_frame_for_date(roi)
                
                if found_date:
                    print(f"🎉 자동 인식 성공: {found_date}")
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