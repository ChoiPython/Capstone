import cv2
import pytesseract
import re
import time
from picamera2 import Picamera2 # Pi 5 전용 공식 라이브러리
from libcamera import controls  # AF 모드 제어용
from yolov8 import detect_food_category # YOLO 모델 연동용

# =================================================================
# [1] 정규식 기반 유통기한 추출 함수 (기존 로직 유지)
# =================================================================
def extract_expiry_date(ocr_text):
    # 알파벳 오인식 방지 전처리
    clean_text = ocr_text.replace('O', '0').replace('o', '0').replace('I', '1').replace('i', '1')
    
    patterns = [
        r'20\d{6}',                        # 1. 20XXXXXX 연속 8자리 (예: 20260609)
        r'20\d{2}[.\s]+\d{2}[.\s]+\d{2}',  # 2. 20XX. XX. XX 형식 (예: 2026. 06. 09)
        r'\d{2}[.\s]+\d{2}[.\s]+\d{2}'     # 3. XX. XX. XX 형식 (예: 26.06.09 또는 26 06 09) -> 추가!
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

# =================================================================
# [2] 조건부 적응형 전처리 및 OCR 실행 함수 (기존 로직 유지)
# =================================================================
def process_frame_for_date(frame):
    # 인식률을 위해 2배 확대
    resized = cv2.resize(frame, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    
    # 1차 시도: 기본 그레이스케일 상태에서 OCR 실행
    config = '--psm 6 -c tessedit_char_whitelist=0123456789.OoIi'
    text_mode1 = pytesseract.image_to_string(gray, config=config)
    date_mode1 = extract_expiry_date(text_mode1)
    if date_mode1:
        return date_mode1
        
    # 2차 시도: 적응형 임계처리(Adaptive Threshold) 적용 후 OCR 실행 (어두운 환경 대비)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    text_mode2 = pytesseract.image_to_string(thresh, config=config)
    return extract_expiry_date(text_mode2)

# =================================================================
# [3] 실시간 1초 주기 연속 자동 스캔 함수 (YOLO 연동 버전)
# =================================================================
def run_continuous_ocr():
    print("라즈베리파이 5 카메라 모듈(자동 스캔 모드) 초기화 중...")
    
    try:
        picam2 = Picamera2()
        # 카메라 설정 (라즈베리파이 센서 규격에 맞게 BGR 포맷 지정)
        config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "BGR888"})
        picam2.configure(config)
        picam2.start()
        
        # [초점 대비] 연속 자동초점 설정 (지원 모듈용)
        try:
            picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        except:
            pass 
            
        print("🎥 카메라 ON! 제품의 유통기한을 초록색 박스 안에 맞춰주세요.")
        
    except Exception as e:
        print(f"❌ 카메라 에러: {e}")
        return None

    # 자동 스캔 타이머 및 주기 설정
    last_scan_time = time.time()
    scan_interval = 1.0  # 1.0초마다 한 번씩 OCR 연산 수행 (라즈베리파이 부하 방지)

    try:
        while True:
            # 실시간 프레임 캡처
            frame = picam2.capture_array()
            
            h, w, _ = frame.shape
            
            # 가이드 박스 정의 (중앙)
            box_width, box_height = 300, 100
            x1 = (w - box_width) // 2
            y1 = (h - box_height) // 2
            x2 = x1 + box_width
            y2 = y1 + box_height

            # 화면 출력용 가이드 그리기
            display_frame = frame.copy()
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(display_frame, "Scanning Date...", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # 모니터에 화면 표시
            cv2.imshow('Smart Fridge - Auto Scanner', display_frame)

            # --- 주기적 자동 스캔 체크 ---
            current_time = time.time()
            if current_time - last_scan_time > scan_interval:
                print("⏳ 유통기한 탐지 중...")
                
                # 초록색 박스 내부 영역만 슬라이싱하여 OCR 분석
                roi = frame[y1:y2, x1:x2]
                found_date = process_frame_for_date(roi)
                
                # 유통기한이 정상 인식되었다면?
                if found_date:
                    print(f"\n🎉 유통기한 자동 인식 완료: {found_date}")
                    
                    # 💡 유통기한이 찍힌 바로 그 프레임으로 YOLO 음식 분류 실행
                    print("🚀 YOLOv8 분류 엔진 가동...")
                    detected_category = detect_food_category(frame, model_path="best.pt")
                    print(f"✅ 분류 결과: {detected_category}")
                    
                    # 카메라 리소스 완벽히 해제 후 데이터 반환
                    picam2.stop()
                    picam2.close() 
                    cv2.destroyAllWindows()
                    return found_date, detected_category # UI 파일로 전달
                
                # 실패 시 타이머 초기화 후 다음 루프 대기
                last_scan_time = current_time

            # 'q'를 누르면 스캔 강제 종료 (안전장치)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    finally:
        # 무조건 실행되는 리소스 안전 종료문
        try:
            picam2.stop()
            picam2.close()
        except:
            pass
        cv2.destroyAllWindows()
        
    return None