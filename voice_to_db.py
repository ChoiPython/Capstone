"""
음성 인식 → 냉장고 DB 저장 (라즈베리파이 5 + ReSpeaker 2-Mics Pi HAT 전용)

구조:
  [1] AudioRecorder : arecord로 녹음 (PyAudio 미사용 — 파이에서 검증된 방식)
  [2] SpeechToText  : faster-whisper로 한국어 인식
  [3] DateParser    : "3일", "일주일", "한달" 등 → YYYY-MM-DD 변환
  [4] VoiceParser   : "이름 카테고리 유통기한" 형식 분해
  [5] main          : 전체 흐름 연결 + DB 저장

설치:
  pip install faster-whisper numpy

실행:
  python voice_to_db.py                  # 1회 인식 후 DB 저장
  python voice_to_db.py --loop           # 반복 인식 (Ctrl+C로 종료)
  python voice_to_db.py --no-db          # 인식만 하고 저장 안 함
  python voice_to_db.py --model medium   # 모델 변경 (기본: small)

발화 예시:
  "우유 유제품 3일"      → 오늘 + 3일
  "닭가슴살 육류 일주일"  → 오늘 + 7일
  "된장 장류 한달"       → 오늘 + 1개월
  "계란 달걀류 7월 20일"  → 2026-07-20
"""

import re
import sys
import time
import queue
import calendar
import argparse
import threading
import subprocess
from datetime import datetime, timedelta

import numpy as np

import db_manager


# ══════════════════════════════════════════════════════════════════════════
# [1] AudioRecorder — arecord 기반 녹음
# ══════════════════════════════════════════════════════════════════════════

