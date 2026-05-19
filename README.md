# final
# 라즈베리파이5 식재료 관리 스마트 냉장고 변신 핫 

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

# tkinter 라즈베리파이 설치
sudo apt-get install python3-tk


# 1. 환경 설치 (PyAudio, SpeechRecognition, Vosk 자동 설치)
python setup_windows.py

# 2. Vosk 한국어 모델 다운로드 후 압축 해제 → 폴더명 'model'로 변경
# https://alphacephei.com/vosk/models → vosk-model-small-ko-0.22.zip
# 3. 실행
python stt_main.py                          # Vosk 오프라인, 단일 발화
python stt_main.py --engine google          # Google 온라인
python stt_main.py --mode continuous        # 연속 인식
python stt_main.py --list-mics             # 마이크 목록

# Raspberry Pi 5 배포
# 동일한 파일 복사 후
chmod +x setup_pi5.sh
./setup_pi5.sh        # 시스템 패키지 + Python 패키지 + 모델 자동 설치

python3 stt_main.py --engine vosk --mode continuous
