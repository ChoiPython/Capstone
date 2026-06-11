import cv2
import os
import time
from ultralytics import YOLO

# 무거운 모델을 매 프레임 로드하지 않고 재사용하기 위한 전역 변수
_yolo_model = None

def detect_food_category(frame, model_path="/home/oldmans/smart_fridge_ver1/best.pt", save_dir="captured_images"):
    global _yolo_model

    # 1. 모델이 없으면 최초 1회만 기동 (렉 방지 핵심)
    if _yolo_model is None:
        print(f"⏳ [YOLO] 모델({model_path})을 최초 로드합니다...")
        try:
            _yolo_model = YOLO(model_path)
            print("✅ [YOLO] 모델 로드가 완료되었습니다.")
        except Exception as e:
            print(f"❌ [YOLO] 모델 로드 실패: {e}")
            return None, None

    # 2. 크롭 이미지를 저장할 폴더 자동 생성
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    try:
        # stream=True로 연산 속도 최적화
        results = _yolo_model(frame, stream=True, verbose=False)
        
        highest_conf = 0.0
        detected_class_name = None
        best_box_coords = None  
        
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                # 확신도(Confidence)가 가장 높은 물체를 탐지
                if conf > highest_conf:
                    highest_conf = conf
                    class_id = int(box.cls[0])
                    detected_class_name = _yolo_model.names[class_id]
                    best_box_coords = box.xyxy[0].cpu().numpy()
        
        # 3. 신뢰도가 40% 이상인 진짜 물체를 찾은 경우 이미지 크롭 및 저장
        if highest_conf >= 0.40 and best_box_coords is not None:
            # 파일명이 중복되지 않도록 현재 타임스탬프 밀리초 사용
            timestamp = int(time.time() * 1000)
            saved_img_path = os.path.join(save_dir, f"item_{timestamp}.jpg")
            
            x1, y1, x2, y2 = map(int, best_box_coords)
            h, w, _ = frame.shape
            
            # 프레임 경계 밖을 넘어가지 않도록 방어 코드 추가
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            # 사각형 영역만큼 크롭
            cropped_img = frame[y1:y2, x1:x2]
            
            # 크롭된 이미지 파일 저장
            if cropped_img.size > 0:
                cv2.imwrite(saved_img_path, cropped_img)
                print(f"🎯 [YOLO] 물체 포착: {detected_class_name} ({highest_conf*100:.1f}%) -> 저장 완료: {saved_img_path}")
                return detected_class_name, saved_img_path
            
        return None, None
            
    except Exception as e:
        print(f"❌ YOLO 연산 에러: {e}")
        return None, None