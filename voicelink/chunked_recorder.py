"""청크 단위 녹음 모듈.

상시 녹음을 위한 청크 단위 저장 시스템입니다.
"""

import logging
import threading
import time
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from .config import VoiceLinkConfig, get_config
from .session import AudioChunk, Session, SessionManager
from .vad import VADConfig, extract_voice_segments

logger = logging.getLogger(__name__)


@dataclass
class ChunkedRecorderState:
    """청크 레코더 상태."""
    is_recording: bool = False
    current_session: Optional[Session] = None
    chunk_count: int = 0
    total_duration: float = 0.0
    last_chunk_time: Optional[datetime] = None
    consecutive_silence_count: int = 0


class ChunkedRecorder:
    """청크 단위로 오디오를 녹음하는 레코더.

    설정된 길이(기본 30초)마다 청크 파일을 저장하고,
    무음 간격을 감지하여 세션을 자동으로 분리합니다.
    """

    def __init__(
        self,
        config: Optional[VoiceLinkConfig] = None,
        device: Optional[int] = None,
    ):
        self.config = config or get_config()
        self.device = device

        self.state = ChunkedRecorderState()
        self.session_manager = SessionManager(self.config.storage.data_path)

        self._stream: Optional[sd.InputStream] = None
        self._audio_buffer: list[np.ndarray] = []
        self._buffer_lock = threading.Lock()
        self._chunk_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._on_chunk_saved: list[Callable[[AudioChunk], None]] = []
        self._on_session_created: list[Callable[[Session], None]] = []
        self._on_chunk_saved: list[Callable[[AudioChunk], None]] = []
        self._on_session_created: list[Callable[[Session], None]] = []
        self._on_session_completed: list[Callable[[Session], None]] = []
        self._on_device_changed: list[Callable[[int, str], None]] = []
        
        # 마지막 스캔 시간
        self._last_device_scan_time = 0.0

    @property
    def data_dir(self) -> Path:
        """데이터 저장 디렉토리를 반환합니다."""
        return self.config.storage.data_path

    def _get_today_dir(self) -> Path:
        """오늘 날짜 폴더를 반환합니다."""
        today = datetime.now().strftime("%Y-%m-%d")
        today_dir = self.data_dir / today
        today_dir.mkdir(parents=True, exist_ok=True)
        return today_dir

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags,
    ) -> None:
        """오디오 입력 콜백."""
        if status:
            logger.warning(f"오디오 상태: {status}")

        with self._buffer_lock:
            self._audio_buffer.append(indata.copy())

    def _calculate_rms(self, audio_data: np.ndarray) -> float:
        """RMS 레벨을 계산합니다."""
        return float(np.sqrt(np.mean(audio_data ** 2)))

    def _is_silent(self, audio_data: np.ndarray) -> bool:
        """무음 여부를 판단합니다."""
        rms = self._calculate_rms(audio_data)
        rms = self._calculate_rms(audio_data)
        return rms < self.config.recording.silence_threshold

    def _calculate_speech_ratio(self, audio_int16: np.ndarray) -> float:
        """오디오의 음성 구간 비율을 계산합니다."""
        if len(audio_int16) == 0:
            return 0.0
        
        try:
            # VAD 설정 (기본값)
            config = VADConfig(
                sample_rate=self.config.recording.sample_rate,
                frame_duration_ms=30,
                aggressiveness=3  # 보수적 판정 (확실한 음성만)
            )
            
            # 음성 추출
            segments = list(extract_voice_segments(
                audio_int16.tobytes(),
                sample_rate=config.sample_rate,
                config=config
            ))
            
            if not segments:
                return 0.0
                
            total_voice_samples = sum(len(seg) for seg in segments) / 2  # 2 bytes per sample
            total_samples = len(audio_int16)
            
            return total_voice_samples / total_samples
            
        except Exception as e:
            # logger.warning(f"VAD 계산 오류: {e}")
            return 0.0

    def _save_chunk(self, audio_data: np.ndarray) -> Optional[AudioChunk]:
        """청크를 저장합니다."""
        if len(audio_data) == 0:
            return None

        now = datetime.now()
        today_dir = self._get_today_dir()

        # 파일명 생성
        time_str = now.strftime("%H-%M-%S")
        chunk_index = self.state.chunk_count + 1
        filename = f"{time_str}_{chunk_index:04d}.wav"
        file_path = today_dir / filename
        relative_path = f"{today_dir.name}/{filename}"

        # int16 변환 (저장 및 VAD용)
        try:
            if audio_data.dtype == np.float32:
                # 클리핑 방지
                audio_clipped = np.clip(audio_data, -1.0, 1.0)
                audio_int16 = (audio_clipped * 32767).astype(np.int16)
            else:
                audio_int16 = audio_data.astype(np.int16)
        except Exception as e:
            logger.error(f"오디오 변환 실패: {e}")
            return None

        # RMS 계산
        rms = self._calculate_rms(audio_data)

        # [VAD] 음성 비율 계산
        speech_ratio = self._calculate_speech_ratio(audio_int16)
        
        # [스마트 무음 판정]
        # 1. RMS가 임계값 미만 (너무 조용함)
        # 2. RMS는 높지만 사람 목소리 비율이 5% 미만 (잡음/소음)
        is_silent = (rms < self.config.recording.silence_threshold) or (speech_ratio < 0.05)

        # WAV 파일 저장
        try:
            with wave.open(str(file_path), "wb") as wf:
                wf.setnchannels(self.config.recording.channels)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.config.recording.sample_rate)
                wf.writeframes(audio_int16.tobytes())

        except Exception as e:
            logger.error(f"청크 저장 실패: {e}")
            return None

        # 청크 객체 생성
        duration = len(audio_data) / self.config.recording.sample_rate
        chunk = AudioChunk(
            file_path=relative_path,
            timestamp=now,
            duration_seconds=duration,
            index=chunk_index,
            rms_level=rms,
            is_silent=is_silent,
            speech_ratio=speech_ratio,
        )

        self.state.chunk_count = chunk_index
        self.state.total_duration += duration
        self.state.last_chunk_time = now

        logger.debug(f"청크 저장: {filename} (RMS: {rms:.4f}, VAD: {speech_ratio*100:.1f}%, 무음: {is_silent})")

        # 콜백 호출
        for callback in self._on_chunk_saved:
            try:
                callback(chunk)
            except Exception as e:
                logger.error(f"청크 콜백 오류: {e}")

        return chunk

    def _handle_session(self, chunk: AudioChunk) -> None:
        """세션 관리를 처리합니다."""
        silence_gap = self.config.session.silence_gap_seconds
        chunk_duration = self.config.recording.chunk_duration_seconds

        # 연속 무음 청크 카운트
        if chunk.is_silent:
            self.state.consecutive_silence_count += 1
        else:
            self.state.consecutive_silence_count = 0

        # 무음 간격으로 세션 분리
        silence_chunks_threshold = silence_gap // chunk_duration

        # 현재 세션이 없으면 새 세션 시작
        if self.state.current_session is None:
            if not chunk.is_silent:
                self._start_new_session(chunk)
            return

        # 세션에 청크 추가
        self.state.current_session.add_chunk(chunk)
        self.session_manager.save_session(self.state.current_session)

        # 충분한 무음이면 세션 종료
        if self.state.consecutive_silence_count >= silence_chunks_threshold:
            self._complete_current_session()
            
        # 연속 무음 시간이 길어지면 다른 장치 스캔 (Smart Silence Monitoring)
        if (
            self.config.device.auto_switch 
            and chunk.is_silent 
            and self.state.consecutive_silence_count >= (self.config.device.silence_timeout_for_switch / chunk_duration)
        ):
            self._check_alternative_devices()

    def _start_new_session(self, first_chunk: AudioChunk) -> None:
        """새 세션을 시작합니다."""
        session = Session.create_new(first_chunk.timestamp)
        session.add_chunk(first_chunk)

        self.state.current_session = session
        self.session_manager.save_session(session)

        logger.info(f"새 세션 시작: {session.session_id}")
        
        # [초기 유효성 검사] 시작하자마자 첫 청크가 사실상 무음이라면(VAD < 5%) 세션 바로 폐기
        # 이는 '녹음 시작 후 N초 동안 음성이 없으면 종료' 로직에 해당함
        if first_chunk.speech_ratio < 0.05:
             logger.info(f"세션 취소 (초기 음성 미검출): {first_chunk.speech_ratio*100:.1f}%")
             self._complete_current_session()  # 저장 후 즉시 종료/삭제됨 (너무 짧아서)
             return

        for callback in self._on_session_created:
            try:
                callback(session)
            except Exception as e:
                logger.error(f"세션 생성 콜백 오류: {e}")

    def _complete_current_session(self) -> None:
        """현재 세션을 완료합니다."""
        if self.state.current_session is None:
            return

        session = self.state.current_session

        # 최소 세션 길이 체크
        if session.duration_seconds < self.config.session.min_session_duration:
            logger.debug(f"세션 무시 (너무 짧음): {session.duration_seconds:.1f}초")
            self.session_manager.delete_session(session.session_id)
        else:
            session.complete()
            self.session_manager.save_session(session)
            logger.info(f"세션 완료: {session.session_id} ({session.duration_seconds:.1f}초)")

            for callback in self._on_session_completed:
                try:
                    callback(session)
                except Exception as e:
                    logger.error(f"세션 완료 콜백 오류: {e}")

        self.state.current_session = None
        self.state.consecutive_silence_count = 0

    def _chunk_processing_loop(self) -> None:
        """청크 처리 루프 (별도 스레드에서 실행)."""
        chunk_duration = self.config.recording.chunk_duration_seconds
        samples_per_chunk = chunk_duration * self.config.recording.sample_rate

        while not self._stop_event.is_set():
            time.sleep(0.1)  # 100ms마다 체크

            with self._buffer_lock:
                if not self._audio_buffer:
                    continue

                # 버퍼 데이터 합치기
                buffer_data = np.concatenate(self._audio_buffer, axis=0)

                # 청크 크기에 도달했는지 확인
                if len(buffer_data) < samples_per_chunk:
                    continue

                # 청크 추출
                chunk_data = buffer_data[:int(samples_per_chunk)]
                remaining = buffer_data[int(samples_per_chunk):]

                # 버퍼 갱신
                self._audio_buffer = [remaining] if len(remaining) > 0 else []

            # 청크 저장 및 세션 처리
            chunk = self._save_chunk(chunk_data)
            if chunk:
                self._handle_session(chunk)

    def start(self) -> bool:
        """녹음을 시작합니다."""
        if self.state.is_recording:
            logger.warning("이미 녹음 중입니다.")
            return False

        # 장치 선택
        device_idx = self.device
        if device_idx is None and self.config.device.auto_detect:
            from .auto_detect import auto_select_capture_device
            device = auto_select_capture_device(verbose=True)
            if device:
                device_idx = device.index
                logger.info(f"자동 선택된 장치: [{device_idx}] {device.name}")

        # 스트림 시작
        try:
            self._stream = sd.InputStream(
                device=device_idx,
                samplerate=self.config.recording.sample_rate,
                channels=self.config.recording.channels,
                dtype="float32",
                blocksize=1024,
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as e:
            logger.error(f"스트림 시작 실패: {e}")
            return False

        # 청크 처리 스레드 시작
        self._stop_event.clear()
        self._chunk_thread = threading.Thread(
            target=self._chunk_processing_loop,
            daemon=True,
        )
        self._chunk_thread.start()

        self.state.is_recording = True
        logger.info("청크 녹음 시작됨")
        return True

    def stop(self) -> None:
        """녹음을 중지합니다."""
        if not self.state.is_recording:
            return

        # 스레드 중지
        self._stop_event.set()
        if self._chunk_thread:
            self._chunk_thread.join(timeout=5.0)

        # 남은 버퍼 저장
        with self._buffer_lock:
            if self._audio_buffer:
                remaining = np.concatenate(self._audio_buffer, axis=0)
                if len(remaining) > self.config.recording.sample_rate:  # 최소 1초
                    chunk = self._save_chunk(remaining)
                    if chunk:
                        self._handle_session(chunk)
                self._audio_buffer = []

        # 현재 세션 완료
        self._complete_current_session()

        # 스트림 중지
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self.state.is_recording = False
        logger.info("청크 녹음 중지됨")

    def on_chunk_saved(self, callback: Callable[[AudioChunk], None]) -> None:
        """청크 저장 시 호출될 콜백을 등록합니다."""
        self._on_chunk_saved.append(callback)

    def on_session_created(self, callback: Callable[[Session], None]) -> None:
        """세션 생성 시 호출될 콜백을 등록합니다."""
        self._on_session_created.append(callback)

    def on_session_completed(self, callback: Callable[[Session], None]) -> None:
        """세션 완료 시 호출될 콜백을 등록합니다."""
        self._on_session_completed.append(callback)

    def on_device_changed(self, callback: Callable[[int, str], None]) -> None:
        """장치 변경 시 호출될 콜백을 등록합니다."""
        self._on_device_changed.append(callback)

    def _check_alternative_devices(self) -> None:
        """다른 활성 장치가 있는지 스캔하고 전환합니다."""
        # 너무 잦은 스캔 방지 (최소 5초 간격)
        now = time.time()
        if now - self._last_device_scan_time < 5.0:
            return
        
        self._last_device_scan_time = now
        
        # 별도 스레드에서 실행하여 녹음 루프 차단 방지
        threading.Thread(target=self._scan_and_switch, daemon=True).start()

    def _scan_and_switch(self) -> None:
        """백그라운드에서 장치를 스캔하고 필요시 전환합니다."""
        try:
            from .auto_detect import find_active_audio_device
            
            # 현재 장치
            current_idx = self.device
            if hasattr(self._stream, 'device'):
                current_idx = self._stream.device
            
            logger.debug(f"대안 장치 스캔 시작 (현재: {current_idx})...")
            
            # 활성 장치 찾기
            active_device = find_active_audio_device(
                probe_duration=0.5,
                threshold=0.005,  # 약간 높은 임계값
                verbose=False
            )
            
            if active_device and active_device.index != current_idx:
                logger.info(f"더 나은 신호 발견: [{active_device.index}] {active_device.name} (RMS: {active_device.rms_level:.4f})")
                self.switch_device(active_device.index)
            else:
                logger.debug("대안 장치 없음")
                
        except Exception as e:
            logger.warning(f"장치 스캔 실패: {e}")

    def switch_device(self, new_device_index: int) -> bool:
        """녹음 장치를 전환합니다."""
        logger.info(f"장치 전환 시도: {self.device} -> {new_device_index}")
        
        # 기존 스트림 중지
        old_stream = self._stream
        self._stream = None  # 콜백에서 참조 방지
        
        if old_stream:
            try:
                old_stream.stop()
                old_stream.close()
            except Exception as e:
                logger.warning(f"기존 스트림 종료 오류: {e}")
        
        # 새 스트림 시작
        try:
            self.device = new_device_index
            self._stream = sd.InputStream(
                device=new_device_index,
                samplerate=self.config.recording.sample_rate,
                channels=self.config.recording.channels,
                dtype="float32",
                blocksize=1024,
                callback=self._audio_callback,
            )
            self._stream.start()
            
            # 장치 이름 찾기
            device_info = sd.query_devices(new_device_index)
            device_name = device_info['name']
            
            logger.info(f"장치 전환 성공: [{new_device_index}] {device_name}")
            
            # 상태 초기화
            self.state.consecutive_silence_count = 0
            
            # 콜백 호출
            for callback in self._on_device_changed:
                try:
                    callback(new_device_index, device_name)
                except Exception as e:
                    logger.error(f"장치 변경 콜백 오류: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"장치 전환 실패: {e}")
            # 실패 시 복구 시도? (생략)
            return False

    def get_status(self) -> dict:
        """현재 상태를 반환합니다."""
        return {
            "is_recording": self.state.is_recording,
            "current_session_id": (
                self.state.current_session.session_id
                if self.state.current_session else None
            ),
            "chunk_count": self.state.chunk_count,
            "total_duration_seconds": self.state.total_duration,
            "last_chunk_time": (
                self.state.last_chunk_time.isoformat()
                if self.state.last_chunk_time else None
            ),
        }

    def __enter__(self) -> "ChunkedRecorder":
        """컨텍스트 매니저 진입."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """컨텍스트 매니저 종료."""
        self.stop()
