import cv2
import os
import time
from ultralytics import YOLO

# =================================================================
# [3] YOLOv8 기반 스마트 냉장고 6대 카테고리 탐지 & 이미지 저장 함수
# =================================================================
def detect_food_category(frame, model_path="best.pt", save_dir="captured_images"):
    """
    카메라 프레임을 받아 학습된 YOLOv8 모델로 카테고리를 탐지하고,
    해당 물체 영역(박스)만 잘라내어 이미지로 저장한 뒤 
    (클래스명, 저장된_이미지_경로)를 반환하는 함수
    """
    # 1. 이미지를 저장할 폴더가 없으면 자동 생성
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    try:
        model = YOLO(model_path)
        results = model(frame, stream=True, verbose=False)
        
        highest_conf = 0.0
        detected_class_name = "etc"
        best_box_coords = None  # 가장 신뢰도가 높은 물체의 좌표 저장용
        
        # 2. 탐지된 결과 분석
        for r in results:
            boxes = r.boxes
            for box in boxes:
                conf = float(box.conf[0])
                if conf > highest_conf:
                    highest_conf = conf
                    class_id = int(box.cls[0])
                    detected_class_name = model.names[class_id]
                    # 바운딩 박스 좌표 추출 [x1, y1, x2, y2]
                    best_box_coords = box.xyxy[0].cpu().numpy()
        
        # 고유한 파일명 생성을 위해 현재 시간을 활용
        timestamp = int(time.time())
        saved_img_path = os.path.join(save_dir, f"item_{timestamp}.jpg")
        
        # 3. 확신할 수 있는 물체가 발견되었을 때 (이미지 크롭)
        if highest_conf >= 0.40 and best_box_coords is not None:
            print(f"🎯 YOLO 탐지 성공: {detected_class_name} (신뢰도: {highest_conf*100:.1f}%)")
            
            # 박스 좌표를 정수형으로 변환
            x1, y1, x2, y2 = map(int, best_box_coords)
            
            # 혹시 모를 에러(박스가 화면 밖으로 나감) 방지를 위해 좌표를 화면 크기 내로 제한
            h, w, _ = frame.shape
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            # 프레임에서 해당 박스 영역만 잘라내기 (Crop)
            cropped_img = frame[y1:y2, x1:x2]
            
            # 잘라낸 이미지 저장
            cv2.imwrite(saved_img_path, cropped_img)
            print(f"📸 인식된 물체 크롭 이미지 저장 완료: {saved_img_path}")
            
            return detected_class_name, saved_img_path
            
        # 4. 확신할 수 없거나 아무것도 못 찾았을 때 (원본 프레임 저장)
        else:
            print("❓ YOLO 탐지 결과: 확실하게 판별할 수 없어 원본을 저장합니다. (etc)")
            # 자르지 않고 원본 프레임을 그대로 저장
            cv2.imwrite(saved_img_path, frame)
            return "etc", saved_img_path
            
    except Exception as e:
        print(f"❌ YOLO 실행 중 오류 발생: {e}")
        return "etc", None