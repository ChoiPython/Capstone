<div align="center">

# 🍉 AI 기반 스마트 식재료 관리 시스템 (Smart Food Manager)
**라즈베리파이 5 기반의 임베디드 컴퓨터 비전 및 엣지 AI 재고 관리 솔루션**

<br>

<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white">
<img src="https://img.shields.io/badge/Raspberry%20Pi%205-A22846?style=for-the-badge&logo=raspberrypi&logoColor=white">
<img src="https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white">
<img src="https://img.shields.io/badge/YOLOv8-00FFFFFF?style=for-the-badge&logo=ultralytics&logoColor=white">
<img src="https://img.shields.io/badge/SQLite3-003B57?style=for-the-badge&logo=sqlite&logoColor=white">

<br>

</div>

---

## 📌 Project Overview
* **타깃 유저:** 1인 가구 및 스마트 홈 환경 사용자
* **핵심 가치:** 카메라 스캔 한 번으로 식재료 종류와 유통기한을 자동 인식하여 식품 낭비를 최소화하는 **'Zero-Effort'** 재고 관리 솔루션

본 프로젝트는 **라즈베리파이 5(Raspberry Pi 5)** 환경에서 고성능 카메라 모듈을 제어하여 냉장고 안의 식품을 스마트하게 관리하는 독립형 임베디드 GUI 프로그램입니다. 딥러닝 기반 이미지 분류(**YOLOv8**)와 문자인식(**Tesseract OCR**)을 결합하여, 사용자가 식품을 카메라에 대기만 하면 유통기한과 6대 식품 카테고리를 자동으로 스캔·분류하여 실시간 데이터베이스에 등록합니다.

---

## ⚙️ Technology Stack

| 분류 | 상세 기술 | 담당 역할 |
| :--- | :--- | :--- |
| **Hardware** | Raspberry Pi 5, Camera Module 3 | Autofocus 기반 고해상도 이미지 데이터 수집 환경 구축 |
| **OS** | Raspberry Pi OS (Linux) | 임베디드 엣지 디바이스 구동 환경 최적화 |
| **GUI Framework** | Python Tkinter, tkcalendar | 데스크톱 기반 관제 대시보드 및 실시간 인터페이스 구현 (16:9) |
| **Object Detection** | Ultralytics YOLOv8 (`best.pt`) | Custom 학습 모델을 통한 6대 푸드 카테고리 분류 및 추론 |
| **Text Recognition** | Tesseract-OCR (PyTesseract) | 포장지에 인쇄된 유통기한 날짜 문자열 추출 및 정제 |
| **Image Processing** | OpenCV | 도트 프린팅 및 빛 반사 극복을 위한 적응형 전처리 파이프라인 |
| **Database** | Firebase / SQLite3 | 식재료 메타데이터 저장, CRUD 처리 및 실시간 동적 새로고침 |
| **Camera Control** | Picamera2, libcamera | 연속 자동초점(Continuous AF) 및 1초 주기 ROI 캡처 제어 |

---

## 🚀 Key Features

1. **실시간 1초 주기 연속 자동 스캔**
   * 매 프레임 OCR 연산을 수행할 때 발생하는 부하를 줄이기 위해, `time.time()` 기반 타이머를 적용하여 1.0초 주기로 가이드 박스 내부 영역(ROI)만 자동 캡처 후 분석합니다.
2. **YOLOv8 기반 식품 분류**
   * 유통기한 텍스트 인식이 성공하는 순간의 프레임을 바탕으로 Custom 학습된 `best.pt` 모델을 구동, 최상위 신뢰도 기반으로 6대 푸드 카테고리 중 하나로 자동 분류합니다.
3. **유연한 날짜 정규식 패턴 매칭 및 데이터 표준화**
   * `YYYY.MM.DD`, `YYYYMMDD` 포맷뿐만 아니라 연도 생략형(`YY.MM.DD`)까지 다중 정규식 패턴 리스트를 통해 포착하며, 6자리 포맷 입력 시 조건문 처리를 통해 앞에 강제로 `20`을 패딩하여 DB 표준 포맷(`YYYY-MM-DD`)으로 자동 변환합니다.
4. **동적 UI 리프레시 및 상태 관리**
   * 식품 등록/수정 모달 팝업 창에서 유통기한을 변경하면 D-Day와 신선도 상태(신선-녹색, 임박-주황색, 만료-적색)가 실시간 계산되어 반영되며, 저장 시 메인 대시보드 화면이 실시간 갱신됩니다.

---

## 📐 System Architecture & Workflow

### 🛠️ 4-Tier Architecture
1. **Device Layer:** 라즈베리 파이 5 + Camera Module 3 (연속 자동초점 및 이미지 캡처)
2. **AI Processing Layer:** OpenCV 전처리 파이프라인 ➡️ YOLOv8 추론 ➡️ Tesseract-OCR 문자 추출
3. **Data Layer:** Firebase / SQLite3 (재고 정보 동기화 및 CRUD 제어)
4. **Application Layer:** Python Tkinter 데스크톱 GUI (사용자 대시보드 및 관제 화면)

### 🔄 System Workflow Data Pipeline

