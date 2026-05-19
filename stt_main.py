"""
STT (Speech-to-Text) - Whisper 기반 고정확도 버전
Windows 개발 / Raspberry Pi 5 배포 공통

엔진 비교:
  faster-whisper small : 정확도 ★★★★☆  속도 빠름  (Pi5 권장)
  faster-whisper medium: 정확도 ★★★★★  속도 보통  (Pi5 가능)
  Google STT            : 정확도 ★★★★☆  인터넷 필요
  Vosk small            : 정확도 ★★☆☆☆  오프라인   (비추천)

설치:
  pip install faster-whisper pyaudio SpeechRecognition numpy
  pip install noisereduce   # 선택: 노이즈 제거
"""

import sys
import time

import pyaudio
import numpy as np
import speech_recognition as sr

# ── faster-whisper 임포트 ─────────────────────────────────────────────────────
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("[경고] faster-whisper 미설치: pip install faster-whisper numpy")

# ── noisereduce 임포트 (선택) ─────────────────────────────────────────────────
try:
    import noisereduce as nr
    NOISEREDUCE_AVAILABLE = True
except ImportError:
    NOISEREDUCE_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════════════
# 설정
# ══════════════════════════════════════════════════════════════════════════════

CONFIG = {
    # ── 엔진 선택 ──────────────────────────────────────────────────
    "engine": "whisper",        # "whisper" | "google"

    # ── Whisper 설정 ───────────────────────────────────────────────
    # 모델 크기: tiny / base / small / medium / large-v3
    # Pi5 권장: small (정확도와 속도 균형)
    # Windows 권장: medium 이상
    "whisper_model": "small",
    "whisper_language": "ko",   # 한국어 고정 (None이면 자동감지)
    "whisper_device": "cpu",    # "cpu" | "cuda" (GPU 있으면 cuda)
    "whisper_compute_type": "int8",  # CPU에서는 int8이 가장 빠름

    # ── 마이크 / 오디오 설정 ───────────────────────────────────────
    "sample_rate": 16000,       # Whisper 권장 샘플레이트
    "chunk_size": 1024,
    "channels": 1,

    # ── 음성 감지 설정 ─────────────────────────────────────────────
    # energy_threshold: 낮을수록 민감 (소음 많으면 높이기)
    # 조용한 환경: 200~400 / 일반 사무실: 400~700 / 시끄러운 곳: 700+
    "energy_threshold": 400,
    "dynamic_energy": True,     # 자동 감도 조절 (권장)
    "pause_threshold": 0.8,     # 발화 종료 판단 무음 길이 (초)
    "phrase_time_limit": 15,    # 최대 발화 길이 (초)
    "timeout": None,

    # ── 노이즈 제거 ────────────────────────────────────────────────
    "noise_reduction": True,    # noisereduce 설치 시 자동 활성화
}


# ══════════════════════════════════════════════════════════════════════════════
# 노이즈 제거
# ══════════════════════════════════════════════════════════════════════════════

def reduce_noise(audio_np: np.ndarray, sample_rate: int) -> np.ndarray:
    """소프트웨어 노이즈 제거 (noisereduce 필요)"""
    if not NOISEREDUCE_AVAILABLE:
        return audio_np
    # 앞 0.5초를 노이즈 샘플로 사용
    noise_sample = audio_np[:int(sample_rate * 0.5)]
    reduced = nr.reduce_noise(
        y=audio_np,
        sr=sample_rate,
        y_noise=noise_sample,
        prop_decrease=0.75,  # 노이즈 감소 강도 (0~1)
        stationary=False,    # 비정상 노이즈도 처리
    )
    return reduced


# ══════════════════════════════════════════════════════════════════════════════
# Whisper STT 엔진
# ══════════════════════════════════════════════════════════════════════════════

