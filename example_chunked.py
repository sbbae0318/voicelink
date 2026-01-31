"""청크 단위 녹음 테스트.

이 스크립트는 VoiceLink의 상시 녹음 기능을 테스트합니다.
30초 동안 실행하여 청크 파일 생성과 세션 관리를 확인합니다.
"""

import time
from pathlib import Path

from voicelink.chunked_recorder import ChunkedRecorder
from voicelink.config import RecordingSettings, SessionSettings, StorageSettings, VoiceLinkConfig
from voicelink.session import SessionManager

# 테스트용 설정 (짧은 청크 길이)
config = VoiceLinkConfig(
    recording=RecordingSettings(
        chunk_duration_seconds=10,  # 테스트용으로 10초 청크
        sample_rate=16000,
        channels=1,
        silence_threshold=0.0005,  # 낮은 임계값
    ),
    storage=StorageSettings(
        data_dir="./test_recordings",  # 테스트용 디렉토리
        retention_days=1,
    ),
    session=SessionSettings(
        silence_gap_seconds=20,  # 20초 무음이면 세션 분리
        min_session_duration=5,  # 최소 5초 세션
    ),
)

print("=" * 60)
print("  VoiceLink 청크 녹음 테스트")
print("=" * 60)
print()
print(f"청크 길이: {config.recording.chunk_duration_seconds}초")
print(f"샘플 레이트: {config.recording.sample_rate} Hz")
print(f"저장 위치: {config.storage.data_path}")
print(f"세션 분리 무음 간격: {config.session.silence_gap_seconds}초")
print()

# 콜백 함수들
def on_chunk_saved(chunk):
    status = "🔇 무음" if chunk.is_silent else "🔊 소리"
    print(f"  [{status}] 청크 저장: {chunk.file_path} (RMS: {chunk.rms_level:.6f})")

def on_session_created(session):
    print(f"\n🆕 새 세션 시작: {session.session_id}")

def on_session_completed(session):
    print(f"\n✅ 세션 완료: {session.session_id} ({session.duration_seconds:.1f}초, {session.total_chunks}개 청크)")

# 레코더 생성 및 시작
recorder = ChunkedRecorder(config)
recorder.on_chunk_saved(on_chunk_saved)
recorder.on_session_created(on_session_created)
recorder.on_session_completed(on_session_completed)

print("🎤 녹음 시작 (30초)...")
print("-" * 60)

if recorder.start():
    try:
        # 30초간 녹음
        for i in range(30):
            time.sleep(1)
            if i % 10 == 9:
                status = recorder.get_status()
                print(f"\n[{i+1}초] 청크: {status['chunk_count']}개, 총 길이: {status['total_duration_seconds']:.1f}초")
    except KeyboardInterrupt:
        print("\n\n사용자 중단")
    finally:
        print("\n" + "-" * 60)
        print("녹음 중지 중...")
        recorder.stop()
else:
    print("❌ 녹음 시작 실패")

print()
print("=" * 60)
print("  결과 요약")
print("=" * 60)

# 세션 매니저로 결과 확인
manager = SessionManager(config.storage.data_path)
sessions = manager.get_today_sessions()

print(f"\n오늘 생성된 세션: {len(sessions)}개")
for session in sessions:
    print(f"  - {session.session_id}")
    print(f"    시작: {session.start_time.strftime('%H:%M:%S')}")
    print(f"    길이: {session.duration_seconds:.1f}초")
    print(f"    청크: {session.total_chunks}개")
    print(f"    상태: {session.status}")

stats = manager.get_stats()
print(f"\n저장소 통계:")
print(f"  총 세션: {stats['total_sessions']}개")
print(f"  디스크 사용량: {stats['disk_usage_mb']:.2f} MB")

# 파일 목록 확인
data_dir = Path(config.storage.data_path)
if data_dir.exists():
    wav_files = list(data_dir.rglob("*.wav"))
    print(f"\n저장된 WAV 파일: {len(wav_files)}개")
    for f in wav_files[:5]:  # 처음 5개만 표시
        print(f"  - {f.relative_to(data_dir)}")
    if len(wav_files) > 5:
        print(f"  ... 외 {len(wav_files) - 5}개")

print()
print("테스트 완료!")