class AudioRecorder:
    """arecord 서브프로세스로 16kHz 모노 오디오를 녹음한다.

    - plughw:<seeed카드>,0 을 우선 시도하고, 점유 중이면 default → pulse 순으로
      자동 전환한다 (사운드 서버가 장치를 잡고 있으면 서버 경유가 정상 동작).
    - 최소 녹음 시간이 지난 뒤, 일정 시간 침묵이 이어지면 자동 종료한다.
    - 어떤 경우에도 (Ctrl+C 포함) arecord 프로세스를 반드시 정리한다.
    """

    RATE = 16000          # Whisper 입력 형식과 동일 → 변환 불필요
    CHUNK_FRAMES = 1024   # 한 번에 읽을 프레임 수 (약 64ms)

    def __init__(self, device: str | None = None,
                 min_sec: float = 4.0,
                 silence_sec: float = 2.0,
                 max_sec: float = 30.0):
        self.device      = device
        self.min_sec     = min_sec
        self.silence_sec = silence_sec
        self.max_sec     = max_sec

    # ── 장치 탐색 ────────────────────────────────────────────────────────

    @staticmethod
    def find_seeed_device() -> str | None:
        """arecord -l 출력에서 seeed(ReSpeaker) 카드 번호를 찾는다."""
        try:
            out = subprocess.run(
                ["arecord", "-l"],
                capture_output=True, text=True, timeout=5,
            ).stdout
        except Exception:
            return None
        # 로케일에 따라 "card 0:" 또는 "카드 0:"
        for m in re.finditer(r"(?:card|카드)\s+(\d+)\s*:\s*(\S+)", out):
            if "seeed" in m.group(2).lower() or "voicec" in m.group(2).lower():
                return f"plughw:{m.group(1)},0"
        return None

    def _device_candidates(self) -> list[str]:
        cands = []
        if self.device:
            cands.append(self.device)
        else:
            seeed = self.find_seeed_device()
            if seeed:
                cands.append(seeed)
        for d in ("default", "pulse"):
            if d not in cands:
                cands.append(d)
        return cands

    # ── 점유 프로세스 진단/정리 ──────────────────────────────────────────

    @staticmethod
    def _kill_stale_arecord():
        """이전 실행이 비정상 종료되며 남긴 arecord 좀비 프로세스를 정리.
        좀비가 장치를 계속 점유하면 '장치나 자원이 동작 중' 오류가 난다."""
        try:
            out = subprocess.run(["pgrep", "-x", "arecord"],
                                 capture_output=True, text=True)
        except FileNotFoundError:
            return
        pids = [p for p in out.stdout.split() if p.isdigit()]
        for pid in pids:
            print(f"[녹음] 이전 실행이 남긴 arecord(PID {pid})를 종료합니다.")
            subprocess.run(["kill", pid], capture_output=True)
        if pids:
            time.sleep(0.5)  # 장치 해제 대기

    @staticmethod
    def _find_device_holders() -> list[str]:
        """/proc/asound에서 캡처 장치를 점유 중인 프로세스를 찾는다."""
        import glob
        holders = []
        for status_path in glob.glob("/proc/asound/card*/pcm*c/sub*/status"):
            try:
                txt = open(status_path).read()
            except OSError:
                continue
            if txt.strip().startswith("closed"):
                continue
            m = re.search(r"owner_pid\s*:\s*(\d+)", txt)
            if m:
                pid = m.group(1)
                try:
                    name = open(f"/proc/{pid}/comm").read().strip()
                except OSError:
                    name = "알 수 없음"
                card = status_path.split("/")[3]
                holders.append(f"{card} ← PID {pid} ({name})")
        return holders

    # ── 녹음 ────────────────────────────────────────────────────────────

    def record(self) -> np.ndarray:
        """발화 하나를 녹음해 float32 (-1.0 ~ 1.0) 배열로 반환."""
        self._kill_stale_arecord()

        last_err = None
        for dev in self._device_candidates():
            try:
                return self._record_from(dev)
            except RuntimeError as e:
                print(f"[녹음] '{dev}' 실패: {e}")
                last_err = e

        holders = self._find_device_holders()
        holder_msg = (
            "  현재 캡처 장치 점유 중: " + ", ".join(holders) + "\n"
            "  → 위 프로세스를 종료한 뒤 다시 실행하세요: kill <PID>\n"
            if holders else
            "  현재 캡처 장치를 점유한 프로세스는 없습니다.\n"
            "  → 케이블/HAT 연결과 드라이버 상태를 확인하세요: arecord -l\n"
        )
        raise RuntimeError(
            f"모든 오디오 장치에서 녹음에 실패했습니다.\n"
            f"{holder_msg}"
            f"  마지막 오류: {last_err}"
        )

    def _record_from(self, device: str) -> np.ndarray:
        cmd = [
            "arecord", "-q",
            "-D", device,
            "-f", "S16_LE",
            "-r", str(self.RATE),
            "-c", "1",
            "-t", "raw",
            "-",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        chunk_q: queue.Queue[bytes] = queue.Queue()

        def _reader():
            while True:
                data = proc.stdout.read(self.CHUNK_FRAMES * 2)  # int16=2byte
                if not data:
                    break
                chunk_q.put(data)

        threading.Thread(target=_reader, daemon=True).start()

        def _core_error() -> str:
            try:
                raw = (proc.stderr.read() or b"").decode(errors="ignore")
            except Exception:
                return ""
            core = [l for l in raw.splitlines() if "arecord:" in l]
            return " / ".join(core) or raw.strip().splitlines()[0] if raw.strip() else ""

        def read_chunk(timeout: float = 3.0) -> np.ndarray:
            """청크 하나를 int16 배열로. arecord가 죽으면 즉시 감지."""
            deadline = time.time() + timeout
            while True:
                try:
                    return np.frombuffer(chunk_q.get(timeout=0.2),
                                         dtype=np.int16)
                except queue.Empty:
                    if proc.poll() is not None and chunk_q.empty():
                        raise RuntimeError(
                            f"arecord 종료(코드 {proc.returncode}): {_core_error()}")
                    if time.time() > deadline:
                        raise RuntimeError(
                            f"{timeout}초간 오디오 입력 없음")

        frames: list[np.ndarray] = []
        try:
            print(f"[녹음] 장치: {device}")

            # 0.5초간 주변 소음을 측정해 침묵 판정 임계값을 자동 보정
            print(">>> 주변 소음 측정 중...", end=" ", flush=True)
            calib = []
            for _ in range(max(1, int(self.RATE / self.CHUNK_FRAMES * 0.5))):
                calib.append(read_chunk().astype(np.float32))
            noise_rms = float(np.sqrt(np.mean(np.concatenate(calib) ** 2)))
            threshold = max(noise_rms * 2.0, 300.0)
            print(f"완료 (임계값={threshold:.0f})")

            print(f">>> 말씀하세요  (최소 {self.min_sec:.0f}초, "
                  f"이후 {self.silence_sec:.0f}초 침묵 시 종료)")

            start = time.time()
            last_speech = start
            while True:
                elapsed = time.time() - start
                if elapsed > self.max_sec:
                    print(f"\n[녹음] 최대 {self.max_sec:.0f}초 도달, 종료")
                    break

                chunk = read_chunk()
                frames.append(chunk)

                rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
                if rms > threshold:
                    last_speech = time.time()

                if elapsed >= self.min_sec and \
                   time.time() - last_speech >= self.silence_sec:
                    print(f"\n[녹음] 침묵 감지, 종료 (총 {elapsed:.1f}초)")
                    break
        finally:
            # Ctrl+C·예외 포함 어떤 경우에도 arecord를 정리 (장치 점유 방지)
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        audio = np.concatenate(frames).astype(np.float32) / 32768.0
        return audio


# ══════════════════════════════════════════════════════════════════════════
# [2] SpeechToText — faster-whisper
# ══════════════════════════════════════════════════════════════════════════

class SpeechToText:
    def __init__(self, model_size: str = "small"):
        from faster_whisper import WhisperModel
        print(f"[STT] Whisper '{model_size}' 모델 로드 중... (첫 실행 시 다운로드)")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        print("[STT] 준비 완료")

    def transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self.model.transcribe(
            audio,
            language="ko",
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500,
                            "speech_pad_ms": 200},
            temperature=0.0,
            condition_on_previous_text=False,
        )
        return " ".join(s.text.strip() for s in segments).strip()


