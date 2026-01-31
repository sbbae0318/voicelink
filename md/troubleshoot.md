# 오디오 장치 트러블슈팅 및 Insight

## 1. 오디오 장치 간섭 (Audio Glitch/Drop-out)

### 증상
- VoiceLink 실행 중 디스코드 마이크가 끊기거나 상대방 목소리가 뚝뚝 끊김.
- VoiceMeeter 오디오 버퍼가 튀거나(Crackling) 잠시 멈춤.

### 원인
- **Intrusive Probing (침습적 탐지)**: `auto_detect` 모듈이 "활성 오디오 장치"를 찾기 위해, 시스템의 **모든** 입력 장치를 0.5초간 실제로 열어서(`sd.InputStream`) RMS 레벨을 측정함.
- 이 과정에서 이미 다른 앱(디스코드, OBS 등)이 점유 중인 장치를 건드리면, 드라이버 레벨에서 스트림 재설정이나 버퍼 초기화가 발생하여 끊김 현상이 발생함.

### 해결책 & Insight
1.  **Blacklist (제외 목록) 적용**:
    - `microphone`, `mic`, `webcam` 등 사용자의 목소리가 들어가는 민감한 장치는 스캔 대상에서 **영구 제외**.
    - `voicemeeter out b1` 등 메인 통신용 가상 장치도 제외.
2.  **Self-Protection (자가 보호)**:
    - 현재 VoiceLink가 녹음 중인 장치 인덱스를 스캔 목록에서 제외하여, 자기 자신이 끊기는 문제 방지.
3.  **Fixed Mode (고정 모드) 권장**:
    - 안정적인 환경에서는 자동 탐지보다 **특정 장치 고정(`preferred_device`)**이 훨씬 안정적임.
    - `auto_detect=False`, `auto_switch=False` 설정 적용.

---

## 2. 좀비 프로세스 (Zombie Processes)

### 증상
- 터미널을 닫거나 종료 스크립트를 실행해도, 잠시 후 다시 백그라운드에서 오디오 간섭이 발생함.

### 원인
- **Windows Task Scheduler**: `setup_autostart.ps1` 스크립트가 프로세스 종료 시 **1분 후 자동 재시작**하도록 설정함.
- 사용자가 의도적으로 종료해도 "오류로 인한 종료"로 간주되어 되살아남.

### 해결책
- 작업 스케줄러에서 `VoiceLink Recording Service` 작업 삭제.
- 개발 단계에서는 자동 재시작 옵션을 신중하게 사용해야 함.
- `taskkill /F /IM python.exe /T` 명령어로 모든 오디오 관련 파이썬 프로세스 일괄 종료.

---

## 3. 장치 식별의 견고성 (Device Robustness)

### 증상
- 재부팅하거나 USB 장치를 변경하면 오디오 장치 인덱스(Index)가 변경됨.
- 설정 파일에 `device_index=13`으로 저장해두면, 나중에 엉뚱한 장치(마이크 등)를 녹음하게 됨.

### 해결책
- **Name-based Lookup**: 인덱스 대신 **장치 이름 패턴(Name Pattern)**을 사용하여 장치를 식별.
- `find_device_by_name("VoiceMeeter Out B2")` 함수 구현.
- 부분 일치(Partial Match) 및 대소문자 무시(Case-insensitive) 로직으로 드라이버 이름이 조금 달라도(MME/WDM 등) 유연하게 찾도록 개선.

---

## 4. Smart Mixing 아이디어 (Future)
- **현재**: Loopback(듣는 소리) 또는 Microphone(말하는 소리) 중 하나만 선택 가능.
- **목표**: "내가 듣는 소리"와 "내가 말하는 소리"를 동시에 녹음하되 트랙을 분리하거나 스마트하게 믹싱.
- **방안**:
  - `python-sounddevice`는 단일 스트림만 지원하므로, 두 개의 스트림(InputStream 2개)을 비동기(`asyncio` 또는 `threading`)로 열어야 함.
  - 두 스트림의 샘플링 레이트를 동기화하는 것이 관건.
