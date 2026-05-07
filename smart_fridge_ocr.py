import cv2
import pytesseract
import re
import time
from picamera2 import Picamera2 # Pi 5 전용 공식 라이브러리 추가
from libcamera import controls # AF 모드 제어 위해 추가

# [1] 정규식 기반 유통기한 추출 함수
def extract_expiry_date(ocr_text):
    # 알파벳 오인식 방지 전처리
    clean_text = ocr_text.replace('O', '0').replace('o', '0').replace('I', '1').replace('i', '1')
    
    patterns = [
        r'20\d{6}',                       # 20XXXXXX 연속 8자리
        r'20\d{2}[.\s]+\d{2}[.\s]+\d{2}'  # 20XX. XX. XX 형식
    ]
    
    for p in patterns:
        match = re.search(p, clean_text)
        if match:
            raw_date = match.group()
            only_nums = re.sub(r'[^0-9]', '', raw_date)
            if len(only_nums) >= 8:
                date_str = only_nums[:8]
                return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return None

# [2] 조건부 적응형 전처리 및 OCR 실행 함수
def process_frame_for_date(frame):
    # 인식률을 위해 2배 확대 (도트 인식 필수)
    img = cv2.resize(frame, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 전처리 파이프라인 (Normal/Invert 혼합)
    stages = [
        {'name': 'Stage 1: Normal (No Invert)', 'kernel': None, 'iter': 0, 'invert': False},
        {'name': 'Stage 1: Inverted', 'kernel': None, 'iter': 0, 'invert': True},
        {'name': 'Stage 2: Light Blur', 'kernel': (3, 3), 'iter': 0, 'invert': True},
        {'name': 'Stage 3: Heavy Blur & Dilation', 'kernel': (5, 5), 'iter': 1, 'invert': True},
    ]

    for stage in stages:
        processed = gray.copy()
        
        # 블러 적용
        if stage['kernel'] is not None:
            processed = cv2.GaussianBlur(processed, stage['kernel'], 0)
            
        # 이진화 (Otsu)
        _, thresh = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 팽창 적용 (도트 이어붙이기)
        if stage['iter'] > 0:
            k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            thresh = cv2.dilate(thresh, k, iterations=stage['iter'])
            
        # 반전 로직 처리
        if stage['invert']:
            final_for_ocr = cv2.bitwise_not(thresh)
        else:
            final_for_ocr = thresh
            
        # OCR 실행 (실전에서는 psm 11 또는 7 사용)
        config = '--psm 11 -c preserve_interword_spaces=1'
        result = pytesseract.image_to_string(final_for_ocr, config=config)
        
        # 결과 검증
        date_match = extract_expiry_date(result)
        if date_match:
            print(f"✅ [{stage['name']}] get date!: {date_match}")
            return date_match
            
    return None
def run_realtime_ocr_pi5():
    print("Raspberry Pi 5 Picamera2 module initializing...")
    
    try:
        # Picamera2 객체 생성
        picam2 = Picamera2()
        
        # OpenCV가 좋아하는 BGR 포맷과 해상도로 셋팅
        config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "BGR888"})
        picam2.configure(config)
        picam2.start()
        print("turn on the camera successfully!")

        # ----------------------------------------------------
        # [새로 추가할 코드] 연속 자동 초점(CAF) 모드 켜기
        # AfMode - 0: 수동, 1: 자동(1회성), 2: 연속 자동 초점(Continuous)
        try:
            picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
            print("Continuous Auto Focus (CAF) feature activated.")
        except Exception as e:
            print(f"Focus control failed (AF not supported by lens): {e}")
        # ----------------------------------------------------
        
    except Exception as e:
        print(f"camera initialization failed: {e}")
        # print("Tip: 터미널에서 'libcamera-hello'를 쳐서 카메라 선이 제대로 꽂혀있는지 확인하세요.")
        return

    print("Align the expiry date within the square and press 'c'. (Exit: 'q')")

    try:
        while True:
            # VideoCapture 대신 Picamera2에서 직접 이미지 배열(Numpy)을 가져옴
            frame = picam2.capture_array()

            h, w, _ = frame.shape
            
            # 가이드 박스 크기 및 위치
            box_width, box_height = 300, 100
            x1 = (w - box_width) // 2
            y1 = (h - box_height) // 2
            x2 = x1 + box_width
            y2 = y1 + box_height

            display_frame = frame.copy()
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(display_frame, "Align Date & Press 'C'", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.imshow('Smart Fridge - Live OCR', display_frame)

            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('c'):
                print("\n--- Capture and OCR Analysis Started ---")
                roi = frame[y1:y2, x1:x2]
                
                # 우리가 만든 전처리+OCR 함수 호출
                found_date = process_frame_for_date(roi)
                
                if found_date:
                    print(f"🎉 Final recognized expiry date: {found_date}")
                else:
                    print("Recognition failed. Adjust lighting or focus and press 'c' again.")
            elif key == ord('q'):
                print("Exiting the program.")
                break
                
    finally:
        # 에러가 나거나 종료될 때 카메라 자원 안전하게 반환
        picam2.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    run_realtime_ocr_pi5()