class WhisperSTT:
    """
    faster-whisper 기반 오프라인 STT
    - 한국어 인식률 업계 최고 수준
    - CPU에서도 실용적 속도 (int8 양자화)
    - 초기 모델 로드: 30초~1분 (이후 즉시 응답)
    """

    def __init__(self, model_size: str = "small", device: str = "cpu",
                 compute_type: str = "int8", language: str = "ko"):
        if not WHISPER_AVAILABLE:
            raise ImportError("pip install faster-whisper 를 먼저 실행하세요.")

        print(f"[Whisper] 모델 로드 중: {model_size}  (첫 실행 시 자동 다운로드)")
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )
        self.language = language
        print(f"[Whisper] 준비 완료 ✓   모델={model_size}  device={device}")

    def transcribe(self, audio_data: sr.AudioData) -> str:
        """AudioData → 텍스트 변환"""
        # WAV → numpy float32 배열로 변환
        wav_bytes = audio_data.get_wav_data(convert_rate=16000, convert_width=2)
        audio_np = np.frombuffer(wav_bytes[44:], dtype=np.int16).astype(np.float32) / 32768.0

        # 노이즈 제거 (noisereduce 설치 시)
        if CONFIG["noise_reduction"]:
            audio_np = reduce_noise(audio_np, 16000)

        segments, info = self.model.transcribe(
            audio_np,
            language=self.language,
            beam_size=5,             # 높을수록 정확, 느림 (5 권장)
            vad_filter=True,         # 음성 구간 자동 감지 (노이즈 제거 효과)
            vad_parameters={
                "min_silence_duration_ms": 500,
                "speech_pad_ms": 200,
            },
            temperature=0.0,         # 0 = greedy 디코딩 (가장 안정적)
            no_speech_threshold=0.6, # 이 값 이상이면 무음으로 처리
            condition_on_previous_text=False,
        )

        text = " ".join(seg.text.strip() for seg in segments)
        return text.strip()


# ══════════════════════════════════════════════════════════════════════════════
# Google STT (온라인)
# ══════════════════════════════════════════════════════════════════════════════

class GoogleSTT:
    def __init__(self, language: str = "ko-KR"):
        self.recognizer = sr.Recognizer()
        self.language = language
        print(f"[Google STT] 언어: {language}")

    def transcribe(self, audio: sr.AudioData) -> str:
        return self.recognizer.recognize_google(audio, language=self.language)


# ══════════════════════════════════════════════════════════════════════════════
# 마이크 STT (메인 클래스)
# ══════════════════════════════════════════════════════════════════════════════

