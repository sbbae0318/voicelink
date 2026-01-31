"""VoiceLink 사용 예제 - 자동 장치 탐지로 시스템 오디오 녹음."""

from voicelink import VoiceLink

# 자동으로 소리가 나는 장치를 찾아서 녹음
# auto_detect=True: 모든 입력 장치를 스캔하여 활성 오디오가 있는 장치 자동 선택
vl = VoiceLink(auto_detect=True)

# Record audio (30초간 녹음)
print("\n🎤 녹음 시작 (30초)...")
result = vl.capture_to_file("output.wav", duration=30)

if result:
    print(f"✅ 녹음 완료: {result}")
else:
    print("❌ 녹음 실패")

# Stream to OpenAI (필요시 주석 해제)
# stream = vl.start_streaming(api_key="sk-...")
