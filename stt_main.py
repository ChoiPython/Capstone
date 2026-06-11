"""
STT (Speech-to-Text) - Whisper 기반 고정확도 버전
Windows 개발 / Raspberry Pi 5 배포 공통

설치:
  pip install faster-whisper pyaudio SpeechRecognition numpy
  pip install noisereduce   # 선택: 노이즈 제거
"""

import re
import sys
import time
import calendar
from datetime import datetime, timedelta

import pyaudio
import numpy as np
import speech_recognition as sr

import db_manager  # DB 저장 모듈

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
    "whisper_model": "small",
    "whisper_language": "ko",
    "whisper_device": "cpu",
    "whisper_compute_type": "int8",

    # ── 마이크 / 오디오 설정 (reSpeaker 하드웨어 네이티브인 48000Hz로 변경!) ──
    "sample_rate": 48000,       # 16000에서 48000으로 수정 완료 ✓
    "chunk_size": 1024,
    "channels": 1,              # 1 = 모노, 2 = 스테레오

    # ── 음성 감지 설정 (연속 모드용) ───────────────────────────────
    "energy_threshold": 400,
    "dynamic_energy": True,
    "pause_threshold": 2.5,     # 연속 모드: 2.5초 침묵 시 발화 종료
    "timeout": None,

    # ── 녹음 시간 설정 (once 모드용) ──────────────────────────────
    "min_record_duration": 6,   # 최소 녹음 시간 (초)
    "silence_after_speech": 2.5,# 발화 후 침묵 감지 시간 (초) → 이후 종료
    "max_record_duration": 60,  # 최대 녹음 시간 (초, 안전장치)

    # ── 노이즈 제거 ────────────────────────────────────────────────
    "noise_reduction": True,

    # ── DB 자동 저장 ───────────────────────────────────────────────
    "auto_save_db": False,
}


# ══════════════════════════════════════════════════════════════════════════════
# 날짜 유틸리티
# ══════════════════════════════════════════════════════════════════════════════

def _add_months(base: datetime, months: int) -> datetime:
    """월 덧셈 (말일 초과 시 해당 월 말일로 클램프)"""
    month = base.month - 1 + months
    year  = base.year + month // 12
    month = month % 12 + 1
    day   = min(base.day, calendar.monthrange(year, month)[1])
    return base.replace(year=year, month=month, day=day)


# 한국어 수사 → 숫자 매핑
_KO_NUM = {
    "한": 1, "두": 2, "세": 3, "네": 4, "다섯": 5,
    "여섯": 6, "일곱": 7, "여덟": 8, "아홉": 9, "열": 10,
}
# 고유어 날수 표현
_KO_DAY = {
    "하루": 1, "이틀": 2, "사흘": 3, "나흘": 4, "닷새": 5,
    "엿새": 6, "이레": 7, "여드레": 8, "아흐레": 9, "열흘": 10,
}
# 한자어 수사 (년 표현용: 일년, 이년, ...)
_KO_SINO = {
    "일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6,
}


# ══════════════════════════════════════════════════════════════════════════════
# 음성 입력 파서 (이름 → 카테고리 → 유통기한)
# ══════════════════════════════════════════════════════════════════════════════

