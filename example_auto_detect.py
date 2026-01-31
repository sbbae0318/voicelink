"""자동 장치 탐지 기능 테스트.

이 스크립트는 시스템의 모든 오디오 장치를 스캔하여
실제로 소리가 나오는 장치를 자동으로 찾아 녹음합니다.

사용법:
1. 먼저 YouTube나 음악 등 오디오를 재생합니다.
2. 이 스크립트를 실행합니다.
3. 자동으로 활성 장치를 찾아 녹음합니다.
"""

from voicelink import VoiceLink

print("=" * 60)
print("  VoiceLink 자동 장치 탐지 테스트")
print("=" * 60)
print()
print("⚠️ 테스트 전에 YouTube나 음악을 재생해주세요!")
print()
input("오디오 재생 중이면 Enter를 눌러 탐지 시작...")
print()

# 방법 1: 생성자에서 자동 탐지
print("\n[방법 1] VoiceLink(auto_detect=True) 사용")
print("-" * 50)
vl = VoiceLink(auto_detect=True)

if vl._default_device is not None:
    print(f"\n🎤 녹음 시작 (5초)...")
    result = vl.capture_to_file("auto_detected_recording.wav", duration=5)
    if result:
        print(f"✅ 저장됨: {result}")
    else:
        print("❌ 녹음 실패")
else:
    print("❌ 활성 장치를 찾을 수 없습니다.")

print()
print("=" * 60)

# 방법 2: 수동으로 장치 탐지 후 설정
print("\n[방법 2] detect_and_set_device() 사용")
print("-" * 50)
vl2 = VoiceLink()
device = vl2.detect_and_set_device()

if device:
    print(f"\n선택된 장치: [{device.index}] {device.name}")
else:
    print("활성 장치를 찾을 수 없습니다.")

print()
print("=" * 60)

# 방법 3: 활성 장치만 조회
print("\n[방법 3] find_active_audio_device() 직접 호출")
print("-" * 50)
from voicelink import find_active_audio_device

active = find_active_audio_device(verbose=True)
if active:
    print(f"\n활성 장치: [{active.index}] {active.name}")
