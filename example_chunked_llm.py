"""청크 단위 녹음 + LLM 자동 제목 생성 테스트.

이 스크립트는 VoiceLink의 상시 녹음 기능과 LLM 기반 제목 생성을 테스트합니다.
Docker에서 Ollama가 실행 중이어야 합니다.
"""

import time
from pathlib import Path

from voicelink.chunked_recorder import ChunkedRecorder
from voicelink.config import (
    RecordingSettings,
    SessionSettings,
    StorageSettings,
    VoiceLinkConfig,
)
from voicelink.session import SessionManager
from voicelink.title_generator import TitleGenerator, TitleGeneratorConfig

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

# LLM 제목 생성기
title_gen = TitleGenerator(TitleGeneratorConfig(
    model="qwen2.5:3b",  # RTX 3090 Ti에서 빠르게 동작
))

print("=" * 60)
print("  VoiceLink 청크 녹음 + LLM 제목 생성 테스트")
print("=" * 60)
print()
print(f"청크 길이: {config.recording.chunk_duration_seconds}초")
print(f"샘플 레이트: {config.recording.sample_rate} Hz")
print(f"저장 위치: {config.storage.data_path}")
print(f"세션 분리 무음 간격: {config.session.silence_gap_seconds}초")
print()

# LLM 연결 확인
if title_gen.is_available():
    print(f"🤖 LLM 모델: {title_gen.config.model} ✅")
else:
    print("⚠️ LLM 서버 연결 실패 - 제목 생성 비활성화")
print()


def on_chunk_saved(chunk):
    """청크 저장 콜백."""
    status = "🔇 무음" if chunk.is_silent else "🔊 소리"
    print(f"  [{status}] 청크: {chunk.file_path} (RMS: {chunk.rms_level:.6f})")


def on_session_created(session):
    """세션 생성 콜백."""
    print(f"\n🆕 새 세션 시작: {session.session_id}")


def on_session_completed(session):
    """세션 완료 콜백 - LLM으로 제목 생성."""
    duration = session.duration_seconds
    chunks = session.total_chunks
    print(f"\n✅ 세션 완료: {session.session_id}")
    print(f"   길이: {duration:.1f}초, 청크: {chunks}개")

    # LLM으로 제목 생성 (실제로는 전사문이 필요하지만, 여기서는 시뮬레이션)
    if title_gen.is_available():
        # 실제 사용 시에는 Whisper로 전사 후 제목 생성
        # 여기서는 테스트로 샘플 텍스트 사용
        sample_transcript = "오늘 녹음된 오디오입니다. 테스트 중입니다."
        title = title_gen.generate(sample_transcript)
        print(f"   📝 자동 생성 제목: {title}")


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
                print(f"\n⏱️  [{i+1}초] 청크: {status['chunk_count']}개")
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

print()
print("테스트 완료!")
