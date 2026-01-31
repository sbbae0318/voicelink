"""VoiceLink 상시 녹음 서비스.

이 스크립트는 무한 루프로 실행되어 상시 녹음을 수행합니다.
Windows 시작 시 자동 실행되도록 설정할 수 있습니다.
"""

import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from voicelink.chunked_recorder import ChunkedRecorder
from voicelink.config import (
    DeviceSettings,
    RecordingSettings,
    SessionSettings,
    StorageSettings,
    VoiceLinkConfig,
)
from voicelink.logging_config import setup_logging
from voicelink.title_generator import TitleGenerator, TitleGeneratorConfig

# 로깅 설정
setup_logging(log_file="./logs/voicelink.log", level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceLinkService:
    """VoiceLink 상시 녹음 서비스."""

    def __init__(self):
        self.config = VoiceLinkConfig(
            recording=RecordingSettings(
                chunk_duration_seconds=30,  # 30초 청크
                sample_rate=16000,
                channels=1,
                silence_threshold=0.01,  # 임계값 상향 (기존 0.001)
            ),
            storage=StorageSettings(
                data_dir="./recordings",  # 녹음 저장 위치
                retention_days=30,  # 30일 보관
            ),
            session=SessionSettings(
                silence_gap_seconds=10,  # 10초 무음이면 세션 종료 (기존 60초)
                min_session_duration=10,  # 최소 10초 세션
            ),
            device=DeviceSettings(
                auto_detect=False,  # 자동 탐지 끄기 (장치 고정)
                auto_switch=False,  # 자동 전환 끄기 (안정성 우선)
                silence_timeout_for_switch=5.0,  # (사용 안 함)
                preferred_device="Voicemeeter Out B2",  # Potato B2 (Aux)
            ),
        )

        self.recorder = ChunkedRecorder(self.config)
        self.title_gen = TitleGenerator(TitleGeneratorConfig(
            ollama_url="http://localhost:11434",
            model="qwen2.5:3b",
        ))

        self._running = False
        self._setup_signal_handlers()
        self._setup_callbacks()

    def _setup_signal_handlers(self):
        """시그널 핸들러 설정."""
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """종료 시그널 처리."""
        logger.info(f"종료 시그널 수신 ({signum})")
        self._running = False

    def _setup_callbacks(self):
        """콜백 설정."""
        self.recorder.on_chunk_saved(self._on_chunk_saved)
        self.recorder.on_session_created(self._on_session_created)
        self.recorder.on_session_completed(self._on_session_completed)
        self.recorder.on_device_changed(self._on_device_changed)

    def _on_device_changed(self, device_index: int, device_name: str):
        """장치 변경 콜백."""
        logger.info(f"🎤 녹음 장치 자동 전환: [{device_index}] {device_name}")

    def _on_chunk_saved(self, chunk):
        """청크 저장 콜백."""
        status = "무음" if chunk.is_silent else "녹음"
        logger.debug(f"[{status}] {chunk.file_path} (RMS: {chunk.rms_level:.4f})")

    def _on_session_created(self, session):
        """세션 생성 콜백."""
        logger.info(f"새 세션 시작: {session.session_id}")

    def _on_session_completed(self, session):
        """세션 완료 콜백."""
        duration = session.duration_seconds
        logger.info(f"세션 완료: {session.session_id} ({duration:.1f}초)")

        # LLM으로 제목 생성 (비동기로 처리 가능)
        if self.title_gen.is_available():
            try:
                # 간단한 제목 생성 (실제로는 전사 후 생성)
                sample_text = f"녹음 세션 {session.start_time.strftime('%H:%M')}"
                title = self.title_gen.generate(sample_text)
                session.title = title
                self.recorder.session_manager.save_session(session)
                logger.info(f"제목 생성: {title}")
            except Exception as e:
                logger.warning(f"제목 생성 실패: {e}")

    def start(self):
        """서비스 시작."""
        logger.info("=" * 60)
        logger.info("VoiceLink 상시 녹음 서비스 시작")
        logger.info("=" * 60)
        logger.info(f"청크 길이: {self.config.recording.chunk_duration_seconds}초")
        logger.info(f"저장 위치: {self.config.storage.data_path}")
        logger.info(f"보관 기간: {self.config.storage.retention_days}일")
        logger.info("")

        if not self.recorder.start():
            logger.error("녹음 시작 실패")
            return False

        self._running = True
        logger.info("녹음 시작됨 (Ctrl+C로 종료)")
        logger.info("-" * 60)

        return True

    def run_forever(self):
        """무한 루프 실행."""
        if not self.start():
            return

        try:
            while self._running:
                time.sleep(1)

                # 매 시간마다 상태 로깅
                if datetime.now().minute == 0 and datetime.now().second < 5:
                    status = self.recorder.get_status()
                    logger.info(
                        f"[상태] 청크: {status['chunk_count']}개, "
                        f"총 녹음: {status['total_duration_seconds']/3600:.1f}시간"
                    )

        except KeyboardInterrupt:
            logger.info("사용자 중단")
        finally:
            self.stop()

    def stop(self):
        """서비스 중지."""
        logger.info("-" * 60)
        logger.info("녹음 중지 중...")
        self.recorder.stop()

        status = self.recorder.get_status()
        logger.info(f"총 청크: {status['chunk_count']}개")
        logger.info(f"총 녹음 시간: {status['total_duration_seconds']/60:.1f}분")
        logger.info("VoiceLink 서비스 종료")


def main():
    """메인 함수."""
    service = VoiceLinkService()
    service.run_forever()


if __name__ == "__main__":
    main()