def parse_date_korean(text: str) -> str | None:
    """한국어 날짜 표현 → YYYY-MM-DD 변환."""
    today = datetime.today()
    t = text.strip()

    # ── 1. 특수 단어
    if "오늘" in t:
        return today.strftime("%Y-%m-%d")
    if "내일" in t:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if "모레" in t:
        return (today + timedelta(days=2)).strftime("%Y-%m-%d")

    # ── 2. 뒤/후 표현
    for word, days in _KO_DAY.items():
        if word in t and re.search(r'[뒤후]', t):
            return (today + timedelta(days=days)).strftime("%Y-%m-%d")

    m = re.search(r'(\d+)\s*일\s*[뒤후]', t)
    if m:
        return (today + timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")

    if "일주일" in t and re.search(r'[뒤후]', t):
        return (today + timedelta(weeks=1)).strftime("%Y-%m-%d")

    m = re.search(r'(\d+)\s*주\s*[뒤후]', t)
    if m:
        return (today + timedelta(weeks=int(m.group(1)))).strftime("%Y-%m-%d")

    for word, num in _KO_NUM.items():
        if re.search(rf'{word}\s*달\s*[뒤후]', t):
            return _add_months(today, num).strftime("%Y-%m-%d")

    m = re.search(r'(\d+)\s*(?:달|개월)\s*[뒤후]', t)
    if m:
        return _add_months(today, int(m.group(1))).strftime("%Y-%m-%d")

    # ── 3. 절대 날짜
    m = re.search(r'(?:(\d{4})년\s*)?(\d{1,2})월\s*(\d{1,2})일', t)
    if m:
        year  = int(m.group(1)) if m.group(1) else today.year
        month = int(m.group(2))
        day   = int(m.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"

    m = re.search(r'\d{4}-\d{2}-\d{2}', t)
    if m:
        return m.group(0)

    # ── 4. 단순 표현
    for word, num in _KO_SINO.items():
        if re.search(rf'{word}\s*년', t):
            return _add_months(today, num * 12).strftime("%Y-%m-%d")

    m = re.search(r'(\d+)\s*년', t)
    if m:
        return _add_months(today, int(m.group(1)) * 12).strftime("%Y-%m-%d")

    if "일주일" in t:
        return (today + timedelta(weeks=1)).strftime("%Y-%m-%d")

    for word, num in _KO_NUM.items():
        if re.search(rf'{word}\s*달', t):
            return _add_months(today, num).strftime("%Y-%m-%d")

    m = re.search(r'(\d+)\s*(?:달|개월)', t)
    if m:
        return _add_months(today, int(m.group(1))).strftime("%Y-%m-%d")

    m = re.search(r'(\d+)\s*주', t)
    if m:
        return (today + timedelta(weeks=int(m.group(1)))).strftime("%Y-%m-%d")

    for word, days in _KO_DAY.items():
        if word in t:
            return (today + timedelta(days=days)).strftime("%Y-%m-%d")

    m = re.search(r'(\d+)\s*일', t)
    if m:
        return (today + timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")

    return None


def parse_voice_input(text: str) -> dict | None:
    """음성 인식 텍스트에서 식재료 정보 추출."""
    _ko_num_re  = '|'.join(_KO_NUM.keys())
    _ko_day_re  = '|'.join(_KO_DAY.keys())
    _ko_sino_re = '|'.join(_KO_SINO.keys())

    date_pattern = (
        r'(?:\d{4}년\s*)?\d{1,2}월\s*\d{1,2}일'
        r'|\d{4}-\d{2}-\d{2}'
        r'|\d+\s*일\s*[뒤후]'
        r'|일주일\s*[뒤후]'
        r'|\d+\s*주\s*[뒤후]'
        r'|(?:' + _ko_num_re + r')\s*달\s*[뒤후]'
        r'|\d+\s*(?:달|개월)\s*[뒤후]'
        r'|(?:' + _ko_day_re + r')\s*[뒤후]'
        r'|(?:' + _ko_sino_re + r')\s*년'
        r'|\d+\s*년'
        r'|일주일'
        r'|(?:' + _ko_num_re + r')\s*달'
        r'|\d+\s*(?:달|개월)'
        r'|\d+\s*주'
        r'|(?:' + _ko_day_re + r')'
        r'|\d+\s*일'
        r'|오늘|내일|모레'
    )

    date_match = re.search(date_pattern, text)
    if not date_match:
        print(f"[파서] 날짜를 찾을 수 없습니다: '{text}'")
        return None

    exp_date = parse_date_korean(date_match.group(0))
    if not exp_date:
        print(f"[파서] 날짜 변환 실패: '{date_match.group(0)}'")
        return None

    before_date = text[: date_match.start()].strip()
    tokens = before_date.split()

    if len(tokens) < 2:
        print(f"[파서] 이름·카테고리 정보 부족: '{before_date}'  (단어 {len(tokens)}개)")
        return None

    name     = " ".join(tokens[:-1])
    category = tokens[-1]

    return {"name": name, "category": category, "exp_date": exp_date}


def save_voice_to_db(text: str) -> bool:
    """인식된 텍스트를 파싱하여 DB에 저장."""
    parsed = parse_voice_input(text)
    if parsed is None:
        print("[DB 저장 건너뜀] 파싱 실패 — 형식: '이름 카테고리 유통기한'")
        return False
    print(f"[파서 결과] 이름={parsed['name']} | 카테고리={parsed['category']} | 유통기한={parsed['exp_date']}")
    return db_manager.insert_item(
        name          = parsed["name"],
        category_name = parsed["category"],
        exp_date      = parsed["exp_date"],
    )


def reduce_noise(audio_np: np.ndarray, sample_rate: int) -> np.ndarray:
    if not NOISEREDUCE_AVAILABLE:
        return audio_np
    noise_sample = audio_np[:int(sample_rate * 0.5)]
    reduced = nr.reduce_noise(
        y=audio_np, sr=sample_rate, y_noise=noise_sample,
        prop_decrease=0.75, stationary=False,
    )
    return reduced


# ══════════════════════════════════════════════════════════════════════════════
# reSpeaker 최적화용 커스텀 마이크 클래스
# ══════════════════════════════════════════════════════════════════════════════

class CustomMicrophone(sr.Microphone):
    class CustomMicrophoneStream(object):
        def __init__(self, pyaudio_stream, channels=1):
            self.pyaudio_stream = pyaudio_stream
            self.channels = channels

        def read(self, size):
            raw_data = self.pyaudio_stream.read(size, exception_on_overflow=False)
            if self.channels == 2:
                audio_np = np.frombuffer(raw_data, dtype=np.int16)
                mono_np = audio_np[0::2]  # 스테레오를 모노로 슬라이싱 변환
                return mono_np.tobytes()
            return raw_data

    def __init__(self, device_index=None, sample_rate=16000, chunk_size=1024, channels=1):
        super().__init__(device_index=device_index, sample_rate=sample_rate, chunk_size=chunk_size)
        self.channels = channels

    def __enter__(self):
        assert self.stream is None, "이미 마이크 스트림이 실행 중입니다."
        pyaudio_module = self.get_pyaudio()
        self.pyaudio_stream = pyaudio_module.open(
            input_device_index=self.device_index,
            channels=self.channels,
            format=self.format,
            rate=self.sample_rate,
            frames_per_buffer=self.chunk_size,
            input=True,
        )
        self.stream = self.CustomMicrophoneStream(self.pyaudio_stream, self.channels)
        return self


# ══════════════════════════════════════════════════════════════════════════════
# Whisper STT 엔진
# ══════════════════════════════════════════════════════════════════════════════

class WhisperSTT:
    def __init__(self, model_size="small", device="cpu",
                 compute_type="int8", language="ko"):
        if not WHISPER_AVAILABLE:
            raise ImportError("pip install faster-whisper 를 먼저 실행하세요.")
        print(f"[Whisper] 모델 로드 중: {model_size}  (첫 실행 시 자동 다운로드)")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.language = language
        print(f"[Whisper] 준비 완료 ✓   모델={model_size}  device={device}")

    def transcribe(self, audio_data: sr.AudioData) -> str:
        # get_wav_data를 호출할 때 16000Hz로 정밀 다운샘플링하여 Whisper에 전달합니다.
        wav_bytes = audio_data.get_wav_data(convert_rate=16000, convert_width=2)
        audio_np = np.frombuffer(wav_bytes[44:], dtype=np.int16).astype(np.float32) / 32768.0
        if CONFIG["noise_reduction"]:
            audio_np = reduce_noise(audio_np, 16000)
        segments, _ = self.model.transcribe(
            audio_np, language=self.language, beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 200},
            temperature=0.0, no_speech_threshold=0.6,
            condition_on_previous_text=False,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()


# ══════════════════════════════════════════════════════════════════════════════
# Google STT (온라인)
# ══════════════════════════════════════════════════════════════════════════════

class GoogleSTT:
    def __init__(self, language="ko-KR"):
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
        self.recognizer.energy_threshold         = self.config["energy_threshold"]
        self.recognizer.dynamic_energy_threshold = self.config["dynamic_energy"]
        self.recognizer.pause_threshold          = self.config["pause_threshold"]

        engine = self.config["engine"]
        if engine == "whisper":
            self.engine = WhisperSTT(
                model_size   = self.config["whisper_model"],
                device       = self.config["whisper_device"],
                compute_type = self.config["whisper_compute_type"],
                language     = self.config["whisper_language"],
            )
        elif engine == "google":
            self.engine = GoogleSTT()
        else:
            raise ValueError(f"지원하지 않는 엔진: {engine}")

        self.engine_type = engine

        if self.config["noise_reduction"] and not NOISEREDUCE_AVAILABLE:
            print("[안내] 노이즈 제거 비활성: pip install noisereduce")

    def _listen_custom(self, mic_index: int = None) -> sr.AudioData:
        min_dur     = self.config["min_record_duration"]
        silence_sec = self.config["silence_after_speech"]
        max_dur     = self.config["max_record_duration"]
        RATE        = self.config["sample_rate"]
        CHUNK       = self.config["chunk_size"]

        p = pyaudio.PyAudio()
        stream = p.open(
            format             = pyaudio.paInt16,
            channels           = self.config["channels"],
            rate               = RATE,
            input              = True,
            input_device_index = mic_index,
            frames_per_buffer  = CHUNK,
        )

        # ── 0.5초 주변 소음 측정으로 에너지 임계값 자동 보정
        print(">>> 주변 소음 측정 중...", end=" ", flush=True)
        calib_chunks = int(RATE / CHUNK * 0.5)
        noise_buf = []
        for _ in range(calib_chunks):
            data = stream.read(CHUNK, exception_on_overflow=False)
            chunk_np = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            if self.config["channels"] == 2:
                chunk_np = chunk_np[0::2]
            noise_buf.append(chunk_np)
        noise_rms       = np.sqrt(np.mean(np.concatenate(noise_buf) ** 2))
        energy_threshold = max(noise_rms * 1.5, self.config["energy_threshold"])
        print(f"완료 (임계값={energy_threshold:.0f})")

        print(
            f">>> 말씀하세요... "
            f"(최소 {min_dur}초 녹음, 이후 {silence_sec}초 침묵 시 자동 종료)"
        )

        frames           = []
        start_time       = time.time()
        last_speech_time = start_time

        while True:
            elapsed = time.time() - start_time

            if elapsed > max_dur:
                print(f"\n[최대 {max_dur}초 초과] 강제 종료")
                break

            try:
                chunk_data = stream.read(CHUNK, exception_on_overflow=False)
            except OSError:
                break

            chunk_np = np.frombuffer(chunk_data, dtype=np.int16)
            
            # ── 2채널(스테레오)일 경우 즉각 1채널(모노)로 축소
            if self.config["channels"] == 2:
                chunk_np = chunk_np[0::2]
                chunk_data = chunk_np.tobytes()

            frames.append(chunk_data)

            chunk_float = chunk_np.astype(np.float32)
            rms = np.sqrt(np.mean(chunk_float ** 2))
            if rms > energy_threshold:
                last_speech_time = time.time()

            if elapsed >= min_dur:
                silence_elapsed = time.time() - last_speech_time
                if silence_elapsed >= silence_sec:
                    print(
                        f"\n[침묵 {silence_elapsed:.1f}초 감지] 녹음 종료 "
                        f"(총 {elapsed:.1f}초 녹음)"
                    )
                    break

        sample_width = p.get_sample_size(pyaudio.paInt16)
        stream.stop_stream()
        stream.close()
        p.terminate()

        return sr.AudioData(b"".join(frames), RATE, sample_width)

    def listen_once(self, mic_index: int = None) -> str:
        audio = self._listen_custom(mic_index=mic_index)
        return self._transcribe(audio)

    def listen_continuous(self, callback, mic_index: int = None):
        mic = CustomMicrophone(
            device_index=mic_index, 
            sample_rate=self.config["sample_rate"],
            channels=self.config["channels"]
        )

        def _cb(recognizer, audio):
            text = self._transcribe(audio)
            if text:
                callback(text)

        print(
            "[STT] 연속 인식 시작 (Ctrl+C로 종료)\n"
            f"       발화 후 {self.config['pause_threshold']}초 침묵 시 인식 → 콜백 호출"
        )
        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

        return self.recognizer.listen_in_background(mic, _cb)

    def _transcribe(self, audio: sr.AudioData) -> str:
        try:
            t0      = time.time()
            text    = self.engine.transcribe(audio)
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

    def calibrate(self, mic_index: int = None, duration: int = 3):
        mic = CustomMicrophone(
            device_index=mic_index, 
            sample_rate=self.config["sample_rate"],
            channels=self.config["channels"]
        )
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
    parser.add_argument("--engine",     choices=["whisper", "google"], default=CONFIG["engine"])
    parser.add_argument("--model",      default=None,
                        choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper 모델 (기본: --save-db 시 medium, 그 외 small)")
    parser.add_argument("--mode",       choices=["once", "continuous"], default="once")
    parser.add_argument("--list-mics",  action="store_true")
    parser.add_argument("--mic-index",  type=int, default=None)
    parser.add_argument("--calibrate",  action="store_true")
    parser.add_argument("--save-db",    action="store_true",
                        help="인식 결과를 DB에 자동 저장")
    parser.add_argument("--min-sec",    type=int, default=CONFIG["min_record_duration"],
                        help=f"최소 녹음 시간 초")
    parser.add_argument("--silence",    type=float, default=CONFIG["silence_after_speech"],
                        help=f"발화 후 침묵 감지 시간 초")
    args = parser.parse_args()

    if args.list_mics:
        list_microphones()
        sys.exit(0)

    if args.model is None:
        args.model = "medium" if args.save_db else "small"
        print(f"[모델] --model 미지정 → '{args.model}' 자동 선택")

    # ── [핵심 개선] reSpeaker 마이크 자동 감지 및 2채널 설정 ──────────────────────────
    if args.mic_index is None:
        print("[마이크] 자동 감지 스캔 중...")
        p = pyaudio.PyAudio()
        detected = False
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                dev_name = info.get("name", "")
                max_in = info.get("maxInputChannels", 0)
                
                # 반드시 이름이 seeed 계열이면서 '실제 입력 채널(maxInputChannels)'이 독점 안되고 살아있어야 선택!
                if any(x in dev_name.lower() for x in ["seeed", "respeaker", "voicecard"]) and max_in > 0:
                    args.mic_index = i
                    CONFIG["channels"] = max_in
                    print(f"  -> ✓ reSpeaker 마이크 직접 감지 완료! (Index: {args.mic_index}, Name: {dev_name})")
                    print(f"  -> {max_in}채널 녹음 및 실시간 모노 정밀변환 모드를 실행합니다.")
                    detected = True
                    break
            except Exception:
                continue
        
        # 하드웨어 직접 접근이 독점되어 있을 경우 -> 기본 가상 채널(default/pulse) 우회 접근
        if not detected:
            print("  -> reSpeaker 하드웨어 장치가 독점되어 직접 접근이 어렵습니다.")
            print("  -> 시스템 기본(default / pulse) 가상 장치를 찾아 우회 연결합니다...")
            for i in range(p.get_device_count()):
                try:
                    info = p.get_device_info_by_index(i)
                    dev_name = info.get("name", "")
                    max_in = info.get("maxInputChannels", 0)
                    
                    if any(x in dev_name.lower() for x in ["default", "pulse"]) and max_in > 0:
                        args.mic_index = i
                        CONFIG["channels"] = max_in
                        print(f"  -> ✓ 기본 가상 마이크 우회 감지 완료! (Index:, Name: {dev_name})")
                        print(f"  -> {max_in}채널 모드로 안전 녹음을 시작합니다.")
                        detected = True
                        break
                except Exception:
                    continue
                    
        p.terminate()
        
        if args.mic_index is None:
            print("  -> ✗ 사용할 수 있는 마이크 장치를 발견하지 못했습니다. 기본 설정을 시도합니다.")
    else:
        # 사용자가 마이크 인덱스를 강제 지정했을 때도 실제 가용 채널 수를 자동으로 확인
        print(f"[마이크] 지정한 마이크 인덱스를 사용합니다: {args.mic_index}")
        p = pyaudio.PyAudio()
        try:
            info = p.get_device_info_by_index(args.mic_index)
            dev_name = info.get("name", "")
            max_in = info.get("maxInputChannels", 0)
            if max_in > 0:
                CONFIG["channels"] = max_in
                print(f"  -> 장치 이름: {dev_name}")
                print(f"  -> 이 장치의 가용 채널 수({max_in}채널)를 자동으로 적용해 구동합니다.")
            else:
                print(f"  -> [경고] 지정하신 {args.mic_index}번 장치는 현재 사용 가능한 채널 수가 0개입니다.")
        except Exception:
            pass
        p.terminate()

    CONFIG["engine"]               = args.engine
    CONFIG["whisper_model"]        = args.model
    CONFIG["auto_save_db"]         = args.save_db
    CONFIG["min_record_duration"]  = args.min_sec
    CONFIG["silence_after_speech"] = args.silence

    if CONFIG["auto_save_db"]:
        db_manager.create_table()
        print("[DB] 냉장고 DB 연결 완료. 자동 저장 활성화.")
        print("[안내] 발화 형식: '이름 카테고리 유통기한'")
        print("       예) 우유 유제품 7월 1일 / 닭가슴살 육류 7일 뒤\n")

    stt = MicrophoneSTT(CONFIG)

    if args.calibrate:
        stt.calibrate(mic_index=args.mic_index)

    # ── once 모드 ──────────────────────────────────────────────────
    if args.mode == "once":
        text = stt.listen_once(mic_index=args.mic_index)
        if text:
            print(f"\n최종 결과: {text}")
            if CONFIG["auto_save_db"]:
                save_voice_to_db(text)

    # ── continuous 모드 ────────────────────────────────────────────
    elif args.mode == "continuous":
        results = []

        def on_result(text):
            results.append(text)
            if CONFIG["auto_save_db"]:
                save_voice_to_db(text)

        stop = stt.listen_continuous(on_result, mic_index=args.mic_index)
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            stop(wait_for_stop=False)
            print("\n\n=== 전체 결과 ===")
            for i, t in enumerate(results, 1):
                print(f" {t}")