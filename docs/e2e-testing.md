# VoiceLink E2E Testing Guide

이 문서는 현재 `voicelink` 프로젝트(파이썬 CLI/라이브러리)의 구조를 요약하고, 프로젝트 특성에 맞는 E2E 테스트 구성을 제안합니다.

## 1) 프로젝트 요약

### 1.1 형태

- Python 패키지 (빌드/의존성: `pyproject.toml`)
- CLI 엔트리포인트: `voicelink = voicelink.cli:main`

### 1.2 핵심 모듈

- `voicelink/capture.py`
  - `sounddevice.InputStream` 기반 오디오 캡처 엔진
  - 콜백 등록(`add_callback`) 및 큐 버퍼링
- `voicelink/recorder.py`
  - 녹음 파일 저장
  - WAV: `scipy.io.wavfile`
  - MP3: `pydub` (옵션 의존성, ffmpeg 필요)
- `voicelink/stream.py`
  - OpenAI Realtime API(WebSocket) 스트리밍
  - thread 내부 asyncio loop로 송수신
  - PCM16/base64 인코딩 후 `input_audio_buffer.append` 전송
- `voicelink/glossary/`
  - 오디오 전사(Whisper) + DSPy 기반 용어 추출/설명 생성
- `voicelink/devices.py`
  - 오디오 디바이스 열거/선택, 루프백/가상 디바이스 휴리스틱
- `voicelink/platform_utils.py`
  - OS 감지 및 가상 오디오 드라이버 설치/상태 체크
- `voicelink/virtual_mic.py`
  - 입력 디바이스 -> 출력 디바이스 라우팅(가상 마이크 구성 도움)

### 1.3 CLI 커맨드(주요)

- `voicelink setup`: 드라이버 상태 점검 및 설치 안내
- `voicelink list-devices`: 디바이스 목록
- `voicelink record`: 파일 녹음
- `voicelink stream`: OpenAI Realtime 스트리밍
- `voicelink glossary`: 오디오 파일로부터 용어집 생성
- `voicelink virtual-mic`: 가상 마이크 구성 안내
- `voicelink info`: 시스템/의존성 정보

## 2) E2E 테스트 구성 원칙

VoiceLink의 “진짜 E2E”는 OS 오디오 드라이버(BlackHole/VB-CABLE/PulseAudio)와 실제 디바이스까지 포함합니다.
하지만 이 경로는 일반적인 CI 환경에서 재현이 어렵고 flake가 발생하기 쉽습니다.

따라서 E2E를 두 레이어로 나누는 구성을 권장합니다.

### 2.1 CI에서 항상 도는 E2E (권장): CLI Flow E2E (하드웨어/드라이버 없이)

목표:
- 사용자가 실제로 호출하는 CLI 경로에서 옵션 파싱/출력/에러 처리 흐름이 깨지지 않음을 보장
- 오디오 I/O 및 외부 네트워크(OpenAI)는 Fake/Mock으로 치환하여 안정적인 CI 신뢰도 확보

핵심 전략:
- Click CLI는 `click.testing.CliRunner`로 실행
- 오디오 캡처는 `sounddevice` 또는 `AudioCapture.start()`를 monkeypatch/fake
- OpenAI WebSocket은 실제 네트워크 대신 로컬 테스트 서버 또는 `_connect()`/`websockets.connect()`를 stub

권장 디렉토리 구조(예시):

```
tests/
  e2e/
    test_cli_setup.py
    test_cli_list_devices.py
    test_cli_record.py
    test_cli_stream.py
```

테스트 범위 예:
- `voicelink setup`
  - 드라이버 상태 체크 함수(`get_driver_status`, `setup_driver`)를 stub
  - 출력에 `[OK]` / `[MISSING]` 등 핵심 라인이 포함되는지 확인
- `voicelink record`
  - fake capture로 일정 샘플을 반환하게 만들고, wav 저장 루틴이 수행되는지 확인
  - tmpdir에 결과 파일 생성 여부 및 exit code 검증
- `voicelink stream`
  - WebSocket 연결을 stub하여 전송 메시지 형식(`input_audio_buffer.append`)이 맞는지 확인
  - 콜백(`add_response_callback`)이 이벤트를 받는지 확인

### 2.2 선택: 시스템 E2E (로컬/전용 러너 전용)

목표:
- macOS/Windows/Linux에서 “실제” 시스템 오디오 캡처가 가능한지 smoke 테스트

권장 운영 방식:
- 기본 CI에서는 제외 (`pytest -m system` 같이 마커로 분리)
- 개발자 머신 또는 self-hosted runner에서만 실행

검증 포인트 예:
- `voicelink list-devices`에 loopback/virtual 디바이스가 노출되는지
- `voicelink record` 결과 파일이 생성되고, 완전 무음(모든 샘플 0)인 케이스를 탐지할 수 있는지

## 3) Test Plan (권장)

### Objective

CI에서 재현 가능한 방식으로, CLI 사용자 플로우가 깨지지 않음을 보장합니다.

### Prerequisites

- 개발 의존성 설치:

```bash
pip install -e ".[dev]"
```

### Test Cases

1. `CLI setup`
   - Input: `voicelink setup`
   - Expected: 예외 없이 종료, 상태 메시지 출력이 기대 형태를 만족
2. `CLI record`
   - Input: `voicelink record -o <tmp>/out.wav -d 0.2`
   - Expected: fake audio를 통해 저장 루틴이 호출되고 결과 파일 경로/성공 메시지가 출력
3. `CLI stream`
   - Input: `voicelink stream` (연결부 stub)
   - Expected: WS 전송 payload가 기대 포맷이며, 콜백이 이벤트를 수신
4. `Glossary from transcript` (E2E 성격의 핵심 기능 검증)
   - Input: `GlossaryGenerator.from_transcript()`
   - Expected: 결과 문서/엔트리 구조가 정상

### Success Criteria

- 위 테스트가 모두 pass
- 기본 CI 테스트는 실제 디바이스/가상 드라이버/외부 네트워크에 의존하지 않음

## 4) 참고: Playwright(E2E 브라우저 테스트)

현재 repo는 Python CLI/라이브러리 중심이라 Playwright가 기본 선택지는 아닙니다.
향후 웹 UI가 별도 앱으로 추가되는 경우, Playwright의 `baseURL + webServer + storageState` 패턴으로 E2E를 구성하는 것이 표준입니다.
