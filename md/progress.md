# VoiceLink 개발 진행 상황

## 버전 히스토리

### v0.1.0 - 기본 기능 (2026-01-31) ✅

#### 완료된 기능

- [x] **핵심 오디오 캡처**
  - sounddevice 기반 오디오 입력
  - float32/int16 포맷 지원
  - 44100Hz/16000Hz 샘플레이트

- [x] **장치 관리**
  - 모든 오디오 장치 나열
  - loopback/virtual 장치 필터링
  - 플랫폼별 최적 장치 자동 선택 (Windows/macOS/Linux)

- [x] **자동 장치 탐지** 🆕
  - 모든 입력 장치 RMS 스캔
  - 활성 오디오 신호 감지
  - 최고 RMS 장치 자동 선택

- [x] **파일 저장**
  - WAV 파일 저장
  - MP3 파일 저장 (pydub 필요)

- [x] **VAD (Voice Activity Detection)** 🆕
  - webrtcvad 기반 음성 구간 추출
  - 무음 제거
  - WAV 파일 후처리

- [x] **Whisper 연동** 🆕
  - OpenAI Whisper API 연동
  - 무음 파일 스킵
  - 배치 전사 (디렉토리)

- [x] **로깅 시스템** 🆕
  - 파일 + 콘솔 로깅
  - 로그 레벨 설정

- [x] **CLI 기본 명령어**
  - `voicelink list-devices`
  - `voicelink record`
  - `voicelink setup`
  - `voicelink info`

---

### v0.2.0 - 세션 관리 (2026-01-31) ✅

#### 완료된 기능

- [x] **청크 단위 저장** 🆕
  - 설정 가능한 청크 길이 (기본 30초)
  - 타임스탬프 기반 파일명: `HH-MM-SS_NNNN.wav`
  - 버퍼링 및 자동 분할

- [x] **일별 폴더 구조** 🆕
  - YYYY-MM-DD 폴더 자동 생성
  - SQLite 기반 메타데이터 저장

- [x] **세션 메타데이터** 🆕
  - SQLite 기반 세션 DB (`sessions.db`)
  - 세션 ID 생성: `sess_YYYYMMDD_HHMMSS_xxxxxx`
  - 청크-세션 자동 매핑

- [x] **세션 경계 감지** 🆕
  - 실시간 RMS 모니터링
  - 무음 간격 기반 세션 자동 분리
  - 세션 자동 시작/완료

- [x] **설정 시스템** 🆕
  - YAML 기반 설정 파일 (`config.yaml`)
  - 녹음/저장소/세션/장치/전사 설정

#### 테스트 결과

| 테스트 | 결과 | 비고 |
|--------|------|------|
| 청크 녹음 30초 | ✅ | 3개 청크 (10초 x 3) 저장됨 |
| 일별 폴더 생성 | ✅ | `2026-01-31/` 폴더 생성 |
| 세션 자동 생성 | ✅ | `sess_20260131_213324_4bc6c5` |
| 세션 완료 | ✅ | 30.0초, 3개 청크 |
| SQLite DB 저장 | ✅ | `sessions.db` 생성 |

#### 추가된 파일

| 파일 | 설명 |
|------|------|
| `voicelink/config.py` | YAML 설정 관리 모듈 |
| `voicelink/session.py` | 세션/청크 관리 모듈 |
| `voicelink/chunked_recorder.py` | 청크 단위 녹음 모듈 |
| `example_chunked.py` | 청크 녹음 테스트 스크립트 |
| `md/spec.md` | 요구사항 명세서 |
| `md/usage.md` | 사용 가이드 |
| `md/progress.md` | 개발 진행 상황 |
| `md/todo.md` | TODO 리스트 |

---

### v0.3.0 - 데몬 모드 (예정)

- [ ] 백그라운드 서비스
- [ ] 시스템 시작 시 자동 실행
- [ ] 트레이 아이콘 (Windows/macOS)
- [ ] 웹 대시보드 (선택)

---

### v0.4.0 - 전사/요약 파이프라인 (예정)

- [ ] 세션 내보내기 (청크 병합)
- [ ] 외부 전사 도구 연동 인터페이스
- [ ] 용어집 자동 생성
- [ ] LLM 기반 회의 요약

---

## 최근 변경 사항

### 2026-01-31

#### 추가된 파일

| 파일 | 설명 |
|------|------|
| `voicelink/auto_detect.py` | 활성 오디오 장치 자동 탐지 |
| `voicelink/vad.py` | Voice Activity Detection 모듈 |
| `voicelink/whisper.py` | Whisper API 연동 모듈 |
| `voicelink/logging_config.py` | 로깅 설정 모듈 |
| `example_debug.py` | 디버그용 예제 스크립트 |
| `example_auto_detect.py` | 자동 탐지 예제 스크립트 |

#### 수정된 파일

| 파일 | 변경 내용 |
|------|----------|
| `voicelink/__init__.py` | auto_detect 옵션, 새 모듈 통합 |
| `example.py` | auto_detect=True 사용 |
| `pyproject.toml` | vad 선택적 의존성 추가 |

#### listener 프로젝트에서 통합한 기능

| 기능 | 원본 | VoiceLink |
|------|------|-----------|
| VAD | `vad_processor.py` | `voicelink/vad.py` |
| 무음 감지 | `ask.py:is_silent()` | `voicelink/vad.py:is_silent()` |
| Whisper 전사 | `ask.py:transcribe_audio()` | `voicelink/whisper.py` |
| 로깅 | `__init__.py` | `voicelink/logging_config.py` |

---

## 테스트 결과

### 2026-01-31 테스트

| 테스트 | 결과 | 비고 |
|--------|------|------|
| 장치 나열 | ✅ | 70개 장치 감지 |
| 자동 장치 탐지 | ✅ | Voicemeeter Out 6 선택 |
| 30초 녹음 | ✅ | output.wav 생성됨 |
| VAD 모듈 로드 | ✅ | webrtcvad 없이도 graceful |
| Whisper 모듈 로드 | ✅ | openai 필요 |

---

## 알려진 이슈

### 열린 이슈

1. **일부 장치 프로브 실패**
   - WASAPI 장치 중 일부가 열기 실패
   - 영향: 탐지 오류 표시되나 기능 정상

2. **CABLE Output 무음**
   - 시스템 출력이 CABLE Input으로 라우팅 안됨
   - 해결: Voicemeeter 사용 또는 수동 출력 장치 변경

### 해결된 이슈

1. ~~장치 자동 선택 시 무음~~ → auto_detect 구현으로 해결

---

*Last Updated: 2026-01-31 21:18*
