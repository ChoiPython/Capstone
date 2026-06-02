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

    # ── 마이크 / 오디오 설정 ───────────────────────────────────────
    "sample_rate": 16000,
    "chunk_size": 1024,
    "channels": 1,

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
    """
    한국어 날짜 표현 → YYYY-MM-DD 변환.

    지원 형식:
      특수   : "오늘" / "내일" / "모레"
      뒤/후  : "7일 뒤(후)" / "2주 뒤(후)" / "일주일 뒤(후)"
               "3달 뒤(후)" / "3개월 뒤(후)" / "한 달 뒤(후)"
               "이틀 뒤(후)" 등 고유어 날수
      절대   : "2024년 7월 1일" / "7월 1일" / "YYYY-MM-DD"
      단순   : "3일" / "일주일" / "한달" / "3달" / "일년" / "1년"
               "이틀" / "사흘" 등 고유어 (뒤/후 없이)
    """
    today = datetime.today()
    t = text.strip()

    # ── 1. 특수 단어 ──────────────────────────────────────────────────
    if "오늘" in t:
        return today.strftime("%Y-%m-%d")
    if "내일" in t:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if "모레" in t:
        return (today + timedelta(days=2)).strftime("%Y-%m-%d")

    # ── 2. 뒤/후 표현 ────────────────────────────────────────────────
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

    # ── 3. 절대 날짜 (단순 표현보다 먼저 — "7월 3일"이 "3일"로 잘못 파싱되는 것 방지) ──
    m = re.search(r'(?:(\d{4})년\s*)?(\d{1,2})월\s*(\d{1,2})일', t)
    if m:
        year  = int(m.group(1)) if m.group(1) else today.year
        month = int(m.group(2))
        day   = int(m.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"

    m = re.search(r'\d{4}-\d{2}-\d{2}', t)
    if m:
        return m.group(0)

    # ── 4. 단순 표현 (뒤/후 없이) ────────────────────────────────────
    # 년 (year) — 일주일보다 먼저 체크 ("일년"의 "일"과 충돌 없음)
    for word, num in _KO_SINO.items():
        if re.search(rf'{word}\s*년', t):
            return _add_months(today, num * 12).strftime("%Y-%m-%d")

    m = re.search(r'(\d+)\s*년', t)
    if m:
        return _add_months(today, int(m.group(1)) * 12).strftime("%Y-%m-%d")

    # 일주일
    if "일주일" in t:
        return (today + timedelta(weeks=1)).strftime("%Y-%m-%d")

    # 달/개월 (month)
    for word, num in _KO_NUM.items():
        if re.search(rf'{word}\s*달', t):
            return _add_months(today, num).strftime("%Y-%m-%d")

    m = re.search(r'(\d+)\s*(?:달|개월)', t)
    if m:
        return _add_months(today, int(m.group(1))).strftime("%Y-%m-%d")

    # 주 (week)
    m = re.search(r'(\d+)\s*주', t)
    if m:
        return (today + timedelta(weeks=int(m.group(1)))).strftime("%Y-%m-%d")

    # 고유어 날수 standalone ("이틀", "사흘" 등)
    for word, days in _KO_DAY.items():
        if word in t:
            return (today + timedelta(days=days)).strftime("%Y-%m-%d")

    # n일 standalone — 반드시 "MM월 DD일" 체크 이후에 위치
    m = re.search(r'(\d+)\s*일', t)
    if m:
        return (today + timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")

    return None


def parse_voice_input(text: str) -> dict | None:
    """
    음성 인식 텍스트에서 식재료 정보 추출.

    기대 발화 형식 (순서 고정):
      "[이름] [카테고리] [유통기한]"
      예) "우유 유제품 7월 1일"
          "닭가슴살 육류 7일 뒤"
          "두부 콩류 2주 후"
          "사과 과일 한 달 뒤"
          "오렌지 주스 음료 내일"

    반환:
      {"name": str, "category": str, "exp_date": str}  성공
      None  파싱 실패
    """
    # ── 날짜 패턴 ─────────────────────────────────────────────────
    _ko_num_re  = '|'.join(_KO_NUM.keys())   # 한|두|세|...
    _ko_day_re  = '|'.join(_KO_DAY.keys())   # 하루|이틀|...
    _ko_sino_re = '|'.join(_KO_SINO.keys())  # 일|이|삼|...

    date_pattern = (
        # ── 절대 날짜 (가장 먼저 — "7월 3일"이 "3일"로 잘못 매칭되는 것 방지)
        r'(?:\d{4}년\s*)?\d{1,2}월\s*\d{1,2}일'              # MM월 DD일
        r'|\d{4}-\d{2}-\d{2}'                                 # YYYY-MM-DD
        # ── 뒤/후 표현
        r'|\d+\s*일\s*[뒤후]'                                  # n일 뒤/후
        r'|일주일\s*[뒤후]'                                     # 일주일 뒤/후
        r'|\d+\s*주\s*[뒤후]'                                  # n주 뒤/후
        r'|(?:' + _ko_num_re + r')\s*달\s*[뒤후]'             # 한/두...달 뒤/후
        r'|\d+\s*(?:달|개월)\s*[뒤후]'                         # n달/개월 뒤/후
        r'|(?:' + _ko_day_re + r')\s*[뒤후]'                  # 이틀/사흘... 뒤/후
        # ── 단순 표현 (뒤/후 없이)
        r'|(?:' + _ko_sino_re + r')\s*년'                     # 일년/이년...
        r'|\d+\s*년'                                            # 1년/2년
        r'|일주일'                                              # 일주일
        r'|(?:' + _ko_num_re + r')\s*달'                      # 한달/두달...
        r'|\d+\s*(?:달|개월)'                                  # n달/개월
        r'|\d+\s*주'                                            # n주
        r'|(?:' + _ko_day_re + r')'                            # 이틀/사흘...
        r'|\d+\s*일'                                            # n일 (단독, 반드시 마지막)
        # ── 특수 단어
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

    # ── 날짜 이전 텍스트에서 이름·카테고리 추출 ─────────────────
    before_date = text[: date_match.start()].strip()
    tokens = before_date.split()

    if len(tokens) < 2:
        print(f"[파서] 이름·카테고리 정보 부족: '{before_date}'  (단어 {len(tokens)}개)")
        return None

    # 첫~끝-1 토큰 = 이름 (여러 단어 허용), 마지막 토큰 = 카테고리
    name     = " ".join(tokens[:-1])
    category = tokens[-1]

    return {"name": name, "category": category, "exp_date": exp_date}


# ══════════════════════════════════════════════════════════════════════════════
# DB 자동 저장 통합 함수
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# 노이즈 제거
# ══════════════════════════════════════════════════════════════════════════════

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

    # ── 커스텀 녹음 (once 모드 전용) ─────────────────────────────────────────
    # SpeechRecognition의 listen()을 우회하여 PyAudio로 직접 녹음.
    # - 최소 min_record_duration 초 동안 반드시 녹음
    # - 그 이후 silence_after_speech 초 침묵이 감지되면 자동 종료
    # - max_record_duration 초를 넘으면 강제 종료

    def _listen_custom(self, mic_index: int = None) -> sr.AudioData:
        min_dur     = self.config["min_record_duration"]   # 기본 10초
        silence_sec = self.config["silence_after_speech"]  # 기본 2초
        max_dur     = self.config["max_record_duration"]   # 기본 60초
        RATE        = self.config["sample_rate"]           # 16000
        CHUNK       = self.config["chunk_size"]            # 1024

        p = pyaudio.PyAudio()
        stream = p.open(
            format             = pyaudio.paInt16,
            channels           = 1,
            rate               = RATE,
            input              = True,
            input_device_index = mic_index,
            frames_per_buffer  = CHUNK,
        )

        # ── 0.5초 주변 소음 측정으로 에너지 임계값 자동 보정 ────────
        print(">>> 주변 소음 측정 중...", end=" ", flush=True)
        calib_chunks = int(RATE / CHUNK * 0.5)
        noise_buf = []
        for _ in range(calib_chunks):
            data = stream.read(CHUNK, exception_on_overflow=False)
            noise_buf.append(np.frombuffer(data, dtype=np.int16).astype(np.float32))
        noise_rms       = np.sqrt(np.mean(np.concatenate(noise_buf) ** 2))
        energy_threshold = max(noise_rms * 1.5, self.config["energy_threshold"])
        print(f"완료 (임계값={energy_threshold:.0f})")

        print(
            f">>> 말씀하세요... "
            f"(최소 {min_dur}초 녹음, 이후 {silence_sec}초 침묵 시 자동 종료)"
        )

        frames           = []
        start_time       = time.time()
        last_speech_time = start_time  # 마지막 발화 감지 시각

        while True:
            elapsed = time.time() - start_time

            # 최대 시간 초과 → 강제 종료
            if elapsed > max_dur:
                print(f"\n[최대 {max_dur}초 초과] 강제 종료")
                break

            try:
                chunk_data = stream.read(CHUNK, exception_on_overflow=False)
            except OSError:
                break

            frames.append(chunk_data)

            # 현재 청크 에너지 계산
            chunk_np = np.frombuffer(chunk_data, dtype=np.int16).astype(np.float32)
            rms = np.sqrt(np.mean(chunk_np ** 2))
            if rms > energy_threshold:
                last_speech_time = time.time()

            # 최소 녹음 시간 경과 후 침묵 체크
            if elapsed >= min_dur:
                silence_elapsed = time.time() - last_speech_time
                if silence_elapsed >= silence_sec:
                    print(
                        f"\n[침묵 {silence_elapsed:.1f}초 감지] 녹음 종료 "
                        f"(총 {elapsed:.1f}초 녹음)"
                    )
                    break

        # 스트림 정리 (get_sample_size는 terminate 전에 호출)
        sample_width = p.get_sample_size(pyaudio.paInt16)
        stream.stop_stream()
        stream.close()
        p.terminate()

        return sr.AudioData(b"".join(frames), RATE, sample_width)

    # ── 단일 발화 인식 ─────────────────────────────────────────────────────────

    def listen_once(self, mic_index: int = None) -> str:
        """최소 10초 + 2초 침묵 감지 후 텍스트 반환"""
        audio = self._listen_custom(mic_index=mic_index)
        return self._transcribe(audio)

    # ── 연속 인식 ─────────────────────────────────────────────────────────────
    # 연속 모드는 SpeechRecognition 백그라운드 리스너 사용.
    # pause_threshold=2.0 이 설정되므로 각 발화 후 2초 침묵 시 인식 트리거.

    def listen_continuous(self, callback, mic_index: int = None):
        """백그라운드 연속 인식, callback(text) 호출"""
        mic = sr.Microphone(device_index=mic_index, sample_rate=self.config["sample_rate"])

        def _cb(recognizer, audio):
            text = self._transcribe(audio)
            if text:
                callback(text)

        print(
            "[STT] 연속 인식 시작 (Ctrl+C로 종료)\n"
            f"      발화 후 {self.config['pause_threshold']}초 침묵 시 인식 → 콜백 호출"
        )
        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

        return self.recognizer.listen_in_background(mic, _cb)

    # ── 내부: 텍스트 변환 ─────────────────────────────────────────────────────

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

    # ── 마이크 감도 자동 보정 ──────────────────────────────────────────────────

    def calibrate(self, mic_index: int = None, duration: int = 3):
        mic = sr.Microphone(device_index=mic_index, sample_rate=self.config["sample_rate"])
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
    parser.add_argument("--model",      default=None,                  # None = 자동 선택
                        choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper 모델 (기본: --save-db 시 medium, 그 외 small)")
    parser.add_argument("--mode",       choices=["once", "continuous"], default="once")
    parser.add_argument("--list-mics",  action="store_true")
    parser.add_argument("--mic-index",  type=int, default=None)
    parser.add_argument("--calibrate",  action="store_true")
    parser.add_argument("--save-db",    action="store_true",
                        help="인식 결과를 DB에 자동 저장 (형식: '이름 카테고리 유통기한')")
    parser.add_argument("--min-sec",    type=int, default=CONFIG["min_record_duration"],
                        help=f"최소 녹음 시간 초 (기본: {CONFIG['min_record_duration']})")
    parser.add_argument("--silence",    type=float, default=CONFIG["silence_after_speech"],
                        help=f"발화 후 침묵 감지 시간 초 (기본: {CONFIG['silence_after_speech']})")
    args = parser.parse_args()

    if args.list_mics:
        list_microphones()
        sys.exit(0)

    # --model 미지정 시: --save-db면 medium, 아니면 small 자동 선택
    if args.model is None:
        args.model = "medium" if args.save_db else "small"
        print(f"[모델] --model 미지정 → '{args.model}' 자동 선택")

    CONFIG["engine"]               = args.engine
    CONFIG["whisper_model"]        = args.model
    CONFIG["auto_save_db"]         = args.save_db
    CONFIG["min_record_duration"]  = args.min_sec
    CONFIG["silence_after_speech"] = args.silence

    if CONFIG["auto_save_db"]:
        db_manager.create_table()
        print("[DB] 냉장고 DB 연결 완료. 자동 저장 활성화.")
        print("[안내] 발화 형식: '이름 카테고리 유통기한'")
        print("       예) 우유 유제품 7월 1일 / 닭가슴살 육류 7일 뒤 / 두부 콩류 2주 후\n")

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
                print(f"  {i}. {t}")