# VoiceLink TODO

## 현재 스프린트: v0.2.0 세션 관리

### 🔴 높은 우선순위

#### 청크 단위 저장 시스템

- [x] `ChunkedRecorder` 클래스 구현 ✅
  - [x] 설정 가능한 청크 길이 (기본 30초)
  - [x] 자동 파일 분할
  - [x] 버퍼 관리

- [x] 일별 폴더 구조 ✅
  - [x] `YYYY-MM-DD/` 자동 생성
  - [x] 청크 파일명: `HH-MM-SS_NNN.wav`
  - [x] 일별 `meta.json` 생성

- [ ] 자동 삭제 스케줄러
  - [ ] 설정된 retention_days 기준 삭제
  - [ ] 디스크 공간 모니터링

#### 세션 관리

- [x] `Session` 데이터 클래스 ✅
  - [x] session_id 생성 규칙
  - [x] 청크 리스트 관리
  - [x] 메타데이터 (시작/종료 시간, RMS 등)

- [x] `SessionManager` 클래스 ✅
  - [x] SQLite DB 스키마 정의
  - [x] 세션 CRUD 작업
  - [x] 세션 조회 필터링

- [x] 세션 경계 감지 ✅
  - [x] 실시간 RMS 모니터링
  - [x] 무음 간격 트래킹
  - [x] 자동 세션 생성/종료

### 🟡 중간 우선순위

#### CLI 확장

- [ ] `voicelink sessions list`
  - [ ] 테이블 출력
  - [ ] 날짜/태그 필터

- [ ] `voicelink sessions export <id>`
  - [ ] 청크 병합
  - [ ] 포맷 변환 옵션

- [ ] `voicelink sessions tag <id> <tag>`
  - [ ] 태그 추가/제거

- [ ] `voicelink cleanup`
  - [ ] dry-run 모드
  - [ ] 공간 확보량 표시

#### 설정 시스템

- [ ] `config.yaml` 파싱
- [ ] 기본 설정 생성
- [ ] CLI에서 설정 오버라이드

### 🟢 낮은 우선순위

- [ ] 세션 수동 분리/병합
- [ ] 세션 메모/설명 추가
- [ ] 녹음 상태 알림

---

## 다음 스프린트: v0.3.0 데몬 모드

### 예정 작업

- [ ] Windows 서비스 등록
- [ ] macOS launchd 등록
- [ ] Linux systemd 서비스
- [ ] 시스템 트레이 아이콘
- [ ] PID 파일 관리
- [ ] 그레이스풀 셧다운

---

## v0.4.0 전사/요약 파이프라인

### 🔴 세션 완료 시 자동 전사+요약

- [ ] **자동 전사 파이프라인**
  - [ ] 세션 완료 감지 (`on_session_completed`)
  - [ ] 청크 병합 → 단일 WAV 파일
  - [ ] Whisper API 전사 (또는 로컬 whisper.cpp)
  - [ ] 전사 결과 저장 (`transcription_path`)
  - [ ] 전사 상태 업데이트 (`transcription_status`)

- [ ] **LLM 요약 생성**
  - [ ] 전사문 → 5단어 이내 제목 생성
  - [ ] 전사문 → 3-5문장 요약 생성
  - [ ] sessions.db에 `title`, `summary` 저장
  - [ ] 웹 대시보드 연동

- [ ] **비동기 처리**
  - [ ] 백그라운드 작업 큐 (threading 또는 asyncio)
  - [ ] 전사 진행률 표시
  - [ ] 에러 핸들링 및 재시도

### 예정 작업

- [ ] 세션 오디오 병합 내보내기
- [ ] 외부 전사 도구 실행기 (whisper CLI)
- [ ] 전사 결과 저장/관리
- [ ] 용어집 추출 (NER)
- [ ] Markdown 보고서 생성

---

## 기술 부채

### 코드 품질

- [ ] 단위 테스트 작성 (pytest)
- [ ] 통합 테스트 작성
- [ ] 타입 힌트 완성
- [ ] 문서화 (docstring 보완)

### 성능 최적화

- [ ] 메모리 프로파일링
- [ ] 디스크 I/O 최적화
- [ ] 멀티스레딩 개선

### 리팩토링

- [ ] 모듈 구조 정리
- [ ] 설정 클래스 통합
- [ ] 에러 핸들링 일관화

---

## 버그 수정

### 열린 버그

| ID | 설명 | 심각도 |
|----|------|--------|
| BUG-001 | 일부 WASAPI 장치 프로브 실패 | 낮음 |

### 해결된 버그

| ID | 설명 | 해결일 |
|----|------|--------|

---

## 아이디어 백로그

> 나중에 고려할 기능들

- [ ] 웹 대시보드 (Flask/FastAPI)
- [ ] 모바일 앱 알림
- [ ] 클라우드 동기화
- [ ] **오디오 장치 점유 문제 해결**
  - [x] 현재 사용 중인 장치(Current InputStream)는 Probe 대상 제외 (디스코드 끊김 방지)
  - [ ] Non-intrusive Probing (WASAPI Loopback 모니터링만 수행)
  - [ ] Voicemeeter API 연동 (더 안정적인 제어)
- [ ] 화자 분리 (Speaker Diarization)
- [ ] 실시간 자막 오버레이
- [ ] 자동 중요 순간 감지
- [ ] 회의 참석자 이름 태깅
- [ ] **Smart Mixing (동시 녹음)**
  - [ ] 시스템 오디오 + 마이크 동시 캡처 (Multi-device capture)
  - [ ] 트랙 별도 저장 또는 스마트 믹싱
  - [ ] 화자 분리 시 소스(Mic/System) 기반 자동 라벨링

---

## 완료된 작업

### 2026-01-31

- [x] 기본 오디오 캡처 구현
- [x] 장치 자동 탐지 (`auto_detect.py`)
- [x] VAD 모듈 (`vad.py`)
- [x] Whisper 연동 (`whisper.py`)
- [x] 로깅 시스템 (`logging_config.py`)
- [x] listener 프로젝트 분석 및 통합
- [x] example.py auto_detect 적용
- [x] 명세서/사용가이드 문서화

---

*Last Updated: 2026-01-31 21:18*