# ══════════════════════════════════════════════════════════════════════════
# [3] DateParser — 한국어 유통기한 표현 → YYYY-MM-DD
# ══════════════════════════════════════════════════════════════════════════

class DateParser:
    """'3일' → 오늘+3일, '일주일' → +7일, '한달' → +1개월 등."""

    # 고유어 날수 (하루 ~ 열흘)
    NATIVE_DAYS = {
        "하루": 1, "이틀": 2, "사흘": 3, "나흘": 4, "닷새": 5,
        "엿새": 6, "이레": 7, "여드레": 8, "아흐레": 9, "열흘": 10,
    }
    # 고유어 수사 (한 달, 두 달 ...)
    NATIVE_NUM = {
        "한": 1, "두": 2, "세": 3, "네": 4, "다섯": 5,
        "여섯": 6, "일곱": 7, "여덟": 8, "아홉": 9, "열": 10,
    }
    # 한자어 수사 (일 년, 이 년 ...)
    SINO_NUM = {"일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6}

    @staticmethod
    def _add_months(base: datetime, months: int) -> datetime:
        month = base.month - 1 + months
        year  = base.year + month // 12
        month = month % 12 + 1
        day   = min(base.day, calendar.monthrange(year, month)[1])
        return base.replace(year=year, month=month, day=day)

    @classmethod
    def date_pattern(cls) -> str:
        """문장에서 날짜 표현을 찾기 위한 통합 정규식.
        긴 표현을 먼저 배치해 부분 일치를 방지한다.
        (예: '7월 3일'이 '3일'로 잘려 인식되지 않도록)"""
        native_day = "|".join(cls.NATIVE_DAYS)
        native_num = "|".join(cls.NATIVE_NUM)
        sino       = "|".join(cls.SINO_NUM)
        return (
            r"(?:\d{4}\s*년\s*)?\d{1,2}\s*월\s*\d{1,2}\s*일"   # 7월 20일
            r"|\d{4}-\d{1,2}-\d{1,2}"                           # 2026-07-20
            r"|일\s*주일|일주일"                                  # 일주일
            rf"|(?:{native_num})\s*(?:달|주)"                    # 한달, 두주
            rf"|(?:{sino})\s*년"                                 # 일년, 이년
            rf"|(?:{native_day})"                                # 사흘, 열흘
            r"|\d+\s*(?:개월|달)"                                # 3개월
            r"|\d+\s*주"                                         # 2주
            r"|\d+\s*년"                                         # 1년
            r"|\d+\s*일"                                         # 3일
            r"|오늘|내일|모레|글피"
        )

    @classmethod
    def parse(cls, text: str) -> str | None:
        """날짜 표현 하나를 YYYY-MM-DD 문자열로 변환. 실패 시 None."""
        today = datetime.today()
        t = text.replace(" ", "")

        # 특수 단어
        special = {"오늘": 0, "내일": 1, "모레": 2, "글피": 3}
        for word, d in special.items():
            if word in t:
                return (today + timedelta(days=d)).strftime("%Y-%m-%d")

        # 절대 날짜: (2026년) 7월 20일
        m = re.search(r"(?:(\d{4})년)?(\d{1,2})월(\d{1,2})일", t)
        if m:
            year  = int(m.group(1)) if m.group(1) else today.year
            month, day = int(m.group(2)), int(m.group(3))
            try:
                d = datetime(year, month, day)
            except ValueError:
                return None
            # 연도 미지정인데 이미 지난 날짜면 내년으로 해석
            if not m.group(1) and d.date() < today.date():
                d = d.replace(year=year + 1)
            return d.strftime("%Y-%m-%d")

        m = re.search(r"\d{4}-\d{1,2}-\d{1,2}", t)
        if m:
            try:
                return datetime.strptime(m.group(0), "%Y-%m-%d") \
                               .strftime("%Y-%m-%d")
            except ValueError:
                return None

        # 일주일
        if "일주일" in t:
            return (today + timedelta(weeks=1)).strftime("%Y-%m-%d")

        # 고유어 날수: 하루, 이틀, 사흘 ...
        for word, days in cls.NATIVE_DAYS.items():
            if word in t:
                return (today + timedelta(days=days)).strftime("%Y-%m-%d")

        # 고유어 수사 + 달/주: 한달, 두주 ...
        for word, n in cls.NATIVE_NUM.items():
            if re.search(rf"{word}(?:개월|달)", t):
                return cls._add_months(today, n).strftime("%Y-%m-%d")
            if re.search(rf"{word}주", t):
                return (today + timedelta(weeks=n)).strftime("%Y-%m-%d")

        # 한자어 수사 + 년: 일년, 이년 ...
        for word, n in cls.SINO_NUM.items():
            if re.search(rf"{word}년", t):
                return cls._add_months(today, n * 12).strftime("%Y-%m-%d")

        # 숫자 표현 (긴 단위부터)
        m = re.search(r"(\d+)(?:개월|달)", t)
        if m:
            return cls._add_months(today, int(m.group(1))).strftime("%Y-%m-%d")
        m = re.search(r"(\d+)년", t)
        if m:
            return cls._add_months(today, int(m.group(1)) * 12) \
                      .strftime("%Y-%m-%d")
        m = re.search(r"(\d+)주", t)
        if m:
            return (today + timedelta(weeks=int(m.group(1)))) \
                   .strftime("%Y-%m-%d")
        m = re.search(r"(\d+)일", t)
        if m:
            return (today + timedelta(days=int(m.group(1)))) \
                   .strftime("%Y-%m-%d")

        return None


# ══════════════════════════════════════════════════════════════════════════
# [4] VoiceParser — "이름 카테고리 유통기한" 분해
# ══════════════════════════════════════════════════════════════════════════

class VoiceParser:
    """인식 텍스트에서 (이름, 카테고리, 유통기한)을 추출한다.

    규칙: 문장 안에서 날짜 표현을 먼저 찾고,
          그 앞 부분의 마지막 단어 = 카테고리, 나머지 = 이름.
    """

    @staticmethod
    def _clean(text: str) -> str:
        # Whisper가 붙이는 문장부호와 '뒤/후' 같은 군더더기 제거
        text = re.sub(r"[.,!?~]", " ", text)
        text = re.sub(r"\s+(뒤|후)(\s|$)", " ", text)
        return text.strip()

    @classmethod
    def parse(cls, text: str) -> dict | None:
        text = cls._clean(text)
        m = re.search(DateParser.date_pattern(), text)
        if not m:
            print(f"[파서] 날짜 표현을 찾지 못했습니다: '{text}'")
            return None

        exp_date = DateParser.parse(m.group(0))
        if not exp_date:
            print(f"[파서] 날짜 변환 실패: '{m.group(0)}'")
            return None

        tokens = text[:m.start()].split()
        if len(tokens) < 2:
            print(f"[파서] 이름·카테고리가 부족합니다 "
                  f"(형식: '이름 카테고리 유통기한'): '{text}'")
            return None

        return {
            "name":     " ".join(tokens[:-1]),
            "category": tokens[-1],
            "exp_date": exp_date,
        }


# ══════════════════════════════════════════════════════════════════════════
# [5] main
# ══════════════════════════════════════════════════════════════════════════

def run_once(recorder: AudioRecorder, stt: SpeechToText,
             save_db: bool) -> None:
    audio = recorder.record()

    t0 = time.time()
    text = stt.transcribe(audio)
    if not text:
        print("[STT] 음성을 인식하지 못했습니다.")
        return
    print(f"[STT] 인식 결과: \"{text}\"  ({time.time() - t0:.1f}초)")

    parsed = VoiceParser.parse(text)
    if not parsed:
        return
    print(f"[파서] 이름={parsed['name']} | 카테고리={parsed['category']} "
          f"| 유통기한={parsed['exp_date']}")

    if save_db:
        ok = db_manager.insert_item(
            name          = parsed["name"],
            category_name = parsed["category"],
            exp_date      = parsed["exp_date"],
        )
        print("[DB] 저장 완료 ✓" if ok else "[DB] 저장 실패 ✗")


def main():
    ap = argparse.ArgumentParser(description="음성 인식 → 냉장고 DB 저장")
    ap.add_argument("--model",   default="small",
                    choices=["tiny", "base", "small", "medium", "large-v3"])
    ap.add_argument("--device",  default=None,
                    help="ALSA 장치 직접 지정 (예: plughw:0,0). 미지정 시 자동")
    ap.add_argument("--min-sec", type=float, default=4.0,
                    help="최소 녹음 시간(초)")
    ap.add_argument("--silence", type=float, default=2.0,
                    help="발화 후 침묵 감지 시간(초)")
    ap.add_argument("--loop",    action="store_true",
                    help="반복 인식 모드 (Ctrl+C로 종료)")
    ap.add_argument("--no-db",   action="store_true",
                    help="DB에 저장하지 않고 인식만")
    args = ap.parse_args()

    save_db = not args.no_db
    if save_db:
        db_manager.create_table()
        print("[DB] 냉장고 DB 준비 완료")
    print("[안내] 발화 형식: '이름 카테고리 유통기한'")
    print("       예) 우유 유제품 3일 / 닭가슴살 육류 일주일 / 된장 장류 한달\n")

    recorder = AudioRecorder(device=args.device,
                             min_sec=args.min_sec,
                             silence_sec=args.silence)
    stt = SpeechToText(model_size=args.model)

    if args.loop:
        print("=== 반복 인식 모드 (Ctrl+C로 종료) ===\n")
        try:
            while True:
                run_once(recorder, stt, save_db)
                print("-" * 50)
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n종료합니다.")
    else:
        run_once(recorder, stt, save_db)


if __name__ == "__main__":
    main()