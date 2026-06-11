import cv2
import pytesseract
import re
import time
from datetime import datetime
from picamera2 import Picamera2 
from libcamera import controls 
from yolov8 import detect_food_category
import numpy as np

# [1] 💡 대폭 강화된 유통기한 정규식 추출 함수 
def extract_expiry_date(ocr_text):
    clean_text = ocr_text.replace('O', '0').replace('o', '0').replace('I', '1').replace('i', '1')
    current_year = str(datetime.now().year)
    
    patterns = [
        (r'20\d{2}[.\s\-\/]*[01]\d[.\s\-\/]*[0-3]\d', 8),
        (r'[23]\d[.\s\-\/]*[01]\d[.\s\-\/]*[0-3]\d', 6),
        (r'([01]\d)[.\s\-\/]+([0-3]\d)', 4)
    ]
    
    for p, expected_len in patterns:
        match = re.search(p, clean_text)
        if match:
            if expected_len == 4:
                month = match.group(1)
                day = match.group(2)
                if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                    return f"{current_year}-{month}-{day}"
            else:
                raw_date = match.group()
                nums = re.sub(r'[^0-9]', '', raw_date)
                if len(nums) == 8:
                    return f"{nums[:4]}-{nums[4:6]}-{nums[6:8]}"
                elif len(nums) == 6:
                    return f"20{nums[:2]}-{nums[2:4]}-{nums[4:6]}" 
                    
    return None

