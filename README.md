# final
# 라즈베리파이5 식재료 관리 스마트 냉장고 변신 핫 

# 음성인식
이름 - 카테고리 - 유통기한(n월n일, 1일 뒤, 1일 후, 하루, 이틀, 한달, 일년, 일주일)

git config --global user.email "본인이메일@example.com"
git config --global user.name "본인이름"

# 상태 확인
git status
git add .
git commit -m
# Tesseract OCR, OpenCV, 

# 라즈베리 실행 시
python3 -m venv venv
source venv/bin/activate

# 1. 환경 설치 (PyAudio, SpeechRecognition, Vosk 자동 설치)
pip install pyaudio SpeechRecognition faster-whisper numpy

pip install noisereduce  # 선택: 노이즈 제거

# small 모델 (첫 실행 시 자동 다운로드 ~250MB)
python stt_main.py --engine whisper --model small

# 더 정확하게 (느리지만 Pi5에서도 동작)
python stt_main.py --engine whisper --model medium

# 마이크 감도가 이상하면 먼저 보정
python stt_main.py --calibrate

# Raspberry Pi 5 배포
# 동일한 파일 복사 후
chmod +x setup_pi5.sh
./setup_pi5.sh        # 시스템 패키지 + Python 패키지 + 모델 자동 설치

python3 stt_main.py --engine vosk --mode continuous