class MicrophoneSTT:

    def __init__(self, config: dict = None):
        self.config = config or CONFIG
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = self.config["energy_threshold"]
        self.recognizer.dynamic_energy_threshold = self.config["dynamic_energy"]
        self.recognizer.pause_threshold = self.config["pause_threshold"]

        engine = self.config["engine"]
        if engine == "whisper":
            self.engine = WhisperSTT(
                model_size=self.config["whisper_model"],
                device=self.config["whisper_device"],
                compute_type=self.config["whisper_compute_type"],
                language=self.config["whisper_language"],
            )
        elif engine == "google":
            self.engine = GoogleSTT()
        else:
            raise ValueError(f"지원하지 않는 엔진: {engine}")

        self.engine_type = engine

        if self.config["noise_reduction"] and not NOISEREDUCE_AVAILABLE:
            print("[안내] 노이즈 제거 비활성: pip install noisereduce")

    # ── 단일 발화 인식 ─────────────────────────────────────────────────────────

    def listen_once(self, mic_index: int = None) -> str:
        """한 번 말하고 텍스트 반환"""
        mic = sr.Microphone(
            device_index=mic_index,
            sample_rate=self.config["sample_rate"],
        )
        with mic as source:
            print(">>> 말씀하세요...", end=" ", flush=True)
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(
                    source,
                    timeout=self.config.get("timeout"),
                    phrase_time_limit=self.config["phrase_time_limit"],
                )
            except sr.WaitTimeoutError:
                print("\n[타임아웃] 음성이 감지되지 않았습니다.")
                return ""
        return self._transcribe(audio)

    # ── 연속 인식 ─────────────────────────────────────────────────────────────

    def listen_continuous(self, callback, mic_index: int = None):
        """백그라운드 연속 인식, callback(text) 호출"""
        mic = sr.Microphone(
            device_index=mic_index,
            sample_rate=self.config["sample_rate"],
        )

        def _cb(recognizer, audio):
            text = self._transcribe(audio)
            if text:
                callback(text)

        print("[STT] 연속 인식 시작 (Ctrl+C로 종료)")
        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

        return self.recognizer.listen_in_background(mic, _cb)

    # ── 내부: 텍스트 변환 ─────────────────────────────────────────────────────

    def _transcribe(self, audio: sr.AudioData) -> str:
        try:
            t0 = time.time()
            text = self.engine.transcribe(audio)
            elapsed = time.time() - t0

            if text:
                print(f"[인식] {text}  ({elapsed:.1f}초)")
            else:
                print("[무음 또는 인식 불가]")
            return text

        except sr.UnknownValueError:
            print("[오류] 음성을 인식하지 못했습니다.")
            return ""
        except sr.RequestError as e:
            print(f"[오류] 서버 연결 실패: {e}")
            return ""
        except Exception as e:
            print(f"[오류] {e}")
            return ""

    # ── 마이크 감도 자동 보정 ──────────────────────────────────────────────────

    def calibrate(self, mic_index: int = None, duration: int = 3):
        """
        주변 환경에 맞게 energy_threshold 자동 측정.
        조용한 상태에서 실행하세요.
        """
        mic = sr.Microphone(device_index=mic_index,
                            sample_rate=self.config["sample_rate"])
        print(f"[감도 보정] {duration}초간 조용히 계세요...")
        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=duration)
        threshold = self.recognizer.energy_threshold
        print(f"[감도 보정] 완료. 권장 energy_threshold = {threshold:.0f}")
        return threshold


# ══════════════════════════════════════════════════════════════════════════════
# 유틸리티
# ══════════════════════════════════════════════════════════════════════════════

def list_microphones():
    p = pyaudio.PyAudio()
    print("\n사용 가능한 마이크:")
    print("-" * 48)
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info["maxInputChannels"] > 0:
            sr_str = f"{int(info['defaultSampleRate'])}Hz"
            print(f"  [{i}] {info['name']:<32} {sr_str}")
    p.terminate()
    print("-" * 48)


# ══════════════════════════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="고정확도 STT (Whisper 기반)")
    parser.add_argument("--engine", choices=["whisper", "google"],
                        default=CONFIG["engine"])
    parser.add_argument("--model", default=CONFIG["whisper_model"],
                        choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper 모델 크기 (기본: small)")
    parser.add_argument("--mode", choices=["once", "continuous"], default="once")
    parser.add_argument("--list-mics", action="store_true", help="마이크 목록 출력")
    parser.add_argument("--mic-index", type=int, default=None)
    parser.add_argument("--calibrate", action="store_true",
                        help="마이크 감도 자동 보정")
    args = parser.parse_args()

    if args.list_mics:
        list_microphones()
        sys.exit(0)

    CONFIG["engine"] = args.engine
    CONFIG["whisper_model"] = args.model

    stt = MicrophoneSTT(CONFIG)

    if args.calibrate:
        stt.calibrate(mic_index=args.mic_index)

    if args.mode == "once":
        text = stt.listen_once(mic_index=args.mic_index)
        if text:
            print(f"\n최종 결과: {text}")

    elif args.mode == "continuous":
        results = []

        def on_result(text):
            results.append(text)

        stop = stt.listen_continuous(on_result, mic_index=args.mic_index)
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            stop(wait_for_stop=False)
            print("\n\n=== 전체 결과 ===")
            for i, t in enumerate(results, 1):
                print(f"  {i}. {t}")