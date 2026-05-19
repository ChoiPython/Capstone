#!/usr/bin/env python3
"""
Windows 환경 설치 확인 및 가이드
실행: python setup_windows.py
"""

import subprocess
import sys
import os


def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def check_python():
    v = sys.version_info
    print(f"[Python] {v.major}.{v.minor}.{v.micro}", end=" ")
    if v.major == 3 and v.minor >= 8:
        print("✓")
        return True
    print("✗ (Python 3.8 이상 필요)")
    return False


def install_packages():
    packages = [
        "pyaudio",
        "SpeechRecognition",
        "vosk",
    ]
    print("\n패키지 설치 중...")
    for pkg in packages:
        print(f"  Installing {pkg}...", end=" ")
        result = run(f"{sys.executable} -m pip install {pkg} -q")
        if result.returncode == 0:
            print("✓")
        else:
            print("✗")
            # PyAudio는 Windows에서 별도 처리
            if pkg == "pyaudio":
                print("\n  [PyAudio 오류 해결]")
                print("  PyAudio Windows 설치가 실패한 경우:")
                print("  1) https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio 에서")
                print("     PyAudio‑0.2.14‑cpXX‑cpXX‑win_amd64.whl 다운로드")
                print("  2) pip install 다운로드경로/PyAudio-...-win_amd64.whl")
                print("  또는: pip install pipwin && pipwin install pyaudio")


def check_vosk_model():
    model_path = "model"
    print(f"\n[Vosk 모델] 경로: ./{model_path}", end=" ")
    if os.path.exists(model_path):
        print("✓ 모델 발견")
    else:
        print("✗ 모델 없음")
        print("\n  한국어 Vosk 모델 다운로드:")
        print("  https://alphacephei.com/vosk/models")
        print("  → vosk-model-small-ko-0.22.zip 다운로드")
        print("  → 압축 해제 후 폴더명을 'model'로 변경하여 스크립트와 같은 위치에 배치")
        print()
        print("  빠른 다운로드 (PowerShell):")
        print("  Invoke-WebRequest -Uri https://alphacephei.com/vosk/models/vosk-model-small-ko-0.22.zip -OutFile model.zip")
        print("  Expand-Archive model.zip .")
        print("  Rename-Item vosk-model-small-ko-0.22 model")


def check_microphone():
    print("\n[마이크 확인]")
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        found = False
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                print(f"  [{i}] {info['name']}")
                found = True
        p.terminate()
        if not found:
            print("  마이크가 감지되지 않았습니다.")
    except Exception as e:
        print(f"  PyAudio 로드 실패: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("  STT 환경 설정 - Windows")
    print("=" * 50)
    check_python()
    install_packages()
    check_vosk_model()
    check_microphone()
    print("\n설치 완료! 실행:")
    print("  python stt_main.py --engine vosk")
    print("  python stt_main.py --engine google")
    print("  python stt_main.py --mode continuous")