1. 사용자가 스캔 페이지에 진입하면 `PiCamera2`가 연속 자동초점 모드로 구동됩니다.
2. 1초 주기로 가이드 박스 내 이미지를 크롭하여 **OpenCV 적응형 전처리 파이프라인**을 통과시킵니다.
3. `Tesseract OCR`이 정제된 이미지에서 텍스트를 파싱하고 정규식 패턴 매칭 성공 시 유통기한 인식을 완료합니다.
4. 유통기한이 잡힌 바로 그 순간의 프레임을 `YOLOv8` 모듈로 토스하여 식품 카테고리를 판별합니다.
5. 추출된 데이터를 바탕으로 `item_reg.py` 모달 팝업이 활성화되며, 사용자 최종 확인 후 저장 시 DB 반영 및 메인 화면이 콜백 함수(`on_update`)로 실시간 리프레시됩니다.

---

## 🔥 Technical Challenges & Troubleshooting (Core Engineering)

### 1. 도트 매트릭스 인쇄 및 비닐 포장지 빛 반사 해결 (적응형 전처리 파이프라인)
* **Problem:** Tesseract OCR은 일반 인쇄물 서체 위주로 학습되어 있어, 실제 과자 봉지나 유제품에 자주 쓰이는 점선 형태의 도트(Dot) 서체 및 비닐 빛 반사 환경에서 인식률이 전멸하는 문제가 발생했습니다.
* **Solution:** 이미지의 가독성을 물리적으로 끌어올리는 6단계 적응형 전처리 파이프라인을 구축하여 인식률을 획기적으로 개선했습니다.

$$\text{[원본 이미지]} \rightarrow \text{[2배 업스케일링]} \rightarrow \text{[가우시안 블러]} \rightarrow \text{[Otsu 이진화]} \rightarrow \text{[모폴로지 팽창/닫힘]} \rightarrow \text{[Regex 필터링]}$$

* **이미지 확대 (Upscaling):** 작은 날짜 글씨의 해상도 확보를 위해 2배 확대 수행.
* **가우시안 블러 (Gaussian Blur):** 점 형태로 끊어진 픽셀 간의 경계를 의도적으로 흐리게 뭉개어 연결성 유도.
* **Otsu 이진화 (Otsu's Binarization):** 배경 노이즈(포장지 그래픽)를 제거하고 글자 영역의 흑백 대비를 극대화하는 최적 임계값 자동 계산.
* **모폴로지 연산 (Morphology Dilation & Closing):** 팽창 및 닫힘 연산을 적용하여 흩어진 도트 픽셀들을 물리적으로 결합하여 선명한 글자 획 형성.
* **정규표현식 필터링:** `r'\d{4}[.\s]+\d{2}[.\s]+\d{2}'` 패턴 등으로 날짜 데이터를 정제하고 13월 등 논리적 오류를 검증하는 예외 처리 로직 탑재.

### 2. 하드웨어 자원 최적화 및 메모리 누수 방지
* **Problem:** 자원이 제한된 엣지 디바이스(라즈베리파이) 환경에서 실시간 스트리밍 프레임마다 대형 AI 모델 추론과 OCR 연산을 동시 구동할 경우, 극심한 CPU/GPU 부하와 발열로 인해 시스템이 강제 종료되는 현상이 있었습니다.
* **Solution:** `time.time()` 타이머 기반으로 무거운 OCR 연산 주기를 1.0초로 제한하는 스로틀링 시스템을 구현했습니다. 또한, YOLOv8 추론 시 대량의 프레임이 메모리에 쌓이는 현상을 방지하기 위해 `stream=True` 옵션을 적용하여 제너레이터 형태로 리소스를 즉각 반환하는 메모리 최적화를 달성했습니다.

---

## 📂 Repository Directory Structure

팀 내 표준 아키텍처 규칙에 따라 아래와 같이 기술별, 레이어별로 모듈화하여 구조를 유지하고 있습니다.

```plaintext
smart_fridge_project/
│
├── assets/                 # UI 아이콘, 대시보드 구조도 및 시각 자료
├── tests/                  # 기능 QA 및 데이터 정합성 검증 스크립트
│   └── insert_dummy.py     # 데이터베이스 테스트용 더미 데이터 삽입 스크립트
├── requirements.txt        # 의존성 패키지 리스트 (opencv-python, ultralytics 등)
├── main.py                 # 프로그램 전체 실행 진입점 (Main Entry)
│
└── src/
    ├── ai/                 # 인공지능 모듈 영역
    │   ├── yolov8.py       # YOLOv8 모델 로드 및 최상위 신뢰도 기반 객체 추론 로직
    │   └── best.pt         # Custom 학습된 6대 식품 분류 가중치 파일
    │
    ├── ocr/                # 컴퓨터 비전 영역
    │   └── smart_fridge_ocr2.py # PiCamera2 제어, OpenCV 파이프라인 및 Tesseract 연동
    │
    ├── database/           # 데이터 영역
    │   └── db_manager.py   # SQLite3 / Firebase 연동 및 데이터 CRUD 함수
    │
    └── gui/                # 애플리케이션 프레젠테이션 영역 (Tkinter UI)
        ├── home.py         # 메인 대시보드 (총 재고 요약 및 신선도 카운트 뷰)
        ├── inventory.py    # 전체 재고 리스트 인터페이스 (필터 및 정렬 기능)
        └── item_reg.py     # 식품 상세 등록 및 수정 모달 팝업 창 (달력 위젯 연동)
