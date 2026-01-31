# VoiceLink 요구사항 명세서

## 개요

VoiceLink는 **상시 실행형 시스템 오디오 캡처 도구**입니다. 컴퓨터를 켜면 자동으로 실행되어 모든 시스템 오디오를 녹음하고, 세션(회의, 통화 등) 단위로 관리합니다.

## 핵심 사용 시나리오

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        VoiceLink 워크플로우                              │
└─────────────────────────────────────────────────────────────────────────┘

[항상 실행]                    [나중에 처리]                [최종 출력]
    │                              │                           │
    ▼                              ▼                           ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ VoiceLink│───▶│ 청크 저장 │───▶│ 세션 감지 │───▶│ 전사     │───▶│ 요약/용어집│
│ Daemon  │    │ (30초)   │    │ (무음 경계)│    │ (외부)   │    │ 생성     │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                   │
                   ▼
              ┌─────────┐
              │ Meta DB │
              └─────────┘
```

## 기능 요구사항

### FR-1: 상시 녹음 (Always-On Recording)

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| FR-1.1 | 시스템 시작 시 자동 실행 (데몬/서비스) | 높음 |
| FR-1.2 | 활성 오디오 장치 자동 탐지 | 높음 |
| FR-1.3 | 백그라운드 리소스 최소화 (<2% CPU) | 중간 |
| FR-1.4 | 녹음 상태 트레이 아이콘 표시 | 낮음 |

### FR-2: 청크 저장 (Chunked Storage)

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| FR-2.1 | 고정 길이(기본 30초) 청크 단위 저장 | 높음 |
| FR-2.2 | 일별 폴더 구조 (`YYYY-MM-DD/`) | 높음 |
| FR-2.3 | 청크 파일 네이밍: `{timestamp}_{index}.wav` | 높음 |
| FR-2.4 | 설정 가능한 삭제 주기 (기본 7일) | 높음 |
| FR-2.5 | 무음 청크 자동 스킵 또는 압축 저장 | 중간 |

### FR-3: 세션 관리 (Session Management)

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| FR-3.1 | 연속 오디오 구간을 세션으로 그룹화 | 높음 |
| FR-3.2 | 세션 메타데이터 JSON 저장 | 높음 |
| FR-3.3 | 세션 경계 감지 (무음 N초 이상) | 높음 |
| FR-3.4 | 수동 세션 분리/병합 CLI 명령 | 중간 |
| FR-3.5 | 세션 태그/라벨 기능 | 낮음 |

### FR-4: 전사 연동 (Transcription Integration)

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| FR-4.1 | 세션 단위 오디오 병합 내보내기 | 높음 |
| FR-4.2 | 외부 전사 도구 연동 인터페이스 | 중간 |
| FR-4.3 | Whisper API 직접 연동 옵션 | 중간 |

### FR-5: 용어집/요약 생성 (Glossary & Summary)

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| FR-5.1 | 전사 결과 기반 기술 용어 추출 | 중간 |
| FR-5.2 | LLM 기반 용어 설명 생성 | 중간 |
| FR-5.3 | 세션 요약 자동 생성 | 중간 |

## 비기능 요구사항

### NFR-1: 성능

- 청크 저장 지연: < 100ms
- 메모리 사용량: < 100MB
- 디스크 I/O: 최소화 (버퍼링 활용)

### NFR-2: 저장 공간

- 30초 청크 (16kHz, 모노, 16비트): ~960KB
- 1시간 녹음: ~115MB
- 8시간/일: ~920MB
- 7일 보관: ~6.5GB

### NFR-3: 안정성

- 예외 발생 시 자동 재시작
- 디스크 공간 부족 시 오래된 파일 자동 삭제
- 크래시 복구: 마지막 세션 상태 복원

## 데이터 구조

### 디렉토리 구조

```
voicelink_data/
├── config.yaml              # 설정 파일
├── sessions.db              # 세션 메타데이터 DB (SQLite)
├── 2026-01-31/
│   ├── meta.json            # 일별 메타데이터
│   ├── 14-30-00_001.wav     # 청크 파일
│   ├── 14-30-30_002.wav
│   ├── 14-31-00_003.wav
│   └── ...
├── 2026-02-01/
│   └── ...
└── exports/                 # 세션 내보내기
    └── session_2026-01-31_143000.wav
```

### 세션 메타데이터 (sessions.db)

```json
{
  "session_id": "sess_20260131_143000",
  "start_time": "2026-01-31T14:30:00",
  "end_time": "2026-01-31T15:45:00",
  "duration_seconds": 4500,
  "chunks": [
    "2026-01-31/14-30-00_001.wav",
    "2026-01-31/14-30-30_002.wav",
    ...
  ],
  "avg_rms": 0.0234,
  "status": "completed",
  "tags": ["meeting", "project-x"],
  "transcription_status": "pending",
  "transcription_path": null
}
```

### 설정 파일 (config.yaml)

```yaml
recording:
  chunk_duration_seconds: 30
  sample_rate: 16000
  channels: 1
  format: wav
  silence_threshold: 0.001
  
storage:
  data_dir: ~/voicelink_data
  retention_days: 7
  auto_cleanup: true
  
session:
  silence_gap_seconds: 60  # 무음 60초 이상이면 세션 분리
  min_session_duration: 30  # 최소 세션 길이
  
device:
  auto_detect: true
  preferred_device: null  # 또는 장치 이름
```

## 인터페이스

### CLI 명령어

```bash
# 데몬 관리
voicelink start           # 녹음 시작 (데몬)
voicelink stop            # 녹음 중지
voicelink status          # 상태 확인

# 세션 관리
voicelink sessions list   # 세션 목록
voicelink sessions export <session_id> -o output.wav
voicelink sessions tag <session_id> meeting
voicelink sessions delete <session_id>

# 전사
voicelink transcribe <session_id>
voicelink transcribe --all-pending

# 용어집/요약
voicelink glossary <session_id>
voicelink summary <session_id>

# 유지보수
voicelink cleanup         # 만료된 파일 삭제
voicelink stats           # 저장 공간 통계
```

## 마일스톤

### v0.1.0 - MVP (현재)
- [x] 기본 오디오 캡처
- [x] 장치 자동 탐지
- [x] 파일 저장

### v0.2.0 - 세션 관리
- [ ] 청크 단위 저장
- [ ] 일별 폴더 구조
- [ ] 세션 메타데이터
- [ ] 세션 경계 감지

### v0.3.0 - 데몬 모드
- [ ] 백그라운드 서비스
- [ ] 자동 시작
- [ ] 트레이 아이콘

### v0.4.0 - 전사 연동
- [ ] 세션 내보내기
- [ ] 외부 전사 도구 연동
- [ ] 용어집/요약 생성

---

*Last Updated: 2026-01-31*
