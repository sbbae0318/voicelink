# VoiceLink 사용 가이드

## 빠른 시작

### 1. 설치

```bash
# 기본 설치
pip install voicelink

# 모든 기능 포함
pip install voicelink[all]

# 개발용
pip install -e ".[all,dev]"
```

### 2. 기본 사용법

#### 단순 녹음 (기존 방식)
```python
from voicelink import VoiceLink

vl = VoiceLink(auto_detect=True)
vl.capture_to_file("output.wav", duration=30)
```

#### 상시 녹음 데몬 (새로운 방식)
```bash
# 녹음 시작 (백그라운드)
voicelink start

# 상태 확인
voicelink status

# 녹음 중지
voicelink stop
```

---

## 사용 시나리오

### 시나리오 1: 하루 종일 녹음

```
08:00  PC 켜기
       └─▶ VoiceLink 자동 시작

09:00  줌 회의 (1시간)
       └─▶ 세션 #1 (120개 청크)

12:00  유튜브 시청 (30분)
       └─▶ 세션 #2 (60개 청크)

14:00  팀 통화 (2시간)
       └─▶ 세션 #3 (240개 청크)

18:00  PC 끄기
       └─▶ 자동 저장
```

### 시나리오 2: 세션 전사 및 요약

```bash
# 오늘 세션 목록 확인
voicelink sessions list --today

# 출력:
# ID                      | 시작          | 길이     | 태그
# sess_20260131_090000   | 09:00        | 01:00:00 | 
# sess_20260131_120000   | 12:00        | 00:30:00 | 
# sess_20260131_140000   | 14:00        | 02:00:00 | 

# 특정 세션 내보내기
voicelink sessions export sess_20260131_090000 -o meeting.wav

# 전사 (외부 도구 사용)
whisper meeting.wav --output_format txt

# 또는 VoiceLink 내장 전사
voicelink transcribe sess_20260131_090000

# 용어집 생성
voicelink glossary sess_20260131_090000 -o glossary.md

# 요약 생성
voicelink summary sess_20260131_090000 -o summary.md
```

---

## 설정

### 설정 파일 위치

- Windows: `%USERPROFILE%\.voicelink\config.yaml`
- macOS/Linux: `~/.voicelink/config.yaml`

### 기본 설정

```yaml
# ~/.voicelink/config.yaml

recording:
  # 청크 길이 (초)
  chunk_duration_seconds: 30
  
  # 샘플레이트 (16000 = Whisper 최적)
  sample_rate: 16000
  
  # 채널 수 (1 = 모노)
  channels: 1
  
  # 포맷 (wav 또는 mp3)
  format: wav
  
  # 무음 임계값 (이 RMS 미만은 무음으로 판정)
  silence_threshold: 0.001
  
storage:
  # 데이터 저장 디렉토리
  data_dir: ~/voicelink_data
  
  # 보관 일수 (0 = 무제한)
  retention_days: 7
  
  # 자동 정리 활성화
  auto_cleanup: true
  
session:
  # 세션 분리 무음 간격 (초)
  silence_gap_seconds: 60
  
  # 최소 세션 길이 (초) - 이보다 짧으면 세션으로 인정 안함
  min_session_duration: 30
  
device:
  # 자동 장치 탐지
  auto_detect: true
  
  # 선호 장치 이름 (null = 자동)
  preferred_device: null
  
  # 대체 장치 목록
  fallback_devices:
    - "Voicemeeter Out B1"
    - "Stereo Mix"
    - "CABLE Output"

transcription:
  # 기본 전사 방법 (whisper_api, whisper_local, external)
  method: whisper_api
  
  # OpenAI API 키 (OPENAI_API_KEY 환경변수 사용 가능)
  api_key: null
  
  # 언어 (null = 자동 감지)
  language: null
  
  # 외부 전사 명령어 템플릿
  external_command: "whisper {input} --output_format txt -o {output}"
```

---

## Python API

### 청크 녹음 (Chunked Recording)

```python
from voicelink import ChunkedRecorder, RecorderConfig

config = RecorderConfig(
    chunk_duration=30,
    sample_rate=16000,
    data_dir="./recordings",
)

recorder = ChunkedRecorder(config)

# 녹음 시작
recorder.start()

# ... 녹음 중 ...

# 녹음 중지
recorder.stop()

# 세션 정보
sessions = recorder.get_sessions()
for session in sessions:
    print(f"{session.id}: {session.duration}초")
```