# [2] 전처리 및 OCR 함수 
def process_frame_for_date(frame):
    img = cv2.resize(frame, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    sharpen_kernel = np.array([[0, -1, 0], 
                               [-1, 5,-1], 
                               [0, -1, 0]])
    gray = cv2.filter2D(gray, -1, sharpen_kernel)
    
    tess_config = '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789.-/ '

    stages = [
        {'name': 'Adaptive Threshold', 'type': 'adaptive', 'blur': (3, 3)},
        {'name': 'Otsu Binary Inv', 'type': 'otsu_inv', 'blur': (3, 3)},
        {'name': 'Otsu Binary', 'type': 'otsu', 'blur': (3, 3)},
        {'name': 'High Contrast Otsu', 'type': 'contrast_otsu', 'blur': (5, 5)},
    ]

    for stage in stages:
        processed = gray.copy()
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

# [3] 🔥 실시간 순차 자동 스캔 카메라 함수
def run_camera_scan():
    final_date = None
    final_category = None
    final_image_path = None
    
    # -------------------------------------------------------------
    # 📌 [STEP 1] 유통기한(OCR) 인식 단계 (자동 스캔 유지)
    # -------------------------------------------------------------
    print("Raspberry Pi 5 Picamera2 module initializing for OCR...")
    window_name_ocr = 'Smart Fridge - STEP 1 (OCR)'
    touch_action = None

    def mouse_click_ocr(event, x, y, flags, param):
        nonlocal touch_action
        if event == cv2.EVENT_LBUTTONDOWN:
            if 520 <= x <= 640 and 0 <= y <= 60:
                touch_action = "CLOSE"

    try:
        picam2 = Picamera2()
        config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "BGR888"})
        picam2.configure(config)
        picam2.start()
        try:
            picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        except:
            pass
    except Exception as e:
        print(f"OCR 단계 카메라 초기화 실패: {e}")
        return None, None, None

    cv2.namedWindow(window_name_ocr, cv2.WINDOW_AUTOSIZE)
    
    try:
        import tkinter as tk
        root = tk._default_root 
        if root is None:
            temp_root = tk.Tk()
            temp_root.withdraw()
            screen_w, screen_h = temp_root.winfo_screenwidth(), temp_root.winfo_screenheight()
            temp_root.destroy()
        else:
            screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
        cv2.moveWindow(window_name_ocr, int((screen_w - 640) / 2), int((screen_h - 480) / 2))
    except:
        pass

    cv2.setMouseCallback(window_name_ocr, mouse_click_ocr)
    last_ocr_time = time.time()

    try:
        while True:
            frame = picam2.capture_array()
            h, w, _ = frame.shape
            
            box_w, box_h = 300, 100
            x1, y1 = (w - box_w) // 2, (h - box_h) // 2
            x2, y2 = x1 + box_w, y1 + box_h

            display_frame = frame.copy()
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(display_frame, "Align Date inside the box", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # [닫기] 버튼
            cv2.rectangle(display_frame, (520, 0), (640, 60), (0, 0, 255), -1)
            cv2.putText(display_frame, "CLOSE", (535, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            cv2.imshow(window_name_ocr, display_frame)

            key = cv2.waitKey(1) & 0xFF
            if touch_action == "CLOSE" or key == ord('q'):
                print("사용자에 의해 프로세스가 종료되었습니다.")
                return None, None, None

            current_time = time.time()
            if current_time - last_ocr_time > 1.0:
                roi = frame[y1:y2, x1:x2]
                found_date = process_frame_for_date(roi)
                
                if found_date:
                    final_date = found_date
                    cv2.putText(display_frame, "Success!", (250, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
                    cv2.imshow(window_name_ocr, display_frame)
                    cv2.waitKey(500)
                    break
                last_ocr_time = current_time

    finally:
        try:
            picam2.stop()
            picam2.close()
        except:
            pass
        cv2.destroyAllWindows()
        cv2.waitKey(1)

    # -------------------------------------------------------------
    # 📌 [STEP 2] 제품(YOLO) 인식 및 수동 캡처(버튼) 단계
    # -------------------------------------------------------------
    print("Raspberry Pi 5 Picamera2 module re-initializing for YOLO...")
    time.sleep(0.3) 
    window_name_yolo = 'Smart Fridge - STEP 2 (YOLO)'
    touch_action = None

    def mouse_click_yolo(event, x, y, flags, param):
        nonlocal touch_action
        if event == cv2.EVENT_LBUTTONDOWN:
            # 우측 상단 CLOSE 버튼
            if 520 <= x <= 640 and 0 <= y <= 60:
                touch_action = "CLOSE"
            # 💡 하단 중앙 SCAN 버튼 영역 터치 감지
            elif 220 <= x <= 420 and 400 <= y <= 460:
                touch_action = "SCAN"

    try:
        picam2 = Picamera2()
        config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "BGR888"})
        picam2.configure(config)
        picam2.start()
        try:
            picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        except:
            pass
    except Exception as e:
        print(f"YOLO 단계 카메라 초기화 실패: {e}")
        return final_date, None, None

    cv2.namedWindow(window_name_yolo, cv2.WINDOW_AUTOSIZE)
    try:
        cv2.moveWindow(window_name_yolo, int((screen_w - 640) / 2), int((screen_h - 480) / 2))
    except:
        pass

    cv2.setMouseCallback(window_name_yolo, mouse_click_yolo)

    try:
        while True:
            frame = picam2.capture_array()
            h, w, _ = frame.shape
            
            box_w, box_h = 400, 350
            x1, y1 = (w - box_w) // 2, (h - box_h) // 2
            x2, y2 = x1 + box_w, y1 + box_h

            display_frame = frame.copy()
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 128, 0), 2)
            cv2.putText(display_frame, "Place Product & Press SCAN", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 128, 0), 2)
            cv2.putText(display_frame, f"Date: {final_date}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # [닫기] 버튼 그리기 (빨간색)
            cv2.rectangle(display_frame, (520, 0), (640, 60), (0, 0, 255), -1)
            cv2.putText(display_frame, "CLOSE", (535, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            # 💡 [스캔] 버튼 그리기 (초록색, 하단 중앙)
            cv2.rectangle(display_frame, (220, 400), (420, 460), (0, 200, 0), -1)
            cv2.putText(display_frame, "SCAN", (270, 440), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)

            cv2.imshow(window_name_yolo, display_frame)

            key = cv2.waitKey(1) & 0xFF

            # 종료 조건
            if touch_action == "CLOSE" or key == ord('q'):
                print("사용자에 의해 프로세스가 종료되었습니다.")
                return final_date, None, None

            # 💡 사용자가 직접 버튼을 누르거나 's' 키를 눌렀을 때만 YOLO 동작
            if touch_action == "SCAN" or key == ord('s'):
                # 화면에 스캔 중임을 표시하고 한 번 업데이트
                cv2.putText(display_frame, "Scanning...", (240, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
                cv2.imshow(window_name_yolo, display_frame)
                cv2.waitKey(50) 
                
                print("스캔 버튼 클릭됨! YOLO 분석을 1회 실행합니다...")
                model_full_path = "/home/oldmans/smart_fridge_ver1/best.pt"
                detected_category, saved_img_path = detect_food_category(frame, model_path=model_full_path)
                
                if detected_category:
                    print(f"✅ yolo success: {detected_category}")
                    cv2.putText(display_frame, f"Matched: {detected_category}", (180, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
                    cv2.imshow(window_name_yolo, display_frame)
                    cv2.waitKey(1000)
                    
                    return final_date, detected_category, saved_img_path
                else:
                    print("❌ 물체를 인식하지 못했습니다. 다시 시도해 주세요.")
                    # 인식 실패 시 에러 메시지 띄워주고 다시 버튼을 누를 수 있게 초기화
                    cv2.putText(display_frame, "Not Found! Try Again.", (150, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
                    cv2.imshow(window_name_yolo, display_frame)
                    cv2.waitKey(1000)
                    touch_action = None 

    finally:
        try:
            picam2.stop()
            picam2.close()
        except:
            pass
        cv2.destroyAllWindows()
        cv2.waitKey(1)

if __name__ == "__main__":
    date, category, img_path = run_camera_scan()
    print("\n=== 최종 스캔 결과 ===")
    print(f"유통기한: {date}")
    print(f"카테고리: {category}")
    print(f"이미지 경로: {img_path}")