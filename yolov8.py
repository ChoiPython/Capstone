import cv2
from ultralytics import YOLO

# =================================================================
# [3] YOLOv8 기반 스마트 냉장고 6대 카테고리 탐지 함수
# =================================================================
def detect_food_category(frame, model_path="best.pt"):
    """
    카메라 프레임을 받아 학습된 YOLOv8 모델로 6대 카테고리 중 
    가장 확률이 높은 음식을 탐지하여 이름(클래스명)을 반환하는 함수
    """
    try:
        # 1. 가중치 파일(best.pt) 로드
        model = YOLO(model_path)
        
        # 2. 이미지 추론 (라즈베리파이 메모리 절약을 위해 stream=True 권장)
        # verbose=False를 주면 터미널 창에 불필요한 로그가 찍히지 않아 깔끔합니다.
        results = model(frame, stream=True, verbose=False)
        
        highest_conf = 0.0
        detected_class_name = "Unknown"  # 아무것도 발견되지 않았을 때 기본값
        
        # 3. 탐지된 결과 분석 (가장 신뢰도(Confidence)가 높은 물체 1개 고르기)
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # 신뢰도 점수 (0.0 ~ 1.0)
                conf = float(box.conf[0])
                
                # 여러 개가 잡혔다면 그중 가장 확실한(확률이 높은) 물체 하나만 선택
                if conf > highest_conf:
                    highest_conf = conf
                    # 클래스 번호 점수 -> 영문 클래스명 변환
                    class_id = int(box.cls[0])
                    detected_class_name = model.names[class_id]
        
        # 임계값 설정 (예: 40% 이상의 확률로 확신할 때만 정답으로 인정)
        if highest_conf >= 0.40:
            print(f"🎯 YOLO 탐지 성공: {detected_class_name} (신뢰도: {highest_conf*100:.1f}%)")
            return detected_class_name
        else:
            print("❓ YOLO 탐지 결과: 무엇인지 확실하게 판별할 수 없습니다. (기타/Unknown)")
            return "etc"  # 확신이 없을 때는 안전하게 etc(기타) 반환
            
    except Exception as e:
        print(f"❌ YOLO 실행 중 오류 발생: {e}")
        return "etc"