### 세션 관리 (Session Management)

```python
from voicelink import SessionManager

manager = SessionManager(data_dir="./recordings")

# 세션 목록
sessions = manager.list_sessions()

# 특정 세션 가져오기
session = manager.get_session("sess_20260131_090000")

# 세션 청크 목록
chunks = session.get_chunks()

# 세션 내보내기 (청크 병합)
session.export("meeting.wav")

# 세션 태그 추가
session.add_tag("meeting")
session.add_tag("project-alpha")

# 세션 삭제
manager.delete_session(session.id)
```

### 전사 및 요약

```python
from voicelink import SessionManager
from voicelink.whisper import transcribe_audio
from voicelink.glossary import GlossaryGenerator

manager = SessionManager()
session = manager.get_session("sess_20260131_090000")

# 세션 내보내기
audio_path = session.export()

# 전사
result = transcribe_audio(audio_path)
print(result.text)

# 용어집 생성
generator = GlossaryGenerator()
glossary = generator.from_text(result.text)
glossary.save("glossary.md")
```

---

## CLI 명령어 상세

### voicelink start

녹음 시작 (백그라운드 데몬)

```bash
voicelink start [OPTIONS]

Options:
  --foreground    포그라운드 실행
  --config PATH   설정 파일 경로
  --data-dir DIR  데이터 저장 디렉토리
  --device NAME   녹음 장치 지정
```

### voicelink sessions

세션 관리

```bash
# 세션 목록
voicelink sessions list [OPTIONS]
  --today         오늘 세션만
  --date DATE     특정 날짜 (YYYY-MM-DD)
  --tag TAG       태그로 필터

# 세션 내보내기
voicelink sessions export SESSION_ID [OPTIONS]
  -o, --output PATH   출력 파일 경로
  --format FORMAT     출력 포맷 (wav, mp3)

# 세션 태그
voicelink sessions tag SESSION_ID TAG

# 세션 삭제
voicelink sessions delete SESSION_ID [--force]
```

### voicelink transcribe

세션 전사

```bash
voicelink transcribe SESSION_ID [OPTIONS]
  --method METHOD   전사 방법 (whisper_api, whisper_local, external)
  --language LANG   언어 코드
  -o, --output PATH 출력 파일 경로
```

### voicelink cleanup

만료 데이터 정리

```bash
voicelink cleanup [OPTIONS]
  --dry-run   실제 삭제 없이 미리보기
  --force     확인 없이 삭제
  --days N    N일 이전 데이터 삭제
```

---

## 외부 전사 도구 연동

### OpenAI Whisper (로컬)

```bash
# Whisper 설치
pip install openai-whisper

# 세션 내보내기 후 전사
voicelink sessions export sess_xxx -o temp.wav
whisper temp.wav --model medium --language ko

# 또는 설정 파일에서 외부 명령 지정
# config.yaml:
# transcription:
#   method: external
#   external_command: "whisper {input} --model medium -o {output}"
```

### Faster Whisper

```bash
# 설치
pip install faster-whisper

# 설정
# config.yaml:
# transcription:
#   method: external
#   external_command: "faster-whisper {input} --model medium -o {output}"
```

### whisper.cpp

```bash
# config.yaml:
# transcription:
#   method: external
#   external_command: "./whisper.cpp/main -m ggml-medium.bin -f {input} > {output}"
```

---

## 문제 해결

### 녹음이 무음인 경우

1. 장치 자동 탐지 확인:
   ```bash
   voicelink list-devices
   ```

2. 활성 장치 탐지:
   ```bash
   voicelink detect-active
   ```

3. 수동 장치 지정:
   ```yaml
   # config.yaml
   device:
     auto_detect: false
     preferred_device: "Voicemeeter Out B1"
   ```

### 세션이 너무 많이 분리되는 경우

```yaml
# config.yaml
session:
  silence_gap_seconds: 120  # 무음 간격을 2분으로 늘림
```

### 디스크 공간 부족

```bash
# 자동 정리 실행
voicelink cleanup

# 보관 일수 줄이기
# config.yaml:
# storage:
#   retention_days: 3
```

---

*Last Updated: 2026-01-31*
