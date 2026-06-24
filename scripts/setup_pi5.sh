#!/bin/bash
# Raspberry Pi 5 STT 환경 설치 스크립트
# 실행: chmod +x setup_pi5.sh && ./setup_pi5.sh

set -e

echo "================================================"
echo "  STT 환경 설정 - Raspberry Pi 5"
echo "================================================"

# ── 시스템 패키지 설치 ────────────────────────────────
echo "[1/4] 시스템 패키지 설치 중..."
sudo apt-get update -q
sudo apt-get install -y \
    portaudio19-dev \
    python3-pyaudio \
    libatlas-base-dev \
    flac \
    alsa-utils \
    -q

echo "  ✓ 시스템 패키지 설치 완료"

# ── Python 패키지 설치 ────────────────────────────────
echo "[2/4] Python 패키지 설치 중..."
pip3 install --upgrade pip -q
pip3 install \
    pyaudio \
    SpeechRecognition \
    vosk \
    -q

echo "  ✓ Python 패키지 설치 완료"

# ── Vosk 한국어 모델 다운로드 ─────────────────────────
echo "[3/4] Vosk 한국어 모델 다운로드 중..."
MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-small-ko-0.22.zip"
MODEL_ZIP="vosk-model-small-ko-0.22.zip"
MODEL_DIR="model"

if [ ! -d "$MODEL_DIR" ]; then
    wget -q --show-progress "$MODEL_URL" -O "$MODEL_ZIP"
    unzip -q "$MODEL_ZIP"
    mv "vosk-model-small-ko-0.22" "$MODEL_DIR"
    rm "$MODEL_ZIP"
    echo "  ✓ Vosk 모델 설치 완료: ./$MODEL_DIR"
else
    echo "  ✓ Vosk 모델 이미 존재: ./$MODEL_DIR"
fi

# ── 마이크 확인 ───────────────────────────────────────
echo "[4/4] 마이크 확인..."
echo "  연결된 오디오 장치:"
arecord -l 2>/dev/null | grep "card" || echo "  (장치 없음 - USB 마이크를 연결하세요)"

echo ""
echo "================================================"
echo "  설치 완료!"
echo "================================================"
echo ""
echo "실행 방법:"
echo "  python3 stt_main.py --engine vosk"
echo "  python3 stt_main.py --engine vosk --mode continuous"
echo "  python3 stt_main.py --list-mics"
echo ""
echo "마이크 인덱스를 지정하려면:"
echo "  python3 stt_main.py --mic-index 1"
echo ""

# ALSA 설정 안내
echo "USB 마이크 연결 시 /etc/asound.conf 설정이 필요할 수 있습니다:"
cat << 'EOF'
  # /etc/asound.conf 예시 (기본 마이크를 USB로 설정)
  pcm.!default {
    type asym
    capture.pcm "mic"
  }
  pcm.mic {
    type plug
    slave { pcm "hw:1,0" }  # 1 = USB 마이크 카드 번호
  }
EOF